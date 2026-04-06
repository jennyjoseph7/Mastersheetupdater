
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
from communication.connectors.communication_helpers import end_session as end_voice_session, generate_uid,get_communication_credential
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
                    end_session(**{
                        "session_id": session_data["session_id"],
                        "additional_dict":{
                            # "history": [],
                            "status": "busy"
                    }
                    })
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


def post_history(session_id, session_history):
    import time
    session_model = gryd.base_model.Model(config.SESSION_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
    session_data = session_model.get(session_id)

    agent_msgs = [d for d in session_history if d.get("role") == "agent"]
    user_msgs = [d for d in session_history if d.get("role") == "user"]

    #in zero'th index add empty user message for better indexing
    user_msgs.insert(0, {"role": "user", "content": "__init__"})

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
    gryd.create_async_task(
        "post_all_messages_for_session",
        config.AUTOCRM_CONVERSATION_SERVICE_NAME,
        args=[],
        kwargs={
            "history": history
        }
    )
    #await_results

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
    
    logger.info(f"Constructed payload for contact status: {payload.get('provider_status')}, message_id: {payload.get('message_id')}")
    if payload.get("provider_status") == "attempted":
        post_contact_status(**payload)
        # gryd.create_async_task(
        #     "post_contact_status", 
        #     config.AUTOCRM_COMMUNICATION_SERVICE_NAME, 
        #     kwargs=payload)
    else: 
        post_contact_status(message_id, **payload)
        # gryd.create_async_task(
        #     "post_contact_status", 
        #     config.AUTOCRM_COMMUNICATION_SERVICE_NAME, 
        #     args = (message_id,),
        #     kwargs=payload)




@gryd.is_a_task(function_name="end_voice_session")
def end_session(*args, **kwargs):
    logger.info(f"Ending session with args: {args}, kwargs: {kwargs}")
    return end_voice_session(*args, **kwargs)



if __name__ == "__main__":

    #provider based on dealershiop id-

    #+919920297124 -Ankita +919833885948- Arshiya

    data = {'_is_testing': False,
 'ctas': ['book-test-drive'],
 'mobile_number': '918401586512',
 'created': 1772785341.039532,
 'purpose': 'Confirm Test drive',
 'updated': 1772785440.9737067,
 'channels': ['voice_phone'],
 'end_date': 1773360000,
 'languages': ['english'],
 'region_id': 'united-states',
 'start_date': 1772755200,
 'campaign_id': '2abffd92-e5d7-3a1b-8fa5-78d4e6590fd8',
 'region_name': 'United States',
 'urgency_hook': 'Slots for the Basalt test drive are filling up fast—confirm yours now!',
 'campaign_name': 'Basalt Test Drive Confirmation Event',
 'campaign_type': 'pre-sales',
 'cost_per_lead': 0.0,
 'dealership_id': 'us-dealership-united-states',
 'purpose_steps': ['- Ask if user is interedted in booking test drive',
  '\\n - if customer says yes',
  "get the pincode of customer from 'Who is the customer section' and cofirm if the customer is in this pincode",
  '\\n - Once they confirm the pincode',
  "you should say 'Thank you. We'll arrange a test drive at your nearest dealership. You'll hear from our team shortly to coordinate the details'"],
 'campaign_offer': "Ready to experience the all-new Basalt? Don't just read about its features, get behind the wheel! Secure your personalized test drive slot now to truly understand what makes the Basalt stand out from the competition.",
 'campaign_status': 'Active',
 'dealership_name': 'US Dealership',
 'number_targeted': 1,
 'budget_allocated': 8.56,
 'supported_brands': ['ford-united-states',
  'toyota-usa-united-states',
  'chevrolet-united-states',
  'general-motors-truck-company-united-states',
  'hyundai-motor-america-united-states'],
 'vehicle_category': 'Passenger Vehicle',
 'campaign_sub_type': 'other',
 'conversation_tone': 'Always use simple sentence construction with easy to understand grammar.\nBe on-point, warm, confident, polite, conversational, and very crisp - like a friendly local representative. Avoid being pushy or overly sales oriented. Incorporate natural conversational elements like brief affirmations to maintain engagement. End every conversation politely, with warmth and gratitude. use a medium pace, easy to follow, with positive, empathetic, and reassuring emotion (not robotic).',
 'campaign_description': "Ready to experience the all-new Basalt? Don't just read about its features, get behind the wheel! Secure your personalized test drive slot now to truly understand what makes the Basalt stand out from the competition.",
 'campaign_user_source': {'source_type': 'default',
  'campaign_users': [{'lead_id': 'vandana-8401586512-us-dealership-united-states-2abffd92-e5d7-3a1b-8fa5-78d4e6590fd8',
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
 'voice_start_language': 'en',
 'campaign_objective_id': 'pre-sales-confirm-test-drive',
 'campaign_objective_name': 'Confirm Test Drive',
 'conversion_rate_percent': 0.0,
 'region_level_guardrails': '- Maintain professional communication standards. Ensure clear communication. Respect regional languages. Provide local language support. Be mindful of potential network issues or poor call quality \n -Trigger calls between 10am to 7pm',
 'region_level_guidelines': 'Avoid slang, sarcasm, or culturally sensitive humor. Use polite, respectful, and neutral tone. Prefer simple sentences suitable for Tier-2/Tier-3 customers',
 'why_user_should_avail_this': "Give  5-7 word short description from the interested_vehicle_feature_summary from the 'Who is the customer ' section that make a strong case for buying this car.If They Mention a Specific Aspect: Talk 1-2 highlights about the aspect and push for test drive. Don't be salesy",
 'supported_brands_guidelines': {},
 'reasons_for_non_applicability': "- If the customer has already purchased a vehicle from another brand, you should say, 'Oh okay, congratulations on your new car! Just out of curiosity, what made you go with that brand? Your feedback helps us improve. And if you ever consider another vehicle in the future, feel free to reach out.' \\n - If the customer has already purchased from your brand, you should say, 'That's great to hear! Congratulations on your purchase. Hope you're enjoying the ride. If you ever need any support or have questions about service, feel free to connect with us anytime.' \\n - If the customer says they are no longer interested in buying a car, you should say, 'No problem at all. Can I ask what changed? Just trying to understand so we can serve you better if your plans change in the future. And if you know anyone looking for a vehicle, we'd love to help them out.' \\n - If the customer's contact number is wrong or belongs to someone else, you should say, 'Oh, I see. Sorry for the confusion. Could you help me with the correct contact number for [customer name], or let me know if they're no longer interested so we can update our records?' \\n - If the customer has relocated to a different city or country, you should say, 'Understood. If your new location has our dealership, I can connect you with the team there. Otherwise, I'll update our records. Safe travels, and feel free to reach out if you're ever back in the area.'",
 'campaign_guardrails_guidelines': "You should try get the customer to confirm that they would like to book a test drive and then confirm the pincode available in 'Who is the customer' section",
 'campaign_objective_description': "Your goal is to have natural, human-like conversations with customers who have shown interest in the vehicle and guide them smoothly towards confirming test drive and also get the pincode of customer from 'Who is the customer section' and cofirm if the customer is in this pincode. You are also knowledgeable about the vehicle so focus on giving the customer a smooth and pleasant experience.",
 'reasons_users_may_not_be_interested': "- If the customer says they are busy or asks for a callback later, you should say, 'Sure, I completely understand. When would be a good time to call you back? I just wanted to make sure you don't miss out on the current offers and available test drive slots before they fill up.' \\n - If the customer says they are just browsing or not ready to buy yet, you should say, 'No worries at all! Most of our customers take their time. How about I book a test drive for you? There's no commitment, and it helps you get a real feel of the vehicle. Would this weekend work for you?' \\n - If the customer says the price is too high or out of budget, you should say, 'I understand budget is important. We have some flexible financing options and exchange offers that might work better for you. Can I share those details? It might bring the monthly payment to something more comfortable.' \\n - If the customer is comparing with other brands, you should say, 'That's smart to compare. Many of our customers also looked at competitor. What I can do is share a quick features highlight of vehicle and after-sales benefits, so you have all the info to make the right choice. Would that help?' \\n - If the customer says they want to wait for the next model or year, you should say, 'I get that. Just so you know, the current model has some launch offers and immediate delivery options that the next one might not have. Plus, waiting could mean 6-8 months. But happy to keep you updated on both. What matters most to you - features or timing?' \\n - If the customer mentions they are getting a better deal elsewhere, you should say, 'I appreciate you being upfront. Let me check what we can do to match or improve that offer. Can you share what package they offered? I'd like to see if we can work something out for you.' \\n -If the customer had a bad experience with the brand before, you should say, 'I'm really sorry to hear that. Things have improved a lot, especially in service and support. I'd love the chance to change that impression. How about a test drive and a chat with our service team so you can see the difference yourself?' \\n - If the customer says they need to discuss with family first, you should say, 'Absolutely, that makes sense. Would it help if I sent you a detailed brochure and financing options you can review together? Or would you prefer to bring your family for a test drive so everyone can experience it?' \\n - If the customer is worried about maintenance costs, you should say, 'That's a valid concern. Our vehicles come with a warranty and service packages that keep costs predictable. I can share the exact maintenance schedule and costs upfront, so there are no surprises later.' \\n - If the customer prefers to buy during festival season or year-end, you should say, 'That's a common choice. Just a heads up - current stock and offers might not be available then, and prices could change. But I can note your interest and reach out closer to that time with the best deals. Does that work?' \\n - If the customer recently test drive and didn't like something, you should say, 'Thanks for sharing that feedback. Can you tell me what specifically didn't feel right? Sometimes it's about the variant or settings. I'd like to address that or maybe suggest a different variant that might suit you better.' \\n - If the customer is unsure about which variant to choose, you should say, 'No problem, that's very common. Let me ask you a few quick questions about how you'll use the car - city driving, highway, family size - and I can recommend the variant that fits your needs and budget best.' \\n - If the customer wants to think about it, you should say, 'Of course, take your time. Just so you have all the information, let me send you the brochure, a video walkthrough, and current offers. And I'm here anytime if questions come up. Should I follow up in a couple of days or would you prefer to reach out when ready? \\n - If the customer asks about exchange value for their old vehicle, you should say, 'Sure, I can arrange for our exchange team to evaluate your current vehicle. Can you share the make, model, year, and approximate kms driven? We'll give you the best possible value.",
 'channel': 'voice_phone',
 'sender': None,
 'provider_name': 'tata-tele',
 'template_message': None,
 'lead_id': 'vandana-8401586512-us-dealership-united-states-2abffd92-e5d7-3a1b-8fa5-78d4e6590fd8',
 'customer_name': 'Vandana',
 'email': None,
 'contact_channel': 'voice_phone',
 'template_id': None,
 'template_details': None}

    
    gryd.create_async_task(
        "trigger_voice_call",
        config.AUTOCRM_VOICE_SERVICE_NAME,
        args = [],
        kwargs = {
            "user_data": data
        }
    )




