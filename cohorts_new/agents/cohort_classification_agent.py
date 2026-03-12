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
import time
from typing import *
import random

logger = get_logger(__name__)

def normalize_cohorts_registry(cohorts_registry:Union[dict, list[dict]]) -> list[dict]:
    """
    Normalize cohorts_registry to a list.
    - If dict with key 'cohorts' → return its value
    - If non-empty list → return as-is
    - If None or invalid → return empty list and log error
    """
    if cohorts_registry is not None:
        if isinstance(cohorts_registry, dict) and cohorts_registry.get("cohorts"):
            return cohorts_registry["cohorts"]
        elif isinstance(cohorts_registry, list) and len(cohorts_registry) > 0:
            return cohorts_registry

    logger.error("Cohort knowledge is not provided.. Setting it to an empty list")
    logger.info("Cohort knowledge: []")
    return []


class CohortClassificationAgent(UtilityMixin):
    def __init__(
            self, 
            source:dict=None, 
            brochure_url:str=None, 
            product_website_url:str=None, 
            cohorts:Union[dict, list[dict]]=None,
            additional_instruction=None,
            model_identifier:str='azure-gpt-4o'
            ):
        """
        Cohort Classification Agent.
        Parameters:
        source (dict or str, optional): A JSON object or path to a JSON file containing customer interaction data. Defaults to None.
        brochure_url (str, optional): URL of the brochure. Defaults to None.
        product_website_url (str, optional): URL of the product website. Defaults to None.
        cohorts (Union[dict, list[dict]], optional): Cohorts registry. Defaults to None.
        model_identifier (str, optional): The identifier of the Large Language Model to use for generating code based on human instructions. Defaults to 'azure-gpt-4o'.
        """
        self.model_identifier:str = model_identifier
        self.source:dict=self._load_json(source=source)
        self.llm:Callable=lambda messages : ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        self.brochure_url:str=brochure_url
        self.product_website_url:str=product_website_url
        self.cohorts_registry = cohorts

        self.additional_instruction : str = additional_instruction or ""

        self.cohorts_registry = normalize_cohorts_registry(self.cohorts_registry,)
        self.brochure_content = self.fetch_brochure_content(brochure_url = self.brochure_url)
        self.product_website_content = self.fetch_product_details_from_website(website_url = self.product_website_url)
    
    def _output_format(self):

        JSON_FORMAT_STRING = """
        {
            "primary_classified_cohort_id": "<name_of_cohort>",
            "secondary_classified_cohort_ids": ["<name_of_cohort_1>","<name_of_cohort_2>",], # Do not repeat primary cohort in this. You can have multiple secondary cohorts up to 5.
            "reasoning": "<reasoning>",
            "confidence_score": "<float> between 0 and 1"
        }
        """
        return JSON_FORMAT_STRING

        # FORMAT = {
        #     "primary_classified_cohort_id": "<name_of_cohort>",
        #     "secondary_classified_cohort_ids": ["<name_of_cohort>","<name_of_cohort>", ], 
        #     "reasoning": "<reasoning>",
        #     "confidence_score": "<float> between 0 and 1"
        # }

        # return FORMAT
    
    def system_prompt(self):
        messages = [] 
        system_prompt = f"""
        You are an intelligent Cohort Classification assistant.
        You will be provided with a list of Cohort knowledge, user interaction data and product website content if available.
        Your task is to classify the Cohort based on the user input. Choose the highest confidence/priority Cohort. 
        Classify the customer into the most appropriate cohort(s) and provide clear reasoning.

        Cohort knowledge:
        {json.dumps(self.cohorts_registry, indent=4)}

        User Interaction/Conversation/CRM Lead Data:
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
        - If user interaction data is not provided, still try to classify into the closest high-priority cohort. You know try to classify based on product info like maybe this could be family man or first time buyer or second product purchaser...

        ## CLASSIFICATION RULES

        ### 1. DATA SOURCE PRIORITY HIERARCHY
        When classifying, prioritize data sources in this order:
        1. **Direct user interaction data** (conversations, CRM records, form submissions)
        2. **Behavioral signals** (browsing patterns, time spent, pages viewed)
        3. **Explicit inquiries** (test drive requests, quote requests, specific questions)
        4. **Demographic information** (age, income, location, family status)
        5. **Product content** (as contextual support only - do NOT classify based solely on product features)
        6. **If product content has pricing information, You can use that for classification.**

        ### 2. HANDLING DATA UNAVAILABILITY

        **Scenario A: Rich Interaction Data Available**
        - Classify based on behavioral patterns and explicit signals
        - Confidence score: 0.7 - 1.0
        - Reasoning should reference specific interactions

        **Scenario B: Minimal Interaction Data (1-3 data points)**
        - Use available signals + demographic inference
        - Cross-reference with product content for context
        - Confidence score: 0.4 - 0.6
        - Reasoning should acknowledge data limitations

        **Scenario C: No Meaningful Interaction Data**
        - Classify into broadest applicable cohort (e.g., "general_prospect", "website_visitor")
        - If demographics available, use those (e.g., age + income → "young_professional", "family_oriented")
        - If product viewed, infer intent cautiously (e.g., EV page visit → "eco_curious")
        - Confidence score: 0.2 - 0.4
        - Reasoning MUST state: "Limited interaction data available. Classification based on [specific minimal signals]."

        
        **CRITICAL TEMPORAL RULES:**
        - If the customer lifecycle status indicates a successful conversion (e.g., "Delivered", "Invoiced", "Booked", "Purchased", "Converted"):
        - The cohort MUST be assigned based on the interactions and signals that led to the purchase. This help to understand what are the primary factors that led to the purchase.
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
            4. Demographics 
            5. Post-purchase activity (LOWEST PRIORITY - ignore if purchase already happened)
            
        
        ## DERIVED SIGNAL & FEATURE INFERENCE LOGIC (MANDATORY)

        Before classification, you MUST derive implicit signals from the raw data. 
        Do NOT rely only on raw fields. Convert CRM, interaction, and product data into behavioral and intent features.

        ### 1. INTENT SIGNAL DERIVATION
        Infer intent strength using the following signals:
        - Test Drive Requested or Given → strong purchase intent
        - Quote Given Date → strong commercial intent
        - Booking / Invoice / Delivery Date → confirmed conversion
        - Multiple follow-ups → active engagement
        - RequestType like "Test drive", "Quote", "Booking" → explicit intent
        - Converted flag = 1 → successful conversion

        Classify intent level:
        - HIGH_INTENT: test drive OR quote OR booking present
        - MEDIUM_INTENT: follow-ups > 0 OR explicit request type
        - LOW_INTENT: only lead creation without engagement

        ### 2. CHANNEL & SOURCE CLASSIFICATION
        Infer acquisition channel from Lead Source, Campaign Source, UTM fields:
        - Paid Digital: FB Lead Form, Google Ads, performance campaigns
        - Organic Digital: website visits, SEO, direct traffic
        - Dealer Driven: Dealer Digital Direct, showroom leads
        - Referral / Offline: walk-ins, partner leads

        ### 3. FUNNEL STAGE INFERENCE
        Infer lifecycle stage from temporal data:
        - Awareness: only CreatedDate exists
        - Consideration: Test Drive / Quote / Follow-ups exist
        - Decision: Booking / Invoice / Delivery exists
        - Post-Purchase: Service or after-sales signals (ignore for cohort if purchase exists)

        ### 4. DEMOGRAPHIC & GEO INFERENCE (SOFT SIGNALS)
        If explicit demographics are missing, infer probabilistically:
        - City / State / Dealer type → urban vs semi-urban buyer
        - Zip code + product segment → affordability bracket
        - Product type (SUV, EV, premium model) → lifestyle cohort hints
        These signals must NEVER override behavioral intent.

        ### 5. PRODUCT INTEREST PATTERN EXTRACTION
        From brochure and website content, infer:
        - Family-oriented interest (7-seater, safety, space)
        - Performance-oriented interest (engine, torque, speed)
        - Budget-sensitive interest (pricing, offers, mileage)
        - Premium aspiration (luxury features, variants, brand positioning)
        - Eco-conscious interest (EV, hybrid, mileage, emissions)

        Use these ONLY when interaction data is weak.

        ### 6. COHORT MATCHING LOGIC
        When mapping to cohorts:
        - First match cohorts based on intent + funnel stage
        - Then refine using channel and product interest patterns
        - Finally adjust using demographics and geography
        - If multiple cohorts match, choose the highest priority cohort from Cohort knowledge
        - If ambiguity remains, choose the most general high-priority cohort and lower confidence

        ### 7. CONFIDENCE SCORE CALIBRATION
        Confidence must be computed based on signal strength:
        - 0.8 – 1.0 → multiple strong behavioral signals + clear cohort match
        - 0.5 – 0.7 → limited but consistent signals
        - 0.3 – 0.5 → weak signals + inferred patterns
        - 0.2 – 0.3 → mostly speculative classification

        ### 8. ANTI-HALLUCINATION RULE
        - Do NOT invent user behavior or demographics.
        - If data is missing, explicitly state that inference is based on limited signals.
        - Never classify purely based on product description unless no interaction data exists.

        ### 9. BUSINESS-REALISTIC COHORT PRIORITY
        Prefer cohorts that reflect real buying behavior over generic personas.
        Example priority:
        - purchase_driven_cohort > intent_based_cohort > channel_based_cohort > demographic_cohort > product_feature_cohort

        ### 10. EXPLANATION STRUCTURE (MANDATORY)
        Reasoning must follow this order:
        1. Key behavioral signals
        2. Funnel stage inference
        3. Product interest alignment
        4. Why this cohort over others
        5. Data limitations (if any)


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
        
        if self.additional_instruction:
            system_prompt += f"\n\n**ADDITIONAL INSTRUCTIONS:**\n{self.additional_instruction}"

        # (only as secondary support)  
        messages.append({"role": "system", "content": system_prompt})
        return messages
        
    def run(self):
        response = self.exec_json_llm_with_retry(self.llm, messages=self.system_prompt())
        logger.info(f"Response from [cohort_classification_agent]: \n {json.dumps(response, indent=4)}")
        return response
    
    def run_with_events(self) -> Iterator[dict]:
        pass 


def random_assign_users(
        users: List[Dict], 
        cohorts: List[Dict], 
        seed=42,
        weights: List[float] = None 
    ):

    """
    Randomly assigns cohorts to users guaranteeing every cohort is used at least once.
    Strategy:
      1. Shuffle cohort list with the given seed.
      2. Tile shuffled cohorts to cover all users (round-robin), then shuffle
         that full assignment list so the final order is random — not striped.
      3. Each user gets exactly one cohort; all cohorts appear >= floor(n/k) times
         and at most ceil(n/k) times, so distribution is as balanced as possible
         while still being random. 
    Args:
        users (List[Dict]): List of user dictionaries.
        cohorts (List[Dict]): List of cohort dictionaries.
        seed (int): Seed for random number generator.
        weights (List[float]): partial weights allowed, e.g. [0.5, 0.3] for 10 cohorts
    Returns:
        List[Dict]: List of user dictionaries with assigned cohorts.
    """

    rng = random.Random(seed)
    n, k = len(users), len(cohorts)

    if weights is not None:
        if len(weights) > k:
            raise ValueError(f"weights length ({len(weights)}) cannot exceed cohorts length ({k})")
        if any(w < 0 for w in weights):
            raise ValueError("weights cannot be negative")
        if sum(weights) > 1.0 + 1e-6:
            raise ValueError(f"weights sum ({sum(weights)}) cannot exceed 1.0")
        remaining_weight = 1.0 - sum(weights)
        unspecified = k - len(weights)
        fill_weight = remaining_weight / unspecified if unspecified > 0 else 0
        full_weights = weights + [fill_weight] * unspecified
        pool = []
        remaining_users = n
        for i, w in enumerate(full_weights):
            if i < k - 1:
                count = round(w * n)
            else:
                count = remaining_users
            remaining_users -= count
            pool.extend([cohorts[i]] * count)
    else:
        shuffled_cohorts = cohorts[:]
        rng.shuffle(shuffled_cohorts)
        pool = (shuffled_cohorts * (n // k + 1))[:n]
        full_weights = [1/k] * k

    rng.shuffle(pool)
    

    results = []
    distribution = {}
    for user, cohort in zip(users, pool):
        cid = cohort.get("cohort_id", "")
        cname = cohort.get("cohort_name", "")
        distribution[cid] = distribution.get(cid, 0) + 1

        payload = {
            **user,
            "primary_classified_cohort_id": cohort.get("cohort_id", ""),
            "primary_classified_cohort_name": cohort.get("cohort_name", ""),
            "primary_classified_cohort_data": json.dumps(cohort),
            "secondary_classified_cohort_ids": "[]",
            "classification_reasoning": "Randomly assigned (no AI classification)",
            "confidence_score": None,
            "assignment_mode": "random",
        }
        if "campaign_id" in cohort:
            payload["campaign_id"] = cohort["campaign_id"]
        results.append(payload)

    debug = True 
    if debug:
        verbose = {}
        verbose['seed'] = seed 
        verbose['total_customers'] = n
        verbose['total_cohorts'] = k

        final_weights = {}
        for i in range(k):
            cohort = cohorts[i]
            cohort_id = cohort.get("cohort_id")
            if not cohort_id:
                cohort_id = f"cohort_{i}"
            
            weight_value = round(full_weights[i], 4)
            final_weights[cohort_id] = weight_value

        verbose['final_weights'] = final_weights
        verbose['distribution'] = distribution


    return {
        "assigned_users": results,
        "meta": verbose
    }
    # return results


