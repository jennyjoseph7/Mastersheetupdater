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

# import utils
logger = hp.get_logger(__name__)
import pyaudio

pya = pyaudio.PyAudio()

FORMAT = pyaudio.paInt16
CHANNELS = 1

# Default Agent configs
SEND_SAMPLE_RATE = 24000
RECEIVE_SAMPLE_RATE = 8000
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

    async def create_session(self, session_id: str, model_name: Union[str, None] = None, response_channel: Union[str, None] = None, voice_id: Union[str, None] = None, prompt: Union[str, None] = None) -> None:
        if SessionRegistry.get_session(session_id):
            raise VoiceAgentError(f"session {session_id} already exists")

        model_name = model_name or self.model_name
        response_channel = (response_channel or self.response_channel).strip().upper()
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

        loop = asyncio.get_running_loop()
        session["start_time"] = loop.time()
        session["loop"] = loop

        SessionRegistry.set_session(session_id, session)

        worker_task = loop.create_task(self.session_worker(session_id))
        session["task"] = worker_task
        SessionRegistry.update_session(session_id, session, force_update=True)
        
        logger.info(f"Started worker for session {session_id}")

    # async def listen_audio(self):
    #     logger.info(f'Listening to the audio')
    #     mic_info = pya.get_default_input_device_info()
    #     self.audio_stream = await asyncio.to_thread(
    #         pya.open,
    #         format=FORMAT,
    #         channels=CHANNELS,
    #         rate=SEND_SAMPLE_RATE,
    #         input=True,
    #         input_device_index=mic_info["index"],
    #         frames_per_buffer=CHUNK_SIZE,
    #     )
    #     if __debug__:
    #         kwargs = {"exception_on_overflow": False}
    #     else:
    #         kwargs = {}
    #     count = 0
    #     while True:
    #         data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
    #         await self.input_queue.put({count: data})
    #         count = count+1

    # async def listen_audio(self):
    #     logger.info(f'Listening to the audio')
    #     mic_info = pya.get_default_input_device_info()
    #     self.audio_stream = await asyncio.to_thread(
    #         pya.open,
    #         format=FORMAT,
    #         channels=CHANNELS,
    #         rate=SEND_SAMPLE_RATE,
    #         input=True,
    #         input_device_index=mic_info["index"],
    #         frames_per_buffer=CHUNK_SIZE,
    #     )
    #     if __debug__:
    #         kwargs = {"exception_on_overflow": False}
    #     else:
    #         kwargs = {}
    #     count = 0
    #     while True:
    #         data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
    #         await self.input_queue.put({count: data})
    #         count = count+1
            
    # async def play_audio(self):
    #     stream = await asyncio.to_thread(
    #         pya.open,
    #         format=FORMAT,
    #         channels=CHANNELS,
    #         rate=RECEIVE_SAMPLE_RATE,
    #         output=True,
    #     )
    #     import wave
        
    #     wave_open = wave.open('shivam_recorder.wav', 'wb')
    #     wave_open.setframerate(24000)
    #     wave_open.setnchannels(2)
    #     wave_open.setsampwidth(2)
    #     # session = SessionRegistry.get_session(self.session_id)
    #     while True:
    #         bytestream = await self.output_queue.get()
    #         # wave_open.writeframes(bytestream)
    #         await asyncio.to_thread(stream.write, bytestream)
    
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
        def _clear():
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

        _clear() #clear queue
        
    async def session_worker(self, session_id: str) -> None:
        session = SessionRegistry.get_session(session_id)
        self.provider_metadata = {} #to maintain stream id etc.

        if not session:
            logger.error(f"Session not found for session {session_id}")
            raise VoiceAgentError(f'Session need to be started.')

        client_connection = session["client_connection"]
        input_queue = session["input_queue"]
        output_queue = session["output_queue"]

        sent_keys_q: asyncio.Queue = session.setdefault("sent_keys", asyncio.Queue())
        session.setdefault("last_seq_key", None)
        
        logger.info(f'inside session worker')
        try:
            loop = asyncio.get_running_loop()
        except Exception:
            logger.warning(f"[{session_id}] could not get running loop for worker")

        worker_error: Optional[BaseException] = None

        try:
            logger.info('before creating client session')
            async with client_connection as async_session:
                logger.info('client session started...')
                session["async_session"] = async_session

                async def sender() -> None:
                    import queue as pyqueue
                    logger.info(f"[{session_id}] sender started")
                    chunk_count = 0
                    
                    try:
                        while True:
                            try:
                                data = await asyncio.to_thread(input_queue.get, timeout=1)
                            except pyqueue.Empty:
                                continue
                            except Exception as e:
                                logger.warning(f"[{session_id}] unexpected sender error: {str(e)}")
                                continue

                            if data is None:
                                # logger.info(f'[{session_id}] Closing request acknowlegded')
                                continue
                            logger.info(f'Received data in input_queue of type {type(data)}')
                            
                            message_id = data.get('message_id')
                            recieved_session_id = data.get('session_id')
                            audio_bytes = data.get('audio_data')
                            
                            if not audio_bytes:
                                logger.info('skippig none byte receuved')
                                continue
                            else:
                                logger.info(f'received {type(audio_bytes)}')
                            
                            self.provider_metadata = data.get('metadata',{})
                            message_type = data.get('message_type', 'start_stream')
                            ##message type to add some more logic - inital config when stream_start etc.

                            if session_id!=recieved_session_id:
                                raise VoiceAgentError(f'mismatch session id is provided: {recieved_session_id}')
                            
                            seq_key = f'{message_id}----{hp.time()}'
                            # seq_key = next(iter(data.keys()))
                            # audio_bytes = data[seq_key]

                            await sent_keys_q.put(seq_key)
                            session["last_seq_key"] = seq_key
                            
                            chunk_count += 1
                            
                            if chunk_count % 20 == 1:
                                import array
                                samples = array.array('h', audio_bytes)
                                max_amp = max(abs(s) for s in samples) if samples else 0
                                logger.info(f"[{session_id}] Chunk #{chunk_count}: {len(audio_bytes)} bytes, max_amp={max_amp}")
                            
                            await async_session.send_realtime_input(
                                audio = {
                                    "data": audio_bytes,
                                    "mime_type": f"audio/pcm;rate={RECEIVE_SAMPLE_RATE}"  # 8000 for Twilio
                                }
                            )

                    except Exception as e:
                        logger.error(f"[{session_id}] sender crashed: {str(e)}")
                        raise

                async def receiver() -> None:
                    input_transcript: list[str] = []
                    output_transcript: list[str] = []

                    logger.info(f"[{session_id}] receiver started")
                    agen = async_session.receive().__aiter__()
                    
                    response_count = 0
                    
                    try:
                        while True:
                            try:
                                if response_count % 5 == 0:
                                    logger.info(f"[{session_id}] Waiting for response #{response_count}...")
                                
                                response = await asyncio.wait_for(agen.__anext__(), timeout=self.process_timeout+1)
                                
                                response_count += 1
                                logger.info(f"[{session_id}] ✓ Got response #{response_count}: {type(response)}")
                                
                            except asyncio.TimeoutError:
                                logger.warning(f"[{session_id}] Timeout after {self.process_timeout}s, will retry...")
                                if hasattr(async_session, "ping"):
                                    try:
                                        await asyncio.wait_for(async_session.ping(), timeout=5)
                                        logger.info(f"[{session_id}] Ping successful")
                                    except Exception as e:
                                        logger.warning(f"[{session_id}] Ping failed: {e}")
                                continue
                                
                            except StopAsyncIteration:
                                logger.info(f"[{session_id}] StopAsyncIteration - turn complete, restarting")
                                agen = async_session.receive().__aiter__()
                                continue
                                
                            try:
                                server_content = getattr(response, "server_content", None)
                                if server_content is None:
                                    logger.debug(f"[{session_id}] Response has no server_content")
                                    continue
                                
                                if server_content.interrupted:
                                    logger.info(f'[{session_id}] Interruption detected.')
                                    self.interrupt(session_id)
                                    payload = {
                                        "session_id": session_id,
                                        "message_id": None,
                                        "audio_data": None,
                                        "message_type": "clear_buffer",
                                        "metadata": self.provider_metadata,
                                    }
                                    output_queue.put(payload)
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
                                                resolved_seq_key = (session.get("last_seq_key") or f"unknown----{hp.time()}")

                                        try:
                                            message_id, start_time = resolved_seq_key.split("----", 1)
                                        except Exception:
                                            message_id, start_time = resolved_seq_key, hp.time()

                                        # Add sample rate to metadata for proper audio conversion
                                        metadata = {**self.provider_metadata, "sample_rate": SEND_SAMPLE_RATE}

                                        payload = {
                                            "session_id": session_id,
                                            "message_id": message_id,
                                            "audio_data": inline_data,
                                            "message_type": "audio_output",
                                            "metadata": metadata,
                                        }
                                        logger.info(f'Puting payload to output queue: {payload}')
                                        output_queue.put(payload)

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
                                    
                            except Exception as e:
                                logger.error(f"[{session_id}] Error processing response: {e}")
                                import traceback
                                traceback.print_exc()
                                
                    except Exception as e:
                        logger.error(f"[{session_id}] receiver crashed: {e}")
                        raise

                    
                sender_task = asyncio.create_task(sender())
                receiver_task = asyncio.create_task(receiver())
                
                # return sender, receiver

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