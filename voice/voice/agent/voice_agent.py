"""
Voice Agent
AI-driven conversational engine for real-time understanding and response generation
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import asyncio
import typing
from gryd_worker import gryd_helpers as hp
try:
    from .gemini import GEMINIAPI
except:
    from gemini import GEMINIAPI
from multiprocessing import Queue
import logging
import utils
logger = utils.get_logger(__name__)

AVAILABLE_AGENT_TYPE = {
    'gemini': GEMINIAPI
}

class VoiceAgentError(hp.GrydError):
    pass

class TestVoiceAgent:
    def __init__(self, session_id:str, input_queue:Queue, output_queue: Queue , system_prompt:str, timeout:int, agent_type:str = 'gemini', **agent_param):
        client_class = AVAILABLE_AGENT_TYPE.get(agent_type)
        if not client_class:
            raise  VoiceAgentError(f'No Agent available of type: {agent_type}')
        
        if not session_id or not session_id.strip():
            raise VoiceAgentError(f'Session id is required to stream the response.')
        
        if not output_queue:
            raise VoiceAgentError(f'Output Queue is required to stream the response.')
        
        self.server_timeout = timeout or 5 
        if self.server_timeout <= 0 or self.server_timeout > 15:
            raise VoiceAgentError(f"Timeout should be in the range of 1sec to 15 sec, received: {self.server_timeout}")
        
        self.session_id = session_id
        self.input_queue = input_queue
        self.output_queue = output_queue
        
        self.agent_type=agent_type
        self.prompt = system_prompt
        self.sequence_number = 0
        
        self.running = True
        self.client = client_class(input_queue, output_queue, system_prompt, self.server_timeout, **agent_param)
        # self.create_session()
        
    async def create_session(self) -> None:
        # asyncio.run(self.client.create_session(self.session_id))
        await self.client.create_session(self.session_id)
        logger.info(f"Started agent session {self.session_id} for agent_type={self.agent_type}")

    
    # def receive_and_push_audio()
    # def push_audio(self, message_id:str, sequence_number, audio_byte:typing.Union[bytes, None]=None):
    #     try:
    #         sequence_number = int(sequence_number)
    #     except Exception:
    #         logger.warning('No sequence number set. Using Default sequence number.')
    #         sequence_number = 0
        
    #     message_sequence_number = f'{message_id}----{sequence_number}----{hp.time()}'
    #     payload_audio = {
    #         message_sequence_number : audio_byte
    #     }
        
    #     try:
    #         if audio_byte:
    #             logger.info(f'Pushed audio to input manager of len {len(audio_byte)}')
    #         else:
    #             logger.info(f'Sending sentinel to input manager.')
    #         self.input_queue.put_nowait(payload_audio)
            
    #     except Exception as e:
    #         logger.warning(f'Failed to put audio into input manager. For detailed info Check traceback logs')
    #         import traceback
    #         traceback.print_exc()

    # def stream_response(self, media_params: dict):
    #     message_id = media_params.get('message_id')
    #     if not message_id  or not message_id.strip():
    #         raise VoiceAgentError(f'Message id is required to stream the response')    
        
    #     session_id = media_params.get('session_id')
        
    #     if not session_id or not session_id.strip():
    #         session_id = self.session_id
            
    #     if session_id!=self.session_id:
    #         raise VoiceAgentError(f'Session id miss matched. Check the intialized session_id')
        
    #     self.sequence_number = media_params.get('sequence_number', self.sequence_number)
            
    #     audio_data = media_params.get('audio_data')
    #     self.push_audio(message_id, self.sequence_number, audio_data)
    #     self.sequence_number = self.sequence_number + 1
        
    def end_session(self) -> None:
        try:
            self.client.end_session(self.session_id)
            logger.info(f"Scheduled end of session {self.session_id}")
        except Exception as exc:
            logger.warning(f"Failed to end session {self.session_id}")
            import traceback
            traceback.print_exc()
            raise
        
async def main():
    import multiprocessing
    output_queue = multiprocessing.Queue()
    input_queue = multiprocessing.Queue()
    print('shivam start')

    client = TestVoiceAgent('shivam_rawat_123', input_queue, output_queue,'have a talk with shivam', 4)

    await client.create_session()
    print('shivam end')

    with open('voice.wav', 'rb') as f:
        audio_byte = f.read()

    for i in range(0, len(audio_byte), 5000):
        audio_content = audio_byte[i:i+5000]
        input_queue.put({
            'message_id': 'shivam',
            'audio_data': audio_content,
            'session_id': 'shivam_rawat_123'
        })

    client.end_session()

    import wave
    wf = wave.open('test_agent_flow.wav', 'wb')
    wf.setframerate(24000)
    wf.setnchannels(1)
    wf.setsampwidth(2)
    print("Waiting for agent responses...")

    loop = asyncio.get_running_loop()

    while True:
        # mp.Queue.get is blocking; run it in a thread
        data = await loop.run_in_executor(None, output_queue.get)

        if data is None:
            print("Received end-of-stream sentinel from worker")
            break

        if isinstance(data, dict) and "error" in data:
            raise RuntimeError(f"Voice worker failed: {data['error']}")

        if not isinstance(data, dict):
            print("Unexpected payload:", data)
            continue

        if data.get("session_id") != 'shivam_rawat_123':
            print("Payload for different session:", data)
            continue

        if data.get("message_type") != "audio_output":
            print("Non-audio payload:", data)
            continue

        audio_bytes = data.get("audio_data")
        if not audio_bytes:
            continue

        msg_id = data.get("message_id")
        print(f"Writing chunk from message_id={msg_id}, len={len(audio_bytes)}")
        wf.writeframes(audio_bytes)

    wf.close()

if __name__ == '__main__':
    asyncio.run(main())


# """
# Voice Agent
# AI-driven conversational engine for real-time understanding and response generation
# """
# import sys, os
# sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# import asyncio
# import random
# from typing import Optional, List, Dict, Any
# from dataclasses import dataclass

# import logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# @dataclass
# class GenerationResult:
#     success: bool
#     message_id: str
#     response_text: Optional[str] = None
#     fillers: Optional[List[str]] = None
#     needs_escalation: bool = False


# class VoiceAgent:
#     """AI conversational engine with streaming response generation"""
    
#     def __init__(self, session_id: str, input_queue: asyncio.Queue, 
#                  output_queue: asyncio.Queue, system_prompt: str):
#         self.session_id = session_id
#         self.input_queue = input_queue
#         self.output_queue = output_queue
#         self.system_prompt = system_prompt
        
#         self.running = True
#         self.conversation_history: List[Dict[str, str]] = []
        
#         # Configuration
#         self.max_generation_attempts = 3
#         self.stream_delay = 0.2  # Delay between chunks for realistic streaming
        
#     async def call_llm_api(self, user_message: str, is_interruption: bool = False) -> GenerationResult:
#         """
#         Call LLM API for response generation
#         In production: Integrate with OpenAI, Anthropic Claude, or other LLM APIs
#         with streaming support
#         """
        
#         # Build conversation context
#         messages = [
#             {"role": "system", "content": self.system_prompt}
#         ]
        
#         # Add conversation history
#         for msg in self.conversation_history[-10:]:  # Last 10 messages for context
#             messages.append(msg)
        
#         # Add current user message
#         messages.append({"role": "user", "content": user_message})
        
#         try:
#             # Simulate LLM API call with streaming
#             # In production: Use actual API with streaming
#             logger.info(f"Calling LLM API for: {user_message[:50]}...")
            
#             await asyncio.sleep(0.5)  # Simulate API latency
            
#             # Simulate response based on context
#             response = await self._simulate_llm_response(user_message, is_interruption)
            
#             return GenerationResult(
#                 success=True,
#                 message_id="",  # Will be set by caller
#                 response_text=response
#             )
            
#         except Exception as e:
#             logger.error(f"LLM API error: {e}")
            
#             # Return failure with fillers
#             return GenerationResult(
#                 success=False,
#                 message_id="",
#                 fillers=self.get_fallback_fillers(),
#                 needs_escalation=True
#             )
    
#     async def _simulate_llm_response(self, user_message: str, is_interruption: bool) -> str:
#         """
#         Simulate LLM response
#         In production: Replace with actual API streaming
#         """
        
#         message_lower = user_message.lower()
        
#         # Handle interruption acknowledgment
#         if is_interruption:
#             return "Of course, let me help you with that."
        
#         # Simple pattern matching for demo
#         if "suv" in message_lower:
#             return "We have several excellent SUV models. Our most popular are the Explorer, the Expedition, and the Edge. The Explorer offers great fuel efficiency and family-friendly features. Would you like to know more about any specific model?"
            
#         elif "sedan" in message_lower:
#             return "Our sedan lineup includes the Fusion, Taurus, and Focus. Each offers unique benefits. The Fusion is perfect for daily commutes with excellent mileage. What's your primary use case for the vehicle?"
            
#         elif "test drive" in message_lower or "schedule" in message_lower:
#             return "I'd be happy to schedule a test drive for you! We have availability this week. Which day works best for you - weekday or weekend?"
            
#         elif "price" in message_lower or "cost" in message_lower:
#             return "Pricing varies by model and trim level. Our SUVs range from $28,000 to $55,000. Would you like me to provide specific pricing for a model you're interested in?"
            
#         elif "hello" in message_lower or "hi" in message_lower:
#             return "Hello! Thank you for calling. I'm here to help you find the perfect vehicle. What are you looking for today?"
            
#         else:
#             return "That's a great question. Let me provide you with the information you need. Our dealership offers comprehensive services and we're committed to finding the right solution for you. Could you tell me a bit more about what you're looking for?"
    
#     def get_fallback_fillers(self) -> List[str]:
#         """Get fallback fillers when generation fails"""
#         return [
#             "Let me look that up for you.",
#             "I'm checking on that information.",
#             "Give me just a moment.",
#             "I want to make sure I give you accurate information."
#         ]
    
#     async def stream_response(self, message_id: str, response_text: str):
#         """
#         Stream response in chunks to output queue
#         Simulates real-time text-to-speech streaming
#         """
        
#         # Send start signal
#         await self.output_queue.put({
#             "type": "start",
#             "message_id": message_id
#         })
        
#         # Split response into sentences for more natural streaming
#         sentences = response_text.replace('!', '.').replace('?', '.').split('.')
#         sentences = [s.strip() + '.' for s in sentences if s.strip()]
        
#         for sentence in sentences:
#             # Send chunk
#             await self.output_queue.put({
#                 "type": "chunk",
#                 "message_id": message_id,
#                 "text": sentence
#             })
            
#             logger.info(f"[{message_id}] Streamed: {sentence}")
            
#             # Delay for realistic streaming
#             await asyncio.sleep(self.stream_delay)
        
#         # Send completion signal
#         await self.output_queue.put({
#             "type": "complete",
#             "message_id": message_id
#         })
        
#         logger.info(f"[{message_id}] Response streaming complete")
    
#     async def generate_response(self, user_message, message_id: str, is_interruption: bool = False):
#         """Generate and stream response for user message"""
        
#         logger.info(f"[{message_id}] Generating response for: {user_message.transcript}")
        
#         # Call LLM
#         result = await self.call_llm_api(user_message.transcript, is_interruption)
#         result.message_id = message_id
        
#         if result.success and result.response_text:
#             # Add to conversation history
#             self.conversation_history.append({
#                 "role": "user",
#                 "content": user_message.transcript
#             })
#             self.conversation_history.append({
#                 "role": "assistant",
#                 "content": result.response_text
#             })
            
#             # Stream response
#             await self.stream_response(message_id, result.response_text)
            
#         else:
#             # Generation failed - send fillers and escalate
#             logger.warning(f"[{message_id}] Generation failed, sending fillers")
            
#             # Send random filler
#             filler = random.choice(result.fillers)
#             await self.output_queue.put({
#                 "type": "filler",
#                 "message_id": message_id,
#                 "text": filler
#             })
            
#             if result.needs_escalation:
#                 # Notify Agent Orchestrator
#                 await self.escalate_to_orchestrator(message_id, user_message.transcript)
    
#     async def escalate_to_orchestrator(self, message_id: str, user_query: str):
#         """
#         Escalate to Agent Orchestrator when unable to generate response
#         In production: Call orchestrator service
#         """
#         logger.info(f"[{message_id}] Escalating to Agent Orchestrator")
        
#         # Simulate orchestrator handling
#         await asyncio.sleep(1)
        
#         # Orchestrator triggers filler generator
#         orchestrator_filler = "I apologize for the delay. Let me connect you with someone who can better assist you with that specific question."
        
#         await self.output_queue.put({
#             "type": "filler",
#             "message_id": message_id,
#             "text": orchestrator_filler
#         })
        
#         # Trigger handover
#         await self.output_queue.put({
#             "type": "handover",
#             "session_id": self.session_id,
#             "message": "Connecting you to a specialist now."
#         })
    
#     async def run(self):
#         """Main run loop for Voice Agent"""
#         logger.info(f"Voice Agent started for session {self.session_id}")
        
#         try:
#             while self.running:
#                 try:
#                     # Poll input queue for user messages
#                     user_message = await asyncio.wait_for(
#                         self.input_queue.get(),
#                         timeout=1.0
#                     )
                    
#                     # Generate response
#                     await self.generate_response(
#                         user_message,
#                         user_message.message_id,
#                         user_message.is_interruption
#                     )
                    
#                 except asyncio.TimeoutError:
#                     # No messages in queue
#                     continue
                    
#         except Exception as e:
#             logger.error(f"Error in Voice Agent: {e}")
#         finally:
#             logger.info("Voice Agent stopped")


# # Test Voice Agent
# async def test_voice_agent():
#     from input_manager import UserMessage
    
#     input_queue = asyncio.Queue()
#     output_queue = asyncio.Queue()
    
#     system_prompt = """You are a helpful automotive sales assistant.
#     Be friendly, informative, and help customers find the right vehicle."""
    
#     agent = VoiceAgent("test_session_001", input_queue, output_queue, system_prompt)
    
#     # Start agent
#     agent_task = asyncio.create_task(agent.run())
    
#     # Simulate user messages
#     async def simulate_user():
#         test_messages = [
#             "Hello, I'm interested in buying an SUV",
#             "What's the price range?",
#             "Can I schedule a test drive?",
#         ]
        
#         for transcript in test_messages:
#             await asyncio.sleep(2)
            
#             message = UserMessage(
#                 message_id=f"msg_{len(test_messages)}",
#                 session_id="test_session_001",
#                 audio_data=transcript.encode(),
#                 transcript=transcript,
#                 timestamp=asyncio.get_event_loop().time()
#             )
            
#             await input_queue.put(message)
    
#     # Monitor output
#     async def monitor_output():
#         while agent.running:
#             if not output_queue.empty():
#                 item = await output_queue.get()
#                 logger.info(f"[OUTPUT] {item}")
#             await asyncio.sleep(0.1)
    
#     await asyncio.gather(
#         simulate_user(),
#         monitor_output(),
#         return_exceptions=True
#     )
    
#     await asyncio.sleep(10)
#     agent.running = False
#     await agent_task


# if __name__ == "__main__":
#     asyncio.run(test_voice_agent())