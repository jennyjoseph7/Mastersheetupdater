from time import time
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
    
# ---------- Flask endpoints ----------

@app.route("/smartflo/webhook/inbound", methods=["POST"])
def inbound_call(*args, **kwargs):
    data = request.get_json()
    logger.info(f"Received inbound call data: {json.dumps(data, indent=4)}")

    if data.get("call_type", "").lower() in ["inbound"]:
        logger.info(f"Processing inbound call for {data.get('caller_id_number')}")

        list(gryd.create_async_task('start_call_from_inbound',config.AUTOCRM_VOICE_INBOUND_SERVICE_NAME , args=[], kwargs={"user_data":data}))
        
        return jsonify({"status": "success", "message": "Inbound call session created."})

    return jsonify({"status": "success", "message": "Inbound call received and processed.", "data": data})

@app.route("/tatatele/create-stream-url/inbound", methods=["POST"])
def create_stream_url(*args, **kwargs):
    t = time()
    data = request.get_json()

    logger.info(f"Processing create_stream_url request: {json.dumps(data, indent=4)}")
    
    from_number = data.get("from_number")[-10:]
    to_number = data.get("to_number")[-10:]

    base_ws_url = config.get_websocket_base_url(to_number)

    wss_url = f"{base_ws_url}/tatatele/{from_number}_{to_number}/{to_number}"

    logger.info(f"[webhook-/tatatele/create-stream-url/inbound] Generated wss_url took {time() - t:.2f} seconds: {wss_url}")
    return jsonify({
        "success": True,
        "wss_url": wss_url
    })


