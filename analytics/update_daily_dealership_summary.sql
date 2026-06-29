-- Procedure to update daily dealership summary analytics
-- Calculates:
--     total_campaign_triggered
--     total_leads_triggered
--     total_pending (disposition in ('queued', 'attempted') in leads)
--     total_converted (disposition='converted' in leads)
--     total_connected (disposition in ('reached', 'contacted', 'engaged') in leads)
--     total_failed (disposition in ('failed', 'busy', 'error') in leads)
--     total_sessions
--     retrigger_count (total_sessions - total_leads_triggered)
-- Grouped by dealership, date (epoch), and channel

CREATE TABLE IF NOT EXISTS daily_dealership_summary (
    daily_dealership_summary_id TEXT PRIMARY KEY,
    dict JSONB,
    created TIMESTAMPTZ DEFAULT NOW(),
    updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE PROCEDURE update_daily_dealership_summary()
LANGUAGE plpgsql
AS $$
DECLARE
    cutoff_epoch_sec BIGINT;
BEGIN
    cutoff_epoch_sec := (EXTRACT(EPOCH FROM (NOW() - INTERVAL '3 days')))::BIGINT;
    INSERT INTO daily_dealership_summary (
        daily_dealership_summary_id,
        dict,
        created,
        updated
    )
    WITH    campaign_raw AS (
        SELECT 
            dict->>'dealership_id' as dealership_id,
            (EXTRACT(EPOCH FROM (TO_TIMESTAMP((dict->>'created')::NUMERIC)::DATE)) * 1000)::BIGINT as activity_date,
            dict->'channels' as channels_json
        FROM (
            SELECT dict FROM pre_sales_campaign
            UNION ALL
            SELECT dict FROM post_sales_campaign
        ) c
        WHERE dict->>'dealership_id' IS NOT NULL 
          AND dict->>'dealership_id' <> ''
          AND (dict->>'created')::NUMERIC::BIGINT IS NOT NULL
          AND (dict->>'created')::NUMERIC::BIGINT <> 0
          AND (dict->>'created')::NUMERIC >= cutoff_epoch_sec
          AND LOWER(dict->>'campaign_status') IN ('active', 'continuous')
    ),
    campaign_data AS (
        SELECT 
            r.dealership_id,
            r.activity_date,
            COALESCE(LOWER(ch.val), 'unknown') as channel
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
        SELECT dealership_id, activity_date, channel, COUNT(*) as total_campaign_triggered
        FROM campaign_data
        GROUP BY 1, 2, 3
    ),
    lead_raw_triggered AS (
        SELECT 
            l.dict->>'dealership_id' as dealership_id,
            (EXTRACT(EPOCH FROM (TO_TIMESTAMP((l.dict->>'created')::NUMERIC)::DATE)) * 1000)::BIGINT as activity_date,
            c.dict->'channels' as channels_json,
            l.dict->>'last_session_channel' as last_session_channel,
            l.dict->>'next_channel' as next_channel,
            l.dict->>'previous_contact_channel' as previous_contact_channel
        FROM (
            SELECT dict FROM pre_sales_lead
            UNION ALL
            SELECT dict FROM post_sales_lead
        ) l
        LEFT JOIN (
            SELECT dict->>'campaign_id' as cid, dict FROM pre_sales_campaign
            WHERE LOWER(dict->>'campaign_status') IN ('active', 'continuous')
            UNION ALL
            SELECT dict->>'campaign_id' as cid, dict FROM post_sales_campaign
            WHERE LOWER(dict->>'campaign_status') IN ('active', 'continuous')
        ) c ON (l.dict->>'campaign_id') = c.cid
        WHERE l.dict->>'dealership_id' IS NOT NULL 
          AND l.dict->>'dealership_id' <> ''
          AND (l.dict->>'created')::NUMERIC::BIGINT IS NOT NULL
          AND (l.dict->>'created')::NUMERIC >= cutoff_epoch_sec
    ),
    lead_data_triggered AS (
        SELECT 
            r.dealership_id,
            r.activity_date,
            COALESCE(LOWER(ch.val), 'unknown') as channel
        FROM lead_raw_triggered r
        LEFT JOIN LATERAL (
            SELECT val FROM jsonb_array_elements_text(
                CASE 
                    WHEN jsonb_typeof(r.channels_json) = 'array' AND jsonb_array_length(r.channels_json) > 0 
                    THEN r.channels_json 
                    ELSE jsonb_build_array(COALESCE(r.last_session_channel, r.next_channel, r.previous_contact_channel, 'unknown'))
                END
            ) AS val
        ) ch ON TRUE
    ),
    lead_counts_triggered AS (
        SELECT 
            dealership_id, 
            activity_date, 
            channel,
            COUNT(*) as total_leads_triggered
        FROM lead_data_triggered
        GROUP BY 1, 2, 3
    ),
    lead_raw_dispositions AS (
        SELECT 
            l.dict->>'dealership_id' as dealership_id,
            (EXTRACT(EPOCH FROM (TO_TIMESTAMP((COALESCE(l.dict->>'updated', l.dict->>'created'))::NUMERIC)::DATE)) * 1000)::BIGINT as activity_date,
            l.dict->>'disposition' as disposition,
            c.dict->'channels' as channels_json,
            l.dict->>'last_session_channel' as last_session_channel,
            l.dict->>'next_channel' as next_channel,
            l.dict->>'previous_contact_channel' as previous_contact_channel
        FROM (
            SELECT dict FROM pre_sales_lead
            UNION ALL
            SELECT dict FROM post_sales_lead
        ) l
        LEFT JOIN (
            SELECT dict->>'campaign_id' as cid, dict FROM pre_sales_campaign
            WHERE LOWER(dict->>'campaign_status') IN ('active', 'continuous')
            UNION ALL
            SELECT dict->>'campaign_id' as cid, dict FROM post_sales_campaign
            WHERE LOWER(dict->>'campaign_status') IN ('active', 'continuous')
        ) c ON (l.dict->>'campaign_id') = c.cid
        WHERE l.dict->>'dealership_id' IS NOT NULL 
          AND l.dict->>'dealership_id' <> ''
          AND (l.dict->>'created')::NUMERIC::BIGINT IS NOT NULL
          AND COALESCE((l.dict->>'updated')::NUMERIC, (l.dict->>'created')::NUMERIC) >= cutoff_epoch_sec
    ),
    lead_data_dispositions AS (
        SELECT 
            r.dealership_id,
            r.activity_date,
            r.disposition,
            COALESCE(LOWER(ch.val), 'unknown') as channel
        FROM lead_raw_dispositions r
        LEFT JOIN LATERAL (
            SELECT val FROM jsonb_array_elements_text(
                CASE 
                    WHEN jsonb_typeof(r.channels_json) = 'array' AND jsonb_array_length(r.channels_json) > 0 
                    THEN r.channels_json 
                    ELSE jsonb_build_array(COALESCE(r.last_session_channel, r.next_channel, r.previous_contact_channel, 'unknown'))
                END
            ) AS val
        ) ch ON TRUE
    ),
    lead_counts_dispositions AS (
        SELECT 
            dealership_id, 
            activity_date, 
            channel,
            COUNT(*) FILTER (WHERE disposition IN ('queued', 'attempted')) as total_pending,
            COUNT(*) FILTER (WHERE disposition = 'converted') as total_converted,
            COUNT(*) FILTER (WHERE disposition IN ('reached', 'contacted', 'engaged')) as total_connected,
            COUNT(*) FILTER (WHERE disposition IN ('failed', 'busy', 'error')) as total_failed
        FROM lead_data_dispositions
        GROUP BY 1, 2, 3
    ),
    session_raw AS (
        SELECT 
            s.dict->>'dealership_id' as dealership_id,
            (EXTRACT(EPOCH FROM (TO_TIMESTAMP((s.dict->>'created')::NUMERIC)::DATE)) * 1000)::BIGINT as activity_date,
            c.dict->'channels' as channels_json,
            s.dict->>'channel' as session_channel
        FROM session s
        LEFT JOIN (
            SELECT dict->>'campaign_id' as cid, dict FROM pre_sales_campaign
            WHERE LOWER(dict->>'campaign_status') IN ('active', 'continuous')
            UNION ALL
            SELECT dict->>'campaign_id' as cid, dict FROM post_sales_campaign
            WHERE LOWER(dict->>'campaign_status') IN ('active', 'continuous')
        ) c ON (s.dict->>'campaign_id') = c.cid
        WHERE s.dict->>'dealership_id' IS NOT NULL 
          AND s.dict->>'dealership_id' <> ''
          AND (s.dict->>'created')::NUMERIC::BIGINT IS NOT NULL
          AND (s.dict->>'created')::NUMERIC >= cutoff_epoch_sec
    ),
    session_data AS (
        SELECT 
            r.dealership_id,
            r.activity_date,
            COALESCE(LOWER(ch.val), 'unknown') as channel
        FROM session_raw r
        LEFT JOIN LATERAL (
            SELECT val FROM jsonb_array_elements_text(
                CASE 
                    WHEN jsonb_typeof(r.channels_json) = 'array' AND jsonb_array_length(r.channels_json) > 0 
                    THEN r.channels_json 
                    ELSE jsonb_build_array(COALESCE(r.session_channel, 'unknown'))
                END
            ) AS val
        ) ch ON TRUE
    ),
    session_counts AS (
        SELECT dealership_id, activity_date, channel, COUNT(*) as total_sessions
        FROM session_data
        GROUP BY 1, 2, 3
    ),
    all_keys AS (
        SELECT dealership_id, activity_date, channel FROM campaign_counts
        UNION
        SELECT dealership_id, activity_date, channel FROM lead_counts_triggered
        UNION
        SELECT dealership_id, activity_date, channel FROM lead_counts_dispositions
        UNION
        SELECT dealership_id, activity_date, channel FROM session_counts
    )
    SELECT
        k.dealership_id || '_' || k.activity_date::TEXT || '_' || k.channel,
        jsonb_build_object(
            'dealership_id', k.dealership_id,
            'activity_date', k.activity_date,
            'channel', k.channel,
            'total_campaign_triggered', COALESCE(cc.total_campaign_triggered, 0),
            'total_leads_triggered', COALESCE(lct.total_leads_triggered, 0),
            'total_pending', COALESCE(lcd.total_pending, 0),
            'total_converted', COALESCE(lcd.total_converted, 0),
            'total_connected', COALESCE(lcd.total_connected, 0),
            'total_failed', COALESCE(lcd.total_failed, 0),
            'total_sessions', COALESCE(sc.total_sessions, 0),
            'retrigger_count', GREATEST(0, COALESCE(sc.total_sessions, 0) - COALESCE(lct.total_leads_triggered, 0)),
            'created', (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT,
            'updated', (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT
        ),
        NOW(),
        NOW()
    FROM all_keys k
    LEFT JOIN campaign_counts cc ON k.dealership_id = cc.dealership_id AND k.activity_date = cc.activity_date AND k.channel = cc.channel
    LEFT JOIN lead_counts_triggered lct ON k.dealership_id = lct.dealership_id AND k.activity_date = lct.activity_date AND k.channel = lct.channel
    LEFT JOIN lead_counts_dispositions lcd ON k.dealership_id = lcd.dealership_id AND k.activity_date = lcd.activity_date AND k.channel = lcd.channel
    LEFT JOIN session_counts sc ON k.dealership_id = sc.dealership_id AND k.activity_date = sc.activity_date AND k.channel = sc.channel
    ON CONFLICT (daily_dealership_summary_id)
    DO UPDATE SET
        dict = EXCLUDED.dict,
        updated = EXCLUDED.updated
    WHERE daily_dealership_summary.dict IS DISTINCT FROM EXCLUDED.dict;

END;
$$;
