import json
import os
from datetime import datetime
from ai_service import ai_service_app

try:
    from .base_agent import BaseAgent, gryd
except ImportError:
    from base_agent import BaseAgent, gryd 


class CampaignIdeaCreatorAgent(BaseAgent):
    """
    Autobot Agent: Generates ideas for campaign based on the type of campaign and objective of the campaign.
    Works with API-based args and kwargs (from Postman / external services).
    Example input : 
    {
      campaign_type: "pre-sale"
      campaign_objective: "Exchange / Loyalty Bonus Offer"
      dealership_idea: {
        languages: ["English"]
        campaign_offer: "₹10,000 exchange bonus" }

    }

    Example Output : 
    {
        "campaign_type": "pre-sales",
        "campaign_objective": "Exchange / Loyalty Bonus Offer",
        "languages": [
          "English"
        ],
        "campaign_offer": "Score a massive ₹10,000 exchange bonus on your next brand new ride!",
        "campaign_name": "Upgrade & Drive: Loyalty Exchange Event",
        "campaign_tagline": "Your Old Car Just Got You an Amazing Deal!",
        "idea": "Target existing customers or prospects looking to upgrade by highlighting a significant monetary bonus for trading in their current vehicle.",
        "campaign_description": "Time to trade up to that dream car! We're giving you an extra ₹10,000 bonus when you exchange your old vehicle with us. This is the best value you'll get for your current car. Don't miss out on maximizing your savings today.",
        "campaign_tone": "Exciting and Value-Driven",
        "urgency_hook": "The ₹10,000 bonus offer vanishes at the end of the month!",
        "ctas": [
          "Exchange Old Car",
          "Book a Test Drive",
          "Request a Call Back"
        ],
        "channels": [
          "whatsapp_chat",
          "email"
        ]
    }

    """

    # Constants
    VALID_CHANNELS = [
        "rcs", "email", "web_chat", "web_chat_voice", "fb_chat", 
        "insta_chat", "twitter_chat", "voice_phone", "whatsapp_chat", 
        "whatsapp_voice_note", "whatsapp_voice_call", "zoom_bot", "ms_teams"
    ]
    
    PRE_SALE_FIELDS = [
        "campaign_type", "campaign_name", "campaign_tagline", "campaign_objective",
        "idea", "campaign_offer", "campaign_description", "campaign_tone",
        "urgency_hook", "ctas", "channels", "init_conversation", "email_subject", "email_body"
    ]
    
    POST_SALE_FIELDS = [
        "campaign_type", "campaign_name", "campaign_objective", "idea",
        "campaign_tagline", "campaign_offer", "campaign_description", 
        "campaign_tone", "urgency_hook", "ctas", "channels", "init_conversation", "email_subject", "email_body"
    ]
    
    PRE_SALE_KEYWORDS = {"pre-sale", "pre_sale", "pre sale", "pre-sales", "pre_sales", "presales"}
    POST_SALE_KEYWORDS = {"post-sale", "post_sale", "post sale", "post-sales", "post_sales", "postsales"}
    
    MAX_ATTEMPTS = 5
    NO_OFFER_VALUES = {"no offer", "no_offer", "null", "none", ""}

    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        
        # Validate source
        if not source or not isinstance(source, dict):
            raise ValueError("source must be a non-empty dictionary")
        
        self.source = source
        self.campaign_type = self._validate_campaign_type(source.get("campaign_type"))
        self.campaign_objective = self._validate_campaign_objective(source.get("campaign_objective"))
        
        self.dealership_id = source.get("dealership_id", "")
        self.languages = self._validate_languages(source.get("languages", ["English"]))
        self.campaign_offer = source.get("campaign_offer", "No Offer")
        self.logger = kwargs.get("logger") or gryd.hp.get_logger(__name__)

        self.model_identifier = "gcp-gemini-2.5-flash-lite"

    def _validate_campaign_type(self, campaign_type):
        """Validate campaign type with proper error message."""
        if not campaign_type:
            raise ValueError("campaign_type is required in source data")
        
        campaign_lower = campaign_type.lower()
        if (campaign_lower not in self.PRE_SALE_KEYWORDS and 
            campaign_lower not in self.POST_SALE_KEYWORDS):
            raise ValueError(f"Invalid campaign_type: {campaign_type}")
        
        return campaign_type

    def _validate_campaign_objective(self, objective):
        """Validate campaign objective."""
        if not objective:
            raise ValueError("campaign_objective is required in source data")
        return objective

    def _validate_languages(self, languages):
        """Ensure languages is always a list."""
        if isinstance(languages, str):
            return [languages]
        elif isinstance(languages, list):
            return languages
        else:
            return ["English"]

    def _get_campaign_type_details(self):
        """Get fields and normalized type based on campaign type."""
        campaign_type_lower = self.campaign_type.lower()
        
        if campaign_type_lower in self.PRE_SALE_KEYWORDS:
            return self.PRE_SALE_FIELDS, "pre-sales"
        elif campaign_type_lower in self.POST_SALE_KEYWORDS:
            return self.POST_SALE_FIELDS, "post-sales"
        else:
            raise ValueError(f"Unsupported campaign type: {self.campaign_type}")

    def _is_no_offer(self, offer):
        """Check if the offer should be considered as no offer."""
        if not offer or not isinstance(offer, str):
            return True
        return offer.lower() in self.NO_OFFER_VALUES

    def _get_presale_prompt(self, existing_data: dict, pre_sale_fields):
        """Builds LLM prompts for pre-sales campaigns with strict field enforcement."""

        language = existing_data.get("languages",["English"])[0]

        system_prompt = f"""
        You are an intelligent Campaign Generator Autobot for automotive dealership pre-sales campaigns.

        Important rules (follow exactly):
        1. OUTPUT: Return a single valid JSON object and nothing else (no prose, no code fences).
        2. KEYS: The JSON object MAY contain only the following keys (and no others):
           {pre_sale_fields}
        3. TYPES & CONSTRAINTS:
           - The language you'll be using to generate description, campaign_name, cta_buttons, campaign_tagline, urgency_hook, and cta_buttons must be colloquial {language}, if the word is difficult in {language} then you can use english word also but the script must be of {language} only. 
           - Keys for the json response will remain in english only, the values, titles and descriptions should be in colloquial {language}
           - campaign_type: string — must be 'pre-sales' (lowercase).
           - campaign_name: non-empty string. should be generated based on the campaign_type, and campaign_objective.
           - campaign_tagline: non-empty catchy tagline.
           - campaign_objective: non-empty string (preserve existing value if present).
           - idea: non-empty string describing the campaign concept.
           - campaign_offer: Check whether the dealer wants to give any offer : {json.dumps(existing_data.get("campaign_offer", "No Offer"))} . If not mentioned any offer then do not return offer. If offer is mentioned then make it sound attractive offer in {language} only.
           - campaign_description: non-empty string (2-4 concise sentences).
           - campaign_tone: non-empty string describing the tone (e.g., "Persuasive", "Urgent", "Exciting").
           - urgency_hook: single short string (ONE urgency sentence; e.g., "Limited stock available — offer ends soon!")
           - ctas: array of 2-3 non-empty strings "cta_library": [ "Download Brochure", "Compare Variants", "Compare with Other Brands", "Book a Test Drive", "Book a Showroom Visit", "Locate a Showroom", "Request a Call Back", "Confirm Booking", "Exchange Old Car"], the "Request a Call Back" will be always there but you need to translate it according to the first language. But remember that it should be under 50 characters.
           - channels: array of 1-2 strings from this exact list only: 
             ["rcs", "email", "web_chat", "web_chat_voice", "fb_chat", "insta_chat", "twitter_chat", 
              "voice_phone", "whatsapp_chat", "whatsapp_voice_note", "whatsapp_voice_call", 
              "zoom_bot", "ms_teams"]
           - init_conversation: It will contain a initial message that can be send to the user.
           - email_subject- The subject that we can have to send a email. It will contain a subject to send the email where we will use the idea.
           - email_body- The body or the main message of the email.
        4. PRESERVATION: If a field exists in the user's existing data, preserve it exactly.
        5. NO NULLS/EMPTY: Never output null, empty string, or empty list for any field.
        6. NO EXTRA KEYS: Do not add languages, budgets, metrics, dates, audiences, or any keys other than the allowed list.
        7. TONE: Persuasive, urgent, conversion-focused for pre-sales.
        8. LENGTH: Keep campaign_description concise (roughly 30-70 words).
        9. OUTPUT FORMAT: Strict JSON only.

        If you understand, respond with the single JSON object that follows these rules.
        """
        
        user_prompt = f"""
        Existing Campaign Data (preserve as-is):
        {json.dumps(existing_data, indent=4)}

        Context:
        - campaign_type: {existing_data.get('campaign_type', '')}
        - campaign_objective: {existing_data.get('campaign_objective', '')}

        Required behavior:
        - Generate only the missing fields from the allowed list above.
        - Ensure 'ctas' is a list of 2-3 short CTAs focused on purchase conversion.
        - One urgency hook is required to create purchase urgency.
        - Ensure 'channels' contains 1-2 allowed channel values relevant for pre-sales outreach.
        - Focus on attracting new customers and driving vehicle purchases.
        - Do NOT output anything beyond the allowed keys.

        Return the single JSON object now.
        """

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def _get_postsale_prompt(self, existing_data: dict, post_sale_fields):

        language = existing_data.get("languages",["English"])[0]

        system_prompt = f"""
        You are an intelligent Campaign Generator Autobot for automotive dealership post-sales campaigns.

        Important rules (follow exactly):
        1. OUTPUT: Return a single valid JSON object and nothing else (no prose, no code fences).
        2. KEYS: The JSON object MAY contain only the following keys (and no others):
           {post_sale_fields}
        3. TYPES & CONSTRAINTS:
           - The language you'll be using to generate description, campaign_name, cta_buttons, campaign_tagline, urgency_hook, and cta_buttons must be colloquial {language}, if the word is difficult in {language} then you can use english word also but the script must be of {language} only. 
           - Keys for the json response will remain in english only, the values, titles and descriptions should be in colloquial {language}
           - campaign_name: non-empty string. should be generated based on the campaign_type, and campaign_objective.
           - campaign_objective: non-empty string (preserve existing value if present).
           - campaign_offer: Check whether the dealer wants to give any offer : {json.dumps(existing_data.get("campaign_offer", "No Offer"))} . If not mentioned any offer then do not return offer. If offer is mentioned then make it sound attractive offer in {language} only.
           - campaign_description: non-empty string (2-4 concise sentences).
           - urgency_hook: single short string (ONE urgency sentence)
           - ctas: array of 2-3 non-empty strings (example: ["Schedule Service", "Renew Warranty"])
           - channels: array of 1-2 strings from allowed list only
           - idea: idea will be a overall campaign suggestion, It will be a 2-3 lines of an explaination of the overall campaign in a attractive way, It will be different than the campaign_description and will give a shorter attractive idea to the dealer.
           - campaign_tagline: This will be tagline based on the idea.
           - campaign_tone: You have generated the idea and now this is the tone of the idea that you generated like formal, professional or maybe other
        4. PRESERVATION: If a field exists in the user's existing data, preserve it exactly.
        5. NO NULLS/EMPTY: Never output null, empty string, or empty list.
        6. NO EXTRA KEYS: Do not add any keys other than the allowed list.
        7. TONE: Appreciative, service-oriented, retention-focused.

        If you understand, respond with the single JSON object that follows these rules.
        """

        user_prompt = f"""
        Existing Campaign Data (preserve as-is):
        {json.dumps(existing_data, indent=4)}

        Context:
        - campaign_type: {existing_data.get('campaign_type', '')}
        - campaign_objective: {existing_data.get('campaign_objective', '')}
        - languages: {existing_data.get('languages', ["English"])}

        Generate only the missing fields from the allowed list above.
        Return the single JSON object now.
        """

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    

    def campaign_creation(self, existing_data: dict, fields):
        """Selects appropriate prompt based on campaign type."""
        self.logger.info(f"Existing Data: {existing_data}")

        campaign_type_lower = self.campaign_type.lower()
        
        if campaign_type_lower in self.PRE_SALE_KEYWORDS:
            return self._get_presale_prompt(existing_data, fields)
        elif campaign_type_lower in self.POST_SALE_KEYWORDS:
            return self._get_postsale_prompt(existing_data, fields)
        else:
            raise ValueError(f"Unsupported campaign type: {self.campaign_type}")

    def validate_campaign_json(self, parsed_campaign: dict, allowed_fields: list) -> dict:
        """
        Takes an already parsed JSON dictionary and returns a new dict 
        containing only the allowed fields, but preserves the original values.
        """
        if not isinstance(parsed_campaign, dict):
            raise TypeError("Expected parsed_campaign to be a dictionary")

        # Keep only allowed keys but don't remove existing good data
        cleaned_data = {}
        for field in allowed_fields:
            if field in parsed_campaign:
                cleaned_data[field] = parsed_campaign[field]

        return cleaned_data

    def _regenerate_missing_fields(self, existing_data: dict, missing_fields: list, all_fields: list, campaign_type: str) -> str:
        """Regenerate specific missing fields using LLM."""
        language = existing_data.get("languages", ["English"])[0]

        system_prompt = f"""
        You are a specialized Campaign Field Generator for automotive dealership campaigns.

        CRITICAL: Generate ONLY the missing fields listed below. Do NOT modify existing fields.

        MISSING FIELDS: {missing_fields}
        Campaign type: {campaign_type}
        Language: {language}
        Campaign objective: {existing_data.get('campaign_objective', '')}

        RULES:
        1. Output MUST be valid JSON containing ONLY the missing fields as keys
        2. Do NOT include any existing fields in your response
        3. All content must be in {language} language
        4. Follow the original field constraints and formats
        5. Your response should be ONLY JSON, no other text

        Return JSON with ONLY the missing fields.
        """

        user_prompt = f"""
        Existing campaign data (DO NOT MODIFY THESE FIELDS):
        {json.dumps({k: v for k, v in existing_data.items() if k in all_fields}, indent=4)}

        Generate ONLY these missing fields: {missing_fields}

        Remember: Return ONLY the missing fields as JSON keys.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return ai_service_app.get_llm_response(
            messages=messages,
            model_identifier=self.model_identifier
        )

    def _get_missing_fields(self, data, fields):
        """Get list of missing or empty fields."""
        return [
            key for key in fields 
            if key != "dealership_id" and (key not in data or not data.get(key))
        ]

    def _attempt_field_generation(self, final_data, missing_fields, all_fields, campaign_type, attempt):
        """Single attempt to generate missing fields."""
        try:
            if attempt == 1:
                ai_response = ai_service_app.get_llm_response(
                    messages=self.campaign_creation(final_data, all_fields),
                    model_identifier=self.model_identifier
                )
            else:
                ai_response = self._regenerate_missing_fields(
                    final_data, missing_fields, all_fields, campaign_type
                )
            
            parsed_campaign = self.extract_json_from_llm_response(ai_response)
            if parsed_campaign:
                parsed_campaign = self.validate_campaign_json(parsed_campaign, all_fields)
                parsed_campaign["campaign_type"] = campaign_type
                final_data.update(parsed_campaign)
                
        except Exception as e:
            self.logger.warning(f"Field generation attempt {attempt} failed: {str(e)}")
        
        return final_data

    def _apply_fallbacks(self, final_data, missing_fields):
        """Apply fallbacks ONLY for ctas and channels, skip others."""
        for field in missing_fields:
            if field == "ctas":
                final_data[field] = ["Request a Call Back"]
                self.logger.info(f"Applied fallback for: {field}")
            elif field == "channels":
                final_data[field] = ["email", "voice_phone"]
                self.logger.info(f"Applied fallback for: {field}")
            else:
                # For other fields, leave them as None - they must be generated
                self.logger.warning(f"Field '{field}' could not be generated after multiple attempts")
                if field not in final_data:
                    final_data[field] = None
        return final_data

    def _clean_and_validate_final_data(self, final_data, fields):
        """Clean and validate the final campaign data."""
        # Remove offer if not applicable
        if self._is_no_offer(final_data.get("campaign_offer")):
            final_data.pop("campaign_offer", None)
        
        # Validate channels
        if final_data.get("channels"):
            final_data["channels"] = [
                channel for channel in final_data["channels"] 
                if channel in self.VALID_CHANNELS
            ]
            # Ensure at least one valid channel
            if not final_data["channels"]:
                final_data["channels"] = ["email"]
        
        # Preserve languages
        if self.languages:
            final_data["languages"] = self.languages
        
        # Remove internal fields from output
        final_data.pop("dealership_id", None)
        
        return final_data
    
    def _merge_json(self,json1, json2):
        merged = json2.copy()       
        merged.update(json1)        
        return merged

    def _generate_missing_fields(self, final_data, fields, campaign_type):
        """Generate missing fields with retry logic."""
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            missing_fields = self._get_missing_fields(final_data, fields)
            
            if not missing_fields:
                self.logger.info("All fields generated successfully!")
                break
                
            self.logger.info(f"Attempt {attempt}: Generating {len(missing_fields)} missing fields")
            final_data = self._attempt_field_generation(final_data, missing_fields, fields, campaign_type, attempt)
        
        # Apply fallbacks for any remaining missing fields
        remaining_missing = self._get_missing_fields(final_data, fields)
        if remaining_missing:
            self.logger.warning(f"Applying fallbacks for remaining fields: {remaining_missing}")
            final_data = self._apply_fallbacks(final_data, remaining_missing)
        
        return final_data

    def run(self):
        """Executes generation and handles merging + optional posting."""
        try:
            fields, normalized_type = self._get_campaign_type_details()
            final_data = self.source.copy()
            
            final_data = self._generate_missing_fields(final_data, fields, normalized_type)
            final_data = self._clean_and_validate_final_data(final_data, fields)
            final_data = self._merge_json(self.source,final_data)
            
            self.logger.info(f"Campaign generation completed successfully")
            self.logger.info(f"Final result: {json.dumps(final_data, ensure_ascii=False, indent=2)}")
            
            return final_data
            
        except Exception as e:
            self.logger.error(f"Campaign generation failed: {str(e)}")
            raise


AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")


@gryd.is_a_task('generate_campaign_idea', logger_param='logger', job_param='job')
def generate_campaign_idea(campaign_type, campaign_objective, dealership_idea=None, dealership_id=None, logger=None, job=None):
    logger = logger or gryd.hp.get_logger(__name__)
    logger.info(f"Creating campaign idea for dealership: {dealership_id}")
    
    try:
        dealership_idea = dealership_idea or {}
        dealership_idea.update({
            'campaign_type': campaign_type,
            'dealership_id': dealership_id,
            'campaign_objective': campaign_objective
        })
        
        agent = CampaignIdeaCreatorAgent(source=dealership_idea, logger=logger)
        result = agent.run()
        
        # Post to database if dealership_id provided
        if dealership_id:
            dim = gryd.base_model.Model('dealership', AUTOCRM_APP_ENTERPRISE_ID)
            result.update({
                "campaign_type": campaign_type,
                "dealership_id": dealership_id,
                "campaign_objective": campaign_objective
            })
            dim.post(result)
        
        return result
        
    except Exception as e:
        logger.error(f"Campaign idea generation failed: {str(e)}")
        raise