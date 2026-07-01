import os
import sys
from pprint import pprint

# agents/whatsapp_template_agents/<this file> → up three levels = project root
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
AGENTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if AGENTS_DIR not in sys.path:
    sys.path.insert(0, AGENTS_DIR)

try:
    from agents.base_agent import gryd
except ImportError:
    from base_agent import gryd

from autocrm_db_helper.PGConnector import AutoCRMPGConnector
pg = AutoCRMPGConnector(enterprise_id="autocrm")

try:
    from agents.whatsapp_template_agents.whatsapp_template_creator_agent import (
        WhatsappTemplateCreatorAgent,
    )
except ImportError:
    from whatsapp_template_creator_agent import WhatsappTemplateCreatorAgent

AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")


def _fetch_campaign_objective(campaign_objective_id):
    """Fetch the campaign_objective record for the given id."""
    record = pg.get(
        "campaign_objective",
        "campaign_objective_id",
        campaign_objective_id,
    )
    if isinstance(record, list):
        record = record[0] if record else None
    if not record:
        raise ValueError(
            f"campaign_objective not found for id='{campaign_objective_id}'"
        )
    return record


def _normalize_variable_set(variable_set):
    """Turn a single 'set of variables' entry into a clean list of attribute
    names. Accepts a tuple/list/set of strings or a single string."""
    if variable_set is None:
        return []
    if isinstance(variable_set, str):
        variable_set = [variable_set]
    elif isinstance(variable_set, (tuple, set)):
        variable_set = list(variable_set)
    elif not isinstance(variable_set, list):
        variable_set = [variable_set]

    cleaned = []
    seen = set()
    for attr in variable_set:
        if attr is None:
            continue
        name = str(attr).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        cleaned.append(name)
    return cleaned


@gryd.is_a_task('bulk_create_whatsapp_templates', logger_param='logger', job_param='job')
def bulk_create_whatsapp_templates(
    language=None,
    campaign_objective_id=None,
    dealership_id=None,
    template_variables=None,
    logger=None,
    job=None,
    **kwargs,
):
    """
    Create multiple WhatsApp templates in one shot — one template per set of
    template variables — WITHOUT posting to the DB or sending for approval.

    Args:
        language (str): Language to generate the templates in (e.g. "english").
        campaign_objective_id (str): The campaign objective id, resolved to its
            name and campaign_type from the campaign_objective model.
        dealership_id (str): The dealership the templates are created for.
        template_variables (list): A list of "sets" of variables, e.g.
            [("person_name",), ("person_name", "reg_number")]. One template is
            generated for each set, using exactly those variables.
        logger (Logger): The logger to use.
        job (Job): The job to use.

    Returns:
        dict: {
            "campaign_objective_id": ...,
            "campaign_objective_name": ...,
            "campaign_type": ...,
            "dealership_id": ...,
            "language": ...,
            "template_count": <n>,
            "templates": [
                {<template>, "campaign_type": ..., "dealership_id": ...,
                 "language": ..., "template_variables": [...]},
                ...
            ]
        }

    Note:
        This task ONLY generates templates so they can be previewed in the UI.
        It does NOT post to the DB or send for approval — that is handled by
        the ``bulk_send_templates_for_approval`` task in
        ``bulk_send_for_approval.py``. The ``templates`` list in the response
        is shaped to be passed straight into that task.
    """
    logger = logger or gryd.hp.get_logger(__name__)
    logger.info(
        "Bulk creating WhatsApp templates (create-only, no approval/db) | "
        f"dealership_id={dealership_id} | campaign_objective_id={campaign_objective_id} | "
        f"language={language}"
    )

    language = language or kwargs.get("language") or "english"
    campaign_objective_id = campaign_objective_id or kwargs.get("campaign_objective_id")
    dealership_id = dealership_id or kwargs.get("dealership_id")
    template_variables = template_variables or kwargs.get("template_variables")

    if not campaign_objective_id:
        logger.error("Validation failed: campaign_objective_id is missing")
        raise ValueError("campaign_objective_id must be provided")
    if not dealership_id:
        logger.error("Validation failed: dealership_id is missing")
        raise ValueError("dealership_id must be provided")
    if not template_variables or not isinstance(template_variables, (list, tuple)):
        logger.error(
            f"Validation failed: template_variables must be a non-empty list, "
            f"got {type(template_variables).__name__}: {template_variables!r}"
        )
        raise ValueError(
            "template_variables must be a non-empty list of variable sets, e.g. "
            "[('person_name',), ('person_name', 'reg_number')]"
        )

    logger.info(f"Received {len(template_variables)} variable set(s) to build templates for")

    logger.info(f"Fetching campaign objective record for id '{campaign_objective_id}'")
    campaign_objective_record = _fetch_campaign_objective(campaign_objective_id)
    campaign_objective_name = campaign_objective_record.get("campaign_objective_name", "")
    if not campaign_objective_name:
        logger.error(
            f"campaign_objective '{campaign_objective_id}' has no campaign_objective_name"
        )
        raise ValueError(
            f"campaign_objective '{campaign_objective_id}' has no campaign_objective_name"
        )
    campaign_type = campaign_objective_record.get("campaign_type", "")
    cta_buttons = campaign_objective_record.get("ctas", []) or []

    logger.info(
        f"Resolved campaign objective '{campaign_objective_name}' "
        f"(campaign_type='{campaign_type}', ctas={cta_buttons}) "
        f"from id '{campaign_objective_id}'"
    )

    templates = []
    total = len(template_variables)
    for idx, variable_set in enumerate(template_variables, start=1):
        attribute_names = _normalize_variable_set(variable_set)
        logger.info(
            f"[{idx}/{total}] Generating template with variables: {attribute_names}"
        )

        user_data = {
            "campaign_type": campaign_type,
            "campaign_objective": campaign_objective_name,
            "dealership_id": dealership_id,
            "languages": [language],
            "data": {"attribute_name": attribute_names},
            "cta_buttons": cta_buttons,
        }

        try:
            agent = WhatsappTemplateCreatorAgent(source=user_data, logger=logger)
            result = agent.run()
        except Exception as e:
            logger.error(
                f"[{idx}/{total}] Template generation failed for variables "
                f"{attribute_names}: {e}"
            )
            raise

        # Enrich each template so it can be fed directly into
        # bulk_send_templates_for_approval (which reads these keys).
        result["template_variables"] = attribute_names
        result["campaign_type"] = campaign_type
        result["campaign_objective"] = campaign_objective_name
        result["dealership_id"] = dealership_id
        result["language"] = language

        logger.info(
            f"[{idx}/{total}] Generated template '{result.get('template_name')}'"
        )
        templates.append(result)

    response = {
        "campaign_objective_id": campaign_objective_id,
        "campaign_objective_name": campaign_objective_name,
        "campaign_type": campaign_type,
        "dealership_id": dealership_id,
        "language": language,
        "template_count": len(templates),
        "templates": templates,
    }

    logger.info(
        f"Bulk template creation complete | generated={len(templates)}/{total} "
        f"template(s) | names={[t.get('template_name') for t in templates]}"
    )
    return response


if __name__ == "__main__":
    result = bulk_create_whatsapp_templates(
        language="english",
        campaign_objective_id="pre-sales-test-drive-booking",
        dealership_id="dave-ai-india",
        template_variables=[("person_name",), ("person_name", "reg_number")],
    )
    pprint(result)

    # The generated templates can be handed off (as-is) to the approval task,
    # which is responsible for posting to the DB and sending for approval:
    #
    #   from agents.whatsapp_template_agents.bulk_send_for_approval import (
    #       bulk_send_templates_for_approval,
    #   )
    #   bulk_send_templates_for_approval(
    #       dealership_id=result["dealership_id"],
    #       campaign_objective_id=result["campaign_objective_id"],
    #       templates=result["templates"],
    #   )
