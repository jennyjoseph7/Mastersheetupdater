import json
import re
from ai_service import ai_service_app
from agents.base_agent import BaseAgent
import pandas as pd 
import os 
from pathlib import Path
import time
from utils import * 

logger = get_logger(__name__)

class CampaignIdeaGeneratorAgent(BaseAgent):
    def __init__(
            self, 
            source:dict=None, 
            classified_cohort:dict=None, 
            affinity_score:dict=None, 
            brochure_url:str=None, 
            product_website_url:str=None, 
            model_identifier:str='azure-gpt-4o'
            ):
        
        self.model_identifier=model_identifier
        self.source=self._load_json(source=source)
        self.classified_cohort=classified_cohort
        self.affinity_score=affinity_score
        self.llm:Callable=lambda messages:ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)

        self.brochure_url:str=brochure_url
        self.product_website_url:str=product_website_url

        self.brochure_content:list[dict]=None
        self.product_website_content:list[dict] = None

        self.brochure_content=self.fetch_brochure_content(brochure_url = self.brochure_url)
        self.product_website_content=self.fetch_product_details_from_website(website_url = self.product_website_url)

    @property
    def whatsapp_template_example_prompt(self):
        prompt = f"""
            {{
                "name": "vehicle_service_confirmation",
                "language": "en_US",
                "category": "utility",
                "parameter_format": "named",
                "components": [
                    {{
                        "type": "body",
                        "text": "Hi {{customer_name}}! Your {{vehicle_model}} is scheduled for service on {{service_date}} at {{service_center}}.",
                        "example": {{
                            "body_text_named_params": [
                                {{
                                    "param_name": "customer_name",
                                    "example": "Amit"
                                }},
                                {{
                                    "param_name": "vehicle_model",
                                    "example": "Jeep Meridian"
                                }},
                                {{
                                    "param_name": "service_date",
                                    "example": "12 Oct 2026"
                                }},
                                {{
                                    "param_name": "service_center",
                                    "example": "Jeep Service Hub – Andheri"
                                }}
                            ]
                        }}
                    }}
                ]
            }}"""
        return prompt


    def whatsapp_templates(self, whatsapp_msgs : list[str]):
        length = None
        if isinstance(whatsapp_msgs, list) and len(whatsapp_msgs) > 0: 
            length = len(whatsapp_msgs)

        system_prompt = f"""
        You are a WhatsApp Message Template Generator AI.

        You will be given:
        1. A list of WhatsApp messages. It will be a list of strings. Each string is a WhatsApp message.

        Use the messages to generate:
        - Exact number of WhatsApp Message Templates for the given number of WhatsApp messages.
        - The WhatsApp Message Templates should be compatible with the WhatsApp API Template Format.

        # Guidelines:
        - EVERY WhatsApp template MUST use named parameters in the body text.
        - DO NOT generate static text-only messages.
        - Each body text MUST contain at least 2 named placeholders using {{param_name}} format.
        - For every placeholder used in the body text, you MUST add a corresponding entry in "body_text_named_params".
        - "body_text_named_params" MUST NOT be empty.
        - Infer realistic automobile-related parameters such as:
            customer_name, vehicle_model, vehicle_make, city, dealer_name, booking_date, test_drive_date, service_center, offer_amount, contact_number.
        - Follow the Sample Message Template structure EXACTLY.
        - Category MUST match the intent (marketing → marketing, service → utility).

        - Sample Message Template: {json.dumps(self.whatsapp_template_example_prompt, indent=4)}

        # Return Strict JSON:
        {{
        "whatsapp_templates": [<whatsapp_templates>, <whatsapp_templates>, <whatsapp_templates>]
        }}
        """

        user_input = f"""
        WhatsApp Messages:
        {json.dumps(whatsapp_msgs, indent=2)}

        Number of WhatsApp Messages: {length}
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        response =  self.exec_json_llm_with_retry(self.llm, messages=messages)
        return response


    # - post_descriptions: generate exactly {num_of_campaign_assets} variants.
    # - instagram_caption_with_hashtags: generate exactly {num_of_campaign_assets} caption per campaign idea.
    # "instagram_caption_with_hashtags": [<string>, <string>, <string>],
    # "post_description": [<string>, <string>, <string>],
    # "whatsapp_msgs": [<string>, <string>, <string>],
    # - whatsapp_msgs: generate exactly {num_of_campaign_assets} variants.
    # • Each message can be up to 7-8 sentences.
    # • Use subtle emojis for engagement.
    # • If competitor exists, include a soft comparison highlighting superiority.
    #     [
    #     {{
    #         "campaign_idea_identifier": "urban_performance_push",
    #         "campaign_objective": "<string>",
    #         "campaign_explanation": "<string>",
    #         "audience": "[<string>]",
    #         "cta": "[<string>, <string>, <string>]",
    #         "campaign_assets": {{
    #             "post_caption": [<string>, <string>, <string>],
    #             "hashtags": [<string>, <string>, <string>],
    #             "hooks": [<string>, <string>, <string>],
    #             "slogan": [<string>, <string>, <string>],
                
    #         }}
    #     }}
    # ]
    #         - Whatsapp messages should be up-to 5-6 sentences. You can add follow-up question in the last sentence. You can also start the message like you know customer were looking for.



    def _campaign_ideas(
            self, 
            num_of_campaign_ideas=3, 
            num_of_campaign_post_sets=3, 
            num_of_hashtags=20,
            *args, 
            **kwargs 
            ):
        
        campaign_theme = kwargs.get("campaign_theme", None)
        core_message_direction = kwargs.get("core_message_direction", None)
        campaign_objective = kwargs.get("campaign_objective", None),
        consumer_insight = kwargs.get("consumer_insight", None)

        brand_name = kwargs.get("brand_name", None)
        product_category = kwargs.get("product_category", None)
        brand_tone = kwargs.get("brand_tone", None)

        system_prompt = f"""
        You are a Product-Driven Campaign Strategy & Creative AI Agent.

        PRODUCT's BRAND CONTEXT:
        - Brand Name: {brand_name}
        - Product Category: {product_category}
        - Brand Tone of Voice: {brand_tone}

        You will be given:
        1. Customer interaction summary 
        2. Cohort classification output 
        3. Customer affinity score
        4. Product brochure content (if available)
        5. Product website content (if available)
        6. Competitor information (if available)

        TASK:
        • Generate {num_of_campaign_ideas} DISTINCT campaign ideas.

        OUTPUT STRUCTURE:
        • Return a LIST (array) of dictionaries.
        • Each dictionary represents ONE campaign idea.

        ASSET COUNT RULES:
            - hashtags: exactly {num_of_hashtags} relevant hashtags for each campaign idea (must be an array).
            - campaign_post_sets: generate exactly {num_of_campaign_post_sets} post sets per campaign idea.
            - Each post set must contain:
                • post_caption: ONE string caption per post set. (must be an array with one element).
                • hooks: ONE string hook per post set (must be an array with one element).
                • slogan: ONE string slogan per post set (must be an array with one element).
                • messages: generate exactly ONE string message per post set (must be an array with one element). Each  message can be up to 7-8 sentences. You can add follow-up question in the last sentence. Use subtle emojis for engagement in the message. You can also start the message like you know customer were looking for if possible.
            - campaign_explanation: generate ONLY ONE explanation per campaign idea.
                • Written for media planners / marketing team.
                • Explain target audience, insight, messaging logic, and best channels.
            - audience: generate type of audience per campaign idea. If cohort classification is available, that would be used.
            - cta: generate CTA variants. (Book a test drive, Book an appointment, Download brochure, Enquire now...etc)

        IDENTIFIER RULES:
        - campaign_idea_identifier must be:
            • short
            • unique
            • lowercase
            • snake_case
            • reflective of the core campaign theme

        GUIDELINES:
        - Understand the product, Carefully Analyze the Product brochure and website if available. Understand the Product's features, specifications etc.
        - If customer interaction summary is missing, rely on cohort classification.
        - Use cohort traits, user intent, and affinity score to personalize messaging.
        - Avoid generic marketing clichés.
        - Try to create unique and engaging messages. Sometime customer name might not be available. So you can try to get name from email address if possible.
        - If there's "Opportunity Name" in the interaction, that might be the customer name. If "Opportunity Owner" is there, that might be representative of the customer.
        - Focus on the customer's needs and preferences.
        - Keep tone premium, confident, and automotive-focused.
        - Do NOT repeat the same captions, hooks, or slogans across variants.
        - Do NOT add or remove fields.
        - Ensure each campaign_post_set has a distinct angle, tone, or theme within the same campaign.
        - If Campaign Theme, Objective, Consumer Insight and Core Message Direction are available, Please consider them while generating the campaign ideas. These needs to be the core of the campaign ideas.

        PRODUCT GUIDELINES:
        - Focus on the product's core usage and industry.
        - Include key features and benefits in all the campaign ideas & post sets.
        - Avoid generic marketing clichés.
        - The Campaign These should highlight Product's core features/benefits. The campaign sets should have Product's name (For eg. Citreon Aircross, Maruti Suzuki Ertiga...), its features.

        OUTPUT RULES:
        - Return STRICT JSON ONLY
        - No markdown
        - No explanations
        - No trailing comments

        FINAL OUTPUT FORMAT EXAMPLE (LIST OF DICTS):

        [
            {{
                "campaign_idea_identifier": "urban_performance_push",
                "campaign_objective": "<string>",
                "campaign_explanation": "<string>",
                "audience": ["<string>"],
                "cta": ["<string>", "<string>"],
                "hashtags": ["<string>", "<string>"],
                
                "campaign_post_sets": [
                    {{
                        "post_caption": ["<string>"],
                        "hooks": ["<string>"],
                        "slogan": ["<string>]",
                        "messages": [<string>]
                    }},
                    {{
                        "post_caption": ["<string>"],
                        "hooks": ["<string>"],
                        "slogan": ["<string>"],
                        "messages": [<string>]
                    }}
                ]
            }}
        ]


        """
        
        user_input = f"""
        Customer Interaction:
        {json.dumps(self.source, indent=2)}

        Classified Cohort:
        {json.dumps(self.classified_cohort, indent=2)}

        Affinity Score:
        {json.dumps(self.affinity_score, indent=2)}
        
        Product Brochure Content:
        {json.dumps(self.brochure_content, indent=2)}
        
        Product Website Content:
        {json.dumps(self.product_website_content, indent=2)}
        
        Campaign Theme:
        {campaign_theme}

        Core Message Direction:
        {core_message_direction}

        Campaign Objective:
        {campaign_objective}

        Consumer Insight:
        {consumer_insight}
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        response =  self.exec_json_llm_with_retry(self.llm, messages=messages)
        return response
    
    def campaign_ideas(
            self, 
            num_of_campaign_ideas=3, 
            num_of_campaign_post_sets=3, 
            num_of_hashtags=20,
            *args, 
            **kwargs 
            ):
        
        campaign_theme = kwargs.get("campaign_theme", None)
        core_message_direction = kwargs.get("core_message_direction", None)
        campaign_objective = kwargs.get("campaign_objective", None),
        consumer_insight = kwargs.get("consumer_insight", None)

        brand_name = kwargs.get("brand_name", None)
        product_category = kwargs.get("product_category", None)
        brand_tone = kwargs.get("brand_tone", None)

        system_prompt = f"""
        You are a Product-Driven Campaign Strategy & Creative AI Agent.

        PRODUCT's BRAND CONTEXT:
        - Brand Name: {brand_name}
        - Product Category: {product_category}
        - Brand Tone of Voice: {brand_tone}

        You will be given:
        1. Customer interaction summary 
        2. Cohort classification output 
        3. Customer affinity score (if available)
        4. Product brochure content (if available)
        5. Product website content (if available)
        6. Competitor information (if available)

        TASK:
        • Generate {num_of_campaign_ideas} DISTINCT campaign ideas.

        OUTPUT STRUCTURE:
        • Return a LIST (array) of dictionaries.
        • Each dictionary represents ONE campaign idea.

        ASSET COUNT RULES:
            - hashtags: exactly {num_of_hashtags} relevant hashtags for each campaign idea (must be an array).
                • MANDATORY: At least 60% must be product-specific hashtags including the exact product model/variant name
                • Product-specific examples: #CitroenAircrossC3, #AircrossAdventure, #AircrossFeatures
                • Remaining 40% can be generic category/industry hashtags
                • NEVER use only generic brand hashtags
            - campaign_post_sets: generate exactly {num_of_campaign_post_sets} post sets per campaign idea.
            - Each post set must contain:
                • post_caption: ONE string caption per post set (must be an array with one element).
                    ⚠️ MANDATORY: Must contain the full product name/model within the first 10 words
                    ⚠️ REJECTION CRITERIA: Captions without explicit product name will be invalid
                • hooks: ONE string hook per post set (must be an array with one element).
                    ⚠️ MANDATORY: Must directly reference the specific product name or model
                    ⚠️ INVALID: Generic hooks like "Discover luxury" or "Experience innovation"
                    ✅ VALID: "Discover the Citroen Aircross C3's luxury" or "Experience Aircross innovation"
                • slogan: ONE string slogan per post set (must be an array with one element).
                    ⚠️ MANDATORY: Must include or directly reference the product name
                    ⚠️ Product name can be woven into the slogan creatively but must be identifiable
                • messages: generate exactly ONE string message per post set (must be an array with one element).
                    ⚠️ MANDATORY REQUIREMENTS:
                        - Product name must appear in the first 2 sentences
                        - Must mention at least 2-3 specific product features/specifications
                        - Must be 7-8 sentences long
                        - Must include subtle emojis for engagement
                        - Can add follow-up question in the last sentence
                        - Can personalize by referencing customer's search/interest if available
                    ⚠️ REJECTION CRITERIA: Generic messages like "our latest offering" or "this amazing product" without explicit product name
            - campaign_explanation: generate ONLY ONE explanation per campaign idea.
                • Written for media planners / marketing team.
                • MANDATORY: Must explicitly state the product name/model in the explanation
                • Explain target audience, insight, messaging logic, and best channels.
                • Must reference specific product features being highlighted
            - audience: generate type of audience per campaign idea. If cohort classification is available, that would be used.
            - cta: generate CTA variants that are product-specific (must be an array).
                ⚠️ MANDATORY: ALL CTAs must include the product name or clear product reference
                ⚠️ INVALID: "Book a test drive", "Download brochure"
                ✅ VALID: "Book a Citroen Aircross test drive", "Download Aircross C3 brochure", "Enquire about Aircross now"
                • Generate at least 2 CTA variants per campaign

        IDENTIFIER RULES:
        - campaign_idea_identifier must be:
            • short
            • unique
            • lowercase
            • snake_case
            • MANDATORY: Include product reference (e.g., "aircross_urban_adventure" NOT "urban_adventure")

        GUIDELINES:
        - Understand the product, Carefully Analyze the Product brochure and website if available. Understand the Product's features, specifications etc.
        - If customer interaction summary is missing, rely on cohort classification.
        - Use cohort traits, user intent, and affinity score to personalize messaging.
        - Avoid generic marketing clichés.
        - Try to create unique and engaging messages. Sometime customer name might not be available. So you can try to get name from email address if possible.
        - If there's "Opportunity Name" in the interaction, that might be the customer name. If "Opportunity Owner" is there, that might be representative of the customer.
        - Focus on the customer's needs and preferences.
        - Keep tone premium, confident, and automotive-focused.
        - Do NOT repeat the same captions, hooks, or slogans across variants.
        - Do NOT add or remove fields.
        - Ensure each campaign_post_set has a distinct angle, tone, or theme within the same campaign.
        - If Campaign Theme, Objective, Consumer Insight and Core Message Direction are available, Please consider them while generating the campaign ideas. These needs to be the core of the campaign ideas.

        ═══════════════════════════════════════════════════════════════════════
        ⚠️  CRITICAL PRODUCT-SPECIFIC REQUIREMENTS - NON-NEGOTIABLE ⚠️
        ═══════════════════════════════════════════════════════════════════════
        
        STEP 1 - PRODUCT IDENTIFICATION (MANDATORY):
        - Extract the EXACT product name/model from brochure and website content
        - Identify the full product designation (e.g., "Citroen Aircross C3", "Samsung Galaxy S24 Ultra")
        - If multiple variants exist, select the most relevant based on customer interaction
        - Store this product name and use it CONSISTENTLY throughout ALL outputs
        
        STEP 2 - VALIDATION CHECKLIST (Every output MUST pass):
        ✓ Product name appears in campaign_idea_identifier
        ✓ Product name appears in campaign_explanation (at least once)
        ✓ Product name appears in ALL post_captions (within first 10 words)
        ✓ Product name/reference appears in ALL hooks
        ✓ Product name appears in ALL slogans
        ✓ Product name appears in ALL messages (within first 2 sentences + feature mentions)
        ✓ Product name appears in ALL CTAs
        ✓ At least 60% of hashtags are product-specific
        ✓ At least 2-3 specific product features mentioned in each message
        
        STEP 3 - FORBIDDEN PATTERNS (NEVER use these):
        ✗ "Our latest offering"
        ✗ "This amazing product"
        ✗ "Experience luxury" (without product name)
        ✗ "Discover innovation" (without product name)
        ✗ Generic brand-only references
        ✗ "The new model" or "our flagship"
        ✗ CTAs without product name
        ✗ Hashtags like #BrandName only (must include model)
        
        STEP 4 - REQUIRED APPROACH:
        - Think PRODUCT LAUNCH, not brand awareness
        - Think PRODUCT SPOTLIGHT, not company promotion
        - Every piece of content should sell THIS SPECIFIC PRODUCT
        - Features, specs, and benefits should be PRODUCT-SPECIFIC, not generic
        - Customer should know EXACTLY which product is being promoted
        
        STEP 5 - FEATURE INTEGRATION (MANDATORY):
        - Extract 5-10 key features from brochure/website
        - Each campaign post set must highlight different features
        - Features must be specific (e.g., "1.2L turbocharged engine" NOT "powerful engine")
        - Weave features naturally into messages, not as bullet points

        ═══════════════════════════════════════════════════════════════════════

        PRODUCT GUIDELINES:
        - Focus on the product's core usage and industry.
        - Include key features and benefits in all the campaign ideas & post sets.
        - Avoid generic marketing clichés.
        - The Campaign should highlight the SPECIFIC product's core features/benefits with explicit product name mentions (For eg. "Citroen Aircross", "Maruti Suzuki Ertiga", etc.)
        - All campaign post sets MUST include the product name and its standout features prominently
        - Think product launch/product spotlight, not brand awareness
        - ZERO TOLERANCE for generic product references

        OUTPUT RULES:
        - Return STRICT JSON ONLY
        - No markdown
        - No explanations
        - No trailing comments
        - If product name cannot be identified from brochure/website, use brand_name + product_category as fallback

        FINAL OUTPUT FORMAT EXAMPLE (LIST OF DICTS):

        [
            {{
                "campaign_idea_identifier": "aircross_urban_performance_push",
                "campaign_objective": "Drive awareness and test drives for Citroen Aircross C3",
                "campaign_explanation": "This campaign targets urban millennials seeking versatile SUVs. The Citroen Aircross C3's key features like 210mm ground clearance and spacious cabin are highlighted to appeal to adventure-seekers who need practical daily drivers. Best channels: Instagram Reels, YouTube pre-roll.",
                "audience": ["Urban millennials 28-40", "Adventure enthusiasts"],
                "cta": ["Book Aircross C3 test drive", "Download Aircross brochure", "Explore Aircross features"],
                "hashtags": ["#CitroenAircross", "#AircrossC3", "#AircrossAdventure", "#CitroenAircrossIndia", "#AircrossFeatures", "#CompactSUV", "#UrbanAdventure", "#SUVLife"],
                
                "campaign_post_sets": [
                    {{
                        "post_caption": ["The Citroen Aircross C3 redefines urban adventure with 210mm ground clearance and bold design"],
                        "hooks": ["Ready to conquer city streets? Meet the Aircross C3"],
                        "slogan": ["Aircross: Built for Every Journey"],
                        "messages": ["Hi! We noticed you were exploring compact SUVs perfect for city adventures. The Citroen Aircross C3 might be exactly what you're looking for! 🚗 With an impressive 210mm ground clearance, this compact SUV handles everything from city potholes to weekend getaways effortlessly. The spacious cabin seats 5 comfortably, while the 315-liter boot space ensures you never leave anything behind. Powered by a 1.2L turbocharged engine, the Aircross C3 delivers peppy performance without compromising on fuel efficiency. The bold design with LED projector headlamps and signature dual-tone roof makes heads turn everywhere you go. Plus, the elevated driving position gives you commanding road visibility ✨ Would you like to experience the Aircross C3 firsthand with a test drive?"]
                    }},
                    {{
                        "post_caption": ["Citroen Aircross C3: Where comfort meets capability in every drive"],
                        "hooks": ["Your daily drive deserves the Aircross C3 upgrade"],
                        "slogan": ["Aircross C3: Adventure Approved, City Ready"],
                        "messages": ["The Citroen Aircross C3 is engineered for those who refuse to compromise! This versatile SUV brings together comfort, style, and performance in one compelling package 🌟 Inside, you'll find a thoughtfully designed cabin with class-leading shoulder room and flexible seating configurations. The 7-inch touchscreen infotainment system keeps you connected with Apple CarPlay and Android Auto. Safety isn't an afterthought—dual airbags, ABS with EBD, and rear parking sensors come standard. The Aircross C3's 180mm of approach angle means speed bumps and rough roads are no longer a concern. Available in vibrant dual-tone color combinations, it's a SUV that reflects your personality 💫 Ready to make every journey memorable?"]
                    }}
                ]
            }}
        ]


        """
        
        user_input = f"""
        Customer Interaction:
        {json.dumps(self.source, indent=2)}

        Classified Cohort:
        {json.dumps(self.classified_cohort, indent=2)}

        Affinity Score:
        {json.dumps(self.affinity_score, indent=2)}
        
        Product Brochure Content:
        {json.dumps(self.brochure_content, indent=2)}
        
        Product Website Content:
        {json.dumps(self.product_website_content, indent=2)}
        
        Campaign Theme:
        {campaign_theme}

        Core Message Direction:
        {core_message_direction}

        Campaign Objective:
        {campaign_objective}

        Consumer Insight:
        {consumer_insight}
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        response =  self.exec_json_llm_with_retry(self.llm, messages=messages)
        return response
    

    def generate_minimal_brand_profile(self):
        system_prompt = """
        You are a Brand Insight Extraction AI.

        TASK:
        Analyze the provided product brochure and website content and extract ONLY the following information:

        1. Brand Name  
        2. Product Category  
        3. Brand Tone of Voice  

        DEFINITIONS:

        - brand_name:
        The official brand or manufacturer name (e.g., Citroën, Jeep, Tata Motors)

        - product_category:
        The primary category of the product such as:
        SUV, Hatchback, Sedan, EV, Luxury Car, Two-Wheeler, etc.

        - brand_tone:
        Describe the tone of communication in 4–6 adjectives only.
        Examples:
            "premium, confident, youthful, innovative"
            "friendly, practical, family-oriented, trustworthy"

        RULES:
        - Use ONLY the provided content.
        - Do NOT invent information.
        - Keep tone concise.
        - If multiple tones are detected, summarize the dominant tone.
        - Return STRICT JSON only.
        - No markdown or explanations.

        OUTPUT FORMAT:

        {
            "brand_name": "<string>",
            "product_category": "<string>",
            "brand_tone": "<string>"
        }
        """

        user_input = f"""
        Product Brochure Content:
        {json.dumps(self.brochure_content, indent=2)}

        Product Website Content:
        {json.dumps(self.product_website_content, indent=2)}
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        response = self.exec_json_llm_with_retry(self.llm, messages=messages)

        return response


        
    def run(
            self, 
            num_of_campaign_ideas=3, 
            num_of_campaign_post_sets=3, 
            num_of_hashtags=20, 
            *args, 
            **kwargs 
            ):
        brand_profile:dict = self.generate_minimal_brand_profile()
        campaign_ideas:list[dict] = self.campaign_ideas(
            num_of_campaign_ideas=num_of_campaign_ideas, 
            num_of_campaign_post_sets=num_of_campaign_post_sets, 
            num_of_hashtags=num_of_hashtags, 
            brand_name=brand_profile["brand_name"],
            product_category=brand_profile["product_category"],
            brand_tone=brand_profile["brand_tone"],
            *args, 
            **kwargs
            )
        
        # for campaign_idea in campaign_ideas:
        #     post_sets: list[dict] = campaign_idea.get("campaign_post_sets", [])
        #     for post_set in post_sets:
        #         whatsapp_msgs: list[str] = post_set.get("messages", [])
        #         if whatsapp_msgs:
        #             whatsapp_templates = self.whatsapp_templates(whatsapp_msgs).get("whatsapp_templates", [])
        #             post_set["whatsapp_templates"] = whatsapp_templates

        return campaign_ideas
    