#!/usr/bin/python
# -*- coding: utf-8 -*-
from copy import deepcopy as copy
import re
import time
from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
import sys
import json

_root = dirname(dirname(abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

 
# ---
# from communication.connectors.whatsapp_connectors.source_connectors import WhatsappMessangerConnector,WhatsappCampaignTemplate
# from communication.connectors.user_source_connectors.source_connector import CampaignSourceFactory
# from communication.connectors.communication_helpers import AuthManager
# from gryd_worker import gryd,gryd_helpers as hp
# from communication.connectors.communication_configs import DB_TIMEZONE,WA_TO_DISPOSITION
# ---
from communication.connectors.base_connector_communication import *
from campaign.campaign_workflow import determine_campaign_next_action,CHANNEL_IDENTIFIER_MAP
from communication.connectors.communication_helpers import _wait_for_next_minute,get_or_create_person

from gryd_worker import gryd, gryd_db_helper as db, gryd_helpers as hp
from agents.get_whatsapp_template_agent import get_whatsapp_template
from agents.get_email_template_agent import get_email_template
from agents.get_rcs_template_agent import get_rcs_template
from communication.connectors.email_communication import communication_sender
from communication.connectors.connector_rcs import gryd_send_rcs
from conversation.lead_post_processing import update_error_in_lead_and_session
from communication.common_functions import get_communication_credential,generate_uid
from config import AUTOCRM_APP_ENTERPRISE_ID,AUTOCRM_CAMPAIGN_SERVICE_NAME,AUTOCRM_COMMUNICATION_SERVICE_NAME, AUTOCRM_CORE_SERVICE_NAME,AUTOCRM_VOICE_SERVICE_NAME, SERVICE,VOICE_PROVIDER_NAME,EMAIL_PROVIDER_NAME,EMAIL_SENDER_NAME,get_phone_code_from_dealership,AutocrmModel
gryd.SERVICE = AUTOCRM_CAMPAIGN_SERVICE_NAME
gryd.set_queue_manager()
logger = gryd.hp.get_logger(gryd.SERVICE)
def clean_phone_number(phone_number: str) -> str:
    """
    Clean phone number:
    - remove spaces
    - remove special characters
    - keep only digits
    Phone numbers like " +91 98-76 543210 " → "919876543210".
    """
    return re.sub(r"\D", "", str(phone_number))



def update_error_to_models(error_msg,source=None,stack_trace=None,**kwargs):
    logger.info(f"Error occurred in source-{source} and Error message -{error_msg}")
    update_lead_disposition_and_post_billing(kwargs)
    return

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
    
    def _format_mobile_number(self, number: str, country_code: str = "91") -> str:
        number = str(number).strip()
        number = re.sub(r'[^0-9]', '', number)
        number = number.lstrip("0")
        if len(number) <= 10:
            number = country_code + number
        return number

    @staticmethod
    def load_models(campaign_type, logger = None):
    
        model_info = {
            'pre-sales': {
                'lead_model': 'pre_sales_lead',
                'person_model': 'person',
                'campaign_model': 'pre_sales_campaign',
                'rooftop_model': 'showroom',
            },
            'post-sales': {
                'lead_model': 'post_sales_lead',
                'vehicle_model': 'vehicle',
                'person_model': 'person',
                'person_vehicle_model': 'person_vehicle',
                'campaign_model': 'post_sales_campaign',
                'rooftop_model': 'workshop',
            },
            'dealership': {
                'lead_model': 'dealership_lead',
                'campaign_model': 'dealership_campaign',
                'rooftop_model': 'dealership',
            }
        }
        if campaign_type not in model_info:
            raise ValueError(f"Invalid campaign type: {campaign_type}")
        models = {}
        for k, v in model_info[campaign_type].items():
            models[k] = gryd.base_model.Model(v, AUTOCRM_APP_ENTERPRISE_ID)
        return models

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
            logger.info(f"Template type: {template_type}")
            if not template_type:
                logger.error("Template type not found in campaign details")
                return {}

            logger.info(f"WhatsApp provider: {whatsapp_provider}")

            # Generate WhatsApp template payload
            try:
                template_class = WhatsappCampaignTemplate.whatsapp(whatsapp_provider)
                logger.info(f"Template class: {template_class}")
                template_payload = template_class.create_template(
                    campaign_details,
                    params_data=campaign_user_data
                )
                # logger.info(f"Generated template payload: {template_payload}")
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
        
        # logger.info(f"[TESTING RCS] --mobile_number--{mobile_number} campaign_details: {json.dumps(campaign_details,indent=4)} -- campaign_user_data: {json.dumps(campaign_user_data,indent=4)}")
        start_time = time.time()
        channel=campaign_details.get("channel")
        provider_name = campaign_details.get("provider_name")
        sender = campaign_details.get("sender")
        logger.info(
            f"Preparing to send campaign message for lead_id={lead_id}, "
            f"provider={provider_name}, number={mobile_number}"
        )
        patch_user_data={}
        if channel in ["whatsapp", "whatsapp_chat"]:
            country_code=get_phone_code_from_dealership(campaign_details.get("dealership_id"),False)
            mobile_number = self._format_mobile_number(
                mobile_number,
                country_code=campaign_user_data.get("country_code") or country_code
            )
            patch_user_data = {"mobile_number":mobile_number,"template_message":campaign_details.get("template_message",'').format(**campaign_user_data)}
            # logger.info(f"Campaign Message patch_user_data: {patch_user_data}")
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
                    provider_name, *args, **kwargs
                )

                # Send WhatsApp message
                response = provider.send_message_whatsapp(
                    mobile_number, sender, **send_data
                )
                # logger.info(f"Response for campaign user {lead_id}: {response}")

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
                        "whatsapp_provider": provider_name,
                        "provider_name": provider_name,
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
        elif channel == "rcs":
            # logger.info(f"RCS mobile_number----{mobile_number}")
            res=gryd_send_rcs(provider_name,mobile_number,None,campaign_details.get("template_message"))
            
            if(isinstance(res,dict)):
                response=res.get("response",None)
                # logger.info(f"RESPONSE --{response} , response['status'] --{response['status']}")
                success = response["status"]=="error"
                logger.info(f"RESPONSE success --{success}")
                
                patch_user_data["message_status"] = "initiated" if success else "failed"
                patch_user_data["sent_message"] = True if success else False
        else:
            logger.error(
                f"Unsupported channel {channel} for campaign user ID {lead_id}"
            )
        # logger.info(f"CAMPAIGN MESSAGE STATUS-----: {json.dumps(campaign_details,indent=4)} ,campaign_user_data --{json.dumps(campaign_user_data,indent=4)} ")
        msg_status=WA_TO_DISPOSITION.get(patch_user_data.get("message_status"), None)
        if msg_status:
            # logger.info(f"TEST MESSAGE_STATUS ------{msg_status} response--{response}")
            data={
                    "lead_id":lead_id,
                    "enterprise_id":enterprise_id,
                    "campaign_id":campaign_details.get("campaign_id"),
                    "campaign_type":campaign_details.get("campaign_type"),
                    "campaign_model":campaign_details.get("campaign_model"),
                    "phone_number":mobile_number,
                    "dealership_id":campaign_details.get("dealership_id"),
                    "message_id": (response.get("message_id", None) if channel == "whatsapp_chat" else getattr(response.get("response"), "sid", None)),
                    "provider_status":msg_status,
                    "message_template_type": campaign_details.get("message_template_type"),
                    "channel_provider":provider_name,
                    "channel":patch_user_data.get("channel") or channel,
                    "template_message":campaign_details.get("template_message"),
                    "skip_workflow": campaign_details.get("skip_workflow", False)
                }
            
            logger.info(f"Calling post_contact_status with data from campaign: {data}")
            gryd.create_async_task(
                "post_contact_status", 
                AUTOCRM_COMMUNICATION_SERVICE_NAME, 
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
        # logger.info(f"------ process_campaign_users_generic ------ {json.dumps(campaign_data,indent=4)}")
        channel= campaign_data.get("channel").upper()
        # logger.info(f"Starting processing {len(campaign_users)} users for campaign_id={campaign_id}, channel={channel} , campaign_data={json.dumps(campaign_data,indent=4)}")
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
            logger.info(f"CHANNEL ---{channel}")
            if channel.upper()=="WHATSAPP_CHAT":
                country_code=get_phone_code_from_dealership(campaign_data.get("dealership_id"),False)
                mobile_number = BaseCampaignCreater()._format_mobile_number(mobile_number, user.get('country_code') or country_code)
                logger.info(f"mobile_number after formatting-----{ mobile_number}")
            if not mobile_number:
                logger.warning(f"[{count}] User record missing mobile_number: {user}")
                continue

            if user.get("unsubscribe", False):
                logger.info(f"[{count}] User {mobile_number} has unsubscribed. Skipping.")
                continue

            logger.info(f"[{count}] Processing user {mobile_number}")
            
            is_testing = kwargs.pop("_is_testing", False)

            # logger.info(f"process_campaign_users_generic campaign_details---{campaign_data}---campaign_users---{user}")
            
            if channel.upper() in ["WHATSAPP_CHAT","RCS"]:
                logger.info(f"[{count}] Sent {channel} message for {mobile_number}")
                
                logger.info("Checking and creating a session for channel: {channel} and user: {mobile_number}")
                campaign_d={**campaign_data,**user}
                session_data=handle_session_logic(mobile_number,None,channel.lower(),False,campaign_d)
                # logger.info(f"Session logic result in campaign : {json.dumps(session_data,indent=4)}")
                if not session_data:
                    logger.error(f"Failed to create session for channel: {channel} and user: {mobile_number}")
                    continue
                # logger.info(f"Session logic result in campaign : {session_data}")
                user["session_id"]=session_data.get("session_id")
                logger.info(f"Session_id when triggering campaign to the user--{user.get('session_id')} for a campaign_id--{campaign_data.get('campaign_id')}")
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
            elif channel.upper()=="VOICE_PHONE":
                logger.info("Sending Voice campaign---")
                # logger.info(f"[voice_channel] campaign_data--{json.dumps(campaign_data,indent=4)}, campaign_users--{json.dumps(campaign_users[0],indent=4)}")
                d={**campaign_data,**campaign_users[0]}  
                logger.info(f"[{count}] Sent {channel} message for phone_number:{d.get('mobile_number')}, campaign_id:{d.get('campaign_id')}, lead_id:{d.get('lead_id')}")
                              
                # logger.info(f"Voice call payload--{json.dumps(d,indent=4)}")

                voice_service_name = campaign_data.get("voice_service_name") or AUTOCRM_VOICE_SERVICE_NAME

                gryd.create_async_task('trigger_voice_call', voice_service_name, args=[],kwargs={"user_data":d})
            elif channel.upper()=="EMAIL":
                logger.info("Sending Email campaign---")
                # logger.info(f"[email_channel] campaign_data--{json.dumps(campaign_data,indent=4)}, campaign_users--{json.dumps(campaign_users[0],indent=4)}")
                email_p=format_email_payload(campaign_data,campaign_users[0],mobile_number)
                # logger.info(f"email_p--{json.dumps(email_p,indent=4)}")
                communication_sender(**email_p)
            
            else:
                logger.error(f"Unsupported channel: {channel}")
                continue
            processed_users.append(campaign_users[0].get("lead_id"))
    
        logger.info(f"Finished processing {len(processed_users or [])} users for campaign_id={campaign_id}, channel={channel}")
        return processed_users

    def get_dyanamic_provider_creds(self,enterprise_id,sender,campaign_details):
        logger.info("Loading Dyanamic Provider creds")
        AUTH = AuthManager(campaign_details.get("whatsapp_provider"))
        logger.info(f"Dynamic provider creds--{AUTH}, sender--{sender}, enterprise_id--{enterprise_id}")
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
                Communication channel (e.g., `"WHATSAPP_CHAT"`, `"VOICE_PHONE"` , `"EMAIL"`).
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
            # logger.info(f"Campaign iser--{campaign_users}")
            # Resolve IDs
            enterprise_id = kwargs.get("enterprise_id") or enterprise_id or "test1"
            campaign_id = kwargs.get("campaign_id") or campaign_id
            logger.info(f'*********[Running Campaign]**************\nCampaign_id: [{campaign_id}]')
            # logger.info(f"Campaign user source--{kwargs.get('campaign_user_source')}")
            # Load campaign user source
            campaign_user_source = kwargs.get("campaign_user_source", {})
            channel = kwargs.get("channel", "").upper()

            if kwargs.get("retry_failed"):
                if campaign_users and channel in ["WHATSAPP_CHAT", "VOICE_PHONE", "EMAIL", "RCS"]:
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
                if campaign_users and channel in ["WHATSAPP_CHAT", "VOICE_PHONE", "EMAIL", "RCS"]:
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
def trigger_campaign(*args, **kwargs):
    """
    Trigger a campaign for a given campaign type and campaign id.

    if kwargs has 'trigger_now', then it will trigger the calls immediately, otherwise it will schedule it
    """
    
    logger.info("------ Triggering Campaign ------")
    campaign_id=kwargs.get("campaign_id")
    campaign_type=kwargs.get("campaign_type")
    lead_table = "pre_sales_lead" if campaign_type == "pre-sales" else "post_sales_lead"
    lead_table_id="pre_sales_lead_id" if campaign_type == "pre-sales" else "post_sales_lead_id"
    filters = {k: v for k, v in kwargs.items() if v is not None}
    logger.info(f"Filters: {filters}")
    with get_pg_connector() as pg:
        leads = list(pg.list(lead_table, filters))
    lm = AutocrmModel(lead_table)
    logger.info(f"Total leads fetched: {len(leads)}")
    valid_leads = []

    # if the lead_data doesnt have a phone number(pre sales) or persons_involved (post sales), skip it
    for lead in leads:

        if campaign_type == "post-sales":
            persons = []
            for _ in range(2):
                persons = lead.get("persons_involved") or []
                if persons:
                    break
                lead = lm.update(lead.get('post_sales_lead_id'), {})
                    
            if not persons:
                logger.info(f"Skipping post-sales lead (no persons involved): {lead.get('post_sales_lead_id')}")
                continue

        else:  
            if not lead.get("phone_number"):
                logger.info(f"Skipping pre-sales lead (no phone number): {lead.get('pre_sales_lead_id')}")
                continue

        valid_leads.append(lead)

    logger.info(f"Valid leads to process: {len(valid_leads)}")

    for lead in valid_leads:
        
        logger.info(f"Queueing task for lead_id={lead.get(lead_table_id)}")
        # list(process_single_lead(None, lead, campaign_type, campaign_id))
        person = get_or_create_person(lead.get("phone_number"),lead.get("dealership_id"))
        pg.update(lead_table, lead_table_id,lead.get(lead_table_id), {"user_id": person.get("user_id")})
        list(determine_campaign_next_action(campaign_type,lead.get(lead_table_id),call_process_single_lead=kwargs.get('trigger_now', True)))
        
    logger.info("All valid leads queued successfully.")

@gryd.is_a_task(function_name="trigger_queued_campaigns")
def trigger_queued_campaigns(*args, **kwargs):
    campaign_type = kwargs.get("campaign_type")
    lead_table="pre_sales_lead" if campaign_type == "pre-sales" else "post_sales_lead"
    start_timestamp = kwargs.get("start")
    end_timestamp = kwargs.get("end","")
    filters = { "_as_option": True, "disposition": "queued", "created": f"{start_timestamp},{end_timestamp}" }
    filters.update(kwargs.get("additional_filters", {}))

    logger.info(f"Fetching queued leads for campaign_type={campaign_type} with filters: {filters}")

    lead_model = AutocrmModel(lead_table)
    leads = lead_model.list(**filters)

    logger.info(f"Total leads fetched: {len(leads)}, {leads[0] if leads else 'No leads found'}")

    if not kwargs.get("only_list", False):
        for lead in leads:
            try:
                logger.info(f"Queueing task for lead_id={lead.get('lead_id')}")
                list(process_single_lead(None, lead, lead.get("campaign_type"), lead.get("campaign_id")))
            except Exception as e:
                logger.error(f"Error occurred while processing lead {lead.get('lead_id')}: {e}")
                continue

@gryd.is_a_task(function_name="nada_pre_sales")
def nada_pre_sales(*args,**kwargs):
    logger.info(f"------ nada_pre_sales ------")
    channel = kwargs.get("channel")
    session_id = kwargs.get("session_id")
    logger.info(f"Channel: {channel}, session ID: {session_id}")
    dealership_id="us-dealership-united-states"
    campaign_id="4c99d5ea-4441-3ce6-841f-de5d7585b3b7"
    urgency_hook="Book now — slots are filling fast!"
    
    if not session_id and not channel:
        logger.error("Session ID or Channel is required.")
        return
    user_id=None
    with get_pg_connector() as pg:
        # getting the user_id from session_id
        session_data=pg.get("session","session_id",session_id)
        if not session_data:
            logger.error(f"No session found for session_id={session_id}")
            return
        logger.info(f"TEST SESSION DATA--{session_data}")
        user_id=session_data.get("user_id")
        phone_number=session_data.get("phone_number")
        person_name=session_data.get("person_name")
        email=session_data.get("email")
        if not user_id or not phone_number:
            logger.error(f"User ID or Phone number missing in session data for session_id={session_id}")
            return
        lead_id=check_and_create_lead_object(**{
            "channel":channel,
            "session_id":session_id,
            "dealership_id":dealership_id,
            "campaign_id":campaign_id,
            "user_id":user_id,
            "urgency_hook":urgency_hook,
            "phone_number":phone_number,
            "person_name":person_name,
            "email":email
        })
        
        # update the session with lead_id and campaign details
        s=pg.update("session","session_id",session_id,{"lead_id":lead_id,"campaign_id":campaign_id,"dealership_id":dealership_id,"campaign_model":"pre_sales_campaign","campaign_type":"pre-sales","lead_model":"pre_sales_lead"})
        logger.info(f"Session data updated with lead_id={lead_id} for the session_id={session_id}")
        
        # updating the session_data_cache with data:{}
        pg.update("session_data_cache","session_id",session_id,{"data":{}})
        
        # process the lead
        # process_single_lead(channel,lead_id,"pre-sales",campaign_id,user_id)
        gryd.create_async_task(
            "process_single_lead",
            AUTOCRM_CAMPAIGN_SERVICE_NAME,
            args=[channel, lead_id, "pre-sales", campaign_id,"01kga11vdgsmhte5p3jzmh2n73"],
            kwargs={}
        )
        
        logger.info(f"Pre-sales lead processed for lead_id={lead_id}")

def check_or_create_campaign(payload):
    
    
    with get_pg_connector() as pg:
        camp_obj_data=pg.get('campaign_objective', 'campaign_objective_id', payload.get("campaign_objective_id"))
        if not camp_obj_data:
            logger.error(f"Campaign objective not found for ID: {payload.get('campaign_objective_id')}")
            return None

        campaign_model = f"{payload.get('campaign_type', camp_obj_data.get('campaign_type')).lower().replace('-', '_')}_campaign"
        camp_data=list(pg.list(campaign_model,{ "campaign_objective_id": payload.get("campaign_objective_id") , "campaign_status": "Continuous"}))
        
        if camp_data:
            logger.info(f"Campaign found for campaign_objective_id - {payload.get('campaign_objective_id')} and the campaign_id is {camp_data[0].get('campaign_id')} for Continuous campaign status.")
            return camp_data[0]
    m=AutocrmModel(model_name=campaign_model)
    
    a={
        "ctas": [
        ],
        "channels": payload.get("channels",["voice_phone","whatsapp_chat"]),
        "dealership_id": payload.get("dealership_id",""),
        "languages": payload.get("languages",["english"]),
        "campaign_objective_id": payload.get("campaign_objective_id",None),
        "campaign_name": payload.get("campaign_name","test campaign"),
        "campaign_type": payload.get("campaign_type","pre-sales"),
        "end_date": time.time() + 86400,
        "start_date": time.time(),
        "urgency_hook": "",
        "cost_per_lead": 0.0,
        "campaign_offer": "",
        "campaign_status": "Continuous",
        "number_targeted": 0,
        "budget_allocated": 0,
        "campaign_description": camp_obj_data.get("description", ""),
        "campaign_user_source": "auto_generated",
        "target_audience_tags": [
            "book-test-drive",
            "book-your-free-service",
            "free-service-due",
            "purchase-date-less-than-1year",
            "warranty-active",
            "active-customer",
            "low-mileage-vehicle",
            "battery_health_alert",
            "tyre_health_alert",
            "tyre-rotation-due",
            "engine-oil-check",
            "brake_inspection_recommended",
            "suspension_check_recommended",
            "wheel_alignment_recommended",
            "car-washing-recommended"
        ],
        "conversion_rate_percent": 0.0
    }
    
    n=m.post(a)
    payload.update(n)
    return payload
    

@gryd.is_a_task(function_name="manual_register_and_trigger_lead", job_param='job', auth_param='auth', logger_param='logger')
def manual_register_and_trigger_lead(name, phone_number, email=None, *args, **kwargs):
    
    logger.info("------ Manual Register And Trigger Lead ------")
    # 1. Extract Details from kwargs with fallbacks (optional)
    campaign_id = kwargs.get("campaign_id",None)
    dealership_id = kwargs.get("dealership_id")
    campaign_type = kwargs.get("campaign_type", 'pre-sales')
    campaign_objective_id = kwargs.get("campaign_objective_id")
    channel=kwargs.get("channel",["voice_phone"])
    if not campaign_id:
        campaign_data=check_or_create_campaign(kwargs)
        campaign_id=campaign_data.get("campaign_id")
        campaign_type=campaign_data.get("campaign_type")
    

    # Validation check to ensure required params are present
    if not all([campaign_id, dealership_id, campaign_objective_id]):
        error_msg = f"Missing required kwargs. Got: campaign_id={campaign_id}, dealership_id={dealership_id}"
        logger.error(error_msg)
        yield {"_error": error_msg}
        return

    # 2. Load Models
    models = BaseCampaignCreater.load_models(campaign_type)
    lead_model = models.get('lead_model')

    # 3. Construct Data Dictionary
    row = {
        "person_name": name,
        "phone_number": phone_number,
        "email": email,
        "campaign_id": campaign_id,
        "dealership_id": dealership_id,
        "campaign_objective_id": campaign_objective_id,
        **kwargs
    }
    logger.info(f"Constructed row for manual registration: {row}")
    # 4. Construct Final Data Payload
    allowed_keys = [
        "phone_number", "email", "person_name", "campaign_id", "dealership_id", 
        "campaign_objective_id", "last_contacted_whatsapp_number", "last_contacted_email", 
        "last_contacted_phone_number", "brand_preference", "model_preference", 
        "variant_preference", "color_preference", "engine_type_preference", 
        "transmission_preference", "range_preference", "feature_preferences", 
        "segment_preference", "competitor_brands", "competitor_models", "emotions", 
        "engagement_events", "previous_interaction_ids", "lead_tags", 
        "interested_vehicle_competitor_vehicles"
    ]
    
    data = {k: row.get(k) for k in allowed_keys if row.get(k) is not None}

    try:
        logger.info(f"Posting {data}")
        # 1. Post the lead to the model
        lead = lead_model.post(data)
        
        if not lead:
            raise ValueError("Lead model post returned empty result.")

        # 2. KEY MAPPING
        if not lead.get('lead_id'):
            lead['lead_id'] = lead.get('pre_sales_lead_id') or lead.get('id')

        actual_id = lead.get('lead_id')
        lead_table = "pre_sales_lead" if campaign_type == "pre-sales" else "post_sales_lead"
        lead_table_id="pre_sales_lead_id" if campaign_type == "pre-sales" else "post_sales_lead_id"
        logger.info(f"Triggering campaign for lead_id: {actual_id}, campaign_id:{campaign_id}, person: {name}")

        # 3. Trigger Campaign
        # Note: Using campaign_id and campaign_type extracted from kwargs
        gryd.create_async_task(
            "process_single_lead",
            AUTOCRM_CAMPAIGN_SERVICE_NAME,
            args=[channel[0], lead, campaign_type, campaign_id],
            kwargs={
                "templateID": kwargs.get("template_id",None),
                "image_url":kwargs.get("url",None),
                "custom_template_variables": kwargs.get("custom_template_variables", None),
                "skip_workflow": kwargs.get("skip_workflow", False)
            }
        )
        
        # with get_pg_connector() as pg:
        #     person = get_or_create_person(lead.get("phone_number"),lead.get("dealership_id"))
        #     pg.update(lead_table, lead_table_id,lead.get(lead_table_id), {"user_id": person.get("user_id")})
        
        
        # logger.info(f"kwargs--{kwargs.get('template_id')}")
        # list(determine_campaign_next_action(campaign_type,lead.get(lead_table_id),channel[0],phone_number,call_process_single_lead=True,templateID=kwargs.get("template_id",None),image_url=kwargs.get("url",None)))

        yield {"_result": {
            "status": "success",
            "lead_id": actual_id,
            "message": f"Lead created for {name} and campaign triggered."
        }}

    except Exception as e:
        logger.error(f"Manual registration/trigger failed: {str(e)}")
        yield {"_error": f"Failed to process manual entry: {str(e)}"}
        raise


def check_and_create_lead_object(**kwargs):
    dealership_id=kwargs.get("dealership_id")
    campaign_id=kwargs.get("campaign_id")
    user_id=kwargs.get("user_id")
    urgency_hook=kwargs.get("urgency_hook")
    with get_pg_connector() as pg:
        existing_leads=list(pg.list("pre_sales_lead",{"campaign_id":campaign_id,"user_id":user_id}))
        if existing_leads:
            logger.info(f"Lead already exists for campaign_id={campaign_id}, user_id={user_id}")
            return existing_leads[0].get("pre_sales_lead_id")
        logger.info(f"TEST USER ID--{user_id} and campaign_id--{campaign_id}")
        lead_data={
            "ctas": [
                "Book a Test Drive",
                "Request a Callback"
            ],
            "created": time.time(),
            "updated": time.time(),
            "lead_tags": [
                "test-drive-booking",
                "book-test-drive"
            ],
            "region_id": "united-states",
            "campaign_id": campaign_id,
            "user_id": user_id,
            "person_name": kwargs.get("person_name"),
            "email": kwargs.get("email"),
            "dealer_name": "us dealership",
            "disposition": "queued",
            "region_name": "United states",
            "workshop_id": "None",
            "phone_number": kwargs.get("phone_number"),
            "urgency_hook": urgency_hook,
            "audience_name": "us test",
            "campaign_name": "Mustang Test Drive ",
            "campaign_type": "pre-sales",
            "dealership_id": dealership_id,
            "campaign_offer": "Don't miss your chance to drive the legendary Mustang! Schedule your test drive now and discover what makes this car a true classic. Limited slots available!",
            "finance_required": False,
            "supported_brands": [
                "ford-united-states",
                "toyota-usa-united-states",
                "chevrolet-united-states",
                "general-motors-truck-company-united-states",
                "hyundai-motor-america-united-states"
            ],
            "vehicle_category": "Passenger Vehicle",
            "campaign_sub_type": "other",
            "conversation_tone": "Be on-point, warm, confident, polite, conversational, and very crisp - like a friendly local representative. Avoid being pushy or overly sales oriented. Incorporate natural conversational elements like brief affirmations to maintain engagement. End every conversation politely, with warmth and gratitude. Speak at a medium pace, easy to follow, with positive, empathetic, and reassuring emotion (not robotic).",
            "pre_sales_lead_id": "vandana-8401586512-us-dealership-united-states-4c99d5ea-4441-3ce6-841f-de5d7585b3b7",
            "campaign_description": "Don't miss your chance to drive the legendary Mustang! Schedule your test drive now and discover what makes this car a true classic. Limited slots available!",
            "campaign_objective_id": "pre-sales-test-drive-booking",
            "dealership_guidelines": "- This dealership sells vehicles only from the following brands: Ford, Toyota, Chevrolet, GMC and Hyundai.You must answer questions strictly using the vehicle information provided to you for these brands only.\n -Do not provide information about any other brands or manufacturers.\n -If a user asks about a vehicle, feature, or specification that is not available in the provided data, respond politely that you do not have that information at the moment. \n -Do not guess, assume, or fabricate details.\n -Keep responses clear, professional, and customer-friendly, suitable for a dealership environment.\n -When possible, highlight features and details that are important to American car buyers  such as performance, engines, safety, technology, comfort, towing, trims, etc. \n - The Ford F-150 is America's best-selling full-size pickup known for its broad engine lineup, rugged capability, advanced tech, and trim-by-trim versatility: base trims like XL and STX offer practical work-ready features with a 2.7 L EcoBoost V6 (approximately 325 hp, 400 lb-ft) and a smooth 10-speed automatic transmission, while mid-range trims such as XLT and Lariat step up with options like a 5.0 L Ti-VCT V8 (approximately 400 hp, 410 lb-ft) or 3.5 L EcoBoost V6 (approximately 400 hp, 500 lb-ft) and available hybrid PowerBoost powertrain (approximately 430 hp, 570 lb-ft) for strong everyday performance and excellent towing; top-end models like King Ranch, Platinum, Tremor, Raptor, and Raptor R bring luxury, off-road hardware, and high-output engines up to a supercharged 5.2 L V8 with 720 hp on Raptor R. The F-150's capability is class-leading: when properly equipped it can tow up to around 13 500 lbs and haul hefty payloads (approximately 2 440 lbs), with advanced trailer tech such as Pro Trailer Backup Assist and Pro Trailer Hitch Assist to make towing easier. Turning circle figures are competitive for a full-size truck (about 47.8 ft/41.2 ft diameter, varying by configuration) and the truck offers multiple drive modes (Normal, Eco, Sport, Tow/Haul, plus terrain modes on 4X4 or off-road trims) to tailor performance. Tech highlights across the lineup include SYNC 4 infotainment with large touchscreens and wireless Apple CarPlay/Android Auto, over-the-air updates, Ford Co-Pilot360 safety suite, available BlueCruise hands-free highway driving, and Pro Power Onboard generators for job-site or camping power. Trim choices let buyers prioritize value and utility (XL/STX), balanced comfort and capability (XLT/Lariat), premium appointments (King Ranch/Platinum) or serious off-road performance (Tremor/Raptor) all with a smooth 10-speed automatic and strong torque delivery suited to American truck buyers.\n - The Ford Mustang remains an iconic American sports car with a lineup tailored to different performance tastes, combining classic rear-wheel-drive dynamics with modern powertrains and tech: base EcoBoost trims use a turbocharged 2.3 L EcoBoost I-4 making about 315 hp and 350 lb-ft of torque paired with a 10-speed automatic transmission for quick, efficient acceleration and everyday usability; GT models step up to the naturally aspirated 5.0 L Coyote V8 delivering around 480-486 hp and 415-418 lb-ft torque with a 6-speed manual (with rev-matching) or optional 10-speed automatic for classic muscle car feel and strong mid-range pull; and the performance-focused Dark Horse variant boosts that V8 to around 500 hp with 418 lb-ft, reinforced drivetrain components, upgraded suspension and brakes for track-ready capability. All variants use a limited-slip differential and rear-wheel drive to maximize traction, and while official turning radius figures for the latest Mustang aren't widely published, prior models typically had an 18-20 ft curb-to-curb turning radius, making U-turns typical for a long-wheelbase coupe. Technical specs emphasize spirited performance (0-60 times vary strongly by trim and conditions) and handling balance with available MagneRide adaptive dampers on higher trims, plus classic muscle-car exhaust notes and optional performance packages that include enhanced cooling, larger brakes, and torque-vectoring tech. Inside, Mustangs come with modern infotainment, digital instrument displays, driver assistance features, selectable drive modes (including Track, Sport, Normal), and options like launch control; trims typically include EcoBoost, EcoBoost Premium, GT, GT Premium, Dark Horse and convertible options within each for buyers prioritizing everything from daily driving and fuel economy to high-performance track use. \n - The Ford Explorer is a versatile, three-row midsize SUV that appeals to American buyers looking for strong performance, family-friendly practicality, and modern tech: it offers a standard 2.3 L EcoBoost turbocharged inline-4 engine producing about 300 hp and 310 lb-ft of torque and an available 3.0 L EcoBoost twin-turbo V6 with around 400 hp and 415 lb-ft of torque on higher trims (both paired with a smooth 10-speed automatic transmission and available rear-wheel-drive or Intelligent 4WD) for confident highway merging and towing; the Explorer can tow up to around 5,000 lbs with the standard Class III Trailer Tow Package. Trims span six main variants — Active 100A (entry-level), Active, ST-Line (sportier styling), Tremor (off-road-ready with all-terrain hardware), Platinum (luxury-oriented), and ST (performance SUV with sport-tuned suspension) - letting buyers emphasize value, capability, comfort, or performance. All models include a selectable drive mode system with Normal, Eco, Sport, Tow/Haul, Slippery, Trail/Off-Road settings to suit conditions, and a modern tech suite with the Ford Digital Experience's large touchscreen, digital gauge cluster, wireless Apple CarPlay/Android Auto, and advanced safety aids (Ford Co-Pilot360). Standard features grow with trim level to include premium audio, heated/ventilated seats, panoramic roof, and hands-free BlueCruise highway driving on higher trims. While official current turning radius figures aren't broadly published by Ford, typical midsize SUV turning circles are competitive for city driving and U-turns. With three rows of seating, generous cargo space and comprehensive driver assistance, the Explorer blends daily usability with strong powertrain choices and customizable trim-by-trim features for a range of American SUV buyers.\n - The Chevrolet Silverado 1500 is a full-size American pickup that blends power, capability, modern tech, and a range of trims to suit work-oriented and lifestyle buyers alike: under the hood buyers can choose from four main engines — a 2.7 L TurboMax turbo-4 with about 310 hp and 430 lb-ft of torque paired to an 8-speed automatic, a traditional 5.3 L EcoTec3 V8 making 355 hp and 383 lb-ft with a 10-speed automatic, a 6.2 L EcoTec3 V8 delivering 420 hp and 460 lb-ft also with a 10-speed, and a 3.0 L Duramax turbo-diesel I6 that offers 305 hp and a strong 495 lb-ft torque figure for excellent towing and fuel economy trade-offs - all designed for strong towing and hauling across configurations. The Silverado's trims range from WT (Work Truck), Custom, LT, RST, Trail Boss and off-road-focused ZR2, up to premium LTZ and High Country, giving customers choices from basic work-ready trucks to rugged off-road builds and luxury-oriented models with advanced comfort and tech features such as large infotainment screens, advanced driver assists, and optional equipment like bed organizers or Multi-Flex tailgate hardware. On the technical side, the Silverado pairs these engines with rear-wheel drive or available four-wheel drive, offers competitive towing capacity up to around 13 000+ lbs depending on configuration, and while exact current turning radius isn't broadly published, recent 1500 models have turning diameters that are typical for full-size pickups (longer wheelbases generally mean wider turns). With its combination of flexible powertrains, robust torque delivery, smooth automatic transmissions, and a broad lineup of trims to match performance, utility, off-road ability and refinement, the Silverado 1500 remains a strong choice for American truck buyers seeking capability and choice.\n - The Chevrolet Equinox is a compact SUV that blends efficient performance, practical utility, modern tech, and broad appeal for American buyers; it is powered by a turbocharged 1.5 L four-cylinder engine producing about 175 hp and 184 lb-ft of torque in front-wheel-drive models and up to around 203 lb-ft with all-wheel drive, paired with a continuously variable transmission (CVT) for FWD or an available 8-speed automatic for AWD for smooth daily driving and responsive power delivery. Key trims include LT (value-oriented), RS (sport-inspired styling), and ACTIV (rugged look with all-terrain capability), each offered with FWD or AWD to suit different preferences and weather conditions, and all trims come with Chevy Safety Assist active safety tech and a large 11.3-inch infotainment display with wireless Apple CarPlay and Android Auto to keep drivers connected. The Equinox delivers competitive cargo space and passenger room with a turning diameter around 37.1 ft (curb-to-curb) for easy maneuvering in urban and suburban environments, and while towing capacity is modest (around 1,500 lbs max with AWD), it covers most everyday needs. Amenities vary by trim from heated seats, driver-assist features and upgraded interior materials on RS and ACTIV, to rugged exterior cues and all-terrain tires on ACTIV, making the Equinox appealing for buyers prioritizing efficiency, safety, comfort, and a versatile compact SUV package. \n - The Chevrolet Traverse is a three-row midsize SUV that appeals to American buyers seeking spacious family-oriented practicality, strong performance, and modern tech: it's powered by a turbocharged 2.5 L inline-4 engine producing around 328 hp and 326 lb-ft of torque paired with an 8-speed automatic transmission, with front-wheel drive standard and available all-wheel drive for added capability; this setup delivers confident highway merging, respectable fuel economy (around 20-27 mpg city/highway depending on drivetrain), and a towing capacity up to about 5,000 lbs for trailers or boats. Key trims include LT (well-equipped core model), Z71 (adds rugged styling and advanced AWD hardware), RS (sport-inspired design), and High Country (top-tier luxury features and available advanced tech), each offering seating for up to 7-8 passengers, ample cargo room and family-friendly features. The Traverse's turning radius is around 5.9 m (about 19.5 ft), making it reasonably maneuverable for a larger SUV, and it packs practical dimensions with a long wheelbase (~121 in) for stable handling. Technology highlights include a large touchscreen with Apple CarPlay/Android Auto, wireless phone charging, multiple USB-C ports, advanced safety systems, and available premium touches like Super Cruise hands-free highway driving on higher trims. With its blend of powerful turbo engine, smooth automatic transmission, versatile trims from practical to premium, and useful family-centric features, the Traverse is a strong choice in the midsize SUV segment. \n - The Toyota RAV4 is a complete redesign for the U.S. market and now comes standard with hybrid powertrains (no conventional gas-only engine), blending efficiency, technology, utility, and safety in a compact SUV package that appeals to American buyers. Powertrain options include a 2.5-liter four-cylinder hybrid engine paired with electric motors delivering about 226 hp in front-wheel-drive form or 236 hp with AWD, coupled to an e-CVT transmission for smooth, efficient operation; a plug-in hybrid (PHEV) variant boosts output to around 320 hp with a ~50 mile electric-only range and all-wheel drive across the board. The RAV4 offers respectable torque from its hybrid system (with around 163 lb-ft from the 2.5L engine plus additional electric motor torque) and a turning radius around 5.6 m (18.5 ft) that contributes to easy maneuverability in urban environments. Dimensions strike a practical balance with roughly 181 in length, ~105.9 in wheelbase, and ample cargo/passenger space, while towing capacity ranges from around 1,750 lbs on base models up to 3,500 lbs when properly equipped on select AWD trims. Standard tech includes a large infotainment touchscreen with wireless Apple CarPlay/Android Auto, Toyota Safety Sense advanced driver-assistance suite, and optional features like wireless charging and premium JBL audio; comfort/convenience features expand with higher trims. In the U.S., the RAV4 is offered in trims such as LE, SE, XLE, XLE Premium, Woodland, XSE, Limited (plus higher-end or performance-oriented PHEV/Rugged/Sport variants), giving buyers a broad range of capability and feature content to match lifestyle and budget needs. \n - The Toyota Tacoma is a highly capable, mid-size pickup engineered for American buyers who want a blend of everyday practicality, strong performance and serious off-road ability: it's built on Toyota's TNGA-F body-on-frame platform and offers two main powertrains - a 2.4-liter i-FORCE turbocharged four-cylinder gasoline engine that delivers up to about 278 hp and 317 lb-ft of torque (with 228 hp/243 lb-ft on the base SR) paired with an 8-speed automatic or available 6-speed intelligent manual transmission, and an i-FORCE MAX hybrid 2.4L turbo with integrated electric motor producing around 326 hp and 465 lb-ft, both optimized for towing, daily driving and trail duty. The Tacoma can tow up to roughly 6,500 lbs when properly equipped and hauls a hefty payload, while its turning radius/minimum circle is around 6.8 m (≈22.2 ft), aiding maneuverability in parking and tight trails. The truck's rugged capability is backed by features like full-time or part-time 4WD systems, multi-terrain select, crawl control and locking differentials on off-road trims, plus Toyota Safety Sense 3.0 with advanced driver aids. Dimensionally the Tacoma has a wheelbase around 131.9 in and typical midsize pickup proportions with a 5-seat cabin and bed options; ground clearance and suspension tune vary by trim. In the U.S. lineup, Tacoma is available across many trims to match different needs and budgets, including SR, SR5, TRD PreRunner, TRD Sport, TRD Off-Road, Limited, Trailhunter and TRD Pro - with i-FORCE MAX hybrid versions offered on select higher and off-road-oriented models - each adding various comfort, tech and capability upgrades such as larger touchscreens, premium audio, adaptive suspension, ARB gear, FOX or Bilstein shocks, and off-road protection. \n - The Toyota Grand Highlander is a three-row, family-oriented SUV that blends spacious interior comfort with versatile performance and modern tech tailored for American buyers: it offers three powertrain choices - a 2.4-liter turbocharged four-cylinder gasoline engine (≈265 hp, 310 lb-ft torque, 8-speed automatic), a 2.5-liter hybrid (≈245 hp with excellent fuel economy), and a 2.4-liter Turbo Hybrid MAX (≈362 hp and ~400 lb-ft torque with a 6-speed automatic), all available with front-wheel drive or all-wheel drive depending on grade. These powertrains provide a balance of everyday responsiveness, towing capability (up to ~5,000 lbs on gas and Hybrid MAX, ~3,500 lbs on hybrid), and efficiency, with EPA combined mpg in the mid-30s on hybrid trims. Standard and available features include Toyota Safety Sense 3.0 advanced driver-assistance, a 12.3-inch touchscreen with wireless Apple CarPlay/Android Auto, three-zone climate control, multiple USB-C ports, digital key, head-up display, panoramic roof, and premium JBL audio on higher trims. Its adult-sized third row and up to ~97.5 cu ft of cargo space (seats folded) support family hauling and road trips. While official turning radius figures aren't widely published, its 3-row SUV footprint (~201 in length, ~116 in wheelbase) yields typical midsize SUV maneuverability. The U.S. lineup includes LE, XLE, Limited, Hybrid Nightshade, and Platinum trims — with both gas and hybrid powertrains across many grades (Hybrid MAX generally on Limited and Platinum) — giving buyers options from efficient family transport to performance-oriented comfort and tech-rich luxury. \n - The GMC Sierra 1500 is positioned as a full-size American truck blending capability, tech, comfort and towing strength: it's offered in a broad range of trims from Pro, SLE, Elevation, SLT, AT4, AT4X, Denali and Denali Ultimate with varying levels of comfort, off-road gear and luxury amenities (from basic work-oriented features up through premium leather seats, adaptive cruise, Super Cruise hands-free driving and advanced cameras) to suit different buyers' needs. Powertrain options include a base 2.7L TurboMax 4-cyl (≈310 hp and 430 lb-ft torque with an 8-speed automatic), a 5.3L EcoTec3 V8 (~355 hp/383 lb-ft), an optional 6.2L V8 (~420 hp/460 lb-ft) and an available 3.0L Duramax Turbo-Diesel I-6 (~305 hp/495 lb-ft), all paired to GM's smooth automatic transmissions (8-speed or 10-speed depending on engine), delivering robust torque for towing and hauling. Towing and hauling are strong points: depending on configuration and engine the Sierra can tow up to around 13,300 lbs when properly equipped and carry nearly 2,200 lbs of payload, with advanced ProGrade trailering systems and up to 14 camera views to assist hitching and maneuvering. Standard tech includes a large infotainment touchscreen, digital driver displays, wireless Apple CarPlay/Android Auto, premium audio options on higher trims, and safety features like lane-keep assist, automatic emergency braking and more. While official turning radius specs vary by cab and drivetrain setup and aren't always publicly highlighted, the Sierra is designed to balance full-size truck capability with reasonable maneuverability. Heavy-duty Sierra 2500/3500 models with larger gas/diesel V-8s and Allison 10-speed automatics are also available for customers needing more commercial-grade performance. Additionally, GMC offers an EV Sierra lineup with battery range options and unique trims (Elevation, AT4, Denali) featuring dual electric motors, substantial power, long range and advanced off-road modes for buyers interested in an electrified truck experience. \n - The GMC Yukon & Yukon XL are large American-style, three-row full-size SUVs built for families, towing and highway comfort, offered in multiple trim levels - Elevation (entry), AT4 and AT4 Ultimate (off-road oriented), and Denali and Denali Ultimate (luxury premium) — with sophisticated interiors, advanced infotainment, and safety tech including large touchscreens, digital driver displays, available Super Cruise hands-free driving, and premium audio options on upper trims. Power comes from three engines across the lineup: a 5.3 L V8 (~355 hp and 383 lb-ft torque), a 6.2 L V8 (~420 hp and 460 lb-ft), and an available 3.0 L Turbo-Diesel I-6 (~305 hp and 495 lb-ft) — all paired to a 10-speed automatic transmission with rear-wheel-drive standard on some trims and 4WD/AWD available or standard on rugged versions. These SUVs are engineered for heavy-duty tasks, with maximum towing up to about 8,400 lbs depending on engine, drivetrain and configuration, and substantial passenger/cargo volumes suitable for long trips or hauling gear. The turning diameter/radius is around 39.5 ft curb to curb (≈~19.75 ft radius), reflecting the vehicle's size while still enabling reasonable maneuverability for its class. Between the standard and available features are advanced driver assists, adaptive air ride suspension on higher trims, Magnetic Ride Control on off-road AT4 models, premium leather seating, panoramic sunroof options, multiple camera views and towing aids, and distinct styling and comfort levels that let buyers choose from capable everyday-use models to highly equipped luxury versions in both Yukon and longer-wheelbase Yukon XL variants. \n - The GMC Terrain is a compact American-market SUV built for daily driving, efficiency and a good mix of tech and utility, offered in three main trims — Elevation, AT4 (off-road-oriented), and Denali (luxury) — with distinctive styling and feature sets to match varying buyer preferences. All 2026 Terrains are powered by a 1.5-liter turbocharged 4-cylinder engine producing around 175 hp with torque figures of 184 lb-ft on FWD and up to 203 lb-ft on AWD models; front-drive layouts use a CVT (continuously variable transmission) while AWD versions get an 8-speed automatic for smoother power delivery and better traction. The Terrain's compact footprint (~181 in length) yields a turning diameter of about 37.1 ft (~18.55 ft radius), helping maneuverability in urban settings, and it can tow up to ~1,500 lbs when properly equipped. Inside, buyers get a 15″ infotainment touchscreen, 11″ driver display, wireless Apple CarPlay/Android Auto, and advanced safety tech such as blind-spot monitoring, lane-keeping assist, adaptive cruise and automatic emergency braking across trims, with AT4 adding rugged styling and small off-road aids and Denali bringing premium leather, heated/ventilated seats, panoramic sunroof and upgraded audio. Fuel economy is competitive for the class (~25-28 mpg combined), and cargo space is generous with up to ~63.5 cu ft with rear seats folded, making the Terrain a versatile choice for families, commuters and weekend adventurers alike. \n - Hyundai Tucson tailored for an American customer, covering the key parameters you'd typically ask about: The Tucson is a compact 5-seat SUV available in multiple trims including SE, SEL, XRT, SEL Premium and Limited for the gasoline model, plus several Hybrid trims (Hybrid Blue SE AWD, Hybrid SEL, Hybrid SEL Convenience and Hybrid Limited AWD) with Front-Wheel or All-Wheel Drive options, offering a range of equipment and price points to suit different needs. The standard engine on most gas models is a 2.5 L naturally aspirated inline-4 producing about 187 hp and 178 lb-ft of torque paired with an 8-speed automatic transmission (with dual shift mode), delivering around 25-33 mpg on EPA ratings depending on trim and drive type; Hybrid variants use a 1.6 L turbocharged gas engine with electric assist for about 231 hp and ~195 lb-ft, improving efficiency and low-end torque with a 6-speed automatic hybrid transmission. Performance-oriented plug-in hybrid versions (where available) can push higher outputs (~268 hp) while keeping a respectable turning radius of about 5.9 m (19.3 ft) for easy maneuvering. Technical dimensions include a wheelbase ~108.5 in, overall length ~182.7 in, cargo capacity of roughly 38.7-39 cu ft behind the rear seats (expandable with seats folded), and towing capability up to ~2,750 lbs on the gas model and around ~2,000 lbs on hybrid variants. Standard features across trims typically include a suite of safety tech (Hyundai SmartSense with lane-keeping, blind-spot warnings, adaptive cruise), touchscreen infotainment with Apple CarPlay/Android Auto, Bluetooth, and available upgrades like larger screens, panoramic sunroof, premium audio and advanced driver assists, backed by Hyundai's typical 5-year/60,000-mile basic warranty \n The Hyundai Elantra is a compact sedan that appeals to American buyers with a range of trim levels and powertrain options, solid fuel economy, modern tech, and safety features in a value-oriented package. In the standard gas-powered lineup you'll find trims like SE, SEL Sport, SEL Sport Premium, and Limited, all powered by a 2.0-liter naturally aspirated I-4 engine producing about 147 hp and 132 lb-ft of torque paired with an Intelligent Variable Transmission (CVT/IVT) driving the front wheels, delivering strong efficiency (roughly 31 city / 40 hwy / 35 combined MPG EPA) and a turning radius around 5.4 m (17.7 ft) for easy maneuverability; this version seats five and offers comfortable interior space with roughly 99-100 cu ft of passenger volume and ~14 cu ft of trunk space. For buyers craving more performance there's the Elantra N Line, which uses a 1.6-liter turbocharged I-4 with about 201 hp and improved torque and handling via a 7-speed dual-clutch automatic transmission, sport-tuned suspension and unique styling cues. Additionally, hybrid variants (such as Blue, SEL Sport and Limited trims) combine a 1.6 L engine with an electric motor for a ~139 hp combined output with higher efficiency and use a 6-speed eco dual-clutch automatic. Across the lineup you'll find a host of technology and safety features including Hyundai SmartSense driver-assist systems (like forward collision warning, blind-spot assist and lane keep assist), wireless Apple CarPlay/Android Auto, touchscreen infotainment (8″ standard, larger available), Bluetooth, multiple USB ports, available Bose premium audio, heated seats and more, plus Hyundai's 5-year/60,000-mile basic warranty. Overall, the Elantra balances practicality, safety tech, and efficiency with options that range from efficient daily commuting to sportier driving engagement. \n - The Hyundai Santa Fe is a midsize SUV that appeals to American buyers with a broad range of trims and powertrain options designed for practicality, comfort, and capability: trims include SE, SEL, XRT, Limited and premium Calligraphy, each available with Front-Wheel Drive or optional HTRAC All-Wheel Drive, plus hybrid versions of SE, SEL, Limited and Calligraphy for better efficiency and performance. The standard powertrain on gasoline models is a 2.5-liter turbocharged inline-4 engine producing 277 hp and 311 lb-ft of torque paired with a smooth 8-speed automatic transmission (Hyundai replaced the former dual-clutch unit in 2026 for better reliability) that drives the front wheels or AWD and delivers EPA fuel economy around 20 city/29 hwy mpg; towing capacity with trailer brakes can reach up to 3,500 lbs depending on configuration. Hybrid models use a 1.6 L turbocharged gas engine with electric assist and a 6-speed automatic, making about 231 hp and 195 lb-ft (hybrid) for improved economy and lower emissions while retaining SUV versatility. The Santa Fe offers a turning radius ~18.9-19.0 ft (5.8 m) for maneuverability in tight spaces and a comfortable interior with seating for five, generous passenger volumes, and ample cargo space expandable with the rear seats folded. Standard and available tech includes a touchscreen infotainment system with Apple CarPlay/Android Auto, wireless charging, multiple USB ports, safety features through Hyundai SmartSense (adaptive cruise, lane assist, blind-spot monitoring), heated/ventilated seats, panoramic sunroof, premium audio, and advanced driver aids, backed by Hyundai's 5-year/60,000-mile basic warranty and extended powertrain coverage.",
            "supported_brand_names": {},
            "region_level_guardrails": "- Maintain professional communication standards. Ensure clear communication. Respect regional languages. Provide local language support. Be mindful of potential network issues or poor call quality \n -Trigger calls between 10am to 7pm",
            "region_level_guidelines": "Avoid slang, sarcasm, or culturally sensitive humor. Use polite, respectful, and neutral tone. Prefer simple sentences suitable for Tier-2/Tier-3 customers",
            "why_user_should_avail_this": "Find 1-2 standout features from the vehicle knowledge base that make a strong case for buying this car.If They Mention a Specific Aspect: Talk 1-2 highlights about the aspect and push for test drive. Don't be salesy",
            "supported_brands_guidelines": {},
            "previous_interaction_details": {},
            "reasons_for_non_applicability": "- If the customer has already purchased a vehicle from another brand, you should say, 'Oh okay, congratulations on your new car! Just out of curiosity, what made you go with that brand? Your feedback helps us improve. And if you ever consider another vehicle in the future, feel free to reach out.' \\n - If the customer has already purchased from your brand, you should say, 'That's great to hear! Congratulations on your purchase. Hope you're enjoying the ride. If you ever need any support or have questions about service, feel free to connect with us anytime.' \\n - If the customer says they are no longer interested in buying a car, you should say, 'No problem at all. Can I ask what changed? Just trying to understand so we can serve you better if your plans change in the future. And if you know anyone looking for a vehicle, we'd love to help them out.' \\n - If the customer's contact number is wrong or belongs to someone else, you should say, 'Oh, I see. Sorry for the confusion. Could you help me with the correct contact number for [customer name], or let me know if they're no longer interested so we can update our records?' \\n - If the customer has relocated to a different city or country, you should say, 'Understood. If your new location has our dealership, I can connect you with the team there. Otherwise, I'll update our records. Safe travels, and feel free to reach out if you're ever back in the area.'",
            "campaign_objective_description": "Your goal is to have natural, human-like conversations with customers who have shown interest in the vehicle and guide them smoothly towards booking a test drive. You are also knowledgeable about the vehicle so focuse on giving the customer a smooth and pleasant experience.",
            "reasons_users_may_not_be_interested": "- If the customer says they are busy or asks for a callback later, you should say, 'Sure, I completely understand. When would be a good time to call you back? I just wanted to make sure you don't miss out on the current offers and available test drive slots before they fill up.' \\n - If the customer says they are just browsing or not ready to buy yet, you should say, 'No worries at all! Most of our customers take their time. How about I book a test drive for you? There's no commitment, and it helps you get a real feel of the vehicle. Would this weekend work for you?' \\n - If the customer says the price is too high or out of budget, you should say, 'I understand budget is important. We have some flexible financing options and exchange offers that might work better for you. Can I share those details? It might bring the monthly payment to something more comfortable.' \\n - If the customer is comparing with other brands, you should say, 'That's smart to compare. Many of our customers also looked at competitor. What I can do is share a quick features highlight of vehicle and after-sales benefits, so you have all the info to make the right choice. Would that help?' \\n - If the customer says they want to wait for the next model or year, you should say, 'I get that. Just so you know, the current model has some launch offers and immediate delivery options that the next one might not have. Plus, waiting could mean 6-8 months. But happy to keep you updated on both. What matters most to you - features or timing?' \\n - If the customer mentions they are getting a better deal elsewhere, you should say, 'I appreciate you being upfront. Let me check what we can do to match or improve that offer. Can you share what package they offered? I'd like to see if we can work something out for you.' \\n -If the customer had a bad experience with the brand before, you should say, 'I'm really sorry to hear that. Things have improved a lot, especially in service and support. I'd love the chance to change that impression. How about a test drive and a chat with our service team so you can see the difference yourself?' \\n - If the customer says they need to discuss with family first, you should say, 'Absolutely, that makes sense. Would it help if I sent you a detailed brochure and financing options you can review together? Or would you prefer to bring your family for a test drive so everyone can experience it?' \\n - If the customer is worried about maintenance costs, you should say, 'That's a valid concern. Our vehicles come with a warranty and service packages that keep costs predictable. I can share the exact maintenance schedule and costs upfront, so there are no surprises later.' \\n - If the customer prefers to buy during festival season or year-end, you should say, 'That's a common choice. Just a heads up - current stock and offers might not be available then, and prices could change. But I can note your interest and reach out closer to that time with the best deals. Does that work?' \\n - If the customer recently test drive and didn't like something, you should say, 'Thanks for sharing that feedback. Can you tell me what specifically didn't feel right? Sometimes it's about the variant or settings. I'd like to address that or maybe suggest a different variant that might suit you better.' \\n - If the customer is unsure about which variant to choose, you should say, 'No problem, that's very common. Let me ask you a few quick questions about how you'll use the car - city driving, highway, family size - and I can recommend the variant that fits your needs and budget best.' \\n - If the customer wants to think about it, you should say, 'Of course, take your time. Just so you have all the information, let me send you the brochure, a video walkthrough, and current offers. And I'm here anytime if questions come up. Should I follow up in a couple of days or would you prefer to reach out when ready? \\n - If the customer asks about exchange value for their old vehicle, you should say, 'Sure, I can arrange for our exchange team to evaluate your current vehicle. Can you share the make, model, year, and approximate kms driven? We'll give you the best possible value."
        }
        
        # l = AutocrmModel("pre_sales_lead", logger = logger)
        # l.post(lead_data)
        lead_id=generate_uid(lead_data)
        # logger.info(f"Creating new pre-sales lead with lead_id={lead_id} and lead_data={json.dumps(lead_data,indent=4)}")     
        with get_pg_connector() as pg:
            l=pg.update("pre_sales_lead", "pre_sales_lead_id", lead_id,lead_data)
            lead_d=list(pg.list("pre_sales_lead",{"campaign_id":campaign_id,"user_id":user_id}))
            # logger.info(f"Lead created: {json.dumps(lead_d,indent=4)} with user_id={user_id} and campaign_id={campaign_id}")
            logger.info(f"Pre-sales lead data created -- {lead_d[0].get('pre_sales_lead_id')}")
            return lead_d[0].get("pre_sales_lead_id")
        
 
@gryd.is_a_task(function_name="process_single_lead")
def process_single_lead(channel, lead, campaign_type, campaign_id,templateID=None, user_id=None,disposition_tag=None,disposition_detail_tag=None,channel_identifier=None,image_url=None, custom_template_variables=None,skip_workflow=False):
    
    """
    Process a single lead and send campaign messages for each user.

    Parameters
    ----------
    channel : str
        The channel to use for sending the campaign message.
    lead : dict or str
        The lead data to process. If a dict, it should contain the lead_id and other relevant fields.
    campaign_type : str
        The type of campaign (pre-sales or post-sales).
    campaign_id : str
        The ID of the campaign.
    user_id : str, optional
        The ID of the user to target for post-sales campaigns. If not provided, the first person in the persons_involved list will be targeted.

    Yields
    -------
    dict
        A dictionary containing the status of the campaign and any errors that occurred.
    """
    logger.info("----- In process_single_lead task -----")
    
    provider_name = None
    template_data = None
    sender_name = None
    template_message = None
    buttons = None
    voice_service_name  = None
    
    TEMPLATE_RESOLVERS = {
        "email": get_email_template,
        "whatsapp_chat": get_whatsapp_template,
        "rcs": get_rcs_template,
    }
    
    if campaign_type == "pre-sales":
        campaign_table = "pre_sales_campaign"
        lead_table = "pre_sales_lead"
        lead_id_field = "pre_sales_lead_id"
    else:
        campaign_table = "post_sales_campaign"
        lead_table = "post_sales_lead"
        lead_id_field = "post_sales_lead_id"

    with get_pg_connector() as pg:
        # campaign_details = list(pg.list(campaign_table, {"campaign_id": campaign_id}))
        campaign_details=pg.get(campaign_table,"campaign_id",campaign_id)

    if not campaign_details:
        yield {"status": "Error", "error_description": f"No campaign found for campaign_id={campaign_id}"}
        return
    
    # campaign_details = campaign_details[0]
    campaign_objective_name=campaign_details.get("campaign_objective_name") 
    logger.info(f"campaign_objective_name: {campaign_objective_name}")
    if not campaign_objective_name:
        
        yield {"status": "Error", "error_description": f"No campaign objective name found for campaign_id={campaign_id}"}
        return
    # logger.info(f"Campaign details: {json.dumps(campaign_details,indent=4)}")
    if isinstance(lead, dict):
        lead_data = lead
        lead_id = lead.get(lead_id_field)
    else:
        lead_id = lead
        with get_pg_connector() as pg:
            # result = list(pg.list(lead_table, {lead_id_field: lead_id}))
            result=pg.get(lead_table,lead_id_field,lead_id)
        if not result:
            yield {"status": "Error", "error_description": f"No lead found for {lead_id_field}={lead_id}"}
            return
        lead_data = result

    if not lead_id:
        yield {"status": "Error", "error_description": "Lead ID missing"}
        return

    logger.info(f"Lead found for lead_id={lead_id}")
    if channel_identifier:
        logger.info(f"CHANNEL_IDENTIFIER-----{channel_identifier} for lead_id={lead_id}")
        lead_data["channel_identifier"] = channel_identifier
    if not channel:
        channel = get_channel(lead_data, campaign_details)

    get_template=TEMPLATE_RESOLVERS.get(channel)
    logger.info(f"Template resolver for channel={channel}: {get_template}")
    if channel == "voice_phone":
        provider_name = VOICE_PROVIDER_NAME
        with get_pg_connector() as pg:
            voice_service_name = pg.get("dealership","dealership_id",lead_data.get("dealership_id")).get("voice_service_name")
    elif channel == "email":
        sender_name=EMAIL_SENDER_NAME
        provider_name = EMAIL_PROVIDER_NAME
        try:
            template_data= get_template(
                lead_id=lead_id,
                campaign_type=campaign_type,
                campaign_objective= [campaign_objective_name] or [],
                dealership_id=lead_data.get("dealership_id"),
                lead_info={}
            )
        except Exception as e:
            logger.error(f"Error in get_template for channel email: {str(e)}")
            update_error_to_models(
                error_msg=f"Error in get_template for channel email: {str(e)}",
                source="process_single_lead",
                **{
                    "lead_id": lead_id,
                    "campaign_id": campaign_id,
                    "campaign_type": campaign_type,
                    "channel": channel
                })
            yield {"status": "Error", "error_description": f"Error in get_template: {str(e)}"}
            return
        
        if not template_data:
            yield {"status": "Error", "error_description": f"No template found for lead_id={lead_id}"}
            return
        
        template_data = template_data[0]
        logger.info(f"Template ID for email={channel_identifier}: {template_data.get('template_id')}")
        
        template_vars = template_data.get("template_variables", [])

        email_body = template_data.get("email_body", "")
        email_subject = template_data.get("email_subject", "")

        if template_vars:
            variable_mapping = {
                var: lead_data.get(var, "")
                for var in template_vars
            }

            email_body = render_template(email_body, variable_mapping)
            email_subject = render_template(email_subject, variable_mapping)

        template_data = {
            "subject": email_subject,
            "message": email_body,
            "template_variables": template_vars,
        }

        # logger.info("Template Data: %s", template_data)
    elif channel in ("whatsapp_chat", "sms", "rcs"):
        logger.info(f"channel: {channel}")
        if not templateID:
            try:
                template_data= get_template(
                    lead_id=lead_id,
                    campaign_type=campaign_type,
                    campaign_objective= [campaign_objective_name] or [],
                    dealership_id=lead_data.get("dealership_id"),
                    lead_info={}
                )
                # template_data=testing_whatsapp_template()
                
            except Exception as e:
                logger.error(f"Error in get_template for channel {channel}: {str(e)}")
                update_error_to_models(
                    error_msg=f"Error in get_template: {str(e)}",
                    source="get_template",
                    **{
                        "lead_id": lead_id,
                        "campaign_id": campaign_id,
                        "campaign_type": campaign_type,
                        "channel": channel
                    }
                )
                yield {"status": "Error", "error_description": f"Error in get_template: {str(e)}"}
                return
            
            if not template_data or not isinstance(template_data, list):
                update_error_to_models(
                    error_msg=f"Error in get_template: Invalid template data- {template_data}",
                    source="get_template",
                    **{
                        "lead_id": lead_id,
                        "campaign_id": campaign_id,
                        "campaign_type": campaign_type,
                        "channel": channel
                    }
                )
                yield {"status": "Error", "error_description": f"No template found for lead_id={lead_id}"}
                return
            
            template_data = template_data[0]
            
            # _d=get_communication_credential(dealership_id=lead_data.get("dealership_id"), channel=channel,provider_name=template_data.get("provider_name","rml"))
            _d=get_communication_credential(dealership_id=lead_data.get("dealership_id"), channel=channel)
            logger.info(f"GET COMMUNICATION CREDS-->{_d}, dealership_id: {lead_data.get('dealership_id')}, channel: {channel}")
            if _d:
                sender_name=_d.get("sender")
                
            logger.info(f"Communication Credential found for dealership_id: {lead_data.get('dealership_id')}, channel: {channel} and sender phone_number: {sender_name}")
        else:
            with get_pg_connector() as pg:
                template_details=pg.get("template","template_id",templateID)
                template_data=template_details
        logger.info(f"TEmplate data: {template_data}")
        
        if template_data.get("provider_name")=="Rml":
            template_data["template_type"] = template_data.get("template_type")+"_template"
        logger.info(f"Template ID for phone_number={lead_data.get('phone_number')}: {template_data.get('template_id')}")
    else:
        yield {"status": "Error", "error_description": f"Unsupported channel: {channel}"}
        return

    mobile = lead_data.get("channel_identifier") or lead_data.get("phone_number")
    
    # logger.info(f"Campaign ID: {campaign_id}, Original Mobile: {mobile}")
    customer_name = "Dear NADA Visitor" if campaign_id == "4c99d5ea-4441-3ce6-841f-de5d7585b3b7" and lead_data.get("person_name") is None else lead_data.get("person_name")
    lead_data['person_name']=customer_name
    logger.info(f"Customer Name: {customer_name}")
    if custom_template_variables:
        logger.info(f"Custom Template Variables: {custom_template_variables} being sent in the params.So using it.")
        variable_mapping = get_variable_values(template_data.get("template_variables", []), custom_template_variables) if template_data else {}
    else:
        variable_mapping = get_variable_values(template_data.get("template_variables", []), lead_data) if template_data else {}
    logger.info(f"Variable Mapping: {variable_mapping}")
    campaign_user = {
        "lead_id": lead_id,
        "mobile_number": mobile,
        "customer_name": customer_name,
        "email": lead_data.get("channel_identifier") if channel == "email" else None,
        "lead_model": lead_table,
        "contact_channel": channel,
        "template_id": template_data.get("template_id") if template_data else None,
        "template_details": template_data.get("template_details") if template_data else None,
        **variable_mapping
    }

    buttons = None
    template_message = None

    if template_data:
        template_vars = custom_template_variables if custom_template_variables else template_data.get("template_variables", [])
        render_data = {v: variable_mapping.get(v, "") for v in template_vars}
        template_data["media_url"]= image_url or None
        
        if channel in ("whatsapp_chat", "sms"):
            buttons = template_data.get("buttons")

            template_str = template_data.get("template_message", "")
            template_str = template_str.replace("{{", "{").replace("}}", "}")
            template_message = template_str.format(**render_data)

        elif channel == "rcs":
            template_message = template_data.get("init_message", "").format(**render_data)

    logger.info(f"Template Message: {template_message}")

    if channel == "web_chat":
        yield {
            "placeholder": template_message,
            "buttons": buttons
        }
        return    
    # logger.info(f"TEMPLATE DATA in : {json.dumps(template_data, indent=4)}")
    
    final_payload = {
        **(template_data or {}),
        **campaign_details,
        "enterprise_id": campaign_details.get("enterprise_id"),
        "campaign_id": campaign_details.get("campaign_id"),
        "channel": channel,
        "voice_service_name": voice_service_name,
        "sender": sender_name or (template_data.get("sender") if template_data else None),
        "provider_name": provider_name or (template_data.get("provider_name").lower() if template_data else None),
        "template_message": template_message,
        "skip_workflow": skip_workflow ,
        "campaign_user_source": {
            "source_type": "default",
            "campaign_users": [campaign_user],
            "country_code": lead_data.get("region_id"),
            "field_mapping": {
                "lead_id": "lead_id",
                "mobile_number": "mobile_number",
                "customer_name": "customer_name",
                "template_id": "template_id",
                "template_details": "template_details",
                "lead_model": "lead_model",
                "contact_channel": "contact_channel",
                "reg_num":"reg_num"
            },
            "config": {
                "batch_size": 100,
                "_skip_sent_message": True
            }
        }
    }
    run_async = campaign_details.get("run_async", False)
    is_testing = campaign_details.get("_is_testing", False)
    # logger.info(f"Final payload prepared for campaign_id={campaign_id} and lead_id={lead_id}: {json.dumps(final_payload, indent=4)}")
    if not run_async:
        logger.info("Running campaign in SYNC mode")
        BaseCustomCampaignManager().run_custom_campaign(
            _is_testing=is_testing,
            **final_payload
        )
        yield {"campaign_response": final_payload}
        return

    logger.info("Queueing ASYNC campaign task")
    async_task = gryd.create_async_task(
        "async_run_custom_campaign",
        AUTOCRM_CAMPAIGN_SERVICE_NAME,
        args=[],
        kwargs={"_is_testing": is_testing, **final_payload},
        enterprise_id=campaign_details.get("enterprise_id", "autocrm")
    )

    yield {"task_response": async_task, "campaign_response": final_payload}

def render_template(text: str, variables: dict) -> str:
    if not text:
        return text
    for key, value in variables.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))
    return text

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
    channels = campaign_details.get("channels") or ["whatsapp_chat"]
    if len(channels) > 0:
        return channels[0]

    return "whatsapp_chat"  #fallback


def get_variable_values(template_variables, lead_data, selected_person=None):
    """
    Extract values for template variables from lead_data or selected_person.
    Priority: selected_person → lead_data → None
    """
    # logger.info(f"Template Variables: {template_variables}, Lead Data: {lead_data}, Selected Person: {selected_person}")
    values = {}
    for var in template_variables:
        if selected_person and var in selected_person:
            values[var] = selected_person.get(var)
        else:
            values[var] = lead_data.get(var)
    return values

def format_number(number: str, country_code: str = None, add_plus: str = None, dealership_id = None):
    number = str(number)
    country_code = country_code or get_phone_code_from_dealership(dealership_id, add_plus)
    return BaseCampaignCreater()._format_mobile_number(number, country_code)
    
def format_email_payload(campaign_data,campaign_user,mobile_number):
    """
    Format email payload for communication_sender function.

    Parameters:
    campaign_data (dict): Campaign data object
    campaign_user (dict): Campaign user data object

    Returns:
    dict: Formatted email payload
    """
    
    logger.info(f"MEssage: {campaign_user}")
    final_message=campaign_data.get("message").replace("\n","<br>")
    p={
        "ent_id":AUTOCRM_APP_ENTERPRISE_ID,
        "enterprise_id":AUTOCRM_APP_ENTERPRISE_ID,
        "sender":{
            "name":"info",
            "email": EMAIL_SENDER_NAME or campaign_data.get("sender"),
        },
        "receiver":{
            "emails": ["praveen@iamdave.ai"] if not campaign_user.get("email") else [campaign_user.get("email")]
        },
        "html_string": final_message or campaign_data.get("message"),
        "subject": campaign_data.get("subject"),
        "provider": EMAIL_PROVIDER_NAME or campaign_data.get("provider_name"),
        "files": [
            campaign_data.get("files") or None
            ],
        "lead_data":{
            "lead_id": campaign_user.get("lead_id"),
            "campaign_id": campaign_data.get("campaign_id"),
            "campaign_type":campaign_data.get("campaign_type"),
            "email":campaign_user.get("email"),
            "dealership_id":campaign_data.get("dealership_id"),
            "channel_provider":EMAIL_PROVIDER_NAME,
            "channel":"email" ,
            "campaign_model": "post_sales_campaign" if campaign_data.get("campaign_type")=="post-sales" else "pre_sales_campaign",
            "phone_number": format_number(mobile_number) if mobile_number else None
        }
       
    }
    
    p_filters = {k: v for k, v in p.items() if v not in [None ,[],[None]]}
    
    return p_filters


def testing_whatsapp_template():
    
    # return [
    #     {
    #         "sender": "917795030599",
    #         "status": "approved",
    #         "buttons": [
    #             {
    #                 "text": "Book Test Drive",
    #                 "type": "QUICK_REPLY"
    #             },
    #             {
    #                 "text": "Explore Aircross",
    #                 "type": "QUICK_REPLY"
    #             },
    #             {
    #                 "text": "Request a Call Back",
    #                 "type": "QUICK_REPLY"
    #             }
    #         ],
    #         "channel": "whatsapp_chat",
    #         "created": 1776770802.5813954,
    #         "updated": 1776771015.0534973,
    #         "language": "english",
    #         "dealer_name": "Dave AI",
    #         "region_name": "India",
    #         "search_term": "aircross_confirm_test_drives_for_value_advantage text english pre-sales hi person_name thank you for showing interest in the citroën aircross 🙏 we have a special offer for you ✅ running cost from just ₹0.40 km ✅ additional benefits worth ₹1.15 lakh ⏳ limited stock valid till 30th april only 🚗 book a test drive and experience the aircross for yourself — nothing beats a real drive",
    #         "template_id": "950110724542119",
    #         "campaign_type": "pre-sales",
    #         "dealership_id": "dave-ai-india",
    #         "provider_name": "Rml",
    #         "template_name": "aircross_confirm_test_drives_for_value_advantage",
    #         "template_type": "text",
    #         "template_message": "Hi {{person_name}},\n\nThank you for showing interest in the Citroën Aircross! 🙏\n\nWe have a special offer for you:\n\n✅ Running cost from just ₹0.40/km* \n✅ Additional benefits worth ₹1.15 Lakh ⏳ Limited stock | Valid till 30th April only\n\n🚗 Book a test drive and experience the Aircross for yourself — nothing beats a real drive!\n",
    #         "template_variables": [
    #             "person_name"
    #         ],
    #         "campaign_objective_name": "Aircross- Confirm Test Drive for Value Advantage- WhatsApp",
    #         "template_button_payloads": [
    #             "aircross_confirm_test_drives_for_value_advantage-book_test_drive",
    #             "aircross_confirm_test_drives_for_value_advantage-explore_aircross",
    #             "aircross_confirm_test_drives_for_value_advantage-request_a_call_back"
    #         ],
    #         "communication_credentials_id": "rml-whatsapp_chat-917795030599"
    #     }
    # ]
    
    return "No Template Found"



if  __name__ == "__main__":
   gryd.create_async_task(
       "trigger_queued_campaigns",
       AUTOCRM_CAMPAIGN_SERVICE_NAME,
        args=[],
        kwargs={
          
            "campaign_type": "pre-sales",
            "start": 1776885055
        }
   )

#    trigger_queued_campaigns(
#        campaign_type="pre-sales",
#        start=1777036302,
#        end = 1777420689,
#        only_list = True
#    )


