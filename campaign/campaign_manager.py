#!/usr/bin/python
# -*- coding: utf-8 -*-
from copy import deepcopy as copy
import re
import time
from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
import sys
import json
sys.path.insert(0, dirname(dirname(abspath(__file__))))

# ---
# from communication.connectors.whatsapp_connectors.source_connectors import WhatsappMessangerConnector,WhatsappCampaignTemplate
# from communication.connectors.user_source_connectors.source_connector import CampaignSourceFactory
# from communication.connectors.communication_helpers import AuthManager
# from gryd_worker import gryd,gryd_helpers as hp
# from communication.connectors.communication_configs import DB_TIMEZONE,WA_TO_DISPOSITION
# ---

from communication.connectors.base_connector_communication import *

from communication.connectors.communication_helpers import _wait_for_next_minute,yield_gryd_task_results

from gryd_worker import gryd, gryd_db_helper as db, gryd_helpers as hp
from agents.get_whatsapp_template_agent import get_whatsapp_template
from config import AUTOCRM_CAMPAIGN_SERVICE_NAME,AUTOCRM_COMMUNICATION_SERVICE_NAME,AUTOCRM_VOICE_SERVICE_NAME,VOICE_PROVIDER_NAME,WHATSAPP_PROVIDER_NAME
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
        
        # logger.info(f"CAMPAIGN MESSAGE STATUS-----: {campaign_details} ,campaign_user_data --{campaign_user_data} ")
        msg_status=WA_TO_DISPOSITION.get(patch_user_data.get("message_status"), None)
        if msg_status:
            logger.info(f"TEST MESSAGE_STATUS ------{msg_status} response--{response}")
            data={
                    "lead_id":lead_id,
                    "enterprise_id":enterprise_id,
                    "campaign_id":campaign_details.get("campaign_id"),
                    "campaign_type":campaign_details.get("campaign_type"),
                    "campaign_model":campaign_details.get("campaign_model"),
                    "phone_number":mobile_number,
                    "dealership_id":campaign_details.get("dealership_id"),
                    "message_id":response.get("message_id",None),
                    "provider_status":msg_status,
                    "channel_provider":whatsapp_provider,
                    "channel":"whatsapp_chat",
                }
        
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
            if channel.upper()=="VOICE_PHONE":
                logger.info("Sending Voice campaign---")
                logger.info(f"[{count}] Sent {channel} message for phone_number:{campaign_data.get('mobile_number')}, campaign_id:{campaign_data.get('campaign_id')}, lead_id:{user.get('lead_id')}")
                # logger.info(f"[voice_channel] campaign_data--{json.dumps(campaign_data,indent=4)}, campaign_users--{json.dumps(campaign_users[0],indent=4)}")
                d={**campaign_data,**campaign_users[0]}
                gryd.create_async_task('trigger_voice_call', AUTOCRM_VOICE_SERVICE_NAME, args=[],kwargs={"user_data":d})
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
                Communication channel (e.g., `"WHATSAPP_CHAT"`, `"VOICE_PHONE"`).
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
            # logger.info(f"Campaign user source--{kwargs.get('campaign_user_source')}")
            # Load campaign user source
            campaign_user_source = kwargs.get("campaign_user_source", {})
            channel = kwargs.get("channel", "").upper()

            if kwargs.get("retry_failed"):
                if campaign_users and channel in ["WHATSAPP_CHAT", "VOICE_PHONE"]:
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
                if campaign_users and channel in ["WHATSAPP_CHAT", "VOICE_PHONE"]:
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
    """
    
    logger.info("------ Triggering Campaign ------")
    campaign_id=kwargs.get("campaign_id")
    campaign_type=kwargs.get("campaign_type")
    lead_table = "pre_sales_lead" if campaign_type == "pre-sales" else "post_sales_lead"

    with get_pg_connector() as pg:
        leads = list(pg.list(lead_table, {"campaign_id": campaign_id}))

    logger.info(f"Total leads fetched: {len(leads)}")

    valid_leads = []

    # if the lead_data doesnt have a phone number(pre sales) or persons_involved (post sales), skip it
    for lead in leads:

        if campaign_type == "post-sales":
            persons = lead.get("persons_involved") or []
            if not persons:
                logger.info(f"Skipping post-sales lead (no persons involved): {lead.get('lead_id')}")
                continue

        else:  
            if not lead.get("phone_number"):
                logger.info(f"Skipping pre-sales lead (no phone number): {lead.get('lead_id')}")
                continue

        valid_leads.append(lead)

    logger.info(f"Valid leads to process: {len(valid_leads)}")

    for lead in valid_leads:
        # logger.info(f"Queueing task for lead_id={lead.get('lead_id')}")

        gryd.create_async_task(
            "process_single_lead",
            AUTOCRM_CAMPAIGN_SERVICE_NAME,
            args=[None, lead, campaign_type, campaign_id],
            kwargs={}
        )

    logger.info("All valid leads queued successfully.")


@gryd.is_a_task(function_name="process_single_lead")
def process_single_lead(channel, lead, campaign_type, campaign_id, user_id=None):
    
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

    if campaign_type == "pre-sales":
        campaign_table = "pre_sales_campaign"
        lead_table = "pre_sales_lead"
        lead_id_field = "pre_sales_lead_id"
    else:
        campaign_table = "post_sales_campaign"
        lead_table = "post_sales_lead"
        lead_id_field = "post_sales_lead_id"

    with get_pg_connector() as pg:
        campaign_details = list(pg.list(campaign_table, {"campaign_id": campaign_id}))

    if not campaign_details:
        yield {"status": "Error", "error_description": f"No campaign found for campaign_id={campaign_id}"}
        return

    campaign_details = campaign_details[0]
    logger.info(f"Campaign details: {json.dumps(campaign_details,indent=4)}")
    if isinstance(lead, dict):
        lead_data = lead
        lead_id = lead.get(lead_id_field)
    else:
        lead_id = lead
        with get_pg_connector() as pg:
            result = list(pg.list(lead_table, {lead_id_field: lead_id}))
        if not result:
            yield {"status": "Error", "error_description": f"No lead found for {lead_id_field}={lead_id}"}
            return
        lead_data = result[0]

    if not lead_id:
        yield {"status": "Error", "error_description": "Lead ID missing"}
        return

    logger.info(f"Lead found for lead_id={lead_id}")

    if not channel:
        channel = get_channel(lead_data, campaign_details)

    provider_name = None
    template_data = None

    if channel == "voice_phone":
        provider_name = VOICE_PROVIDER_NAME

    elif channel in ("whatsapp_chat", "sms", "rcs"):
        template_data = get_whatsapp_template(
            lead_id=lead_id,
            campaign_type=campaign_type,
            campaign_objective=campaign_details.get("campaign_objective"),
            # campaign_objective= [
            #     "Service Reminder"
            # ],
            # dealership_id = lead_data.get("dealership_id"), //for later
            lead_info={}
        )
        if not template_data:
            yield {"status": "Error", "error_description": f"No template found for lead_id={lead_id}"}
            return
        template_data = template_data[0]
        logger.info(f"Template ID for phone_number={lead_data.get('phone_number')}: {template_data.get('template_id')}")
    else:
        yield {"status": "Error", "error_description": f"Unsupported channel: {channel}"}
        return

    if campaign_type == "pre-sales":
        mobile = lead_data.get("phone_number")
        customer_name = lead_data.get("person_name")
        variable_mapping = get_variable_values(template_data.get("template_variables", []), lead_data) if template_data else {}

    else:
        persons = lead_data.get("persons_involved") or []
        selected_person = None

        if user_id:
            selected_person = next((p for p in persons if p.get("user_id") == user_id), None)
        if not selected_person and persons:
            selected_person = persons[0]

        if not selected_person:
            yield {"status": "Error", "error_description": f"No valid person for post-sales lead_id={lead_id}"}
            return

        mobile = selected_person.get("last_contacted_whatsapp_number")
        customer_name = selected_person.get("person_name")
        variable_mapping = get_variable_values(template_data.get("template_variables", []), lead_data, selected_person) if template_data else {}

    campaign_user = {
        "lead_id": lead_id,
        "mobile_number": mobile,
        "customer_name": customer_name,
        "contact_channel": channel,
        "template_id": template_data.get("template_id") if template_data else None,
        "template_details": template_data.get("template_details") if template_data else None,
        **variable_mapping
    }

   
    template_message = None
    buttons = None

    if template_data:
        buttons = template_data.pop("buttons", None)
        template_vars = template_data.get("template_variables", [])
        render_data = {v: template_data.get(v, "") for v in template_vars}
        template_message = template_data.get("template_message", "").format(**render_data)

   
    if channel == "web_chat":
        yield {"placeholder": template_message, "buttons": buttons}
        return

   
    final_payload = {
        **campaign_details,
        **(template_data or {}),
        "enterprise_id": campaign_details.get("enterprise_id"),
        "campaign_id": campaign_details.get("campaign_id"),
        "channel": channel,
        "sender": template_data.get("sender") if template_data else None,
        "provider_name": provider_name or (template_data.get("provider_name").lower() if template_data else None),
        "template_message": template_message,
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
                "batch_size": 100,
                "_skip_sent_message": True
            }
        }
    }

    run_async = campaign_details.get("run_async", True)
    is_testing = campaign_details.get("_is_testing", False)

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
        enterprise_id=campaign_details.get("enterprise_id", "autobotcrm")
    )

    yield {"task_response": async_task, "campaign_response": final_payload}



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
    channels = campaign_details.get("channels") or ["voice_phone"]
    if len(channels) > 0:
        return channels[0]

    return "voice_phone"  #fallback

def get_variable_values(template_variables, lead_data, selected_person=None):
    """
    Extract values for template variables from lead_data or selected_person.
    Priority: selected_person → lead_data → None
    """
    values = {}
    for var in template_variables:
        if selected_person and var in selected_person:
            values[var] = selected_person.get(var)
        else:
            values[var] = lead_data.get(var)
    return values


