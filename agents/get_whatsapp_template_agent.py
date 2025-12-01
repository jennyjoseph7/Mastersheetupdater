import json
import os, sys
import random

try:
    from .base_agent import BaseAgent, gryd
except ImportError:
    from base_agent import BaseAgent, gryd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from autocrm_db_helper.PGConnector import AutoCRMPGConnector
pg = AutoCRMPGConnector(enterprise_id="autocrm")

from agents.data_attributes_retriever_agent import data_attribute_retriever

from pprint import pprint



class get_whatsapp_template_agent(BaseAgent):
    def __init__(self, source, *args, **kwargs):
        super().__init__(**kwargs)

        if not source or not isinstance(source, dict):
            raise ValueError("source must be a non-empty dictionary")

        self.source = source
        self.template_variables = source.get("template_variables", [])
        self.campaign_type = source.get("campaign_type")

        if not isinstance(self.template_variables, list):
            raise ValueError("template_variables must be a list")


    def pick_from_model(self):

        records = list(pg.list(
            table_name="template",
            where={"campaign_type": self.campaign_type}
        ))

        print("records",records)

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

        limit = 1
        data_attrs = set(self.template_variables)

        print("data_attrs",data_attrs)

        exact_matches = []
        near_matches = []

        for tpl in templates:
            tpl_vars_raw = tpl.get("template_variables", [])
            tpl_vars = self.normalize_vars(tpl_vars_raw)
            tpl_set = set(tpl_vars)

            # Reject templates that contain variables not in data
            if not tpl_set.issubset(data_attrs):
                continue

            # Exact match
            if tpl_set == data_attrs:
                exact_matches.append(tpl)
            else:
                overlap = len(tpl_set.intersection(data_attrs))
                near_matches.append((overlap, tpl))

        if exact_matches:
            if len(exact_matches) > limit:
                return random.sample(exact_matches, limit)
            return exact_matches

        if near_matches:
            max_overlap = max([ov for ov, _ in near_matches])
            best = [tpl for ov, tpl in near_matches if ov == max_overlap]
            if len(best) > limit:
                return random.sample(best, limit)
            return best

        return []


    def run(self):
        all_templates = self.pick_from_model()
        best = self.match_templates_strict(all_templates)
        return best



@gryd.is_a_task('get_whatsapp_template', logger_param='logger', job_param='job')
def get_whatsapp_template(lead_info=None, lead_id=None, campaign_type=None, logger=None, job=None):

        logger = logger or gryd.hp.get_logger(__name__)
        logger.info("Getting WhatsApp Template...")

        try:
            lead_info = lead_info or {}
            updates = {
                "id": lead_id,
                "campaign_type": campaign_type
            }

            for k, v in updates.items():
                if v is not None:
                    lead_info[k] = v

            # 1. Run Data Attribute Retriever
            attribute_agent = data_attribute_retriever(source=lead_info, logger=logger)
            attribute_list_sets = attribute_agent.run()

            print("attribute list sets",attribute_list_sets)

            if not attribute_list_sets:
                raise ValueError("No attribute sets extracted by data_attribute_retriever")

            # Only first attribute set is required
            data_attributes = attribute_list_sets[0]

            data = {
                "campaign_type": campaign_type,
                "template_variables": data_attributes
            }

            # 2. Template Selector Agent
            template_agent = get_whatsapp_template_agent(source=data, logger=logger)
            result = template_agent.run()

            return result

        except Exception as e:
            logger.error(f"Template retrieval failed: {str(e)}")
            raise
