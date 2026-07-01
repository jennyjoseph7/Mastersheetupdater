import os
import sys
from os.path import dirname, abspath, join as joinpath

BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from config import AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME, AUTOCRM_CONVERSATION_SERVICE_NAME, AUTOCRM_CORE_SERVICE_NAME, AUTOCRM_MESSAGE_DELIVERED_ITEM, AUTOCRM_MESSAGE_DELIVERED_PRICE, AUTOCRM_MESSAGE_DELIVERED_UNITS, AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_COMMUNICATION_SERVICE_NAME,AUTOCRM_CAMPAIGN_SERVICE_NAME, WHATSAPP_PRICING_INR, AutocrmModel, AUTOCRM_CRM_UPDATE_SERVICE_NAME
import config
from gryd_worker import gryd, gryd_helpers as hp, gryd_audit_helper
from autocrm_db_helper import get_pg_connector
json = hp.json
from conversation.yield_response import yield_result, yield_error, yield_status
from conversation.prompt import run_prompt_sync
from communication.common_functions import get_communication_credential, generate_uid
from datetime import datetime
from agents.sentiment_agent import SentimentAnalysisAgent
from conversation import converse
from campaign.campaign_workflow import CHANNEL_IDENTIFIER_MAP
import autocrm_validator as auto_val
import time
from agents.workflows import WorkflowFactory, send_sop_alert
import autocrm_validator as auto_val
gryd.SERVICE = AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME
THREADS_PER_SESSION = 0.1
__version__ = "0.0.1"
gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(gryd.SERVICE)
PROMPT_DIR = joinpath(dirname(abspath(__file__)), "prompts")



# from ai_service import ai_service_app

def WARM_UP():
    mlogger.info("WARM_UP CALLED for {} service".format(gryd.SERVICE))
    with get_pg_connector() as pg:
        pass    
    return

def update_session_data_in_lead(session_id, status, pg = None):
    """Updates the session data in the lead models associated with the given session id."""
    if not pg:
        mlogger.error("Postgres connection is required to update session data in lead.")
        return
    session_data = pg.get("session", "session_id",session_id)
    if not session_data:
        mlogger.info(f"Could not find session with session_id: {session_id}")
        return
    lead_id = session_data.get("lead_id")
    campaign_type = session_data.get("campaign_type")
    last_interaction_time = session_data.get("last_response_time",None)
    if lead_id:
        model_and_ids = {
            "post-sales": ("post_sales_lead", "post_sales_lead_id"),
            "pre-sales": ("pre_sales_lead", "pre_sales_lead_id")
        }
        lead_model, lead_model_id = model_and_ids.get(campaign_type, (None, None))

        pg.update(lead_model,lead_model_id,lead_id,{"last_session_id":session_id,"last_session_status":status,"last_interaction_time":last_interaction_time})
        mlogger.info(f"Updated session data in lead with session_id: {session_id} and lead_id: {lead_id}")

@gryd.is_a_task(function_name="end_session_and_post_process")
def end_session_and_post_process(*args, **kwargs):
    """
    Ends a session and triggers a post session process task.

    Args:
        session_id (str): The session id to end.

    Returns:
        None
    """
    session_id = kwargs.get("session_id")
    additional_dict = kwargs.get("additional_dict",{})
    pg = kwargs.get("pg",None)
    _call_post_process=kwargs.get("call_post_process",True)
    additional_dict["session_live"] = additional_dict.get("session_live", False)
    additional_dict["status"] = additional_dict.get("status", "completed")
    additional_dict["end_time"] = additional_dict.get("end_time", time.time())

    mlogger.info(f"Ending session with session_id: {session_id}")
    def _do_db_work(pg_conn):
        # if additional_dict has history we will update it in the session model
        pg_conn.update("session", "session_id", session_id, additional_dict)
        update_session_data_in_lead(
            session_id,
            "completed",
            pg=pg_conn  
        )

    if pg:
        _do_db_work(pg)
    else:
        with get_pg_connector() as pg_conn:
            _do_db_work(pg_conn)

    if any( _ == "voice" for _ in kwargs.get("channel", "").split("_")):
        mlogger.info(f"Session with session_id: {session_id} is a voice session, posting messages for voice session.")
        post_messages_for_voice_session(session_id, additional_dict.get("history",[]))
        
    mlogger.info(f"Calling post session process task for session_id: {session_id}")
    if _call_post_process:
        list(post_session_process(**{"session_id":session_id}))
    
    return {"message": f"Session with session_id: {session_id} ended and post session process task triggered."}



def post_messages_for_voice_session(session_id, session_history):
    session_model = gryd.base_model.Model(config.SESSION_MODEL_NAME, config.AUTOCRM_APP_ENTERPRISE_ID)
    session_data = session_model.get(session_id)

    agent_msgs = [d for d in session_history if d.get("role") == "agent"]
    user_msgs = [d for d in session_history if d.get("role") == "user"]

    #in zero'th index add empty user message for better indexing
    user_msgs.insert(0, {"role": "user", "content": "__init__"})
    if len(agent_msgs) != len(user_msgs):
        mlogger.error(
            f"post_history: agent ({len(agent_msgs)}) and user ({len(user_msgs)}) message counts do not match"
        )

    max_len = max(len(user_msgs), len(agent_msgs))
    history = []
    for i in range(max_len):
        u = user_msgs[i] if i < len(user_msgs) else {}
        a = agent_msgs[i] if i < len(agent_msgs) else {}
        tme = hp.time()
        history.append({
            "reply_to": str(generate_uid(u) if u else gryd.hp.make_uuid3(str(time.time()))),
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

    mlogger.info(f"Calling task post_all_messages_for_session with history: {history}")
    converse.post_all_messages_for_session(history=history)

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
    
    session_data = {}; session_mdl_obj = {}
    
    with get_pg_connector() as pg:
        session_data = pg.get("session_data_cache","session_id",session_id)
        session_mdl_obj = pg.get("session","session_id",session_id)
    
    if not session_mdl_obj:
        mlogger.info("session_mdl_obj not found for session_id == {}".format(session_id))
        yield from yield_error("error","session_mdl_obj not found",*args, **kwargs)
        return
    session_data_clean = session_data.get("data", {}) if session_data else {}
    campaign_data = session_data_clean.get("campaign_data", {}) if session_data_clean else {}
    campaign_type_val = campaign_data.get("campaign_type") or session_mdl_obj.get("campaign_type") or ""
    campaign_type = "pre_sales" if campaign_type_val.lower() == "pre-sales" else "post_sales"
    lead_id = session_data_clean.get("user_data", {}).get(f"{campaign_type}_lead_id") or session_mdl_obj.get("lead_id")

    if lead_id:
        try:
            with get_pg_connector() as pg:
                session_hist = auto_val.plot_lead_session_history_func(ins=None, lead_attribute=lead_id)
                update_session_hist = pg.update(f"{campaign_type}_lead", f"{campaign_type}_lead_id", lead_id, {"lead_timeline": session_hist})
                mlogger.info(f"Updated session history in lead data (early update) == {update_session_hist}")
        except Exception as e:
            mlogger.error(f"Failed to update session history early: {e}")

    if session_mdl_obj.get("status") in ["busy",
                                        "no-answer",
                                        "cancelled",
                                        "failed",
                                        "pre-initiated"]:
        mlogger.info("status is {}, Not doing post processing".format(session_mdl_obj.get("status")))
        return
        
    if not session_data:
        mlogger.info("session_data not found for session_id == {}".format(session_id))
        yield from yield_error("error","session_data not found",*args, **kwargs)
        return
    
    session_data = session_data.get("data",{})
    campaign_data = session_data.get("campaign_data", {})
    campaign_type = "pre_sales" if campaign_data.get("campaign_type").lower() == "pre-sales" else "post_sales"
    mlogger.info("campaign_data == {}".format(campaign_data))
    lead_id = session_data.get("user_data").get(f"{campaign_type}_lead_id") or session_mdl_obj.get("lead_id")
    mlogger.info(f"Lead id--{lead_id}, campaign_type--{campaign_type}")
    lead_data = {}
    with get_pg_connector() as pg:
        lead_data = pg.get(f"{campaign_type}_lead",f"{campaign_type}_lead_id",lead_id) or campaign_data.get("user_data") or {}
        sales_campaign_data = pg.get(f"{campaign_type}_campaign", "campaign_id", session_mdl_obj.get("campaign_id")) if session_mdl_obj.get("campaign_id") else {}

        cur_lead = lead_data.get('disposition', None)
        # cur_disp_detail = lead_data.get('disposition_detail', None)


    if not lead_data:
        mlogger.info("lead_data not found for session_id == {} having campaign_data == {}".format(session_id, campaign_data))
        yield from yield_error("error","lead_data not found",*args, **kwargs)
        return

    messages = session_data.get("messages", [])
    if not messages or len(messages) == 0:
        mlogger.info("messages not found in session_data")
        yield from yield_error("error","messages not found in session_data",*args, **kwargs)
        return
    
    sentiment_score = -1
    emotion_analysis = {}

    if messages:
        sentiment_agent = SentimentAnalysisAgent(source = messages, model_identifier="databricks-gemini-3.1-flash-lite")
        senti_output = sentiment_agent.run()
        mlogger.info(f"Sentiment Analysis Output: {senti_output}")
        data = senti_output.get("raw_response", [])
        if data:
            text = data[0].get("text",'').replace('\xa0', ' ')
            aa = json.loads(text) if text else {}
        elif isinstance(senti_output, dict):
            aa = senti_output
        elif isinstance(senti_output, str):
            aa = json.loads(senti_output)
        else:
            aa = {}
        sentiment_score = aa.get("conversation_analytics",{}).get("overall_sentiment_score",-1)
        emotion_analysis = aa.get("conversation_analytics",{}).get("emotion_analysis",{})
        mlogger.info(f"sentiment data gave me score = {sentiment_score} and ananlysis = {emotion_analysis}")
    
    sentiment_classification = get_disposition_classification(query = "", session_id = session_id, session_data_cache = session_data, session_mdl_obj= session_mdl_obj) if messages and len(messages) > 0 else {"disposition"}
       
    updated_lead_data = get_disposition(session_id,session_data,session_mdl_obj, sentiment_classification) if messages and len(messages) > 0 else {"disposition"}
        
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

    session_update_data.update({
        k: v for k, v in {
            "sentiment_score": sentiment_score if sentiment_score != -1 else None,
            "emotion_analysis": emotion_analysis,
            "sentiment_classification": sentiment_classification
        }.items() if v
    })
    
    if sentiment_score != -1:
        session_update_data["sentiment_score"] = sentiment_score
    if emotion_analysis:
        session_update_data["emotion_analysis"] = emotion_analysis
    if sentiment_classification:
        session_update_data["sentiment_classification"] = sentiment_classification

    try:
        summary_text = session_mdl_obj.get('summary') or ''
        convo_msgs = messages[-8:] if isinstance(messages, list) else messages
        convo_text = '\n'.join([m.get('message') or m.get('customer_response') or str(m) for m in convo_msgs])

        # Prefer shared prompt template loaded via helper
        template = get_prompt_file('detect_intent.txt') or get_prompt_file('detect_intent')
        if template:
            prompt_text = template.format(summary=summary_text or '', conversation=convo_text)
        else:
            if summary_text:
                prompt_text = f"Summary: {summary_text}"
            else:
                prompt_text = f"Conversation:\n{convo_text}"

        resp = run_prompt_sync(user_query=" ", system_prompt=prompt_text, history=[], audit_params={"session_id": session_id}, temperature=0.2, **{"model_identifier":"databricks-gemini-3.1-flash-lite", "session_id": session_id})
        mlogger.info(f"Intent detection prompt response: {hp.json.loads(resp)}")
        if isinstance(resp, dict):
            raw = resp.get("output") or resp.get("text") or resp.get("result")
        else:
            raw = resp

        if isinstance(raw, dict):
            analysis = raw
        else:
            try:
                analysis = json.loads(raw)
            except Exception:
                analysis = {}
        primary_intent = analysis.get("primary_intent")
        cust_num = session_mdl_obj.get("phone_number")
        cust_name = session_mdl_obj.get("person_name")

        updated_lead_data["customer_intent"] = primary_intent
        analysis.update({"customer_number": cust_num, "customer_name": cust_name, "dealership_name": campaign_data.get("dealership_name", "Unknown"), 'vehicle_category': campaign_data.get("vehicle_category")})
        session_update_data.update({
            "customer_intent": primary_intent,
            "customer_mood": analysis.get("mood"),
            "customer_sentiment": analysis.get("sentiment"),
            "customer_priority": analysis.get("priority"),
            "recommended_action": analysis.get("recommended_action"),
        })
    
        workflow_name = analysis.get("workflow_to_trigger")
        if workflow_name:
            campaign_objective_id = (campaign_data.get('campaign_objective_id') or lead_data.get('campaign_objective_id'))
            if campaign_objective_id:
                try:
                    wf_obj = WorkflowFactory.get_workflow(campaign_objective_id, dealership_id=session_mdl_obj.get('dealership_id'))
                    wf_obj.handle_workflow(workflow_name, session_id=session_id, session_data=session_data, session_mdl_obj=session_mdl_obj, updated_lead_data=updated_lead_data, sentiment_classification=sentiment_classification, analysis=analysis)
                except Exception:
                    mlogger.exception("Failed to load or trigger workflow based on intent")
    except Exception:
        mlogger.exception("Failed to detect customer intent via prompt")

    # try:

    #     campaign_objective_id = (campaign_data.get('campaign_objective_id') or lead_data.get('campaign_objective_id'))
    #     if campaign_objective_id:
    #         try:
    #             wf_obj = WorkflowFactory.get_workflow(campaign_objective_id, dealership_id=session_mdl_obj.get('dealership_id'))
    #             wf_obj.handle_workflow('sop_alert', session_id=session_id, session_data=session_data, session_mdl_obj=session_mdl_obj, updated_lead_data=updated_lead_data, sentiment_classification=sentiment_classification)
    #         except Exception:
    #             mlogger.exception('Failed to invoke sop_alert workflow')
    #     else:
    #         try:
    #             mlogger.info('No campaign_objective_id found; using send_sop_alert fallback')
    #             send_sop_alert(session_id=session_id, session_data=session_data, session_mdl_obj=session_mdl_obj, updated_lead_data=updated_lead_data, sentiment_classification=sentiment_classification)
    #         except Exception:
    #             mlogger.exception('Failed to send sop alert via fallback')
    # except Exception as e:
    #     mlogger.exception(f"Failed to trigger sop alert workflow: {e}")
    
    appt_date_time_purpose = {}
    
    if updated_lead_data.get("disposition") == "converted":
        appt_date_time_purpose = get_appt_date_time_purpose(session_id,session_data)
        updated_lead_data.update(appt_date_time_purpose)
    
    user_or_vehicle_data = get_extra_data(session_id,session_data)
    
    summary_updated = get_summary(session_id,session_data)

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
                user_or_vehicle_data["preferred_language"] = updated_lead_data.get("follow_up_language")
            pg.update("person","user_id",session_mdl_obj.get("user_id"),user_or_vehicle_data)

    DISPOSITION_SEQUENCE = {
        "queued": 0,
        "attempted": 1,
        "error": 2,
        "failed": 3,
        "busy": 4,
        "reached": 5,
        "contacted": 6,
        "engaged": 7,
        "converted": 8
    }
    new_desposition = updated_lead_data.get("disposition", 0)
    position_new_despo = DISPOSITION_SEQUENCE.get(new_desposition, -1)
    existing_position_despo = DISPOSITION_SEQUENCE.get(cur_lead, -1)
    with get_pg_connector() as pg:
        """
        check heirarchy of diposition before updating lead and session data, only update if the new diposition is higher in heirarchy than the current disposition
        """
        pg.update("session","session_id",session_id,session_update_data)
        mlogger.info("appointment data == {}".format(appt_date_time_purpose))
        try:
            crm_sheet = sales_campaign_data.get("crm_source_details", {}).get('sheet_url', '')
            crm_phone = (updated_lead_data.get("mobile_number") or updated_lead_data.get("phone_number") or lead_data.get("mobile_number") or lead_data.get("phone_number"))
            crm_update = {"sheet_name": crm_sheet, "phone_number": crm_phone}
            crm_update.update({k: v for k, v in updated_lead_data.items() if k not in crm_update})
            if crm_sheet and crm_phone:
                gryd.create_async_task(
                    "update_lead_in_sheet",
                    AUTOCRM_CRM_UPDATE_SERVICE_NAME,
                    args=[],
                    kwargs=crm_update,
                )
                mlogger.info(
                    f"[CRM DEBUG] crm_sheet={crm_sheet}, crm_phone={crm_phone}"
                )
                mlogger.info(f"Entered CRM update for sheet={crm_sheet} phone={crm_phone}")
        except Exception as e:
            mlogger.exception(f"Failed to enter CRM update: {e}")
        session_hist = auto_val.plot_lead_session_history_func(ins = None, lead_attribute = lead_id)
        update_session_hist = pg.update(f"{campaign_type}_lead",f"{campaign_type}_lead_id",lead_id,{"lead_timeline": session_hist, "lead_summary_english": summary_updated})
        if position_new_despo > existing_position_despo:
            updated_lead_data = pg.update(f"{campaign_type}_lead",f"{campaign_type}_lead_id",lead_id,updated_lead_data)
            if appt_date_time_purpose.get("appointment_date"):
                visit_data = get_visit_data(session_id,session_data, appt_date_time_purpose,updated_lead_data, session_mdl_obj)
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

    channel_mapping = {
        "whatsapp_chat": ("last_contacted_whatsapp_number", "phone_number"),
        "email": ("last_contacted_email", "email"),
        "voice_phone": ("last_contacted_phone_number", "phone_number"),
        "rcs": ("last_contacted_phone_number", "phone_number")
    }
    if not channel_mapping.get(channel):
        mlogger.info(f"Channel {channel} not in channel_mapping, skipping channel identifier update.")
        return
    
    if channel in channel_mapping:
        field_name, data_key = channel_mapping[channel]
        person_payload[field_name] = data.get(data_key)

    with get_pg_connector() as pg:
        pg.update("person", "user_id", user_id, person_payload)
        mlogger.info(f"[update_channel_identifier] Updated channel identifier for user_id={user_id} with payload={person_payload}")
    return 

def call_next_campaign_workflow_task(campaign_id,campaign_type,lead_id,channel,channel_identifier,disposition,pg=None,skip_workflow=False):
    mlogger.info(f"In the campaign workflow task for campaign_type: {campaign_type}, lead_id: {lead_id}, channel: {channel}, channel_identifier: {channel_identifier}, disposition: {disposition}")
    mlogger.info(f"Skip workflow flag={skip_workflow} for campaign_id: {campaign_id} and lead_id: {lead_id}")
    if skip_workflow:
        mlogger.info(f"Skipping workflow for campaign_id:{campaign_id}, lead_id:{lead_id}")
        return

    if not campaign_id:
        mlogger.error(f"campaign_id is required for campaign_type: {campaign_type}, lead_id: {lead_id}, channel: {channel}, channel_identifier: {channel_identifier}, disposition: {disposition}")
        return
    campaign_model= "pre_sales_campaign" if campaign_type == "pre-sales" else "post_sales_campaign"
    def _do_db_work(pg_conn):
        a=pg_conn.get(campaign_model,"campaign_id",campaign_id)
        
        if not a or a.get("campaign_status", "").lower() != "active":
            mlogger.info(f"Campaign with campaign_id: {campaign_id} is not active. Not calling next campaign workflow task.")
            return
        # TODO:before calling ananth task check the campaign status and then call.. 
        mlogger.info(f"Calling next campaign workflow task for campaign_type: {campaign_type}, lead_id: {lead_id}, channel: {channel}, channel_identifier: {channel_identifier}, disposition: {disposition}")
        gryd.create_async_task(
            "determine_campaign_next_action",
            AUTOCRM_CAMPAIGN_SERVICE_NAME,
            args=[campaign_type,lead_id,channel,channel_identifier,disposition],
            kwargs={"enterprise_id": AUTOCRM_APP_ENTERPRISE_ID},
        )
        # determine_campaign_next_action(campaign_type,lead_id,channel,channel_identifier,disposition,pg_conn)

    if pg:
        _do_db_work(pg)
    else:
        with get_pg_connector() as pg_conn:
            _do_db_work(pg_conn)
  
  
@gryd.is_a_task(function_name="update_lead_disposition_and_post_billing")
def update_lead_disposition_and_post_billing(incoming_status, user_id=None, should_bill=None, **data):    
    mlogger.info(f"[update_lead_disposition] Attempting to update lead disposition with incoming_status={incoming_status}, user_id={user_id}, data={data}")
    post_template_message=data.get("post_template_message")
    if should_bill:
        mlogger.info(f"[post_contact_status] Billing triggered for incoming_status ={incoming_status}")
        post_billing_obj(**data)
        # post_audit_logs(**data)
        
    DISPOSITION_SEQUENCE = [
        "queued",
        "attempted",
        "error",
        "failed",
        "busy",
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
    
    update_payload = {}; lead_id = data.get("lead_id"); campaign_type = data.get("campaign_type"); channel = data.get("channel")
    user_id = user_id or data.get("user_id")

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
        mlogger.info(f"Lead table--{lead_table} | lead_pk--{lead_pk} | lead_key--{lead_key}")
        lead=pg.get(lead_table,lead_pk,lead_key)
        if not lead:
            mlogger.warning(f"[post_contact_status] No lead found for {lead_key}")
            return
        
        latest_lead_disposition = lead.get("disposition")
        
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
            latest_lead_disposition = incoming_status
            if incoming_status == "failed":
                update_payload["disposition_detail"] = data.get("failure_reason")

            update_payload["previous_contact_channel"] = channel 
            
            person_payload = {"previous_contact_channel": channel}
            pg.update("person", "user_id", user_id, person_payload)
        else:
            mlogger.info(
                "[post_contact_status] Disposition skipped "
                f"(current={lead.get('disposition')}, incoming={incoming_status})"
            )

        update_payload.pop("lead_id", None)
        update_payload.pop("dealership_id", None)
        # check if the session is live and update the session and lead model..
        s_d=list(pg.list_order_by("session",{"lead_id":lead_id,"channel":channel,"lead_model":lead_table, "session_live": True, "status~" : "completed"},order="DESC"))
        if not s_d:
            mlogger.info(f"No session data found for lead_id: {lead_id} and channel: {channel}, skipping session update.")
            return None
        s_d=s_d[0]
        session_id = s_d.get("session_id")
        mlogger.info(f"Since the session is live, Updating session disposition and status for lead_id: {lead_id}")
        _p = {
                "disposition": incoming_status,
                "status": incoming_status,
                **(
                    {"disposition_detail": data.get("failure_reason")}
                    if incoming_status == "failed" and data.get("failure_reason")
                    else {}
                )
            }
        pg.update("session","session_id",session_id,_p)
        # mlogger.info(f"[post_contact_status] update_payload for lead_id={lead_id}: {update_payload}")
        if update_payload and s_d:
            mlogger.info(f"Since the session is live, Updating lead with update_payload for lead_id={lead_id}: {update_payload}")
            pg.update(
                lead_table,
                lead_pk,
                lead_key,
                update_payload
            )
        
        template_message = data.get("template_message") if data else None
        if channel in ["whatsapp_chat"] and s_d:
            # s_d=list(pg.list("session",{"lead_id":lead_id,"channel":"whatsapp_chat","lead_model":lead_table}))
            if post_template_message and template_message and incoming_status in ["delivered", "reached"]:
                mlogger.info(f"Since the session is live, Updating template_message in history for lead_id: {lead_id} for channel: whatsapp_chat")
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
        
        
        # calling ananth task to determine next campaign action based on updated diposition and other params, doing this after updating the lead so that we have the latest lead data in that task.
        channel_identifier = get_channel_identifier(data)
        mlogger.info(f"--------[CALL] Calling next campaign workflow task for latest lead disposition -- {latest_lead_disposition} for filters: {lead.get('campaign_id')},{lead.get('campaign_type')},{lead_id},{data.get('channel')},{channel_identifier},{data.get('skip_workflow', False)}")
        call_next_campaign_workflow_task(lead.get("campaign_id"),lead.get("campaign_type"),lead_id,data.get("channel"),channel_identifier,latest_lead_disposition,pg=pg,skip_workflow=data.get("skip_workflow", False))
        return 

def get_channel_identifier(data):
    
    identifier_key = CHANNEL_IDENTIFIER_MAP.get(data.get("channel"))

    if not identifier_key:
        raise ValueError(f"Unsupported channel: {data.get('channel')}")

    channel_ide = data.get(identifier_key)

    if not channel_ide:
        raise ValueError(
            f"Missing '{identifier_key}' for channel '{data.get('channel')}'"
        )
    return channel_ide

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
            session_data=list(pg.list("session",{"phone_number":mob_num}))
            if not session_data: return
            session_data=session_data[0]
            dealership_id=session_data.get("dealership_id",None)
            lead_id=session_data.get('lead_id',None)
            lead_model= 'post_sales_lead' if session_data.get('campaign_type') == 'post-sales' else 'pre_sales_lead'
            
        mlogger.info(f"We have dealership_id: {dealership_id} in contact_status_data")
        c = get_communication_credential(dealership_id=dealership_id, channel="whatsapp_chat")
        if c:
            mlogger.info(f"Communication Credential found for dealership_id: {dealership_id} and channel whatsapp_chat")
        if lead_id:
            mlogger.info(f"We have lead_id: {lead_id} in contact_status_data")
            lead_model_id="post_sales_lead_id" if lead_model == "post_sales_lead" else "pre_sales_lead_id"

            lead_data=pg.get(lead_model,lead_model_id,lead_id)

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
        
        # posting_audit_logs
        
        mlogger.info(f"Posted Billing for lead_id: {lead_id} and campaign_id: {campaign_id} with item_description: {item_description}")    


def post_audit_logs(**message_dict):
    mlogger.info(f"Post audit logs for message_dict: {json.dumps(message_dict)}")

    output_quantity = 1

    provider = message_dict.get("provider")
    category = message_dict.get("message_category")

    output_pricing_dollars = WHATSAPP_PRICING_INR.get(provider, {}).get(category, 0)

    output_cost_dollars = output_quantity * output_pricing_dollars

    _job = {
        "channel": message_dict.get("channel"),
        "message_id": message_dict.get("message_id"),
        "mobile_number": message_dict.get("mobile_number"),
        "session_id": message_dict.get("session_id"),
        "user_id": message_dict.get("user_id"),
        "enterprise_id": AUTOCRM_APP_ENTERPRISE_ID,
        "service": AUTOCRM_COMMUNICATION_SERVICE_NAME
    }

    _tasks = {
        "output_pricing_units": "count",
        "output_quantity": output_quantity,
        "output_pricing_dollars": output_pricing_dollars,
        "output_cost_dollars": output_cost_dollars
    }

    gryd_audit_helper.audit_log(job=_job, value=_tasks)
    
    
def get_summary(session_id,session_data):
    
    messages = session_data.get("messages")
    existing_summary = session_data.get("user_data").get("lead_summary")

    if not messages:
        return existing_summary if existing_summary else ""
    
    if existing_summary:
        summary_prompt_template = get_prompt_file("existing_summary.txt")
        prompt = summary_prompt_template.format(existing_summary = existing_summary, messages = messages)
    
    else:
        no_summary_prompt_template = get_prompt_file("no_existing_summary.txt")
        prompt = no_summary_prompt_template.format(messages = messages)
    

    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"databricks-gemini-3.1-flash-lite","session_id":session_id})
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
    campaign_data = session_data_cache.get("campaign_data", {})
    campaign_objective = campaign_data.get("campaign_objective", "General Customer Engagement")
    campaign_purpose = campaign_data.get("purpose", "General Customer Engagement")
    campaign_description = campaign_data.get("campaign_description",campaign_data.get("campaign_objective_description"))
    messages = session_data_cache.get("messages")
    p_steps = campaign_data.get("purpose_steps",[])
    purpose_steps=f"These are the mandatory steps that need to be completed for the campaign purpose to be achieved - {', '.join(p_steps)} . If these steps are met in the conversation history with the customer. Then mark the disposition detail as 'Converted'." if p_steps else ""
    message_history = []
    has_user_message = False
    for message in messages:
        if not message:
            continue

        role = message.get("role", "customer")

        message_history.append({"role" : role, "message":message.get("message","")})
        
        if not has_user_message and message.get("message") and len(message.get("message")) > 0:
            has_user_message = True
    
    if not has_user_message:
        return {"disposition":"contacted","disposition_detail":"No Response","prioritization_score":10,"prioritization_category":"INACTIVE"}
    
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
                "CONVERTED": "Use this category when the customer successfully completes the campaign objective during the conversation and provides all required information or confirmation needed to finalize the lead, booking, inquiry, or conversion action."
            },

            "POSITIVE": {
                "ENQUIRED FOR TEST DRIVE": "Use this category when the customer independently asks for a test drive, expresses interest in experiencing the vehicle firsthand, or requests details about scheduling a test drive.",
                
                "SHOWROOM VISIT PLANNED": "Use this category when the customer has already agreed to, scheduled, or confirmed a showroom visit, test drive, or in-person appointment. This includes cases where a specific date, time, or intent to visit has been clearly established.",

                "WILL DECIDE LATER, WILL PURCHASE WITHIN 15 DAYS": "Use this category when the customer indicates a strong purchase intent and mentions they are likely to make a buying decision within approximately 15 days.",

                "WILL DECIDE LATER, WILL PURCHASE WITHIN 1 TO 3 MONTHS": "Use this category when the customer expresses interest in purchasing the vehicle but indicates that the buying decision or purchase timeline is expected within the next 1 to 3 months.",

                "ENQUIRED FOR PRICING": "Use this category when the customer independently asks for the vehicle price, on-road cost, offers, discounts, financing details, EMI information, or any pricing-related information.",

                "ENQUIRED FOR SPECIFICATIONS": "Use this category when the customer independently asks about the vehicle specifications, features, mileage, variants, engine details, safety features, dimensions, technology, or performance-related information.",

                "ENQUIRED FOR SHOWROOM VISIT": "Use this category when the customer independently asks about visiting the showroom, requests showroom timings or location details, or expresses intent to visit the dealership.",

                "ENQUIRED FOR BROCHURE": "Use this category when the customer independently requests a brochure, catalog, specification sheet, PDF, or any official informational material related to the vehicle.",

                "ENQUIRED FOR DEALERSHIP DETAILS": "Use this category when the customer independently asks for dealership contact details, address, branch location, showroom information, or dealer-related assistance.",

                "INTERESTED IN ANOTHER CAR SAME DEALERSHIP": "Use this category when the customer shows interest in a different vehicle model offered by the same dealership or brand instead of the originally discussed vehicle.",

                "FOLLOW UP REQUIRED": "Use this category when the customer shows interest in the offering but does not complete the campaign objective during the current conversation. The customer may need additional persuasion, information, clarification, or future engagement before converting.",

                "REQUESTED CALLBACK": "Use this category when the customer explicitly asks the agent to call again at a later date or time. This includes requests such as asking for a callback tomorrow, later in the day, after work hours, or at any specified future time."
            },

            "NEUTRAL": {
                "WILL DECIDE LATER, EXPLORING OPTIONS": "Use this category when the customer indicates that they are currently evaluating multiple options and are not ready to make an immediate purchase decision.",

                "JUST EXPLORING": "Use this category when the customer asks questions or seeks information about the vehicle but does not show any clear buying intent or commitment toward the campaign objective.",

                "WILL CALL SHOWROOM/WORKSHOP THEMSELVES": "Use this category when the customer states that they will directly contact or visit the dealership, showroom, service center, or workshop on their own without further assistance from the agent.",

                "GENERAL INQUIRY": "Use this category when the customer asks generic or broad questions that are not directly related to the campaign objective, purchase decision, or a specific vehicle requirement.",

                "COMPARING WITH ANOTHER BRAND": "Use this category when the customer compares the discussed vehicle with vehicles from competing brands or asks comparative questions involving another manufacturer.",

                "LANGUAGE BARRIER": "Use this category when the conversation cannot proceed effectively because the customer prefers another language, cannot understand the agent, or communication fails due to language mismatch.",

                "AUDIO ISSUE": "Use this category when the conversation cannot continue properly due to technical audio problems affecting either the customer or the agent. Examples include poor network quality, inability to hear the other party, excessive noise, microphone issues, echo, or broken audio.",

                "TEST DRIVE COMPLETED": "Use this category when the customer confirms that they have already completed a test drive for the discussed vehicle prior to or during the conversation.",

                "ENQUIRED FOR OTHERS": "Use this category when the customer asks for additional information, services, or details that do not fit into any of the predefined enquiry-related categories."
            },

            "NEGATIVE": {
                "NO RESPONSE": "Use this category only when there is absolutely no customer response or input throughout the entire conversation. The user role must be completely empty from start to finish. If there is any speech, text, automated prompt, or voicemail detection, this category must not be used.",

                "CALL DISCONNECTED": "Use this category when a live human interaction was established (for example, the customer responded with greetings or acknowledgements such as 'hello', 'yes', or similar), but the conversation ended unexpectedly due to silence, dropped connection, or the customer stopping responses after the interaction began. Do not use this category if an automated voicemail or recording system was detected.",

                "VOICEMAIL": "Use this category when the call reaches an automated voicemail system or recorded prompt instead of a live customer. Indicators include phrases such as 'please leave a message', 'record your message after the beep', voicemail greetings, or audible beeps. If any automated system prompt is detected, this category overrides all other categories.",

                "NOT INTERESTED": "Use this category when the customer explicitly states that they are not interested in the vehicle, the offer, or continuing the conversation regarding the campaign objective.",

                "NO BUYING INTENT": "Use this category when the customer clearly indicates that they do not intend to purchase any vehicle and have no interest in buying a car at present.",

                "PURCHASED ELSEWHERE": "Use this category when the customer explicitly states that they have already purchased the product or vehicle from another dealer, brand, platform, or competitor, making the current campaign no longer relevant.",

                "LOST TO COMPETITION": "Use this category when the customer confirms that they purchased or finalized a vehicle from a competing automotive brand instead of the discussed brand.",

                "PURCHASE POSTPONED": "Use this category when the customer states that their vehicle purchase plan has been postponed indefinitely or delayed significantly due to personal, financial, or situational reasons.",

                "INVALID LEAD": "Use this category when the contacted person is not a valid or relevant lead for the campaign. Examples include wrong numbers, unrelated individuals, duplicate leads, customers outside the target audience, or cases where the customer clearly states they are not interested or not eligible.",

                "TALK TO HUMAN": "Use this category when the customer explicitly requests to speak with a human representative, sales executive, advisor, or dealership staff instead of continuing with the AI agent or automated system."
            }
            }
    
    if campaign_type == "post-sales":
        disp_details_options = {
                "CONVERTED": {
                    "CONVERTED": "Use this category when the customer successfully completes the campaign objective during the conversation and provides all required information or confirmation needed to finalize the lead, booking, inquiry, or conversion action."
                },

                "POSITIVE": {
                    "ENQUIRED FOR TEST DRIVE": "Use this category when the customer independently asks for a test drive, expresses interest in experiencing the vehicle firsthand, or requests details about scheduling a test drive.",

                    "SHOWROOM VISIT PLANNED": "Use this category when the customer has already agreed to, scheduled, or confirmed a showroom visit, test drive, or in-person appointment. This includes cases where a specific date, time, or intent to visit has been clearly established.",

                    "WILL DECIDE LATER, WILL PURCHASE WITHIN 15 DAYS": "Use this category when the customer indicates a strong purchase intent and mentions they are likely to make a buying decision within approximately 15 days.",

                    "WILL DECIDE LATER, WILL PURCHASE WITHIN 1 TO 3 MONTHS": "Use this category when the customer expresses interest in purchasing the vehicle but indicates that the buying decision or purchase timeline is expected within the next 1 to 3 months.",

                    "ENQUIRED FOR PRICING": "Use this category when the customer independently asks for the vehicle price, on-road cost, offers, discounts, financing details, EMI information, or any pricing-related information.",

                    "ENQUIRED FOR SPECIFICATIONS": "Use this category when the customer independently asks about the vehicle specifications, features, mileage, variants, engine details, safety features, dimensions, technology, or performance-related information.",

                    "ENQUIRED FOR SHOWROOM VISIT": "Use this category when the customer independently asks about visiting the showroom, requests showroom timings or location details, or expresses intent to visit the dealership.",

                    "ENQUIRED FOR BROCHURE": "Use this category when the customer independently requests a brochure, catalog, specification sheet, PDF, or any official informational material related to the vehicle.",

                    "ENQUIRED FOR DEALERSHIP DETAILS": "Use this category when the customer independently asks for dealership contact details, address, branch location, showroom information, or dealer-related assistance.",

                    "INTERESTED IN ANOTHER CAR SAME DEALERSHIP": "Use this category when the customer shows interest in a different vehicle model offered by the same dealership or brand instead of the originally discussed vehicle.",

                    "FOLLOW UP REQUIRED": "Use this category when the customer shows interest in the offering but does not complete the campaign objective during the current conversation. The customer may need additional persuasion, information, clarification, or future engagement before converting.",

                    "REQUESTED CALLBACK": "Use this category when the customer explicitly asks the agent to call again at a later date or time. This includes requests such as asking for a callback tomorrow, later in the day, after work hours, or at any specified future time."
                },

                "NEUTRAL": {
                    "WILL DECIDE LATER, EXPLORING OPTIONS": "Use this category when the customer indicates that they are currently evaluating multiple options and are not ready to make an immediate purchase decision.",

                    "JUST EXPLORING": "Use this category when the customer asks questions or seeks information about the vehicle but does not show any clear buying intent or commitment toward the campaign objective.",

                    "WILL CALL SHOWROOM/WORKSHOP THEMSELVES": "Use this category when the customer states that they will directly contact or visit the dealership, showroom, service center, or workshop on their own without further assistance from the agent.",

                    "GENERAL INQUIRY": "Use this category when the customer asks generic or broad questions that are not directly related to the campaign objective, purchase decision, or a specific vehicle requirement.",

                    "COMPARING WITH ANOTHER BRAND": "Use this category when the customer compares the discussed vehicle with vehicles from competing brands or asks comparative questions involving another manufacturer.",

                    "LANGUAGE BARRIER": "Use this category when the conversation cannot proceed effectively because the customer prefers another language, cannot understand the agent, or communication fails due to language mismatch.",

                    "AUDIO ISSUE": "Use this category when the conversation cannot continue properly due to technical audio problems affecting either the customer or the agent. Examples include poor network quality, inability to hear the other party, excessive noise, microphone issues, echo, or broken audio.",

                    "TEST DRIVE COMPLETED": "Use this category when the customer confirms that they have already completed a test drive for the discussed vehicle prior to or during the conversation.",

                    "ENQUIRED FOR OTHERS": "Use this category when the customer asks for additional information, services, or details that do not fit into any of the predefined enquiry-related categories."
                },

                "NEGATIVE": {
                    "NO RESPONSE": "Use this category only when there is absolutely no customer response or input throughout the entire conversation. The user role must be completely empty from start to finish. If there is any speech, text, automated prompt, or voicemail detection, this category must not be used.",

                    "CALL DISCONNECTED": "Use this category when a live human interaction was established (for example, the customer responded with greetings or acknowledgements such as 'hello', 'yes', or similar), but the conversation ended unexpectedly due to silence, dropped connection, or the customer stopping responses after the interaction began. Do not use this category if an automated voicemail or recording system was detected.",

                    "VOICEMAIL": "Use this category when the call reaches an automated voicemail system or recorded prompt instead of a live customer. Indicators include phrases such as 'please leave a message', 'record your message after the beep', voicemail greetings, or audible beeps. If any automated system prompt is detected, this category overrides all other categories.",

                    "NOT INTERESTED": "Use this category when the customer explicitly states that they are not interested in the vehicle, the offer, or continuing the conversation regarding the campaign objective.",

                    "NO BUYING INTENT": "Use this category when the customer clearly indicates that they do not intend to purchase any vehicle and have no interest in buying a car at present.",

                    "PURCHASED ELSEWHERE": "Use this category when the customer explicitly states that they have already purchased the product or vehicle from another dealer, brand, platform, or competitor, making the current campaign no longer relevant.",

                    "LOST TO COMPETITION": "Use this category when the customer confirms that they purchased or finalized a vehicle from a competing automotive brand instead of the discussed brand.",

                    "PURCHASE POSTPONED": "Use this category when the customer states that their vehicle purchase plan has been postponed indefinitely or delayed significantly due to personal, financial, or situational reasons.",

                    "INVALID LEAD": "Use this category when the contacted person is not a valid or relevant lead for the campaign. Examples include wrong numbers, unrelated individuals, duplicate leads, customers outside the target audience, or cases where the customer clearly states they are not interested or not eligible.",

                    "TALK TO HUMAN": "Use this category when the customer explicitly requests to speak with a human representative, sales executive, advisor, or dealership staff instead of continuing with the AI agent or automated system."
                }
                }

    purpose = campaign_purpose if campaign_purpose else campaign_objective

    details_options = disp_details_options[sentiment.upper()]
        
    prompt_template = get_prompt_file("disposition.txt")
    prompt = prompt_template.format(purpose=purpose, campaign_description = campaign_description, purpose_steps = purpose_steps, session_summary = session_summary, message_history = message_history, disp_details_options = details_options, example_disposition_response=example_disposition_response)

    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id}, temperature = 0.2, **{"model_identifier":"databricks-gemini-3.1-flash-lite","session_id":session_id})

    mlogger.info("prompt == {}".format(prompt))
    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"databricks-gemini-3.1-flash-lite","session_id":session_id, "temperature": 0.2})
    # mlogger.info("disposition prompt response ======= {}".format(resp))

    return hp.json.loads(resp)

def get_visit_data(session_id,session_data_cache,appt_date_time_purpose,lead_data, session_mdl_obj):
    mlogger.info("get_visit_data called with session_data_cache == {}".format(json.dumps(session_data_cache)))
    session_data = session_data_cache
    campaign_data = session_data.get("campaign_data",{})
    campaign_type = "pre_sales" if campaign_data.get("campaign_type") == "pre-sales" else "post_sales"

    lead_id = session_data.get("user_data").get(f"{campaign_type}_lead_id") or session_mdl_obj.get("lead_id")

    mlogger.info("campaign_data == {}".format(json.dumps(campaign_data)))
    if campaign_data.get("campaign_type") == "pre-sales":
        if not lead_data.get("showroom_id"):
            mlogger.info("showroom_id not found in lead_data")
            return {}
        
    if campaign_data.get("campaign_type") == "post-sales":
        if not lead_data.get("workshop_id"):
            mlogger.info("workshop_id not found in lead_data")
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
        appt_data.update({
                            "service_date": date_str,
                            "post_sales_lead_id": lead_id,
                            "workshop_id": lead_data.get("workshop_id")
                        })
        

    elif campaign_type == "pre_sales":
        appt_data.update(
            {
                "pre_sales_lead_id": lead_id,
                "showroom_id": lead_data.get("showroom_id")
            }
        )

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
    # lead_data = session_data_cache.get("user_data")
    campaign_data = session_data_cache.get("campaign_data")
    campaign_objective = campaign_data.get("campaign_objective")
    campaign_description = campaign_data.get("campaign_description")
    message_history = session_data_cache.get("messages")
    # campaign_type = campaign_data.get("campaign_type")
    response_example = {
        "appointment_date": "DD-MM-YYYY format for the date mentioned",
        "appointment_time": "HH:MM format for the time mentioned",
        "purpose": ["purpose1","purpose2","purpose3"]
    }
    
    prompt_template = get_prompt_file("appt_date_time_purpose.txt")
    datetime_format = datetime.now().strftime("%A, %B %d, %Y %I:%M:%S %p")
    prompt = prompt_template.format(campaign_objective=campaign_objective, campaign_description=campaign_description, message_history=message_history, datetime_format=datetime_format, response_example=json.dumps(response_example))

    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"databricks-gemini-3.1-flash-lite","session_id":session_id})
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
    # campaign_data = session_data_cache.get("campaign_data")
    messages = session_data_cache.get("messages")
    message_history = []
    for message in messages:
        if not message:
            continue
        role = message.get("role", "customer")
        # role = "my agent" if message.get("intent", "") in ["llm_response"] else "customer"
        message_history.append({"role" : role, "message":message.get("message","")})
        # if "intent" in message and message.get("intent") == "llm_response":
        # else:
        #     message_history.append({"role" : "customer", "message":message.get("message","")})
    response_example = {
        "follow_up_language": "en"
    }
    
    datetime_format = datetime.now().strftime("%A, %B %d, %Y %I:%M:%S %p")
    
    prompt_template = get_prompt_file("preffered_language.txt")
    prompt = prompt_template.format(message_history=message_history, datetime_format=datetime_format, response_example= json.dumps(response_example))


    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"databricks-gemini-3.1-flash-lite","session_id":session_id})
    mlogger.info("get_preffered_language prompt response ======= {}".format(resp))
    return hp.json.loads(resp)
        
def get_callback_date_time(session_id,session_data_cache):
    """
    Retrieves the callback date time from the conversation history.

    Parameters
    ----------
    session_id : str
        The unique identifier of the session.
    session_data_cache : dict
        The data of the session.

    Returns
    -------
    dict
        A dictionary containing the callback date and time.
    """
    # campaign_data = session_data_cache.get("campaign_data")

    message_history = session_data_cache.get("messages")
    datetime_format = datetime.now().strftime("%A, %B %d, %Y %I:%M:%S %p")
    response_example = {
        "follow_up_date": "DD-MM-YYYY HH:MM format for the date and time for callback"
    }
    prompt_template = get_prompt_file("callback_date_time.txt")
    prompt = prompt_template.format(message_history=message_history, datetime_format=datetime_format, response_example= json.dumps(response_example))

    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"databricks-gemini-3.1-flash-lite","session_id":session_id})
    mlogger.info("get_callback_date_time prompt response ======= {}".format(resp))
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
    lead_variable_campaign_type = get_lead_variables(campaign_type)
    purpose = campaign_purpose if campaign_purpose else campaign_objective 
    example_data = {
        "colour": "blue"
    }
    empty_dict = {}
    prompt_template = get_prompt_file("extra_data.txt")
    prompt = prompt_template.format(purpose=purpose, campaign_description=campaign_description, lead_data=json.dumps(lead_data), lead_variable_campaign_type=json.dumps(lead_variable_campaign_type), message_history=json.dumps(message_history), example_data=json.dumps(example_data))

    resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"databricks-gemini-3.1-flash-lite","session_id":session_id})
    mlogger.info("got extra data response as ===== {} --{}".format(resp,type(resp)))
    
    if resp and isinstance(resp,str):
        updated_dict = hp.json.loads(resp)

    mlogger.info("getting extra data summary for campaign_type {} and updated_dict {}".format(campaign_type,updated_dict))
    
    prompt_not_current_summary = get_prompt_file("not_current_summary.txt")
    prompt_current_summary = get_prompt_file("current_summary.txt") 

    if campaign_type == "post-sales":
        current_summary = lead_data.get("vehicle_persona_summary")
        if not current_summary:
            prompt = prompt_not_current_summary.format(message_history=message_history)

        else:
            prompt = prompt_current_summary.format(current_summary = current_summary, message_history = message_history)

        resp = run_prompt_sync(user_query=" ",system_prompt=prompt,history=[],audit_params={"session_id":session_id},**{"model_identifier":"databricks-gemini-3.1-flash-lite","session_id":session_id})
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
        for campaign_id in campaign_ids:
            with get_pg_connector() as pg:
                session_ids = list(pg.list("session",{"campaign_id":campaign_id}))
                for session_data in session_ids:
                    if session_data.get("status") not in ["busy"]:
                        yield from post_session_process(session_id=session_data.get("session_id"))
            
    if "campaign_id" in kwargs:
        with get_pg_connector() as pg:
            session_ids = list(pg.list("session",{"campaign_id":kwargs.get("campaign_id")}))
            for session_data in session_ids:
                if session_data.get("status") not in ["busy"]:
                    yield from post_session_process(session_id=session_data.get("session_id"))
        return
    if "dealership_id" in kwargs:
        with get_pg_connector() as pg:
            session_ids = list(pg.list("session",{"dealership_id":kwargs.get("dealership_id")}))
            for session_data in session_ids:
                if session_data.get("status") not in ["busy"]:
                    yield from post_session_process(session_id=session_data.get("session_id"))
        return


def get_disposition_classification(query = None, session_id = None, session_data_cache = None, session_mdl_obj = None):
    campaign_data = session_data_cache.get("campaign_data")
    campaign_objective = campaign_data.get("campaign_objective")
    campaign_purpose = campaign_data.get("purpose")
    campaign_description = campaign_data.get("campaign_description",campaign_data.get("campaign_objective_description"))
    purpose = campaign_purpose if campaign_purpose else campaign_objective 
    messages = session_data_cache.get("messages")
    session_summary = session_mdl_obj.get("summary")
    message_history = []
    has_user_message = False
    for message in messages:
        if not message:
            continue
        role = message.get("role", "customer")

        message_history.append({"role" : role, "message":message.get("message","")})

        if not has_user_message and message.get("message") and len(message.get("message")) > 0:
            has_user_message = True

    if not has_user_message:
        return "neutral"

    p_steps = campaign_data.get("purpose_steps",[])
    purpose_steps = f"These are the mandatory steps that need to be completed for the campaign purpose to be achieved: {', '.join(p_steps)}" if p_steps else ""
    
    prompt_template = get_prompt_file("disposition_classification.txt")

    prompt = prompt_template.format(campaign_purpose=purpose, campaign_description=campaign_description, purpose_steps=purpose_steps, session_summary=session_summary, message_history=message_history)

    result = run_prompt_sync(user_query = " ",  system_prompt= prompt, history=[], **{"session_id": session_id, "model_identifier":"databricks-gemini-3.1-flash-lite"})
    return result


def update_error_in_lead_and_session(error_msg,source,**kwargs):
    
    mlogger.info(f"[Error Occured] - {error_msg} -- Source - {source}. So updating in the lead and session.")
    
    lead_id=kwargs.get("lead_id")
    lead_model=kwargs.get("lead_model")
    channel=kwargs.get("channel")
    session_id=kwargs.get("session_id") or None
    lead_model_id="pre_sales_lead_id" if lead_model == "pre_sales_lead" else "post_sales_lead_id"
    with get_pg_connector() as pg:
        if lead_id and lead_model:
            pg.update(lead_model,lead_model_id,lead_id,{"disposition":"error","disposition_detail":error_msg})
        if not session_id:
            s_d=list(pg.list("session",{"lead_id":lead_id,"lead_model":lead_model,"channel":channel}))
            session_id=s_d[0].get("session_id") if s_d else None
        pg.update("session","session_id",session_id,{"disposition":"error","disposition_detail":error_msg})
        mlogger.info(f"Updated ERROR in lead and session for lead_id={lead_id} and lead_model={lead_model} and channel={channel} and session_id={session_id}")
    return

def get_prompt_file(file_name: str) -> str:
    file_path = os.path.join(PROMPT_DIR, file_name)
    with open(file_path,"r", encoding="utf-8") as f:
        prompt_template = f.read()
    return prompt_template
