"""
Meta Webhook Server — Lead Ingestion Endpoint
==============================================
Receives real-time lead notifications from Meta's Webhook system
and kicks off the lead ingestion pipeline.

Two endpoints:
  GET  /meta/webhook  — verification (one-time Meta handshake)
  POST /meta/webhook  — event notifications (every time a lead submits a form)

How Meta's webhook flow works:
  1.  We register our URL in Meta App Dashboard.
  2.  Meta sends a GET with hub.verify_token → we echo back hub.challenge.
  3.  Dealership's Facebook Page subscribes to our app (POST to /{page-id}/subscribed_apps).
  4.  Whenever someone fills a Lead Ad form, Meta POSTs a notification to us.
  5.  The notification contains ONLY the leadgen_id (not the actual form data).
  6.  We immediately return 200 OK, then call the Graph API in the background
      to fetch the full lead (name, phone, email, etc.).
  7.  We add the normalized lead to AutoNgage campaign.

Security:
  - Payload signature is validated using HMAC-SHA256 with META_APP_SECRET.
  - Only payloads with a valid X-Hub-Signature-256 header are processed.

Running locally (for testing with ngrok):
  source crm_integration/local.sh
  python3 crm_integration/crm_integration/meta_capi/webhook_server.py

  Then expose via ngrok:
  ngrok http 5055

  Register https://<ngrok-url>/meta/webhook in Meta App Dashboard.

Environment variables (add to local.sh):
  META_APP_SECRET          : From App Dashboard -> Settings -> Basic
  META_WEBHOOK_VERIFY_TOKEN: Any string you choose (set same in App Dashboard)
  META_PAGE_ACCESS_TOKEN   : Long-lived Page Access Token (to call Graph API)
  META_WEBHOOK_PORT        : Port to listen on (default: 5055)

  For local dev fallback config (when meta_webhook_config table row doesn't exist yet):
  META_TEST_CAMPAIGN_ID           : AutoNgage campaign_id to use for test page
  META_TEST_DEALERSHIP_ID         : dealership_id for the test page
  META_TEST_CAMPAIGN_OBJECTIVE_ID : campaign_objective_id for the test page
  META_TEST_CAMPAIGN_TYPE         : e.g. "pre-sales" (default)
  META_TEST_DEALERSHIP_NAME       : optional display name

References:
  https://developers.facebook.com/docs/graph-api/webhooks/getting-started/
  https://developers.facebook.com/docs/graph-api/webhooks/getting-started/webhooks-for-leadgen/
  https://developers.facebook.com/docs/marketing-api/guides/lead-ads/retrieving/
"""

import os
import sys
import hashlib
import hmac
import json
import logging
import threading
from typing import Optional

from flask import Flask, request, jsonify, abort, render_template

# -- Path setup ----------------------------------------------------------------
_CAPI_DIR    = os.path.dirname(os.path.abspath(__file__))
_CRM_INT     = os.path.dirname(_CAPI_DIR)
_CRM_ROOT    = os.path.dirname(_CRM_INT)
_AGENTS_ROOT = os.path.dirname(_CRM_ROOT)

for p in (_CRM_INT, _CRM_ROOT, _AGENTS_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

# cron package is at _AGENTS_ROOT/cron/ — must be imported AFTER path setup above.
# The gryd_worker shim at crm_integration/crm_integration/gryd_worker.py intercepts
# gryd_worker imports and breaks cron/cron.py -> config.py -> gryd_worker chain.
# Remove it temporarily so the pip-installed gryd_worker is found instead.
_shim_dir = os.path.join(_CRM_ROOT, "crm_integration")
_shim_was_in_path = _shim_dir in sys.path
if _shim_was_in_path:
    sys.path.remove(_shim_dir)
try:
    from cron.cron import _poll_and_post_process_session
    print("[WEBHOOK] cron.cron import OK — _poll_and_post_process_session loaded ✅")
except Exception as _cron_import_err:
    import traceback as _tb
    print(f"[WEBHOOK] cron.cron import FAILED: {type(_cron_import_err).__name__}: {_cron_import_err}")
    _tb.print_exc()
    _poll_and_post_process_session = None
finally:
    # Always restore the shim dir so other crm_integration imports still work
    if _shim_was_in_path and _shim_dir not in sys.path:
        sys.path.insert(0, _shim_dir)


from crm_integration.crm_integration.meta_capi.graph_api_client import (
    MetaGraphAPIClient,
    MetaGraphAPIError,
)

# normalize_field_data: canonical version lives in meta_lead_ads.py
try:
    from cohorts_new.ad_platforms.meta_lead_ads import normalize_field_data
except ImportError:
    # Fallback to local copy if cohorts_new path not available
    from crm_integration.crm_integration.meta_capi.graph_api_client import normalize_field_data

# -- Logging -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s: %(name)s: %(levelname)s: %(message)s",
)
logger = logging.getLogger("meta_webhook")

# -- Flask app -----------------------------------------------------------------
app = Flask(__name__)


# ------------------------------------------------------------------------------
# Config -- read from environment
# ------------------------------------------------------------------------------

def _require_env(key: str) -> str:
    val = os.environ.get(key, "")
    if not val or val.startswith("YOUR_"):
        logger.warning("  %s is not set in environment -- webhook may not work.", key)
    return val


APP_SECRET        = os.environ.get("META_APP_SECRET", "")
VERIFY_TOKEN      = os.environ.get("META_WEBHOOK_VERIFY_TOKEN", "autongage_meta_webhook")
PAGE_ACCESS_TOKEN = os.environ.get("META_PAGE_ACCESS_TOKEN", "")
WEBHOOK_PORT      = int(os.environ.get("META_WEBHOOK_PORT", 5055))

# Local JSON config file — written by seed/meta_webhook_config_seed.py when DB unavailable
_LOCAL_CONFIG_PATH = os.path.join(_AGENTS_ROOT, "config", "meta_webhook_config.json")


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def _verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Validate Meta's X-Hub-Signature-256 header.
    Returns True if the payload is genuinely from Meta.

    Meta computes: sha256=HMAC(APP_SECRET, raw_payload_bytes)
    """
    if not APP_SECRET:
        logger.warning("META_APP_SECRET not set -- skipping signature validation.")
        return True  # Allow in dev mode; NEVER skip in production

    if not signature_header or not signature_header.startswith("sha256="):
        logger.warning("Missing or malformed X-Hub-Signature-256 header.")
        return False

    expected_sig = signature_header[len("sha256="):]
    computed_sig = hmac.new(
        APP_SECRET.encode("utf-8"),
        payload_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_sig, expected_sig)


def _get_webhook_config(page_id: str) -> Optional[dict]:
    """
    Look up the AutoNgage campaign configuration for a given Meta page_id.

    Priority order:
      1. meta_webhook_config table in Postgres (production)
      2. config/meta_webhook_config.json file (local dev — written by seed script)
      3. META_TEST_* environment variables (quick test override)

    Returns a dict with: dealership_id, campaign_id, campaign_type,
    campaign_objective_id, dealership_name -- or None if not found anywhere.
    """
    # -- Priority 1: Try DB --------------------------------------------------
    try:
        from autocrm_db_helper import get_pg_connector
        with get_pg_connector() as pg:
            rows = list(pg.list("meta_webhook_config", {
                "page_id":   page_id,
                "is_active": True,
            }))
            if rows:
                cfg = rows[0]
                logger.info(
                    "[WEBHOOK] Config found in DB for page_id=%s -> campaign=%s dealership=%s",
                    page_id, cfg.get("campaign_id"), cfg.get("dealership_id"),
                )
                return cfg
            logger.info("[WEBHOOK] No DB config for page_id=%s", page_id)
    except Exception as exc:
        logger.warning(
            "[WEBHOOK] DB config lookup failed (%s) -- trying local JSON file.",
            type(exc).__name__,
        )

    # -- Priority 2: Local JSON file (written by seed/meta_webhook_config_seed.py) ---
    try:
        if os.path.exists(_LOCAL_CONFIG_PATH):
            with open(_LOCAL_CONFIG_PATH, "r") as f:
                all_configs = json.load(f)
            if isinstance(all_configs, list):
                for cfg in all_configs:
                    if str(cfg.get("page_id")) == str(page_id) and cfg.get("is_active", True):
                        logger.info(
                            "[WEBHOOK] Config found in local JSON file for page_id=%s "
                            "-> campaign=%s dealership=%s",
                            page_id, cfg.get("campaign_id"), cfg.get("dealership_id"),
                        )
                        return cfg
            logger.info("[WEBHOOK] No JSON file config for page_id=%s", page_id)
        else:
            logger.info("[WEBHOOK] Local config file not found: %s", _LOCAL_CONFIG_PATH)
    except Exception as exc:
        logger.warning("[WEBHOOK] JSON file config lookup failed: %s", exc)

    # -- Priority 3: Env variable fallback (for quick overrides) --------------
    campaign_id   = os.environ.get("META_TEST_CAMPAIGN_ID", "")
    dealership_id = os.environ.get("META_TEST_DEALERSHIP_ID", "")
    campaign_obj  = os.environ.get("META_TEST_CAMPAIGN_OBJECTIVE_ID", "")

    if campaign_id and dealership_id and campaign_obj:
        logger.warning(
            "[WEBHOOK] Using ENV fallback config for page_id=%s "
            "(META_TEST_CAMPAIGN_ID / META_TEST_DEALERSHIP_ID / META_TEST_CAMPAIGN_OBJECTIVE_ID). "
            "Run seed/meta_webhook_config_seed.py to create a proper config file.",
            page_id,
        )
        return {
            "dealership_id":         dealership_id,
            "campaign_id":           campaign_id,
            "campaign_type":         os.environ.get("META_TEST_CAMPAIGN_TYPE", "pre-sales"),
            "campaign_objective_id": campaign_obj,
            "dealership_name":       os.environ.get("META_TEST_DEALERSHIP_NAME", ""),
        }

    return None


def _process_lead_async(leadgen_id: int, page_id: str, form_id: str, ad_id: str):
    """
    Background thread: fetch full lead from Graph API -> add to AutoNgage.
    Runs in a daemon thread so the webhook returns 200 immediately.

    Flow:
      1. Fetch full lead data from Meta Graph API (Graph API call).
      2. Look up AutoNgage campaign config for this page_id (meta_webhook_config table).
      3. Map Meta lead fields -> AutoNgage lead format (name->person_name etc.).
      4. Call _trigger_audience_task() -> manual_register_and_trigger_lead() -> creates
         pre_sales_lead in DB + queues process_single_lead Gryd task (AI call).
      5. Poll for call session completion -> post_session_process() (disposition update).
      6. Write audit log entry.
    """
    logger.info(
        "[WEBHOOK] Processing lead: leadgen_id=%s page_id=%s form_id=%s ad_id=%s",
        leadgen_id, page_id, form_id, ad_id,
    )

    # -- Step 1: Fetch full lead data from Meta Graph API ---------------------
    if not PAGE_ACCESS_TOKEN or PAGE_ACCESS_TOKEN.startswith("YOUR_"):
        logger.error(
            "[WEBHOOK] META_PAGE_ACCESS_TOKEN not set -- cannot fetch lead %s. "
            "Add it to crm_integration/local.sh.",
            leadgen_id,
        )
        return

    try:
        graph_client = MetaGraphAPIClient(page_access_token=PAGE_ACCESS_TOKEN)
        meta_lead = graph_client.get_lead(leadgen_id=leadgen_id)
    except MetaGraphAPIError as exc:
        logger.error("[WEBHOOK] Failed to fetch leadgen_id=%s: %s", leadgen_id, exc)
        return
    except Exception:
        logger.exception("[WEBHOOK] Unexpected error fetching leadgen_id=%s", leadgen_id)
        return

    logger.info(
        "[WEBHOOK] Lead fetched: leadgen_id=%s name=%r phone=%r",
        leadgen_id,
        meta_lead.get("name"),
        meta_lead.get("phone_number"),
    )

    # -- Step 2: Look up AutoNgage campaign config for this page_id -----------
    config = _get_webhook_config(page_id)
    if not config:
        logger.warning(
            "[WEBHOOK] No meta_webhook_config found for page_id=%s. "
            "Skipping ingestion -- lead audit-logged only. "
            "Add a row to meta_webhook_config (or set META_TEST_* env vars) to activate.",
            page_id,
        )
        _audit_log_lead({
            **meta_lead,
            "page_id":  page_id,
            "ingested": False,
            "reason":   "no_config",
        })
        return

    logger.info(
        "[WEBHOOK] Config resolved: dealership=%s campaign=%s type=%s",
        config.get("dealership_id"),
        config.get("campaign_id"),
        config.get("campaign_type"),
    )

    # -- Step 3: Map Meta lead fields -> AutoNgage format ---------------------
    # _trigger_audience_task() reads "person_name" (not "name") and
    # "vehicle_model" (not "car_model") -- map them here.
    autongage_lead = {
        "person_name":      meta_lead.get("name", ""),
        "phone_number":     meta_lead.get("phone_number", ""),
        "email":            meta_lead.get("email", ""),
        "vehicle_model":    (
            meta_lead.get("car_model")
            or meta_lead.get("vehicle_model", "")
        ),
        # Required by pre_sales_lead model — map from Meta form if present,
        # otherwise default to "Passenger Vehicle" (same as campaign_manager default).
        "vehicle_category": (
            meta_lead.get("vehicle_category")
            or meta_lead.get("car_category")
            or "Passenger Vehicle"
        ),
        # Generic source metadata stored in pre_sales_lead.external_source_data (jsonb)
        # Saved by manual_register_and_trigger_lead -> allowed_keys includes this key.
        "external_source_data": {
            "source":     "meta",
            "leadgen_id": str(leadgen_id),
            "ad_id":      ad_id or meta_lead.get("ad_id", ""),
            "form_id":    form_id or meta_lead.get("form_id", ""),
            "page_id":    page_id,
        },
    }

    # -- Step 4: Trigger AutoNgage lead + AI call -----------------------------
    import time as _time

    # def _local_poll_and_post_process(lead_id: str, timeout_secs: int = 600, poll_interval: int = 15):
    #     """
    #     Self-contained session poller — does NOT import from cron.cron.

    #     Polls the DB contact_status table for a completed session, then calls
    #     post_session_process(session_id) to compute and store the disposition.

    #     Runs in the same background thread as _process_lead_async so we don't
    #     block the Flask server.
    #     """
    #     logger.info(
    #         "[WEBHOOK][POLL] Starting session poll for lead_id=%s (timeout=%ds)",
    #         lead_id, timeout_secs,
    #     )

    #     # Lazy imports — only needed when GCP creds are available
    #     try:
    #         from autocrm_db_helper import get_pg_connector
    #     except ImportError as e:
    #         logger.warning("[WEBHOOK][POLL] autocrm_db_helper unavailable (%s) — skipping poll.", e)
    #         return

    #     try:
    #         from conversation.lead_post_processing import post_session_process
    #     except ImportError as e:
    #         logger.warning("[WEBHOOK][POLL] post_session_process unavailable (%s) — skipping poll.", e)
    #         return

    #     start     = _time.time()
    #     processed = False

    #     while _time.time() - start < timeout_secs and not processed:
    #         try:
    #             with get_pg_connector() as pg:
    #                 sessions = list(pg.list("contact_status", {"lead_id": lead_id}))

    #                 for session in sessions:
    #                     status = session.get("provider_status")
    #                     session_id = session.get("message_id")

    #                     logger.info(
    #                         "[WEBHOOK][POLL] session_id=%s provider_status=%s",
    #                         session_id, status,
    #                     )

    #                     if status != "contacted":
    #                         continue

    #                     # Session complete — check transcript is ready
    #                     messages = list(pg.list("message", {"session_id": session_id}))
    #                     valid_messages = [
    #                         m for m in messages if m.get("message", "").strip()
    #                     ]

    #                     logger.info(
    #                         "[WEBHOOK][POLL] session_id=%s — %d valid transcript messages",
    #                         session_id, len(valid_messages),
    #                     )

    #                     if len(valid_messages) < 3:
    #                         logger.info(
    #                             "[WEBHOOK][POLL] Transcript not ready yet, waiting %ds...",
    #                             poll_interval,
    #                         )
    #                         break  # wait and re-poll

    #                     # Transcript is ready — run post_session_process
    #                     logger.info(
    #                         "[WEBHOOK][POLL] Running post_session_process for session_id=%s",
    #                         session_id,
    #                     )
    #                     try:
    #                         list(post_session_process(session_id=session_id))
    #                         logger.info(
    #                             "[WEBHOOK][POLL] post_session_process done for session_id=%s",
    #                             session_id,
    #                         )
    #                         processed = True
    #                     except Exception as psp_err:
    #                         logger.error(
    #                             "[WEBHOOK][POLL] post_session_process failed: %s", psp_err
    #                         )
    #                         processed = True  # don't retry on error
    #                     break

    #         except Exception as db_err:
    #             err_str = str(db_err).lower()

    #             # Permanent errors — wrong DB / missing tables. Stop immediately.
    #             if "does not exist" in err_str or "undefined table" in err_str or "undefinedtable" in err_str:
    #                 logger.warning(
    #                     "[WEBHOOK][POLL] DB table not found (%s). "
    #                     "Your GCP_SECRET points to the test DB which doesn't have session tables. "
    #                     "This is expected. "
    #                     "Disposition will be set by the server's cron automatically.",
    #                     db_err,
    #                 )
    #                 return  # Stop immediately — retrying won't help

    #             # Transient errors (connection timeout etc.) — log and retry
    #             logger.warning("[WEBHOOK][POLL] DB poll error (will retry): %s", db_err)

    #         if not processed:
    #             _time.sleep(poll_interval)

    #     if not processed:
    #         logger.warning(
    #             "[WEBHOOK][POLL] Timed out waiting for completed session for lead_id=%s "
    #             "(timeout=%ds). Disposition will be set by server cron.",
    #             lead_id, timeout_secs,
    #         )

    try:
        # Fix: crm_integration/crm_integration/gryd_worker.py is a local shim that
        # intercepts `from gryd_worker import gryd` in cron.py and then tries
        # `from crm_integration.gryd_worker import gryd` which doesn't exist.
        # Remove the shim directory from sys.path so the pip-installed gryd_worker
        # package is found directly instead.
        _shim_dir = os.path.join(_CRM_ROOT, "crm_integration")
        _patched  = _shim_dir in sys.path
        if _patched:
            sys.path.remove(_shim_dir)
        try:
            from crm_integration.crm_integration.cron import _trigger_audience_task
        finally:
            if _patched and _shim_dir not in sys.path:
                sys.path.insert(0, _shim_dir)  # restore after import

        logger.info(
            "[WEBHOOK] Triggering AutoNgage lead creation: phone=%s campaign=%s",
            autongage_lead.get("phone_number"),
            config.get("campaign_id"),
        )

        task_result = _trigger_audience_task(
            lead                  = autongage_lead,
            campaign_id           = config["campaign_id"],
            campaign_objective_id = config["campaign_objective_id"],
            campaign_type         = config.get("campaign_type", "pre-sales"),
            dealership_id         = config["dealership_id"],
            dealership_name       = config.get("dealership_name", ""),
        )
        logger.info("[WEBHOOK] _trigger_audience_task result: %s", task_result)

        # -- Step 5: Poll for session completion -> post_session_process -----
        lead_id = (task_result or {}).get("lead_id")
        if lead_id:
            logger.info(
                "[WEBHOOK] Call queued for lead_id=%s — starting session poll.",
                lead_id
            )
            if callable(_poll_and_post_process_session):
                # cron.cron._poll_and_post_process_session(lead_id, logger)
                _poll_and_post_process_session(lead_id, logger)
            else:
                logger.warning(
                    "[WEBHOOK] _poll_and_post_process_session not available — "
                    "session polling skipped. Disposition set by server cron."
                )

            # -- Step 6: Send disposition to Meta CAPI ---------------------------
            # Read the final disposition from the pre_sales_lead table and fire
            # a Conversions API event back to Meta.
            try:
                from autocrm_db_helper import get_pg_connector
                from crm_integration.crm_integration.meta_capi.tasks import push_capi_lead_event

                disposition = None
                with get_pg_connector() as _pg:
                    leads_rows = list(_pg.list("pre_sales_lead", {"pre_sales_lead_id": lead_id}))
                    if leads_rows:
                        disposition = leads_rows[0].get("disposition")

                if disposition:
                    logger.info(
                        "[WEBHOOK] Firing Meta CAPI event: phone=%s disposition=%s leadgen_id=%s",
                        autongage_lead.get("phone_number"), disposition, leadgen_id,
                    )
                    list(push_capi_lead_event(
                        phone_number      = autongage_lead.get("phone_number", ""),
                        disposition       = disposition,
                        email             = autongage_lead.get("email", ""),
                        name              = autongage_lead.get("person_name", ""),
                        facebook_lead_id  = int(leadgen_id) if leadgen_id else None,
                        lead_event_source = config.get("dealership_name", "DaveAI AutoCRM"),
                        logger            = logger,
                    ))
                    logger.info("[WEBHOOK] ✅ Meta CAPI event sent for lead_id=%s", lead_id)
                else:
                    logger.warning(
                        "[WEBHOOK] No disposition found for lead_id=%s — skipping Meta CAPI event.",
                        lead_id,
                    )
            except Exception as capi_err:
                logger.error("[WEBHOOK] Meta CAPI send failed: %s", capi_err, exc_info=True)

        else:
            logger.warning(
                "[WEBHOOK] No lead_id returned from _trigger_audience_task -- skipping poll."
            )

    except Exception:
        logger.exception(
            "[WEBHOOK] Failed to ingest leadgen_id=%s into AutoNgage", leadgen_id
        )
        _audit_log_lead({
            **meta_lead,
            "page_id":  page_id,
            "ingested": False,
            "reason":   "exception during ingestion -- see logs",
        })
        return

    # -- Step 7: Audit log successful ingestion -------------------------------
    _audit_log_lead({**meta_lead, "page_id": page_id, "ingested": True})


def _audit_log_lead(lead: dict):
    """Write lead to a local audit log file for debugging / traceability."""
    import time
    audit_dir = os.path.join(_CRM_ROOT, "audit_logs")
    os.makedirs(audit_dir, exist_ok=True)
    audit_path = os.path.join(audit_dir, "meta_leads_received.jsonl")

    entry = {
        "received_at": int(time.time()),
        **lead,
    }
    with open(audit_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    logger.debug("Audit log written: %s", audit_path)


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@app.route("/meta/sdk-test")
def meta_sdk_test():
    """
    Renders a static HTML page with the Meta JavaScript SDK initialized.
    Used for testing Meta App Events (logPageView, logEvent) and verifying
    the webhook payload sent by Meta.
    """
    return render_template("meta_sdk_test.html", app_id="1584438076681815")


@app.get("/meta/webhook")
def webhook_verify():
    """
    Meta Webhook Verification (GET).

    Meta sends this when you configure the Webhook URL in App Dashboard.
    We must reply with the hub.challenge value if verify_token matches.
    """
    mode         = request.args.get("hub.mode", "")
    challenge    = request.args.get("hub.challenge", "")
    verify_token = request.args.get("hub.verify_token", "")

    logger.info(
        "Webhook verification request: mode=%r verify_token=%r",
        mode, verify_token,
    )

    if mode == "subscribe" and verify_token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully.")
        return challenge, 200

    logger.warning(
        "Webhook verification FAILED. "
        "Expected verify_token=%r, got %r",
        VERIFY_TOKEN, verify_token,
    )
    abort(403)


@app.post("/meta/webhook")
def webhook_event():
    """
    Meta Webhook Event Notification (POST).

    Receives leadgen notifications. Each notification may contain
    multiple leads across multiple entries.

    IMPORTANT: Must return 200 OK immediately.
    If we return anything else / timeout, Meta retries every hour for 36 hours.
    """
    # -- Validate signature ---------------------------------------------------
    raw_body  = request.get_data()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not _verify_signature(raw_body, signature):
        logger.warning("Webhook signature validation FAILED -- rejecting request.")
        abort(403)

    # -- Parse payload --------------------------------------------------------
    try:
        payload = request.get_json(force=True, silent=True) or {}
    except Exception:
        logger.warning("Could not parse webhook payload as JSON.")
        return jsonify({"status": "error", "reason": "invalid json"}), 400

    logger.info("FULL WEBHOOK PAYLOAD:\n%s", json.dumps(payload, indent=2))

    object_type = payload.get("object", "")
    entries     = payload.get("entry", [])

    logger.info(
        "Webhook event received: object=%r entries=%d",
        object_type, len(entries),
    )

    # -- Handle Application events (e.g. App Events if Meta sends them) --------
    if object_type == "application":
        logger.info("Application webhook received! Logging all entries.")
        for entry in entries:
            logger.info("App entry: %s", json.dumps(entry, indent=2))
        return jsonify({"status": "ok"}), 200

    # -- Only handle Page leadgen events --------------------------------------
    if object_type != "page":
        logger.info("Ignoring non-page webhook object: %r", object_type)
        return jsonify({"status": "ignored"}), 200

    leads_queued = 0

    for entry in entries:
        page_id = str(entry.get("id", ""))
        changes = entry.get("changes", [])

        for change in changes:
            if change.get("field") != "leadgen":
                continue

            value      = change.get("value", {})
            leadgen_id = value.get("leadgen_id")
            form_id    = str(value.get("form_id", ""))
            ad_id      = str(value.get("ad_id") or value.get("adgroup_id", ""))

            if not leadgen_id:
                logger.warning("leadgen change received but no leadgen_id: %s", value)
                continue

            logger.info(
                "Queuing lead: leadgen_id=%s page_id=%s form_id=%s",
                leadgen_id, page_id, form_id,
            )

            # Process in a background thread so we return 200 immediately
            t = threading.Thread(
                target=_process_lead_async,
                args=(int(leadgen_id), page_id, form_id, ad_id),
                daemon=True,
            )
            t.start()
            leads_queued += 1

    return jsonify({"status": "ok", "leads_queued": leads_queued}), 200


@app.post("/meta/webhook/test-direct")
def webhook_test_direct():
    """
    LOCAL TESTING ONLY — Bypass Meta Graph API fetch entirely.

    POST a raw lead JSON directly to this endpoint. The server will skip
    the Graph API call and jump straight to campaign config lookup → 
    _trigger_audience_task → poll.

    Example body:
        {
            "name":         "Priyanshul",
            "phone_number": "+917696770402",
            "email":        "",
            "page_id":      "1774145496137418"
        }
    """
    data = request.get_json(force=True) or {}

    # Build a meta_lead dict matching what Graph API would return
    meta_lead = {
        "name":             data.get("name", "Test User"),
        "phone_number":     data.get("phone_number", ""),
        "email":            data.get("email", ""),
        "car_model":        data.get("car_model", ""),
        "vehicle_category": data.get("vehicle_category", "Passenger Vehicle"),
    }
    page_id  = data.get("page_id", os.environ.get("META_PAGE_ID", ""))

    if not meta_lead["phone_number"]:
        return jsonify({"status": "error", "reason": "phone_number is required"}), 400

    logger.info(
        "[WEBHOOK/test-direct] Injecting hardcoded lead: name=%r phone=%r page_id=%s",
        meta_lead["name"], meta_lead["phone_number"], page_id,
    )

    # Reuse _process_lead_async logic — but skip Graph API fetch
    # Build autongage_lead the same way Step 3 does
    autongage_lead = {
        "person_name":      meta_lead["name"],
        "phone_number":     meta_lead["phone_number"],
        "email":            meta_lead["email"],
        "vehicle_model":    meta_lead.get("car_model", ""),
        "vehicle_category": meta_lead.get("vehicle_category", "Passenger Vehicle"),
        "external_source_data": {
            "source":   "meta_test_direct",
            "page_id":  page_id,
        },
    }

    # Run in background thread (same as normal flow)
    import threading
    def _run():
        try:
            cfg = _get_webhook_config(page_id)
            if not cfg:
                logger.warning("[WEBHOOK/test-direct] No config for page_id=%s", page_id)
                return

            logger.info(
                "[WEBHOOK/test-direct] Config resolved: dealership=%s campaign=%s",
                cfg.get("dealership_id"), cfg.get("campaign_id"),
            )

            from crm_integration.crm_integration.cron import _trigger_audience_task
            result = _trigger_audience_task(
                lead=autongage_lead,
                campaign_id=cfg["campaign_id"],
                campaign_objective_id=cfg.get("campaign_objective_id", ""),
                campaign_type=cfg.get("campaign_type", "pre-sales"),
                dealership_id=cfg["dealership_id"],
                dealership_name=cfg.get("dealership_name", ""),
                logger=logger,
            )
            lead_id = (result or {}).get("lead_id")
            logger.info("[WEBHOOK/test-direct] lead_id=%s", lead_id)

            if lead_id and _poll_and_post_process_session:
                _poll_and_post_process_session(lead_id, logger)

                # -- Step 6: Send disposition to Meta CAPI ---------------------------
                try:
                    from autocrm_db_helper import get_pg_connector
                    from crm_integration.crm_integration.meta_capi.tasks import push_capi_lead_event

                    disposition = None
                    with get_pg_connector() as _pg:
                        leads_rows = list(_pg.list("pre_sales_lead", {"pre_sales_lead_id": lead_id}))
                        if leads_rows:
                            disposition = leads_rows[0].get("disposition")

                    if disposition:
                        logger.info(
                            "[WEBHOOK/test-direct] Firing Meta CAPI event: phone=%s disposition=%s",
                            autongage_lead.get("phone_number"), disposition
                        )
                        list(push_capi_lead_event(
                            phone_number      = autongage_lead.get("phone_number", ""),
                            disposition       = disposition,
                            email             = autongage_lead.get("email", ""),
                            name              = autongage_lead.get("person_name", ""),
                            facebook_lead_id  = None, # No real leadgen_id in test-direct
                            lead_event_source = cfg.get("dealership_name", "DaveAI AutoCRM"),
                            logger            = logger,
                        ))
                        logger.info("[WEBHOOK/test-direct] ✅ Meta CAPI event sent for lead_id=%s", lead_id)
                    else:
                        logger.warning(
                            "[WEBHOOK/test-direct] No disposition found for lead_id=%s — skipping Meta CAPI event.",
                            lead_id,
                        )
                except Exception as capi_err:
                    logger.error("[WEBHOOK/test-direct] Meta CAPI send failed: %s", capi_err, exc_info=True)

        except Exception:
            logger.exception("[WEBHOOK/test-direct] Error processing hardcoded lead")

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return jsonify({
        "status":   "ok",
        "message":  "hardcoded lead queued for processing",
        "name":     meta_lead["name"],
        "phone":    meta_lead["phone_number"],
        "page_id":  page_id,
    }), 200


@app.get("/meta/webhook/health")
def health():
    """Simple health check endpoint."""
    return jsonify({
        "status":         "ok",
        "app_secret_set": bool(APP_SECRET),
        "page_token_set": bool(PAGE_ACCESS_TOKEN),
        "verify_token":   VERIFY_TOKEN[:6] + "...",  # partial, for safety
    }), 200


# ------------------------------------------------------------------------------
# Run
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Meta Webhook Server starting on port %d", WEBHOOK_PORT)
    logger.info("Verify token : %s", VERIFY_TOKEN)
    logger.info("App secret   : %s", "set" if APP_SECRET else "NOT SET")
    logger.info("Page token   : %s", "set" if PAGE_ACCESS_TOKEN else "NOT SET")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Webhook URL to register in Meta App Dashboard:")
    logger.info("  https://<your-ngrok-or-server-domain>/meta/webhook")
    logger.info("")
    logger.info("Health check: http://localhost:%d/meta/webhook/health", WEBHOOK_PORT)
    logger.info("")

    app.run(host="0.0.0.0", port=WEBHOOK_PORT, debug=False)
