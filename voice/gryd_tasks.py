
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
        "dave-ai-sociograph-solutions-india": ("tatatele", "agent_5701ka8618cbfxcbdp4wg6xb3x23"),
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
    # user_data["user_id"] = person_obj.get("user_id","a4abae7d832632c7")

    session_model = base_model.Model(config.SESSION_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
    session_obj = {
        "user_id": user_data.get("user_id", "d40d8858-1c88-37d6-93ad-8960d6a02798"),
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
    if user_data.get("campaign_type") == "pre-sales":
        pre_sales_lead_model = base_model.Model("pre_sales_lead", config.AUTOCRM_APP_ENTERPRISE_ID)
        pre_sales_lead_model.patch(
            session_data.get("lead_id"),
            {"last_session_channel":user_data.get("channel")}
        )

        pre_sales_campaign_model = base_model.Model("pre_sales_campaign", config.AUTOCRM_APP_ENTERPRISE_ID)
        pre_sales_campaign_model_data = pre_sales_campaign_model.get(session_data.get("campaign_id"))
        agent_config.update({
            k : v for k, v in pre_sales_campaign_model_data.items() if k.startswith("voice_") and v
        })
    elif user_data.get("campaign_type") == "post-sales":
        post_sales_lead_model = base_model.Model("post_sales_lead", config.AUTOCRM_APP_ENTERPRISE_ID)
        post_sales_lead_model.patch(
            session_data.get("lead_id"),
            {"last_session_channel":user_data.get("channel")}
        )

        post_sales_campaign_model = base_model.Model("post_sales_campaign", config.AUTOCRM_APP_ENTERPRISE_ID)
        post_sales_campaign_model_data = post_sales_campaign_model.get(session_data.get("campaign_id"))
        agent_config.update({
            k : v for k, v in post_sales_campaign_model_data.items() if k.startswith("voice_") and v
        })

    # session_data["room_id"] = user_data.get("room_id", "ambal_auto")
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
    if user_data.get("dealership_id") in list(dealership_provider_map.keys()):
        provider = dealership_provider_map[user_data.get("dealership_id")][0]
        session_data["agent_id"] = dealership_provider_map[user_data.get("dealership_id")][1]
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
    import time

    timeout = time.time() + float(user_data.get("call_timeout", 600))  # 10 minutes

    attempted_timeout = time.time() + float(user_data.get("attempted_status_timeout", 60))  # 1 minutes

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
    # m = gryd.base_model.Model(config.BILLING_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
    # return m.post(obj)


def post_history(session_id, session_history):
    import time
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
            "reply_to": converter.generate_uid(u) if u else gryd.hp.make_uuid3(str(time.time())),
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
        session_model = base_model.Model(config.SESSION_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
        session_data = session_model.get(session_id)

    if additiona_params:
        session_data.update(additiona_params)

    logger.info(f'Posting contact status with payload: {session_data}: status: {session_data.get("status")}, message_id: {message_id}, session_id: {session_id}')
    attrs=["phone_number", "lead_id","campaign_id","campaign_type","email","dealership_id","channel","campaign_model"]
    payload = {a:session_data.get(a) for a in attrs if session_data.get(a)}
    payload["provider_status"] = session_data.get("status", "attempted")
    payload["message_id"] = message_id or BaseWebhookConverter().generate_uid(session_data)
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
    'generate_prompt': False,


  
        'ctas': ['book-test-drive'],
        'created': 1770869404.7936192,
        'purpose': 'Confirm Test drive',
        'updated': 1770875248.5407114,
        'channels': ['voice_phone'],
        'end_date': 1771459200,
        'languages': ['english'],
        'region_id': 'india',
        'start_date': 1770854400,
        'campaign_id': '7d9e6ba7-adca-3be4-a040-4a488bd06a93',
        'region_name': 'India',
        'urgency_hook': "Don't miss out — book your test drive now!",
        'campaign_name': 'Tech-Driven Test Drive 12 Jan 1st',
        'campaign_type': 'pre-sales',
        'cost_per_lead': 0.0,
        'dealership_id': 'dave-ai-sociograph-solutions-india',
        'purpose_steps': ["- Ask if customer is interedted in booking test drive, if customer says yes, get the pincode of the customer from 'Who is the customer section' and cofirm if it is correct.",
        "\n - Once they confirm the pincode, you should only respond with- 'Thank you. We'll arrange a test drive at your nearest dealership. You'll hear from our team shortly to coordinate the details. Is there anything else i can help you with?'"],
        'campaign_offer': '',
        'campaign_status': 'Active',
        'dealership_name': 'Dave AI-Sociograph Solutions',
        'number_targeted': 1,
        'budget_allocated': 8.56,
        'supported_brands': ['maruti-suzuki-nexa-suzuki-motor-corporation-india',
        'toyota-kirloskar-motor-tata-motors-limited-india',
        'jeep-jeep-india',
        'citroen-citroen-india',
        'hyundai-motor-india-hyundai-motor-company-india',
        'maruti-suzuki-arena-suzuki-motor-corporation-india',
        'byd-byd-company-limited-india',
        'kia-kia-corporation-india',
        'toyota-toyota-motor-corporation-india',
        'mahindra-mahindra-mahindra-india'],
        'vehicle_category': 'Passenger Vehicle',
        'campaign_sub_type': 'other',
        'conversation_tone': "Speak like a friendly local representative, not a product expert reading specs, Keep sentences short, simple, and natural, One idea per sentence — pause often, Warm, calm, confident, and respectful, Never rush or push.\n - When the customer responds to you, acknowledge what the customer said by saying things similar to: “Got it.” “That makes sense.” “Fair point.” “Absolutely.” \n - while responding, use disfluency or thinking sounds such as  - 'Uh', 'Umm', 'like', 'ur', 'you know', and then continue responding to give a feeling of thinking about what you are responding with. \n - Avoid feature lists but simple nudges unless the customer asks. \n -End every conversation politely, with warmth and gratitude. \n - when trying to inform the user about features, try not to mention about more than 2 features in one respone. \n - when describing a feature of the car, keep it short, simple and to the point. \n - Make sure you are always trying get the user to fulfill a purpose of confirming a test drive, Don't be too blatent or pushy ",
        'campaign_description': '',
        'campaign_user_source': {'source_type': 'default',
        'campaign_users': [{'lead_id': 'vandana-8401586512-dave-ai-sociograph-solutions-india-7d9e6ba7-adca-3be4-a040-4a488bd06a93',
            'mobile_number': '8401586512',
            'customer_name': 'Vandana',
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
        'campaign_objective_id': 'pre-sales-confirm-test-drives-through-tech-appeal',
        'campaign_objective_name': 'Confirm Test Drives Through Tech Appeal',
        'conversion_rate_percent': 0.0,
        'region_level_guardrails': '- Maintain professional communication standards. Ensure clear communication. Respect regional languages. Provide local language support. Be mindful of potential network issues or poor call quality \n -Trigger calls between 10am to 7pm',
        'region_level_guidelines': 'Avoid slang, sarcasm, or culturally sensitive humor. Use polite, respectful, and neutral tone. Prefer simple sentences suitable for Tier-2/Tier-3 customers',
        'why_user_should_avail_this': 'Core Differentiator, Context-aware AI assistant integrated with full vehicle systems, Understands natural, conversational commands (not keyword-based), Makes real-time decisions using live vehicle data, Connected Ecosystem, Remote AC pre-conditioning, Remote lock/unlock, Live vehicle diagnostics, Full sync with MyCitroën app, Infotainment & Interface, 10.25” lag-free touchscreen, Wireless Apple CarPlay & Android Auto, Wireless charging, 7” digital driver display',
        'other_important_information': 'Tech Features: The Citroën Basalt features Cara, the intelligent voice assistant, giving you hands-free control and seamless interaction on the go. It also comes with a 10.25-inch floating touchscreen with wireless Apple CarPlay and Android Auto, a 7-inch digital cluster, Bluetooth connectivity, steering-mounted controls, and a wireless charger — making every drive smart, connected, and effortless \n - Apart from the technology, the Basalt also stands out for its bold design on the road, the comfort you actually feel every day, and the fact that you get premium features without paying extra just for a badge. \n - Beyond the tech, people also like the Basalt for its strong road presence, the everyday comfort it offers, and the premium feel — without the usual premium-brand pricing. \n - It’s also known for its bold road presence, great everyday comfort, and premium features — without charging you just for the brand name.',
        'supported_brands_guidelines': {},
        'reasons_for_non_applicability': "If customer seems low on tech interest - Don't ask to learn but speak to test a hypothesis and guage if they maybe interested in safety or family or another key feature. And then lead into it. Keep pitch warm and short. \n - If customer is busy “No problem at all. When would be a better time to call you back?” (Optional)  “I just want to make sure you don’t miss available test drive slots.” \n - If customer is just browsing “That’s completely fine. A test drive usually helps people decide faster.” “There’s no commitment at all.” “Would this weekend work, or sometime next week?” \n - If price feels high “I understand. Budget matters.” “There are financing and exchange options that often surprise people.” “Would you like me to quickly check what might work better for you?” \n - If comparing with other brands “That’s smart.” “Many customers compare before deciding.” “Instead of explaining, I’d suggest a short test drive — it gives real clarity.” “Would you like me to arrange that?”  \n - If they want to wait “I get that.” “Just so you know, current offers and availability may change later.” “I can keep you updated.” “What’s more important for you — timing or features?” \n - If they got a better deal elsewhere “Thanks for sharing that.” “Let me see what we can do on our side.” “What exactly did they offer?” \n - if they had a bad past experience “I’m really sorry to hear that.” “A lot has changed, especially service-wise.” “I’d love to give you a fresh experience — even just a drive.” \n - If family decision is involved “Of course, that makes sense.” “Would it help if everyone experienced the car together?” “I can arrange a family test drive.” \n - If worried about maintenance “That’s a valid concern.” “We have clear service packages — no surprises.” “I can explain that briefly or share it on WhatsApp.” \n - If unsure about variant “No worries — that’s very common.” “Let me ask you one or two quick questions and I’ll suggest what fits best.” \n - If they want time to think “Absolutely.” “I’ll send you the brochure and a short video.” “Would you like me to follow up, or should I wait for you to reach out?” \n - Closure Rule (Very Important) Every conversation must end with one soft next step: Test drive booking, Follow-up time, WhatsApp info share Example endings: “Shall I book a test drive for you?”, “Can I send you the details on WhatsApp?”, “When would be a good time to reconnect?”, Always end with warmth:“Thanks for your time. Really appreciate it.”.",
        'campaign_guardrails_guidelines': '- If a customer asks about the NCAP rating, share only the current and officially available information, avoid any speculation about future ratings or test outcomes, and do not make assumptions or comparisons with competitors. \n - Avoid exaggerating safety features. \n - do not claim ‘safest in segment’ unless officially certified \n - maintain a calm and neutral tone when questioned \n -refrain from criticizing competitors, limit technical details to a 2-3 key features at a time, and avoid emotional hype. \n - Avoid mentioning discounts, urgency, or scarcity tactics, focus the communication on the driving experience, and consistently maintain a tech-focused narrative throughout. \n - if the customer shows low interest in tech, Do not re-push tech after this pivot. Listen to their priorities and adjust conversation accordingly',
        'campaign_objective_description': 'Help customers experience the Citroën Basalt by gently nudging them toward a test drive.Focus on making the car feel easy, smart, and pleasant to live with, especially for someone who values everyday technology and convenience — without sounding like a sales pitch',
        'custom_conversation_start_pattern': ["Thank you for considering the Citroën Basalt. What many tech-focused buyers are appreciating about the Basalt is how clean and intuitive the infotainment system is and a very driver-focused interface without overcomplicating things. I'd love to understand what matters most to you in your next car"],
        'reasons_users_may_not_be_interested': 'Position tech as: Making daily driving easier, Reducing distraction, Feeling modern, not complicated . \n - Example: “It’s the kind of tech you stop noticing after a while — because it just fits into your routine.”.',
        'channel': 'voice_phone',
        'sender': None,
        'provider_name': 'tata-tele',
        'template_message': None,
        'lead_id': 'vandana-8401586512-dave-ai-sociograph-solutions-india-7d9e6ba7-adca-3be4-a040-4a488bd06a93',
        'customer_name': 'Vandana',
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
