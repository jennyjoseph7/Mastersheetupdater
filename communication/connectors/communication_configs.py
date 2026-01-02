# ENVIRONMENT= cfg.ENVIRONMENT
BASE_URL = "https://test.iamdave.ai"

# Communication Services
GRYD_COMMUNICATION_SERVICE = "autocrm-communication"
GRYD_COMMUNICATION_BROKER = "sqs"
GRYD_COMMUNICATION_TIMEOUT = 10
GRYD_COMMUNICATION_SHUTDOWN_TIMEOUT = 43200

# Conversation Service
CONVERS_SERVICE_NAME = "autocrm-conversation"
CONVERS_TASK_NAME = "converse"

# Campaign / Messaging
WHATSAPP_MESSAGE_SPLIT_LENGTH = 4000
CAMPAIGN_MAX_BATCH_SIZE = 100
CAMPAIGN_MAX_TRIGGER = 10000
CAMPAIGN_BATCH_SLEEP_TIME = 100
MAX_MODEL_CONN_RETRY = 5
VOICE_CAMPAIGN_BASE_URL="https://ambal.loca.lt"

# Keep a sleep time of N sec before sending whatsapp message
SLEEP_OVER_MESSAGE = 0.5

# Misc
DB_TIMEZONE = "Asia/Kolkata"
FILE_CHUNK_SIZE = 1024 * 1024

# campaign_configs for sending message as per limit
WHATSAPP_MAX_MESSAGE_PER_DAY=100000
EMAIL_MAX_MESSAGE_PER_DAY=100000
VOICE_MAX_MESSAGE_PER_DAY=20000

# TO Send WEBHOOK to Worker
GRYD_COMMUNICATION_WEBHOOK_ASYNC= True

# whatsapp configs
INBOUND = "INBOUND"
IGNORED_STATUSES = {"ACK"}

TRACKABLE_STATUSES = {"READ", "RECEIVED", "SENT", "DELIVERED", "INITIATED","FAILED"}

WA_TO_DISPOSITION = {
    "read": "contacted",
    "sent": "attempted",
    "initiated": "queued",
    "delivered": "reached",
    "failed": "failed",
    "interacted":"engaged"
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
   




