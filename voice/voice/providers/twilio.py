#!/usr/bin/env python3
import os
import json
import base64
import asyncio
import logging
from dotenv import load_dotenv
from fastapi import WebSocket, WebSocketDisconnect, Request, HTTPException, APIRouter
from fastapi.responses import JSONResponse, Response
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
    raise Exception("Missing required Twilio environment variables")

# Initialize router and Twilio client
router = APIRouter()
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


class TwilioProvider:
    """Twilio provider for voice streaming"""

    def __init__(self, input_queue, output_queue):
        """
        Args:
            input_queue: Queue to put incoming audio/events
            output_queue: Queue to get outgoing audio
        """
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.active_streams = {}  # stream_sid -> session_id mapping

    async def handle_stream(self, websocket: WebSocket, session_id: str):
        """
        Handle Twilio media stream WebSocket connection

        Args:
            websocket: Twilio WebSocket connection
            session_id: Unique session identifier
        """
        await websocket.accept()
        logger.info(f"Twilio stream accepted for session: {session_id}")

        stream_sid = None

        try:
            # Task to receive from Twilio
            async def receive_from_twilio():
                nonlocal stream_sid
                while True:
                    try:
                        msg = await websocket.receive_json()
                        event = msg.get("event")

                        if event == "start":
                            stream_sid = msg["start"].get("streamSid")
                            self.active_streams[stream_sid] = session_id
                            logger.info(f"Stream started: {stream_sid}")

                            # Put start event in input queue
                            await self.input_queue.put({
                                "type": "stream_start",
                                "session_id": session_id,
                                "stream_sid": stream_sid,
                                "data": msg["start"]
                            })

                        elif event == "media":
                            # Get audio payload (base64 encoded �-law)
                            payload = msg.get("media", {}).get("payload")
                            if payload:
                                # Put audio in input queue
                                await self.input_queue.put({
                                    "type": "audio_input",
                                    "session_id": session_id,
                                    "stream_sid": stream_sid,
                                    "audio": payload,
                                    "encoding": "mulaw",
                                    "sample_rate": 8000
                                })

                        elif event == "stop":
                            logger.info(f"Stream stopped: {stream_sid}")
                            await self.input_queue.put({
                                "type": "stream_stop",
                                "session_id": session_id,
                                "stream_sid": stream_sid
                            })
                            break

                        elif event == "mark":
                            # Mark event for tracking
                            await self.input_queue.put({
                                "type": "mark",
                                "session_id": session_id,
                                "stream_sid": stream_sid,
                                "mark": msg.get("mark")
                            })

                    except WebSocketDisconnect:
                        logger.info(f"Twilio disconnected: {session_id}")
                        break
                    except Exception as e:
                        logger.error(f"Error receiving from Twilio: {e}")
                        break

            # Task to send to Twilio
            async def send_to_twilio():
                while True:
                    try:
                        # Get output from queue
                        output = await self.output_queue.get()

                        # Check if output is for this session
                        if output.get("session_id") != session_id:
                            continue

                        output_type = output.get("type")

                        if output_type == "audio_output":
                            # Send audio to Twilio
                            # Expecting base64 encoded �-law audio
                            if stream_sid and output.get("audio"):
                                await websocket.send_json({
                                    "event": "media",
                                    "streamSid": stream_sid,
                                    "media": {
                                        "payload": output["audio"]
                                    }
                                })

                        elif output_type == "clear":
                            # Clear Twilio buffer (for interruptions)
                            if stream_sid:
                                await websocket.send_json({
                                    "event": "clear",
                                    "streamSid": stream_sid
                                })

                        elif output_type == "mark":
                            # Send mark event
                            if stream_sid and output.get("mark"):
                                await websocket.send_json({
                                    "event": "mark",
                                    "streamSid": stream_sid,
                                    "mark": {
                                        "name": output["mark"]
                                    }
                                })

                        elif output_type == "stop":
                            # Stop the stream
                            logger.info(f"Stopping stream: {session_id}")
                            break

                    except Exception as e:
                        logger.error(f"Error sending to Twilio: {e}")
                        break

            # Run both tasks concurrently
            receive_task = asyncio.create_task(receive_from_twilio())
            send_task = asyncio.create_task(send_to_twilio())

            await asyncio.gather(receive_task, send_task, return_exceptions=True)

        except Exception as e:
            logger.error(f"Stream error for {session_id}: {e}")

        finally:
            # Cleanup
            if stream_sid and stream_sid in self.active_streams:
                del self.active_streams[stream_sid]

            await self.input_queue.put({
                "type": "stream_closed",
                "session_id": session_id,
                "stream_sid": stream_sid
            })

            try:
                await websocket.close()
            except:
                pass

            logger.info(f"Stream closed: {session_id}")



class Twilio():
    pass



@router.post("/outbound-call")
async def outbound_call(request: Request):
    """
    Initiate an outbound call via Twilio

    Expected JSON body:
    {
        "number": "+1234567890",
        "session_id": "unique_session_id",
        "callback_data": {}  # Optional data to pass to callbacks
    }
    """
    data = await request.json()
    number = data.get("number")
    session_id = data.get("session_id")

    if not number:
        raise HTTPException(status_code=400, detail="Phone number is required")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")

    try:
        # Create Twilio call
        call = twilio_client.calls.create(
            status_callback=f"https://{request.headers.get('host')}/twilio/status-callback",
            status_callback_event=[
                "initiated", "ringing", "answered", "completed",
                "busy", "no-answer", "canceled", "failed"
            ],
            status_callback_method="POST",
            from_=TWILIO_PHONE_NUMBER,
            to=number,
            url=f"https://{request.headers.get('host')}/twilio/twiml?session_id={session_id}"
        )

        return JSONResponse({
            "success": True,
            "call_sid": call.sid,
            "session_id": session_id
        })

    except TwilioRestException as e:
        logger.error(f"Twilio error: {e.msg} (code: {e.code})")
        raise HTTPException(status_code=500, detail=f"Twilio error: {e.msg}")


@router.api_route("/twiml", methods=["GET", "POST"])
async def get_twiml(request: Request):
    """
    Return TwiML to connect call to media stream
    """
    params = dict(request.query_params)
    session_id = params.get("session_id")

    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")

    host = request.headers.get('host')
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Connect>
                    <Stream url="wss://{host}/twilio/stream">
                        <Parameter name="session_id" value="{session_id}"/>
                    </Stream>
                </Connect>
            </Response>"""

    return Response(content=twiml, media_type="text/xml")


@router.websocket("/stream")
async def media_stream(websocket: WebSocket):
    """
    WebSocket endpoint for Twilio media stream
    """
    if provider is None:
        await websocket.close(code=1011, reason="Provider not initialized")
        return

    # Get session_id from query params or first message
    session_id = None

    # Accept connection first
    await websocket.accept()

    # # Wait for start message to get session_id
    # try:
    #     start_msg = await websocket.receive_json()
    #     if start_msg.get("event") == "start":
    #         custom_params = start_msg.get("start", {}).get("customParameters", {})
    #         session_id = custom_params.get("session_id")
    # except:
    #     await websocket.close()
    #     return

    # if not session_id:
    #     logger.error("No session_id found in stream")
    #     await websocket.close()
    #     return

    # # Put the start message back by handling it
    # await provider.input_queue.put({
    #     "type": "stream_start",
    #     "session_id": session_id,
    #     "stream_sid": start_msg["start"].get("streamSid"),
    #     "data": start_msg["start"]
    # })

    # # Handle the stream (but skip the start event since we already processed it)
    # await provider.handle_stream(websocket, session_id)


@router.post("/status-callback")
async def status_callback(request: Request):
    """
    Handle Twilio status callbacks

    Twilio sends call status updates here
    """
    form_data = await request.form()
    data = dict(form_data)

    logger.info(f"Status callback: {data}")

    if provider:
        # Put status update in input queue
        await provider.input_queue.put({
            "type": "call_status",
            "call_sid": data.get("CallSid"),
            "status": data.get("CallStatus"),
            "from": data.get("From"),
            "to": data.get("To"),
            "data": data
        })

    return Response(status_code=200)


# Helper functions for audio conversion
def mulaw_to_pcm16(mulaw_b64: str) -> str:
    """Convert base64 �-law to base64 PCM16"""
    import audioop
    mulaw_bytes = base64.b64decode(mulaw_b64)
    pcm_bytes = audioop.ulaw2lin(mulaw_bytes, 2)
    return base64.b64encode(pcm_bytes).decode('utf-8')


def pcm16_to_mulaw(pcm16_b64: str) -> str:
    """Convert base64 PCM16 to base64 �-law"""
    import audioop
    pcm_bytes = base64.b64decode(pcm16_b64)
    mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)
    return base64.b64encode(mulaw_bytes).decode('utf-8')



