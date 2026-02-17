

CREATE OR REPLACE PROCEDURE update_campaign_performance_summary(
    p_campaign_id TEXT,
    p_campaign_type TEXT,
    p_lead_model TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_campaign_name TEXT;
    v_campaign_objective_id TEXT;
    v_cost_per_lead JSONB;
    v_engagement_stats JSONB;
    v_failure_reasons JSONB;
    v_intent_distribution JSONB;

    v_sql TEXT;
BEGIN
    -- get campaign name, campaign objective id and cost per lead from the campaign model. Either pre-sales or post-sales
    IF p_campaign_type = 'pre-sales' THEN
        SELECT
            dict->>'campaign_name',
            dict->>'campaign_objective_id'
        INTO
            v_campaign_name,
            v_campaign_objective_id
        FROM pre_sales_campaign
        WHERE dict->>'campaign_id' = p_campaign_id;

    ELSIF p_campaign_type = 'post-sales' THEN
        SELECT
            dict->>'campaign_name',
            dict->>'campaign_objective_id'
        INTO
            v_campaign_name,
            v_campaign_objective_id
        FROM post_sales_campaign
        WHERE dict->>'campaign_id' = p_campaign_id;

    ELSE
        RAISE EXCEPTION 'Invalid campaign type: %', p_campaign_type;
    END IF;

    -- cost per lead can be calculated as total cost / converted leads. Total cost can be obtained from campaign model and converted leads can be obtained from contact_status table
    WITH total_cost AS (
    SELECT
        COALESCE(SUM((dict->>'item_total')::NUMERIC), 0) AS cost
    FROM billing
    WHERE dict->>'campaign_id' = p_campaign_id
    --   AND dict->>'campaign_type' = p_campaign_type
      AND dict->>'transaction_type' = 'debit'
    ),
    converted_per_channel AS (
        SELECT
            LOWER(dict->>'channel') AS channel,
            COUNT(*) AS converted_leads
        FROM session
        WHERE dict->>'campaign_id' = p_campaign_id
        AND dict->>'campaign_type' = p_campaign_type
        AND LOWER(dict->>'disposition') = 'converted'
        GROUP BY 1
    ),
    total_converted AS (
        SELECT COALESCE(SUM(converted_leads), 0) AS total
        FROM converted_per_channel
    )
    SELECT jsonb_agg(
        jsonb_build_object(
            'channel', c.channel,
            'total_cost', 
                CASE 
                    WHEN t.total = 0 THEN 0
                    ELSE ROUND(tc.cost * c.converted_leads / t.total, 2)
                END,
            'converted_leads', c.converted_leads,
            'cost_per_lead',
                CASE
                    WHEN c.converted_leads = 0 THEN NULL
                    ELSE ROUND(
                        (tc.cost * c.converted_leads / NULLIF(t.total, 0))
                        / c.converted_leads,
                        2
                    )
                END
        )
    )
    INTO v_cost_per_lead
    FROM converted_per_channel c
    CROSS JOIN total_cost tc
    CROSS JOIN total_converted t;

    -- engagement stats
    v_sql := format($sql$
        SELECT jsonb_agg(
            jsonb_build_object(
                'channel', channel,
                'sent_called', sent_called,
                'delivered_answered', delivered_answered,
                'read_greeted', read_greeted,
                'interacted', interacted,
                'converted', converted,
                'total', total
            )
            ORDER BY channel
        )
        FROM (
            SELECT
                COALESCE(channel, 'all') AS channel,

                COUNT(*) FILTER (
                    WHERE status IN (
                        'attempted','engaged','converted',
                        'reached','contacted','failed','error'
                    )
                ) AS sent_called,

                COUNT(*) FILTER (
                    WHERE status IN (
                        'reached','contacted','engaged','converted'
                    )
                ) AS delivered_answered,

                COUNT(*) FILTER (
                    WHERE status IN (
                        'contacted','engaged','converted'
                    )
                ) AS read_greeted,

                COUNT(*) FILTER (
                    WHERE status IN (
                        'engaged','converted'
                    )
                ) AS interacted,

                COUNT(*) FILTER (WHERE status = 'converted') AS converted,
                COUNT(*) AS total

            FROM (
                SELECT
                    LOWER(dict->>'last_session_channel') AS channel,
                    LOWER(dict->>'disposition') AS status
                FROM %I
                WHERE dict->>'campaign_id' = $1
                AND dict->>'campaign_type' = $2
            ) s
            GROUP BY GROUPING SETS (
                (channel),   -- per channel
                ()           -- ALL channels
            )
        ) t
    $sql$, p_lead_model);

    EXECUTE v_sql
    USING p_campaign_id, p_campaign_type
    INTO v_engagement_stats;


    -- failure reasons stats
    SELECT jsonb_agg(
        jsonb_build_object(
            'channel', channel,
            'message', message,
            'count', cnt
        )
    )
    INTO v_failure_reasons
    FROM (
        SELECT
            LOWER(dict->>'channel') AS channel,
            COALESCE(
                NULLIF(dict->>'failure_reason', ''),
                NULLIF(dict->>'error_message', ''),
                'failed'
            ) AS message,
            COUNT(*) AS cnt
        FROM contact_status
        WHERE dict->>'campaign_id' = p_campaign_id
          AND dict->>'campaign_type' = p_campaign_type
          AND LOWER(dict->>'provider_status') = 'failed'
        GROUP BY 1, 2
    ) t;

    v_sql := format($sql$
        SELECT jsonb_agg(
            jsonb_build_object(
                'disposition_detail', disposition_detail,
                'count', cnt
            )
            ORDER BY cnt DESC
        )
        FROM (
            SELECT
                COALESCE(
                    NULLIF(LOWER(dict->>'disposition_detail'), ''),
                    'unknown'
                ) AS disposition_detail,
                COUNT(*) AS cnt
            FROM %I
            WHERE dict->>'campaign_id' = $1
            AND dict->>'campaign_type' = $2
            GROUP BY 1
        ) t
    $sql$, p_lead_model);

    EXECUTE v_sql
    USING p_campaign_id, p_campaign_type
    INTO v_intent_distribution;

    -- finally inserting the stats into campaign_performance_summary model
    INSERT INTO campaign_performance_summary (
        campaign_performance_summary_id,
        dict,
        created,
        updated
    )
    VALUES (
        p_campaign_id || '-' || p_campaign_type,
        jsonb_build_object(
            'campaign_id', p_campaign_id,
            'campaign_type', p_campaign_type,
            'campaign_name', v_campaign_name,
            'campaign_objective_id', v_campaign_objective_id,
            'cost_per_lead_by_channel', COALESCE(v_cost_per_lead, '[]'::jsonb),
            'engagement_stats', COALESCE(v_engagement_stats, '[]'::jsonb),
            'failure_stats_by_channel', COALESCE(v_failure_reasons, '[]'::jsonb),
            'intent_distribution_by_channel', COALESCE(v_intent_distribution, '[]'::jsonb),
            'created', (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT,
            'updated', (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT
        ),
        NOW(),
        NOW()
    )
    ON CONFLICT (campaign_performance_summary_id)
    DO UPDATE SET
        dict = EXCLUDED.dict,
        updated = EXCLUDED.updated;

END;
$$;
