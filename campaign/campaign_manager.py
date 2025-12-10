#!/usr/bin/python
# -*- coding: utf-8 -*-
from copy import deepcopy as copy
import math
import os
from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
import sys
sys.path.insert(0, dirname(dirname(abspath(__file__))))
from communication.connectors.communication_helpers import _wait_for_next_minute,yield_gryd_task_results
from communication.connectors.base_connector_communication import *
from config import AUTOCRM_CAMPAIGN_SERVICE_NAME
gryd.SERVICE = AUTOCRM_CAMPAIGN_SERVICE_NAME
gryd.set_queue_manager()
QUEUE_MANAGER = gryd.get_queue_manager(AUTOCRM_CAMPAIGN_SERVICE_NAME)
logger=hp.get_logger(__name__)
def clean_phone_number(phone_number: str) -> str:
    """
    Clean phone number:
    - remove spaces
    - remove special characters
    - keep only digits
    Phone numbers like " +91 98-76 543210 " → "919876543210".
    """
    return re.sub(r"\D", "", str(phone_number))


class BaseCampaignCreater:
    def create_text_template(self):
        '''
        Method to text template accoriding to the provider.
        '''
        raise NotImplementedError("Subclasses must implement the `create_text_template` method.")
        
    def create_carousel_template(self):
        '''
        Method to carousel template accoriding to the provider.
        '''
        raise NotImplementedError("Subclasses must implement the `create_carousel_template` method.")
    
    def create_media_template(self):
        '''
        Method to media template accoriding to the provider.
        '''
        raise NotImplementedError("Subclasses must implement the `create_media_template` method.")
    
    def _format_mobile_number(self,number: str, country_code: str = "91") -> str:
        
        number = str(number).strip()
        number = re.sub(r'[^0-9]', '', number)
        number = number.lstrip("0")
        if len(number) == 10:
            number = country_code + number
        return number

    def __init__(self,*args,**kwargs):
        pass

    def create_campaign_payload(self, campaign_details: dict, campaign_user_data: dict, enterprise_id: str) -> dict:
        """
        Create the payload required for sending a campaign message.

        Args:
            campaign_details (dict): Contains details of the campaign, like provider, template type, etc.
            campaign_user_data (dict): Contains user-specific data for personalization.
            enterprise_id (str): ID of the enterprise.

        Returns:
            dict: The prepared payload for the campaign.
                Returns {} if any required data or step fails.
        """
        try:
            whatsapp_provider = (
                campaign_details.get("whatsapp_provider") 
                or campaign_details.get("provider_name")
            )
            sender = campaign_details.get("sender")
            template_type = campaign_details.get("template_type")

            if not template_type:
                logger.error("Template type not found in campaign details")
                return {}

            logger.info(f"WhatsApp provider: {whatsapp_provider}")

            # Generate WhatsApp template payload
            try:
                template_class = WhatsappCampaignTemplate.whatsapp(whatsapp_provider)
                template_payload = template_class.create_template(
                    campaign_details,
                    params_data=campaign_user_data
                )
                template_payload.update({"is_campaign": True})
                logger.debug(f"Generated template payload: {template_payload}")

            except Exception as inner_err:
                hp.print_error()
                logger.exception(f"Error creating template payload: {inner_err}")
                return {}

            # Construct the final payload
            send_data = {
                "_additional_data": {
                    "campaign_conversation_id": campaign_details.get("conversation_id"),
                    "campaign_name": campaign_details.get("campaign_name"),
                    "campaign_id": campaign_details.get("campaign_id"),
                    "campaign_template": True,
                    "enterprise_id": enterprise_id,
                    "customer_state": "cs_campaign_templates",
                    "campaign_user_id": campaign_user_data.get("campaign_user_id"),
                },
                "campaign_user_id": campaign_user_data.get("campaign_user_id"),
                "customer_state": "cs_campaign_templates",
                "whatsapp_credential": (
                    campaign_user_data.get("whatsapp_credential") 
                    or campaign_details.get("whatsapp_credential", {})
                ),
                "enterprise_id": enterprise_id,
                "whatsapp_provider": whatsapp_provider,
                "message": None,
                "data": {"response_data": template_payload},
            }

            return send_data

        except Exception as e:
            hp.print_error()
            logger.exception(f"Unexpected error while creating campaign payload: {e}")
            return {}

    
    def send_campaign_message(
            self,
            mobile_number: str,
            lead_id: str,
            campaign_details: dict,
            campaign_user_data: dict,
            enterprise_id: str,
            *args,
            **kwargs
        ) -> dict:
        
        """
        Send a campaign message to a lead based on the campaign details.

        Args:
            mobile_number (str): The mobile number of the lead.
            lead_id (str): The lead ID.
            campaign_details (dict): The campaign details.
            campaign_user_data (dict): The campaign user data.
            enterprise_id (str): The enterprise ID.

        Returns:
            dict: The campaign user data with the updated message status.
        """
        start_time = time.time()
        whatsapp_provider = campaign_details.get("provider_name")
        sender = campaign_details.get("sender")
        logger.info(
            f"Preparing to send campaign message for lead_id={lead_id}, "
            f"provider={whatsapp_provider}, number={mobile_number}"
        )
        # logger.info(f"MOBILE NUMBER_---{mobile_number}")
        # Format mobile number safely
        mobile_number = self._format_mobile_number(
            mobile_number,
            country_code=campaign_user_data.get("country_code", "91") or "91"
        )
        patch_user_data = {"mobile_number":mobile_number,"template_message":campaign_details.get("template_message",'').format(**campaign_user_data)}
        logger.info(f"Campaign Message patch_user_data: {patch_user_data}")
        # Build payload
        send_data = self.create_campaign_payload(
            campaign_details, campaign_user_data, enterprise_id
        )
        if not send_data:
            logger.error(f"Failed to create send_data for campaign user ID {lead_id}")
            patch_user_data = {
                "execution_error": True,
                "execution_error_message": "Failed to create campaign payload",
                "sent_message": False,
            }
            return patch_user_data

        try:
            # Initialize provider connector
            provider = WhatsappMessangerConnector.whatsapp(
                whatsapp_provider, *args, **kwargs
            )

            # Send WhatsApp message
            response = provider.send_message_whatsapp(
                mobile_number, sender, **send_data
            )
            logger.info(f"Response for campaign user {lead_id}: {response}")

            # Handle successful response
            if isinstance(response, dict):
                response_code = response.get("response_code") or response.get("status_code")
                success = response_code == 200
                end_time = time.time()

                patch_user_data = {
                    "sent_message": True if success else  False,
                    "message_status": "initiated" if success else "failed",
                    "message_triggered_timestamp": hp.now(tz=DB_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"),
                    "message_id": response.get("message_id"),
                    "response_code": response_code,
                    "time_take_to_process": round(end_time - start_time, 3),
                    "sent_payload": response.get("sent_payload"),
                    "api_response_time": response.get("api_response_time"),
                    "message_request_id": response.get("message_request_id"),
                    "whatsapp_provider": whatsapp_provider,
                    "provider_name": whatsapp_provider,
                }

            else:
                # Non-dict response
                logger.warning(f"Unexpected response type for user {lead_id}: {type(response)}")
                patch_user_data = {
                    "sent_message": False,
                    "message_status": "invalid_response",
                    "execution_error": True,
                    "execution_error_message": f"Unexpected response type: {type(response)}",
                }

        except Exception as e:
            hp.print_error()
            logger.exception(f"Error sending message for campaign user ID {lead_id}: {e}")
            patch_user_data = {
                "execution_error": True,
                "execution_error_message": str(e),
                "sent_message": False,
                "message_status": "error",
            }

       
        logger.info(
            f"Updated campaign user {lead_id} with patch: {patch_user_data}"
        )
        
        logger.info(f"TEST MESSAGE_STATUS ------{patch_user_data.get('message_status')}")
        
        data={
                "lead_id":lead_id,
                "enterprise_id":enterprise_id,
                "campaign_id":campaign_details.get("campaign_id"),
                "campaign_type":campaign_details.get("campaign_type"),
                "campaign_model":campaign_details.get("campaign_model"),
                "phone_number":mobile_number,
                "message_id":response.get("message_id"),
                "provider_status":patch_user_data.get("message_status"),
                "channel_provider":whatsapp_provider,
                "channel":"whatsapp_chat",
            }
        gryd.create_async_task(
            "post_contact_status", 
            GRYD_COMMUNICATION_STATUS_SERVICE, 
            kwargs=data
        )
        return patch_user_data
        
        
class BaseCustomCampaignManager:
    """Manages custom campaign workflows, including user processing,
    campaign detail posting, and orchestration of batch execution."""

    
    def process_campaign_users_generic(
        self,
        enterprise_id,
        campaign_id,
        campaign_users,
        campaign_data,
        *args,
        **kwargs
    ):
        """
        Process a list of campaign users and send campaign messages for each user.

        Parameters
        ----------
        enterprise_id : str
            Unique identifier for the enterprise.
        campaign_id : str
            Unique identifier for the campaign.
        campaign_users : List[dict]
            List of campaign user dictionaries.
        campaign_data : dict
            Campaign data dictionary containing provider, template, etc. details.
        *args
            Variable positional arguments.
        **kwargs
            Additional keyword arguments.

        Returns
        -------
        List[str]
            List of processed campaign user IDs.
        """
        channel= campaign_data.get("channel").upper()
        logger.info(f"Starting processing {len(campaign_users)} users for campaign_id={campaign_id}, channel={channel}")
        #  use contact status model ---
        
        # --- Load credentials ---
        channel_key = "sender" if channel.upper() == "WHATSAPP_CHAT" else "caller_id"
        credential=None
        if channel.upper() == "WHATSAPP_CHAT":
            credential, provider = self.get_dyanamic_provider_creds(
                enterprise_id, campaign_data.get(channel_key), campaign_data
            )
            campaign_data[f"{channel.lower()}_credential"] = credential
        skip_creds_check = channel != "WHATSAPP_CHAT"
        if not credential and not skip_creds_check:
            logger.error(f"❌ {channel} credentials not found — aborting.")
            return []
        
        processed_users = []

        for count, user in enumerate(campaign_users, start=1):
            mobile_number = clean_phone_number(user.get("mobile_number", "")) if channel.upper() == "WHATSAPP_CHAT" else user.get("mobile_number", "")
            logger.info(f"mobile_number-----{ mobile_number}")
            logger.info(f"USER----------{user}")
            if channel.upper()=="WHATSAPP_CHAT":
                mobile_number = BaseCampaignCreater()._format_mobile_number(mobile_number,user.get("country_code","91"))
                
            if not mobile_number:
                logger.warning(f"[{count}] User record missing mobile_number: {user}")
                continue

            if user.get("unsubscribe", False):
                logger.info(f"[{count}] User {mobile_number} has unsubscribed. Skipping.")
                continue

            logger.info(f"[{count}] Processing user {mobile_number}")
            
            is_testing = kwargs.pop("_is_testing", False)

            # logger.info(f"process_campaign_users_generic campaign_details---{campaign_data}---campaign_users---{user}")
            
            if channel.upper()=="WHATSAPP_CHAT":
                logger.info(f"[{count}] Sent {channel} message for {campaign_data}")
                #TODO Send async 
                if is_testing:
                    logger.info(f"[{count}] Sending WhatsApp message synchronously for {campaign_data.get('campaign_id')} for phone_number={campaign_data.get('mobile_number')}")
                    continue
                if not campaign_data.get("run_async"):
                    logger.info(f"[{count}] Sending WhatsApp message synchronously for {campaign_data.get('campaign_id')}")
                    async_send_campaign_message(user.get("mobile_number"),
                        user.get("lead_id"),
                        campaign_data,
                        user,
                        enterprise_id,
                        count,)
                else:
                    logger.info(f"[{count}] Dispatching async WhatsApp message for phone_number:{campaign_data.get('mobile_number')}, campaign_id:{campaign_data.get('campaign_id')}, lead_id:{campaign_users.get('lead_id')}")
                    gryd.create_async_task("async_send_campaign_message",AUTOCRM_CAMPAIGN_SERVICE_NAME,args=[
                        user.get("mobile_number"),
                        user.get("lead_id"),
                        campaign_data,
                        user,
                        enterprise_id,
                        count
                    ],enterprise_id=enterprise_id)
            if channel.upper()=="VOICEBOT":
                logger.info(f"[{count}] Sent {channel} message for phone_number:{campaign_data.get('mobile_number')}, campaign_id:{campaign_data.get('campaign_id')}, lead_id:{campaign_users.get('lead_id')}")
                # send_voice_campaign_message(campaign_user_data.get("mobile_number"),campaign_user_data,campaign_details_data,VOICE_CAMPAIGN_BASE_URL)
                # TODO call nikit task for voice
                pass

            processed_users.append(campaign_users[0].get("lead_id"))
    
        logger.info(f"Finished processing {len(processed_users or [])} users for campaign_id={campaign_id}, channel={channel}")
        return processed_users

    def get_dyanamic_provider_creds(self,enterprise_id,sender,campaign_details):
        logger.info("Loading Dyanamic Provider creds")
        AUTH = AuthManager(campaign_details.get("whatsapp_provider"))
        whatsapp_cred_details= AUTH.get_headers(sender, enterprise_id,complete_data=True)
        logger.debug(f"whatsapp_cred_details:: {whatsapp_cred_details}, {type(whatsapp_cred_details)}")
        whatsapp_credential, whatsapp_provider = whatsapp_cred_details.get("auth_headers"),whatsapp_cred_details.get("whatsapp_provider")
        return whatsapp_credential, whatsapp_provider 

        
    def prepare_campaign_dates(self, campaign_details):
        start_date = campaign_details.get(
            "start_date",
            hp.now(tz=DB_TIMEZONE).strftime("%Y-%m-%d"),
        )
        end_date = campaign_details.get(
            "end_date",
            (hp.now(tz=DB_TIMEZONE) + hp.timedelta(days=7)).strftime("%Y-%m-%d"),
        )
        return start_date, end_date
    
    
    # ============================================================
    # Function: run_custom_campaign
    # Description: Main orchestrator that executes custom campaigns
    #              by fetching users batch-wise from the defined source
    #              and processing them per communication channel.
    # ============================================================

    def run_custom_campaign(
        self, 
        enterprise_id=None,
        campaign_users=[],
        *args, 
        **kwargs
    ):
        """
        Run a custom campaign by fetching users batch-wise and processing them
        according to the specified communication channel.

        This function serves as the main orchestrator for executing campaigns.
        It retrieves users from a configured source (e.g., database or API) in
        batches, then processes each batch depending on the channel type such
        as WhatsApp or Voice.

        Parameters
        ----------
        enterprise_id : str, optional
            The unique identifier of the enterprise. Defaults to `"test1"` if
            not provided.
        campaign : dict, optional
            The overall campaign metadata or configuration dictionary.
        campaign_details_data : dict, optional
            Detailed configuration for the specific campaign execution.
            Expected keys include:
                - `campaign_id` : str
                Unique identifier for the campaign.
                - `campaign_detail_id` : str
                Unique identifier for the campaign detail.
                - `campaign_user_source` : dict
                Configuration details of the user source.
                - `channel` : str
                Communication channel (e.g., `"WHATSAPP_CHAT"`, `"VOICEBOT"`).
        campaign_id : str, optional
            Campaign identifier (used if not specified in `campaign_details_data`).
        campaign_status_check_id : str, optional
            Optional identifier for tracking campaign status.
        *args
            Variable positional arguments (reserved for future use).
        **kwargs
            Additional keyword arguments.
            Supported keys:
                - `_is_testing` : bool, default=False
                If True, runs in test mode without sending messages.

        Returns
        -------
        dict or None
            Returns a dictionary with keys `error` and `error_message` if an
            exception occurs. Returns `None` after successful execution.

        Notes
        -----
        - User data is fetched batch-wise to support large-scale processing.
        - The process halts automatically when no users remain or when a
        stop/error signal is returned from the data source.
        - Extendable for additional channels or custom logic through
        `CampaignSourceFactory` and `process_campaign_users_generic`.

        Examples
        --------
        >>> self.run_custom_campaign(
        ...     enterprise_id="ent_123",
        ...     campaign_id="camp_456",
        ...     campaign_details_data={
        ...         "channel": "WHATSAPP_CHAT",
        ...         "campaign_user_source": {"source_type": "db"}
        ...     }
        ... )
        """

        try:
            # logger.info(f"Campaign details: {json.dumps(kwargs, indent=4, default=str)}")
            logger.info(f"kwargs--{kwargs.get('campaign_id')}")
            # Resolve IDs
            enterprise_id = kwargs.get("enterprise_id") or enterprise_id or "test1"
            campaign_id = kwargs.get("campaign_id") or campaign_id
            logger.info(f'*********[Running Campaign]**************\nCampaign_id: [{campaign_id}]')

            # Load campaign user source
            campaign_user_source = kwargs.get("campaign_user_source", {})
            channel = kwargs.get("channel", "").upper()

            if kwargs.get("retry_failed"):
                if campaign_users and channel in ["WHATSAPP_CHAT", "VOICEBOT"]:
                    self.process_campaign_users_generic(
                        enterprise_id=enterprise_id, 
                        campaign_id=campaign_id, 
                        campaign_users=campaign_users, 
                        **kwargs
                    )
                    return {"info":"Campaign Message sent for Failed user"}



            source = CampaignSourceFactory.create_from_source_json(
                enterprise_id=enterprise_id,
                campaign_details_data=kwargs,
                campaign_user_source=campaign_user_source,
                
            )
            _skip_sent_message = campaign_user_source.get("_skip_sent_message", True)

            batch_no = 1
            while True:
                logger.info(f"Fetching data for batch {batch_no}")
                campaign_users = source.fetch_next_batch()
                # Stop if no users returned or an error/stopped signal
                if not campaign_users or (isinstance(campaign_users, dict) and ("error" in campaign_users or "stopped" in campaign_users or "sucess" in campaign_users)):
                    logger.info(f"Batch fetch ended: {json.dumps(campaign_users, indent=4, default=str)}")
                    break

                logger.info(f"--- Batch {batch_no} --- Fetched {len(campaign_users)} users")
                batch_no += 1

                logger.info(f"campaign_users----{campaign_users}---and channel----{channel}")
                # Process users based on channel
                if campaign_users and channel in ["WHATSAPP_CHAT", "VOICEBOT"]:
                    self.process_campaign_users_generic(
                        enterprise_id=enterprise_id, 
                        campaign_id=campaign_id, 
                        campaign_users=campaign_users, 
                        campaign_data=kwargs
                    )

        except Exception as e:
            hp.print_error()
            logger.error(f"Error while running campaign: {e}")
            return {"error": True, "error_message": str(e)}
@gryd.is_a_task(function_name="async_send_campaign_message")
def async_send_campaign_message(mobile_number: str,lead_id: str,campaign_details: dict,campaign_user_data: dict,enterprise_id: str,*args,**kwargs):
    logger.info("Sending Async Campaign message")
    b=BaseCampaignCreater()
    b.send_campaign_message(mobile_number,lead_id,campaign_details,campaign_user_data,enterprise_id,*args,**kwargs)

@gryd.is_a_task(function_name="async_run_custom_campaign")
def async_run_custom_campaign(*args,**kwargs):
    logger.info("Sending Async Campaign message")
    b=BaseCustomCampaignManager()
    b.run_custom_campaign(*args,**kwargs)
     
# NOTE: Whatever template_variables are present we need to have that user_info 
# Ex- in template_variables = ["customer_name", "model"] then we need to have
# user_info = {"customer_name": "Praveen", "model": "Brezza"}

"""
TODO: check all the TODOs.
post 3 status to contact status for each user with the campaign_id,then we need to also create a id while posting the status.
remove unwanted logs.
test with multiple users.
handle session.
check the fetch_next_batch.
Add proper loggers with time taken.
"""

