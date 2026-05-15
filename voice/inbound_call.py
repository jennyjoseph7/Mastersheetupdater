import time
import json
import os
import sys
from typing import Any, Dict

_voice_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _voice_root not in sys.path:
    sys.path.insert(0, _voice_root)
from flask import Blueprint, request, jsonify
from gryd_worker import gryd_helpers as hp, gryd
import gryd_tasks
import config
from communication.connectors.communication_helpers import handle_session_logic

from voice.providers.elevanlabs_tatatele import (
    CallSession,
    call_sessions,
    session_lock,
    run_async_in_thread,
    terminate_sessions_for_phone,
    session_active
)

gryd.SERVICE = config.AUTOCRM_VOICE_INBOUND_SERVICE_NAME
gryd.set_queue_manager()


logger = hp.get_logger(__name__)

app = Blueprint("tatatelli_inbound", __name__)


@gryd.is_a_task(function_name="start_call_from_inbound")
def start_call_from_inbound(*args, **kwargs):
    data = kwargs.get("user_data", {})
    customer_number = data.get("caller_id_number")
    agent_number = data.get("call_to_number")
    logger.info(f"[start_call_from_inbound] customer={customer_number}, agent={agent_number}")

    session_data = handle_session_logic(customer_number, from_number=agent_number, channel = "voice_phone", engaged=True)
    logger.info(f"Session data after handling session logic: {session_data}")

    if "error" in session_data:
        logger.error(f"Error in session logic: {session_data['error']}")
        return session_data
    
    for x in gryd_tasks.converse.get_primary_prompt(*args, **{
            "session_id" : session_data['session_id'],
            "session_data" : session_data,
            "channel":"voice_phone"
        }):
            if x.get('prompt'):
                session_data["prompt"] = x.get('prompt')
                break
    
    credentials = {}
    with gryd_tasks.get_pg_connector() as pg:
        campaign_data = hp.make_single(list(pg.list(session_data.get("campaign_model"), {"campaign_id": session_data.get("campaign_id")})), force=True)
        logger.info(f"Campaign data retrieved in inbound call: {campaign_data.get('campaign_id')}, voice_agent_id: {campaign_data.get('voice_agent_id')}")
        credentials = hp.make_single(list(pg.list("communication_credential", {"dealership_id": session_data.get("dealership_id"), "channel": "voice_phone"})), force=True)
        credentials["bot_name"] = campaign_data.get("voice_agent_id") or credentials["bot_name"] if credentials else None
        logger.info(f"Provider credentials retrieved in inbound call: {credentials}")
    #NOTE: get agent id from campaign data

    
    if credentials:
        provider = credentials.get("provider_name", "tatatele").replace("-", "").strip().lower()
        session_data["agent_id"] = credentials.get("bot_name")
        session_data["language"] = "en"
        session_data["provider_credentials"] = {
            "tatatele_phone_number_api_key": credentials.get("auth_token")
        }
        session_data["provider"] = provider
        session_data["agent_number"] = credentials.get("sender") 
    else:
        logger.warning(f"No credentials found for dealership_id {session_data.get('dealership_id')}, channel voice_phone")  
        return {"status": "error", "message": "No provider credentials found for this dealership and channel."}



    terminated = terminate_sessions_for_phone(customer_number, agent_number, exclude_session_id=session_data["session_id"])
    if terminated > 0:
        logger.info(f"Terminated {terminated} old session(s) for {customer_number}/{agent_number}")


    def start_session(call_id):
        logger.info(f'Starting session with call_id: {call_id}')
        with session_lock:
            if call_id in call_sessions:
                logger.info(f"[{call_id}] Session already exists, bridge likely running")
                return True

            session = CallSession(call_id)
            # Ensure phone numbers are in session_data for tracking
            session.session_data = session_data
            call_sessions[call_id] = session

        logger.info(f"[{call_id}] Starting Connection to websocket bridge")
        external_wss = f"{config.get_websocket_base_url(customer_number[-10:])}/tatatele/{customer_number[-10:]}/{agent_number[-10:]}_{customer_number[-10:]}"

        async def start_bridge():
            await session.connect_external_websocket(external_wss)

        run_async_in_thread(start_bridge())
        #we have to check how to disconnect socket from elevanlabs -  
        return True
    
    yield {"status": "success", "message": "Inbound call session created.", "session_id": session_data.get('session_id')}

    s = start_session(session_data.get('session_id'))

    #updating session status, contact status to answered and posting billing for call connected.
    gryd_tasks.post_billing_object("reached", session_id = session_data["session_id"])
    with gryd_tasks.get_pg_connector() as pg:
        pg.update("session", "session_id", session_data.get('session_id'), {"status": "answered"})
    gryd_tasks.post_contact_status_voice(session_id = session_data['session_id'], message_id = session_data['session_id'],  **{"status": "answered"})
    
    timeout = time.time() + float(session_data.get("call_timeout", 600))  # 10 minutes
    while time.time() < timeout:
        time.sleep(5)
        logger.info(f"Inbound call is ongoing for {customer_number}, checking status...")
        with gryd_tasks.get_pg_connector() as pg:
            if not session_active(session_data["session_id"]):
                logger.info(f"Session not found or likely to be terminated already....")
                return {"status": "success", "message": f"Inbound call session ended."}
            
            contact_status = hp.make_single(list[Any](pg.list_order_by("contact_status", {"message_id": session_data["session_id"]}, order_by="created", order="DESC")), force = True)
            if (contact_status and contact_status.get("provider_status") in ["contacted"]):
                logger.info(f"Call ended with status {contact_status.get('provider_status')}, terminating session {session_data['session_id']}")
                return {"status": "success", "message": f"Inbound call session ended with status {contact_status.get('provider_status')}"}
            
    logger.info(f"Inbound call session {session_data['session_id']} timed out after {time.time() - (timeout - float(session_data.get('call_timeout', 600))):.2f} seconds, terminating session.")
    return {"status": "success", "message": "Inbound call session ended due to timeout."}



