

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.helpers import *
import time
import logging
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, Union, Literal
from multiprocessing import Process, Queue, Manager
import threading
import queue
import signal

import utils
logger = utils.get_logger(__name__)

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
    AI_AGENT_RESPONSE = "ai_agent_responding"
    HUMAN_AGENT_RESPONSE = "human_agent_responding"
    CLEAR_BUFFER = 'clear_buffer'
    TAG = "output_manager"

class MessageTimeLifecyle(Enum):
    USER_INPUT_SENT  = "user_sent"
    INPUT_SOCKET_RECIEVED = "socket_recieved"
    INPUT_MANAGER_RECIEVED = "input_manager_recieved"
    AGENT_RECIEVED = "agent_recieved"
    AGENT_RESPONDED = "agent_responded"
    OUTPUT_MANAGER_RECIEVED  = "output_manager_recieved"
    OUTPUT_SOCKET_SENT   = "output_socket_recieved"
    


@dataclass
class Message:
    message_id: str
    session_id: str
    state: Union[InputState, OutputState] = None
    tag: Literal["input_manager", "output_manager"] = "input_manager"
    message_type: Literal['stream_start', 'audio_input', 'audio_output', 'clear_buffer'] = 'stream_start'
    metadata: dict = None
    audio_data: Union[bytes, dict[str, any]] = None


    def to_dict(self):
        return {
            'message_id': self.message_id,
            'session_id': self.session_id,
            'state': self.state,
            'tag': self.tag,
            'message_type': self.message_type,
            'metadata': self.metadata,
            'audio_data': self.audio_data

        }


class InputManager:
    """Manages incoming user audio stream in a separate process"""

    def __init__(self, session_id: str, client, input_queue: Queue, output_queue: Queue, provider, buffer_identifier, shutdown_event=None):
        self.session_id = session_id
        self.input_queue = input_queue  # multiprocessing.Queue - sends to voice agent
        self.output_queue = output_queue  # multiprocessing.Queue - receives from voice agent
        self.provider = provider # to keep input and output consistent
        self.buffer_identifier = buffer_identifier  # Shared buffer identifier between processes
        self.shutdown_event = shutdown_event  # multiprocessing.Event for shutdown signal

        self.state = InputState.IDLE

        self.current_message_id: Optional[str] = None
        self.active_generation = False
        self.last_activity_time = time.time()

        #websocket connected client
        self.client = client

        #identify message
        self.tag = 'input_manager'

        # Configuration
        self.idle_timeout = 10.0
        self.interruption_threshold = 0.5

        self.running = True

        #active thread list
        self.active_threads = []

    def process_user_input(self, raw_data: dict[str, any], message_id:str, state: InputState | OutputState, is_interruption: bool = False):
        """Process incoming user audio and transcript (blocking)"""

        # Handle interruption
        # if is_interruption and self.state == InputState.PROCESSING:
        #     logger.info(f"Interruption detected during message {self.current_message_id}")
        #     self.handle_interruption(raw_data)
        #     return

        # Start new message
        self.current_message_id = message_id
        self.last_activity_time = time.time()

        if not raw_data:
            return


        in_payload = self.provider.receive_message(raw_data)
        # logger.info(f'recieved data in input queue: {type(in_payload.get("audio_data"))}')

        # if in_payload.get('audio_data')[:10] == self.buffer_identifier.value:
        #     # logger.info('Looks like messaage from output manager ignoring...')
        #     return

        if in_payload.get('message_type','') == 'stream_start':
            session_id = in_payload.get('metadata',{}).get('custom_params', {}).get('session_id')
            if  session_id !=  self.session_id:
                logger.info(f'looks like getting stream for different session id, current session_id {self.session_id} but recieved is {session_id}')
                return  

        message = Message(

            message_id=message_id,
            session_id=self.session_id,
            audio_data = in_payload.get('audio_data', None),
            message_type = in_payload['message_type'],
            metadata = in_payload.get('metadata', {}),
            state=state
            )

        #logger.info(f"user input [{message_id}]: {message.to_dict()}")

        # Update state
        self.state = state
        self.active_generation = True #temparory

        # Push to input queue for Voice Agent to process
        self.input_queue.put(message.to_dict())

        # Monitor response latency (simple blocking approach) --> using threading
        response_latencylatency_task = threading.Thread(target=self.check_response_latency, args = (message_id, ), daemon=False)
        response_latencylatency_task.start()

        #so that if running later we can disconnect
        self.active_threads.append(response_latencylatency_task) 

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
            state=InputState.REQUEST_FILLER.value
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
                # logger.info(f"Response taking longer, triggering filler for {message_id}")
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

        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, _frame):
            logger.info(f"Input Manager received signal {signum}, shutting down...")
            self.running = False

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        try:
            # Set the sync callback for MessagingClient
            message_id = generate_uuid()
            state = InputState.PROCESSING

            self.client.on_message_callback = lambda x: self.process_user_input(x, message_id, state)

            # Start the MessagingClient in a separate thread
            self.client.run()

            # Keep the process alive while running
            logger.info(f"Input Manager entering main loop for session {self.session_id}")
            while self.running:
                # Check shutdown event
                if self.shutdown_event and self.shutdown_event.is_set():
                    logger.info("Shutdown event detected in InputManager")
                    self.running = False
                    break
                time.sleep(0.1)

        except Exception as e:
            logger.error(f"Error in Input Manager: {e}")
        finally:
            # Cleanup: disconnect client when exiting
            logger.info(f"Input Manager shutting down, disconnecting client...")
            try:
                self.client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting client: {e}")
            logger.info(f"Input Manager stopped for session {self.session_id}")

    def get_process(self):
        return Process(
            target = self.run
        )

class OutputManager:
    """Manages outgoing voice responses in a separate process"""

    def __init__(self, session_id: str, client, output_queue: Queue, provider, buffer_identifier, shutdown_event=None):
        self.session_id = session_id
        self.output_queue = output_queue  # multiprocessing.Queue - receives from voice agent
        self.provider  = provider #to maintain consistent output
        self.buffer_identifier = buffer_identifier  # Shared buffer identifier between processes
        self.shutdown_event = shutdown_event  # multiprocessing.Event for shutdown signal
        self.running = True

        #websocket connected client
        self.client = client


    def run(self):
        """Main run loop for Output Manager (blocking, runs in separate process)"""
        logger.info(f"Output Manager started for session {self.session_id} in process {os.getpid()}")

        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, _frame):
            logger.info(f"Output Manager received signal {signum}, shutting down...")
            self.running = False

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        try:
            self.client.run()

            # Keep the process alive while running
            logger.info(f"Output Manager entering main loop for session {self.session_id}")
            while self.running:
                # Check shutdown event
                if self.shutdown_event and self.shutdown_event.is_set():
                    logger.info("Shutdown event detected in OutputManager")
                    self.running = False
                    break

                try:
                    message = self.output_queue.get(timeout=0.1)
                    if not message:
                        continue

                    # Check for shutdown signal
                    if message.get("type") == "shutdown":
                        logger.info("Received shutdown signal in OutputManager")
                        self.running = False
                        break

                    # Set shared buffer identifier from the first 10 bytes of audio data
                    # if message.get('audio_data'):
                    #     self.buffer_identifier.value = message.get('audio_data')[:10]

                    message = self.provider.send_message(message)
                    # message['tag'] = 'output_manager'
                    # logger.info(f'recieved message from output queue: {message}')
                    #message_id

                    self.client.send_message(message)
                except queue.Empty:
                    pass
                except Exception as e:
                    logger.error(f"Error in OutputManager main loop: {e}")

                # time.sleep(0.1)

        except Exception as e:
            logger.error(f"Error in Output Manager: {e}")
        finally:
            # Cleanup: disconnect client when exiting
            logger.info(f"Output Manager shutting down, disconnecting client...")
            try:
                self.client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting client: {e}")
            logger.info(f"Output Manager stopped for session {self.session_id}")

    def get_process(self):
        return Process(
            target = self.run
        )




if __name__ == "__main__":
    #pkill -9 -f "multiprocessing.resource_tracker" && pkill -9 -f "multiprocessing.spawn" && echo "Killed orphaned multiprocessing processes"
    pass