"""
Output Manager
Sends AI or human agent's response stream back to voice provider
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import asyncio
import logging
from enum import Enum
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OutputMode(Enum):
    AI_AGENT = "ai_agent"
    HUMAN_AGENT = "human_agent"
    FILLER = "filler"


class OutputManager:
    """Manages outgoing audio stream to voice provider"""
    
    def __init__(self, session_id: str, output_queue: asyncio.Queue):
        self.session_id = session_id
        self.output_queue = output_queue
        
        self.mode = OutputMode.AI_AGENT
        self.current_message_id: Optional[str] = None
        self.is_streaming = False
        self.running = True
        
        # For message tracking
        self.message_buffer: Dict[str, list] = {}
        
    async def send_to_voice_provider(self, audio_chunk: bytes, message_id: str):
        """
        Send audio chunk to voice provider
        In production: Send via WebSocket/WebRTC to voice provider
        """
        # Simulate sending to voice provider
        logger.debug(f"[{message_id}] Sending audio chunk ({len(audio_chunk)} bytes)")
        await asyncio.sleep(0.05)  # Simulate network latency
    
    async def send_text_to_speech(self, text: str, message_id: str):
        """
        Convert text to speech and stream to voice provider
        In production: Use TTS service (Google TTS, Amazon Polly, ElevenLabs, etc.)
        """
        logger.info(f"[{message_id}] TTS: {text}")
        
        # Simulate chunked audio generation and streaming
        # Split text into smaller parts for streaming
        words = text.split()
        chunk_size = 5
        
        for i in range(0, len(words), chunk_size):
            if not self.is_streaming or self.current_message_id != message_id:
                logger.info(f"[{message_id}] Streaming cancelled")
                break
                
            chunk_text = ' '.join(words[i:i + chunk_size])
            
            # Simulate TTS conversion to audio
            audio_chunk = chunk_text.encode('utf-8')
            
            await self.send_to_voice_provider(audio_chunk, message_id)
            
            await asyncio.sleep(0.3)  # Simulate time to generate and play audio
    
    async def handle_ai_response(self, message: Dict[str, Any]):
        """Handle AI agent response"""
        message_id = message.get('message_id')
        
        if message.get('type') == 'start':
            logger.info(f"[{message_id}] Starting AI response stream")
            self.current_message_id = message_id
            self.is_streaming = True
            
        elif message.get('type') == 'chunk':
            text_chunk = message.get('text', '')
            if self.is_streaming and self.current_message_id == message_id:
                await self.send_text_to_speech(text_chunk, message_id)
                
        elif message.get('type') == 'complete':
            logger.info(f"[{message_id}] AI response complete")
            self.is_streaming = False
            
        elif message.get('type') == 'cancel':
            cancel_msg_id = message.get('message_id')
            logger.info(f"[{cancel_msg_id}] Cancelling current stream")
            
            if self.current_message_id == cancel_msg_id:
                self.is_streaming = False
                self.current_message_id = None
    
    async def handle_filler(self, message: Dict[str, Any]):
        """Handle filler responses during buying time"""
        message_id = message.get('message_id')
        filler_text = message.get('text', '')
        
        logger.info(f"[{message_id}] Playing filler: {filler_text}")
        
        # Temporarily switch to filler mode
        previous_mode = self.mode
        self.mode = OutputMode.FILLER
        
        await self.send_text_to_speech(filler_text, message_id)
        
        # Restore previous mode
        self.mode = previous_mode
    
    async def handle_handover(self, message: Dict[str, Any]):
        """Handle transition to human agent"""
        logger.info(f"Switching to human agent mode for session {self.session_id}")
        
        # Send transition message
        transition_text = message.get('message', 'Connecting you to an agent now.')
        await self.send_text_to_speech(transition_text, "handover_msg")
        
        # Switch mode
        self.mode = OutputMode.HUMAN_AGENT
        self.is_streaming = False
        
        # Start listening for human agent audio stream
        await self.stream_human_agent_audio()
    
    async def stream_human_agent_audio(self):
        """
        Stream live audio from human agent via messaging server
        In production: Connect to socket server and forward live stream
        """
        logger.info("Starting human agent audio stream")
        
        # Simulate receiving human agent audio chunks
        # In production: WebSocket connection to messaging server
        for i in range(10):
            if not self.running:
                break
                
            # Simulate receiving audio from human agent
            audio_chunk = f"Human agent audio chunk {i}".encode('utf-8')
            await self.send_to_voice_provider(audio_chunk, "human_agent")
            
            await asyncio.sleep(0.5)
        
        logger.info("Human agent stream ended")
    
    async def handle_end_call(self, message: Dict[str, Any]):
        """Handle call termination"""
        goodbye_text = message.get('message', 'Goodbye!')
        
        logger.info(f"Ending call for session {self.session_id}")
        await self.send_text_to_speech(goodbye_text, "end_call")
        
        # Stop the manager
        self.running = False
    
    async def process_queue_item(self, item: Dict[str, Any]):
        """Process single item from output queue"""
        item_type = item.get('type')
        
        if item_type in ['start', 'chunk', 'complete', 'cancel']:
            await self.handle_ai_response(item)
            
        elif item_type == 'filler' or item_type == 'request_filler':
            await self.handle_filler(item)
            
        elif item_type == 'handover':
            await self.handle_handover(item)
            
        elif item_type == 'end_call':
            await self.handle_end_call(item)
            
        else:
            logger.warning(f"Unknown message type: {item_type}")
    
    async def run(self):
        """Main run loop for Output Manager"""
        logger.info(f"Output Manager started for session {self.session_id}")
        
        try:
            while self.running:
                try:
                    # Poll output queue continuously
                    item = await asyncio.wait_for(
                        self.output_queue.get(), 
                        timeout=1.0
                    )
                    
                    await self.process_queue_item(item)
                    
                except asyncio.TimeoutError:
                    # No items in queue, continue polling
                    continue
                    
        except Exception as e:
            logger.error(f"Error in Output Manager: {e}")
        finally:
            logger.info("Output Manager stopped")


# Test the Output Manager
async def test_output_manager():
    output_queue = asyncio.Queue()
    
    manager = OutputManager("test_session_001", output_queue)
    
    # Start manager
    manager_task = asyncio.create_task(manager.run())
    
    # Simulate various message types
    async def simulate_messages():
        await asyncio.sleep(1)
        
        # AI response
        message_id = "msg_test_001"
        
        await output_queue.put({
            "type": "start",
            "message_id": message_id
        })
        
        await output_queue.put({
            "type": "chunk",
            "message_id": message_id,
            "text": "Hello! I'd be happy to help you with that."
        })
        
        await asyncio.sleep(2)
        
        await output_queue.put({
            "type": "chunk",
            "message_id": message_id,
            "text": "We have several great SUV models available."
        })
        
        await asyncio.sleep(2)
        
        await output_queue.put({
            "type": "complete",
            "message_id": message_id
        })
        
        # Filler
        await asyncio.sleep(1)
        await output_queue.put({
            "type": "filler",
            "message_id": "msg_test_002",
            "text": "Let me check that information for you."
        })
        
        # Handover
        await asyncio.sleep(2)
        await output_queue.put({
            "type": "handover",
            "session_id": "test_session_001",
            "message": "Connecting you to our specialist now."
        })
        
        await asyncio.sleep(5)
        
        # End call
        await output_queue.put({
            "type": "end_call",
            "message": "Thank you for calling. Have a great day!"
        })
    
    await simulate_messages()
    await manager_task


if __name__ == "__main__":
    asyncio.run(test_output_manager())