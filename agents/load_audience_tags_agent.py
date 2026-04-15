
# ps
# I/P :
# vehicle id, purchased date, odometer reading, when taken odometer reading,



# Catagory

# process : avd odo reading




# O/P :

import json
import os, sys, requests
from datetime import datetime
from ai_service import ai_service_app

try:
    from .base_agent import BaseAgent, gryd
except ImportError:
    from base_agent import BaseAgent, gryd 
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from autocrm_db_helper.PGConnector import AutoCRMPGConnector

pg = AutoCRMPGConnector(enterprise_id="autocrm")

class loadAudianceTags(BaseAgent):

    """
        Select relevant audience_task_ids using AI
        and deterministically attach target fields.
    """

    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        
        # Validate source
        if not source or not isinstance(source, dict):
            raise ValueError("source must be a non-empty dictionary")

        self.source = source
        self.campaign_type = source.get("campaign_type")
        self.campaign_objective = source.get("campaign_objective")
        self.campaign_idea = source.get("campaign_idea")
        self.dealership_id = source.get("dealership_id", "")
        
        self.logger = kwargs.get("logger") or gryd.hp.get_logger(__name__)
        self.model_identifier =   "openai-gpt-4.1-mini"#"gcp-gemini-2.5-flash-lite"



    def load_data(self):
        return list(pg.list(
            table_name= "audience_task",
            where= {

        
            }
        ))
    
    def extract_fields_for_task(
        self,
        task_id: str,
        record_map: dict
    ) -> list[str]:
        record = record_map.get(task_id)
        if not record:
            return []

        fields = []
        for mapping in record.get("field_mapping", []):
            if mapping.get("enabled") is True:
                target = mapping.get("target_field")
                if target:
                    fields.append(target.strip())

        return fields

    # Build AI-readable metadata

    def build_ai_context(self, records: list[dict]) -> list[dict]:
        context = []

        for rec in records:
            fields = [
                m.get("target_field").strip()
                for m in rec.get("field_mapping", [])
                if m.get("enabled") is True and m.get("target_field")
            ]

            context.append({
                "audience_task_id": rec.get("audience_task_id"),
                "campaign_type": rec.get("campaign_type"),
                "tags": rec.get("tags", []),
                "available_fields": fields
            })

        return context

    def apply_ai(self, records: list[dict]) -> list[dict]:
        ai_context = self.build_ai_context(records)

        system_prompt = f"""
        You are an expert audience strategist selecting audience tasks for executing a marketing campaign.

        Your goal is to choose the MOST RELEVANT audience_task_id(s) that can successfully run the campaign. Minimum 1 id is must. return the most relevant id/ids

        --------------------
        CAMPAIGN DETAILS
        --------------------
        Campaign Idea:
        {self.campaign_idea}

        Campaign Objective:
        {self.campaign_objective}

        Campaign Type:
        {self.campaign_type}

        --------------------
        AUDIENCE TASK METADATA
        --------------------
        Each audience task contains:
        - audience_task_id
        - campaign_type (when it is applicable)
        - tags (describe who the audience represents)
        - available_fields (data available to execute the campaign)

        {json.dumps(ai_context, indent=2)}

        --------------------
        SELECTION RULES (VERY IMPORTANT)
        --------------------
        1. Campaign Type Match
           - Prefer audience tasks whose campaign_type matches the campaign
           - Strongly penalize mismatches unless no other option exists

        2. Tag Relevance (Primary Signal)
           - Tags must clearly describe the audience needed for the campaign
           - Ignore generic or testing audiences unless explicitly relevant
           - Avoid audiences with conflicting intent (e.g., inactive users for retention)

        3. Field Compatibility (Execution Feasibility)
           - The available_fields must support executing the campaign
           - If key data needed for the campaign is missing, do NOT select that task

        4. Minimal Selection Strategy
           - Select ONLY ONE audience_task_id in most cases
           - Select TWO ONLY IF:
             - Each audience serves a clearly different purpose, AND
             - Both are genuinely required to run the campaign

        5. Rejection Rule
           - If an audience task is only loosely or indirectly related, REJECT it

        --------------------
        OUTPUT INSTRUCTIONS (STRICT)
        --------------------
        - Return ONLY valid JSON
        - Return a JSON LIST
        - Each item must contain ONLY:
          {{"audience_task_id": "<id>"}}

        Examples:
        Correct:
        [
          {{"audience_task_id": "task_123"}}
        ]

        Correct (rare case):
        [
          {{"audience_task_id": "task_123"}},
          {{"audience_task_id": "task_456"}}
        ]

        Incorrect:
        - Explanations
        - Additional keys
        - Strings
        - Nested objects
        - More than 2 IDs also minimum 1 is required, return the most relevant one

        --------------------
        FINAL CHECK BEFORE RETURNING
        --------------------
        - Ask yourself: "Can this campaign be executed successfully using this audience?"
        - If unsure → DO NOT include the audience
        - When in doubt → return ONE best audience_task_id
        """


        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": ""}
        ]

        response = ai_service_app.get_llm_response(
            messages=messages,
            model_identifier=self.model_identifier
        )

        return self.parse_ai_response(response)

    # Parse & validate AI output

    def parse_ai_response(self, response) -> list[dict]:
        try:
            if isinstance(response, str):
                response = json.loads(response)

            if not isinstance(response, list):
                raise ValueError("AI response is not a list")

            validated = []
            for item in response:
                if (
                    isinstance(item, dict)
                    and isinstance(item.get("audience_task_id"), str)
                ):
                    validated.append(
                        {"audience_task_id": item["audience_task_id"]}
                    )

            return validated

        except Exception as e:
            self.logger.error(f"AI response parsing failed: {e}")
            return []

    # Main runner

    def run(self) -> list[dict]:
        records = self.load_data()

        if not records:
            self.logger.warning("No audience_task records found")
            return []

        record_map = {
            r.get("audience_task_id"): r
            for r in records
        }

        ai_selected = self.apply_ai(records)

        if not ai_selected:
            self.logger.warning("AI returned no valid audience_task_id")
            return []

        final_output = []

        for item in ai_selected:
            task_id = item["audience_task_id"]

            fields = self.extract_fields_for_task(
                task_id=task_id,
                record_map=record_map
            )

            final_output.append({
                "audience_task_id": task_id,
                "fields": fields
            })

        return final_output





AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")

@gryd.is_a_task("select_relevant_audience_tasks",logger_param="logger",job_param="job")
def select_relevant_audience_tasks(source=None,logger=None,job=None):
    logger = logger or gryd.hp.get_logger(__name__)

    selector = loadAudianceTags(source=source, logger=logger)
    return selector.run()















































































































# @gryd.is_a_task('load_audiance_tags', logger_param='logger', job_param='job')
# def load_audiance_tags(vehicle_id,service_visit_id, logger=None, job=None):
#     logger = logger or gryd.hp.get_logger(__name__)
#     logger.info(f"Creating load audiance tags for vehicle no : {vehicle_id}")
    
#     result = {
        
#         "expected_service_date" : "18-11-2025", #Maybe null in case of customer lost
#         "message_text" : "Hi, Your last service was on 18th June, As of the next service is due on completion of 5 months, Your next service should be completed by 18th Nov", #Maybe null in case of customer lost
#         "customer_tags" : {
#                         "service_date_in_7days" : True,
#                         "service_date_in_15days" : False,
#                         "customer_overtaked_by_other_workshop" : False,
#                         "customer_lost" : False
#                         }
    


#     }
        
#     return result












































    # """Audience Tagging Agent

    # This agent processes customer vehicle data and service history to generate
    # intelligent audience tags such as predicted odometer usage, next service date,
    # lost-customer detection, and customer overtaked by competitor-workshop detection.

    # It is designed to be used inside automated CRM and service-reminder pipelines
    # where customer segmentation and personalization depend on updated vehicle usage
    # insights.

    # inputs will be :
    # campaign _obj 

    # take camp_obj apply relevant filter, post to post sales lead, return vehicles

    # op- List of tags

    # {
    #     args : [],
    #     kwargs : {
    #         "vehicle_id" : "id of the vehicle",:
    #             "model, 
    #             "variant", 
    #             "reg_number",
    #             "purchase_date",
    #             previous service info -  
    #                 "odometer_reading" : "last odometer reading recorded",
    #                 "odometer_reading_record_date" : "Date of the odometer reading",
    #                 "last_service_date" : "Last service date"
    #     }
    
    
    # } 


    # Output will be :
    # {
    #                 Free Service : 

    #                     "service_date_in_7days" : list
    #                     "service_date_in_15days" : list
    #                     "service_date_in_1month" : list

    #                     "service_due_in_7days" : list
    #                     "service_due_in_15days" : list
    #                     "service_due_in_1month" : list
    #                     "service_due_in_45days" : list
    #                     "service_due_in_3months" : list



                        

                    
    #                 Paid Service : 

    #                     "service_date_in_7days" : list
    #                     "service_date_in_15days" : list
    #                     "customer_overtaked_by_other_workshop" : list
    #                     "customer_lost" : list
                        
    
    
    # }
    
    # """


    # def __init__(self, vehicle_id, service_visit_id):
    #     self.vehicle_id = vehicle_id
    #     self.service_visit_id = service_visit_id

    # def vehicle_data_retriever(self):
    #     pg = AutoCRMPGConnector(enterprise_id="autocrm")
    #     vehicle_record = pg.get(
    #         table_name="vehicle", 
    #         id_attr="vehicle_id",
    #         id=self.vehicle_id
    #     )

    #     return vehicle_record

    # def service_data_retriever(self):
    #     pg = AutoCRMPGConnector(enterprise_id="autocrm")
    #     service_record = pg.get(
    #         table_name="service_visit", 
    #         id_attr="service_visit_id",
    #         id=self.service_visit_id
    #     )

    #     return service_record

    # def odometer_reading_predictor(self,vehicle_record : dict, service_record : dict):
    #     """Wll do odometer reading prediction for next service"""



        


    #     pass


    # def service_time_predictor(self):
    #     """if odometer reading is low, it will calculate next service date according to the last service date"""
    #     pass

    # def lost_customer_detector(self):
    #     """Will detect the customer who left the workshop for servicing calculated by odometer and time of not serviced
    #     IP : Service history data
    #     """
    #     pass


    # def competetor_overtaked_predictor(self):
        
    #     """this will detect the customer who did the last service in an another workshop
    #     IP : Service history data
    #     """
    #     pass
        


