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
    def __init__(
            self, 
            source:dict=None, 
            brochure_url:str=None, 
            product_website_url:str=None, 
            cohorts:Union[dict, list[dict]]=None, 
            model_identifier:str='azure-gpt-4o'
            ):
        self.model_identifier:str = model_identifier
        self.source:dict=self._load_json(source=source)
        self.llm:Callable=lambda messages : ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        self.brochure_url:str=brochure_url
        self.product_website_url:str=product_website_url
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

        self.brochure_content = self.fetch_brochure_content(brochure_url = self.brochure_url)
        self.product_website_content = self.fetch_product_details_from_website(website_url = self.product_website_url)
            
    def _cohort_knowledge(self):
        # return self.cohorts_registry
        file_path = Path(__file__).parent / "prompt_data" / "cohorts.csv"
        data = pd.read_csv(file_path)
        return [row.to_dict() for idx, row in data.iterrows()]
    
    def _output_format(self):
        FORMAT = {
            "cohort_ids": ["<name_of_cohort>","<name_of_cohort>"],
            "primary_classified_cohort_id": "<name_of_cohort>",
            "reasoning": "<reasoning>",
            "confidence_score": "<float> between 0 and 1"
        }

        return FORMAT # {"cohort_id": "<name_of_cohort>"}
    
    def system_prompt(self):
        messages = [] 
        system_prompt = f"""
        You are an intelligent Cohort Classification assistant.
        You will be provided with a list of Cohort knowledge, user interaction data and product website content if available.
        Your task is to classify the Cohort based on the user input. Choose the highest confidence/priority Cohort. Classify the customer into the most appropriate cohort(s) and provide clear reasoning.

        Cohort knowledge:
        {json.dumps(self.cohorts_registry, indent=4)}

        User Interaction/Conversation Data:
        {json.dumps(self.source, indent=4)}

        Product Website Content:
        {json.dumps(self.product_website_content, indent=4)}

        Product Brochure Content:
        {json.dumps(self.brochure_content, indent=4)}

        Guidelines:
        - Strictly follow the Cohort knowledge.
        - If interaction is not clearly covered in Cohort knowledge, still try to classify into the closest high-priority cohort.
        - Analyze the user interaction data and the Cohort knowledge to determine the Cohort.
        - Your response should be a JSON object from Cohort knowledge. Just the cohort_id is required. 
        - Give appropriate confidence score between 0 and 1 and reasoning for the classification in 4-5 sentences.

        
        **CRITICAL TEMPORAL RULES:**
        - If the customer lifecycle status indicates a successful conversion (e.g., "Delivered", "Invoiced", "Booked", "Purchased", "Converted"):
        - The cohort MUST be assigned based on the interactions and signals that led to the purchase.
        - Post-purchase or after-sales interactions (service visits, complaints, accessories, promotions after delivery, etc.) must NOT influence cohort classification.
        - Focus on:
            - Pre-purchase browsing behavior
            - Test drives
            - inquiries
            - feature interests
            - pricing discussions
            - financing interactions
            - dealership visits prior to conversion

        - After-sales cohorts (e.g., service_customer, after_sales_promo, retention_campaign, etc.) should ONLY be used when:
            - The customer has NOT yet purchased, OR
            - There is explicitly no meaningful pre-purchase interaction history.

        **Priority Order for Decision Making:**
        1. Pre-purchase intent signals  
        2. Product interest patterns  
        3. Behavioral engagement before conversion  
        4. Demographics (only as secondary support)  
        5. Post-purchase activity (LOWEST PRIORITY – ignore if purchase already happened)


        **REASONING GUIDELINES:**
        - ✅ GOOD: "Sarah has been classified as 'luxury_suv_aspirants' because she viewed the premium X7 model 5 times, spent 12 minutes on the luxury features page, and her demographic profile indicates high purchasing power ($150K+ income bracket)."
        - ❌ BAD: "The customer is interested in luxury vehicles."
        - ✅ GOOD: "John fits 'eco_conscious_first_time_buyers' as he exclusively browsed hybrid and electric models, downloaded the EV buyer's guide, and submitted a quote request for the EV model with zero ICE vehicle interactions."
        - ❌ BAD: "Customer wants an eco-friendly car."
        - ✅ GOOD: "Ravi has been classified as 'family_suv_buyers' because before purchase he inquired multiple times about 7-seater features, safety ratings, and child seat compatibility. Although his recent interactions include service bookings after delivery, those are post-purchase signals and are ignored for cohort determination as per temporal rules."

        **KEY PRINCIPLES:**
        - Be specific and evidence-based
        - Reference actual behavioral data
        - Explain WHY this cohort over others
        - Use customer name naturally (e.g., "John's browsing pattern..." not "The customer John...")

        - Output format: {json.dumps(self._output_format(), indent=4)}
       
        """
        messages.append({"role": "system", "content": system_prompt})
        return messages
        
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
                logger.exception(f"Attempt {attempt}/{MAX_RETRIES} failed in cohort_classification_agent")
                if attempt < MAX_RETRIES:
                    time.sleep(BACKOFF)

        raise RuntimeError("LLM call failed after retries") from last_exception



