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

logger = get_logger(__name__)

class CohortGenerationAgent(BaseAgent):
    @property
    def allowed_cohort_ids(self):
        DEFAULT_COHORT_IDS = {
            "awareness": [
                "brand_discovery_users",
                "feature_explorers",
                "lifestyle_alignment_seekers",
                "performance_curiosity_users",
            ],
            "consideration": [
                "spec_comparison_users",
                "price_value_evaluators",
                "finance_inquirers",
                "ev_curiosity_users",
                "safety_tech_researchers",
            ],
            "high_intent": [
                "test_drive_seekers",
                "dealer_locator_users",
                "offer_page_visitors",
                "high_intent_buyers",
            ],
            "ownership": [
                "existing_owners",
                "service_maintenance_users",
                "accessory_upgrade_seekers",
                "warranty_insurance_inquirers",
            ],
            "retargeting": [
                "dropped_high_intent_users",
                "inactive_returning_users",
                "abandoned_configurator_users",
            ],
        }
        return DEFAULT_COHORT_IDS
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.brochure_url:str = kwargs.get("brochure_url", None)
        self.product_website_url:str = kwargs.get("product_website_url", None)

        self.brochure_content : list[dict] = None
        self.product_website_content : list[dict] = None

        if self.brochure_url:
            self.brochure_content = self.fetch_brochure_content(brochure_url = self.brochure_url)
    
        if self.product_website_url:
            self.product_website_content = self.fetch_product_details_from_website(website_url = self.product_website_url)

        self.model_identifier:str = kwargs.get("model_identifier", "azure-gpt-4o")
        self.llm = lambda messages : ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        

    @property
    def output_schema(self):
        schema = {
        "cohorts": [
            {
                "cohort_id": "<snake_case_unique_id>",
                "cohort_name": "<human_readable_name>",
                "intent_level": "<low | medium | high>",
                "description": "<clear business description>",
                "eligibility_rules": {
                    "events": [
                        {
                            "type": "<event_type>",
                            "page": "<page_or_context>",
                            "min_count": "<number>",
                            "min_seconds": "<number_optional>"
                        }
                    ]  
                },
                "behavioral_signals": [
                    "<signal_1>",
                    "<signal_2>"
                ],
                "exclusion_rules": [
                    "<rule_1>",
                    "<rule_2>"
                ],
                "priority": "<integer_lower_is_higher_priority>",
                "message_style_tags": [
                    "<tag_1>",
                    "<tag_2>"
                ],
                "recommended_channels": [
                    "email",
                    "whatsapp",
                    "push"
                ],
                "cooldown_days": "<integer>"
            }]
        }
        return schema

    def system_prompt(self):
        system_prompt = f"""
        You are a Cohort Generation Agent for a production-grade personalization system.

        You will be provided with:
        - Product brochure content (PDF extracted text)
        - Product website content

        Your task:
        Generate multiple user cohorts suitable for real-world marketing and personalization systems.

        Instructions:
        - Analyze both brochure and website content deeply.
        - Identify distinct user segments based on intent, behavior, and value.
        - Generate atleast 12-15 cohorts covering the full funnel (awareness → conversion).
        - Cohorts must be mutually distinguishable and production-ready.
        - Rules must be deterministic and convertible into code.
        - Important:
            - You MUST only use cohort_id values from the following allowed list: {self.allowed_cohort_ids}

        Your response MUST strictly follow this JSON schema:

        {json.dumps(self.output_schema, indent=4, default=str)}

        Rules:
        - Output valid JSON only
        - Do not include explanations or markdown
        - Do not hallucinate unsupported product features
        """
        messages = [
            {"role": "system", "content": system_prompt}
        ]     
        return messages
    
    def run(self):
        try:
            messages = self.system_prompt()
            if self.brochure_content:
                messages.append({"role": "user", "content": json.dumps(self.brochure_content, indent=4, default=str)})
            if self.product_website_content:
                messages.append({"role": "user", "content": json.dumps(self.product_website_content, indent=4, default=str)})
            response = self.extract_json_from_llm_response(self.llm(messages))
            coherts = response.get("cohorts", [])
            response = {"cohorts": [{"idx": idx, **cohort} for idx, cohort in enumerate(coherts)]}
        except Exception as e:
            traceback.print_exc()
            response = {"error": str(e), "raw_response": response}
        return response


    
