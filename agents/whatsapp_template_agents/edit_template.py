"""Edit an existing Airtel WhatsApp template (Manage Templates APIs).

Companion task to ``bulk_send_for_approval``. The input is the updated template
dict with ``template_id`` inside it. The Airtel credential is resolved from the
template's stored record (or an explicitly supplied
``communication_credential_id`` / ``dealership_id``), the edit is POSTed to the
content-manager endpoint, the stored record is updated, and its status reset to
``pending`` for re-approval.

Airtel reference (Manage Templates APIs → Edit Template):
    URL: https://iqwhatsapp.airtel.in/gateway/airtel-xchange/
         whatsapp-content-manager/v1/template   (POST)
    Body: templateId, wabaId, subAccountId, customerId, templateContent
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests

# agents/whatsapp_template_agents/<this file>  →  up three levels = project root
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import AUTOCRM_AGENT_SERVICE_NAME, gryd, hp

gryd.SERVICE = AUTOCRM_AGENT_SERVICE_NAME
gryd.set_queue_manager()
logger = hp.get_logger(gryd.SERVICE)

from autocrm_db_helper.PGConnector import AutoCRMPGConnector

pg = AutoCRMPGConnector(enterprise_id="autocrm")

# Reuse the credential/payload helpers shared with the bulk approval task.
try:
    from agents.whatsapp_template_agents.bulk_send_for_approval import (
        AIRTEL_EDIT_TEMPLATE_URL,
        _build_headers,
        _build_template_content,
        _detect_provider,
        _is_media_template,
        _resolve_airtel_credential,
        _resolve_auth_data,
    )
except ImportError:
    from bulk_send_for_approval import (  # type: ignore
        AIRTEL_EDIT_TEMPLATE_URL,
        _build_headers,
        _build_template_content,
        _detect_provider,
        _is_media_template,
        _resolve_airtel_credential,
        _resolve_auth_data,
    )

# RML edits are delegated to the shared migrator (same component builder used by
# the bulk approval flow), keyed by the credential's provider_name.
try:
    from agents.generic_template_migrator import (
        RouteMobileTemplateMigrator,
        WhatsAppTemplateMigrator,
    )
except ImportError:  # pragma: no cover - fallback when agents/ is on sys.path
    from generic_template_migrator import (  # type: ignore
        RouteMobileTemplateMigrator,
        WhatsAppTemplateMigrator,
    )


def _fetch_template_record(template_id: str) -> Optional[dict]:
    record = pg.get("template", "template_id", template_id)
    if isinstance(record, list):
        return record[0] if record else None
    return record or None


def _get_credential_by_id(cred_id: Optional[str]) -> Optional[dict]:
    if not cred_id:
        return None
    record = pg.get(
        "communication_credential", "communication_credentials_id", cred_id
    )
    if isinstance(record, list):
        return record[0] if record else None
    return record or None


def _resolve_credential_for_edit(
    template: dict,
    existing_record: Optional[dict],
    override_cred_id: Optional[str],
    dealership_id: Optional[str],
) -> Optional[dict]:
    """Resolve the Airtel credential for an edit, preferring an explicit
    credential id, then the stored template's credential, then the dealership."""
    cred_id = (
        override_cred_id
        or template.get("communication_credentials_id")
        or (existing_record or {}).get("communication_credentials_id")
    )
    credential = _get_credential_by_id(cred_id)
    if credential:
        return credential

    deal = (
        dealership_id
        or template.get("dealership_id")
        or (existing_record or {}).get("dealership_id")
    )
    if deal:
        return _resolve_airtel_credential(deal)
    return None


def _update_template_record(
    template: dict,
    template_id: str,
    ordered_vars: List[str],
    existing_record: Optional[dict],
) -> None:
    """Best-effort: update the stored template record with the edited content
    and reset its status to ``pending`` (an edit triggers re-approval)."""
    update_payload: Dict[str, Any] = {"status": "pending"}

    if template.get("template_name"):
        update_payload["template_name"] = template["template_name"]

    body = template.get("template_message") or template.get("body")
    if body is not None:
        update_payload["template_message"] = body

    if template.get("language"):
        update_payload["language"] = str(template["language"]).lower()

    if "buttons" in template:
        buttons = template.get("buttons") or []
        name_lower = (
            template.get("template_name")
            or (existing_record or {}).get("template_name")
            or ""
        ).lower()
        update_payload["buttons"] = buttons
        update_payload["template_button_payloads"] = (
            template.get("template_button_payloads")
            or [
                f"{name_lower}-{(b.get('buttonText') or b.get('text') or '').lower().replace(' ', '_')}"
                for b in buttons
                if isinstance(b, dict) and (b.get("buttonText") or b.get("text"))
            ]
        )

    update_payload["template_variables"] = (
        template.get("template_variables") or ordered_vars
    )
    if _is_media_template(template):
        update_payload["template_type"] = "media"

    for key in ("header", "footer", "media_type", "media_url"):
        if template.get(key) is not None:
            update_payload[key] = template[key]

    pg.update(
        table_name="template",
        id_attr="template_id",
        id=template_id,
        data=update_payload,
    )
    logger.info(f"Updated template record template_id={template_id} (pending)")


def _edit_rml_template(
    template: dict,
    credential: Optional[dict],
    existing_record: Optional[dict],
) -> Tuple[List[str], str]:
    """Edit an existing template on Route Mobile (RML).

    RML's Edit Template API is keyed by ``template_name`` (the normalized name
    stored at creation), not the id. Returns ``(ordered_vars, rml_template_name)``
    so the caller can keep the stored record name consistent and future-proof
    for subsequent edits.
    """
    cred_id = (credential or {}).get("communication_credentials_id")
    if not cred_id:
        raise RuntimeError(
            "RML edit requires a communication_credentials_id on the credential"
        )

    logger.info(
        f"RML edit starting | credential={cred_id} | "
        f"provider_name={(credential or {}).get('provider_name')!r}"
    )

    migrator = RouteMobileTemplateMigrator(communication_credential_id=cred_id)

    # Prefer the stored (already RML-normalized) name so the edit targets the
    # correct remote template; fall back to the supplied name otherwise.
    rml_template_name = (
        template.get("rml_template_name")
        or (existing_record or {}).get("template_name")
        or template.get("template_name")
    )
    if not rml_template_name:
        raise RuntimeError("RML edit requires the existing template_name")

    body = template.get("template_message") or template.get("body") or ""
    ordered_vars = migrator._extract_ordered_variables(body)
    processed_body = migrator._process_message_variables(body, ordered_vars)
    logger.info(
        f"RML edit prepared | template_name={rml_template_name!r} | "
        f"ordered_vars={ordered_vars} | processed_body={processed_body!r}"
    )

    components = migrator._build_components(
        processed_body,
        ordered_vars,
        template.get("buttons") or [],
        footer=template.get("footer"),
        media_type=template.get("media_type"),
        media_url=template.get("media_url"),
    )
    logger.info(
        f"RML edit components for template_name={rml_template_name!r}: "
        f"{json.dumps(components, ensure_ascii=False)}"
    )

    edit_response = migrator._edit_on_rml(rml_template_name, credential, components)
    logger.info(
        f"RML edit completed for template_name={rml_template_name!r} | "
        f"response={edit_response}"
    )
    return ordered_vars, rml_template_name


# EXAMPLE PAYLOAD:
# {
#     "template": {
#         "template_id": "01j6rmpxaypjmrv3pe5n4naqdp",
#         "template_name": "autobot_offer_template",
#         "template_message": "Hi {{person_name}}, your updated offer is ready!",
#         "footer": "Grab now",
#         # media template (image/video/document): media_url is the sample value
#         "media_type": "image",
#         "media_url": "https://.../offer.jpg",
#         "buttons": [
#             {"type": "QUICK_REPLY", "text": "Know More"},
#             {"type": "URL", "buttonText": "Visit", "url": "https://..."}
#         ]
#     }
# }
@gryd.is_a_task("edit_template", logger_param="logger", job_param="job")
def edit_template(template: Any = None, logger=None, job=None, **kwargs) -> str:
    """Edit an existing WhatsApp template (Airtel or RML).

    The input is the updated template dict with ``template_id`` inside it. The
    credential is resolved from the template's stored record (or an explicitly
    supplied ``communication_credential_id`` / ``dealership_id``) and the
    provider is auto-detected from it. The stored record is updated and its
    status reset to ``pending`` for re-approval. Returns the ``template_id``.
    """
    logger = logger or hp.get_logger(__name__)

    template = template if template is not None else kwargs.get("template")
    if isinstance(template, str):
        template = json.loads(template)
    if not isinstance(template, dict) or not template:
        raise ValueError(
            "template (updated template dict containing template_id) is required"
        )

    template_id = template.get("template_id") or kwargs.get("template_id")
    if not template_id:
        raise ValueError("template_id must be present inside the template")
    template["template_id"] = template_id

    existing_record = _fetch_template_record(template_id)
    credential = _resolve_credential_for_edit(
        template,
        existing_record,
        kwargs.get("communication_credential_id"),
        kwargs.get("dealership_id"),
    )
    if not credential:
        logger.warning(
            f"No credential resolved for template_id={template_id}; "
            f"using default Airtel account."
        )

    provider = _detect_provider(credential)
    logger.info(
        f"edit_template resolved | template_id={template_id} | "
        f"provider={provider} | "
        f"credential={(credential or {}).get('communication_credentials_id')} | "
        f"existing_record_found={existing_record is not None}"
    )

    if provider == "rml":
        ordered_vars, rml_template_name = _edit_rml_template(
            template, credential, existing_record
        )
        logger.info(
            f"Edited RML template '{rml_template_name}' "
            f"(template_id={template_id})"
        )
        # Keep the stored record name as the RML-normalized name so later edits
        # continue to resolve the right remote template.
        template["template_name"] = rml_template_name
        try:
            _update_template_record(
                template, template_id, ordered_vars, existing_record
            )
        except Exception as e:
            logger.error(
                f"Edited template_id={template_id} but failed to update record: {e}"
            )
        return template_id

    auth_data = _resolve_auth_data(credential)
    headers = _build_headers(credential)
    logger.info(
        f"Editing template_id={template_id} via Airtel | "
        f"provider={provider} | "
        f"credential={(credential or {}).get('communication_credentials_id')} | "
        f"wabaId={auth_data['waba_id']} | subAccountId={auth_data['sub_account_id']}"
    )

    content, ordered_vars = _build_template_content(template)
    # Airtel's edit endpoint reuses the create request model, so ``category`` is
    # mandatory and must be one of Airtel's accepted enum values
    # (TRANSACTIONAL, OTP, AUTHENTICATION, MARKETING, UTILITY). The template's
    # campaign_type (e.g. "PRE-SALES") is not a valid category, so we always
    # send MARKETING here.
    category = "MARKETING"
    # Airtel's edit endpoint also requires the (non-empty) templateName. Prefer
    # the supplied name, falling back to the stored record's name.
    template_name = (
        template.get("template_name")
        or (existing_record or {}).get("template_name")
    )
    if not template_name:
        raise ValueError(
            f"template_name is required to edit template_id={template_id} "
            f"(not found on the input or the stored record)"
        )
    logger.info(
        f"Using fixed category for template_id={template_id}: {category} | "
        f"templateName={template_name!r}"
    )
    payload = {
        "templateId": template_id,
        "templateName": template_name,
        "wabaId": auth_data["waba_id"],
        "subAccountId": auth_data["sub_account_id"],
        "customerId": auth_data["customer_id"],
        "category": category,
        "templateContent": content,
    }
    logger.info(
        f"Airtel edit-template payload for template_id={template_id}: "
        f"{json.dumps(payload, ensure_ascii=False)}"
    )

    resp = requests.post(
        AIRTEL_EDIT_TEMPLATE_URL,
        headers=headers,
        data=json.dumps(payload),
        timeout=60,
    )
    logger.info(
        f"Airtel edit-template response for template_id={template_id}: "
        f"{resp.status_code} - {resp.text}"
    )
    if not resp.ok:
        raise RuntimeError(
            f"Airtel edit-template error for template_id={template_id}: "
            f"{resp.status_code} - {resp.text}"
        )
    logger.info(f"Edited template_id={template_id} via Airtel")

    try:
        _update_template_record(template, template_id, ordered_vars, existing_record)
    except Exception as e:
        logger.error(
            f"Edited template_id={template_id} but failed to update record: {e}"
        )

    return template_id
