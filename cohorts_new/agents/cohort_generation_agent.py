import sys, os
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import json
import re
from ai_service import ai_service_app
import pandas as pd 
import os 
from pathlib import Path
import requests
import tempfile
from cohorts_new.utils.utility import *
from cohorts_new.utils.common_utils import *

from urllib.parse import urlparse
import validators
from typing import *
import traceback

logger = get_logger(__name__)

class ProductCohortGenerationAgent(UtilityMixin):
    def __init__(self, brochure_url=None, product_website_url=None, model_identifier="azure-gpt-4o", additional_instruction=None, *args, **kwargs):
        """
        Initialize the ProductCohortGenerationAgent.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
            (brochure_url: str, product_website_url: str, model_identifier: str)
        """
        try:
            super().__init__(*args, **kwargs)
        except Exception as e:
            print("\n")
            traceback.print_exc()
            print("\n Error with super init. Ignoring...")
            pass 

        self.brochure_url : str = brochure_url
        self.product_website_url : str = product_website_url

        self.brochure_content : list[dict] = self.fetch_brochure_content(brochure_url = self.brochure_url)
        self.product_website_content : list[dict] = self.fetch_product_details_from_website(website_url = self.product_website_url)
        
        self.model_identifier : str = model_identifier
        self.llm : Callable = lambda messages : ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)

        self.num_of_cohorts : int = kwargs.get("num_of_cohorts", 20)
        if isinstance(self.num_of_cohorts, str):
            self.num_of_cohorts = int(self.num_of_cohorts)
        if self.num_of_cohorts is None:
            self.num_of_cohorts = 20
        
        self.additional_instruction : str = additional_instruction or ""

        identifiers = [
            "Automotive",
            "Healthcare",
            "Finance",
            "Insurance",
            "Retail",
            "Ecommerce",
            "Real Estate",
            "Travel",
            "Hospitality",
            "Education",
            "Manufacturing",
            "Technology / SaaS",
            "Telecom",
            "Energy",
            "Media & Entertainment",
            "Logistics",
            "FMCG",
            "Other"
        ]

        self.identifiers = [i.lower() for i in identifiers]

    @property
    def output_schema(self):
        schema = {
        "cohorts": [
            {
                "cohort_id": "<snake_case_unique_id>",
                "cohort_name": "<human_readable_name>",
                "description": "<clear business description and how this cohort is adhere to the product positioning. Mention product feature, name, and any other relevant details. No more than 3 sentences>",
                "behavioral_signals": ["<signal_1>", "<signal_2>"],
                "eligibility_rules": [
                    "<rule_1>",
                    "<rule_2>"
                ],
                "exclusion_rules": [
                    "<rule_1>",
                    "<rule_2>"
                ],
                
                "message_style_tags": [
                    "<tag_1>",
                    "<tag_2>"
                ],
                "recommended_channels": [
                    "email",
                    "whatsapp",
                    "push",
                    "voice",
                    "instagram",
                    "facebook",
                    "sms"
                ],
                "cooldown_days": "<integer>"
            }]
        }
        return schema
        # "intent_level": "<low | medium | high>",
        # "priority": "<integer_lower_is_higher_priority>"
    
    def _cohort_ids_generation_prompt(self, domain="automotive") -> list[str]:
        system_prompt = f"""
        You are a {domain} Cohort ID Generation Agent for a production-grade personalization system.

        **INPUT:**
        You will receive:
        - Product brochure content (PDF/Word extracted text)
        - Product website content (if available)

        **TASK:**
        Generate unique and distinct user cohorts based on the product positioning, target market, and customer segmentation suitable for real-world marketing and personalization systems.

        **COHORT DIMENSIONS:**
        Consider multiple segmentation verticals including but not limited to:

        1. **Purchase Journey & Intent Stage**
        - Awareness, consideration, decision, post-purchase
        - Research phase, comparison shopping, ready-to-buy

        2. **Psychographic & Lifestyle**
        - Luxury seekers, budget-conscious, eco-conscious
        - Adventure enthusiasts, family-oriented, urban professionals
        - Status-driven, performance-focused, safety-first

        3. **Demographic & Life Stage**
        - First-time buyers, upgraders, repeat customers
        - Young professionals, families with children, retirees
        - High-income, mid-market, value seekers

        4. **Geographic & Contextual**
        - Urban vs rural, climate-specific needs
        - Regional preferences (if applicable)

        5. **Usage Pattern & Needs**
        - Daily commuters, weekend adventurers, business travelers
        - Off-road enthusiasts, highway drivers, city drivers
        - High-mileage users, occasional drivers

        6. **Vehicle Segment (for automotive)**
        - SUV seekers, sedan buyers, truck enthusiasts
        - Electric/hybrid interested, traditional fuel preference
        - Compact vs full-size preference

        7. **Brand Preference (for automotive)**
        - Luxury brands, compact brands, midsize brands
        - Premium brands, midrange brands, budget brands

        8. **Feature Preference (for automotive)**
        - Safety features, tech features, comfort features
        - Performance features, interior features, exterior features
        - Color preference, interior color, exterior color
        - Technology preference, interior technology, exterior technology

        9. **First Time Buyers (for automotive)**
        - You need to include at least one cohort specifically for first-time buyers (FTB) in your final output.

        **REQUIREMENTS:**
        - Generate exactly {self.num_of_cohorts} cohorts (strict requirement)
        - Each cohort must be mutually distinguishable (minimal overlap)
        - Cover the full customer funnel from awareness to loyalty
        - Cohort IDs must be unique, descriptive, and actionable
        - Use snake_case format, lowercase only
        - Avoid generic terms; be specific to {domain} context.
        - If website content is available, please analyze it well and align cohort IDs with website sections (Check for sections like Specs, 3D Configurator, etc.)

        **FORMAT:**
        Return ONLY a valid Python list of strings (no markdown, no explanations):

        [
            "cohort_id_1",
            "cohort_id_2",
            ...
        ]

        **GOOD EXAMPLES:**
        [
            "luxury_suv_aspirants",
            "design_and_configurator_enthusiasts",
            "eco_conscious_first_time_buyers",
            "performance_enthusiast_upgraders",
            "family_safety_prioritizers",
            "budget_compact_sedan_seekers",
            "adventure_offroad_enthusiasts"
        ]

        **BAD EXAMPLES (avoid these):**
        [
            "car_buyers",  // Too generic
            "users",  // Not descriptive
            "SegmentA",  // Not meaningful
            "high-income-buyers"  // Wrong format (use snake_case)
        ]
        """

        if self.additional_instruction:
            system_prompt += f"\n\n**ADDITIONAL INSTRUCTIONS:**\n{self.additional_instruction}"
        
        messages = [
            {
                "role": "system", 
                "content": system_prompt
            }
        ]
        return messages

    def _cohorts_generation_prompt(self, cohort_batch : list):
        system_prompt = f"""
        You are a Cohort Generation Agent for a production-grade personalization system.

        You will be provided with:
        - Product brochure content (PDF/Word extracted text)
        - Product website content (If available)

        Your task:
        Your task is to generate multiple user cohorts based on the product positioning and target market suitable for real-world marketing and personalization systems.

        Instructions:
        - Analyze both brochure and website content deeply.
        - Identify distinct user segments based on intent, behavior, and value.
        - Generate cohorts covering the full funnel (awareness → conversion).
        - Cohorts must be mutually distinguishable and production-ready.

        You MUST generate for following cohorts: {cohort_batch}

        Return only in the following format:

        {json.dumps(self.output_schema, indent=4)}

        """
        # if self.additional_instruction:
        #     system_prompt += f"\n\n**ADDITIONAL INSTRUCTIONS:**\n{self.additional_instruction}"
        
        messages = [
            {
                "role": "system", 
                "content": system_prompt
            }
        ]
        return messages
    
    def chunk_list(self, items:list, chunk_size=10):
        list_length = len(items) # Get length of items list

        for i in range(0, list_length, chunk_size): # Loop over items list For example: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
            limit = i + chunk_size # Set limit
            yield items[i:limit] 

    def _classify_domain(self):
        prompt = f"""
        You are a **Product Domain Classification Agent** for a production-grade personalization system.

        Your task:
        - Analyze the provided product brochure content and website content
        - Identify the **primary industry/domain** the product belongs to
        - Choose **ONLY ONE** identifier from the allowed list
        - If the domain is unclear, return "other"

        Allowed Identifiers:
        {json.dumps(self.identifiers, indent=4)}

        Classification rules:
        - Focus on the product's **core usage and industry**
        - Ignore marketing fluff
        - Prefer the most specific applicable domain
        - Do NOT invent new identifiers

        Product brochure content:
        {json.dumps(self.brochure_content, indent=4)}

        Product website content:
        {json.dumps(self.product_website_content, indent=4)}

        Return response strictly in the following JSON format:

        {{
            "identifier": "<one_of_the_allowed_identifiers>",
            "confidence": "high | medium | low",
            "reasoning": "<short explanation in 1-2 lines>"
        }}
        """

        messages = []
        messages.append({"role": "system", "content": prompt})
        try:
            return self.exec_json_llm_with_retry(self.llm, messages=messages)
        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}
    
    @property
    def additional_product_context(self):
        return """
            Analyze both brochure and website content deeply.
            Identify distinct user segments based on intent, behavior, and value.
            Generate cohorts covering the full funnel (awareness → conversion).
            Cohorts must be mutually distinguishable and production-ready.
            """


    def run(self, batch_size=10):
        domain = self._classify_domain().get("identifier", "automotive").title()
        cohort_id_generation_prompt = self._cohort_ids_generation_prompt(domain=domain)
        product_context_parts = []

        if self.brochure_content:
            product_context_parts.append(f"PRODUCT BROCHURE:\n{json.dumps(self.brochure_content, indent=2)}")

        if self.product_website_content:
            product_context_parts.append(f"PRODUCT WEBSITE:\n{json.dumps(self.product_website_content, indent=2)}")

        if product_context_parts:
            product_context = "\n\n".join(product_context_parts)
            cohort_id_generation_prompt.append({
                "role": "user",
                "content": f"{self.additional_product_context}\n{product_context}"
            })

        final_cohorts = []
        cohort_ids = self.exec_json_llm_with_retry(self.llm, messages=cohort_id_generation_prompt)
        logger.info(f"Cohort IDs: {cohort_ids}")
        allowed_cohorts = cohort_ids

        try:
            cohort_batches = list(self.chunk_list(items=allowed_cohorts, chunk_size=batch_size))
            logger.info(f"Cohort_batches: {cohort_batches}")
            for batch_idx, cohort_batch in enumerate(cohort_batches, start=1):
                logger.info(f"Running cohort contextualization batch {batch_idx}/{len(cohort_batches)}")
                messages = self._cohorts_generation_prompt(cohort_batch = cohort_batch)
                
                # Add product context to messages (this was outside the loop!)
                product_context_parts = []
                if self.brochure_content:
                    product_context_parts.append(f"PRODUCT BROCHURE:\n{json.dumps(self.brochure_content, indent=2)}")

                if self.product_website_content:
                    product_context_parts.append(f"PRODUCT WEBSITE:\n{json.dumps(self.product_website_content, indent=2)}")

                if product_context_parts:
                    product_context = "\n\n".join(product_context_parts)
                    messages.append({
                        "role": "user",
                        "content": f"{self.additional_product_context}\n{product_context}"
                    })
                
                # Execute LLM call for this batch
                response = self.exec_json_llm_with_retry(self.llm, messages=messages)
                coherts = response.get("cohorts", [])
                final_cohorts.extend(coherts)
        
            final_result = {"cohorts": [{"idx": idx, **cohort} for idx, cohort in enumerate(final_cohorts, start=1)]}
            return final_result

        except Exception as e:
            traceback.print_exc()
            response = {"error": str(e), "raw_response": response if 'response' in locals() else None}
        return response
    

    def run_with_events(self, batch_size=10) -> Iterable[dict]:
        def emit(event_type, data=None):
            return {"type": event_type, "data": data}
        try:
            yield emit("status", "classifying domain")
            domain = self._classify_domain().get("identifier", "automotive").title()
            cohort_id_generation_prompt:list[dict] = self._cohort_ids_generation_prompt(domain=domain)
            product_context_parts = []
            if self.brochure_content:
                product_context_parts.append(f"PRODUCT BROCHURE:\n{json.dumps(self.brochure_content, indent=2)}")
            if self.product_website_content:
                product_context_parts.append(f"PRODUCT WEBSITE:\n{json.dumps(self.product_website_content, indent=2)}")
            if product_context_parts:
                product_context = "\n\n".join(product_context_parts)
                cohort_id_generation_prompt.append({
                    "role": "user",
                    "content": f"{self.additional_product_context} \n {product_context}"
                })
            yield emit("status", "generating cohort ids")
            cohort_ids:list[str] = self.exec_json_llm_with_retry(self.llm, messages=cohort_id_generation_prompt)
            logger.info(f"Cohort IDs: {cohort_ids}")
            allowed_cohorts = cohort_ids
            yield emit("status", f"batching cohorts ({len(allowed_cohorts)})")
            cohort_batches:list[list[str]] = list(self.chunk_list(items=allowed_cohorts, chunk_size=batch_size))
            
            for batch_idx, cohort_batch in enumerate(cohort_batches, start=1):
                yield emit("status", f"generating cohorts batch {batch_idx}/{len(cohort_batches)}")
                messages = self._cohorts_generation_prompt(cohort_batch=cohort_batch)
                
                # Add product context to messages
                product_context_parts = []
                if self.brochure_content:
                    product_context_parts.append(f"PRODUCT BROCHURE:\n{json.dumps(self.brochure_content, indent=2)}")
                if self.product_website_content:
                    product_context_parts.append(f"PRODUCT WEBSITE:\n{json.dumps(self.product_website_content, indent=2)}")
                if product_context_parts:
                    product_context = "\n\n".join(product_context_parts)
                    messages.append({
                        "role": "user",
                        "content": f"{self.additional_product_context}\n{product_context}"
                    })
                
                response = self.exec_json_llm_with_retry(self.llm, messages=messages)
                cohorts:list[dict] = response.get("cohorts", [])
                yield emit("cohort", cohorts)
            yield emit("done", "cohort generation completed")
        except Exception as e:
            traceback.print_exc()
            yield emit("error", str(e))
        
