"""WhatsApp template approval status sync from provider into DB.

Accepts either:
  - ``template_ids`` as a single id (str) → fetch provider status, update DB, return status
  - ``template_ids`` as a list → sync each id and return approved / pending id lists
  - ``dealership_id`` → resolve whatsapp credential, sync all pending templates for the
    dealership, return approved / pending id lists separately

Also exposes ``sync_template_status_by_id`` for programmatic single-template sync.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Optional, Tuple, Union

import requests

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import AUTOCRM_AGENT_SERVICE_NAME, gryd, hp

gryd.SERVICE = AUTOCRM_AGENT_SERVICE_NAME
gryd.set_queue_manager()

from autocrm_db_helper.PGConnector import AutoCRMPGConnector

pg = AutoCRMPGConnector(enterprise_id="autocrm")

AIRTEL_TEMPLATE_URL = (
    "https://iqwhatsapp.airtel.in/gateway/airtel-xchange/"
    "whatsapp-content-manager/v1/template"
)
RML_LOGIN_URL = "https://apis.rmlconnect.net/auth/v1/login/"
RML_TEMPLATES_URL = "https://apis.rmlconnect.net/wba/templates"

DEFAULT_AIRTEL_AUTH = {
    "waba_id": "113485138500957",
    "customer_id": "SOCIOGRAPH_uu76NiJRbNmsq5zPgu5V",
    "sub_account_id": "965a92cd-ac2e-4674-87ab-99fc174e071f",
    "auth_headers": {
        "Content-Type": "application/json",
        "Authorization": "Basic ZGF2ZV9haTpJSjJQVjhebDVjODU=",
    },
}

ALLOWED_DB_STATUSES = frozenset({"pending", "approved", "rejected", "error"})

_PROVIDER_STATUS_ALIASES = {
    "pending_for_review": "pending",
    "in_appeal": "pending",
    "pending_deletion": "pending",
}

_RML_PROVIDER_NAMES = frozenset(
    {"rml", "route_mobile", "route mobile", "routemobile"}
)

TemplateIdsInput = Union[str, List[str], None]


def _normalize_template_status(raw_status: Optional[str]) -> Optional[str]:
    if not raw_status:
        return None
    status = str(raw_status).strip().lower()
    status = _PROVIDER_STATUS_ALIASES.get(status, status)
    if status in ALLOWED_DB_STATUSES:
        return status
    return None


def _resolve_provider(credential: dict, template_record: dict) -> str:
    provider = (credential.get("provider_name") or "").strip().lower()
    if provider:
        return provider
    return (template_record.get("provider_name") or "").strip().lower()


def _resolve_airtel_auth(credential: dict) -> dict:
    auth = credential.get("auth_headers")
    valid_auth_header = (
        isinstance(auth, dict)
        and "Authorization" in auth
        and isinstance(auth["Authorization"], str)
        and auth["Authorization"].strip() != ""
    )
    string_auth_fields = [
        credential.get("waba_id"),
        credential.get("customer_id"),
        credential.get("sub_account_id"),
    ]
    valid_strings = all(
        isinstance(v, (str, int)) and str(v).strip() != ""
        for v in string_auth_fields
    )
    return credential if (valid_strings and valid_auth_header) else DEFAULT_AIRTEL_AUTH


def _fetch_template_record(template_id: str) -> Optional[dict]:
    record = pg.get("template", "template_id", template_id)
    if isinstance(record, list):
        return record[0] if record else None
    return record or None


def _fetch_credential(communication_credentials_id: str) -> Optional[dict]:
    credential = pg.get(
        "communication_credential",
        "communication_credentials_id",
        communication_credentials_id,
    )
    if isinstance(credential, list):
        return credential[0] if credential else None
    return credential or None


def _resolve_whatsapp_credential(dealership_id: str) -> Optional[dict]:
    """Resolve the dealership's WhatsApp credential (prefers Airtel)."""
    records = list(
        pg.list(
            table_name="communication_credential",
            where={"dealership_id": dealership_id, "channel": "whatsapp_chat"},
        )
    )
    if not records:
        return None
    airtel = [
        r
        for r in records
        if (r.get("provider_name") or "").strip().lower() == "airtel"
    ]
    return airtel[0] if airtel else records[0]


def _update_template_status_in_db(
    template_id: str,
    status: str,
    logger,
    rejected_reason: Optional[str] = None,
) -> None:
    if status not in ALLOWED_DB_STATUSES:
        raise ValueError(
            f"Invalid status '{status}' for template_id={template_id}; "
            f"allowed: {sorted(ALLOWED_DB_STATUSES)}"
        )

    update_payload = {"status": status}
    if status == "rejected" and rejected_reason and rejected_reason.upper() != "NONE":
        update_payload["rejection_reason"] = rejected_reason

    pg.update(
        table_name="template",
        id_attr="template_id",
        id=template_id,
        data=update_payload,
    )
    logger.info(f"Updated template_id={template_id} status='{status}'")


def _fetch_airtel_template_status(
    template_id: str,
    auth_data: dict,
    logger,
) -> Tuple[Optional[str], Optional[str]]:
    url = (
        f"{AIRTEL_TEMPLATE_URL}"
        f"?customerId={auth_data['customer_id']}"
        f"&subAccountId={auth_data['sub_account_id']}"
        f"&wabaId={auth_data['waba_id']}"
        f"&templateId={template_id}"
    )
    headers = auth_data["auth_headers"]
    logger.debug(f"[Airtel] GET → {url}")

    response = requests.request("GET", url, headers=headers, data={}, timeout=30)
    response_json = response.json()
    template_data = response_json.get("template")
    if not template_data:
        logger.warning(
            f"[Airtel] No template data for template_id={template_id}: {response_json}"
        )
        return None, None

    status = _normalize_template_status(template_data.get("registrationStatus"))
    if not status:
        raw = template_data.get("registrationStatus")
        logger.warning(
            f"[Airtel] Unmapped or empty status for template_id={template_id}: {raw!r}"
        )
        return None, None

    return status, None


def _rml_login(auth_creds: dict, logger) -> Optional[str]:
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
            timeout=30,
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

    body = resp.json()
    jwt = body.get("JWTAUTH") or body.get("jwtauth") or body.get("token")
    if not jwt:
        logger.error(f"[RML] login response missing JWTAUTH: {body}")
        return None
    return jwt


def _rml_fetch_templates(jwt: str, logger) -> Optional[Dict[str, dict]]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": jwt,
    }
    try:
        response = requests.request(
            "GET", RML_TEMPLATES_URL, headers=headers, data={}, timeout=30
        )
        response_json = response.json()
    except Exception as e:
        logger.error(f"[RML] fetch templates failed: {e}")
        return None

    if not response.ok:
        logger.error(
            f"[RML] viewTemplateMessage error: {response.status_code} - "
            f"{response_json if response_json is not None else response.text[:500]}"
        )
        return None

    templates_by_id: Dict[str, dict] = {}
    templates_by_name: Dict[str, dict] = {}
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
    return {"by_id": templates_by_id, "by_name": templates_by_name}


def _fetch_rml_template_status(
    template_id: str,
    remote_templates: Dict[str, dict],
    logger,
) -> Tuple[Optional[str], Optional[str]]:
    remote = remote_templates["by_id"].get(str(template_id)) or remote_templates[
        "by_name"
    ].get(str(template_id))
    if not remote:
        logger.warning(
            f"[RML] template_id={template_id} not found in remote listing"
        )
        return None, None

    status = _normalize_template_status(remote.get("status"))
    if not status:
        logger.warning(
            f"[RML] Unmapped or empty status for template_id={template_id}: "
            f"{remote.get('status')!r}"
        )
        return None, None

    rejected_reason = remote.get("rejected_reason")
    return status, rejected_reason


def sync_template_status_by_id(template_id: str, logger=None) -> Dict:
    """Look up a template, resolve its provider, fetch remote status, update DB.

    Returns:
        Success:
            {
                "success": True,
                "template_id": "...",
                "provider": "airtel" | "rml",
                "status": "...",
            }

        Failure:
            {"success": False, "error": "...", "template_id": "..."}
    """
    logger = logger or hp.get_logger("template_status_update")

    template_id = (template_id or "").strip()
    if not template_id:
        error = "template_id is required"
        logger.error(error)
        return {"success": False, "error": error}

    record = _fetch_template_record(template_id)
    if not record:
        error = f"Template not found in DB: {template_id}"
        logger.error(error)
        return {"success": False, "error": error, "template_id": template_id}

    communication_credentials_id = record.get("communication_credentials_id")
    if not communication_credentials_id:
        error = (
            f"Template {template_id} has no communication_credentials_id; "
            f"cannot resolve provider"
        )
        logger.error(error)
        return {"success": False, "error": error, "template_id": template_id}

    credential = _fetch_credential(communication_credentials_id)
    if not credential:
        error = f"Communication credential not found: {communication_credentials_id}"
        logger.error(error)
        return {"success": False, "error": error, "template_id": template_id}

    provider = _resolve_provider(credential, record)

    try:
        if provider in ("airtel", ""):
            auth_data = _resolve_airtel_auth(credential)
            status, rejected_reason = _fetch_airtel_template_status(
                template_id, auth_data, logger
            )
            resolved_provider = "airtel"

        elif provider in _RML_PROVIDER_NAMES:
            auth_creds = credential.get("auth_creds") or {}
            jwt = _rml_login(auth_creds, logger)
            if not jwt:
                error = (
                    f"RML login failed for credential {communication_credentials_id}"
                )
                logger.error(error)
                return {"success": False, "error": error, "template_id": template_id}

            remote_templates = _rml_fetch_templates(jwt, logger)
            if not remote_templates:
                error = "Failed to fetch templates from RML"
                logger.error(error)
                return {"success": False, "error": error, "template_id": template_id}

            status, rejected_reason = _fetch_rml_template_status(
                template_id, remote_templates, logger
            )
            resolved_provider = "rml"

        else:
            error = (
                f"Unsupported provider '{credential.get('provider_name') or provider}' "
                f"for template {template_id}"
            )
            logger.error(error)
            return {
                "success": False,
                "error": error,
                "template_id": template_id,
                "provider": provider,
            }

        if not status:
            error = (
                f"Could not resolve status from {resolved_provider} "
                f"for template_id={template_id}"
            )
            logger.error(error)
            return {
                "success": False,
                "error": error,
                "template_id": template_id,
                "provider": resolved_provider,
            }

        _update_template_status_in_db(
            template_id, status, logger, rejected_reason=rejected_reason
        )
        return {
            "success": True,
            "template_id": template_id,
            "provider": resolved_provider,
            "status": status,
        }

    except Exception as e:
        error = f"Failed to sync status for template_id={template_id}: {e}"
        logger.error(error)
        return {"success": False, "error": error, "template_id": template_id}


def _empty_buckets() -> Dict[str, List[str]]:
    return {
        "approved_template_ids": [],
        "pending_template_ids": [],
        "rejected_template_ids": [],
        "error_template_ids": [],
    }


def _append_to_bucket(buckets: Dict[str, List[str]], template_id: str, status: str) -> None:
    if status == "approved":
        buckets["approved_template_ids"].append(template_id)
    elif status == "pending":
        buckets["pending_template_ids"].append(template_id)
    elif status == "rejected":
        buckets["rejected_template_ids"].append(template_id)
    else:
        buckets["error_template_ids"].append(template_id)


def _parse_template_ids_input(
    template_ids: TemplateIdsInput,
    template_id: Optional[str],
    kwargs: dict,
) -> tuple[Optional[str], Optional[List[str]]]:
    """Return (single_id, id_list). Exactly one mode is populated when input is valid."""
    raw = template_ids
    if raw is None:
        raw = template_id or kwargs.get("template_ids") or kwargs.get("template_id")

    if raw is None:
        return None, None

    if isinstance(raw, str):
        single = raw.strip()
        return (single, None) if single else (None, None)

    if isinstance(raw, list):
        ids = [str(item).strip() for item in raw if item and str(item).strip()]
        return None, ids

    return None, None


def _sync_batch_with_credential(
    template_ids: List[str],
    credential: dict,
    logger,
) -> Dict[str, List[str]]:
    """Check provider status for each template under one credential; update DB."""
    buckets = _empty_buckets()
    provider = _resolve_provider(credential, {})

    if provider in ("airtel", ""):
        auth_data = _resolve_airtel_auth(credential)
        for template_id in template_ids:
            try:
                status, rejected_reason = _fetch_airtel_template_status(
                    template_id, auth_data, logger
                )
                if not status:
                    buckets["pending_template_ids"].append(template_id)
                    continue
                _update_template_status_in_db(
                    template_id, status, logger, rejected_reason=rejected_reason
                )
                _append_to_bucket(buckets, template_id, status)
            except Exception as e:
                logger.error(f"[Airtel] Failed template_id={template_id}: {e}")
                buckets["error_template_ids"].append(template_id)

    elif provider in _RML_PROVIDER_NAMES:
        auth_creds = credential.get("auth_creds") or {}
        jwt = _rml_login(auth_creds, logger)
        if not jwt:
            logger.error(
                f"[RML] login failed for credential "
                f"{credential.get('communication_credentials_id')}; "
                f"keeping {len(template_ids)} template(s) pending."
            )
            buckets["pending_template_ids"].extend(template_ids)
            return buckets

        remote_templates = _rml_fetch_templates(jwt, logger)
        if not remote_templates:
            logger.error(
                "[RML] Could not fetch remote templates; keeping all as pending."
            )
            buckets["pending_template_ids"].extend(template_ids)
            return buckets

        for template_id in template_ids:
            try:
                status, rejected_reason = _fetch_rml_template_status(
                    template_id, remote_templates, logger
                )
                if not status:
                    buckets["pending_template_ids"].append(template_id)
                    continue
                _update_template_status_in_db(
                    template_id, status, logger, rejected_reason=rejected_reason
                )
                _append_to_bucket(buckets, template_id, status)
            except Exception as e:
                logger.error(f"[RML] Failed template_id={template_id}: {e}")
                buckets["error_template_ids"].append(template_id)
    else:
        logger.warning(
            f"Unsupported provider_name='{credential.get('provider_name')}' "
            f"for credential {credential.get('communication_credentials_id')}"
        )
        for template_id in template_ids:
            try:
                _update_template_status_in_db(template_id, "error", logger)
            except Exception as e:
                logger.error(
                    f"Failed to mark template_id={template_id} as error: {e}"
                )
            buckets["error_template_ids"].append(template_id)

    return buckets


def _sync_template_id_list(template_ids: List[str], logger) -> Dict:
    """Sync each template id individually (supports mixed credentials)."""
    buckets = _empty_buckets()
    results: List[dict] = []

    for template_id in template_ids:
        outcome = sync_template_status_by_id(template_id, logger=logger)
        results.append(outcome)
        if not outcome.get("success"):
            buckets["error_template_ids"].append(template_id)
            continue
        _append_to_bucket(buckets, template_id, outcome["status"])

    return {
        "success": True,
        **buckets,
        "results": results,
    }


def _list_pending_template_ids(
    dealership_id: str,
    credential: dict,
) -> List[str]:
    cred_id = credential.get("communication_credentials_id")
    records = list(
        pg.list(
            table_name="template",
            where={"dealership_id": dealership_id, "status": "pending"},
        )
    )

    pending_ids: List[str] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        template_id = record.get("template_id")
        if not template_id:
            continue

        channel = (record.get("channel") or "").strip().lower()
        if channel and channel != "whatsapp_chat":
            continue

        record_cred_id = record.get("communication_credentials_id")
        if cred_id and record_cred_id and record_cred_id != cred_id:
            continue

        pending_ids.append(str(template_id))

    return pending_ids


def _sync_by_dealership(dealership_id: str, logger) -> Dict:
    dealership_id = (dealership_id or "").strip()
    if not dealership_id:
        return {"success": False, "error": "dealership_id is required"}

    credential = _resolve_whatsapp_credential(dealership_id)
    if not credential:
        error = f"No whatsapp_chat credential found for dealership_id={dealership_id}"
        logger.error(error)
        return {"success": False, "error": error, "dealership_id": dealership_id}

    pending_ids = _list_pending_template_ids(dealership_id, credential)
    if not pending_ids:
        logger.info(
            f"No pending WhatsApp templates for dealership_id={dealership_id}"
        )
        return {
            "success": True,
            "dealership_id": dealership_id,
            **_empty_buckets(),
        }

    logger.info(
        f"Syncing {len(pending_ids)} pending template(s) for "
        f"dealership_id={dealership_id} | "
        f"credential={credential.get('communication_credentials_id')}"
    )
    buckets = _sync_batch_with_credential(pending_ids, credential, logger)
    return {
        "success": True,
        "dealership_id": dealership_id,
        **buckets,
    }


@gryd.is_a_task(
    "template_status_update",
    logger_param="logger",
    job_param="job",
)
def template_status_update(
    template_ids: TemplateIdsInput = None,
    template_id: Optional[str] = None,
    dealership_id: Optional[str] = None,
    logger=None,
    job=None,
    **kwargs,
):
    """
    Sync WhatsApp template approval status from the provider into the DB.

    Input (exactly one mode):
      - ``template_ids`` / ``template_id`` as a **string** → sync one template and
        return ``{success, template_id, status, provider}``.
      - ``template_ids`` as a **list** → sync each id and return approved / pending /
        rejected / error id lists.
      - ``dealership_id`` → resolve whatsapp credential, sync all pending templates
        for that dealership, return approved / pending id lists separately.

    Supported providers: Airtel (default) and Route Mobile (RML).
    """
    logger = logger or hp.get_logger("template_status_update")

    dealership_id = (dealership_id or kwargs.get("dealership_id") or "").strip()
    single_id, id_list = _parse_template_ids_input(template_ids, template_id, kwargs)

    if dealership_id and (single_id or id_list):
        error = "Provide either template_ids/template_id or dealership_id, not both"
        logger.error(error)
        return {"success": False, "error": error}

    if dealership_id:
        return _sync_by_dealership(dealership_id, logger)

    if single_id:
        logger.info(f"Syncing single template_id={single_id}")
        return sync_template_status_by_id(single_id, logger=logger)

    if id_list is not None:
        if not id_list:
            error = "template_ids list is empty"
            logger.error(error)
            return {"success": False, "error": error}
        logger.info(f"Syncing {len(id_list)} template id(s)")
        return _sync_template_id_list(id_list, logger)

    error = "template_ids, template_id, or dealership_id is required"
    logger.error(error)
    return {"success": False, "error": error}
