from time import time
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
    terminate_sessions_for_phone
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
    
    credentials = session_data.get("communication_credentials", {})
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
    
    s = start_session(session_data.get('session_id'))

    yield {"status": "success", "message": "Inbound call session created.", "session_id": session_data.get('session_id')}
    