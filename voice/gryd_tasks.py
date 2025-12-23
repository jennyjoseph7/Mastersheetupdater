import os
import sys
sys.path.append(os.path.dirname(__file__))
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp
from gryd_worker.gryd_routes import payload_decorator
from models import model as base_model
from ai_service import ai_service_app
from voice import providers
import config
import datetime
import pytz
import voice.utils as vhp

logger = hp.get_logger(__name__)


gryd.SERVICE = config.AUTOCRM_VOICE_SERVICE_NAME
gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(__name__)



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

   
    user_data = kwargs.get("user_data", {})
    logger.info(f"Triggering voice call with user data: {user_data}")

    if not all (k in user_data for k in ("session_id", "campaign_id", "campaign_type", "mobile_number")):
        logger.error("Missing required user data fields: 'session_id', 'campaign_id', 'campaign_type'")
        yield {
            "error": "Missing required user data fields: 'session_id', 'campaign_id', 'campaign_type'"
        }

    session_model = base_model.Model(config.SESSION_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
    session_obj = {
        "user_id": user_data.get("user_id"),
        "campaign_id": user_data.get("campaign_id"),
        "campaign_type": user_data.get("campaign_type"),
        "status":"queued",
        "channel": user_data.get("channel", "voice_phone"),
        "phone_number":vhp.format_phone_number(user_data.get("mobile_number")),
        "start_time": hp.epoch()
        
    }
    session_data = session_model.post(session_obj)
    logger.info(f"Session for Voice Call: {session_data}")
    provider = user_data.get("provider", "tatatele")

    response = providers.make_call(provider, session_data, *args, **kwargs)

    yield {
        "success": response.get("success"),
        "call_sid": response.get("call_sid"),
        "message": response.get("message"),
        "session_id":session_data["session_id"],
        "user_id":session_data["user_id"],
        "campaign_id": session_data["campaign_id"],
    }




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
        "campaign_id":,
        "channel": ,
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
    elif status in ["connected"]:
        x = {
        "item_name" : config.AUTOCRM_CALL_CONNECTED_ITEM,
        "item_quantity" : 1,
        "item_price" : config.AUTOCRM_CALL_CONNECTED_PRICE,
        "item_total" : config.AUTOCRM_CALL_CONNECTED_PRICE,
        "item_units" : config.AUTOCRM_CALL_CONNECTED_UNITS,
        }

    obj.update(x)
    m = gryd.base_model.Model(config.BILLING_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
    return m.post(obj)

def format_transcript(transcript, start_time_unix):
    #praveen gave this format but i think this deosnt make sense as timestamps will be diff for user and agent
    user_queries = []
    agent_responses = []
    timestamps = []
    session_history = []

    func = lambda x: datetime.fromtimestamp(start_time_unix+float(x), tz=pytz.timezone("UTC")).strftime("%Y-%m-%d %I:%M:%S %p %z")
    for msg in transcript:
        session_history.append({
            "role":msg.get('role'),
            "message":msg.get('message','').replace('.','') if msg.get('message') else '',
            "timestamp": func(msg.get('time_in_call_secs',0.0))
        })
    
    return session_history   

def patch_session_hitory(data, session_id = None):
    session_history = format_transcript(data.get('transcript'), data.get('metadata').get('accepted_time_unix_secs'))

    session_id = session_id or data.get('user_id')
    m = gryd.base_model.Model(config.SESSION_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)

    r = m.patch(
        session_id, 
        {
            "history" : session_history
        }
    )
    logger.info(f"Patched session model : {r}")

def post_history(data):

    history  = []
    for d in data:
        pass
    
    gryd.create_async_task(
        "post_all_messages_for_session",
        config.AUTOCRM_CONVERSATION_SERVICE_NAME, 
        args = [],
        kwargs = {
            "history": history or data
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


if __name__ == "__main__":
    pass
    data =  {'_is_testing': False, 'ctas': ['book-service', 'request-callback'], 'created': 1764835501.0808802, 'remarks': 'Focus on high-value customers with service history', 'updated': 1764835501.0822716, 'channels': ['whatsapp_chat', 'email', 'voice_phone'], 'end_date': 1735689600, 'languages': ['english', 'hindi', 'tamil'], 'region_id': 'south-india', 'start_date': 1704067200, 'campaign_id': '74f260b8-e8dc-3c52-ab8d-31bd0fc49943', 'dealer_name': 'Ambal Auto', 'region_name': 'South India', 'workshop_id': 'ambal-auto - ambal-auto---service-center - coimbatore', 'actual_spent': 35000, 'urgency_hook': ['Your vehicle service is due in 30 days. Book now to avoid last-minute rush!'], 'campaign_name': 'Scheduled Service Reminder', 'campaign_type': 'post-sales', 'cost_per_lead': 0, 'dealership_id': 'ambal-auto-south-india', 'workshop_name': 'Ambal Auto - Service Center', 'campaign_offer': '10% discount on service charges for bookings made within 7 days', 'number_engaged': 200, 'number_reached': 360, 'workshop_email': 'workshop@ambalauto.com', 'campaign_status': 'Active', 'number_targeted': 400, 'budget_allocated': 40000, 'number_contacted': 300, 'number_converted': 100, 'supported_brands': ['maruti-suzuki-arena', 'maruti-suzuki-nexa'], 'workshop_address': 'Ambal Auto, Iyer Hospital Premises, Trichy Rd, Coimbatore, Tamil Nadu 641005', 'workshop_pincode': '641005', 'campaign_sub_type': ['workshop awareness'], 'campaign_objective': ['Service reminder'], 'responsible_person': 'Ramesh Kumar', 'workshop_full_name': 'Ambal Auto Ambal Auto - Service Center', 'campaign_description': 'Remind customers about their upcoming scheduled service appointments', 'campaign_user_source': {'source_type': 'default', 'campaign_users': [{'lead_id': 'tn37dm7087-ambal-auto-scheduled-service-reminder', 'mobile_number': '918850988794', 'customer_name': None, 'contact_channel': 'voice_phone', 'template_id': None, 'template_details': None}], 'field_mapping': {'lead_id': 'lead_id', 'mobile_number': 'mobile_number', 'customer_name': 'customer_name', 'template_id': 'template_id', 'template_details': 'template_details', 'contact_channel': 'contact_channel'}, 'config': {'batch_size': 100, '_skip_sent_message': True}}, 'workshop_geolocation': [11.0168, 76.9558], 'dealership_description': 'Our customers can experience the joy of state-of-the-art technology, reliability, transparency and complete peace of mind.', 'campaign_objective_type': ['lead volume'], 'conversion_rate_percent': 0, 'region_level_guardrails': 'Maintain professional communication standards. Respect regional languages.', 'region_level_guidelines': 'Emphasize technology features and premium quality. Highlight safety ratings.', 'workshop_contact_number': '+91-9876543501', 'workshop_operating_hours': {'closing_time': '18:00', 'opening_time': '09:00'}, 'supported_brands_guidelines': [], 'channel': 'voice_phone', 'sender': None, 'provider_name': 'tata-tele', 'template_message': None, 'lead_id': 'tn37dm7087-ambal-auto-scheduled-service-reminder', 'mobile_number': '919113687241', 'customer_name': None, 'contact_channel': 'voice_phone', 'template_id': None, 'template_details': None}
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