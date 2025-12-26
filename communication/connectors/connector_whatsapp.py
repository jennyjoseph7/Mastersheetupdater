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

# added new instead of
import sys,os
import time
from connectors.communication_helpers import format_box_log,safe_orjson_dumps
from connectors.communication_configs import DB_TIMEZONE
from config import AUTOCRM_COMMUNICATION_SERVICE_NAME
from connectors.whatsapp_connectors.source_connectors import WhatsappMessangerConnector,WhatsappReceiverConnector,BaseWebhookConverter
import json
from autocrm_db_helper import get_pg_connector
#  this from connectors.base_connector_communication import *

sys.path.insert(0, dirname(dirname(abspath(__file__))))
from gryd_worker import gryd, gryd_db_helper as db, gryd_helpers as hp
gryd.SERVICE = AUTOCRM_COMMUNICATION_SERVICE_NAME
gryd.set_queue_manager()
logger = gryd.hp.get_logger(gryd.SERVICE)

logger.info("---Intializing Test Whatsapp Connectors")


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
        channel (str): The channel name (e.g., 'WHATSAPP', 'VOICE_PHONE').
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

        # logger.info(f"[ForwardWebhook] Final payload: {json.dumps(forwarded_data, indent=4)}")

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
    # logger.info(f"Received a webhook request for {args} with kwargs: {safe_orjson_dumps(kwargs)}")
    
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
    Handle and store contact status updates coming from WhatsApp / messaging providers.
    ----------
    1. If `message_id` is NOT provided:
        - Creates a new contact_status record.
        - Generates a UID based on the payload.
        - Stores created and updated timestamps.

    2. If `message_id` IS provided:
        - Fetches existing contact_status record.
        - Updates provider_status, timestamps, and regenerates UID.
        - Saves the updated contact_status record.

    3. Additional updates when message_status is "initiated" or "queued":
        - If campaign_type == "post-sales":
              • Find the corresponding post_sales_lead
              • Update persons_involved[].last_contacted_whatsapp_number
        - Else (pre-sales):
              • Update previous_contact_channel in pre_sales_lead
        - Always update person model:
              • last_contacted_whatsapp_number
              • previous_contact_channel
    """
    logger.info(f"TEST [post_contact_status] status====={data.get('message_status')}")
    message_id = args[0] if args else None
    logger.info(f"[post_contact_status] message_id={message_id}")

    with get_pg_connector() as pg:

        if not message_id:
            logger.info("[post_contact_status] No message_id → creating new record")

            payload = {
                **data,
                "created": time.time(),
                "updated": time.time()
            }

            contact_status_id = BaseWebhookConverter().generate_uid(payload)
            # logger.info(f"[post_contact_status] data={data}")
            pg.update("contact_status", "contact_status_id", contact_status_id, payload)
            if data.get("provider_status") in [ "initiated", "queued"]:
                person_d=list(pg.list("person", {"phone_number": data.get("phone_number")}))
                logger.info(f"[post_contact_status] person_d={person_d}")
                if person_d:
                    person_d=person_d[0]
                    user_id=person_d.get("user_id")
                    pg.update("person", "user_id", user_id, {"last_contacted_whatsapp_number": data.get("phone_number"),"previous_contact_channel": "whatsapp_chat"})
                # we need to update vehicle also but there is nothing to update check once with soham or ananth.
                if data.get("campaign_type") == "post-sales":
                    lead_d = list(pg.list("post_sales_lead", {"post_sales_lead_id": data.get("lead_id")}))
                    lead = lead_d[0]
                    persons_involved = lead.get("persons_involved", [])
                    pg.update(
                        "post_sales_lead",
                        "post_sales_lead_id",
                        data.get("lead_id"),
                        {
                            "persons_involved": [
                                {**p, "last_contacted_whatsapp_number": data.get("phone_number")}
                                if p.get("user_id") == user_id else p
                                for p in persons_involved
                            ],
                            "disposition": data.get("provider_status"),
                        })
                else:
                    pg.update("pre_sales_lead", "pre_sales_lead_id", data.get("lead_id"), {"previous_contact_channel": "whatsapp_chat"})
            
            return 

        records = list(pg.list("contact_status", {"message_id": message_id}))
        existing = records[0] if records else None

        if not existing:
            logger.warning(f"[post_contact_status] No existing record found for {message_id}. Nothing to update.")
            return

        existing["provider_status"] = (data.get("message_status") or "")
        existing["updated"] = time.time()
        existing["created"] = time.time()
        payload = existing
        contact_status_id =  BaseWebhookConverter().generate_uid(payload)
        if data.get("message_status")=="failed":
            logger.info(f"[post_contact_status] failed message_id={data.get('message_id')} | Failed message = {data.get('error_message',data.get('error_title'))}")
            payload["failure_reason"] = "Message not delivered"
        # Bcoz we have initially created the record for queued so skipping it
        if data.get("message_status") not in ["initiated", "queued"]:
            pg.update("contact_status", "contact_status_id", contact_status_id, payload)
            
        # logger.info(
        #     f"[post_contact_status] contact status={data.get('message_status')} "
        #     f"campaign_id={existing.get('campaign_id')} | phone={existing.get('phone_number')} | message_id={existing.get('message_id')}"
        # )

    return

        
@gryd.is_a_task(function_name="check_or_create_session")
def check_or_create_session(phone_number, campaign_details, from_web_chat): 
    return BaseWebhookConverter().handle_session_logic(phone_number, campaign_details, from_web_chat)


    
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


    