from time import time
import json
import os
import sys
from typing import Any, Dict

_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from flask import Blueprint, request, jsonify

import config
from gryd_worker import gryd_helpers as hp
import utils

# Reuse session infrastructure and bridge from outbound implementation.
from .elevanlabs_tatatele import (
    CallSession,
    call_sessions,
    session_lock,
    run_async_in_thread,
    terminate_session,
    terminate_sessions_for_phone,
    calculate_elevenlabs_billing_usd,
    format_transcript,
)

#
logger = hp.get_logger(__name__)

app = Blueprint("tatatelli_inbound", __name__)



# ---------- Flask endpoints ----------

@app.route("/tatatele-inbound-call", methods=["POST"])
def inbound_call(*args, **kwargs):
    """
    SmartFlo calls this webhook when a customer dials in (Call received on Server event).
    Parses the payload using SmartFlo's actual field names, starts the bridge session,
    and returns the wss_url for SmartFlo to stream audio to.
    """
    logger.info("Received /tatatele-inbound-call headers: %s", dict(request.headers))
    raw = request.get_data()
    logger.info("Inbound call raw payload: %s", raw)
    return jsonify( {"error": "This endpoint is not implemented yet. Please use the outbound flow instead."}), 501
