#!/usr/bin/env python3
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import os
import json
import base64
import asyncio
import logging
import traceback
from elevenlabs import ElevenLabs
import requests
import websockets
from dotenv import load_dotenv
from flask import Blueprint, request, jsonify, Response
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from pprint import pprint
from gryd_worker import gryd
import time
import utils

logger = utils.get_logger(__name__)



load_dotenv()
API_KEY = os.getenv("API_KEY") or os.environ.get("API_KEY")
AGENT_ID = os.getenv("AGENT_ID") or os.environ.get("AGENT_ID")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID") or os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN") or os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER") or os.environ.get("TWILIO_PHONE_NUMBER")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID") or os.environ.get("PHONE_NUMBER_ID", "phnum_8201k1anbf9wet6v915q8arr1vmz")

if not all([API_KEY, AGENT_ID, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, PHONE_NUMBER_ID]):
    raise Exception("Missing required environment variables: API_KEY, AGENT_ID, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, PHONE_NUMBER_ID")

app = Blueprint('twilio_routes', __name__)
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)



def twilio_call(number, session_id):
    try:
        call = twilio_client.calls.create(
            status_callback=f"https://{request.headers.get('host')}/twilio-callback-events",
            status_callback_event=[
                            "failed",
                            "no-answer",
                            "canceled",
                            "busy",
                            "queued",
                            "initiated",
                            "ringing",
                            "in-progress",
                            "completed"],
            from_=TWILIO_PHONE_NUMBER,
            to=number,
            url=f"https://{request.headers.get('host')}/outbound-call-twiml?session_id={session_id}"
        )
        return call
    except TwilioRestException as exc:
        logger.error(f"Twilio error: {exc.msg} (code: {exc.code})")           
        return


@app.route("/outbound-call", methods=["POST"])
def outbound_call():
    logger.info('Request headers: %s', dict(request.headers))
    data = request.get_json()
    number = data.get("number")
    if not number:
        return jsonify({"error": "Phone number is required"}), 400
    response = twilio_call(number, data.get("session_id", "test_session"))



    return jsonify({"success": True, "message": "Call initiated", "callSid": response.sid})


@app.route("/outbound-call-twiml", methods=["GET", "POST"])
def outbound_call_twiml():
    logger.info('Request headers: %s', dict(request.headers))

    params = request.args.to_dict()
    twiml_response = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
    <Response>
        <Connect>
            <Stream url=\"wss://autobot-messenger.gryd.in/ws?room_id=test_session\">
                <Parameter name="session_id" value="{params.get('session_id')}"></Parameter>
            </Stream>
        </Connect>
    </Response>"""
    return Response(twiml_response, mimetype="text/xml")


