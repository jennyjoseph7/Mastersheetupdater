from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
import sys
import json
import importlib
import pkgutil
# import time
import flask as Flask
# import uuid
# sys.path.insert(0, dirname(dirname(abspath(__file__))))
from gryd_worker import gryd,gryd_routes, gryd_helpers as hp
import sys, os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
from autocrm_db_helper import get_pg_connector
# from agents.get_whatsapp_template_agent import get_whatsapp_template
# from campaign.campaign_manager import BaseCustomCampaignManager
from config import AUTOCRM_CAMPAIGN_SERVICE_NAME,VOICE_PROVIDER_NAME

gryd.SERVICE = AUTOCRM_CAMPAIGN_SERVICE_NAME
THREADS_PER_SESSION = 0.1
gryd.set_queue_manager()
logger = gryd.hp.get_logger(gryd.SERVICE)
logger.info(f"GRYD SERVICE---{gryd.SERVICE}")
from communication.connectors.load_providers import load_providers
# from communication.connectors.whatsapp_connectors.source_connectors import BaseWebhookConverter

def WARM_UP():
    logger.info("WARM_UP CALLED")
    with get_pg_connector() as pg:
        load_providers(["whatsapp","email"])
        pass    
    return

# WARM_UP()

def import_modules(module_name):
    logger.info(f"Initializing {module_name} module")
    module_ref = {
        module_info.name: importlib.import_module(f"{module_name}.{module_info.name}")
                        for module_info in pkgutil.iter_modules([module_name])
    }
    if not module_ref:return
    _ = {setattr(v, 'gryd', gryd) for v in module_ref.values()}
    return _

module_list=["campaign"]
imported_modules = dict(map(lambda module: (module, import_modules(module)), module_list))

logger.info(f"List of all task campaign {json.dumps(gryd.LIST_OF_TASKS or {}, indent=4,default=str)}   {imported_modules}")

if __name__ == "__main__":
    pass
