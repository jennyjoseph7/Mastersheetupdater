import json
import re
from ai_service import ai_service_app
from agents.base_agent import BaseAgent
import pandas as pd 
import os 
from pathlib import Path

class CampaignIdeaGeneratorAgent(BaseAgent):
    def __init__(self, source, classified_cohort : dict, brochure_url=None, product_website_url=None, model_identifier='azure-gpt-4o'):
        self.model_identifier = model_identifier
        self.source = self._load_json(source=source)
        self.classified_cohort = classified_cohort
        self.llm = lambda messages : ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)

        self.brochure_url : str = brochure_url
        self.product_website_url : str = product_website_url

        self.brochure_content : list[dict] = None
        self.product_website_content : list[dict] = None

        if self.brochure_url:
            self.brochure_content = self.fetch_brochure_content(brochure_url = self.brochure_url)
    
        if self.product_website_url:
            self.product_website_content = self.fetch_product_details_from_website(website_url = self.product_website_url)
            

    def generate_campaign_ideas(self):
        system_prompt = f"""
        You are a Campaign Idea Generator AI.

        You will be given:
        1. Customer interaction summary.
        2. The cohort classification output.
        3. Product brochure content if available.
        4. Product website content if available.

        Use cohort traits + message tags + user intent to generate:
        - 3 campaign message ideas
        - 3 retargeting nudges
        - 3 short hooks
        - 3 WhatsApp follow-up messages. Can be up-to 5-6 sentences per message. Add subtle emojis in the message for user engagement. If competitor is available, add a mention of it. Show how your product is superior to it.
        - 3 value propositions
        - 3 variant recommendations (if possible)

        Return STRICT JSON:
        {{
        "campaign_ideas": [],
        "nudges": [],
        "hooks": [],
        "whatsapp_msgs": [],
        "value_props": [],
        "variant_recos": []
        }}
        """

        user_input = f"""
        Customer Interaction:
        {json.dumps(self.source, indent=2)}

        Classified Cohort:
        {json.dumps(self.classified_cohort, indent=2)}
        
        Product Brochure Content:
        {json.dumps(self.brochure_content, indent=2)}
        
        Product Website Content:
        {json.dumps(self.product_website_content, indent=2)}
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        result = self.llm(messages)
        try:
            return self.extract_json_from_llm_response(result)
        except:
            return {"error": "LLM returned malformed JSON", "raw": result}
        
    def run(self):
        return self.generate_campaign_ideas()