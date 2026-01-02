-- Reads template table
-- Groups them by approval_status
-- Calculates:
--     approval_status
--     total_count
-- Inserts or updates summary rows to template_summary model
-- Updates only if data changed

-- Ex- 
    -- {
    --         "created": 1766993143905,
    --         "updated": 1766993143905,
    --         "total_count": 49,
    --         "approval_status": [
    --             {
    --                 "count": 44,
    --                 "status": "approved"
    --             },
    --             {
    --                 "count": 3,
    --                 "status": "pending"
    --             },
    --             {
    --                 "count": 2,
    --                 "status": "rejected"
    --             }
    --         ],
    --         "template_summary_id": "template_summary"
    --     }
    
CREATE OR REPLACE PROCEDURE update_template_summary()
LANGUAGE plpgsql
AS $$
DECLARE
    v_approval_status JSONB;
    v_total_count BIGINT;
BEGIN

    -- get count and status from template
    SELECT jsonb_agg(
        jsonb_build_object(
            'status', status,
            'count', cnt
        )
        ORDER BY status
    )
    INTO v_approval_status
    FROM (
        SELECT
            LOWER(dict->>'status') AS status,
            COUNT(*) AS cnt
        FROM template
        GROUP BY LOWER(dict->>'status')
    ) t;

    -- TOTAL COUNT
    SELECT COUNT(*)
    INTO v_total_count
    FROM template;

    INSERT INTO template_summary (
        template_summary_id,
        dict,
        created,
        updated
    )
    VALUES (
        'template_summary',
        jsonb_build_object(
            'approval_status', COALESCE(v_approval_status, '[]'::jsonb),
            'total_count', v_total_count,
            'created', (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT,
            'updated', (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT
        ),
        NOW(),
        NOW()
    )
    ON CONFLICT (template_summary_id)
    DO UPDATE SET
        dict = EXCLUDED.dict,
        updated = EXCLUDED.updated
    WHERE template_summary.dict IS DISTINCT FROM EXCLUDED.dict;

END;
$$;
