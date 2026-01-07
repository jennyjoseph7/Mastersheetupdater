#!/usr/bin/env python3
import sys, os

from typing import Any, Dict
import typing
# Add the autobot_agents root directory to path to find config and other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from .provider_base import ProviderBase
import json
import base64
import audioop
import array
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
from threading import Thread

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
SERVER_URL = os.environ.get("SERVER_URL", 'https://ambal.loca.lt')
if SERVER_URL.endswith('/'):
    SERVER_URL = SERVER_URL[:-1]

app = Blueprint('twilio_routes', __name__)
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None


def make_call_twilio(session_data, *args, **kwargs):
    number = session_data.get("phone_number", "918850988794") #for test
    session_id = session_data.get('session_id')
    user_id = session_data.get('user_id')

    from ..core.voice_app import run_async_session
    thread = Thread(
        target=run_async_session,
        kwargs=session_data,
        daemon=True
    )
    thread.start()

    try:
        call = twilio_client.calls.create(
            status_callback=f"{SERVER_URL}/twilio-callback-events",
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
            url=f"{SERVER_URL}/outbound-call-twiml?session_id={session_id}"
        )
        logger.info(f"Twilio call initiated with SID: {call.sid}")
        return call.__dict__
    except TwilioRestException as exc:
        logger.error(f"Twilio error: {exc.msg} (code: {exc.code})")           
        return {
            "error": exc.msg
        }




@app.route("/outbound-call", methods=["POST"])
def outbound_call():
    logger.info('Request headers: %s', dict(request.headers))
    data = request.get_json()
    number = data.get("number")
    logger.info(f"Initiating outbound call to number: {number}")
    logger.info(f"Initiating data: {data}")

    if not number:
        return jsonify({"error": "Phone number is required"}), 400

    session_id = data.get("session_id", "test_session")

    #temp for now
    # Start the user session in a background thread
    # Import here to avoid circular import
    # from ..core.voice_app import run_async_session
    # thread = Thread(
    #     target=run_async_session,
    #     kwargs=data,
    #     daemon=True
    # )
    # thread.start()

    # Initiate the Twilio call
    response = make_call_twilio(data)
    return jsonify({"success": True, "message": "Call initiated", "callSid": response['sid']})


@app.route("/outbound-call-twiml", methods=["GET", "POST"])
def outbound_call_twiml():
    logger.info('Request headers: %s', dict(request.headers))

    params = request.args.to_dict()
    session_id = params.get('session_id')
    
    twiml_response = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
    <Response>
        <Connect>
            <Stream url=\"wss://autobot-messenger.gryd.in/ws/twilio/{session_id}/{session_id}_input_client\">
                <Parameter name="session_id" value="{session_id}"></Parameter>
            </Stream>
        </Connect>
    </Response>"""
    return Response(twiml_response, mimetype="text/xml")


class MessageHandler(ProviderBase):
    """Twilio-specific provider implementation"""

    def __init__(self):
        super().__init__("Twilio")
        self._resample_state = None
        
    def parse_incoming(self, raw_message: Dict[str, Any]) -> dict:
        """Convert Twilio message to generic format"""
        msg_type = raw_message.get('event')
        if msg_type == 'start':
            return dict(
                message_type='stream_start',
                metadata={
                    'stream_sid': raw_message.get('streamSid'),
                    'call_sid': raw_message.get('callSid'),
                    'media_format': raw_message.get('mediaFormat', {}),
                    'custom_params': raw_message.get("customParameters", {})
                }
            )
            #stream_start, audio_input - in
            #audio_output, clear_buffer - out
            
        elif msg_type == 'media':
            # Twilio sends mulaw, convert to PCM16 for generic format
            audio_mulaw = raw_message.get('media',{}).get('payload')
            audio_pcm16 = self._mulaw_to_pcm16(audio_mulaw) if audio_mulaw else None

            return dict(
                message_type='audio_input',
                audio_data=audio_pcm16,
                metadata={
                    'stream_sid': raw_message.get('streamSid')
                }
            )
        elif msg_type == 'stop':
            return dict(
                message_type='end_stream',
                metadata={
                    'stream_sid': raw_message.get('streamSid')
                }
            )
        else:
            # Unknown type, pass through
            return dict(
                message_type=msg_type or 'unknown',
                metadata=raw_message
            )

    def format_outgoing(self, generic_message: dict) -> Dict[str, Any]:
        """Convert generic format to Twilio message"""
        msg_type = generic_message.get('message_type')

        if msg_type == 'audio_output':
            # Convert PCM16 to mulaw for Twilio (with resampling to 8000 Hz)
            audio_data = generic_message.get('audio_data')
            if audio_data:
                # Get source sample rate from metadata, default to 24000 (OpenAI)
                source_rate = generic_message.get('metadata', {}).get('sample_rate', 24000)
                audio_mulaw = self._pcm16_to_mulaw(audio_data, source_sample_rate=source_rate)
            else:
                audio_mulaw = None

            return {
                'event': 'media',
                'streamSid': generic_message.get('metadata').get('stream_sid'),
                'media':{
                    'payload': audio_mulaw
                }
            }

        elif msg_type == 'clear_buffer':
            return {
                'event': 'clear',
                'streamSid': generic_message.get('metadata').get('stream_sid')
            }

        elif msg_type == 'mark':
            return {
                'event': 'mark',
                'mark': generic_message.get('metadata').get('mark', 'default'),
                'streamSid': generic_message.get('metadata').get('stream_sid')
            }

        elif msg_type == 'end_stream':
            return {
                'event': 'stop',
                'streamSid': generic_message.get('metadata').get('stream_sid')
            }

        else:
            # Default passthrough
            return {
                'event': msg_type,
                **generic_message.get('metadata')
            }

    def _mulaw_to_pcm16(self, mulaw_b64: str) -> typing.Union[str, bytes]:
        """Convert base64 mulaw to base64 PCM16 and amplify"""

        mulaw_bytes = base64.b64decode(mulaw_b64)
        pcm_bytes = audioop.ulaw2lin(mulaw_bytes, 2)
        
        return pcm_bytes
    
    def _pcm16_to_mulaw(self, pcm16_b64: typing.Union[str, bytes], source_sample_rate: int = 24000) -> str:
        """
        Convert PCM16 to mulaw for Twilio (8000 Hz required).

        Args:
            pcm16_b64: Base64 encoded PCM16 audio or raw bytes
            source_sample_rate: Sample rate of the input audio (default: 24000 for OpenAI)

        Returns:
            Base64 encoded mulaw audio at 8000 Hz
        """

        pcm_bytes = (base64.b64decode(pcm16_b64) if isinstance(pcm16_b64, str) else pcm16_b64)
        
        if source_sample_rate != 8000:
            pcm_bytes, self._resample_state = audioop.ratecv(
                pcm_bytes, # input data
                2, # sample width (16-bit = 2 bytes)
                1, # number of channels (mono)
                source_sample_rate, # input sample rate
                8000, # output sample rate (Twilio requirement)
                self._resample_state,
            )
            logger.debug(f"[Twilio] Resampled audio from {source_sample_rate}Hz to 8000Hz")

        # Convert to mulaw
        mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)
        return base64.b64encode(mulaw_bytes).decode('utf-8')


