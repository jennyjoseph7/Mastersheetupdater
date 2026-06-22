"""Bulk-submit WhatsApp templates to Airtel for approval.

Given a ``dealership_id``, a ``campaign_objective_id`` and a list of generated
templates (which may mix different Airtel template *types* — Static Text Body,
Text Body with Variables, Header-Body-Footer, and URL-based Media), this task
submits each one to the Airtel "Create Template" API for approval, stores a
``pending`` record in the ``template`` model, and returns the list of Airtel
``templateId``s.

Airtel reference (Create Templates APIs):
    URL: https://iqwhatsapp.airtel.in/gateway/airtel-xchange/
         whatsapp-content-manager/v1/template
    Headers: app-id, Content-Type, Authorization (Basic)

Each create call submits ONE template and returns one ``templateId``; we loop
over the supplied list so a single task call submits the whole batch and
returns every id. (Airtel's "Bulk Send Templates API" is a different endpoint
that delivers already-approved templates to recipient numbers — it is not used
here because this task is about getting templates *approved*.)
"""

import json
import os
import re
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

# RML (Route Mobile) support is delegated to the shared migrator, which already
# implements RML's JWT login, payload building (text/media/footer/CTA buttons)
# and category mapping. We reuse it here so a single bulk call can submit to
# either Airtel or RML depending on the resolved credential's provider.
try:
    from agents.generic_template_migrator import (
        RouteMobileTemplateMigrator,
        TemplateMigrationAbortError,
        WhatsAppTemplateMigrator,
    )
except ImportError:  # pragma: no cover - fallback when agents/ is on sys.path
    from generic_template_migrator import (  # type: ignore
        RouteMobileTemplateMigrator,
        TemplateMigrationAbortError,
        WhatsAppTemplateMigrator,
    )

pg = AutoCRMPGConnector(enterprise_id="autocrm")

AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")

# Recognised provider names on a ``communication_credential``. Anything not
# matched here falls back to the Airtel flow (the historical default).
RML_PROVIDER_NAMES = {"rml", "routemobile", "route_mobile", "route mobile"}
AIRTEL_PROVIDER_NAMES = {"airtel"}

AIRTEL_CREATE_TEMPLATE_URL = (
    "https://iqwhatsapp.airtel.in/gateway/airtel-xchange/"
    "whatsapp-content-manager/v1/template"
)

# Edit Template (Manage Templates APIs) uses the same content-manager resource
# URL as create (POST) with ``templateId`` in the body.
AIRTEL_EDIT_TEMPLATE_URL = AIRTEL_CREATE_TEMPLATE_URL

# Used only when the resolved credential is missing the Airtel auth fields, so a
# misconfigured dealership credential still submits against the shared account
# (mirrors disposition_template_approval_updator.DEFAULT_AIRTEL_AUTH).
DEFAULT_AIRTEL_AUTH = {
    "waba_id": "113485138500957",
    "customer_id": "SOCIOGRAPH_uu76NiJRbNmsq5zPgu5V",
    "sub_account_id": "965a92cd-ac2e-4674-87ab-99fc174e071f",
    "auth_headers": {
        "Content-Type": "application/json",
        "Authorization": "Basic ZGF2ZV9haTpJSjJQVjhebDVjODU=",
    },
}

LANG_TO_CODE = {
    "English": "en", "Hindi": "hi", "Assamese": "as", "Bengali": "bn",
    "Gujarati": "gu", "Kannada": "kn", "Kashmiri": "ks", "Malayalam": "ml",
    "Marathi": "mr", "Nepali": "ne", "Odia": "or", "Punjabi": "pa",
    "Sanskrit": "sa", "Sindhi": "sd", "Tamil": "ta", "Telugu": "te",
    "Urdu": "ur", "Konkani": "kok", "Manipuri": "mni", "Maithili": "mai",
    "Santali": "sat", "Dogri": "doi", "Bodo": "bdo",
}

MEDIA_TYPE_MAP = {
    "image": "IMAGE",
    "video": "VIDEO",
    "document": "DOCUMENT",
    "audio": "AUDIO",
}

_VARIABLE_PATTERN = r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}"


def _coerce_templates(templates: Any) -> List[dict]:
    """Normalize the ``templates`` input into a list of template dicts.

    Accepts a list, a single template dict, or a JSON string of either.
    """
    if templates is None:
        return []
    if isinstance(templates, str):
        templates = json.loads(templates)
    if isinstance(templates, dict):
        # Either a single template or a wrapper like {"templates": [...]}.
        if isinstance(templates.get("templates"), list):
            return [t for t in templates["templates"] if isinstance(t, dict)]
        return [templates]
    if isinstance(templates, list):
        return [t for t in templates if isinstance(t, dict)]
    raise ValueError("templates must be a list, dict, or JSON string")


def _extract_ordered_variables(message: str) -> List[str]:
    """Return ``{{var}}`` names in first-seen order, de-duplicated."""
    extracted = re.findall(_VARIABLE_PATTERN, message or "")
    seen: set = set()
    return [v for v in extracted if not (v in seen or seen.add(v))]


def _process_message_variables(message: str, ordered_vars: List[str]) -> str:
    """Replace named ``{{var}}`` placeholders with positional ``{{1}}`` ones."""
    processed = message or ""
    for idx, var_name in enumerate(ordered_vars, start=1):
        pat = r"\{\{\s*" + re.escape(var_name) + r"\s*\}\}"
        processed = re.sub(pat, "{{" + str(idx) + "}}", processed)
    return processed


def _format_buttons(buttons: Optional[list]) -> list:
    """Map stored buttons to Airtel's create-template button schema.

    Quick-reply buttons only need ``type``/``buttonText``. Call-to-action and
    other rich button types (URL, PHONE_NUMBER, COPY_CODE, FLOW, OTP) pass
    their extra fields through unchanged when present.
    """
    formatted = []
    passthrough_keys = (
        "subType", "url", "urlType", "phoneNumber",
        "flowId", "flowAction", "navigateScreen",
    )
    for btn in buttons or []:
        if not isinstance(btn, dict):
            continue
        text = btn.get("buttonText") or btn.get("text")
        out: Dict[str, Any] = {"type": btn.get("type", "QUICK_REPLY")}
        if text:
            out["buttonText"] = text
        for key in passthrough_keys:
            if btn.get(key) is not None:
                out[key] = btn[key]
        formatted.append(out)
    return formatted


def _is_media_template(template: dict) -> bool:
    return bool(
        str(template.get("template_type", "")).lower() == "media"
        or template.get("media_type")
        or template.get("media_url")
    )


def _build_template_content(template: dict) -> Tuple[dict, List[str]]:
    """Build the Airtel ``templateContent`` block and return ordered var names.

    Handles all supported types from one schema:
      - Static Text Body          → body only
      - Text Body with Variables  → body + sample.variables
      - Header-Body-Footer        → + header / footer / buttons
      - Media (URL based)         → + media type and url-based sample.fileHandle
    """
    body = template.get("template_message") or template.get("body") or ""
    lang_raw = (template.get("language") or "english").strip().capitalize()
    lang_code = LANG_TO_CODE.get(lang_raw, "en")

    ordered_vars = _extract_ordered_variables(body)
    processed_body = _process_message_variables(body, ordered_vars)

    content: Dict[str, Any] = {"language": lang_code, "body": processed_body}

    header = template.get("header")
    if header:
        content["header"] = header

    footer = template.get("footer")
    if footer:
        content["footer"] = footer

    buttons = _format_buttons(template.get("buttons"))
    if buttons:
        content["buttons"] = buttons

    sample: Dict[str, Any] = {}
    if ordered_vars:
        # Airtel accepts the variable names here as the sample values (this is
        # what the existing single-template approval flow already submits).
        sample["variables"] = ordered_vars

    if _is_media_template(template):
        media_type = str(template.get("media_type") or "image").lower()
        content["media"] = MEDIA_TYPE_MAP.get(media_type, "IMAGE")
        # URL-based (not id-based): the public media URL is supplied as the
        # sample media reference. An explicit ``file_handle`` overrides it.
        file_handle = template.get("file_handle") or template.get("media_url")
        if file_handle:
            sample["fileHandle"] = file_handle

    if sample:
        content["sample"] = sample

    return content, ordered_vars


def _resolve_airtel_credential(dealership_id: str) -> Optional[dict]:
    """Find the dealership's Airtel WhatsApp credential (falls back to any
    whatsapp_chat credential if no provider is tagged 'airtel')."""
    records = list(
        pg.list(
            table_name="communication_credential",
            where={"dealership_id": dealership_id, "channel": "whatsapp_chat"},
        )
    )
    if not records:
        return None
    airtel = [
        r for r in records
        if (r.get("provider_name") or "").strip().lower() == "airtel"
    ]
    return airtel[0] if airtel else records[0]


def _resolve_auth_data(credential: Optional[dict]) -> dict:
    """Resolve waba/customer/subAccount ids, falling back to the shared default
    when the credential is missing any of them."""
    credential = credential or {}
    fields = [
        credential.get("waba_id"),
        credential.get("customer_id"),
        credential.get("sub_account_id"),
    ]
    if all(isinstance(v, (str, int)) and str(v).strip() for v in fields):
        return {
            "waba_id": credential["waba_id"],
            "customer_id": credential["customer_id"],
            "sub_account_id": credential["sub_account_id"],
        }
    return {
        "waba_id": DEFAULT_AIRTEL_AUTH["waba_id"],
        "customer_id": DEFAULT_AIRTEL_AUTH["customer_id"],
        "sub_account_id": DEFAULT_AIRTEL_AUTH["sub_account_id"],
    }


def _build_headers(credential: Optional[dict]) -> dict:
    auth = (credential or {}).get("auth_headers")
    if not (isinstance(auth, dict) and str(auth.get("Authorization") or "").strip()):
        auth = DEFAULT_AIRTEL_AUTH["auth_headers"]
    headers = dict(auth)
    headers.setdefault("Content-Type", "application/json")
    headers.setdefault("app-id", "IRONMAN")
    return headers


def _get_credential_by_id(cred_id: Optional[str]) -> Optional[dict]:
    """Fetch a single ``communication_credential`` by its id."""
    if not cred_id:
        return None
    record = pg.get(
        "communication_credential", "communication_credentials_id", cred_id
    )
    if isinstance(record, list):
        return record[0] if record else None
    return record or None


def _detect_provider(credential: Optional[dict]) -> str:
    """Return the normalized provider name (``'rml'``, ``'airtel'``, ...).

    Defaults to ``'airtel'`` when the credential is missing or untagged so
    existing dealerships keep working without a provider field.
    """
    provider = ((credential or {}).get("provider_name") or "").strip().lower()
    if provider in RML_PROVIDER_NAMES:
        return "rml"
    return provider or "airtel"


def _submit_rml_template_for_approval(
    template: dict,
    migrator: "RouteMobileTemplateMigrator",
    credential: dict,
) -> Tuple[str, List[str], str]:
    """Submit ONE template to Route Mobile (RML) for approval.

    Returns ``(template_id, ordered_vars, normalized_template_name)``. RML
    requires a sample value rather than a variable name, so the media URL is
    passed straight through as the header sample and body variables are sent
    as example values by the migrator.
    """
    template_name = template.get("template_name")
    if not template_name:
        raise ValueError("template_name is required for every template")

    body = template.get("template_message") or template.get("body") or ""
    ordered_vars = migrator._extract_ordered_variables(body)
    processed_body = migrator._process_message_variables(body, ordered_vars)

    lang_raw = (template.get("language") or "english").strip().capitalize()
    lang_code = WhatsAppTemplateMigrator.LANG_TO_CODE.get(lang_raw, "en")

    normalized_name = migrator._normalize_template_name(template_name)
    category = (
        template.get("category")
        or template.get("campaign_type")
        or "marketing"
    )

    template_id = migrator._submit_to_rml(
        normalized_name,
        credential,
        processed_body,
        template.get("buttons") or [],
        ordered_vars,
        lang_code,
        category=category,
        footer=template.get("footer"),
        media_type=template.get("media_type"),
        media_url=template.get("media_url"),
    )
    if not template_id:
        raise RuntimeError(
            f"RML returned no template id for '{normalized_name}'"
        )
    return template_id, ordered_vars, normalized_name


def _submit_template_for_approval(
    template: dict,
    auth_data: dict,
    headers: dict,
) -> Tuple[str, List[str]]:
    """Submit ONE template and return ``(template_id, ordered_vars)``."""
    template_name = template.get("template_name")
    if not template_name:
        raise ValueError("template_name is required for every template")

    content, ordered_vars = _build_template_content(template)
    # Airtel only accepts a fixed category enum (TRANSACTIONAL, OTP,
    # AUTHENTICATION, MARKETING, UTILITY). A template's campaign_type (e.g.
    # "PRE-SALES") is not a valid category, so always send MARKETING.
    payload = {
        "customerId": auth_data["customer_id"],
        "templateName": template_name,
        "wabaId": auth_data["waba_id"],
        "category": "MARKETING",
        "subAccountId": auth_data["sub_account_id"],
        "templateContent": content,
    }
    logger.info(
        f"Airtel create-template payload for '{template_name}': "
        f"{json.dumps(payload, ensure_ascii=False)}"
    )

    resp = requests.post(
        AIRTEL_CREATE_TEMPLATE_URL,
        headers=headers,
        data=json.dumps(payload),
        timeout=60,
    )
    logger.info(
        f"Airtel create-template response for '{template_name}': "
        f"{resp.status_code} - {resp.text}"
    )
    if not resp.ok:
        raise RuntimeError(
            f"Airtel create-template error for '{template_name}': "
            f"{resp.status_code} - {resp.text}"
        )

    template_id = (resp.json().get("template") or {}).get("templateId")
    if not template_id:
        raise RuntimeError(
            f"No templateId returned for '{template_name}': {resp.json()}"
        )
    return template_id, ordered_vars


def _fetch_campaign_objective(campaign_objective_id: str) -> dict:
    if not campaign_objective_id:
        return {}
    try:
        record = gryd.base_model.Model(
            "campaign_objective", AUTOCRM_APP_ENTERPRISE_ID
        ).get(campaign_objective_id)
        if record:
            return record
    except Exception as e:
        logger.warning(f"Gryd campaign_objective fetch failed, trying PG: {e}")
    records = pg.get(
        "campaign_objective", "campaign_objective_id", campaign_objective_id
    )
    if isinstance(records, list):
        return records[0] if records else {}
    return records or {}


def _post_template_record(
    template: dict,
    template_id: str,
    ordered_vars: List[str],
    credential: Optional[dict],
    campaign_objective: dict,
    dealership_id: str,
) -> None:
    """Best-effort: store a ``pending`` template record linked to the
    dealership/campaign objective so the approval poller can track it."""
    name_lower = (template.get("template_name") or "").lower()
    buttons = template.get("buttons") or []
    button_payloads = template.get("template_button_payloads") or [
        f"{name_lower}-{(b.get('buttonText') or b.get('text') or '').lower().replace(' ', '_')}"
        for b in buttons
        if isinstance(b, dict) and (b.get("buttonText") or b.get("text"))
    ]

    objective_name = campaign_objective.get("campaign_objective_name", "")
    record = {
        "template_id": template_id,
        "communication_credentials_id": (credential or {}).get(
            "communication_credentials_id"
        ),
        "channel": "whatsapp_chat",
        "status": "pending",
        "language": (template.get("language") or "english").lower(),
        "template_name": template.get("template_name"),
        "template_type": template.get(
            "template_type", "media" if _is_media_template(template) else "text"
        ),
        "template_message": template.get("template_message") or template.get("body"),
        "template_variables": template.get("template_variables") or ordered_vars,
        "buttons": buttons,
        "template_button_payloads": button_payloads,
        "campaign_type": template.get("campaign_type")
        or campaign_objective.get("campaign_type"),
        "campaign_objective": [objective_name] if objective_name
        else template.get("campaign_objective", []),
        "campaign_objective_name": objective_name,
        "dealership_id": dealership_id,
        "provider_name": (credential or {}).get("provider_name", "Airtel"),
    }
    for key in ("header", "footer", "media_type", "media_url"):
        if template.get(key):
            record[key] = template[key]

    gryd.base_model.Model("template", AUTOCRM_APP_ENTERPRISE_ID).post(record)
    logger.info(
        f"Posted template '{record['template_name']}' | id={template_id} (pending)"
    )


def _enqueue_approval_poll(
    template_ids: List[str], credential: Optional[dict]
) -> None:
    cred_id = (credential or {}).get("communication_credentials_id")
    if not template_ids or not cred_id:
        return
    try:
        gryd.await_result(
            task="update_disposition_template_approval",
            service=AUTOCRM_AGENT_SERVICE_NAME,
            kwargs={
                "template_ids": template_ids,
                "communication_credentials_id": cred_id,
            },
            gryd_logger=logger,
        )
        logger.info(f"Enqueued approval status poll for {len(template_ids)} template(s)")
    except Exception as e:
        logger.error(f"Failed to enqueue approval status poll: {e}")


# EXAMPLE PAYLOAD:
# {
#     "dealership_id": "daveai",
#     "campaign_objective_id": "pre-sales-test-drive-booking",
#     # optional: force a specific credential/provider instead of resolving by
#     # dealership_id (handy when a dealership has both Airtel and RML creds):
#     "communication_credential_id": "rml-whatsapp_chat-...",
#     "templates": [
#         {"template_name": "...", "template_message": "...", "buttons": [...]},
#         # Media template (image/video/document) with footer + CTA buttons.
#         # For RML, media_url is sent as the header *sample* value.
#         {"template_name": "...", "template_message": "...",
#          "media_type": "image", "media_url": "https://...", "footer": "...",
#          "buttons": [
#              {"type": "URL", "buttonText": "Visit", "url": "https://..."},
#              {"type": "PHONE_NUMBER", "buttonText": "Call", "phoneNumber": "+91..."}
#          ]}
#     ]
# }
@gryd.is_a_task(
    "bulk_send_templates_for_approval",
    logger_param="logger",
    job_param="job",
)
def bulk_send_templates_for_approval(
    dealership_id: Optional[str] = None,
    campaign_objective_id: Optional[str] = None,
    templates: Any = None,
    logger=None,
    job=None,
    **kwargs,
) -> List[str]:
    """Submit every supplied template for approval (Airtel or RML).

    The provider is auto-detected from the resolved ``communication_credential``
    (``provider_name``). Returns the list of provider ``templateId``s for the
    templates that were submitted successfully (failures are logged and
    skipped).
    """
    logger = logger or hp.get_logger(__name__)

    dealership_id = dealership_id or kwargs.get("dealership_id")
    campaign_objective_id = campaign_objective_id or kwargs.get("campaign_objective_id")
    templates = templates if templates is not None else kwargs.get("templates")
    communication_credential_id = kwargs.get("communication_credential_id")

    if not dealership_id and not communication_credential_id:
        raise ValueError(
            "dealership_id or communication_credential_id is required"
        )

    template_list = _coerce_templates(templates)
    if not template_list:
        logger.info("No templates supplied; nothing to submit.")
        return []

    credential = (
        _get_credential_by_id(communication_credential_id)
        if communication_credential_id
        else _resolve_airtel_credential(dealership_id)
    )
    provider = _detect_provider(credential)
    if not credential:
        logger.warning(
            f"No whatsapp_chat credential for dealership_id={dealership_id}; "
            f"using default Airtel account."
        )
    campaign_objective = _fetch_campaign_objective(campaign_objective_id)

    logger.info(
        f"Bulk submitting {len(template_list)} template(s) for approval | "
        f"provider={provider} | dealership_id={dealership_id} | "
        f"campaign_objective_id={campaign_objective_id} | "
        f"credential={(credential or {}).get('communication_credentials_id')}"
    )

    if provider == "rml":
        return _bulk_send_rml(
            template_list,
            credential,
            campaign_objective,
            dealership_id,
            logger,
        )

    auth_data = _resolve_auth_data(credential)
    headers = _build_headers(credential)

    template_ids: List[str] = []
    for index, template in enumerate(template_list):
        name = template.get("template_name", f"<index {index}>")
        try:
            template_id, ordered_vars = _submit_template_for_approval(
                template, auth_data, headers
            )
        except Exception as e:
            logger.error(f"Failed to submit template '{name}': {e}")
            continue

        template_ids.append(template_id)
        try:
            _post_template_record(
                template,
                template_id,
                ordered_vars,
                credential,
                campaign_objective,
                dealership_id,
            )
        except Exception as e:
            logger.error(
                f"Submitted '{name}' (id={template_id}) but failed to post record: {e}"
            )

    logger.info(
        f"Bulk approval submission done | submitted={len(template_ids)}/"
        f"{len(template_list)} | template_ids={template_ids}"
    )

    _enqueue_approval_poll(template_ids, credential)
    return template_ids


def _bulk_send_rml(
    template_list: List[dict],
    credential: Optional[dict],
    campaign_objective: dict,
    dealership_id: Optional[str],
    logger,
) -> List[str]:
    """Submit a batch of templates to Route Mobile (RML) for approval.

    Uses one ``RouteMobileTemplateMigrator`` for the whole batch so the JWT is
    minted once and reused. A login failure aborts the batch early (every
    template would hit the same auth wall). Stores ``media_url``, ``media_type``
    and ``template_type='media'`` on media template records.
    """
    cred_id = (credential or {}).get("communication_credentials_id")
    if not cred_id:
        logger.error(
            "RML provider requires a communication_credentials_id on the "
            "resolved credential; cannot submit."
        )
        return []

    migrator = RouteMobileTemplateMigrator(communication_credential_id=cred_id)

    template_ids: List[str] = []
    for index, template in enumerate(template_list):
        name = template.get("template_name", f"<index {index}>")
        try:
            template_id, ordered_vars, normalized_name = (
                _submit_rml_template_for_approval(template, migrator, credential)
            )
        except TemplateMigrationAbortError as abort:
            logger.error(
                f"RML batch aborted while submitting '{name}': "
                f"{abort.user_message}"
            )
            break
        except Exception as e:
            logger.error(f"Failed to submit RML template '{name}': {e}")
            continue

        template_ids.append(template_id)
        # Persist the normalized (RML-accepted) name so a later edit can find
        # the template by name.
        record_template = dict(template)
        record_template["template_name"] = normalized_name
        try:
            _post_template_record(
                record_template,
                template_id,
                ordered_vars,
                credential,
                campaign_objective,
                dealership_id,
            )
        except Exception as e:
            logger.error(
                f"Submitted RML '{normalized_name}' (id={template_id}) but "
                f"failed to post record: {e}"
            )

    logger.info(
        f"RML bulk approval submission done | submitted={len(template_ids)}/"
        f"{len(template_list)} | template_ids={template_ids}"
    )

    _enqueue_approval_poll(template_ids, credential)
    return template_ids
