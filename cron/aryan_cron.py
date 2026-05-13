import sys, os
import requests
import json
import re
import time
from datetime import datetime, timezone ,timedelta
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR in sys.path:
    sys.path.remove(BASE_DIR)
sys.path.insert(0, BASE_DIR)
from config import AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_CRON_SERVICE_NAME, AUTOCRM_AGENT_SERVICE_NAME, gryd, hp, AUTOCRM_CAMPAIGN_SERVICE_NAME
from autocrm_db_helper import get_pg_connector
from typing import List, Union, Dict, Any
from autocrm_db_helper.PGConnector import AutoCRMPGConnector
from analytics.loader import load_stored_procedures

from cron.cron import overall_campaign_summary,template_summary,performance_summary,manage_active_sessions,call_campaign_workflow,reset_auth_creds,schedule_campaign_trigger,call_next_campaign_workflow_task,daily_dealership_summary

from communication.common_functions import generate_uid
pg = AutoCRMPGConnector(enterprise_id="autocrm")
from gryd_worker import gryd_db_helper as db
gryd.SERVICE = AUTOCRM_CRON_SERVICE_NAME
gryd.set_queue_manager()
logger = gryd.hp.get_logger(gryd.SERVICE)

load_stored_procedures()
