import json
import os, sys
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



class get_whatsapp_template_agent(BaseAgent):
    def __init__(self, source, *args, **kwargs):
        super().__init__(**kwargs)

        if not source or not isinstance(source, dict):
            raise ValueError("source must be a non-empty dictionary")

        self.source = source
        self.template_variables = source.get("template_variables", [])
        #self.template_variables = self.template_variables[0]
        self.campaign_type = source.get("campaign_type","")
        self.campaign_objective = source.get("campaign_objective",[])
        #self.dealership_id = source.get("dealership_id","daveai")
        self.limit = 1

        if not isinstance(self.template_variables, list):
            raise ValueError("template_variables must be a list")

    # def retrieve_credentials(self,dealership_id):
    #     records = list(pg.list(
    #         table_name="communication_credential",
    #         where={"dealership_id": dealership_id,
    #         }
    #     ))
    #     communication_credential = records[0]
    #     communication_credentials_id = communication_credential.get("communication_credentials_id")
    #     return communication_credentials_id


    def pick_from_model(self):

        records = list(pg.list(
            table_name="template",
            where={"campaign_type": self.campaign_type,
                   "template_type" : "text",
                   "channel" : "whatsapp_chat",
                   "status" : "approved",
                   #"communication_credentials_id" : communication_credentials_id
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

        # Normalize input objectives: strip whitespace and convert to lowercase
        input_objectives = set(
            obj.strip().lower() if isinstance(obj, str) else obj
            for obj in (self.campaign_objective or [])
        )
        print("input_objectives",input_objectives)
        # template_variables is a list of lists - process each list
        data_attrs_list = self.template_variables or []

        print("data_attrs_list",data_attrs_list)

        if not isinstance(data_attrs_list, list):
            data_attrs_list = [data_attrs_list]

        all_results = []

        # Process each attribute set in data_attrs_list
        for data_attrs_raw in data_attrs_list:
            # Normalize current attribute set
            data_attrs = set(data_attrs_raw) if isinstance(data_attrs_raw, list) else set([data_attrs_raw])

            exact_matches = []  # Both objectives AND variables match exactly
            obj_partial_var_exact = []  # Objectives partial, variables exact
            obj_exact_var_near = []  # Objectives exact, variables near
            obj_partial_var_near = []  # Objectives partial, variables near
            obj_partial_no_vars = []  # Objectives partial, no variables

            for tpl in templates:
                # ---- Campaign Objective Processing ----
                tpl_objectives = tpl.get("campaign_objective") or []
                tpl_objectives = tpl_objectives if isinstance(tpl_objectives, list) else [tpl_objectives]

                # Normalize template objectives: strip whitespace and convert to lowercase
                tpl_objectives = set(
                    obj.strip().lower() if isinstance(obj, str) else obj
                    for obj in tpl_objectives
                )

                # Determine objective match type
                obj_exact = tpl_objectives == input_objectives and tpl_objectives
                obj_partial = bool(tpl_objectives & input_objectives)

                # Skip if no objective match at all
                if not (obj_exact or obj_partial):
                    continue
                
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

                # ---- Categorize by Match Quality ----
                if obj_exact and var_exact:
                    # Best: both exact
                    exact_matches.append(tpl)
                elif obj_exact and var_near:
                    # Objectives exact, variables partial
                    obj_exact_var_near.append((overlap, tpl))
                elif obj_exact and var_none:
                    # Objectives exact, no variables
                    obj_exact_var_near.append((0, tpl))
                elif obj_partial and var_exact:
                    # Objectives partial, variables exact
                    obj_partial_var_exact.append((len(tpl_objectives & input_objectives), tpl))
                elif obj_partial and var_near:
                    # Objectives partial, variables partial
                    obj_score = len(tpl_objectives & input_objectives)
                    obj_partial_var_near.append((obj_score, overlap, tpl))
                elif obj_partial and var_none:
                    # Worst: objectives partial, no variables
                    obj_score = len(tpl_objectives & input_objectives)
                    obj_partial_no_vars.append((obj_score, tpl))

            # ---- Collect Results in Priority Order for this attribute set ----
            current_results = []

            # 1. Exact matches (both objectives and variables)
            if exact_matches:
                current_results.extend(exact_matches[:limit])
            # 2. Objective partial, variable exact (sorted by objective overlap)
            elif obj_partial_var_exact:
                obj_partial_var_exact.sort(key=lambda x: x[0], reverse=True)
                current_results.extend([tpl for _, tpl in obj_partial_var_exact][:limit])
            # 3. Objective exact, variable near (sorted by variable overlap)
            elif obj_exact_var_near:
                obj_exact_var_near.sort(key=lambda x: x[0], reverse=True)
                current_results.extend([tpl for _, tpl in obj_exact_var_near][:limit])
            # 4. Objective partial, variable near (sorted by objective, then variable overlap)
            elif obj_partial_var_near:
                obj_partial_var_near.sort(key=lambda x: (x[0], x[1]), reverse=True)
                current_results.extend([tpl for _, _, tpl in obj_partial_var_near][:limit])
            # 5. Objective partial, no variables (sorted by objective overlap)
            elif obj_partial_no_vars:
                obj_partial_no_vars.sort(key=lambda x: x[0], reverse=True)
                current_results.extend([tpl for _, tpl in obj_partial_no_vars][:limit])

            all_results.extend(current_results)

        # Remove duplicates while preserving order and apply limit
        seen = set()
        unique_results = []
        for tpl in all_results:
            tpl_id = id(tpl)  # Use object identity
            if tpl_id not in seen:
                seen.add(tpl_id)
                unique_results.append(tpl)
                if len(unique_results) >= limit:
                    break
                
        return unique_results


    def run(self):
        #communication_credentials_id = self.retrieve_credentials(self.dealership_id)
        all_templates = self.pick_from_model()
        best = self.match_templates_strict(all_templates)
        return best



@gryd.is_a_task('get_whatsapp_template', logger_param='logger', job_param='job')
def get_whatsapp_template(lead_info=None, lead_id=None, campaign_type=None, campaign_objective = None,dealership_id=None, logger=None, job=None, **kwargs):

        logger = logger or gryd.hp.get_logger(__name__)
        logger.info("Getting WhatsApp Template...")
        # if dealership_id is None:
        #     dealership_id = 'daveai'

        try:
            lead_info = lead_info or {}
            lead_info.update({k: v for k, v in kwargs.items() if v is not None})
            updates = {
                "id": lead_id,
                "campaign_type": campaign_type,
                
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

            attribute_list_sets
            logger.info(f"Template variables : {attribute_list_sets}")

            data = {
                "campaign_type": campaign_type,
                "template_variables": attribute_list_sets,
                "campaign_objective" : campaign_objective,
                #"dealership_id" : dealership_id
            }

            logger.info(f"Source data : {data}")

            # 2. Template Selector Agent
            template_agent = get_whatsapp_template_agent(source=data, logger=logger)
            result = template_agent.run()

            return result

        except Exception as e:
            logger.error(f"Template retrieval failed: {str(e)}")
            raise
