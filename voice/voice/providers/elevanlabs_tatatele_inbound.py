import time
import json
import os
import sys
from typing import Any, Dict

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

import config
from communication.connectors.communication_helpers import handle_session_logic
from flask import Blueprint, request, jsonify
from gryd_worker import gryd_helpers as hp, gryd

from .tatatele import CloudPhoneAPI, TATATELE_API_TOKEN, TATATELE_BASE_URL

logger = hp.get_logger(__name__)

app = Blueprint("tatatelli_inbound", __name__)


def hangup_inbound_call(call_id):
    api = CloudPhoneAPI(TATATELE_API_TOKEN, TATATELE_BASE_URL)
    response = api.hangup_call(call_id)
    logger.info(f"Hangup call response: {response}")

def get_service_name(agent_number):
    try:
        from voice import gryd_tasks
    except ImportError as e:
        import gryd_tasks
    
    outbound_service_name = config.AUTOCRM_VOICE_SERVICE_NAME
    def _func(agent_number):  
        outbound_service_name = config.AUTOCRM_VOICE_SERVICE_NAME
        with gryd_tasks.get_pg_connector() as pg:
            cc = list(pg.list(
                "communication_credential",
                {
                    "sender": agent_number,
                    "channel": "voice_phone"
                }
            ))
            logger.info(f"Communication credentials found for {agent_number}: {cc}")
            if not cc:
                return None, None
            
            dealership_id = cc[0].get("dealership_id")
            dealer = pg.get("dealership", "dealership_id", dealership_id)
            if not dealer:
                logger.info(f"No dealer found for dealership_id {dealership_id}")
                return config.AUTOCRM_VOICE_INBOUND_SERVICE_NAME, outbound_service_name
            outbound_service_name = dealer.get('voice_service_name', outbound_service_name)
            service_name = f"{outbound_service_name}-inbound"
            return service_name, outbound_service_name
    sn = _func(agent_number)
    if agent_number.startswith("91") and not sn:
        logger.info(f"Agent number {agent_number} starts with country code, trying without it.")
        agent_number = agent_number[-10:]
        sn = _func(agent_number)

    sn = sn or (config.AUTOCRM_VOICE_INBOUND_SERVICE_NAME, outbound_service_name)
    logger.info(f"Service name for agent number {agent_number}: {sn}")

    return sn

def check_available_threads(service_name):
   c = gryd.get_service_connection()
   available_threads = c.execute_read("SELECT COUNT(*) FROM service_job WHERE dict->>'service' = %s AND dict->>'environment' = %s AND dict->>'current_task' IS NULL", params = (service_name, gryd.get_environment()))
   logger.info(f"Available threads for service {service_name}: {available_threads}")
   return True if available_threads and available_threads >= 1 else False

@app.route("/smartflo/webhook/inbound", methods=["POST"])
def inbound_call(*args, **kwargs):
    data = request.get_json(silent=True) or request.form.to_dict() or request.data.decode() or {}
    data = {
        key.strip():value for key, value in data.items()
    }
    logger.info(f"Received inbound call data: {json.dumps(data, indent=4)}")
  
    if data.get("call_type", "").lower() in ["inbound"]:
        import gryd_tasks
        caller_id = data.get("caller_id_number", "")
        if caller_id and not str(caller_id).startswith("91"):
            caller_id = "91" + str(caller_id)
        data["caller_id_number"] = caller_id
        logger.info(f"Processing inbound call for {data.get('caller_id_number')}")

        service_name, outbound_service_name = get_service_name(data.get("call_to_number", ""))
        if not check_available_threads(service_name):
            logger.warning(f"No available threads for service {service_name}. Hanging up the call.")
            hangup_inbound_call(data.get("call_id"))
            session_data = handle_session_logic(data.get('caller_id_number'), from_number=data.get("call_to_number", ""), channel = "voice_phone", engaged=True, origin="inbound")

            if session_data:
                with gryd_tasks.get_pg_connector() as pg:
                    pg.update("session", "session_id", session_data["session_id"], {"status": "busy", "disposition": "busy", "end_time": hp.epoch(), "session_live":False, "disposition_detail":"No available threads to handle the call. Call has been hung up."})
                session_data["mobile_number"] = session_data["phone_number"]
                session_data["from_inbound"] = True
                gryd.create_async_task("trigger_voice_call", outbound_service_name, args=[], kwargs={"user_data": session_data}, delay = 60)
                logger.info(f"Created async task to trigger outbound call for session {session_data.get('session_id')} after hanging up inbound call.")
            return jsonify({"status": "error", "message": "No available threads to handle the call. Call has been hung up."})
        
        gryd.create_async_task('start_call_from_inbound', service_name , args=[], kwargs={"user_data":data})
        return jsonify({"status": "success", "message": "Inbound call session created."})
    elif data.get("call_status") in ["answered"]:
        t = time.time()
        import gryd_tasks

        with gryd_tasks.get_pg_connector() as pg:
            filters = {
                "phone_number": data.get("customer_no_with_prefix") ,
                "channel": "voice_phone"
            }

            logger.info(f"Session filters: {filters}")
            sessions =  list[Any](
                    pg.list_order_by("session", 
                    filters,
                    order_by="created", order="DESC")
                )
            
            logger.info(f"Sessions found for inbound status 'contacted': {len(sessions)}")

            if not sessions:
                logger.info(f"No sessions found for inbound status 'contacted'")
                return jsonify({"status": "error", "message": "No session found for inbound status 'contacted'"})

            session = hp.make_single( sessions,  force = True)
            logger.info(f"Latest session found for inbound status 'contacted': {session}")
            pg.update("session",
                    "session_id",
                    session["session_id"], 
                    {
                        "call_recording": data.get("recording_url"), 
                        "duration": float(data.get("duration", 0.0))
                    }
            ) #add more attributes when needed
            


        logger.info(f"[webhook-/smartflo/webhook/inbound] Time taken to update session with recording URL and duration: {time.time() - t:.2f} seconds")
        gryd_tasks.post_contact_status_voice(session_id = session["session_id"], message_id = session["session_id"],  **{"status": "contacted"})
    
    elif data.get("call_status") in ["busy", "failed", "no-answer"]:
        t = time.time()
        import gryd_tasks
        with gryd_tasks.get_pg_connector() as pg:
            filters = {
                "phone_number": data.get("customer_no_with_prefix") ,
                "channel": "voice_phone"
            }

            logger.info(f"Session filters for call status {data.get('call_status')}: {filters}")
            sessions =  list[Any](
                    pg.list_order_by("session", 
                    filters,
                    order_by="created", order="DESC")
                )
            
            logger.info(f"Sessions found for call status {data.get('call_status')}: {len(sessions)}")

            if not sessions:
                logger.info(f"No sessions found for call status {data.get('call_status')}")
                return jsonify({"status": "error", "message": f"No session found for call status {data.get('call_status')}"})

            session = hp.make_single( sessions,  force = True)
            logger.info(f"Latest session found for call status {data.get('call_status')}: {session}")
        logger.info(f"[webhook-/smartflo/webhook/inbound] Time taken to find session for call status {data.get('call_status')}: {time.time() - t:.2f} seconds")
        gryd_tasks.post_contact_status_voice(session_id = session["session_id"], message_id = session["session_id"],  **{"status": data.get("call_status")})

    return jsonify({"status": "success", "message": "Inbound call received and processed.", "data": data})

@app.route("/tatatele/create-stream-url/inbound", methods=["POST"])
def create_stream_url(*args, **kwargs):
    t = time.time()
    data =  request.get_json(silent=True) or request.form.to_dict() or request.data.decode() or {}


    logger.info(f"Processing create_stream_url request: {json.dumps(data, indent=4)}")
    
    #inbound case swap
    to_number = data.get("from_number")[-10:]
    from_number = data.get("to_number")[-10:]
    
    base_ws_url = config.get_websocket_base_url(to_number)

    wss_url = f"{base_ws_url}/tatatele/{from_number}_{to_number}/{to_number}"

    logger.info(f"[webhook-/tatatele/create-stream-url/inbound] Generated wss_url took {time.time() - t:.2f} seconds: {wss_url}")
    return jsonify({
        "success": True,
        "wss_url": wss_url
    })



if __name__ == "__main__":
    sn = get_service_name("918065251317")
    check_available_threads(sn)