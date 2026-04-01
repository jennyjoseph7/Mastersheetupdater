import os
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0,BASE_DIR)
from config import AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME, AutocrmModel
from gryd_worker import gryd, gryd_helpers as hp
from autocrm_db_helper import get_pg_connector
json = hp.json
from conversation.yield_response import yield_result,yield_error, yield_status
from conversation.prompt import run_prompt_sync
from datetime import datetime

gryd.SERVICE = AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME
gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(gryd.SERVICE)




# from ai_service import ai_service_app

def WARM_UP():
    mlogger.info("WARM_UP CALLED for {} service".format(gryd.SERVICE))
    with get_pg_connector() as pg:
        pass    
    return

@gryd.is_a_task()
def post_session_process(*args, **kwargs):
    """
    Post session process is a task that runs after a conversation is closed.
    It takes in the session_id and session_data and updates the lead data and session data accordingly.
    It also calls the sentiment agent to get the sentiment analysis of the conversation.
    If the lead disposition is converted, it also gets the appointment date and time, and updates the lead data with it.
    Finally, it updates the session data with the sentiment score and emotion analysis.
    :param session_id: The unique identifier of the session.
    :param session_data: The data of the session.
    :return: The result of the task.
    """
    session_id = kwargs.get("session_id")
    mlogger.info("post_session_process called with session_id == {}".format(session_id))
    
    if not session_id:
        mlogger.info("session_id not passed in kwargs")
        yield from yield_error("error","session_id not passed in kwargs",*args, **kwargs)
        return
    session_data = {}
    with get_pg_connector() as pg:
        session_data = pg.get("session_data_cache","session_id",session_id)
        session_mdl_obj = pg.get("session","session_id",session_id)
    if not session_mdl_obj:
        mlogger.info("session_id not passed in kwargs")
        yield from yield_error("error","session_mdl_obj not found",*args, **kwargs)
        return
    if session_mdl_obj.get("status") in ["busy",
                "no-answer",
                "cancelled",
                "failed",
                "pre-initiated"]:
        mlogger.info("status is {}, Not doing post processing".format(session_mdl_obj.get("status")))
        return
        
    if not session_data:
        mlogger.info("session_id not passed in kwargs")

        yield from yield_error("error","session_data not found",*args, **kwargs)
        return
    session_data = session_data.get("data",{})
    campaign_data = session_data.get("campaign_data")
    mlogger.info("campaign_data == {}".format(campaign_data))
    campaign_type = "pre_sales" if campaign_data.get("campaign_type") == "pre-sales" else "post_sales"

    lead_id = session_data.get("user_data").get(f"{campaign_type}_lead_id")
    lead_data = {}
    with get_pg_connector() as pg:
        lead_data = pg.get(f"{campaign_type}_lead",f"{campaign_type}_lead_id",lead_id) or campaign_data.get("user_data")

    if not lead_data:
        yield from yield_error("error","lead_data not found",*args, **kwargs)
        mlogger.info("session_id not passed in kwargs")

        return

    # lead_disposition = lead_data.get("disposition")

    # if lead_disposition != "engaged":
    #     mlogger.info("lead_disposition is not engaged")
    #     yield from yield_error("error","lead_disposition is not engaged",*args, **kwargs)
    #     return

    messages = session_data.get("messages")
    if not messages or len(messages) == 0:
        mlogger.info("messages not found in session_data")
        yield from yield_error("error","messages not found in session_data",*args, **kwargs)
        return
    sentiment_score = -1
    emotion_analysis = {}
    if messages:
        from agents import sentiment_agent
        sentiment_agent = sentiment_agent.SentimentAnalysisAgent(source = messages, model_identifier="gcp-gemini-2.5-flash-lite")
        aa = sentiment_agent.run()
        sentiment_score = aa.get("conversation_analytics",{}).get("overall_sentiment_score",-1)
        emotion_analysis = aa.get("conversation_analytics",{}).get("emotion_analysis",{})
        mlogger.info(f"sentiment data gave me score = {sentiment_score} and ananlusis = {emotion_analysis}")
    
    updated_lead_data = get_disposition(session_id,session_data) if session_data.get("messages") and len(session_data.get("messages")) > 0 else {"disposition"}
    mlogger.info("got disposition as == {}".format(updated_lead_data))
    
    
    session_update_data = {"disposition":updated_lead_data.get("disposition"),"disposition_detail":updated_lead_data.get("disposition_detail")}
    if updated_lead_data.get("disposition_detail") == "Requested Callback":
        follow_up = get_callback_date_time(session_id,session_data)
        if isinstance(follow_up,dict):
            if "follow_up_date" in follow_up:
                format_string = "%d-%m-%Y %H:%M"
                try:
                    timestamp_object = datetime.strptime(follow_up.get("follow_up_date"), format_string)
                    updated_lead_data["follow_up_date"] = timestamp_object.timestamp()
                except KeyError as e:
                    mlogger.info("KeyError == {}".format(e))
    if updated_lead_data.get("disposition_detail") =="Language barrier":
        follow_up = get_preffered_language(session_id,session_data)
        if isinstance(follow_up,dict):
            if "follow_up_language" in follow_up:
                updated_lead_data["follow_up_language"] = follow_up.get("follow_up_language")

    mlogger.info("lead data =={}".format(updated_lead_data))

    if sentiment_score != -1:
        session_update_data["sentiment_score"] = sentiment_score
    if emotion_analysis:
        session_update_data["emotion_analysis"] = emotion_analysis
    appt_date_time_purpose = {}
    if updated_lead_data.get("disposition") == "converted":
        appt_date_time_purpose = get_appt_date_time_purpose(session_id,session_data)
        updated_lead_data.update(appt_date_time_purpose)
    mlogger.info("updated_lead_data == {}".format(updated_lead_data))
    
    user_or_vehicle_data = get_extra_data(session_id,session_data)
    mlogger.info("user_or_vehicle_data == {}".format(user_or_vehicle_data))
    
    summary_updated = get_summary(session_id,session_data)
    mlogger.info("summary_update == {}".format(summary_updated))

    updated_lead_data["lead_summary"] = summary_updated
    
    if campaign_type == "post_sales":
        if user_or_vehicle_data.get("vehicle_persona_summary"):
            updated_lead_data["vehicle_persona_summary"] = user_or_vehicle_data.get("vehicle_persona_summary")
    
    if campaign_type == "post_sales":
        with get_pg_connector() as pg:
            mlogger.info("updating vehicle == {}".format(user_or_vehicle_data))
            if updated_lead_data.get("follow_up_language"):
                pers_id = session_mdl_obj.get("user_id")
                pg.update("person","user_id",pers_id,{"preferred_language":[updated_lead_data.get("follow_up_language")]})

            pg.update("vehicle","vehicle_id",session_data.get("user_data").get("vehicle_id"),user_or_vehicle_data)
    if campaign_type == "pre_sales":
        with get_pg_connector() as pg:
            mlogger.info("updating person == {}".format(user_or_vehicle_data))
            if updated_lead_data.get("follow_up_language"):
                user_or_vehicle_data["preferred_language"] = [updated_lead_data.get("follow_up_language")]
            pg.update("person","user_id",session_mdl_obj.get("user_id"),user_or_vehicle_data)
    
    with get_pg_connector() as pg:
        updated_lead_data = pg.update(f"{campaign_type}_lead",f"{campaign_type}_lead_id",lead_id,updated_lead_data)
        pg.update("session","session_id",session_id,session_update_data)
        mlogger.info("appointment data == {}".format(appt_date_time_purpose))
        if appt_date_time_purpose.get("appointment_date"):
            visit_data = get_visit_data(session_id,session_data, appt_date_time_purpose,updated_lead_data)
            mlogger.info("visit data == {}".format(visit_data))
            if not visit_data:
                return
            visit_model = "showroom_visit" if campaign_data.get("campaign_type") == "pre-sales" else "service_visit"
            m = AutocrmModel(visit_model)
            mlogger.info("visit_model == {}".format(visit_model))
            posted = m.post(visit_data)
            mlogger.info("visit posted == {}".format(posted))
    
def get_summary(session_id,session_data):
    messages = session_data.get("messages")

    existing_summary = session_data.get("user_data").get("lead_summary")
    if not messages:
        return existing_summary if existing_summary else ""
    if existing_summary:
        prompt = f"""
            You are a summariser agent. I will provide you with the summary from the previous session. You are to update the existing summary using the current session history. Keep the overall summary brief. Try to maintain all pertinent information about their sessions in the summary. 
            Previous session summary - {existing_summary}
            Current session history - {messages}
            Provide the new updated summary.
        """
    else:
        prompt = f"""
            You are a summariser agent. You are to create a brief summary using the current session history. 
            Current session history - {messages}
            Provide the Summary.
        """
    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"gcp-gemini-2.5-flash-lite","session_id":session_id})
    mlogger.info("get_summary prompt response ======= {}".format(resp))
    return resp
def get_lead_variables(campaign_type):
    """
        Get the list of lead variables for the given campaign type.

        Args:
            campaign_type (str): The type of campaign, either "post-sales" or "pre-sales".

        Returns:
            list: A list of lead variables for the given campaign type.

        Raises:
            ValueError: If the campaign type is not one of "post-sales" or "pre-sales".
    """
    if campaign_type == "post-sales":
        return [
            {
            "name": "engine_capacity_cc",
            "type": "number",
            "units": "cc"
        },
        {
            "name": "drivetrain",
            "type": "text",
            "options": [
                "FWD",
                "RWD",
                "AWD",
                "4WD"
            ]
        },
        {
            "name": "engine_number",
            "type": "text"
        },
        {
            "name": "chassis_number",
            "type": "text"
        },
        {
            "name": "accessories",
            "type": "text"
        },
        {
            "name": "purchase_date",
            "type": "number"
        },
        {
            "name": "registration_date",
            "type": "number"
        },
        {
            "name": "original_delivery_date",
            "type": "number"
        },
        {
            "name": "next_service_due",
            "type": "number"
        },
        {
            "name": "service_feedback",
            "type": "text"
        },
        {
            "name": "feedback_rating",
            "type": "text"
        },
        {
            "name": "feedback_sentiment_score",
            "type": "text"
        },
        {
            "name": "warranty_expiry_date",
            "type": "number"
        },
        {
            "name": "extended_warranty_purchased",
            "type": "bool"
        },
        {
            "name": "avg_service_cost",
            "type": "number"
        },
        {
            "name": "service_frequency",
            "type": "number"
        },
        {
            "name": "loan_end_date",
            "type": "number"
        },
        {
            "name": "odometer_reading",
            "type": "number",
            "units": "km"
        },
        {
            "name": "odometer_reading_date",
            "type": "number"
        },
        {
            "name": "avg_monthly_mileage",
            "type": "number",
            "units": "km"
        },
        {
            "name": "vehicle_usage_category",
            "type": "text",
            "options": [
                "Personal",
                "Fleet",
                "Commercial",
                "Rental",
                "Demo"
            ]
        },
        {
            "name": "battery_health",
            "type": "text",
            "options": [
                "Good",
                "Average",
                "Weak",
                "Needs Replacement"
            ]
        },
        {
            "name": "battery_warranty_expiry_date",
            "type": "number"
        },
        {
            "name": "battery_change_date",
            "type": "number"
        },
        {
            "name": "battery_service_date",
            "type": "number"
        },
        {
            "name": "oil_change_date",
            "type": "number"
        },
        {
            "name": "brake_pad_change_date",
            "type": "number"
        },
        {
            "name": "tyre_change_date",
            "type": "number"
        },
        {
            "name": "tyre_change_details",
            "type": "text"
        },
        {
            "name": "tyre_health",
            "type": "text"
        },
        {
            "name": "wheel_alignment",
            "type": "text",
            "options": [
                "Front-end",
                "Thrust",
                "Four-wheel"
            ]
        },
        {
            "name": "suspension_check_date",
            "type": "number"
        },
        {
            "name": "coolant_radiator_service_date",
            "type": "number"
        },
        {
            "name": "ac_vent_cleaning_date",
            "type": "number"
        },
        {
            "name": "underbody_coating_date",
            "type": "number"
        },
        {
            "name": "car_wash_date",
            "type": "number"
        },
        {
            "name": "brake_oil_change_date",
            "type": "number"
        },
        {
            "name": "oil_filter_replacement_date",
            "type": "number"
        },
        {
            "name": "polishing_and_waxing_date",
            "type": "number"
        },
        {
            "name": "ac_vent_cleaning_date",
            "type": "number"
        },
        {
            "name": "repair_notes",
            "type": "text"
        },
        {
            "name": "first_owner_name",
            "type": "text"
        },
        {
            "name": "ownership_status",
            "type": "text",
            "options": [
                "Owned",
                "Leased",
                "Financed",
                "Fleet",
                "Corporate"
            ]
        },
        {
            "name": "finance_loan_status",
            "type": "text"
        },
        {
            "name": "loan_provider",
            "type": "text"
        },
        {
            "name": "loan_account_number",
            "type": "text"
        },
        {
            "name": "loan_amount",
            "type": "number",
            "units": "INR"
        },
        {
            "name": "emi_amount",
            "type": "number",
            "units": "INR"
        },
        {
            "name": "emi_due_date",
            "type": "number"
        },
        {
            "name": "fastag_id",
            "type": "text"
        },
        {
            "name": "rc_book_number",
            "type": "text"
        },
        {
            "name": "status",
            "type": "text",
            "options": [
                "Active",
                "In Service",
                "Sold",
                "Scrapped",
                "Pending Transfer",
                "Inactive"
            ]
        }
        ]
    if campaign_type == "pre-sales":
        return [
            {
            "name": "name",
            "title": "Name",
            "type": "text",
            "ui_element": "text"
        },
        {
            "name": "full_name",
            "title": "Name",
            "type": "text",
            "ui_element": "text"
        },
        {
            "name": "name_title",
            "title": "Name",
            "type": "text",
            "options": [
                "Mr.",
                "Ms.",
                "Mrs.",
                "Dr.",
                "Prof.",
                "Rev.",
                "Fr.",
                "Sister",
                "Brother",
                ""
            ],
            "default": "",
            "ui_element": "text"
        },
        {
            "name": "phone_number",
            "title": "Phone Number",
            "type": "text"
        },
        {
            "name": "email",
            "title": "Email",
            "type": "text",
            "ui_element": "email"
        },
        {
            "name": "area",
            "title": "Area or Region",
            "type": "text"
        },
        {
            "name": "city",
            "title": "City or District",
            "type": "text"
        },
        {
            "name": "pincode",
            "title": "Pincode",
            "type": "text"
        },
        {
            "name": "address",
            "title": "Address",
            "type": "text",
            "ui_element": "textarea"
        },

        {
            "name": "alt_phone_number_2",
            "title": "Alt Phone Number 2",
            "type": "text",
            "ui_element": "tel"
        },
        {
            "name": "alt_phone_number_3",
            "title": "Alt Phone Number 3",
            "type": "text",
            "ui_element": "tel"
        },
        {
            "name": "alt_phone_number_4",
            "title": "Alt Phone Number 4",
            "type": "text",
            "ui_element": "tel"
        },
        {
            "name": "alt_email_2",
            "title": "Alt Email 2",
            "type": "text",
            "ui_element": "email"
        },
        {
            "name": "alt_email_3",
            "title": "Alt Email 3",
            "type": "text",
            "ui_element": "email"
        },
        {
            "name": "alt_email_4",
            "title": "Alt Email 4",
            "type": "text",
            "constraint": {
                "function": "email_validator"
            }
        },
        {
            "name": "preferred_language",
            "title": "Preferred Language",
            "type": "text",
            "ui_element": "select",
            "options": [
                "Spanish (Mexico)",
                "Spanish",
                "Spanish (Argentina)",
                "Spanish (South America)",
                "Arabic (Qatar)",
                "Arabic (UAE)",
                "Arabic (KSA)",
                "Arabic (Oman)",
                "Arabic (Kuwait)",
                "English (India)",
                "English (USA)",
                "English (UK)",
                "English (Australia)",
                "Assamese",
                "Hindi",
                "Tamil",
                "Telugu",
                "Kannada",
                "Malayalam",
                "Marathi",
                "Bengali",
                "Gujarati",
                "Punjabi",
                "Odia",
                "Other"
            ]
        },
        {
            "name": "known_languages",
            "title": "Known Languages",
            "type": "string_list",
            "options": [
                "Spanish (Mexico)",
                "Spanish",
                "Spanish (Argentina)",
                "Spanish (South America)",
                "Arabic (Qatar)",
                "Arabic (UAE)",
                "Arabic (KSA)",
                "Arabic (Oman)",
                "Arabic (Kuwait)",
                "English (India)",
                "English (USA)",
                "English (UK)",
                "English (Australia)",
                "Assamese",
                "Hindi",
                "Tamil",
                "Telugu",
                "Kannada",
                "Malayalam",
                "Marathi",
                "Bengali",
                "Gujarati",
                "Punjabi",
                "Odia",
                "Other"
            ]
        },
        {
            "name": "preferred_communication_channel",
            "title": "Preferred Communication Channel",
            "type": "text",
            "ui_element": "select",
            "options": [
                "Phone",
                "WhatsApp",
                "Email",
                "SMS",
                "In-person"
            ]
        },
        {
            "name": "preferred_contact_window",
            "title": "Preferred Contact Window",
            "type": "nested_object",
            "dict_keys": [
                "start_time",
                "end_time"
            ],
            "ui_element": "time_interval"
        },
        {
            "name": "gender",
            "title": "Gender",
            "type": "text",
            "ui_element": "select",
            "options": [
                "Male",
                "Female",
                "Other"
            ]
        },
        {
            "name": "estimated_monthly_income",
            "title": "Estimated Monthly Income",
            "type": "number",
            "ui_element": "number",
            "units": "INR"
        },
        {
            "name": "education_level",
            "title": "Education Level",
            "type": "text",
            "ui_element": "select",
            "options": [
                "Unknown",
                "High School",
                "Undergraduate",
                "Diploma",
                "Postgraduate",
                "Doctorate",
                "Other"
            ]
        },
        {
            "name": "fleet_owner",
            "title": "Fleet Owner",
            "type": "bool",
            "ui_element": "switch"
        },
        {
            "name": "family_size",
            "title": "Family Size",
            "type": "number",
            "ui_element": "number"
        },
        {
            "name": "marital_status",
            "title": "Marital Status",
            "type": "text",
            "ui_element": "select",
            "options": [
                "Single",
                "Married",
                "Divorced",
                "Widowed",
                "Other"
            ]
        }
        ]
    else:
        return ["vehicle_name","vehicle_model","vehicle_type"]
def get_disposition(session_id, session_data_cache):
    lead_data = session_data_cache.get("user_data")
    campaign_data = session_data_cache.get("campaign_data")
    campaign_objective = campaign_data.get("campaign_objective")
    campaign_purpose = campaign_data.get("purpose")
    campaign_description = campaign_data.get("campaign_description",campaign_data.get("campaign_objective_description"))
    messages = session_data_cache.get("messages")
    p_steps = campaign_data.get("purpose_steps",[])
    purpose_steps=f"These are the mandatory steps that need to be completed for the campaign purpose to be achieved - {', '.join(p_steps)} . If these steps are met in the conversation history with the customer. Then mark the disposition detail as 'Converted'." if p_steps else ""
    message_history = []
    has_user_message = False
    for message in messages:
        mlogger.info("message in get_disposition -  {}".format(message))
        if "intent" in message and message.get("intent") == "llm_response":
            message_history.append({"role" : "me", "message":message.get("message","")})
        else:
            if not has_user_message and message.get("message") and len(message.get("message")) > 0:
                has_user_message = True
            message_history.append({"role" : "customer", "message":message.get("message","")})
    if not has_user_message:
        return {"disposition":"contacted","disposition_detail":"Didnt speak","prioritization_score":10,"prioritization_category":"INACTIVE"}
    mlogger.info("message_history in get_disposition -  {}".format(message_history))
    campaign_type = campaign_data.get("campaign_type")
    example_disposition_response =  """{
        "disposition": "converted" or "engaged",
        "disposition_detail": "choose from list above based on history of conversation",
        "prioritization_score" : "number_values_from_0_to_100",
        "prioritization_category" : "COMPLETE or HOT or WARM or COOL or COLD or INACTIVE"
    }"""
    disp_details_options = [
                "Voicemail",
                "Didnt pickup",
                "Didnt speak",
                "Rejected",
                "Language barrier",
                "Is not decision maker",
                "Will decide later, will purchase within 15 days",
                "Will decide later, will purchase within 1 to 3 months",
                "Will decide later, exploring options",
                "No buying intent",
                "Just Exploring",
                "Will call showroom themselves",
                "Requested Callback",
                "Purchased elsewhere",
                "Converted",
                "Enquired for Pricing",
                "Enquired for Specifications",
                "Enquired for Test Drive",
                "Enquired for Showroom Visit",
                "Enquired for Brochure",
                "Enquired for Dealership Details",
                "Enquired for Others",
                "Comparing with another brand",
                "Others"]

    if campaign_type == "post-sales":
        disp_details_options = [
                "Didnt pickup",
                "Didnt speak",
                "Rejected",
                "Vehicle is commercial or part of a fleet",
                "Vehicle is not being run",
                "Requires special spare parts",
                "Others",
                "Wrong contact number",
                "Voicemail",
                "Has sold/given away the car",
                "Has moved to another location",
                "Cannot make decision on servicing",
                "Will call workshop themselves",
                "Requested Callback",
                "Looking for a discount",
                "Language barrier",
                "Has serviced car in another dealership",
                "Will decide tomorrow",
                "Will decide within 1 to 3 days",
                "Will decide within 4 to 7 days",
                "Will decide within 8 to 14 days",
                "Will decide within 15 to 30 days",
                "Will decide within 31 to 60 days",
                "Will decide within 61 to 90 days",
                "Will decide after 90 days",
                "Converted"
            ]

    prompt = f"""
    You are a analyst bot that has the single purpose of looking at the conversation history with my customer and I and check if they completed the objective of my campaign. 
    I am running a campaign with the objective of {campaign_purpose if campaign_purpose else campaign_objective}.
    These are some details of the campaign - {campaign_description}.
    {purpose_steps}
    I want to know if the purpose of the campaign was met by the customer.
    For example:
        If campaign is about booking a test drive check if the customer booked a test drive.
        If campaign is about buying a car check if the customer bought a car.
        If campaign is about informing the user about an offer we are running check if the customer was informed about the offer.

    The conversation history is as follows:
    {message_history}
    Now check if the objective of the campaign was met by the customer. 
    If the objective was met the disposition should be converted.
    In all other cases it should be engaged.
    Select of the the following disposition detail to be the disposition description. If the disposition is converted the prioritization score should be 100 and prioritization category should be COMPLETE. Other wise determine the interest the have shown during the call and put a score and pick from the categories for prioritization.
    Possible values for disposition_detail:
    {disp_details_options}
    Only pick ONE value from this above list for disposition details.

    The disposition and disposition detail is for the customer and their intent shown in the conversation history.
    Special Cases:-
    - if the user has asked for a callback or requested to speak with a human or a phone call in any way without completing the objective of the campaign then the Disposition Detail would be = 'Requested Callback'.
    - if the user has not completed the objective of the campaign and has suggested they do not understand the language i am speaking or asked me to switch to a different language, the Disposition Detail would be = 'Language barrier'.
    - if the user has disconnected the call without completing the conversation, the Disposition Detail would be = 'Call Disconnected'.
    Your response must be ONLY the JSON object string that i can convert to json using json.loads. 
    Do NOT add code fences, do NOT add markdown formatting, do NOT add triple backticks, 
    do NOT prepend labels (like "json"). Output only valid JSON.
    Incase you detect that the messages from the user are from a Voice Mail then disposition should be "engaged" and disposition detail should be "Voicemail".
    Your response should be in the following JSON format:
    {example_disposition_response}
    """

    mlogger.info("prompt == {}".format(prompt))
    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"gcp-gemini-2.5-flash-lite","session_id":session_id})
    mlogger.info("disposition prompt response ======= {}".format(resp))
    return hp.json.loads(resp)
def get_visit_data(session_id,session_data_cache,appt_date_time_purpose,lead_data):
    mlogger.info("get_visit_data called with session_data_cache == {}".format(json.dumps(session_data_cache)))
    session_data = session_data_cache
    campaign_data = session_data.get("campaign_data",{})
    campaign_type = "pre_sales" if campaign_data.get("campaign_type") == "pre-sales" else "post_sales"

    lead_id = session_data.get("user_data").get(f"{campaign_type}_lead_id")
    campaign_data = session_data.get("campaign_data")
    mlogger.info("campaign_data == {}".format(json.dumps(campaign_data)))
    if campaign_data.get("campaign_type") == "pre-sales":
        if not lead_data.get("showroom_id"):
            mlogger.info("showroom_id not found in lead_data")
            return {}
    if campaign_data.get("campaign_type") == "post-sales":
        if not lead_data.get("workshop_id"):
            mlogger.info("showroom_id not found in lead_data")
            return {}
        
    date_str = appt_date_time_purpose.get("appointment_date")
    time_str = appt_date_time_purpose.get("appointment_time") or "10:00:00"
    full_datetime_str = f"{date_str} {time_str}"
    format_string = "%d-%m-%Y %H:%M"
    timestamp_object = datetime.strptime(full_datetime_str, format_string)
    
    appt_data = {
            "appointment_date" : date_str,
            "appointment_time" : time_str
    }
    if campaign_type == "post_sales":
        appt_data["post_sales_lead_id"]= lead_id
        appt_data["service_date"]= date_str
        appt_data["workshop_id"] = lead_data.get("workshop_id")

    elif campaign_type == "pre_sales":
        appt_data["pre_sales_lead_id"]= lead_id
        appt_data["showroom_id"] = lead_data.get("showroom_id")


    return appt_data
        
def get_appt_date_time_purpose(session_id,session_data_cache):
    """
    Retrieves the appointment date time and purpose from the conversation history.

    Parameters
    ----------
    session_id : str
        The unique identifier of the session.
    session_data_cache : dict
        The data of the session.

    Returns
    -------
    dict
        A dictionary containing the appointment date, time and purpose.
    """
    lead_data = session_data_cache.get("user_data")
    campaign_data = session_data_cache.get("campaign_data")
    campaign_objective = campaign_data.get("campaign_objective")
    campaign_description = campaign_data.get("campaign_description")
    message_history = session_data_cache.get("messages")
    campaign_type = campaign_data.get("campaign_type")
    response_example = {
        "appointment_date": "DD-MM-YYYY format for the date mentioned",
        "appointment_time": "HH:MM format for the time mentioned",
        "purpose": ["purpose1","purpose2","purpose3"]
    }
    prompt = f"""
    You are an analyst bot that looks at my conversation history with my customer and detects if the customer made a booking for a date time and given any purpose details.
    I am running a campaign with the objective of {campaign_objective}.
    these are some details of the campaign {campaign_description}.
    I want to know if the customer made a booking for a date time and given any purpose details.

    The conversation history is as follows:
    {message_history}
    Now check if the customer made a booking for a date time and given any purpose details.
    for your reference the timestamp for today is {datetime.now().strftime("%A, %B %d, %Y %I:%M:%S %p")}
    For example:
    if campaign was to book a service, purpose would be a list of issues they would like to get fixed during the service or list of different services they want.
    if campaign was to book a test drive, purpose would be the aspects of the car they would like to test.

    Your response must be ONLY the JSON object string that i can convert to json using json.loads. 
    Do NOT add code fences, do NOT add markdown formatting, do NOT add triple backticks, 
    do NOT prepend labels (like "json"). Output only valid JSON.

    Your response should be in the following JSON format:
    {response_example}
    """
    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"gcp-gemini-2.5-flash-lite","session_id":session_id})
    mlogger.info("get_appt_date_time_purpose prompt response ======= {}".format(resp))
    return hp.json.loads(resp)

def get_preffered_language(session_id,session_data_cache):
    """
    Retrieves the preffered language from the conversation history.

    Parameters
    ----------
    session_id : str
        The unique identifier of the session.
    session_data_cache : dict
        The data of the session.

    Returns
    -------
    dict
        A dictionary containing the preffered language.
    """
    campaign_data = session_data_cache.get("campaign_data")
    message_history = session_data_cache.get("messages")
    response_example = {
        "follow_up_language": "en"
    }
    prompt = f"""
    You are an analyst bot that looks at my conversation history with my customer and detects if the customer asks to speak in a different language what language was it.
    

    The conversation history is as follows:
    {message_history}
    For your reference the timestamp for today is {datetime.now().strftime("%A, %B %d, %Y %I:%M:%S %p")}
    For example:
    If the customer says anything 'talk in hindi' you should return the value of follow_up_language as 'hi' which is the google language code for hindi.
    If the customer just speaks in a different language for example only speaks in tamil. You should return the value of follow_up_language as 'ta' which is the google language code for tamil.

    Your response must be ONLY the JSON object string that i can convert to json using json.loads. 
    Do NOT add code fences, do NOT add markdown formatting, do NOT add triple backticks, 
    do NOT prepend labels (like "json"). Output only valid JSON.

    Your response should be in the following JSON format:
    {json.dumps(response_example)}
    """
    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"gcp-gemini-2.5-flash-lite","session_id":session_id})
    mlogger.info("callback_date_time prompt response ======= {}".format(resp))
    return hp.json.loads(resp)
        
def get_callback_date_time(session_id,session_data_cache):
    """
    Retrieves the appointment date time and purpose from the conversation history.

    Parameters
    ----------
    session_id : str
        The unique identifier of the session.
    session_data_cache : dict
        The data of the session.

    Returns
    -------
    dict
        A dictionary containing the appointment date, time and purpose.
    """
    lead_data = session_data_cache.get("user_data")
    campaign_data = session_data_cache.get("campaign_data")
    campaign_objective = campaign_data.get("campaign_objective")
    campaign_description = campaign_data.get("campaign_description")
    message_history = session_data_cache.get("messages")
    campaign_type = campaign_data.get("campaign_type")
    response_example = {
        "follow_up_date": "DD-MM-YYYY HH:MM format for the date and time for callback"
    }
    prompt = f"""
    You are an analyst bot that looks at my conversation history with my customer and detects if when i called the customer, and the customer requested to be called back at a later time, what date and time did they ask for the callback.
    

    The conversation history is as follows:
    {message_history}
    For your reference the timestamp for today is {datetime.now().strftime("%A, %B %d, %Y %I:%M:%S %p")}
    For example:
    If the customer says anything like call me tomorrow or day after at 1pm. Return the date time value in the format of DD-MM-YYYY HH:MM where the date month and year is for the date they mentioned and hh mm is for the time they mention.
    If the customer only says tomorrow, or date but does not mention a time. Return the date time value in the format of DD-MM-YYYY HH:MM where the date month and year is for the date they mentioned and hh mm is for 12pm.
    If the customer has asks for a callback at just a time. Return the date time value in the format of DD-MM-YYYY HH:MM where the date month and year is for today and hh mm is for the time they mention.
    If the customer does not mention any date or time. Return the date time value in the format of DD-MM-YYYY HH:MM where the date month and year is for today and hh mm is for 1 hour after the current time.
    
    Your response must be ONLY the JSON object string that i can convert to json using json.loads. 
    Do NOT add code fences, do NOT add markdown formatting, do NOT add triple backticks, 
    do NOT prepend labels (like "json"). Output only valid JSON.

    Your response should be in the following JSON format:
    {json.dumps(response_example)}
    """
    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"gcp-gemini-2.5-flash-lite","session_id":session_id})
    mlogger.info("callback_date_time prompt response ======= {}".format(resp))
    return hp.json.loads(resp)




def get_extra_data(session_id,session_data_cache):
    """
    Retrieves extra data from the conversation history that can be posted to person or vehicle model based on campaign type

    Parameters
    ----------
    session_id : str
        The unique identifier of the session.
    session_data_cache : dict
        The data of the session.

    Returns
    -------
    dict
        A dictionary containing the extra data that was able to be identified from the conversation history.
    """
    lead_data = session_data_cache.get("user_data")
    campaign_data = session_data_cache.get("campaign_data")
    campaign_objective = campaign_data.get("campaign_objective")
    campaign_purpose = campaign_data.get("campaign_purpose")
    campaign_description = campaign_data.get("campaign_description")
    message_history = session_data_cache.get("messages")
    campaign_type = campaign_data.get("campaign_type")
    example_data = {
        "colour": "blue"
    }
    empty_dict = {}
    prompt = f"""
    You are a data identifier bot that helps pick out values i want to save about the user from the conversation history.
    I am running a campaign with the objective of {campaign_purpose if campaign_purpose else campaign_objective}.
    these are some details of the campaign {campaign_description}.
    This the the information i already have about the user.
    {lead_data}
    I want you to check the history for the following attributes:
    {get_lead_variables(campaign_type)}

    The conversation history is as follows: 
    {message_history}

    Your response should be in JSON format with a dictionary with keys for the attributes you were able to identify from the above list. Do not add keys you are unable to find values for or ones that are already available in the data above.

    

    Example if the attributes im looking for include colour and variant_name and the message history contains a message from the user specifying they have a blue car. Your response should be like the following:-
    {example_data}
    if no new data is found then return empty json object.
    Your response must be ONLY the JSON object string that i can convert to json using json.loads(<your response string>). 
    Do NOT add code fences, do NOT add markdown formatting, do NOT add triple backticks, 
    do NOT prepend labels (like "json"). Output only valid JSON.
    Always make sure the exact response you give as string should be a valid JSON string that can be used for python api json.loads(<your response string>)
    """
    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"gcp-gemini-2.5-flash-lite","session_id":session_id})
    mlogger.info("got extra data response as ===== {} --{}".format(resp,type(resp)))
    if resp and isinstance(resp,str):
        updated_dict = hp.json.loads(resp)
    mlogger.info("getting extra data summary for campaign_type {} and updated_dict {}".format(campaign_type,updated_dict))
    if campaign_type == "post-sales":
        current_summary = lead_data.get("vehicle_persona_summary")
        mlogger.info("current_summary == {}".format(current_summary))
        if not current_summary:
            prompt = f"""
                You are a summariser agent. You are to create a brief summary of the information aboout the vehicle that is mentioned in the conversation history provided below. Only keep the relevent information about the vehicle itself.

                Conversation history - {message_history}
                Provide the Summary.

            """
        else:
            prompt = f"""
            You are a summariser agent. You are to update the summary of the vehicle that is mentioned in the conversation history provided below. Only keep the relevent information about the vehicle itself. Use the previous summary as a starting point. Add more information to it based on the conversation history.

            Previous summary - {current_summary}
            Conversation history - {message_history}
            Provide the updated summary.
            """
        mlogger.info("vehicle summary prompt == {}".format(prompt))
        resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"gcp-gemini-2.5-flash-lite","session_id":session_id})
        mlogger.info("got vehicle summary response as ===== {}".format(resp))
        updated_dict["vehicle_persona_summary"] = resp

    return updated_dict














@gryd.is_a_task()
def session_close(*args, **kwargs):
    '''
    Called when session is over (1 day since last message/phone call cut). 
    calls agents to analyse call history
    deletes session_data_cache
    sets disposition and disposition description
    '''
    logger = kwargs.get("logger",mlogger)
    logger.info("session_close called")

    ##TODO call all closing tasks for getting stats etc.
    awaited_tasks = []
    awaited_tasks.append({
        "task": "update_lead_data",
        "kwargs": kwargs
    })
    awaited_tasks.append({
        "task": "update_person_data",
        "kwargs": kwargs
    })
    task_result_generator = gryd.yield_results(awaited_tasks)

    for task_result in task_result_generator:
        logger.info(f"Task '{task_result[1]}' status: {task_result[3]} \n") 
    with get_pg_connector() as pg:
        if kwargs.get("history"):
            ##TODO post history into message model
            pass

        if kwargs.get("session_data_cache"):
            pass
        pg.delete("session_data_cache","session_id",kwargs.get("session_id"))

    yield {"status" : "complete","session_id":kwargs.get("session_id")}

@gryd.is_a_task()
def add_to_session_cache(*args, **kwargs):
    logger = kwargs.get("logger",mlogger)
    logger.info("add_to_session_cache called")
    new_session_data = kwargs.get("session_data_cache_data")
    if not new_session_data:
        yield from yield_error("error","session_data_cache_data not found",*args, **kwargs)
        return
    session_id = kwargs.get("session_id")
    with get_pg_connector() as pg:
        session_data_old = pg.get("session_data_cache","session_id",session_id)
        session_data_cache_updated = pg.update("session_data_cache","session_id",session_id,{"session_id":session_id,"data":session_data_old.get("data",{}).update(new_session_data)})
    yield from yield_status("success","added_to_session_cache",*args, **kwargs)
    yield {"session_data_cache":session_data_cache_updated}
    return



@gryd.is_a_task(
        # function_name = "update_person_vehicle", #custom name of function
        # job_param = "job_params", #provide a job param attr with this name
        # auth_param= "auth_params", #provide a auth param attr with this name
        # logger_param = "logger", #provide a logger attr with this name
        # service = "autocrm-conversation", #set name of service under which you want to create the task
        # is_special_task = False, #IGNORE for result queue etc
        # input_generator = None, #function to generate input for testing #MANDATORY
        # result_verifier = None, #function to verify result should return True or False
        # sample_input = None, #Dict[str, Any]
        # is_agent = True, # True if agent. make sure you adhere to agent input and output 
        # depends_on = None, #:Union[List[Tuple[str, str]], List[str], None] either pass list of service,task or just list of task
        # expected_input = {"fruit_one":"text","fruit_two" : "number"}, #:Union[Dict[str, str], None] 
        # optional_input = {"vegetable" : "text"}, #:Union[Dict[str, str], None] 
        # capability_function = None #:Union[Dict[str, str], None] Defaults to using Docstring
        )
def update_person_vehicle(*args, **kwargs):
    '''
    This task called to update the person or vehicle data based on lead model and conversation history from message model.
    '''
    logger = kwargs.get("logger",mlogger)
    logger.info("test_agent called")
    return


@gryd.is_a_task()
def update_lead_data(*args, **pass_kwargs):
    '''
    look at message history for a session and then check the person and existin lead data nad update the lead model attrs
    '''
    pass
@gryd.is_a_task()
def post_visit_data(*args, **pass_kwargs):
    '''
    agent to update the showroom/workshop visit model object based on messages for session
    '''

    session_id = pass_kwargs.get("session_id")
    if not session_id:
        yield from yield_error("error","session_id not passed in kwargs",*args, **pass_kwargs)
    with get_pg_connector() as pg:
        messages = list(pg.list("message","message_id",None,{"session_id":pass_kwargs.get("session_id")}))
        
    pass

@gryd.is_a_task()
def set_feedback(*args, **pass_kwargs):
    '''
    agent to analyse the feedback/review and also post the data to the session model
    '''
    if not pass_kwargs.get("session_id"):
        yield from yield_error("error","session_id not found",*args, **pass_kwargs)
        return
    
    
    pass

@gryd.is_a_task()
def post_session_processes(*args, **kwargs):
    '''
    This task is called to post process the session data once it is over.
    It can be called with session_ids, campaign_id or dealership_id.
    If session_ids is passed, it will call post_session_process for each session_id.
    If campaign_id is passed, it will fetch all session_ids with campaign_id and call post_session_process for each session_id.
    If dealership_id is passed, it will fetch all session_ids with dealership_id and call post_session_process for each session_id.
    :param session_ids: The list of session_ids to be post processed
    :param campaign_id: The campaign_id to be post processed
    :param dealership_id: The dealership_id to be post processed
    :return: The result of the task
    '''
    mlogger.info("post_session_processes called with kwargs == {}".format(kwargs))
    if not kwargs.get("session_ids") and not kwargs.get("campaign_id") and not kwargs.get("dealership_id"):
        yield from yield_error("error","session_id not found",*args, **kwargs)
        return
    if "session_ids" in kwargs and len(kwargs.get("session_ids",[])) == 0:
        yield from yield_error("error","session_ids not found",*args, **kwargs)
        return
    if "session_ids" in kwargs and len(kwargs.get("session_ids",[])) > 0:
        session_ids = kwargs.get("session_ids")
        for session_id in session_ids:
            yield from post_session_process(session_id=session_id)
        return
    if "campaign_id" in kwargs:
        with get_pg_connector() as pg:
            session_ids = list(pg.list("session",{"campaign_id":kwargs.get("campaign_id")}))
            mlogger.info("running post_lead_process for session_ids == {}".format(session_ids))
            for session_data in session_ids:
                if session_data.get("status") not in ["busy"]:
                    mlogger.info("running post_lead_process for session_id == {} with status == {}".format(session_data.get("session_id"),session_data.get("status")))
                    yield from post_session_process(session_id=session_data.get("session_id"))
        return
    if "dealership_id" in kwargs:
        with get_pg_connector() as pg:
            session_ids = list(pg.list("session",{"dealership_id":kwargs.get("dealership_id")}))
            mlogger.info("running post_lead_process for session_ids == {}".format(session_ids))
            for session_data in session_ids:
                if session_data.get("status") not in ["busy"]:
                    mlogger.info("running post_lead_process for session_id == {} with status == {}".format(session_data.get("session_id"),session_data.get("status")))
                    yield from post_session_process(session_id=session_data.get("session_id"))
        return
