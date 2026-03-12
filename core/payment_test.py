from calendar import c
import sys
import os, re
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from config import AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_CORE_SERVICE_NAME, \
    gryd, gryd_routes, hp, \
    GRYD_FILE_USER_ID, \
    GRYD_FILE_API_KEY, \
    GRYD_FILE_SERVER_URL, \
    MAX_AUDIENCE_ERRORS, \
    DEFAULT_OTP, \
    ALLOWED_COUNTRY_CODES, \
    OTP_TEMPLATE_ID, \
    AutocrmModel, \
    EXCHANGE_RATE_HOST_API_KEY, \
    EXCHANGE_RATE_HOST_BASE_URL, \
    csv
from autocrm_db_helper import get_pg_connector
from typing import List, Union, Dict, Any
import requests
import tempfile
import math
import requests
from communication.connectors.load_providers import load_providers
from communication.connectors.whatsapp_connectors.source_connectors import BaseWebhookConverter
from communication.connectors.connector_mail import send_email_otp

CHANNEL_LOADED = {}

import autocrm_validator
THIS_DIR = dirname(abspath(__file__))
if THIS_DIR not in sys.path:
    sys.path.append(THIS_DIR)
from razorpay_service import create_credit_purchase, confirm_payment_success, mark_payment_failed, mark_payment_cancelled

gryd.SERVICE = AUTOCRM_CORE_SERVICE_NAME
gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(gryd.SERVICE)
logger = mlogger
# from core.core import payment_service

source = {
    "dealership_id": "arya_raj-south-india",
        "credits": 500
}

res = gryd.create_async_task('payment_service', AUTOCRM_CORE_SERVICE_NAME,args=["purchase_credit"],kwargs=source)
print(res)

