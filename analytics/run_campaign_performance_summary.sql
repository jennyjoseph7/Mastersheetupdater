-- run_campaign_performance_summary

-- Finds only campaigns that need updating based on updated timestamp
-- Calls the update_campaign_performance_summary procedure
-- Avoids reprocessing unchanged campaigns
-- Works for both pre-sales and post-sales

CREATE OR REPLACE PROCEDURE run_campaign_performance_summary()
LANGUAGE plpgsql
AS $$
DECLARE
    r RECORD;
BEGIN
    -- running a loop and checking whether the campaign needs to be updated based on the last updated time is higher than the last updated time in the campaign_performance_summary table

    -- for pre-sales campaigns
    FOR r IN
        SELECT 
            c.dict->>'campaign_id' AS campaign_id
        FROM pre_sales_campaign c
        LEFT JOIN campaign_performance_summary s
            ON s.campaign_performance_summary_id =
               c.dict->>'campaign_id' || '-pre-sales'
        WHERE
            s.campaign_performance_summary_id IS NULL
            OR c.updated > TO_TIMESTAMP(
                (s.dict->>'updated')::BIGINT / 1000
            )
    LOOP
        RAISE NOTICE '[CRON] Updating PRE-SALES campaign: %', r.campaign_id;
        CALL update_campaign_performance_summary(r.campaign_id, 'pre-sales');
    END LOOP;


    -- for post-sales campaigns
    FOR r IN
        SELECT 
            c.dict->>'campaign_id' AS campaign_id
        FROM post_sales_campaign c
        LEFT JOIN campaign_performance_summary s
            ON s.campaign_performance_summary_id =
               c.dict->>'campaign_id' || '-post-sales'
        WHERE
            s.campaign_performance_summary_id IS NULL
            OR c.updated > TO_TIMESTAMP(
                (s.dict->>'updated')::BIGINT / 1000
            )
    LOOP
        RAISE NOTICE '[CRON] Updating POST-SALES campaign: %', r.campaign_id;
        CALL update_campaign_performance_summary(r.campaign_id, 'post-sales');
    END LOOP;

END;
$$;
