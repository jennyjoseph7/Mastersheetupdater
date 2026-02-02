--Structure of campaign_performance_summary

-- 1.cron job performance_summary --This task checks for campaigns which require an update to their performance summary.
    -- It does this by checking for campaigns which have a newer updated timestamp than the
    -- latest updated timestamp in the campaign_performance_summary table.

    -- It then executes a stored procedure to update the campaign_performance_summary table
    -- with the latest data from the campaigns

-- 2. run_campaign_performance_cron --This task is triggered by the cron job and calls the update_campaign_performance_summary stored procedure by passing the campaign_id and campaign_type.

-- 3. update_campaign_performance_summary --This stored procedure takes the campaign_id and campaign_type as input and updates the campaign_performance_summary table with the latest data from the campaigns.
    -- Calculates:
        -- engagement_stats
        -- failure_reasons
        -- intent_distribution
        -- cost_per_lead
    -- It then inserts or updates the campaign_performance_summary table with the calculated data.
    -- Ex- 
    -- {
    --         "created": 1767001870120,
    --         "updated": 1767001870120,
    --         "campaign_id": "63d8d5e1-640b-363f-bbe4-e298772149c8",
    --         "campaign_name": "Fronx Launch Campaign",
    --         "campaign_type": "pre-sales",
    --         "cost_per_lead": 0,
    --         "engagement_stats": [
    --             {
    --                 "count": 13,
    --                 "status": "failed",
    --                 "channel": "whatsapp_chat"
    --             },
    --             {
    --                 "count": 108,
    --                 "status": "unknown",
    --                 "channel": "whatsapp_chat"
    --             }
    --         ],
    --         "failure_stats_by_channel": [
    --             {
    --                 "count": 13,
    --                 "channel": "whatsapp_chat",
    --                 "message": "failed"
    --             }
    --         ],
    --         "campaign_performance_summary_id": "7b2c9a6d-e406-3539-81c2-60d799d29275"
    --     }


CREATE OR REPLACE PROCEDURE update_campaign_performance_summary(
    p_campaign_id TEXT,
    p_campaign_type TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_campaign_name TEXT;
    v_campaign_objective_id TEXT;
    v_cost_per_lead NUMERIC;
    v_engagement_stats JSONB;
    v_failure_reasons JSONB;
    v_intent_distribution JSONB;
BEGIN
    -- get campaign name, campaign objective id and cost per lead from the campaign model. Either pre-sales or post-sales
    IF p_campaign_type = 'pre-sales' THEN
        SELECT
            dict->>'campaign_name',
            dict->>'campaign_objective_id',
            (dict->>'cost_per_lead')::NUMERIC
        INTO
            v_campaign_name,
            v_campaign_objective_id,
            v_cost_per_lead
        FROM pre_sales_campaign
        WHERE dict->>'campaign_id' = p_campaign_id;

    ELSIF p_campaign_type = 'post-sales' THEN
        SELECT
            dict->>'campaign_name',
            dict->>'campaign_objective_id',
            (dict->>'cost_per_lead')::NUMERIC
        INTO
            v_campaign_name,
            v_campaign_objective_id,
            v_cost_per_lead
        FROM post_sales_campaign
        WHERE dict->>'campaign_id' = p_campaign_id;

    ELSE
        RAISE EXCEPTION 'Invalid campaign type: %', p_campaign_type;
    END IF;

    -- engagement stats
    SELECT jsonb_agg(
        jsonb_build_object(
            'channel', channel,
            'status', status,
            'count', cnt
        )
    )
    INTO v_engagement_stats
    FROM (
        SELECT
            LOWER(dict->>'channel') AS channel,
            CASE LOWER(dict->>'provider_status')
                WHEN 'contacted' THEN 'read'
                WHEN 'attempted' THEN 'sent'
                WHEN 'queued' THEN 'initiated'
                WHEN 'reached' THEN 'delivered'
                WHEN 'failed' THEN 'failed'
                WHEN 'engaged' THEN 'interacted'
                WHEN 'initiated' THEN 'initiated'
                WHEN 'sent' THEN 'sent'
                WHEN 'delivered' THEN 'delivered'
                WHEN 'read' THEN 'read'
                ELSE 'unknown'
            END AS status,
            COUNT(*) AS cnt
        FROM contact_status
        WHERE dict->>'campaign_id' = p_campaign_id
          AND dict->>'campaign_type' = p_campaign_type
        GROUP BY 1, 2
    ) t;

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

    SELECT jsonb_agg(
        jsonb_build_object(
            'channel', channel,
            'count', cnt
        )
    )
    INTO v_intent_distribution
    FROM (
        SELECT 
            LOWER(dict->>'channel') AS channel,
            COUNT(*) AS cnt
        FROM session 
        WHERE dict->>'campaign_id' = p_campaign_id
        AND (LOWER(dict->>'disposition') IN ('interacted','engaged') OR LOWER(dict->>'status') IN ('interacted','engaged'))
        GROUP BY 1
    ) t;
    
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
            'engagement_stats', COALESCE(v_engagement_stats, 'null'::jsonb),
            'failure_stats_by_channel', COALESCE(v_failure_reasons, 'null'::jsonb),
            'cost_per_lead', v_cost_per_lead,
            'intent_distribution_by_channel',COALESCE(v_intent_distribution, 'null'::jsonb),
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

    -- IF p_campaign_type = 'pre-sales' THEN
    --     UPDATE pre_sales_campaign
    --     SET last_stats_calculated_at = NOW()
    --     WHERE dict->>'campaign_id' = p_campaign_id;
    -- ELSE
    --     UPDATE post_sales_campaign
    --     SET last_stats_calculated_at = NOW()
    --     WHERE dict->>'campaign_id' = p_campaign_id;
    -- END IF;

END;
$$;
