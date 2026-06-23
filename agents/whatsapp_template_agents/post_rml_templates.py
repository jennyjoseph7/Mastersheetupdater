from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from agents.generic_template_migrator import (
        RouteMobileTemplateMigrator,
        WhatsAppTemplateMigrator,
    )
except ModuleNotFoundError as e:
    if e.name not in {"agents", "agents.generic_template_migrator"}:
        raise
    from generic_template_migrator import (  # type: ignore
        RouteMobileTemplateMigrator,
        WhatsAppTemplateMigrator,
    )

from config import AUTOCRM_APP_ENTERPRISE_ID, gryd, hp


logger = hp.get_logger("post_rml_templates")


_RML_PROVIDER_NAMES = {"rml"}


def _get_model(model_name: str):
    return gryd.base_model.Model(model_name, AUTOCRM_APP_ENTERPRISE_ID)


def _validate_inputs(template_data: dict, communication_credential_id: str) -> Optional[str]:
    if not isinstance(template_data, dict):
        return "template_data must be a dict"
    if not communication_credential_id:
        return "communication_credential_id is required"
    if not template_data.get("template_name"):
        return "template_name is required"
    if not template_data.get("template_message"):
        return "template_message is required"
    return None


def _resolve_template_variables(template_data: dict, ordered_vars: List[str]) -> List[str]:
    if (
        "template_variables" in template_data
        and template_data.get("template_variables") is not None
    ):
        return template_data.get("template_variables") or []
    return ordered_vars


def _copy_optional_fields(record: dict, template_data: dict) -> dict:
    optional_fields = (
        "buttons",
        "template_button_payloads",
        "campaign_type",
        "campaign_objective",
        "campaign_objective_name",
        "lead_tags",
        "disposition",
        "disposition_details",
    )
    for field in optional_fields:
        if field in template_data and template_data.get(field) is not None:
            record[field] = template_data[field]
    return record


def _build_template_record(
    template_data: dict,
    communication_credential_id: str,
    template_id: str,
    normalized_template_name: str,
    template_variables: List[str],
) -> dict:
    record = {
        "template_id": template_id,
        "communication_credentials_id": communication_credential_id,
        "channel": "whatsapp_chat",
        "status": "pending",
        "language": template_data.get("language", "english"),
        "template_name": normalized_template_name,
        "template_type": template_data.get("template_type", "text"),
        "template_message": template_data["template_message"],
        "template_variables": template_variables,
    }
    return _copy_optional_fields(record, template_data)


def post_rml_template_for_approval(
    template_data: dict, communication_credential_id: str
) -> Dict:
    """Submit one Route Mobile WhatsApp template for approval and post it to DB.

    Returns:
        Success:
            {
                "success": True,
                "template_id": "...",
                "template_variables": [...],
                "record": {...},
            }

        Failure:
            {"success": False, "error": "..."}
    """
    validation_error = _validate_inputs(template_data, communication_credential_id)
    if validation_error:
        logger.error(validation_error)
        return {"success": False, "error": validation_error}

    try:
        credential = _get_model("communication_credential").get(
            communication_credential_id
        )
    except Exception as e:
        logger.error(f"Failed to fetch communication credential: {e}")
        return {
            "success": False,
            "error": f"Failed to fetch communication credential: {e}",
        }

    if not credential:
        error = f"No credential found for id: {communication_credential_id}"
        logger.error(error)
        return {"success": False, "error": error}

    provider_name = (credential.get("provider_name") or "").strip().lower()
    if provider_name not in _RML_PROVIDER_NAMES:
        error = (
            f"Unsupported provider '{credential.get('provider_name')}' for "
            f"credential '{communication_credential_id}'. Expected provider 'rml'."
        )
        logger.error(error)
        return {"success": False, "error": error}

    migrator = RouteMobileTemplateMigrator(
        communication_credential_id=communication_credential_id
    )

    template_message = template_data["template_message"]
    ordered_vars = migrator._extract_ordered_variables(template_message)
    processed_message = migrator._process_message_variables(
        template_message, ordered_vars
    )
    template_variables = _resolve_template_variables(template_data, ordered_vars)

    lang_raw = (template_data.get("language") or "english").strip().capitalize()
    lang_code = WhatsAppTemplateMigrator.LANG_TO_CODE.get(lang_raw, "en")
    normalized_template_name = migrator._normalize_template_name(
        template_data["template_name"]
    )

    try:
        template_id = migrator._submit_to_rml(
            normalized_template_name,
            credential,
            processed_message,
            template_data.get("buttons") or [],
            ordered_vars,
            lang_code,
            category=template_data.get("campaign_type", "marketing"),
        )
    except Exception as e:
        logger.error(f"RML approval failed: {e}")
        return {"success": False, "error": f"RML approval failed: {e}"}

    if not template_id:
        error = "RML approval response did not include a template id"
        logger.error(error)
        return {"success": False, "error": error}

    record = _build_template_record(
        template_data,
        communication_credential_id,
        template_id,
        normalized_template_name,
        template_variables,
    )

    try:
        _get_model("template").post(record)
    except Exception as e:
        logger.error(f"Failed posting template to DB: {e}")
        return {
            "success": False,
            "error": f"Failed posting template to DB: {e}",
            "template_id": template_id,
            "record": record,
        }

    logger.info(
        f"Posted RML template '{normalized_template_name}' with id '{template_id}'"
    )
    return {
        "success": True,
        "template_id": template_id,
        "template_variables": template_variables,
        "record": record,
    }
