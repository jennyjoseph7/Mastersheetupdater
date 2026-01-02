-- Reads pre-sales and post-sales campaigns
-- Groups them by dealership_id
-- Calculates:
--     active_count
--     total_count
--     total_reach
--     conversation_rate
-- Inserts or updates summary rows
-- Updates only if data changed
-- Skips completed / cancelled campaigns

-- Ex- 

    --  {
    --         "created": 1766995992401,
    --         "updated": 1766995992401,
    --         "total_count": 48,
    --         "total_reach": 0,
    --         "active_count": 25,
    --         "campaign_type": "post-sales",
    --         "dealership_id": "nexa-delhi-south-nexa-dealer-group-north-india",
    --         "conversation_rate": 0,
    --         "campaign_summary_id": "nexa-delhi-south-nexa-dealer-group-north-india-post-sales"
    --     }
    
CREATE OR REPLACE PROCEDURE update_overall_campaign_summary()
LANGUAGE plpgsql
AS $$
BEGIN

    WITH pre_sales_campaign_model AS (
        SELECT
            dict->>'dealership_id' AS dealership_id,
            dict
        FROM pre_sales_campaign
        WHERE dict->>'dealership_id' IS NOT NULL
        AND dict->>'dealership_id' <> ''
    )
    -- PRE-SALES
    INSERT INTO campaign_summary (
        campaign_summary_id,
        dict,
        created,
        updated
    )
    SELECT
        pre.dealership_id || '_' || 'pre-sales' AS campaign_summary_id,
        jsonb_build_object(
            'campaign_type', 'pre-sales',
            'dealership_id', pre.dealership_id,
            'active_count', COUNT(*) FILTER (WHERE pre.dict->>'campaign_status' = 'Active'),
            'total_count', COUNT(*),
            'total_reach',
                (
                    SELECT COUNT(*)
                    FROM contact_status cs
                    WHERE LOWER(cs.dict->>'provider_status') IN ('reached','delivered')
                      AND cs.dict->>'campaign_type' = 'pre-sales'
                      AND cs.dict->>'dealership_id' = pre.dealership_id
                ),
            'conversation_rate',
                COALESCE(
                    (
                        SELECT COUNT(*)::NUMERIC
                        FROM session s
                        WHERE LOWER(s.dict->>'disposition') = 'converted'
                          AND s.dict->>'campaign_type' = 'pre-sales'
                          AND s.dict->>'dealership_id' = pre.dealership_id
                    )
                    /
                    NULLIF(
                        (
                            SELECT COUNT(*)::NUMERIC
                            FROM contact_status cs
                            WHERE LOWER(cs.dict->>'provider_status') IN ('reached','delivered')
                              AND cs.dict->>'campaign_type' = 'pre-sales'
                              AND cs.dict->>'dealership_id' = pre.dealership_id
                        ),
                        0
                    ),
                    0
                ) * 100,
            'created', (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT,
            'updated', (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT
        ),
        NOW(),
        NOW()
    FROM pre_sales_campaign_model pre
    GROUP BY pre.dealership_id
    ON CONFLICT (campaign_summary_id)
    DO UPDATE SET
        dict = EXCLUDED.dict,
        updated = EXCLUDED.updated
    WHERE campaign_summary.dict IS DISTINCT FROM EXCLUDED.dict;

    -- POST-SALES
    WITH post_sales_campaign_model AS (
        SELECT
            dict->>'dealership_id' AS dealership_id,
            dict
        FROM post_sales_campaign
        WHERE dict->>'dealership_id' IS NOT NULL
        AND dict->>'dealership_id' <> ''
    )

    INSERT INTO campaign_summary (
        campaign_summary_id,
        dict,
        created,
        updated
    )
    SELECT
        post.dealership_id || '_' || 'post-sales' AS campaign_summary_id,
        jsonb_build_object(
            'campaign_type', 'post-sales',
            'dealership_id', post.dealership_id,
            'active_count', COUNT(*) FILTER (WHERE post.dict->>'campaign_status' = 'Active'),
            'total_count', COUNT(*),
            'total_reach',
                (
                    SELECT COUNT(*)
                    FROM contact_status cs
                    WHERE LOWER(cs.dict->>'provider_status') IN ('reached','delivered')
                      AND cs.dict->>'campaign_type' = 'post-sales'
                      AND cs.dict->>'dealership_id' = post.dealership_id
                ),
            'conversation_rate',
                COALESCE(
                    (
                        SELECT COUNT(*)::NUMERIC
                        FROM session s
                        WHERE LOWER(s.dict->>'disposition') = 'converted'
                          AND s.dict->>'campaign_type' = 'post-sales'
                          AND s.dict->>'dealership_id' = post.dealership_id
                    )
                    /
                    NULLIF(
                        (
                            SELECT COUNT(*)::NUMERIC
                            FROM contact_status cs
                            WHERE LOWER(cs.dict->>'provider_status') IN ('reached','delivered')
                              AND cs.dict->>'campaign_type' = 'post-sales'
                              AND cs.dict->>'dealership_id' = post.dealership_id
                        ),
                        0
                    ),
                    0
                ) * 100,
            'created', (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT,
            'updated', (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT
        ),
        NOW(),
        NOW()
    FROM post_sales_campaign_model post
    WHERE post.dealership_id IS NOT NULL
    AND post.dealership_id <> ''
    GROUP BY post.dealership_id
    ON CONFLICT (campaign_summary_id)
    DO UPDATE SET
        dict = EXCLUDED.dict,
        updated = EXCLUDED.updated
    WHERE campaign_summary.dict IS DISTINCT FROM EXCLUDED.dict;
    
END;
$$;
