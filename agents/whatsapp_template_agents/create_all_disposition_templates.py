"""Create disposition templates for EVERY standard scenario in one shot.

Convenience wrapper around ``disposition_templates_creator``. Instead of firing
the ``create_disposition_templates`` task once per disposition, this task runs
the creator for the full, fixed set of standard disposition scenarios — so a
single call generates, submits for provider approval, and posts the complete
disposition template suite for a campaign objective.

Scenarios mirror ``conversation/lead_post_processing.py`` for pre-sales and
post-sales (same labels in both blocks today). The set is chosen from the
campaign objective's ``campaign_type``. Excludes ``NO RESPONSE`` and
``INVALID LEAD`` from template creation.
"""

import os
import sys
from typing import Any, Dict, List, Optional

# agents/whatsapp_template_agents/<this file>  →  up three levels = project root
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import AUTOCRM_SHORT_RUN_AGENT_SERVICE_NAME, gryd, hp

gryd.SERVICE = AUTOCRM_SHORT_RUN_AGENT_SERVICE_NAME
gryd.set_queue_manager()
logger = hp.get_logger(gryd.SERVICE)

from autocrm_db_helper.PGConnector import AutoCRMPGConnector

pg = AutoCRMPGConnector(enterprise_id="autocrm")

try:
    from agents.whatsapp_template_agents.disposition_templates_creator import (
        DispositionTemplatesCreator,
        build_disposition_scenarios,
    )
except ImportError:
    from whatsapp_template_agents.disposition_templates_creator import (  # type: ignore
        DispositionTemplatesCreator,
        build_disposition_scenarios,
    )


def _fetch_campaign_type(campaign_objective_id: str) -> str:
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
    return record.get("campaign_type") or "pre-sales"


def _build_scenarios(campaign_type: str) -> List[Dict[str, str]]:
    """(disposition, disposition_details) pairs for the given campaign type."""
    return build_disposition_scenarios(campaign_type)


def _run_one_scenario(
    base_source: Dict[str, Any], scenario: Dict[str, str]
) -> Dict[str, Any]:
    """Run the disposition creator once for a single scenario."""
    source = {
        **base_source,
        "disposition": scenario["disposition"],
        "disposition_details": scenario["disposition_details"],
    }
    agent = DispositionTemplatesCreator(source=source, logger=logger)
    templates = agent.run()
    return {
        "disposition": scenario["disposition"],
        "disposition_details": scenario["disposition_details"],
        "templates_created": len(templates or []),
        "template_ids": [
            t.get("template_id")
            for t in (templates or [])
            if isinstance(t, dict) and t.get("template_id")
        ],
    }


# EXAMPLE PAYLOAD:
# {
#     "campaign_objective_id": "post-sales-free-service-due-reminder-ambal-auto-south-india",
#     "dealership_id": "daveai",
#     "languages": ["English", "Hindi"]
#     # "communication_credential_id": "airtel-whatsapp_chat-917795030574"  (optional)
# }
@gryd.is_a_task(
    "create_all_disposition_templates",
    logger_param="logger",
    job_param="job",
)
def create_all_disposition_templates(
    campaign_objective_id: Optional[str] = None,
    dealership_id: Optional[str] = None,
    languages: Any = None,
    communication_credential_id: Optional[str] = None,
    logger=None,
    job=None,
    **kwargs,
) -> Dict[str, Any]:
    """Run the disposition template creator across every standard scenario.

    Scenarios are resolved from the campaign objective's campaign_type
    (pre-sales or post-sales). Each scenario is best-effort: a failure is
    logged and skipped so the rest of the suite still gets created.
    """
    logger = logger or hp.get_logger(__name__)

    campaign_objective_id = campaign_objective_id or kwargs.get("campaign_objective_id")
    dealership_id = dealership_id or kwargs.get("dealership_id")
    languages = languages if languages is not None else kwargs.get("languages")
    communication_credential_id = communication_credential_id or kwargs.get(
        "communication_credential_id"
    )

    if not campaign_objective_id:
        raise ValueError("campaign_objective_id is required")
    if not dealership_id:
        raise ValueError("dealership_id is required")
    if not languages:
        raise ValueError("languages is required (string or non-empty list)")

    campaign_type = _fetch_campaign_type(campaign_objective_id)

    base_source: Dict[str, Any] = {
        "campaign_objective_id": campaign_objective_id,
        "dealership_id": dealership_id,
        "languages": languages,
    }
    if communication_credential_id:
        base_source["communication_credential_id"] = communication_credential_id

    scenarios = _build_scenarios(campaign_type)
    logger.info(
        f"Creating ALL disposition templates | "
        f"campaign_objective_id={campaign_objective_id} | "
        f"campaign_type={campaign_type} | "
        f"dealership_id={dealership_id} | languages={languages} | "
        f"scenarios={len(scenarios)}"
    )

    results: List[Dict[str, Any]] = []
    failures: List[Dict[str, str]] = []
    for index, scenario in enumerate(scenarios, start=1):
        details = scenario["disposition_details"]
        logger.info(
            f"[{index}/{len(scenarios)}] Running disposition scenario | "
            f"disposition={scenario['disposition']} | disposition_details='{details}'"
        )
        try:
            results.append(_run_one_scenario(base_source, scenario))
        except Exception as e:
            logger.error(
                f"Scenario '{details}' (disposition={scenario['disposition']}) failed: {e}"
            )
            failures.append(
                {
                    "disposition": scenario["disposition"],
                    "disposition_details": details,
                    "error": str(e),
                }
            )

    total_templates = sum(r["templates_created"] for r in results)
    logger.info(
        f"Done creating all disposition templates | "
        f"scenarios_succeeded={len(results)}/{len(scenarios)} | "
        f"templates_created={total_templates} | failures={len(failures)}"
    )

    return {
        "campaign_objective_id": campaign_objective_id,
        "campaign_type": campaign_type,
        "dealership_id": dealership_id,
        "languages": languages,
        "scenarios_total": len(scenarios),
        "scenarios_succeeded": len(results),
        "templates_created": total_templates,
        "results": results,
        "failures": failures,
    }
