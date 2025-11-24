from gryd_worker import gryd, gryd_routes, gryd_helpers as hp
import os, sys
AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")
AUTOCRM_ADMIN_ID = os.environ.get("AUTOCRM_ADMIN_ID", "ananth+autocrm-app@i2ce.in")
AUTOCRM_ADMIN_PHONE_NUMBER = os.environ.get("AUTOCRM_ADMIN_PHONE_NUMBER", "99980838165")
AUTOCRM_ADMIN_PASSWORD = os.environ.get("AUTOCRM_ADMIN_PASSWORD", "D@vei2ce")
AUTOCRM_CRON_SERVICE_NAME = os.environ.get("AUTOCRM_CRON_SERVICE_NAME", "autocrm-cron")
AUTOCRM_CONVERSATION_SERVICE_NAME = os.environ.get("AUTOCRM_CONVERSATION_SERVICE_NAME", "autocrm-conversation")
AUTOCRM_CONVERSATION_SERVICE_NAME = os.environ.get("AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME", "autocrm-conversation-post-process")
AUTOCRM_AGENT_SERVICE_NAME = os.environ.get("AUTOBOT_AGENT_SERVICE_NAME", "autocrm-agent")
AUTOCRM_VOICE_SERVICE_NAME = os.environ.get("AUTOCRM_VOICE_SERVICE_NAME", "autocrm-voice")
AUTOCRM_COMMUNICATION_SERVICE_NAME = os.environ.get("AUTOCRM_COMMUNICATION_SERVICE_NAME", "autocrm-communication")
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
BASE_DIR = hp.dirname(hp.abspath(__file__))
DATA_DIR = hp.joinpath(BASE_DIR, "data")
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
