import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)
import importlib
import pkgutil
import helpers as hp
import json
from gryd_worker import gryd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from campaign.campaign_workflow import determine_campaign_next_action
from typing import Union

from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
import sys
# --- Set import path for internal modules ---
sys.path.insert(0, dirname(dirname(abspath(__file__))))

from connectors.communication_configs import *
from config import AUTOCRM_COMMUNICATION_SERVICE_NAME
gryd.SERVICE = AUTOCRM_COMMUNICATION_SERVICE_NAME
# config={
#     "broker_type": GRYD_COMMUNICATION_BROKER,
#     "timeout":GRYD_COMMUNICATION_TIMEOUT,
#     "wait_time_to_shutdown":GRYD_COMMUNICATION_SHUTDOWN_TIMEOUT
#     }
gryd.set_queue_manager()
QUEUE_MANAGER = gryd.get_queue_manager(AUTOCRM_COMMUNICATION_SERVICE_NAME)
logger=hp.get_logger(__name__)

def import_modules(module_name):
    logger.info(f"Initializing {module_name} module")
    module_ref = {
        module_info.name: importlib.import_module(f"{module_name}.{module_info.name}")
                        for module_info in pkgutil.iter_modules([module_name])
    }
    if not module_ref:return
    _ = {setattr(v, 'gryd', gryd) for v in module_ref.values()}
    return _

module_list=["communication"]
imported_modules = dict(map(lambda module: (module, import_modules(module)), module_list))

logger.info(f"List of all task {json.dumps(gryd.LIST_OF_TASKS or {}, indent=4,default=str)}   {imported_modules}")

@gryd.is_a_task(function_name="get_communication_status_details")
def get_communication_status_details(*args,**kwargs):
    return {
        "info":"Communication Worker is running...",
        "current-environment":os.environ.get("ENVIRONMENT"),
        "service_name":GRYD_COMMUNICATION_SERVICE,
        "service_broker":GRYD_COMMUNICATION_BROKER,
        "converse_service":CONVERS_SERVICE_NAME,
        "converse_taks":CONVERS_TASK_NAME
    }

@gryd.is_a_task(function_name="determine_campaign_next_action")
def determine_campaign_next_action(enterprise_id: str, campaign_id: str, channel: str, user_id: str, session_id: str, disposition: str, i2ce_headers: Union[dict, None] = None):
    """
    This task is used to determine the next action for a campaign.
    It is used to determine the next action for a campaign based on the disposition of the message.
    Args:
        enterprise_id: The ID of the enterprise.
        campaign_id: The ID of the campaign.
        channel: The channel of the campaign.
        user_id: The ID of the user.
        session_id: The ID of the session.
        disposition: The disposition of the message.
    Returns:
        None.
        Triggers the next action for a campaign.
    """
    return determine_campaign_next_action(enterprise_id, campaign_id, channel, user_id, session_id, disposition, i2ce_headers)





