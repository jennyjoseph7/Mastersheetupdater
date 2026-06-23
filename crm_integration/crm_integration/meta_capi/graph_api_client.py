"""
Meta Graph API Client — Lead Data Fetcher
==========================================
Fetches full lead details from Meta's Graph API using a `leadgen_id`
received from the Webhook notification.

Flow:
  1. Webhook fires → we receive leadgen_id (just a number)
  2. This client calls GET /v21.0/{leadgen_id}?fields=id,created_time,field_data
  3. We get back the actual form data (name, phone, email, etc.)
  4. We normalize it into our internal lead dict format

Graph API endpoint:
  GET https://graph.facebook.com/{API_VERSION}/{leadgen_id}
      ?access_token={PAGE_ACCESS_TOKEN}
      &fields=id,created_time,ad_id,form_id,field_data

Required permissions on the Meta App:
  - leads_retrieval
  - pages_manage_metadata
  - pages_show_list
  - pages_read_engagement
  - ads_management

Access Token type:
  - Page Access Token (long-lived, generated from a System User
    who has ADVERTISE permission on the Page)

References:
  https://developers.facebook.com/docs/marketing-api/guides/lead-ads/retrieving/
  https://developers.facebook.com/docs/graph-api/webhooks/getting-started/webhooks-for-leadgen/
"""

import os
import logging
import time
import requests
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

GRAPH_API_VERSION = os.environ.get("META_CAPI_API_VERSION", "v21.0")
GRAPH_BASE_URL    = "https://graph.facebook.com"

# Fields to fetch from the Graph API for each lead
LEAD_FIELDS = "id,created_time,ad_id,form_id,field_data"

MAX_RETRIES         = 3
BASE_BACKOFF_SECS   = 2


# ─────────────────────────────────────────────────────────────────────────────
# Normalizer — field_data list → flat dict
# ─────────────────────────────────────────────────────────────────────────────

# Maps Meta form field names → our internal key names.
# Extend this dict to cover each dealership's custom field names.
FIELD_NAME_MAP: dict[str, str] = {
    # ── Standard Meta Lead Ad field names ──────────────────────────────────
    "full_name":         "name",
    "first_name":        "first_name",
    "last_name":         "last_name",
    "email":             "email",
    "phone_number":      "phone_number",
    "phone":             "phone_number",
    "mobile_number":     "phone_number",

    # ── Automotive / dealership custom fields (common) ─────────────────────
    "car_model":         "car_model",
    "vehicle_model":     "car_model",
    "model_of_interest": "car_model",
    "city":              "city",
    "state":             "state",
    "zip_code":          "zip_code",
    "pincode":           "zip_code",
    "comments":          "comments",
    "message":           "comments",
    "budget":            "budget",
}


def normalize_field_data(field_data: list) -> dict:
    """
    Convert Meta's field_data list into a flat dict using FIELD_NAME_MAP.

    Meta returns:
        [
            {"name": "full_name",    "values": ["Ravi Kumar"]},
            {"name": "phone_number", "values": ["9876543210"]},
            ...
        ]

    We return:
        {
            "name":         "Ravi Kumar",
            "phone_number": "9876543210",
            ...
        }

    Unknown field names are kept as-is (snake_cased).
    """
    result = {}
    for field in field_data:
        raw_name = field.get("name", "").strip().lower()
        values   = field.get("values", [])
        value    = values[0] if values else None

        # Map to our internal name, or keep original
        internal_name = FIELD_NAME_MAP.get(raw_name, raw_name.replace(" ", "_"))
        result[internal_name] = value

    # ── Build "name" from first_name + last_name if full_name missing ──────
    if "name" not in result:
        first = result.pop("first_name", "")
        last  = result.pop("last_name", "")
        if first or last:
            result["name"] = f"{first} {last}".strip()

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Graph API Client
# ─────────────────────────────────────────────────────────────────────────────

class MetaGraphAPIClient:
    """
    Fetches full lead data from Meta Graph API using a leadgen_id.

    Usage:
        client = MetaGraphAPIClient.from_env()
        lead   = client.get_lead(leadgen_id=123123123123)
        # → {"name": "Ravi Kumar", "phone_number": "9876543210", ...}

    Environment variables:
        META_PAGE_ACCESS_TOKEN   : Long-lived Page access token (required).
        META_CAPI_API_VERSION    : Graph API version (default: v21.0).
    """

    def __init__(self, page_access_token: str, api_version: str = GRAPH_API_VERSION):
        if not page_access_token:
            raise ValueError(
                "MetaGraphAPIClient: META_PAGE_ACCESS_TOKEN is required. "
                "Add it to crm_integration/local.sh."
            )
        self.page_access_token = page_access_token
        self.api_version       = api_version

    @classmethod
    def from_env(cls) -> "MetaGraphAPIClient":
        """Instantiate from META_PAGE_ACCESS_TOKEN environment variable."""
        token = os.environ.get("META_PAGE_ACCESS_TOKEN", "")
        version = os.environ.get("META_CAPI_API_VERSION", GRAPH_API_VERSION)
        return cls(page_access_token=token, api_version=version)

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_lead(self, leadgen_id: int) -> dict:
        """
        Fetch and normalize a single lead from Meta Graph API.

        Args:
            leadgen_id : The Facebook-generated lead ID from the webhook payload.

        Returns:
            dict: Normalized internal lead dict, e.g.:
                {
                    "facebook_lead_id": 123123123123,
                    "name":             "Ravi Kumar",
                    "phone_number":     "9876543210",
                    "email":            "ravi@example.com",
                    "car_model":        "Hyundai Creta",
                    "created_time":     "2024-06-01T10:00:00+0000",
                    "ad_id":            "444555666",
                    "form_id":          "111222333",
                    "status":           "NEW",
                }

        Raises:
            MetaGraphAPIError  : On non-retryable API error.
            ValueError         : If leadgen_id is invalid.
        """
        if not leadgen_id:
            raise ValueError("get_lead: leadgen_id is required.")

        url = f"{GRAPH_BASE_URL}/{self.api_version}/{leadgen_id}"
        params = {
            "access_token": self.page_access_token,
            "fields":       LEAD_FIELDS,
        }

        raw = self._get_with_retry(url, params)

        # ── Parse raw response ─────────────────────────────────────────────
        field_data    = raw.get("field_data", [])
        normalized    = normalize_field_data(field_data)

        lead = {
            "facebook_lead_id": int(raw.get("id", leadgen_id)),
            "created_time":     raw.get("created_time"),
            "ad_id":            raw.get("ad_id") or raw.get("adgroup_id"),
            "form_id":          raw.get("form_id"),
            "status":           "NEW",     # Always start as NEW in AutoNgage
            **normalized,
        }

        logger.info(
            "MetaGraphAPIClient: fetched lead %s — name=%r phone=%r",
            leadgen_id,
            lead.get("name"),
            lead.get("phone_number"),
        )
        return lead

    # ── Internal ───────────────────────────────────────────────────────────────

    def _get_with_retry(self, url: str, params: dict) -> dict:
        """GET with exponential backoff retry on rate limit (HTTP 429)."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(url, params=params, timeout=15)
            except requests.RequestException as exc:
                if attempt >= MAX_RETRIES:
                    raise MetaGraphAPIError(
                        f"Network error after {attempt} attempts: {exc}"
                    ) from exc
                time.sleep(BASE_BACKOFF_SECS ** attempt)
                continue

            if resp.status_code == 200:
                return resp.json()

            try:
                body     = resp.json()
                fb_error = body.get("error", {})
                code     = fb_error.get("code", 0)
                message  = fb_error.get("message", resp.text)
            except Exception:
                fb_error = {}
                code     = 0
                message  = resp.text

            # Rate limit
            if resp.status_code == 429 or code == 80004:
                if attempt < MAX_RETRIES:
                    wait = BASE_BACKOFF_SECS ** attempt
                    logger.warning(
                        "MetaGraphAPIClient: rate limited — retry %d/%d in %ds",
                        attempt, MAX_RETRIES, wait,
                    )
                    time.sleep(wait)
                    continue
                raise MetaGraphAPIError(
                    f"Rate limit after {MAX_RETRIES} retries.", code=429
                )

            # Token expired / permission denied
            if code in (190, 200, 210, 273):
                raise MetaGraphAPIError(
                    f"Token/permission error (FB code {code}): {message}",
                    code=resp.status_code,
                )

            raise MetaGraphAPIError(
                f"Graph API error {resp.status_code}: {message}",
                code=resp.status_code,
            )

        raise MetaGraphAPIError("Exhausted retries.")


class MetaGraphAPIError(Exception):
    """Raised on unrecoverable Meta Graph API errors."""
    def __init__(self, message: str, code: int = 0):
        super().__init__(message)
        self.code = code
