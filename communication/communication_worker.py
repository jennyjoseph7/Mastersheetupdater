
import importlib
import pkgutil
import json
from gryd_worker import gryd, gryd_helpers as hp
import sys, os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
# from campaign.campaign_workflow import determine_campaign_next_action

from typing import Union
from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile

# --- Set import path for internal modules ---
# sys.path.insert(0, dirname(dirname(abspath(__file__))))

from communication.connectors.communication_configs import *
from config import AUTOCRM_COMMUNICATION_SERVICE_NAME
gryd.SERVICE = AUTOCRM_COMMUNICATION_SERVICE_NAME
THREADS_PER_SESSION = 0.1
gryd.set_queue_manager()
logger = gryd.hp.get_logger(gryd.SERVICE)
from communication.connectors.connector_whatsapp import *
from communication.connectors.load_providers import load_providers
from communication.connectors.connector_mail import *
from communication.connectors.connector_rcs import *
def WARM_UP():
    logger.info("WARM_UP CALLED")
    with get_pg_connector() as pg:
        load_providers(["whatsapp","email"])
        pass    
    return


@gryd.is_a_task(function_name="send_custom_template")
def send_custom_template(*args,**kwargs):
    logger.info("Send custom template called---")
    BaseWebhookConverter.send_custom_template(*args,**kwargs)


