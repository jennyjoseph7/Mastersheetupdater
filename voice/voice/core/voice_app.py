
import sys, os, json
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agent import voice_agent
from manager.manager import *
from clients import messaging_client as ws
from utils import *
from providers import provider_base as voice_provider

import asyncio
import uuid
from multiprocessing import Process, Queue
import queue
import time

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
import utils
logger = utils.get_logger(__name__)


Queue()

async def user_session(system_prompt:str, init_config: dict = None,  **user_data):

    input_queue = Queue()
    output_queue = Queue()

    session_id = user_data.get('session_id', 'test_session')
    
    #websocket connection
    input_client = ws.MessagingClient(
        session_id,
        tag = "input_client"
    )

    output_client = ws.MessagingClient(
        session_id,
        tag = "output_client"
    )

    provider = voice_provider.get_provider(user_data.get('provider', 'twilio'))

    IM = InputManager(
        session_id,
        input_client,
        input_queue,
        output_queue,
        provider
    )

    OM = OutputManager(
       session_id, 
       output_client,
       output_queue,
       provider
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
    "You are a helful assistant.",
    10)

    await VB.create_session()

    try:
        while True:
            # Note the () calls and async sleep
            if not im.is_alive() or not om.is_alive():
                break
            await asyncio.sleep(0.1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.info(f"Session cancelled, cleaning up... {e}")
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        logger.info("Cleanup complete")
    finally:
        # Cleanup
        logger.info('cleaning up')

        #thread cleanup for input manager
        if IM.active_threads:
            for thread in IM.active_threads:
                if thread.is_alive():
                    thread.kill()
        input_client.disconnect()
        output_client.disconnect()
        im.terminate()
        im.join(timeout=5)
        om.terminate()
        om.join(timeout=5)
        if im.is_alive() or om.is_alive():
            logger.warning("Process didn't terminate, forcing...")
            im.kill()
            om.kill()



if __name__ == "__main__":
    try:
        asyncio.run(user_session("hey"))
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        logger.info("Cleanup complete")




