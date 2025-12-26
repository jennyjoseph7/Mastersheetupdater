CREATE OR REPLACE PROCEDURE update_overall_campaign_summary()
LANGUAGE plpgsql
AS $$
BEGIN
    -- pre-sales campaign summary
    INSERT INTO overall_campaign_summary (
        campaign_summary_id,
        dict,
        created,
        updated
    )
    VALUES (
        'pre-sales',
        jsonb_build_object(
            'campaign_type','pre-sales',
            'active_count',(SELECT COUNT(*) FROM pre_sales_campaign WHERE dict->>'campaign_status' = 'Active'),
            'total_count',(SELECT COUNT(*) FROM pre_sales_campaign),
            'total_reach',(SELECT COUNT(*) FROM contact_status WHERE LOWER(dict->>'provider_status') IN ('reached', 'delivered')  AND dict->>'campaign_type' = 'pre-sales'),
            'conversation_rate',
            COALESCE(
                (
                    SELECT COUNT(*)::NUMERIC
                    FROM session s
                    WHERE LOWER(s.dict->>'disposition') = 'converted'
                    AND s.dict->>'campaign_type' = 'pre-sales'
                )
                /
                NULLIF(
                    (
                        SELECT COUNT(*)::NUMERIC
                        FROM contact_status cs
                        WHERE LOWER(cs.dict->>'provider_status') in ('reached' , 'delivered')
                        AND cs.dict->>'campaign_type' = 'pre-sales'
                    ),
                    0
                ),
                0
            ) * 100
        ),
        NOW(),
        NOW()
    )
    ON CONFLICT (campaign_summary_id)
    DO UPDATE SET
        dict = EXCLUDED.dict,
        updated = EXCLUDED.updated;

    -- post-sales campaign summary
    INSERT INTO overall_campaign_summary (
        campaign_summary_id,
        dict,
        created,
        updated
    )
    VALUES (
        'post-sales',
        jsonb_build_object(
            'campaign_type','post-sales',
            'active_count',(SELECT COUNT(*) FROM post_sales_campaign WHERE dict->>'campaign_status' = 'Active'),
            'total_count',(SELECT COUNT(*) FROM post_sales_campaign),
            'total_reach',(SELECT COUNT(*) FROM contact_status WHERE LOWER(dict->>'provider_status') IN ('reached', 'delivered')  AND dict->>'campaign_type' = 'post-sales'),
            'conversation_rate',
            COALESCE(
                (
                    SELECT COUNT(*)::NUMERIC
                    FROM session s
                    WHERE LOWER(s.dict->>'disposition') = 'converted'
                    AND s.dict->>'campaign_type' = 'post-sales'
                )
                /
                NULLIF(
                    (
                        SELECT COUNT(*)::NUMERIC
                        FROM contact_status cs
                        WHERE LOWER(cs.dict->>'provider_status') in ('reached' , 'delivered')
                        AND cs.dict->>'campaign_type' = 'post-sales'
                    ),
                    0
                ),
                0
            ) * 100
        ),
        NOW(),
        NOW()
    )
    ON CONFLICT (campaign_summary_id)
    DO UPDATE SET
        dict    = EXCLUDED.dict,
        updated = EXCLUDED.updated;

END;
$$;
