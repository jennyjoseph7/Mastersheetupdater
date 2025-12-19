import json
import os, sys
import re
from ai_service import ai_service_app

try:
    from .base_agent import BaseAgent, gryd
except ImportError:
    from base_agent import BaseAgent, gryd 

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from autocrm_db_helper.PGConnector import AutoCRMPGConnector
pg = AutoCRMPGConnector(enterprise_id="autocrm")

from agents.data_attributes_retriever_agent import data_attribute_retriever

import random

class WhatsappTemplateCreatorAgent(BaseAgent):
    """
    This agent creates templates for whatsapp business. The input will be like : {
      campaign_type: "pre-sale"
      campaign_objective: "Exchange / Loyalty Bonus Offer"
      dealership_idea: {
        languages: ["English"]
        campaign_offer: "₹10,000 exchange bonus" }

    }  

    and output will be like :
    {
    "template_name": "Autobot_PreSale_Upgrade_Offer_v1",
    "template_message": "Hello {{person_name}}! Thinking about upgrading your {{current_car_model}} ({{current_car_age}} old)? We have an exclusive offer on the {{interested_model}} valid until {{offer_validity}}. Visit us at {{nearest_dealership}} to explore details: {{offer_details}}!",
    "buttons": [
        {
            "type": "QUICK_REPLY",
            "text": "Exchange Old Car"
        },
        {
            "type": "QUICK_REPLY",
            "text": "Book a Test Drive"
        },
        {
            "type": "QUICK_REPLY",
            "text": "Request a Call Back"
        }
    ],
    "template_button_payloads": [
        "autobot_presale_upgrade_offer_v1-exchange_old_car",
        "autobot_presale_upgrade_offer_v1-book_a_test_drive",
        "autobot_presale_upgrade_offer_v1-request_a_call_back"
    ]
}

    """

    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)

        print(f"Kwargs are {kwargs}")
        
        # Validate source
        if not source or not isinstance(source, dict):
            raise ValueError("source must be a non-empty dictionary")
        
        self.source = source
        print(source)
        self.campaign_type = source.get("campaign_type","")
        self.campaign_id = source.get("campaign_id","")
        self.campaign_objective = self._validate_campaign_objective(source.get("campaign_objective"))
        self.input_data = source.get("data",{})
        self.dealership_id = source.get("dealership_id", "")
        self.languages = self._validate_languages(source.get("languages", ["english"]))
        self.cta_buttons = source.get("cta_buttons", [])
        self.ai_generation = source.get("ai_generation",True)
        self.logger = kwargs.get("logger") or gryd.hp.get_logger(__name__)

        self.model_identifier =   'openai-gpt-4.1-mini' #"gcp-gemini-2.5-flash-lite" #"groq-qwen-3-32B" 'groq-qwen-32b' 'groq-deepseek-r1-distill-llama-70b'

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
            return ["english"]
        
    def _extract_attributes(self,json_path):
        with open(json_path, "r") as f:
            data = json.load(f)

        names = [data.get("name")]

        for attr in data.get("attributes", []):
            if "name" in attr:
                names.append(attr["name"])

        return names

    def _build_prompt(self):
        """
        Constructs the AI prompt based on the pre-defined schema.
        Follows the same pattern as CampaignIdeaCreatorAgent.
        """
        language = self.languages[0]

        airtel_rules = """airtel_whatsapp_template_rules:

        general:
          - Template_name must be lowercase without spaces or special characters (only a–z, 0–9, underscore).
          - No grammar or spelling mistakes.

        content_format:
          - Placeholders must use double curly braces (e.g., {{name}}).
          - No placeholders allowed in header if header type is plain text.
          - Placeholders must not break sentence meaning.
          - Emojis allowed only in body (not in header).
          - No URLs allowed inside body text.
          - No phone numbers allowed inside body text (use CTA call button instead).

        compliance_policies:
          - No sensitive personal data (e.g., Aadhaar, PAN, bank info).
          - No threatening, abusive, or fear-triggering content.
          - No medical, gambling, political content.

        structure:
          body:
            - Max length: 1024 characters.
            - Recommended max placeholders: 4–5 only.
          header:
            - Only 1 header allowed (text OR media).
            - Media header requires alt text.
          footer:
            - Plain text only (no placeholders, no emojis).
          buttons:
            - Allowed: 2 CTA buttons OR 3 quick reply buttons (not both).
            - Max length for button text: 20 characters.
            - Button text cannot contain placeholders.
            - Quick reply button text must be concise (e.g., “Check Offers”, "Book a Service", "Book a Testdrive", "Book Showroom Visit", “Request a Callback”).
            - Buttons must have "Request a Callback" in all templates, This one is a mendatory requirement

        payload_key_rules:
          - Payload keys for buttons must be lowercase and unique.
          - No spaces, only hyphens/underscore allowed.

        rejection_common_reasons:
          - Placeholder formatting wrong.
          - Category mismatch (e.g., promo under utility).
          - Buttons contain placeholders.
          - Link inside body instead of CTA URL button.
          - Brand mismatch with account.
          - Too many placeholders."""

        system_prompt = f"""
        You are an intelligent WhatsApp Template Generator Autobot for automotive dealership markeiting campaigns, adhering strictly to Airtel's messaging compliance standards (professional tone, clear value proposition) generate attractive and interactive whatsapp templates for running campaigns.

        Important rules (follow exactly):
        1. OUTPUT: Return a single valid JSON object and nothing else (no prose, no code fences, no extra characters).
        2. KEYS: The JSON object MUST contain exactly these keys (no others):
            - template_name: string,
            - template_text: string
            - suggested_ctas: array of strings
            - lead_tags: array of strings (must contain 2-3 relevant tags for the template's purpose) for example : "service-due","regular-customer", "warranty-active", "early-adopter","launch-interested","premium-seeker", "test-drive-interested", "high-intent", "new-buyer"

        3. TYPES & CONSTRAINTS (Airtel/Meta Compliance):
            - Rules of airtel are listed here, follow them so that your templates are not get rejected : {airtel_rules}
            - The language you'll be using to generate template_text must be colloquial {language}
            - template_name: descriptive name related to campaign (use underscores, NO SPACES, must be lowercase).  will start with autobot word, an unique template name each time.
            - template_text: personalized message using ALL attributes with the EXACT format: {{attribute_name}}, You need to use all attributes and nothing more than given, under 400 characters (strict limit for compliance). The message must align with the Campaign Objective and campaign Type also should Disposition and disposition details if exists.
            - suggested_ctas: array of 2-3 CTA buttons.
            - lead_tags: array of 2-3 short, descriptive words (e.g., ["service-due", "new-model"]).

        4. ATTRIBUTE HANDLING (CRITICAL):
            - You MUST use ALL key attributes provided : '{self.input_data}' in the 'Available Customer Data' except 'disposition' and 'disposition_details'. Don't add anything that is not present, but whatever is present, must include.
            - If 'disposition' is present in the data, **use its value solely to understand the customer's last interaction and tailor the message's tone and context (e.g., if the disposition is "Busy", the template should be apologetic or mention trying again later).**
            - **'disposition' and 'disposition_details' MUST NOT be included as placeholders in the template_message and attributes_used. Use these details for have a understanding of what to write. If disposition and disposition details exists in input it means it is a follow up message template. Just have understanding of what type of followup and write template message**
            - The placeholder format MUST be {{attribute_name}} exactly (e.g., {{person_name}}).

        5. CTA HANDLING:
            - If existing CTA buttons are provided: {self.cta_buttons}, use them as suggested_ctas.
            - If no CTA buttons provided, generate 2-3 relevant CTAs, always including "Request a Call Back".
            - CTA eg. library for reference: ["Download Brochure", "Compare Variants", "Book a Test Drive", "Book a Showroom Visit", "Locate a Showroom", "Request a Call Back", "Exchange Old Car"]
            - Rules : These CTAs must be there when it comes to these campaign objectives :
                    Free Service Due Reminder >> [Book a Service, Request a Call Back]
                    General Service Due Reminder >> [Book a Service, Request a Call Back]
                    Inactive Customer Reactivation >> [Book a Service, Request a Call Back]
                    Service Overdue  >> [ Book a Service, Request a Call Back]
                    Insurance Renewal Reminder >> [Renew Insurance, Request a Call Back]
                    Extended Warranty Offer >> [Buy Extended Warranty, Request a Call Back]
                    CCP >> [ Buy CCP, Request a Call Back ]
        6. CONTEXT:
            - Campaign Objective: {self.campaign_objective}
            - Campaign Type: {self.campaign_type}
            - Available Data Attributes: (Refer to user_prompt for the exact data dictionary structure)

        7. FORMAT & INTEGRITY: Never output null, empty string, or empty list for any field. Ensure the JSON is a single, valid object.

        If you understand, respond with the single JSON object that follows these rules.
        """

        user_prompt = f"""
        Generate a WhatsApp message template using the provided campaign context and customer data.

        Campaign Objective: {self.campaign_objective}
        Campaign Type: {self.campaign_type}
        Available Customer Data: {self.input_data} (Use ALL attributes except 'disposition_details'. Attributes must be formatted as {{attribute_name}} in the template_text.), All attributes must include in the template_message except 'disposition_details' and 'disposition'
        Preferred CTA Buttons: {self.cta_buttons}

        Create an engaging, personalized template under 400 characters that uses ALL necessary customer attributes and strictly follows the instructions above. Generate relevant 'lead_tags' (2-3 words) based on the template's purpose.

        Return ONLY the required JSON object.
        """
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    def _parse_ai_response(self, text):
        try:
            # Try to parse directly first
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                # Extract JSON from markdown code blocks
                json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    return json.loads(json_str)
                else:
                    # Try to find JSON object in the text
                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(0))
                    else:
                        raise ValueError("No JSON found in response")
            except Exception as e:
                print(f"Failed to parse AI response: {e}")
                print(f"Raw response: {text}")
                # Fallback to basic structure
                return {
                    "template_name": "Auto_Generated_Template",
                    "template_text": "Thank you for your interest. Please contact us for more information.",
                    "suggested_ctas": ["Request a Call Back"]
                }

    def _assemble_output(self, generated):
            buttons = []
            template_button_payloads=[]
            template_name = generated.get("template_name", "").lower().strip().replace(" ", "_").replace("-", "_")

            for cta in generated.get("suggested_ctas", []):
                buttons.append({"type": "QUICK_REPLY", "text": cta})
                slug = (
                cta.lower().strip().replace(" ", "_").replace("-", "_"))

                template_button_payloads.append(f"{template_name}-{slug}")


            return {
                "template_name": generated.get("template_name"),
                "template_message": generated.get("template_text"),
                "buttons": buttons,
                "template_button_payloads": template_button_payloads
            }
    
    
    def fix_template_message_braces(self,template_json: dict) -> dict:
        """
        Ensures that only the template_message field has {{placeholders}}
        by converting {var} → {{var}} without affecting existing {{var}}.
        """
        if "template_message" not in template_json:
            return template_json  # nothing to fix

        message = template_json["template_message"]

        # Regex: replace {var} only when it's not already {{var}}
        pattern = r'(?<!{){([^{}]+)}(?!})'
        fixed_message = re.sub(pattern, r'{{\1}}', message)

        template_json["template_message"] = fixed_message
        return template_json
    

    def run(self):
        """Executes template generation and returns final result."""

        try:
            self.logger.info("Starting WhatsApp template generation...")
            self.logger.info(f"Source data: {json.dumps(self.source, indent=2)}")
            # Generate template data
            generated_data = ai_service_app.get_llm_response(
                messages= self._build_prompt(),
                model_identifier=self.model_identifier
            )
            generated_data = self._parse_ai_response(generated_data)
            # Assemble final output
            final_output = self._assemble_output(generated_data)
            final_output["lead_tags"] = generated_data.get("lead_tags", [])
            final_output = self.fix_template_message_braces(final_output)
            self.logger.info("Template generation completed successfully")
            self.logger.info(f"Generated template: {final_output['template_name']}")
            return final_output
        except Exception as e:
            self.logger.error(f"Template generation failed: {str(e)}")
            raise



AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")

@gryd.is_a_task('generate_whatsapp_template', logger_param='logger', job_param='job')
def generate_whatsapp_template(*args, logger=None, job=None, **kwargs):
    logger = logger or gryd.hp.get_logger(__name__)
    logger.info("Creating WhatsApp template using CRM data...")

    

    try:
        user_data = kwargs or {}
        if "user_data" in kwargs and isinstance(kwargs["user_data"], dict):
            user_data = kwargs["user_data"]


        if not isinstance(user_data, dict):
            logger.error("Invalid user_data type. Expected dict.")
            raise ValueError("user_data must be a dictionary")

        logger.info(f"Incoming template data: {user_data}")

        agent = WhatsappTemplateCreatorAgent(source=user_data, logger=logger)
        logger.info("Running template generation agent...")

        result = agent.run()
        logger.info("Template generated successfully")

        return result

    except Exception as e:
        logger.error(f"WhatsApp template generation failed: {str(e)}")
        raise

