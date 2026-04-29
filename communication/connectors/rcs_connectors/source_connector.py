#!/usr/bin/python
# -*- coding: utf-8 -*-

from communication_helpers import *
from config import AUTOCRM_COMMUNICATION_SERVICE_NAME,AUTOCRM_CONVERSATION_SERVICE_NAME
from gryd_worker import gryd, gryd_db_helper as db, gryd_helpers as hp
logger = gryd.logger
        
class RCSMessengerConnector:
    _registry = {}

    @classmethod
    def register(cls, provider: str, connector_cls):
        cls._registry[provider.lower()] = connector_cls
        logger.info(f"✅ Registered RCS provider: {provider}")

    @classmethod
    def get_provider(cls, provider: str):
        """
        Retrieves the RCS connector class registered for the given provider.

        Args:
            provider (str): The name of the RCS provider.

        Returns:
            The RCS connector class registered for the given provider.

        Raises:
            ValueError: If the provider is not registered.
        """
        provider = provider.lower()
        if provider not in cls._registry:
            raise ValueError(f"RCS Provider '{provider}' is not registered.")
        return cls._registry[provider]()
    
    
    def __init__(self, provider: str=None,**kwargs):
        self.default_message_dict: Dict[str, str] = {
            # === Identification ===
            "conversation_id": None,         # Unique conversation ID (per session/thread)
            "provider": None,       # Name of WhatsApp provider (e.g., meta, airtel)
            "enterprise_id": None,           # Tenant or client ID

            # === Participant Info ===
            "mobile_number": None,           # Customer's phone number (from/to)
            "to": None,             # Business number / source sender

            # === Message Tracking ===
            "message_id": None,              # Unique message ID from provider
            "sms_sid": None,      # Optional request UUID for tracking
            "SmsMessageSid": None,      # Optional request UUID for tracking
            
            # === Status & Timing ===
            "message_status": '',          # Status (e.g., sent, delivered, read)
            "status_timestamp": None,        # When status update occurred
            # "message_timestamp": None,       # Original message send time

            # === Content Type ===
            "message_type": '',            # Type of message (text, image, document, etc.)
            "message_text": '',            # Plain text message content
            "message_voice": None,           # Voice media metadata (if any)
            "message_image": None,           # Image media metadata (if any)
            "message_document": None,        # Document media metadata (if any)
            "message_location": None,        # Location payload (lat/lng)

            # === System Metadata ===
            # "channel_metadata":None,
            "message_dict": None,            # Original raw message block
            # "message_parameters": None,      # Button payloads / quick replies / CTA data

            # === Webhook Info ===
            "webhook_action": None,          # Inbound webhook action (send/receive/status)
            "webhook_received_time": None,   # Epoch or ISO time when webhook was received
            "language": None,                # Detected or selected language

            # === User Profile ===
            "profile": None,                 # Complete user profile dict
            "profile_name": None,            # Name extracted from profile

            # === Error Info ===
            "error": {},                     # Error dict (if any issues in parsing or delivery)
        }
        self.auth_model="communication_credential"
        
        self.whatsapp_provider: str = provider
        # self.message_model_name: str = message_model_name
        self.create_task_payload={}
        self.gryd_service_name= gryd.SERVICE
        self.webhook_process_start_time=kwargs.get("webhook_process_start_time",time.time())
        self.webhook_received_timestamp= hp.now(tz=DB_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
        
        
    def safe_update_dict(self, updates: dict):
        """
        Safely updates self.default_message_dict with non-empty values from updates.

        Skips keys with None, empty strings, empty lists/dicts, or string "null".
        Adds new keys if not present already.
        """
        logger.info(f"TEST safe update dict ---{updates}")
        for key, value in updates.items():
            if value in (None, "", [], {}, "null"):
                continue
            self.default_message_dict[key] = value
            
    def process_message_dict(self,*args,**kwargs):
        message_data = self.default_message_dict
        logger.info(f"TEST process message dict ---{message_data}")
        if not message_data:return
        message_dict=message_data.get("message_dict",{}).get("channelPayload")
        temporary_data = {  
            # "webhook_start_time":self.webhook_process_start_time,
            # "webhook_process_time":self.webhook_process_end_time,
            "message_sent_time_to_conversation":hp.now(tz=DB_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"),
            "message_received_time":message_dict.get("sendTime"),
            "message_sent_at":time.time(),
            "user_details":{
                "provider": message_data.get("provider"),
                "message_id": message_data.get("message_id"),
                "mobile_number": message_data.get("mobile_number"),
                "to": message_data.get("to"),
                "agent_id":message_data.get("agentId")
            }
        }
        
        converse_kwargs = {
            "customer_response" : message_dict.get("text"),
            "channel":"whatsapp_chat",
            "temporary_data": {"channel_response_task":{"service":AUTOCRM_COMMUNICATION_SERVICE_NAME,"task":"receive_converse_response_rcs","kwargs":temporary_data}},
            "response_length":"agent",
            "communication_data":{
                "rcs_message_id":message_data.get("message_id"),
                "user_sent_time":temporary_data.get("message_sent_at"),
                # "webhook_received_time":webhook_received_time
            }
        }
        
        self.converse_payload = {
            "_job": {
                "task": CONVERS_TASK_NAME,
                "service": AUTOCRM_CONVERSATION_SERVICE_NAME,
                "kwargs": converse_kwargs,
            }
        }
        
        kwargs["temporary_data"] = temporary_data
        logger.info("Calling session logic...")
        # call session logic here...
        d=handle_session_logic(message_data.get("mobile_number").replace('rcs:+',''),"rcs",True)
        logger.info(f"Session logic result: {d}")
        user_d=temporary_data.get("user_details")
        converse_kwargs.update({
            "session_id":d.get("session_id",None),
            "campaign_id":d.get("campaign_id","inbound"),
            "campaign_type":d.get("campaign_type","inbound"),
            "dealershp_id":d.get("dealership_id",None),
            # these 2 we need to check and send for email also..
            # "provider":user_d.get("rcs",None), 
            "contact":user_d.get("mobile_number",None),
            "lead_id":"inbound" if not d.get("campaign_id") else d.get("lead_id","inbound"),
            # "lead_id":d.get("lead_id",None)
        })
        # Remove all None values
        converse_kwargs = {k: v for k, v in converse_kwargs.items() if v is not None}
    
        res = gryd.create_async_task(
                CONVERS_TASK_NAME,
                AUTOCRM_CONVERSATION_SERVICE_NAME,
                kwargs=converse_kwargs
            )
        
        logger.info(f"Created Async task result---")
        
