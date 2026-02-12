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
import config
from connectors.whatsapp_connectors.source_connectors import WhatsappMessangerConnector,WhatsappReceiverConnector,BaseWebhookConverter
import json
from autocrm_db_helper import get_pg_connector
#  this from connectors.base_connector_communication import *

sys.path.insert(0, dirname(dirname(abspath(__file__))))
from gryd_worker import gryd, gryd_db_helper as db, gryd_helpers as hp
gryd.SERVICE = config.AUTOCRM_COMMUNICATION_SERVICE_NAME
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


# @gryd.is_a_task(function_name="post_contact_status")
# def post_contact_status(*args, **data):
    
#     # lead_id, user_id, campaign_type,campaign_id, message_id
#     """
#     Handle and store contact status updates coming from WhatsApp / messaging providers.
#     Disposition updates for post-sales leads are strictly monotonic.
#     """
#     DISPOSITION_SEQUENCE = [
#         "queued",
#         "attempted",
#         "error",
#         "failed",
#         "reached",
#         "contacted",
#         "engaged",
#         "converted",
#     ]

#     def can_update_disposition(current, incoming):
#         if not incoming or incoming not in DISPOSITION_SEQUENCE:
#             return False
#         if not current or current not in DISPOSITION_SEQUENCE:
#             return True
#         return DISPOSITION_SEQUENCE.index(incoming) > DISPOSITION_SEQUENCE.index(current)

#     logger.info(f"[post_contact_status] message_status={data.get('message_status')}")
    
#     logger.info(f"[post_contact_status] args={args} | data={data}")
#     message_id = args[0] if args else None
#     logger.info(f"[post_contact_status] message_id={message_id}")

#     with get_pg_connector() as pg:
#         user_id = None
#         lead_id = None
#         campaign_type = None
#         channel = None
#         # update person
#         # person_d = list(pg.list("person", {"phone_number": data.get("phone_number")}))
#         person_d = list(pg.list_order_by(
#                 "person",
#                 {"phone_number": data.get("phone_number")},
#                 order_by="updated",
#                 order="DESC"
#             ))
        
#         if person_d:
#             person = person_d[0]
#             user_id = person.get("user_id")

#             person_payload = {
#                 "previous_contact_channel": (
#                     "whatsapp_chat"
#                     if data.get("channel") == "whatsapp_chat"
#                     else "email"
                    
#                 )
#             }

#             if data.get("channel") == "whatsapp_chat":
#                 person_payload["last_contacted_whatsapp_number"] = data.get("phone_number")
#             elif data.get("channel") == "email":
#                 person_payload["last_contacted_email"] = data.get("email")
#             elif data.get("channel") == "voice_phone":
#                 person_payload["last_contacted_phone_number"] = data.get("phone_number")
#             pg.update("person", "user_id", user_id, person_payload)
        
        
#         update_payload = {}
        
#         # Create contact status new record (if No message_id)
#         if not message_id:
#             logger.info("[post_contact_status] Creating new contact_status")

#             payload = {
#                 **data,
#                 "user_id": user_id,
#                 "created": time.time(),
#                 "updated": time.time(),
#             }
#             contact_status_id = BaseWebhookConverter().generate_uid(payload)

#             pg.update("contact_status", "contact_status_id", contact_status_id, payload)
#         else:
#             records = list(pg.list("contact_status", {"message_id": message_id}))
#             if not records:
#                 logger.warning(f"[post_contact_status] No contact_status found for {message_id}")
#                 return

#             existing = records[0]
#             existing["provider_status"] = data.get("message_status") or ""
#             existing["updated"] = time.time()
            
#             lead_id = existing.get("lead_id")
#             campaign_type = existing.get("campaign_type")
#             channel = existing.get("channel")
            
#             if data.get("message_status") == "failed":
#                 existing["failure_reason"] = "Message not delivered"

#             payload = existing
#             update_payload = existing
#             contact_status_id = BaseWebhookConverter().generate_uid(payload)

#             # Avoid duplicate queued / initiated overwrite
#             if data.get("message_status") not in ["initiated", "queued"]:
#                 pg.update("contact_status", "contact_status_id", contact_status_id, payload)
                
        
#         # logger.info(f"[post_contact_status] lead_id={lead_id} | provider_status={data.get('message_status')}")
#          # Lead update
#         campaign_type = campaign_type or data.get("campaign_type")
#         channel = channel or data.get("channel") 
#         lead_table = "post_sales_lead" if campaign_type == "post-sales" else "pre_sales_lead"
#         lead_pk = "post_sales_lead_id" if campaign_type == "post-sales" else "pre_sales_lead_id"
        
        
#         a={lead_pk: lead_id or data.get("lead_id")}
#         lead_d = list(pg.list(lead_table, a))
#         # logger.info(f"[post_contact_status] lead_table={lead_table}, a={a}, lead_d={lead_d}")
#         if not lead_d:
#             logger.warning(f"[post_contact_status] No lead found for {lead_id or data.get('lead_id')}")
#             return

#         lead = lead_d[0]
#         # logger.info(f"[post_contact_status] lead={lead}")
#         incoming_disp = data.get("message_status")

#         # persons / channel updates
#         if campaign_type == "post-sales" and user_id:
#             persons = lead.get("persons_involved", [])
#             update_payload["persons_involved"] = [
#                 (
#                     {
#                         **p,
#                         (
#                             "last_contacted_whatsapp_number"
#                             if channel == "whatsapp_chat"
#                             else "last_contacted_email"
#                         ): (
#                             data.get("mobile_number") or data.get("phone_number")
#                             if channel == "whatsapp_chat"
#                             else data.get("email")
#                         ),
#                     }
#                     if p.get("user_id") == user_id
#                     else p
#                 )
#                 for p in persons
#             ]
#         else:
#             update_payload["previous_contact_channel"] = (
#                 "whatsapp_chat"
#                 if channel == "whatsapp_chat"
#                 else "email"
#             )

#         # disposition update
#         if can_update_disposition(lead.get("disposition"), incoming_disp):
#             update_payload["disposition"] = incoming_disp
#         else:
#             logger.info(
#                 f"[post_contact_status] Disposition skipped "
#                 f"(current={lead.get('disposition')}, incoming={incoming_disp})"
#             )
#         # logger.info(f"[post_contact_status] update_payload={update_payload}")
    
#         # logger.info(f"[post_contact_status] lead_table={lead_table}, lead_pk={lead_pk}, lead_id={lead_id or data.get('lead_id')}")
#         if update_payload:
#             if update_payload.get("lead_id"):
#                 logger.info(f"[post_contact_status] Removing lead_id from update_payload")
#                 update_payload.pop("lead_id")
            
#             if update_payload.get("dealership_id"):
#                 logger.info(f"[post_contact_status] Removing dealership_id from update_payload")
#                 update_payload.pop("dealership_id")
#             pg.update(
#                 lead_table,
#                 lead_pk,
#                 lead_id or data.get("lead_id"),
#                 update_payload,
#             )

#     return

@gryd.is_a_task(function_name="post_contact_status")
def post_contact_status(*args, **data):
    """
    Handle and store contact status updates coming from WhatsApp / messaging providers.
    Disposition updates for post-sales leads are strictly monotonic.
    """

    DISPOSITION_SEQUENCE = [
        "queued",
        "attempted",
        "error",
        "failed",
        "reached",
        "contacted",
        "engaged",
        "converted",
    ]

    BILLABLE_STATUSES = {"delivered", "reached", "read", "contacted"}

    def can_update_disposition(current, incoming):
        if not incoming or incoming not in DISPOSITION_SEQUENCE:
            return False
        if not current or current not in DISPOSITION_SEQUENCE:
            return True
        return DISPOSITION_SEQUENCE.index(incoming) > DISPOSITION_SEQUENCE.index(current)

    logger.info(f"[post_contact_status] args={args} | data={data}")

    message_id = args[0] if args else None
    incoming_status = (data.get("message_status") or "").lower()

    raw_channel = data.get("channel")
    channel = raw_channel.strip() if isinstance(raw_channel, str) else None

    with get_pg_connector() as pg:
        user_id = None
        lead_id = None
        campaign_type = None
        update_payload = {}

        # person update
        person_d = list(
            pg.list_order_by(
                "person",
                {"phone_number": data.get("phone_number")},
                order_by="updated",
                order="DESC",
            )
        )

        if person_d and channel:
            person = person_d[0]
            user_id = person.get("user_id")

            person_payload = {"previous_contact_channel": channel}

            if channel == "whatsapp_chat":
                person_payload["last_contacted_whatsapp_number"] = data.get("phone_number")
            elif channel == "email":
                person_payload["last_contacted_email"] = data.get("email")
            elif channel == "voice_phone":
                person_payload["last_contacted_phone_number"] = data.get("phone_number")

            pg.update("person", "user_id", user_id, person_payload)

        if not message_id:
            payload = {
                **data,
                "user_id": user_id,
                "created": time.time(),
                "updated": time.time(),
            }
            contact_status_id = BaseWebhookConverter().generate_uid(payload)
            pg.update("contact_status", "contact_status_id", contact_status_id, payload)
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
        existing["message_status"] = incoming_status
        existing["updated"] = time.time()

        if incoming_status == "failed":
            existing["failure_reason"] = "Message not delivered"

        payload = existing
        contact_status_id = BaseWebhookConverter().generate_uid(payload)

        if incoming_status not in {"initiated", "queued"}:
            pg.update(
                "contact_status",
                "contact_status_id",
                contact_status_id,
                payload,
            )

        # post billing obj
        should_bill = (channel == "whatsapp_chat"
            and incoming_status in BILLABLE_STATUSES
            and previous_status not in BILLABLE_STATUSES
        )

        logger.info(f"[post_contact_status] should_bill={should_bill} | message_id={message_id} | prev={previous_status} → incoming={incoming_status}")
        if should_bill:
            logger.info(f"[post_contact_status] Billing triggered | message_id={message_id} | prev={previous_status} → incoming={incoming_status}")
            post_billing_obj(**data)

        # updating lead disposition
        lead_id = existing.get("lead_id")
        campaign_type = existing.get("campaign_type") or data.get("campaign_type")

        lead_table = (
            "post_sales_lead"
            if campaign_type == "post-sales"
            else "pre_sales_lead"
        )
        lead_pk = (
            "post_sales_lead_id"
            if campaign_type == "post-sales"
            else "pre_sales_lead_id"
        )

        lead_key = lead_id or data.get("lead_id")
        lead_d = list(pg.list(lead_table, {lead_pk: lead_key}))

        if not lead_d:
            logger.warning(f"[post_contact_status] No lead found for {lead_key}")
            return

        lead = lead_d[0]

        if campaign_type == "post-sales" and user_id and channel:
            persons = lead.get("persons_involved") or []

            channel_field_map = {
                "whatsapp_chat": (
                    "last_contacted_whatsapp_number",
                    data.get("mobile_number") or data.get("phone_number"),
                ),
                "email": ("last_contacted_email", data.get("email")),
                "voice_phone": (
                    "last_contacted_phone_number",
                    data.get("phone_number"),
                ),
            }

            field_name, field_value = channel_field_map.get(channel, (None, None))

            if field_name and field_value:
                update_payload["persons_involved"] = [
                    (
                        {**p, field_name: field_value}
                        if p.get("user_id") == user_id
                        else p
                    )
                    for p in persons
                ]

        elif channel:
            update_payload["previous_contact_channel"] = channel

        if can_update_disposition(lead.get("disposition"), incoming_status):
            update_payload["disposition"] = incoming_status
        else:
            logger.info(
                "[post_contact_status] Disposition skipped "
                f"(current={lead.get('disposition')}, incoming={incoming_status})"
            )

        update_payload.pop("lead_id", None)
        update_payload.pop("dealership_id", None)

        if update_payload:
            pg.update(
                lead_table,
                lead_pk,
                lead_key,
                update_payload,
            )

    yield contact_status_id
       
@gryd.is_a_task(function_name="check_or_create_session")
def check_or_create_session(phone_number, campaign_details, from_web_chat): 
    return BaseWebhookConverter().handle_session_logic(phone_number, campaign_details, from_web_chat)

def post_billing_obj(**message_dict):
    wa_status=message_dict.get("message_status")
    logger.info(f"Post billing obj for message_id: {message_dict.get('message_id')} and status: {wa_status}---")
    
    dealership_id=None
    item_description=None
    lead_id=None
    lead_model=None
    mob_num=message_dict.get('mobile_number')
    # posting billing model
    with get_pg_connector() as pg:
        contact_status_data=list(pg.list("contact_status",{"message_id":message_dict.get("message_id")}))
        contact_status_data=contact_status_data[0] if contact_status_data else {}
        
        if contact_status_data:
            dealership_id = contact_status_data.get("dealership_id")
            lead_id = contact_status_data.get("lead_id",None)
            lead_model= 'post_sales_lead' if contact_status_data.get('campaign_type') == 'post-sales' else 'pre_sales_lead'
        else:
            logger.info(f"Contact Status Data not found for message_id since it is a inbound message and not through campaign: {message_dict.get('message_id')}")
            session_data=list(pg.list("session",{"phone_number":mob_num}))[0]
            if not session_data: return
            dealership_id=session_data.get("dealership_id",None)
            lead_id=session_data.get('lead_id',None)
            lead_model= 'post_sales_lead' if session_data.get('campaign_type') == 'post-sales' else 'pre_sales_lead'
            
        logger.info(f"We have dealership_id: {dealership_id} in contact_status_data")
        if lead_id:
            logger.info(f"We have lead_id: {lead_id} in contact_status_data")
            lead_model_id="post_sales_lead_id" if lead_model == "post_sales_lead" else "pre_sales_lead_id"
            # logger.info(f"We have lead_model: {lead_model} and lead_model_id: {lead_model_id} in contact_status_data")
            lead_data=list(pg.list(lead_model,{lead_model_id:lead_id}))[0]
            # logger.info(f"We have lead_data: {lead_data}")
            if lead_data:
                item_description =f"{lead_data.get('campaign_type', 'unknown')} - {lead_data.get('campaign_objective_name', 'campaign_objective_id')} - {lead_data.get('campaign_name', 'unknown')} - {lead_data.get('channel', 'unknown')} - {config.WHATSAPP_PROVIDER_NAME} - {message_dict.get('mobile_number')}"
                campaign_id=lead_data.get('campaign_id')
            else:
                logger.info(f"Lead data not found for lead_id: {lead_id}")
                return      
        else:
            logger.info(f"Lead data not found for lead_id: {lead_id}")
            return   
    if lead_id and campaign_id and item_description:
        logger.info(f"Posting Billing for lead_id: {lead_id} and campaign_id: {campaign_id} with item_description: {item_description}")
        
        gryd.create_async_task(
            'post_billing',
            config.AUTOCRM_CORE_SERVICE_NAME,
            args=[
                dealership_id,
                "debit",
                config.AUTOCRM_MESSAGE_DELIVERED_ITEM,
                item_description,
                hp.now(as_datetime=False),
                1,
                config.AUTOCRM_MESSAGE_DELIVERED_PRICE,
                config.AUTOCRM_MESSAGE_DELIVERED_UNITS,
                "credits",
                campaign_id,
                "whatsapp_chat"
            ]
        )

    
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


    