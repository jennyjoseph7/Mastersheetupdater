import json
import os
import re
from datetime import datetime
from ai_service import ai_service_app

try:
    from .base_agent import BaseAgent, gryd
except ImportError:
    from base_agent import BaseAgent, gryd 

from autocrm_db_helper.PGConnector import AutoCRMPGConnector
pg = AutoCRMPGConnector(enterprise_id="autocrm")
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
        self.campaign_objective = self._validate_campaign_objective(source.get("campaign_objective"))
        self.input_data = source.get("data",{})
        self.dealership_id = source.get("dealership_id", "")
        self.languages = self._validate_languages(source.get("languages", ["english"]))
        self.cta_buttons = source.get("cta_buttons", ["Get a Call Back"])
        self.ai_generation = source.get("ai_generation",True)
        self.logger = kwargs.get("logger") or gryd.hp.get_logger(__name__)

        self.model_identifier = "gcp-gemini-2.5-flash-lite"

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

    def _build_prompt(self):
        """
        Constructs the AI prompt based on the pre-defined schema.
        Follows the same pattern as CampaignIdeaCreatorAgent.
        """
        language = self.languages[0]

        system_prompt = f"""
        You are an intelligent WhatsApp Template Generator Autobot for automotive dealership campaigns.

        Important rules (follow exactly):
        1. OUTPUT: Return a single valid JSON object and nothing else (no prose, no code fences).
        2. KEYS: The JSON object MUST contain exactly these keys (no others):
           - template_name: string, It should be relevant to the type and objective.
           - template_text: string , This is the main message, use the attributes of data to create the template and the message will be as the objective and type of the campaign 
           - attributes_used: array of strings
           - suggested_ctas: array of strings

        3. TYPES & CONSTRAINTS:
           - The language you'll be using to generate template_text must be colloquial {language}
           - template_name: descriptive name related to campaign (use underscores, no spaces)
           - template_text: personalized message using 2-4 attributes with {{placeholders}}, under 400 characters
           - attributes_used: array of attribute names actually used in template_text
           - suggested_ctas: array of 2-3 CTA buttons

        4. CTA HANDLING:
           - If existing CTA buttons are provided: {self.cta_buttons}
           - If no CTA buttons provided, generate 2-3 relevant CTAs including "Request a Call Back"
           - CTA library: ["Download Brochure", "Compare Variants", "Book a Test Drive", "Book a Showroom Visit", "Locate a Showroom", "Request a Call Back", "Confirm Booking", "Exchange Old Car"]

        5. CONTEXT:
           - Campaign Objective: {self.campaign_objective}
           - Campaign Type: {self.campaign_type}
           - Available Data: 

        6. PRESERVATION: Use the existing CTA buttons if provided, otherwise generate relevant ones.
        7. NO NULLS/EMPTY: Never output null, empty string, or empty list for any field.
        8. FORMAT: Keep template_text conversational and WhatsApp-friendly.

        If you understand, respond with the single JSON object that follows these rules.
        """

        user_prompt = f"""
        Generate a WhatsApp message template using the provided campaign context and data.

        Campaign Objective: {self.campaign_objective}
        Campaign Type: {self.campaign_type}
        Available Customer Data: {self.input_data}
        Preferred CTA Buttons: {self.cta_buttons}

        Create an engaging, personalized template that uses relevant customer attributes.
        Return ONLY the JSON object with the required fields.
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
    
    def pick_from_model(self):
        records = list(pg.list(
        table_name= "dealership_idea",
        where= {
            "campaign_objective" : self.campaign_objective,
            "campaign_type": self.campaign_type
        
        }
        ))

        if not records:
            return []

        # Randomly pick 5 without duplicates
        sample_size = min(5, len(records))
        picked = random.sample(records, sample_size)

        return picked
    

    def run(self):
        """Executes template generation and returns final result."""
        if self.ai_generation is True:
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

                self.logger.info("Template generation completed successfully")
                self.logger.info(f"Generated template: {final_output['template_name']}")

                return final_output

            except Exception as e:
                self.logger.error(f"Template generation failed: {str(e)}")
                raise
        else:
            final_output = self.pick_from_model()
            return final_output


AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")

@gryd.is_a_task('generate_whatsapp_template', logger_param='logger', job_param='job')
def generate_whatsapp_template(*args, logger=None, job=None, **kwargs):
    logger = logger or gryd.hp.get_logger(__name__)
    logger.info("Creating WhatsApp template using CRM data...")

    try:
        user_data = kwargs or {}

        if not isinstance(user_data, dict):
            logger.error("Invalid user_data type. Expected dict.")
            raise ValueError("user_data must be a dictionary")

        logger.info(f"Incoming template data: {user_data}")

        agent = WhatsappTemplateCreatorAgent(source=user_data, logger=logger)
        logger.info("Running template generation agent...")

        result = agent.run()
        logger.info("Template generated successfully")

        try:
            dim = gryd.base_model.Model('templates', AUTOCRM_APP_ENTERPRISE_ID)
            logger.info(f"Posting result to model 'templates' under enterprise '{AUTOCRM_APP_ENTERPRISE_ID}'")
            dim.post(result)
            logger.info("Post completed successfully!")
        except Exception as db_error:
            logger.error(f"Failed posting to Gryd model: {db_error}")

        return result

    except Exception as e:
        logger.error(f"WhatsApp template generation failed: {str(e)}")
        raise


# @gryd.is_a_task('generate_whatsapp_template', logger_param='logger', job_param='job')
# def generate_whatsapp_template(*args,user_data=None, logger=None, job=None,**kwargs):
#     """
#     Gryd task wrapper for template generation.
#     Matches the structure of CampaignIdeaCreatorAgent.
#     """
#     logger = logger or gryd.hp.get_logger(__name__)
#     logger.info("Creating WhatsApp template using CRM data...")

#     try:
#         user_data = user_data or {}
        
#         # Validate input structure
#         if not isinstance(user_data, dict):
#             logger.error("Invalid user_data type. Expected dict.")
#             raise ValueError("user_data must be a dictionary")

#         logger.info(f"Incoming template data: {user_data}")
        
#         # Instantiate TemplateCreatorAgent with proper structure
#         agent = WhatsappTemplateCreatorAgent(source=user_data, logger=logger)
#         logger.info("Running template generation agent...")

#         result = agent.run()
#         logger.info("Template generated successfully")

#         # Post to database
#         #try:
#             #dim = gryd.base_model.Model('templates', AUTOCRM_APP_ENTERPRISE_ID)
#             #logger.info(f"Posting result to model 'templates' under enterprise '{AUTOCRM_APP_ENTERPRISE_ID}'")
#             #dim.post(result)
#             #logger.info("Post completed successfully!")
#         #except Exception as db_error:
#             #logger.error(f"Failed posting to Gryd model: {db_error}")

#         return result

#     except Exception as e:
#         logger.error(f"WhatsApp template generation failed: {str(e)}")
#         raise

