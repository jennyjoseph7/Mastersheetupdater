
import os
import sys
_voice_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _voice_root not in sys.path:
    sys.path.insert(0, _voice_root)
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp
from gryd_worker.gryd_routes import payload_decorator
#from models import model as base_model
from ai_service import ai_service_app
import config
import datetime
import pytz
import time

from conversation import converse
# from communication.connectors.communication_helpers import  generate_uid, get_communication_credential
from communication.common_functions import generate_uid, get_communication_credential
from communication.connectors.connector_whatsapp import post_contact_status

from autocrm_db_helper import get_pg_connector

logger = hp.get_logger(__name__)


gryd.SERVICE = config.AUTOCRM_VOICE_SERVICE_NAME
gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(__name__)

country_codes = {
    "IN": "+91",
    "US": "+1",
    "UK": "+44",
    "CA": "+1",
    "AU": "+61",
    "DE": "+49",
    "FR": "+33",
    "ES": "+34",
    "IT": "+39",
    "BR": "+55",
    "MX": "+52",
    "RU": "+7",
    "JP": "+81",
    "CN": "+86"
}


provider_country_codes_format = {
    "tatatele": lambda cc: cc.lstrip("+"),
    "twilio": lambda cc: cc,
}

def format_phone_number(phone_number, provider = "tatatele", country_code = "IN"):
    phone_number = phone_number.strip().replace(" ", "").replace("-", "")[-10:]
    
    cc = provider_country_codes_format[provider](country_codes.get(country_code, "+91"))
    phone_number = f"{cc}{phone_number}"
    return phone_number


@gryd.is_a_task(function_name="trigger_voice_call")
def trigger_voice_call(*args, **kwargs):
    """
    Initiates a call to the user and prepares session-related data.

    This function creates and stores data for both the session and the user (person) 
    until the call successfully connects. The stored data is later used to generate 
    the dynamic prompt for the call.

    The data structure typically includes fields such as:
        {
            "user_name": "<string>",
            "<vehicle_specific>": "<value>",
            "campaign_id": "<string>",
            "campaign_workflow_id": "<string>"
        }

    The function ensures that the call session context is available to the voice agent 
    or downstream system that uses the generated prompt.

    Args:
        ...: (Describe input parameters here)

    Returns:
        None or dict: (Describe return value if applicable)
    """
    
    #temporary changes-
    #4c99d5ea-4441-3ce6-841f-de5d7585b3b7  - campaign id for testing
    dealership_provider_map = {
        "us-dealership-united-states": ("elevanlab", "agent_6501kg4h48mbfhp8cryeh1a66t3j"),
        "sales-dealership1-india": ("tatatele", "agent_5701ka8618cbfxcbdp4wg6xb3x23"),  #stellantis
        "stellantis-india": ("tatatele", "agent_5701ka8618cbfxcbdp4wg6xb3x23"),
        "dave-ai-sociograph-solutions-india": ("tatatele", "agent_5701ka8618cbfxcbdp4wg6xb3x23"),
        "ambal-auto-india": ("tatatele", "agent_0501k747d7s6e3xv5t3xew1rn217")
    }
    import json
    #TODO: Get agent number from dealership model and add in session_data in agent_number
    # logger.info(f"Received request to trigger voice call with args: {args}, kwargs: {json.dumps(kwargs,indent=4)}")
    user_data = kwargs.get("user_data", {})
    logger.info(f"Triggering voice call with user data: {user_data}")

    if not all (k in user_data for k in ("campaign_id", "campaign_type", "mobile_number")):
        logger.error("Missing required user data fields: 'campaign_id', 'campaign_type', 'mobile_number'")
        yield {
            "error": "Missing required user data fields: 'campaign_id', 'campaign_type', 'mobile_number'"
        }

    person_model = gryd.base_model.Model("person", config.AUTOCRM_APP_ENTERPRISE_ID)
    person_obj = person_model.list(**{"phone_number":user_data.get("mobile_number")}).get('data',{})
    person_obj = person_obj[0] if person_obj else {}
    if not person_obj:
        logger.error(f"No person found with mobile number: {user_data.get('mobile_number')}")

        person_obj = person_model.post(
            {
                "phone_number": format_phone_number(user_data.get("mobile_number")),
                "name": user_data.get("customer_name", "Unknown"),
                "email": user_data.get("email"),
            }
        )
        logger.info(f"Created new person object: {person_obj}")

    campaign_type = user_data.get("campaign_type")
    lead_id= user_data.get("lead_id")
    channel = user_data.get("channel","voice_phone")
    campaign_id = user_data.get("campaign_id")
    CONFIG_D = {
        "pre-sales": {
            "table": "pre_sales_lead",
            "pk": "pre_sales_lead_id",
            "model": "pre_sales_campaign",
        },
        "post-sales": {
            "table": "post_sales_lead",
            "pk": "post_sales_lead_id",
            "model": "post_sales_campaign",
        },
    }

    config_data = CONFIG_D.get(campaign_type)
    
    session_model = gryd.base_model.Model(config.SESSION_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
    if lead_id and config_data:
        with get_pg_connector() as pg:
            l=list(pg.list(config_data.get("table"),{f"{config_data.get('pk')}": lead_id}))
            if not l:
                logger.info(f"No lead found for lead_id: {lead_id} in model: {config_data.get('table')}")
            l=l[0] if l else {}
            l_person_name = l.get("person_name",None)
            l_campaign_obj_name = l.get("campaign_objective_name",None)
            l_campaign_name = l.get("campaign_name",None)
        
            session_obj = {
                "user_id": person_obj.get("user_id"),
                "campaign_id": campaign_id,
                "campaign_type": campaign_type,
                "lead_id": lead_id,
                "status":"attempted",
                "channel": channel,
                "person_name": l_person_name or None,
                "campaign_objective_name": l_campaign_obj_name or None,
                "campaign_name": l_campaign_name or None,
                "dealership_id": user_data.get("dealership_id"),
                "phone_number":format_phone_number(user_data.get("mobile_number")),
                "start_time": hp.epoch()
                
            }
            session_data = session_model.post(session_obj)

            #if agent_id passed in task kwargs
            agent_config = {
                "voice_agent_id": user_data.get("agent_id")
            }

            logger.info(f"Session created with data: {session_data}")
            if config_data:
                pg.update(
                    config_data["table"],
                    config_data["pk"],
                    lead_id,
                    {"last_session_channel": channel},
                )
                logger.info(
                    f"Updated last_session_channel for {config_data['pk']}: {lead_id} "
                    f"with channel: {channel}"
                )

                campaign_model = gryd.base_model.Model(
                    config_data["model"],
                    config.AUTOCRM_APP_ENTERPRISE_ID,
                )
                campaign_data = campaign_model.get(campaign_id)

                agent_config.update({
                    k: v
                    for k, v in campaign_data.items()
                    if k.startswith("voice_") and v
                })

    if user_data.get("generate_prompt", True):
        for x in converse.get_primary_prompt(*args, **{
            "session_id" : session_data['session_id'],
            "session_data" : session_data,
            "channel":"voice_phone"
        }):
            if x.get('prompt'):
                session_data["prompt"] = x.get('prompt')
                break

    
    user_data.update(session_data)
    
    # credentials_model = gryd.base_model.Model("communication_credential", config.AUTOCRM_APP_ENTERPRISE_ID)

    # credentials = credentials_model.list(**{
    #     "dealership_id": user_data.get("dealership_id"),
    #     "channel": "voice_phone"
    # }).get("data", [])

    # voice_id = user_data.get("voice_id",None)
    voice_start_language= user_data.get("voice_start_language","en")
    voice_agent_id= user_data.get("voice_agent_id",None)
    logger.info(f"Received Voice_agent_id from user data (i.e from campaign model): {voice_agent_id}")
    credentials = get_communication_credential(dealership_id = user_data.get("dealership_id"), channel = "voice_phone")

    logger.info(f"Credentials found for dealership_id {user_data.get('dealership_id')}: {credentials}")
    logger.info(f"Voice start language---{voice_start_language}")

    if credentials:
        provider = credentials.get("provider_name", "tatatele").replace("-", "").strip().lower()
        session_data["agent_id"] = voice_agent_id if voice_agent_id else credentials.get("bot_name")
        session_data["language"] = voice_start_language if voice_start_language else "en"
        session_data["provider_credentials"] = {
            "tatatele_phone_number_api_key": credentials.get("auth_token")
        }
        session_data["provider"] = provider
        session_data["agent_number"] = credentials.get("sender") 
    else:
        logger.warning(f"No credentials found for dealership_id {user_data.get('dealership_id')}, channel voice_phone")  
    # else:
    #     #temporary provider selection logic
    #     provider = "tatatele"
    #     logger.info(f"Using dealership_id: {user_data.get('dealership_id')} for provider mapping. {list(dealership_provider_map.keys())}")
    #     if user_data.get("dealership_id") in list(dealership_provider_map.keys()):
    #         provider = dealership_provider_map[user_data.get("dealership_id")][0]
    #         session_data["agent_id"] = dealership_provider_map[user_data.get("dealership_id")][1]
    #     #----------end-----------

        #provider = user_data.get("provider_name", provider).replace("-", "").strip().lower()


    logger.info(f"Session for Voice Call: {session_data}")

    from voice import providers
    response = providers.make_call(provider, session_data, *args, **kwargs)
    logger.info(f"Response from provider {provider}: {response}")
    yield {
        "success": response.get("success"),
        "call_sid": response.get("call_sid"),
        "message": response.get("message"),
        "session_id":session_data["session_id"],
        "user_id":session_data["user_id"],
        "campaign_id": session_data["campaign_id"],
    }

    post_contact_status_voice(user_data, message_id=session_data["session_id"])

    if provider.lower() in ["twilio", "elevanlab"]:
        #as we are making direct call from provider.
        return response

    timeout = time.time() + float(user_data.get("call_timeout", 600))  # 10 minutes

    attempted_timeout = time.time() + float(user_data.get("attempted_status_timeout", 30))  # 0.5 minutes

    while time.time() < timeout:
        time.sleep(5)
        with get_pg_connector() as pg:
            statuses = list(pg.list_order_by("contact_status", {"message_id": session_data["session_id"]}, order_by="created"))
            if not statuses:
                logger.info(f"No contact status object found yet for message_id: {session_data['session_id']}, waiting...")
                continue
            

            #making this change as not able to debug why its sending status busy after status reached to state contacted - No resolution found yet
            if len(statuses) > 2:
                for s in statuses:
                    if s.get("provider_status") in ["contacted"]:
                        logger.info(f"Call ended with status 'contacted' for: {session_data.get('phone_number')}, message_id: {session_data['session_id']}")
                        return

            latest = statuses[0]
            logger.info(f"Latest contact status for message_id: {session_data['session_id']} is: {latest}")
            if latest["provider_status"] in ["attempted"]:
                if time.time() > attempted_timeout:
                    logger.info(f"Call seems to be not connecting for: {session_data.get('phone_number')}, message_id: {session_data['session_id']}, status: {latest['provider_status']}. Ending session.")
                    post_contact_status_voice(session_id = session_data["session_id"], message_id=session_data["session_id"], **{"status": "busy"})
                    gryd.create_async_task(
                        "end_session_and_post_process",
                        config.AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME,
                        args  = [],
                        kwargs={
                            "session_id": session_data["session_id"],
                            "additional_dict":{
                                "status": "busy"
                            }
                        }
                    )
                    return
                logger.info(f"Call is ongoing for, still connecting: {session_data.get('phone_number')}, message_id: {session_data['session_id']}, status: {latest['provider_status']}")
                continue
            elif latest["provider_status"] in ["reached"]:
                logger.info(f"Call reached with status '{latest['provider_status']}' for: {session_data.get('phone_number')}, message_id: {session_data['session_id']}")
                continue
            elif latest["provider_status"] in ["contacted"]:
                logger.info(f"Call ended with status '{latest['provider_status']}' for: {session_data.get('phone_number')}, message_id: {session_data['session_id']}")
                return
            
            logger.info(f"Call is ongoing for: {session_data.get('phone_number')}, message_id: {session_data['session_id']}, status: {latest['provider_status']}")
            



@gryd.is_a_task(function_name="post_billing_object")
def post_billing_object(status, session_id, duration = 1, *args, **kwargs):

    tme = hp.now(as_datetime=False)
    timmm = hp.time()

    session_model = gryd.base_model.Model(config.SESSION_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
    session_data = session_model.get(session_id)

    campaing_model = gryd.base_model.Model(session_data.get('campaign_model'), config.AUTOCRM_APP_ENTERPRISE_ID)
    campaign_data = campaing_model.get(session_data.get("campaign_id"))

    #campaign_id and channel in descriptin
    #maintaining credits - soham's task 

    obj = {
        "created" : timmm,
        "updated" : timmm,
        "transaction_date" : tme,
        "transaction_type" : "debit",
        "item_description" : f"{session_data.get('campaign_type', 'unknown')} - {campaign_data.get('campaign_objective_name', 'unknown')} - {campaign_data.get('campaign_name', 'unknown')} - {session_data.get('channel', 'unknown')} - {session_data.get('provider', 'twilio')} - {session_data.get('phone_number', 'unknown')}",
        "dealership_id" : session_data.get("dealership_id"),
        "currency" : "credits",
        "status" : "success",
        "campaign_id": session_data.get('campaign_id'),
        "channel": session_data.get('channel', 'voice_phone'),
    }
    
    x = {}
    if status in ["completed"]:       
        x = {
        "item_name" : config.AUTOCRM_CALL_COMPLETED_ITEM,
        "item_quantity" : duration,
        "item_price" : config.AUTOCRM_CALL_COMPLETED_PRICE,
        "item_units" : config.AUTOCRM_CALL_COMPLETED_UNITS,
        }
    elif status in ["reached"]:
        x = {
        "item_name" : config.AUTOCRM_CALL_CONNECTED_ITEM,
        "item_quantity" : 1,
        "item_price" : config.AUTOCRM_CALL_CONNECTED_PRICE,
        "item_units" : config.AUTOCRM_CALL_CONNECTED_UNITS,
        }

    obj.update(x)
    
    logger.info(f"Calling task post_billing : {obj}")
    gryd.create_async_task(
        "post_billing",
        config.AUTOCRM_CORE_SERVICE_NAME,
        args = [
            obj["dealership_id"],
            obj["transaction_type"],
            obj["item_name"],
            obj["item_description"],
            obj["transaction_date"],
            obj["item_quantity"],
            obj["item_price"],
            obj["item_units"],
            obj["currency"],
            obj["campaign_id"],
            obj["channel"]
        ]
    )
    # m = gryd.gryd.base_model.Model(config.BILLING_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
    # return m.post(obj)
   
def post_contact_status_voice(session_data = None, session_id = None, message_id=None, **additiona_params):
    if not session_data and session_id:
        session_model = gryd.base_model.Model(config.SESSION_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
        session_data = session_model.get(session_id)

    if additiona_params:
        session_data.update(additiona_params)

    logger.info(f'Posting contact status with payload: {session_data}: status: {session_data.get("status")}, message_id: {message_id}, session_id: {session_id}')
    attrs=["phone_number", "lead_id","campaign_id","campaign_type","email","dealership_id","channel","campaign_model"]
    payload = {a:session_data.get(a) for a in attrs if session_data.get(a)}
    payload["provider_status"] = session_data.get("status", "attempted")
    payload["message_id"] = message_id or generate_uid(session_data)
    
    logger.info(f"Constructed payload for contact status: {payload.get('provider_status')}, message_id: {payload.get('message_id')}")
    if payload.get("provider_status") == "attempted":
        post_contact_status(**payload)
    else: 
        post_contact_status(message_id, **payload)


@gryd.is_a_task(function_name="post_lanuage_change_func")
def post_lanuage_change_func(*args, **kwargs):    
    language = kwargs.get("changed_language")
    session_data = kwargs.get("session_data", {})
    lead_model_name = session_data.get("lead_model")
    lead_id = session_data.get("lead_id")
    with get_pg_connector() as pg:
        x = pg.update(
            lead_model_name,
            f"{lead_model_name}_id",
            lead_id,
            {"follow_up_language": language}
        )
        logger.info(f"Updated lead with new language preference: {x}")

def post_lanuage_change(session_data, changed_language):
    # logger.info(f"Calling task post_lanuage_change_func with session_data: {session_data}, changed_language: {changed_language}")
    gryd.create_async_task(
        "post_lanuage_change_func",
       config.AUTOCRM_VOICE_SERVICE_NAME,
        args = [],
        kwargs = {
            "changed_language": changed_language,
            "session_data": session_data
        }
    )

def delete_extra_status(campaign_ids):
    i = 0

    if i > len(campaign_ids):
        logger.info("Completed one full cycle of checking all campaign ids")
        return
    try:
        for campaign_id in campaign_ids:
            logger.info(f"Checking campaign_id: {campaign_id} for extra busy status: Attempt {i+1}")
            session_model = gryd.base_model.Model("session", config.AUTOCRM_APP_ENTERPRISE_ID)
            sessions = session_model.list(**{"campaign_id": campaign_id, "status": "busy", "_as_option": True, "_filter_attributes": ["session_id", "call_recording", "status"]})
            logger.info(f"Sessions for campaign_id {campaign_id}: {sessions}")
            session_ids = [s.get("session_id") for s in sessions if s.get("call_recording") and s.get("status") == "busy"]
            logger.info(f"Session ids: {session_ids}")
            for session_id in session_ids:
                time.sleep(5)
                with get_pg_connector() as pg:
                    statuses = list(pg.list_order_by("contact_status", {"message_id": session_id}, order_by="created"))
                    logger.info(f"Statuses: {statuses} and length: {len(statuses)}")
                    if len(statuses) > 3:
                        for s in statuses:
                            if s.get("provider_status") in ["busy"]:
                                logger.info(f"Deleting busy contact status for: {session_id}, contact_status_id: {s.get('contact_status_id')}")
                                gryd.base_model.Model("contact_status", config.AUTOCRM_APP_ENTERPRISE_ID).delete(s.get("contact_status_id"))

                                # end_session(**{
                                # "session_id": session_id,
                                # "additional_dict":{
                                #     "status": "completed"
                                # }})
            i += 1
    except Exception as e:
        logger.error(f"Error in delete_extra_status: {e}")
        delete_extra_status(campaign_ids)
    return


if __name__ == "__main__":
    pass