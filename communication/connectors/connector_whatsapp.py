# This file contains all the gryd task and initialises whatsapp connectors.

from os.path import (
    exists as ispath,
    dirname,
    abspath,
    basename,
    join as joinpath,
    split as pathsplit,
    splitext,
    sep as dirsep,
    isfile
)
from flask import request
import sys
# --- Set import path for internal modules ---
sys.path.insert(0, dirname(dirname(abspath(__file__))))
from connectors.base_connector_communication import *
logger= get_logger(__name__)
logger.info("Intializing Test Whatsapp Connectors")
from connectors.campaign_manager import BaseCustomCampaignManager,BaseWebhookConverter

ALLOWED_PROVIDERS= str(os.environ.get("ALLOWED_PROVIDERS","airtel,rml,meta,concord,gupshup"))

CACHE_FILE = "static/uploads/custom_whatsapp_webhook.json"
CACHE_TTL = 3600*24  # 24 hour (in seconds)
MAX_RETRIES = 5
RETRY_DELAY = 2  # seconds

def reupdateConversation(enterprise_id, conversation_id, conversation):
    """
    Remaps old enterprise_id and conversation_id to new ones based on the conversation string.
    
    Example:
        conversation = "no_code_low_code,indiaautobot,autobot,indiaautbot"
        -> old: (no_code_low_code, indiaautobot)
           new: (autobot, indiaautbot)
    """
    if not conversation:
        return enterprise_id, conversation_id

    new_conversations = [item.strip() for item in conversation.split(",")]
    # Expect groups of 4 elements
    if len(new_conversations) % 4 != 0:
        logger.warning(f"⚠️ Invalid conversation mapping format: {conversation}")
        return enterprise_id, conversation_id

    for i in range(0, len(new_conversations), 4):
        old_ent = new_conversations[i].lower()
        old_conv = new_conversations[i + 1]
        new_ent = new_conversations[i + 2]
        new_conv = new_conversations[i + 3]

        if old_ent == enterprise_id.lower() and old_conv == conversation_id:
            logger.info(
                f"✅ Remapping conversation: "
                f"{enterprise_id}/{conversation_id} → {new_ent}/{new_conv}"
            )
            return new_ent, new_conv

    logger.info(f"ℹ️ No remap found for {enterprise_id}/{conversation_id}")
    return enterprise_id, conversation_id


@gryd.is_a_task(function_name="process_forwarded_webhook")
# def process_forwarded_webhook(channel, channel_provider, enterprise_id, conversation_id, payload, language="english"):
def process_forwarded_webhook(*args, **kwargs):

    """
    Process a forwarded webhook request from the communication server.

    Args:
        channel (str): The channel name (e.g., 'WHATSAPP', 'VOICEBOT').
        channel_provider (str): The channel provider (e.g., 'airtel', 'rml').
        enterprise_id (str): The enterprise ID.
        conversation_id (str): The conversation ID.
        payload (dict): The payload received from the communication server.
        language (str): The language of the webhook (default: 'english').

    Returns:
        None

    Raises:
        None

    Notes:
        This function is called by the communication server when a webhook is received.
        It processes the webhook by extracting the required information and sending it to the `process_webhook` task.
    """
    channel,conversation_id=args[:2]
    logger.info(f"Recieved forwarded webhook from communication server for channel: {channel}")
    
    try:
        forwarded_data = {
            "channel": channel,
            "provider": kwargs.get("whatsapp_provider"),
            "enterprise_id": kwargs.get("enterprise_id"),
            "conversation_id": conversation_id,
            "language": kwargs.get("language", "english"),
            "webhook_received_time": time.time(),
            **kwargs
        }

        logger.info(f"[ForwardWebhook] Final payload: {json.dumps(forwarded_data, indent=4)}")

        process_webhook.apply_async(
                *(kwargs.get("whatsapp_provider"), kwargs.get("enterprise_id"), conversation_id, kwargs.get("language", "english")),
                **forwarded_data
            )


        logger.info("[ForwardWebhook] Processing completed successfully")

    except Exception as e:
        logger.error(f"[ForwardWebhook] Error processing webhook: {str(e)}", exc_info=True)

@gryd.is_a_task(function_name="process_webhook")
# @timelogger()
def process_webhook(*args, **kwargs):
    """
    Handle an incoming WhatsApp webhook and trigger the conversation engine.

    This task:
        - Validates and parses the incoming WhatsApp webhook payload.
        - Extracts message text, timestamps, identifiers, and routing metadata.
        - Resolves the correct session, person, and dealership context.
        - Constructs the `converse_kwargs` dictionary required by the
          conversation engine.
        - Forwards `converse_kwargs` to the appropriate conversation task
          (e.g., `converse`, `receive_converse_response`, etc.).
        - Yields a lightweight status object for task acknowledgment.

    The constructed `converse_kwargs` (passed internally to the conversation engine)
    follows this structure:
        {
            "customer_response": <text message sent by the user>,
            "session_id": "<session identifier>",
            "channel": "whatsapp_chat",
            "temporary_data": {
                "channel_response_task": {
                    "service": "autocrm-communication",
                    "task": "receive_converse_response",
                    "kwargs": <temporary_data>
                }
            },
            "response_length": "agent",
            "communication_data": {
                "whatsapp_message_id": "<provider message id>",
                "user_sent_time": "<timestamp when user sent message>",
                "webhook_received_time": "<timestamp when webhook reached server>"
            }
        }

    Args:
        data (dict): Raw webhook payload received from the WhatsApp provider.
        *args: Additional positional arguments.
        **kwargs: Contains context such as provider name, route metadata,
                  signature headers, or token data.

    
    calls the converse task to get the response back.
    gryd.create_async_task(
            CONVERS_TASK_NAME,
            CONVERS_SERVICE_NAME,
            kwargs=converse_kwargs
        )

    
    """
    logger.info(f"Received a webhook request for {args} with kwargs: {safe_orjson_dumps(kwargs)}")
    
    # as enterprise_id is not captured in kwargs so getting it from webhook args 
    whatsapp_provider, enterprise_id, conversation_id ,language= args[:4]
    if whatsapp_provider not in ALLOWED_PROVIDERS:
        logger.error(f"****Provider {whatsapp_provider} Not Found****")
        return 
    kwargs.update({"whatsapp_provider": whatsapp_provider, "enterprise_id": enterprise_id, "conversation_id": conversation_id,"language":language})
    format_box_log({
        "Received Webhook": whatsapp_provider,
        "Enterprise Id" : enterprise_id,
        "ARGS": args,
        "Time": hp.now(tz=DB_TIMEZONE)
    })
    logger.info(f"Received {whatsapp_provider} webhook for {enterprise_id} with kwargs: {safe_orjson_dumps(kwargs)}")
    

    if whatsapp_provider.lower() in WhatsappReceiverConnector._registry:
        kwargs["webhook_process_start_time"]=time.time()
        provider_instance = WhatsappReceiverConnector.whatsapp(whatsapp_provider,**kwargs)
        res= provider_instance.process_webhook(**kwargs)
        return res
    return {"info": "Whatsapp Provider Not Found"}

@gryd.is_a_task(function_name="receive_converse_response")
def receive_converse_response(*args,**kwargs):
    logger.info(f"Received Converse Response with args :{args}")
    logger.info(f"Received Converse Response with kwargs :{json.dumps(kwargs,indent=4)}")
    whatsapp_provider= kwargs.get("whatsapp_provider",'') or kwargs.get("temporary_data",{}).get("whatsapp_user_details",{}).get("whatsapp_provider",'')

    email_user_details =   kwargs.get("email_user_details",'') or kwargs.get("temporary_data",{}).get("email_user_details",{})
    message_sent_at= kwargs.get("temporary_data",{}).get("message_sent_at",0)

    if message_sent_at:
        logger.info(f"\n****Received Converse response at ** : {time.time()-float(message_sent_at)}")
    

    logger.info(f"_register :: {WhatsappMessangerConnector._registry}")
    if whatsapp_provider.lower() in WhatsappMessangerConnector._registry:
        logger.debug("Procssing Whatsapp Connector")
        provider_init= WhatsappMessangerConnector.whatsapp(whatsapp_provider,*args,**kwargs)
        provider_init.converse_receiver(*args,**kwargs)
        return 
    logger.error("No Whatsapp Provider found in receive_converse_response")
    return

@gryd.is_a_task(function_name="send_message_whatsapp")
def send_message_whatsapp(*args,**kwargs):
    logger.info(f"Received  Response with args :{args}")
    logger.info(f"Received  Response with kwargs :{kwargs}")
    whatsapp_provider= kwargs.get("whatsapp_provider")
    if not whatsapp_provider or whatsapp_provider.lower() not in WhatsappMessangerConnector._registry:
        logger.info("No Whatsapp Provider found")
        return {"error":"Whatsapp Provider not found"}
    provider_init = WhatsappMessangerConnector.whatsapp(whatsapp_provider,*args,**kwargs)
    
    res = provider_init.send_message_whatsapp(*args,**kwargs)
    return res

@gryd.is_a_task(function_name="post_contact_status")
def post_contact_status(*args, **data):
    """
    1) First call → args empty → create new contact_status
    2) Second call → args contains message_id → update existing contact_status
    """

    message_id = args[0] if args else None
    logger.info(f"[post_contact_status] message_id={message_id}")
    with get_pg_connector() as pg:

        if not message_id:
            # logger.info("[post_contact_status] No message_id → creating new record")

            payload = {
                **data,
                "created": time.time(),
                "updated": time.time()
            }

            # Generate primary key
            contact_status_id = BaseWebhookConverter().generate_uid(payload)

            pg.update("contact_status", "contact_status_id", contact_status_id, payload)

            logger.info(
                f"[post_contact_status] contact status {data.get('message_status')} "
                f"campaign_id={data.get('campaign_id')} | phone={data.get('phone_number')}"
            )

            return 


        records = list(pg.list("contact_status", {"message_id": message_id}))
        existing = records[0] if records else None

        if not existing:
            logger.warning(f"[post_contact_status] No existing record found for {message_id}. Nothing to update.")
            return

        existing["provider_status"] = (data.get("message_status") or "").upper()
        existing["updated"] = time.time()
        existing["created"] = time.time()
        payload = existing
        # logger.info(f"[post_contact_status] payload when message_id is present={payload}")
        contact_status_id = BaseWebhookConverter().generate_uid(payload)

        pg.update("contact_status", "contact_status_id", contact_status_id, payload)

        logger.info(
            f"[post_contact_status] contact status={data.get('message_status')} "
            f"campaign_id={existing.get('campaign_id')} | phone={existing.get('phone_number')}"
        )

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

@gryd.is_a_task()    
def check_or_create_session(self, phone_number): 
    """
    Process an incoming WhatsApp message and resolve the correct Person,
    Campaign context, Dealership, and Session data for the conversation.

    Workflow:
        1. Identify or create a Person based on the phone number.
        2. Check the contact_status model to determine whether the incoming
           message is related to a previously sent campaign.
        3. If a campaign is found:
               - Extract campaign_id and dealership_id.
               - Pass these into the session creation logic.
           If no campaign is found:
               - Determine dealership_id from communication_credential
                 based on the sender phone number.
        4. Create or retrieve an active session based on the resolved payload.

    Parameters:
        phone_number (str): The user's WhatsApp mobile number from which the 
                            message was received.

    """
    
    yield {
        "session_id": "session_id_123",
        "conversation_id": "conversation_id_123",
        "session_live": True,
        "status": "active",
        "application": "whatsapp",
        "user_id": "user_id_123",
        "dealership_id": "dealership_id_123"
    }

@gryd.is_a_task(function_name="trigger_campaign")
def trigger_campaign(campaign_type, campaign_id):
    """
    Trigger a campaign for a given campaign type and campaign id.

    Parameters:
        campaign_type (str): The type of campaign (pre-sales or post-sales).
        campaign_id (str): The id of the campaign to trigger.

    Returns:
        None

    Raises:
        ValueError: If the campaign_id is invalid.
    """
    logger.info("------ Triggering Campaign ------")

    # campaign details
    with get_pg_connector() as pg:
        if campaign_type == "pre_sales":
            
            campaign_details = list(pg.list("pre_sales_campaign", {"campaign_id": campaign_id}))
            lead_table = "pre_sales_lead"
        else:
            campaign_details = list(pg.list("post_sales_campaign", {"campaign_id": campaign_id}))
            lead_table = "post_sales_lead"

    if not campaign_details:
        raise ValueError("Invalid campaign_id")

    campaign_details = campaign_details[0]
    logger.info(f"CAMPAIGN DETAILS---{json.dumps(campaign_details,indent=4)}")

    # leads
    with get_pg_connector() as pg:
        leads = list(pg.list(lead_table, {"campaign_id": campaign_id}))

    logger.info(f"Total leads: {len(leads)}")

    # Process each lead individually
    for lead in leads:

        logger.info(f"Queueing task for single lead...")
        res=gryd.create_async_task(
            "process_single_lead",
            GRYD_COMMUNICATION_CAMPAIGN_SERVICE,
            args=[None, lead, campaign_details],
            kwargs={}
        )

@gryd.is_a_task(function_name="process_single_lead")
def process_single_lead(channel, lead, campaign_details):
    """
    Trigger campaign for a single lead.
    Channel is already decided outside this function.
    """

    logger.info(f"In process_single_lead task---------")
    
    if not channel:
        channel = get_channel(lead, campaign_details)
        
    lead_id_field = (
        "pre_sales_lead_id"
        if campaign_details.get("campaign_type") == "pre-sales"
        else "post_sales_lead_id"
    )
    lead_id = lead.get(lead_id_field)
    if not lead_id:
        return None

    # Template fetch
    
    # template_data=gryd.create_async_task(
    #     "get_template_from_lead",
    #     GRYD_COMMUNICATION_CAMPAIGN_SERVICE,
    #     args=[lead_id],
    #     kwargs={}
    #     )
    
    # template_data=yield_gryd_task_results("get_template_from_lead",GRYD_COMMUNICATION_CAMPAIGN_SERVICE,{"lead_id":lead_id})
    
    template_data = get_template_from_lead(lead_id) #temporary
    logger.info(f"TEMPATES DATA---{template_data}")
    campaign_user = {
        "lead_id": lead_id,
        "mobile_number": lead.get("phone_number"),
        "customer_name": lead.get("person_name"),
        "model": (lead.get("model_preference") or [None])[0],
        "contact_channel": channel,                   
        "template_id": template_data.get("template_id"),
        "template_details": template_data.get("template_details"),
    }

    # Final payload (for one user)
    final_payload = {
        **campaign_details,
        **template_data,
        # "channel": channel,
        "enterprise_id": campaign_details.get("enterprise_id"),
        "campaign_id": campaign_details.get("campaign_id"),
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
                "batch_size": 100,        # default
                "_skip_sent_message": True
            }
        }
    }

    run_async = campaign_details.get("run_async", True)
    is_testing = campaign_details.get("_is_testing", False)
    b = BaseCustomCampaignManager()
    
    # Sync mode
    if not run_async:
        logger.info(f"herre-{final_payload}")
        b.run_custom_campaign(
            _is_testing=is_testing,
            **final_payload
        )
        yield {"campaign_response": final_payload}
    

    logger.info(f"campaign_detailsssssss-----{campaign_details}")
    # Async mode — separate queue task
    task = gryd.create_async_task(
        "async_run_custom_campaign",
        GRYD_COMMUNICATION_CAMPAIGN_SERVICE,
        args=[],
        kwargs={"_is_testing": is_testing, **final_payload},
        enterprise_id=campaign_details.get("enterprise_id","autobotcrm")
    )

    yield {
        "task_response": task,
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


if __name__=="__main__":
    # for airtel 
    # data={
    # "messages": [
    #     {
    #     "to": "917795030574",
    #     "businessId": "soco_addtwo",
    #     "from": "919113687241",
    #     "sessionId": "9da2b3855f104d169f677e7dcbea58c2",
    #     "profile": {
    #         "name": "Praveen A"
    #     },
    #     "message": {
    #         "text": {
    #         "body": "Hiii"
    #         },
    #         "timestamp": 1762666888537,
    #         "type": "text"
    #     },
    #     "webhook_received_time": 1762666888.645379,
    #     "ent_id": "autobot",
    #     "conversation_id": "msil_auto_demo",
    #     "whatsapp_provider": "airtel",
    #     "language": "english",
    #     "enterprise_id": "autobot"
    #     }
    # ]}
    # process_webhook("airtel","autobot","msil_auto_demo","english",**data)
    
    pass


    