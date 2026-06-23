"""
Meta Lead Ads Integration — Testing Module
============================================
Extends the existing MetaAdsManager authentication foundation to add:

  1. get_all_campaigns()       — list campaigns from the Ad Account
  2. get_campaign_ads()        — list ads within a campaign
  3. get_leads()               — retrieve leadgen IDs from an ad/form
  4. get_lead_detail()         — fetch full lead data via Graph API
  5. send_conversion_event()   — push CRM outcome back to Meta CAPI

This module is for TESTING the full Meta Lead Ads pipeline before the
production webhook-based ingestion flow is wired in.

Current polling flow (this file):
    Campaigns → Ads → Leads → Graph API → Normalized Lead Data

Future production flow (webhook_server.py):
    Webhook → leadgen_id → Graph API → Normalized Lead Data

The lead-fetching logic (get_lead_detail + _normalize_field_data) is
shared by both flows so the webhook can reuse it without duplication.

Usage:
    from cohorts_new.ad_platforms.meta_lead_ads import MetaLeadAdsManager

    mgr = MetaLeadAdsManager(
        app_id       = "...",
        app_secret   = "...",
        access_token = "...",   # Page Access Token with leads_retrieval
        ad_account_id= "act_...",
        page_id      = "...",
    )

    campaigns = mgr.get_all_campaigns()
    ads       = mgr.get_campaign_ads(campaign_id="120245319830110664")
    leads     = mgr.get_leads(ad_id="120245319830110664")
    detail    = mgr.get_lead_detail(leadgen_id=123456789)
    mgr.send_conversion_event(leadgen_id=123456789, stage="Contacted")

Required Meta App permissions:
    leads_retrieval, pages_manage_metadata, pages_show_list,
    pages_read_engagement, ads_management
"""

from conversation import yield_response
import os
import sys
import time
import hashlib
import logging
import requests
from typing import Optional, List, Dict
import json

# ── Path bootstrap (mirrors meta_ads_manager.py pattern) ────────────────────
_SELF_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT   = os.path.abspath(os.path.join(_SELF_DIR, ".."))
_ROOT     = os.path.abspath(os.path.join(_PARENT, ".."))
for _p in (_PARENT, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Reuse existing MetaAdsManager as the auth base ──────────────────────────
from cohorts_new.ad_platforms.meta_ads_manager import MetaAdsManager

try:
    from facebook_business.adobjects.lead import Lead
    from facebook_business.adobjects.ad import Ad
    from facebook_business.adobjects.adset import AdSet
    from facebook_business.adobjects.campaign import Campaign
    from facebook_business.adobjects.leadgenform import LeadgenForm
except ImportError:
    raise ImportError(
        "facebook_business package required. "
        "Run: pip install facebook_business"
    )

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

GRAPH_BASE_URL = "https://graph.facebook.com"
# adgroup_id was removed in API v21.0; use ad_id instead
LEAD_FIELDS    = "id,created_time,ad_id,form_id,field_data"

# Maps Meta Lead Ad form field names → internal field names.
# Add dealership-specific aliases here as needed.
FIELD_NAME_MAP: Dict[str, str] = {
    "full_name":         "name",
    "first_name":        "first_name",
    "last_name":         "last_name",
    "email":             "email",
    "phone_number":      "phone_number",
    "phone":             "phone_number",
    "mobile_number":     "phone_number",
    "mobile":            "phone_number",
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

# CRM stage → CAPI event_name mapping
STAGE_TO_EVENT: Dict[str, str] = {
    "new":               "Lead",
    "contacted":         "Contacted",
    "interested":        "MQL",
    "qualified":         "MQL",
    "test_drive_booked": "SQL",
    "appointment":       "SQL",
    "converted":         "Converted",
    "not_interested":    "Not Interested",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper — shared field normalizer (reused by webhook_server.py)
# ─────────────────────────────────────────────────────────────────────────────

def normalize_field_data(field_data: list) -> dict:
    """
    Convert Meta's field_data list into a flat internal dict.

    Meta returns:
        [{"name": "full_name", "values": ["Ravi Kumar"]}, ...]

    Returns:
        {"name": "Ravi Kumar", "phone_number": "...", ...}
    """
    result = {}
    for field in field_data:
        raw   = field.get("name", "").strip().lower()
        vals  = field.get("values", [])
        value = vals[0] if vals else None
        key   = FIELD_NAME_MAP.get(raw, raw.replace(" ", "_"))
        result[key] = value

    # Combine first_name + last_name → name if full_name missing
    if "name" not in result:
        first = result.pop("first_name", "") or ""
        last  = result.pop("last_name",  "") or ""
        combined = f"{first} {last}".strip()
        if combined:
            result["name"] = combined

    return result


def _hash_pii(value: str, pii_type: str = "generic") -> str:
    """SHA-256 hash a PII value (for CAPI user_data)."""
    import re
    if pii_type == "email":
        value = value.strip().lower()
    elif pii_type == "phone":
        value = re.sub(r"\D", "", value)
    else:
        value = value.strip().lower()
    return hashlib.sha256(value.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# MetaLeadAdsManager
# ─────────────────────────────────────────────────────────────────────────────

class MetaLeadAdsManager(MetaAdsManager):
    """
    Extends MetaAdsManager with lead retrieval and Conversions API support.

    Inherits:
        - Meta SDK initialization (FacebookAdsApi.init)
        - self.ad_account  (AdAccount object)
        - self.access_token, self.page_id, self.api_version

    Adds:
        - get_all_campaigns()       List all campaigns
        - get_campaign_ads()        List ads in a campaign
        - get_leads()               List leads from an ad
        - get_leads_by_form()       List leads from a lead form
        - get_lead_detail()         Fetch full lead via Graph API
        - get_all_leads_for_campaign() Convenience: campaign → all leads
        - send_conversion_event()   Push outcome to Meta CAPI
    """

    def __init__(
        self,
        app_id        : Optional[str] = None,
        app_secret    : Optional[str] = None,
        access_token  : Optional[str] = None,
        ad_account_id : Optional[str] = None,
        page_id       : Optional[str] = None,
        pixel_id      : Optional[str] = None,   # for CAPI (Part 2)
        api_version   : str           = "v21.0",
    ):
        """
        Parameters
        ----------
        app_id, app_secret, access_token, ad_account_id, page_id
            Same as MetaAdsManager — passed to FacebookAdsApi.init().
        pixel_id : str
            Meta Pixel ID used for sending CAPI conversion events (Part 2).
            If None, send_conversion_event() will raise a clear error.
        api_version : str
            Default is v21.0 (current stable Marketing API version).

        Note on appsecret_proof
        -----------------------
        The Meta SDK computes appsecret_proof = HMAC-SHA256(app_secret, access_token)
        and appends it to every API call.  This FAILS with 400 "Invalid appsecret_proof"
        when the app_secret belongs to a DIFFERENT Meta App than the one that issued
        the access_token.  In that case we automatically re-init without app_secret
        so the SDK skips proof generation, which is safe for development/testing.
        """
        super().__init__(
            app_id        = app_id,
            app_secret    = app_secret,
            access_token  = access_token,
            ad_account_id = ad_account_id,
            page_id       = page_id,
            api_version   = api_version,
        )
        self.pixel_id = pixel_id

        # ── Auto-fix: verify the SDK actually works; if appsecret_proof
        # is invalid (app_secret belongs to a different app than the token),
        # re-init without app_secret so the SDK stops sending it.
        self._verify_and_fix_sdk_init(
            app_id=app_id, access_token=access_token,
            ad_account_id=ad_account_id, api_version=api_version,
        )

        logger.info(
            "MetaLeadAdsManager ready | account=%s page=%s pixel=%s",
            ad_account_id, page_id, pixel_id or "not set",
        )

    def _verify_and_fix_sdk_init(
        self,
        app_id: str,
        access_token: str,
        ad_account_id: str,
        api_version: str,
    ):
        """
        Make a lightweight test API call.  If it fails with appsecret_proof
        error (code 100), re-initialize the SDK without app_secret so the
        HMAC proof is never sent.

        Diagnostic logged at WARNING level so the developer always sees it.
        """
        from facebook_business.api import FacebookAdsApi
        from facebook_business.adobjects.adaccount import AdAccount
        from facebook_business.adobjects.campaign import Campaign
        from facebook_business.exceptions import FacebookRequestError

        try:
            # Minimal probe — just fetch the account node, no heavy data
            probe = AdAccount(ad_account_id)
            probe.api_get(fields=["id"])
            logger.info(
                "SDK verification OK — appsecret_proof accepted by Meta."
            )
        except FacebookRequestError as exc:
            fb_error = exc.api_error_message() or ""
            if "appsecret_proof" in fb_error.lower() or exc.api_error_code() == 100:
                logger.warning(
                    "⚠  appsecret_proof rejected by Meta (error 100). "
                    "Reason: the app_secret belongs to a DIFFERENT Meta App "
                    "than the one that issued the access_token. "
                    "Re-initializing SDK without app_secret (proof skipped). "
                    "This is safe for testing; for production, ensure app_secret "
                    "and access_token come from the same Meta App."
                )
                FacebookAdsApi.init(
                    app_id       = app_id,
                    app_secret   = None,     # ← disables appsecret_proof
                    access_token = access_token,
                    api_version  = api_version,
                )
                self.ad_account = AdAccount(ad_account_id)
                logger.info("SDK re-initialized without appsecret_proof — OK.")
            else:
                # Different error — surface it so the developer sees it
                logger.error(
                    "SDK verification failed (not an appsecret_proof issue): %s", exc
                )
                raise
        except Exception as exc:
            logger.error("SDK verification unexpected error: %s", exc)
            raise


    # ── 1. Campaigns ───────────────────────────────────────────────────────────

    def get_all_campaigns(
        self,
        status_filter: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Return all campaigns for the configured Ad Account.

        Args:
            status_filter : Optional list of statuses to filter by,
                            e.g. ["ACTIVE", "PAUSED"].
                            If None, returns all campaigns.

        Returns:
            List of dicts with keys:
                id, name, status, objective, effective_status, created_time
        """
        fields = [
            Campaign.Field.id,
            Campaign.Field.name,
            Campaign.Field.status,
            Campaign.Field.objective,
            Campaign.Field.effective_status,
            Campaign.Field.created_time,
        ]
        params = {}
        if status_filter:
            params["effective_status"] = status_filter

        campaigns = self.ad_account.get_campaigns(fields=fields, params=params)
        results = []
        for c in campaigns:
            data = c.export_all_data()
            results.append({
                "id":               data.get("id"),
                "name":             data.get("name"),
                "status":           data.get("status"),
                "effective_status": data.get("effective_status"),
                "objective":        data.get("objective"),
                "created_time":     data.get("created_time"),
            })

        logger.info("get_all_campaigns: found %d campaigns", len(results))
        return results

    # ── 2. Ads ─────────────────────────────────────────────────────────────────

    def get_campaign_ads(self, campaign_id: str) -> List[Dict]:
        """
        Return all ads belonging to a specific campaign.

        Args:
            campaign_id : Campaign ID string (numeric, no prefix needed).

        Returns:
            List of dicts with keys:
                id, name, status, effective_status, adset_id, campaign_id, creative
        """
        fields = [
            Ad.Field.id,
            Ad.Field.name,
            Ad.Field.status,
            Ad.Field.effective_status,
            Ad.Field.adset_id,
            Ad.Field.campaign_id,
            Ad.Field.creative,
        ]
        ads = self.ad_account.get_ads(
            fields=fields,
            params={"campaign_id": campaign_id},
        )
        results = []
        for ad in ads:
            data = ad.export_all_data()
            creative = data.get("creative", {})
            if hasattr(creative, "_data"):
                creative = creative._data
            results.append({
                "id":               data.get("id"),
                "name":             data.get("name"),
                "status":           data.get("status"),
                "effective_status": data.get("effective_status"),
                "adset_id":         data.get("adset_id"),
                "campaign_id":      data.get("campaign_id"),
                "creative_id":      creative.get("id") if isinstance(creative, dict) else None,
            })

        logger.info(
            "get_campaign_ads: campaign=%s → %d ads", campaign_id, len(results)
        )
        return results

    # ── 3. Leads — via Ad ──────────────────────────────────────────────────────

    def get_leads(
        self,
        ad_id: str,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict]:
        """
        Retrieve leadgen IDs from a specific Ad.

        NOTE: This returns lightweight lead records (leadgen_id + metadata).
        Call get_lead_detail(leadgen_id) to get the full form data.

        Args:
            ad_id  : The Ad ID to retrieve leads from.
            since  : ISO date string "YYYY-MM-DD" — only leads after this date.
            until  : ISO date string "YYYY-MM-DD" — only leads before this date.
            limit  : Max records to return per page (default 200).

        Returns:
            List of dicts:
                leadgen_id, created_time, ad_id, form_id
        """
        ad = Ad(ad_id)
        params = {"limit": limit}
        if since:
            params["filtering"] = [{"field": "time_created", "operator": "GREATER_THAN", "value": since}]

        fields = ["id", "created_time", "ad_id", "form_id"]
        leads_cursor = ad.get_leads(fields=fields, params=params)

        results = []
        for lead in leads_cursor:
            data = lead.export_all_data() if hasattr(lead, "export_all_data") else dict(lead)
            results.append({
                "leadgen_id":   data.get("id"),
                "created_time": data.get("created_time"),
                "ad_id":        data.get("ad_id") or ad_id,
                "form_id":      data.get("form_id"),
            })

        logger.info("get_leads: ad=%s → %d leads", ad_id, len(results))
        return results

    # ── 4. Leads — via Lead Form ───────────────────────────────────────────────

    def get_leads_by_form(
        self,
        form_id: str,
        limit: int = 200,
    ) -> List[Dict]:
        """
        Retrieve leads directly from a Lead Ad Form.

        Useful when you know the form_id but not the ad_id.

        Args:
            form_id : The Lead Form (leadgen form) ID.
            limit   : Max records to return.

        Returns:
            Same structure as get_leads().
        """
        form = LeadgenForm(form_id)
        fields = ["id", "created_time", "ad_id", "form_id", "field_data"]
        leads_cursor = form.get_leads(fields=fields, params={"limit": limit})

        results = []
        for lead in leads_cursor:
            data = lead.export_all_data() if hasattr(lead, "export_all_data") else dict(lead)
            field_data = data.get("field_data", [])
            normalized = normalize_field_data(field_data)
            results.append({
                "leadgen_id":   data.get("id"),
                "created_time": data.get("created_time"),
                "ad_id":        data.get("ad_id"),
                "form_id":      data.get("form_id") or form_id,
                **normalized,
                "status": "NEW",
            })

        logger.info("get_leads_by_form: form=%s → %d leads", form_id, len(results))
        return results

    # ── 5. Full Lead Detail — Graph API ───────────────────────────────────────

    def get_lead_detail(self, leadgen_id: int) -> Dict:
        """
        Fetch the full lead form data for a single leadgen_id via Graph API.

        This is the core function shared between:
          - Polling flow  (called after get_leads())
          - Webhook flow  (called after receiving webhook notification)

        Args:
            leadgen_id : The numeric lead ID from Meta.

        Returns:
            dict: Normalized internal lead:
                {
                    "facebook_lead_id": 123456789,
                    "name":             "Ravi Kumar",
                    "phone_number":     "9876543210",
                    "email":            "ravi@example.com",
                    "car_model":        "Hyundai Creta",
                    "created_time":     "2024-06-01T10:00:00+0000",
                    "ad_id":            "...",
                    "form_id":          "...",
                    "status":           "NEW",
                }
        """
        url = f"{GRAPH_BASE_URL}/{self.api_version}/{leadgen_id}"
        params = {
            "access_token": self.access_token,
            "fields":       LEAD_FIELDS,
        }

        for attempt in range(1, 4):
            try:
                resp = requests.get(url, params=params, timeout=15)
            except requests.RequestException as exc:
                if attempt >= 3:
                    raise RuntimeError(
                        f"Network error fetching leadgen_id {leadgen_id}: {exc}"
                    ) from exc
                time.sleep(2 ** attempt)
                continue

            if resp.status_code == 200:
                raw = resp.json()
                break

            body = resp.json()
            err  = body.get("error", {})
            code = err.get("code", 0)

            if resp.status_code == 429 or code == 80004:
                time.sleep(2 ** attempt)
                continue

            raise RuntimeError(
                f"Graph API error {resp.status_code} for leadgen_id {leadgen_id}: "
                f"{err.get('message', resp.text)}"
            )
        else:
            raise RuntimeError(f"Exhausted retries for leadgen_id {leadgen_id}")

        field_data = raw.get("field_data", [])
        normalized = normalize_field_data(field_data)

        lead = {
            "facebook_lead_id": int(raw.get("id", leadgen_id)),
            "created_time":     raw.get("created_time"),
            "ad_id":            raw.get("ad_id"),
            "form_id":          raw.get("form_id"),
            "status":           "NEW",
            **normalized,
        }

        logger.info(
            "get_lead_detail: leadgen_id=%s name=%r phone=%r",
            leadgen_id, lead.get("name"), lead.get("phone_number"),
        )
        return lead

    # ── 6. Convenience — full campaign → all lead details ──────────────────────

    def get_all_leads_for_campaign(
        self,
        campaign_id: str,
        enrich: bool = True,
    ) -> List[Dict]:
        """
        Walk Campaign → Ads → Leads → (optionally) fetch full details.

        Args:
            campaign_id : Campaign to pull leads from.
            enrich      : If True, calls get_lead_detail() for each lead
                          to return full form data. If False, returns only
                          lightweight records (leadgen_id, created_time, etc.)

        Returns:
            List of normalized lead dicts.
        """
        ads = self.get_campaign_ads(campaign_id)
        logger.info(
            "get_all_leads_for_campaign: campaign=%s has %d ads",
            campaign_id, len(ads),
        )

        all_leads = []
        for ad in ads:
            ad_id = ad["id"]
            raw_leads = self.get_leads(ad_id=ad_id)

            if not enrich:
                all_leads.extend(raw_leads)
                continue

            for raw in raw_leads:
                leadgen_id = raw.get("leadgen_id")
                if not leadgen_id:
                    continue
                try:
                    detail = self.get_lead_detail(int(leadgen_id))
                    all_leads.append(detail)
                except Exception as exc:
                    logger.warning(
                        "Could not fetch detail for leadgen_id=%s: %s",
                        leadgen_id, exc,
                    )

        logger.info(
            "get_all_leads_for_campaign: campaign=%s → %d total leads",
            campaign_id, len(all_leads),
        )
        return all_leads

    # ── 7. Conversions API — send outcome back to Meta ─────────────────────────

    def send_conversion_event(
        self,
        stage: str,
        leadgen_id   : Optional[int]  = None,
        phone_number : Optional[str]  = None,
        email        : Optional[str]  = None,
        name         : Optional[str]  = None,
        event_time   : Optional[int]  = None,
        pixel_id     : Optional[str]  = None,
        lead_event_source: str        = "DaveAI AutoCRM",
        test_event_code  : Optional[str] = None,
    ) -> Dict:
        """
        Push a CRM stage outcome back to Meta via Conversions API.

        Supported stages (case-insensitive):
            new, contacted, interested, qualified,
            test_drive_booked, appointment, converted, not_interested

        Args:
            stage            : CRM disposition/stage string.
            leadgen_id       : Facebook lead ID (highest-priority identifier).
            phone_number     : Raw phone — will be hashed.
            email            : Raw email — will be hashed.
            name             : Full name — split and hashed.
            event_time       : Unix timestamp; defaults to now().
            pixel_id         : Override instance pixel_id for this call.
            lead_event_source: CRM name shown in Meta Events Manager.
            test_event_code  : Pass Meta test code for sandbox testing.

        Returns:
            dict: {"status": "ok", "events_received": N}

        Raises:
            ValueError  : If pixel_id is not configured.
            RuntimeError: On CAPI API error.
        """
        _pixel_id = pixel_id or self.pixel_id
        if not _pixel_id:
            raise ValueError(
                "send_conversion_event: pixel_id is required. "
                "Pass it to MetaLeadAdsManager(pixel_id=...) or as a parameter."
            )

        if not any([leadgen_id, phone_number, email, name]):
            raise ValueError(
                "send_conversion_event: at least one customer identifier "
                "(leadgen_id, phone_number, email, or name) is required."
            )

        # ── Map stage → CAPI event_name ────────────────────────────────────
        event_name = STAGE_TO_EVENT.get(stage.lower().strip(), "Lead")
        logger.info(
            "send_conversion_event: stage=%r → event_name=%r pixel=%s",
            stage, event_name, _pixel_id,
        )

        # ── Build user_data (hashed PII) ───────────────────────────────────
        user_data: Dict = {}
        if leadgen_id:
            user_data["lead_id"] = int(leadgen_id)
        if email:
            user_data["em"] = [_hash_pii(email, "email")]
        if phone_number:
            user_data["ph"] = [_hash_pii(phone_number, "phone")]
        if name:
            parts = name.strip().split(maxsplit=1)
            if len(parts) >= 1:
                user_data["fn"] = [_hash_pii(parts[0])]
            if len(parts) == 2:
                user_data["ln"] = [_hash_pii(parts[1])]

        # ── Build CAPI payload ─────────────────────────────────────────────
        event = {
            "event_name":   event_name,
            "event_time":   event_time or int(time.time()),
            "action_source": "system_generated",
            "user_data":    user_data,
            "custom_data": {
                "lead_event_source": lead_event_source,
                "event_source":      "crm",
            },
        }

        payload: Dict = {"data": [event]}
        if test_event_code:
            payload["test_event_code"] = test_event_code

        # ── POST to CAPI endpoint ──────────────────────────────────────────
        api_ver  = self.api_version or "v21.0"
        endpoint = f"{GRAPH_BASE_URL}/{api_ver}/{_pixel_id}/events"
        params   = {"access_token": self.access_token}

        logger.info("=" * 80)
        logger.info("META CAPI DEBUG")
        logger.info("DATASET / PIXEL ID : %s", _pixel_id)
        logger.info("ENDPOINT           : %s", endpoint)
        logger.info("PAYLOAD            : %s", json.dumps(payload, indent=2))
        
        # Verify the pixel/dataset ID via GET request
        try:
            verify_url = f"{GRAPH_BASE_URL}/{api_ver}/{_pixel_id}"
            verify_resp = requests.get(verify_url, params={"fields": "id,name", "access_token": self.access_token}, timeout=10)
            logger.info("PIXEL VERIFICATION : %s", json.dumps(verify_resp.json(), indent=2))
        except Exception as v_err:
            logger.error("Failed to verify pixel ID: %s", v_err)
        
        logger.info("=" * 80)

        for attempt in range(1, 4):
            try:
                resp = requests.post(endpoint, params=params, json=payload, timeout=30)
            except requests.RequestException as exc:
                if attempt >= 3:
                    raise RuntimeError(f"CAPI network error: {exc}") from exc
                time.sleep(2 ** attempt)
                continue

            if resp.status_code == 200:
                result = resp.json()

                logger.info("=" * 80)
                logger.info("META RESPONSE")
                logger.info("RESPONSE JSON : %s", json.dumps(result, indent=2))
                logger.info("=" * 80)

                logger.info(
                    "✓ CAPI event sent: stage=%r event=%r events_received=%s",
                    stage,
                    event_name,
                    result.get("events_received"),
                )

                return {"status": "ok", **result}

            body = resp.json()
            err  = body.get("error", {})
            code = err.get("code", 0)

            if (resp.status_code == 429 or code == 80004) and attempt < 3:
                time.sleep(2 ** attempt)
                continue

            raise RuntimeError(
                f"CAPI error {resp.status_code}: {err.get('message', resp.text)}"
            )

        raise RuntimeError("send_conversion_event: exhausted retries.")
