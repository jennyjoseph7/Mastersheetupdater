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
from communication.common_functions import generate_uid
from config import *
from campaign.campaign_workflow import CHANNEL_IDENTIFIER_MAP
from connectors.whatsapp_connectors.source_connectors import WhatsappMessangerConnector,WhatsappReceiverConnector,BaseWebhookConverter
import json
import functools
from autocrm_db_helper import get_pg_connector
#  this from connectors.base_connector_communication import *

_root = dirname(dirname(abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
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

def log_execution_time(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            duration = time.time() - start_time
            logger.info(f"[TIMING] Function -> {func.__name__} took {duration:.3f} seconds")
    return wrapper

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
    
    logger.info(f"Recieved forwarded webhook from communication server for channel: {channel}, kwargs: {kwargs}")
    
    try:
        forwarded_data = {
            "channel": channel,
            "provider": kwargs.get("whatsapp_provider","airtel"),
            "enterprise_id": kwargs.get("enterprise_id" , AUTOCRM_APP_ENTERPRISE_ID),
            "conversation_id": conversation_id,
            "language": kwargs.get("language", "english"),
            "webhook_received_time": time.time(),
            **kwargs
        }

        # logger.info(f"[ForwardWebhook] Final payload: {json.dumps(forwarded_data, indent=4)}")

        process_webhook.apply_async(
                *(kwargs.get("whatsapp_provider","airtel"), kwargs.get("enterprise_id", AUTOCRM_APP_ENTERPRISE_ID), conversation_id, kwargs.get("language", "english")),
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
            AUTOCRM_CONVERSATION_SERVICE_NAME,
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
    Disposition updates for post-sales leads are strictly monotonic.
    """

    BILLABLE_STATUSES = {"delivered", "reached", "read", "contacted"}

    logger.info(f"[post_contact_status] args={args} | data={data}")

    message_id = args[0] if args else None
    incoming_status = (data.get("message_status") or data.get("provider_status","")).lower()

    logger.info(f"[post_contact_status] Processing message_id={message_id} with incoming_status={incoming_status}")
    raw_channel = data.get("channel")
    channel = raw_channel.strip() if isinstance(raw_channel, str) else None
    channel_identifier=CHANNEL_IDENTIFIER_MAP.get(channel)
    with get_pg_connector() as pg:
        user_id = None
        should_bill = None
        # lead_id = None
        # campaign_type = None

        if not message_id:
            # person update
            person_d = list(pg.list_order_by(
                    "person",
                    {"phone_number": data.get("phone_number")},
                    order_by="updated",
                    order="DESC",
                )
            )
            logger.info(f"[post_contact_status] user with phone_number={data.get('phone_number')} has person records: {person_d}")
            if person_d and channel:
                person = person_d[0]
                user_id = person.get("user_id")

                gryd.create_async_task(
                    "update_channel_identifier",
                    AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME,
                    args=[user_id],
                    kwargs=data
                )
                
            payload = {
                **data,
                "user_id": user_id,
                "created": time.time(),
                "updated": time.time(),
            }
            contact_status_id = generate_uid(payload)
            logger.info(f"[post_contact_status] No message_id provided. Creating new contact_status with contact_status_id={contact_status_id}")
            pg.update("contact_status", "contact_status_id", contact_status_id, payload)
            # logger.info(f"Checking data for lead_disposition- Payload new --{json.dumps(data,indent=4)}")
            
            gryd.create_async_task(
                "update_lead_disposition_and_post_billing",
                AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME,
                args=[incoming_status],
                kwargs={"user_id": user_id , **data},
            )
            logger.info(f"[post_contact_status] New contact_status created for incoming_status={incoming_status}.Also calling next determine_campaign_next_action--{json.dumps(data,indent=4)}")
            
            call_next_campaign_workflow_task(data.get("campaign_id"),data.get("campaign_type"),data.get("lead_id"),data.get("channel"),data.get(channel_identifier),incoming_status,pg=pg,skip_workflow=data.get("skip_workflow", False))
            # update_lead_disposition(pg, incoming_status,user_id=user_id, **data) 
            return
        
        records= list(pg.list_order_by(
                "contact_status",
                {"message_id": message_id},
                order_by="updated",
                order="DESC"
            ))
        if not records:
            logger.warning(
                f"[post_contact_status] No contact_status found for message_id={message_id}"
            )
            return

        existing = records[0]
        logger.info(f"[post_contact_status] existing={existing}---- message_status ={existing.get('provider_status')}")
        previous_status = (existing.get("provider_status") or "").lower()
        channel = existing.get("channel") or channel

        existing["provider_status"] = incoming_status
        # existing["message_status"] = incoming_status
        existing["created"] = time.time()
        existing["updated"] = time.time()

        if incoming_status == "failed":
            existing["failure_reason"] = data.get("error").get("message") if data.get("error").get("message") else "Message delivery failed"

        payload = existing
        contact_status_id = generate_uid(payload)

        if incoming_status not in {"initiated", "queued", "attempted"}:
            pg.update(
                "contact_status",
                "contact_status_id",
                contact_status_id,
                payload
            )
            logger.info(f"[post_contact_status] contact_status created with incoming_status={incoming_status} and contact_status_id={contact_status_id}. Also calling next determine_campaign_next_action in--{json.dumps(data,indent=4)}")
            # logger.info(f"Skip workflow value: {data.get('skip_workflow')}")
            call_next_campaign_workflow_task(data.get("campaign_id"),data.get("campaign_type"),data.get("lead_id"),data.get("channel"),data.get(channel_identifier),incoming_status,pg=pg,skip_workflow=data.get("skip_workflow", False))

        # post billing obj
        should_bill = (channel in ["whatsapp_chat"]
            and incoming_status in BILLABLE_STATUSES
            and previous_status not in BILLABLE_STATUSES
        )

        logger.info(f"[post_contact_status] should_bill={should_bill} | message_id={message_id} | prev={previous_status} → incoming={incoming_status}")
        
        # logger.info(f"Checking data for lead_disposition- Payload--{json.dumps(payload,indent=4)}")
        # updating lead disposition
        gryd.create_async_task(
            "update_lead_disposition_and_post_billing",
            AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME,
            args=[incoming_status],
            kwargs={ "should_bill":should_bill,"post_template_message":True,**payload} 
        )
        # update_lead_disposition(pg,incoming_status,**payload)

    return 


def call_next_campaign_workflow_task(campaign_id,campaign_type,lead_id,channel,channel_identifier,disposition,pg=None,skip_workflow=False):
    logger.info(f"In the campaign workflow task for campaign_type: {campaign_type}, lead_id: {lead_id}, channel: {channel}, channel_identifier: {channel_identifier}, disposition: {disposition}")
    logger.info(f"Skip workflow flag={skip_workflow} for campaign_id: {campaign_id} and lead_id: {lead_id}")
    if skip_workflow:
        logger.info(f"Skipping workflow for campaign_id:{campaign_id}, lead_id:{lead_id}")
        return

    if not campaign_id:
        logger.error(f"campaign_id is required for campaign_type: {campaign_type}, lead_id: {lead_id}, channel: {channel}, channel_identifier: {channel_identifier}, disposition: {disposition}")
        return
    campaign_model= "pre_sales_campaign" if campaign_type == "pre-sales" else "post_sales_campaign"
    def _do_db_work(pg_conn):
        a=list(pg_conn.list(campaign_model, {"campaign_status": "Active"}))
        if not a:
            logger.info(f"Campaign with campaign_id: {campaign_id} is not active. Not calling next campaign workflow task.")
            return
        # TODO:before calling ananth task check the campaign status and then call.. 
        logger.info(f"Calling next campaign workflow task for campaign_type: {campaign_type}, lead_id: {lead_id}, channel: {channel}, channel_identifier: {channel_identifier}, disposition: {disposition}")
        gryd.create_async_task(
            "determine_campaign_next_action",
            AUTOCRM_CAMPAIGN_SERVICE_NAME,
            args=[campaign_type,lead_id,channel,channel_identifier,disposition],
            kwargs={"enterprise_id": AUTOCRM_APP_ENTERPRISE_ID},
        )
        # determine_campaign_next_action(campaign_type,lead_id,channel,channel_identifier,disposition,pg_conn)

    if pg:
        _do_db_work(pg)
    else:
        with get_pg_connector() as pg_conn:
            _do_db_work(pg_conn)
  
# @gryd.is_a_task(function_name="check_or_create_session")
# def check_or_create_session(phone_number, campaign_details, from_web_chat): 
#     return BaseWebhookConverter().handle_session_logic(phone_number, campaign_details, from_web_chat)

@gryd.is_a_task(function_name="send_media_template")
def send_media_template(*args, **kwargs):
    return BaseWebhookConverter().send_media_template(*args, **kwargs)
    
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


    
