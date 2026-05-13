-- Procedure to update daily dealership summary analytics
-- Calculates:
--     total_campaign_triggered
--     total_leads_triggered
--     total_pending
--     total_converted
--     total_connected
-- Grouped by dealership, date, and channel (as per updated model)

CREATE TABLE IF NOT EXISTS daily_dealership_summary (
    daily_dealership_summary_id TEXT PRIMARY KEY,
    dict JSONB,
    created TIMESTAMPTZ DEFAULT NOW(),
    updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE PROCEDURE update_daily_dealership_summary()
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO daily_dealership_summary (
        daily_dealership_summary_id,
        dict,
        created,
        updated
    )
    WITH campaign_raw AS (
        SELECT 
            dict->>'dealership_id' as dealership_id,
            TO_CHAR(TO_TIMESTAMP((dict->>'created')::BIGINT / 1000), 'YYYY-MM-DD') as activity_date,
            dict->'channels' as channels_json
        FROM (
            SELECT dict FROM pre_sales_campaign
            UNION ALL
            SELECT dict FROM post_sales_campaign
        ) c
        WHERE dict->>'dealership_id' IS NOT NULL 
          AND dict->>'dealership_id' <> ''
          AND (dict->>'created') IS NOT NULL
          AND (dict->>'created') <> ''
    ),
    campaign_data AS (
        -- Explode channels array to get per-channel campaign counts
        SELECT 
            r.dealership_id,
            r.activity_date,
            COALESCE(LOWER(ch.val), 'unknown') as lead_channel
        FROM campaign_raw r
        LEFT JOIN LATERAL (
            SELECT val FROM jsonb_array_elements_text(
                CASE 
                    WHEN jsonb_typeof(r.channels_json) = 'array' AND jsonb_array_length(r.channels_json) > 0 
                    THEN r.channels_json 
                    ELSE '["unknown"]'::jsonb 
                END
            ) AS val
        ) ch ON TRUE
    ),
    campaign_counts AS (
        SELECT dealership_id, activity_date, lead_channel as channel, COUNT(*) as total_campaign_triggered
        FROM campaign_data
        GROUP BY 1, 2, 3
    ),
    lead_data AS (
        SELECT 
            dict->>'dealership_id' as dealership_id,
            TO_CHAR(TO_TIMESTAMP((dict->>'created')::BIGINT / 1000), 'YYYY-MM-DD') as activity_date,
            COALESCE(LOWER(dict->>'channel'), 'unknown') as lead_channel,
            LOWER(dict->>'provider_status') as provider_status
        FROM contact_status
        WHERE dict->>'dealership_id' IS NOT NULL 
          AND dict->>'dealership_id' <> ''
          AND (dict->>'created') IS NOT NULL
          AND (dict->>'created') <> ''
    ),
    lead_counts AS (
        SELECT 
            dealership_id, 
            activity_date, 
            lead_channel as channel,
            COUNT(*) as total_leads_triggered,
            COUNT(*) FILTER (WHERE provider_status IN ('initiated', 'queued', 'pending')) as total_pending
        FROM lead_data
        GROUP BY 1, 2, 3
    ),
    session_data AS (
        SELECT 
            dict->>'dealership_id' as dealership_id,
            TO_CHAR(TO_TIMESTAMP((dict->>'created')::BIGINT / 1000), 'YYYY-MM-DD') as activity_date,
            COALESCE(LOWER(dict->>'channel'), 'unknown') as lead_channel,
            LOWER(dict->>'disposition') as disposition
        FROM session
        WHERE dict->>'dealership_id' IS NOT NULL 
          AND dict->>'dealership_id' <> ''
          AND (dict->>'created') IS NOT NULL
          AND (dict->>'created') <> ''
    ),
    session_counts AS (
        SELECT 
            dealership_id, 
            activity_date, 
            lead_channel as channel,
            COUNT(*) FILTER (WHERE disposition = 'converted') as total_converted,
            COUNT(*) FILTER (WHERE disposition IN ('reached', 'contacted', 'engaged')) as total_connected
        FROM session_data
        GROUP BY 1, 2, 3
    ),
    all_keys AS (
        SELECT dealership_id, activity_date, channel FROM campaign_counts
        UNION
        SELECT dealership_id, activity_date, channel FROM lead_counts
        UNION
        SELECT dealership_id, activity_date, channel FROM session_counts
    )
    SELECT
        k.dealership_id || '_' || k.activity_date || '_' || k.channel,
        jsonb_build_object(
            'dealership_id', k.dealership_id,
            'activity_date', k.activity_date,
            'channel', k.channel,
            'total_campaign_triggered', COALESCE(cc.total_campaign_triggered, 0),
            'total_leads_triggered', COALESCE(lc.total_leads_triggered, 0),
            'total_pending', COALESCE(lc.total_pending, 0),
            'total_converted', COALESCE(sc.total_converted, 0),
            'total_connected', COALESCE(sc.total_connected, 0),
            'created', (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT,
            'updated', (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT
        ),
        NOW(),
        NOW()
    FROM all_keys k
    LEFT JOIN campaign_counts cc ON k.dealership_id = cc.dealership_id AND k.activity_date = cc.activity_date AND k.channel = cc.channel
    LEFT JOIN lead_counts lc ON k.dealership_id = lc.dealership_id AND k.activity_date = lc.activity_date AND k.channel = lc.channel
    LEFT JOIN session_counts sc ON k.dealership_id = sc.dealership_id AND k.activity_date = sc.activity_date AND k.channel = sc.channel
    ON CONFLICT (daily_dealership_summary_id)
    DO UPDATE SET
        dict = EXCLUDED.dict,
        updated = EXCLUDED.updated
    WHERE daily_dealership_summary.dict IS DISTINCT FROM EXCLUDED.dict;

END;
$$;
