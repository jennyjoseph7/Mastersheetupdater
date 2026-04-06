# from autocrm_db_helper import get_pg_connector
import functools
import os
import sys
import json
import time
import uuid
import base64
import pprint
import requests
import mimetypes
import smtplib
import boto3
from pathlib import Path
import orjson
from dateutil.relativedelta import relativedelta 
from tempfile import NamedTemporaryFile
from decimal import Decimal
from uuid import UUID
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import make_msgid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional, Dict, Any, List, Union, Callable,Tuple,Generator
from urllib.parse import urlparse
from os.path import (
    exists as ispath,
    dirname,
    abspath,
    basename,
    join as joinpath,
    split as pathsplit,
    splitext,
    sep as dirsep,
    isfile
)

from validate_email import validate_email

# --- Set import path for internal modules ---
sys.path.insert(0, dirname(dirname(abspath(__file__))))
from config import AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME
from gryd_worker import gryd, gryd_helpers as hp,gryd_db_helper as db
logger=gryd.logger

# ------- Load All Configs ----------------------
from connectors.communication_configs import *
# from communication.connectors.whatsapp_connectors.source_connectors import BaseWebhookConverter

# Path to parent folder
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PARENT_DIR)

from autocrm_db_helper import get_pg_connector

# --- Model loaders ---
default_get_or_load_model = gryd.load_gryd_model
NullEmptyCheck=[None, "", "null", "None"]

# common functions

def handle_session_logic(phone_number, channel=None,engaged=False,campaign_details=None, from_web_chat=False):
    payload = {}
    dealership_id = None

    # 1. PERSON
    person = get_or_create_person(phone_number)
    if person:
        payload.update({
            "phone_number": phone_number,
            "user_id": person.get("user_id"),
            "person_name": person.get("name"),
            "email": person.get("email")
        })

    with get_pg_connector() as pg:
        logger.info("TEST Loading session logic...------------")
        # FROM WEB CHAT
        if from_web_chat and campaign_details:
            logger.info("Campaign details received from web chat.")
            payload.update({
                "campaign_id": campaign_details.get("campaign_id"),
                "campaign_type": campaign_details.get("campaign_type"),
                "lead_id": campaign_details.get("lead_id"),
            })
            session = get_or_create_session(payload,channel,engaged)
            return {**session}

        logger.info(f"TEST phone_number: {phone_number}")
        # 3. CONTACT STATUS
        contact_list = list(
            pg.list_order_by("contact_status", {
                "phone_number": phone_number,"channel":channel
            },order_by="created", order="DESC")
        )
        logger.info(f"TEST contact_list present: {len(contact_list)}")
        

        campaign_id = campaign_type = campaign_model = lead_id = None

        if contact_list:
            
            contact = contact_list[0]
            logger.info(f"Contact found: {contact}")

            campaign_id = contact.get("campaign_id")
            campaign_type = contact.get("campaign_type")
            lead_id = contact.get("lead_id")

            campaign_model= "post_sales_campaign" if campaign_type == "post-sales" else "pre_sales_campaign"
            lead_model = "post_sales_lead" if campaign_type == "post-sales" else "pre_sales_lead"
            lead_model_id="post_sales_lead_id" if campaign_type == "post-sales" else "pre_sales_lead_id"
            if lead_id and lead_model:
                l=pg.get(lead_model,lead_model_id, lead_id)
                if not l:
                    logger.info(f"No lead found for lead_id: {lead_id} in model: {lead_model}")
                # l=l[0] if l else {}
                l_person_name = l.get("person_name",None)
                l_campaign_obj_name = l.get("campaign_objective_name",None)
                l_campaign_name = l.get("campaign_name",None)

            payload.update({
                "campaign_id": campaign_id,
                "campaign_type": campaign_type,
                "campaign_model": campaign_model,
                "lead_id": lead_id,
                "lead_model": lead_model,
                "person_name": l_person_name,
                "campaign_objective_name": l_campaign_obj_name,
                "campaign_name": l_campaign_name
            })
        else:
            logger.info(f"No existing campaign association for {phone_number}")

        # 4. CAMPAIGN FLOW
        # Override if campaign_details provided
        if campaign_details:
            logger.info("Overriding campaign with campaign_details.")
            if not campaign_details.get("campaign_id"):
                return {"error": "campaign_details missing campaign_id"}

            campaign_id = campaign_details["campaign_id"]
            campaign_type = campaign_details.get("campaign_type")
            campaign_model= "post_sales_campaign" if campaign_type == "post-sales" else "pre_sales_campaign"
            lead_model = "post_sales_lead" if campaign_type == "post-sales" else "pre_sales_lead"
            payload.update({
                "campaign_id": campaign_id,
                "campaign_type": campaign_type,
                "campaign_model": campaign_model,
                "lead_id": campaign_details.get("lead_id") if campaign_details.get("lead_id") else None,
                "lead_model": lead_model,
                "person_name": campaign_details.get("person_name") if campaign_details.get("person_name") else None,
                "campaign_objective_name": campaign_details.get("campaign_objective_name"),
                "campaign_name": campaign_details.get("campaign_name")
            })

        if campaign_id: 
            model_name = "pre_sales_campaign" if campaign_type == "pre-sales" else "post_sales_campaign"
            # campaign_data = pg.get(model_name, {"campaign_id": campaign_id})
            campaign_data= pg.get(model_name,"campaign_id",campaign_id)
            if campaign_data:
                dealership_id = campaign_data.get("dealership_id")
                payload["campaign_objective_name"] = campaign_data.get("campaign_objective_name")
                payload["campaign_name"] = campaign_data.get("campaign_name")
                payload["dealership_id"] = dealership_id

                # get credentials for dealership (skip if "dave")
                if dealership_id and dealership_id.lower() != "dave":
                    _ = list(pg.list("communication_credential", {"dealership_id": dealership_id}))

            logger.info(f"TEST BEFORE SESSION FINAL PAYLOAD: {payload}")
            session = get_or_create_session(payload,channel)
            return {**session, "dealership_id": dealership_id}

        # 5. NON-CAMPAIGN FLOW
        creds = list(pg.list("communication_credential", {"sender": phone_number}))
        if creds:
            dealership_id = creds[0].get("dealership_id")
            payload["dealership_id"] = dealership_id

        session = get_or_create_session(payload,channel)
        return {**session, "dealership_id": dealership_id}

def apply_filters(session_id=None, user_id=None, channel=None, session_live=None, status=None):
    conditions = [] 
    params = ()
    if session_id:
        conditions.append("dict->>'session_id' = %s")
        params += (session_id,)          
    if user_id:
        conditions.append("dict->>'user_id' = %s")
        params += (user_id,)
    if channel:
        conditions.append("dict->>'channel' = %s")
        params += (channel,)
    if session_live:
        conditions.append("CAST (dict->>'session_live' AS bool) = %s")
        params += (session_live,)
    if status:
        if status.endswith('~'):
            conditions.append("dict->>'status' <> %s")
            status = status[:-1]
            # first_part += "AND LOWER(CAST(dict->>'status' AS text)) <> LOWER(%s)"
            params += (status,)
        else:
            conditions.append("dict->>'session_live' = %s")
            params += (session_live,)

    condition = "Where " + " AND ".join(conditions)
    return condition, params

def get_or_create_session(data,channel=None,engaged=False):
    """
    Find active session or create new one.
    session_live=True AND status != completed
    """
    logger.info(f"In create or get session function. User id: {data.get('user_id')}, data: {data}")
    
    filters = {
        "session_id":data.get("session_id"),
        "user_id":data.get("user_id"),
        # "campaign_id":data.get("campaign_id"),
        # "channel": channel or "whatsapp_chat" if data.get("campaign_type")=="post-sales" else None, 
        "channel": channel or "whatsapp_chat",
        "session_live": True,
        "status": "completed~"
    }
    
    filters = {k: v for k, v in filters.items() if v is not None}
    condition, param = apply_filters(**filters)
    
    logger.info(f"TEST filters for sessions--{filters}")
    with get_pg_connector() as pg:
        sessions = list(db.GrydPGConnector.list(pg, "session", condition, param))
        # logger.info(f'TEST sessions found for {sessions}')
        if sessions:
            new_campaign_id = str(data.get("campaign_id")).strip() if data.get("campaign_id") else None
            old_campaign_id = str(sessions[0].get("campaign_id")).strip() if sessions[0].get("campaign_id") else None

            logger.info(f"Found exisiting session for user_id: {data.get('user_id')}")
            logger.info(f"Old campaign id: {sessions[0].get('campaign_id')}, New campaign id: {data.get('campaign_id')}")

            is_previous_session_inbound=False
            # Handle case where old_campaign_id is 'inbound' and new_campaign_id is None
            if old_campaign_id == "inbound" and not new_campaign_id:
                logger.info("Old campaign id is 'inbound' and new campaign id is None. Returning existing session.")
                is_previous_session_inbound=True
                return sessions[0]
            logger.info(f"Is previous session inbound: {is_previous_session_inbound}")
            if (new_campaign_id != old_campaign_id):
                logger.info("There is a new triggered campaign for this user. Since there is an existing session, we are ending the existing(old) session and creating a new session..")
                logger.info(f"OLD SESSIONID--{sessions[0].get('session_id')}")
                # end the old session also check if session end_time
                end_session(**{"session_id":sessions[0].get("session_id"),"pg":pg})
                # create new session
                s=create_new_session(data,channel,engaged)
                return s
            else:
                logger.info("Session has exisiting campaign_id. So we are returning the existing session.")
                previous_disposition = sessions[0].get("disposition")
                session_id = sessions[0].get("session_id")
                # TODO:check condition for voice_phone also
                if channel in ["whatsapp_chat","rcs"]:
                    channel_identifier=sessions[0].get("phone_number")
                elif channel in ["email"]:
                    channel_identifier=sessions[0].get("email")
                    
                # Case 1: already engaged → do nothing
                if previous_disposition == "engaged":
                    logger.info(f"Session {session_id} already engaged. Nothing to do.")
                # Case 2: converted 
                elif previous_disposition == "converted":
                    logger.info(f"Session {session_id} already converted. Handling converted session logic.")
                    logger.info(f"Calling determine_campaign_next_action for disposition {previous_disposition} and the session_id: {session_id}")
                    # call_next_campaign_workflow_task(sessions[0].get("campaign_id"),sessions[0].get("campaign_type"),sessions[0].get("lead_id"),sessions[0].get("channel"),channel_identifier,data.get("disposition"),pg=pg)
                # Case 3: anything else → update the disposition to engaged
                else:
                    if engaged:
                        logger.info(f"Since the user has interacted . Updating the disposition from {previous_disposition} to engaged for session {session_id}.")
                        logger.info(f"Calling determine_campaign_next_action for the session_id: {session_id}--> diposition is set to engaged.")
                        # call_next_campaign_workflow_task(sessions[0].get("campaign_id"),sessions[0].get("campaign_type"),sessions[0].get("lead_id"),sessions[0].get("channel"),channel_identifier,"engaged",pg=pg)

                    pg.update("session","session_id",session_id,{"disposition":"engaged","status":"interacted"})
                    
                    # updating disposition in lead
                    if data.get("campaign_type") == "pre-sales":
                        pg.update("pre_sales_lead","pre_sales_lead_id",data.get("lead_id"),{"disposition":"engaged"})
                    elif data.get("campaign_type") == "post-sales":
                        pg.update("post_sales_lead","post_sales_lead_id",data.get("lead_id"),{"disposition":"engaged"})
                    # TODO:update last_contacted_whatsapp_number,last_contacted_email,last_contacted_phone_number in person model ( refer post_sales_lead)
                    sessions[0]["disposition"] = "engaged"
                return sessions[0]

        logger.info(f"No Existing session found. Creating a new one..")
        
        # Create new session
        s=create_new_session(data,channel,engaged)
        
        return s


def end_session(*args, **kwargs):
    """
    Ends a session and triggers a post session process task.

    Args:
        session_id (str): The session id to end.

    Returns:
        None
    """
    session_id=kwargs.get("session_id")
    additional_dict=kwargs.get("additional_dict",{})
    pg=kwargs.get("pg",None)
    _call_post_process=kwargs.get("call_post_process",True)
    additional_dict["session_live"] = additional_dict.get("session_live", False)
    additional_dict["status"] = additional_dict.get("status", "completed")
    additional_dict["end_time"] = additional_dict.get("end_time", time.time())

    logger.info(f"Ending session with session_id: {session_id}")
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
    logger.info(f"Calling post session process task for session_id: {session_id}")
    # post_session_process(**{"session_id":session_id})
    if _call_post_process:
        gryd.create_async_task("post_session_process",AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME,args=[],kwargs={"session_id":session_id})
    logger.info(f"Session with session_id: {session_id}. Has been ended.")

def handle_session_post_process_or_end(session_id,pg,history_updated,can_call_post_process,inactive_cutoff_epoch):
    """
    Handles post session process or end session based on session end date and history update.

    If the end date is reached and there is no new history, the session is ended.
    If the end date is reached but there is new history, the post session process is triggered.
    If there is new history and can_call_post_process is True, the post session process is triggered.
    Also updates the last_post_process_time in the session_model.

    Args:
        session_id (str): The session id to handle.
        pg (GrydPGConnector): The database connector.
        history_updated (bool): Whether there is new history.
        can_call_post_process (bool): Whether to call the post session process.

    Returns:
        None
    """
    logger.info(f"In Handling session post process or end function. For session_id: {session_id} and history_updated: {history_updated} and can_call_post_process: {can_call_post_process}")
    session = pg.get("session", "session_id",session_id)
    if not session:
        logger.warning(f"Session {session_id} not found")
        return
    campaign_model = "pre_sales_campaign" if session.get("campaign_type") == "pre-sales" else "post_sales_campaign"
    campaign_id=session.get("campaign_id")
    campaign = pg.get(campaign_model, "campaign_id",campaign_id)
    if not campaign:
        logger.warning(f"Campaign {campaign_id} not found for session {session_id}")
        return
    end_date_str = campaign.get("end_date")
    now_epoch = int(time.time())
    end_date_epoch = int(end_date_str) if end_date_str else None
    logger.info(f"Inactive cutoff epoch: {inactive_cutoff_epoch}")
    is_inactive = (
        inactive_cutoff_epoch is not None and
        now_epoch > inactive_cutoff_epoch
    )
    # end_session if end_date reached and no history to be updated..
    if end_date_epoch and now_epoch >= end_date_epoch:
        if not history_updated and is_inactive:
            logger.info(f"End date reached for session {session_id} and no new history and also its been inactive for more than {inactive_cutoff_epoch} seconds. So ending the session.")
            end_session(**{"session_id":session_id,"call_post_process":False}, pg=pg)
            return

        logger.info(f"End date reached for session {session_id} but history updated .Since it has been inactive for less than {inactive_cutoff_epoch} seconds. So not ending the session.")

    # call post_session_process only if there is new history 
    if history_updated and can_call_post_process:
        logger.info(f"Triggering post_session_process for session {session_id} as history updated.And not ending session.")

        gryd.create_async_task(
            "post_session_process",
            AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME,
            args=[],
            kwargs={"session_id": session_id},
        )

        # also updating the last_post_process_time in session_model..
        pg.update(
            "session",
            "session_id",
            session_id,
            {"last_post_process_time": now_epoch,
             "has_unprocessed_history": False
             }
        )
        logger.info(f"after triggering post_session_process for session {session_id}.Also updating the last_post_process_time in session_model.")
        return
        
def create_new_session(data,channel=None,engaged=False):
    logger.info(f"Creating new session for user_id: {data.get('user_id')} and data: {json.dumps(data,indent=4)}")
    with get_pg_connector() as pg:
        new_session = {
            **data,
            "session_live": True,
            "channel": channel or "whatsapp_chat",
            "status": "interacted" if engaged else "queued",
            "disposition": "engaged" if engaged else "queued",
            "campaign_type": data.get("campaign_type","inbound"),
            "campaign_id": data.get("campaign_id",'inbound'),
            "person_name": data.get("person_name"),
            "campaign_objective_name": data.get("campaign_objective_name"),
            "campaign_name": data.get("campaign_name"),
            "created": time.time(),
            "updated": time.time(),
            "start_time": time.time()
        }
                
        data["updated"] = time.time()
        # logger.info(f"Data for new session: {json.dumps(new_session,indent=4)}")
        # logger.info(f"Generating session_id for new session with data: {json.dumps(data,indent=4)}")
        session_id=generate_uid(data)
        s= pg.update("session","session_id",session_id,new_session)
        logger.info(f"Session with user_id: {data.get('user_id')}. Doesnt exist. Created a new session. And the session_id is -- {s}")
        
        # updating last_session_channel
        if data.get("campaign_type") == "pre-sales":
            pg.update("pre_sales_lead","pre_sales_lead_id",s.get("lead_id"),{"last_session_channel":channel,"user_id":data.get("user_id")})
        elif data.get("campaign_type") == "post-sales":
            pg.update("post_sales_lead","post_sales_lead_id",s.get("lead_id"),{"last_session_channel":channel})
        # TODO:update last_contacted_whatsapp_number,last_contacted_email,last_contacted_phone_number in person model ( refer post_sales_lead)
        return s 


def update_session_data_in_lead(session_id,status,pg=None):
    if not pg:
        logger.error("Postgres connection is required to update session data in lead.")
        return
    session_data = pg.get("session", "session_id",session_id)
    if not session_data:
        logger.info(f"Could not find session with session_id: {session_id}")
    lead_id = session_data.get("lead_id")
    campaign_type = session_data.get("campaign_type")
    last_interaction_time = session_data.get("last_response_time",None)
    if lead_id:
        lead_model="post_sales_lead" if campaign_type == "post-sales" else "pre_sales_lead"
        lead_model_id="post_sales_lead_id" if campaign_type == "post-sales" else "pre_sales_lead_id"
        pg.update(lead_model,lead_model_id,lead_id,{"last_session_id":session_id,"last_session_status":status,"last_interaction_time":last_interaction_time})
        logger.info(f"Updated session data in lead with session_id: {session_id} and lead_id: {lead_id}")

def get_or_create_person(phone_number):
    """Return person object; create if not exists."""
    logger.info(f"Getting or creating person for phone_number: {phone_number}")
    
    with get_pg_connector() as pg:
        # filters={"phone_number":phone_number,"_sort_by": "updated", "_sort_reverse": True}
        person_list = list(pg.list_order_by(
            "person",
            {"phone_number":phone_number},
            order_by="updated",
            order="DESC"
        ))
        
        logger.info(f"Person list found: {person_list}")
        if person_list:
            logger.info(f"Person already exists for phone_number: {phone_number} and the user_id is {person_list[0].get('user_id')}")
            return person_list[0]  
        
        d={
            "phone_number": phone_number,
            "created":time.time(),
        }
        # Create new person
        user_id_attr=generate_uid(d)
        logger.info(f"user_id_attr: {user_id_attr}")
        d= pg.update("person","user_id",user_id_attr,{
            "phone_number": phone_number,
            "created":time.time(),
            "updated":time.time()
            })
        logger.info(f"Person with phone_number: {phone_number}. Doesnt exist. Created a new one. data: {d}")
        return d

def generate_uid(data):
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data, sort_keys=True)
    else:
        data_str = str(data)

    uid = uuid.uuid3(uuid.NAMESPACE_DNS, data_str)
    uid=str(uid)
    # logger.info(f"Generated UID: {uid} and type of uid: {type(uid)} for data: {data_str}")
    return uid

def get_communication_credential(dealership_id="daveai", channel=None):
    logger.info(f"Getting communication credential for dealership - {dealership_id}")

    if not channel:
        logger.info(
            f"Channel not provided for dealership - {dealership_id}. Returning None."
        )
        return None

    with get_pg_connector() as pg:
        creds = list(
            pg.list(
                "communication_credential",
                {"dealership_id": dealership_id, "channel": channel}
            )
        )
        if creds:
            return creds[0]

        # Fallback to default dealership "daveai" if no creds found for the dealership and channel
        if dealership_id != "daveai":
            logger.info(
                f"No credential found for dealership - {dealership_id}. "
                f"Falling back to default dealership - daveai for channel - {channel}"
            )
            creds = list(
                pg.list(
                    "communication_credential",
                    {"dealership_id": "daveai", "channel": channel}
                )
            )
            if creds:
                return creds[0]

    return None

def reload_model_ref(model_name,enteprise_id):
        logger.info(f"Getting Model Connection for model_name: {model_name} and enteprise_id : {enteprise_id}")
        for model_conn_retry in range(MAX_MODEL_CONN_RETRY):
            try:
                return gryd.load_gryd_model(model_name,enteprise_id)
            except Exception as e:
                hp.print_error()
                logger.error(f"Unable to load model retrying for {model_conn_retry+1}")
                time.sleep(20)
        logger.info(f"Max Retry of {MAX_MODEL_CONN_RETRY} done..Unable to load the model...")
        raise ConnectionError("Unable to connect the model")

def is_within_last_minute(ts: str, fmt: str = "%Y-%m-%dT%H:%M:%S") -> bool:
    """
    Check if the given timestamp string is within the last 60 seconds.
    
    Args:
        ts (str): Timestamp string (e.g., "2025-09-07T10:35:21")
        fmt (str): Format of the timestamp string
    
    Returns:
        bool: True if within last 60 seconds, else False
    """
    try:
        given_time = datetime.strptime(ts, fmt)
    except ValueError:
        return False

    now = datetime.utcnow()
    return (now - given_time) <= timedelta(seconds=60)

def _wait_for_next_minute(last_minute_ts: str):
    """Sleep until the next minute boundary based on last_minute_ts."""
    last_dt = datetime.fromisoformat(last_minute_ts)
    next_window = last_dt + timedelta(minutes=1)
    now = datetime.utcnow()
    wait_seconds = (next_window - now).total_seconds()
    if wait_seconds > 0:
        logger.info(f"Rate limit reached. Sleeping for {int(wait_seconds)} seconds...")
        time.sleep(wait_seconds + 1)  # +1 sec buffer

# ✅ Universal execution time logger with warning support
def timelogger(label: Optional[str] = None, warn_threshold: float = 10.0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            instance = args[0] if args else None
            class_name = type(instance).__name__ if hasattr(instance, "__class__") and not isinstance(instance, type) else ""
            func_label = label or func.__name__
            full_label = f"{class_name}.{func_label}" if class_name else func_label

            start_time = time.time()
            logger.info(f"[⏱️ START] {full_label} at {datetime.now().isoformat()}")

            try:
                result = func(*args, **kwargs)
                logger.debug(f"[🔁 RETURN] {full_label} => {result}")
                return result
            except Exception as e:
                logger.error("Arguments passed to function:")
                logger.error(f"args: {pprint.pformat(args)}")
                logger.error(f"kwargs: {pprint.pformat(kwargs)}")
                hp.print_error()
            finally:
                duration = round(time.time() - start_time, 3)
                if duration > warn_threshold:
                    logger.warning(f"[⚠️ SLOW] {full_label} took {duration}s (>{warn_threshold}s)")
                else:
                    logger.info(f"[✅ DONE] {full_label} completed in {duration}s")
        return wrapper
    return decorator

def format_box_log(log_dict, message=''):
    # Convert all values to strings first
    str_items = {str(k): str(v) for k, v in log_dict.items()}
    max_key_len = max(len(k) for k in str_items.keys())
    max_val_len = max(len(v) for v in str_items.values())

    border = "+" + "-" * (max_key_len + 2) + "+" + "-" * (max_val_len + 2) + "+"
    lines = [border]
    
    for key, value in str_items.items():
        line = f"| {key:<{max_key_len}} | {value:<{max_val_len}} |"
        lines.append(line)
        lines.append(border)
    
    # return "\n".join(lines)
    
    log_output = "\n" + "\n".join(lines) + "\n"
    logger.info(f"{message} \n {log_output}")

def safe_orjson_dumps(obj, pretty: bool = True, sort_keys: bool = False) -> str:
    """
    Safely serialize a Python object to JSON using orjson.
    Supports datetime, Decimal, UUID, and falls back to string for unknown types.
    
    Args:
        obj: The Python object to serialize (dict, list, etc.)
        pretty: If True, pretty-print with indentation.
        sort_keys: If True, sort keys in the output JSON.

    Returns:
        JSON string
    """
    
    def default(o):
        if isinstance(o, (datetime, Decimal, UUID)):
            return str(o)
        return str(o)  # fallback for other unsupported types

    options = 0
    if pretty:
        options |= orjson.OPT_INDENT_2
    if sort_keys:
        options |= orjson.OPT_SORT_KEYS

    try:
        return orjson.dumps(obj, default=default, option=options).decode('utf-8')
    except Exception as e:
        return f'{{"error": "Failed to serialize", "exception": "{str(e)}"}}'

def make_uuid(*ids):
    # join all ids into a single string
    s = ''.join(map(str, ids))
    # encode to bytes
    s_bytes = s.encode("utf-8")
    # base64 encode
    b64 = base64.urlsafe_b64encode(s_bytes)
    # convert back to string and replace padding
    return b64.decode("utf-8").replace('=', '_')

def truncate_values(data, max_len=50):
    """Recursively truncate long string values in dict/list"""
    if isinstance(data, dict):
        return {k: truncate_values(v, max_len) for k, v in data.items()}
    elif isinstance(data, list):
        return [truncate_values(v, max_len) for v in data]
    elif isinstance(data, str) and len(data) > max_len:
        return data[:max_len] + f"... (truncated, {len(data)} chars)"
    else:
        return data

def get_template_details(template_id):
    
    with get_pg_connector() as pg:
        template_details=pg.get("template","template_id",template_id)
        return template_details


CountyCodeDefaultMapper={
    "rml":"+91",
    "default":"91"
}

class AuthManager:
    def __init__(self, provider_name):
        self.provider_name = provider_name
        # self.auth_model = "whatsapp_auth_cred" #change it
        self.auth_model = "communication_credential" #change it
        

    def format_number(self, number: str, country_code: str = "91", add_plus: str = None):
        number = str(number)
        if len(number) <= 10:
            number = country_code + number
        if len(number) == 12 and add_plus:
            number = "+" + number
        return number

  
    def get_headers(self, channel_number: str, enterprise_id: str, complete_data=False) -> Dict[str, str]:
        """
        Retrieve authentication headers for a given channel number and enterprise ID.

        Logic:
        - Normalize channel number.
        - Try multiple number variants to increase hit rate.
        - Lookup order:
            1. Postgres: communication_credential.sender
            2. Fallback DB model (default_get_or_load_model)
        - Returns either auth_headers or full credential object based on `complete_data`.
        """
        logger.info("[AuthManager]::: GETTING CREDS")

        # if not enterprise_id:
        #     logger.warning("[HEADERS] Enterprise ID missing. Returning empty headers.")
        #     return {}

        start_time = time.time()

        channel_number = self.format_number(channel_number)
        logger.info(f"[HEADERS] Fetching headers for channel={channel_number}, enterprise={enterprise_id}")

        candidates = [channel_number]

        if len(channel_number) > 12:
            if channel_number.startswith("+91"):
                candidates.append(channel_number[3:])   
            elif channel_number.startswith("91"):
                candidates.append(channel_number[2:])  
        elif len(channel_number) == 10:
            candidates.append("91" + channel_number)    

        tried_numbers = set()

        for num in candidates:
            if num in tried_numbers:
                continue
            tried_numbers.add(num)

            try:
                t0 = time.time()
                
                with get_pg_connector() as pg:
                    creds = list(pg.list("communication_credential", {"sender": num}))
                    creds = creds[0]
                    if creds:
                        logger.info(
                            f"[HEADERS] Found credentials via PG for {num} and creds: {creds}"
                            f"| Time: {time.time() - t0:.3f}s"
                        )
                        return creds.get("auth_headers", {}) if not complete_data else creds

                # Fallback: DB model
                model = default_get_or_load_model(self.auth_model, enterprise_id)
                if model:
                    auth = model.get(num) or {}
                    if auth.get("auth_headers"):
                        logger.info(f"[HEADERS] Found credentials via DB model for {num}")
                        return auth.get("auth_headers", {}) if not complete_data else auth

            except Exception as e:
                logger.exception(f"[HEADERS] Error while checking number {num}: {e}")

        logger.warning(
            f"[HEADERS] No credentials found for {channel_number} "
            f"after {len(candidates)} attempts | Total time: {time.time() - start_time:.3f}s"
        )

        return {}

if __name__ == "__main__":
    # reset_rml_creds()
    
    # yield_gryd_task_results("createPerson",CONVERS_SERVICE_NAME,**{
    #         "mobile_number": "919113687241",
    #         "enterprise_id": "no_code_low_code"
    #     })
    pass



