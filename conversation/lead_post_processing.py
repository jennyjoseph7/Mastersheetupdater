import os
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from config import AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME
from gryd_worker import gryd, gryd_helpers as hp
from autocrm_db_helper import get_pg_connector
from prompt import yield_primary_prompt, run_prompt_sync
json = hp.json