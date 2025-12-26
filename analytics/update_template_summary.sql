CREATE OR REPLACE PROCEDURE update_template_summary()
LANGUAGE plpgsql
AS $$
DECLARE
    v_approval_status JSONB;
    v_total_count BIGINT;
BEGIN

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
            'total_count', v_total_count
        ),
        NOW(),
        NOW()
    )
    ON CONFLICT (template_summary_id)
    DO UPDATE SET
        dict = EXCLUDED.dict,
        updated = EXCLUDED.updated;

END;
$$;
