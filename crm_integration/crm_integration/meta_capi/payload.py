"""
Meta Conversions API — Payload Builder
=======================================
Builds a spec-compliant server-event payload for the
Conversion Leads integration endpoint:

  POST https://graph.facebook.com/{API_VERSION}/{PIXEL_ID}/events

Required top-level keys (per Meta docs):
  - event_name      : string — the CRM stage name (e.g. "Lead", "MQL", "Converted")
  - event_time      : int    — Unix timestamp (seconds) of the stage change
  - action_source   : "system_generated"
  - user_data       : object — must include at least one customer identifier
  - custom_data     : object — must include lead_event_source + event_source="crm"

Hashing: Meta requires SHA-256 hashing of PII (email, phone).
         The helper `hash_pii()` handles this normalisation + hashing.

References:
  https://developers.facebook.com/documentation/ads-commerce/conversions-api/conversion-leads-integration/payload-specification
  https://developers.facebook.com/documentation/ads-commerce/conversions-api/conversion-leads-integration/crm-integration/3-implementing-the-crm-integration
"""

import hashlib
import time
import re
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# PII Hashing helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_email(email: str) -> str:
    """Lowercase, strip whitespace — Meta normalisation rules."""
    return email.strip().lower()


def _normalise_phone(phone: str) -> str:
    """
    Strip everything except digits.
    E.g. "+91-98765 43210" → "919876543210"
    Meta expects E.164 digits only, no +.
    """
    digits = re.sub(r"\D", "", phone)
    return digits


def hash_pii(value: str, pii_type: str = "generic") -> str:
    """
    Normalise and SHA-256 hash a PII value.

    Args:
        value    : Raw PII string (email, phone, name, etc.)
        pii_type : "email" | "phone" | "generic"
                   Controls the normalisation applied before hashing.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    if pii_type == "email":
        value = _normalise_email(value)
    elif pii_type == "phone":
        value = _normalise_phone(value)
    else:
        value = value.strip().lower()

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Payload builder
# ─────────────────────────────────────────────────────────────────────────────

def build_lead_event_payload(
    *,
    event_name: str,
    lead_event_source: str,
    lead_id: Optional[int] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    country: Optional[str] = None,
    event_time: Optional[int] = None,
    test_event_code: Optional[str] = None,
) -> dict:
    """
    Build a single Conversion Leads server-event payload dict.

    Usage example:
        payload = build_lead_event_payload(
            event_name="Lead",
            lead_event_source="DaveAI CRM",
            lead_id=1234567890123456,
            email="user@example.com",
            phone="+919876543210",
        )

    Args:
        event_name         : CRM stage (e.g. "Lead", "MQL", "Contacted", "Converted").
        lead_event_source  : Human-readable name of your CRM, e.g. "DaveAI AutoCRM".
        lead_id            : Facebook-generated lead ID (15-17 digit int).  HIGHEST PRIORITY.
        email              : Raw (un-hashed) email — will be hashed internally.
        phone              : Raw phone number — will be normalised + hashed.
        first_name         : Raw first name — will be hashed.
        last_name          : Raw last name — will be hashed.
        city               : Raw city — will be hashed.
        state              : Raw state/province — will be hashed.
        zip_code           : Raw zip — will be hashed.
        country            : ISO 2-letter country code, lowercase, hashed.
        event_time         : Unix timestamp; defaults to now().
        test_event_code    : Optional — pass Meta's test event code during QA.

    Returns:
        dict: A single event object ready to be placed inside {"data": [<here>]}.

    Raises:
        ValueError: If no customer information parameter is provided.
    """
    # Validate: at least one customer identifier must be present
    has_identifier = any([lead_id, email, phone, first_name, last_name])
    if not has_identifier:
        raise ValueError(
            "build_lead_event_payload: at least one customer information "
            "parameter (lead_id, email, phone, first/last name) is required."
        )

    # ── user_data ─────────────────────────────────────────────────────────────
    user_data: dict = {}

    if lead_id is not None:
        # Must be integer per Meta spec
        user_data["lead_id"] = int(lead_id)

    if email:
        user_data["em"] = [hash_pii(email, pii_type="email")]

    if phone:
        user_data["ph"] = [hash_pii(phone, pii_type="phone")]

    if first_name:
        user_data["fn"] = [hash_pii(first_name)]

    if last_name:
        user_data["ln"] = [hash_pii(last_name)]

    if city:
        user_data["ct"] = [hash_pii(city)]

    if state:
        user_data["st"] = [hash_pii(state)]

    if zip_code:
        user_data["zp"] = [hash_pii(zip_code)]

    if country:
        user_data["country"] = [hash_pii(country.lower())]

    # ── Assemble event ─────────────────────────────────────────────────────────
    event: dict = {
        "event_name": event_name,
        "event_time": event_time or int(time.time()),
        "action_source": "system_generated",
        "user_data": user_data,
        "custom_data": {
            "lead_event_source": lead_event_source,
            "event_source": "crm",
        },
    }

    if test_event_code:
        event["test_event_code"] = test_event_code

    return event


def wrap_events_payload(events: list, test_event_code: Optional[str] = None) -> dict:
    """
    Wrap a list of event dicts into the top-level {"data": [...]} structure
    expected by the Meta CAPI endpoint.

    Args:
        events          : List of event dicts from build_lead_event_payload().
        test_event_code : If provided, appends to the wrapper (used for test mode).

    Returns:
        dict: {"data": [...], "test_event_code": "..."}
    """
    wrapper: dict = {"data": events}
    if test_event_code:
        wrapper["test_event_code"] = test_event_code
    return wrapper
