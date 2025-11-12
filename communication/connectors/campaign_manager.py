#!/usr/bin/python
# -*- coding: utf-8 -*-
import asyncio
from copy import deepcopy as copy
import math
import os
from typing import Dict, Any, List, Tuple, Optional, Generator
from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
import sys
sys.path.insert(0, dirname(dirname(abspath(__file__))))
from connectors.communication_helpers import _wait_for_next_minute,yield_gryd_task_results
from connectors.base_connector_communication import *
from connectors.whatsapp_connectors.source_connectors import *
logger=hp.get_logger(__name__)

CAMPAIGN_ARCHIVE_KEYS={
    "WHATSAPP":[
                    "message_status", "message_id", "sent_payload", "response_code", "message_status",
                    "sent_timestamp", "api_response_time", "message_request_id",
                    "delivered_timestamp", "initiated_timestamp", "message_triggered_timestamp","error_code","error_href","message_id",
                    "error_title","error_details","time_take_to_process",
                    "pricing_billable","pricing_category","user_id","conversation_id","session_id",
                ],
    "VOICEBOT":[
                    "message_status", "message_id", "sent_payload", "response_code",
                    "sent_timestamp", "api_response_time", "message_request_id",
                    "delivered_timestamp", "initiated_timestamp", "message_triggered_timestamp",
                    "error_code", "error_href", "error_title", "error_details",
                    "time_take_to_process", "pricing_billable", "pricing_category","user_id","conversation_id","session_id",
                ]
}

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
                or campaign_details.get("channel_provider")
            )
            channel_number = campaign_details.get("channel_number")
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
            campaign_user_id: str,
            campaign_details: dict,
            campaign_user_data: dict,
            enterprise_id: str,
            *args,
            **kwargs
        ) -> dict:
        """
        Sends a WhatsApp campaign message and updates campaign user data.

        Args:
            mobile_number (str): Recipient’s mobile number.
            campaign_user_id (str): ID of the campaign user.
            campaign_details (dict): Metadata about the campaign (provider, template, etc.).
            campaign_user_data (dict): Data for the user in the campaign.
            enterprise_id (str): Enterprise ID.
            *args, **kwargs: Additional arguments passed to the WhatsApp connector.

        Returns:
            dict: Final patch data used to update the campaign user record.
                Returns an error patch dict if something fails.
        """
        start_time = time.time()
        whatsapp_provider = campaign_details.get("channel_provider")
        channel_number = campaign_details.get("channel_number")

        logger.info(
            f"Preparing to send campaign message for user_id={campaign_user_id}, "
            f"provider={whatsapp_provider}, channel={channel_number}"
        )

        # Format mobile number safely
        mobile_number = self._format_mobile_number(
            mobile_number,
            country_code=campaign_user_data.get("country_code", "91") or "91"
        )
        patch_user_data = {"mobile_number":mobile_number,"campaign_message":campaign_details.get("campaign_message",'').format(**campaign_user_data)}
        logger.info(f"Campaign Message patch_user_data: {patch_user_data}")
        # Build payload
        send_data = self.create_campaign_payload(
            campaign_details, campaign_user_data, enterprise_id
        )
        if not send_data:
            logger.error(f"Failed to create send_data for campaign user ID {campaign_user_id}")
            patch_user_data = {
                "execution_error": True,
                "execution_error_message": "Failed to create campaign payload",
                "sent_message": False,
            }
            # update_model_record(
            #     enterprise_id,
            #     M_GRYD_CAMPAIGN_USER_DETAIL,
            #     campaign_user_id,
            #     patch_user_data,
            #     id_attr="campaign_user_id",
            # )
            return patch_user_data

        try:
            # Initialize provider connector
            provider = WhatsappMessangerConnector.whatsapp(
                whatsapp_provider, *args, **kwargs
            )

            # Send WhatsApp message
            response = provider.send_message_whatsapp(
                mobile_number, channel_number, **send_data
            )
            logger.info(f"Response for campaign user {campaign_user_id}: {response}")

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
                    "channel_provider": whatsapp_provider,
                }

            else:
                # Non-dict response
                logger.warning(f"Unexpected response type for user {campaign_user_id}: {type(response)}")
                patch_user_data = {
                    "sent_message": False,
                    "message_status": "invalid_response",
                    "execution_error": True,
                    "execution_error_message": f"Unexpected response type: {type(response)}",
                }

        except Exception as e:
            hp.print_error()
            logger.exception(f"Error sending message for campaign user ID {campaign_user_id}: {e}")
            patch_user_data = {
                "execution_error": True,
                "execution_error_message": str(e),
                "sent_message": False,
                "message_status": "error",
            }

        # update_model_record(
        #     enterprise_id,
        #     M_GRYD_CAMPAIGN_USER_DETAIL,
        #     campaign_user_id,
        #     patch_user_data,
        #     id_attr="campaign_user_id",
        # )
        logger.info(
            f"Updated campaign user {campaign_user_id} with patch: {patch_user_data}"
        )
            
        # Always update user record (even if it failed)
        try:
            logger.info(f"once the campaign is triggered I am creating a session---")
            b=BaseWebhookConverter()
            d=b.check_whatsapp_session_status(**{"user_id":mobile_number,"call_type":"outbound","conversation_id":campaign_details.get("conversation_id"),"enterprise_id":enterprise_id,"campaign_id":campaign_details.get("campaign_id")})
            logger.info(f"DATA from check_whatsapp_session_status from campaign-----{d}")
            
            session_id=d.get("session_id")
            engID=d.get("engagement_id")
            campaign_id=d.get("campaign_id")
            if session_id:
                logger.info(f"Session Id: {session_id}")
                patch_user_data["session_id"] = session_id                
                d={
                    "session_id":patch_user_data.get('session_id'),
                    "message_status":patch_user_data.get('message_status'),
                    "enterprise_id":enterprise_id,
                    "campaign_user_id":campaign_user_id
                }
                logger.info(f"Calling patch person session to update status and dispositon ..")
                BaseWebhookConverter().patch_person_session_status(**d)
    
                # create a history object by passing the campaign message
                # if engID:
                #     append_session_history(
                #         **{
                #             "session_id": session_id,
                #             "enterprise_id": enterprise_id,
                #             "mobile_number": mobile_number,
                #             "conversation_id": campaign_details.get("conversation_id"),
                #             "campaign_message": campaign_details.get("campaign_message",'').format(**campaign_user_data),
                #             "engagement_id": engID,
                            
                #         }
                #     )
                # else:
                #     logger.info("engID missing — skipping append_session_history()")
                
                # update_model_record(
                #     enterprise_id,
                #     M_GRYD_CAMPAIGN_USER_DETAIL,
                #     campaign_user_id,
                #     {"session_id":patch_user_data.get('session_id')},
                #     id_attr="campaign_user_id",
                # )
                
        except Exception as patch_err:
            hp.print_error()
            logger.exception(f"Failed to patch campaign user {campaign_user_id}: {patch_err}")

        return patch_user_data
        
# def append_session_history(*args,**kwargs):
#     """
#     Appends a new message entry to the WhatsApp session history.
#     """
#     logger.info(f"Appending history for session_id: {kwargs}")

#     try:
#         HEADERS = ConverseHeader.get(kwargs.get("enterprise_id"))

#         query_params = {
#             "index":0,
#             "intent":"whatsapp_init",
#             "created_sequence":int(time.time()),
#             "user_id": kwargs.get("mobile_number"),
#             "response": "hi",
#             "sender_id": kwargs.get("mobile_number"),
#             "session_id": kwargs.get("session_id"),
#             "request_type": "type",
#             "engagement_id":kwargs.get("engagement_id"),
#             "conversation_id": kwargs.get("conversation_id"),
#         }
        
#         logger.info(f"TEST QUERY PARAMS for getting MESSAGE ID: {json.dumps(query_params, indent=4)}")

#         resp = requests.post(
#             f"{BASE_URL}/object/history",
#             params=query_params,
#             headers=HEADERS,
#         )

#         if resp.status_code != 200:
#             logger.warning(
#                 f"Failed to fetch initial message for session {kwargs.get('session_id')}. "
#                 f"Status: {resp.status_code}, Response: {resp.text}"
#             )
#             return

#         resp_json = resp.json()
#         message_id = resp_json.get("message_id")
#         logger.info(f"TEST Updated message_id: {message_id}")
#         if message_id:
#             new_message = {
#                 "index":1,
#                 "intent": "whatsapp_init",
#                 "created_sequence":int(time.time()),
#                 "user_id": kwargs.get("mobile_number"),
#                 "reply_to": message_id,
#                 "response": kwargs.get("campaign_message"),
#                 "sender_id": kwargs.get("mobile_number"),
#                 "session_id": kwargs.get("session_id"),
#                 "request_type": "system",
#                 "engagement_id":kwargs.get("engagement_id"),
#                 "conversation_id": kwargs.get("conversation_id")
#             }
            
#             logger.info(f"TEST QUERY PARAMS for posting index 1 response: {json.dumps(new_message, indent=4)}")
            

#             post_resp = requests.post(
#                 f"{BASE_URL}/object/history",
#                 headers=HEADERS,
#                 json=new_message,
#             )

#             if post_resp.status_code == 200:
#                 logger.info(f"History added successfully for session {kwargs.get('session_id')}")
#             else:
#                 logger.warning(
#                     f"Failed to append history for session {kwargs.get('session_id')}. "
#                     f"Status: {post_resp.status_code}, Response: {post_resp.text}"
#                 )
#         else:
#             logger.warning(
#                 f"No message_id found for session {kwargs.get('session_id')}; history not updated."
#             )

#     except Exception as e:
#         logger.exception(f"Error while appending history for session {kwargs.get('session_id')}: {e}")



@gryd.is_a_task(function_name="async_send_campaign_message")
def async_send_campaign_message(mobile_number: str,campaign_user_id: str,campaign_details: dict,campaign_user_data: dict,enterprise_id: str,*args,**kwargs):
    logger.info("Sending Async Campaign message")
    b=BaseCampaignCreater()
    b.send_campaign_message(mobile_number,campaign_user_id,campaign_details,campaign_user_data,enterprise_id,*args,**kwargs)

# @gryd.is_a_task(function_name="send_voice_campaign_message")
def send_voice_campaign_message(mobile_number: str,campaign_user_data: dict,campaign_details: dict,VOICE_CAMPAIGN_BASE_URL: str,*args,**kwargs):
    mobile_number=BaseCampaignCreater()._format_mobile_number(mobile_number,country_code="+91")
    payload = json.dumps({
        "number":mobile_number,
        "user_name": campaign_user_data.get("name"),
        "profile_type": "post_sales",
        "conversation_id": campaign_user_data.get("conversation_id"),
        "campaign_id": campaign_user_data.get("campaign_id")
    })
    requests.post(f"{VOICE_CAMPAIGN_BASE_URL}/outbound-call",data=payload)
    logger.info(f"sent a voice campaign for Mobile number : {mobile_number}")
class BaseCustomCampaignManager:
    """Manages custom campaign workflows, including user processing,
    campaign detail posting, and orchestration of batch execution."""

    
    def process_campaign_users_generic(
        self,
        enterprise_id,
        campaign_id,
        campaign_details_data,
        campaign_users,
        campaign_status_check_id=None,
        **kwargs
    ):
        """
        Generic processor for campaign users across channels (WhatsApp, Voice, etc.).Handles new user creation, archiving, retry logic, and async send dispatching.

        Args:
            enterprise_id (str)
            campaign_id (str)
            campaign_details_data (dict)
            campaign_users (List[dict])
            campaign_status_check_id (str)
            channel (str): Channel name e.g., 'WHATSAPP', 'VOICE'
            send_func (callable): Function to send messages/calls asynchronously
            **kwargs: extra options, e.g., _is_testing

        Returns:
            List[str]: List of processed campaign_user_ids
        """
        channel= campaign_details_data.get("channel").upper()
        logger.info(f"Starting processing {len(campaign_users)} users for campaign_id={campaign_id}, channel={channel}")

        # --- Load model references ---
        campaign_user_detail_model = reload_model_ref(M_GRYD_CAMPAIGN_USER_DETAIL, enterprise_id)
        campaign_user_detail_archive_model = reload_model_ref(M_GRYD_CAMPAIGN_USER_DETAIL_ARCHIVE, enterprise_id)

        # --- Load credentials ---
        channel_key = "channel_number" if channel.upper() == "WHATSAPP" else "caller_id"
        credential=None
        if channel.upper() == "WHATSAPP":
            credential, provider = self.get_dyanamic_provider_creds(
                enterprise_id, campaign_details_data.get(channel_key), campaign_details_data
            )
            campaign_details_data[f"{channel.lower()}_credential"] = credential
        skip_creds_check = channel != "WHATSAPP"
        if not credential and not skip_creds_check:
            logger.error(f"❌ {channel} credentials not found — aborting.")
            return []
        
        processed_users = []

        for count, user in enumerate(campaign_users, start=1):
            mobile_number = clean_phone_number(user.get("mobile_number", "")) if channel.upper() == "WHATSAPP" else user.get("mobile_number", "")
            logger.info(f"mobile_number-----{ mobile_number}")
            
            if channel.upper()=="WHATSAPP":
                mobile_number = BaseCampaignCreater()._format_mobile_number(mobile_number,user.get("country_code","91"))
                
            if not mobile_number:
                logger.warning(f"[{count}] User record missing mobile_number: {user}")
                continue

            if user.get("unsubscribe", False):
                logger.info(f"[{count}] User {mobile_number} has unsubscribed. Skipping.")
                continue

            logger.info(f"[{count}] Processing user {mobile_number}")

            # Enrich user
            enriched_user = {
                **user,
                "campaign_status_check_id": campaign_status_check_id,
                "campaign_id": campaign_id,
                "campaign_name": campaign_details_data.get("campaign_name"),
                "conversation_id": campaign_details_data.get("conversation_id"),
                "campaign_detail_id": campaign_details_data.get("campaign_detail_id"),
                "campaign_type": campaign_details_data.get("campaign_type"),
                "template_id": campaign_details_data.get("template_id"),
                "channel": channel,
                "channel_provider": campaign_details_data.get("channel_provider"),
                "enterprise_id":enterprise_id
            }

            # Construct campaign_user_id
            campaign_user_id = val.name_to_id_func(
                {},
                {
                    "campaign_id": campaign_id,
                    "mobile_number": mobile_number,
                    "template_id": enriched_user.get("template_id"),
                    "campaign_detail_id":campaign_details_data.get("campaign_detail_id"),
                },
                "campaign_user_id",
                "campaign_id",
                "campaign_detail_id",
                "mobile_number",
                "template_id",
                attribute_join="",
                is_unique=True,
                separator="-",
            )

            try:
                campaign_user_data = campaign_user_detail_model.get(campaign_user_id)
                logger.info(f"[{count}] Fetched existing campaign_user_data for {campaign_user_id}")
            except KeyError:
                logger.info(f"[{count}] No existing campaign_user found for {campaign_user_id}")
                campaign_user_data = {}

            is_new_user = not bool(campaign_user_data)
            logger.info(f"[{count}] {campaign_user_id} is_new_user={is_new_user}")
            
            # New user creation
            if is_new_user:
                enriched_user.update({"sent_count": 1, "campaign_user_id": campaign_user_id})
                campaign_user_data = campaign_user_detail_model.post(enriched_user)
                logger.info(f"[{count}] Created new campaign_user: {campaign_user_id}")

            # Skip already sent messages
            skip_sent = campaign_details_data.get("_skip_sent_message")
            if skip_sent is None:
                skip_sent = campaign_details_data.get("skip_sent_message", True)

            is_testing = kwargs.pop("_is_testing", False)

            logger.info(
                f"Skip check → _skip_sent_message={campaign_details_data.get('_skip_sent_message')} , "
                f"skip_sent_message={campaign_details_data.get('skip_sent_message')} , "
                f"final skip_sent={skip_sent}, is_testing={is_testing}"
            )

            # Archive existing record
            if not is_new_user:
                failed_retry = None
                old_count = campaign_user_data.get("sent_count", 1)
                if campaign_user_data.get("message_status", '').lower() == "failed":
                    failed_retry = campaign_user_data.get("failed_retry", 0) + 1

                new_count = old_count + 1
                old_campaign_data = {k: campaign_user_data.get(k, None) for k in CAMPAIGN_ARCHIVE_KEYS[channel.upper()] if k in campaign_user_data}
                archive_id = make_uuid(time.time(), campaign_user_id)
                archive_entry = {
                    **old_campaign_data,
                    **enriched_user,
                    "campaign_user_id": campaign_user_id,
                    "campaign_user_archive_id": archive_id,
                }
                campaign_user_detail_archive_model.post(archive_entry)
                logger.info(f"[{count}] Archived old record for {campaign_user_id} as {archive_id}")

                update_data = {
                    "sent_count": new_count,
                    "campaign_user_archive_ids": campaign_user_data.get("campaign_user_archive_ids", []) + [archive_id],
                    **{k: None for k in CAMPAIGN_ARCHIVE_KEYS[channel.upper()]},
                }
                if failed_retry:
                    # TODO RETRY For Failed
                    update_data.update({"failed_retry": failed_retry})

                campaign_user_detail_model.patch(campaign_user_id, update_data)
                logger.info(f"[{count}] Patched campaign_user {campaign_user_id} with updated counts and archive ids")


            if channel.upper()=="WHATSAPP":
                logger.info(f"[{count}] Sent {channel} message for {campaign_user_id}")
                #TODO Send async 
                if is_testing:
                    logger.info(f"[{count}] Sending WhatsApp message synchronously for {campaign_user_data.get('campaign_user_id')}")
                    continue
                if not campaign_details_data.get("run_async"):
                    logger.info(f"[{count}] Sending WhatsApp message synchronously for {campaign_user_data.get('campaign_user_id')}")
                    async_send_campaign_message(campaign_user_data.get("mobile_number"),
                        campaign_user_data.get("campaign_user_id"),
                        campaign_details_data,
                        campaign_user_data,
                        enterprise_id,
                        count,)
                else:
                    logger.info(f"[{count}] Dispatching async WhatsApp message for {campaign_user_data.get('campaign_user_id')}")
                    gryd.create_async_task("async_send_campaign_message",GRYD_COMMUNICATION_CAMPAIGN_SERVICE,args=[
                        campaign_user_data.get("mobile_number"),
                        campaign_user_data.get("campaign_user_id"),
                        campaign_details_data,
                        campaign_user_data,
                        enterprise_id,
                        count,
                    ],enterprise_id=enterprise_id)
            if channel.upper()=="VOICEBOT":
                logger.info(f"[{count}] Sent {channel} message for {campaign_user_id}")
                #TODO Get the data from audience model and then see 
                send_voice_campaign_message(campaign_user_data.get("mobile_number"),campaign_user_data,campaign_details_data,VOICE_CAMPAIGN_BASE_URL)
                pass

            processed_users.append(campaign_user_id)
    
        logger.info(f"Finished processing {len(processed_users or [])} users for campaign_id={campaign_id}, channel={channel}")
        return processed_users

    def get_dyanamic_provider_creds(self,enterprise_id,channel_number,campaign_details):
        logger.info("Loading Dyanamic Provider creds")
        AUTH = AuthManager(campaign_details.get("whatsapp_provider"))
        whatsapp_cred_details= AUTH.get_headers(channel_number, enterprise_id,complete_data=True)
        logger.debug(f"whatsapp_cred_details:: {whatsapp_cred_details}, {type(whatsapp_cred_details)}")
        whatsapp_credential, whatsapp_provider = whatsapp_cred_details.get("auth_headers"),whatsapp_cred_details.get("whatsapp_provider")
        return whatsapp_credential, whatsapp_provider 

        
    def prepare_campaign_dates(self, campaign_details):
        start_date = campaign_details.get(
            "campaign_start_date",
            hp.now(tz=DB_TIMEZONE).strftime("%Y-%m-%d"),
        )
        end_date = campaign_details.get(
            "campaign_end_date",
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
        campaign_details_data={},
        campaign_id=None,
        campaign_status_check_id=None,
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
                Communication channel (e.g., `"WHATSAPP"`, `"VOICEBOT"`).
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
        ...         "channel": "WHATSAPP",
        ...         "campaign_user_source": {"source_type": "db"}
        ...     }
        ... )
        """

        try:
            logger.info(f"Campaign details: {json.dumps(campaign_details_data, indent=4, default=str)}")

            # Resolve IDs
            enterprise_id = campaign_details_data.get("enterprise_id") or enterprise_id or "test1"
            campaign_id = campaign_details_data.get("campaign_id") or campaign_id
            campaign_detail_id = campaign_details_data.get("campaign_detail_id")
            campaign_status_check_id= campaign_details_data.get("campaign_status_check_id")
            logger.info(f'*********[Running Campaign]**************\nCampaign_id: [{campaign_id}]  ==>  Campaign_Status_check_id: [{campaign_status_check_id}]')

            # Load campaign user source
            campaign_user_source = campaign_details_data.get("campaign_user_source", {})
            channel = campaign_details_data.get("channel", "").upper()

            if kwargs.get("retry_failed"):
                if campaign_users and channel in ["WHATSAPP", "VOICEBOT"]:
                    self.process_campaign_users_generic(
                        enterprise_id=enterprise_id, 
                        campaign_id=campaign_id, 
                        campaign_details_data=campaign_details_data,
                        campaign_users=campaign_users, 
                        campaign_status_check_id=campaign_status_check_id,
                        _is_testing=kwargs.get("_is_testing", False)
                    )
                    return {"info":"Campaign Message sent for Failed user"}



            source = CampaignSourceFactory.create_from_source_json(
                enterprise_id=enterprise_id,
                campaign_details_data=campaign_details_data,
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

                # Process users based on channel
                if campaign_users and channel in ["WHATSAPP", "VOICEBOT"]:
                    self.process_campaign_users_generic(
                        enterprise_id=enterprise_id, 
                        campaign_id=campaign_id, 
                        campaign_details_data=campaign_details_data,
                        campaign_users=campaign_users, 
                        campaign_status_check_id=campaign_status_check_id,
                        _is_testing=kwargs.get("_is_testing", False)
                    )

        except Exception as e:
            hp.print_error()
            logger.error(f"Error while running campaign: {e}")
            return {"error": True, "error_message": str(e)}




whatsapp_info={
    "channel": "whatsapp",
    "channel_provider": "rml",
    "enterprise_id": "test1",
    "campaign_name": "WhatsappTestingVersion3",
    "template_type": "media_template",
    "template_name": "whatsapp_campaign_testing",
    "template_variables": [],  #specific to whatsapp these varible is same has replace by whatsapp template varaible and this info should present in user info else error
    "template_buttons_payload": [], # Details of button there in template
    "channel_provider_number": "8951708731"    # all the creds will be picked for whatsapp creds db
}

voice_info={
    "channel":"voic",
    "channel_provider":"twilo",
    "enterprise_id":"test1",
    "campaign_name":"VocieTestingVersion3",
    "template_name": "voice_campaign_testing"
}



def createGrydCampaign(info:dict)-> dict:
    campaign_info = {
        "enterprise_id": info.get("enterprise_id"),
        "channel": info.get("channel"),
        "channel_provider": info.get("channel_provider"),
        "campaign_name": info.get("campaign_name"),
        "campaign_start_date": info.get("campaign_start_date"),
        "campaign_end_date": info.get("campaign_end_date"),
        "campaign_created_by": info.get("campaign_created_by")
    }

    try:
        logger.info(f"Creating campaign for enterprise_id={campaign_info.get('enterprise_id')}, "
                    f"channel={campaign_info.get('channel')}, provider={campaign_info.get('channel_provider')}")
        logger.debug(f"Campaign info payload: {json.dumps(campaign_info, indent=2, default=str)}")

        model_ref = reload_model_ref(M_GRYD_CAMPAIGN, campaign_info.get("enterprise_id"))
        model_response = model_ref.post(campaign_info)

        logger.info(f"Campaign created successfully: enterprise_id={campaign_info.get('enterprise_id')}, "
                    f"name={campaign_info.get('campaign_name')}")
        logger.debug(f"Model response: {json.dumps(model_response, indent=2, default=str)}")

        return model_response

    except Exception as e:
        logger.error(f"Error while creating campaign for enterprise_id={campaign_info.get('enterprise_id')} | "
                     f"campaign_name={campaign_info.get('campaign_name')} | Error={str(e)}",
                     exc_info=True)
        hp.print_error()
        raise



def createGrydCampaignDetails(details:dict)-> dict:
    try:
        campaign_id = details.get("campaign_id")
        logger.info(f"Creating Campaign Details for campaign_id={campaign_id}")
        logger.debug(f"Incoming details (before enrichment): {json.dumps(details, indent=2, default=str)}")

    

        model_ref = reload_model_ref(M_GRYD_CAMPAIGN_DETAIL, details.get("enterprise_id"))
        model_response = model_ref.post(details)

        logger.info(f"Campaign details created successfully for campaign_id={campaign_id}")
        logger.debug(f"Model response: {json.dumps(model_response, indent=2, default=str)}")

        return model_response

    except Exception as e:
        logger.error(
            f"Error While Creating Campaign Details for campaign_id={campaign_id} | Error={str(e)}",
            exc_info=True
        )
        hp.print_error()
        raise

def createGrydCampaignStatus( enterprise_id: str, campaign_details_data: dict ) -> Dict[str, Any]:
    """
    Create or post a campaign status record.
    Generates a deterministic campaign_status_check_id based on campaign_id, campaign_detail_id, and user source.
    """
    try:
        # Generate unique campaign_status_check_id
        campaign_status_check_id = val.name_to_id_func(
            {},
            campaign_details_data,
            "campaign_status_check_id",
            "campaign_id",
            "channel",
            "channel_provider",
            attribute_join="",
            is_unique=True,
            separator="-",
        )

        payload = {
            "campaign_status_check_id": campaign_status_check_id,
            "campaign_id": campaign_details_data.get("campaign_id"),
            "campaign_detail_id": campaign_details_data.get("campaign_detail_id"),
            "max_per_day": campaign_details_data.get("max_per_day"),
            "campaign_user_source": campaign_details_data.get("campaign_user_source") or {},
            "channel":campaign_details_data.get("channel"),
            "channel_provider":campaign_details_data.get("channel_provider"),
            "last_minute_ts":None,
        }

        logger.info(f"Creating campaign status:\n{json.dumps(payload, indent=2)}")

        model_ref = reload_model_ref(M_GRYD_CAMPAIGN_STATUS_CHECK, enterprise_id)
        response = model_ref.post(payload)

        logger.info(f"Campaign status created successfully: {response}")
        return response

    except Exception as e:
        logger.error("Error while creating campaign status.", exc_info=True)
        hp.print_error()
        raise

def generate_campaign_detail_id(*args) -> str:
    """
    Generate a unique campaign detail ID based on the campaign ID, template identifier, 
    and (optionally) a user source dictionary.

    Args:
        campaign_id (str): Unique identifier of the campaign.
        template_id (str): Identifier for the message template used in the campaign.
        user_source (dict, optional): Additional dynamic user source details. 
            Example: For WhatsApp campaigns with multiple file sources, 
            this can differentiate IDs. Defaults to an empty dict.

    Returns:
        str: A deterministic UUIDv3 string uniquely representing the campaign detail.

    Note:
        The dynamic user_source logic can be enabled later if needed 
        by including it in the UUID generation.
    """

    # TODO: Enable dynamic user_source when multiple sources per campaign are required.
    # source_str = json.dumps(user_source or {}, sort_keys=True)
    # return str(hp.make_uuid3(str(campaign_id), str(template_id), source_str))

    return str(hp.make_uuid3(*args))



def build_base_campaign_details(campaign, user_input, template_id, campaign_detail_id) -> dict:
    return {
        **campaign,
        "campaign_type": user_input.get("campaign_type"),
        "campaign_user_source": user_input.get("campaign_user_source", {}) or {},
        "conversation_id": user_input.get("conversation_id"),
        "template_id": template_id,
        "campaign_detail_id": str(campaign_detail_id),
        "channel_number": user_input.get("channel_number"),
        "run_async":user_input.get("run_async"),
        "campaign_source":user_input.get("campaign_user_source", {}).get("source_type"),
        "max_per_day":user_input.get("max_per_day"),
        "campaign_message":user_input.get("campaign_message")
    }
def _build_campaign_metadata(campaign: dict, user_input: dict):
    """Extract and normalize common campaign metadata."""
    campaign_id = campaign.get("campaign_id") or str(uuid.uuid4())
    channel = user_input.get("channel", "").strip()
    channel_provider = user_input.get("channel_provider", "").strip()
    conversation_id = user_input.get("conversation_id", "").strip()
    campaign_detail_id = generate_campaign_detail_id(campaign_id, channel, channel_provider, conversation_id)
    return campaign_id, channel, channel_provider, conversation_id, campaign_detail_id


def voiceTransfromation(campaign, user_input):
    template_id = user_input.get('template_id') or user_input.get('template_name') or "default_template"
    campaign_id, channel, channel_provider, conversation_id, campaign_detail_id = _build_campaign_metadata(
            campaign, user_input
        )
    campaign_details = build_base_campaign_details(campaign, user_input, template_id, campaign_detail_id)
    logger.info(f"Posting campaign_details: {json.dumps(campaign_details, indent=4)}")
    return campaign_details


def whatsappTransfromation(campaign, user_input):
    user_data = copy(user_input or {})
    template_type = user_data.get("template_type", "text_template")
    if "max_per_day" not in user_data:
        user_data.update({"max_per_day":WHATSAPP_MAX_MESSAGE_PER_DAY})

    # Template-specific fields
    if template_type == "carousel_template":
        data = {
            "type": "template",
            "template_type": "carousel_template",
            "template_id": user_data.get("template_id"),
            "template_name": user_data.get("template_name"),
            "template_variables": user_data.get("template_variables", []),
            "carousel": user_data.get("carousel", [])
        }
    elif template_type == "media_template":
        data = {
            "type": "template",
            "template_type": "media_template",
            "template_id": user_data.get("template_id"),
            "template_name": user_data.get("template_name"),
            "media_type": user_data.get("template_media_type"),
            "media_url": user_data.get("template_media_url"),
            "media_id": user_data.get("template_media_id"),
            "media_file_name": user_data.get("media_file_name"),
            "template_variables": user_data.get("template_variables", []),
            "template_buttons_payload": user_data.get("template_buttons_payload", [])
        }
    else:
        data = {
            "type": "template",
            "template_type": "text_template",
            "template_id": user_data.get("template_id"),
            "template_name": user_data.get("template_name"),
            "template_variables": user_data.get("template_variables", []),
            "template_buttons_payload": user_data.get("template_buttons_payload", [])
        }

    template_id = data.get("template_id") or data.get("template_name") or "default_template"
    campaign_id, channel, channel_provider, conversation_id, campaign_detail_id = _build_campaign_metadata(
            campaign, user_input
        )

    campaign_details = {**data, **build_base_campaign_details(campaign, user_data, template_id, campaign_detail_id)}
    logger.info("Posting campaign_details:\n%s", json.dumps(campaign_details, indent=4))
    return campaign_details

def TransformationAndCreateCampaign(campaign_details):
    """Main campaign orchestration: create/fetch campaign, details, and status."""
    """
    Orchestrates the full campaign creation lifecycle including campaign, campaign details,
    and campaign status management, with optional reset functionality.

    ---
    **Workflow Overview:**
    1. **Campaign Creation or Retrieval**  
       - If `campaign_id` exists and `_force_campaign_update` is False → fetch existing campaign.  
       - Otherwise → create a new campaign using `createGrydCampaign()`.

    2. **Campaign Details Creation or Retrieval**  
       - If `campaign_detail_id` exists and not forced → fetch existing details.  
       - Else → dynamically invoke the channel-specific transformer (from
         `CAMPAIGN_CHANNEL_TRANSFORMERS`) to prepare campaign detail data, 
         and create it using `createGrydCampaignDetails()`.

    3. **Campaign Status Creation**  
       - Always creates a campaign status record using `createGrydCampaignStatus()`.  
       - If `_reset_campaign_status` is True → resets campaign tracking fields such as 
         `sent_count`, `last_update`, `last_minute_ts`, etc., via a PATCH update.

    4. **Response**  
       - Returns identifiers for the created/fetched campaign, campaign details, and 
         campaign status, along with campaign detail metadata.

    ---
    **Args:**
        campaign_details (dict):  
            A dictionary containing the following keys:
            - `enterprise_id` (str): Enterprise identifier.
            - `campaign_id` (str, optional): Existing campaign ID (if updating).
            - `campaign_detail_id` (str, optional): Existing campaign detail ID.
            - `channel` (str): Channel type (e.g., "WHATSAPP", "SMS", "EMAIL").
            - `_force_campaign_update` (bool, optional): Force recreate campaign if True.
            - `_reset_campaign_status` (bool, optional): Reset campaign tracking counters if True.
            - Additional transformer-specific fields as required by each channel.

    ---
    **Returns:**
        dict: A dictionary with the following structure:
        ```python
        {
            "campaign_id": str,
            "campaign_detail_id": str,
            "campaign_details_data": dict,
            "campaign_status_check_id": str
        }
        ```

    ---
    **Raises:**
        Exception: If any of the steps (campaign creation, details creation, status creation)
                   fail or return invalid data.

    ---
    **Example:**
        ```python
        response = TransformationAndCreateCampaign({
            "enterprise_id": "ent_123",
            "channel": "whatsapp",
            "campaign_name": "Festive Sale",
            "_reset_campaign_status": True
        })
        print(response)
        # Output:
        # {
        #     "campaign_id": "cmp_456",
        #     "campaign_detail_id": "cd_789",
        #     "campaign_status_check_id": "cs_101112",
        #     "campaign_details_data": {...}
        # }
        ```
    """
    enterprise_id = campaign_details.get("enterprise_id")
    campaign_id = campaign_details.get("campaign_id")
    force_update = campaign_details.get("_force_campaign_update", False)
    channel = (campaign_details.get("channel") or "").upper()
    _reset_campaign_status= campaign_details.pop("_reset_campaign_status",False)
    logger.info(f"_reset_campaign_status: : {_reset_campaign_status}")

    # --- STEP 1: Create or Fetch Campaign ---
    try:
        model_ref = reload_model_ref(M_GRYD_CAMPAIGN, enterprise_id)
        campaign = model_ref.get(campaign_id) if campaign_id and not force_update else createGrydCampaign(campaign_details)
        if not campaign or "campaign_id" not in campaign:
            raise Exception("Campaign creation failed or invalid response.")
    except Exception as e:
        logger.error(f"Error during campaign creation: {e}", exc_info=True)
        raise

    # --- STEP 2: Create or Fetch Campaign Details ---
    campaign_detail_id = campaign_details.get("campaign_detail_id")
    campaign_details_data = None
    try:
        if campaign_detail_id and not force_update:
            model_ref = reload_model_ref(M_GRYD_CAMPAIGN_DETAIL, enterprise_id)
            campaign_details_data = model_ref.get(campaign_detail_id)
        else:
            transformer = CAMPAIGN_CHANNEL_TRANSFORMERS.get(channel)
            if not transformer:
                raise ValueError(f"Unsupported channel: {channel}")
            
            reflected = transformer(campaign, campaign_details)
            if not reflected:
                raise Exception("Transformation failed — no campaign details created.")
            campaign_details_data = createGrydCampaignDetails(reflected)
    except Exception as e:
        logger.error(f"Error during campaign detail creation: {e}", exc_info=True)
        raise

    # --- STEP 3: Create Campaign Status ---
    try:
        campaign_status_detail = createGrydCampaignStatus( enterprise_id, campaign_details_data)
    except Exception as e:
        logger.error(f"Error during campaign status creation: {e}", exc_info=True)
        raise
    if _reset_campaign_status:
        model_ref = reload_model_ref(M_GRYD_CAMPAIGN_STATUS_CHECK, enterprise_id)
        updated = {
            "sent_count": 0,
            "today_sent": 0,
            "last_minute_ts":None,
            "last_minute_count": 0,
            "last_update": None,
            "last_offset":0
        }
        response = model_ref.patch(campaign_status_detail.get("campaign_status_check_id"),updated)
        logger.info(f"Reseting the Campaign Status : {response}")
    # --- STEP 4: Return Response ---
    return {
        "campaign_id": campaign.get("campaign_id"),
        "campaign_detail_id": campaign_details_data.get("campaign_detail_id"),
        "campaign_details_data": campaign_details_data,
        "campaign_status_check_id": campaign_status_detail.get("campaign_status_check_id")
    }



@gryd.is_a_task(function_name="RunCampaignOrCreater")
def RunCampaignOrCreater(campaign_details=None,*args,**kwargs):
    if not campaign_details:
        raise Exception("Empty Campaign details passed")
    if not isinstance(campaign_details, dict):
        raise ValueError(f"Campaign Details should be dict, got {type(campaign_details)}")

    if not campaign_details.get("enterprise_id"):
        raise Exception("No Enterprise Information provided")
    if not campaign_details.get("channel"):
        raise Exception("No Channel Information provided")
    if not campaign_details.get("channel_provider"):
        raise Exception("No Channel Provider provided")

    # Always call generic function
    result = TransformationAndCreateCampaign(campaign_details)
    logger.info(f"result:: {json.dumps(result,indent=4)}")
    b=BaseCustomCampaignManager()

    logger.info("Running campaign ...")

    run_async = campaign_details.get("run_async", False)
    is_testing = campaign_details.get("_is_testing", False)
    enterprise_id = campaign_details.get("enterprise_id")

    if not run_async:
        b.run_custom_campaign(
            _is_testing=is_testing,
            **result
        )
        return {"campaign_response": result}

    # Async flow
    task_response = gryd.create_async_task(
        "async_run_custom_campaign",
        GRYD_COMMUNICATION_CAMPAIGN_SERVICE,
        args=[],
        kwargs={
            "_is_testing": is_testing,
            **result,
        },
        enterprise_id=enterprise_id,
    )

    return {
        "task_response": task_response,
        "campaign_response": result
    }

@gryd.is_a_task(function_name="async_run_custom_campaign")
def async_run_custom_campaign(*args,**kwargs):
    logger.info("Sending Async Campaign message")
    b=BaseCustomCampaignManager()
    b.run_custom_campaign(*args,**kwargs)


# @gryd.is_a_task(function_name="async_run_failed_user")
# def async_run_failed_user(enterprise_id: str, campaign_user_id: str = None, campaign_user_data: dict = None):
#     """
#     Retry running a failed campaign user execution asynchronously.

#     Args:
#         enterprise_id (str): Enterprise ID.
#         campaign_user_id (str, optional): ID of the campaign user record.
#         campaign_user_data (dict, optional): Data containing enterprise, campaign, and user info.

#     Returns:
#         dict: Response indicating success or failure.
#     """

#     REMOVE_UNWANTED = [
#         'sent_timestamp', 'read_timestamp', 'delivered_timestamp', 'received_timestamp',
#         'failed_timestamp', 'sent_payload', 'sent_message', 'message_request_id',
#         'time_take_to_process', 'message_status', 'created', 'updated',
#         'session_id', 'message_triggered_timestamp','initiated_timestamp'
#     ]

#     try:
#         # Step 1: Fetch campaign user data if not provided
#         if not campaign_user_data and campaign_user_id:
#             # campaign_user_data = fetch_record(
#             #     enterprise_id,
#             #     M_GRYD_CAMPAIGN_USER_DETAIL,
#             #     campaign_user_id,
#             #     id_attr="campaign_user_id"
#             # )

#         # Step 2: Validate presence of campaign user data
#         if not campaign_user_data:
#             logger.error("Campaign user data not found.")
#             return {"error": True, "error_message": "Campaign user data not found."}
#         campaign_user_data["enterprise_id"]=enterprise_id
#         # Step 3: Validate mandatory fields
#         required_fields = ["enterprise_id", "campaign_id", "campaign_detail_id"]
#         missing_fields = [f for f in required_fields if not campaign_user_data.get(f)]
#         if missing_fields:
#             logger.error(f"Missing required fields: {', '.join(missing_fields)}")
#             return {"error": True, "error_message": f"Missing required fields: {', '.join(missing_fields)}"}

#         # Step 4: Fetch campaign details
#         campaign_detail = fetch_record(
#             campaign_user_data["enterprise_id"],
#             M_GRYD_CAMPAIGN_DETAIL,
#             campaign_user_data["campaign_detail_id"],
#             id_attr="campaign_detail_id"
#         )

#         if not campaign_detail:
#             logger.error("Campaign detail record not found.")
#             return {"error": True, "error_message": "Campaign detail not found."}

#         # Step 5: Remove unwanted fields safely
#         for key in REMOVE_UNWANTED:
#             campaign_user_data.pop(key, None)

#         # Step 6: Execute retry
#         b = BaseCustomCampaignManager()
#         b.run_custom_campaign(
#             enterprise_id=campaign_user_data["enterprise_id"],
#             campaign_id=campaign_user_data["campaign_id"],
#             campaign_details_data=campaign_detail,
#             campaign_users=[campaign_user_data],
#             retry_failed=True
#         )

#         logger.info(f"Retry initiated successfully for campaign: {campaign_user_data['campaign_id']}")
#         return {"success": True, "message": "Retry initiated successfully."}

#     except Exception as e:
#         logger.exception(f"Error during async_run_failed_user: {e}")
#         return {"error": True, "error_message": f"Exception occurred: {str(e)}"}





    

CAMPAIGN_CHANNEL_TRANSFORMERS={
    "WHATSAPP":whatsappTransfromation,
    "VOICEBOT":voiceTransfromation,
    # "EMAIL":emailTransfromation
}


if __name__=="__main__":
    # run_enteprise_campaign(**user_input)
    # RunCampaignOrCreater(
    #     {
    #         "_is_testing":False,
    #         "enterprise_id": "no_code_low_code",
    #         "channel": "whatsapp",
    #         "channel_provider": "rml",
    #         "channel_number": "8951708731",
    #         "campaign_name": "RML-Test-service-reminder_new",
    #         "campaign_start_date": "2025-08-03",
    #         "campaign_end_date": "2025-08-09",
    #         "campaign_created_by": "nitesh",
    #         "_force_campaign_update": False,
    #         "max_per_day": 20000,
    #         "campaign_user_source": {
    #             "source_type": "default",
    #             "is_internal": True,
    #             "connection": {
    #                 "endpoint": "",
    #                 "headers": {}
    #             },
    #             "credentials": {     # optional
    #                 "username": "",
    #                 "password": "",
    #                 "api_key": ""
    #             },
    #             "config": {
    #                 # "source_model": "campaign_user_detail",
    #                 "batch_size": 500,
    #                 "offset": 0,
    #                 "filters": {"active": True},
    #                 "retry_policy": {"max_retries": 3, "backoff": "exponential"}
    #             },
    #             "field_mapping": {
    #                 "phone_number": "mobile_number",
    #                 "first_name": "first_name"
    #             },
    #             "metadata": {
    #                 "description": "Internal GryD user database",
    #                 "owner": "automation_team"
    #             },
    #             "campaign_users": [
    #                 {
    #                     "name": "Nitesh Kumar Sahu",
    #                     "date": "20 Aug 2025",
    #                     "location": "Delhi",
    #                     "service_id": "PMSB-856P48H75N6369",
    #                     "mobile_number": "9348927558"
    #                 },
    #             ],
    #             "_skip_sent_message":False
    #         },
    #         "template_type": "media_template",
    #         "template_id": "service_reminder_p",
    #         "template_variables": ["name", "date", "location", "service_id"],
    #         "template_buttons_payload": [
    #             "book-service-reminder-yes",
    #             "book-service-reminder-reschdule"
    #         ],
    #         "run_async":False,
    #         "_reset_campaign_status":False
    #     }
    # )


     ######   TO RUN FOR failed User with Campaign user data
    # async_run_failed_user(
    #     "no_code_low_code",
    #     campaign_user_data={
    #     "enterprise_id":"no_code_low_code",
    #     "name": "Nitesh Kumar Sahu",
    #     "channel": "WHATSAPP",
    #     "car_model": "Breeza",
    #     "campaign_id": "servicereminder",
    #     "message_type": "interactive",
    #     "phone_number": "9348927558",
    #     "campaign_name": "ServiceReminder",
    #     "mobile_number": "9348927558",
    #     "sent_timestamp": 1761760682.182418,
    #     "campaign_user_id": "servicereminder-eecd7805-3dff-3ed5-8021-f6df5874e720-9348927558-01k8rbeesdpz8p06v4706r4xqy",
    #     "channel_provider": "airtel",
    #     "api_response_time": "0.16277217864990234",
    #     "whatsapp_provider": "airtel",
    #     "campaign_detail_id": "eecd7805-3dff-3ed5-8021-f6df5874e720",
       

    # }
    # )

    ######   TO RUN FOR failed User with Campaign user id
    # async_run_failed_user(
    #     "no_code_low_code",
    #     campaign_user_id= "servicereminder-eecd7805-3dff-3ed5-8021-f6df5874e720-9348927558-01k8rbeesdpz8p06v4706r4xqy",
    # )
    RunCampaignOrCreater(
        {
            
            'campaign_id': 'servicereminder',
            # "_is_testing":True,
            "enterprise_id": "autobot",
            # "enterprise_id": "no_code_low_code",
            # 'campaign_detail_id': 'a6cde695-a310-38e2-af25-9a1b17ee700f',
            "channel": "whatsapp",
            "channel_provider": "airtel",
            # "channel_provider":"trello",
            "channel_number": "918951412003",
            "conversation_id":"indiaautobot",
            "campaign_name": "ServiceReminder",
            "campaign_start_date": "2025-08-03",
            "campaign_end_date": "2025-08-09",
            "campaign_created_by": "praveen",
            "_force_campaign_update": True,
            "_reset_campaign_status": True,
            "max_per_day": 20000,

            "campaign_user_source": {
                "source_type": "default",
                "is_internal": True,
                "connection": {
                    # "endpoint":"https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/6cf59074-f661-4221-b0a5-baafe8305374-6903a06e_demo_testing_campaign_info.csv",
                    # "endpoint":"https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/4de7c76c-3c49-4b82-9f50-716e785d6443-6903a306_demo_testing_campaign_info_test_test.csv",
                    "headers": {                    
                    }
                },
                "config": {
                    # "source_model": "campaign_user_detail",
                    "batch_size": 500,
                    "offset": 0,
                    "filters": {"active": True},
                    "retry_policy": {"max_retries": 3, "backoff": "exponential"}
                },
                "field_mapping": {
                    "mobile_number":"Phone Number",
                    "name": "Name"
                },
                "metadata": {
                    "description": "Internal GryD user database",
                    "owner": "automation_team"
                },
                "campaign_users": [
                    {
                        "name": "nikit",
                        "name": "Nitesh",
                        "car_model":"Breeza",
                        "mobile_number": "9348927558"
                    },
                
                ],
                "_skip_sent_message":False
            },

            
            "template_type": "text_template",
            "template_id": "01k8rbeesdpz8p06v4706r4xqy",
            "template_variables": ["name","car_model"],
            "template_buttons_payload": [
                "book-service-reminder-yes",
                "book-service-reminder-No"
            ],

            "run_async":False

            
        }
    )
   
    pass

