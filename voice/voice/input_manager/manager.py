"""
Input Manager
Handles user audio input, manages AI agent states, and coordinates with voice agent
"""

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.helpers import *
import asyncio
import uuid
import time
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    INTERRUPTION = "interruption"
    HANDOVER = "handover"
    REQUEST_FILLER = "request_filler" #buying time

class OutputState(Enum):
    END_CALL = "end_call"
    COMPLETED = "completed"
    RESPONDING = "responding"
    AI_AGENT = "ai_agent"
    HUMAN_AGENT = "human_agent"

#

@dataclass
class UserMessage:
    message_id: str
    session_id: str
    audio_data: Optional[bytes] = None 
    transcript: Optional[str] = None
    timestamp: float
    is_interruption: bool = False
    type: Optional[AgentState] = None

@dataclass
class AIAgentMessage:
    pass

class InputManager:
    """Manages incoming user audio stream and agent states"""
    
    def __init__(self, session_id: str, input_queue: asyncio.Queue, output_queue = asyncio.Queue):
        self.session_id = session_id
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.state = AgentState.IDLE
        
        self.current_message_id: Optional[str] = None
        self.active_generation = False
        self.last_activity_time = time.time()
        
        # Configuration
        self.idle_timeout = 10.0  # seconds
        self.interruption_threshold = 0.5  # seconds of audio to detect interruption
        
        self.running = True
        self.cancellation_event = asyncio.Event()
    
    
    async def handle_user_input(self, audio_data: bytes = None, transcript: str = None, is_interruption: bool = False):
        """Process incoming user audio and transcript"""
        
        # Check for handover keywords
        '''     handover_keywords = ["human agent", "speak to someone", "real person", "representative"]
        if any(keyword in transcript.lower() for keyword in handover_keywords):
            await self.trigger_handover()
            return'''
        
        # Handle interruption
        if is_interruption and self.state == AgentState.PROCESSING:
            logger.info(f"Interruption detected during message {self.current_message_id}")
            await self.handle_interruption(audio_data, transcript)
            return
        
        # Create new message
        message_id = generate_uuid()
        self.current_message_id = message_id
        self.last_activity_time = time.time()
        
        message = UserMessage(
            message_id=message_id,
            session_id=self.session_id,
            audio_data=audio_data,
            transcript=transcript,
            timestamp=time.time(),
            is_interruption=is_interruption,
            type = AgentState.PROCESSING
        )
        
        logger.info(f"New user input [{message_id}]: {transcript}")
        
        # Update state
        self.state = AgentState.PROCESSING
        self.active_generation = True
        
        # Push to input queue for Voice Agent to process
        await self.input_queue.put(message)
        
        # Start buying time if response takes too long
        asyncio.create_task(self.monitor_response_latency(message_id))
    
    async def handle_interruption(self, audio_data: bytes, transcript: str):
        """Handle user interruption during active response"""
        
        # Cancel current generation
        logger.info(f"Cancelling current generation for {self.current_message_id}")
        self.cancellation_event.set()
        self.active_generation = False
        
        # Create interruption message
        new_message_id = generate_uuid()
        
        
        # Send cancellation signal to output queue
        await self.output_queue.put(interruption_message)
        
        # Update current message and state
        self.current_message_id = new_message_id
        self.state = AgentState.INTERRUPTION
    
        # Send acknowledgment filler
        interruption_message = UserMessage(
            message_id=new_message_id,
            session_id=self.session_id,
            audio_data=audio_data,
            transcript=transcript,
            timestamp=time.time(),
            is_interruption=True,
            type = AgentState.REQUEST_FILLER

        )
        await self.input_queue.put(interruption_message)
        
        self.state = AgentState.PROCESSING
        self.active_generation = True
        self.cancellation_event.clear()
    
    async def monitor_response_latency(self, message_id: str):
        """Monitor response generation time and trigger filler if needed"""
        await asyncio.sleep(1.5)  # Wait threshold before fillers
        
        if self.active_generation and self.current_message_id == message_id:
            logger.info(f"Response taking longer, triggering buying time for {message_id}")
            self.state = AgentState.REQUEST_FILLER
            
            # Trigger filler generation
            await self.output_queue.put({
                "type": self.state ,
                "message_id": message_id
            })
    
    async def trigger_handover(self):
        """Initiate handover to human agent"""
        logger.info(f"Triggering handover for session {self.session_id}")
        
        self.state = AgentState.HANDOVER
        self.active_generation = False
        
        # Send handover notification
        await self.output_queue.put({
            "type": "handover",
            "session_id": self.session_id,
            "message": "Let me connect you with a human agent right away."
        })
        
        # Stop input processing but keep output active for human agent stream
        self.running = False
        logger.info("Input Manager stopped for handover")
    
    async def monitor_idle_timeout(self):
        """Monitor idle state and end call if threshold exceeded"""
        while self.running:
            await asyncio.sleep(1)
            
            if self.state == AgentState.IDLE:
                idle_duration = time.time() - self.last_activity_time
                
                if idle_duration > self.idle_timeout:
                    logger.info(f"Idle timeout reached ({idle_duration:.1f}s), ending call")
                    
                    # Send goodbye message
                    await self.output_queue.put({
                        "type": AgentState.END_CALL,
                        "message_id": self.current_message_id
                    })
                    
                    self.running = False
                    break
    
    async def run(self):
        """Main run loop for Input Manager"""
        logger.info(f"Input Manager started for session {self.session_id}")
        
        # Start idle monitor
        idle_task = asyncio.create_task(self.monitor_idle_timeout())
        
        try:
            # Process audio stream
            async for audio_data, transcript, is_interruption in self.simulate_audio_stream():
                if not self.running:
                    break
                    
                await self.handle_user_input(audio_data, transcript, is_interruption)
                
                # Reset to idle after processing
                if self.state != AgentState.HANDOVER:
                    self.state = AgentState.IDLE
                    self.active_generation = False
                    self.last_activity_time = time.time()
            
        except Exception as e:
            logger.error(f"Error in Input Manager: {e}")
        finally:
            self.running = False
            idle_task.cancel()
            logger.info("Input Manager stopped")


# Test the Input Manager
async def test_input_manager():
    input_queue = asyncio.Queue()
    output_queue = asyncio.Queue()
    
    manager = InputManager("test_session_001", input_queue, output_queue)
    
    # Start manager
    manager_task = asyncio.create_task(manager.run())
    
    # Monitor queues
    async def monitor_queues():
        while manager.running:
            if not input_queue.empty():
                msg = await input_queue.get()
                logger.info(f"[INPUT QUEUE] Received: {msg.transcript}")
            
            if not output_queue.empty():
                msg = await output_queue.get()
                logger.info(f"[OUTPUT QUEUE] Received: {msg}")
            
            await asyncio.sleep(0.1)
    
    monitor_task = asyncio.create_task(monitor_queues())
    
    await manager_task
    monitor_task.cancel()


if __name__ == "__main__":
    asyncio.run(test_input_manager())