
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp
from gryd_worker.gryd_routes import payload_decorator
from models import model as base_model
from ai_service import ai_service_app
import config
import datetime
import pytz
from conversation import converse
from communication.connectors.whatsapp_connectors.source_connectors import BaseWebhookConverter
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
        "ambal-auto-india": ("tatatele", "agent_0501k747d7s6e3xv5t3xew1rn217")
    }
   
    user_data = kwargs.get("user_data", {})
    logger.info(f"Triggering voice call with user data: {user_data}")

    if not all (k in user_data for k in ("campaign_id", "campaign_type", "mobile_number")):
        logger.error("Missing required user data fields: 'campaign_id', 'campaign_type', 'mobile_number'")
        yield {
            "error": "Missing required user data fields: 'campaign_id', 'campaign_type', 'mobile_number'"
        }

    #temporary 
    person_model = base_model.Model("person", config.AUTOCRM_APP_ENTERPRISE_ID)

    person_obj = person_model.list(**{"phone_number":user_data.get("mobile_number")}).get('data',{})
    person_obj = person_obj[0] if person_obj else {}
     #

    if not person_obj:
        logger.error(f"No person found with mobile number: {user_data.get('mobile_number')}")
        yield {
            "error": f"No person found with mobile number: {user_data.get('mobile_number')}"
        }
    user_data["user_id"] = person_obj.get("user_id","a4abae7d832632c7")

    session_model = base_model.Model(config.SESSION_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
    session_obj = {
        "user_id": user_data.get("user_id"),
        "campaign_id": user_data.get("campaign_id"),
        "campaign_type": user_data.get("campaign_type"),
        "lead_id": user_data.get("lead_id"),
        "status":"attempted",
        "channel": user_data.get("channel", "voice_phone"),
        "phone_number":format_phone_number(user_data.get("mobile_number")),
        "start_time": hp.epoch()
        
    }
    session_data = session_model.post(session_obj)

    session_data["room_id"] = user_data.get("room_id", "ambal_auto")
    session_data["agent_id"] = user_data.get("agent_id")    
    if user_data.get("generate_prompt", True):
        for x in converse.get_primary_prompt(*args, **{
            "session_id" : session_data['session_id'],
            "session_data" : session_data,
            "channel":"voice_phone"
        }):
            if x.get('prompt'):
                session_data["prompt"] = x.get('prompt')
                break

    
    logger.info(f"Session for Voice Call: {session_data}")
    user_data.update(session_data)

    #temporary provider selection logic
    provider = "tatatele"
    logger.info(f"Using dealership_id: {user_data.get('dealership_id')} for provider mapping. {list(dealership_provider_map.keys())}")
    if user_data.get("dealership_id") in list(dealership_provider_map.keys()):
        provider = dealership_provider_map[user_data.get("dealership_id")][0]
        session_data["agent_id"] = dealership_provider_map[user_data.get("dealership_id")][1]
    #----------end-----------

    #provider = user_data.get("provider_name", provider).replace("-", "").strip().lower()
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

    post_contact_status_voice(user_data, message_id=response.get("call_sid"))


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
        "currency" : config.AUTOCRM_CURRENCY,
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
        "item_total" : duration*config.AUTOCRM_CALL_COMPLETED_PRICE,
        "item_units" : config.AUTOCRM_CALL_COMPLETED_UNITS,
        }
    elif status in ["queued", "contacted"]:
        x = {
        "item_name" : config.AUTOCRM_CALL_CONNECTED_ITEM,
        "item_quantity" : 1,
        "item_price" : config.AUTOCRM_CALL_CONNECTED_PRICE,
        "item_total" : config.AUTOCRM_CALL_CONNECTED_PRICE,
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
            obj["currency"]
        ]
    )
    # m = gryd.base_model.Model(config.BILLING_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
    # return m.post(obj)


def post_history(session_id, session_history):
    
    session_model = base_model.Model(config.SESSION_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
    session_data = session_model.get(session_id)

    converter = BaseWebhookConverter()
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
            "reply_to": converter.generate_uid(u) if u else "",
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
    gryd.create_async_task(
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
        session_model = base_model.Model(config.SESSION_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
        session_data = session_model.get(session_id)

    if additiona_params:
        session_data.update(additiona_params)

    logger.info(f'Posting contact status with payload: {session_data}')
    attrs=["phone_number", "lead_id","campaign_id","campaign_type","email","dealership_id","channel","campaign_model"]
    payload = {a:session_data.get(a) for a in attrs if session_data.get(a)}
    payload["provider_status"] = session_data.get("status", "attempted")
    payload["message_id"] = message_id or BaseWebhookConverter.generate_uid(session_data)
    for x in gryd.create_async_task(
        "post_contact_status", 
        config.AUTOCRM_COMMUNICATION_SERVICE_NAME, 
        kwargs=payload
    ):
        return x


@gryd.is_a_task(function_name="end_voice_session")
def end_session(*args, **kwargs):
    logger.info(f"Ending session with args: {args}, kwargs: {kwargs}")
    converter = BaseWebhookConverter()
    return converter.end_session(*args, **kwargs)



if __name__ == "__main__":


    #provider based on dealershiop id-

    #+919920297124 -Ankita +919833885948- Arshiya

    data = {'_is_testing': False,
    'mobile_number': "918850988794", #"919604780730", #"918850988794", #"918401586512", #"918850988794",
    "dealership_id": 'stellantis-india',
    'generate_prompt': False,


    'ctas': ['book-service'],
    'created': 1769076498.8989508,
    'updated': 1769076620.0956566,
    'channels': ['voice_phone'],
    'end_date': 1769644800,
    'languages': ['english'],
    'region_id': 'south-india',
    'start_date': 1769040000,
    'campaign_id': '7b187cc3-b868-366e-97d0-d1f793fd813b',
    'dealer_name': 'deepaklogin3',
    'region_name': 'South India',
    'urgency_hook': 'Don’t wait—keep your car running smooth with timely service!',
    'campaign_name': 'general service reminder- 22nd jan voice',
    'campaign_type': 'post-sales',
    'cost_per_lead': 0.0,
    'campaign_offer': "Hey there! It’s almost time for your vehicle's periodic maintenance. Swing by the dealership to keep your ride in tip-top shape and avoid any surprises on the road. Let’s keep your journey safe and smooth!",
    'campaign_status': 'Active',
    'number_targeted': 3,
    'budget_allocated': 25.68,
    'supported_brands': ['hyundai'],
    'campaign_sub_type': 'other',
    'conversation_tone': 'Be on-point, warm, confident, polite, conversational, and very crisp — like a friendly local representative. Avoid being pushy or overly sales oriented. Incorporate natural conversational elements like brief affirmations   to maintain engagement. End every conversation politely, with warmth and gratitude. Speak at a medium pace, easy to follow, with positive, empathetic, and reassuring emotion (not robotic).',
    'custom_attributes': [],
    'campaign_description': "Hey there! It’s almost time for your vehicle's periodic maintenance. Swing by the dealership to keep your ride in tip-top shape and avoid any surprises on the road. Let’s keep your journey safe and smooth!",
    'campaign_user_source': {'source_type': 'default',
    'campaign_users': [{'lead_id': 'dl9cay4026-deepaklogin3-general-service-reminder--22nd-jan-voice',
        'mobile_number': '8850988794',
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
    'target_audience_tags': ['service-due',
    'periodic-maintenance',
    'active-customer',
    'paid-service-eligible',
    'last-service-older-than-6months',
    'battery_health_alert',
    'tyre_health_alert',
    'tyre-rotation-due',
    'engine-oil-check',
    'brake_inspection_recommended',
    'wheel_alignment_recommended',
    'car-washing-recommended',
    'brake-pad-check',
    'engine-performance-check',
    'suspension_check_recommended',
    'coolant_radiator_check',
    'ac_vent_cleaning_recommended'],
    'campaign_objective_id': 'post-sales-general-service-due-reminder-ambal-auto-south-india',
    'campaign_objective_name': 'General Service Due Reminder',
    'campaign_objective_type': ['lead volume'],
    'conversion_rate_percent': 0.0,
    'region_level_guardrails': 'Maintain professional communication standards. Respect regional languages.',
    'region_level_guidelines': 'Emphasize technology features and premium quality. Highlight safety ratings.',
    'why_user_should_avail_this': 'Regular periodic servicing keeps your vehicle safe, efficient, and performing at its best. It protects long term engine health, prevents unexpected repair costs, and ensures a smooth drive. Engine oil and filters naturally degrade with time, so yearly replacement is important even with low running. A general checkup also helps spot early issues in brakes, battery, suspension, and electrical systems before they turn into major repairs. Periodic service keeps the warranty valid and maintains the resale value of your car.',
    'other_important_information': 'Periodic maintenance is mileage/time based — typically every year or 10,000 km once. Completing on time helps maintain warranty validity.',
    'supported_brands_guidelines': {},
    'reasons_for_non_applicability': "- If the customer says the service is already completed, you should say, 'Thank you for letting me know! I'll update the records.'\n- If the customer has sold the car, you should say, 'Oh okay, got it. Could you please share the new owner's contact number, so we can update our records?.'",
    'reasons_users_may_not_be_interested': "- If the customer says they are busy, you should say, 'Sure, I completely understand. When can I call you back regarding your free service? Your vehicle needs to have that completed, so I will reach you at a time that works best for you.' \n - If the customer says they haven't driven much or want to skip service, you should say 'I understand. Even if the car is not driven much, the engine oil and filters need to be changed every year because they have a validity period. When they age, the oil loses effectiveness and the components start wearing out, which can cause bigger issues later. That is why periodic service is still important.' \n - If Customer Says they don't have the money to service or financial constraint or can we book it to next month, you should say 'I understand. Just a reminder — your service window ends in few days and the yearly service will lapse after that.  When you bring your car to our garage, our service advisor will review and adjust the pricing to ensure you get the best value. With continued service, you'll keep earning loyalty points, which can be redeemed to offset future charges.' \n - If customer says they plan to sell the vehicle, you should say, 'Got it. Completing the service can increase resale value and give buyers more confidence due to an updated service record.'",
    'channel': 'voice_phone',
    'sender': None,
    'provider_name': 'tata-tele',
    'template_message': None,
    'lead_id': 'dl9cay4026-deepaklogin3-general-service-reminder--22nd-jan-voice',
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





{
    "uuid": "6988359567e27",
    "call_to_number": "+919702523384",
    "caller_id_number": "8065251305",
    "start_stamp": "2026-02-08 12:34:53",
    "answer_stamp": "",
    "end_stamp": "2026-02-08 12:34:59",
    "billsec": "6",
    "digits_dialed": "",
    "direction": "clicktocall",
    "duration": "6",
    "answered_agent": "",
    "answered_agent_name": "",
    "answered_agent_number": "",
    "missed_agent": "",
    "call_flow": [
        {
            "type": "init",
            "value": "h3.08-1770534283.2156835",
            "time": "1770534293"
        },
        {
            "type": "Agent",
            "id": "",
            "name": "",
            "dialst": "Dialed",
            "num": "+919702523384",
            "time": 1770534293
        },
        {
            "type": "voice-streaming",
            "name": "Ambal Auto Prod",
            "id": "553",
            "time": 1770534293
        },
        {
            "id": 553,
            "name": "Ambal Auto Prod",
            "type": "voice-streaming",
            "s_id": "a118e1a0-77e1-4fad-8707-77d65f37e226",
            "s_ip": "10.98.44.81",
            "s_port": 12544,
            "a_h": "TTLHYD-Server-003-telephony-8",
            "r_h": "vpaas-rtp-docker-35",
            "status": "started",
            "time": 1770534294.338
        },
        {
            "id": 553,
            "name": "Ambal Auto Prod",
            "type": "voice-streaming",
            "s_id": "a118e1a0-77e1-4fad-8707-77d65f37e226",
            "s_ip": "10.98.44.81",
            "s_port": 12544,
            "a_h": "TTLHYD-Server-003-telephony-8",
            "r_h": "vpaas-rtp-docker-35",
            "status": "ended",
            "time": 1770534298.911
        },
        {
            "type": "hangup",
            "time": 1770534299
        }
    ],
    "broadcast_lead_fields": "",
    "recording_url": "https://cloudphone.tatateleservices.com/file/recording?callId=h3.08-1770534283.2156835&type=rec&token=emtyTmduSlJZRGpSWnpMNHhyK04rODZkd2tzY204WXVKSEQyQWN3Qk1vTXJPY25VcU13VG9ncmRUUitaRTYvTTo6YWIxMjM0Y2Q1NnJ0eXl1dQ%3D%3D",
    "recording_name": "$recording_name",
    "call_status": "contacted",
    "call_id": "h3.08-1770534283.2156835",
    "outbound_sec": "6",
    "agent_ring_time": "6",
    "agent_transfer_ring_time": "$agent_transfer_ring_time",
    "billing_circle": {
        "operator": "Idea",
        "circle": "Mumbai"
    },
    "call_connected": "1",
    "aws_call_recording_identifier": "9d2c63a93ccbf0a174320709e5c18080",
    "customer_no_with_prefix ": "+919702523384",
    "campaign_name": "$campaign_name",
    "campaign_id": "$campaign_id",
    "customer_ring_time": "10",
    "reason_key": "Call Disconnected By Caller",
    "hangup_cause_description": "Normal call clearing",
    "hangup_cause_code": "16",
    "hangup_cause_key": "NORMAL_CLEARING",
    "ref_id": "1b4e38a7-b0d4-497e-8004-385a86532f58",
    "custom_identifier": "3d5af0f4-bb88-312f-9ecd-a12583efd7f4",
    "status": "answered"
}