import sys
from os.path import dirname, abspath, join as joinpath
import os
sys.path.append(dirname(dirname(dirname(dirname(__file__)))))

import config as env
import asyncio
import threading
import traceback
from google import genai
from google.genai import types
from gryd_worker import gryd_helpers as hp
from typing import Dict, Any, Optional, Union

import utils
logger = utils.get_logger(__name__)

# Default Agent configs
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

class VoiceAgentError(hp.GrydError):
    pass


class SessionRegistry:
    """
    Each session dict contains:
      - client_connection
      - async_session
      - input_queue
      - output_queue
      - loop
      - task
      - start_time
      - message_sequence_id
      - sent_keys (asyncio.Queue of seq_keys in send order)
      - last_seq_key
      - status
      - last_error
    """
    sessions: dict[str, Any] = {}
    lock = threading.Lock()

    @classmethod
    def set_session(cls, session_id: str, session: Dict[str, Any]) -> None:
        with cls.lock:
            session.setdefault("status", "active")
            cls.sessions[session_id] = session

    @classmethod
    def mark_session_error(cls, session_id: str, error: str) -> None:
        with cls.lock:
            if session_id in cls.sessions:
                cls.sessions[session_id]["status"] = "error"
                cls.sessions[session_id]["last_error"] = error

    @classmethod
    def get_session(cls, session_id: str) -> Optional[Dict[str, Any]]:
        with cls.lock:
            return cls.sessions.get(session_id)

    @classmethod
    def update_session(cls, session_id: str, updates: Dict[str, Any], force_update: bool = False) -> None:
        with cls.lock:
            session = cls.sessions.get(session_id) or {}
            for key, value in updates.items():
                if key in session and not force_update:
                    continue
                session[key] = value
            session.setdefault("status", "active")
            cls.sessions[session_id] = session

    @classmethod
    def remove_session(cls, session_id: str) -> None:
        with cls.lock:
            cls.sessions.pop(session_id, None)


class GEMINIAPI:
    def __init__(self, input_queue, output_queue, prompt, timeout, **voice_params: Any) -> None:
        self.process_timeout = timeout
        self.audio_type: str = voice_params.get("audio_type", "pcm")
        self.sample_rate: int = int(voice_params.get("sample_rate", RECEIVE_SAMPLE_RATE))
        self.chunk_size: int = int(voice_params.get("chunk_size", 15000))
        self.voice_id: str = voice_params.get("voice_id", "Aoede")
        self.prompt = prompt

        self.client = genai.Client(
            api_key = env.GOOGLE_API_KEY
        )
        self.model_name: str = voice_params.get("model_name", "gemini-live-2.5-flash-preview")
        self.response_channel: str = voice_params.get("response_channel", voice_params.get("response", "AUDIO"),).strip().upper()

        self.input_queue = input_queue
        self.output_queue = output_queue

    def make_client_connection(self, model_name: str, response_channel: str, prompt: str, voice_id: str):
        system_prompt = prompt or self.prompt

        config_params = {
            "response_modalities": [response_channel],
            "system_instruction": system_prompt,
            "output_audio_transcription": {},
            "input_audio_transcription": {},
            "speech_config": types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_id
                    )
                )
            ),
        }
        logger.info(f"Configured voice agent model={model_name}, response_channel={response_channel}, voice_id={voice_id}")
        return self.client.aio.live.connect(model=model_name, config=config_params)

    async def create_session(self, session_id: str, model_name:Union[str, None] = None, response_channel:Union[str,None]= None, voice_id:Union[str, None]=None, prompt: Union[str,None]=None) -> None:
        if SessionRegistry.get_session(session_id):
            raise VoiceAgentError(f"session {session_id} already exists")

        model_name = model_name or self.model_name
        response_channel = response_channel or  self.response_channel
        response_channel = response_channel.strip().upper()
        if response_channel not in ("AUDIO", "TEXT"):
            raise VoiceAgentError(f"{response_channel} is not supported. Use AUDIO or TEXT.")

        user_prompt = prompt or self.prompt
        voice_id = voice_id or self.voice_id
        client_connection = self.make_client_connection(model_name, response_channel, user_prompt, voice_id)

        session: dict[str, Any] = {
            "client_connection": client_connection,
            "input_queue": self.input_queue,
            "output_queue": self.output_queue,
            "start_time": None,
            "message_sequence_id": None,
            "sent_keys": asyncio.Queue(),
            "last_seq_key": None,
        }

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            raise VoiceAgentError("No running asyncio event loop. create_session must be called within an active event loop.")

        session["start_time"] = loop.time()
        session["loop"] = loop

        SessionRegistry.set_session(session_id, session)

        session_task = loop.create_task(self.session_worker(session_id))
        session["task"] = session_task
        SessionRegistry.update_session(session_id, session, force_update=True)
        # logger.info(f"Started worker for session {session_id}")

    # def push_audio(self, session_id: str, media_params: dict) -> None:
    #     session = SessionRegistry.get_session(session_id)
    #     if not session:
    #         raise VoiceAgentError(f"Session {session_id} not found")

    #     message_id = media_params.get("message_id")
    #     if not message_id or not str(message_id).strip():
    #         raise VoiceAgentError("message_id is required")

    #     payload = media_params.get("payload") or {}
    #     audio_bytes = payload.get("audio_byte")
    #     sequence_number = payload.get("sequence", 0)

    #     if audio_bytes is None:
    #         raise VoiceAgentError("No audio_byte provided")

    #     try:
    #         sequence_number = int(sequence_number)
    #     except Exception:
    #         logger.warning("[%s] Invalid sequence; using 0.", session_id)
    #         sequence_number = 0

    #     seq_key = f"{message_id}---{sequence_number}"
    #     session["message_sequence_id"] = seq_key

    #     input_queue = session["input_queue"]
    #     loop = session.get("loop")
    #     if loop is None:
    #         raise VoiceAgentError(
    #             "Session loop not available; recreate the session inside an event loop."
    #         )

    #     def _put() -> None:
    #         try:
    #             input_queue.put_nowait({seq_key: audio_bytes})
    #         except Exception:
    #             logger.warning("[%s] Failed to put audio into input_queue", session_id)

    #     loop.call_soon_threadsafe(_put)

    def end_session(self, session_id: str) -> None:
        session = SessionRegistry.get_session(session_id)
        if not session:
            return

        loop = session.get("loop")
        if not loop:
            return

        def _put_sentinel() -> None:
            try:
                session["input_queue"].put_nowait(None)
            except Exception:
                logger.warning("[%s] failed to schedule session sentinel", session_id)
        loop.call_soon_threadsafe(_put_sentinel)

    def interrupt(self, session_id: str):
        session = SessionRegistry.get_session(session_id)
        if not session:
            logger.warning(f"[{session_id}] interrupt flagged but unable to clear the queue")
            return

        input_queue = session["input_queue"]
        output_queue = session["output_queue"]
        loop = session.get("loop")

        async def _clear():
            try:
                while not input_queue.empty():
                    input_queue.get_nowait()
            except Exception:
                pass

            try:
                while not output_queue.empty():
                    output_queue.get_nowait()
            except Exception:
                pass
            logger.info(f"[{session_id}] queues cleared")

        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(_clear(), loop)
        else:
            logger.warning(f"[{session_id}] no active loop to clear queues")
        
    async def session_worker(self, session_id: str) -> None:
        session = SessionRegistry.get_session(session_id)
        if not session:
            logger.error(f"Session not found for session {session_id}")
            raise VoiceAgentError(f'Session need to be started.')

        client_connection = session["client_connection"]
        input_queue = session["input_queue"]
        output_queue = session["output_queue"]

        sent_keys_q: asyncio.Queue = session.setdefault("sent_keys", asyncio.Queue())
        session.setdefault("last_seq_key", None)

        try:
            loop = asyncio.get_running_loop()
        except Exception:
            logger.warning(f"[{session_id}] could not get running loop for worker")

        sender_task = None
        receiver_task = None
        worker_error: Optional[BaseException] = None

        try:
            async with client_connection as async_session:
                session["async_session"] = async_session

                async def sender() -> None:
                    logger.info(f"[{session_id}] sender started")
                    try:
                        while True:
                            try:
                                # Enforce "real-time" input: fail if we don't get audio within process_timeout
                                data = input_queue.get()
                            except Exception as e:
                                msg = "Audio needs to be sent in real time."
                                logger.info(f"[{session_id}] sender timed out while waiting for audio chunk {self.process_timeout}")
                                raise VoiceAgentError(msg)

                            if data is None:
                                # logger.info(f'[{session_id}] Closing request acknowlegded')
                                break

                            seq_key = next(iter(data.keys()))
                            audio_bytes = data[seq_key]

                            await sent_keys_q.put(seq_key)
                            session["last_seq_key"] = seq_key

                            await async_session.send_realtime_input(
                                audio = {
                                    "data": audio_bytes,
                                    "mime_type": f"audio/pcm;rate={self.sample_rate}",
                                }
                            )
                    except asyncio.CancelledError:
                        logger.info(f"[{session_id}] sender cancelled (normal shutdown).")
                    except VoiceAgentError as e:
                        logger.error(f"[{session_id}] sender VoiceAgentError: {str(e)}")
                        SessionRegistry.mark_session_error(session_id, str(e))
                        raise
                    except Exception as e:
                        logger.error(f"[{session_id}] sender crashed due to {str(e)}")
                        SessionRegistry.mark_session_error(session_id, str(e))
                        raise VoiceAgentError(str(e))

                async def receiver() -> None:
                    input_transcript: list[str] = []
                    output_transcript: list[str] = []

                    logger.info(f"[{session_id}] receiver started")
                    agen = async_session.receive().__aiter__()

                    try:
                        while True:
                            try:
                                response = await asyncio.wait_for(agen.__anext__(), timeout=self.process_timeout+1)
                            except asyncio.TimeoutError:
                                if hasattr(async_session, "ping"):
                                    try:
                                        await asyncio.wait_for(async_session.ping(), timeout=5)
                                    except Exception:
                                        logger.debug(f"[{session_id}] ping failed during timeout")
                                continue
                            except StopAsyncIteration:
                                logger.info(f"[{session_id}] Agent Finished Executing.")
                                # traceback.print_exc()
                                break
                            except asyncio.CancelledError as e:
                                traceback.print_exc()
                                logger.info(f"[{session_id}] receiver cancelled (normal shutdown).")
                                break
                            except Exception as e:
                                logger.warning(f"[{session_id}] exception during receive(): {str(e)}")
                                SessionRegistry.mark_session_error(session_id, str(e))
                                break

                            try:
                                server_content = getattr(response, "server_content", None)
                                if server_content is None:
                                    continue

                                resolved_seq_key = None
                                model_turn = server_content.model_turn
                                if model_turn and model_turn.parts:
                                    part = model_turn.parts[0]
                                    inline_data = getattr(getattr(part, "inline_data", None), "data", None)
                                    if inline_data is not None:
                                        if not resolved_seq_key:
                                            try:
                                                resolved_seq_key = sent_keys_q.get_nowait()
                                            except asyncio.QueueEmpty:
                                                resolved_seq_key = (session.get("last_seq_key") or "unknown----0")

                                        try:
                                            message_id, sequence_number, start_time = resolved_seq_key.split("----", 2)
                                        except Exception:
                                            message_id, sequence_number, start_time = resolved_seq_key, "0", hp.time()

                                        payload = {
                                            session_id: {
                                                message_id: {
                                                    "sequence_number": sequence_number,
                                                    "agent_response": inline_data,
                                                    "agent_recieved": float(start_time),
                                                    "agent_responded": hp.time()
                                                }
                                            }
                                        }
                                        output_queue.put(payload)
                                
                                if (hasattr(server_content, "interrupted") and server_content.interrupted):
                                    logger.info(f'[{session_id}] Interruption detected.')
                                    self.interrupt(session_id)
                                    
                                if server_content.output_transcription:
                                    output_transcript.append(server_content.output_transcription.text)
                                    logger.info(f"[{session_id}] Output Transcript: {server_content.output_transcription.text}")

                                if server_content.input_transcription:
                                    input_transcript.append(server_content.input_transcription.text)
                                    logger.info(f"[{session_id}] Input Transcript: {server_content.input_transcription.text}")

                                if server_content.generation_complete:
                                    # logger.info(f"[{session_id}] Agent finished generation.")
                                    logger.info(f"[{session_id}] Final Input Transcription: {''.join(input_transcript).strip()}")
                                    logger.info(f"[{session_id}] Final Output Transcription: {''.join(output_transcript).strip()}")
                                    
                            except asyncio.CancelledError:
                                logger.info(f"[{session_id}] receiver processing cancelled.")
                                traceback.print_exc()
                                break
                            except Exception:
                                logger.warning(f"[{session_id}] error processing response")
                                traceback.print_exc()

                    finally:
                        # logger.info(f'[{session_id}] reciever finished the task')
                        pass
                    
                    
                sender_task = asyncio.create_task(sender())
                receiver_task = asyncio.create_task(receiver())

                done, pending = await asyncio.wait({sender_task, receiver_task}, return_when=asyncio.FIRST_EXCEPTION)

                for t in done:
                    exc = t.exception()
                    if exc:
                        worker_error = exc
                        logger.warning(f"[{session_id}] task {t} finished with exception: {exc}")
                        if not isinstance(exc, asyncio.CancelledError):
                            SessionRegistry.mark_session_error(session_id, traceback.format_exc())

                for t in pending:
                    t.cancel()
                    try:
                        await t
                    except asyncio.CancelledError:
                        pass

        except Exception as e:
            worker_error = worker_error or e
            logger.warning(f'[{session_id}] session worker crashed: {e}": {traceback.format_exc()}')
            SessionRegistry.mark_session_error(session_id, traceback.format_exc())
        finally:
            try:
                if worker_error:
                    err_msg = str(worker_error)
                    logger.info(f"[{session_id}] sending error to output_queue: {err_msg}")
                    self.output_queue.put({"error": err_msg})
                else:
                    self.output_queue.put(None)
            except Exception:
                logger.warning(f"[{session_id}] failed to put final message into output_queue from session_worker")

            try:
                if session.get("async_session") is not None:
                    try:
                        await session["async_session"].close()
                    except Exception:
                        pass
            except Exception:
                pass

            SessionRegistry.remove_session(session_id)
            # logger.info("Worker for session %s has exited and cleaned up", session_id)
