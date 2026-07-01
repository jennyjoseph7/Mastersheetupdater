"""
Meta CAPI — CRM Lead Mapper
============================
Translates the internal lead dictionary (as returned by
GoogleDocsCRM.read_leads_from_sheet() or the `update_lead_in_sheet` kwargs)
into the keyword arguments accepted by `build_lead_event_payload()`.

Internal lead dict shape (from GoogleDocsCRM / autoengage_crm_worker):
    {
        "phone_number"     : "9876543210",
        "name"             : "Ravi Kumar",
        "email"            : "ravi@example.com",
        "disposition"      : "contacted",        # or "not_interested", "converted", etc.
        "lead_summary"     : "...",
        "sentiment"        : "positive",
        "facebook_lead_id" : 1234567890123456,   # optional — if stored in sheet
        "status"           : "QUEUED",
        ...
    }

Disposition → CAPI event_name mapping:
    We map your internal CRM disposition values to meaningful CAPI stage names.
    Meta uses event_name to model the funnel, so consistent naming matters.
    Edit DISPOSITION_MAP to match YOUR dealership's disposition vocabulary.

Stage lifecycle order (must be sent in chronological order per Meta docs):
    1. "Lead"           — initial raw lead from FB Lead Ad
    2. "Contacted"      — AI/agent made first contact (call placed)
    3. "MQL"            — Marketing Qualified Lead (positive interest signalled)
    4. "SQL"            — Sales Qualified Lead (appointment / test drive booked)
    5. "Converted"      — Deal closed / purchase confirmed

References:
  https://developers.facebook.com/documentation/ads-commerce/conversions-api/conversion-leads-integration/payload-specification
"""

import logging
import time
from typing import Optional

from .payload import build_lead_event_payload

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Disposition → CAPI stage mapping
# Extend / edit this map to match your actual CRM disposition values.
# ─────────────────────────────────────────────────────────────────────────────

DISPOSITION_MAP: dict[str, str] = {
    # ── Raw / initial ──────────────────────────────────────────────────────
    "new":              "Lead",
    "queued":           "Lead",
    "initiated":        "Lead",

    # ── Contact made ───────────────────────────────────────────────────────
    "contacted":        "Contacted",
    "called":           "Contacted",
    "connected":        "Contacted",
    "picked_up":        "Contacted",

    # ── Qualified ──────────────────────────────────────────────────────────
    "interested":       "MQL",
    "engaged":          "MQL",
    "follow_up":        "MQL",
    "callback_requested": "MQL",

    # ── Sales-ready ────────────────────────────────────────────────────────
    "appointment_booked": "SQL",
    "test_drive_booked":  "SQL",
    "demo_scheduled":     "SQL",
    "negotiating":        "SQL",

    # ── Closed / won ───────────────────────────────────────────────────────
    "converted":        "Converted",
    "booked":           "Converted",
    "purchased":        "Converted",
    "deal_closed":      "Converted",

    # ── Negative ───────────────────────────────────────────────────────────
    "not_interested":   "Not Interested",
    "dnc":              "Do Not Call",
    "invalid":          "Invalid Lead",
    "no_answer":        "Contacted",   # still counts as a contact attempt
    "voicemail":        "Contacted",
}

DEFAULT_EVENT_NAME = "Lead"  # Fallback if disposition not found in map


class CRMLeadToCapiMapper:
    """
    Converts an internal CRM lead dict into a CAPI server-event payload dict.

    Usage:
        mapper = CRMLeadToCapiMapper(lead_event_source="DaveAI AutoCRM")
        event  = mapper.map(lead_dict)
        # → ready to pass to MetaCAPIClient.send_events([event])

    Per-dealership config:
        Set `lead_event_source` to a human-readable CRM name for that
        dealership, e.g. "Ambal Hyundai AutoCRM".
    """

    def __init__(
        self,
        lead_event_source: str = "DaveAI AutoCRM",
        disposition_map: Optional[dict] = None,
        default_event_name: str = DEFAULT_EVENT_NAME,
        test_event_code: Optional[str] = None,
    ):
        self.lead_event_source = lead_event_source
        self.disposition_map = disposition_map or DISPOSITION_MAP
        self.default_event_name = default_event_name
        self.test_event_code = test_event_code

    # ── Public ─────────────────────────────────────────────────────────────────

    def map(self, lead: dict, event_time: Optional[int] = None) -> dict:
        """
        Convert an internal lead dict to a CAPI event payload dict.

        Args:
            lead        : Internal lead dict (from sheet / post_session kwargs).
            event_time  : Unix timestamp; defaults to now(). Pass the actual
                          stage-change time if available for accurate attribution.

        Returns:
            dict: A single CAPI server-event ready for MetaCAPIClient.send_events().
        """
        disposition = str(lead.get("disposition", "new")).strip().lower()
        event_name = self.disposition_map.get(disposition, self.default_event_name)

        logger.debug(
            "CRMLeadToCapiMapper: disposition=%r → event_name=%r",
            disposition, event_name,
        )

        # ── Customer identifiers ───────────────────────────────────────────
        lead_id = self._extract_lead_id(lead)
        phone   = self._extract_phone(lead)
        email   = lead.get("email") or None
        name    = lead.get("name") or ""
        first_name, last_name = self._split_name(name)

        return build_lead_event_payload(
            event_name=event_name,
            lead_event_source=self.lead_event_source,
            lead_id=lead_id,
            email=email,
            phone=phone,
            first_name=first_name or None,
            last_name=last_name or None,
            event_time=event_time or int(time.time()),
            test_event_code=self.test_event_code,
        )

    def map_many(self, leads: list, event_time: Optional[int] = None) -> list:
        """
        Map a list of lead dicts to a list of CAPI event dicts.
        Skips and logs any leads that fail mapping (no PII available).
        """
        events = []
        for lead in leads:
            try:
                events.append(self.map(lead, event_time=event_time))
            except ValueError as exc:
                logger.warning(
                    "CRMLeadToCapiMapper: skipping lead %r — %s",
                    lead.get("phone_number", "?"),
                    exc,
                )
        return events

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _extract_lead_id(self, lead: dict) -> Optional[int]:
        """
        Try common field names where the Facebook Lead ID might be stored.
        Returns None if not found or not a valid integer.
        """
        for key in ("facebook_lead_id", "fb_lead_id", "lead_id", "leadgen_id"):
            val = lead.get(key)
            if val:
                try:
                    return int(val)
                except (TypeError, ValueError):
                    continue
        return None

    def _extract_phone(self, lead: dict) -> Optional[str]:
        for key in ("phone_number", "mobile_number", "phone", "mobile"):
            val = lead.get(key)
            if val:
                return str(val).strip()
        return None

    @staticmethod
    def _split_name(full_name: str):
        """Split 'First Last' into (first, last). Returns ('', '') on empty."""
        parts = full_name.strip().split(maxsplit=1)
        if len(parts) == 2:
            return parts[0], parts[1]
        elif len(parts) == 1:
            return parts[0], ""
        return "", ""
