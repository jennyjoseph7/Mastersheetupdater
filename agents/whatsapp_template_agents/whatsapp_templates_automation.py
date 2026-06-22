import json
import os, sys
import random, re, requests
from pprint import pprint
from agents.base_agent import BaseAgent, gryd


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from autocrm_db_helper.PGConnector import AutoCRMPGConnector
pg = AutoCRMPGConnector(enterprise_id="autocrm")

from agents.data_attributes_retriever_agent import data_attribute_retriever
from agents.whatsapp_template_creator_agent import WhatsappTemplateCreatorAgent
AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")
data ={
"attribute_name" : [],
}
campaign_objectives = ["Test Drive Booking"
]
cta_buttons = ["Book Test Drive", "Request a Call Back"]
campagn_type = "pre-sales"
communication_credential_id = "airtel-917795030574"

from pprint import pprint
logger = gryd.hp.get_logger(__name__)

default_data = {
            "waba_id": "113485138500957",
            "customer_id": "SOCIOGRAPH_uu76NiJRbNmsq5zPgu5V",
            "sub_account_id": "965a92cd-ac2e-4674-87ab-99fc174e071f",
            "auth_headers": {
                "Content-Type": "application/json",
                "Authorization": "Basic ZGF2ZV9haTpJSjJQVjhebDVjODU="
            }       
        }


def send_template_for_approval(template_data: dict,languages: list) -> str | None:
    """
    Extract variables directly from message body {{var_name}}
    Replace them in order to {{1}}, {{2}}, ...
    Add the original variable names in templateContent.sample.variables
    Submit template for approval and return templateId.
    """
    LANG_TO_CODE = {
        "English": "en",
        "Hindi": "hi",
        "Assamese": "as",
        "Bengali": "bn",
        "Gujarati": "gu",
        "Kannada": "kn",
        "Kashmiri": "ks",
        "Malayalam": "ml",
        "Marathi": "mr",
        "Nepali": "ne",
        "Odia": "or",
        "Punjabi": "pa",
        "Sanskrit": "sa",
        "Sindhi": "sd",
        "Tamil": "ta",
        "Telugu": "te",
        "Urdu": "ur",
        "Konkani": "kok",
        "Manipuri": "mni",
        "Maithili": "mai",
        "Santali": "sat",
        "Dogri": "doi",
        "Bodo": "bdo"
    }
    lang = languages[0].strip().lower()
    lang = LANG_TO_CODE.get(lang,"en")
    url = "https://iqwhatsapp.airtel.in/gateway/airtel-xchange/whatsapp-content-manager/v1/template"

    template_name = template_data.get("template_name")
    template_message = template_data.get("template_message")
    buttons = template_data.get("buttons", [])
    standard_buttons = []
    for btn in template_data.get("buttons", []):
        new_btn = {
            "type": btn.get("type", "QUICK_REPLY"),
            "buttonText": btn.get("buttonText") or btn.get("text")
        }
        standard_buttons.append(new_btn)

    buttons = standard_buttons

    if not template_name or not template_message:
        raise ValueError("template_name and template_message must exist in template_data")

    # Extract variables from message body in order of appearance
    # Matches: {{vehicle_model}}, {{ service_due_date }} etc.
    variable_pattern = r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}"
    extracted_variables = re.findall(variable_pattern, template_message)

    # Remove duplicates but preserve order
    seen = set()
    ordered_variables = [v for v in extracted_variables if not (v in seen or seen.add(v))]

    # Replace each variable with numeric placeholder
    processed_message = template_message
    for idx, var_name in enumerate(ordered_variables, start=1):
        pattern = r"\{\{\s*" + re.escape(var_name) + r"\s*\}\}"
        processed_message = re.sub(pattern, "{{" + str(idx) + "}}", processed_message)

    # Build Airtel payload
    payload = {
        "templateName": template_name,
        "wabaId": default_data["waba_id"],
        "customerId": default_data["customer_id"],
        "category": "MARKETING",
        "subAccountId": default_data["sub_account_id"],
        "templateContent": {
            "language": lang,
            "body": processed_message,
            "buttons": buttons,
            "sample": {
                "variables": ordered_variables  
            }
        }
    }

    headers = default_data["auth_headers"]


    pprint(payload)

    payload = {
        "templateName": template_name,
        "wabaId": default_data["waba_id"],
        "customerId": default_data["customer_id"],
        "category": "MARKETING",
        "subAccountId": default_data["sub_account_id"],
        "templateContent": {
            "language": lang,
            "body": processed_message,
            "buttons": buttons,
            "sample": {
                "variables": ordered_variables  
            }
        }
    }

    headers = default_data["auth_headers"]


    pprint(payload)

    if not ordered_variables:
        payload["templateContent"].pop("sample", None)


    #Submit request
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if not response.ok:
            print(f"API Error: {response.status_code} - {response.text}")
            return None

        response_data = response.json()
        pprint(response_data)
        template_id = response_data.get("template", {}).get("templateId")

        if not template_id:
            print("Template ID not found in API response:", response_data)
            return None

        return_data =  {"template_id":template_id,"template_variables":ordered_variables}
        return return_data
    
    except Exception as e:
        print("Unexpected error:", e)
        return None

def post_template_into_model(template_data,template_id, template_variables, campaign_type, campaign_objective, communication_credential_id):
    if not template_id:
        return
    template_data["template_id"] = template_id
    template_data["campaign_type"] = campaign_type
    template_data["campaign_objective"] = [campaign_objective]
    template_data["communication_credentials_id"] = communication_credential_id
    template_data["template_type"] = "text"
    disposition = None
    disposition_detail = None
    if isinstance(template_variables, list):
        for idx, item in enumerate(template_variables):
            if isinstance(item, dict):
                disposition = item.get("disposition")
                disposition_detail = item.get("disposition_detail")
                if disposition and disposition_detail:
                    del template_variables[idx]
                    break
                break
    if disposition and disposition_detail:
        template_data["disposition_tags"] = [disposition, disposition_detail]
    template_data["template_variables"] = template_variables
    try:
        dim = gryd.base_model.Model('template', AUTOCRM_APP_ENTERPRISE_ID)
        logger.info(f"Posting result to model 'templates' under enterprise '{AUTOCRM_APP_ENTERPRISE_ID}'")
        dim.post(template_data)
        logger.info("Post completed successfully!")
    except Exception as db_error:
        logger.error(f"Failed posting to Gryd model: {db_error}")



for campaign_obj in campaign_objectives:
    user_data = {
        "campaign_objective" : campaign_obj,
        "campagn_type" : campagn_type,
        "data" : data ,
        "cta_buttons" : cta_buttons
    }
    agent = WhatsappTemplateCreatorAgent(source= user_data, logger = logger)
    result = agent.run()

    api_response = send_template_for_approval(template_data=result, languages=["English"])
    template_id = api_response.get("template_id")
    post_template_into_model(template_data=result,template_id=template_id,template_variables=data.get("attribute_name"),campaign_type=campagn_type,campaign_objective=campaign_obj, communication_credential_id= communication_credential_id)


print("done")













