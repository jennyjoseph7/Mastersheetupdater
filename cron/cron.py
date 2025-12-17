import sys, os
import requests
import json
import re
                    
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from config import AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_CRON_SERVICE_NAME, AUTOCRM_AGENT_SERVICE_NAME, gryd, hp
from autocrm_db_helper import get_pg_connector
from typing import List, Union, Dict, Any
from autocrm_db_helper.PGConnector import AutoCRMPGConnector
pg = AutoCRMPGConnector(enterprise_id="autocrm")
AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")

gryd.SERVICE = AUTOCRM_CRON_SERVICE_NAME
gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(gryd.SERVICE)


def clear_otp_cache(logger=None, job=None):
    logger = logger or mlogger
    otp_cache_model = gryd.base_model.Model('otp_cache', AUTOCRM_APP_ENTERPRISE_ID)
    otp_cache_model.delete_many({"expiry": f",{hp.epoch() - 3600}"})

@gryd.is_a_task(logger_param='logger', job_param='job')
def create_campaign_ideas_for_dealerships(
        campaign_types:Union[List[str], None]=None, 
        campaign_objectives:Union[List[str], Dict[str, List[str]]]=None, 
        logger=None, job=None, *args, **kwargs
    ) -> Dict[str, int]:
    """
    This task creates campaign ideas for all dealerships.
    Args:
        campaign_types (list): The types of campaigns to create.
        campaign_objectives (list or dict): The objectives of the campaigns to create. If a dict, the key is the dealership id and the value is a list of objectives.
        depending on each campaign_type, for each dealership, we will be calling the create_campaign_idea task with the appropriate arguments.
        logger (Logger): The logger to use.
        job (Job): The job to use.
        return (dict): The number of campaign ideas created.
        *args: The arguments to pass to the task.
        **kwargs: The keyword arguments to pass to the task.
    """
    logger = logger or mlogger
    pre_sales_campaign_model = gryd.base_model.Model('pre_sales_campaign', AUTOCRM_APP_ENTERPRISE_ID)
    post_sales_campaign_model = gryd.base_model.Model('post_sales_campaign', AUTOCRM_APP_ENTERPRISE_ID)
    campaign_objective_model = gryd.base_model.Model('campaign_objective', AUTOCRM_APP_ENTERPRISE_ID)
    default_campaign_objectives = {
        'post-sales': campaign_objective_model.list(campaign_type='post-sales', _as_option = True, _page_size=100),
        'pre-sales': campaign_objective_model.list(campaign_type='pre-sales', _as_option = True, _page_size=100)
    }
    campaign_types = hp.make_list(campaign_types or ['pre-sales', 'post-sales'])
    if isinstance(campaign_objectives, list):
        campaign_types = [campaign_types[0]]
        campaign_objectives = {campaign_types[0]: campaign_objectives}
    elif isinstance(campaign_objectives, dict):
        if any(k not in campaign_objectives for k in campaign_types):
            raise ValueError(f"All campaign_types {campaign_types} must be present in campaign_objectives dict. {campaign_objectives}")
    else:
        raise ValueError(f"campaign_objectives must be a list or dict. {campaign_objectives}")
    campaign_objectives = campaign_objectives or default_campaign_objectives
    dm = gryd.base_model.Model('dealership', AUTOCRM_APP_ENTERPRISE_ID)
    created_idea_count = 0
    for dealership in dm.yield_list():
        logger.info(f"Creating campaign ideas for dealership: {dealership['dealership_id']}")
        for campaign_type in campaign_types:
            logger.info(f"Creating campaign ideas for dealership: {dealership['dealership_id']} with campaign_type: {campaign_type}")
            for campaign_objective in campaign_objectives[campaign_type]:
                logger.info(f"Creating campaign idea for dealership: {dealership['dealership_id']} with campaign_type: {campaign_type} and campaign_objective: {campaign_objective}")
                languages = dealership.get('languages', ['English'])
                dealership_id = dealership['dealership_id']
                kwargs = {'dealership_id': dealership_id, 'languages': languages}
                dealership_idea = gryd.await_result(
                    'generate_campaign_idea',AUTOCRM_AGENT_SERVICE_NAME, args=[campaign_type, campaign_objective], kwargs=kwargs, gryd_logger=logger, job_param=job
                )
                if dealership_idea:
                    created_idea_count += 1
                created_idea_count += 1
    return {
        "created_idea_count": created_idea_count,
    }

@gryd.is_a_task('create_campaign_templates', logger_param='logger', job_param='job')
def create_campaign_templates(logger=None, job=None):
    """
    This task creates campaign templates for all communication providers.
    Args:
        logger (Logger): The logger to use.
        job (Job): The job to use.
    Returns:
        dict: The number of campaign templates created.
    """
    created_template_count = 0

    logger = logger or mlogger
    communication_credentials_model = gryd.base_model.Model('communication_credential', AUTOCRM_APP_ENTERPRISE_ID)
    dealership_model = gryd.base_model.Model('dealership', AUTOCRM_APP_ENTERPRISE_ID)
    # For all dealerships registered on whatsapp or whatsapp_chat, create campaign templates for them.
    communication_credentials = list(
    communication_credentials_model.yield_list(
        channel=["whatsapp_chat", "whatsapp"]
        )
    )

    logger.info(f"communication creds are : {communication_credentials}")

    # Now loop safely without depending on an active DB cursor
    for communication_credential in communication_credentials:
        dealership_id = communication_credential['dealership_id']
        logger.info(f"dealership id id : {dealership_id}")
        communication_credential_id = communication_credential['communication_credentials_id']
        dealer_name = communication_credential['dealer_name']
        communication_provider_id = communication_credential['communication_provider_id']
        provider_name = communication_credential['provider_name']
        channel = communication_credential['channel']
        data = {
            'waba_id': communication_credential.get('waba_id'),
            'customer_id': communication_credential.get('customer_id'),
            'sub_account_id': communication_credential.get('sub_account_id'),
            'auth_headers': communication_credential.get('auth_headers')  
        }
        default_data = {
            "waba_id": "113485138500957",
            "customer_id": "SOCIOGRAPH_uu76NiJRbNmsq5zPgu5V",
            "sub_account_id": "965a92cd-ac2e-4674-87ab-99fc174e071f",
            "auth_headers": {
                "Content-Type": "application/json",
                "Authorization": "Basic ZGF2ZV9haTpJSjJQVjhebDVjODU="
            }       
        }
               
        string_auth_fields = [
            data.get("waba_id"),
            data.get("customer_id"),
            data.get("sub_account_id")
        ]

        valid_strings = all(
            isinstance(v, (str, int)) and str(v).strip() != ""
            for v in string_auth_fields
        )

        # Validate auth header dict
        auth = data.get("auth_headers")
        valid_auth_header = (
            isinstance(auth, dict)
            and "Authorization" in auth
            and isinstance(auth["Authorization"], str)
            and auth["Authorization"].strip() != ""
        )

        # If ANY field is missing/invalid → fallback to default
        if not (valid_strings and valid_auth_header):
            data = default_data

        post_sales_campaign_model = gryd.base_model.Model('post_sales_campaign', AUTOCRM_APP_ENTERPRISE_ID)
        pre_sales_campaign_model = gryd.base_model.Model('pre_sales_campaign', AUTOCRM_APP_ENTERPRISE_ID)
        default_campaign_objectives = {
            'post-sales': post_sales_campaign_model._model_ref.attributes['campaign_objective_name'].options,
            'pre-sales': pre_sales_campaign_model._model_ref.attributes['campaign_objective_name'].options
        }
        logger.info(f"default_campaign_objectives are : {default_campaign_objectives}")

        logger.info(f"Creating campaign templates for dealer {dealer_name} for provider {provider_name} on channel {channel}")
        for campaign_type in ["pre-sales", "post-sales"]:
            campaign_objectives = default_campaign_objectives[campaign_type]
            for campaign_objective in campaign_objectives:
                logger.info(f"generating campaign template for dealer {dealer_name} for provider {provider_name} on channel {channel} for campaign type {campaign_type} and campaign objective {campaign_objective}")
                dealership = dealership_model.get(dealership_id)
                languages = dealership.get('languages') or ['English']
                default_attributes = {
                    "pre-sales": {
                        "campaign_type": campaign_type,
                        "campaign_objective": campaign_objective,
                        "dealership_id": dealership_id,
                        "languages": languages,
                    },
                    "post-sales": {
                        "campaign_type": campaign_type,
                        "campaign_objective": campaign_objective,
                        "dealership_id": dealership_id,
                        "languages": languages
                    }
                }
                template_required_attributes = {
                    "pre-sales": ["dealer_name", "showroom_full_name", "person_name", "vehicle_category"],
                    "post-sales": ["dealer_name", "workshop_full_name", "reg_number", "vehicle_model", "vehicle_category"]

                }
                audiance_required_attributes = {
                    "pre-sales":[],
                    "post-sales" : []
                }

                template_optional_attributes = {
                    "pre-sales": {
                        "sessions":['last_session_channel', 'last_session_status', "last_session_timestamp"], 
                        "car_preferences": ["brand_preference", "model_preference", "variant_preference", "color_preference"], 
                        "engine_preference":["engine_type_preference", "transmission_preference", "range_preference", "feature_preferences"],
                        "campaign_info":["campaign_offer","urgency_hook","campaign_tagline"]
                    },
                    "post-sales": {
                        "preferences" : ["vehicle_variant", "vehicle_color", "vehicle_type" ],
                        "campaign_info":[ "campaign_offer", "urgency_hook","campaign_tagline"],
                        "sessions": ["last_session_channel", "last_session_status", "last_session_timestamp"]
                    }

                }
                pre_sale_special_combinations = [["model_preference","color_preference" ],["model_preference", "variant_preference"],["last_session_channel", "last_session_status"]]
                post_sale_special_combinations = [["campaign_offer", "urgency_hook"],["last_session_channel", "last_session_status"],["dealer_name", "workshop_full_name", "reg_number", "vehicle_model", "vehicle_category","next_service_due"]]



                dispositions = ["reached", "engaged"]

                postsales_disposition_detail = {
                        "reached": [
                            "Message Deliverd but didn't seen",
                            "Message sent but not replied"
                        ],
                        "engaged": [
                            "Looking for a discount",
                            "Will decide tomorrow",
                            "Will decide within 1 to 3 days",
                            "Will decide within 4 to 7 days",
                            "Will decide within 8 to 14 days",
                            "Will decide within 15 to 30 days",
                            "Will decide within 31 to 60 days",
                            "Will decide within 61 to 90 days",
                            "Will decide after 90 days",
                            "Will call workshop themselves",
                            "Vehicle is not being run"
                        ]
                    }

                presale_disposition_detail = {
                        "reached": [
                            "Message Deliverd but didn't seen",
                            "Message sent but not replied"
                        ],
                        "engaged": [
                            "Looking for a discount",
                            "Will decide tomorrow",
                            "Will decide within 1 to 3 days",
                            "Will decide within 4 to 7 days",
                            "Will decide within 8 to 14 days",
                            "Will decide within 15 to 30 days",
                            "Will decide within 31 to 60 days",
                            "Will decide within 61 to 90 days",
                            "Will decide after 90 days",
                            "Will call dealership themselves"
                        ]
                    }

                

                def get_template_variable_list(campaign_type):
                    final_list = []

                    required = template_required_attributes[campaign_type]
                    optional = template_optional_attributes[campaign_type]
                    specials = (
                        pre_sale_special_combinations
                        if campaign_type == "pre-sales"
                        else post_sale_special_combinations
                    )
                    disposition_details = (
                        presale_disposition_detail
                        if campaign_type == "pre-sales"
                        else postsales_disposition_detail
                    )

                    # Base template (required only)
                    base_templates = [required.copy()]

                    # Type-1: required + one optional field

                    for opt_list in optional.values():
                        for field in opt_list:
                            base_templates.append(required + [field])

                    # Type-2: required + special combination

                    for special in specials:
                        base_templates.append(required + special)

                    # Add disposition variations

                    for tmpl in base_templates:
                        for disp in dispositions:
                            for detail in disposition_details[disp]:
                                t = tmpl.copy()
                                t.append({
                                    "disposition": disp,
                                    "disposition_detail": detail
                                })
                                final_list.append(t)

                    return final_list
                
                    
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
                        "wabaId": data["waba_id"],
                        "customerId": data["customer_id"],
                        "category": "MARKETING",
                        "subAccountId": data["sub_account_id"],
                        "templateContent": {
                            "language": lang,
                            "body": processed_message,
                            "buttons": buttons,
                            "sample": {
                                "variables": ordered_variables  
                            }
                        }
                    }
                
                    headers = data["auth_headers"]
                
                
                    print(payload)
                
                    #Submit request
                    try:
                        response = requests.post(url, headers=headers, data=json.dumps(payload))
                
                        if not response.ok:
                            print(f"API Error: {response.status_code} - {response.text}")
                            return None
                
                        response_data = response.json()
                        print(response_data)
                        template_id = response_data.get("template", {}).get("templateId")
                
                        if not template_id:
                            print("Template ID not found in API response:", response_data)
                            return None
                
                        return_data =  {"template_id":template_id,"template_variables":ordered_variables}
                        return return_data

                    except Exception as e:
                        print("Unexpected error:", e)
                        return None
                
                def post_template_into_model(template_data,template_id, template_variables):

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

                def get_approval_status_and_update_in_db(template_ids:List):
                    for template_id in template_ids:
                        total = len(template_ids)
                        logger.info(f"Starting template approval sync for {total} templates")
                        try:
                            for id in template_ids:
                            
                                url = "https://iqwhatsapp.airtel.in/gateway/airtel-xchange/whatsapp-content-manager/v1/template?customerId="+data["customer_id"]+"&"+"subAccountId="+data["sub_account_id"]+"&"+"wabaId="+data["waba_id"]+"&"+"templateId="+id

                                payload = {}
                                headers = data["auth_headers"]

                                logger.debug(f"GET → {url}")

                                response = requests.request("GET", url, headers=headers, data=payload)
                                response = response.json()
                                template_data = response.get("template")
                                logger.info(f"response is {response}")
                                status = template_data.get("registrationStatus").lower()

                                pg.update(table_name="template",id_attr="template_id", id=id,data={"status" : status})
                                logger.info(f"Updated Successfully for template id = {id}")


                        except Exception as e:
                           # Log and continue to next one
                           print(f"[FAILED] template {template_id}: {e}")
                           continue
                

                final_attribute_list = get_template_variable_list(campaign_type)
                template_ids = []

                for attr_list in final_attribute_list:
                    kwargs = {'campaign_type':campaign_type,'campaign_objective': campaign_objective, 'dealership_id': dealership_id, 'languages': languages, 'data':{'attribute_name':attr_list}}
                    campaign_template = gryd.await_result(
                        'generate_whatsapp_template',AUTOCRM_AGENT_SERVICE_NAME, kwargs=kwargs, gryd_logger=logger
                    )
                    #logic for airtel api 
                    api_response = send_template_for_approval(template_data= campaign_template, languages= languages)
                    template_id = api_response.get("template_id")
                    variables = api_response.get("template_variables")
                    template_ids.append(template_id)
                    post_template_into_model(template_data = campaign_template ,template_id= template_id, template_variables = variables)
                
                get_approval_status_and_update_in_db(template_ids=template_ids)

                if campaign_template:
                    created_template_count += 1
    return {
        "created_template_count": created_template_count,
    }

@gryd.is_a_task('update_template_status', logger_param='logger', job_param='job')
def update_template_status(template_ids:List,dealership_id:str,logger=None, job=None):
    """
    get_template_status worker gets the status of a whatsapp template and update the status in template model:
    input : template_ids : A list of template ids, 
            dealership_id : Id of the dealership, required for getting their comm creds 

    """
    logger = logger or mlogger
    if not template_ids or not isinstance(template_ids, list):
        logger.error("template_ids is missing or invalid. Must be a non-empty list.")
        return

    if not dealership_id:
        logger.error("dealership_id is None or empty.")
        return


    default_data = {
            "waba_id": "113485138500957",
            "customer_id": "SOCIOGRAPH_uu76NiJRbNmsq5zPgu5V",
            "sub_account_id": "965a92cd-ac2e-4674-87ab-99fc174e071f",
            "auth_headers": {
                "Content-Type": "application/json",
                "Authorization": "Basic ZGF2ZV9haTpJSjJQVjhebDVjODU="
            }       
        }
    records = list(pg.list(
    table_name= "communication_credential",
    where= {

        "dealership_id": dealership_id

    }
    ))
    data = records[0] if records else default_data

    string_auth_fields = [
            data.get("waba_id"),
            data.get("customer_id"),
            data.get("sub_account_id")
        ]

    valid_strings = all(
        isinstance(v, (str, int)) and str(v).strip() != ""
        for v in string_auth_fields
    )
    # Validate auth header dict
    auth = data.get("auth_headers")
    valid_auth_header = (
        isinstance(auth, dict)
        and "Authorization" in auth
        and isinstance(auth["Authorization"], str)
        and auth["Authorization"].strip() != ""
    )
    # If ANY field is missing/invalid → fallback to default
    if not (valid_strings and valid_auth_header):
        data = default_data

    total = len(template_ids)
    logger.info(f"Starting template approval sync for {total} templates")

    for template_id in template_ids:
        
        try:
            for id in template_ids:
            
                url = "https://iqwhatsapp.airtel.in/gateway/airtel-xchange/whatsapp-content-manager/v1/template?customerId="+data["customer_id"]+"&"+"subAccountId="+data["sub_account_id"]+"&"+"wabaId="+data["waba_id"]+"&"+"templateId="+id
                payload = {}
                headers = data["auth_headers"]
                logger.debug(f"GET → {url}")
                response = requests.request("GET", url, headers=headers, data=payload)
                response = response.json()
                template_data = response.get("template")
                logger.info(f"response is {response}")
                status = template_data.get("registrationStatus").lower()
                pg.update(table_name="template",id_attr="template_id", id=id,data={"status" : status})
                logger.info(f"Updated Successfully for template id = {id}")
        except Exception as e:
           # Log and continue to next one
           print(f"[FAILED] template {template_id}: {e}")
           continue