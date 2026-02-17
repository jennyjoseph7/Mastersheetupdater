
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp
from gryd_worker.gryd_routes import payload_decorator
#from models import model as base_model
from ai_service import ai_service_app
import config
import datetime
import pytz
import time

from conversation import converse
from communication.connectors.communication_helpers import end_session as end_voice_session, generate_uid
#from communication.connectors.whatsapp_connectors.source_connectors import BaseWebhookConverter
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
            "campaign_workflow_id": "<string>",
            "agent_number": <the caller number>,
            "dealership_id": <the dealership id for which we are sending the info"
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

    #TODO: Get agent number from dealership model and add in session_data in agent_number
   
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
                "phone_number": user_data.get("mobile_number", user_data.get("phone_number")),
                "name": user_data.get("customer_name", "Unknown"),
                "email": user_data.get("email"),
            }
        )
        logger.info(f"Created new person object: {person_obj}")

        

    session_model = gryd.base_model.Model(config.SESSION_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
    session_obj = {
        "user_id": person_obj.get("user_id"),
        "campaign_id": user_data.get("campaign_id"),
        "campaign_type": user_data.get("campaign_type"),
        "lead_id": user_data.get("lead_id"),
        "status":"attempted",
        "channel": user_data.get("channel", "voice_phone"),
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
    if session_data.get("campaign_type") == "pre-sales":
        pre_sales_lead_model = gryd.base_model.Model("pre_sales_lead", config.AUTOCRM_APP_ENTERPRISE_ID)
        r = pre_sales_lead_model.update(
            session_data.get("lead_id"),
            {"last_session_channel":session_data.get("channel")},
            internal=True,
            _previous_instance={}
        )

        logger.info(f"Pre-sales lead model patch response: {r}")
        pre_sales_campaign_model = gryd.base_model.Model("pre_sales_campaign", config.AUTOCRM_APP_ENTERPRISE_ID)
        pre_sales_campaign_model_data = pre_sales_campaign_model.get(session_data.get("campaign_id"))
        agent_config.update({
            k : v for k, v in pre_sales_campaign_model_data.items() if k.startswith("voice_") and v
        })
    elif session_data.get("campaign_type") == "post-sales":
        post_sales_lead_model = gryd.base_model.Model("post_sales_lead", config.AUTOCRM_APP_ENTERPRISE_ID)
        r = post_sales_lead_model.update(
            session_data.get("lead_id"),
            {"last_session_channel":session_data.get("channel")},
            internal=True,
            _previous_instance={}
        )
        logger.info(f"Post-sales lead model patch response: {r}")

        post_sales_campaign_model = gryd.base_model.Model("post_sales_campaign", config.AUTOCRM_APP_ENTERPRISE_ID)
        post_sales_campaign_model_data = post_sales_campaign_model.get(session_data.get("campaign_id"))
        agent_config.update({
            k : v for k, v in post_sales_campaign_model_data.items() if k.startswith("voice_") and v
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

    #temporary provider selection logic
    provider = "tatatele"
    logger.info(f"Using dealership_id: {user_data.get('dealership_id')} for provider mapping. {list(dealership_provider_map.keys())}")
    dealership_id = user_data.get('dealership_id')
    default_agent = ("tatatele", "agent_5701ka8618cbfxcbdp4wg6xb3x23")
    if user_data.get("dealership_id") in list(dealership_provider_map.keys()):
        provider = user_data.get('provider') or dealership_provider_map.get(dealership_id, default_agent)[0]
        session_data["agent_id"] = user_data.get('agent_id') or dealership_provider_map.get(dealership_id,default_agent)[1]
        if user_data.get('agent_number')
            session_data["agent_number"] = user_data.get("agent_number")
    #----------end-----------

    #provider = user_data.get("provider_name", provider).replace("-", "").strip().lower()
    logger.info(f"Session for Voice Call: {session_data}")

    from voice import providers
    response = providers.make_call(provider, session_data, *args, **kwargs)

    yield {
        "success": response.get("success"),
        "call_sid": response.get("call_sid"),
        "message": response.get("message"),
        "session_id":session_data["session_id"],
        "user_id":session_data["user_id"],
        "campaign_id": session_data["campaign_id"],
    }

    post_contact_status_voice(user_data, message_id=session_data["session_id"])

    from autocrm_db_helper import get_pg_connector

    timeout = time.time() + float(user_data.get("call_timeout", 600))  # 10 minutes

    attempted_timeout = time.time() + float(user_data.get("attempted_status_timeout", 30))  # 0.5 minutes

    while time.time() < timeout:
        time.sleep(5)
        with get_pg_connector() as pg:
            statuses = list(pg.list_order_by("contact_status", {"message_id": session_data["session_id"]}, order_by="created"))
            if not statuses:
                logger.info(f"No contact status object found yet for message_id: {session_data['session_id']}, waiting...")
                continue
            latest = statuses[0]
            if latest["provider_status"] in ["attempted"]:
                if time.time() > attempted_timeout:
                    logger.info(f"Call seems to be not connecting for: {session_data.get('phone_number')}, message_id: {session_data['session_id']}, status: {latest['provider_status']}. Ending session.")
                    post_contact_status_voice(session_id = session_data["session_id"], message_id=session_data["session_id"], **{"status": "busy"})
                    end_session(**{
                        "session_id": session_data["session_id"],
                        "additional_dict":{
                            "history": [],
                            "status": "busy"
                    }
                    })
                    return
                logger.info(f"Call is ongoing for, still connecting: {session_data.get('phone_number')}, message_id: {session_data['session_id']}, status: {latest['provider_status']}")
                continue
            elif latest["provider_status"] in ["contacted", "reached"]:
                logger.info(f"Call ended with status '{latest['provider_status']}' for: {session_data.get('phone_number')}, message_id: {session_data['session_id']}")
                return
            
            logger.info(f"Call is ongoing for: {session_data.get('phone_number')}, message_id: {session_data['session_id']}, status: {latest['provider_status']}")
            continue




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


def post_history(session_id, session_history):
    import time
    session_model = gryd.base_model.Model(config.SESSION_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
    session_data = session_model.get(session_id)

    agent_msgs = [d for d in session_history if d.get("role") == "agent"]
    user_msgs = [d for d in session_history if d.get("role") == "user"]

    if len(agent_msgs) != len(user_msgs):
        logger.error(
            f"post_history: agent ({len(agent_msgs)}) and user ({len(user_msgs)}) message counts do not match"
        )

    max_len = max(len(user_msgs), len(agent_msgs))
    history = []
    for i in range(max_len):
        u = user_msgs[i] if i < len(user_msgs) else {}
        a = agent_msgs[i] if i < len(agent_msgs) else {}
        tme = hp.time()
        history.append({
            "reply_to": generate_uid(u) if u else gryd.hp.make_uuid3(str(time.time())),
            "customer_response": u.get("message", ""),
            "request_data": {
                "customer_response": u.get("message", "")
            },
            "session_id": session_data.get("session_id"),
            "user_id": session_data.get("user_id"),
            "responses": [
                {
                    "intent": "llm_response",
                    "placeholder": a.get("message", ""),
                    "index": i + 1,
                    "created": tme,
                    "updated": tme
                }
            ]
        })

    logger.info(f"Calling task post_all_messages_for_session with history: {history}")
    gryd.await_result(
        "post_all_messages_for_session",
        config.AUTOCRM_CONVERSATION_SERVICE_NAME,
        args=[],
        kwargs={
            "history": history
        }
    )

def post_actions(session_id):
   logger.info(f'Calling post session process task for session_id: {session_id}')
   gryd.create_async_task(
       "post_session_process",
       config.AUTOCRM_CONVERSATION_SERVICE_NAME, 
       args = [],
       kwargs = {
           "session_id" : session_id
       }
   )

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
    gryd.create_async_task(
        "post_contact_status", 
        config.AUTOCRM_COMMUNICATION_SERVICE_NAME, 
        kwargs=payload)
    #make this normal function


@gryd.is_a_task(function_name="end_voice_session")
def end_session(*args, **kwargs):
    logger.info(f"Ending session with args: {args}, kwargs: {kwargs}")
    return end_voice_session(*args, **kwargs)



if __name__ == "__main__":


    #provider based on dealershiop id-

    #+919920297124 -Ankita +919833885948- Arshiya

    data = {'_is_testing': False,
    'ctas': ['book-test-drive'],
    'mobile_number': '918850988794',



    'created': 1771122373.4420457,
    'updated': 1771123721.3710845,
    'channels': ['voice_phone'],
    'end_date': 1771718400,
    'languages': ['english'],
    'region_id': 'india',
    'start_date': 1771113600,
    'campaign_id': 'fb72d256-2294-3a32-8c4c-80a3e31c9eec',
    'region_name': 'India',
    'urgency_hook': 'Slots are filling up fast — book your test drive now!',
    'campaign_name': 'Get Behind the Wheel!',
    'campaign_type': 'pre-sales',
    'cost_per_lead': 0.0,
    'dealership_id': 'sales-dealership1-india',
    'campaign_offer': "Don't just imagine driving your dream car—experience it! Book a test drive today and feel the difference. Our team is ready to assist you in making the best choice for your next vehicle.",
    'campaign_status': 'Active',
    'dealership_name': 'Sales Dealership1',
    'number_targeted': 1,
    'budget_allocated': 8.56,
    'supported_brands': ['jeep-jeep-india', 'citroen-citroen-india'],
    'vehicle_category': 'Passenger Vehicle',
    'campaign_sub_type': 'other',
    'conversation_tone': 'Friendly',
    'campaign_description': "Don't just imagine driving your dream car—experience it! Book a test drive today and feel the difference. Our team is ready to assist you in making the best choice for your next vehicle.",
    'campaign_user_source': {'source_type': 'default',
    'campaign_users': [{'lead_id': 'nikit-918850988794-sales-dealership1-india-fb72d256-2294-3a32-8c4c-80a3e31c9eec',
        'mobile_number': '918850988794',
        'customer_name': 'Nikit',
        'email': None,
        'contact_channel': 'voice_phone',
        'template_id': None,
        'template_details': None}],
    'field_mapping': {'lead_id': 'lead_id',
    'mobile_number': 'mobile_number',
    'customer_name': 'customer_name',
    'template_id': 'template_id',
    'template_details': 'template_details',
    'contact_channel': 'contact_channel',
    'reg_num': 'reg_num'},
    'config': {'batch_size': 100, '_skip_sent_message': True}},
    'campaign_objective_id': 'pre-sales-test-drive-booking-nexa-delhi-south-nexa-dealer-group-north-india',
    'campaign_objective_name': 'Test Drive Booking',
    'conversion_rate_percent': 0.0,
    'region_level_guardrails': '- Maintain professional communication standards. Ensure clear communication. Respect regional languages. Provide local language support. Be mindful of potential network issues or poor call quality in India \\n -Trigger calls between 10am to 7pm.',
    'region_level_guidelines': 'Avoid slang, sarcasm, or culturally sensitive humor. Use polite, respectful, and neutral tone. Prefer simple sentences suitable for Tier-2/Tier-3 customers',
    'why_user_should_avail_this': 'Experience the premium features and performance of NEXA vehicles with no obligation',
    'other_important_information': 'Test drives are free and include home pickup/drop service. No pressure sales approach.',
    'supported_brands_guidelines': {},
    'reasons_for_non_applicability': 'Already purchased, outside service area, not eligible for test drive',
    'campaign_objective_description': 'Generate test drive bookings by encouraging potential customers to experience the vehicle firsthand',
    'reasons_users_may_not_be_interested': 'Not ready to purchase, already test driven, preference for other models',
    'channel': 'voice_phone',
    'sender': None,
    'provider_name': 'tata-tele',
    'template_message': None,
    'lead_id': 'nikit-918850988794-sales-dealership1-india-fb72d256-2294-3a32-8c4c-80a3e31c9eec',
    'customer_name': 'Nikit',
    'email': None,
    'contact_channel': 'voice_phone',
    'template_id': None,
    'template_details': None}

        #trigger_voice_call(**{"user_data":data})

    gryd.create_async_task(
        "trigger_voice_call",
        config.AUTOCRM_VOICE_SERVICE_NAME,
        args = [],
        kwargs = {
            "user_data": data
        }
    )


    # for x in trigger_voice_call(**{"user_data":data}):
    #     print(x)

    # from gryd_worker import gryd
    # from communication.connectors.load_providers import load_providers
        
    # load_providers(["whatsapp","email"])
    # gryd.create_async_task(
    #         "process_single_lead",
    #         "autocrm-campaign",
    #         args=["voice_phone", "tn37dm7087-ambal-auto-scheduled-service-reminder","post-sales","74f260b8-e8dc-3c52-ab8d-31bd0fc49943"],
    #         kwargs={}
    #     )


{'_is_testing': False, 'ctas': ['book-test-drive'], 'created': 1771122373.4420457, 'updated': 1771122534.6489363, 'channels': ['voice_phone'], 'end_date': 1771718400, 'languages': ['english'], 'region_id': 'india', 'start_date': 1771113600, 'campaign_id': 'fb72d256-2294-3a32-8c4c-80a3e31c9eec', 'region_name': 'India', 'urgency_hook': 'Slots are filling up fast — book your test drive now!', 'campaign_name': 'Get Behind the Wheel!', 'campaign_type': 'pre-sales', 'cost_per_lead': 0.0, 'dealership_id': 'sales-dealership1-india', 'campaign_offer': "Don't just imagine driving your dream car—experience it! Book a test drive today and feel the difference. Our team is ready to assist you in making the best choice for your next vehicle.", 'campaign_status': 'Active', 'dealership_name': 'Sales Dealership1', 'number_targeted': 1, 'budget_allocated': 8.56, 'supported_brands': ['jeep-jeep-india', 'citroen-citroen-india'], 'vehicle_category': 'Passenger Vehicle', 'campaign_sub_type': 'other', 'conversation_tone': 'Friendly', 'campaign_description': "Don't just imagine driving your dream car—experience it! Book a test drive today and feel the difference. Our team is ready to assist you in making the best choice for your next vehicle.", 'campaign_user_source': {'source_type': 'default', 'campaign_users': [{'lead_id': 'nikit-918850988794-sales-dealership1-india-fb72d256-2294-3a32-8c4c-80a3e31c9eec', 'mobile_number': '918850988794', 'customer_name': 'Nikit', 'email': None, 'contact_channel': 'voice_phone', 'template_id': None, 'template_details': None}], 'field_mapping': {'lead_id': 'lead_id', 'mobile_number': 'mobile_number', 'customer_name': 'customer_name', 'template_id': 'template_id', 'template_details': 'template_details', 'contact_channel': 'contact_channel', 'reg_num': 'reg_num'}, 'config': {'batch_size': 100, '_skip_sent_message': True}}, 'campaign_objective_id': 'pre-sales-test-drive-booking-nexa-delhi-south-nexa-dealer-group-north-india', 'campaign_objective_name': 'Test Drive Booking', 'conversion_rate_percent': 0.0, 'region_level_guardrails': '- Maintain professional communication standards. Ensure clear communication. Respect regional languages. Provide local language support. Be mindful of potential network issues or poor call quality in India \\n -Trigger calls between 10am to 7pm.', 'region_level_guidelines': 'Avoid slang, sarcasm, or culturally sensitive humor. Use polite, respectful, and neutral tone. Prefer simple sentences suitable for Tier-2/Tier-3 customers', 'why_user_should_avail_this': 'Experience the premium features and performance of NEXA vehicles with no obligation', 'other_important_information': 'Test drives are free and include home pickup/drop service. No pressure sales approach.', 'supported_brands_guidelines': {}, 'reasons_for_non_applicability': 'Already purchased, outside service area, not eligible for test drive', 'campaign_objective_description': 'Generate test drive bookings by encouraging potential customers to experience the vehicle firsthand', 'reasons_users_may_not_be_interested': 'Not ready to purchase, already test driven, preference for other models', 'channel': 'voice_phone', 'sender': None, 'provider_name': 'tata-tele', 'template_message': None, 'lead_id': 'nikit-918850988794-sales-dealership1-india-fb72d256-2294-3a32-8c4c-80a3e31c9eec', 'mobile_number': '918850988794', 'customer_name': 'Nikit', 'email': None, 'contact_channel': 'voice_phone', 'template_id': None, 'template_details': None}


#answered by agent

{
    "uuid": "69882f281b4b0",
    "call_to_number": "+919594778746",
    "caller_id_number": "+918065251305",
    "start_stamp": "2026-02-08 12:07:18",
    "answer_agent_number": "+919594778746",
    "call_id": "h11.08-1770532638.2135633",
    "billing_circle": {
        "operator": "Idea",
        "circle": "Mumbai"
    },
    "call_status": "queued",
    "direction": "click_to_call",
    "customer_no_with_prefix ": "+919594778746",
    "ref_id": "5c4113fa-538e-422b-8925-685bdc6915c0",
    "custom_identifier": "1ca7c3d1-9545-3413-80c2-8956b256e716",
    "status": "Answered by agent"
}





