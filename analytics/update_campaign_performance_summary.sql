CREATE OR REPLACE PROCEDURE update_campaign_performance_summary(
    p_campaign_id TEXT,
    p_campaign_type TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE --define variables
    v_campaign_name TEXT;
    v_engagement_stats JSONB;
    v_failure_reasons JSONB;
BEGIN

    IF p_campaign_type = 'pre-sales' THEN
        SELECT dict->>'campaign_name', dict->>'campaign_objective_id'
        INTO v_campaign_name
        FROM pre_sales_campaign
        WHERE dict->>'campaign_id' = p_campaign_id;

    ELSIF p_campaign_type = 'post-sales' THEN
        SELECT dict->>'campaign_name', dict->>'campaign_objective_id'
        INTO v_campaign_name
        FROM post_sales_campaign
        WHERE dict->>'campaign_id' = p_campaign_id;

    ELSE
        RAISE EXCEPTION 'Invalid campaign_type: %', p_campaign_type;
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
                WHEN 'contacted'   THEN 'read'
                WHEN 'attempted'  THEN 'sent'
                WHEN 'queued'   THEN 'initiated'
                WHEN 'reached'   THEN 'delivered'
                WHEN 'failed'      THEN 'failed'
                WHEN 'engaged'  THEN 'interacted'
                WHEN 'read'        THEN 'read'
                WHEN 'sent'        THEN 'sent'
                WHEN 'initiated'   THEN 'initiated'
                WHEN 'delivered'   THEN 'delivered'
                ELSE 'unknown'
            END AS status,

            COUNT(*) AS cnt
        FROM contact_status
        WHERE dict->>'campaign_id' = p_campaign_id
        AND dict->>'campaign_type' = p_campaign_type
        GROUP BY
            LOWER(dict->>'channel'),
            CASE LOWER(dict->>'provider_status')
                WHEN 'contacted'   THEN 'read'
                WHEN 'attempted'  THEN 'sent'
                WHEN 'queued'   THEN 'initiated'
                WHEN 'reached'   THEN 'delivered'
                WHEN 'failed'      THEN 'failed'
                WHEN 'engaged'  THEN 'interacted'
                WHEN 'read'        THEN 'read'
                WHEN 'sent'        THEN 'sent'
                WHEN 'initiated'   THEN 'initiated'
                WHEN 'delivered'   THEN 'delivered'
                ELSE 'unknown'
            END
    ) t;

    -- failure stats
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

            CASE
                WHEN LOWER(dict->>'channel') = 'whatsapp_chat'
                    THEN 'Message not delivered'
                ELSE COALESCE(
                    NULLIF(dict->>'failure_reason', ''),
                    NULLIF(dict->>'error_message', ''),
                    'failed'
                )
            END AS message,

            COUNT(*) AS cnt
        FROM contact_status
        WHERE dict->>'campaign_id' = p_campaign_id
        AND dict->>'campaign_type' = p_campaign_type
        AND LOWER(dict->>'provider_status') = 'failed'
        GROUP BY
            LOWER(dict->>'channel'),
            CASE
                WHEN LOWER(dict->>'channel') = 'whatsapp_chat'
                    THEN 'Message not delivered'
                ELSE COALESCE(
                    NULLIF(dict->>'failure_reason', ''),
                    NULLIF(dict->>'error_message', ''),
                    'failed'
                )
            END
    ) t;

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
            'engagement_stats', COALESCE(v_engagement_stats, '[]'::jsonb),
            'failure_stats_by_channel', COALESCE(v_failure_reasons, '[]'::jsonb)
        ),
        NOW(),
        NOW()
    )
    ON CONFLICT (campaign_performance_summary_id)
    DO UPDATE SET
        dict = EXCLUDED.dict,
        updated = EXCLUDED.updated;

   
    -- -- updating last_stats_calculated_at
    -- IF p_campaign_type = 'pre-sales' THEN
    --     UPDATE pre_sales_campaign
    --     SET last_stats_calculated_at = v_now
    --     WHERE campaign_id = p_campaign_id;

    -- ELSE
    --     UPDATE post_sales_campaign
    --     SET last_stats_calculated_at = v_now
    --     WHERE campaign_id = p_campaign_id;
    -- END IF;

END;
$$;
