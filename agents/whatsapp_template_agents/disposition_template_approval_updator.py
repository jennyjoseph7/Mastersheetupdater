import json
import os
import re
import sys
import time
from typing import Dict, List, Optional

import requests

try:
    from agents.base_agent import gryd
except ImportError:
    from base_agent import gryd

# agents/whatsapp_template_agents/<this file> → up three levels = project root
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import AUTOCRM_AGENT_SERVICE_NAME

gryd.SERVICE = AUTOCRM_AGENT_SERVICE_NAME
gryd.set_queue_manager()

from autocrm_db_helper.PGConnector import AutoCRMPGConnector

try:
    from agents.generic_template_migrator import WhatsAppTemplateMigrator
except ImportError:
    from generic_template_migrator import WhatsAppTemplateMigrator  # type: ignore

try:
    from agents.whatsapp_template_agents.whatsapp_template_creator_agent import (
        WhatsappTemplateCreatorAgent,
    )
except ImportError:
    from whatsapp_template_agents.whatsapp_template_creator_agent import (  # type: ignore
        WhatsappTemplateCreatorAgent,
    )

pg = AutoCRMPGConnector(enterprise_id="autocrm")

AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")

FIRST_PAUSE_SECONDS = 3 * 60
ROUND_PAUSE_SECONDS = 5 * 60
STATUS_UPDATE_PAUSE_SECONDS = 2

ALLOWED_DB_STATUSES = frozenset({"pending", "approved", "rejected", "error"})

# Sentinel returned by the status fetchers when the provider reports the
# template with no usable status. Such a template is stuck and must be deleted
# and re-submitted (recreated) rather than polled indefinitely.
RECREATE_SIGNAL = "__needs_recreation__"

# Guard against an endless delete/recreate loop when a template keeps coming
# back without a valid status. After this many attempts the template is marked
# as error and polling stops.
MAX_RECREATION_ATTEMPTS = 3

# Keys that must not be carried over to the freshly recreated template record.
_RECREATE_SKIP_KEYS = frozenset(
    {"template_id", "status", "created", "updated", "_id", "_rev", "rejection_reason"}
)

_PROVIDER_STATUS_ALIASES = {
    "pending_for_review": "pending",
    "in_appeal": "pending",
    "pending_deletion": "pending",
}

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


def _normalize_template_status(raw_status: Optional[str]) -> Optional[str]:
    """Map provider status to one of template.json allowed values, or None."""
    if not raw_status:
        return None
    status = str(raw_status).strip().lower()
    status = _PROVIDER_STATUS_ALIASES.get(status, status)
    if status in ALLOWED_DB_STATUSES:
        return status
    return None


def _is_pending_status(status: Optional[str]) -> bool:
    return status == "pending"


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


def _update_template_status_in_db(
    template_id: str,
    status: str,
    logger,
    rejected_reason: Optional[str] = None,
) -> None:
    if status not in ALLOWED_DB_STATUSES:
        logger.warning(
            f"Refusing to store invalid status '{status}' for template_id={template_id}; "
            f"allowed: {sorted(ALLOWED_DB_STATUSES)}"
        )
        return

    update_payload = {"status": status}
    if status == "rejected" and rejected_reason and rejected_reason.upper() != "NONE":
        update_payload["rejection_reason"] = rejected_reason

    pg.update(
        table_name="template",
        id_attr="template_id",
        id=template_id,
        data=update_payload,
    )
    logger.info(
        f"Updated template_id={template_id} status='{status}'"
    )
    time.sleep(STATUS_UPDATE_PAUSE_SECONDS)


def _fetch_airtel_template_status(
    template_id: str,
    auth_data: dict,
    logger,
) -> Optional[str]:
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
        return None

    status = _normalize_template_status(template_data.get("registrationStatus"))
    if not status:
        raw = template_data.get("registrationStatus")
        logger.warning(
            f"[Airtel] Unmapped or empty status for template_id={template_id}: {raw!r}"
        )
        # Provider knows the template but has no usable status for it; the
        # submission is stuck. Signal a delete + recreate instead of polling.
        return RECREATE_SIGNAL
    return status


def _fetch_template_record(template_id: str) -> Optional[dict]:
    record = pg.get("template", "template_id", template_id)
    if isinstance(record, list):
        return record[0] if record else None
    return record or None


def _sanitize_airtel_template_name(name: str) -> str:
    """Lowercase alphanumerics + underscores only (Airtel/WhatsApp constraint)."""
    cleaned = re.sub(r"[\s-]+", "_", (name or "").lower().strip())
    cleaned = re.sub(r"[^a-z0-9_]", "_", cleaned)
    return cleaned or "autobot_disposition_template"


def _build_regeneration_source(record: dict) -> dict:
    """Reconstruct a WhatsappTemplateCreatorAgent source from a stored template
    record so a rejected template can be regenerated with fresh content."""
    variables = list(record.get("template_variables") or [])
    objective_name = record.get("campaign_objective_name") or (
        (record.get("campaign_objective") or [""])[0]
    )
    disposition = record.get("disposition", "")
    disposition_details = record.get("disposition_details", "")
    cta_buttons = [
        btn.get("buttonText") or btn.get("text")
        for btn in (record.get("buttons") or [])
        if (btn.get("buttonText") or btn.get("text"))
    ]

    purpose = (
        "Regenerate a fresh WhatsApp template variation: the previous version was "
        "REJECTED by the provider, so write new, compliant wording that keeps the "
        "same intent and uses ONLY the placeholders provided. Do NOT include any "
        "phone number, contact number, email, OTP, payment/account number, or other "
        "sensitive identifier in the message or CTA labels — those cause rejection."
    )
    if disposition or disposition_details:
        purpose += (
            f" This is a disposition follow-up template "
            f"(disposition='{disposition}', details='{disposition_details}')."
        )

    return {
        "campaign_type": record.get("campaign_type", ""),
        "campaign_objective": objective_name,
        "dealership_id": record.get("dealership_id", ""),
        "languages": [record.get("language") or "english"],
        "cta_buttons": cta_buttons,
        "data": {
            "purpose": purpose,
            "attribute_name": variables,
            "disposition": disposition,
            "disposition_details": disposition_details,
        },
    }


def _regenerate_template_content(record: dict, logger) -> Optional[dict]:
    """Generate brand-new template content (name/message/buttons) for a rejected
    template. Returns ``None`` if generation fails."""
    try:
        agent = WhatsappTemplateCreatorAgent(
            source=_build_regeneration_source(record), logger=logger
        )
        content = agent.run()
    except Exception as e:
        logger.error(
            f"[Airtel] Failed to regenerate content for "
            f"template_id={record.get('template_id')}: {e}"
        )
        return None

    if not content or not content.get("template_message"):
        logger.error(
            f"[Airtel] Regeneration produced no template_message for "
            f"template_id={record.get('template_id')}"
        )
        return None

    # Unique, provider-safe name so Airtel never rejects it as a duplicate.
    base_name = _sanitize_airtel_template_name(content.get("template_name"))
    content["template_name"] = f"{base_name}_{int(time.time())}"[:100]
    return content


def _recreate_airtel_template(
    template_id: str,
    auth_data: dict,
    credential: dict,
    logger,
    regenerate: bool = False,
) -> Optional[str]:
    """Delete a problematic Airtel template and submit a replacement.

    ``regenerate=False`` (status None/unmapped/error): re-submit the SAME stored
    content for a fresh templateId. ``regenerate=True`` (status rejected):
    generate BRAND-NEW content and submit that instead.

    In both cases we submit first, post a new ``pending`` record mirroring the
    old one, then delete the stuck record, and return the new templateId so the
    caller can swap it into the poll list.

    Returns the new template_id, or ``None`` if recreation could not proceed
    (in which case the caller should keep the original id pending).
    """
    record = _fetch_template_record(template_id)
    if not record:
        logger.error(
            f"[Airtel] Cannot recreate template_id={template_id}: not found in DB"
        )
        return None

    extra_record_updates: Dict[str, object] = {}
    if regenerate:
        content = _regenerate_template_content(record, logger)
        if not content:
            return None
        template_name = content["template_name"]
        template_message = content["template_message"]
        source_buttons = content.get("buttons") or []
        extra_record_updates = {
            "buttons": source_buttons,
            "template_button_payloads": content.get("template_button_payloads", []),
            "lead_tags": content.get("lead_tags", record.get("lead_tags", [])),
        }
    else:
        template_name = record.get("template_name")
        template_message = record.get("template_message")
        if not template_name or not template_message:
            logger.error(
                f"[Airtel] Cannot recreate template_id={template_id}: "
                f"missing template_name/template_message"
            )
            return None
        source_buttons = record.get("buttons") or []

    cred_id = (
        credential.get("communication_credentials_id")
        or record.get("communication_credentials_id")
    )

    try:
        migrator = WhatsAppTemplateMigrator(communication_credential_id=cred_id)
        buttons = [
            {
                "type": btn.get("type", "QUICK_REPLY"),
                "buttonText": btn.get("buttonText") or btn.get("text"),
            }
            for btn in source_buttons
        ]
        ordered_vars = migrator._extract_ordered_variables(template_message)
        processed_message = migrator._process_message_variables(
            template_message, ordered_vars
        )
        lang_raw = (record.get("language") or "english").strip().capitalize()
        lang_code = WhatsAppTemplateMigrator.LANG_TO_CODE.get(lang_raw, "en")

        # Submit FIRST: only touch the DB once we have a new templateId so a
        # failed submission never leaves the disposition set short a template.
        new_template_id = migrator._submit_for_approval(
            template_name,
            auth_data,
            processed_message,
            buttons,
            ordered_vars,
            lang_code,
        )
    except Exception as e:
        action = "regenerate" if regenerate else "re-submit"
        logger.error(
            f"[Airtel] Failed to {action} template_id={template_id}: {e}"
        )
        return None

    new_record = {k: v for k, v in record.items() if k not in _RECREATE_SKIP_KEYS}
    new_record["template_id"] = new_template_id
    new_record["status"] = "pending"
    new_record["template_name"] = template_name
    new_record["template_message"] = template_message
    new_record["template_variables"] = ordered_vars
    new_record["buttons"] = source_buttons
    new_record.update(extra_record_updates)

    try:
        gryd.base_model.Model("template", AUTOCRM_APP_ENTERPRISE_ID).post(new_record)
    except Exception as e:
        logger.error(
            f"[Airtel] Submitted template_id={template_id} → {new_template_id}, "
            f"but failed to post the new record: {e}"
        )
        return None

    try:
        pg.delete("template", "template_id", template_id)
    except Exception as e:
        logger.error(
            f"[Airtel] Posted replacement {new_template_id} but failed to delete "
            f"old template_id={template_id}: {e}"
        )

    action = "Regenerated" if regenerate else "Recreated"
    logger.info(
        f"[Airtel] {action} template '{template_name}': removed old "
        f"template_id={template_id}, new template_id={new_template_id}"
    )
    return new_template_id


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
) -> tuple[Optional[str], Optional[str]]:
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


def _resolve_provider(credential: dict) -> str:
    return (credential.get("provider_name") or "").strip().lower()


def _check_and_update_templates(
    template_ids: List[str],
    credential: dict,
    logger,
    recreation_attempts: Optional[Dict[str, int]] = None,
) -> List[str]:
    """Check provider status for each template, update DB, return still-pending ids."""
    provider = _resolve_provider(credential)
    still_pending: List[str] = []
    if recreation_attempts is None:
        recreation_attempts = {}

    if provider in ("airtel", ""):
        auth_data = _resolve_airtel_auth(credential)
        for template_id in template_ids:
            try:
                status = _fetch_airtel_template_status(template_id, auth_data, logger)

                # None/unmapped/error → re-submit the SAME content.
                # rejected → generate a BRAND-NEW template.
                resend_same = status in (RECREATE_SIGNAL, "error")
                regenerate = status == "rejected"

                if resend_same or regenerate:
                    attempts = recreation_attempts.get(template_id, 0)
                    if attempts >= MAX_RECREATION_ATTEMPTS:
                        logger.error(
                            f"[Airtel] template_id={template_id} unresolved after "
                            f"{attempts} recreation attempt(s) (last status="
                            f"{status}); marking as error and stopping."
                        )
                        _update_template_status_in_db(template_id, "error", logger)
                        continue
                    new_template_id = _recreate_airtel_template(
                        template_id,
                        auth_data,
                        credential,
                        logger,
                        regenerate=regenerate,
                    )
                    if new_template_id:
                        # Drop the old id, poll the new one next round.
                        recreation_attempts[new_template_id] = attempts + 1
                        still_pending.append(new_template_id)
                    else:
                        recreation_attempts[template_id] = attempts + 1
                        still_pending.append(template_id)
                    continue

                if not status:
                    still_pending.append(template_id)
                    continue
                _update_template_status_in_db(template_id, status, logger)
                if _is_pending_status(status):
                    still_pending.append(template_id)
            except Exception as e:
                logger.error(f"[Airtel] Failed template_id={template_id}: {e}")
                still_pending.append(template_id)

    elif provider in ("rml", "route_mobile", "route mobile", "routemobile"):
        auth_creds = credential.get("auth_creds") or {}
        jwt = _rml_login(auth_creds, logger)
        if not jwt:
            logger.error(
                f"[RML] login failed for credential "
                f"{credential.get('communication_credentials_id')}; keeping all pending."
            )
            return list(template_ids)

        remote_templates = _rml_fetch_templates(jwt, logger)
        if not remote_templates:
            logger.error("[RML] Could not fetch remote templates; keeping all pending.")
            return list(template_ids)

        for template_id in template_ids:
            try:
                status, rejected_reason = _fetch_rml_template_status(
                    template_id, remote_templates, logger
                )
                if not status:
                    still_pending.append(template_id)
                    continue
                _update_template_status_in_db(
                    template_id, status, logger, rejected_reason=rejected_reason
                )
                if _is_pending_status(status):
                    still_pending.append(template_id)
            except Exception as e:
                logger.error(f"[RML] Failed template_id={template_id}: {e}")
                still_pending.append(template_id)
    else:
        logger.warning(
            f"Unsupported provider_name='{credential.get('provider_name')}' "
            f"for credential {credential.get('communication_credentials_id')}; "
            f"marking {len(template_ids)} templates as error."
        )
        for template_id in template_ids:
            _update_template_status_in_db(template_id, "error", logger)

    return still_pending


@gryd.is_a_task(
    "update_disposition_template_approval",
    logger_param="logger",
    job_param="job",
)
def update_disposition_template_approval(
    template_ids: List[str],
    communication_credentials_id: str,
    logger=None,
    job=None,
):
    """
    Fire-and-forget polling task for disposition template approval status.

    Waits 2 minutes before the first check, then re-checks every 60 minutes
    until every template is approved, rejected, or error. Templates still
    pending approval remain in the poll list between rounds.
    """
    logger = logger or gryd.hp.get_logger(__name__)

    pending = [tid for tid in (template_ids or []) if tid]
    if not pending:
        logger.info("No template ids to track; exiting approval poll.")
        return

    if not communication_credentials_id:
        logger.error("communication_credentials_id is required for approval poll.")
        return

    credential = pg.get(
        "communication_credential",
        "communication_credentials_id",
        communication_credentials_id,
    )
    if not credential:
        logger.error(
            f"communication_credential not found: {communication_credentials_id}"
        )
        return

    logger.info(
        f"Disposition approval poll started for {len(pending)} templates | "
        f"credential={communication_credentials_id} | "
        f"first pause={FIRST_PAUSE_SECONDS}s | "
        f"round pause={ROUND_PAUSE_SECONDS}s"
    )

    time.sleep(FIRST_PAUSE_SECONDS)

    # Persists across rounds so a template that keeps coming back without a
    # valid status is recreated at most MAX_RECREATION_ATTEMPTS times.
    recreation_attempts: Dict[str, int] = {}

    round_num = 1
    while pending:
        logger.info(
            f"Approval poll round {round_num}: checking {len(pending)} template(s)"
        )
        pending = _check_and_update_templates(
            pending, credential, logger, recreation_attempts
        )

        if not pending:
            logger.info("All disposition templates resolved; exiting approval poll.")
            break

        logger.info(
            f"{len(pending)} template(s) still pending approval; "
            f"sleeping {ROUND_PAUSE_SECONDS}s before next round"
        )
        time.sleep(ROUND_PAUSE_SECONDS)
        round_num += 1
