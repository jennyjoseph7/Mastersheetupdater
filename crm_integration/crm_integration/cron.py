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

  4. For each lead, triggers Aryan's audience task (campaign_id + objective_id).

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
            # (Aryan set crm_name and sheet_url at top level instead of nested)
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
                       f"Ask Aryan to set crm_source_details on this campaign in the DB.")
                continue

            logger(f"[CRON] Processing campaign_id={campaign_id}, sheet={sheet_name}, "
                   f"last_sync={last_sync_iso}")

            try:
                crm = load_crm(crm_name, sheet_name=sheet_name)

                # ── STEP 1: Fetch unprocessed leads (empty/NEW, up to batch_size) ──
                # Filter: skip QUEUED/CONTACTED/engaged/done rows — only brand-new leads.
                # Sahib's task writes the final disposition back to the sheet;
                # we only need to trigger Aryan and mark each lead as QUEUED.
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

                # ── STEP 2: Trigger Aryan's task + mark sheet row QUEUED ─────────
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
# TRIGGER ARYAN'S TASK via HTTP API
# ─────────────────────────────────────────────────────────────────────────────

# Aryan's API endpoint
ARYAN_API_URL = (
    "https://autobot-webapp-dev-unstable.gryd.in:60133"
    "/gryd/task/autocrm-campaign/manual_register_pre_sales"
)

# Auth headers — read from env (set by local.sh / setup.sh), fallback to dev values
ARYAN_API_HEADERS = {
    "Content-Type":          "application/json",
    "X-GRYD-APPLICATION-ID": os.environ.get("AUTOCRM_APP_ID",         "autocrm"),
    "X-GRYD-ENTERPRISE-ID":  os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm"),
    "X-GRYD-TOKEN":          os.environ.get("AUTOCRM_TOKEN",           "3bde2588-6b4a-330a-b949-c73ab53cc046"),
    "X-GRYD-SESSION-ID":     os.environ.get("AUTOCRM_SESSION_ID",      "b7eb0857-bdae-325a-903e-5c4fc48851b3"),
    "X-GRYD-ROLE":           os.environ.get("AUTOCRM_ROLE",            "admin"),
}


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
    Trigger Aryan's manual_register_pre_sales task for a single lead via HTTP POST.

    API: POST /gryd/task/autocrm-campaign/manual_register_pre_sales
    args[0] = name
    args[1] = phone_number
    args[2] = email
    """
    # Extract the three required fields from the sheet row
    name         = lead.get("person_name", "")
    phone_number = lead.get("phone_number", "")
    email        = lead.get("email", "")        # not in sheet yet → empty string

    # vehicle_model from the sheet → model_preference list
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

            # Preferences — model comes from the sheet
            # brand/color/features can be added once the sheet has those columns
            "model_preference":    model_preference,
            "brand_preference":    [],
            "color_preference":    [],
            "feature_preferences": [],
        },
        "runtime_limit": 30000,
        "cancellable":   True,
    }

    logger(f"[CRON] POST manual_register_pre_sales → phone={phone_number}, name={name}")

    response = _requests.post(
        ARYAN_API_URL,
        headers=ARYAN_API_HEADERS,
        json=payload,
        timeout=30,
    )

    if response.ok:
        logger(f"[CRON] API call success: status={response.status_code}, "
               f"job_id={response.json().get('job_id') or response.json().get('task_id', 'N/A')}")
    else:
        raise RuntimeError(
            f"API returned {response.status_code}: {response.text[:200]}"
        )


