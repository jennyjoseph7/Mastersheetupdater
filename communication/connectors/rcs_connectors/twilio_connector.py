import os,re,sys
from os.path import dirname, abspath, join as joinpath

from communication.connectors.rcs_connectors.source_connector import RCSMessengerConnector
BASE_DIR = dirname(dirname(dirname(dirname(abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
# from communication.connectors.rcs_connectors.base_connector import RCSConnectorBase
from communication.connectors.rcs_connectors.source_connector import RCSMessengerConnector
from twilio.rest import Client
from communication_helpers import *
from gryd_worker import gryd, gryd_db_helper as db, gryd_helpers as hp
logger = gryd.logger
from config import TWILIO_ACCOUNT_SID ,TWILIO_AUTH_TOKEN,TWILIO_PHONE_NUMBER,RCS_AGENT_ID,AUTOCRM_COMMUNICATION_SERVICE_NAME
class TwilioRCSConnector(RCSMessengerConnector):
    def __init__(self,**kwargs):
        super().__init__(provider="twilio", **kwargs)
        
        self.account_sid = TWILIO_ACCOUNT_SID
        self.auth_token = TWILIO_AUTH_TOKEN
        self.client = Client(self.account_sid, self.auth_token)
        self.provider_name = "twilio"
        logger.info(f"✅ Initialized Twilio RCS connector")
        
    def send_rcs(self, to_number: str, from_number: str, message: str,provider: str = "twilio", **kwargs) -> Dict[str, Any]:
        logger.info(f"[TEST] Sending RCS message to {to_number} via Twilio")
        try:
            response = self.client.messages.create(
                body=message,
                from_= from_number or RCS_AGENT_ID,  # Your Twilio RCS-enabled number
                to=to_number if to_number.startswith("rcs:") else "rcs:+"+to_number
            )
            logger.info(f"Sent RCS message: {response.sid}")
            return {
                "provider": provider,
                "response": response,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Failed to send RCS message: {e}")
            return {
                "status": "error",
                "provider": provider,
                "error": str(e)
            }
        
    # getting message status from twilio
    def get_rcs_status(self,*args, **kwargs):
        logger.info(f"Received RCS Status webhook with args :{args}")
        logger.info(f"Received RCS Status webhook with kwargs :{json.dumps(kwargs,indent=4)}")
        
        msg_status=kwargs.get("MessageStatus").lower()
        logger.info(f"PROCESS STATUS CHECK---status --- {msg_status}")
        
        _status= WA_TO_DISPOSITION.get(msg_status, None)
        message_dict={}
        message_dict["message_id"] = kwargs.get("MessageSid")
        message_dict["message_status"] = _status
        message_dict["channel"] = "rcs"
        message_dict["phone_number"] = kwargs.get("To").replace("rcs:+","") if kwargs.get("To").startswith("rcs:+") else kwargs.get("To")
        
        if _status:
            mob_num=kwargs.get("To").replace("rcs:+","")
            logger.info(f"Received {_status} status webhook for mobile number: {mob_num}")
            logger.info(f"Calling post_contact_status with Message dict : {message_dict}")
            logger.info(f"Calling post_contact_status and checking the disposition : {_status}")    
            gryd.create_async_task(
                'post_contact_status',
                AUTOCRM_COMMUNICATION_SERVICE_NAME,
                args = (message_dict.get('message_id'),),
                kwargs=message_dict)
            # self.post_contact_status(message_dict.get('message_id'),**message_dict)
            
        return 
       
    
    # create a task to get incoming message and call it to twilio . also create a task to send it to the user ( refer receive_converse_kwargs in connector_whatsapp.py)
    def process_rcs_webhook(self, *args, **kwargs):
        logger.info(f"Received RCS webhook with args :{args}")
        logger.info(f"Received RCS webhook with kwargs :{json.dumps(kwargs,indent=4)}")
        
        self.payload_converter(*args, **kwargs)
            
        self.process_message_dict(*args, **kwargs)
        return 
    
    def payload_converter(self, *args, **kwargs):
        """
        Converts incoming webhook payload into a standardized format.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments containing webhook details.

        Updates:
            self.default_message_dict: Stores structured message data.
        """
        try:
            # message = kwargs.get("message", {})
            profile = kwargs.get("profile", {})
            error_details = kwargs.get("errorDetails", {})

            raw_channel_metadata = kwargs.get("ChannelMetadata")
            # logger.info(f"RAW CONTEXT MESSAGE: {raw_channel_metadata}")

            channel_metadata = {}

            if raw_channel_metadata:
                if isinstance(raw_channel_metadata, tuple):
                    raw_channel_metadata = raw_channel_metadata[0]

                if isinstance(raw_channel_metadata, str):
                    channel_metadata = json.loads(raw_channel_metadata)
                elif isinstance(raw_channel_metadata, dict):
                    channel_metadata = raw_channel_metadata

            message_dict = channel_metadata.get("data", {}).get("context", {})

            # Update default message dictionary
            self.safe_update_dict({
                "provider": kwargs.get("provider","twilio"),
                "enterprise_id": kwargs.get("enterprise_id"),
                "conversation_id": kwargs.get("conversation_id"),
                "mobile_number": kwargs.get("From", ""),
                "to": kwargs.get("To", ""),
                "message_id": kwargs.get("MessageSid"),
                "sms_sid": kwargs.get("SmsSid"),
                "message_status": kwargs.get("SmsStatus", "").upper(),
                "SmsMessageSid": kwargs.get("SmsMessageSid"),
                "message_dict": message_dict,
                "message_type":"text",
                # "message_timestamp":
                "webhook_recieved_time": kwargs.get("webhook_recieved_time"),
                "profile": profile,
                "error": error_details,
                "profile_name": profile.get("name"),
                "language": kwargs.get("language")
            })

            # Flatten error details into self.default_message_dict
            if isinstance(error_details, dict):
                self.safe_update_dict({f"error_{key}": value for key, value in error_details.items()})

            logger.info(f"RCS webhook payload_converter: {kwargs}")
            # Extract and update additional context and media details
            # self.safe_update_dict(self.extract_context_message(kwargs) or {})
            # self.safe_update_dict(self.extract_text_media(kwargs) or {})
        except Exception as e:
            logger.error(f"Error while processing incoming webhook: {e}", exc_info=True)


    
    def process_status_check(self,*args,**kwargs):
        
        """
        Process message status webhook payload and triggers a contact status update asynchronously.

        Args:
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            dict: Response message indicating the status of the webhook processing.
        """
        
    
    
    
    # post the campaign message to contact_status - check 
    
    
    
RCSMessengerConnector.register("twilio", TwilioRCSConnector)
