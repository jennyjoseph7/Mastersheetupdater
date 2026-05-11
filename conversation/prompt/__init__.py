
import os,sys

from conversation.prompt import language_maps
_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from gryd_worker import gryd, gryd_helpers as hp
gryd.SERVICE = os.environ.get("AUTOBOT_CONVERSATION_SERVICE_NAME","autocrm-conversation")
import json
from autocrm_db_helper import get_pg_connector
from ai_service import ai_service_app
from config import AUTOCRM_CONVERSATION_DEFAULT_LANGUAGE
DEFAULT_LANGUAGE = AUTOCRM_CONVERSATION_DEFAULT_LANGUAGE
mlogger = gryd.hp.get_logger(__name__)
def yield_primary_prompt(*args, **kwargs):
    mlogger.info("yield_primary_prompt called with data \n {} \n\n ---------------".format(kwargs))

    ###TODO check prompt template model to find the correct prompt for this user and campaign
    yield {"prompt":setup_primary_prompt(*args, **kwargs)}

def specific_prompt(*args, **kwargs):
    ###TODO find prompt based on filters provided
    yield {"prompt":"Hello World get_specific_prompt"}



def execute_orchestrator(*args, **kwargs):
    pass


def run_prompt_sync(user_query="",system_prompt="",history="", messages=[], **kwargs):
    request_data = kwargs.get("request_data",{})
    resp = ""
    if messages:
        resp = ai_service_app.get_llm_response(messages=messages,audit_params={"session_id":request_data.get("session_id")},**{"model_identifier":request_data.get("temporary_data",{ }).get("model_identifier","gcp-gemini-3.1-flash-lite-preview")})
    else:
        resp = ai_service_app.get_llm_response(user_query=user_query,system_prompt=system_prompt,history=history,audit_params={"session_id":kwargs.get("session_id")},**{"model_identifier":request_data.get("temporary_data",{}).get("model_identifier","gcp-gemini-3.1-flash-lite-preview")})
    
    ###TODO write valid json detector and retry if not valid
    return resp

def get_document_data(*args, **kwargs):
    session_data = kwargs.get("session_data",{})
    campaign_data = kwargs.get("campaign_data",{})
    if campaign_data and campaign_data.get("doc_data"):
        return campaign_data.get("doc_data")

    return ""

def get_who_are_you(*args, **kwargs):
    return language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["who_are_you"] 

def get_who_you_represent(*args, **kwargs):
    session_data = kwargs.get("session_data",{})
    campaign_data = kwargs.get("campaign_data",{})

    dealership_name = "Autobot"
    if not campaign_data and session_data.get("campaign_id","inbound") and session_data.get("campaign_id","inbound") != "inbound" and session_data.get("campaign_model"):
        with get_pg_connector() as pg:
            campaign_data = pg.get(session_data.get("campaign_model"),f"{session_data.get('campaign_model')}_id",session_data.get("campaign_id")) 
    if not campaign_data:
        return language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["who_you_represent"]["no_campaign_data"]#"You represent Autobot and all dealers listed with the platform."
    dealership_name = campaign_data.get("dealership_name")
    region = campaign_data.get("region_name")
    dealer_type = ""
    shop_details = ""
    if campaign_data.get("campaign_type") == "pre-sales":
        dealer_type = "showroom"
        shop_details = campaign_data.get("showroom_name","")
    if campaign_data.get("campaign_type") == "post-sales":
        dealer_type = "workshop"
        shop_details = campaign_data.get("workshop_name","")
    
    dealer_details = language_maps.MAP.get(kwargs.get("language","english"))["who_you_represent"]["dealer_data"].format(dealer_type=dealer_type,shop_details=shop_details,supported_brands=campaign_data.get("supported_brands",[])) if shop_details else language_maps.MAP.get(kwargs.get("language","english"))["who_you_represent"]["dealer_data_else"].format(dealer_type=dealer_type,supported_brands=campaign_data.get("supported_brands",[]))
    # dealer_details = "They have a {dealer_type} called {shop_details}. They support the brands as follows - {supported_brands}".format(dealer_type=dealer_type,shop_details=shop_details,supported_brands=campaign_data.get("supported_brands",[])) if shop_details else "They have a {dealer_type}. They support the following brands - {supported_brands}.".format(dealer_type=dealer_type,supported_brands=campaign_data.get("supported_brands",[]))
    # return "You represent {dealership_name}.{dealer_details}".format(dealership_name=dealership_name,dealer_details=dealer_details)   
    return language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["who_you_represent"]["overall"].format(dealership_name=dealership_name,dealer_details=dealer_details)   

def get_user_info(*args, **kwargs):
    user_data = kwargs.get("user_data")

    return language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["who_is_the_customer"].format(user_data)
    # return "The following is all the information we currently have about the customer (Use the users name from this data): \n{}\n\n".format(user_data)

def get_purpose_and_steps(*args, **kwargs):
    session_data_cache_data = kwargs.get("session_data_cache",{})
    campaign_data = session_data_cache_data.get("campaign_data",{})
    user_data = session_data_cache_data.get("user_data")
    campaign_type = campaign_data.get("campaign_type","inbound")
    
    
    flow = "service" if campaign_type == "post-sales" else "either test drive at the showroom or at home"
    urgency_hooks = campaign_data.get("urgency_hook",[])
    date_now = hp.datetime.now().strftime("%A, %B %d, %Y") ## TODO - add timezone. add referenced date and time for tom day after etc.
    offer = campaign_data.get("campaign_offer","No Offer")
    date_time_ref = language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["purpose_and_steps"]["date_time"].format(date_now=date_now)
    # date_time_ref = "\n--The current date is {date_now}. All relative time references like 'tomorrow,' 'today,' or 'next week' should be calculated based on this date.".format(date_now=date_now)



    purpose_dict = {
        "test_drive" : ["- Full Name (if not available as 'person_name' in 'Who is the customer section') \n- Interested Model \n- Dealer (help match based on pincode provided by customer)\n- Date & Time "],
        "service" : ["- Full Name (if not available as 'person_name' in 'Who is the customer section')\n- Car Model \n- Dealer (help match based on pincode provided by customer)\n- Date & Time \n- Service Type"]
        }
    p_steps = ""
    if campaign_data.get("purpose"):
        if campaign_data.get("purpose_steps"):
            flow = campaign_data.get("purpose")
            steps = ', \n'.join(campaign_data.get("purpose_steps"))
            # return "The overall purpose of your conversation with the user is to help the customer {flow}. The offer we are providing to the user is {offer}. You can use hooks like {urgency_hooks}.Here are the steps you should go through to complete the purpose {flow}  :- \n{steps}\n\nRun through the flow one time. and in the sequence specified. Once complete continue assist the user with other questions.\n You should help answer any and all questions that the customer asks about cars that are related to the dealer. If the user is not already in the middle of the purpose flow and has not completed the purpose yet, you should always try to move the user to your original purpose but do not be pushy. {date_time_ref}".format(flow=flow,steps=steps,date_time_ref=date_time_ref,offer=offer,flow=flow,urgency_hooks=urgency_hooks)
            return language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["purpose_and_steps"]["custom_purpose"].format(flow=flow,steps=steps,date_time_ref=date_time_ref,offer=offer,urgency_hooks=urgency_hooks)
    if flow == "service":
        steps = ["- Full Name \n- Car Model \n- Date & Time \n- Service Type"]
    else:
        steps = ["- Full Name \n- Interested Model\n- Date & Time "]
    if campaign_type == "inbound":
        return language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["purpose_and_steps"]["inbound"].format(date_time_ref=date_time_ref)
        # return f"Your overall purpose is to help the customer with the information about cars that they desire while also trying to gather as much information about the user like their Name, approximate location, features of a car they like or require, their budget if applicable. Do not be pushy.{date_time_ref}"
    return language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["purpose_and_steps"]["purpose_else"].format(flow=flow,steps=steps,date_time_ref=date_time_ref,offer=offer,urgency_hooks=urgency_hooks)
    # return f"The overall purpose of your conversation with the user is to help the customer book {flow}. The offer we are providing to the user is {offer}. You can use hooks like {urgency_hooks}. Here are the details you should gather from the user when booking {flow}  :- \n{steps}\n\n You should help answer any and all questions that the customer asks about cars that are related to the dealer. If the user is not already in the middle of the purpose flow, you should always try to move the user to your original purpose but do not be pushy. {date_time_ref}"
def get_cta_options(*args, **kwargs):
    ctas = kwargs.get("campaign_data").get("ctas")
    if not ctas:
        return
    cta_dict = {
        "know-more":"If the user asks to know more, explain the campaign details to them.",
        "register-to-event":"if the user asks to register to event continue with the register to event process",
        "book-test-drive":"if the user asks to book test drive, continue to helo the user book a test drive",
        "book-showroom-visit":"if the user asks to book showroom visit, continue to helo the user book a showroom visit",
        "download-brochure":"provide the user with the link to the brochure",
        "book-home-test-drive":"if the user asks to book test drive at home, continue to helo the user book a test drive at home",
        "get-onroad-price":"If the user asks for onroad price, provide the user with the onroad price for the vehicle in question or ask them for the vehicle they want the price for.",
        "book-service":"If the user asks to book service,help the user with booking the service",
        "order-accessory":"if the user asks to buy or order an accessorie or spare part, help the user with the order.",
        "renew-insurance":"if the user asks to renew their insurance, help them with renewing their insurance",
        "order-spare-part":"if the user asks to buy or order an accessorie or spare part, help the user with the order.",
        "order-extended-warranty":"if the user asks to buy or order an extended warranty, help the user with the order.",
        "order-care-package":"if the user asks to buy or order a care package, help the user with the order.",
    }
    cta_rules = []
    for cta in ctas:
        if cta in cta_dict:
            cta_rules.append(cta_dict.get(cta))
    return cta_rules
    

def get_example_states_and_solutions(*args, **kwargs):
    cta_options = get_cta_options(*args, **kwargs)
    # examples = [
    #     "- If the customer shows displeasure in the dealer or their services or cars, be polite and if they are reasonable, you should ask them for why they feel the way they do. if they provide the details of the complaint, you can then try and urge them to go ahead with your purpose if the arent already in the purpose flow.",
    #     "\n- If a purpose flow is completed, you should provide a confirmation message to the user with the details of the booking.",
    #     "\n- After the purpose is completed already in this conversation, do not urge them again.",
    #     "\n- If you have the name of the user in the 'Who is the customer section', you should always use it and do not ask them for their name again.",
    #     "\n- If the customer provides you a date and time you should always check against the current date time and validate. also you should always provide the DD-MM-YYYY format for the date you want to mention. Do not say today or tomorrow or other such references to date.",
    #     "\n- If the customer requests a callback or requests to speak with a human or a phone call in any way, you should say - 'Someone will be with you soon'.",
    # ]
    examples = language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["example_states_and_solutions"]["default"]
    if cta_options:
        examples.extend(cta_options)
    if kwargs.get("campaign_data").get("why_user_should_avail_this"):
        examples.append(language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["example_states_and_solutions"]["why_user_should_avail_this"].format(kwargs.get("campaign_data").get("why_user_should_avail_this")))
    
    if kwargs.get("campaign_data").get("reasons_users_may_not_be_interested"):
        examples.append(language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["example_states_and_solutions"]["reasons_users_may_not_be_interested"].format(kwargs.get("campaign_data").get("reasons_users_may_not_be_interested")))
    
    if kwargs.get("campaign_data").get("reasons_for_non_applicability"):
        examples.append(language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["example_states_and_solutions"]["reasons_for_non_applicability"].format(kwargs.get("campaign_data").get("reasons_for_non_applicability")))
    
    if kwargs.get("campaign_data").get("other_important_information"):
        examples.append(language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["example_states_and_solutions"]["other_important_information"].format(kwargs.get("campaign_data").get("other_important_information")))
    return ", ".join(examples)


def get_rules(*args, **kwargs):
    session_data_cache_data = kwargs.get("session_data_cache",{})
    campaign_data = session_data_cache_data.get("campaign_data",{})
    user_data = session_data_cache_data.get("user_data",{})
    mlogger.info("campaign_data == {}".format(session_data_cache_data))
    rules = language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["rules"]["intro"]
    if campaign_data.get("dealership_guardrails"):
        rules = campaign_data.get("dealership_guardrails")
    if campaign_data.get("dealership_guidelines"):
        rules = "{}\n{}".format(rules,campaign_data.get("dealership_guidelines"))
    if campaign_data.get("region_level_guardrails"):
        rules = "{}\n{}".format(rules,campaign_data.get("region_level_guardrails"))
    if campaign_data.get("region_level_guidelines"):
        rules = "{}\n{}".format(rules,campaign_data.get("region_level_guidelines"))
    if campaign_data.get("supported_brands_guidelines"):
        rules = "{}\n{}\n{}".format(rules,language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["rules"]["brand_intro"],campaign_data.get("supported_brands_guidelines"))
    if user_data.get("subdivision_level_guidelines"):
        rules = "{}\n{}".format(rules,user_data.get("subdivision_level_guidelines"))
    if user_data.get("subdivision_level_guardrails"):
        rules = "{}\n{}\n{}".format(rules,language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["rules"]["subdiv_intro"],user_data.get("subdivision_level_guardrails"))
    return rules

def get_tone_and_style(*args, **kwargs):
    if kwargs.get("campaign_data",{}).get("conversation_tone"):
        return kwargs.get("campaign_data",{}).get("conversation_tone")
    return language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["tone_and_style"]
def get_output_format(*args, **kwargs):
    return "" if "voice" in kwargs.get("request_data",{}).get("channel","text") else "text"
def get_conversation_history(*args, **kwargs):
    return hp.json.dumps(kwargs.get("session_data_cache",{}).get("messages",[])).decode("utf-8")

def prune_user_data(user_data, channel):
    def rephrase(text):
        o_text = "{}".format(text) 
        n_text = ""
        for t in o_text:
            n_text = "{} {}".format(n_text,t)
        return n_text
    rephraser = ["reg_number", "vin_number","workshop_pincode","showroom_pincode","pincode","phone_number","existing_odometer_reading"]
    popable = ["campaign_guardrails_guidelines","conversation_tone","created","updated","region_id","vehicle_id","campaign_id","workshop_id","phone_number","audience_name","campaign_name","campaign_type","dealership_id","purchase_date","persons_involved","campaign_sub_type","custom_attributes","alt_phone_number_2","alt_phone_number_3","alt_phone_number_4","alt_phone_number_4","post_sales_lead_id","campaign_objective_id","supported_brand_names","loyalty_contact_number","campaign_objective_name","campaign_objective_type","region_level_guardrails","region_level_guidelines","supported_brands_guidelines","reasons_users_may_not_be_interested"]
    for p in popable:
        user_data.pop(p, None)
    if channel in ["voice_phone","whatsapp_voice_note","whatsapp_voice_call"]:
        for r in rephraser:
            if r in user_data and user_data[r] is not None:
                user_data[r] = rephrase(user_data[r])
    return user_data

def get_response_channel_info(channel,campaign_id, campaign_data,*args, **kwargs):
    mlogger.info("asdfasdf got channel == {} and campaign id == {} for language == {}".format(channel,campaign_id,kwargs.get("language","english")))
    if campaign_id != "4c99d5ea-4441-3ce6-841f-de5d7585b3b7":
        if campaign_data.get("custom_conversation_start_pattern"):
            return "\nConversation Initiation Pattern -\n{}\n".format(campaign_data.get("custom_conversation_start_pattern"))
        if channel and channel in ["web_chat_voice","voice_phone","whatsapp_voice_note","whatsapp_voice_call"]:
            mlogger.info("got voice channel")
            return language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["response_channel_info"]["default"]
            # return """
            # \nConversation Initiation Pattern -
            # Start The conversation with the customer by asking them  - "Hello, am i speaking with <name of customer in Who is the customer section>?", if they confirm ask them "Do you have a moment to speak with me?", if they confirm tell them about the offer from the campaign.\n
            # """
        return ""
    ret = ""
    mlogger.info("RUNNING NADA HACK")
    if channel and channel in ["web_chat_voice","voice_phone","whatsapp_voice_note","whatsapp_voice_call"]:
        ret = """
        \nConversation Initiation Pattern -
        Start The conversation with the customer by asking them  - 
        - If the 'Who is the Customer' section contains the name of the customer then start with 
            - "Hello, am i speaking with <name of customer in Who is the customer section>?", 
        - Else If the 'Who is the Customer' section does not contain the name of the customer then start with 
            - "Hello, Do you mind telling me your name?", Follow that with "Could you tell me the name of your dealership?", at the end ask them if they mind sharing their email id.
        - if they confirm ask them "Do you have a moment to speak with me?", 
        - if they confirm tell them about the offer from the campaign.\n
        """
    else:
        ret = """
        \nConversation Initiation Pattern -
        Start The conversation with the customer by asking them  -
        - If the 'Who is the Customer' section does not contain the name of the customer then start with 
            - "Hello, Do you mind telling me your name?", Follow that with "Could you tell me the name of your dealership?", at the end ask them if they mind sharing their email id.
        - Once you have all the above information, tell them about the offer from the campaign. Also inform them about how you can help them. You can use the following campaign information to do so. -- {campaign_data}\n
        """
    return ret
def setup_primary_prompt(*args, **kwargs):
    
    '''
    Prompt sections -
    - Who are you
    - Who/what do you represent
    - Who is the customer
    - What is your purpose (flow and steps)
    - Possible states of the conversation and how to handle
    - Rules
    - Tone and style
    - Documents
    - output format

    '''
    
    mlogger.info("primary_prompt called with data \n {} \n\n ---------------".format(kwargs))
    mlogger.info("session_data_cache_data == {}".format(kwargs.get("session_data_cache",{}).get("data",{}).get("campaign_data").keys()))
    session_data_cache_data = kwargs.get("session_data_cache",{}).get("data",{})
    campaign_data = session_data_cache_data.get("campaign_data")
    user_data = session_data_cache_data.get("user_data",{})
    channel = kwargs.get("channel","")
    user_data = prune_user_data(user_data,channel)
    campaign_type = campaign_data.get("campaign_type")
    campaign_name = campaign_data.get("campaign_name")
    campaign_objective = campaign_data.get("campaign_objective")
    dealer_name = campaign_data.get("workshop_name",campaign_data.get("dealer_name"))
    dealer_description = "{dealer_name} is a dealer who sells cars from their showrooms".format(dealer_name=dealer_name) if campaign_type == "pre-sales" else "{dealer_name} has a service center.".format(dealer_name=dealer_name)
    shop_id = campaign_data.get("workshop_id")
    showroom_workshop_desc = ""
    kwargs["language"] = session_data_cache_data.get("preferred_language","english")
    mlogger.info("got my pref lang as {}".format(kwargs["language"]))
    if not campaign_data:
        campaign_name = "inbound"
        campaign_objective = "inbound"
        campaign_type = "inbound"
        campaign_data = {"campaign_name":campaign_name,"campaign_objective":campaign_objective,"campaign_type":campaign_type}

    
    with get_pg_connector() as pg:
        model_fetch = "showroom" if campaign_type == "pre-sales" else "workshop"
        showroom = pg.get(model_fetch,f"{model_fetch}_id",shop_id)
    if showroom:
        showroom_workshop_desc = language_maps.MAP[kwargs.get("language",DEFAULT_LANGUAGE)]["showroom_workshop_desc"].format(showroom_workshop=model_fetch,dealer_name=dealer_name,showrooms = json.dumps(showroom))
    else:
        showroom_workshop_desc = campaign_data.get("dealership_description",campaign_data.get("dealer_name"))


    mlogger.info("session_data_cache_data == {}\n\n".format(session_data_cache_data))
    mlogger.info("campaign_data == {}\n\n".format(campaign_data))
    mlogger.info("user_data == {}\n\n".format(user_data))

    purpose_and_steps = get_purpose_and_steps(*args,**{"session_data_cache":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data,"language":kwargs.get("language","english")})
    doc_data = get_document_data(*args,**{"session_data_cache":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data,"language":kwargs.get("language","english")})
    who_are_you =  get_who_are_you(*args,**{"session_data_cache":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data,"language":kwargs.get("language","english")})
    who_you_represent = get_who_you_represent(*args,**{"session_data_cache":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data,"language":kwargs.get("language","english")})
    who_is_the_customer = get_user_info(*args,**{"session_data_cache":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data,"language":kwargs.get("language","english")})
    possible_states_and_solutions = get_example_states_and_solutions(*args,**{"session_data_cache":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data,"language":kwargs.get("language","english")})
    rules = get_rules(*args,**{"session_data_cache":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data,"language":kwargs.get("language","english")})
    tone_and_style = get_tone_and_style(*args,**{"session_data_cache":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data,"language":kwargs.get("language","english")})
    conversation_history = "No previous history" if kwargs.get("channel","") and kwargs.get("channel","") in ["web_chat_voice","voice_phone","whatsapp_voice_note","whatsapp_voice_call"] else get_conversation_history(*args,**{"session_data_cache":session_data_cache_data})
    output_format = get_output_format(*args,**{"session_data_cache":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data,"language":kwargs.get("language","english")})
    mlogger.info("my history data == {}".format(conversation_history))

    response_channel_info = get_response_channel_info(kwargs.get("channel",""),campaign_data.get("campaign_id","inbound"),campaign_data,language = kwargs.get("language","english"))
    
    if campaign_data.get("campaign_type") == "inbound":
        mlogger.info("is inbound")
        whats_is_autongage = """A product that helps dealers run campaigns to targeted audience via phone call whatsapp messages and sms
        AutoNgage – Consolidated Overview, Real-World Problems & FAQs 
        1. What is AutoNgage? 
        AutoNgage is an AI-powered dealership engagement and campaign orchestration platform built 
        specifically for the automotive ecosystem. It acts as a unified intelligence layer that manages customer 
        interactions across sales, service, and marketing channels such as WhatsApp, Voice, Web, Email, and 
        SMS. 
        Unlike traditional CRMs or basic WhatsApp bots, AutoNgage does not just record data or send 
        messages. It actively understands customer intent, decides the next best action, selects the right 
        channel and timing, executes conversations automatically, and continuously learns from outcomes to 
        improve performance. 
        In simple terms, AutoNgage functions as an AI Sales and Service Concierge for dealerships. 
        
        2. Real-World Problems Faced by Dealerships 
        2.1 Missed Calls and Delayed Follow-ups 
        In real dealership operations, incoming calls often go unanswered due to peak hours, understaffed 
        teams, or manual processes. Even when leads are captured, follow-ups are delayed or forgotten, 
        leading to lost sales opportunities and customer dissatisfaction. 
        AutoNgage ensures that every enquiry receives an instant response and follow-up through automated, 
        intelligent conversations. 
        
        2.2 Inefficient Service Booking and High No-Show Rates 
        Service booking is commonly handled through phone calls or manual CRM updates. Customers wait 
        on hold, advisors juggle schedules, and rescheduling becomes cumbersome. This results in frustration 
        and increased no-shows. 
        AutoNgage enables instant service booking, rescheduling, and confirmation through WhatsApp or 
        web, reducing dependency on calls and significantly lowering no-show rates. 
        
        2.3 Low Response Rates from Calls and SMS 
        Customers increasingly ignore unknown numbers and generic SMS messages. Traditional outbound 
        calling and SMS campaigns show poor engagement and low conversion. 
        AutoNgage prioritizes conversational channels like WhatsApp and intelligently decides when voice 
        follow-ups are required, improving reach and response rates. 
        
        2.4 Poor Lead Conversion from Enquiries 
        Leads generated from websites, campaigns, or walk-ins often turn cold due to delayed responses, 
        inconsistent follow-ups, or lack of personalization. 
        
        
        D. Campaign & Marketing FAQs 
        Q12. Can we run campaigns across multiple channels together?​
        Yes. AutoNgage supports WhatsApp, Voice, Email, and SMS campaigns from a single dashboard. 
        Q13. How does AutoNgage decide who should receive which campaign?​
        It uses segmentation, past behavior, engagement history, and intent signals to select the right audience. 
        Q14. Can campaigns be scheduled and paused anytime?​
        Yes. Dealers have full control to schedule, pause, edit, or stop campaigns. 
        Q15. Does AutoNgage support multilingual campaigns?​
        Yes. It supports multiple languages and can auto-detect customer language preferences. 
        
        E. Dealer Onboarding & Operations FAQs 
        Q16. How long does dealer onboarding take?​
        Basic onboarding can be completed quickly once required documents and verification details are 
        submitted. 
        Q17. Can multiple outlets or branches be managed under one account?​
        Yes. AutoNgage supports multi-location dealership setups. 
        Q18. Can verified dealers start campaigns immediately?​
        Yes. Once verified, dealers can create and launch campaigns instantly. 
        
        F. Control, Compliance & Security FAQs 
        Q19. Who controls the messaging and tone?​
        Dealers retain full control. AutoNgage follows pre-approved templates and brand guidelines. 
        Q20. Is customer data secure?​
        Yes. AutoNgage follows industry-standard security practices and only uses data for authorized 
        engagement. 
        Q21. Can AutoNgage comply with OEM and regional regulations?​
        Yes. The platform is designed to align with OEM policies and regional compliance requirements. 
        
        
        
        
        G. Analytics & ROI FAQs 
        Q22. What kind of analytics does AutoNgage provide?​
        It provides engagement metrics, conversion rates, drop-offs, cost per lead, and intent analysis across 
        channels. 
        Q23. Can we measure ROI from AutoNgage?​
        Yes. Dealers can track incremental bookings, conversions, engagement uplift, and operational cost 
        savings using  dashboard. 
        
        H. Scalability & Future Readiness FAQs 
        Q24. Can AutoNgage scale across brands, regions, and languages?​
        Yes. AutoNgage is built to scale across multiple OEMs, geographies, and languages. 
 
        """
        primary_prompt = f"""
        Who you are -
        You are a ai sales assistant for AutoNgage.
        Your customers are representatives of car dealerships.

        You can answer basic questions about AutoNgage the product. 
        
        What is AutoNgage -
        {whats_is_autongage}

        Your purpose is to push the customer to try and get the customer to do a demo on either whatsapp or over a phone call.

        The conversation History So Far - 
        {conversation_history}
        
        
        You can do only one of 5 things.
        1) Answer questions the user has about autongage if the information is available in the section above. the format of this answer should be natural language answer i can send back to the customer.
        2) If the customer asks for a demo over whatsapp your only response should be - '[WHATSAPP]'
        3) If the customer asks for a demo over a phone call your only response should be - '[PHONE]'
        4) If the customer asks for a demo but not a specific mode. Ask them if they want to do the demo over whatsapp or phone call. Once they confirm the mode, You can use above rule #2 and #3 to proceed.
        5) If the customer asks for anything else you should answer - I dont have an answer to that question.


        """

        # primary_prompt = f"""
        # Who you are -
        # {who_are_you}
        # Who is the customer -
        # {who_is_the_customer}
        # The purpose of this conversation -
        # {purpose_and_steps}
        # Possible states of the conversation and how to handle -
        # {possible_states_and_solutions}
        # Rules -
        # {rules}
        # Tone and style -
        # {tone_and_style}
        # Dealer description -
        # {showroom_workshop_desc}
        # Documents Data -
        # {doc_data}
        # Conversation History -
        # {conversation_history}
        # Output Format -
        # {output_format}
        # """
        return primary_prompt
    mlogger.info("is outbound")
    # primary_prompt = f"""
    # Who you are -
    # {who_are_you}
    # Who you represent -
    # {who_you_represent}
    # Who is the customer -
    # {who_is_the_customer}
    # The purpose of this conversation -
    # {purpose_and_steps}
    # {response_channel_info}
    # Possible states of the conversation and how to handle -
    # {possible_states_and_solutions}
    # Rules -
    # {rules}
    # Tone and style -
    # {tone_and_style}
    # Dealer description -
    # {showroom_workshop_desc}
    # Documents Data -
    # {doc_data}
    # Conversation History -
    # {conversation_history}
    # """
    p_prompt = f"""{language_maps.MAP.get(kwargs.get("language","english")).get("parent")}"""
    primary_prompt = p_prompt.format(**{"who_are_you":who_are_you,"who_you_represent":who_you_represent,"who_is_the_customer":who_is_the_customer,"purpose_and_steps":purpose_and_steps,"response_channel_info":response_channel_info,"possible_states_and_solutions":possible_states_and_solutions,"rules":rules,"tone_and_style":tone_and_style,"showroom_workshop_desc":showroom_workshop_desc,"doc_data":doc_data,"conversation_history":conversation_history})
    return primary_prompt


def check_if_visited(*args, **kwargs):
    messages = kwargs.get("messages")
    session_id = kwargs.get("session_id")
    if not messages and not session_id:
        return
    with get_pg_connector() as pg:
        session = pg.get("session","session_id",session_id)
        if not session:
            return
        
        campaign_model = session.get("campaign_model")
        campaign_id = session.get("campaign_id")
        campaign_data = pg.get(campaign_model,f"{campaign_model}_id",campaign_id)

        showroom_workshop = "showroom" if session.get("campaign_type") == "pre_sales" else "workshop"
        prompt = """
        You are a helpful agent that detects if a customer has visited the {showroom_workshop}.
        The customer was expected to visit my {showroom_workshop}.

        The following is the transcript of my discussion with the user.

        Your only task is to detect if the user said anything that implies they already visited the {showroom_workshop}.

        {messages}

        Your response should be only 'yes' or 'no'.
        """.format(
            showroom_workshop = showroom_workshop,
            messages = json.dumps(messages)
        )
        
        xx = run_prompt_sync(user_query="",system_prompt=prompt,history=[], messages=[], **kwargs)
        mlogger.info("xx == {}".format(xx))
        pass