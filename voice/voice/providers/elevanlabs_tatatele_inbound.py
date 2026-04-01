from time import time
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

# Reuse the existing outbound bridge/session implementation.
from .elevanlabs_tatatele import (
    CallSession,
    call_sessions,
    session_lock,
    run_async_in_thread,
    terminate_sessions_for_phone,
)

logger = utils.get_logger(__name__)

app = Blueprint("tatatelli_inbound", __name__)


def start_inbound_session_tatatele(session_data: dict) -> dict:
    """
    Start a TataTele inbound call session bridge (no call origination).

    Minimum expected session_data fields:
    - from_number: inbound caller (customer)
    - to_number: inbound dialed number (agent/DID)
    """
    session_data = session_data or {}

    from_number = (session_data.get("from_number") or session_data.get("from") or "").strip()
    to_number = (session_data.get("to_number") or session_data.get("to") or "").strip()

    if from_number.startswith("+"):
        from_number = from_number[1:]
    if to_number.startswith("+"):
        to_number = to_number[1:]

    if not from_number or not to_number:
        return {"success": False, "error": "from_number and to_number are required"}

    customer_number = session_data.get("phone_number") or from_number
    agent_number = session_data.get("agent_number") or to_number

    if isinstance(customer_number, str) and customer_number.startswith("+"):
        customer_number = customer_number[1:]
    if isinstance(agent_number, str) and agent_number.startswith("+"):
        agent_number = agent_number[1:]

    session_id = session_data.get("session_id") or session_data.get("custom_identifier")
    if not session_id:
        session_id = str(hp.make_uuid3("tatatele_inbound", from_number, to_number, str(time())))
        session_data["session_id"] = session_id

    session_data["phone_number"] = customer_number
    session_data["agent_number"] = agent_number
    session_data["caller_id"] = agent_number

    terminated = terminate_sessions_for_phone(customer_number, agent_number, exclude_session_id=session_id)
    if terminated > 0:
        logger.info(f"Terminated {terminated} old session(s) for {customer_number}/{agent_number}")

    def start_session(call_id: str) -> bool:
        logger.info(f"[inbound] Starting session with call_id: {call_id}")
        with session_lock:
            if call_id in call_sessions:
                logger.info(f"[{call_id}] Session already exists, bridge likely running")
                return True

            session = CallSession(call_id)
            session.session_data = session_data
            call_sessions[call_id] = session

        logger.info(f"[{call_id}] Starting Connection to websocket bridge (inbound)")
        external_wss = f"{config.AUTOCRM_WEBSOCKET_BASE_URL}/tatatele/{customer_number}/{agent_number}_{customer_number}"

        async def start_bridge():
            await session.connect_external_websocket(external_wss)

        run_async_in_thread(start_bridge())
        return True

    started = start_session(session_id)

    base_ws_url = config.AUTOCRM_WEBSOCKET_BASE_URL
    wss_url = f"{base_ws_url}/tatatele/{customer_number}_{agent_number}/{agent_number}"

    return {
        "success": bool(started),
        "session_id": session_id,
        "from_number": from_number,
        "to_number": to_number,
        "phone_number": customer_number,
        "agent_number": agent_number,
        "wss_url": wss_url,
    }


@app.route("/tatatele-inbound-call", methods=["POST"])
def inbound_call(*args, **kwargs):
    logger.info("Received /tatatele-inbound-call request headers: %s", dict(request.headers))
    data = request.get_json(silent=True) or {}
    resp = start_inbound_session_tatatele(data)
    if not resp.get("success"):
        return jsonify(resp), 400
    return jsonify(resp), 200


@app.route("/tatatele/inbound/create-stream-url", methods=["POST"])
def inbound_create_stream_url(*args, **kwargs):
    """
    Helper endpoint that only builds the expected websocket URL.
    Useful if your TataTele inbound webhook needs just a stream URL.
    """
    data = request.get_json(silent=True) or {}
    from_number = (data.get("from_number") or "").strip()
    to_number = (data.get("to_number") or "").strip()
    if from_number.startswith("+"):
        from_number = from_number[1:]
    if to_number.startswith("+"):
        to_number = to_number[1:]
    if not from_number or not to_number:
        return jsonify({"success": False, "error": "from_number and to_number are required"}), 400

    base_ws_url = config.AUTOCRM_WEBSOCKET_BASE_URL
    wss_url = f"{base_ws_url}/tatatele/{from_number}_{to_number}/{to_number}"
    return jsonify({"success": True, "wss_url": wss_url}), 200

