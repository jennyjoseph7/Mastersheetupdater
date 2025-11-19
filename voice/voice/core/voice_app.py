"""
Voice App Core - Main Orchestrator
Manages job intake, prompt generation, and coordinates all managers
"""
import sys, os, json
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agent import voice_agent
from manager.manager import *
from clients import messaging_client as ws
from utils import helpers as hp, streaming as sh
import asyncio
import uuid
from multiprocessing import Process, Queue
import queue
import time

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




def user_session(system_prompt:str, init_config: dict = None,  **user_data):

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

    IM = InputManager(
        session_id,
        input_client,
        input_queue,
        output_queue
    )

    OM = OutputManager(
       session_id, 
       output_client,
       output_queue
    )


    ##TODO: logic to terminate other process when one is completed/failed/disconected
    im = IM.get_process()
    im.start()

    om = OM.get_process()
    om.start()
    # Keep the session running until interrupted
    try:
        while im.is_alive() or om.is_alive():
            time.sleep(2)
            ##logic for generting, sending, recieving responses.
    except Exception as e:
        logger.info("Session cancelled, cleaning up...")
    finally:
        # Cleanup
        logger.info('cleaning up')
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
        user_session("hey")
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        logger.info("Cleanup complete")




