import urllib.parse
import re

# --
# from typing import Optional,Dict,Any, List, Union, Callable,Tuple,Generator
# from gryd_worker import gryd, gryd_db_helper as db, gryd_helpers as hp
# from connectors.communication_configs import *
# from connectors.communication_helpers import AuthManager,format_box_log,safe_orjson_dumps
# --

from conversation.lead_post_processing import post_session_process

from config import AUTOCRM_COMMUNICATION_SERVICE_NAME,WHATSAPP_PROVIDER_NAME,WHATSAPP_PROVIDER_NUMBER
from connectors.communication_helpers import * 

from gryd_worker import gryd, gryd_db_helper as db, gryd_helpers as hp
logger = gryd.logger


# Path to parent folder
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(PARENT_DIR)

from autocrm_db_helper import get_pg_connector

from config import AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME,AUTOCRM_CAMPAIGN_SERVICE_NAME

logger.info("[INIT] Intializing Source Connector inside whatsapp_connector------------")
def SleepOverMessage():
    time.sleep(SLEEP_OVER_MESSAGE)

NullEmptyCheck=[None, "", "null", "None"]


class BaseCampaingStatusUpdator:
    def __init__(self):
        pass

    # ------------------- PARSERS -------------------

    def _parse_airtel_payload(self, data: dict):
        """Parse Airtel webhook data into normalized form."""
        logger.info(f"[_parse_airtel_payload] Raw data: {data}")

        msg_stream = data.get("msgStream", "").upper()
        msg_status = data.get("msgStatus", "").upper()

        if msg_stream == INBOUND:
            logger.info("[_parse_airtel_payload] Skipping INBOUND message processing.")
            return {}, ""

        if not msg_status or msg_status in IGNORED_STATUSES:
            logger.info(f"[_parse_airtel_payload] Skipping processing for status: {msg_status}")
            return {}, ""

        error_details = data.get("errorDetails") or {}
        message_dict = {
            "message_type": data.get("messageType"),
            "error_details": error_details or None,
            "error_code": error_details.get("code"),
            "error_title": error_details.get("title"),
            "error_href": error_details.get("href"),
            "message_status": msg_status,
            f"{msg_status.lower()}_timestamp": data.get("webhook_recieved_time", hp.time()),
        }
        message_id = data.get("messageId") if msg_status in TRACKABLE_STATUSES else ""

        logger.info(f"[_parse_airtel_payload] Parsed: message_id={message_id}, message_dict={message_dict}")
        return message_dict, message_id

    def _parse_rml_payload(self, data: dict):
        """Parse RML webhook data into normalized form."""
        logger.info(f"[_parse_rml_payload] Raw data: {data}")

        statuses = data.get("statuses", [])
        if not statuses:
            logger.info("[_parse_rml_payload] Not a status webhook")
            return {}, ""

        status = statuses[0]
        msg_status = status.get("status", "").upper()
        message_id = status.get("id")
        template_message_type = status.get("conversation", {}).get("origin", {}).get("type")
        pricing = status.get("pricing", {})
        errors = (status.get("errors") or [{}])[0]

        pricing_dict = {
            "pricing_billable": pricing.get("billable"),
            "pricing_model": pricing.get("pricing_model"),
            "pricing_category": pricing.get("category"),
            "pricing_type": pricing.get("pricing_type"),
            "meta_message_id": status.get("message_id"),
        }
        message_dict = {
            "template_message_type": template_message_type,
            "errors": errors,
            "error_details": errors.get("details"),
            "error_code": errors.get("code"),
            "error_title": errors.get("title"),
            "error_message": errors.get("message"),
            "error_data_details": errors.get("error_data", {}).get("details"),
            "message_status": msg_status,
            f"{msg_status.lower()}_timestamp": status.get("timestamp"),
            **pricing_dict
        }

        logger.info(f"[_parse_rml_payload] Parsed: message_id={message_id}, message_dict={message_dict}")
        return message_dict, message_id

    # ------------------- PROVIDER PARSERS -------------------
    def _parse_rml_context(self, data: dict):
        logger.info(f"[_parse_rml_context] Raw data: {data}")
        button_text, reply_text, message_id, button_payload = None, None, None, None

        messages = (data.get("messages") or [{}])[0]
        message_type = messages.get("type", "")
        message_type_data = messages.get(message_type, {})

        if message_type == "button":
            # Route Mobile sends button data flat
            button_text = message_type_data.get("text")
            button_payload = message_type_data.get("payload")
            message_id = messages.get("context", {}).get("id")

        elif message_type in {"button_reply", "list_reply"}:
            # Other types may have title/text
            button_text = message_type_data.get("title") or message_type_data.get("text")
            button_payload = message_type_data.get("payload")
            message_id = messages.get("context", {}).get("id")

        elif message_type == "text":
            reply_text = message_type_data.get("body")
            message_id = messages.get("context", {}).get("id")

        logger.info(
            f"[_parse_rml_context] Parsed: message_id={message_id}, "
            f"button_text={button_text}, reply_text={reply_text}, button_payload={button_payload}"
        )
        return message_id, button_text, reply_text, button_payload



    def _parse_airtel_context(self, data: dict):
        logger.info(f"[_parse_airtel_context] Raw data: {data}")
        button_text, reply_text, message_id = None, None, None

        message_status = data.get("msgStatus", "").lower()
        if message_status != "received":
            logger.info("[_parse_airtel_context] Skipping non-received message.")
            return None, None, None

        message_parameters = data.get("messageParameters") or {}
        if not message_parameters:
            logger.info("[_parse_airtel_context] No message parameters found.")
            return None, None, None

        button_text = message_parameters.get("button", {}).get("text")
        reply_text = message_parameters.get("text", {}).get("body")
        context = message_parameters.get('context', {})
        message_id = f"{message_parameters.get('context', {}).get('id', '')}".strip()
        message_id = f"{context.get('messageRequestId')}-{data.get('sourceAddress')}"

        logger.info(f"[_parse_airtel_context] Parsed: message_id={message_id}, button_text={button_text}, reply_text={reply_text}")
        return message_id if message_id else None, button_text, reply_text


class BaseWebhookConverter:
    """
    Base class for handling webhook payload conversions.

    This class serves as a foundation for converting incoming webhook payloads into a standardized format.  
    It provides utility methods for token verification, message processing, and status updates.

    Subclasses should implement specific logic for different webhook providers.

    Attributes:
        default_message_dict (dict): Stores the standardized message data after conversion.
        whatsapp_provider (str): The name of the WhatsApp provider handling the webhook.
    
    Methods:
        payload_converter(*args, **kwargs):
            Converts the raw webhook payload into a structured format.

        process_webhook(*args, **kwargs):
            Orchestrates webhook processing, including token verification, status checks, and message handling.

        process_status_check():
            Determines if the webhook relates to a message status update and processes it accordingly.

        process_message_dict(*args, **kwargs):
            Extracts and structures message details before further processing.

        update_message_detail():
            Updates or inserts message-related data into the storage or database.

    Usage:
        This class should be subclassed and extended for specific webhook providers.
    """
    
    def parse_common_payload(self,kwargs):
        entry = kwargs.get("entry", [])
        webhook_data = hp.make_single(entry, None, True, {})
        changes = hp.make_single(webhook_data.get("changes", []), None, True, {})
        message_request_id = webhook_data.get("id", "")

        value_data = changes.get("value", {})
        statuses = hp.make_single(value_data.get("statuses", []), None, True, {})
        status = statuses.get("status", "")
        status_timestamp = statuses.get("timestamp", None)

        contacts = hp.make_single(value_data.get("contacts", []), None, True, {})
        content = hp.make_single(value_data.get("messages", []), None, True, {})
        message_id = statuses.get("id") or content.get("id", "")
        message_type = content.get("type", "text")
        text = content.get("text", {}).get("body", "")
        location = content.get("location", {})

        name = contacts.get("profile", {}).get("name", "")
        mobile_number = contacts.get("wa_id", "")
        channel_number = value_data.get("metadata", {}).get("display_phone_number", "")
        phone_number_id = value_data.get("metadata", {}).get("phone_number_id", "")
        source = value_data.get("messaging_product", "")
        message_timestamp = content.get("timestamp", None)

        return {
            "message_id": message_id,
            "message_type": message_type,
            "message_text": text,
            "message_timestamp": message_timestamp,
            "message_status": status,
            "status_timestamp": status_timestamp,
            "message_request_id": message_request_id,
            "mobile_number": mobile_number,
            "profile_name": name,
            "location": location,
            "channel_number": channel_number,
            "phone_number_id": phone_number_id,
            "source": source,
            "content": content,
            "value_data": value_data,
        }

    def get_provider_specific_fields(self,provider, content, phone_number_id, kwargs):
        interactive_data = {}
        media_detail = {}

        message_type = content.get("type")

        # Interactive message parsing
        if message_type == "interactive":
            sub_type = content.get("interactive", {}).get("type", "")
            text = content.get("interactive", {}).get(sub_type, {}).get("title", "sent")
            context_id = content.get("interactive", {}).get(sub_type, {}).get("id", "")
            flow_json = content.get("interactive", {}).get(sub_type, {}).get("response_json", {})
            reply_id = content.get("interactive", {}).get(sub_type, {}).get("id", "sent").strip()
            go_to, intent, count = ("none", "none", "none") if not reply_id else (reply_id.split("##") + ["", ""])[:3]

            interactive_data = {
                "message_sub_type": sub_type,
                "message_type": message_type,
                "message_text": text,
                "flow_json": flow_json,
                "context_id": context_id,
                "go_to": go_to,
                "intent": intent,
            }

        # Button fallback
        if message_type == "button":
            text = content.get("button", {}).get("text", "").lower()
            interactive_data["message_text"] = text

        # Media download (only META needs this)
        if message_type in ["image", "document", "video", "audio"] and provider == "META":
            media_id = content.get(message_type, {}).get("id", "").lower()
            media_url = self.get_meta_media(media_id, phone_number_id, message_type, kwargs.get("enterprise_id"))
            media_detail = {
                "message_media_url": media_url,
                "message_media_type": message_type
            }

        return interactive_data, media_detail
    


    def __init__(self, whatsapp_provider: str=None, message_model_name: Optional[str] = "whatsapp_message", default_message_dict = {},*args,**kwargs):
        self.default_message_dict: Dict[str, str] = {
            # === Identification ===
            "conversation_id": None,         # Unique conversation ID (per session/thread)
            "whatsapp_provider": None,       # Name of WhatsApp provider (e.g., meta, airtel)
            "enterprise_id": None,           # Tenant or client ID

            # === Participant Info ===
            "mobile_number": None,           # Customer's phone number (from/to)
            "from_number": None,             # Business number / source sender

            # === Message Tracking ===
            "message_id": None,              # Unique message ID from provider
            "message_request_id": None,      # Optional request UUID for tracking
            "session_id": None,              # Session context ID (optional)

            # === Status & Timing ===
            "message_status": '',          # Status (e.g., sent, delivered, read)
            "status_timestamp": None,        # When status update occurred
            "message_timestamp": None,       # Original message send time

            # === Content Type ===
            "message_type": '',            # Type of message (text, image, document, etc.)
            "message_text": '',            # Plain text message content
            "message_voice": None,           # Voice media metadata (if any)
            "message_image": None,           # Image media metadata (if any)
            "message_document": None,        # Document media metadata (if any)
            "message_location": None,        # Location payload (lat/lng)

            # === System Metadata ===
            "message_sort": None,            # Sorting hint (e.g., for grouping)
            "message_stream": None,          # Stream info if part of a batch
            "message_dict": None,            # Original raw message block
            "message_parameters": None,      # Button payloads / quick replies / CTA data

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
        # self.auth_model="whatsapp_auth_cred"
        self.auth_model="communication_credential"
        
        self.whatsapp_provider: str = whatsapp_provider
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
        for key, value in updates.items():
            if value in (None, "", [], {}, "null"):
                continue
            self.default_message_dict[key] = value
    
    # @timelogger()
    def audio_to_text_converter(self,audio_url,headers=None,recognizer="openai-whisper-online",sample_rate=16000,language="english"):

        asr_api= os.environ.get("ASR-API","https://gryd-webapp-dev-334553189554.asia-south1.run.app/gryd/api/asr/do_asr")
        payload = {
            "job_id": str(uuid.uuid4()),
            "kwargs": {
                "tasl_id": str(uuid.uuid4()),
                "audio_url": audio_url,
                "recognizer": recognizer,
                "sample_rate": sample_rate,
                "language": language
            }

        }
        if headers is None:
            headers = {
                "Content-Type": "application/json",
                "X-GRYD-ENTERPRISE-ID": "no_code_low_code",
                "X-GRYD-SESSION-ID": "aadfbfd5-2f54-31f5-aa5f-4e35d350d12d",
                "X-GRYD-TOKEN": "b39dfdbb-2a36-3501-9595-6458f9878bfa"
            }
        try:
            logger.info("Sending ASR request to {}".format(asr_api))
            logger.info("Payload: {}".format(payload))

            response = requests.post(asr_api, headers=headers, data=json.dumps(payload))
            logger.info("ASR response text :: {}".format(response.text))
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error("Request failed: {}".format(str(e)))
            try:
                logger.error("Response content: {}".format(response.content.decode('utf-8', errors='replace')))
            except Exception as decode_err:
                logger.error("Failed to decode error response: {}".format(str(decode_err)))
            return None
    
    def extract_media(self,*args,**kwargs):
        '''
        Method to extract media from the incoming payload.
        '''
        raise NotImplementedError("Subclasses must implement the `convert` method.")
    
    def payload_converter(self,*args,**kwargs):
        """
        Converts incoming webhook payload into a standardized format.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments containing webhook details.

        Updates:
            self.default_message_dict: Stores structured message data.
        """
        raise NotImplementedError("Subclasses must implement the `convert` method.")
    def _format_mobile_number(self, number: str, country_code: str = "91",add_plus:str=None) -> str:
        number = str(number)
        if len(number) <= 10:
            number = country_code + number
        if len(number)==12 and add_plus:
            number = "+" + number
        return number
    # @timelogger()
    def get_headers(self, channel_number: str, enterprise_id: str) -> Dict[str, str]:
        """
        Retrieve authentication headers for a given channel number and enterprise ID.
        - Uses multiple number formats to improve hit rate.
        - Tries cache-aware fetch_credentials first, then whatsapp_auth, then DB model.
        """
        # if not enterprise_id:
        #     logger.warning("[HEADERS] Enterprise ID missing. Returning empty headers.")
        #     return {}

        start_time = time.time()
        auth = AuthManager(self.whatsapp_provider)
        logger.info(f"[HEADERS] Fetching headers for channel={channel_number}, enterprise={enterprise_id}")
        headers = auth.get_headers(channel_number, enterprise_id)
        return headers


    def update_message_detail(self):
        """
        Updates or posts message details in the message model.
        """
        message_dict = self.default_message_dict
        enterprise_id = message_dict.get("enterprise_id")

        # Construct patch dictionary
        patch_dict = {
            "enterprise_id": enterprise_id,
            "from_number": message_dict.get("from_number"),
            "user_id":message_dict.get("mobile_number"),
            "mobile_number": message_dict.get("mobile_number"),
            "message_request_id": message_dict.get("message_request_id"),
            "message_parameters": message_dict.get("message_parameters"),
            "message_id": message_dict.get("message_id"),
            "conversation_id": message_dict.get("conversation_id"),
            "message_status": message_dict.get("message_status",'').upper(),
            "status_update_timestamp": message_dict.get("status_timestamp"),
            "error": message_dict.get("error"),
            "message_sort": message_dict.get("message_sort"),
            "message_type": message_dict.get("message_type"),
            "session_id": message_dict.get("session_id"),
            "message_option_id": message_dict.get("message_option_id"),
            "message_text": message_dict.get("message_text"),
            "message_context_request_id": message_dict.get("message_context_request_id"),
            "message_context_id": message_dict.get("message_context_id"),
            "whatsapp_provider": message_dict.get("whatsapp_provider") or self.whatsapp_provider,
            f"{message_dict.get('message_status', '').lower()}_timestamp": message_dict.get("status_timestamp"),
        }

        # Remove empty or null values
        patch_dict = {key: value for key, value in patch_dict.items() if value not in NullEmptyCheck}

        try:
            message_id = patch_dict.get("message_id")
            if not message_id:
                logger.warning("Message ID is missing. Skipping update.")
                return
            # gryd.create_async_task("upsert_message_status",GRYD_COMMUNICATION_STATUS_SERVICE,args=[self.message_model_name,enterprise_id, message_id,patch_dict,False])
            # upsert_message_status.apply_async(*(self.message_model_name,enterprise_id, message_id,patch_dict,False))
            return {"response":"Message Processed in Queue"}

        except Exception as e:
            hp.print_error()
            logger.error(f"Error updating message detail: {e}", exc_info=True)
            return {"error": str(e)}

    def process_status_check(self,*args,**kwargs):
        
        """
        Process message status webhook payload and triggers a contact status update asynchronously.

        Args:
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            dict: Response message indicating the status of the webhook processing.
        """
        if not (message_dict := self.default_message_dict):
            return None
        
        # logger.info(f"PROCESS STATUS CHECK---status --- {message_dict.get('message_status')}---data---{json.dumps(self.default_message_dict,indent=4)}")
        
        msg_status=message_dict.get("message_status").lower()
        wa_status= WA_TO_DISPOSITION.get(msg_status, None)
        
        # whatsapp status webhooks received here-----
        if wa_status:
            logger.info(f"Received {wa_status} status webhook for {message_dict.get('enterprise_id')} enterprise and mobile number: {message_dict.get('recipientAddress',message_dict.get('mobile_number'))}")
            message_dict["message_status"]=wa_status
            logger.info(f"Message dict: {message_dict}")
            gryd.create_async_task(
                'post_contact_status',
                AUTOCRM_COMMUNICATION_SERVICE_NAME,
                args = (message_dict.get('message_id'),),
                kwargs=message_dict)
            # self.post_contact_status(message_dict.get('message_id'),**message_dict)
            
        #Still any othere status hook there we will return  
        if msg_status: return {"info":f"Received {msg_status}--->{wa_status} status webhook"}

        return {}
    # @timelogger(label="process_message_dict")
    def process_message_dict(self, *args, **kwargs):
        """
        Processes the message dictionary and triggers a conversation workflow.
        
        Args:
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        message_dict = self.default_message_dict
        # logger.info(f"TEST process message dict ---{message_dict}")
        if not message_dict:return
        # Extract required fields
        enterprise_id = message_dict.get("enterprise_id")
        mobile_number = message_dict.get("mobile_number")
        conversation_id = message_dict.get("conversation_id")
        message_text = message_dict.get("message_text")
        message_media_url  =message_dict.get("message_media_url")
        message_type= message_dict.get("message_type")
        message_media_type= message_dict.get("message_media_type")

        if not message_text and not message_media_url:
            logger.error("No valid message text found in body or media URL. Cannot process further.")
            return

        # logger.info(f"[process_message_dict] PROCESSING MESSAGE DICT---{json.dumps(message_dict, indent=4)}")
        
        try: 
            self.webhook_process_end_time= time.time() - self.webhook_process_start_time
        except Exception as e:
            self.webhook_process_end_time=None
            pass
       # Prepare temporary data
        temporary_data = {  
            "webhook_start_time":self.webhook_process_start_time,
            "webhook_process_time":self.webhook_process_end_time,
            "message_sent_time_to_conversation":hp.now(tz=DB_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"),
            "message_received_time":self.webhook_received_timestamp,
            "message_sent_at":time.time(),
            "whatsapp_message_context":{
                "message_button_payload":message_dict.get("button_payload"),
                "message_context_id":message_dict.get("message_context_id"),
            },
            "message_option_id":message_dict.get("message_option_id"),
            "whatsapp_user_details":{
                "whatsapp_provider": message_dict.get("whatsapp_provider"),
                "session_id": message_dict.get("session_id"),
                "message_id": message_dict.get("message_id"),
                "mobile_number": mobile_number,
                "enterprise_id": enterprise_id,
                "conversation_id": conversation_id,
                "from_number": message_dict.get("from_number"),
                "phone_number_id":message_dict.get("phone_number_id")
            }
        }
        webhook_received_time = float(message_dict.get("webhook_received_time",0))
        # logger.info(f"TEST webhook_received_time----{webhook_received_time}")

        format_box_log({
            "Webbhook Provider": message_dict.get("whatsapp_provider"),
            "Webhook Received Time":webhook_received_time,
            "Message Sent at":temporary_data.get("message_sent_at"),
            "Webhook Processed":float(temporary_data.get("message_sent_at",0))-float(webhook_received_time)
        })
       
        logger.info(f"message_media_url (before processing): {message_media_url} | type: {type(message_media_url)}")

        
        if isinstance(message_media_url, dict):
            file_path = message_media_url.get("file_path")
            customer_response = message_media_url.get("customer_response")

            temporary_data.update({
                "message_media_type": message_media_type,
                "file_path": file_path,
                "message_media_url": message_media_url,
            })
            message_text = customer_response or file_path
            message_media_url = json.dumps(message_media_url)

        logger.info(f"message_media_url (after processing): {message_media_url} | type: {type(message_media_url)}")

        logger.info(f"[Performance Tracking] USER SENT TIME ---{temporary_data.get('message_sent_at')}")
        logger.info(f"[Performance Tracking] WEBHOOK RECEIVED TIME ---{webhook_received_time}")
        logger.info(f"[Performance Tracking] WEBHOOK PROCESS TIME ---{temporary_data.get('webhook_start_time')}")
        logger.info(f"[Performance Tracking] WEBHOOK PROCESS END TIME ---{temporary_data.get('webhook_process_time')}")
        converse_kwargs = {
            "customer_response" : message_text,
            "channel":"whatsapp_chat",
            "temporary_data": {"channel_response_task":{"service":"autocrm-communication","task":"receive_converse_response","kwargs":temporary_data}},
            "response_length":"agent",
            "communication_data":{
                "whatsapp_message_id":message_dict.get("message_id"),
                "user_sent_time":temporary_data.get("message_sent_at"),
                "webhook_received_time":webhook_received_time
            }
        }
        if message_dict.get("go_to") or   message_dict.get("intent"):
            converse_kwargs.update({
                "go_to": message_dict.get("go_to"),
                "intent": message_dict.get("intent"),
            })

        
        self.converse_payload = {
            "_job": {
                "task": CONVERS_TASK_NAME,
                "service": CONVERS_SERVICE_NAME,
                "kwargs": converse_kwargs,
            }
        }

        kwargs["temporary_data"] = temporary_data
        logger.info("Calling session logic...")
        # call session logic here...
        d=self.handle_session_logic(mobile_number,"whatsapp_chat")
        logger.info(f"Session logic result: {d}")
        user_d=temporary_data.get("whatsapp_user_details")
        converse_kwargs.update({
            "session_id":d.get("session_id",None),
            "campaign_id":d.get("campaign_id","inbound"),
            "campaign_type":d.get("campaign_type","inbound"),
            "dealershp_id":d.get("dealership_id",None),
            # these 2 we need to check and send for email also..
            "provider":user_d.get("whatsapp_provider",None), 
            "contact":user_d.get("mobile_number",None),
            "lead_id":"inbound" if not d.get("campaign_id") else d.get("lead_id","inbound"),
            # "lead_id":d.get("lead_id",None),
        })
        # Remove all None values
        converse_kwargs = {k: v for k, v in converse_kwargs.items() if v is not None}
        button_payload=message_dict.get("message_dict").get("button").get("payload") if message_dict.get("message_dict").get("button") else None
        logger.info(f"[process_message_dict] Button payload: {button_payload}       ")
        if message_text.lower() == "see autongage in action":
            logger.info(f"Sending Autongage demo template with mobile_number: {mobile_number}")
            self.send_custom_template(**{"mobile_number":mobile_number,"template_id":"01kg4ntf1ztsa783ss81nq8gqs"})
            return
        elif button_payload =="nada_autongage-call":
            gryd.create_async_task(
                "nada_pre_sales",
                AUTOCRM_CAMPAIGN_SERVICE_NAME,
                args=[],
                kwargs={"channel":"voice_phone","session_id":d.get("session_id",None)}
            )
        elif button_payload =="nada_autongage-chat":
            gryd.create_async_task(
                "nada_pre_sales",
                AUTOCRM_CAMPAIGN_SERVICE_NAME,
                args=[],
                kwargs={"channel":"whatsapp_chat","session_id":d.get("session_id",None)}
            )
        # i will have dealership_id,campaign_id,urgency_hook,user_id, create a pre_sales lead for this.
        # update the session with this lead id ,campaign id and campaign_type
        else:
            logger.info(f"Sending Converse with payload: {safe_orjson_dumps(converse_kwargs)} for service name : {CONVERS_SERVICE_NAME}")
            res = gryd.create_async_task(
                CONVERS_TASK_NAME,
                CONVERS_SERVICE_NAME,
                kwargs=converse_kwargs
            )

            logger.info(f"Created Async task result: {res}")

    
    def handle_session_logic(self,phone_number, channel=None,campaign_details=None, from_web_chat=False):
        payload = {}
        dealership_id = None

        # 1. PERSON
        person = self.get_or_create_person(phone_number)
        if person:
            payload.update({
                "phone_number": phone_number,
                "user_id": person.get("user_id"),
                
            })

        with get_pg_connector() as pg:
            logger.info("TEST Loading session logic...------------")
            # FROM WEB CHAT
            if from_web_chat and campaign_details:
                logger.info("Campaign details received from web chat.")
                payload.update({
                    "campaign_id": campaign_details.get("campaign_id"),
                    "campaign_type": campaign_details.get("campaign_type"),
                    "lead_id": campaign_details.get("lead_id"),
                })
                session = self.get_or_create_session(payload,channel)
                return {**session}

            logger.info(f"TEST phone_number: {phone_number}")
            # 3. CONTACT STATUS
            contact_list = list(
                pg.list_order_by("contact_status", {
                    "phone_number": phone_number
                },order_by="created", order="DESC")
            )
            logger.info(f"TEST contact_list present: {len(contact_list)}")
            

            campaign_id = campaign_type = campaign_model = lead_id = None

            if contact_list:
                
                contact = contact_list[0]
                logger.info(f"Contact found: {contact}")

                campaign_id = contact.get("campaign_id")
                campaign_type = contact.get("campaign_type")
                lead_id = contact.get("lead_id")

                campaign_model= "post_sales_campaign" if campaign_type == "post-sales" else "pre_sales_campaign"
                lead_model = "post_sales_lead" if campaign_type == "post-sales" else "pre_sales_lead"
                
                payload.update({
                    "campaign_id": campaign_id,
                    "campaign_type": campaign_type,
                    "campaign_model": campaign_model,
                    "lead_id": lead_id,
                    "lead_model": lead_model
                })
            else:
                logger.info(f"No existing campaign association for {phone_number}")

            # 4. CAMPAIGN FLOW
            # Override if campaign_details provided
            if campaign_details:
                logger.info("Overriding campaign with campaign_details.")
                if not campaign_details.get("campaign_id"):
                    return {"error": "campaign_details missing campaign_id"}

                campaign_id = campaign_details["campaign_id"]
                campaign_type = campaign_details.get("campaign_type")

                payload.update({
                    "campaign_id": campaign_id,
                    "campaign_type": campaign_type,
                })

            if campaign_id: 
                model_name = "pre_sales_campaign" if campaign_type == "pre_sales" else "post_sales_campaign"
                campaign_data = list(pg.list(model_name, {"campaign_id": campaign_id}))

                if campaign_data:
                    c_data = campaign_data[0]
                    dealership_id = c_data.get("dealership_id")
                    payload["dealership_id"] = dealership_id

                    # get credentials for dealership (skip if "dave")
                    if dealership_id and dealership_id.lower() != "dave":
                        _ = list(pg.list("communication_credential", {"dealership_id": dealership_id}))

                logger.info(f"TEST BEFORE SESSION FINAL PAYLOAD: {payload}")
                session = self.get_or_create_session(payload,channel)
                return {**session, "dealership_id": dealership_id}

            # 5. NON-CAMPAIGN FLOW
            creds = list(pg.list("communication_credential", {"sender": phone_number}))
            if creds:
                dealership_id = creds[0].get("dealership_id")
                payload["dealership_id"] = dealership_id

            session = self.get_or_create_session(payload,channel)
            return {**session, "dealership_id": dealership_id}

    def get_or_create_person(self,phone_number):
        """Return person object; create if not exists."""
        logger.info(f"Getting or creating person for phone_number: {phone_number}")
        
        with get_pg_connector() as pg:
            person_list = list(pg.list(
                "person", 
                {"phone_number":phone_number}
            ))
            if person_list:
                logger.info(f"Person already exists for phone_number: {phone_number}")
                return person_list[0]  
            
            d={
                "phone_number": phone_number,
                "created":time.time(),
            }
            # Create new person
            user_id_attr=self.generate_uid(d)
            logger.info(f"user_id_attr: {user_id_attr}")
            d= pg.update("person","user_id",user_id_attr,{
                "phone_number": phone_number,
                "created":time.time(),
                "updated":time.time()
                })
            logger.info(f"Person with phone_number: {phone_number}. Doesnt exist. Created a new one. data: {d}")
            return d

    def generate_uid(self,data):
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)

        uid = uuid.uuid3(uuid.NAMESPACE_DNS, data_str)

        return uid.hex[:16]   # 16 characters
      
    def apply_filters(self, session_id=None, user_id=None, channel=None, session_live=None, status=None):
        conditions = [] 
        params = ()
        if session_id:
            conditions.append("dict->>'session_id' = %s")
            params += (session_id,)          
        if user_id:
            conditions.append("dict->>'user_id' = %s")
            params += (user_id,)
        if channel:
            conditions.append("dict->>'channel' = %s")
            params += (channel,)
        if session_live:
            conditions.append("CAST (dict->>'session_live' AS bool) = %s")
            params += (session_live,)
        if status:
            if status.endswith('~'):
                conditions.append("dict->>'status' <> %s")
                status = status[:-1]
                # first_part += "AND LOWER(CAST(dict->>'status' AS text)) <> LOWER(%s)"
                params += (status,)
            else:
                conditions.append("dict->>'session_live' = %s")
                params += (session_live,)

        condition = "Where " + " AND ".join(conditions)
        return condition, params
    
    def get_or_create_session(self,data,channel=None):
        """
        Find active session or create new one.
        session_live=True AND status != completed
        """
        logger.info(f"In create or get session function. User id: {data.get('user_id')}, data: {data}")
        
        filters = {
            "session_id":data.get("session_id"),
            "user_id":data.get("user_id"),
            # "campaign_id":data.get("campaign_id"),
            "channel": channel or "whatsapp_chat" if data.get("campaign_type")=="post-sales" else None,
            "session_live": True,
            "status": "completed~"
        }
        
        filters = {k: v for k, v in filters.items() if v is not None}
        condition, param = self.apply_filters(**filters)
        
        # logger.info(f"TEST filters for sessions--{filters}")
        with get_pg_connector() as pg:
            sessions = list(db.GrydPGConnector.list(pg, "session", condition, param))
            # logger.info(f'TEST sessions found for {sessions}')
            if sessions:
                new_campaign_id = str(data.get("campaign_id")).strip() if data.get("campaign_id") else None
                old_campaign_id = str(sessions[0].get("campaign_id")).strip() if sessions[0].get("campaign_id") else None

                logger.info(f"Found exisiting session for user_id: {data.get('user_id')}")
                logger.info(f"Old campaign id: {sessions[0].get('campaign_id')}, New campaign id: {data.get('campaign_id')}")

                is_previous_session_inbound=False
                # Handle case where old_campaign_id is 'inbound' and new_campaign_id is None
                if old_campaign_id == "inbound" and not new_campaign_id:
                    logger.info("Old campaign id is 'inbound' and new campaign id is None. Returning existing session.")
                    is_previous_session_inbound=True
                    return sessions[0]
                logger.info(f"Is previous session inbound: {is_previous_session_inbound}")
                if (new_campaign_id != old_campaign_id) and not is_previous_session_inbound:
                    logger.info("There is a new triggered campaign for this user. Since there is an existing session, we are ending the existing(old) session and creating a new session..")
                    logger.info(f"OLD SESSIONID--{sessions[0].get('session_id')}")
                    # end the old session
                    self.end_session(**{"session_id":sessions[0].get("session_id")})
                    # create new session
                    s=self.create_new_session(data,channel)
                    return s
                else:
                    logger.info("Session has exisiting campaign_id. So we are returning the existing session.")
                    return sessions[0]

            logger.info(f"No Existing session found. Creating a new one..")
            
            # Create new session
            s=self.create_new_session(data,channel)
            
            return s

    @gryd.is_a_task(function_name="end_session")
    def end_session(*args, **kwargs):
        """
        Ends a session and triggers a post session process task.

        Args:
            session_id (str): The session id to end.

        Returns:
            None
        """
        session_id=kwargs.get("session_id")
        logger.info(f"Ending session with session_id: {session_id}")
        with get_pg_connector() as pg:
            pg.update("session","session_id",session_id,{"session_live":False,"status":"completed","end_time":time.time()})
            update_session_data_in_lead(session_id,"completed")
        logger.info(f"Calling post session process task for session_id: {session_id}")
        # post_session_process(**{"session_id":session_id})
        gryd.create_async_task("post_session_process",AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME,args=[],kwargs={"session_id":session_id})
        logger.info(f"Session with session_id: {session_id}. Has been ended.")
        
    @gryd.is_a_task(function_name="check_or_create_session")
    def check_or_create_session(phone_number, campaign_details, from_web_chat): 
        return BaseWebhookConverter().handle_session_logic(phone_number, campaign_details, from_web_chat)

    def create_new_session(self,data,channel=None):
        with get_pg_connector() as pg:
            new_session = {
                **data,
                "session_live": True,
                "channel": channel or "whatsapp_chat",
                "status": "interacted",
                "disposition": "engaged",
                "campaign_type": data.get("campaign_type","inbound"),
                "campaign_id": data.get("campaign_id",'inbound'),
                "created": time.time(),
                "updated": time.time(),
                "start_time": time.time()
            }
            
            data["updated"] = time.time()
            session_id=self.generate_uid(data)
            s= pg.update("session","session_id",session_id,new_session)
            logger.info(f"Session with user_id: {data.get('user_id')}. Doesnt exist. Created a new session. And the session_id is -- {s}")
            
            # updating last_session_channel
            if data.get("campaign_type") == "pre_sales":
                pg.update("pre_sales_lead","pre_sales_lead_id",s.get("lead_id"),{"last_session_channel":channel})
            elif data.get("campaign_type") == "post_sales":
                pg.update("post_sales_lead","post_sales_lead_id",s.get("lead_id"),{"last_session_channel":channel})
            # TODO:update last_contacted_whatsapp_number,last_contacted_email,last_contacted_phone_number in person model ( refer post_sales_lead)
            return s 
    def send_otp_template(*args, **kwargs):
        logger.info("Send OTP template called")

        template_id = kwargs.get("template_id")
        mobile_number = kwargs.get("mobile_number")
        otp = kwargs.get("otp")

        if not template_id or not mobile_number or not otp:
            logger.error("template_id or mobile_number or otp missing")
            return

        provider_name = WHATSAPP_PROVIDER_NAME
        sender = WHATSAPP_PROVIDER_NUMBER

        t_data = {
            "mobile_number": mobile_number,
            "template_id": template_id,
            "provider_name": provider_name,
            "sender": sender,
        }

        if otp:
            otp_list = [otp]
            t_data.update({
                "template_variables": otp_list,
                "variables": otp_list,
                "suffix": otp_list,
            })

        headers = BaseWebhookConverter().get_headers(sender, "")
        config = PROVIDER_CONFIG.get(provider_name.lower(), {})

        t_data.update({
            "headers": headers,
            "base_url": config.get("base_url", ""),
        })
        provider = WhatsappMessangerConnector.whatsapp(
            provider_name, *args, **kwargs
        )
        provider.handle_custom_template(**t_data)

        return
    
    def send_custom_message(*args, **kwargs):
        logger.info("Send custom message called")
        to = kwargs.get("to")
        message = kwargs.get("message")

        if not to or not message:
            logger.error("Missing 'to' or 'message' in custom message")
            return

        provider = WhatsappMessangerConnector.whatsapp(
            WHATSAPP_PROVIDER_NAME, *args, **kwargs
        )
        logger.info(f"Provider: {provider}")
        logger.info(f"Sending message to {to} with content: {message}")
        provider._send_text(to, message)
        return
    
    # @timelogger()
    def process_webhook(self, *args, **kwargs):
        """
        Processes incoming webhook requests.

        This function verifies the token, processes the payload, updates campaign status, 
        and handles message processing based on the webhook type.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments containing webhook details.

        Returns:
            dict: Response message indicating the status of the webhook processing.
        """
        # logger.info("TEST process webhook before payload converter----")
        self.payload_converter(*args, **kwargs)
        

        # gryd.create_async_task("update_campaign_status_params",GRYD_COMMUNICATION_STATUS_SERVICE,args=[kwargs.get("whatsapp_provider"),kwargs.get("enterprise_id")],kwargs=kwargs)
        if self.process_status_check():
            return {"info": f"Status Webhook Processed for {self.default_message_dict.get('enterprise_id', '')}"}

        self.process_message_dict(*args, **kwargs)
 
        return {"info": f"Webhook Processed for {self.default_message_dict.get('enterprise_id', '')}"}

    def send_custom_template(*args,**kwargs):
        logger.info("Send custom template called---")
        template_id=kwargs.get("template_id")
        mobile_number=kwargs.get("mobile_number")        
        if not template_id or not mobile_number:
            logger.error("template_id or mobile_number missing")
            return
        t_data={}
        
        template_details=get_template_details(template_id)
        if not template_details:
            logger.error(f"No template found for template_id={template_id}")
            return
        
        
        logger.info(f"[Send template] Template details: {template_details}")
        if template_details:
            t_data.update({
                "template_id": template_details.get("template_id"),
                "variables": template_details.get("template_variables"),
                "buttons": template_details.get("template_button_payloads"),
                "channel":template_details.get("channel"),
                "sender":template_details.get("sender"),
                "provider_name":template_details.get("provider_name"),
                "mobile_number":mobile_number
            })
                        
        provider = WhatsappMessangerConnector.whatsapp(
                t_data.get("provider_name"), *args, **kwargs
            )
        headers=BaseWebhookConverter().get_headers(t_data.get("sender"),"")
        config = PROVIDER_CONFIG.get(t_data.get("provider_name").lower(), {})
        base_url = config.get("base_url", "")
        t_data.update({"headers":headers,"base_url":base_url})
        provider.handle_custom_template(**t_data)
        
    
    def send_twilio_message(*args,**kwargs):
        logger.info("Send Twilio message called---")
        mobile_number=kwargs.get("mobile_number")        
        message_text=kwargs.get("message_text")        
        if not mobile_number or not message_text:
            logger.error("mobile_number or message_text missing")
            return
        t_data={
            "mobile_number":mobile_number,
            "message_text":message_text,
        }
                        
        provider = WhatsappMessangerConnector.whatsapp(
                "twilio", *args, **kwargs
            )
        headers=BaseWebhookConverter().get_headers("", "")
        config = PROVIDER_CONFIG.get("twilio", {})
        base_url = config.get("base_url", "")
        t_data.update({"headers":headers,"base_url":base_url})
        provider.handle_twilio_message(**t_data)
class PayloadBuilder:
    def __init__(self, provider_name, from_number):
        self.provider_name = provider_name
        self.from_number = from_number

    def format_number(self, number: str, country_code: str = "91", add_plus: str = None):
        number = str(number)
        if len(number) <= 10:
            number = country_code + number
        if len(number) == 12 and add_plus:
            number = "+" + number
        return number

    def build_payload(self, to_number):
        formatted_to = self.format_number(to_number)
        formatted_from = self.format_number(self.from_number)

        base_payloads = {
            "default": {"to": formatted_to, "from": formatted_from},
            "meta": {"to": formatted_to, "messaging_product": "whatsapp"},
            "concord": {"to": formatted_to, "messaging_product": "whatsapp", "recipient_type": "individual"},
            "gupshup": {"channel": "whatsapp", "source": formatted_from, "destination": formatted_to, "src.name": "Bot"},
            "rml": {"phone": self.format_number(formatted_to, country_code="+91", add_plus=True)}
        }

        return base_payloads.get(self.provider_name, base_payloads["default"])




class BaseWhatsappMessenger:
    def flatten_json(self,nested_json, parent_key='', sep='.'):
        items = []
        for k, v in nested_json.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.flatten_json(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def __init__(self,*args,**kwargs):
        
        self.whatsapp_provider=kwargs.get("whatsapp_provider")
        # self.message_model ="whatsapp_message"
        # self.whatsapp_auth_model = "whatsapp_auth_cred"
        self.whatsapp_auth_model="communication_credential"
        config = PROVIDER_CONFIG.get(self.whatsapp_provider, {})
        self.base_url = config.get("base_url", "")
        self.media_types = config.get("media_types", ["image", "document", "audio", "video"])
        self.response_mapping = config.get("response_mapping", {})
    
        # required to call each provider main method
        self.provider_manager_dict={
            "airtel":self.manage_airtel_api,
            "tcl":self.manage_tcl_api,
            "meta":self.manage_graph_api,
            "gupshup":self.manage_gupshup_api,
            "rml":self.manage_rml_api,  
            "concord":self.manage_concord_api,
            "twilio":self.manage_twilio_api,
        }
        pass
    def manage_concord_api(self,*args,**kwargs):
        '''
        Method to manage airtel api.
        '''
        raise NotImplementedError("Subclasses must implement the `manage_concord_api api` method.")
    
    def manage_airtel_api(self,*args,**kwargs):
        '''
        Method to manage airtel api.
        '''
        raise NotImplementedError("Subclasses must implement the `manage airtel api` method.")
    
    def manage_twilio_api(self,*args,**kwargs):
        '''
        Method to manage twilio api.
        '''
        raise NotImplementedError("Subclasses must implement the `manage twilio api` method.")
    def manage_graph_api(self,*args,**kwargs):
        '''
        Method to manage airtel api.
        '''
        raise NotImplementedError("Subclasses must implement the `manage graph api` method.")
    
    def manage_gupshup_api(self,*args,**kwargs):
        '''
        Method to manage airtel api.
        '''
        raise NotImplementedError("Subclasses must implement the `manage gupshup api` method.")
    
    def manage_rml_api(self,*args,**kwargs):
        '''
        Method to manage airtel api.
        '''
        raise NotImplementedError("Subclasses must implement the `manage rml api` method.")
    

    def manage_tcl_api(self,*args,**kwargs):
        '''
        Method to manage tcl api.
        '''
        raise NotImplementedError("Subclasses must implement the `manage tcl api` method.")
    
    def _format_mobile_number(self, number: str, country_code: str = "91",add_plus:str=None) -> str:
        number = str(number)
        if len(number) <= 10:
            number = country_code + number
        if len(number)==12 and add_plus:
            number = "+" + number
        return number

    
    def send_request(self, url, payload, headers):
        """Send the POST request based on provider type."""
        try:
            if self.whatsapp_provider == "gupshup":
                return requests.post(url, headers=headers, data=urllib.parse.urlencode(payload))
            return requests.post(url, headers=headers, json=payload)
        except Exception as e:
            hp.print_error()
            return {}

    def handle_response(self, response, payload, elapsed_time, **kwargs):
        """Handle and process the API response."""
        if isinstance(response,dict):
            raise ValueError("Response object can't dict")
        if response.status_code not in [200, 202]:
            logger.error(f"Error Response: {response.text}, Status Code: {response.status_code}")
            return self._handle_error_response(response)

        try:
            response_data = response.json()
        except ValueError:
            logger.error("Failed to decode JSON response.")
            return {"error_response": "Invalid JSON", "status_code": response.status_code}

        response_data.update({
            "status_code": response.status_code,
            "to_number": payload.get("to") or payload.get("destination")
        })
        logger.info(f"Successful Response: {response_data} ====== {self.whatsapp_provider }  {self.response_mapping}")
        try:
            return self._map_and_post_message(response_data, payload, elapsed_time, **kwargs)
        except Exception:
            hp.print_error()
            return response_data

    def _handle_error_response(self, response):
        """Safely handle error responses."""
        content_type = response.headers.get('Content-Type', '').lower()
        response_data = {"error_response": response.text, "status_code": response.status_code}

        if 'application/json' in content_type:
            try:
                json_data = response.json()
                response_data.update(self.flatten_json(json_data, sep="_"))
            except Exception:
                hp.print_error()

        return response_data

    def _map_and_post_message(self, response_data, payload, elapsed_time, **kwargs):
        """Map provider-specific fields and post message to model."""
        mapped_payload = {
            k: response_data.get(v) for k, v in self.response_mapping.items()
        }

        if self.whatsapp_provider == "airtel":
            mapped_payload.update({
                "message_id": f"{response_data.get('messageRequestId')}-{payload.get('to')}"
            })
        if self.whatsapp_provider=="concord":
            mapped_payload.update({
                "message_id":response_data.get("message",{}).get("queue_id"),
                "message_status":response_data.get("message",{}).get("message_status")
            })

        mapped_payload.update({
            "whatsapp_provider": self.whatsapp_provider,
            "api_response_time": str(elapsed_time),
            "from": payload.get("from"),
            "to": payload.get("to"),
            "sent_payload": payload
        })

        mapped_payload.update(kwargs.get("_additional_data", {}) or {})

        # enterprise_id = (
        #     self.enterprise_id
        #     or kwargs.get("enterprise_id")
        #     or kwargs.get("_additional_data", {}).get("enterprise_id")
        # )

        # logger.info(f"[**Posting**] Message Details to {enterprise_id}")
        
        # upsert_message_status.apply_async(*("whatsapp_message",enterprise_id,message_id,post_dict,True))
        # gryd.create_async_task("upsert_message_status",GRYD_COMMUNICATION_STATUS_SERVICE,args=["whatsapp_message",enterprise_id,message_id,post_dict,True])

        # logger.info(f"[_map_and_post_message] Mapped Payload: {mapped_payload}")
        return mapped_payload


    def log_request(self, url, headers, payload):
        logger.info(f"URL: {url}\nHeaders: {headers}\nPayload:\n{safe_orjson_dumps(payload)}")
        logger.info(f"Sending WhatsApp message to {self.whatsapp_provider}")


    # --- Final Refactored Entry Point ---
    def post_api(self, url, payload, headers, *args, **kwargs):
        """
        Sends a POST request to the specified URL with the given payload and headers.
        Logs request/response and handles response mapping & storage.
        """
        self.whatsapp_provider = self.whatsapp_provider or kwargs.get("whatsapp_provider")
        response_data = None

        try:
            self.log_request(url, headers, payload)
            start_time = hp.time()
            response = self.send_request(url, payload, headers)
            elapsed_time = hp.time() - start_time
            logger.info(f"🌐 Response received in {elapsed_time:.2f} seconds from {self.whatsapp_provider}")

            response_data = self.handle_response(response, payload, elapsed_time, **kwargs)

        except requests.exceptions.RequestException as e:
            hp.print_error()
            logger.exception("Exception occurred during API call.")
            response_data = {"unknown_error": str(e)}

        return response_data
 
    def send_message_whatsapp(self, to: Union[str, List[str]], from_number: str, **kwargs: Any) -> Any:
        logger.info(f"Received params :: {safe_orjson_dumps(kwargs)}")
        
        self.enterprise_id = kwargs.get("enterprise_id")
        self.whatsapp_provider = kwargs.get("channel_provider") or kwargs.get("whatsapp_provider")
        
        auth = AuthManager(self.whatsapp_provider)
        logger.info(f"auth---{auth}")
        self.headers = kwargs.pop("_credential", {}) or auth.get_headers(from_number, self.enterprise_id)
        if not self.headers:
            raise Exception(f"Headers not present in whatsapp_auth_creds model for {from_number}")
        
        res = {}
        recipients = hp.make_list(to)
        builder = PayloadBuilder(self.whatsapp_provider, from_number)
        
        for recipient in recipients:
            try:
                to_formatted = builder.format_number(recipient)
                payload = builder.build_payload(to_formatted)

                handler = self.provider_manager_dict.get(self.whatsapp_provider)
                if not handler:
                    raise ValueError(f"No handler found for provider: {self.whatsapp_provider}")
                
                logger.info(f"Sending message to {to_formatted} using {self.whatsapp_provider} : {handler}")
                res = handler(payload, **kwargs)

                logger.info(f"Response from {self.whatsapp_provider}: {res} | Payload: {safe_orjson_dumps(payload)}")
            
            except Exception as e:
                logger.exception(f"Error sending message via {self.whatsapp_provider} to {recipient}: {str(e)}")
        
        return res


    def converse_receiver(self, *args: Any, **kwargs: Any) -> Any:
        """
        Processes incoming message data and forwards it to WhatsApp via the appropriate provider.
        """
        try:
            logger.info(f"Processing received message with data: {kwargs}")
            
            # Extract temporary data and relevant fields
            self.temporary_data = kwargs.pop("temporary_data", {})
            self.whatsapp_user_details = self.temporary_data.get("whatsapp_user_details",{})
            self.whatsapp_provider = self.whatsapp_user_details.get("whatsapp_provider") or self.whatsapp_user_details.get("channel_provider")
            self.from_number = self.whatsapp_user_details.get("from_number")
            self.mobile_number = self.whatsapp_user_details.get("mobile_number")
            self.enterprise_id = self.whatsapp_user_details.get("enterprise_id")
            self.session_id= self.whatsapp_user_details.get("session_id")
            self.phone_number_id = self.whatsapp_user_details.get("phone_number_id")
            kwargs["session_id"] = self.whatsapp_user_details.get("session_id")
            data = kwargs.pop("data", {})  # safely pop "data", default to {}
            kwargs["response_data"] = data if isinstance(data, dict) else {}


            # Prepare parameters for WhatsApp message sending
            params = {
                "enterprise_id": self.enterprise_id,
                "whatsapp_provider": self.whatsapp_provider,
                "_credential": self.whatsapp_user_details.get("_credential", {}) or self.whatsapp_user_details.get("whatsapp_credential"),
                "message": kwargs.get("message") or kwargs.get("placeholder"),
                "session_id":self.session_id,
                "data": kwargs,
            }

            return self.send_message_whatsapp(self.mobile_number, self.from_number, **params)
        except Exception as e:
            hp.print_error(e)
            logger.error("An error occurred while processing the message.")

    def preprocess_for_whatsapp(self,message: str) -> str:
        # Line breaks
        message = message.replace("<br>", "\n")
        message = re.sub(r"</p>", "\n\n", message)
        
        # Bold
        message = re.sub(r"<b>(.*?)</b>", r"*\1*", message)
        message = re.sub(r"<strong>(.*?)</strong>", r"*\1*", message)
        message = re.sub(r"\*\*(.*?)\*\*", r"*\1*", message)  # markdown bold
        
        # Italic
        message = re.sub(r"<i>(.*?)</i>", r"_\1_", message)
        message = re.sub(r"<em>(.*?)</em>", r"_\1_", message)
        message = re.sub(r"__(.*?)__", r"_\1_", message)  # markdown italic
        
        # Lists
        message = re.sub(r"<li>(.*?)</li>", r"• \1\n", message)
        
        # Strip unsupported tags but keep text
        message = re.sub(r"</?u>", "", message)   # remove underline tags
        message = re.sub(r"</?ul>", "", message)  # remove <ul>
        message = re.sub(r"</?ol>", "", message)  # remove <ol>
        message = re.sub(r"<p>", "", message)     # handled by </p>
        
        return message.strip()


    def split_message_safely(self, message: str, is_msg_invalid: bool) -> list[str]:
        if is_msg_invalid or not message:
            return [""]

        if "|" in message and len(message) <= WHATSAPP_MESSAGE_SPLIT_LENGTH:
            return message.split("|")
        
        elif "|" in message:
            return message.split("|")

        message =  self.preprocess_for_whatsapp(message)

        chunks = []
        current_chunk = ""

        # Split by lines first to preserve \n as logical boundaries
        lines = message.split('\n')

        for line in lines:
            line += '\n'  # Add back the newline that was removed by split
            words = line.split()

            for word in words:
                if len(current_chunk) + len(word) + 1 <= WHATSAPP_MESSAGE_SPLIT_LENGTH:
                    current_chunk += (" " if current_chunk and not current_chunk.endswith('\n') else "") + word
                else:
                    chunks.append(current_chunk)
                    current_chunk = word

            # Preserve the newline at the end of the line
            if current_chunk and not current_chunk.endswith('\n'):
                current_chunk += '\n'

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    

    def check_descriptions(self, response_data: Optional[Dict[str, Any]]) -> bool:
        return bool(self.prepare_button_options(response_data, check_description=True))

    def prepare_button_options(
        self, response_data: Optional[Dict[str, Any]], check_description: bool = False
    ) -> Union[Tuple[List[Dict[str, Any]], bool, str], bool]:

        options_list = response_data.get("buttons", []) if response_data else []
        
        if not isinstance(options_list, list) or not options_list:
            # logger.error(f"Invalid or missing buttons payload :: {response_data}")
            return ([], False, "") if not check_description else False

        valid_options = [o for o in options_list if o.get("title")]
        if not valid_options:
            logger.error("No valid button titles found")
            return ([], False, "") if not check_description else False

        use_list_picker = any(len(o["title"]) > 20 for o in valid_options)
        use_description = any(len(o["title"]) > 24 for o in valid_options)

        if check_description:
            return True if use_list_picker else use_description

        heading = response_data.get("list_picker_heading", "Select Below")
        return valid_options, use_description, heading

    def get_media_type_and_meta(self, response_data: dict, media_order: list) -> tuple[str, dict]:
        """
        Auto-detect media type and extract corresponding metadata dict.

        Returns:
            (media_type, media_meta_dict)
        """
        media_type = next((mt.upper() for mt in media_order if mt.lower() in response_data), None)
        if not media_type:
            return "", {}

        media_meta = response_data.pop(media_type.lower(), {})
        if not isinstance(media_meta, dict) or not media_meta:
            return "", {}

        return media_type, media_meta

    def extract_common_media_fields(self, media_meta: dict) -> dict:
        """
        Extracts shared fields like URL, caption, filename from media metadata.
        """
        return {
            "url": media_meta.get("url") or media_meta.get("link", ""),
            "caption": media_meta.get("caption"),
            "filename": media_meta.get("filename") or media_meta.get("file_name")
        }
    
    def _prepare_send_request(
        self,
        payload: Dict[str, Any],
        extra_payload: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        media_func: Optional[Dict[str, Any]] = None,
        send_media: Optional[Dict[str, Any]] = None,
        wrap_message_key: bool = False,
        type: Optional[str] = None,
        custom_api_path: Optional[str] = None,
        **kwargs: Any
    ):
        """
        Prepares and sends the final API request.

        Supports:
        - extra_payload: dynamic fields (like template overrides)
        - message: core message content
        - media_func: placeholder for media logic (Route Mobile)
        - send_media: media attachments
        - wrap_message_key: whether to wrap in {"message": "..."}
        - custom_api_path: to override the base URL
        """
        try:
            # Merge payload components
            if extra_payload:
                payload.update(extra_payload)
            # =====bug in the code=====
            if message and hasattr(self, "message_payload"):
                payload.update(self.message_payload(message))

            if send_media and isinstance(send_media, dict):
                payload.update(send_media)

            # Fallback: handle media_func logic (RML compatibility stub)
            if media_func and isinstance(media_func, dict):
                payload.update(media_func)

            if not payload:
                logger.warning("Empty payload. Skipping request.")
                return

            # Apply default base keys
            if wrap_message_key and isinstance(wrap_message_key,bool):
                request_payload = {
                    "message": json.dumps(payload, separators=(",", ":"))
                }
                request_payload.update(self.default_payload)
            else:
                request_payload = payload
                request_payload.update(self.default_payload)

            # Choose endpoint
            api_path = custom_api_path or self.base_url
            # Final request
            self.res = self.post_api(api_path, request_payload, self.headers, **kwargs)


        except Exception as e:
            logger.error(f"Error processing request to {custom_api_path or self.base_url}: {e}", exc_info=True)
            if hasattr(hp, "print_error"):
                hp.print_error()


class WhatsappMessangerConnector:
    _registry = {}
    _class_name = "WhatsappMessangerConnector"

    @classmethod
    def register(cls, source_type: str, source_class: type):
        cls._registry[source_type.lower()] = source_class
        # logger.info(f"✅ {cls._class_name} Registered source: {source_type} -> {source_class.__name__}")
    @classmethod
    def whatsapp(cls,source_type,*args,**kwargs):
        logger.info(f"Intializing {cls._class_name}")
        src_type = source_type.lower()
        if not src_type:
            raise ValueError("Missing 'src_type' in campaign_user_source")

        logger.info(f"Loading campaign src_type: {src_type}")
        source_class = cls._registry.get(src_type)
        if not source_class:
            raise ValueError(f"Unsupported source type: {src_type}")
        
        return source_class(whatsapp_provider=source_type,*args,**kwargs)


class WhatsappReceiverConnector:
    _registry = {}
    _class_name = "WhatsappReceiverConnector"

    @classmethod
    def register(cls, source_type: str, source_class: type):
        cls._registry[source_type.lower()] = source_class
        # logger.info(f"✅ {cls._class_name} Registered source: {source_type} -> {source_class.__name__}")
    @classmethod
    def whatsapp(cls,source_type,**kwargs):
        logger.info(f"Intializing {cls._class_name}")
        src_type = source_type.lower()
        if not src_type:
            raise ValueError("Missing 'src_type' in campaign_user_source")

        logger.info(f"Loading campaign src_type: {src_type}")
        source_class = cls._registry.get(src_type)
        if not source_class:
            raise ValueError(f"Unsupported source type: {src_type}")
        
        return source_class(**kwargs)


class WhatsappCampaignTemplate:
    _registry = {}
    _class_name = "WhatsappCampaignTemplate"

    @classmethod
    def register(cls, source_type: str, source_class: type):
        # logger.info(f"TEST class registry {source_type} -> {source_class}")
        cls._registry[source_type.lower()] = source_class
        # logger.info(f"✅ {cls._class_name} Registered source: {source_type} -> {source_class.__name__}")
    @classmethod
    def whatsapp(cls,source_type,*args,**kwargs):
        logger.info(f"Intializing {cls._class_name}")
        src_type = source_type.lower()
        if not src_type:
            raise ValueError("Missing 'src_type' in campaign_user_source")

        logger.info(f"Loading campaign src_type: {src_type}")
        logger.info(f"WhatsappCampaignTemplate registry: {WhatsappCampaignTemplate._registry.keys()}")
        source_class = cls._registry.get(src_type)
        logger.info(f"source_class: {source_class}")
        if not source_class:
            raise ValueError(f"Unsupported source type: {src_type}")
        
        return source_class(whatsapp_provider=source_type,*args,**kwargs)



def update_session_data_in_lead(session_id,status):
    with get_pg_connector() as pg:
        session_data = list(pg.list("session", {"session_id": session_id}))
        if not session_data:
            logger.info(f"Could not find session with session_id: {session_id}")
        session_data = session_data[0]
        lead_id = session_data.get("lead_id")
        campaign_type = session_data.get("campaign_type")
        last_interaction_time = session_data.get("last_response_time",None)
        if lead_id:
            lead_model="post_sales_lead" if campaign_type == "post-sales" else "pre_sales_lead"
            lead_model_id="post_sales_lead_id" if campaign_type == "post-sales" else "pre_sales_lead_id"
            logger.info(f"Updating session data in lead with session_id: {session_id} and lead_id: {lead_id}")
            pg.update(lead_model,lead_model_id,lead_id,{"last_session_id":session_id,"last_session_status":status,"last_interaction_time":last_interaction_time})
            logger.info(f"Updated session data in lead with session_id: {session_id} and lead_id: {lead_id}")


        
