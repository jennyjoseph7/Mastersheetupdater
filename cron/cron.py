
# from elevenlabs.conversational_ai.mcp_servers.tool_configs.types import mcp_tool_config_override_create_request_model_input_overrides_value
import sys, os
import requests
import json
import re
from datetime import datetime
import time                 
from os.path import dirname, abspath, join as joinpath



BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from conversation.lead_post_processing import post_session_process
from config import AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_VOICE_SERVICE_NAME, AUTOCRM_CRON_SERVICE_NAME, AUTOCRM_AGENT_SERVICE_NAME,AUTOCRM_CAMPAIGN_SERVICE_NAME,DEFAULT_CHANNELS, AUTOCRM_COMMUNICATION_SERVICE_NAME,VOICE_BATCH_SIZE,NON_VOICE_BATCH_SIZE,VOICE_CHANNELS,NON_VOICE_CHANNELS,VOICE_START_TIME,VOICE_END_TIME,NON_VOICE_START_TIME,NON_VOICE_END_TIME,VOICE_MAX_QUEUE_LENGTH,NON_VOICE_MAX_QUEUE_LENGTH,gryd, hp,AutocrmModel, OUTBOUND_VOICE_SERVICES, INBOUND_VOICE_SERVICES
from crm_integration.crm_integration import load_crm
from crm_integration.crm_integration.load_crm import load_crm
from conversation.lead_post_processing import post_session_process
# from crm_integration.crm_integration.cron import _trigger_audience_task
from autocrm_db_helper import get_pg_connector
from typing import List, Union, Dict, Any
from autocrm_db_helper.PGConnector import AutoCRMPGConnector
from campaign.campaign_workflow import CHANNEL_IDENTIFIER_MAP
from communication.connectors.whatsapp_connectors.source_connectors import BaseWebhookConverter
from gryd_worker import gryd,gryd_db_helper as db, beats as cron_worker,gryd_audit_helper
from communication.connectors.communication_helpers import handle_session_post_process_or_end
from campaign.campaign_manager import manual_register_and_trigger_lead
pg = AutoCRMPGConnector(enterprise_id="autocrm")
AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")

gryd.SERVICE = AUTOCRM_CRON_SERVICE_NAME
gryd.set_queue_manager()
__version__ = "0.0.1"
mlogger = gryd.hp.get_logger(gryd.SERVICE)

mlogger.info(f"SERVICE --{gryd.SERVICE}")

def SETUP():
    """When we are running this worker for the first time in an environment
    """
    pass

def clear_otp_cache(logger=None, job=None):
    logger = logger or mlogger
    otp_cache_model = gryd.base_model.Model('otp_cache', AUTOCRM_APP_ENTERPRISE_ID)
    otp_cache_model.delete_many({"expiry": f",{hp.epoch() - 3600}"})

@gryd.is_a_task(function_name="overall_campaign_summary")
def overall_campaign_summary():
    mlogger.info("Running overall campaign summary...")
    with get_pg_connector() as pg:

        # Time before execution (force BIGINT -> Python int)
        before = int(list(
            pg.yield_results(
                "SELECT (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT"
            )
        )[0][0])
        mlogger.info(f"Before: {before}")
        pg.execute_write(
            "CALL update_overall_campaign_summary();",
            _fetch=False
        )

        # Count updated rows
        row = next(
            pg.yield_results(
                """
                SELECT COUNT(*)::BIGINT
                FROM campaign_summary
                WHERE updated >= to_timestamp(%s / 1000.0)
                """,
                (before,)
            ),
            None
        )

        updated_rows = int(row[0]) if row else 0
        mlogger.info(f"Updated Rows: {updated_rows}")
        # Count total rows (force BIGINT)
        row = next(
            pg.yield_results(
                "SELECT COUNT(*)::BIGINT FROM campaign_summary"
            ),
            None
        )

        total_rows = int(row[0]) if row else 0

        if updated_rows > 0:
            mlogger.info(
                f"[CRON] Campaign Summary Updated | "
                f"Rows Updated: {updated_rows} | Total Rows: {total_rows}"
            )
        else:
            mlogger.info(
                "[CRON] No campaign changes detected. Skipping update."
            )

        return {
            "updated_rows": updated_rows,
            "total_rows": total_rows
        }


@gryd.is_a_task(function_name="template_summary")
def template_summary():
    with get_pg_connector() as pg:
        pg.execute_write(
            "CALL update_template_summary();",
            _fetch=False
        )
        rows = list(
            pg.yield_results(
                "SELECT COUNT(*) FROM template_summary;"
            )
        )
        print(f"[CRON] update_template_summary row count = {rows}")
        return rows


@gryd.is_a_task(function_name="daily_dealership_summary")
def daily_dealership_summary():
    # from analytics.loader import load_stored_procedures
    mlogger.info("Loading stored procedures for analytics...")
    # load_stored_procedures()
    mlogger.info("Running daily dealership summary...")
    with get_pg_connector() as pg:
        pg.execute_write(
            "CALL update_daily_dealership_summary();",
            _fetch=False
        )
        rows = list(
            pg.yield_results(
                "SELECT COUNT(*) FROM daily_dealership_summary;"
            )
        )
        mlogger.info(f"[CRON] daily_dealership_summary updated. Total rows: {rows[0][0]}")
        return rows


def fetch_campaigns(pg, run_started_at_ms, batch_size=50, from_time_ms=None):
    return list(pg.yield_results("""
        WITH last_run AS (
            SELECT
                COALESCE(
                    %s::BIGINT,
                    MAX((dict->>'last_processed_at')::BIGINT),
                    0
                ) AS last_processed_at
            FROM campaign_performance_summary
        )

        SELECT DISTINCT
            cs.dict->>'campaign_id' AS campaign_id,
            cs.dict->>'campaign_type' AS campaign_type
        FROM contact_status cs, last_run lr
        WHERE
            cs.created > TO_TIMESTAMP(lr.last_processed_at / 1000)
            AND cs.created <= TO_TIMESTAMP(%s / 1000)
        LIMIT %s;
    """, (
        from_time_ms,
        run_started_at_ms,   
        batch_size
    ))) 

@gryd.is_a_task(function_name="performance_summary")
def performance_summary(from_time_ms=None):
    mlogger.info("[CRON] Starting campaign performance summary job...")

    run_started_at_ms = int(time.time() * 1000)

    mlogger.info(f"run_started_at_ms: {run_started_at_ms}")
    if from_time_ms:
        mlogger.info(f"[CRON] Override from_time_ms: {from_time_ms}")

    total_processed = 0

    with get_pg_connector() as pg:
        campaigns = fetch_campaigns(pg,run_started_at_ms,from_time_ms=from_time_ms)

        if not campaigns:
            mlogger.info("[CRON] No campaigns to process")
            return

        mlogger.info(f"[CRON] Processing batch of {len(campaigns)} campaigns")

        for campaign_id, campaign_type in campaigns:
            mlogger.info(f"campaign_id: {campaign_id}, campaign_type: {campaign_type}")
            if not campaign_id or not campaign_type:
                mlogger.error(f"[CRON] Invalid campaign data: campaign_id={campaign_id}, campaign_type={campaign_type}")
                continue
            lead_model = (
                "pre_sales_lead" if campaign_type == "pre-sales"
                else "post_sales_lead"
            )

            try:
                mlogger.info(f"Executing update_campaign_performance_summary for campaign_id: {campaign_id}")

                pg.execute_write("""
                    CALL update_campaign_performance_summary(%s, %s, %s);
                """, (campaign_id, campaign_type, lead_model), _fetch=False)

                total_processed += 1

                mlogger.info(f"[CRON] Processed {campaign_id} ({campaign_type})")

            except Exception as e:
                mlogger.error(f"[CRON] Failed {campaign_id} ({campaign_type}): {str(e)}")

    mlogger.info(f"[CRON] Completed. Total processed: {total_processed}")

    return total_processed


def set_min_worker_count(services, environment, min_worker_count, max_worker_count):
    """
    Set worker configuration for a list of services.

    :param services: List of service names
    :param environment: Environment name (e.g., 'praveen-local')
    :param min_worker_count: Minimum worker count
    :param max_worker_count: Maximum worker count
    """
    for service in services:
        try:
            cron_worker.set_worker_config(
                service,
                environment=environment,
                minimum_worker_count=min_worker_count,
                maximum_worker_count=max_worker_count
            )
            print(f"Config set for {service}")
        except Exception as e:
            print(f"Failed for {service}: {str(e)}")
            
        # TODO: use a scale_down function to scale down the environment - gryd_worker:0.5.1

@gryd.is_a_task(function_name = "test_cron_job", logger_param = 'logger', job_param = 'job')
def test_cron_job(execution_time = 110, logger = None, job = None):
    """
    This job basically executes a loop by sleeping for 1 sec until execution time expires
    """
    logger = logger or mlogger
    n = hp.now()
    st = hp.epoch()
    logger.info("Start time: %s (%s)", n, st)
    for k in range(execution_time):
        time.sleep(1) 
        logger.info("Executed test_cron_job for %s secs", k + 1)
    logger.info("Completing the test job after %s secs @ %s", hp.epoch() - st, hp.now())
    return execution_time

# @gryd.is_a_task(function_name="campaign_objective_performance_summary")
# def campaign_objective_performance_summary():
    
#     """
#     This task checks for campaigns which require an update to their performance summary.
#     It does this by checking for campaigns which have a newer updated timestamp than the
#     latest updated timestamp in the campaign_performance_summary table.

#     It then executes a stored procedure to update the campaign_performance_summary table
#     with the latest data from the campaigns.

#     :return: The number of campaigns which required an update to their performance summary.
#     :rtype: int
#     """
#     with get_pg_connector() as pg:
#         mlogger.info("[CRON] Checking campaigns needing performance update...")

#         counts = list(pg.yield_results("""
#             SELECT SUM(total) FROM (
#                 SELECT COUNT(*) AS total
#                 FROM pre_sales_campaign c
#                 LEFT JOIN campaign_performance_summary s
#                 ON s.dict->>'campaign_objective_id' =
#                      c.dict->>'campaign_objective_id'
#                 WHERE
#                     s.campaign_performance_summary_id IS NULL
#                     OR c.updated > TO_TIMESTAMP((s.dict->>'updated')::BIGINT / 1000)

#                 UNION ALL

#                 SELECT COUNT(*) AS total
#                 FROM post_sales_campaign c
#                 LEFT JOIN campaign_performance_summary s
#                 ON s.dict->>'campaign_objective_id' =
#                      c.dict->>'campaign_id'
#                 WHERE
#                     s.campaign_performance_summary_id IS NULL
#                     OR c.updated > TO_TIMESTAMP((s.dict->>'updated')::BIGINT / 1000)
#             ) t;
#         """))

#         update_count = int(counts[0][0]) if counts and counts[0][0] is not None else 0

#         if update_count == 0:
#             mlogger.info("[CRON] No campaign objective updates detected. Skipping execution.")
#             return 0

#         mlogger.info(f"[CRON] {update_count} campaigns require update. Running procedure...")

#         pg.execute_write("CALL run_campaign_objective_performance_summary();", _fetch=False)

#         mlogger.info(f"[CRON] Campaign objective performance update completed. Updated rows: {update_count}")

#         return update_count

def normalize_ts(ts):
    if not ts:
        return None
    if isinstance(ts, str):
        return int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
    if isinstance(ts, float):
        return int(ts)
    if isinstance(ts, int):
        return ts
    return None

@gryd.is_a_task(function_name="manage_active_sessions")
def manage_active_sessions(*args, **kwargs):

    """
    Checks for sessions which require an update to their history or post-process.

    This task checks for sessions which have a newer last_response_time than the last
    updated history_time. It then updates the session's history with the new data.

    After updating the history, it checks if the session can be post-processed (i.e. if there
    is new data to process or if it's been more than POST_PROCESS_INTERVAL_SECONDS seconds since
    the last post-process time). If so, it calls the handle_session_post_process_or_end function
    to either post-process the session or end it.

    :param args: Not used
    :param kwargs: Accepts the following keyword arguments:
        only_for_channels (list): A list of channels to check (default: [])
        post_process_interval_seconds (int): The interval in seconds between post-process calls (default: 10)
    :return: None
    :rtype: NoneType
    """

    kwargs_dict = dict(kwargs)
    limit=kwargs_dict.get("limit") or 500
    only_for_channels = kwargs_dict.get("only_for_channels") or []

    POST_PROCESS_INTERVAL_SECONDS = kwargs_dict.get("post_process_interval_seconds", 10) * 60

    INACTIVITY_TIMEOUT_SECONDS = kwargs_dict.get("inactivity_timeout_seconds", 10) * 60

    mlogger.info("------------ Managing active sessions ------------")
    
    query="""
    SELECT *
        FROM (
            SELECT
            (
                s.dict::jsonb ||
                jsonb_build_object(

                    'needs_history_update',
                        CASE
                            WHEN
                                (s.dict->>'last_response_time') IS NOT NULL
                                AND (
                                    (s.dict->>'history_updated_time') IS NULL
                                    OR
                                    COALESCE(
                                        (s.dict->>'last_response_time')::NUMERIC,
                                        0
                                    ) >
                                    COALESCE(
                                        (s.dict->>'history_updated_time')::NUMERIC,
                                        0
                                    )
                                )
                            THEN TRUE
                            ELSE FALSE
                        END,
                        

                    'needs_post_process',
                        CASE
                            WHEN (
                                (s.dict->>'last_response_time') IS NOT NULL
                                AND (
                                    s.dict->>'last_post_process_time' IS NULL
                                    OR (
                                        EXTRACT(EPOCH FROM NOW())::NUMERIC -
                                        COALESCE(
                                            (s.dict->>'last_post_process_time')::NUMERIC,
                                            0
                                        )
                                    ) >= %s
                                )
                                AND COALESCE(
                                    (s.dict->>'has_unprocessed_history')::BOOLEAN,
                                    FALSE
                                ) = TRUE
                            )
                            THEN TRUE
                            ELSE FALSE
                        END,

                    'inactive_cutoff_epoch',
                        CASE
                            WHEN (s.dict->>'last_response_time') IS NOT NULL
                            THEN
                                (
                                    (s.dict->>'last_response_time')::NUMERIC
                                    + %s
                                )
                            ELSE NULL
                        END
                )
            ) AS dict

            FROM session s

            WHERE
                (s.dict->>'session_live')::BOOLEAN = TRUE

                AND COALESCE(
                    s.dict->>'status',
                    ''
                ) NOT IN ('completed', 'failed', 'busy')

                AND COALESCE(
                    s.dict->>'channel',
                    ''
                ) != 'voice_phone'

                AND (
                    (
                        s.dict->>'campaign_type' = 'pre-sales'
                        AND EXISTS (
                            SELECT 1
                            FROM pre_sales_campaign p
                            WHERE
                                p.dict->>'campaign_id' =
                                s.dict->>'campaign_id'
                                AND LOWER(
                                    p.dict->>'campaign_status'
                                ) = 'active'
                        )
                    )
                    OR
                    (
                        s.dict->>'campaign_type' = 'post-sales'
                        AND EXISTS (
                            SELECT 1
                            FROM post_sales_campaign p
                            WHERE
                                p.dict->>'campaign_id' =
                                s.dict->>'campaign_id'
                                AND LOWER(
                                    p.dict->>'campaign_status'
                                ) = 'active'
                        )
                    )
                )
        ) q

        WHERE
            COALESCE(
                (q.dict->>'needs_history_update')::BOOLEAN,
                FALSE
            )
            OR
            COALESCE(
                (q.dict->>'needs_post_process')::BOOLEAN,
                FALSE
            )

        LIMIT %s;
    """
    
    with get_pg_connector() as pg:

        mlogger.info("------------------------")
        session_list = pg.fetch_all(query, (
            POST_PROCESS_INTERVAL_SECONDS,
            INACTIVITY_TIMEOUT_SECONDS,
            limit
        ))

        mlogger.info(f"Eligible active sessions count: {len(session_list)}")
        
        if not session_list:
            mlogger.info("No eligible active sessions found.")
            return


        for row in session_list:
            session = {}
            
            try:

                session = row.get("dict", row)
                
                session_id = session.get("session_id")

                channel = session.get("channel")

                if only_for_channels and channel not in only_for_channels:
                    mlogger.info(f"Skipping session {session_id} for channel {channel}")
                    continue

                mlogger.info(f"Processing session_id={session_id}")

                needs_history_update = session.get("needs_history_update")

                needs_post_process = session.get("needs_post_process")

                inactive_cutoff_epoch = session.get("inactive_cutoff_epoch")

                last_history_epoch = float(session.get("history_updated_time") or 0)

                existing_history = session.get("history", []) or []

                mlogger.info(f"Needs history update: {needs_history_update} and Needs post process: {needs_post_process} for session_id={session_id}")
                # HISTORY UPDATE

                if needs_history_update:

                    mlogger.info(f"Updating history for session_id={session_id}")

                    message_query = """
                        SELECT
                            dict,
                            GREATEST(
                                CASE
                                    WHEN COALESCE(dict->>'created','') ~ '^[0-9]+(\\.[0-9]+)?$'
                                    THEN (dict->>'created')::NUMERIC
                                    ELSE EXTRACT(
                                        EPOCH FROM
                                        (dict->>'created')::TIMESTAMPTZ
                                    )
                                END,
                                CASE
                                    WHEN COALESCE(dict->>'updated','') ~ '^[0-9]+(\\.[0-9]+)?$'
                                    THEN (dict->>'updated')::NUMERIC
                                    ELSE EXTRACT(
                                        EPOCH FROM
                                        (dict->>'updated')::TIMESTAMPTZ
                                    )
                                END
                            ) AS effective_ts
                        FROM message
                        WHERE
                            dict->>'session_id' = %s
                            AND GREATEST(
                                CASE
                                    WHEN COALESCE(dict->>'created','') ~ '^[0-9]+(\\.[0-9]+)?$'
                                    THEN (dict->>'created')::NUMERIC
                                    ELSE EXTRACT(
                                        EPOCH FROM
                                        (dict->>'created')::TIMESTAMPTZ
                                    )
                                END,
                                CASE
                                    WHEN COALESCE(dict->>'updated','') ~ '^[0-9]+(\\.[0-9]+)?$'
                                    THEN (dict->>'updated')::NUMERIC
                                    ELSE EXTRACT(
                                        EPOCH FROM
                                        (dict->>'updated')::TIMESTAMPTZ
                                    )
                                END
                            ) > %s
                        ORDER BY effective_ts ASC
                    """

                    history_rows = pg.fetch_all(
                        message_query,
                        (
                            session_id,
                            last_history_epoch or 0
                        )
                    )

                    if not history_rows:
                        mlogger.info(
                            f"No new messages found for session {session_id}"
                        )
                        continue

                    mlogger.info(
                        f"Found {len(history_rows)} messages for session {session_id}"
                    )

                    appended_history = []
                    last_ts = None

                    for row in history_rows:
                        # mlogger.info(f"Processing message: {row}")
                        record = row[0]
                        ts = float(row[1])
                        # mlogger.info(f"Ts: {ts}")
                        # mlogger.info(f"Processing message: created={record.get('created')} updated={record.get('updated')} effective_ts={ts} history_updated_time={last_history_epoch}")

                        if not ts:
                            continue

                        last_ts = float(ts)

                        appended_history.append({
                            "index": record.get("index"),
                            "role": ("user" if record.get("reply_to") == "" else "agent"),
                            "timestamp": ts,
                            "message": record.get("message"),
                        })

                    if not appended_history:
                        mlogger.info(f"No valid messages found for session {session_id}")
                        continue

                    mlogger.info(f"Appending {len(appended_history)} messages to history for session {session_id}")

                    start_time = normalize_ts(session.get("start_time"))

                    update_payload = {
                        "history": existing_history + appended_history,
                        "history_updated_time": float(last_ts),
                        "has_unprocessed_history": True
                    }

                    if start_time and last_ts:
                        update_payload["duration"] = (last_ts - start_time)

                    pg.update(
                        "session",
                        "session_id",
                        session_id,
                        update_payload
                    )

                    mlogger.info(f"Updated history for session_id={session_id} messages_added={len(appended_history)} history_updated_time={last_ts}")

                    # needs_post_process = True
                
                # POST PROCESS

                if needs_post_process:

                    mlogger.info(f"Calling post-process for session_id={session_id}")

                    handle_session_post_process_or_end(session_id=session_id, pg=pg, history_updated=True, can_call_post_process=True, inactive_cutoff_epoch=inactive_cutoff_epoch)

            except Exception as e:

                mlogger.exception(f"Error processing session_id={session.get('session_id')}: {str(e)}")

        mlogger.info("************************************************")
   
    
        
def apply_filters(session_id=None, user_id=None, channel=None, session_live=None, status=None, disposition=None):
    conditions = [] 
    params = ()
    if session_id:
        conditions.append("dict->>'session_id' = %s")
        params += (session_id,)          
    if user_id:
        conditions.append("dict->>'user_id' = %s")
        params += (user_id,)
    if channel:
        if channel.endswith('~'):
            conditions.append("dict->>'channel' <> %s")
            channel = channel[:-1]
            params += (channel,)
        else:
            conditions.append("dict->>'channel' = %s")
            params += (channel,)
    if session_live:
        conditions.append("CAST (dict->>'session_live' AS bool) = %s")
        params += (session_live,)
    if status:
        if status.endswith('~'):
            conditions.append("dict->>'status' <> %s")
            status = status[:-1]
            # first_part += "AND LOWER(CAST(dict->>'status' AS text)) <> LOWER(%s)"
            params += (status,)
        else:
            conditions.append("dict->>'session_live' = %s")
            params += (session_live,)
    if disposition:
        if disposition.endswith('~'):
            conditions.append("dict->>'disposition' <> %s")
            disposition = disposition[:-1]
            params += (disposition,)
        else:
            conditions.append("dict->>'disposition' = %s")
            params += (disposition,)

    condition = "Where " + " AND ".join(conditions)
    return condition, params


@gryd.is_a_task(function_name="schedule_campaign_trigger")
def schedule_campaign_trigger(*args, **kwargs):
    """
    Schedules campaigns which have a start_date earlier than the current epoch time.
    
    This function is used by the cron service to periodically trigger campaigns which are planned.
    It checks both pre-sales and post-sales campaigns and sets the campaign_status to "Active".
    
    :return: None
    """
    epoch_time = int(time.time())
    batch_size= kwargs.get("batch_size", 50)
    
    where_clause = f"""
    (dict->>'campaign_status') = 'Planned'
    AND (dict->>'start_date')::bigint <= {epoch_time}
    LIMIT {batch_size}
    """

    tables = ["pre_sales_campaign", "post_sales_campaign"]
    
    with get_pg_connector() as pg:

        for table in tables:
            campaigns = list(pg.list(table, where_clause))

            mlogger.info(f"Found {len(campaigns)} campaigns to trigger in {table}")
            
            for campaign in campaigns:
                mlogger.info(f"Triggering campaign for- campaign_id: {campaign.get('campaign_id')} , campaign_type: {campaign.get('campaign_type')} , delearship_id: {campaign.get('dealership_id')}")
            
            #TODO: we need to get the channels, check the queue length and if the queue length is <= max_thresold we proceed and get leads and trigger the campaign, else we skip and wait for the next cron cycle to trigger the campaign.
            # and at the end change the campaign status to "Active"
            
            #     pg.update(
            #         table,
            #         "campaign_id",
            #         campaign.get("campaign_id"),
            #         {"campaign_status": "Active"},
            #     )
                
                
                

@gryd.is_a_task(function_name="end_campaigns")     
def end_campaigns(**kwargs):
    """
    Ends campaigns whose end_date is less than current epoch time.
    """
    
    months_ago = kwargs.get("months_ago", 0)
    limit = kwargs.get("limit", 500)
    cutoff_epoch = None
    if months_ago:
        cutoff_epoch = (
            int(time.time())
            - (months_ago * 30 * 24 * 60 * 60)
        )
    else:
        cutoff_epoch = int(time.time())

    tables = ["pre_sales_campaign","post_sales_campaign"]
    mlogger.info(f"Cutoff epoch: {cutoff_epoch}, months ago: {months_ago}")
    with get_pg_connector() as pg:

        for table in tables:

            query = f"""
                SELECT *
                FROM {table}
                WHERE (dict->>'end_date')::BIGINT < %s
                AND (dict->>'campaign_status') = 'Active'
                ORDER BY (dict->>'end_date')::BIGINT ASC
                LIMIT {limit}
            """

            
            campaigns = list(
                pg.fetch_all(query, [cutoff_epoch])
            )

            mlogger.info(
                f"Found {len(campaigns)} campaigns to end in {table}"
            )

            for campaign in campaigns:

                campaign_id = campaign[0]

                mlogger.info(
                    f"Ending campaign_id={campaign_id} in {table}"
                )

                pg.update(
                    table,
                    "campaign_id",
                    campaign_id,
                    {
                        "campaign_status": "Completed"
                    }
                )

            mlogger.info(f"Completed processing for {table}")
            
@gryd.is_a_task(logger_param='logger', job_param='job')
def create_campaign_ideas_for_dealerships(
        campaign_types:Union[List[str], None]=None, 
        campaign_objectives:Union[List[str], Dict[str, List[str]]]=None, 
        logger=None, job=None, *args, **kwargs
    ) -> Dict[str, int]:
    """
    This task creates campaign ideas for all dealerships.
    Args:
        campaign_types (list): The types of campaigns to create.
        campaign_objectives (list or dict): The objectives of the campaigns to create. If a dict, the key is the dealership id and the value is a list of objectives.
        depending on each campaign_type, for each dealership, we will be calling the create_campaign_idea task with the appropriate arguments.
        logger (Logger): The logger to use.
        job (Job): The job to use.
        return (dict): The number of campaign ideas created.
        *args: The arguments to pass to the task.
        **kwargs: The keyword arguments to pass to the task.
    """
    logger = logger or mlogger
    pre_sales_campaign_model = gryd.base_model.Model('pre_sales_campaign', AUTOCRM_APP_ENTERPRISE_ID)
    post_sales_campaign_model = gryd.base_model.Model('post_sales_campaign', AUTOCRM_APP_ENTERPRISE_ID)
    campaign_objective_model = gryd.base_model.Model('campaign_objective', AUTOCRM_APP_ENTERPRISE_ID)
    default_campaign_objectives = {
        'post-sales': campaign_objective_model.list(campaign_type='post-sales', _as_option = True, _page_size=100),
        'pre-sales': campaign_objective_model.list(campaign_type='pre-sales', _as_option = True, _page_size=100)
    }
    campaign_types = hp.make_list(campaign_types or ['pre-sales', 'post-sales'])
    if isinstance(campaign_objectives, list):
        campaign_types = [campaign_types[0]]
        campaign_objectives = {campaign_types[0]: campaign_objectives}
    elif isinstance(campaign_objectives, dict):
        if any(k not in campaign_objectives for k in campaign_types):
            raise ValueError(f"All campaign_types {campaign_types} must be present in campaign_objectives dict. {campaign_objectives}")
    else:
        raise ValueError(f"campaign_objectives must be a list or dict. {campaign_objectives}")
    campaign_objectives = campaign_objectives or default_campaign_objectives
    dm = gryd.base_model.Model('dealership', AUTOCRM_APP_ENTERPRISE_ID)
    created_idea_count = 0
    for dealership in dm.yield_list():
        logger.info(f"Creating campaign ideas for dealership: {dealership['dealership_id']}")
        for campaign_type in campaign_types:
            logger.info(f"Creating campaign ideas for dealership: {dealership['dealership_id']} with campaign_type: {campaign_type}")
            for campaign_objective in campaign_objectives[campaign_type]:
                logger.info(f"Creating campaign idea for dealership: {dealership['dealership_id']} with campaign_type: {campaign_type} and campaign_objective: {campaign_objective}")
                languages = dealership.get('languages', ['English'])
                dealership_id = dealership['dealership_id']
                kwargs = {'dealership_id': dealership_id, 'languages': languages}
                dealership_idea = gryd.await_result(
                    'generate_campaign_idea',AUTOCRM_AGENT_SERVICE_NAME, args=[campaign_type, campaign_objective], kwargs=kwargs, gryd_logger=logger, job_param=job
                )
                if dealership_idea:
                    created_idea_count += 1
                created_idea_count += 1
    return {
        "created_idea_count": created_idea_count,
    }
    
@gryd.is_a_task('create_campaign_templates', logger_param='logger', job_param='job')
def create_campaign_templates(logger=None, job=None):
    """
    This task creates campaign templates for all communication providers.
    Args:
        logger (Logger): The logger to use.
        job (Job): The job to use.
    Returns:
        dict: The number of campaign templates created.
    """
    created_template_count = 0

    logger = logger or mlogger
    communication_credentials_model = gryd.base_model.Model('communication_credential', AUTOCRM_APP_ENTERPRISE_ID)
    dealership_model = gryd.base_model.Model('dealership', AUTOCRM_APP_ENTERPRISE_ID)
    # For all dealerships registered on whatsapp or whatsapp_chat, create campaign templates for them.
    communication_credentials = list(
    communication_credentials_model.yield_list(
        channel=["whatsapp_chat", "whatsapp"]
        )
    )

    logger.info(f"communication creds are : {communication_credentials}")

    # Now loop safely without depending on an active DB cursor
    for communication_credential in communication_credentials:
        dealership_id = communication_credential['dealership_id']
        logger.info(f"dealership id id : {dealership_id}")
        communication_credential_id = communication_credential['communication_credentials_id']
        dealer_name = communication_credential['dealer_name']
        communication_provider_id = communication_credential['communication_provider_id']
        provider_name = communication_credential['provider_name']
        channel = communication_credential['channel']
        data = {
            'waba_id': communication_credential.get('waba_id'),
            'customer_id': communication_credential.get('customer_id'),
            'sub_account_id': communication_credential.get('sub_account_id'),
            'auth_headers': communication_credential.get('auth_headers')  
        }
        default_data = {
            "waba_id": "113485138500957",
            "customer_id": "SOCIOGRAPH_uu76NiJRbNmsq5zPgu5V",
            "sub_account_id": "965a92cd-ac2e-4674-87ab-99fc174e071f",
            "auth_headers": {
                "Content-Type": "application/json",
                "Authorization": "Basic ZGF2ZV9haTpJSjJQVjhebDVjODU="
            }       
        }
               
        string_auth_fields = [
            data.get("waba_id"),
            data.get("customer_id"),
            data.get("sub_account_id")
        ]

        valid_strings = all(
            isinstance(v, (str, int)) and str(v).strip() != ""
            for v in string_auth_fields
        )

        # Validate auth header dict
        auth = data.get("auth_headers")
        valid_auth_header = (
            isinstance(auth, dict)
            and "Authorization" in auth
            and isinstance(auth["Authorization"], str)
            and auth["Authorization"].strip() != ""
        )

        # If ANY field is missing/invalid → fallback to default
        if not (valid_strings and valid_auth_header):
            data = default_data

        post_sales_campaign_model = gryd.base_model.Model('post_sales_campaign', AUTOCRM_APP_ENTERPRISE_ID)
        pre_sales_campaign_model = gryd.base_model.Model('pre_sales_campaign', AUTOCRM_APP_ENTERPRISE_ID)
        default_campaign_objectives = {
            'post-sales': post_sales_campaign_model._model_ref.attributes['campaign_objective_name'].options,
            'pre-sales': pre_sales_campaign_model._model_ref.attributes['campaign_objective_name'].options
        }
        logger.info(f"default_campaign_objectives are : {default_campaign_objectives}")

        logger.info(f"Creating campaign templates for dealer {dealer_name} for provider {provider_name} on channel {channel}")
        for campaign_type in ["pre-sales", "post-sales"]:
            campaign_objectives = default_campaign_objectives[campaign_type]
            for campaign_objective in campaign_objectives:
                logger.info(f"generating campaign template for dealer {dealer_name} for provider {provider_name} on channel {channel} for campaign type {campaign_type} and campaign objective {campaign_objective}")
                dealership = dealership_model.get(dealership_id)
                languages = dealership.get('languages') or ['English']
                default_attributes = {
                    "pre-sales": {
                        "campaign_type": campaign_type,
                        "campaign_objective": campaign_objective,
                        "dealership_id": dealership_id,
                        "languages": languages,
                    },
                    "post-sales": {
                        "campaign_type": campaign_type,
                        "campaign_objective": campaign_objective,
                        "dealership_id": dealership_id,
                        "languages": languages
                    }
                }
                template_required_attributes = {
                    "pre-sales": ["dealer_name", "showroom_full_name", "person_name", "vehicle_category"],
                    "post-sales": ["dealer_name", "workshop_full_name", "reg_number", "vehicle_model", "vehicle_category"]

                }
                audiance_required_attributes = {
                    "pre-sales":[],
                    "post-sales" : []
                }

                template_optional_attributes = {
                    "pre-sales": {
                        "sessions":['last_session_channel', 'last_session_status', "last_session_timestamp"], 
                        "car_preferences": ["brand_preference", "model_preference", "variant_preference", "color_preference"], 
                        "engine_preference":["engine_type_preference", "transmission_preference", "range_preference", "feature_preferences"],
                        "campaign_info":["campaign_offer","urgency_hook","campaign_tagline"]
                    },
                    "post-sales": {
                        "preferences" : ["vehicle_variant", "vehicle_color", "vehicle_type" ],
                        "campaign_info":[ "campaign_offer", "urgency_hook","campaign_tagline"],
                        "sessions": ["last_session_channel", "last_session_status", "last_session_timestamp"]
                    }

                }
                pre_sale_special_combinations = [[],["model_preference","color_preference" ],["model_preference", "variant_preference"],["last_session_channel", "last_session_status"]]
                post_sale_special_combinations = [[],["campaign_offer", "urgency_hook"],["last_session_channel", "last_session_status"],["dealer_name", "workshop_full_name", "reg_number", "vehicle_model", "vehicle_category","next_service_due"]]



                dispositions = ["queued", "attempted", "reached", "engaged"]

                postsales_disposition_detail = {
                        "queued": [
                            "User is interested in purchasing a vehicle"
                        ],
                        "attempted": [
                            "Attempted to contact regarding the vehicle",
                        ],
                        "reached": [
                            "Message Deliverd but didn't seen",
                            "Message sent but not replied"
                        ],
                        "engaged": [
                            "Looking for a discount",
                            "Will decide tomorrow",
                            "Will decide within 1 to 3 days",
                            "Will decide within 4 to 7 days",
                            "Will decide within 8 to 14 days",
                            "Will decide within 15 to 30 days",
                            "Will decide within 31 to 60 days",
                            "Will decide within 61 to 90 days",
                            "Will decide after 90 days",
                            "Will call workshop themselves",
                            "Vehicle is not being run"
                        ]
                    }

                presale_disposition_detail = {
                        "queued": [
                            "User is interested in servicing their vehicle"
                        ],
                        "attempted": [
                            "Attempted to contact regarding the servicing of the vehicle",
                        ],
                        "reached": [
                            "Message Deliverd but didn't seen",
                            "Message sent but not replied"
                        ],
                        "engaged": [
                            "Looking for a discount",
                            "Will decide tomorrow",
                            "Will decide within 1 to 3 days",
                            "Will decide within 4 to 7 days",
                            "Will decide within 8 to 14 days",
                            "Will decide within 15 to 30 days",
                            "Will decide within 31 to 60 days",
                            "Will decide within 61 to 90 days",
                            "Will decide after 90 days",
                            "Will call dealership themselves"
                        ]
                    }

                

                def get_template_variable_list(campaign_type):
                    final_list = []

                    required = template_required_attributes[campaign_type]
                    optional = template_optional_attributes[campaign_type]
                    specials = (
                        pre_sale_special_combinations
                        if campaign_type == "pre-sales"
                        else post_sale_special_combinations
                    )
                    disposition_details = (
                        presale_disposition_detail
                        if campaign_type == "pre-sales"
                        else postsales_disposition_detail
                    )

                    # Base template (required only)
                    base_templates = [required.copy()]

                    # Type-1: required + one optional field

                    for opt_list in optional.values():
                        for field in opt_list:
                            base_templates.append(required + [field])

                    # Type-2: required + special combination

                    for special in specials:
                        base_templates.append(required + special)

                    # Add disposition variations

                    for tmpl in base_templates:
                        for disp in dispositions:
                            for detail in disposition_details[disp]:
                                t = tmpl.copy()
                                t.append({
                                    "disposition": disp,
                                    "disposition_detail": detail
                                })
                                final_list.append(t)

                    return final_list
                
                    
                def send_template_for_approval(template_data: dict,languages: list) -> str | None:
                    """
                    Extract variables directly from message body {{var_name}}
                    Replace them in order to {{1}}, {{2}}, ...
                    Add the original variable names in templateContent.sample.variables
                    Submit template for approval and return templateId.
                    """


                    LANG_TO_CODE = {
                        "English": "en",
                        "Hindi": "hi",
                        "Assamese": "as",
                        "Bengali": "bn",
                        "Gujarati": "gu",
                        "Kannada": "kn",
                        "Kashmiri": "ks",
                        "Malayalam": "ml",
                        "Marathi": "mr",
                        "Nepali": "ne",
                        "Odia": "or",
                        "Punjabi": "pa",
                        "Sanskrit": "sa",
                        "Sindhi": "sd",
                        "Tamil": "ta",
                        "Telugu": "te",
                        "Urdu": "ur",
                        "Konkani": "kok",
                        "Manipuri": "mni",
                        "Maithili": "mai",
                        "Santali": "sat",
                        "Dogri": "doi",
                        "Bodo": "bdo"
                    }
                    lang = languages[0].strip().lower()
                    lang = LANG_TO_CODE.get(lang,"en")

                
                    url = "https://iqwhatsapp.airtel.in/gateway/airtel-xchange/whatsapp-content-manager/v1/template"
                
                    template_name = template_data.get("template_name")
                    template_message = template_data.get("template_message")
                    buttons = template_data.get("buttons", [])
                    standard_buttons = []
                    for btn in template_data.get("buttons", []):
                        new_btn = {
                            "type": btn.get("type", "QUICK_REPLY"),
                            "buttonText": btn.get("buttonText") or btn.get("text")
                        }
                        standard_buttons.append(new_btn)
                
                    buttons = standard_buttons
                
                    if not template_name or not template_message:
                        raise ValueError("template_name and template_message must exist in template_data")
                
                    # Extract variables from message body in order of appearance
                    # Matches: {{vehicle_model}}, {{ service_due_date }} etc.
                    variable_pattern = r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}"
                    extracted_variables = re.findall(variable_pattern, template_message)
                
                    # Remove duplicates but preserve order
                    seen = set()
                    ordered_variables = [v for v in extracted_variables if not (v in seen or seen.add(v))]
                
                    # Replace each variable with numeric placeholder
                    processed_message = template_message
                    for idx, var_name in enumerate(ordered_variables, start=1):
                        pattern = r"\{\{\s*" + re.escape(var_name) + r"\s*\}\}"
                        processed_message = re.sub(pattern, "{{" + str(idx) + "}}", processed_message)
                
                    # Build Airtel payload
                    payload = {
                        "templateName": template_name,
                        "wabaId": data["waba_id"],
                        "customerId": data["customer_id"],
                        "category": "MARKETING",
                        "subAccountId": data["sub_account_id"],
                        "templateContent": {
                            "language": lang,
                            "body": processed_message,
                            "buttons": buttons,
                            "sample": {
                                "variables": ordered_variables  
                            }
                        }
                    }
                
                    headers = data["auth_headers"]
                    if not ordered_variables:
                        payload["templateContent"].pop("sample", None)
                
                
                    print(payload)
                
                    #Submit request
                    try:
                        response = requests.post(url, headers=headers, data=json.dumps(payload))
                
                        if not response.ok:
                            print(f"API Error: {response.status_code} - {response.text}")
                            return None
                
                        response_data = response.json()
                        print(response_data)
                        template_id = response_data.get("template", {}).get("templateId")
                
                        if not template_id:
                            print("Template ID not found in API response:", response_data)
                            return None
                
                        return_data =  {"template_id":template_id,"template_variables":ordered_variables}
                        return return_data

                    except Exception as e:
                        print("Unexpected error:", e)
                        return None
                
                def post_template_into_model(template_data,template_id, template_variables):

                    if not template_id:
                        return

                    template_data["template_id"] = template_id
                    template_data["campaign_type"] = campaign_type
                    template_data["campaign_objective"] = [campaign_objective]
                    template_data["communication_credentials_id"] = communication_credential_id
                    template_data["template_type"] = "text"
                    disposition = None
                    disposition_detail = None

                    if isinstance(template_variables, list):
                        for idx, item in enumerate(template_variables):
                            if isinstance(item, dict):
                                disposition = item.get("disposition")
                                disposition_detail = item.get("disposition_detail")

                                if disposition and disposition_detail:
                                    del template_variables[idx]
                                    break
                                break
                            
                    if disposition and disposition_detail:
                        template_data["disposition_tags"] = [disposition, disposition_detail]

                    template_data["template_variables"] = template_variables



                    try:
                        dim = gryd.base_model.Model('template', AUTOCRM_APP_ENTERPRISE_ID)
                        logger.info(f"Posting result to model 'templates' under enterprise '{AUTOCRM_APP_ENTERPRISE_ID}'")
                        dim.post(template_data)
                        logger.info("Post completed successfully!")
                    except Exception as db_error:
                        logger.error(f"Failed posting to Gryd model: {db_error}")

                def get_approval_status_and_update_in_db(template_ids:List):
                    for template_id in template_ids:
                        total = len(template_ids)
                        logger.info(f"Starting template approval sync for {total} templates")
                        try:
                            for id in template_ids:
                            
                                url = "https://iqwhatsapp.airtel.in/gateway/airtel-xchange/whatsapp-content-manager/v1/template?customerId="+data["customer_id"]+"&"+"subAccountId="+data["sub_account_id"]+"&"+"wabaId="+data["waba_id"]+"&"+"templateId="+id

                                payload = {}
                                headers = data["auth_headers"]

                                logger.debug(f"GET → {url}")

                                response = requests.request("GET", url, headers=headers, data=payload)
                                response = response.json()
                                template_data = response.get("template")
                                logger.info(f"response is {response}")
                                status = template_data.get("registrationStatus").lower()

                                pg.update(table_name="template",id_attr="template_id", id=id,data={"status" : status})
                                logger.info(f"Updated Successfully for template id = {id}")


                        except Exception as e:
                           # Log and continue to next one
                           print(f"[FAILED] template {template_id}: {e}")
                           continue
                

                final_attribute_list = get_template_variable_list(campaign_type)
                template_ids = []

                for attr_list in final_attribute_list:
                    kwargs = {'campaign_type':campaign_type,'campaign_objective': campaign_objective, 'dealership_id': dealership_id, 'languages': languages, 'data':{'attribute_name':attr_list}}
                    campaign_template = gryd.await_result(
                        'generate_whatsapp_template',AUTOCRM_AGENT_SERVICE_NAME, kwargs=kwargs, gryd_logger=logger
                    )
                    #logic for airtel api 
                    api_response = send_template_for_approval(template_data= campaign_template, languages= languages)
                    template_id = api_response.get("template_id")
                    variables = api_response.get("template_variables")
                    template_ids.append(template_id)
                    post_template_into_model(template_data = campaign_template ,template_id= template_id, template_variables = variables)
                
                get_approval_status_and_update_in_db(template_ids=template_ids)

                if campaign_template:
                    created_template_count += 1
    return {
        "created_template_count": created_template_count,
    }

def _normalize_template_status(raw_status):
    """Normalize provider-specific status strings to our canonical values."""
    if not raw_status:
        return None
    status = str(raw_status).strip().lower()
    # Airtel returns `pending_for_review`; Meta/RML return `pending`.
    if status == "pending_for_review":
        status = "pending"
    return status


def _sync_airtel_template_statuses(auth_data, template_ids, logger):
    """Sync status for Airtel-provided WhatsApp templates (per-template GET)."""
    for template_id in template_ids:
        try:
            url = (
                "https://iqwhatsapp.airtel.in/gateway/airtel-xchange/"
                "whatsapp-content-manager/v1/template"
                f"?customerId={auth_data['customer_id']}"
                f"&subAccountId={auth_data['sub_account_id']}"
                f"&wabaId={auth_data['waba_id']}"
                f"&templateId={template_id}"
            )
            headers = auth_data["auth_headers"]
            logger.debug(f"[Airtel] GET → {url}")

            response = requests.request("GET", url, headers=headers, data={})
            response_json = response.json()
            template_data = response_json.get("template")
            if not template_data:
                logger.warning(
                    f"[Airtel] No template data for template {template_id}: {response_json}"
                )
                continue

            logger.info(f"[Airtel] response for {template_id}: {response_json}")
            status = _normalize_template_status(template_data.get("registrationStatus"))
            if not status:
                logger.warning(f"[Airtel] Empty status for template {template_id}")
                continue

            pg.update(
                table_name="template",
                id_attr="template_id",
                id=template_id,
                data={"status": status},
            )
            logger.info(f"[Airtel] Updated status='{status}' for template_id={template_id}")
        except Exception as e:
            logger.error(f"[Airtel] [FAILED] template {template_id}: {e}")
            continue


RML_LOGIN_URL = "https://apis.rmlconnect.net/auth/v1/login/"
RML_TEMPLATES_URL = "https://apis.rmlconnect.net/wba/templates"


def _rml_login(auth_creds, logger):
    """Call Route Mobile's Login API (``POST /auth/v1/login/``) and return a JWT.

    Spec: https://routemobile.github.io/WhatsApp-Business-API/WBS.html
      #tag/WhatsApp-Login/operation/loginApi2

    Returns the ``JWTAUTH`` string on success, ``None`` otherwise.
    """
    if not isinstance(auth_creds, dict):
        logger.error("[RML] auth_creds missing; cannot login for JWT.")
        return None
    username = auth_creds.get("username")
    password = auth_creds.get("password")
    if not username or not password:
        logger.error("[RML] auth_creds.username / auth_creds.password missing.")
        return None

    try:
        resp = requests.post(
            RML_LOGIN_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps({"username": username, "password": password}),
        )
    except Exception as e:
        logger.error(f"[RML] login request failed: {e}")
        return None

    if not resp.ok:
        logger.error(
            f"[RML] login failed: {resp.status_code} - "
            f"{resp.text[:500] if resp.text else '<empty>'}"
        )
        return None

    try:
        body = resp.json()
    except Exception as e:
        logger.error(f"[RML] login response not JSON: {e}")
        return None

    jwt = body.get("JWTAUTH") or body.get("jwtauth") or body.get("token")
    if not jwt:
        logger.error(f"[RML] login response missing JWTAUTH: {body}")
        return None

    logger.info("[RML] login succeeded; obtained fresh JWTAUTH")
    return jwt


def _rml_fetch_templates(jwt, logger):
    """Fetch the full template list from RML using a freshly-minted JWT.

    Returns the parsed JSON body (expected shape: ``{"total": N, "data": [...]}``)
    or ``None`` on unrecoverable failure.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": jwt,
    }
    try:
        logger.debug(f"[RML] GET → {RML_TEMPLATES_URL}")
        response = requests.request(
            "GET", RML_TEMPLATES_URL, headers=headers, data={}
        )
    except Exception as e:
        logger.error(f"[RML] [FAILED] fetching templates: {e}")
        return None

    try:
        response_json = response.json()
    except Exception:
        response_json = None

    if not response.ok:
        logger.error(
            f"[RML] viewTemplateMessage error: {response.status_code} - "
            f"{response_json if response_json is not None else response.text[:500]}"
        )
        return None

    if response_json is None:
        logger.error("[RML] viewTemplateMessage returned non-JSON body.")
        return None

    return response_json


def _sync_rml_template_statuses(auth_data, template_ids, logger):
    """Sync status for Route Mobile (RML) WhatsApp templates.

    For every run we call the Login API (``POST /auth/v1/login/``) with
    ``auth_creds`` from the communication credential to mint a fresh JWT,
    then call the View Template Message endpoint
    (``GET /wba/templates``) which returns every template on the account.
    We look up each of our pending templates in the returned ``data`` array
    and update their status. Any stored JWT on the credential is ignored —
    only ``auth_creds.username`` / ``auth_creds.password`` are read from DB.

    Spec:
      - https://routemobile.github.io/WhatsApp-Business-API/WBS.html
        #tag/WhatsApp-Login/operation/loginApi2
      - https://routemobile.github.io/WhatsApp-Business-API/WBS.html
        #tag/WhatsApp-Messaging-Template-API/operation/viewTemplateMessage
    """
    jwt = _rml_login(auth_data.get("auth_creds"), logger)
    if not jwt:
        logger.error(
            f"[RML] login failed for credential "
            f"{auth_data.get('communication_credentials_id')}; "
            f"skipping status sync."
        )
        return

    response_json = _rml_fetch_templates(jwt, logger)
    if response_json is None:
        return

    templates_by_id = {}
    templates_by_name = {}
    for item in response_json.get("data") or []:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        item_name = item.get("name")
        if item_id:
            templates_by_id[str(item_id)] = item
        if item_name:
            templates_by_name[str(item_name)] = item

    logger.info(
        f"[RML] fetched {len(templates_by_id)} templates from viewTemplateMessage"
    )

    for template_id in template_ids:
        try:
            remote = templates_by_id.get(str(template_id)) or templates_by_name.get(
                str(template_id)
            )
            if not remote:
                logger.warning(
                    f"[RML] template_id={template_id} not found in remote listing"
                )
                continue

            status = _normalize_template_status(remote.get("status"))
            if not status:
                logger.warning(
                    f"[RML] Empty status for template {template_id}: {remote}"
                )
                continue

            update_payload = {"status": status}
            rejected_reason = remote.get("rejected_reason")
            if status == "rejected" and rejected_reason and rejected_reason.upper() != "NONE":
                update_payload["rejection_reason"] = rejected_reason

            pg.update(
                table_name="template",
                id_attr="template_id",
                id=template_id,
                data=update_payload,
            )
            logger.info(
                f"[RML] Updated status='{status}' for template_id={template_id}"
            )
        except Exception as e:
            logger.error(f"[RML] [FAILED] template {template_id}: {e}")
            continue


@gryd.is_a_task('update_template_status', logger_param='logger', job_param='job')
def update_template_status(dealership_id:str,logger=None, job=None):
    """
    get_template_status worker gets the status of a whatsapp template and update the status in template model:
    input : dealership_id : Id of the dealership, required for getting their comm creds

    Provider dispatch (read from ``communication_credential.provider_name``):
      - ``airtel`` → Airtel iqwhatsapp per-template GET
      - ``rml`` / ``route mobile`` → Route Mobile ``/wba/templates`` list
    """
    logger = logger or mlogger
    if not dealership_id:
        logger.error("dealership_id is None or empty.")
        return

    def retrieve_template_ids(communication_credentials_id):
        records = list(pg.list(
            table_name="template",
            where={
                "status": "pending",
                "communication_credentials_id": communication_credentials_id
            }
        ))
        return [
            r.get("template_id")
            for r in records
            if r.get("template_id")
        ]

    default_data = {
        "waba_id": "113485138500957",
        "customer_id": "SOCIOGRAPH_uu76NiJRbNmsq5zPgu5V",
        "sub_account_id": "965a92cd-ac2e-4674-87ab-99fc174e071f",
        "auth_headers": {
            "Content-Type": "application/json",
            "Authorization": "Basic ZGF2ZV9haTpJSjJQVjhebDVjODU="
        }
    }
    records = list(pg.list(
        table_name="communication_credential",
        where={"dealership_id": dealership_id}
    ))

    for data in records:
        communication_credential_id = data.get("communication_credentials_id")
        provider_name = (data.get("provider_name") or "").strip().lower()

        template_ids = retrieve_template_ids(communication_credential_id)
        if not template_ids:
            logger.info(
                f"No pending templates for credential {communication_credential_id}"
            )
            continue

        # Validate auth header dict (common to every provider)
        auth = data.get("auth_headers")
        valid_auth_header = (
            isinstance(auth, dict)
            and "Authorization" in auth
            and isinstance(auth["Authorization"], str)
            and auth["Authorization"].strip() != ""
        )

        total = len(template_ids)
        logger.info(
            f"Starting template approval sync for {total} templates "
            f"(provider={provider_name or 'unknown'}, "
            f"credential={communication_credential_id})"
        )

        if provider_name in ("airtel", ""):
            # Airtel needs waba_id / customer_id / sub_account_id to be present.
            string_auth_fields = [
                data.get("waba_id"),
                data.get("customer_id"),
                data.get("sub_account_id"),
            ]
            valid_strings = all(
                isinstance(v, (str, int)) and str(v).strip() != ""
                for v in string_auth_fields
            )
            auth_data = data if (valid_strings and valid_auth_header) else default_data
            _sync_airtel_template_statuses(auth_data, template_ids, logger)

        elif provider_name in ("rml", "route_mobile", "route mobile", "routemobile"):
            # RML always logs in fresh using auth_creds to mint a JWT; any
            # stored Authorization is ignored.
            auth_creds = data.get("auth_creds") or {}
            has_auth_creds = bool(
                isinstance(auth_creds, dict)
                and auth_creds.get("username")
                and auth_creds.get("password")
            )
            if not has_auth_creds:
                logger.error(
                    f"[RML] Missing auth_creds.username/password on credential "
                    f"{communication_credential_id}; skipping."
                )
                continue
            _sync_rml_template_statuses(data, template_ids, logger)

        else:
            logger.warning(
                f"Unsupported provider_name='{data.get('provider_name')}' for "
                f"credential {communication_credential_id}; skipping "
                f"{total} templates."
            )
            continue

    return "Completed !!!!"

        
def rml_auth_login(user_name, password, max_retries=10, backoff=2):
    url = "https://apis.rmlconnect.net/auth/v1/login/"
    payload = json.dumps({
        "username": user_name,
        "password": password,
        "tdvalue": "3650",
        "recaptcha": None
    })
    headers = {
        'origin': 'https://myaccount.rmlconnect.net',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'Content-Type': 'application/json'
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers=headers, data=payload, timeout=10)

            response.raise_for_status()

            mlogger.info(f"Success on attempt {attempt}")
            return response.json()

        except requests.HTTPError as http_err:
            status_code = http_err.response.status_code
            if 400 <= status_code < 500:
                mlogger.error(f"Fatal error {status_code}: {http_err.response.text}")
                raise
            else:
                mlogger.warning(f"Server error {status_code} on attempt {attempt}: {http_err.response.text}")

        except requests.RequestException as e:
            mlogger.warning(f"Network error on attempt {attempt}: {e}")

        # retry logic
        if attempt < max_retries:
            sleep_time = backoff * attempt
            mlogger.info(f"Retrying in {sleep_time}s...")
            time.sleep(sleep_time)

    raise Exception(f"Failed after {max_retries} attempts")

@gryd.is_a_task(function_name="reset_auth_creds")
def reset_auth_creds(*args, **kwargs):
    """
    Refresh and reset authentication credentials for communication providers.

    This function retrieves communication credential records using the
    provided filters, authenticates with supported providers, and updates
    authorization headers with newly generated authentication tokens.

    Currently, only the RML provider is supported.

    Args:
        *args:
            Unused positional arguments.

        **kwargs:
            Optional filters used to fetch communication credentials.
            Any keyword argument with a non-None value is included in
            the database query.

            Example:
                provider_name="Rml"
                sender="9876543210"

    Workflow:
        1. Build query filters from kwargs.
        2. Fetch matching communication credentials.
        3. Validate presence of authentication credentials.
        4. Authenticate against supported providers.
        5. Extract authentication token from response.
        6. Update auth headers in database.
        7. Log successes, unsupported providers, and failures.

    Supported Providers:
        - RML / rml

    Returns:
        str:
            "Completed!" after processing all matching credentials.

    Notes:
        - Credentials without `auth_creds` are skipped.
        - Unsupported providers are logged and ignored.
        - Errors during authentication are caught and logged so
          processing continues for remaining records.
        - Existing auth headers are preserved and merged with
          refreshed authorization values.

    Example:
        reset_auth_creds(provider_name="Rml")

        reset_auth_creds(
            sender="9876543210",
            provider_name="Rml"
        )
    """
    filters = {k: v for k, v in kwargs.items() if v is not None}
    mlogger.info(f"Filters for resetting auth creds: {filters}")
    mlogger.info("Resetting Auth credentials...")
    
    # NOTE: For now we are doing just for RML. 
    with get_pg_connector() as pg:
        creds = list(pg.list("communication_credential",filters))
        
        for i in creds:
            auth_creds=i.get("auth_creds")
            
            if not auth_creds:
                mlogger.warning(f"No auth creds found for credential {i.get('communication_credentials_id')} and for the number {i.get('sender')}")
                continue
            
            user_name=auth_creds.get("username")
            password=auth_creds.get("password")
            
            try:
                if i.get("provider_name") in ["Rml","rml"]:
                    resp=rml_auth_login(user_name, password)
                    
                    if isinstance(resp, dict):
                        JWTAUTH = resp.get("JWTAUTH")
                        if not JWTAUTH:
                            raise Exception(f"No JWTAUTH found in response: {resp.keys()}")

                        auth_headers = i.get("auth_headers", {})
                        auth_headers.update({"Content-Type": "application/json","Authorization": JWTAUTH})

                        pg.update("communication_credential","communication_credentials_id",i.get("communication_credentials_id"),{"auth_headers": auth_headers})
                    
                    mlogger.info(f"Successfully reset RML credentials for credential {i.get('communication_credentials_id')} and for the number {i.get('sender')}")
                    
                else:
                    mlogger.warning(f"Provider {i.get('provider_name')} is not supported for credential {i.get('communication_credentials_id')}")
            except Exception as e:
                mlogger.error(f"Failed to reset RML credentials for credential {i.get('communication_credentials_id')}: {e} and for the number {i.get('sender')}")
                continue

    return "Completed!"

def normalize_channels(raw_channels):
    if not raw_channels:
        return DEFAULT_CHANNELS

    if isinstance(raw_channels, dict):
        keys = list(raw_channels.keys())
        if len(keys) == 1 and keys[0] == "null":
            return DEFAULT_CHANNELS
        return keys 

    if isinstance(raw_channels, list):
        if len(raw_channels) == 0:
            return DEFAULT_CHANNELS
        return raw_channels

    return DEFAULT_CHANNELS

def get_queue_length(channel,dealership_id=None):
    ql = 0
    mlogger.info(f"Getting queue length for dealership_id={dealership_id} and channel={channel}")
    if channel in ["whatsapp","whatsapp_chat", "rms","email"]:
        ql = gryd.get_queue_length(service=AUTOCRM_COMMUNICATION_SERVICE_NAME)
        mlogger.info(f"Queue length for whatsapp_chat is {ql}")
        return ql
    elif channel in ["voice_phone", "voice"]:
        with get_pg_connector() as pg:
            dealer  = pg.get("dealership", "dealership_id", dealership_id)
            if not dealer:
                mlogger.info(f"No dealership found with dealership_id {dealership_id} returning for default..")
                return gryd.get_queue_length(service=AUTOCRM_VOICE_SERVICE_NAME)
            if not dealer.get("voice_service_name"):
                mlogger.info(f"No voice_service_name found for dealership_id {dealership_id} returning for default..")
                return gryd.get_queue_length(service=AUTOCRM_VOICE_SERVICE_NAME)

            ql = gryd.get_queue_length(service = dealer.get("voice_service_name")) or 0
            mlogger.info(f"Queue length for dealership_id={dealership_id} and channel={channel} is {ql}")
            return ql

    
def get_all_dealerships(pg, channel_filter=None, **kwargs):
    # query = """
    #     SELECT DISTINCT ON (dict->>'dealership_id')
    #         dict->>'dealership_id' AS dealership_id,
    #         COALESCE(dict->'channels', '[]'::jsonb) AS channels
    #     FROM dealership
    #     ORDER BY dict->>'dealership_id'
    # """
    kwargs.update({"dealer_status": "active"})
    mlogger.info("Dealership filter: %s", kwargs)
    result = list(pg.list("dealership", kwargs))
    # result = list(pg.list("dealership", {}))
    mlogger.info("Got %s dealers matching with filter %s", len(result), kwargs)
    
    dealerships = []

    for row in result:
        dealership_id = row.get("dealership_id")
        raw_channels = row.get("channels")
        channels = normalize_channels(raw_channels)

        if channel_filter:
            channels = [c for c in channels if c in channel_filter]

        if not channels:
            continue

        dealerships.append({
            "id": dealership_id,
            "channels": channels
        })
    mlogger.info("Got %s dealers matching with channels %s", len(dealerships), channels)
    return dealerships

@gryd.is_a_task(function_name="mark_inactive_dealerships")
def mark_inactive_dealerships(*args,**kwargs):
    """
    Mark dealerships as inactive if they have not had any contact activity
    within the specified inactivity period.

    This function retrieves the latest contact timestamp for each dealership
    from the `contact_status` table and compares it against an inactivity
    threshold. Any dealership whose most recent contact is older than the
    configured number of inactive days (or has no contact history at all)
    is marked with `dealer_status = 'inactive'`.

    Args:
        *args:
            Unused positional arguments.

        **kwargs:
            inactive_days (int, optional):
                Number of days of inactivity before a dealership is marked
                inactive. Defaults to 14 days.

    Workflow:
        1. Calculate inactivity threshold timestamp.
        2. Fetch latest contact timestamp per dealership.
        3. Identify dealerships:
            - not already inactive
            - with no contact history OR
            - whose latest contact is older than the threshold
        4. Update dealership status to "inactive".
        5. Log dealership details and summary count.

    Returns:
        dict:
            {
                "count": int,
                    Number of dealerships marked inactive.

                "dealership_ids": list[str],
                    List of dealership IDs updated.
            }
    """
    with get_pg_connector() as pg:
        INACTIVE_DAYS=kwargs.get("inactive_days",14)
        inactivity_days=time.time()-(INACTIVE_DAYS * 24 * 60 * 60)
        limit=kwargs.get("limit",100)
        
        query = f"""
        WITH latest_contact AS (
            SELECT DISTINCT ON (dict->>'dealership_id')
                dict->>'dealership_id' AS dealership_id,
                CAST(dict->>'created' AS FLOAT) AS created
            FROM contact_status
            ORDER BY
                dict->>'dealership_id',
                CAST(dict->>'created' AS FLOAT) DESC
        )

        SELECT
            d.dict->>'dealership_id',
            lc.created
        FROM dealership d
        LEFT JOIN latest_contact lc
            ON d.dict->>'dealership_id' = lc.dealership_id
        WHERE
            COALESCE(d.dict->>'dealer_status','') != 'inactive'
            AND (
                lc.created IS NULL
                OR lc.created < {inactivity_days}
            )
        LIMIT {limit}
        """

        result = pg.fetch_all(query)
        dealership_ids = [row[0] for row in result]

        mlogger.info(f"Inactive dealership count: {len(result)} for inactive days = {INACTIVE_DAYS} days")

        for dealership_id, created in result:
            mlogger.info(f"Dealership={dealership_id} is inactive for {INACTIVE_DAYS} days. Last contact timestamp={created}")

            pg.update("dealership", "dealership_id", dealership_id, {"dealer_status": "inactive"})
            
        return {
            "count": len(result),
            "dealership_ids": dealership_ids
        }

def process_lead(pg,lead, channel):
    """
    Process a lead for a given communication channel and schedule an
    asynchronous task for lead handling.

    This function extracts lead information, determines the corresponding
    lead model based on campaign type, resolves the channel identifier,
    and triggers the `process_single_lead` async task. After scheduling
    the task, it clears the lead's next scheduled processing fields to
    avoid duplicate execution.
    """
    # mlogger.info(f"[PROCESS] Processing lead for channel {lead}")
    lead_id=None
    try:
        data, lead_type = lead  
        if not data:
            return
    
        campaign_type=data.get("campaign_type")
        lead_model="pre_sales_lead" if campaign_type == "pre-sales" else "post_sales_lead"
        lead_model_id="pre_sales_lead_id" if campaign_type == "pre-sales" else "post_sales_lead_id"
        lead_id=data.get(lead_model_id)
        channel = data.get("next_channel") if data.get("next_channel") else channel
        if data.get("next_channel_identifier"):
            mlogger.info("Since we have a next channel identifier %s, we are using it.", data.get("next_channel_identifier"))
            channel_identifier=data.get("next_channel_identifier") 
        else:
            c_i=CHANNEL_IDENTIFIER_MAP.get(channel)
            channel_identifier=data.get(c_i).replace("+","") if c_i and data.get(c_i) else None
        mlogger.info("[PROCESS] Processing lead %s for channel %s", lead_id,channel)
        mlogger.info("[PROCESS] channel identifier %s", channel_identifier)
        # mlogger.info("[PROCESS] lead data %s", json.dumps(data,indent=4))
        # TODO: Based on the next_trigger and next_channel call process_single_lead
        mlogger.info(f"Autotriggering - Calling process_single_lead task for channel: {channel}, channel_identifier: {channel_identifier}, lead_id: {lead_id}, campaign_type: {campaign_type}")
        gryd.create_async_task('process_single_lead', AUTOCRM_CAMPAIGN_SERVICE_NAME, args= [
                channel,
                lead_id,
                campaign_type,
                data.get("campaign_id"),
            ], kwargs = {
                "disposition_tag": data.get('disposition',None),
                "disposition_detail_tag": data.get('disposition_detail',None),
                "channel_identifier":  channel_identifier
            })
        # update these attributes in lead_model
        pg.update(lead_model,lead_model_id,lead_id,{
            "next_channel": None,
            "next_channel_identifier": None,
            "next_schedule_time": None,
            "next_trigger": None
        })
        
    except Exception as e:
        mlogger.error(f"[FAILED] Lead {lead_id}")

def fetch_leads(dealership_id, channel, batch_size):
    with get_pg_connector() as pg:
        
        query = """
            WITH pre AS (
                SELECT
                    l.dict,
                    'pre_sales' AS lead_type
                FROM pre_sales_lead l
                WHERE
                    l.dict->>'dealership_id' = %s
                    AND l.dict->>'next_channel' = %s
                    AND (l.dict->>'next_schedule_time')::NUMERIC <= EXTRACT(EPOCH FROM NOW())
                    AND EXISTS (
                        SELECT 1
                        FROM pre_sales_campaign c
                        WHERE
                            c.dict->>'campaign_id' = l.dict->>'campaign_id'
                            AND LOWER(c.dict->>'campaign_status') IN ('active', 'continuous')
                    )
                ORDER BY (l.dict->>'next_schedule_time')::NUMERIC ASC
                LIMIT %s
            ),
            post AS (
                SELECT
                    l.dict,
                    'post_sales' AS lead_type
                FROM post_sales_lead l
                WHERE
                    l.dict->>'dealership_id' = %s
                    AND l.dict->>'next_channel' = %s
                    AND (l.dict->>'next_schedule_time')::NUMERIC <= EXTRACT(EPOCH FROM NOW())
                    AND EXISTS (
                        SELECT 1
                        FROM post_sales_campaign c
                        WHERE
                            c.dict->>'campaign_id' = l.dict->>'campaign_id'
                            AND LOWER(c.dict->>'campaign_status') IN ('active', 'continuous')
                    )
                ORDER BY (l.dict->>'next_schedule_time')::NUMERIC ASC
                LIMIT %s
            )
            SELECT *
            FROM (
                SELECT * FROM pre
                UNION ALL
                SELECT * FROM post
            ) t
            ORDER BY (dict->>'next_schedule_time')::NUMERIC ASC
            LIMIT %s;
        """
        
        params = (
            dealership_id, channel, batch_size,
            dealership_id, channel, batch_size,
            batch_size
        )
        
        _leads=pg.fetch_all(query, params)
        mlogger.info(f"[fetch_leads] TOTAL LEADS for dealership_id={dealership_id} and channel={channel} is {len(_leads)}")
        # mlogger.info(f"LEAD_DATA-->{json.dumps(_leads,indent=4)}")
        # yield _leads
        
        seen = set()
        duplicates = []
        unique_leads = []

        for lead in _leads:
            data, lead_type = lead
            if lead_type == "pre_sales":
                lead_model = "pre_sales_lead"
                lead_id = data.get("pre_sales_lead_id")
            else:
                lead_model = "post_sales_lead"
                lead_id = data.get("post_sales_lead_id")

            unique_key = f"{lead_model}:{lead_id}"
            # mlogger.info(f"[fetch_leads] Processing lead for lead_model: {lead_model}, lead_id: {lead_id}, campaign_id: {data.get('campaign_id')}")

            if unique_key in seen:
                duplicates.append(unique_key)
                continue

            seen.add(unique_key)
            unique_leads.append(lead)

        if duplicates:
            mlogger.info(f"[fetch_leads] DUPLICATE LEADS FOUND: {duplicates}")

        mlogger.info(f"[fetch_leads] Returning {len(unique_leads)} unique leads for dealership_id={dealership_id} and channel={channel}")
        return unique_leads

# @gryd.is_a_task(function_name="test_campaign_workflow")
# def test_campaign_workflow(*args, **kwargs):
#     dealership_id = kwargs.get("dealership_id")
#     channel = kwargs.get("channel")
#     batch_size = kwargs.get("batch_size") or VOICE_BATCH_SIZE

#     try:
#         leads = next(fetch_leads(dealership_id, channel, batch_size))
#     except StopIteration:
#         leads = []

#     mlogger.info(f"TEST [FETCH] Fetched {len(leads)} leads for {dealership_id} - {channel}")

#     if not leads:
#         mlogger.info(f"TEST [EMPTY] No leads for {dealership_id} - {channel}")
#         return

#     mlogger.info(f"[PROCESS] Processing {len(leads)} leads for {dealership_id} - {channel}")

#     with get_pg_connector() as pg:
#         for lead in leads:
#             process_lead(pg, lead, channel)
            
#     return {
#         "status": "success",
#         "message": f"Leads processed successfully for dealership_id={dealership_id} and channel={channel}",
#         "count": len(leads)
#     }

@gryd.is_a_task(function_name="test_campaign_workflow")
def test_campaign_workflow(*args, **kwargs):
    dealership_id = kwargs.get("dealership_id")
    channel = kwargs.get("channel")
    batch_size = kwargs.get("batch_size") or VOICE_BATCH_SIZE
    max_threshold= kwargs.get("voice_max_queue_size") or VOICE_MAX_QUEUE_LENGTH
    try:
        queue_length = get_queue_length(channel, dealership_id)
        mlogger.info(f"[CHECK] Dealership={dealership_id}, Channel={channel}, Queue={queue_length}")
        # leads = next(fetch_leads(dealership_id, channel, batch_size))
        if queue_length <= max_threshold:
            leads = next(fetch_leads(dealership_id, channel, batch_size),[])
            mlogger.info(f"[FETCH] Fetched {len(leads)} leads for {dealership_id} - {channel}")
            # mlogger.info(f"[FETCH] LEAD_DATA-->{json.dumps(leads,indent=4)}")
            if not leads:
                mlogger.info(f"[EMPTY] No leads for {dealership_id} - {channel}")
                return
            mlogger.info(f"[PROCESS] Processing {len(leads)} leads for {dealership_id} - {channel}")

            with get_pg_connector() as pg:
                for lead in leads:
                    process_lead(pg,lead, channel)

            return {
                "status": "success",
                "message": f"Leads processed successfully for dealership_id={dealership_id} and channel={channel}",
                "count": len(leads)
            }
        else:
            mlogger.info(f"[SKIP] Queue({queue_length})> max_threshold({max_threshold}) for dealership={dealership_id}, channel={channel}")
            return
    except Exception as e:
        mlogger.error(f"[ERROR] Failed for dealership={dealership_id}, channel={channel}")
        return {
            "status": "error",
            "message": str(e)
        }
    
@gryd.is_a_task(function_name="process_all_dealerships_for_voice")    
def process_dealerships_voice(voice_batch_size=None,voice_max_queue_size=None,voice_start_time=None,voice_end_time=None, **kwargs):  
    
    """
    First get all the dealerships with the channel filter voice_phone and dealer_status is active.
    for each dealerships and channels we are checking the queue_length and if the queue_lengh is less than the max_thresold 
    then we fetch all the leads for that dealership where we have the next_channel and next_schedule_time < = now time and 
    then process each lead by calling process_single_lead function.
    """
    
    mlogger.info("-------Process all dealerships for voice phone and trigger campaign next action-------")
    
    max_threshold= voice_max_queue_size or VOICE_MAX_QUEUE_LENGTH
    batch_size = voice_batch_size or VOICE_BATCH_SIZE
    start_time = voice_start_time or VOICE_START_TIME
    end_time = voice_end_time or VOICE_END_TIME
    current_hour = hp.now(tz='Asia/Kolkata').hour  #TODO:later update tz according to the region
    mlogger.info(f"Current hour for channel - voice_phone is {current_hour}")
    # Doing an additional check to see if the current hour is within the allowed execution time.
    if current_hour < start_time or current_hour > end_time:
        mlogger.info("Outside allowed execution window for channel - voice_phone.So exiting...")
        return
    with get_pg_connector() as pg:
        dealerships = get_all_dealerships(pg, channel_filter=VOICE_CHANNELS, **kwargs)
        mlogger.info(f"Total dealerships for channel - voice_phone = {len(dealerships)}")
        for dealership in dealerships:
            dealership_id = dealership["id"]
            channels = dealership["channels"]
            for channel in channels:
                mlogger.info("--------------------------------------------")
                try:
                    queue_length = get_queue_length(channel, dealership_id)
                    mlogger.info(f"[CHECK] Dealership={dealership_id}, Channel={channel}, Queue={queue_length}")
                    if queue_length <= max_threshold:
                        leads = fetch_leads(dealership_id, channel, batch_size)
                        mlogger.info(f"[FETCH] Fetched {len(leads)} leads for {dealership_id} - {channel}")
                        # mlogger.info(f"[FETCH] LEAD_DATA-->{json.dumps(leads,indent=4)}")
                        if not leads:
                            mlogger.info(f"[EMPTY] No leads for {dealership_id} - {channel}")
                            continue
                        mlogger.info(f"[PROCESS] Processing {len(leads)} leads for {dealership_id} - {channel}")

                        for lead in leads:
                            process_lead(pg,lead, channel)
                    else:
                        mlogger.info(f"[SKIP] Queue({queue_length})> max_threshold({max_threshold}) for dealership={dealership_id}, channel={channel}")
                        continue
                except Exception as e:
                    mlogger.error(f"[ERROR] Failed for dealership={dealership_id}, channel={channel}")

                
@gryd.is_a_task(function_name="process_dealerships_non_voice")
def process_dealerships_non_voice(batch_size=None,non_voice_max_queue_size=None,non_voice_start_time=None,non_voice_end_time=None, **kwargs):
    
    """
    First get all the dealerships with the channel filter non voice_phone(whatsapp_chat,email,rcs etc..) and dealer_status is active.
    for each dealerships and channels we are checking the queue_length and if the queue_lengh is less than the max_thresold 
    then we fetch all the leads for that dealership where we have the next_channel and next_schedule_time < = now time and 
    then process each lead by calling process_single_lead function.
    """
    
    mlogger.info("-------Process all dealerships for non voice channels and trigger campaign next action-------")

    max_threshold= non_voice_max_queue_size or NON_VOICE_MAX_QUEUE_LENGTH
    b_z = batch_size or NON_VOICE_BATCH_SIZE
    start_time = non_voice_start_time or NON_VOICE_START_TIME
    end_time = non_voice_end_time or NON_VOICE_END_TIME
    current_hour = hp.now(tz='Asia/Kolkata').hour #TODO:later update tz according to the region
    mlogger.info(f"Current hour for channel - non voice is {current_hour}")
    # Doing an additional check to see if the current hour is within the allowed execution time.
    if current_hour < start_time or current_hour > end_time:
        mlogger.info("Outside allowed execution window for channel - non voice.So exiting...")
        return
    with get_pg_connector() as pg:
        dealerships = get_all_dealerships(pg, channel_filter=NON_VOICE_CHANNELS, **kwargs)

        mlogger.info(f"Total dealerships for non voice channels = {len(dealerships)}")
        
        for dealership in dealerships:
            dealership_id = dealership["id"]
            channels = dealership["channels"]
            for channel in channels:
                mlogger.info("--------------------------------------------")
                
                try:
                    queue_length = get_queue_length(channel, dealership_id)
                    mlogger.info(f"[CHECK] Dealership={dealership_id}, Channel={channel}, Queue={queue_length}")
                    if queue_length <= max_threshold:
                        leads = fetch_leads(dealership_id, channel, b_z)
                        mlogger.info(f"[FETCH] Fetched {len(leads)} leads for {dealership_id} - {channel}")
                        if not leads:
                            mlogger.info(f"[EMPTY] No leads for {dealership_id} - {channel}")
                            continue
                        mlogger.info(f"[PROCESS] Processing {len(leads)} leads for {dealership_id} - {channel}")

                        for lead in leads:
                            process_lead(pg,lead, channel)
                    else:
                        mlogger.info(f"[SKIP] Queue>{max_threshold} for dealership={dealership_id}, channel={channel}")
                        continue
                except Exception as e:
                    mlogger.error(f"[ERROR] Failed for dealership={dealership_id}, channel={channel}")
            

@gryd.is_a_task(function_name="manage_socket_server_load", job_param = 'job', logger_param = 'logger')
def manage_socket_server_load(
        upgrade_threshold = None,
        socket_server_app_name = None,
        max_replicas = 100,
        logger = None,
        job = None
    ):
    """
    function to go through all the socket servers, associated with the current environment,
    scale_up if any one has max_connections - upgrade_threshold connections,
    scale_down if total connections < upgrade_threshold * total servers
    """
    logger = logger or mlogger
    ssm = AutocrmModel("socket_server")
    environment = os.environ.get('ENVIRONMENT', 'local')
    upgrade_threshold = upgrade_threshold or 10
    gke_namespace = os.environ.get('GKE_NAMESPACE', 'autobot')
    socket_server_app_name = os.environ.get('AUTOCRM_WEBSOCKET_APP', 'autocrm-socket')
    wctr = cron_worker.wctr.get_controller('gke')
    v1 = wcrt.app_client_v1()
    def scale_up(count = 1):
        current_replicas = 0
        ml = list(map(lambda x: (x.metadata.name, x.spec.replicas), list(filter(lambda x: (x.metadata.name == socket_server_app_name), v1.list_namespaced_deployment(gke_namespace).items))))
        if ml:
            current_replicas = ml[0][1]
        new_replicas = current_replicas + count
        new_replicas = max(min(new_replicas, max_replicas), 0)
        if new_replicas == current_replicas:
            logger.info("Reached threshold, so not scaling by %s", count)
            return current_replicas
        body = {"spec": {"replicas": new_replicas}}
        # Apply the patch to scale the deployment
        r = v1.patch_namespaced_deployment_scale(
            name=socket_server_app_name, 
            namespace=gke_namespace, 
            body=body
        )
        logger.info("Scaled app %s in namespace %s for environment %s to %s, by %s", socket_server_app_name, gke_namespace, environment, r.spec.replicas, count)
        return r.spec.replicas
    any_connections = 0
    any_servers = 0
    to_delete = []
    kwargs = {
        "environment": environment,
    }
    for sv in ssm.yield_list(**kwargs):
        if not sv.get('last_uptime_ping') or sv.get('last_uptime_ping') < hp.epoch() - 120:
            to_delete.append(sv.get('socker_server_id'))
        else:
            any_servers += 1
        any_connection += sv.get('active_connections')
        if sv.get('active_connections', 0) > sv.get('max_active_connections', 100) - upgrade_threshold:
            scale_up()
            return True
    if (any_connections < upgrade_threshold*any_servers) and any_servers > 1:
        logger.info("Total active connections %s are less than %s x %s, scaling down", any_connections, upgrade_threshold, any_servers)
        scale_up(-1)
        return True
    for k in to_delete:
        ssm.delete(k)
    return False

def get_active_crm_campaigns():

    campaigns = []

    campaign_list = [
        "pre_sales_campaign",
        "post_sales_campaign"
    ]

    for campaign_model in campaign_list:

        query = f"""
        SELECT *,
               '{campaign_model}' AS campaign_model
        FROM {campaign_model}
        WHERE dict->>'campaign_status'=%s
        
        """
        # AND (dict->>'last_sync_timestamp'):: NUMERIC
        #     <= EXTRACT(EPOCH FROM NOW())

        results = pg.fetch_all(
            query,
            ("Continuous",)
        )

        mlogger.info(
            f"Found {len(results)} campaigns "
            f"in model {campaign_model}"
        )

        campaigns.extend(results)

    return campaigns

# SESSION POLL HELPER — called by process_crm_campaigns after triggering a lead

def _poll_and_post_process_session(lead_id: str, logger, timeout_secs: int = 600, poll_interval: int = 5):
    """
    After _trigger_audience_task queues a call, poll the DB every `poll_interval`
    seconds (up to `timeout_secs`) waiting for the voice session to complete.
    Once a completed session is found for the given lead_id, calls
    post_session_process with the REAL session_id so that disposition,
    lead_summary, and CRM sheet are updated correctly.
    Args:
        lead_id:       The lead_id returned by _trigger_audience_task.
        logger:        Logger instance from the cron context.
        timeout_secs:  How long to wait (default: 10 minutes).
        poll_interval: How often to poll in seconds (default: 5 s).
    """
    # Statuses that mean the call is still in progress — keep polling.
    PENDING_STATUSES = {
        "pre-initiated",
        "initiated",
        "busy",
        "attempted",
        "ringing",
        "in-progress",
        None
    }
    start = time.time()
    logger.info(f"[CRON][POLL] Polling for completed session — lead_id={lead_id} (timeout={timeout_secs}s)")

    # ── Fast-fail: check if contact_status table exists before looping ──────────
    # pg.list() silently swallows UndefinedTable (via `finally: return`).
    # fetch_all() properly propagates it, so we can detect wrong DB early.
    try:
        with get_pg_connector() as _chk_pg:
            _chk_pg.fetch_all("SELECT * FROM contact_status LIMIT 1")
    except Exception as _tbl_err:
        logger.warning(
            f"print stable error " + str(_tbl_err)
        )
        return  # exit cleanly — don't loop 600s on a known-missing table
    # ────────────────────────────────────────────────────────────────────────────

    while time.time() - start < timeout_secs:
        try:
            with get_pg_connector() as pg:
                cs= list(
                    pg.list_order_by("contact_status", {"lead_id": lead_id}, order_by="created")
                )
                cs=cs[0] if cs and isinstance(cs,list) and len(cs) > 0 else None 
                if not cs:
                    logger.info(
                        f"[CRON][POLL] No contact_status found for lead_id={lead_id}, waiting..."
                    )
                    time.sleep(poll_interval)
                    continue
                
                status = cs.get("provider_status")
                if status == "contacted":

                    session_id = cs.get("message_id")

                    logger.info(
                        f"[CRON][POLL] Session completed — session_id={session_id}, status={status}"
                    )

                    # Fetch transcript/messages for this session
                    messages =  pg.get("session", "session_id", session_id)
                    messages = messages.get("history", []) if messages else []

                    if not messages:
                        logger.info(
                            f"[CRON][POLL] No messages found for session_id={session_id}, waiting..."
                        )
                        time.sleep(poll_interval)
                        continue

                    logger.info(
                        f"[CRON][POLL] Found {len(messages)} messages for session_id={session_id}"
                    )

                    # Keep waiting until transcript is actually available
                    valid_messages = [
                        m for m in messages
                        if m.get("message", "").strip()
                    ]

                    logger.info(
                        f"[CRON][POLL] Valid transcript messages count={len(valid_messages)}"
                    )

                    # Minimum conversation validation
                    if len(valid_messages) < 3:
                        logger.info(
                            "[CRON][POLL] Transcript not ready yet, waiting..."
                        )
                        time.sleep(poll_interval)
                        continue

                    logger.info(
                        f"[CRON][POLL] Transcript ready. Running post_session_process for session_id={session_id}"
                    )

                    try:
                        list(post_session_process(**{
                            "session_id": session_id
                        }))

                        logger.info(
                            f"[CRON][POLL] post_session_process done for session_id={session_id}"
                        )

                    except Exception as psp_err:
                        logger.error(
                            f"[CRON][POLL] post_session_process failed: {psp_err}"
                        )

                    return # done — exit the polling loop
        except Exception as poll_err:
            err_msg = str(poll_err).lower()
            # Permanent error: table doesn't exist (wrong DB / test DB).
            # Retrying won't help — exit immediately.
            if "does not exist" in err_msg or "undefinedtable" in err_msg:
                logger.warning(
                    f"[CRON][POLL] DB table missing — GCP_SECRET likely points to test DB "
                    f"which doesn't have contact_status/message tables. "
                    f"Disposition will be set by server cron. Error: {poll_err}"
                )
                return  # permanent error — don't retry
            logger.error(f"[CRON][POLL] DB poll error for lead_id={lead_id}: {poll_err}")
        time.sleep(poll_interval)
    logger.warning(
        f"[CRON][POLL] Timed out after {timeout_secs}s waiting for session — lead_id={lead_id}"
    )


@gryd.is_a_task(function_name="process_crm_campaigns",logger_param="logger",job_param="job")
def process_crm_campaigns(batch_size=None, queue_length=None , logger=None, job=None):
    # Get all the active campaign where te campaign_Status is Continuous and last_sync_timestamp <= current time
    # For each  campaigns we get the channel check the queu length and if the queu length is <= max_thresold we proceed and get leads
    
    logger =  mlogger

    campaigns = get_active_crm_campaigns()

    if not campaigns:
        logger.info("No campaigns")
        return

    logger.info(f"Current queue={queue_length}")

    for campaign in campaigns:
        campaign = campaign[1]
        logger.info(f"Processing campaign: {campaign}")
        campaign_id = campaign.get("campaign_id")
        dealership_id = campaign.get("dealership_id")
        channels = campaign.get("channels", [])
        crm_details = campaign.get("crm_source_details", {}) or {}
        sheet_url = crm_details.get("sheet_url")
        crm_name = crm_details.get("crm_name")
        campaign_type = campaign.get("campaign_type")

        logger.info(f"Processing campaign_id={campaign_id}")

        try:
            sheet_url = crm_details.get("sheet_url")

            if not sheet_url:
                logger.warning(f"No sheet_url for campaign={campaign.get('_id')}")
                continue

            crm_batch_size = crm_details.get("batch_size")

            for channel in channels:

                is_voice = channel == VOICE_CHANNELS

                max_queue_threshold = (
                    queue_length
                    if queue_length is not None
                    else (
                        VOICE_MAX_QUEUE_LENGTH
                        if is_voice
                        else NON_VOICE_MAX_QUEUE_LENGTH
                    )
                )

                max_batch_size = (
                    batch_size
                    if batch_size is not None
                    else (
                        VOICE_BATCH_SIZE
                        if is_voice
                        else NON_VOICE_BATCH_SIZE
                    )
                )

                current_queue = get_queue_length(
                    channel,
                    dealership_id
                )

                if current_queue >= max_queue_threshold:
                    logger.info(f"Queue threshold reached for {channel}")
                    continue

                effective_batch_size = (crm_batch_size or max_batch_size)

                remaining_capacity = (max_queue_threshold - current_queue)

                leads_to_fetch = min(effective_batch_size,remaining_capacity)

                if leads_to_fetch <= 0:
                    continue

                
                crm = load_crm(
                    crm_name=crm_name,
                    credentials=crm_details.get("api_key"),   # dict from DB
                    sheet_url=crm_details.get("sheet_url"),   # full URL from DB
                )
                

                leads = crm.read_leads_from_sheet(
                    batch_size=leads_to_fetch
                )

                logger.info(f"Fetched {len(leads)} leads for {dealership_id} - {channel}")

                for lead in leads:
                    
                    try:
                        
                        # calling trigger_audience_task which will upload the specific lead to the model and then trigger the campaign
                        task_result = _trigger_audience_task(
                            lead=lead,
                            campaign_id=campaign.get("campaign_id"),
                            campaign_objective_id=campaign.get("campaign_objective_id"),
                            campaign_type=campaign_type,
                            dealership_id=dealership_id,
                            channels=channels,
                            dealership_name=campaign.get("dealership_name")
                        )
                        
                        # mlogger.info(f"Lead: {json.dumps(lead,indent=4)} ")
                        #as soon as the call is triggered, update the lead status back to the sheet for that specific lead.
                        crm.update_status_for_matching_rows(lead,"queued")
                        
                        # After triggering the call, poll DB for the real completed
                        logger.info(f"[process_crm_campaigns] Task result: {task_result}")
                        lead_id = (task_result or {}).get("lead_id")
                        if lead_id:
                            # logger.info(f"[CRON] Waiting for call session to complete for lead_id={lead_id}")
                            # _poll_and_post_process_session(lead_id, logger)
                            logger.info(f"[process_crm_campaigns] Lead id: {lead_id} for campaign: {campaign.get('campaign_id')} and channel: {channel} has been processed.")
                        else:
                            logger.warning(f"[process_crm_campaigns] No lead_id {lead_id} in task result for campaign: {campaign.get('campaign_id')} and channel: {channel}")

                    except Exception as e:
                        logger.error(f"Lead failed: {e}")
                logger.info(
                    f"Finished processing leads for campaign_model={campaign.get('campaign_model')} and channel={channel}")
                pg.update(
                    f"{campaign.get('campaign_type').replace('-','_')}_campaign",
                    "campaign_id",
                    campaign_id,
                    {
                        "last_sync_timestamp": time.time()
                    }
                )    
                    
        except Exception:
            logger.exception(
                f"Campaign error: {campaign.get('_id')}"
            )


def _trigger_audience_task(lead: dict,campaign_id: str,campaign_objective_id: str,campaign_type: str,dealership_id: str,dealership_name: str,channels:list,logger=None):
    logger = logger or mlogger

    name = lead.get("person_name", "")
    phone_number = lead.get("phone_number", "")
    email = lead.get("email", "")

    vehicle_model = lead.get("vehicle_model", "")
    vehicle_category = (
        lead.get("vehicle_category", "Passenger Vehicle")
        or "Passenger Vehicle"
    )

    model_preference = [vehicle_model] if vehicle_model else []

    task_args = (name,phone_number,email)

    task_kwargs = {
        "channel": channels,
        "campaign_id": campaign_id,
        "campaign_objective_id": campaign_objective_id,
        "campaign_type": campaign_type,
        "dealership_id": dealership_id,
        "dealership_name": dealership_name or "",
        "model_preference": model_preference,
        "brand_preference": [],
        "color_preference": [],
        "feature_preferences": [],
        "vehicle_category": vehicle_category,
    }

    logger.info(
        f"[CRON] Queueing manual_register_and_trigger_lead "
        f"for phone={phone_number}"
    )

    result =list(manual_register_and_trigger_lead(*task_args, **task_kwargs))
    if not result:
        logger.info(f"[CRON][ERROR] Task failed for phone={phone_number}")
    result = result[0].get("_result") if isinstance(result, list) else result
    # lead_id = (result or {}).get("lead_id")    
    # logger.info(f"[CRON][DEBUG] Queue response: {lead_id}, result={result}")
 
    return result


def get_c_and_wcrt(c = None, wcontroller = None):
    if os.environ.get('WORKER_CONTEOLLER') != 'gke':
        raise hp.GrydError(f"Cannot scale service unless WORKER_CONTEOLLER is 'gke' not {os.environ.get('WORKER_CONTEOLLER')}")
    c = c or gryd.get_service_connection()
    wcontroller = wcontroller or cron_worker.wctr.get_controller('gke')
    return c, wcontroller

@gryd.is_a_task('scale_up_service', logger_param = 'logger', job_param = 'job') 
def scale_up_service(service_names, environment = None, count = 1, retries = 3, c = None, wcontroller = None, logger = None, job = None):
    logger = logger or mlogger
    c, wcontroller = get_c_and_wcrt(c, wcontroller)
    environment = gryd.get_environment(environment)
    ret = []
    if isinstance(service_name, str):
        service_names = service_names.split(',')
    if not isinstance(service_name, list):
        raise ValueError(f"Service names have to be comma separated string or list, not {service_names}")
    for service_name in service_names:
        service_name = service_name.strip()
        try:
            logger.info("Scaling up service %s (%s) by %s", service_name, environment, count)
            ret.append(wcontroller.scale_up(service_name, environment = environment, count = count))
        except Exception as e:
            if 'Unauthorized' in str(e) and retries > 0:
                wcontroller = cron_worker.wctr.get_controller('gke')
                return scale_down_service(service_name, environment, count, retries - 1)
            raise
    return hp.make_single(ret)

@gryd.is_a_task('scale_down_service', logger_param = 'logger', job_param = 'job') 
def scale_down_service(service_names, environment = None, count = 1, retries = 3, logger = None, job = None):
    return scale_up_service(service_names, environment, - count, retries = retries, logger = logger, job = job)

def is_outbound_voice(service):
    if 'voice' in service and 'inbound' not in service:
        return True
    return False

@gryd.is_a_task('scale_up_voice', logger_param = 'logger', job_param = 'job') 
def scale_up_voice(environment = None, count = 1, retries = 3, logger = None, job = None):
    c, wcontroller = get_c_and_wcrt()
    environment = gryd.get_environment(environment)
    return list(map(lambda x: scale_up_service(
            x, environment = environment, count = count,
            c = c, wcontroller = wcontroller,
        ), OUTBOUND_VOICE_SERVICES
    ))

@gryd.is_a_task('scale_down_voice', logger_param = 'logger', job_param = 'job') 
def scale_up_voice(environment = None, count = 1, retries = 3, logger = None, job = None):
    c, wcontroller = get_c_and_wcrt()
    environment = gryd.get_environment(environment)
    return list(map(lambda x: scale_down_service(
            x, environment = environment, count = wcontroller.get_worker_count(x, environment),
            c = c, wcontroller = wcontroller,
        ), OUTBOUND_VOICE_SERVICES
    ))


def check_inactive_sessions(*args, **kwargs):
    """
    Check for inactive sessions, and update them accordingly.

    Parameters:
        *args: Any additional positional arguments
        **kwargs: Any additional keyword arguments

    Keyword Arguments:
        inactivity_time (int): The number of minutes to consider a session inactive.
            Defaults to 30.
        only_for_channels (List[str]): A list of channels to check for inactive sessions.
            Defaults to [].
        outbound_timeout_minutes (int): The number of minutes to wait for an outbound response.
            Defaults to 1440.

    Returns:
        None
    """

    kwargs_dict = dict(kwargs)

    inactivity_time = kwargs_dict.get("inactivity_time") or 30
    only_for_channels = kwargs_dict.get("only_for_channels") or []
    outbound_timeout_minutes = kwargs_dict.get("outbound_timeout_minutes") or 1440

    mlogger.info(
        "------------ Checking for inactive sessions ------------- "
        f"inactivity_time={inactivity_time}"
    )

    filters = {"session_live": True, "status": "completed~","status":"busy~","status":"failed~"}
    condition, param = apply_filters(**filters)

    with get_pg_connector() as pg:
        session_list = list(
            db.GrydPGConnector.list(pg, "session", condition, param)
        )

        mlogger.info(f"Active sessions count: {len(session_list)}")

        if not session_list:
            mlogger.info("No active sessions found.")
            return

        now_epoch = int(time.time())
        other_channels = []
        for session in session_list:
            session_id = session.get("session_id")
            channel = session.get("channel")
            campaign_type = session.get("campaign_type") or "inbound"

            if channel not in only_for_channels:
                other_channels.append(channel)
                # mlogger.info(
                #     f"Skipping session {session_id} "
                #     f"(channel={channel})"
                # )
                continue

            # last activity time ----------
            last_response_str = session.get("last_response_time")
            last_history_str = session.get("history_updated_time")
            session_created_str = (
                session.get("created") or session.get("start_time")
            )

            if last_response_str:
                last_activity_epoch = int(last_response_str)
            elif last_history_str:
                last_activity_epoch = int(last_history_str)
            elif session_created_str:
                last_activity_epoch = int(session_created_str)
            else:
                mlogger.warning(
                    f"Session {session_id} has no timestamps; "
                    "skipping inactivity check"
                )
                continue

            last_response_epoch = (
                int(last_response_str) if last_response_str else None
            )
            last_history_epoch = (
                int(last_history_str) if last_history_str else None
            )

            # inactivity timeout ----------
            # if campaign_type != "post-sales":
            #     session_timeout_seconds = outbound_timeout_minutes * 60
            # else:
            #     session_timeout_seconds = inactivity_time * 60

            session_timeout_seconds = inactivity_time * 60 
            mlogger.info(
                f"Session {session_id} timeout set to "
                f"{session_timeout_seconds}s"
            )
            inactive_cutoff_epoch = (
                last_activity_epoch + session_timeout_seconds
            )

            existing_history = session.get("history", []) or []

            # Only sync history if last_response_time moved forward
            if (
                last_response_epoch
                and (
                    last_history_epoch is None
                    or last_response_epoch > last_history_epoch
                )
            ):
                history_rows = list(
                    pg.list("message", {"session_id": session_id})
                )

                new_records = []
                for row in history_rows:
                    ts = row.get("created") or row.get("updated")
                    if ts:
                        ts = int(ts)
                        if (
                            last_history_epoch is None
                            or ts > last_history_epoch
                        ):
                            new_records.append(row)

                if new_records:
                    appended_history = []
                    last_ts = None

                    for record in new_records:
                        ts = record.get("created") or record.get("updated")
                        if ts:
                            last_ts = int(ts)

                        appended_history.append(
                            {
                                "index": record.get("index"),
                                "role": (
                                    "user"
                                    if record.get("reply_to") == ""
                                    else "agent"
                                ),
                                "timestamp": ts,
                                "message": record.get("message"),
                            }
                        )

                    pg.update(
                        "session",
                        "session_id",
                        session_id,
                        {
                            "history": existing_history
                            + appended_history,
                            "history_updated_time": last_ts,
                        },
                    )
                    # TODO:also update session related data to respective lead_model by passing last_session_id which will update last_session_channel,last_interaction etc..
                    # update_session_data_in_lead(session_id=session_id,"") 
                    mlogger.info(
                        f"Appended {len(appended_history)} messages"
                        f"for session {session_id}"
                    )
                else:
                    mlogger.info(f"No new history rows for session {session_id}")
            else:
                mlogger.info(f"Skipping history sync for session {session_id} (no new responses)")

            # Inactivity Check ----------
            if now_epoch > inactive_cutoff_epoch:
                mlogger.info(
                    f"Ending inactive session {session_id} "
                    f"(inactive for {now_epoch - last_activity_epoch}s)"
                )

                # ending the session --------
                # end_session(session_id=session_id, pg=pg)
            else:
                mlogger.info(
                    f"Session {session_id} still active "
                    f"({inactive_cutoff_epoch - now_epoch}s remaining)"
                )
        mlogger.info(f"Other channel counts skipped: {len(other_channels)}")
        mlogger.info("************************************************")
        return 


if __name__ == "__main__":
    pass
    # print("[TEST] Running CRM cron...")

    # result = process_crm_campaigns(batch_size=1)

    # print(result)            
