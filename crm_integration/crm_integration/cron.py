"""
CRM Sync Cron — autoengage-crm worker

This cron task is called periodically (e.g. every 5 minutes) by the
Gryd scheduler. It:

  1. Queries the pre_sales_campaign + post_sales_campaign models for
     campaigns where:
       - campaign_status == "Continuous"
       - campaign_user_source == "crm"
       - last_sync_timestamp <= NOW()   (i.e. it's time to re-sync)

  2. For each such campaign, reads the CRM source details:
       crm_source_details.crm_name  →  e.g. "googledocs"
       crm_source_details.sheet_url →  e.g. "Ambal Sanganur Post-sales"

  3. Calls fetch_crm_leads (our task) to pull leads from the sheet
     since last_sync_timestamp.

  4. For each lead, triggers autocrm audience task (campaign_id + objective_id).

  5. Updates last_sync_timestamp on the campaign to NOW() so next cron
     only picks up newer rows.

HOW TO REGISTER AS A CRON:
  In Gryd cron scheduler, register this function to run every N minutes.
  It will be called with no arguments — it queries the DB itself.
"""

import os
import time

import requests as _requests

from gryd_worker import gryd

from crm_integration.load_crm import load_crm


gryd.SERVICE = "autoengage-crm"
gryd.set_queue_manager()

AUTOCRM_APP_ENTERPRISE_ID = "autocrm"   # same as in cron.py in autobot_agents


# ─────────────────────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _now_epoch() -> float:
    """Current time as Unix epoch (seconds)."""
    return time.time()


def _get_continuous_crm_campaigns(campaign_model_name: str) -> list:
    """
    Query the Gryd model for campaigns where campaign_status == "Continuous"
    and last_sync_timestamp is in the past (or never set).
    Returns a list of campaign dicts ready to be synced.
    """
    model = gryd.base_model.Model(campaign_model_name, AUTOCRM_APP_ENTERPRISE_ID)

    now = _now_epoch()

    campaigns = list(model.yield_list(campaign_status="Continuous"))

    # Filter: only those whose last_sync_timestamp is in the past (or never set)
    ready = []
    for c in campaigns:
        last_sync = c.get("last_sync_timestamp")
        if last_sync is None or float(last_sync) <= now:
            ready.append(c)

    return ready


def _update_last_sync_timestamp(campaign_model_name: str, campaign_id: str):
    """
    Update the campaign's last_sync_timestamp to NOW so next cron run
    only picks up rows added after this moment.
    """
    model = gryd.base_model.Model(campaign_model_name, AUTOCRM_APP_ENTERPRISE_ID)
    model.patch(campaign_id, {"last_sync_timestamp": _now_epoch()})


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CRON TASK
# ─────────────────────────────────────────────────────────────────────────────

@gryd.is_a_task(
    logger_param="logger",
    job_param="job"
)
def sync_crm_campaigns(batch_size=100, logger=None, job=None):
    """
    Main cron entry point — called periodically by Gryd scheduler.
    Processes all Continuous CRM campaigns for both pre-sales and post-sales.

    Args:
        batch_size (int): Max leads to process per campaign per run. Default 100.
                          Praveen: "whatever batch size is being passed, return that batch size."
    """
    logger = logger or print

    results = {
        "pre_sales_processed":  0,
        "post_sales_processed": 0,
        "total_leads_fetched":  0,
        "errors":               []
    }

    for campaign_type, model_name in [
        ("pre-sales",  "pre_sales_campaign"),
        ("post-sales", "post_sales_campaign")
    ]:
        logger(f"[CRON] Checking {model_name} for Continuous CRM campaigns...")

        try:
            campaigns = _get_continuous_crm_campaigns(model_name)
            logger(f"[CRON] Found {len(campaigns)} campaigns to sync for {campaign_type}")
        except Exception as e:
            logger(f"[CRON][ERROR] Could not query {model_name}: {e}")
            results["errors"].append(str(e))
            continue

        for campaign in campaigns:
            campaign_id          = campaign.get("campaign_id")
            campaign_objective_id = campaign.get("campaign_objective_id")
            dealership_id        = campaign.get("dealership_id")
            dealership_name      = campaign.get("dealership_name", "")
            crm_source = campaign.get("crm_source_details") or {}

            # Read from crm_source_details first, fall back to top-level fields
            # (The campaign has crm_name and sheet_url at top level instead of nested)
            crm_name   = crm_source.get("crm_name")  or campaign.get("crm_name")
            sheet_name = crm_source.get("sheet_url") or campaign.get("sheet_url")
            last_sync  = campaign.get("last_sync_timestamp")

            # Normalize crm_name — handle different naming conventions
            CRM_NAME_MAP = {
                "google_sheet":  "googledocs",
                "googlesheet":   "googledocs",
                "google sheet":  "googledocs",
                "googledocs":    "googledocs",
                "google_docs":   "googledocs",
                "salesforce":    "salesforce",
            }
            if crm_name:
                crm_name = CRM_NAME_MAP.get(crm_name.lower().strip(), crm_name.lower().strip())

            # Convert epoch to ISO date string for our connector's filter
            if last_sync:
                import datetime
                last_sync_iso = datetime.datetime.fromtimestamp(
                    float(last_sync)
                ).strftime("%Y-%m-%d")
            else:
                last_sync_iso = None

            # ── DEBUG: print full campaign so we can see what's in the DB ──────
            logger(f"[CRON][DEBUG] Campaign data: "
                   f"crm_source_details={crm_source}, "
                   f"campaign_user_source={campaign.get('campaign_user_source')}, "
                   f"campaign_status={campaign.get('campaign_status')}")

            if not crm_name or not sheet_name:
                logger(f"[CRON][SKIP] Campaign {campaign_id} is missing crm_source_details. "
                       f"crm_name={crm_name}, sheet_url={sheet_name}. "
                       f"Ask the campaign owner to set crm_source_details on this campaign in the DB.")
                continue

            logger(f"[CRON] Processing campaign_id={campaign_id}, sheet={sheet_name}, "
                   f"last_sync={last_sync_iso}")

            try:
                crm = load_crm(crm_name, sheet_name=sheet_name)

                # ── STEP 1: Fetch unprocessed leads (empty/NEW, up to batch_size) ──
                # Filter: skip QUEUED/CONTACTED/engaged/done rows — only brand-new leads.
                # Sahib's task writes the final disposition back to the sheet;
                # we only need to trigger autocrm-campaign task and mark each lead as QUEUED.
                leads = (
                    crm.list_pre_sales_leads(batch_size=batch_size)
                    if campaign_type == "pre-sales"
                    else crm.list_post_sales_leads(last_updated=last_sync_iso)
                )

                logger(f"[CRON] Fetched {len(leads)} new leads for campaign {campaign_id} "
                       f"(batch_size={batch_size})")
                results["total_leads_fetched"] += len(leads)

                if not leads:
                    logger(f"[CRON] No new leads. Campaign still counted as processed.")
                    _update_last_sync_timestamp(model_name, campaign_id)
                    if campaign_type == "pre-sales":
                        results["pre_sales_processed"] += 1
                    else:
                        results["post_sales_processed"] += 1
                    continue

                # ── STEP 2: Trigger autocrm-campaign task + mark sheet row QUEUED ─────────
                # QUEUED = call has been scheduled, don't re-trigger on next cron run.
                # Sahib's task will overwrite QUEUED with the real disposition
                # (e.g. "engaged", "not_interested") once the call completes.
                for lead in leads:
                    try:
                        _trigger_audience_task(
                            lead=lead,
                            campaign_id=campaign_id,
                            campaign_objective_id=campaign_objective_id,
                            campaign_type=campaign_type,
                            dealership_id=dealership_id,
                            dealership_name=dealership_name,
                            logger=logger
                        )
                        try:
                            crm.patch_pre_sales_lead(lead, "QUEUED")
                            logger(f"[CRON] Marked phone={lead.get('phone_number')} as QUEUED in sheet")
                        except Exception as patch_err:
                            logger(f"[CRON][WARN] Could not mark QUEUED for {lead.get('phone_number')}: {patch_err}")
                    except Exception as lead_err:
                        logger(f"[CRON][ERROR] Lead {lead.get('phone_number')}: {lead_err}")
                        results["errors"].append(str(lead_err))

                # ── STEP 3: Update last_sync_timestamp ───────────────────────────
                _update_last_sync_timestamp(model_name, campaign_id)
                logger(f"[CRON] Updated last_sync_timestamp for campaign {campaign_id}")

                if campaign_type == "pre-sales":
                    results["pre_sales_processed"] += 1
                else:
                    results["post_sales_processed"] += 1


            except Exception as campaign_err:
                logger(f"[CRON][ERROR] Campaign {campaign_id}: {campaign_err}")
                results["errors"].append(str(campaign_err))

    logger(f"[CRON] Done. Results: {results}")
    return results



# ─────────────────────────────────────────────────────────────────────────────
# AUTOCRM-CAMPAIGN TASK — GRYD TASK APPROACH (via execute_task_with_polling)
# Praveen: "convert this from API to a task, just do a task"
# ─────────────────────────────────────────────────────────────────────────────

# autocrm-campaign service constants
AUTOCRM_BASE_URL  = "https://autobot-webapp-dev-unstable.gryd.in:60133"
AUTOCRM_SERVICE   = "autocrm-campaign"
AUTOCRM_TASK_NAME = "manual_register_and_trigger_lead"

# Auth headers — read from env (set by local.sh / setup.sh), fallback to dev values
AUTOCRM_API_HEADERS = {
    "Content-Type":          "application/json",
    "X-GRYD-APPLICATION-ID": os.environ.get("AUTOCRM_APP_ID",            "autocrm"),
    "X-GRYD-ENTERPRISE-ID":  os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm"),
    "X-GRYD-TOKEN":          os.environ.get("AUTOCRM_TOKEN",             "3bde2588-6b4a-330a-b949-c73ab53cc046"),
    "X-GRYD-SESSION-ID":     os.environ.get("AUTOCRM_SESSION_ID",        "b7eb0857-bdae-325a-903e-5c4fc48851b3"),
    "X-GRYD-ROLE":           os.environ.get("AUTOCRM_ROLE",              "admin"),
}


def execute_task_with_polling(
    base_url,
    service,
    task_name,
    payload,
    on_progress=None,
    interval_ms=2000,
    max_retries=60,
    headers=None,
):
    """
    Executes an asynchronous gryd task, polls for status, retrieves the final result.
    Gryd task pattern — this is the correct way to call a gryd task (not raw API).

    Steps:
      1. POST  /gryd/task/{service}/{task_name}  → get task_id
      2. POLL  /gryd/status/{task_id}            → wait for success/failure
      3. GET   /gryd/result/{task_id}            → return final result
    """
    headers = headers or {"Content-Type": "application/json"}

    def api(endpoint, method="GET", data=None):
        url = f"{base_url}{endpoint}"
        if method == "POST":
            res = _requests.post(url, json=data, headers=headers)
        else:
            res = _requests.get(url, headers=headers)
        res.raise_for_status()
        return res.json()

    # 1. Submit the task
    if on_progress:
        on_progress("Submitting task to queue...")

    task_res = api(f"/gryd/task/{service}/{task_name}", "POST", payload)

    task_id = (
        task_res.get("job", {}).get("task_id")
        or task_res.get("task_id")
    )

    if not task_id:
        raise Exception(
            f"Failed to retrieve task_id from response: {task_res}"
        )

    if on_progress:
        on_progress(f"Task submitted. task_id={task_id}")

    # 2. Poll status
    attempts    = 0
    is_complete = False

    while not is_complete and attempts < max_retries:
        attempts += 1
        time.sleep(interval_ms / 1000.0)

        status_res     = api(f"/gryd/status/{task_id}", "GET")
        current_status = (status_res.get("status") or "").lower()

        if on_progress and (status_res.get("message") or current_status):
            on_progress(status_res.get("message") or f"Status: {current_status}...")

        if current_status in ["success", "completed"]:
            is_complete = True
            if on_progress:
                on_progress("Task complete. Retrieving results...")
        elif current_status in ["failed", "error"]:
            raise Exception(
                status_res.get("error")
                or status_res.get("message")
                or "Task failed on the server."
            )

    if not is_complete:
        raise Exception(f"Task {task_id} timed out after {max_retries} retries.")

    # 3. Fetch result
    result_res = api(f"/gryd/result/{task_id}", "GET")

    if not result_res or "result" not in result_res:
        raise Exception(f"Failed to retrieve result for task {task_id}: {result_res}")

    return result_res["result"]


def _trigger_audience_task(
    lead: dict,
    campaign_id: str,
    campaign_objective_id: str,
    campaign_type: str,
    dealership_id: str,
    dealership_name: str,
    logger
):
    """
    Trigger the autocrm-campaign registration task for a single lead.

    Uses execute_task_with_polling (gryd task approach) instead of raw HTTP POST.
    args[0] = name
    args[1] = phone_number
    args[2] = email
    """
    name         = lead.get("person_name", "")
    phone_number = lead.get("phone_number", "")
    email        = lead.get("email", "")       # not in sheet yet → empty string

    vehicle_model    = lead.get("vehicle_model", "")
    model_preference = [vehicle_model] if vehicle_model else []

    payload = {
        "args": [name, phone_number, email],
        "kwargs": {
            "channel":               "voice_phone",
            "campaign_id":           campaign_id,
            "campaign_objective_id": campaign_objective_id,
            "campaign_type":         campaign_type,
            "dealership_id":         dealership_id,
            "dealership_name":       dealership_name or "",
            "model_preference":      model_preference,
            "brand_preference":      [],
            "color_preference":      [],
            "feature_preferences":   [],
        },
        "runtime_limit": 30000,
        "cancellable":   True,
    }

    logger(f"[CRON] Triggering {AUTOCRM_TASK_NAME} → phone={phone_number}, name={name}")

    result = execute_task_with_polling(
        base_url=AUTOCRM_BASE_URL,
        service=AUTOCRM_SERVICE,
        task_name=AUTOCRM_TASK_NAME,
        payload=payload,
        headers=AUTOCRM_API_HEADERS,
        on_progress=lambda msg: logger(f"[CRON][AUTOCRM] {msg}"),
        interval_ms=3000,   # poll every 3 seconds
        max_retries=30,     # max 90 seconds wait per lead
    )

    logger(f"[CRON] autocrm-campaign task done for phone={phone_number}: {result}")
    logger(f"[CRON][DEBUG] Full autocrm-campaign result = {result}")

    logger(
        f"[CRON][DEBUG] "
        f"campaign_id={campaign_id}, "
        f"campaign_objective_id={campaign_objective_id}, "
        f"phone={phone_number}"
    )

    return result
