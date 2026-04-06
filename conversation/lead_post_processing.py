import os
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from config import AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME, AUTOCRM_CONVERSATION_SERVICE_NAME,AUTOCRM_CORE_SERVICE_NAME,AUTOCRM_MESSAGE_DELIVERED_ITEM,AUTOCRM_MESSAGE_DELIVERED_PRICE,AUTOCRM_MESSAGE_DELIVERED_UNITS,AutocrmModel
from gryd_worker import gryd, gryd_helpers as hp
from autocrm_db_helper import get_pg_connector
json = hp.json
from conversation.yield_response import yield_result,yield_error, yield_status
from conversation.prompt import run_prompt_sync
from communication.connectors.communication_helpers import get_communication_credential,generate_uid
from datetime import datetime
from agents.sentiment_agent import SentimentAnalysisAgent
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
        sentiment_agent = SentimentAnalysisAgent(source = messages, model_identifier="gcp-gemini-3.1-flash-lite-preview")
        aa = sentiment_agent.run()
        sentiment_score = aa.get("conversation_analytics",{}).get("overall_sentiment_score",-1)
        emotion_analysis = aa.get("conversation_analytics",{}).get("emotion_analysis",{})
        mlogger.info(f"sentiment data gave me score = {sentiment_score} and ananlusis = {emotion_analysis}")
    
    sentiment_classification = get_disposition_classification(query = "", session_id = session_id, session_data_cache = session_data, session_mdl_obj= session_mdl_obj) if session_data.get("messages") and len(session_data.get("messages")) > 0 else {"disposition"}
   
    mlogger.info(f"\n\n sentiment_classified_for_query is ==> {sentiment_classification}\n\n")
    
    updated_lead_data = get_disposition(session_id,session_data,session_mdl_obj, sentiment_classification) if session_data.get("messages") and len(session_data.get("messages")) > 0 else {"disposition"}
    
    mlogger.info("got disposition as == {}".format(updated_lead_data))
    
    session_update_data = {"disposition": updated_lead_data.get("disposition"), "disposition_detail":updated_lead_data.get("disposition_detail")}
    if updated_lead_data.get("disposition_detail").lower() == "requested callback":
        follow_up = get_callback_date_time(session_id,session_data)
        if isinstance(follow_up,dict):
            if "follow_up_date" in follow_up:
                format_string = "%d-%m-%Y %H:%M"
                try:
                    timestamp_object = datetime.strptime(follow_up.get("follow_up_date"), format_string)
                    updated_lead_data["follow_up_date"] = timestamp_object.timestamp()
                except KeyError as e:
                    mlogger.info("KeyError == {}".format(e))
    if updated_lead_data.get("disposition_detail").lower() =="language barrier":
        follow_up = get_preffered_language(session_id,session_data)
        if isinstance(follow_up,dict):
            if "follow_up_language" in follow_up:
                updated_lead_data["follow_up_language"] = follow_up.get("follow_up_language")

    # yield {"lead_data":updated_lead_data,"session_id":session_id,"session_summary":session_mdl_obj.get("summary",""),"session_transcript":session_mdl_obj.get("history",[]), 'sentiment_analyse': sentiment_classification}
    # return
    if sentiment_score != -1:
        session_update_data["sentiment_score"] = sentiment_score
    if emotion_analysis:
        session_update_data["emotion_analysis"] = emotion_analysis
    if sentiment_classification:
        session_update_data["sentiment_classification"] = sentiment_classification
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
    if session_mdl_obj.get("channel") in ["whatsapp_chat"]:
        session_update_data["summary"] = summary_updated
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
    
@gryd.is_a_task(function_name="update_channel_identifier")
def update_channel_identifier(user_id,**data):
    """
    Updates the last contacted channel identifier for a user.
    
    Args:
        *args: Additional positional arguments.
        **data: Additional keyword arguments containing the data to be updated.
            channel (str): The channel identifier to be updated.
            phone_number (str): The phone number associated with the channel.
            email (str): The email address associated with the channel.
            user_id (str): The user id for which to update the channel identifier.
    """
    person_payload = {}
    channel=data.get("channel")
    if channel == "whatsapp_chat":
        person_payload["last_contacted_whatsapp_number"] = data.get("phone_number")
    elif channel == "email":
        person_payload["last_contacted_email"] = data.get("email")
    elif channel in ["voice_phone" ,"rcs"]:
        person_payload["last_contacted_phone_number"] = data.get("phone_number")
    with get_pg_connector() as pg:
        pg.update("person", "user_id", user_id, person_payload)
        mlogger.info(f"[update_channel_identifier] Updated channel identifier for user_id={user_id} with payload={person_payload}")
    return 

@gryd.is_a_task(function_name="update_lead_disposition_and_post_billing")
def update_lead_disposition_and_post_billing(incoming_status, user_id=None, should_bill=None, **data):    
    # mlogger.info(f"[update_lead_disposition] Called with incoming_status={incoming_status} for lead_id={data.get('lead_id')} and DATA= {json.dumps(data,indent=4)}")
    mlogger.info(f"[update_lead_disposition] Attempting to update lead disposition with incoming_status={incoming_status}, user_id={user_id}, data={data}")
    
    post_template_message=data.get("post_template_message")
    if should_bill:
        mlogger.info(f"[post_contact_status] Billing triggered for incoming_status ={incoming_status}")
        post_billing_obj(**data)
    
    DISPOSITION_SEQUENCE = [
        "queued",
        "attempted",
        "busy",
        "error",
        "failed",
        "reached",
        "contacted",
        "engaged",
        "converted"
    ]
    
    def can_update_disposition(current, incoming):
        if not incoming or incoming not in DISPOSITION_SEQUENCE:
            return False
        if not current or current not in DISPOSITION_SEQUENCE:
            return True
        return DISPOSITION_SEQUENCE.index(incoming) > DISPOSITION_SEQUENCE.index(current)
    
    update_payload = {}
    lead_id = data.get("lead_id")
    user_id = user_id or data.get("user_id")
    campaign_type = data.get("campaign_type")
    channel = data.get("channel")
    
    lead_table = (
        "post_sales_lead"
        if campaign_type == "post-sales"
        else "pre_sales_lead"
    )
    lead_pk = (
        "post_sales_lead_id"
        if campaign_type == "post-sales"
        else "pre_sales_lead_id"
    )

    lead_key = lead_id
    with get_pg_connector() as pg:
        # lead_d = list(pg.list(lead_table, {lead_pk: lead_key}))
        mlogger.info(f"Lead table--{lead_table} | lead_pk--{lead_pk} | lead_key--{lead_key}")
        lead=pg.get(lead_table,lead_pk,lead_key)
        # mlogger.info(f"[post_contact_status] lead data={lead}")
        if not lead:
            mlogger.warning(f"[post_contact_status] No lead found for {lead_key}")
            return

        if campaign_type == "post-sales" and user_id and channel:
            mlogger.info(f"[post_contact_status] Updating lead for post-sales with user_id={user_id} and channel={channel}")
            persons = lead.get("persons_involved") or []

            channel_field_map = {
                "whatsapp_chat": (
                    "last_contacted_whatsapp_number",
                    data.get("mobile_number") or data.get("phone_number"),
                ),
                "email": ("last_contacted_email", data.get("email")),
                "voice_phone": (
                    "last_contacted_phone_number",
                    data.get("phone_number"),
                ),
            }

            field_name, field_value = channel_field_map.get(channel, (None, None))

            if field_name and field_value:
                update_payload["persons_involved"] = [
                    (
                        {**p, field_name: field_value}
                        if p.get("user_id") == user_id
                        else p
                    )
                    for p in persons
                ]

        
        if can_update_disposition(lead.get("disposition"), incoming_status):
            mlogger.info(
                f"[post_contact_status] Updating disposition for lead_id={lead_id} "
                f"(current={lead.get('disposition')}, incoming={incoming_status})"
            )
            update_payload["disposition"] = incoming_status
            #only updating the previous_contact_channel when the diposition is updated and it is higher in sequence than the current diposition
            update_payload["previous_contact_channel"] = channel 
            
            # updating previous_contact_channel for person as well only when the disposition is updated and it is higher in sequence than the current diposition
            person_payload = {"previous_contact_channel": channel}
            pg.update("person", "user_id", user_id, person_payload)
        else:
            mlogger.info(
                "[post_contact_status] Disposition skipped "
                f"(current={lead.get('disposition')}, incoming={incoming_status})"
            )

        update_payload.pop("lead_id", None)
        update_payload.pop("dealership_id", None)
        # mlogger.info(f"[post_contact_status] update_payload for lead_id={lead_id}: {update_payload}")
        if update_payload:
            pg.update(
                lead_table,
                lead_pk,
                lead_key,
                update_payload,
            )
        
        # also updating session dispositon--
        template_message = data.get("template_message") if data else None
        if channel in ["whatsapp_chat"]:
            s_d=list(pg.list("session",{"lead_id":lead_id}))
            if not s_d:
                mlogger.info(f"No session found for lead_id: {lead_id}")
                return
            s_d=s_d[0]
            session_id = s_d.get("session_id")
            mlogger.info(f"Updating session disposition for lead_id: {lead_id}")
            pg.update("session","session_id",session_id,{"disposition":incoming_status,"status":incoming_status})
            if post_template_message and template_message and incoming_status in ["delivered", "reached"]:
                mlogger.info(f"Updating template_message in history for lead_id: {lead_id}")
                p={
                    "reply_to": generate_uid(data),
                    "customer_response": "",
                    "request_data": {
                        "customer_response": ""
                    },
                    "session_id": session_id,
                    "user_id": data.get("user_id"),
                    "responses": [
                        {
                            "intent": "greeting",
                            "placeholder": template_message,
                            "index": 1
                        }
                    ]
                }
                # post_messages_data(**p)
                gryd.create_async_task(
                    "post_messages_data",
                    AUTOCRM_CONVERSATION_SERVICE_NAME,
                    args=[],
                    kwargs=p
                )
            
        return 

def post_billing_obj(**message_dict):
    wa_status=message_dict.get("message_status")
    mlogger.info(f"Post billing obj for message_id: {message_dict.get('message_id')} and status: {wa_status}---")
    
    dealership_id=None
    item_description=None
    lead_id=None
    lead_model=None
    mob_num=message_dict.get('mobile_number')
    # posting billing model
    with get_pg_connector() as pg:
        contact_status_data=list(pg.list("contact_status",{"message_id":message_dict.get("message_id")}))
        contact_status_data=contact_status_data[0] if contact_status_data else {}
        
        if contact_status_data:
            dealership_id = contact_status_data.get("dealership_id")
            lead_id = contact_status_data.get("lead_id",None)
            lead_model= 'post_sales_lead' if contact_status_data.get('campaign_type') == 'post-sales' else 'pre_sales_lead'
        else:
            mlogger.info(f"Contact Status Data not found for message_id since it is a inbound message and not through campaign: {message_dict.get('message_id')}")
            session_data=list(pg.list("session",{"phone_number":mob_num}))[0]
            if not session_data: return
            dealership_id=session_data.get("dealership_id",None)
            lead_id=session_data.get('lead_id',None)
            lead_model= 'post_sales_lead' if session_data.get('campaign_type') == 'post-sales' else 'pre_sales_lead'
            
        mlogger.info(f"We have dealership_id: {dealership_id} in contact_status_data")
        c=get_communication_credential(dealership_id=dealership_id, channel="whatsapp_chat")
        if c:
            mlogger.info(f"Communication Credential found for dealership_id: {dealership_id} and channel whatsapp_chat")
        if lead_id:
            mlogger.info(f"We have lead_id: {lead_id} in contact_status_data")
            lead_model_id="post_sales_lead_id" if lead_model == "post_sales_lead" else "pre_sales_lead_id"
            # mlogger.info(f"We have lead_model: {lead_model} and lead_model_id: {lead_model_id} in contact_status_data")
            lead_data=list(pg.list(lead_model,{lead_model_id:lead_id}))[0]
            # mlogger.info(f"We have lead_data: {lead_data}")
            if lead_data:
                item_description =f"{lead_data.get('campaign_type', 'unknown')} - {lead_data.get('campaign_objective_name', 'campaign_objective_id')} - {lead_data.get('campaign_name', 'unknown')} - {lead_data.get('channel', 'unknown')} - {c.get('provider_name', 'unknown')} - {message_dict.get('mobile_number')}"
                campaign_id=lead_data.get('campaign_id')
            else:
                mlogger.info(f"Lead data not found for lead_id: {lead_id}")
                return      
        else:
            mlogger.info(f"Lead data not found for lead_id: {lead_id}")
            return   
    if lead_id and campaign_id and item_description:
        mlogger.info(f"Posting Billing for lead_id: {lead_id} and campaign_id: {campaign_id} with item_description: {item_description}")
        
        gryd.create_async_task(
            'post_billing',
            AUTOCRM_CORE_SERVICE_NAME,
            args=[
                dealership_id,
                "debit",
                AUTOCRM_MESSAGE_DELIVERED_ITEM,
                item_description,
                hp.now(as_datetime=False),
                1,
                AUTOCRM_MESSAGE_DELIVERED_PRICE,
                AUTOCRM_MESSAGE_DELIVERED_UNITS,
                "credits",
                campaign_id,
                "whatsapp_chat"
            ]
        )
        mlogger.info(f"Posted Billing for lead_id: {lead_id} and campaign_id: {campaign_id} with item_description: {item_description}")    


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
    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"gcp-gemini-3.1-flash-lite-preview","session_id":session_id})
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
    
def get_disposition(session_id, session_data_cache,session_mdl_obj, sentiment):
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
            message_history.append({"role" : "my agent", "message":message.get("message","")})
        else:
            if not has_user_message and message.get("message") and len(message.get("message")) > 0:
                has_user_message = True
            message_history.append({"role" : "customer", "message":message.get("message","")})
    if not has_user_message:
        return {"disposition":"contacted","disposition_detail":"No Response","prioritization_score":10,"prioritization_category":"INACTIVE"}
    mlogger.info("message_history in get_disposition -  {}".format(message_history))
    session_summary = session_mdl_obj.get("summary")
    campaign_type = campaign_data.get("campaign_type")
    example_disposition_response =  """{
        "disposition": "converted" or "engaged",
        "disposition_detail": "choose from list above based on history of conversation",
        "prioritization_score" : "number_values_from_0_to_100",
        "prioritization_category" : "COMPLETE or HOT or WARM or COOL or COLD or INACTIVE"
    }"""
    disp_details_options = {
                        "CONVERTED": {
                            "CONVERTED": "The customer completes the purpose of the campaign and provides the necessary information."
                        },
                        "POSITIVE": {
                            "ENQUIRED FOR TEST DRIVE": "the customer by themselves asked for a test drive of the vehicle.",
                            "SHOWROOM VISIT PLANNED": "the customer Already booked a showroom visit.",
                            "WILL DECIDE LATER, WILL PURCHASE WITHIN 15 DAYS": "the customer said they would decide to buy the vehicle within 15 days.",
                            "WILL DECIDE LATER, WILL PURCHASE WITHIN 1 TO 3 MONTHS": "the customer said they would decide to buy the vehicle within 1 to 3 months.",
                            "ENQUIRED FOR PRICING": "the customer by themselves asked for the price of the vehicle.",
                            "ENQUIRED FOR SPECIFICATIONS": "the customer by themselves asked for the specifications of the vehicle.",
                            "ENQUIRED FOR SHOWROOM VISIT": "the customer by themselves asked for a showroom visit of the vehicle.",
                            "ENQUIRED FOR BROCHURE": "the customer by themselves asked for a brochure of the vehicle.",
                            "ENQUIRED FOR DEALERSHIP DETAILS": "the customer by themselves asked for dealership details.",
                            "INTERESTED IN ANOTHER CAR SAME DEALERSHIP": "If user mentions for a different car but from the same dealer",
                            "FOLLOW UP REQUIRED": "the customer Needs a follow up to convince them to complete the campaign objective.",
                            "REQUESTED CALLBACK": "the customer Asked to call back at a later date and or time."
                        },
                        "NEUTRAL": {
                            "WILL DECIDE LATER, EXPLORING OPTIONS": "the customer said they will decide on the purchase of the vehicle at a later time and are only exploring all their options now.",
                            "JUST EXPLORING": "This will only happen if the customer has actually asked about the car or related features but shows no interest in the purpose of the call.",
                            "WILL CALL SHOWROOM/WORKSHOP THEMSELVES": "The customer will contact the dealership, showroom or workshop themselves.",
                            "GENERAL INQUIRY": "the customer is Asking generic questions not specific to the purpose of the campaign or the vehicle.",
                            "COMPARING WITH ANOTHER BRAND": "The customer by themselves is comparing the vehicle with another brand.",
                            "LANGUAGE BARRIER": "If the customer has asked to speak in a different language and did not finish the conversation or intent of the campaign.",
                            "AUDIO ISSUE": "There was issues with hearing the customer or the agent for either party.",
                            "TEST DRIVE COMPLETED": "the customer Already completed a test drive.",
                            "ENQUIRED FOR OTHERS": "the customer by themselves asked for other details not listed above.",
                            "OTHERS": "All other disposition details not listed above."
                        },
                        "NEGATIVE": {
                            "NO RESPONSE": "This category applies only if the user role is completely empty with no text at all from the start to the end of the call. If there is any text or any automated prompt in the user messages then it cannot be marked as No Response.",
                            "CALL DISCONNECTED": "This category applies if a human conversation was established such as the user saying hello or yes or oh yeah but the user then stopped responding or the line went silent after an agent query. It must not be used if an automated recording prompt was detected.",
                            "VOICEMAIL": "This must be selected if any user message contains automated system text such as record your message or beeping. The presence of any automated phrasing in the user role overrides all other categories.",
                            "NOT INTERESTED": "the customer Specifically said they are not interested in the vehicle.",
                            "NO BUYING INTENT": "the customer said they Do not want to purchase a car. Neither are the interested in the car.",
                            "PURCHASED ELSEWHERE": "the customer Already purchased a vehicle elsewhere.",
                            "LOST TO COMPETITION": "the customer Bought a competitor brands vehicle.",
                            "PURCHASE POSTPONED": "the customer indicates that the Purchase has been postponed",
                            "INVALID LEAD": "the customer Not a valid lead.",
                            "TALK TO HUMAN": "The customer request for talking with human."
                        }
                    }
    if campaign_type == "post-sales":
        disp_details_options = {
                "CONVERTED": {
                    "CONVERTED": "The customer completes the purpose of the campaign and provides the necessary information."
                },
                "POSITIVE": {
                    "WILL DECIDE TOMORROW": "The customer said they would decide to service the vehicle tomorrow.",
                    "WILL DECIDE WITHIN 1 TO 3 DAYS": "The customer said they would decide to service the vehicle within 1 to 3 days.",
                    "WILL DECIDE WITHIN 4 TO 7 DAYS": "The customer said they would decide to service the vehicle within 4 to 7 days.",
                    "WILL DECIDE WITHIN 8 TO 14 DAYS": "The customer said they would decide to service the vehicle within 8 to 14 days.",
                    "WILL DECIDE WITHIN 15 TO 30 DAYS": "The customer said they would decide to service the vehicle within 15 to 30 days.",
                    "WILL DECIDE WITHIN 31 TO 60 DAYS": "The customer said they would decide to service the vehicle within 31 to 60 days.",
                    "WILL DECIDE WITHIN 61 TO 90 DAYS": "The customer said they would decide to service the vehicle within 61 to 90 days.",
                    "WILL DECIDE AFTER 90 DAYS": "The customer said they would decide to service the vehicle after 90 days.",
                    "PRICE INQUIRY": "The customer is interested in the price of the service.",
                    "LOOKING FOR A DISCOUNT": "The customer is looking for a discount on the campaign purpose.",
                    "REQUESTED CALLBACK": "The customer asked the agent to call back at a later date and or time."
                },
                "NEUTRAL": {
                    "CUSTOMER BUSY": "The customer was busy.",
                    "WILL CALL WORKSHOP THEMSELVES": "The customer will contact the workshop themselves.",
                    "LANGUAGE BARRIER": "The customer has asked to speak in a different language and did not finish the conversation or intent of the campaign.",
                    "AUDIO ISSUE": "There was issues with hearing the customer or the agent for either party.",
                    "CALL QUALITY ISSUE": "There was issues with the quality of the call.",
                    "CONNECTION ISSUE": "There was issues with the connection between the customer and the agent.",
                    "REQUIRES SPECIAL SPARE PARTS": "The vehicle requires special spare parts for repair.",
                    "OTHERS": "All other disposition details not listed above.",
                    "CANNOT MAKE DECISION ON SERVICING": "The customer the agent has called is not the right person to make the decision."
                },
                "NEGATIVE": {
                    "VEHICLE IS COMMERCIAL OR PART OF A FLEET": "The vehicle is a commercial vehicle and not applicable for the campaign purpose.",
                    "HAS SOLD OR GIVEN AWAY THE CAR": "The customer has sold or given away the vehicle.",
                    "VEHICLE IS NOT BEING RUN": "Vehicle is unused and not being run.",
                    "HAS MOVED TO ANOTHER LOCATION": "The customer has moved to another location.",
                    "WRONG CONTACT NUMBER": "Customer tells the agent they have the wrong person or number that was contacted",
                    "NO RESPONSE": "This category applies only if the user role is completely empty with no text at all from the start to the end of the call.",
                    "CALL DISCONNECTED": "Human conversation was established but the user stopped responding or the line went silent. Not for automated prompts.",
                    "VOICEMAIL": "Selected if any user message contains automated system text (recording prompts, beeps). Overrides all other categories.",
                    "UNSUBSCRIBED": "The customer asked to unsubscribed from the campaign.",
                    "CONTACT FATIGUE": "customer implied they were being contacted too many times by the agent.",
                    "NOT INTERESTED": "The customer specifically said they are not interested (Inferred from general context).",
                    "PURCHASE POSTPONED": "They decided or implied they will postpone the service.",
                    "HAS SERVICED CAR IN ANOTHER DEALERSHIP": "The customer has serviced the vehicle in another dealership.",
                    "EXISTING DEALER CONTACT": "The customer already did the campaign objective from an existing dealership.",
                    "LOST TO COMPETITION": "the customer already did the campaign objective from a competitors workshop",
                    "TALK TO HUMAN": "The customer requested for talking with human.",
                    "INVALID LEAD": "Not a valid lead."
                }
            }

    prompt = f"""
    # You are a analyst bot that has the single purpose of looking at the conversation summary provided below about my customer and my agent and check if they completed the objective of my campaign. 
    # I am running a campaign with the objective of {campaign_purpose if campaign_purpose else campaign_objective}.
    # These are some details of the campaign - {campaign_description}.
    {purpose_steps}
    # I want to know if the purpose of the campaign was met by the customer.
    For example:
        If campaign is about booking a test drive check if the customer booked a test drive.
        If campaign is about buying a car check if the customer bought a car.
        If campaign is about informing the user about an offer we are running check if the customer was informed about the offer.

    # The summary of my conversation with the customer is as follows:\n
    {session_summary}\n
    # The conversation history between my agent and the costomer is ask follows:\n
    {message_history}\n
    # Now check if the objective of the campaign was met by the customer. 
    If the objective was met the disposition should be converted.
    In all other cases it should be engaged.
    If the disposition is converted the prioritization score should be 100 and prioritization category should be COMPLETE. Other wise determine the interest the have shown during the call and put a score and pick from the categories for prioritization.
    # Possible values and description to qualify for disposition_detail are:
    \n{disp_details_options[sentiment.upper()]}\n
    Only pick ONE value from this above list for disposition details.
    The disposition detail is a description of the status of the customer based on the conversation summary provided above. Not what the agent said. Only consider the customer's interaction to conclude on the final disposition detail value.,

    # The disposition and disposition detail is for the customer and their intent shown in the conversation summary above.
    # Special Cases:-
    - if the user has asked for a callback or requested to speak with a human or a phone call in any way without completing the objective of the campaign then the Disposition Detail would be = 'Requested Callback'.
    - if the user has not completed the objective of the campaign and has suggested they do not understand the language i am speaking or asked me to switch to a different language, the Disposition Detail would be = 'Language barrier'.
    # Your response must be ONLY the JSON object string that i can convert to json using json.loads. 
    # Do NOT add code fences, do NOT add markdown formatting, do NOT add triple backticks, 
    # Do NOT prepend labels (like "json"). Output only valid JSON.
    # Your response should be in the following JSON format:
    {example_disposition_response}
    """

    mlogger.info("prompt == {}".format(prompt))
    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"gcp-gemini-3.1-flash-lite-preview","session_id":session_id})
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
    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"gcp-gemini-3.1-flash-lite-preview","session_id":session_id})
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
    messages = session_data_cache.get("messages")
    message_history = []
    for message in messages:
        if "intent" in message and message.get("intent") == "llm_response":
            message_history.append({"role" : "my agent", "message":message.get("message","")})
        else:
            message_history.append({"role" : "customer", "message":message.get("message","")})
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
    If the customer seems to be speaking in a language different from the language the agent is speaking in the follow_up_language should be the google language code for the language the customer is speaking in.
    
    Your response must be ONLY the JSON object string that i can convert to json using json.loads. 
    Do NOT add code fences, do NOT add markdown formatting, do NOT add triple backticks, 
    do NOT prepend labels (like "json"). Output only valid JSON.

    Your response should be in the following JSON format with the language code as the value for the follow_up_language key based on the language that the customer is comfortable in:
    {json.dumps(response_example)}
    """
    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"gcp-gemini-3.1-flash-lite-preview","session_id":session_id})
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
    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"gcp-gemini-3.1-flash-lite-preview","session_id":session_id})
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
    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"gcp-gemini-3.1-flash-lite-preview","session_id":session_id})
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
        resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"gcp-gemini-3.1-flash-lite-preview","session_id":session_id})
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
    if not kwargs.get("session_ids") and not kwargs.get("campaign_id") and not kwargs.get("campaign_ids") and not kwargs.get("dealership_id"):
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
    if "campaign_ids" in kwargs and len(kwargs.get("campaign_ids",[])) > 0:
        campaign_ids = kwargs.get("campaign_ids")
        mlogger.info("running post_lead_process for campaign_ids == {}".format(campaign_ids))
        for campaign_id in campaign_ids:
            with get_pg_connector() as pg:
                session_ids = list(pg.list("session",{"campaign_id":campaign_id}))
                mlogger.info("running post_lead_process for session_ids == {}".format(session_ids))
                for session_data in session_ids:
                    # mlogger.info("running post_lead_process for session_id == {} for campaign_id == {}".format(session_data.get("session_id"),session_data.get("campaign_id")))
                    if session_data.get("status") not in ["busy"]:
                        mlogger.info("running post_lead_process for session_id == {} with status == {}".format(session_data.get("session_id"),session_data.get("status")))
                        yield from post_session_process(session_id=session_data.get("session_id"))
            
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


def get_disposition_classification(query = None, session_id = None, session_data_cache = None, session_mdl_obj = None):
    classify_list = ["negative", "neutral", "positive", "converted"]
    lead_data = session_data_cache.get("user_data")
    campaign_data = session_data_cache.get("campaign_data")
    campaign_objective = campaign_data.get("campaign_objective")
    campaign_purpose = campaign_data.get("purpose")
    campaign_description = campaign_data.get("campaign_description",campaign_data.get("campaign_objective_description"))
    messages = session_data_cache.get("messages")
    session_summary = session_mdl_obj.get("summary")
    message_history = []
    has_user_message = False
    for message in messages:
        mlogger.info("message in get_disposition -  {}".format(message))
        if "intent" in message and message.get("intent") == "llm_response":
            message_history.append({"role" : "my agent", "message":message.get("message","")})
        else:
            if not has_user_message and message.get("message") and len(message.get("message")) > 0:
                has_user_message = True
            message_history.append({"role" : "customer", "message":message.get("message","")})
    if not has_user_message:
        return "neutral"

    p_steps = campaign_data.get("purpose_steps",[])
    purpose_steps = f"These are the mandatory steps that need to be completed for the campaign purpose to be achieved: {', '.join(p_steps)}" if p_steps else ""

    prompt = f"""
    # ROLE
    You are a highly precise analyst bot. Your single purpose is to evaluate a conversation summary and history to determine if a customer met the specific objective of a campaign.

    # CAMPAIGN DETAILS
    - Objective: {campaign_purpose if campaign_purpose else campaign_objective}
    - Description: {campaign_description}
    {purpose_steps}

    # EVALUATION CRITERIA
    1. Look only at the CUSTOMER'S interaction and intent.
    2. Ignore agent actions except to provide context for the customer's response.
    3. Match the customer's status against the following classification list:
    {classify_list}

    # EXAMPLES FOR CLASSIFICATION REFERENCE
    POSITIVE (Customer is interested but hasn't committed/converted yet)
     - Reasoning: The user rejects the current timing or specific detail but maintains a conversational bridge. This indicates high intent with a logistical friction point rather than a lack of interest.
    - Example: [{{'role': 'user', 'message': 'Not at this time'}}, {{'role': 'agent', 'message': 'When would be a better time?'}}] -> Customer is open to future contact.
    
    NEGATIVE (Customer explicitly declines the objective)
     - Reasoning: The user provides a definitive 'No' or a contextual rejection that closes the loop on the specific goal. No alternative or future opening is provided.
     - Example: [{{'role': 'agent', 'message': 'Would you be interested in booking a test drive?'}}, {{'role': 'user', 'message': "No, I'm at a state by state"}}] -> Objective rejected.
    
    NEUTRAL (Inconclusive, language barrier, or no clear progress)
     - Reasoning: The input is semantically "noise" relative to the objective. It contains no discernible intent (positive or negative) or suggests a communication barrier that prevents state progression.
     - Example: [{{'role': 'user', 'message': 'Hindi'}}, {{'role': 'user', 'message': '[background noise]'}}] -> No decision made.

    CONVERTED (Customer successfully completed the primary objective)
     - Reasoning: The user has explicitly accepted the core call-to-action (CTA) or provided the specific data required to close the task (e.g., confirming a time or providing a phone number).
     - Example: [{{'role': 'agent', 'message': 'Are you interested?'}}, {{'role': 'user', 'message': 'Yes, sign me up for the 10 AM slot'}}] -> Objective achieved.
    
    # INPUT DATA
    Conversation Summary:
    {session_summary}

    Message History:
    {message_history}

    # FINAL INSTRUCTION
    Based on the data above, pick exactly ONE value from the classification list provided. Return ONLY that word/phrase and nothing else. No explanation, no punctuation, just the value.
    """
    result = run_prompt_sync(user_query = " ",  system_prompt= prompt, history=[], **{"session_id": session_id, "model_identifier":"gcp-gemini-3.1-flash-lite-preview"})
    return result