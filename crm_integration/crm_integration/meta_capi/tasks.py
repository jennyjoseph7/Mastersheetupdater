"""
Meta CAPI Gryd Tasks
======================
These tasks plug into the existing autoengage_crm_worker.py via the
@gryd.is_a_task decorator pattern, so they can be:
  - Triggered directly from cron.py via gryd.create_async_task(...)
  - Triggered automatically from post_session_process / update_lead_in_sheet
  - Queued to SQS and processed by the worker

Available tasks:
  push_capi_lead_event    — send a single lead event to Meta CAPI
  push_capi_lead_events   — send a batch of leads to Meta CAPI

How to call from cron.py / post-session:
    gryd.create_async_task(
        "push_capi_lead_event",
        AUTOCRM_CRM_UPDATE_SERVICE_NAME,
        kwargs={
            "phone_number"     : "9876543210",
            "disposition"      : "contacted",
            "email"            : "user@example.com",
            "name"             : "Ravi Kumar",
            "facebook_lead_id" : 1234567890123456,   # if stored in sheet
            "lead_event_source": "DaveAI AutoCRM",   # dealership-specific
        }
    )
"""

import os
import logging

logger = logging.getLogger(__name__)

# ── Gryd bootstrap (same pattern as autoengage_crm_worker.py) ─────────────────
import sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from gryd_worker import gryd
from config import AUTOCRM_CRM_UPDATE_SERVICE_NAME

gryd.SERVICE = AUTOCRM_CRM_UPDATE_SERVICE_NAME
gryd.set_queue_manager()

# ── CAPI imports ───────────────────────────────────────────────────────────────
from crm_integration.crm_integration.meta_capi.client import (
    MetaCAPIClient,
    MetaCAPIError,
    MetaCAPIRateLimitError,
)
from crm_integration.crm_integration.meta_capi.mapper import CRMLeadToCapiMapper


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_client() -> MetaCAPIClient:
    """
    Build MetaCAPIClient from environment variables.
    Raises RuntimeError if META_PIXEL_ID or META_CAPI_ACCESS_TOKEN are not set.
    """
    pixel_id = os.environ.get("META_PIXEL_ID", "")
    access_token = os.environ.get("META_CAPI_ACCESS_TOKEN", "")

    if not pixel_id or not access_token:
        raise RuntimeError(
            "META_PIXEL_ID and META_CAPI_ACCESS_TOKEN must be set in environment. "
            "Add them to crm_integration/local.sh or your secrets manager."
        )

    return MetaCAPIClient.from_env()


# ─────────────────────────────────────────────────────────────────────────────
# Task: push_capi_lead_event
# ─────────────────────────────────────────────────────────────────────────────

@gryd.is_a_task(
    logger_param="logger",
    job_param="job",
)
def push_capi_lead_event(
    phone_number: str,
    disposition: str,
    email: str = None,
    name: str = None,
    facebook_lead_id: int = None,
    lead_event_source: str = "DaveAI AutoCRM",
    event_time: int = None,
    logger=None,
    job=None,
    **kwargs,
):
    """
    Send a single CRM lead conversion event to Meta CAPI.

    Args:
        phone_number       : Lead's phone number (raw — will be hashed).
        disposition        : CRM disposition string (e.g. "contacted", "converted").
        email              : Lead's email (raw — will be hashed). Optional.
        name               : Lead's full name (raw — will be hashed). Optional.
        facebook_lead_id   : The Meta-generated lead ID (15-17 digit int). Highest priority.
        lead_event_source  : Name of this CRM (shown in Meta Events Manager).
        event_time         : Unix timestamp of the stage change. Defaults to now().
        **kwargs           : Any extra lead fields (ignored, but safe to pass).

    Returns:
        dict: {"status": "ok", "events_received": N}  or  {"status": "error", "reason": ...}
    """
    _logger = logger or logging.getLogger(__name__)

    try:
        client = _get_client()
    except RuntimeError as exc:
        _logger.error("push_capi_lead_event: CAPI not configured — %s", exc)
        return {"status": "skipped", "reason": str(exc)}

    # Build internal lead dict from task parameters
    lead_dict = {
        "phone_number":     phone_number,
        "disposition":      disposition,
        "email":            email,
        "name":             name or "",
        "facebook_lead_id": facebook_lead_id,
    }

    mapper = CRMLeadToCapiMapper(lead_event_source=lead_event_source)
    try:
        event = mapper.map(lead_dict, event_time=event_time)
    except ValueError as exc:
        _logger.warning("push_capi_lead_event: Cannot map lead — %s", exc)
        return {"status": "error", "reason": str(exc)}

    try:
        response = client.send_single_event(event)
        _logger.info(
            "push_capi_lead_event: ✓ sent to Meta. phone=%s disposition=%s events_received=%s",
            phone_number, disposition, response.get("events_received"),
        )
        return {"status": "ok", **response}

    except MetaCAPIRateLimitError as exc:
        _logger.error("push_capi_lead_event: Rate limit — %s", exc)
        return {"status": "rate_limited", "reason": str(exc)}

    except MetaCAPIError as exc:
        _logger.error("push_capi_lead_event: Meta error — %s", exc)
        return {"status": "error", "reason": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Task: push_capi_lead_events  (batch)
# ─────────────────────────────────────────────────────────────────────────────

@gryd.is_a_task(
    logger_param="logger",
    job_param="job",
)
def push_capi_lead_events(
    leads: list,
    lead_event_source: str = "DaveAI AutoCRM",
    event_time: int = None,
    logger=None,
    job=None,
):
    """
    Send a batch of CRM leads to Meta CAPI in a single API call.

    Args:
        leads              : List of lead dicts, each with at minimum
                             {"phone_number": ..., "disposition": ...}.
        lead_event_source  : Name of this CRM.
        event_time         : Shared Unix timestamp for all events in the batch.

    Returns:
        dict: {"status": "ok", "sent": N, "skipped": M, "events_received": K}
    """
    _logger = logger or logging.getLogger(__name__)

    try:
        client = _get_client()
    except RuntimeError as exc:
        _logger.error("push_capi_lead_events: CAPI not configured — %s", exc)
        return {"status": "skipped", "reason": str(exc)}

    mapper = CRMLeadToCapiMapper(lead_event_source=lead_event_source)
    events = mapper.map_many(leads, event_time=event_time)

    if not events:
        _logger.warning("push_capi_lead_events: No mappable leads in batch of %d.", len(leads))
        return {"status": "ok", "sent": 0, "skipped": len(leads), "events_received": 0}

    try:
        response = client.send_events(events)
        events_received = response.get("events_received", len(events))
        _logger.info(
            "push_capi_lead_events: ✓ batch of %d → Meta received %d events.",
            len(events), events_received,
        )
        return {
            "status": "ok",
            "sent": len(events),
            "skipped": len(leads) - len(events),
            "events_received": events_received,
        }

    except MetaCAPIRateLimitError as exc:
        _logger.error("push_capi_lead_events: Rate limit — %s", exc)
        return {"status": "rate_limited", "reason": str(exc), "sent": 0}

    except MetaCAPIError as exc:
        _logger.error("push_capi_lead_events: Meta error — %s", exc)
        return {"status": "error", "reason": str(exc), "sent": 0}
