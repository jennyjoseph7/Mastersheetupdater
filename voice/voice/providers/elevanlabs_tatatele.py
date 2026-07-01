from asyncio.subprocess import create_subprocess_shell
from time import time, monotonic
import os, sys
_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from .tatatele import CloudPhoneAPI, TATATELE_API_TOKEN, TATATELE_BASE_URL
import config
import json
try:
    import orjson
    _dumps = lambda obj: orjson.dumps(obj).decode("utf-8")  # text frame for websockets
    _loads = orjson.loads
except ImportError:
    _dumps = json.dumps
    _loads = json.loads
import base64
import asyncio
import logging
import threading
import aiohttp  # Async HTTP - much faster than requests
import websockets
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Blueprint
from elevenlabs import ElevenLabs
from typing import Dict, Any, Optional
import audioop  # Native C extension - fast audio processing
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp
import utils

# Use uvloop for faster event loop (Linux/macOS only)
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass  # uvloop not available, use default event loop

logger = hp.get_logger(__name__)

# Set ENABLE_BRIDGE_TIMING=1 to log monotonic latency milestones to the logger (TataTele ↔ ElevenLabs).
# Append one JSON object per call to this path (JSON Lines) for offline stats. Creates parent dirs on first write.
BRIDGE_TIMING_LOG_DIR = os.environ.get("BRIDGE_TIMING_LOG_DIR", "voice_logs").strip()
ENABLE_BRIDGE_TIMING_COLLECT = os.environ.get("ENABLE_BRIDGE_TIMING_COLLECT", True)
bridge_timing_log_lock = threading.Lock()


def _elapsed_ms(t0: float) -> float:
    return (monotonic() - t0) * 1000.0


def _append_bridge_timing_jsonl(record: Dict[str, Any], agent_number: str  = "dave", customer_number: str = "test") -> None:
    try:
        line = json.dumps(record, ensure_ascii=False) + "\n"
        if not os.path.isdir(BRIDGE_TIMING_LOG_DIR):
            os.makedirs(BRIDGE_TIMING_LOG_DIR, exist_ok=True)
        with bridge_timing_log_lock:
            log_path = os.path.join(BRIDGE_TIMING_LOG_DIR, f"voice_session_timing_{agent_number}_{customer_number}_{time()}.json")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception as e:
        logger.warning("BRIDGE_TIMING_LOG_DIR write failed: %s", e)


def _build_bridge_timing_record(
    call_id: str,
    session_data: Optional[dict],
    bt: dict,
    chunks_to_el: int,
    audio_events: int,
    chunks_to_tt: int,
    error: Optional[str],
) -> dict:
    session_data = session_data or {}

    def _delta(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None:
            return None
        return round(a - b, 3)

    cumulative_ms = {
        "signed_url": bt.get("signed_url_ms"),
        "el_ws_connect": bt.get("el_ws_connect_ms"),
        "config_sent": bt.get("config_sent_ms"),
        "first_tt_media_in": bt.get("first_tt_media_in_ms"),
        "first_chunk_to_el": bt.get("first_chunk_to_el_ms"),
        "first_el_audio": bt.get("first_el_audio_ms"),
        "first_tt_out": bt.get("first_tt_out_ms"),
    }
    derived_ms = {
        "first_user_to_first_agent_ms": _delta(bt.get("first_el_audio_ms"), bt.get("first_chunk_to_el_ms")),
        "config_to_first_tt_media_ms": _delta(bt.get("first_tt_media_in_ms"), bt.get("config_sent_ms")),
        "first_el_audio_to_first_tt_out_ms": _delta(bt.get("first_tt_out_ms"), bt.get("first_el_audio_ms")),
    }
    return {
        "schema": "bridge_timing_v1",
        "ts_unix": time(),
        "call_id": call_id,
        "session_id": session_data.get("session_id"),
        "phone_number": session_data.get("phone_number"),
        "agent_number": session_data.get("agent_number"),
        "signed_url_http_ms": bt.get("signed_url_http_ms"),
        "el_ws_handshake_ms": bt.get("el_ws_handshake_ms"),
        "conversation_init_step_ms": bt.get("conversation_init_step_ms"),
        "cumulative_ms": cumulative_ms,
        "first_el_audio_since_user_ms": bt.get("first_el_audio_since_user_ms"),
        "stats": {
            "chunks_to_elevenlabs": chunks_to_el,
            "audio_events_from_elevenlabs": audio_events,
            "chunks_to_tatatele": chunks_to_tt,
        },
        "derived_ms": derived_ms,
        "error": error,
    }


# ---- Config / env ----
load_dotenv()
API_KEY = os.environ.get("EXTERNAL_LLM_API_KEY", "sk_e232d2802c87154961d0fcdf71f5b418735282cc9a61a179")
AGENT_ID = os.environ.get("DEFAULT_AGENT_ID", "agent_4501kp8jfafdfj297zej22s890y8")
TATATELE_PHONE_NUMBER = os.environ.get("TATATELE_PHONE_NUMBER", "918065251305")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "phnum_8201k1anbf9wet6v915q8arr1vmz")

# ---- Clients ----
tatatele_client = CloudPhoneAPI(TATATELE_API_TOKEN, TATATELE_BASE_URL)
elevenlabs_client = ElevenLabs(base_url="https://api.elevenlabs.io", api_key=API_KEY)
app = Blueprint("tatatelli", __name__)


# Session manager for concurrent calls
call_sessions: Dict[str, 'CallSession'] = {}

# Thread lock for session management 
session_lock = threading.Lock()


# ---------- CallSession Class ----------

def session_active(call_id, return_session = False):
    with session_lock:
        if call_id  in call_sessions:
            if return_session:
                return call_sessions[call_id]
            return True
        return False

def _schedule_websocket_close(ws, bridge_loop: Optional[asyncio.AbstractEventLoop], call_id: str, socket_name: str,) -> None:
    if ws is None or getattr(ws, "closed", False):
        return
    if bridge_loop is None or not bridge_loop.is_running():
        logger.warning(
            f"[{call_id}] Cannot close {socket_name}: bridge loop missing or not running"
        )
        return

    async def _close() -> None:
        try:
            await ws.close()
            logger.info(f"[{call_id}] Closed {socket_name}")
        except Exception as e:
            logger.warning(f"[{call_id}] Error closing {socket_name}: {e}")

    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None

    if running is bridge_loop:
        bridge_loop.create_task(_close())
    else:
        try:
            fut = asyncio.run_coroutine_threadsafe(_close(), bridge_loop)
            fut.result(timeout=15.0)
        except Exception as e:
            logger.warning(
                f"[{call_id}] Thread-safe close failed for {socket_name}: {e}"
            )

            
def terminate_session(call_id: str):
    with session_lock:
        if call_id in call_sessions:
            session = call_sessions[call_id]
            # bridge_loop = getattr(session, "_bridge_loop", None)
            # for socket_name in ["dave_ws", "external_ws"]:
            #     logger.info(f"[{call_id}] Checking {socket_name} for termination")
            #     socket_obj = getattr(session, socket_name, None)
            #     if socket_obj and not getattr(socket_obj, "closed", False):
            #         _schedule_websocket_close(
            #             socket_obj, bridge_loop, call_id, socket_name
            #         )
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

    logger.info(f"Checking for existing sessions for phone {phone_key} to terminate (exclude_session_id={exclude_session_id})")

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
        self.dave_ws: Optional[websockets.WebSocketClientProtocol] = ws
        self._bridge_loop: Optional[asyncio.AbstractEventLoop] = None
        self.stream_sid: Optional[str] = None
        self.media_buffer = []
        self.processed_agent_responses = set()
        self.processed_audio_events = set()
        self.stop_event = asyncio.Event()
        self.session_data = {}
        self.call_sid = None
        logger.info(f"[{self.call_id}] Session created")


    async def hangup_tatatele_call(self):
        """Hang up the TataTele phone call via their REST API."""
        hangup_id =  self.call_sid 
        logger.info(f"[{self.call_id}] Attempting to hang up TataTele call with SID: {hangup_id}")
        if not hangup_id:
            logger.warning(f"[{self.call_id}] No call ID available for TataTele hangup, trying from session_data")
        elif self.session_data.get("call_sid"):
            hangup_id = self.session_data.get("call_sid")
            logger.info(f"[{self.call_id}] Using call_sid from session_data for hangup: {self.session_data.get('call_sid')}")
        if not hangup_id:
            logger.error(f"[{self.call_id}] No call ID available for TataTele hangup, aborting hangup")
            return
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, tatatele_client.hangup_call, hangup_id)
            logger.info(f"[{self.call_id}] TataTele hangup response: {result}")
        except Exception as e:
            logger.error(f"[{self.call_id}] Failed to hangup TataTele call: {e}")

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
                logger.info("elevellabs session url {}".format(j))
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

        bridge_timing = None
        if ENABLE_BRIDGE_TIMING_COLLECT:
            bridge_timing = {
                "t0": monotonic(),
                "signed_url_ms": None,
                "signed_url_http_ms": None,
                "el_ws_connect_ms": None,
                "el_ws_handshake_ms": None,
                "config_sent_ms": None,
                "conversation_init_step_ms": None,
                "first_tt_media_in_ms": None,
                "first_chunk_to_el_ms": None,
                "first_el_audio_ms": None,
                "first_el_audio_mono": None,
                "first_el_audio_since_user_ms": None,
                "first_tt_out_ms": None,
                "last_user_chunk_mono": None,
            }

        # Counter for audio chunks sent to ElevenLabs
        chunks_sent_to_elevenlabs = [0]

        async def handle_tatatele_media_message(tt_msg: dict):
            payload_b64 = self.extract_media_payload_from_tatatele(tt_msg)
            if not payload_b64:
                return

            if bridge_timing is not None and bridge_timing["first_tt_media_in_ms"] is None:
                bridge_timing["first_tt_media_in_ms"] = _elapsed_ms(bridge_timing["t0"])
                if ENABLE_BRIDGE_TIMING_COLLECT:
                    logger.info(
                        f"[{self.call_id}] [bridge_timing] first_tatatele_media_in "
                        f"elapsed_ms={bridge_timing['first_tt_media_in_ms']:.1f}"
                    )

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
                    if bridge_timing is not None:
                        bridge_timing["last_user_chunk_mono"] = monotonic()
                        if bridge_timing["first_chunk_to_el_ms"] is None:
                            bridge_timing["first_chunk_to_el_ms"] = _elapsed_ms(bridge_timing["t0"])
                            if ENABLE_BRIDGE_TIMING_COLLECT:
                                logger.info(
                                    f"[{self.call_id}] [bridge_timing] first_user_chunk_to_elevenlabs "
                                    f"elapsed_ms={bridge_timing['first_chunk_to_el_ms']:.1f}"
                                )
                    await self.dave_ws.send(_dumps({"user_audio_chunk": converted_audio}))
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
                        t_send = monotonic()
                        await wb.send(_dumps(msg_out))
                        if bridge_timing is not None and bridge_timing["first_tt_out_ms"] is None:
                            bridge_timing["first_tt_out_ms"] = _elapsed_ms(bridge_timing["t0"])
                            extra = ""
                            if bridge_timing.get("first_el_audio_mono") is not None:
                                el_to_wire_ms = (t_send - bridge_timing["first_el_audio_mono"]) * 1000.0
                                extra = f" el_audio_recv_to_tatatele_send_ms={el_to_wire_ms:.1f}"
                            if ENABLE_BRIDGE_TIMING_COLLECT:
                                logger.info(
                                    f"[{self.call_id}] [bridge_timing] first_chunk_to_tatatele (flush) "
                                    f"elapsed_ms={bridge_timing['first_tt_out_ms']:.1f}{extra}"
                                )
                    except Exception as e:
                        logger.error(f"[{self.call_id}] Failed to flush buffered audio: %s", e)

                # Send current audio
                try:
                    msg_out = {
                        "event": "media",
                        "streamSid": self.stream_sid,
                        "media": {"payload": converted_audio}
                    }
                    t_send = monotonic()
                    await wb.send(_dumps(msg_out))
                    if bridge_timing is not None and bridge_timing["first_tt_out_ms"] is None:
                        bridge_timing["first_tt_out_ms"] = _elapsed_ms(bridge_timing["t0"])
                        extra = ""
                        if bridge_timing.get("first_el_audio_mono") is not None:
                            el_to_wire_ms = (t_send - bridge_timing["first_el_audio_mono"]) * 1000.0
                            extra = f" el_audio_recv_to_tatatele_send_ms={el_to_wire_ms:.1f}"
                        if ENABLE_BRIDGE_TIMING_COLLECT:
                            logger.info(
                                f"[{self.call_id}] [bridge_timing] first_chunk_to_tatatele "
                                f"elapsed_ms={bridge_timing['first_tt_out_ms']:.1f}{extra}"
                            )
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
                    await wb.send(_dumps(clear_msg))
                    logger.info(f"[{self.call_id}] -> SENT clear TO Tatatele (interruption)")
                except Exception as e:
                    logger.error(f"[{self.call_id}] Failed to send clear: %s", e)
            # Also clear our outgoing buffer
            audio_out_buffer.clear()

        async def handle_dave_message(raw_msg):
            try:
                msg_data = _loads(raw_msg)
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

                if bridge_timing is not None and audio_b64 and bridge_timing["first_el_audio_ms"] is None:
                    now_m = monotonic()
                    bridge_timing["first_el_audio_ms"] = _elapsed_ms(bridge_timing["t0"])
                    bridge_timing["first_el_audio_mono"] = now_m
                    since_user = None
                    if bridge_timing.get("last_user_chunk_mono") is not None:
                        since_user = (now_m - bridge_timing["last_user_chunk_mono"]) * 1000.0
                        bridge_timing["first_el_audio_since_user_ms"] = since_user
                    if ENABLE_BRIDGE_TIMING_COLLECT:
                        logger.info(
                            f"[{self.call_id}] [bridge_timing] first_agent_audio_from_elevenlabs "
                            f"elapsed_ms={bridge_timing['first_el_audio_ms']:.1f}"
                            + (
                                f" since_last_user_chunk_sent_ms={since_user:.1f}"
                                if since_user is not None
                                else " since_last_user_chunk_sent_ms=n/a"
                            )
                        )

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

            #  INTERRUPTION - User interrupted agent - Importat
            elif msg_type == "interruption":
                logger.info(f"[{self.call_id}] USER INTERRUPTED - clearing audio")
                await send_clear_to_tatatele()

            # CONVERSATION INITIATION METADATA 
            elif msg_type == "conversation_initiation_metadata":
                metadata = msg_data.get("conversation_initiation_metadata_event", {})
                conv_id = metadata.get("conversation_id")
                logger.info(f"[{self.call_id}] Conversation started: {conv_id}")

            #  USER TRANSCRIPT 
            elif msg_type == "user_transcript":
                user_event = msg_data.get("user_transcription_event", {})
                transcript = user_event.get("user_transcript", "")
                is_final = user_event.get("is_final", False)
                if is_final and transcript:
                    logger.info(f"[{self.call_id}] User said: {transcript}")

            # AGENT RESPONSE (text) 
            elif msg_type == "agent_response":
                agent_event = msg_data.get("agent_response_event", {})
                response = agent_event.get("agent_response", "")
                if response:
                    logger.info(f"[{self.call_id}] Agent: {response}")

            #  AGENT RESPONSE CORRECTION 
            elif msg_type == "agent_response_correction":
                correction_event = msg_data.get("agent_response_correction_event", {})
                original = correction_event.get("original_agent_response", "")
                corrected = correction_event.get("corrected_agent_response", "")
                logger.info(f"[{self.call_id}] Agent corrected: '{original}' -> '{corrected}'")

            # ===== PING - Keep alive =====
            elif msg_type == "ping":
                ping_event = msg_data.get("ping_event", {})
                event_id = ping_event.get("event_id")
                if self.stop_event.is_set():
                    logger.info(f"[{self.call_id}] Ping received after stop_event; skipping pong")
                    return
                if self.dave_ws is None or getattr(self.dave_ws, "closed", False):
                    logger.info(f"[{self.call_id}] Ping received but ElevenLabs WS is closed; skipping pong")
                    return
                # Respond with pong (only while the call is active).
                try:
                    await self.dave_ws.send(_dumps({"type": "pong", "event_id": event_id}))
                except Exception as e:
                    logger.error(f"[{self.call_id}] Failed to send pong: %s", e)

            #  CLIENT TOOL CALL 
            elif msg_type == "agent_tool_request":
                tool_request_event = msg_data.get("agent_tool_request", {})
                logger.info(f"too_request_event {msg_data}")

            elif msg_type == "agent_tool_response":
                #user agent monitoring for context update
                tool_event = msg_data.get("agent_tool_response", {})
                tool_name = tool_event.get("tool_name", "unknown")
                logger.info(f"[{self.call_id}] Tool call requested: {tool_name}")
                # Handle end-call tool calls from ElevenLabs agent
                if tool_name in ("end_call", "hang_up", "hangup", "end_conversation", "disconnect"):
                    logger.info(f"[{self.call_id}] Agent requested call end via tool: {tool_name} - triggering hangup")
                    self.stop_event.set() 
                    return

            #  VAD (Voice Activity Detection) 
            elif msg_type == "vad_score":
                vad_event = msg_data.get("vad_score", {})
                vad_type = vad_event.get("type")  # "start" or "stop"
                logger.debug(f"[{self.call_id}] VAD: {vad_type}")

            #  INTERNAL TENTATIVE AGENT RESPONSE 
            elif msg_type == "internal_tentative_agent_response":
                # Ignore tentative responses
                pass

            #  ERROR EVENT 
            elif msg_type == "error":
                error_event = msg_data.get("error", {}) or msg_data
                error_code = error_event.get("code", "unknown")
                error_message = error_event.get("message", str(error_event))
                logger.error(f"[{self.call_id}] ElevenLabs ERROR: code={error_code}, message={error_message} - triggering call hangup")
                self.stop_event.set()
                return

            #  CONVERSATION END 
            elif msg_type == "conversation_end":
                end_event = msg_data.get("conversation_end_event", {})
                reason = end_event.get("reason", "unknown")
                logger.info(f"[{self.call_id}] ElevenLabs conversation ended: {reason} - triggering call hangup")
                self.stop_event.set()
                return

            #  UNKNOWN EVENT 
            else:
                logger.info(f"[{self.call_id}] Unknown ElevenLabs event: {msg_type} - {msg_data}")

        bridge_error = None
        try:
            # CONNECT TO ELEVENLABS IMMEDIATELY
            t_http = monotonic()
            signed_url = await self.get_signed_url()
            if bridge_timing is not None:
                bridge_timing["signed_url_ms"] = _elapsed_ms(bridge_timing["t0"])
                bridge_timing["signed_url_http_ms"] = _elapsed_ms(t_http)
                if ENABLE_BRIDGE_TIMING_COLLECT:
                    logger.info(
                        f"[{self.call_id}] [bridge_timing] get_signed_url_http_ms={bridge_timing['signed_url_http_ms']:.1f} "
                        f"cumulative_ms={bridge_timing['signed_url_ms']:.1f}"
                    )
            t_ws = monotonic()
            self.dave_ws = await websockets.connect(signed_url)
            if bridge_timing is not None:
                bridge_timing["el_ws_connect_ms"] = _elapsed_ms(bridge_timing["t0"])
                bridge_timing["el_ws_handshake_ms"] = _elapsed_ms(t_ws)
                if ENABLE_BRIDGE_TIMING_COLLECT:
                    logger.info(
                        f"[{self.call_id}] [bridge_timing] elevenlabs_ws_handshake_ms={bridge_timing['el_ws_handshake_ms']:.1f} "
                        f"cumulative_ms={bridge_timing['el_ws_connect_ms']:.1f}"
                    )
            logger.info(f"[{self.call_id}] *** CONNECTED TO ELEVENLABS IMMEDIATELY ***")

            #Send initial config to 11labs
            logger.info(f"Sending initial config to ElevenLabs {self.session_data}")
            config_data = {
                "type": "conversation_initiation_client_data",
                "dynamic_variables": self.session_data.get("dynamic_variables", {}),
                "user_id": self.session_data.get("session_id") or self.session_data.get("user_id")
            }

            # Set language presets
            config_data["conversation_config"] = {
                "language_presets": {
                    "en": {
                        "overrides": {
                            "agent": {
                                "first_message": "Hello, how can I help?",
                                "language": "en"
                            }
                        }
                    },
                    "hi": {
                        "overrides": {
                            "agent": {
                                "first_message": "",
                                "language": "hi"
                            }
                        }
                    }
                }
            }

            if self.session_data.get("prompt"):
                config_data["conversation_config_override"] = {
                    "agent": {
                        "prompt": {"prompt":self.session_data.get("prompt", "")},
                        "first_message": self.session_data.get("voice_first_message"),
                        "language": self.session_data.get("language", "en")
                    }
                }
                
                
            t_cfg = monotonic()
            await self.dave_ws.send(_dumps(config_data))
            if bridge_timing is not None:
                bridge_timing["config_sent_ms"] = _elapsed_ms(bridge_timing["t0"])
                bridge_timing["conversation_init_step_ms"] = _elapsed_ms(t_cfg)
                if ENABLE_BRIDGE_TIMING_COLLECT:
                    logger.info(
                        f"[{self.call_id}] [bridge_timing] conversation_init_send_ms={bridge_timing['conversation_init_step_ms']:.1f} "
                        f"cumulative_ms={bridge_timing['config_sent_ms']:.1f}"
                    )

            # Send buffered media immediately - not sure why jay added?.
            for chunk in self.media_buffer:
                logger.info(f"[{self.call_id}] FLUSHING buffered chunk (len={len(chunk)})")
                try:
                    await self.dave_ws.send(_dumps({"user_audio_chunk": chunk}))
                    logger.info(f"[{self.call_id}] -> FLUSHED buffered chunk")
                except Exception as e:
                    logger.warning(f"[{self.call_id}] Failed to flush buffered chunk: {e}")
            self.media_buffer.clear()

            # Start parallel readers
            async def tatatele_reader(timeout = 60):
                logger.info(f"[{self.call_id}] TataTele reader started")
                while not self.stop_event.is_set():
                    try:
                        message = await asyncio.wait_for(wb.recv(), timeout=timeout)
                        tt_msg = _loads(message)
                        ev = tt_msg.get("event")

                        if ev == "media":
                            await handle_tatatele_media_message(tt_msg)
                        elif ev == "start":
                            logger.info(f"[{self.call_id}] START EVENT: {tt_msg}")
                            self.stream_sid = tt_msg.get("start", {}).get("streamSid", self.stream_sid)
                            self.call_sid = tt_msg.get("start", {}).get("callSid") #use in hangup call for tatatele
                            # Flush any buffered outgoing audio now that we have stream _sid
                            while audio_out_buffer:
                                buffered = audio_out_buffer.pop(0)
                                try:
                                    msg_out = {
                                        "event": "media",
                                        "streamSid": self.stream_sid,
                                        "media": {"payload": buffered}
                                    }
                                    t_send = monotonic()
                                    await wb.send(_dumps(msg_out))
                                    if bridge_timing is not None and bridge_timing["first_tt_out_ms"] is None:
                                        bridge_timing["first_tt_out_ms"] = _elapsed_ms(bridge_timing["t0"])
                                        extra = ""
                                        if bridge_timing.get("first_el_audio_mono") is not None:
                                            el_to_wire_ms = (t_send - bridge_timing["first_el_audio_mono"]) * 1000.0
                                            extra = f" el_audio_recv_to_tatatele_send_ms={el_to_wire_ms:.1f}"
                                        if ENABLE_BRIDGE_TIMING_COLLECT:
                                            logger.info(
                                                f"[{self.call_id}] [bridge_timing] first_chunk_to_tatatele (start_flush) "
                                                f"elapsed_ms={bridge_timing['first_tt_out_ms']:.1f}{extra}"
                                            )
                                    logger.debug(f"[{self.call_id}] -> FLUSHED buffered outgoing audio")
                                except Exception as e:
                                    logger.error(f"[{self.call_id}] Failed to flush outgoing audio: %s", e)

                        elif ev == "stop":
                            logger.info(f"[{self.call_id}] Call ended by platform")
                            self.stop_event.set()
                            try:
                                if self.dave_ws is not None and not getattr(self.dave_ws, "closed", False):
                                    await self.dave_ws.close()
                                    logger.info(f"[{self.call_id}] Closed ElevenLabs WS on TataTele stop")
                            except Exception as e:
                                logger.warning(f"[{self.call_id}] Failed to close ElevenLabs WS on stop: %s", e)
                            break

                        elif ev == "mark":
                            # Marks indicate playback position
                            mark_name = tt_msg.get("mark", {}).get("name")
                            logger.debug(f"[{self.call_id}] Mark: {mark_name}")
                    except (asyncio.TimeoutError, TimeoutError):
                        logger.error(f"[{self.call_id}] Taatele reader timed out waiting for message")
                        self.stop_event.set()
                        break
                    except asyncio.CancelledError:
                        logger.info(f"[{self.call_id}] Tatatele reader cancelled")
                        self.stop_event.set()
                        break
                    except Exception as e:
                        logger.info(f"[{self.call_id}] Tatatele reader error: %s", e)
                        self.stop_event.set()
                        break


            async def dave_reader(timeout=60):
                logger.info(f"[{self.call_id}] ElevenLabs reader started")
                while not self.stop_event.is_set():
                    try:
                        message = await asyncio.wait_for(self.dave_ws.recv(), timeout=timeout)
                        await handle_dave_message(message)
                    except (asyncio.TimeoutError, TimeoutError):
                        logger.error(f"[{self.call_id}] Dave reader timed out waiting for message")
                        self.stop_event.set()
                        break
                    except websockets.exceptions.ConnectionClosed as e:
                        logger.error(f"[{self.call_id}] ElevenLabs WS closed: code={e.code}, reason={e.reason}")
                        self.stop_event.set()
                        break
                    except Exception as e:
                        logger.error(f"[{self.call_id}] Dave reader error: %s", e)
                        self.stop_event.set()
                        break
                  
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
            if bridge_timing is not None:
                bt = bridge_timing
                logger.info(
                    f"[{self.call_id}] [bridge_timing] session_summary_ms "
                    f"signed_url={bt.get('signed_url_ms')} "
                    f"el_ws={bt.get('el_ws_connect_ms')} "
                    f"config_sent={bt.get('config_sent_ms')} "
                    f"first_tt_in={bt.get('first_tt_media_in_ms')} "
                    f"first_to_el={bt.get('first_chunk_to_el_ms')} "
                    f"first_el_audio={bt.get('first_el_audio_ms')} "
                    f"first_tt_out={bt.get('first_tt_out_ms')}"
                )

        except Exception as e:
            bridge_error = repr(e)
            logger.exception(f"[{self.call_id}] Main error: %s", e)
        finally:
            self.processed_agent_responses.clear()
            # Hang up the TataTele phone call so the user isn't left on a dead line
            await self.hangup_tatatele_call()

            logger.info(f"[{self.call_id}] Bridge closed")
            
            if bridge_timing is not None :
                _append_bridge_timing_jsonl(
                    _build_bridge_timing_record(
                        self.call_id,
                        self.session_data,
                        bridge_timing,
                        chunks_sent_to_elevenlabs[0],
                        audio_events_received[0],
                        chunks_sent_to_tatatele[0], 
                        bridge_error,
                    ),
                    agent_number=self.session_data.get("agent_number"),
                    customer_number=self.session_data.get("phone_number")
                )

            # Cleanup session
            terminate_session(self.call_id)

    async def connect_external_websocket(self, url: str, timeout = 32):
        """Connect to external websocket for this call session."""
        self._bridge_loop = asyncio.get_running_loop()
        t = time()
        try:
            logger.info(f"[{self.call_id}] connecting to {url}")
            try:
                self.external_ws = await websockets.connect(url)
                logger.info(f"[{self.call_id}] connected to {url}")
                logger.info(f"[{self.call_id}] Time taken to connect to external WebSocket: {time() - t:.2f} seconds")
            except Exception as conn_error:
                logger.error(f"[{self.call_id}] Failed to establish WebSocket connection to {url}: {conn_error}")
                raise

            while not self.stop_event.is_set():
                try:
                    message = await asyncio.wait_for(self.external_ws.recv(), timeout=timeout)
                    logger.info(f"[{self.call_id}] First message from tatatele received: {message}")
                    await self.outbound_media_stream(self.external_ws)
                except (asyncio.TimeoutError, TimeoutError):
                    #make it as failed for timeout
                    logger.info(f"[{self.call_id}] No message received in {timeout} seconds, checking stop_event")
                except Exception as e:
                    #set it as busy for recv error.
                    logger.error(f"[{self.call_id}] recv error: %s", e)
                finally:
                    self.stop_event.set()
                    break
        except Exception as e:
            logger.exception(f"[{self.call_id}] connection failed: %s", e)
        finally:
            #Socket cleanup - ensure all websockets are closed
            sockets_to_close = []
            if getattr(self, "external_ws", None):
                sockets_to_close.append(("external_ws", self.external_ws))
            if getattr(self, "dave_ws", None):
                sockets_to_close.append(("dave_ws", self.dave_ws))

            closed_ids = set()
            for socket_name, socket_obj in sockets_to_close:
                if id(socket_obj) in closed_ids:
                    continue
                closed_ids.add(id(socket_obj))
                try:
                    if not getattr(socket_obj, "closed", False):
                        await socket_obj.close()
                        logger.info(f"[{self.call_id}] Closed {socket_name}")
                except Exception as e:
                    logger.warning(f"[{self.call_id}] Error closing {socket_name}: {e}")

            self.external_ws = None
            self.dave_ws = None
            logger.info(f"[{self.call_id}] Done With session cleanup")


# ---------- Helper functions ----------

def run_async_in_thread(coro):
    """Run an async coroutine in a background thread with its own event loop."""
    #store reference to file/db - status in db then based on status then terminate
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
    analysis = callback_data.get('analysis', {}) or {}
    call_successful = analysis.get('call_successful', 'unknown')

    # Error information (if any)
    error = metadata.get('error', {}) or {}
    error_code = error.get('code', None)
    error_reason = error.get('reason', None)

    # RAG usage
    rag_usage = metadata.get('rag_usage', {}) or {}
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
    caller_id = session_data.get("agent_number", TATATELE_PHONE_NUMBER)
    session_id = session_data.get("session_id")
    customer_number = session_data.get("phone_number", "918850988794") #for test
    tatatele_phone_number_api_key = session_data.get("provider_credentials", {}).get('tatatele_phone_number_api_key')

    session_started = False

    session_data["agent_number"] = agent_number
    session_data["caller_id"] = caller_id

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
        external_wss = f"{config.get_websocket_base_url(customer_number[-10:])}/tatatele/{customer_number[-10:]}/{agent_number[-10:]}_{customer_number[-10:]}"

        async def start_bridge():
            await session.connect_external_websocket(external_wss)

        run_async_in_thread(start_bridge())
        #we have to check how to disconnect socket from elevanlabs -  
        return True

    if session_id and not session_started:
        session_started = start_session(session_id)

    try:
        logger.info("Originate call to %s via tatatele", customer_number)
        response = tatatele_client.click_to_call_support(
            caller_id,
            customer_number,
            custom_id= session_id, #custom_identifier session_id in this case
            api_key = tatatele_phone_number_api_key
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
        "Answered by agent": "reached"

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
    # if raw_status is None:
    #     raise KeyError("Missing 'call_status' field")

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
    t = time()
    data = request.get_json()

    from_number = data.get("from_number")[-10:]
    to_number = data.get("to_number")[-10:]

    base_ws_url = config.get_websocket_base_url(to_number)

    wss_url = f"{base_ws_url}/tatatele/{from_number}_{to_number}/{to_number}"

    logger.info(f"[webhook-/tatatele/create-stream-url] Generated wss_url took {time() - t:.2f} seconds: {wss_url}")
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
    t  = time()
    raw = request.get_data()
    logger.info(f"Received SmartFlo webhook: {raw}")
    payload = tatatele_status_map(raw)

    call_id = payload.get("call_id")
    if not call_id:
        logger.warning("Received webhook without call_id")
        return jsonify({"status": "error", "message": "Missing call_id"}), 400

    session_id = payload.get("custom_identifier") 
    status = payload.get("call_status")

    logger.info(f"[{call_id}] Incoming payload: {json.dumps(payload, indent=4)}")
    import gryd_tasks
    if  status in ["contacted"]: #after call ended

        session_model = config.AutocrmModel(config.SESSION_MODEL_NAME, logger = logger )
        session_model.update(session_id, 
                             {
                                "call_recording": payload.get("recording_url"), 
                                "duration": float(payload.get("duration", 0.0))
                            }) #add more attributes when needed
        logger.info(f"[webhook-/smartflo/webhook] Time taken to update session with recording URL and duration: {time() - t:.2f} seconds")
        gryd_tasks.post_contact_status_voice(session_id = session_id, message_id = session_id,  **{"status": status})
    elif status in ["reached"]: # as soon as call is answered 
        gryd_tasks.post_billing_object(status, session_id)
        gryd_tasks.post_contact_status_voice(session_id = session_id, message_id = session_id,  **{"status": status})
        logger.info(f"[webhook-/smartflo/webhook] Time taken to post billing object and contact status for reached: {time() - t:.2f} seconds")
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
    t = time()
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
    transcript_summary= data.get("analysis",{}).get("transcript_summary")
    logger.info(f"Transcript summary: {transcript_summary}")
    logger.info(f"Triggering post session process for session_id: {session_id}")


    gryd_tasks.gryd.create_async_task(
        "end_session_and_post_process",
        config.AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME,
        args  = [],
        kwargs={
            "session_id": session_id,
            "additional_dict":{
                "history": session_history,
                "status": "completed",
                "summary": transcript_summary
            },
            "channel": "voice_phone"
        }
    )



    logger.info(f"[webhook-tatatele-conversation] Time taken to post history and end session: {time() - t:.2f} seconds")
    
    # gryd_tasks.post_actions(session_id) #calling in end_session

    return jsonify({"status": "processed"})


def format_transcript(transcript, start_time_unix):
    from datetime import datetime
    session_history = []
    if not transcript:
        return []
    func = lambda x: start_time_unix + float(x)
    for msg in transcript:
        session_history.append({
            "role":msg.get('role'),
            "message":msg.get('message','').replace('.','') if msg.get('message') else '',
            "timestamp": func(msg.get('time_in_call_secs',0.0))
        })
    
    return session_history


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)



    # make_call_tatatele - session_data - prompt, agent, user numbers etc.

    # 1. connect_external_websocket
    #     - connecting to go server where 11lab response are sent
    #     - connecting to 11labs websocket and starting the streaming
    #         1. we send initial config - prompt, user_id, dynamic variables etc.
    #         2. wait for tatatele to start call and recieve buffer as soon as call is connected
    

    #credentials 
    #elevanlanbs labs



