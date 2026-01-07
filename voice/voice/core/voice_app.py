
import sys, os, json
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agent import voice_agent
from manager.manager import *
from clients import messaging_client as ws
from utils import *
from .. import providers

import asyncio
import uuid
from multiprocessing import Process, Queue, Event, Manager
import queue
import time
import signal


from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
import utils
logger = utils.get_logger(__name__)

# Global flag for clean shutdown
shutdown_requested = False



async def user_session(**user_data):

    input_queue = Queue()
    output_queue = Queue()

    # Shutdown events for graceful termination
    shutdown_event = Event()

    # Create shared Manager for process-safe shared variables
    manager = Manager()
    # Create shared namespace for buffer identifier
    buffer_identifier = manager.Namespace()
    buffer_identifier.value = None  # Will store the first 10 bytes of audio_data

    session_id = user_data.get('session_id', 'test_session')

    #websocket connection
    input_client = ws.MessagingClient(
        session_id,
        tag = "input_client"
    )

    t = time.time()
    output_client = ws.MessagingClient(
        session_id,
        tag = "output_client"
    )

    provider = providers.get_provider(user_data.get('provider', 'twilio'))
    tp = time.time() - t

    try:
        from voice.voice.providers.twilio import MessageHandler
    except:
        from voice.providers.twilio import MessageHandler
        
    IM = InputManager(
        session_id,
        input_client,
        input_queue,
        output_queue,
        MessageHandler(),
        buffer_identifier,
        shutdown_event
    )

    OM = OutputManager(
       session_id,
       output_client,
       output_queue,
        MessageHandler(),
       buffer_identifier,
       shutdown_event
    )



    ##TODO: logic to terminate other process when one is completed/failed/disconected
    im = IM.get_process()
    im.start()

    om = OM.get_process()
    om.start()
    VB = voice_agent.TestVoiceAgent(
    session_id,
    input_queue,
    output_queue,
    user_data.get('prompt', 'You are a useful assistant.'),
    10)

    await VB.create_session()

    #make call to user:
    #call_object = call(user_data.get('number'), session_id)

    try:
        while True:
            # Note the () calls and async sleep
            if not im.is_alive() or not om.is_alive():
                logger.info("One or more manager processes died, exiting...")
                break
            if shutdown_requested:
                logger.info("Shutdown requested, exiting...")
                break
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        logger.info("Session cancelled via asyncio.CancelledError")
    except KeyboardInterrupt:
        logger.info("\nKeyboardInterrupt received, shutting down gracefully...")
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Session error, cleaning up... {e}")
    finally:
        # Cleanup
        logger.info('cleaning up')

        # Set shutdown event to signal processes
        shutdown_event.set()

        # Send shutdown signal to both processes via queues
        try:
            output_queue.put({"type": "shutdown"}, block=False)
        except Exception as e:
            logger.error(f"Error putting shutdown to output_queue: {e}")

        # Give processes time to shutdown gracefully
        logger.info("Waiting for processes to shutdown gracefully...")
        time.sleep(1.0)

        #thread cleanup for input manager
        if IM and IM.active_threads:
            logger.info("Cleaning up InputManager threads...")
            for thread in IM.active_threads:
                if thread and thread.is_alive():
                    thread.join(timeout=1)

        # Disconnect clients (these are in parent process, not needed)
        # input_client.disconnect()
        # output_client.disconnect()

        # Terminate processes gracefully first
        if im and im.is_alive():
            logger.info("Terminating Input Manager process...")
            im.terminate()

        if om and om.is_alive():
            logger.info("Terminating Output Manager process...")
            om.terminate()

        # Wait for graceful termination
        if im:
            im.join(timeout=3)
        if om:
            om.join(timeout=3)

        # Force kill if still alive
        if im and im.is_alive():
            logger.warning("Input Manager didn't terminate, forcing kill...")
            im.kill()
            im.join(timeout=2)

        if om and om.is_alive():
            logger.warning("Output Manager didn't terminate, forcing kill...")
            om.kill()
            om.join(timeout=2)

        # Close the queues
        try:
            input_queue.close()
            output_queue.close()
            input_queue.join_thread()
            output_queue.join_thread()
        except Exception as e:
            logger.error(f"Error closing queues: {e}")

        logger.info("Cleanup complete")


def run_async_session(**user_data):
    """Run the async user session in a new event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(user_session(**user_data))
    finally:
        loop.close()


if __name__ == "__main__":
    def signal_handler(signum, _frame):
        global shutdown_requested
        logger.info(f"\nReceived signal {signum}, requesting shutdown...")
        shutdown_requested = True

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(user_session(**{
            "number":"+918850988794",
            "session_id":"918850988794-session-"+str(uuid.uuid4()),
        }))
    except KeyboardInterrupt:
        logger.info("\nKeyboardInterrupt in main, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Main cleanup complete")




