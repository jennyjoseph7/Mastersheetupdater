"""
Voice Agent
AI-driven conversational engine for real-time understanding and response generation
"""

import asyncio
import typing
import munch
import traceback
import threading
from google import genai
from google.genai import types
from gryd_worker import gryd_helpers as hp
import pyaudio

pya = pyaudio.PyAudio()
logger = hp.get_logger(__name__)


##Mic configs
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024


RECEIVER_POLL_TIMEOUT = 600
RECIEVER_SHUTDOWN_DRAIN_TIMEOUT = 20 
SENDER_SHUTDOWN_TMEOUT=5

class VoiceAgentError(hp.GrydError):
    pass

class SessionRegistry:
    sessions: typing.Dict[str, typing.Any] = {}
    lock = threading.Lock()

    @classmethod
    def set_session(cls, session_id: str, session: typing.Any):
        with cls.lock:
            session.setdefault("status", "active")
            cls.sessions[session_id] = session

    @classmethod
    def mark_session_error(cls, session_id: str, error: str):
        with cls.lock:
            if session_id in cls.sessions:
                cls.sessions[session_id]["status"] = "error"
                cls.sessions[session_id]["last_error"] = error

    @classmethod
    def get_session(cls, session_id: str):
        with cls.lock:
            return cls.sessions.get(session_id)

    @classmethod
    def update_session(cls, session_id, updates: dict, force_update: bool = False):
        with cls.lock:
            session = cls.sessions.get(session_id) or {}
            for key, value in updates.items():
                if key in session and not force_update:
                    continue
                session[key] = value
            session.setdefault("status", "active")
            cls.sessions[session_id] = session

    @classmethod
    def remove_session(cls, session_id: str):
        with cls.lock:
            cls.sessions.pop(session_id, None)

#INput_Structure , output structure, Input and output Queue and state management
# class VOICEAGENT()
#     def __init__(self) -> None:
#         pass
    
#     def push_audio

class GEMINI_API():
    def __init__(self, voice_params: typing.Union[munch.Munch, dict] = {}) -> None:
        self.audio_type = voice_params.get('audio_type', 'pcm')
        self.sample_rate = voice_params.get('sample_rate', 24000)
        self.chunk_size = voice_params.get('chunk_size', 15000)
        self.voice_id = voice_params.get('voice_id', 'Aoede')

        self.client = genai.Client()
        self.model_name = voice_params.get('model_name', 'gemini-live-2.5-flash-preview')
        self.response_channel = voice_params.get('response', 'AUDIO').strip().upper()

    def make_client_connection(self, model_name, response_channel, prompt, voice_id):
        # logger.info(f'Prompt has been registered with {prompt} with {response_channel}')
        config_params = {
            "response_modalities": [response_channel],
            'system_instruction': prompt,
            "output_audio_transcription": {},
            'input_audio_transcription': {},
            'speech_config': types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_id)
                )
            ),
        }
        logger.info(f'Successfully Configured the Voice Agent.')
        return self.client.aio.live.connect(model=model_name, config=config_params)

    def create_session(self, session_id: str, media_params: dict):
        # self.session_id = session_id
        session = SessionRegistry.get_session(session_id)
        if session:
            raise VoiceAgentError(f"session {session_id} already exists")

        model_name = media_params.get('model_name', self.model_name)
        response_channel = media_params.get('response_channel', self.response_channel).strip().upper()
        if response_channel not in ['AUDIO', 'TEXT']:
            raise VoiceAgentError(f'{response_channel} is not supported. Check the available channels.')
        
        user_prompt = media_params.get('agent', {}).get('prompt', '')
        voice_id = media_params.get('voice_id', self.voice_id)
        output_queue = media_params.get('queue')
        if output_queue is None:
            raise VoiceAgentError('An output queue must be provided by the caller.')

        input_queue = asyncio.Queue()
        self.output_queue = output_queue
        self.input_queue = input_queue
        client_connection = self.make_client_connection(model_name, response_channel, user_prompt, voice_id)

        session = {
            'client_connection': client_connection,
            'input_queue': input_queue,
            'output_queue': output_queue,
            'stop': False,
            'start_time': None,
            'message_sequence_id': None,
            'sent_keys': asyncio.Queue(),
            'last_seq_key': None,  
        }

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            raise VoiceAgentError('No running asyncio event loop. create_session must be called within an active event loop.')

        session['start_time'] = loop.time()
        session['loop'] = loop

        SessionRegistry.set_session(session_id, session)

        session_task = loop.create_task(self.session_worker(session_id))
        session['task'] = session_task
        SessionRegistry.update_session(session_id, session, force_update=True)
        logger.info(f'Started worker for session {session_id}')

    def push_audio(self, session_id: str, media_params: dict):
        session = SessionRegistry.get_session(session_id)
        if not session:
            raise VoiceAgentError(f'Session {session_id} not found')

        message_id = media_params.get('message_id')
        if not message_id or not str(message_id).strip():
            raise VoiceAgentError('message_id is required')

        payload = media_params.get('payload') or {}
        audio_bytes = payload.get('audio_byte')
        sequence_number = payload.get('sequence', 0)

        if audio_bytes is None:
            raise VoiceAgentError('No audio_byte provided')

        try:
            sequence_number = int(sequence_number)
        except Exception:
            logger.warning('No sequence number set. Using Default sequence number.')
            sequence_number = 0
            # raise VoiceAgentError('sequence must be an int')

        seq_key = f'{message_id}---{sequence_number}'
        session['message_sequence_id'] = seq_key

        input_queue = session['input_queue']
        loop = session.get('loop')
        if loop is None:
            raise VoiceAgentError('Session loop not available; recreate the session inside an event loop.')

        def _put():
            try:
                logger.info(f'Pushing audio data to input_queue with {seq_key}')
                input_queue.put_nowait({seq_key: audio_bytes})
            except Exception:
                logger.warning('failed to put audio into session input_queue')
        loop.call_soon_threadsafe(_put)

    def end_session(self, session_id: str):
        session = SessionRegistry.get_session(session_id)
        if not session:
            return
        session['stop'] = True
        loop = session.get('loop')
        if loop:
            try:
                loop.call_soon_threadsafe(lambda: session['input_queue'].put_nowait(None))
            except Exception:
                logger.warning('failed to schedule session sentinel')

        
    async def session_worker(self, session_id: str):
        session = SessionRegistry.get_session(session_id)
        if not session:
            logger.error(f'Worker started for missing session {session_id}')
            return

        client_conn = session['client_connection']
        input_queue = session['input_queue']
        output_queue = session['output_queue']
        sender_done = asyncio.Event()
        
        sent_keys_q: asyncio.Queue = session.setdefault('sent_keys', asyncio.Queue())
        session.setdefault('last_seq_key', None)
        
        try:
            loop = asyncio.get_running_loop()
            logger.info(f'Worker for {session_id} started on loop {loop}')
        except Exception:
            logger.warning('could not get running loop for worker')

        async_session = None
        sender_task = None
        receiver_task = None

        try:
            async with client_conn as async_session:
                session['async_session'] = async_session

                async def sender():
                    logger.info(f'[{session_id}] sender started')
                    try:
                        while True:
                            data = await input_queue.get()
                            if data is None or session.get('stop'):
                                logger.info(f'[{session_id}] CLosing Request received.')
                                break

                            
                            seq_key = next(iter(data.keys()))
                            audio_bytes = data[seq_key]
                            
                            await sent_keys_q.put(seq_key)
                            session['last_seq_key'] = seq_key
                            await async_session.send_realtime_input(audio={'data': audio_bytes, 'mime_type': f'audio/pcm;rate={16000}'})
                            
                    except asyncio.CancelledError as e:
                        logger.info(f'[{session_id}] failed when sending the audio chunks. due to {str(e)}')
                        traceback.print_exc
                        # raise VoiceAgentError({'error_occured': e})
                        pass
                    except Exception as e:
                        logger.error(f'[{session_id}] crashed due to {e}')
                        SessionRegistry.mark_session_error(session_id, traceback.format_exc())
                    finally:
                        # sender_done.set()
                        logger.info(f'[{session_id}] Server Closed Successfully.')

                async def receiver():
                    input_transcript = []
                    output_transcript = []
                    
                    logger.info(f'[{session_id}] receiver started')
                    agen = async_session.receive().__aiter__()
                    try:
                        while True:
                            try:
                                response = await asyncio.wait_for(agen.__anext__(), timeout=RECEIVER_POLL_TIMEOUT)
                            except asyncio.TimeoutError:
                                if hasattr(async_session, "ping"):
                                    try:
                                        await asyncio.wait_for(async_session.ping(), timeout=5)
                                    except Exception:
                                        logger.debug(f'[{session_id}] ping failed during timeout')
                                continue
                            except StopAsyncIteration:
                                logger.info(f'[{session_id}] receive generator closed by server')
                                agen  = async_session.receive().__aiter__()
                                continue
                            except asyncio.CancelledError as e:
                                logger.info(f'[{session_id}] receiver cancelled due to {str(e)}')
                                raise VoiceAgentError(e)
                            except Exception as e:
                                logger.warning(f'[{session_id}] exception during receive(): {e}')
                                SessionRegistry.mark_session_error(session_id, str(e))
                                break

                            try:
                                server_content = response.server_content
                                if server_content is None:
                                    continue
                                
                                resolved_seq_key = None
                                model_turn = server_content.model_turn
                                if model_turn and model_turn.parts:
                                    part = model_turn.parts[0]
                                    inline_data = getattr(part.inline_data, 'data', None)
                                    if inline_data is not None:
                                        if not resolved_seq_key:
                                            try:
                                                resolved_seq_key = sent_keys_q.get_nowait()
                                            except asyncio.QueueEmpty:
                                                resolved_seq_key = session.get('last_seq_key') or f'unknown---0'

                                        try:
                                            message_id, sequence_number = resolved_seq_key.split('---', 1)
                                        except Exception:
                                            message_id, sequence_number = resolved_seq_key, '0'

                                        # payload = {
                                        #     session_id: {
                                        #         message_id: {
                                        #             'sequence_number': sequence_number,
                                        #             'agent_response': inline_data,
                                        #         }
                                        #     }
                                        # }
                                        
                                    # await output_queue.put(payload)
                                        await output_queue.put(inline_data)
                                if server_content.generation_complete:
                                    logger.info(f'Agent Finished the Genertion.') 
                                    logger.info(f'Final Input Transcription: {"".join(output_transcript).strip()}')
                                    logger.info(f'Final Output Transcription: {"".join(input_transcript).strip()}')
                                    
                                    input_transcript = []
                                    output_transcript = []
                                    # break    #Currently breaking on first Complete generation.  Might need to change to continue
                                
                                if server_content.output_transcription:
                                    input_transcript.append(server_content.output_transcription.text)
                                    logger.info('Output Transcript: %s', server_content.output_transcription.text)
                                
                                if server_content.input_transcription:
                                    output_transcript.append(server_content.input_transcription.text)
                                    logger.info('Input Transcript: %s', server_content.input_transcription.text)

                            except asyncio.CancelledError:
                                logger.info(f'[{session_id}] receiver processing cancelled')
                                raise
                            except Exception:
                                logger.warning(f'[{session_id}] error processing response: {traceback.format_exc()}')

                            # if sender_done.is_set():
                            #     # logger.info('Server closed request recieved.')
                            #     # # break
                            #     if sent_keys_q.empty():
                            #         logger.info('Server closed request recieved.')
                                #     pass
                    except asyncio.CancelledError:
                        logger.info(f'[{session_id}] receiver cancelled outer')
                        raise
                    finally:
                        logger.info(f'[{session_id}] receiver finished')

                sender_task = asyncio.create_task(sender())
                receiver_task = asyncio.create_task(receiver())

                try:
                    # await sender_task
                    await asyncio.wait_for(sender_task, timeout=RECEIVER_POLL_TIMEOUT)
                except asyncio.TimeoutError:
                    logger.info(f'Server closed. Audio Need to send in realtime.')
                    raise VoiceAgentError(f'Audio need to send in realtime.')
                except asyncio.CancelledError:
                    logger.info(f'[{session_id}]Cancelled ')
                    if receiver_task and not receiver_task.done():
                        receiver_task.cancel()
                        try:
                            await receiver_task
                        except asyncio.CancelledError:
                            receiver_task.done()
                            pass
                    # raise VoiceAgentError(f'Unable to get the receiver. Due to Internal Error')
                
                try:
                    # await receiver_task
                    await asyncio.wait_for(receiver_task, timeout=SENDER_SHUTDOWN_TMEOUT)
                except asyncio.TimeoutError:
                    logger.info(f'[{session_id}] did not receive result with the timeout')
                    if receiver_task and not receiver_task.done():
                        receiver_task.cancel()
                        try:
                            await receiver_task
                        except asyncio.CancelledError:
                            
                            pass
                except asyncio.CancelledError:
                    logger.info(f'[{session_id}] outer cancelled while draining receiver')
                    if receiver_task and not receiver_task.done():
                        receiver_task.cancel()
                        try:
                            await receiver_task
                        except asyncio.CancelledError:
                            pass
                    raise VoiceAgentError(f'Unable to send the output. Due to internal Error')

        except Exception as e:
            logger.warning(f'[{session_id}] session worker crashed due to "{e}"')
            traceback.print_exc()
            SessionRegistry.mark_session_error(session_id, str(e))
            
        finally:
            for tname, t in (('sender', sender_task), ('receiver', receiver_task)):
                if t and not t.done():
                    logger.debug(f'[{session_id}] final cleanup: cancelling {tname}')
                    t.cancel()
                    try:
                        await t
                    except asyncio.CancelledError:
                        pass

            try:
                if session.get('async_session') is not None:
                    try:
                        await session['async_session'].close()
                    except Exception:
                        pass
            except Exception:
                pass

            SessionRegistry.remove_session(session_id)
            logger.info(f'Worker for session {session_id} has exited and cleaned up')

    async def listen_audio(self):
        logger.info(f'Listening to the audio')
        mic_info = pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}
        count = 0
        while True:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
            await self.input_queue.put({count: data})
            count = count+1
            
    async def play_audio(self):
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        import wave
        
        wave_open = wave.open('shivam_recorder.wav', 'wb')
        wave_open.setframerate(24000)
        wave_open.setnchannels(2)
        wave_open.setsampwidth(2)
        # session = SessionRegistry.get_session(self.session_id)
        while True:
            bytestream = await self.output_queue.get()
            # wave_open.writeframes(bytestream)
            await asyncio.to_thread(stream.write, bytestream)
    
async def main():
    va = VoiceAgent()
    output_queue = asyncio.Queue()  
    session_id = 'shivam_test'

    prompt_shivam = """You are a friendly and professional Maruti Digital Agent for the India region.   \n        Your role is to have natural, human-like conversations with customers that already own Maruti cars. \n        You should help the customer with the discovery and purchase of Customer Convenience Package.  \n         \n        You are an outbound call agent, calls customer who own Maruti Suzuki vehicles. \n        Don't give irrelevant information, do not talk about other competitors, and encourage Customer Convenience Package booking.\n\n        \n        Information on the user :- \n        {'customer_name': 'Soham', 'car_odo_reading': 59000, 'car_model': 'CIAZ', 'car_registration': 'MP04CT5084', 'car_variant_name': 'MARUTI CIAZ SMART HYBRID ALPHA 1.5L AT', 'vehicle_age': '2Years, 3Months, 22Days', 'last_service_date': '9/2/2025 01:38:37 PM', 'last_service_dealer': 'PLATINUM MOTOCORP LLP', 'next_service_due_date': '8/15/2025 12:00:00 AM'}\n\n        \n\n\n        \ud83c\udfaf Goals:  \n        1. Greet warmly and create a pleasant, welcoming atmosphere.When calling a customer,  Ask them if they can hear you. \n        2. If the User information includes the name of the user, ask them if you are speaking with <user name>. If name is not available in the information above, ask the user if they are the owner of a Maruti Suzuki vehicle.\n        3. Ask the user if they are the owner of the car mentioned in the information above.\n        4. If they are not the owner or not affilicated. Apologise and ask them for the number of the new owner if possible to update the records.\n        5. If it is their car, use the information on their car to explain why buying Customer Convenience Package would be beneficial for them.\n        6. Nudge the customer to go through the steps of purchasing the Customer Convenience Package.\n        7. Always try to pull them towards booking or purchasing Customer Convenience Package.\n        8. Capture customer details in a friendly and non-intrusive way:  \n            - Maruti Car owned if not mentioned in information below.\n- Type \n- Category(Gold, Platinum, Royal Platinum)\n- Plans((a) Hydro and rodent protect, (b)Fuel and rodent protect, (c) Plus and rodent protect)(details available in documents)\n        9. Gently encourage Customer Convenience Package booking without being pushy. The goal is to make it sound like a natural next step.  \n        10. You should explain the options in the steps to the customer and then ask them to select values the steps mentioned in point #4\n        11. If the customer asks about certain details about the product, answer but end your answer by subtly urging them to return to our Customer Convenience Package flow and provide the next required information.\n        12.  When ever possible use the information your have about the customer to make your responses more relatable and personalised.\n        \n        \ud83d\udde3\ufe0f Tone & Style:  \n            None\n        \n        \n        \ud83e\udd1d Conversation Flow:  \n        - Start with a warm greeting: introduce yourself as a Maruti digital sales assistant.  \n        - Ask about the customer's interest in Maruti cars.  \n        - If they mention a product \u2192 share some key highlights.  \n        - Suggest a Customer Convenience Package naturally:  \n        - \"A lot of customers have greatly benefited from our Customer Convenience Package. What about you?\"         \n        - Confirm all details politely before finishing.  \n        - End with appreciation and reassurance with a gist of what options they selected and information they provided:  \n        - \u201cThanks so much, I've got everything noted down. I will be sending you a message on whatsapp with the details and a payment link. You can continue there.\u201d  Then cut the call.\n        -  Avoid redundancy and monotonous speech.\n\n        Important Notes:\n        - If the customer vehicle age is older than 3 years they are not eligible for Customer Convenience Package.  Or if they the kms driven is higher than 1,00,000 kms they are not eligible for Customer Convenience Package.\n\n        Agent Personality:\n\n        You are friendly, patient, and knowledgeable about all Maruti products and Customer Convenience Package.\n        You are consultative, not pushy\n        You listen actively and adapt to customer needs\n        You are dedicated to providing an excellent customer experience\n        \n        Handling Objections:\n        \n        Price concerns: Emphasize value, features, financing options, and long-term benefits\n        Comparison with competitors: Highlight benefits, coverage, and possible downsides of not purchasing Customer Convenience Package.\n        Not ready to decide: Offer information, no-pressure follow-up, and stay helpful\n        They are not interested or cutting the call or do not want to talk - ask them to wait and hear you out about Customer Convenience Package.\n\n        Out of Scope Queries:\n        If customer asks about:\n        \n        Information not specifically in the prompt or documents uploaded.\n        Other car brands\n        Unrelated products/services\n        Information you don't have.\n        \n        \n        Always:\n        \n        Be warm and professional\n        Speak clearly and at a comfortable pace\n        Confirm understanding by repeating back important details\n        Show enthusiasm about Maruti products\n        Make the customer feel valued\n        Speak in simple short sentences so not to sound like an advertisement for a product.\n        When asking the user for some information for the steps, ask them one step at a time to not overwhelm them.\n        \n        Never:\n        Never ask the user for any information that is not required to complete the Customer Convenience Package flow.\n        Never ask the user for any payment information.\n        Never ask the user to tell you their cars odometer reading.\n\n        Never say you do not know the answer or cannot help the customer.\n        Do not mention your own name. Just refer to yourself as the Maruti's Digital Agent.\n        Following is information you can use to answer the customer queries about the products.\n\n        \n\nDocument id - faqsforccp : \n**Question: What is Customer Convenience Package?**\n\n**Answer: Customer Convenience Package (\u201cCCP\u201d) is a coverage provided by Maruti Suzuki India Limited**\n(\u201cMaruti Suzuki\u201d) which covers repair/replacement cost of engine or its allied part(s) which gets\ndamaged owing to issues/ defect arising due to water entry causing hydro lock or failure of engine parts\nand/or due to use of adulterated fuel and issue/defect arising due to rodent or insect bite beyond the\n_reasonable control of the customer, which are not covered under warranty or extended warranty._\n\n_For Customer having EW :-_\n\n_CCP can be purchased within 1 year and 9 months or mileage of 25 000 km from the date of vehicle sale_\n_for CCP 1 year package._\n\n_CCP can be purchased within 1 year and 9 months or mileage of 45 000 km from the date of vehicle sale_\n_for CCP 2 year package._\n\n_CCP can be purchased within 1 year and 9 months or mileage of 60 000 from the date of vehicle sale for_\n_CCP 3 year package._\n\n**Question: How many CCP plans does Maruti Suzuki offer?**\n\nAnswer : Currently Maruti Suzuki offers CCP plans with 9 options for customers with EW(CCP).\n\n_i)_ _CCP hydro and rodent protect :- for a period of 1 year, 2 years and 3 years which covers_\n_repairs for hydrostatic part failure and damages caused due to rodent or insect bite beyond_\n_the reasonable control of the customer._\n_ii)_ _CCP fuel and rodent protect :- for a period of 1 year, 2 years and 3 years which covers repairs_\n_for fuel adulteration failure and damages caused due to rodent or insect bite beyond the_\n_reasonable control of the customer._\niii) _CCP plus which covers repairs for hydrostatic failure, fuel adulteration failure and damage_\n_due to rodent or insect bite beyond the reasonable control of the customer are also available_\n_for a period of 1 year, 2 year and 3 year policy options._\n\n**Question: What are the packages available under CCP?**\n\n**Answer: CCP Package will be available in 9 types, given below:**\n\n_For CCP with 1 year Validity:-_\n\n**_CCP Gold_** _-  Valid up to 40 000 km or 12 months (For CCP Plans \u2013 (a) Hydro and rodent_\n_protect, (b)Fuel and rodent protect, (c) Plus and rodent protect)_\n\n_For CCP with 2 year Validity_\n\n**_CCP Platinum \u2013    Valid up to 70 000 km or 24 months (For CCP Plans- (a) Hydro and rodent_**\n_protect, (b)Fuel and rodent protect, (c) Plus and rodent protect)_\n\n_For CCP with 3 year Validity_\n\n\n-----\n\n**_CCP Royal Platinum - valid up to 100 000 km or 36 months (for CCP plans (a) Hydro and rodent_**\n_protect, (b)Fuel and rodent protect, (c) Plus and rodent protect)_\n\n**Question: Can CCP be purchased if I do not have an extended warranty on my vehicle.**\n\n**Answer: Yes N-EW CCP applicable for 1 year, 2 years and 3 years can be purchased if vehicle does not**\n_have extended warranty._\n\n**Question: What is N-EW CCP?**\n\n**Answer: N-EW CCP is No Extended warranty Customer Convenience Package, i.e. customers who have**\nnot purchased extended warranty can buy N-EW CCP.\n\n_N-EW CCP can be purchased within 9 months or mileage of 25 000 km from the date of vehicle sale for N-_\n_EW CCP 1 year._\n\n_N-EW CCP can be purchased within 9 months or mileage of 45 000 km from the date of vehicle sale for_\n_N-EW CCP 2 year._\n\n_N-EW CCP can be purchased within 9 months or mileage of 60 000 from the date of vehicle sale for N-EW_\n_CCP 3 year._\n\n**Question: What are the packages available under N-EW CCP?**\n\n**_Answer:- N-EW CCP Package will be available in 9 types, given below:_**\n\n_For N-EW CCP with 1 year Validity:-_\n\n**_N-EW CCP Gold_** _-  Valid up to 40 000 km or 12 months (For N-EW CCP Plans \u2013 (a)_\n_Hydro and rodent protect, (b)Fuel and rodent protect, (c) Plus and rodent protect)_\n\n_For N-EW CCP with 2 year Validity_\n\n**_N-EW CCP Platinum \u2013    Valid up to 70 000 km or 24 months (For N-EW CCP Plans- (a) Hydro and_**\n_rodent protect, (b)Fuel and rodent protect, (c) Plus and rodent protect)_\n\n_For N-EW CCP with 3 year Validity_\n\n**_N-EW CCP Royal Platinum - valid up to 100 000 km or 36 months (for N-EW CCP plans (a) Hydro_**\n_and rodent protect, (b)Fuel and rodent protect, (c) Plus and rodent protect)_\n\n**Question: Can CCP and N-EW CCP be renewed?**\n\n**Answer : Yes, CCP 1 year and CCP 2 years packages can be renewed for additional 1 more year till**\nvehicle is in warranty (36 months or 100 000 km) from the date of sale).N-EW CCP can\u2019t be renewed\n\n**_Question: What packages are available for renewal?_**\n\n\n-----\n\n_Answer:- CCP 1 year and 2 years Packages can be renewed for additional 1 year or 40 000 km with_\n_following package options:-_\n\n_1-_ _CCP Gold \u2013 Plus & Rodent Protect_\n_2-_ _CCP Gold \u2013 Hydro & Rodent Protect_\n_3-_ _CCP Gold \u2013 Fuel & Rodent Protect_\n\n**Question: How much will the CCP for my car cost me?**\n\n**Answer: The cost of CCP varies with every model variant. You can get an estimated cost for the CCP on**\nthe official website of Maruti Suzuki under the tab \u2018Services\u2019.\n\n**Question: For CCP claims, can I only visit the dealership from where I purchased the car/policy?**\n\n**Answer: As long as you visit any authorized Maruti Suzuki Dealer Service Centre, you can claim repairs**\nunder CCP at any authorized dealership, in any location across India.\n\n**Question: What is the Customer convenience package coverage applicability timelines?**\n\n_a._ _If CCP is purchased within 15 days of the vehicle sale invoice date - Benefits can be availed for_\n\n_period of 1 year, 2 years or 3 year as per the CPP terms mentioned in the policy._\n_b._ _If CCP is purchased after 15 days of the vehicle sale invoice date - Benefits can be availed after_\n\n_completion of 90 days of purchase of the CCP for a period 1 year, 2 years or 3 year as per CCP_\n_terms mentioned in policy._\nKindly note that the eligibility period is duly mentioned in the certificate and claims would be\naccepted during the said timeline.\n\n**Question: Are consumables like engine oil and coolant covered under CCP in case of breakdown?**\n\n**Answer: Consumables like Coolant, Engine oil etc.to address failures/damage arising solely out of water**\nentry in the engine or failure of engine parts due to use of adulterated fuel shall be covered under the\nCPP as per applicable packages. However, discretion of Maruti Suzuki shall be final and binding in this\nregard.\n\n**Question: In event of a breakdown, what should a customer do?**\n\n**Answer: Immediately take all steps necessary to minimize the extent of loss. The customer must bring**\nthe vehicle without delay to the nearest MSIL authorized workshop at his own cost to effect repair and\nto apprise the workshop about the CCP availability. Customer should also authorize the workshop to\ninspect the vehicle by dismantling requisite parts and establish the cause of breakdown/concern.\n\n**Question: Can CCP be cancelled once purchased.**\n\n**Answer: If the CCP is cancelled, the amount paid shall stand forfeited.**\n\n**_Question:- Can CCP be purchased via Easy EMI_**\n\n**_Answer : Yes_**\n\n**_Question :_** **_What is Easy EMI?_**\n\n\n-----\n\n**_Answer :-_** _Easy EMI is a financing option offered by Maruti Suzuki that allows you to purchase extended_\n_warranty or Customer Convenience Package without paying any interest on the EMI. This means you can_\n_spread the cost of the extended warranty or Customer Convenience Package over 3 or 6 monthly_\n_instalments without incurring any additional interest charges._\n\n**_Question : What is the minimum transaction amount required for Easy EMI with different banks?_**\n\n**_Answer: Please refer to the following table for the minimum transaction amount required for each bank_**\n_based on the tenure. The information provided in the table is indicative and may vary depending on the_\n_bank\u2019s policies and terms and conditions._\n\n|Issuing Banks (Credit Card)|Minimum Transaction Amount (for 3- and 6- months EMI tenure) in INR|\n|---|---|\n|HDFC Bank|1000|\n|State Bank of India|3000|\n|Kotak Mahindra Bank|2500|\n|ICICI Bank|1500|\n|Axis Bank|2500|\n|HSBC Bank|2000|\n|Standard Chartered Bank|2500|\n|Ratnakar bank Limited|2500|\n|Yes bank|2500|\n|Bank Of Baroda|2500|\n|IndusInd Bank|2000|\n|Amex|5000|\n|IDBI Bank|3000|\n\n\n-----END OF DOCUMENT faqsforccp \n\n\n\nDocument id - ewccpknowledgebank1 : \nExtended Warranty (EW) overview:\n\nWhen you buy a Maruti Suzuki car, the company offers you standard warranty up to 3 years or 1 Lakh kms,\nwhichever comes first for the car which are purchased after 8th July 2024. For the car which were purchased\nbefore 8th July 2024, company used to offer a standard warranty up to 2 years or 60000 kms, which ever\ncomes first. However, you can extend this coverage for up to 6 years or 1 60 000 km by purchasing extended\nwarranty for your car.\n\nTypes of Extended warranties offered by Maruti Suzuki:\n\nPlatinum: In this customer can extend warranty coverage of car up to 4 years or 120000 kms (whichever comes\nfirst ).\n\nRoyal Platinum: In this customer can extend warranty coverage of car up to 5 years or 140000 kms ( whichever\ncomes first ).\n\nSolitaire: In this customer can extend their warranty coverage of car up to 6 years or 160000 kms (whichever\ncomes first ).\n\nExtended warranty benefits:\n\nCovers breakdown of high valued Mechanical and Electrical Parts i.e Compressor, Engine control module\n(ECM), Engine, self-assembly, steering assembly, strut, head lamp, tail lamp, fog lamp, ORVM, infotainment\nsystem, radiator & master cylinder.\n\nBest resale value of cars.\n\nTension free drive up to 1,60,000 kms*\n\nOne time payment against rising cost of parts & labor charges.\n\nCCP ( Customer convenience Package ) overview:\n\nCustomer Convenience Package (CCP) is a coverage provided by Maruti Suzuki India Limited which covers\nrepair/replacement cost of engine or its allied part(s) which gets damaged owing to issues/ defect arising due\nto water entry causing hydro lock or failure of engine parts and/or due to use of adulterated fuel and issue/\ndefect arising due to rodent or insect bite beyond the reasonable control of the customer, which are not\ncovered under warranty or EW.\n\nTypes of CCP offered by Maruti Suzuki:\n\nCCP Type 1: Retail CCP\n\nType of Retail CCP packages:\n\nCCP Gold: Covers up to 1 year or 40000kms whichever comes first from the car sale date.\n\nCCP Platinum: Covers up to 2 years or 70000kms whichever comes first from the car sale date.\n\nCCP Royal Platinum: Covers up to 3 years or 100000kms whichever comes first from the car sale date.\n\nRetail CCP Purchase Eligibility:\n\nPurchase Validity( From Car sale date)\n\nPackage Type\n\nDuration\n\nOdometer km shown\n\nCCP Gold\n\n1 year and 9 Months ( For customers with EW) and 9 months ( For Non-EW Customers)\n\n<=25000\n\nCCP Platinum\n\n<=45000\n\nCCP Royal Platinum\n\n<=60000\n\nRetail CCP offerings:\n\nCCP Offerings\n\nCoverage\n\nCCP Hydro\n\nCovers the repairs due to Water entering the Engine\n\nCCP Fuel\n\nCovers repair due to improper fuel quality\n\nCCP Plus\n\nCovers repair due to water entering the engine and improper fuel quality\n\nNote: Customer can opt any one of the above-mentioned offerings along with the type of CCP package\npurchased.\n\nRetail CCP claim details:\n\nNote:\n\nIf Retail CCP is purchased within 15 days from car sale date,coverages provided by CCP starts from the CCP\npurchase date.\n\nIf Retail CCP is purchased after 15 days from car sale date,coverages provided by CCP starts after 90 days from\nthe CCP purchase date.\n\nCCP Package wise claim details\n\nCCP Type 2: Service activated CCP\n\nPurchase duration: It can be purchased after 3rd year and up to 10th year from vehicle sale date.\n\nCoverage duration: 1 year or 10000kms from service CCP sale date whichever comes first\n\nNote: Service CCP coverage starts after 15 days from purchasing service CCP\n\nObjective of the outbound call:\n\nTo sell CCP and EW amongst the target customer groups.\n\nTypes of target customer groups for EW:\n\nCustomers booked their car but yet to take delivery of their car and not opted for EW at the time of car\nbooking.\n\nCustomers who have completed first free service ( after 30 days or 1000 kms which ever comes first) and not\npurchased EW.\n\nCustomers whose standard warranty is going to expire within next 3months.\n\nTypes of target customer groups for CCP:\n\nCustomers who have completed first free service ( after 30 days or 1000 kms which ever comes first) and not\npurchased CCP.\n\nCustomers who have purchased car before 30 days from current date and not purchased CCP.\n\nExisting CCP & EW bot interaction script:\n\nEW FAQs:\n\nWhat is Maruti Suzuki Extended Warranty?\n\nAns: When you buy a Maruti Suzuki car, the company offers you warranty up to 3 years or 1 00 000 km\n(whichever comes first). However, you can extend this coverage for up to 6 years or 1 60 000 km by\npurchasing extended warranty for your car.\n\nWhat are the different types of Extended warranty?\n\nAns: You can choose from 3 types of extended warranty plans for your car. The Solitaire offers coverage up to 6\nyears or 1 60 000 km*; Royal Platinum offers coverage up to 5 years of 1 40 000 km*; and the Platinum\nextends the coverage up to 4 years or 1 20 000 km*.\n\nWhy should I take the Extended warranty and what are the parts does it covers?\n\nAns: As per the current trend a owner owns a vehicle for at least 5-6 years and the average kms he covers at\nleast 1,50000 kms .But the standard warranty lapses after completion of 3 years from the vehicle retail date\n.And Its generally provides coverage for high valued parts like Electronic Control Module (ECM), Compressor,\nSteering, Suspension, Injectors, Headlamp, Tail Lamp, Fog Lamp, Window Regulator, ORVM, Clutch Release\nBearing, Infotainment System, Radiator, Brake Master Cylinder, Wheel Cylinder & Lock Set.\n\nWill EW expire once I sell my car?\n\nAns: It can be transferred to new owner and also you can get better resale value of car if you have an extended\nwarranty.\n\nWhy should I take EW if the company is already providing me standard insurance of 3 years?\n\nAns: Company provides standard insurance of 3 years/1,000,00 kms which ever comes earlier .\n\nFor ex: If your car will complete 1,000,00 kms in 2 years then standard Insurance will get lapsed in 2 years.\n\nAlso you will be getting better resale value if you have EW.\n\nCan I get an extended warranty after completion of the standard warranty? ( i.e. 3years or 1,00,000 kms\nwhichever comes earlier)?\n\nANS: No you cannot buy an Extended warranty after completion of standard warranty.\n\nWhy should I buy EW at the time of buying the car rather immediately before completion of standard\nWarranty?\n\nANS: Prices are dynamic, it will cost much lower at the time of buying the vehicle\n\nWhat are conditions to which EW does not apply?\n\nANS: This extended warranty shall not apply to:\n\na) Any vehicle which has been used for competition, rallies or racing or for any purposes other than what it\nwas designed for\n\nb) Any repairs or replacement arising from accidents or collision.\n\nc) Any defect or damage caused by misuse, negligence, abnormal use, insufficient care, vandalism, theft, riot,\nfire, flooding not limited to entry of water/fluids in the components resulting in engine seizure, hydrostatic\nlock, etc. or any external damages to the body/ components.\n\nd) Any damage as a result of usage of adulterated fuel/ lubricants/ oil/ coolant/ fluids/ polishing products or\nany fuel/ lubricants/ oil/ coolant/ fluids used other than those specified in the Owner\u2019s Manual and Service\nBooklet.\n\ne) Any vehicle which has been modified or altered, including without limitation, the installation of\nperformance accessories, enlargements of lights or any other external changes.\n\nf) Any vehicle on which parts or accessories not approved by Maruti Suzuki have been fitted and the damages\nto the body/components due to such fitment.\n\ng) Any vehicle which has not been operated in accordance with the operating instructions prescribed in the\nOwner\u2019s Manual and Service Booklet .\n\nh) Any vehicle in which the scheduled service inspections as prescribed in this Owner\u2019s Manual and Service\nBooklet has not been carried out.\n\ni) Any damage owing to the vehicle being assembled, disassembled, tampered, adjusted or repaired by any\nunauthorized dealer/ service station.\n\nj) Any damage or deterioration to the vehicle or its parts caused by airborne fallout, industrial fallout, acid\nrain, hail or hailstorm, windstorm, lightning or any other environmental factors, bird droppings, rodents bite/\nrat bite.\n\nk) Insignificant defects which do not affect the function of the vehicle including without limitation, sound,\nvibration and fluid seep etc.\n\nl) Any natural wear & tear including without limitation, ageing, wear & tear or deterioration such as\ndiscoloration, fading, deformation or blurring and fabric discoloration.\n\nm) Vehicles wherein domestic LPG gas/LPG Cylinder/CNG kits has been retrofitted.\n\nn) Corrosion, rusting of body parts and/ or components.\n\no) Any vehicle on which odometer has been changed unauthorisedly or odometer reading has been modified/\ntampered with/ or not matching with the service records.\n\np) The damage(s) caused to the vehicle being unattended despite knowledge that the defect exists and\nignorance by the owner/ user of the vehicle.\n\nq) Any damage(s) caused to the vehicle including battery/ tyre due to parking of the vehicle in idle condition\nfor long duration of time periods.\n\nr) Any vehicle on which any retro fitment is done which is not authorized and/ or type approved as per\nstandards prescribed by the relevant authority including but not limited to Automotive Industry Standards.\n\ns) Any vehicle on which the retro-fitment is such which directly or indirectly causes any damage to the vehicle\nor affects the functions of the vehicle in any manner whatsoever.\n\n9) Which components & services are not covered in EW?\n\nANS:\n\na) Normal maintenance service required, including without limitation, oil and fluid changes headlight aiming,\nfastener retightening, wheel balancing, wheel alignment and tyre rotation, cleaning of injectors, ignition\ntiming, clutch and valve clearance.\n\nb) The replacement of normal wear parts, including without limitation, bulbs, battery, tyres, tubes, spark plugs,\nbrake discs, brake shoes, brake drum, brake pads, belts, hoses, filters (all types) with or without sensors, wiper\narms/ wiper blades and brushes.\n\nc) Any seals and gasket replaced or refitted as a part of periodic scheduled maintenance services.\n\nd) Clutch disc, clutch pressure plate, catalytic converter, and muffler.\n\ne) Replacement of belts (timing belt, SHVS belt/ Alternator/ compressor/ water pump, etc.)\n\nf) Trims, wheel rims, wheel alloys, rubber & plastic parts, all body panels including, glass run, seat fabrics, roof\nlining, gear knob, steering wheel logo, all emblems, cup holder and door weather strips.\n\ng) Paintwork, bodywork and moldings, water/fluid entry into the vehicle or parts, corrosion of body parts,\nglass, key and interior trims.\n\nh) Lithium-ion battery & Motor Generator Unit for petrol vehicles.\n\n10)If I have EW Platinum, can I upgrade to EW solitare or EW Royal Platinum and What will be the cost?\n\nAND : Yes It can be upgraded\n\nOnly you have to pay the price difference between two variants\n\nSample scenarios in case customer denies to buy EW :\n\nScenario 1:\n\nCustomer: I don\u2019t want to purchase Extended warranty as per day running kms is very less and standard\nwarranty already covers up to 100000 kms\n\nBot reply: Standard warranty covers up to 3 years or 100000 kms which ever comes earlier . So even if total\nkms covered is less than 100000 kms in 3 yaers and your car is about to be 3 years old . Your standard\nwarranty will expire after 3 years from car sale date.\n\nScenario 2:\n\nCustomer: I don\u2019t want to purchase EW because I am planning to sell car within the period of standard\nwarranty\n\nBot reply: Extended warranty is transferrable, you can transfer it to next owner of car. Also you will get a\nbetter resale value of car\n\nScenario 3:\n\nCustomer: I don\u2019t want to purchase EW as for me price is on higher side\n\nBot reply : You can pay the price using 6 Easy EMIs with your credit card\n\nScenario 4:\n\nCustomer: I don\u2019t want to purchase EW as of now and will purchase after the expiry of standard warranty.\n\nBot reply: You cannot purchase EW after expiry of standard warranty, it can be purchased within period of\nstandard warranty\n\nCCP FAQs\n\nWhat is customer convenience Package (CCP) ?\n\nANS: Customer Convenience Package (\"CCP\") is a coverage provided by Maruti Suzuki India Limited (\"Maruti\nSuzuki\") which covers repair/replacement cost of engine or its allied part(s) which gets damaged owing to\nissues/ defect arising due to water entry causing hydro lock or failure of engine parts and/or due to use of\nadulterated fuel and issue/defect arising due to rodent or insect bite beyond the reasonable control of the\ncustomer, which are not covered under warranty or extended warranty.\n\nWhat are the different types of CCP ?\n\nANS: For Customer having EW :\nCCP GOLD can be purchased within 1 year and 9 months or mileage of 25 000 km from the date of vehicle sale\nfor CCP 1 year package.\n\nCCP PLATINUM can be purchased within 1 year and 9 months or mileage of 45 000 km from the date of\nvehicle sale for CCP 2 year package.\n\nCCP ROYAL PLATINUM can be purchased within 1 year and 9 months or mileage of 60 000 from the date of\nvehicle sale for CCP 3 year package.\n\nFor customers not having EW can purchase N-EW CCP Instead within 9 months from the date of vehicle sale.\n\nWhat does the CCP plan of Maruti Suzuki offers?\n\nANS:\n\ni) CCP hydro and rodent protect :- for a period of 1 year, 2 years and 3 years which covers repairs for\nhydrostatic part failure and damages caused due to rodent or insect bite beyond the reasonable control of the\ncustomer.\n\nii) CCP fuel and rodent protect :- for a period of 1 year, 2 years and 3 years which covers repairs for fuel\nadulteration failure and damages caused due to rodent or insect bite beyond the reasonable control of the\ncustomer.\n\niii) CCP plus which covers repairs for hydrostatic failure, fuel adulteration failure and damage due to rodent or\ninsect bite beyond the reasonable control of the customer are also available for a period of 1 year, 2 year and\n3 year policy options.\n\nWhy should I buy CCP if I have already taken additional protection in Insurance?\n\nANS: Insurance do not cover delayed hydrostatic lock but CCP does .\n\nCan I buy a CCP If I do not have EW?\n\nANS: Yes N-EW CCP applicable for 1 year, 2 years and 3 years can be purchased if vehicle does not have\nextended warranty.\n\nCan CCP & N-EW CCP can be renewed?\n\nANS: Yes, CCP 1 year and CCP 2 years packages can be renewed for additional 1 more year till vehicle is in\nwarranty (36 months or 100 000 km) from the date of sale).N-EW CCP can't be renewed.\n\nWhich packages of CCP can be renewed?\n\nANS: CCP 1 year and 2 years Packages can be renewed for additional 1 year or 40 000 km with following\npackage options:\nCCP Gold - Plus & Rodent Protect\n\nCCP Gold - Hydro & Rodent Protect\n\nCCP Gold - Fuel & Rodent Protect\n\nHow much will CCP cost me for my Car ?\n\nANS: It varies as per different car variants.\n\nWhat is the CCP coverage applicability timelines ?\n\nANS:\n\na. If CCP is purchased within 15 days of the vehicle sale invoice date - Benefits can be availed for period of 1\nyear, 2 years or 3 year as per the CCP terms mentioned in the policy.\n\nb. If CCP is purchased after 15 days of the vehicle sale invoice date - Benefits can be availed after completion of\n90 days of purchase of the CCP for a period 1 year, 2 years or 3 year as per CCP terms mentioned in policy.\n\nNOTE: Eligibility period is duly mentioned in the certificate and claims would be accepted during the said\ntimeline.\n\nAre consumables like engine oil and coolant are covered under CCP in case of any breakdown?\n\nANS: Consumables like Coolant, Engine oil etc.to address failures/damage arising solely out of water entry in\nthe engine or failure of engine parts due to use of adulterated fuel shall be covered under the CCP as per\napplicable packages. However, discretion of Maruti Suzuki shall be final and binding in this regard.\n\nIn case of breakdown what should a customer do?\n\nANS: The customer must bring the vehicle without delay to the nearest MSIL authorized workshop at his own\ncost to effect repair and to apprise the workshop about the CCP availability.\n\nDoes EMI option available in buying CCP?\n\nANS: Easy EMI is a financing option offered by Maruti Suzuki that allows you to purchase extended warranty\nor Customer Convenience Package without paying any interest on the EMI. This means you can spread the cost\nof the extended warranty or Customer Convenience Package over 3 or 6 monthly instalments without incurring\nany additional interest charges.\n\nNOTE: EMI option is available with Credit cards only\n\nWhat is the Minimum transaction amount required for Easy EMI with different banks?\n\nANS:\n\nIssuing Banks (Credit Card)\n\nMinimum Transaction Amount (for 3- and 6- months EMI tenure) in INR\n\nHDFC Bank\n\n1000\n\nState Bank Of India\n\n3000\n\nKotak Mahindra Bank\n\n2500\n\nICICI Bank\n\n1500\n\nAxis Bank\n\n2500\n\nHSBC Bank\n\n2000\n\nStandard Chartered Bank\n\n2500\n\nRatnakar Bank Limited\n\n2500\n\nYes Bank\n\n2500\n\nBank Of Baroda\n\n2500\n\nIndusInd Bank\n\n2000\n\nAmex\n\n5000\n\nIDBI Bank\n\n3000\n\n14) If a customer already has 2 year CCP package, can he purchase 3 year CCP Plan?\n\nAns : If 3 year CCP Hydro is already there, then 3 year CCP Fuel can be purchased and vice versa.\n\nBut, 3 year CCP Hydro cannot be purchased, if 2 year Hydro is already available.\n\n15) Is wrong fuel entry in vehicle cases covered in CCP 3 year?\n\nAns : Cases of wrong fuel filling (Diesel instead of Petrol & Vice Versa) will not be covered under any of CCP\npackage including CCP 3 year.\n\nList of languages in which bot would be interacting\n\nEnglish\n\nHindi\n\nBengali\n\nMarathi\n\nTelugu\n\nTamil\n\nGujarati\n\nKannada\n\nOdia\n\nMalayalam\n\nPunjabi\n\nAssamese\n\nSample scenarios in case customer denies to buy CCP\n\nScenario 1:\n\nCustomer: I don\u2019t want to purchase CCP as price is on higher side for me.\n\nBot reply: You can pay the price using 6 Easy EMIs with your credit card\n\nScenario 2:\n\nCustomer: I don\u2019t want to purchase CCP because I am not able to understand the benefits of CCP properly.\n\nBot reply: Customer Convenience Package (\"CCP\") is a coverage provided by Maruti Suzuki India Limited\n(\"Maruti Suzuki\") which covers repair/replacement cost of engine or its allied part(s) which gets damaged\nowing to issues/ defect arising due to water entry causing hydro lock or failure of engine parts and/or due to\nuse of adulterated fuel and issue/defect arising due to rodent or insect bite beyond the reasonable control of\nthe customer, which are not covered under warranty or extended warranty.\n\nScenario 3:\n\nCustomer: I don\u2019t want to purchase CCP as I have already taken additional hydro protection in Insurance.\n\nBot reply: Insurance do not cover delayed hydrostatic lock but CCP does .\n\n\n-----END OF DOCUMENT ewccpknowledgebank1 \n\n\n\nDocument id - ewfaqs : \n**Q1. What is Extended warranty?**\n\nWhen you buy a Maruti Suzuki car, the company offers you warranty up to 3 years or 1 00\n000 km (whichever comes first). However, you can extend this coverage for up to 6 years\nor 1 60 000 km by purchasing extended warranty for your car.\n\n**Q2. How many extended warranty plans does Maruti Suzuki offer?**\n\nYou can choose from 3 extended warranty plans for your car. The Solitaire offers\ncoverage up to 6 years or 1 60 000 km*; Royal Platinum offers coverage up to 5 years of 1\n40 000 km*; and the Platinum extends the coverage up to 4 years or 1 20 000 km*.\n\n**Q3. How much will the extended warranty for my car cost me?**\n\nThe cost of extended warranty varies with every model variant and depends on the\ncurrent running of the vehicle. You can get an estimated cost for extended warranty on\nthe Maruti Suzuki Service web page.\n\n**Q4. Are any high value parts covered under the warranty?**\n\nYes. The warranty offers coverage for your car\u2019s high value parts, including the highpressure pump, compressor, ECM, turbocharger assembly, steering assembly, self\nassembly, strut, and the engine.\n\n**Q5. For warranty repairs, can I only visit the dealership from where I purchased the car?**\n\nNo, as long as you visit an authorized Maruti Suzuki Service centre, you can claim\nwarranty repairs at any dealership, in any location across India.\n\n**Q6. Will my car\u2019s primary warranty, extended warranty, Customer Convenience Package**\n(CCP), or Maintenance Cost Protection (MCP) expire when I sell my car?\n\nNo, all the products and services by Maruti Suzuki Service can be transferred to the next\nlegitimate owner of the vehicle.\n\n**Q7: Can I cancel my extended warranty?**\n\nA: Yes, you can cancel your extended warranty until your vehicle is under the primary\nwarranty. However, there will be an administrative fee of Rs 200 or 10% of the extended\nwarranty basic price (whichever is higher).\n\n**Q8: How do I cancel my extended warranty?**\n\nA: To cancel your extended warranty, you must visit the nearest Maruti Suzuki dealership\nand submit a cancellation inquiry.\n\n\n-----\n\n**QG: Will I be charged a fee for cancelling my extended warranty?**\n\nA: Yes, there will be an administrative fee of Rs 200 or 10% of the extended warranty\nbasic price (whichever is higher).\n\n**Q10: Will I receive a refund for the taxes paid on my extended warranty?**\n\nA: No, the tax amount collected during the purchase of the extended warranty will not\nbe refunded.\n\n**Q11: Can I cancel a converted extended warranty policy (Platinum to Royal**\n**Platinum, Royal Platinum to Platinum, or Platinum to Solitaire)?**\n\nA: No, converted policies cannot be cancelled under any circumstances.\n\n**Q12: What happens to my \"Easy EMI\" option if I cancel my extended warranty?**\n\nA: If you opted for the \"Easy EMI\" option and cancel your extended warranty, you need to\ncontact your respective bank or their call centre to cancel the EMI. Maruti Suzuki is\ncommitted to providing excellent service but kindly note that EMI transactions are\nhandled directly by the respective financial institutions. For any concerns or issues\nrelated to EMI payments, please reach out to your finance provider for assistance.\n\n**Q13: Will I be responsible for any costs associated with cancelling my \"Easy EMI\"**\n**option?**\n\nA: Yes, you may be responsible for interest costs, convenience charges, or other related\nfees if you cancel your \"Easy EMI\" option.\n\n**Q14: How long will it take to receive a refund for my cancelled extended warranty?**\n\nA: If you paid for your extended warranty online, the refund process may take up to 12\nworking days.\n\n**Q15: What if I don't receive my refund within the specified timeframe?**\n\nA: If you haven't received your refund within 12 working days, please contact Maruti\nSuzuki customer service for assistance.\n\n**What is Easy EMI?**\n\nA: Easy EMI is a financing option offered by Maruti Suzuki that allows you to purchase\nextended warranty or Customer Convenience Package without paying any interest on\nthe EMI. This means you can spread the cost of the extended warranty or Customer\nConvenience Package over 3 or 6 monthly instalments without incurring any additional\ninterest charges.\n\n\n-----\n\n**What is the minimum transaction amount required for Easy EMI with different**\n**banks?**\n\nA: Please refer to the following table for the minimum transaction amount required for\neach bank based on the tenure. The information provided in the table is indicative and\n_may vary depending on the bank\u2019s policies and terms and conditions._\n\n**Minimum Transaction**\n\n**Issuing Banks (Credit Card)** **Amount (for 3- and 6-**\n\n**months EMI tenure)**\nHDFC Bank 1000\nState Bank of India 3000\nKotak Mahindra Bank 2500\nICICI Bank 1500\nAxis Bank 2500\nHSBC Bank 2000\nStandard Chartered Bank 2500\nRatnakar bank Limited 2500\nYes bank 2500\nBank Of Baroda 2500\nIndusInd Bank 2000\nAmex 5000\nIDBI Bank 3000\n\n|Issuing Banks (Credit Card)|Minimum Transaction Amount (for 3- and 6- months EMI tenure)|\n|---|---|\n|HDFC Bank|1000|\n|State Bank of India|3000|\n|Kotak Mahindra Bank|2500|\n|ICICI Bank|1500|\n|Axis Bank|2500|\n|HSBC Bank|2000|\n|Standard Chartered Bank|2500|\n|Ratnakar bank Limited|2500|\n|Yes bank|2500|\n|Bank Of Baroda|2500|\n|IndusInd Bank|2000|\n|Amex|5000|\n|IDBI Bank|3000|\n\n\n-----END OF DOCUMENT ewfaqs \n\n\n\nDocument id - revised_ew_terms_and_conditions_19thjune : \n**Maruti Suzuki Extended Warranty Obligation:**\n\nIf any defect(s) should be found in the Maruti Suzuki vehicle within the extended warranty\ncoverage period in the electrical/mechanical part, Maruti Suzuki\u2019s only obligation is to repair\nor replace at its sole discretion the part shown to be defective, with a new part or the\nequivalent at no cost to the owner for parts or labour, when Maruti Suzuki acknowledges that\nsuch a defect is attributable to faulty material or workmanship at the time of manufacture.\nSuch defective parts, which have been replaced, shall become the property of Maruti Suzuki.\n\nThe owner is responsible for any repair or replacements that are not covered by this\nextended warranty.\n\nExtended Warranty is subject to the following terms & conditions:\n\n1. Extended Warranty registration form & certificate of extended warranty registration\n\nThe Extended warranty registration form & the certificate of extended warranty registration\nforms a part of contract between Maruti Suzuki India Limited and the owner of the extended\nwarranty of the vehicle as per the details mentioned on the extended warranty certificate.\n\n**2.** **Limitations:**\n\nThis extended warranty shall not apply to:\n\na) Any vehicle which has been used for competition, rallies or racing or for any\n\npurposes other than what it was designed for.\n\nb) Any repairs or replacement arising from accidents or collision.\n\nc) Any defect or damage caused by misuse, negligence, abnormal use, insufficient\n\ncare, vandalism, theft, riot, fire, flooding not limited to entry of water/fluids in the\ncomponents resulting in engine seizure, hydrostatic lock, etc. or any external\ndamages to the body/ components.\n\nd) Any damage as a result of usage of adulterated fuel/ lubricants/ oil/ coolant/ fluids/\n\npolishing products or any fuel/ lubricants/ oil/ coolant/ fluids used other than those\nspecified in the Owner\u2019s Manual and Service Booklet.\n\ne) Any vehicle which has been modified or altered, including without limitation, the\n\ninstallation of performance accessories, enlargements of lights or any other external\nchanges.\n\nf) Any vehicle on which parts or accessories not approved by Maruti Suzuki have been\n\nfitted and the damages to the body/components due to such fitment.\n\ng) Any vehicle which has not been operated in accordance with the operating\n\ninstructions prescribed in the Owner\u2019s Manual and Service Booklet\n\nh) Any vehicle in which the scheduled service inspections as prescribed in this Owner\u2019s\n\nManual and Service Booklet has not been carried out.\n\ni) Any damage owing to the vehicle being assembled, disassembled, tampered,\n\nadjusted or repaired by any unauthorized dealer/ service station.\n\n\n-----\n\nj) Any damage or deterioration to the vehicle or its parts caused by airborne fallout,\n\nindustrial fallout, acid rain, hail or hailstorm, windstorm, lightning or any other\nenvironmental factors, bird droppings, rodents bite/ rat bite.\n\nk) Insignificant defects which do not affect the function of the vehicle including without\n\nlimitation, sound, vibration and fluid seep etc.\n\nl) Any natural wear & tear including without limitation, ageing, wear & tear or\n\ndeterioration such as discoloration, fading, deformation or blurring and fabric\ndiscoloration.\n\nm) Vehicles wherein domestic LPG gas/LPG Cylinder/CNG kits has been retrofitted.\n\nn) Corrosion, rusting of body parts and/ or components.\n\no) Any vehicle on which odometer has been changed unauthorisedly or odometer\n\nreading has been modified/ tampered with/ or not matching with the service records.\n\np) The damage(s) caused to the vehicle being unattended despite knowledge that the\n\ndefect exists and ignorance by the owner/ user of the vehicle.\n\nq) Any damage(s) caused to the vehicle including battery/ tyre due to parking of the\n\nvehicle in idle condition for long duration of time periods.\n\nr) Any vehicle on which any retro fitment is done which is not authorized and/ or type\n\napproved as per standards prescribed by the relevant authority including but not\nlimited to Automotive Industry Standards.\n\ns) Any vehicle on which the retro-fitment is such which directly or indirectly causes any\n\ndamage to the vehicle or affects the functions of the vehicle in any manner\nwhatsoever.\n\n**3.** **List of services and components not covered:**\n\nThis is limited list of items not covered:\na) Normal maintenance service required, including without limitation, oil and fluid changes\nheadlight aiming, fastener retightening, wheel balancing, wheel alignment and tyre rotation,\ncleaning of injectors, ignition timing, clutch and valve clearance.\n\nb) The replacement of normal wear parts, including without limitation, bulbs, battery, tyres,\ntubes, spark plugs, brake discs, brake shoes, brake drum, brake pads, belts, hoses, filters\n(all types) with or without sensors, wiper arms/ wiper blades and brushes.\n\nc) Any seals and gasket replaced or refitted as a part of periodic scheduled maintenance\nservices.\n\nd) Clutch disc, clutch pressure plate, catalytic converter, and muffler.\n\n\n-----\n\ne) Replacement of belts (timing belt, SHVS belt/ Alternator/ compressor/ water pump, etc.)\n\nf) Trims, wheel rims, wheel alloys, rubber & plastic parts, all body panels including, glass\nrun, seat fabrics, roof lining, gear knob, steering wheel logo, all emblems, cup holder and\ndoor weather strips.\n\ng) Paintwork, bodywork and moldings, water/fluid entry into the vehicle or parts, corrosion of\nbody parts, glass, key and interior trims.\n\nh) Lithium-ion battery & Motor Generator Unit for petrol vehicles.\n\n**4.    Cancellation of EW Policy**\n\na) Any Extended Warranty if required to be cancelled, can be done till the vehicle is under\nprimary warranty by Extended Warranty selling dealer. There will be an administrative fee of\nRs 200/- or 10% of Extended Warranty basic price (whichever is higher) for policy\ncancellation. Also, tax amount collected during Extended Warranty will not be refunded.\n\nb) Any converted policy (Platinum to Royal Platinum, Royal Platinum or Platinum to Solitaire)\nwill not be cancelled under any circumstances.\n\n\n-----END OF DOCUMENT revised_ew_terms_and_conditions_19thjune \n\n\n"""
    va.create_session(session_id, {
        'agent': {'prompt': prompt_shivam},
        'queue': output_queue,
        'response_channel': 'AUDIO', #TEXT, AUDIO
    })
    
    # asyncio.create_task(va.listen_audio())
    # import time
    # time.sleep(10)
    # asyncio.create_task(va.play_audio())

    # with (
    #     va, 
    #     asyncio.taskgroups
    # )
    
    await asyncio.gather(va.listen_audio(), va.play_audio())
    # asyncio.c()
    # await va.listen_audio()
    # await va.play_audio()
    # import pyaudio, wave
    # p = pyaudio.PyAudio()

    # CHUNK = 1024
    # FORMAT = pyaudio.paInt16
    # CHANNELS = 2
    # RATE = 16000
    # RECORD_SECONDS = 5
    # stream = p.open(format=FORMAT,
    #             channels=CHANNELS,
    #             rate=RATE,
    #             input=True,
    #             frames_per_buffer=CHUNK) 
    # count = 0
    # wf = wave.open('shivam_rawat_recording.wav', 'wb')
    # wf.setframerate(24000)
    # wf.setnchannels(1)
    # wf.setsampwidth(2)
    
    # def run():
    #     count=0
    #     for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    #         audio_byte = stream.read(CHUNK)
    #         print(type(audio_byte))
    #     # for i in range(0, len(audio_bytes), 5000):
    #         # audio_byte = audio_bytes[i:i+5000]
    #         print('push')
    #         wf.writeframes(audio_byte)
    #         va.push_audio(session_id, {
    #             'message_id': 'shivam-test-11',
    #             'payload': {'sequence': count, 'audio_byte': audio_byte}
    #         })
    #         count = count+1
    # va.push_audio(session_id, {
    #         'message_id': 'shivam-test-11',
    #         'payload': {'sequence': 0, 'audio_byte': audio_bytes}
    #     })
    # threading.Thread(target=run())
    # print('Audio pushed')

    # await asyncio.sleep(5)

    # va.end_session(session_id)
    # print('end_session scheduled')

    # session = SessionRegistry.get_session(session_id)
    # if session and 'task' in session:
    #     try:
    #         await session['task']
    #     except Exception:
    #         pass
    
    # import wave
    # wf = wave.open('shivam_rawat_shivam.wav', 'wb')
    # wf.setframerate(24000)
    # wf.setnchannels(1)
    # wf.setsampwidth(2)
    # # {'shivam_test': {'shivam-test-11': {'sequence_number': '0', 'agent_response':
    # while not output_queue.empty():
    #     data = await output_queue.get()
    #     if data is None:
    #         break
        
    #     message_payload = data.get('shivam_test')
    #     sequence_number = message_payload.get('shivam-test-11').get('sequence_number')
    #     agent_response = message_payload.get('shivam-test-11').get('agent_response')
        
    #     print(type(message_payload))
    #     print(type(agent_response))
    #     print(sequence_number)
    #     wf.writeframes(agent_response)
    
    # wf.close()
if __name__ == '__main__':
    asyncio.run(main())
