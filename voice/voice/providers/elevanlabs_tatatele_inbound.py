import time
import json
import os
import sys
from typing import Any, Dict

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

import config
from flask import Blueprint, request, jsonify
from gryd_worker import gryd_helpers as hp, gryd

logger = hp.get_logger(__name__)

app = Blueprint("tatatelli_inbound", __name__)

@app.route("/smartflo/webhook/inbound", methods=["POST"])
def inbound_call(*args, **kwargs):
    data = request.get_json(silent=True) or request.form.to_dict() or request.data.decode() or {}
    data = {
        key.strip():value for key, value in data.items()
    }
    logger.info(f"Received inbound call data: {json.dumps(data, indent=4)}")
  

    # Note: call connected for inbound billing is pending.
    if data.get("call_type", "").lower() in ["inbound"]:
        caller_id = data.get("caller_id_number", "")
        if caller_id and not str(caller_id).startswith("91"):
            caller_id = "91" + str(caller_id)
        data["caller_id_number"] = caller_id
        logger.info(f"Processing inbound call for {data.get('caller_id_number')}")

        gryd.create_async_task('start_call_from_inbound',config.AUTOCRM_VOICE_INBOUND_SERVICE_NAME , args=[], kwargs={"user_data":data})
        
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
            logger.info(f"Session found for inbound status 'contacted': {session}")
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

