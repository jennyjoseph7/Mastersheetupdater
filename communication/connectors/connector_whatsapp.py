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

@gryd.is_a_task(function_name="update_campaign_status_params")
def update_campaign_status_params(*args,**kwargs):
    """
    Processes campaign status updates for a given WhatsApp provider and enterprise ID.

    This function retrieves the appropriate webhook converter for the specified provider
    and executes relevant campaign status update methods if they exist.

    Args:
        *args: Positional arguments containing:
            - whatsapp_provider (str): The WhatsApp provider name.
            - enterprise_id (str): The enterprise ID.
        **kwargs: Additional keyword arguments, including:
            - args (tuple): A tuple of arguments.
            - kwargs (dict): A dictionary of keyword arguments.

    Returns:
        dict: 
            - {"info": "Campaign Message status Processed"} if processing succeeds.
            - {"error": "Error While processing campaign status"} if an exception occurs.

    Logs:
        - Logs errors if the provider or enterprise ID is missing.
        - Logs when the function receives the campaign status update request.

    Raises:
        - Logs and handles any exceptions that occur during execution.
    """
    start_time=time.time()
    logger.info(f"Received  update_camapign_status for with args: {args}  {len(args)}")
    whatsapp_provider,enterprise_id=args[0],args[1]
    if not (whatsapp_provider and enterprise_id):
        logger.error(f"Provider {whatsapp_provider} or enterprise_id : {enterprise_id} is missing.")
        return
    if not kwargs.get("enterprise_id"):
        kwargs.update({"enterprise_id":enterprise_id})
    try:
        if whatsapp_provider.lower() in WhatsappReceiverConnector._registry:
            provider_instance= BaseCampaingStatusUpdator()
            if hasattr(provider_instance,"update_message_status_for_campaign"):
                provider_instance.update_message_status_for_campaign(whatsapp_provider,enterprise_id,*args,**kwargs)
            if hasattr(provider_instance,"check_for_campaign_context"):
                provider_instance.check_for_campaign_context(*args,**kwargs)
            logger.info(f"@@@ Time Take to Update Campaing Status ::: {time.time()-start_time}")
            return {"info": "Campaing Message status Processed"}
    except Exception as e:
        hp.print_error()
        return {"error":"Error While processing camapign status"}


@gryd.is_a_task(function_name="post_contact_status")
def post_contact_status(data, *args, **kwargs):
    """
    Posts contact status updates when a campaign trigger occurs.

    For each lead, this function posts a new status object while keeping the 
    same `message_id` across updates. The function yields a structured dictionary 
    representing the current contact status, which can be sent to downstream 
    systems or stored for tracking.

    Example yielded data:
        {
            "message_id": "msh123abcd",
            "channel_provider": "twilio",
            "channel": "voice_phone",
            "phone_number": "8850988794",
            "response_id": "sid12323123",
            "campaign_id": "campaign_pre_sales_123",
            "provider_status": "initiated"
        }

    Typical provider statuses may include:
        - "initiated"
        - "queued"
        - "in-progress"
        - "completed"
        - "failed"

    Args:
        ...: (Describe any parameters here, such as campaign data or status input.)

    Yields:
        dict: A dictionary containing the contact status details for each lead.
    """


    yield  {
        "message_id":"msh123abcd",
        "channel_provider": "twilio",
        "channel":"voice_phone",
        "phone_number":"8850988794",
        "response_id":"sid12323123",
        "campaign_id" : "campaign_pre_sales_123",
        "provider_status": "initiated"
    }
    

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


# the below function is writtern in connectors.source_connectors (function name handle_incoming_message)
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



if __name__=="__main__":
    # data={
    # "messages": [
    #     {
    #     "id": "0046d404-b561-11f0-a380-0a58a9feac02",
    #     "from": "919113687241",
    #     "type": "text",
    #     "timestamp": "1761808865",
    #     "text": {
    #         "body": "what can you do?"
    #     },
    #     "message_id": "wamid.HBgMOTE5MTEzNjg3MjQxFQIAEhggQUM3RDhBRTYzRDI1ODkzNjY5NDhFOEE2MTRBN0RFRkQA"
    #     }
    # ],
    # "contacts": [
    #     {
    #     "profile": {
    #         "name": "Praveen A"
    #     },
    #     "wa_id": "919113687241"
    #     }
    # ],
    # "brand_msisdn": "918951708731",
    # "request_id": "0046d404-b561-11f0-a380-0a58a9feac02",
    # "webhook_received_time": 1761808866.994164,
    # "enterprise_id": "no_code_low_code",
    # "ent_id": "no_code_low_code",
    # "conversation_id": "indiaautobot",
    # "whatsapp_provider": "rml",
    # "language": "english"
    # }
    
    # process_webhook("rml","no_code_low_code","indiaautobot","english",**data)
    
    
    # for airtel 
    data={
    "messages": [
        {
  "to": "917795030574",
  "businessId": "soco_addtwo",
  "from": "919113687241",
  "sessionId": "9da2b3855f104d169f677e7dcbea58c2",
  "profile": {
    "name": "Praveen A"
  },
  "message": {
    "text": {
      "body": "Hiii"
    },
    "timestamp": 1762666888537,
    "type": "text"
  },
  "webhook_received_time": 1762666888.645379,
  "ent_id": "autobot",
  "conversation_id": "msil_auto_demo",
  "whatsapp_provider": "airtel",
  "language": "english",
  "enterprise_id": "autobot"
}

    ]}
    process_webhook("airtel","autobot","msil_auto_demo","english",**data)


    # gryd.create_async_task(
    #         "converse",
    #         "autocrm-conversation",
    #         kwargs={
    #             "channel":"whatsapp"
    #         }
    #     )
    
    
   
    pass


    