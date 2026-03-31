import json
import os, sys
import re
import random

try:
    from .base_agent import BaseAgent#, gryd
except ImportError:
    from base_agent import BaseAgent#, gryd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config import  AUTOCRM_AGENT_SERVICE_NAME, gryd, hp
gryd.SERVICE = AUTOCRM_AGENT_SERVICE_NAME
gryd.set_queue_manager()

from autocrm_db_helper.PGConnector import AutoCRMPGConnector
pg = AutoCRMPGConnector(enterprise_id="autocrm")

from agents.data_attributes_retriever_agent import data_attribute_retriever

from pprint import pprint



class get_rcs_template_agent(BaseAgent):
    def __init__(self, source, *args, **kwargs):
        super().__init__(**kwargs)

        if not source or not isinstance(source, dict):
            raise ValueError("source must be a non-empty dictionary")

        self.source = source
        self.template_variables = source.get("template_variables", [])
        self.campaign_type = source.get("campaign_type","")
        self.campaign_objective = source.get("campaign_objective",[])
        self.dealership_id = source.get("dealership_id","daveai")
        self.is_disposition = source.get("is_disposition", False)
        if self.is_disposition:
            self.disposition = source.get("disposition", "")
            self.disposition_details = source.get("disposition_details", "")
        self.language = source.get("language", "english")
        self.limit = 1

        if not isinstance(self.template_variables, list):
            raise ValueError("template_variables must be a list")
        if not isinstance(self.campaign_objective, list):
            raise ValueError("campaign_objective must be a list")
        if self.campaign_objective == []:
            raise ValueError("campaign_objective cannot be empty")

    def retrieve_credentials(self,dealership_id):
        records = list(pg.list(
            table_name="communication_credential",
            where={"dealership_id": dealership_id,
                   'channel': 'rcs'
            }
        ))
        communication_credential = records[0]
        communication_credentials_id = communication_credential.get("communication_credentials_id")
        return communication_credentials_id


    def slugify_disposition_detail(self,detail: str) -> str:
        """'Cannot make decision on servicing' → 'Cannot-make-decision-on-servicing'"""
        return re.sub(r"[\s_]+", "-", detail.strip().lower())

    def pick_from_model(self,communication_credentials_id):

        if self.is_disposition :
            records = list(pg.list(
                table_name="template",
                where={"campaign_type": self.campaign_type,
                       "campaign_objective_name" : self.campaign_objective[0],
                       "template_type" : "rcs",
                        "channel" : "rcs",
                        "status" : "approved",
                        "communication_credentials_id" : communication_credentials_id,
                        "language" : self.language,
                        "disposition" : self.disposition,
                        "disposition_details" : self.slugify_disposition_detail(self.disposition_details)
                }
            ))
        else:
            records = list(pg.list(
                table_name="template",
                where={"campaign_type": self.campaign_type,
                       "campaign_objective_name" : self.campaign_objective[0],
                       "template_type" : "rcs",
                       "channel" : "rcs",
                       "status" : "approved",
                       "communication_credentials_id" : communication_credentials_id,
                       "language" : self.language
                }
            ))

        #print("records",records)

        return records or []
    

    def normalize_vars(self, tpl_vars):
        if isinstance(tpl_vars, list):
            return tpl_vars
        
        print("tpl_vars",tpl_vars)

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

        print("data_attrs_list", data_attrs_list)

        if not isinstance(data_attrs_list, list):
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



@gryd.is_a_task('get_rcs_template', logger_param='logger', job_param='job')
def get_rcs_template(lead_info=None, lead_id=None, campaign_type=None, campaign_objective=None, dealership_id=None, is_disposition=None, disposition=None, disposition_details=None,language = None, logger=None, job=None, **kwargs):

        logger = logger or gryd.hp.get_logger(__name__)
        logger.info("Getting RCS Template...")
        if dealership_id is None:
            dealership_id = 'daveai'

        if is_disposition and (not disposition or not disposition_details):
            raise ValueError("disposition and disposition_details must be provided when is_disposition is True")

        try:
            lead_info = lead_info or {}
            lead_info.update({k: v for k, v in kwargs.items() if v is not None})
            updates = {
                "id": lead_id,
                "campaign_type": campaign_type,
                "is_disposition": is_disposition
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

            logger.info(f"Template variables : {attribute_list_sets}")

            data = {
                "campaign_type": campaign_type,
                "template_variables": attribute_list_sets,
                "campaign_objective" : campaign_objective,
                "dealership_id" : dealership_id,
                "is_disposition": is_disposition,
                "disposition": disposition or "",
                "disposition_details": disposition_details or "",
                "language": language or "english"
            }

            logger.info(f"Source data : {data}")

            # 2. Template Selector Agent
            template_agent = get_rcs_template_agent(source=data, logger=logger)
            result = template_agent.run()

            if not result:
                return "No template found for this input"

            return result

        except Exception as e:
            logger.error(f"Template retrieval failed: {str(e)}")
            raise