from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
import sys
import json
import importlib
import pkgutil
import flask as Flask
# sys.path.insert(0, dirname(dirname(abspath(__file__))))
from gryd_worker import gryd,gryd_routes
import helpers as hp
logger=hp.get_logger(__name__)
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autocrm_db_helper import get_pg_connector
from agents.get_whatsapp_template_agent import get_whatsapp_template
from campaign.campaign_manager import BaseCustomCampaignManager
from config import AUTOCRM_CAMPAIGN_SERVICE_NAME
gryd.SERVICE = AUTOCRM_CAMPAIGN_SERVICE_NAME
gryd.set_queue_manager()
QUEUE_MANAGER = gryd.get_queue_manager(AUTOCRM_CAMPAIGN_SERVICE_NAME)

logger.info(f"GRYD SERVICE---{gryd.SERVICE}")
def import_modules(module_name):
    logger.info(f"Initializing {module_name} module")
    module_ref = {
        module_info.name: importlib.import_module(f"{module_name}.{module_info.name}")
                        for module_info in pkgutil.iter_modules([module_name])
    }
    if not module_ref:return
    _ = {setattr(v, 'gryd', gryd) for v in module_ref.values()}
    return _

module_list=["campaign"]
imported_modules = dict(map(lambda module: (module, import_modules(module)), module_list))

logger.info(f"List of all task {json.dumps(gryd.LIST_OF_TASKS or {}, indent=4,default=str)}   {imported_modules}")

def WARM_UP():
    logger.info("WARM_UP CALLED")
    with get_pg_connector() as pg:
        pass    
    return

@gryd.is_a_task(function_name="send_text_template_for_approval")
def send_text_template_for_approval(data, *args, **kwargs):
    """
    Send a WhatsApp template to the Airtel API for approval.

    This function prepares and forwards the template payload to Airtel's 
    template approval API. On success, Airtel returns a template ID that 
    can later be used to check the template's approval status.

    Expected Input for text template (example):
    {
        "templateName": "SaleCarousel",
        "wabaId": "113485138500957",
        "customerId": "SOCIOGRAPH_uu76NiJRbNmsq5zPgu5V",
        "category": "MARKETING",
        "subAccountId": "965a92cd-ac2e-4674-87ab-99fc174e071f",
        "templateContent": {
            "language": "en",
            "body": "This is just for testing for autobot demo",
            "buttons": [
                {
                    "type": "QUICK_REPLY",
                    "buttonText": "Button1"
                },
                {
                    "type": "QUICK_REPLY",
                    "buttonText": "Button2"
                },
                {
                    "type": "CALL_TO_ACTION",
                    "buttonText": "Website",
                    "subType": "URL",
                    "url": "https://www.google.com"
                }
            ]
        }
    }

    Returns:
        dict: Response from Airtel containing the `template_id`.
              This ID can be used to track approval status.

    """
    
    yield {
        "template_id": "template_id_123",
    }

@gryd.is_a_task(function_name="trigger_campaign")
def trigger_campaign(campaign_type, campaign_id):
    """
    Trigger a campaign for a given campaign type and campaign id.
    """
    logger.info("------ Triggering Campaign ------")

    lead_table = "pre_sales_lead" if campaign_type == "pre-sales" else "post_sales_lead"

    with get_pg_connector() as pg:
        leads = list(pg.list(lead_table, {"campaign_id": campaign_id}))

    logger.info(f"Total leads fetched: {len(leads)}")

    valid_leads = []

    # if the lead_data doesnt have a phone number(pre sales) or persons_involved (post sales), skip it
    for lead in leads:

        if campaign_type == "post-sales":
            persons = lead.get("persons_involved") or []
            if not persons:
                logger.info(f"Skipping post-sales lead (no persons involved): {lead.get('lead_id')}")
                continue

        else:  
            if not lead.get("phone_number"):
                logger.info(f"Skipping pre-sales lead (no phone number): {lead.get('lead_id')}")
                continue

        valid_leads.append(lead)

    logger.info(f"Valid leads to process: {len(valid_leads)}")

    for lead in valid_leads:
        # logger.info(f"Queueing task for lead_id={lead.get('lead_id')}")

        gryd.create_async_task(
            "process_single_lead",
            AUTOCRM_CAMPAIGN_SERVICE_NAME,
            args=[None, lead, campaign_type, campaign_id],
            kwargs={}
        )

    logger.info("All valid leads queued successfully.")

@gryd.is_a_task(function_name="process_single_lead")
def process_single_lead(channel, lead, campaign_type, campaign_id, user_id=None):
    """
    Process a single lead from a campaign.

    Args:
        channel (str): The channel to use for communication. If not provided, it will be determined from the lead data.
        lead (dict or str): Lead data to process. If a dict, it should contain the lead_id. If a str, it is the lead_id.
        campaign_type (str): The type of campaign. Either "pre_sales" or "post_sales".
        campaign_id (str): The ID of the campaign.
        user_id (str, optional): The ID of the user to select for post-sales campaigns. If not provided, the first person will be selected.

    Returns:
        dict: Response from Airtable containing the `template_id`.
              This ID can be used to track approval status.
    """
    logger.info("----- In process_single_lead task -----")

    with get_pg_connector() as pg:
        if campaign_type == "pre-sales":
            campaign_details = list(pg.list("pre_sales_campaign", {"campaign_id": campaign_id}))
            lead_table = "pre_sales_lead"
            lead_id_field = "pre_sales_lead_id"
        else:
            campaign_details = list(pg.list("post_sales_campaign", {"campaign_id": campaign_id}))
            lead_table = "post_sales_lead"
            lead_id_field = "post_sales_lead_id"

    if not campaign_details:
        raise ValueError("Invalid campaign_id")

    campaign_details = campaign_details[0]
    # logger.info(f"CAMPAIGN DETAILS:\n{json.dumps(campaign_details, indent=4)}")

    if isinstance(lead, dict):
        lead_data = lead
        lead_id = lead.get(lead_id_field)
    else:
        lead_id = lead
        logger.info(f"Fetching full lead details for lead_id={lead_id}")

        with get_pg_connector() as pg:
            result = list(pg.list(lead_table, {lead_id_field: lead_id}))

        if not result:
            logger.error(f"No lead found for {lead_id_field}={lead_id}")
            return None

        lead_data = result[0]

    logger.info(f"Lead found: for lead_id={lead_id}")
    if not lead_id:
        logger.error("Lead ID missing in lead data so skipping..")
        return None

    if not channel:
        channel = get_channel(lead_data, campaign_details)

    # template_data = get_template_from_lead(lead_id)  # TODO: replace with GRYD async // input--lead_id, campaign_type output - template_data ,task name - get_whatsapp_template 
    # template_data=gryd.await_result(
    #     task="get_whatsapp_template",
    #     service="autocrm-agent",
    #     kwargs={
    #     "lead_id": lead_id,
    #     "campaign_type": campaign_type,
    #     "lead_info": {}
    #     }
    # )
    template_data=get_whatsapp_template(lead_id=lead_id, campaign_type=campaign_type, lead_info={})
        
    if not template_data:
        logger.error(f"No template data found for lead_id={lead_id}")
        return None
    template_data = template_data[0]
    logger.info(f"TEMPLATE DATA for mobile_number = {lead_data.get('phone_number')} and lead_id= {lead_id} and template details :\n{json.dumps(template_data, indent=4)}")

    buttons = template_data.pop("buttons", None)
    # if buttons:
    #     template_data = buttons
    # logger.info(f"TEMPLATE DATA:\n{json.dumps(template_data, indent=4)}")
    template_variables = template_data.get("template_variables", [])
    #TODO:later we need to change this..
    if campaign_type == "pre-sales":
        mobile = lead_data.get("phone_number")
        customer_name = lead_data.get("person_name")
        # model = (lead_data.get("model_preference") or [None])[0]
        variable_mapping = get_variable_values(template_variables, lead_data)
        
    else:
        persons = lead_data.get("persons_involved") or []
        selected_person = None

        # user_id is provided then find matching person
        if user_id:
            for p in persons:
                if p.get("user_id") == user_id:
                    selected_person = p
                    break

        if not selected_person and persons:
            selected_person = persons[0]

        if not selected_person:
            logger.error(f"No valid person found for post-sales lead_id={lead_id}")
            return None

        mobile = selected_person.get("last_contacted_whatsapp_number")
        customer_name = selected_person.get("person_name")
        # model = lead_data.get("vehicle_model")
        variable_mapping = get_variable_values(template_variables, lead_data, selected_person)
    campaign_user = {
        "lead_id": lead_id,
        "mobile_number": mobile,
        "customer_name": customer_name,
        # "model": model,
        "contact_channel": channel,
        "template_id": template_data.get("template_id"),
        "template_details": template_data.get("template_details"),
        **variable_mapping
    }
    logger.info(f"CAMPAIGN USER for lead_id = {lead_id}")
    template_vars = template_data.get("template_variables", []) 
    t_v = {var: template_data.get(var, "") for var in template_vars} 
    template_message = template_data.get("template_message", "").format(**t_v) 
    logger.info(f"Updated template_message: {template_message}")
    if channel == "web_chat":
        logger.info("Since it is a webchat channel we need to get the message from the template")
        data={
            "placeholder":template_message,
            "buttons":buttons
        }
        yield data
        return
    
    final_payload = {
        **campaign_details,
        **template_data,

        "enterprise_id": campaign_details.get("enterprise_id"),
        "campaign_id": campaign_details.get("campaign_id"),
        # these 2 channel and sender has to come from template_data check with prince 
        "channel": channel,
        "sender": "917795030574",
        "provider_name": "airtel",
        "template_message": template_message,
        "campaign_user_source": {
            "source_type": "default",
            "campaign_users": [campaign_user],
            "field_mapping": {
                "lead_id": "lead_id",
                "mobile_number": "mobile_number",
                "customer_name": "customer_name",
                "template_id": "template_id",
                "template_details": "template_details",
                "contact_channel": "contact_channel",
            },
            "config": {
                "batch_size": 100,
                "_skip_sent_message": True
            }
        }
    }

    run_async = campaign_details.get("run_async", True)
    is_testing = campaign_details.get("_is_testing", False)

    if not run_async:
        logger.info("Running in SYNC mode")
        b = BaseCustomCampaignManager()
        b.run_custom_campaign(
            _is_testing=is_testing,
            **final_payload
        )
        yield {"campaign_response": final_payload}
        return

    logger.info("Queueing async_run_custom_campaign task...")

    async_task = gryd.create_async_task(
        "async_run_custom_campaign",
        AUTOCRM_CAMPAIGN_SERVICE_NAME,
        args=[],
        kwargs={"_is_testing": is_testing, **final_payload},
        enterprise_id=campaign_details.get("enterprise_id", "autobotcrm")
    )

    yield {
        "task_response": async_task,
        "campaign_response": final_payload
    }

def get_channel(lead, campaign_details):
    """
    Get the contact channel for a lead.

    First, check if the lead has a preferred contact channel.
    If not, check if the campaign has specified channels.
    If yes, use the first channel in the list.
    If none of the above, fallback to "voice".

    :param lead: The lead object
    :param campaign_details: The campaign details object
    :return: The contact channel for the lead
    """
    
    
    #TODO:check this.
        # map_channel_to_provider = {"voice": "voicebot", "whatsapp": "whatsapp_chat"}
        # channel = map_channel_to_provider[channel]
        
    preferred = lead.get("preferred_contact_channel")
    if preferred:
        return preferred

    # check for Campaign channels and use the first channel.
    channels = campaign_details.get("channels") or ["voice"]
    if len(channels) > 0:
        return channels[0]

    return "voice"  #fallback

# @gryd.is_a_task(function_name="get_template_from_lead")
def get_template_from_lead(*args,**kwargs):
    """
    Get template information from the lead.

    Returns a dictionary containing the template information.
    """
    logger.info("Inside get_template_from_lead---")
    
    lead_id=kwargs.get("lead_id")
    
    logger.info(f"LEAD_ID---{lead_id}")
    
    # if not lead_id:
    #     return { "error":"No lead_id present.. "}
        
    return {
        "template_id": "01k8x5qma8r5rqvax694a6eabf",
        "template_name": "Service Reminder",
        "template_type": "text",
        "channel": "whatsapp_chat",
        "language": "english",
        "template_variables": [
            "customer_name",
            "model"
        ],
        "status": "approved",
        "template_media_id": None,
        "template_media_type": None,
        "template_media_url": None,
        "template_message": None,
        "dealer_name": None,
        "region_name": None,
        "communication_credentials_id": None,
        "media_file_name": None,
        "template_payload": {}, #for media
        "sender": "917795030574",
        "provider_name": "airtel",
        "template_buttons_payload": [
            "book-service-reminder-yes",
            "book-service-reminder-No"
        ]
    }


def get_variable_values(template_variables, lead_data, selected_person=None):
    """
    Extract values for template variables from lead_data or selected_person.
    Priority: selected_person → lead_data → None
    """
    values = {}
    for var in template_variables:
        if selected_person and var in selected_person:
            values[var] = selected_person.get(var)
        else:
            values[var] = lead_data.get(var)
    return values