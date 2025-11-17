"""
Input Manager with Multi-Process Queue Implementation
Handles user audio input in a separate process to avoid asyncio single-thread limitations
"""

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.helpers import *
import time
import logging
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, Union, Literal
from multiprocessing import Process, Queue
import threading
import queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InputState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    INTERRUPTION = "interruption"
    HANDOVER = "handover"
    REQUEST_FILLER = "request_filler"
    TAG = "input_manager"


class OutputState(Enum):
    END_CALL = "end_call"
    COMPLETED = "completed"
    RESPONDING = "responding"
    AI_AGENT = "ai_agent"
    HUMAN_AGENT = "human_agent"
    TAG = "output_manager"


@dataclass
class Message:
    message_id: str
    session_id: str
    audio_data: Union[bytes, dict[str, any]] = None
    transcript: Optional[str] = None
    timestamp: float = 0.0
    is_interruption: bool = False
    state: Union[InputState, OutputState] = None
    tag: Literal["input_manager", "output_manager"] = "input_manager"

    def to_dict(self):
        return {
            'message_id': self.message_id,
            'session_id': self.session_id,
            'audio_data': self.audio_data,
            'transcript': self.transcript,
            'timestamp': self.timestamp,
            'is_interruption': self.is_interruption,
            'state': self.state,
            'tag': self.tag
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class InputManager:
    """Manages incoming user audio stream in a separate process"""

    def __init__(self, session_id: str, client, input_queue: Queue, output_queue: Queue):
        self.session_id = session_id
        self.input_queue = input_queue  # multiprocessing.Queue - sends to voice agent
        self.output_queue = output_queue  # multiprocessing.Queue - receives from voice agent
        self.state = InputState.IDLE

        self.current_message_id: Optional[str] = None
        self.active_generation = False
        self.last_activity_time = time.time()
        
        #websocket connected client
        self.client = client

        # Configuration
        self.idle_timeout = 10.0
        self.interruption_threshold = 0.5

        self.running = True

    def process_user_input(self, raw_data: dict[str, any], message_id:str, state: InputState | OutputState, is_interruption: bool = False):
        """Process incoming user audio and transcript (blocking)"""

        # Handle interruption
        # if is_interruption and self.state == InputState.PROCESSING:
        #     logger.info(f"Interruption detected during message {self.current_message_id}")
        #     self.handle_interruption(raw_data)
        #     return

        # Create new message
        self.current_message_id = message_id
        self.last_activity_time = time.time()

        message = Message(
            message_id=message_id,
            session_id=self.session_id,
            audio_data=raw_data,
            transcript= None,
            timestamp=time.time(),
            is_interruption=is_interruption,
            state=state
        )

        logger.info(f"New user input [{message_id}]: {message.to_dict()}")

        # Update state
        self.state = state
        self.active_generation = True #temparory

        # Push to input queue for Voice Agent to process
        self.input_queue.put(message.to_dict())

        # Monitor response latency (simple blocking approach) --> using threading
        latency_task = threading.Thread(target=self.check_response_latency, args = (message_id, ), daemon=True)
        latency_task.start()
        #self.check_response_latency(message_id) - blocking the process

    def handle_interruption(self, audio_data: bytes, transcript: str):
        """Handle user interruption during active response"""

        # Cancel current generation
        logger.info(f"Cancelling current generation for {self.current_message_id}")
        self.active_generation = False

        # Send cancellation signal to output queue
        self.output_queue.put({
            "type": "cancel",
            "message_id": self.current_message_id
        })

        # Create interruption message
        new_message_id = generate_uuid()
        self.current_message_id = new_message_id
        self.state = InputState.INTERRUPTION

        # Send interruption message
        interruption_message = Message(
            message_id=new_message_id,
            session_id=self.session_id,
            audio_data=audio_data,
            transcript=transcript,
            timestamp=time.time(),
            is_interruption=True,
            type=InputState.REQUEST_FILLER.value
        )
        self.input_queue.put(interruption_message.to_dict())

        self.state = InputState.PROCESSING
        self.active_generation = True

    def check_response_latency(self, message_id: str):
        """Check if response is taking too long (simple check)"""
        start_time = time.time()

        while self.active_generation and self.current_message_id == message_id:
            elapsed = time.time() - start_time

            if elapsed > 1.5:
                logger.info(f"Response taking longer, triggering filler for {message_id}")
                self.state = InputState.REQUEST_FILLER

                # self.output_queue.put({
                #     "type": "request_filler",
                #     "message_id": message_id
                # })
                break

            time.sleep(0.1)

    def trigger_handover(self):
        """Initiate handover to human agent"""
        logger.info(f"Triggering handover for session {self.session_id}")

        self.state = InputState.HANDOVER
        self.active_generation = False

        self.output_queue.put({
            "type": "handover",
            "session_id": self.session_id,
            "message": "Let me connect you with a human agent right away."
        })

        self.running = False
        logger.info("Input Manager stopped for handover")

    def monitor_idle_timeout(self):
        """Monitor idle state and end call if threshold exceeded"""
        while self.running:
            time.sleep(1)

            if self.state == InputState.IDLE:
                idle_duration = time.time() - self.last_activity_time

                if idle_duration > self.idle_timeout:
                    logger.info(f"Idle timeout reached ({idle_duration:.1f}s), ending call")

                    self.output_queue.put({
                        "type": "end_call",
                        "message_id": self.current_message_id,
                        "message": "Thank you for calling. Goodbye!"
                    })

                    self.running = False
                    break


    def run(self):
        """Main run loop for Input Manager (blocking, runs in separate process)"""
        logger.info(f"Input Manager started for session {self.session_id} in process {os.getpid()}")

        # Set the sync callback for MessagingClient
        message_id = generate_uuid()
        state = InputState.PROCESSING

        self.client.on_message_callback = lambda x: self.process_user_input(x, message_id, state, False)

        # Start the MessagingClient in a separate thread
        self.client.run()

        # Keep the process alive while running
        logger.info(f"Input Manager entering main loop for session {self.session_id}")
        while self.running:
            time.sleep(0.1)

        logger.info(f"Input Manager stopped for session {self.session_id}")

    def get_process(self):
        return Process(
            target = self.run
        )

class OutputManager:
    """Manages outgoing voice responses in a separate process"""

    def __init__(self, session_id: str, client, output_queue: Queue):
        self.session_id = session_id
        self.output_queue = output_queue  # multiprocessing.Queue - receives from voice agent
        self.running = True

        #websocket connected client
        self.client = client

    def process_output(self, message):
        """Process outgoing message"""
        msg_type = message.get('type', 'unknown')

        if msg_type == 'cancel':
            logger.info(f"[OUTPUT] Cancelling message {message.get('message_id')}")
        elif msg_type == 'request_filler':
            logger.info(f"[OUTPUT] Playing filler for {message.get('message_id')}")
        elif msg_type == 'handover':
            logger.info(f"[OUTPUT] Handover: {message.get('message')}")
            self.running = False
        elif msg_type == 'end_call':
            logger.info(f"[OUTPUT] End call: {message.get('message')}")
            self.running = False
        elif msg_type == 'response':
            logger.info(f"[OUTPUT] Playing response: {message.get('text', '')[:50]}...")
        else:
            logger.info(f"[OUTPUT] Received: {message}")

    def run(self):
        """Main run loop for Output Manager (blocking, runs in separate process)"""
        logger.info(f"Output Manager started for session {self.session_id} in process {os.getpid()}")
        
        self.client.run()

        # Keep the process alive while running
        logger.info(f"Input Manager entering main loop for session {self.session_id}")
        while self.running:
            time.sleep(0.1)

    def get_process(self):
        return Process(
            target = self.run
        )



# Test the multi-process setup
def test_multiprocess_managers():
    """Test input and output managers in separate processes"""
    session_id = "test_session_001"

    # Create multiprocessing queues
    input_queue = Queue()  # Input -> Voice Agent
    output_queue = Queue()  # Voice Agent -> Output

    # Start input manager process
    input_process = Process(
        target=start_input_manager,
        args=(session_id, input_queue, output_queue)
    )

    # Start output manager process
    output_process = Process(
        target=start_output_manager,
        args=(session_id, output_queue)
    )

    input_process.start()
    output_process.start()

    # Main process monitors the input queue (simulating voice agent)
    logger.info(f"Main process {os.getpid()} monitoring queues...")

    try:
        while input_process.is_alive() or output_process.is_alive():
            try:
                # Check input queue
                msg = input_queue.get(timeout=1)
                logger.info(f"[MAIN/VOICE AGENT] Received from input: {msg.get('transcript', msg)}")

                # Simulate processing and send response
                time.sleep(0.5)
                output_queue.put({
                    'type': 'response',
                    'message_id': msg.get('message_id'),
                    'text': f"AI response to: {msg.get('transcript', 'unknown')}"
                })
            except queue.Empty:
                continue

    except KeyboardInterrupt:
        logger.info("Shutting down...")

    finally:
        input_process.join(timeout=5)
        output_process.join(timeout=5)

        if input_process.is_alive():
            input_process.terminate()
        if output_process.is_alive():
            output_process.terminate()

        logger.info("All processes stopped")


if __name__ == "__main__":
    test_multiprocess_managers()
