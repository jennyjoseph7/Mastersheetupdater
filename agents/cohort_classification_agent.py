import json
import re
from ai_service import ai_service_app
from agents.base_agent import BaseAgent
import pandas as pd 
import os 
from pathlib import Path
import requests
import tempfile
from utils import *
from urllib.parse import urlparse
import validators
import time

logger = get_logger(__name__)

class CohortClassificationAgent(BaseAgent):
    def __init__(self, source, brochure_url=None, product_website_url=None, cohorts = None, model_identifier='azure-gpt-4o'):
        self.model_identifier : str = model_identifier
        self.source : dict = self._load_json(source=source)
        self.llm = lambda messages : ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        self.brochure_url : str = brochure_url
        self.product_website_url : str = product_website_url
        self.cohorts_registry = cohorts

        if self.cohorts_registry is not None:
            if isinstance(self.cohorts_registry, dict) and len(self.cohorts_registry) > 0 and "cohorts" in self.cohorts_registry:
                self.cohorts_registry = self.cohorts_registry["cohorts"]
            elif isinstance(self.cohorts_registry, list) and len(self.cohorts_registry) > 0:
                self.cohorts_registry = self.cohorts_registry
        else:
            self.cohorts_registry = []
            logger.error("Cohort knowledge is not provided.. Setting it to an empty list")
            logger.info(f"Cohort knowledge: {self.cohorts_registry}")

        self.brochure_content : list[dict] = None
        self.product_website_content : list[dict] = None

        if self.brochure_url:
            self.brochure_content = self.fetch_brochure_content(brochure_url = self.brochure_url)
    
        if self.product_website_url:
            self.product_website_content = self.fetch_product_details_from_website(website_url = self.product_website_url)
            
    def _cohort_knowledge(self):
        # return self.cohorts_registry
        file_path = Path(__file__).parent / "prompt_data" / "cohorts.csv"
        data = pd.read_csv(file_path)
        return [row.to_dict() for idx, row in data.iterrows()]
    
    def _output_format(self):
        return {
            "cohort_id": "<name_of_cohort>"
        }
    
    def system_prompt(self):
        messages = [] 
        system_prompt = f"""
        You are an intelligent Cohort Classification assistant.
        You will be provided with a list of Cohort knowledge, user interaction data and product website content if available.
        Your task is to classify the Cohort based on the user input.

        Cohort knowledge:
        {json.dumps(self.cohorts_registry, indent=4)}

        User Interaction/Conversation Data:
        {json.dumps(self.source, indent=4)}

        Product Website Content:
        {json.dumps(self.product_website_content, indent=4)}

        Product Brochure Content:
        {json.dumps(self.brochure_content, indent=4)}

        Guidelines:
        - Analyze the user interaction data and the Cohort knowledge to determine the Cohort.
        - Your response should be a JSON object from Cohort knowledge. Just the cohort_id is required. 
        - Output format: {json.dumps(self._output_format(), indent=4)}
       
        """
        messages.append({"role": "system", "content": system_prompt})
        return messages
    
    #  {{
    #       "cohort_name": "<name_of_cohort>",
    #       "secondary_cohort": "<secondary_cohort_name>",
    #       "description": "<short_description_of_cohort>",
    #       "rule_hints": "<hints_for_cohort_classification>",
    #       "message_style_tags": "<tags_for_message_style>"
    #  }}
    
    def _run(self):
        try:
            messages = self.system_prompt()
            response = self.llm(messages)
            logger.info(f"response from cohort_classification_agent: {response}")
            response = self.extract_json_from_llm_response(response)
        except Exception as e:
            response = {"error": str(e), "raw_response": response}
        return response
        

    def run(self):
        MAX_RETRIES = 3
        BACKOFF = 2 
        last_exception = None

        for attempt in range(1, MAX_RETRIES + 1): # 1, 2, 3
            try:
                messages = self.system_prompt()
                response = self.llm(messages)
                logger.info(f"response from cohort_classification_agent: {response}")
                response = self.extract_json_from_llm_response(response)
                return response

            except Exception as e:
                last_exception = e
                logger.exception(
                f"Attempt {attempt}/{MAX_RETRIES} failed in cohort_classification_agent")
                if attempt < MAX_RETRIES:
                    time.sleep(BACKOFF)

        raise RuntimeError("LLM call failed after retries") from last_exception



