from time import time
import os, sys

import pytz
# Add the autobot_agents root directory to path to find config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from .tatatele import CloudPhoneAPI, TATATELE_API_TOKEN, TATATELE_BASE_URL
import config
import json
import base64
import asyncio
import logging
import threading
from ai_service import ai_service
import aiohttp  # Async HTTP - much faster than requests
import websockets
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Blueprint
from elevenlabs import ElevenLabs
from typing import Dict, Any, Optional
import audioop  # Native C extension - fast audio processing
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp
from utils import helpers as vhp
import utils

# Use uvloop for faster event loop (Linux/macOS only)
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass  # uvloop not available, use default event loop

logger = utils.get_logger(__name__)

# ---- Config / env ----
load_dotenv()
API_KEY = os.environ.get("EXTERNAL_LLM_API_KEY", "sk_3f302b2e36acc353d040152b3d6c9bc7bf728955483bce75")
AGENT_ID = os.environ.get("DEFAULT_AGENT_ID", "agent_5701ka8618cbfxcbdp4wg6xb3x23")
TATATELE_PHONE_NUMBER = os.environ.get("TATATELE_PHONE_NUMBER", "918065251305")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "phnum_8201k1anbf9wet6v915q8arr1vmz")

# ---- Clients ----
tatatele_client = CloudPhoneAPI(TATATELE_API_TOKEN, TATATELE_BASE_URL)
elevenlabs_client = ElevenLabs(base_url="https://api.elevenlabs.io", api_key=API_KEY)
app = Blueprint("tatatelli", __name__)


# Session manager for concurrent calls
call_sessions: Dict[str, 'CallSession'] = {}
# Thread lock for session management (prevents race conditions)
session_lock = threading.Lock()


# ---------- CallSession Class ----------

def terminate_session(call_id: str):
    with session_lock:
        if call_id in call_sessions:
            session = call_sessions[call_id]
            session.stop_event.set()
            del call_sessions[call_id]
            logger.info(f"[{call_id}] Session terminated")
            return True
        logger.info(f"[{call_id}] Session not found ignoring...")
        return False

def terminate_sessions_for_phone(customer_number: str, agent_number: str, exclude_session_id: str = None):
    """Terminate any existing sessions for this phone number combination."""
    phone_key = f"{customer_number}_{agent_number}"
    sessions_to_terminate = []

    with session_lock:
        for session_id, session in list(call_sessions.items()):
            if session_id == exclude_session_id:
                continue
            session_phone_key = f"{session.session_data.get('phone_number', '')}_{session.session_data.get('agent_number', '')}"
            if session_phone_key == phone_key:
                sessions_to_terminate.append(session_id)

    # Terminate outside the lock to avoid deadlock (terminate_session also acquires lock)
    for session_id in sessions_to_terminate:
        logger.info(f"[{session_id}] Terminating old session for phone {phone_key}")
        terminate_session(session_id)

    return len(sessions_to_terminate)

class CallSession:
    """Manages state for a single call, enabling concurrent call support."""

    def __init__(self, call_id: str, ws=None):
        self.call_id = call_id
        self.bridge_started = False
        self.dave_ws: Optional[websockets.WebSocketClientProtocol] = ws
        self.stream_sid: Optional[str] = None
        self.media_buffer = []
        self.processed_agent_responses = set()
        self.processed_audio_events = set()
        self.stop_event = asyncio.Event()
        self.session_data = {}
        logger.info(f"[{self.call_id}] Session created")


    async def get_signed_url(self):
        """Fetch signed URL using async aiohttp - non-blocking."""
        logger.info(f"{self.session_data} Fetching signed URL for ElevenLabs connection")
        user_number = self.session_data.get("phone_number")
        agent_number = self.session_data.get("agent_number")
        
        agent_id = self.session_data.get("agent_id") or AGENT_ID
        if not agent_id or not API_KEY:
            raise RuntimeError("Missing AGENT_ID or API_KEY")
        url = f"https://api.elevenlabs.io/v1/convai/conversation/get-signed-url?agent_id={agent_id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"xi-api-key": API_KEY}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"[{self.call_id}] Failed to get signed url: %s %s", resp.status, text)
                    raise Exception(f"Failed to get signed URL: {resp.status} {text}")
                j = await resp.json()
                return j["signed_url"]

    @staticmethod
    def pcm16_16k_to_mulaw_8k_base64(b64_pcm16_16k):
        """Convert 16kHz PCM16 base64 → 8kHz μ-law base64 for telephony.
        Uses audioop only (C extension) - ~10x faster than pydub."""
        return b64_pcm16_16k
        try:
            raw_pcm16 = base64.b64decode(b64_pcm16_16k)
            # Downsample 16kHz → 8kHz using audioop (native C, very fast)
            pcm16_8k, _ = audioop.ratecv(raw_pcm16, 2, 1, 16000, 8000, None)
            # Convert linear PCM to μ-law
            mulaw = audioop.lin2ulaw(pcm16_8k, 2)
            return base64.b64encode(mulaw).decode("utf-8")
        except Exception as e:
            logger.error("Audio convert error (pcm→mulaw): %s", e)
            return None

    @staticmethod
    def mulaw_8k_to_pcm16_16k_base64(b64_mulaw_8k):
        """Convert 8kHz μ-law base64 → 16kHz PCM16 base64 for ElevenLabs.
        Uses audioop only (C extension) - ~10x faster than pydub."""
        try:
            mulaw_data = base64.b64decode(b64_mulaw_8k)
            # Convert μ-law to linear PCM (16-bit)
            pcm16_8k = audioop.ulaw2lin(mulaw_data, 2)
            # Upsample 8kHz → 16kHz
            pcm16_16k, _ = audioop.ratecv(pcm16_8k, 2, 1, 8000, 16000, None)
            return base64.b64encode(pcm16_16k).decode("utf-8")
        except Exception as e:
            logger.error("Audio convert error (mulaw→pcm): %s", e)
            return None


    @staticmethod
    def extract_audio_b64_from_dave(msg: dict) -> str | None:
        if not isinstance(msg, dict):
            return None
        for key in ("audio", "audio_event", "user_audio_chunk"):
            v = msg.get(key)
            if v and len(v) > 0:
                return v if isinstance(v, str) else v.get("audio_base_64") or v
        if msg.get("type") == "audio" and isinstance(msg.get("audio"), str):
            return msg.get("audio")
        return None

    @staticmethod
    def extract_media_payload_from_tatatele(tt_msg: dict) -> str | None:
        try:
            return tt_msg.get("media", {}).get("payload")
        except Exception:
            return None


    async def outbound_media_stream(self, wb):
        """Main media bridging logic for this call session."""
        logger.info(f"[{self.call_id}] Tatatele websocket accepted")

        # Counter for audio chunks sent to ElevenLabs
        chunks_sent_to_elevenlabs = [0]

        async def handle_tatatele_media_message(tt_msg: dict):
            payload_b64 = self.extract_media_payload_from_tatatele(tt_msg)
            if not payload_b64:
                return

            # Extract streamSid immediately from media event
            if not self.stream_sid:
                self.stream_sid = tt_msg.get("streamSid")
                logger.info(f"[{self.call_id}] *** EXTRACTED stream_sid from media: {self.stream_sid} ***")

            # Convert μ-law 8kHz → PCM16 16kHz for ElevenLabs
            converted_audio = payload_b64 #self.mulaw_8k_to_pcm16_16k_base64(payload_b64)
            if not converted_audio:
                logger.warning(f"[{self.call_id}] Audio conversion failed")
                return

            # Buffer if Dave not ready, send immediately if ready
            if self.dave_ws and not self.stop_event.is_set():
                try:
                    await self.dave_ws.send(json.dumps({"user_audio_chunk": converted_audio}))
                    chunks_sent_to_elevenlabs[0] += 1
                    if chunks_sent_to_elevenlabs[0] % 50 == 0:  # Log every 50 chunks
                        logger.info(f"[{self.call_id}] Sent {chunks_sent_to_elevenlabs[0]} audio chunks to ElevenLabs")
                except websockets.exceptions.ConnectionClosed:
                    logger.warning(f"[{self.call_id}] ElevenLabs connection closed, stopping sends (sent {chunks_sent_to_elevenlabs[0]} chunks)")
                    self.dave_ws = None
                    self.stop_event.set()
                except Exception as e:
                    logger.error(f"[{self.call_id}] Failed to send to ElevenLabs %s", e)
                    self.dave_ws = None
            elif not self.stop_event.is_set():
                self.media_buffer.append(converted_audio)
                logger.info(f"[{self.call_id}] BUFFERED media chunk (total={len(self.media_buffer)})")

        # Buffer for audio received before stream_sid is ready
        audio_out_buffer = []
        chunks_sent_to_tatatele = [0]
        audio_events_received = [0]

        async def send_audio_to_tatatele(audio_b64: str):
            """Convert and send audio to TataTele, or buffer if not ready."""
            converted_audio = self.pcm16_16k_to_mulaw_8k_base64(audio_b64)
            if not converted_audio:
                logger.warning(f"[{self.call_id}] Audio conversion to TataTele failed")
                return

            if self.stream_sid:
                # Flush any buffered audio first
                while audio_out_buffer:
                    buffered = audio_out_buffer.pop(0)
                    try:
                        msg_out = {
                            "event": "media",
                            "streamSid": self.stream_sid,
                            "media": {"payload": buffered}
                        }
                        await wb.send(json.dumps(msg_out))
                    except Exception as e:
                        logger.error(f"[{self.call_id}] Failed to flush buffered audio: %s", e)

                # Send current audio
                try:
                    msg_out = {
                        "event": "media",
                        "streamSid": self.stream_sid,
                        "media": {"payload": converted_audio}
                    }
                    await wb.send(json.dumps(msg_out))
                    chunks_sent_to_tatatele[0] += 1
                    if chunks_sent_to_tatatele[0] % 50 == 0:  # Log every 50 chunks
                        logger.info(f"[{self.call_id}] Sent {chunks_sent_to_tatatele[0]} audio chunks to TataTele")
                except Exception as e:
                    logger.error(f"[{self.call_id}] Failed to send to Tatatele: %s", e)
            else:
                # Buffer until stream_sid is available
                audio_out_buffer.append(converted_audio)
                logger.debug(f"[{self.call_id}] Buffered outgoing audio (total={len(audio_out_buffer)})")

        async def send_clear_to_tatatele():
            """Send clear event to stop any buffered audio on TataTele side."""
            if self.stream_sid:
                try:
                    clear_msg = {
                        "event": "clear",
                        "streamSid": self.stream_sid
                    }
                    await wb.send(json.dumps(clear_msg))
                    logger.info(f"[{self.call_id}] -> SENT clear TO Tatatele (interruption)")
                except Exception as e:
                    logger.error(f"[{self.call_id}] Failed to send clear: %s", e)
            # Also clear our outgoing buffer
            audio_out_buffer.clear()

        async def handle_dave_message(raw_msg):
            try:
                if isinstance(raw_msg, bytes):
                    raw_msg = raw_msg.decode("utf-8")
                msg_data = json.loads(raw_msg)
                msg_type = msg_data.get("type")
                # Log all messages except frequent ones
                if msg_type not in ("audio", "internal_tentative_agent_response", "vad"):
                    logger.info(f"[{self.call_id}] <- ElevenLabs: {msg_type}")
            except Exception as e:
                logger.error(f"[{self.call_id}] Failed to parse ElevenLabs message: %s", e)
                return

            msg_type = msg_data.get("type")

            # ===== AUDIO EVENT - Main audio from agent =====
            if msg_type == "audio":
                audio_events_received[0] += 1
                audio_event = msg_data.get("audio_event", {})
                audio_b64 = audio_event.get("audio_base_64")

                # Log first few audio events to debug format
                if audio_events_received[0] <= 3:
                    logger.info(f"[{self.call_id}] Audio event #{audio_events_received[0]}: msg_keys={list(msg_data.keys())}, audio_event_keys={list(audio_event.keys()) if audio_event else 'None'}, has_audio={bool(audio_b64)}, audio_len={len(audio_b64) if audio_b64 else 0}")

                if audio_b64:
                    await send_audio_to_tatatele(audio_b64)
                else:
                    # Try alternative field name - some API versions use "audio" directly
                    audio_b64 = msg_data.get("audio")
                    if audio_b64 and isinstance(audio_b64, str):
                        logger.info(f"[{self.call_id}] Found audio in 'audio' field")
                        await send_audio_to_tatatele(audio_b64)
                    else:
                        logger.warning(f"[{self.call_id}] Audio event has no audio data: {list(msg_data.keys())}")

            # ===== INTERRUPTION - User interrupted agent =====
            elif msg_type == "interruption":
                logger.info(f"[{self.call_id}] USER INTERRUPTED - clearing audio")
                await send_clear_to_tatatele()

            # ===== CONVERSATION INITIATION METADATA =====
            elif msg_type == "conversation_initiation_metadata":
                metadata = msg_data.get("conversation_initiation_metadata_event", {})
                conv_id = metadata.get("conversation_id")
                logger.info(f"[{self.call_id}] Conversation started: {conv_id}")

            # ===== USER TRANSCRIPT =====
            elif msg_type == "user_transcript":
                user_event = msg_data.get("user_transcription_event", {})
                transcript = user_event.get("user_transcript", "")
                is_final = user_event.get("is_final", False)
                if is_final and transcript:
                    logger.info(f"[{self.call_id}] User said: {transcript}")

            # ===== AGENT RESPONSE (text) =====
            elif msg_type == "agent_response":
                agent_event = msg_data.get("agent_response_event", {})
                response = agent_event.get("agent_response", "")
                if response:
                    logger.info(f"[{self.call_id}] Agent: {response}")

            # ===== AGENT RESPONSE CORRECTION =====
            elif msg_type == "agent_response_correction":
                correction_event = msg_data.get("agent_response_correction_event", {})
                original = correction_event.get("original_agent_response", "")
                corrected = correction_event.get("corrected_agent_response", "")
                logger.info(f"[{self.call_id}] Agent corrected: '{original}' -> '{corrected}'")

            # ===== PING - Keep alive =====
            elif msg_type == "ping":
                ping_event = msg_data.get("ping_event", {})
                event_id = ping_event.get("event_id")
                # Respond with pong
                try:
                    pong_msg = {"type": "pong", "event_id": event_id}
                    await self.dave_ws.send(json.dumps(pong_msg))
                except Exception as e:
                    logger.error(f"[{self.call_id}] Failed to send pong: %s", e)

            # ===== CLIENT TOOL CALL =====
            elif msg_type == "client_tool_call":
                tool_event = msg_data.get("client_tool_call", {})
                tool_name = tool_event.get("tool_name", "unknown")
                logger.info(f"[{self.call_id}] Tool call requested: {tool_name}")
                # TODO: Handle tool calls if needed

            # ===== VAD (Voice Activity Detection) =====
            elif msg_type == "vad":
                vad_event = msg_data.get("vad_event", {})
                vad_type = vad_event.get("type")  # "start" or "stop"
                logger.debug(f"[{self.call_id}] VAD: {vad_type}")

            # ===== INTERNAL TENTATIVE AGENT RESPONSE =====
            elif msg_type == "internal_tentative_agent_response":
                # Ignore tentative responses
                pass

            # ===== ERROR EVENT =====
            elif msg_type == "error":
                error_event = msg_data.get("error", {}) or msg_data
                error_code = error_event.get("code", "unknown")
                error_message = error_event.get("message", str(error_event))
                logger.error(f"[{self.call_id}] ElevenLabs ERROR: code={error_code}, message={error_message}")

            # ===== CONVERSATION END =====
            elif msg_type == "conversation_end":
                end_event = msg_data.get("conversation_end_event", {})
                reason = end_event.get("reason", "unknown")
                logger.info(f"[{self.call_id}] ElevenLabs conversation ended: {reason}")

            # ===== UNKNOWN EVENT =====
            else:
                logger.info(f"[{self.call_id}] Unknown ElevenLabs event: {msg_type} - {msg_data}")

        try:
            # CONNECT TO ELEVENLABS IMMEDIATELY
            signed_url = await self.get_signed_url()
            self.dave_ws = await websockets.connect(signed_url)
            logger.info(f"[{self.call_id}] *** CONNECTED TO ELEVENLABS IMMEDIATELY ***")

            #Send initial config to 11labs
            logger.info(f"Sending initial config to ElevenLabs {self.session_data}")
            config_data = {
                "type": "conversation_initiation_client_data",
                "dynamic_variables": self.session_data.get("dynamic_variables", {}),
                "user_id": self.session_data.get("session_id") or self.session_data.get("user_id")
            }

            if self.session_data.get("prompt"):
                config_data["conversation_config_override"] = {
                    "agent": {
                        "prompt": {"prompt":self.session_data.get("prompt", "")},
                        "first_message": self.session_data.get("first_message"),
                        "language": self.session_data.get("language", "en")
                    }
                }
                
            await self.dave_ws.send(json.dumps(config_data))

            # Send buffered media immediately - not sure why jay added?.
            for chunk in self.media_buffer:
                logger.info(f"[{self.call_id}] FLUSHING buffered chunk (len={len(chunk)})")
                try:
                    await self.dave_ws.send(json.dumps({"user_audio_chunk": chunk}))
                    logger.info(f"[{self.call_id}] -> FLUSHED buffered chunk")
                except Exception as e:
                    logger.warning(f"[{self.call_id}] Failed to flush buffered chunk: {e}")
            self.media_buffer.clear()

            # Start parallel readers
            async def tatatele_reader():
                while True:
                    try:
                        raw = await wb.recv()
                        tt_msg = json.loads(raw)
                        ev = tt_msg.get("event")

                        if ev == "media":
                            await handle_tatatele_media_message(tt_msg)
                        elif ev == "start":
                            logger.info(f"[{self.call_id}] START EVENT: {tt_msg}")
                            self.stream_sid = tt_msg.get("start", {}).get("streamSid", self.stream_sid)
                            logger.info(f"[{self.call_id}] *** GOT stream_sid: {self.stream_sid} ***")

                            # Flush any buffered outgoing audio now that we have stream_sid
                            while audio_out_buffer:
                                buffered = audio_out_buffer.pop(0)
                                try:
                                    msg_out = {
                                        "event": "media",
                                        "streamSid": self.stream_sid,
                                        "media": {"payload": buffered}
                                    }
                                    await wb.send(json.dumps(msg_out))
                                    logger.debug(f"[{self.call_id}] -> FLUSHED buffered outgoing audio")
                                except Exception as e:
                                    logger.error(f"[{self.call_id}] Failed to flush outgoing audio: %s", e)

                        elif ev == "stop":
                            logger.info(f"[{self.call_id}] Call ended by platform")
                            break

                        elif ev == "mark":
                            # Marks indicate playback position
                            mark_name = tt_msg.get("mark", {}).get("name")
                            logger.debug(f"[{self.call_id}] Mark: {mark_name}")

                    except asyncio.CancelledError:
                        logger.info(f"[{self.call_id}] Tatatele reader cancelled")
                        raise  # Re-raise to properly exit
                    except Exception as e:
                        logger.error(f"[{self.call_id}] Tatatele reader error: %s", e)
                        break

            async def dave_reader():
                try:
                    async for raw in self.dave_ws:
                        await handle_dave_message(raw)
                except websockets.exceptions.ConnectionClosed as e:
                    logger.error(f"[{self.call_id}] ElevenLabs WS closed: code={e.code}, reason={e.reason}")
                except Exception as e:
                    logger.error(f"[{self.call_id}] Dave reader error: %s", e)
                finally:
                    # Signal that ElevenLabs connection closed
                    self.stop_event.set()
                    logger.info(f"[{self.call_id}] ElevenLabs connection closed, signaling stop")

            # Run both readers - cancel the other when one exits
            tatatele_task = asyncio.create_task(tatatele_reader())
            dave_task = asyncio.create_task(dave_reader())

            done, pending = await asyncio.wait(
                [tatatele_task, dave_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            logger.info(f"[{self.call_id}] Both readers stopped")
            logger.info(f"[{self.call_id}] STATS: Sent {chunks_sent_to_elevenlabs[0]} chunks to ElevenLabs, received {audio_events_received[0]} audio events, sent {chunks_sent_to_tatatele[0]} chunks to TataTele")

        except Exception as e:
            logger.exception(f"[{self.call_id}] Main error: %s", e)
        finally:
            self.processed_agent_responses.clear()
            try:
                if self.dave_ws:
                    await self.dave_ws.close()
                    self.dave_ws = None
            except Exception as e:
                logger.warning(f"[{self.call_id}] Error closing ElevenLabs WebSocket: {e}")
            logger.info(f"[{self.call_id}] Bridge closed")

            # Cleanup session
            terminate_session(self.call_id)

    async def connect_external_websocket(self, url: str):
        """Connect to external websocket for this call session."""
        ws = None
        try:
            logger.info(f"[{self.call_id}] connecting to {url}")
            try:
                ws = await websockets.connect(url)
                logger.info(f"[{self.call_id}] connected to {url}")
                self.bridge_started = True
            except Exception as conn_error:
                logger.error(f"[{self.call_id}] Failed to establish WebSocket connection to {url}: {conn_error}")
                raise

            while not self.stop_event.is_set():
                try:
                    msg = await ws.recv()
                    logger.info(f"[{self.call_id}] received: {msg}")
                    await self.outbound_media_stream(ws)
                except Exception as e:
                    logger.error(f"[{self.call_id}] recv error: %s", e)
                    break
        except Exception as e:
            logger.exception(f"[{self.call_id}] connection failed: %s", e)
        finally:
            try:
                if ws:
                    await ws.close()
            except Exception as e:
                logger.warning(f"[{self.call_id}] Error closing external WebSocket: {e}")
            self.bridge_started = False
            logger.info(f"[{self.call_id}] external websocket closed")


# ---------- Helper functions ----------

def run_async_in_thread(coro):
    """Run an async coroutine in a background thread with its own event loop."""
    def thread_target():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()

    logger.info("Starting async task in background thread")
    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()


def calculate_elevenlabs_billing_usd(callback_data):
    # Safely extract nested data

    CREDIT_TIER_MAP = {
        "creator": 0.0003,  # dollar per credit
        "pro": 0.00024,
        "scale": 0.00018,
        "business": 0.00012
    }

    metadata = callback_data.get('metadata', {})
    charging = metadata.get('charging', {})
    llm_usage = charging.get('llm_usage', {})

    #  base charges
    call_charge = charging.get('call_charge', 0)
    llm_charge = charging.get('llm_charge', 0)
    llm_price = charging.get('llm_price', 0)

    #  free tier consumption
    free_minutes_consumed = charging.get('free_minutes_consumed', 0.0)
    free_llm_dollars_consumed = charging.get('free_llm_dollars_consumed', 0.0)

    #  total credits spent
    total_credits_spent = call_charge + llm_charge


    credit_to_usd_rate = CREDIT_TIER_MAP.get(charging.get('tier', 'creator'), 0.00024)

    # === CONVERT TO USD ===
    total_amount_usd = round(total_credits_spent * credit_to_usd_rate, 4)
    call_charge_usd = round(call_charge * credit_to_usd_rate, 4)
    llm_charge_usd = round(llm_charge * credit_to_usd_rate, 4)

    # Extract call details
    call_duration_secs = metadata.get('call_duration_secs', 0)
    call_duration_mins = round(call_duration_secs / 60, 2)

    # Calculate cost per minute/second
    cost_per_second_credits = round(call_charge / call_duration_secs, 4) if call_duration_secs > 0 else 0
    cost_per_minute_credits = round(cost_per_second_credits * 60, 2) if call_duration_secs > 0 else 0

    cost_per_second_usd = round(cost_per_second_credits * credit_to_usd_rate, 6)
    cost_per_minute_usd = round(cost_per_minute_credits * credit_to_usd_rate, 4)

    # Extract additional metadata
    status = callback_data.get('status', 'unknown')
    conversation_id = callback_data.get('conversation_id', 'N/A')
    agent_id = callback_data.get('agent_id', 'N/A')

    # Billing tier and discounts
    tier = charging.get('tier', 'unknown')
    dev_discount = charging.get('dev_discount', False)
    is_burst = charging.get('is_burst', False)

    # Call outcome
    analysis = callback_data.get('analysis', {})
    call_successful = analysis.get('call_successful', 'unknown')

    # Error information (if any)
    error = metadata.get('error', {})
    error_code = error.get('code', None)
    error_reason = error.get('reason', None)

    # RAG usage
    rag_usage = metadata.get('rag_usage', {})
    rag_usage_count = rag_usage.get('usage_count', 0)

    # Construct complete billing dictionary
    billing_breakdown = {
        # === TOTAL AMOUNT ===
        'total_credits_spent': total_credits_spent,
        'total_amount_usd': total_amount_usd,
        'currency': 'USD',
        'credit_to_usd_rate': credit_to_usd_rate,

        # === CREDIT & USD BREAKDOWN ===
        'charges': {
            'call_charge': {
                'credits': call_charge,
                'usd': call_charge_usd,
            },
            'llm_charge': {
                'credits': llm_charge,
                'usd': llm_charge_usd,
            },
            'llm_price': {
                'credits': llm_price,
                'usd': round(llm_price * credit_to_usd_rate, 4),
            },
        },

        # === CALL DETAILS ===
        'call_details': {
            'duration_seconds': call_duration_secs,
            'duration_minutes': call_duration_mins,
            'cost_per_second': {
                'credits': cost_per_second_credits,
                'usd': cost_per_second_usd,
            },
            'cost_per_minute': {
                'credits': cost_per_minute_credits,
                'usd': cost_per_minute_usd,
            },
        },

        # === FREE TIER USAGE ===
        'free_tier_consumed': {
            'free_minutes_consumed': free_minutes_consumed,
            'free_llm_dollars_consumed': free_llm_dollars_consumed,
        },

        # === IDENTIFIERS ===
        'identifiers': {
            'conversation_id': conversation_id,
            'agent_id': agent_id,
        },

        # === ACCOUNT INFO ===
        'account_info': {
            'tier': tier,
            'dev_discount_applied': dev_discount,
            'is_burst_call': is_burst,
        },

        # === CALL STATUS ===
        'call_status': {
            'status': status,
            'call_successful': call_successful,
            'error_code': error_code,
            'error_reason': error_reason,
        },

        # === USAGE STATS ===
        'usage_stats': {
            'rag_queries': rag_usage_count,
            'llm_usage': llm_usage,
        },

        # === TIMESTAMPS ===
        'timestamps': {
            'start_time_unix': metadata.get('start_time_unix_secs'),
            'accepted_time_unix': metadata.get('accepted_time_unix_secs'),
        },
    }

    return billing_breakdown

def make_call_tatatele(session_data, *args, **kwargs):

    logger.info(f"Making Tatatele call with session data: {session_data}")
    session_data = session_data or {}
    agent_number = session_data.get("agent_number", TATATELE_PHONE_NUMBER)
    caller_id = session_data.get("caller_id", TATATELE_PHONE_NUMBER)
    room_id = session_data.get("room_id", "default_room")
    session_id = session_data.get("session_id")
    customer_number = session_data.get("phone_number", "918850988794") #for test
    session_started = False

    # Terminate any old sessions for this phone number to prevent duplicates
    terminated = terminate_sessions_for_phone(customer_number, agent_number, exclude_session_id=session_id)
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
        external_wss = f"{config.AUTOCRM_WEBSOCKET_BASE_URL}/tatatele/{customer_number}/{agent_number}_{customer_number}"

        async def start_bridge():
            await session.connect_external_websocket(external_wss)

        run_async_in_thread(start_bridge())
        return True

    if session_id and not session_started:
        session_started = start_session(session_id)

    try:
        logger.info("Originate call to %s via tatatele", customer_number)
        response = tatatele_client.click_to_call_support(
            caller_id,
            customer_number,
            custom_id= session_id #custom_identifier
        )

        logger.info(f"Tatatele originate response: {response}")
        call_id = response.get('ref_id')
        if call_id and not session_started:
            logger.info(f"No session id provider starting session with call_id: {call_id}")
            start_session(call_id)

        if not session_started:
            response["error_message"] = f"Session was not started for call_id: {call_id}"
            response["success"] = False
            logger.error(f"Session was not started for call_id: {call_id}")

        return response
    except Exception as exc:
        logger.exception("Tatatele call initiation failed")
        return {"error": str(exc)}


# -----------------------------------------
# Tata Tele Payload Normalizer
# -----------------------------------------
def tatatele_status_map(payload: bytes) -> Dict[str, Any]:
    TATA_TELE_STATUS_MAP = {
        "failed": "error",
        "no-answer": "failed",
        "canceled": "failed",
        "missed": "failed",
        "busy": "failed",
        "queued": "queued",
        "initiated": "attempted",
        "ringing": "reached",
        "answered": "contacted",
        "in-progress": "contacted",
        "completed": "contacted",
        "Answered by customer": "contacted",
        "Answered by agent": "queued"

    }

    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("Payload must be bytes")

    try:
        json_str = payload.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("Invalid UTF-8 JSON payload")

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        raise ValueError("Payload is not valid JSON")

    if not isinstance(data, dict):
        raise ValueError("JSON must be a dict")

    raw_status = data.get("call_status") or data.get("status")
    if raw_status is None:
        raise KeyError("Missing 'call_status' field")

    mapped_status = TATA_TELE_STATUS_MAP.get(raw_status, raw_status)
    data["status"] = raw_status  # Preserve original
    data["call_status"] = mapped_status
    return data



# ---------- Flask endpoints ----------

@app.route("/")
def root():
    return jsonify({"message": "Server is running"})

@app.route('/tatatele/create-stream-url', methods=['POST'])
def create_stream_url(*args, **kwargs):
    data = request.get_json()
    base_ws_url = config.AUTOCRM_WEBSOCKET_BASE_URL

    from_number = data.get("from_number")[1:]
    to_number = data.get("to_number")[1:]
    wss_url = f"{base_ws_url}/tatatele/{from_number}_{to_number}/{to_number}"

    logger.info(f"Generated wss_url: {wss_url}")
    return jsonify({
        "sucess": True,
        "wss_url": wss_url
    })

@app.route("/tatatele-outbound-call", methods=["POST"])
def outbound_call(*args, **kwargs):
    logger.info("Received /outbound-call request headers: %s", dict(request.headers))
    data = request.get_json()
    number = data.get("phone_number")
    if not number:
        return jsonify({"error": "Phone number is required"}), 400
    response = make_call_tatatele(data)
    if  response.get("error"):
        logger.exception(f"Tatatele originate failed: {response}")
        return jsonify({"success": False, "message": "Call failed", "call_response": response}), 500
    return jsonify({"success": True, "message": "Call initiated", "call_response": response}), 200


@app.route("/smartflo/webhook", methods=["POST"])
def smartflo_webhook():
    from voice import gryd_tasks
    raw = request.get_data()
    payload = tatatele_status_map(raw)

    call_id = payload.get("call_id")
    if not call_id:
        logger.warning("Received webhook without call_id")
        return jsonify({"status": "error", "message": "Missing call_id"}), 400

    session_id = payload.get("custom_identifier") 
    status = payload.get("call_status")

    logger.info(f"[{call_id}] Incoming payload: {json.dumps(payload, indent=4)}")

    if  payload ["status"] in ["contacted"]:
        #start_session(call_id, {"room_id":"ambal_auto"})
        #patch the statuss
        #gryd_tasks.post_billing_object("contacted", session_id)
        pass
    elif payload ["status"] in ["queued"]:
        gryd_tasks.post_billing_object(status, session_id)
    elif status in ['failed', 'canceled', 'missed', 'busy', 'completed']:
        logger.info(f"[{call_id}] Call ended or failed - cleaning up session")

        # Cleanup session
        terminate_session(call_id)
        # Also try with session_id in case that was used as the key
        if session_id and session_id != call_id:
            terminate_session(session_id)

    return jsonify({"status": status})


@app.route("/tatatele-conversation", methods=["POST"])
def process():
    # secret - wsec_ca35c4c015f51dd09074893f1986484145df6c3e662311ce675f4892ffbf155e
    payload = request.get_json()

    logger.info(f"Processing payload: {json.dumps(payload, indent=4)}")

    if payload.get("full_audio"):
        return jsonify({"status": "ignored", "message": "Full audio payloads are ignored to save bandwidth"})

    data = payload.get("data", {})

    billing = calculate_elevenlabs_billing_usd(data)  # these will go to audit logs / billing system

    credits = billing.get("total_credits_spent", 0)
    amount_usd = billing.get("total_amount_usd", 0)
    currency = billing.get("currency", "USD")

    duration = float(billing.get("call_details", {}).get("duration_seconds", 0.0))
    logger.info(f"Calculated billing: {json.dumps(billing, indent=4)}")

    session_id = data.get("user_id", "2f7a2c16541d3348")

    # Import here to avoid circular import
    import gryd_tasks
    xx = gryd_tasks.post_billing_object("completed", session_id, duration)  # call it in async

    logger.info(f"Billing record created: {xx}")

    session_history = format_transcript(data.get("transcript", []), data.get("metadata", {}).get("start_time_unix_secs", time()))
    logger.info(f"Triggering post history and actions for session_id: {session_id}")
    
    gryd_tasks.end_session(**{
        "session_id": session_id,
        "history": session_history,
        "status": "completed"
    })
    
    gryd_tasks.post_actions(session_id)
    gryd_tasks.post_history(session_history, all_data = data)

    return jsonify({"status": "processed"})


def format_transcript(transcript, start_time_unix):
    from datetime import datetime
    session_history = []
    if not transcript:
        return []
    func = lambda x: datetime.fromtimestamp(start_time_unix+float(x), tz=pytz.timezone("UTC")).strftime("%Y-%m-%d %I:%M:%S %p %z")
    for msg in transcript:
        session_history.append({
            "role":msg.get('role'),
            "message":msg.get('message','').replace('.','') if msg.get('message') else '',
            "timestamp": func(msg.get('time_in_call_secs',0.0))
        })
    
    return session_history

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
