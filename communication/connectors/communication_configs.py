from os.path import (
    exists as ispath,
    dirname,
    abspath,
    basename,
    join as joinpath,
    split as pathsplit,
    splitext,
    sep as dirsep,
    isfile
)
import sys

# --- Local & Gryd modules ---
from models import model as mod, action as _act, validators as val
import helpers as hp
from gryd_worker import gryd, gryd_db_helper as db
# --- Optional modules ---
try:
    from gryd_worker import gryd_helpers as ghp
except ImportError:
    ghp = None  # fallback if needed

# --- Logger ---
def get_logger(name=None,**kwargs):
    return hp.get_logger(name or __name__,**kwargs)
logger=get_logger()

sys.path.insert(0, dirname(dirname(abspath(__file__))))


# --- Gryd configuration ---
from AppConfig.gryd_config import DynamicConfig
# from AppConfig.i2ceHeaders import Headers,DEFAULT_ENTERPRISE_HEADERS
cfg = DynamicConfig()
# try:
#     ENTERPRISE_HEADERS = Headers()
#     if not ENTERPRISE_HEADERS:
#         logger.warning("ENTERPRISE_HEADERS not found — attempting reload.")

#         # Retry loading headers up to 2 times
#         for attempt in range(2):
#             Headers.reload_all()
#             ENTERPRISE_HEADERS = Headers()
#             if ENTERPRISE_HEADERS:
#                 logger.info(f"ENTERPRISE_HEADERS successfully loaded on retry {attempt + 1}")
#                 break

#     # Final fallback
#     if not ENTERPRISE_HEADERS:
#         logger.warning("ENTERPRISE_HEADERS still not available after retries. Loading default headers.")
#         ENTERPRISE_HEADERS = DEFAULT_ENTERPRISE_HEADERS
# except Exception as e:
#     logger.exception(f"Failed to initialize ENTERPRISE_HEADERS: {e}")
#     ENTERPRISE_HEADERS = DEFAULT_ENTERPRISE_HEADERS


# # CONVERATION HEADERS
# ConverseHeader=ENTERPRISE_HEADERS


# Worker ENVIRONMENT 
ENVIRONMENT= cfg.ENVIRONMENT
BASE_URL = cfg.CONVERSATION_BASE_URL 




# Communication Services
GRYD_COMMUNICATION_SERVICE = cfg.gryd_communication_service
GRYD_COMMUNICATION_STATUS_SERVICE = cfg.gryd_communication_status_service
GRYD_COMMUNICATION_CAMPAIGN_SERVICE = cfg.gryd_communication_campaign_service
GRYD_COMMUNICATION_BROKER = cfg.gryd_communication_broker
GRYD_COMMUNICATION_TIMEOUT = cfg.gryd_communication_timeout
GRYD_COMMUNICATION_SHUTDOWN_TIMEOUT = cfg.gryd_communication_shutdown_timeout



# Conversation Service
CONVERS_SERVICE_NAME = cfg.convers_service_name
CONVERS_TASK_NAME = cfg.convers_task_name



# Campaign / Messaging
WHATSAPP_MESSAGE_SPLIT_LENGTH = cfg.whatsapp_message_split_length
CAMPAIGN_MAX_BATCH_SIZE = cfg.campaign_max_batch_size
CAMPAIGN_MAX_TRIGGER = cfg.campaign_max_trigger
CAMPAIGN_BATCH_SLEEP_TIME = cfg.campaign_batch_sleep_time
MAX_MODEL_CONN_RETRY = cfg.max_model_conn_retry
VOICE_CAMPAIGN_BASE_URL=cfg.voice_campaign_base_url
# Keep a sleep time of N sec before sending whatsapp message
SLEEP_OVER_MESSAGE = cfg.sleep_over_message

# Campaign Model Names
M_GRYD_CAMPAIGN_USER_DETAIL=cfg.GRYD_CAMPAIGN_USER_DETAIL
M_GRYD_CAMPAIGN_USER_DETAIL_ARCHIVE=cfg.GRYD_CAMPAIGN_USER_DETAIL_ARCHIVE
M_GRYD_CAMPAIGN_USER_INTERACTION=cfg.GRYD_CAMPAIGN_USER_INTERACTION
M_GRYD_CAMPAIGN=cfg.GRYD_CAMPAIGN
M_GRYD_CAMPAIGN_DETAIL=cfg.GRYD_CAMPAIGN_DETAIL
M_GRYD_CAMPAIGN_STATUS_CHECK=cfg.GRYD_CAMPAIGN_STATUS_CHECK


# Misc
DB_TIMEZONE = cfg.db_timezone
FILE_CHUNK_SIZE = cfg.file_chunk_size


# campaign_configs for sending message as per limit
WHATSAPP_MAX_MESSAGE_PER_DAY=cfg.WHATSAPP_MAX_MESSAGE_PER_DAY
EMAIL_MAX_MESSAGE_PER_DAY=cfg.EMAIL_MAX_MESSAGE_PER_DAY
VOICE_MAX_MESSAGE_PER_DAY=cfg.VOICE_MAX_MESSAGE_PER_DAY

# TO Send WEBHOOK to Worker
GRYD_COMMUNICATION_WEBHOOK_ASYNC=cfg.gryd_communication_webhook_async



# whatsapp configs


INBOUND = "INBOUND"
IGNORED_STATUSES = {"ACK"}
# TRACKABLE_STATUSES = {"READ", "RECEIVED", "SENT", "DELIVERED", "INITIATED","FAILED"}
TRACKABLE_STATUSES = {"READ", "RECEIVED", "SENT", "DELIVERED","FAILED"}

MODEL_ID_DETAIL={
    "gryd_campaign_user_detail":"campaign_user_id",
    "gryd_campaign_user_detail_archive":"campaign_user_archive_id",
    
}

NONE_TEMPLATE_TYPES= ["buttons","images","url","image","document","documents","video","videos","audios"]
PROVIDER_CONFIG = {
    "airtel": {
        "base_url": "https://iqwhatsapp.airtel.in/gateway/airtel-xchange/basic/whatsapp-manager/v1",
        "media_types": ["image", "document", "audio", "video"],
        "response_mapping": {
            "message_request_id": "messageRequestId",
            "message_status": "status",
            "response_code": "code",
            "response_success": "success"
        }
    },
    "tcl": {
        "base_url": "https://api.apigw.tatacommunications.com/v1/whatsapp/messages",
        "media_types": ["image", "document", "audio", "video"],
        "response_mapping": {
            "message_id": "id"
        }
    },
    "meta": {
        "base_url": "https://graph.facebook.com/v22.0",
        "media_types": ["image", "document", "audio", "video"],
        "response_mapping": {
            "message_id": "id"
        }
    },
    "gupshup": {
        "base_url": "https://api.gupshup.io/sm/api/v1/msg",
        "media_types": ["image", "document", "audio", "video"],
        "response_mapping": {
            "message_id": "messageId",
            "message_status": "status"
        }
    },
    "rml": {
        "base_url": "https://apis.rmlconnect.net/wba/v1/messages",
        "media_types": ["image", "document", "audio", "video"],
        "response_mapping": {
            "api_response_message": "message",
            "message_status": "status",
            "message_id": "request_id"
        }
    },
    "concord":{
        "base_url": "https://wa-crm.concordtechnosoft.com/api/meta/v19.0/272801029247445/messages",
        "media_types":["image", "document", "audio", "video"],
        "response_mapping": {
            "api_response_message": "message",
            "message_status": "message_status",
            "message_id": "request_id"
        }

    }
}
   



logger.info(f"GRYD_COMMUNICATION_SERVICE:{GRYD_COMMUNICATION_SERVICE}")
logger.info(f"GRYD_COMMUNICATION_STATUS_SERVICE: {GRYD_COMMUNICATION_STATUS_SERVICE}")
logger.info(f"GRYD_COMMUNICATION_CAMPAIGN_SERVICE: {GRYD_COMMUNICATION_CAMPAIGN_SERVICE}")

config={
    "broker_type": GRYD_COMMUNICATION_BROKER,
    "timeout":GRYD_COMMUNICATION_TIMEOUT,
    "wait_time_to_shutdown":GRYD_COMMUNICATION_SHUTDOWN_TIMEOUT
    }
gryd.SERVICE = GRYD_COMMUNICATION_SERVICE
gryd.set_queue_manager(config = config)
gryd.__CUSTOM_MODULE__ = "COMMUNICATION"
logger.info(f"[INITGRYD] Intaializing  {gryd.__CUSTOM_MODULE__ } Worker")
