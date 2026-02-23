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

DEFAULT_AUTOMOTIVE_COHORT_IDS = {
    "awareness": ["brand_discovery_users", "feature_explorers", "lifestyle_alignment_seekers", "performance_curiosity_users",],
    "consideration": ["spec_comparison_users", "price_value_evaluators", "finance_inquirers", "ev_curiosity_users", "safety_tech_researchers",],
    "high_intent": ["test_drive_seekers","dealer_locator_users", "offer_page_visitors", "high_intent_buyers",],
    "ownership": ["existing_owners", "service_maintenance_users", "accessory_upgrade_seekers", "warranty_insurance_inquirers",],
    "retargeting": ["dropped_high_intent_users", "inactive_returning_users", "abandoned_configurator_users", "low_intent_buyers",],
}

_automotive_cohorts = [v for cohort_list in DEFAULT_AUTOMOTIVE_COHORT_IDS.values() for v in cohort_list] 

automotive_cohorts = [
    # Purchase Journey & Intent Stage (1-20)
    "brand_discovery_users",
    "feature_explorers",
    "price_comparison_seekers",
    "test_drive_intenders",
    "brochure_downloaders",
    "dealership_visitors",
    "finance_enquiry_users",
    "insurance_enquiry_users",
    "online_configurators",
    "variant_comparers",
    "accessory_browsers",
    "review_readers",
    "video_review_watchers",
    "first_time_enquirers",
    "repeat_researchers",
    "booking_intenders",
    "offer_seekers",
    "exchange_evaluators",
    "waiting_period_sensitive",
    "immediate_purchase_ready",

    # Vehicle Type Preference (21-45)
    "suv_seekers",
    "compact_suv_seekers",
    "mid_size_suv_seekers",
    "full_size_suv_seekers",
    "sedan_lovers",
    "compact_sedan_seekers",
    "premium_sedan_seekers",
    "hatchback_buyers",
    "premium_hatchback_buyers",
    "mpv_seekers",
    "luxury_car_aspirers",
    "sports_car_enthusiasts",
    "electric_vehicle_seekers",
    "hybrid_vehicle_seekers",
    "diesel_preference_buyers",
    "petrol_preference_buyers",
    "cng_preference_buyers",
    "automatic_transmission_seekers",
    "manual_transmission_lovers",
    "four_by_four_offroad_seekers",
    "pickup_truck_seekers",
    "convertible_aspirers",
    "coupe_lovers",
    "micro_suv_seekers",
    "van_seekers",

    # Demographic Based (46-75)
    "young_professionals",
    "gen_z_buyers",
    "millennial_buyers",
    "family_with_kids",
    "newly_married_couples",
    "single_urban_commuters",
    "senior_citizen_buyers",
    "women_car_buyers",
    "first_jobbers",
    "high_income_executives",
    "middle_income_families",
    "budget_conscious_buyers",
    "rural_buyers",
    "small_town_buyers",
    "metro_city_residents",
    "suburban_families",
    "entrepreneurs",
    "corporate_fleet_decision_makers",
    "government_employee_buyers",
    "students_first_car",
    "expatriate_returnees",
    "dual_income_households",
    "large_joint_families",
    "working_mothers",
    "tech_industry_professionals",
    "medical_professionals",
    "sales_professionals",
    "frequent_travelers",
    "retired_leisure_buyers",
    "young_couples_no_kids",

    # Usage Pattern Based (76-110)
    "daily_commuters",
    "highway_travel_enthusiasts",
    "long_distance_drivers",
    "weekend_getaway_seekers",
    "offroad_adventurers",
    "city_only_users",
    "ride_share_drivers",
    "taxi_fleet_owners",
    "delivery_vehicle_users",
    "school_run_parents",
    "business_travel_users",
    "airport_commuters",
    "hill_station_travelers",
    "bad_road_users",
    "heavy_luggage_travelers",
    "pet_friendly_car_seekers",
    "cycling_trip_users",
    "camping_enthusiasts",
    "towing_requirement_users",
    "monsoon_heavy_use",
    "high_mileage_drivers",
    "low_mileage_users",
    "multiple_car_households",
    "single_car_households",
    "occasional_drivers",
    "night_drive_users",
    "chauffeur_driven_preference",
    "self_drive_preference",
    "car_pooling_users",
    "interstate_travelers",
    "rural_road_users",
    "construction_site_users",
    "college_commuters",
    "premium_daily_commuters",
    "elderly_family_transport",

    # Psychographic / Motivation (111-150)
    "performance_curiosity_users",
    "design_style_seekers",
    "safety_conscious_buyers",
    "technology_enthusiasts",
    "status_symbol_seekers",
    "value_for_money_buyers",
    "brand_loyalists",
    "eco_conscious_buyers",
    "low_maintenance_seekers",
    "resale_value_conscious",
    "comfort_first_buyers",
    "adventure_lifestyle_seekers",
    "luxury_experience_seekers",
    "minimalist_practical_buyers",
    "image_conscious_buyers",
    "peer_influenced_buyers",
    "social_media_influenced",
    "influencer_followers",
    "early_adopters",
    "late_majority_buyers",
    "risk_averse_buyers",
    "deal_hunters",
    "feature_maximizers",
    "mileage_focused_buyers",
    "power_speed_lovers",
    "silent_cabin_seekers",
    "music_system_lovers",
    "connected_car_seekers",
    "gadget_friendly_buyers",
    "family_safety_prioritizers",
    "rugged_look_seekers",
    "color_customization_lovers",
    "interior_comfort_seekers",
    "boot_space_seekers",
    "low_cost_of_ownership",
    "high_end_audio_seekers",
    "sunroof_aspirers",
    "premium_brand_aspirers",
    "practical_utility_seekers",
    "driver_assistance_seekers",

    # Ownership Stage (151-170)
    "first_time_car_buyers",
    "first_time_suv_buyers",
    "upgrade_from_hatchback",
    "upgrade_from_sedan",
    "downgrade_seekers",
    "additional_car_buyers",
    "replacement_buyers",
    "loyal_brand_repeaters",
    "warranty_concerned_buyers",
    "service_package_seekers",
    "extended_warranty_buyers",
    "accessories_upgraders",
    "modification_enthusiasts",
    "insurance_switchers",
    "loan_dependent_buyers",
    "cash_buyers",
    "exchange_offer_users",
    "pre_owned_car_considerers",
    "new_car_only_buyers",
    "long_term_owners",

    # Price & Finance Mindset (171-185)
    "entry_level_budget_buyers",
    "mid_range_value_seekers",
    "premium_segment_buyers",
    "luxury_segment_aspirers",
    "ultra_luxury_buyers",
    "low_downpayment_seekers",
    "emi_sensitive_buyers",
    "total_cost_sensitive",
    "high_discount_seekers",
    "festive_offer_buyers",
    "corporate_discount_users",
    "student_discount_seekers",
    "rural_finance_seekers",
    "subscription_model_seekers",
    "leasing_preference_users",

    # Geographic & Contextual (186-200)
    "urban_metro_buyers",
    "tier2_city_buyers",
    "tier3_town_buyers",
    "rural_area_buyers",
    "coastal_region_users",
    "hill_area_users",
    "hot_climate_users",
    "cold_region_users",
    "flood_prone_region_users",
    "narrow_road_users",
    "high_traffic_city_users",
    "gated_community_residents",
    "apartment_parking_conscious",
    "farmhouse_owners",
    "tourist_region_operators"
]


automotive_cohorts = [
    "urban_metro_buyers",
    "tier2_city_buyers",
    "tier3_town_buyers",
    "rural_area_buyers",
    "coastal_region_users",
    "hill_area_users",
    "hot_climate_users",
    "cold_region_users",
    "flood_prone_region_users",
    "narrow_road_users",
    "high_traffic_city_users",
    "gated_community_residents",
    "apartment_parking_conscious",
    "farmhouse_owners",
    "tourist_region_operators"
]


class CohortGenerationAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.brochure_url : str = kwargs.get("brochure_url", None)
        self.product_website_url : str = kwargs.get("product_website_url", None)

        self.brochure_content : list[dict] = self.fetch_brochure_content(brochure_url = self.brochure_url)
        self.product_website_content : list[dict] = self.fetch_product_details_from_website(website_url = self.product_website_url)
        
        self.model_identifier : str = kwargs.get("model_identifier", "azure-gpt-4o")
        self.llm : Callable = lambda messages : ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)

        self.required_funnel_stages = [
            "Awareness", 
            "Consideration", 
            "High_intent", 
            "Conversion", 
            "Retention"
        ]

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
                "intent_level": "<low | medium | high>",
                "description": "<clear business description>",
                "priority": "<integer_lower_is_higher_priority>",
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
    

#     "eligibility_rules": {
#     "events": [
#         {
#             "type": "<event_type>",
#             "page": "<page_or_context>",
#             "min_count": "<number>",
#             "min_seconds": "<number_optional>"
#         }
#     ]  
# },



    def _allowed_cohort_domain(self, domain="automotive"):
        if domain == "automotive":
            return automotive_cohorts
        return {}
    
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

    # [id for ids in allowed_cohorts.values() for id in ids]
    def _cohort_generation_system_prompt(self):
        _classified_identifier = self._classify_domain()
        logger.info(f"Classified Identifier: {json.dumps(_classified_identifier, indent=4)}")
        identifier = self._classify_domain()["identifier"].lower() or "automotive"
        allowed_cohorts = self._allowed_cohort_domain(identifier=identifier)

        system_prompt = f"""
        You are a Cohort Generation Agent for a production-grade personalization system.

        You will be provided with:
        - Product brochure content (PDF extracted text)
        - Product website content

        Your task:
        Your task is to generate multiple user cohorts based on the product positioning and target market suitable for real-world marketing and personalization systems.

        Instructions:
        - Analyze both brochure and website content deeply.
        - Identify distinct user segments based on intent, behavior, and value.
        - Generate cohorts covering the full funnel (awareness → conversion).
        - Cohorts must be mutually distinguishable and production-ready.
        - Rules must be deterministic and convertible into code.
        
        - Important:
        - You must generate definitions for ALL {len(allowed_cohorts)} cohorts from this list:
        {json.dumps(allowed_cohorts, indent=2)}

        Your response MUST strictly follow this JSON schema:

        {json.dumps(self.output_schema, indent=4, default=str)}

        Rules:
        - Output valid JSON only
        - Do not include explanations or markdown
        - Do not hallucinate unsupported product features
        """
        messages = [
            {
                "role": "system", 
                "content": system_prompt
            }
        ]     
        return messages
    
    def _build_contextualization_prompt(self, cohort_batch:list):
        system_prompt = f"""
        You are a Cohort Contextualization Agent.

        Your job is NOT to create new cohorts.

        Your job is to:

        - Take an existing master cohort taxonomy
        - Understand the provided product deeply
        - Convert GENERIC cohorts into PRODUCT-SPECIFIC cohort definitions

        You must generate definitions ONLY for the following cohorts:

        {json.dumps(cohort_batch, indent=4)}

        Instructions:
        - Analyze brochure and website content carefully
        - For EACH provided cohort_id:
            - Write product-specific description
            - Define clear eligibility rules
            - Define behavioral signals
            - Assign intent level
            - Assign priority
            - Suggest channels
        - Do NOT invent new cohort IDs
        - Do NOT skip any cohort
        - All rules must be actionable and deterministic

        OUTPUT FORMAT:
        Strictly follow this JSON schema:

        {json.dumps(self.output_schema, indent=4)}

        IMPORTANT:
        - Respond ONLY with valid JSON
        - No explanations or markdown
        """

        messages = [{"role": "system", "content": system_prompt}]

        return messages
    
    def chunk_list(self, items:list, chunk_size=10):
        for i in range(0, len(items), chunk_size):
            yield items[i:i + chunk_size]
    
    def run(self, batch_size=10):
        final_cohorts = []
        classification = self._classify_domain()
        domain = classification.get("identifier", "automotive").lower()
        logger.info(f"Domain classified as: '{domain}'")
        allowed_cohorts = self._allowed_cohort_domain(domain=domain)

        try:
            cohort_batches = list(self.chunk_list(allowed_cohorts, batch_size))
            for batch_idx, cohort_batch in enumerate(cohort_batches, start=1):
                logger.info(f"Running cohort contextualization batch {batch_idx}/{len(cohort_batches)}")
                messages = self._build_contextualization_prompt(cohort_batch = cohort_batch)
                if self.brochure_content is not None:
                    messages.append({
                        "role": "user", 
                        "content": f"Product Brochure Content: {json.dumps(self.brochure_content, indent=4, default=str)}"
                        })
                if self.product_website_content is not None:
                    messages.append({
                        "role": "user", 
                        "content": f"Product Website Content: {json.dumps(self.product_website_content, indent=4, default=str)}"
                        })
                response = self.exec_json_llm_with_retry(self.llm, messages=messages)
                coherts = response.get("cohorts", [])
                final_cohorts.extend(coherts)
        
            final_result = {"cohorts": [{"idx": idx, **cohort} for idx, cohort in enumerate(final_cohorts, start=1)]}
            return final_result

        except Exception as e:
            traceback.print_exc()
            response = {"error": str(e), "raw_response": response}
        return response



class ProductCohortGenerationAgent(BaseAgent):
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