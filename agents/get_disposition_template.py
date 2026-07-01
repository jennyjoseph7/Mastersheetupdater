import json
import os, sys
import re
import time

try:
    from .base_agent import BaseAgent
except ImportError:
    from base_agent import BaseAgent

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# NOTE: disposition_templates_creator sets gryd.SERVICE to the agent service at
# import time, so it is imported BEFORE we configure our own service below.
try:
    from agents.whatsapp_template_agents.disposition_templates_creator import (
        DispositionTemplatesCreator,
        KNOWN_DISPOSITION_CASES,
    )
except ImportError:
    from whatsapp_template_agents.disposition_templates_creator import (  # type: ignore
        DispositionTemplatesCreator,
        KNOWN_DISPOSITION_CASES,
    )

try:
    from agents.whatsapp_template_agents.disposition_template_approval_updator import (
        _check_and_update_templates,
    )
except ImportError:
    from whatsapp_template_agents.disposition_template_approval_updator import (  # type: ignore
        _check_and_update_templates,
    )

from config import AUTOCRM_AGENT_SERVICE_NAME, gryd, hp

gryd.SERVICE = AUTOCRM_AGENT_SERVICE_NAME
gryd.set_queue_manager()
logger = gryd.hp.get_logger(gryd.SERVICE)

from autocrm_db_helper.PGConnector import AutoCRMPGConnector
pg = AutoCRMPGConnector(enterprise_id="autocrm")

from agents.data_attributes_retriever_agent import data_attribute_retriever

from pprint import pprint


# Synchronous approval wait settings (provider approval is usually quick,
# but can take a while — poll until approved/rejected or timeout).
APPROVAL_FIRST_CHECK_SECONDS = 60
APPROVAL_POLL_INTERVAL_SECONDS = 120
APPROVAL_WAIT_TIMEOUT_SECONDS = 30 * 60


def _slugify(text: str) -> str:
    """'Language Barrier' → 'language-barrier'"""
    return re.sub(r"[\s_]+", "-", (text or "").strip().lower())


class get_disposition_template_agent(BaseAgent):
    """
    Finds an approved disposition template in the template model that best
    matches the lead's data attributes (same matching strategy as
    get_whatsapp_template_agent, but always disposition-scoped).
    """

    def __init__(self, source, *args, **kwargs):
        super().__init__(**kwargs)

        if not source or not isinstance(source, dict):
            raise ValueError("source must be a non-empty dictionary")

        self.source = source
        self.template_variables = source.get("template_variables", [])
        self.campaign_type = source.get("campaign_type", "")
        self.campaign_objective = source.get("campaign_objective", [])
        self.dealership_id = source.get("dealership_id", "daveai")
        self.disposition = (source.get("disposition") or "").strip().lower()
        # Kept as the raw normalized input; slugified at query time in
        # stored_disposition_filters() to match the stored slug format.
        self.disposition_details = (source.get("disposition_details") or "").strip().lower()
        self.language = source.get("language", "english")
        self.limit = 1

        if not self.disposition_details:
            raise ValueError("disposition_details is required for disposition templates")
        if not isinstance(self.template_variables, list):
            raise ValueError("template_variables must be a list")
        if not isinstance(self.campaign_objective, list):
            raise ValueError("campaign_objective must be a list")
        if self.campaign_objective == []:
            raise ValueError("campaign_objective cannot be empty")

    def retrieve_credentials(self, dealership_id):
        records = list(pg.list(
            table_name="communication_credential",
            where={"dealership_id": dealership_id,
                   'channel': 'whatsapp_chat'
            }
        ))
        if not records:
            raise ValueError(
                f"No whatsapp_chat credential found for dealership_id={dealership_id}"
            )
        communication_credential = records[0]
        communication_credentials_id = communication_credential.get("communication_credentials_id")
        print("communication_credentials_id", communication_credentials_id)
        return communication_credentials_id

    def slugify_disposition_detail(self, detail: str) -> str:
        """'Will call themself' → 'will-call-themself' (matches stored format)."""
        return _slugify(detail)

    def stored_disposition_filters(self):
        """
        Templates store ``disposition`` lowercased and ``disposition_details``
        slugified (e.g. "will-call-themself"), so the DB search slugifies
        disposition_details here before it goes into pick_from_model.
        """
        return {
            "disposition": self.disposition,
            "disposition_details": self.slugify_disposition_detail(self.disposition_details),
        }

    def pick_from_model(self, communication_credentials_id):
        where = {
            "campaign_type": self.campaign_type,
            "campaign_objective_name": self.campaign_objective[0],
            "channel": "whatsapp_chat",
            "status": "approved",
            "communication_credentials_id": communication_credentials_id,
        }
        where.update(self.stored_disposition_filters())

        logger.info(f"Querying templates with filters:", where)

        records = list(pg.list(table_name="template", where=where))

        # Language is stored with inconsistent casing ('Hindi' vs 'hindi'),
        # so filter it case-insensitively in python instead of in the query.
        wanted_language = (self.language or "english").strip().lower()
        records = [
            r for r in records
            if (r.get("language") or "").strip().lower() == wanted_language
        ]

        logger.info(f"Retrieved records: {records}")

        return records or []

    def normalize_vars(self, tpl_vars):
        if isinstance(tpl_vars, list):
            return tpl_vars

        logger.info(f"Processing template variables: {tpl_vars}")

        if isinstance(tpl_vars, str):
            # Postgres array "{a,b,c}"
            if tpl_vars.startswith("{") and tpl_vars.endswith("}"):
                return tpl_vars.strip("{}").split(",")

            # JSON list string
            try:
                return json.loads(tpl_vars)
            except:
                pass

        return []

    def match_templates_strict(self, templates):
        limit = self.limit

        # template_variables is a list of lists - process each list
        data_attrs_list = self.template_variables or []

        logger.info(f"data_attrs_list: {data_attrs_list}")

        if not isinstance(data_attrs_list, list):
            data_attrs_list = [data_attrs_list]

        # If it's a flat list of strings (single attribute set), wrap it so
        # the loop below treats it as one set instead of N single-element sets.
        if data_attrs_list and all(isinstance(item, str) for item in data_attrs_list):
            data_attrs_list = [data_attrs_list]

        all_results = []

        # Process each attribute set in data_attrs_list
        for data_attrs_raw in data_attrs_list:
            # Normalize current attribute set
            data_attrs = set(data_attrs_raw) if isinstance(data_attrs_raw, list) else set([data_attrs_raw])

            exact_matches = []          # variables match exactly
            var_near_matches = []       # variables near
            no_vars_matches = []        # no variables

            for tpl in templates:
                # ---- Template Variable Processing ----
                tpl_vars_raw = tpl.get("template_variables", [])
                tpl_vars = self.normalize_vars(tpl_vars_raw)
                tpl_set = set(tpl_vars)

                # Reject templates with extra variables not in input
                if tpl_set and not tpl_set.issubset(data_attrs):
                    continue

                # Determine variable match type
                var_exact = tpl_set == data_attrs and tpl_set
                var_near = bool(tpl_set & data_attrs) if tpl_set else False
                var_none = not tpl_set

                # Calculate overlap for sorting near matches
                overlap = len(tpl_set & data_attrs) if tpl_set else 0

                # ---- Categorize by Variable Match Quality ----
                if var_exact:
                    exact_matches.append(tpl)
                elif var_near:
                    var_near_matches.append((overlap, tpl))
                elif var_none:
                    no_vars_matches.append(tpl)

            # ---- Collect Results in Priority Order for this attribute set ----
            current_results = []

            # 1. Exact variable matches
            if exact_matches:
                current_results.extend(exact_matches[:limit])
            # 2. Variable near matches (sorted by overlap)
            elif var_near_matches:
                var_near_matches.sort(key=lambda x: x[0], reverse=True)
                current_results.extend([tpl for _, tpl in var_near_matches][:limit])
            # 3. No variable templates
            elif no_vars_matches:
                current_results.extend(no_vars_matches[:limit])

            all_results.extend(current_results)

        # Remove duplicates while preserving order and apply limit
        seen = set()
        unique_results = []
        for tpl in all_results:
            tpl_id = tpl.get("template_id", id(tpl))
            if tpl_id not in seen:
                seen.add(tpl_id)
                unique_results.append(tpl)
                if len(unique_results) >= limit:
                    break

        return unique_results

    def run(self):
        communication_credentials_id = self.retrieve_credentials(self.dealership_id)
        all_templates = self.pick_from_model(communication_credentials_id)
        best = self.match_templates_strict(all_templates)
        return best


class LocalDispositionTemplatesCreator(DispositionTemplatesCreator):
    """
    Local override of DispositionTemplatesCreator (the original file is left
    untouched): creation + provider approval submission stay the same, but the
    fire-and-forget approval poll task is skipped — this module waits for
    approval synchronously instead.
    """

    def run(self):
        return self.create_disposition_templates()


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


def _wait_for_template_approval(template_ids, communication_credentials_id, logger):
    """
    Synchronously poll the provider (Airtel/RML) for approval of the given
    template ids, updating the template model status along the way.
    Returns the ids that are still pending when the wait ends.
    """
    credential = pg.get(
        "communication_credential",
        "communication_credentials_id",
        communication_credentials_id,
    )
    if isinstance(credential, list):
        credential = credential[0] if credential else None
    if not credential:
        raise ValueError(
            f"communication_credential not found: {communication_credentials_id}"
        )

    pending = [tid for tid in (template_ids or []) if tid]
    if not pending:
        return []

    deadline = time.time() + APPROVAL_WAIT_TIMEOUT_SECONDS
    logger.info(
        f"Waiting for approval of {len(pending)} template(s) | "
        f"first check in {APPROVAL_FIRST_CHECK_SECONDS}s | "
        f"timeout {APPROVAL_WAIT_TIMEOUT_SECONDS}s"
    )
    time.sleep(APPROVAL_FIRST_CHECK_SECONDS)

    round_num = 1
    while pending and time.time() < deadline:
        logger.info(f"Approval check round {round_num}: {len(pending)} pending")
        pending = _check_and_update_templates(pending, credential, logger)
        if not pending:
            break
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        time.sleep(min(APPROVAL_POLL_INTERVAL_SECONDS, remaining))
        round_num += 1

    if pending:
        logger.warning(f"Approval wait ended with {len(pending)} still pending: {pending}")
    else:
        logger.info("All created templates resolved (approved/rejected/error).")
    return pending


def _fetch_approved_templates(template_ids):
    """Fetch the created template records that ended up approved."""
    approved = []
    for template_id in template_ids or []:
        record = pg.get("template", "template_id", template_id)
        if isinstance(record, list):
            record = record[0] if record else None
        if record and record.get("status") == "approved":
            approved.append(record)
    return approved


@gryd.is_a_task('get_disposition_template', logger_param='logger', job_param='job')
def get_disposition_template(lead_info=None, lead_id=None, campaign_objective_id=None, campaign_type=None, dealership_id=None, disposition=None, disposition_details=None, language=None, logger=None, job=None, **kwargs):
    """
    1. Resolve campaign objective name/type from campaign_objective_id.
    2. Search the template model for an approved disposition template.
    3. If none exists, create one via DispositionTemplatesCreator (submitted
       to the provider for approval).
    4. Wait for provider approval, updating the template model status.
    5. Return the approved template record(s) (each contains template_id).
    """
    logger = logger or gryd.hp.get_logger(__name__)
    logger.info("Getting Disposition Template...")

    if dealership_id is None:
        dealership_id = 'daveai'
    language = language or "english"

    if not campaign_objective_id:
        raise ValueError("campaign_objective_id must be provided")
    if not disposition_details:
        raise ValueError("disposition_details must be provided")
    if not disposition:
        # Derive the expected disposition for known cases
        # (e.g. 'language barrier' → 'engaged', 'converted' → 'converted')
        config = KNOWN_DISPOSITION_CASES.get(_slugify(disposition_details))
        if not config:
            raise ValueError("disposition must be provided")
        disposition = config["expected_disposition"]

    try:
        # 0. Derive objective name (and campaign_type) from the objective id
        campaign_objective_record = _fetch_campaign_objective(campaign_objective_id)
        campaign_objective_name = campaign_objective_record.get("campaign_objective_name", "")
        if not campaign_objective_name:
            raise ValueError(
                f"campaign_objective '{campaign_objective_id}' has no campaign_objective_name"
            )
        campaign_type = campaign_type or campaign_objective_record.get("campaign_type", "")
        logger.info(
            f"Resolved campaign objective '{campaign_objective_name}' "
            f"(campaign_type='{campaign_type}') from id '{campaign_objective_id}'"
        )

        lead_info = lead_info or {}
        lead_info.update({k: v for k, v in kwargs.items() if v is not None})
        updates = {
            "id": lead_id,
            "campaign_type": campaign_type,
            "is_disposition": True
        }

        for k, v in updates.items():
            if v is not None:
                lead_info[k] = v

        # 1. Run Data Attribute Retriever
        attribute_agent = data_attribute_retriever(source=lead_info, logger=logger)
        attribute_list_sets = attribute_agent.run()

        logger.info(f"attribute list sets --{attribute_list_sets}")

        if not attribute_list_sets:
            raise ValueError("No attribute sets extracted by data_attribute_retriever")

        # attribute_list_sets is already filtered by data_attribute_retriever
        # (drops *_id, phone_number, disposition, workshop_*, etc.), so the
        # variable matching only considers relevant attributes.
        data = {
            "campaign_type": campaign_type,
            "template_variables": attribute_list_sets,
            "campaign_objective": [campaign_objective_name],
            "dealership_id": dealership_id,
            "is_disposition": True,
            "disposition": disposition,
            "disposition_details": disposition_details,
            "language": language,
        }

        logger.info(f"Source data : {data}")

        # 2. Reuse the proven WhatsApp retrieval (disposition-scoped): it filters
        # on campaign/disposition/credential/language and matches against the
        # already-filtered variables. Only create if it finds no template.
        # Lazy import: get_whatsapp_template_agent sets gryd.SERVICE to the
        # short-run worker at import time, which would mis-register this task.
        from agents.whatsapp_template_agents.get_whatsapp_template_agent import (
            get_whatsapp_template_agent,
        )

        template_agent = get_whatsapp_template_agent(source=data, logger=logger)
        result = template_agent.run()

        if result:
            logger.info(f"Found existing disposition template: {result[0].get('template_id')}")
            return result

        # 3. None found — create disposition templates and submit for approval
        logger.info("No approved disposition template found; creating new templates...")

        creator = LocalDispositionTemplatesCreator(
            source={
                "campaign_objective_id": campaign_objective_id,
                "disposition": disposition,
                "disposition_details": disposition_details,
                "dealership_id": dealership_id,
                "languages": [language],
                # Constrain generated templates to the lead's actual attributes so
                # no template references a variable the lead doesn't have.
                "lead_attributes": attribute_list_sets,
            },
            logger=logger,
        )
        created = creator.run()

        created_template_ids = [
            r.get("template_id") for r in (created or [])
            if isinstance(r, dict) and r.get("template_id")
        ]
        if not created_template_ids:
            raise RuntimeError("Disposition template creation returned no template ids")

        logger.info(f"Created {len(created_template_ids)} template(s): {created_template_ids}")

        # 4. Wait for provider approval (updates template model status too)
        still_pending = _wait_for_template_approval(
            created_template_ids,
            creator.communication_credential_id,
            logger,
        )

        # 5. Re-run the search — newly approved templates are now in the model
        result = template_agent.run()
        if result:
            logger.info(f"Returning approved disposition template: {result[0].get('template_id')}")
            return result

        # Strict variable matching may not align with the created variable
        # sets — fall back to any approved template we just created.
        approved_created = _fetch_approved_templates(created_template_ids)
        if approved_created:
            logger.info(
                f"Returning approved created template: {approved_created[0].get('template_id')}"
            )
            return approved_created[:template_agent.limit]

        return {
            "status": "pending",
            "message": "Templates created and submitted for approval, "
                       "but none were approved within the wait window",
            "created_template_ids": created_template_ids,
            "pending_template_ids": still_pending,
        }

    except Exception as e:
        logger.error(f"Disposition template retrieval failed: {str(e)}")
        raise
