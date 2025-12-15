# config/app_config.py
import os
import json
import yaml
from pathlib import Path
from dotenv import load_dotenv
from gryd_worker import gryd_helpers as ghp
logger=ghp.get_logger(__name__)

load_dotenv()


class DynamicConfig:
    """
    Loads configuration from:
    1️⃣ System environment variables (os.environ)
    2️⃣ YAML/JSON config file
    3️⃣ Default values in class
    """

    def __init__(self, config_file: str | None = None):
        logger.info("Loading Config file")
        self._config_data = {}

        if config_file and Path(config_file).exists():
            ext = Path(config_file).suffix.lower()
            with open(config_file, "r") as f:
                if ext in [".yaml", ".yml"]:
                    self._config_data = yaml.safe_load(f) or {}
                elif ext == ".json":
                    self._config_data = json.load(f) or {}
                else:
                    raise ValueError("Config file must be .yaml, .yml, or .json")

    # ---- Generic getter with priority: ENV > config file > default ----
    def get(self, key: str, default=None):
        return os.getenv(key.upper(), self._config_data.get(key, default))
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Fetch a boolean config value: ENV > config file > default."""
        val = os.getenv(key.upper(), self._config_data.get(key, default))
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.strip().lower() in ("true", "1", "yes", "y")
        return bool(val)


    # ---------------- BASIC APP CONFIG ----------------
    @property
    def environment(self) -> str:
        return self.get("environment", "development")

    @property
    def host(self) -> str:
        return self.get("host", "0.0.0.0")

    @property
    def port(self) -> int:
        return int(self.get("port", 5000))

    # ---------------- COMMUNICATION SERVICES ----------------
    @property
    def gryd_communication_service(self) -> str:
        return self.get("GRYD_COMMUNICATION_SERVICE", "autocrm-communication")

    @property
    def gryd_communication_broker(self) -> str:
        return self.get("GRYD_COMMUNICATION_BROKER", "sqs")

    @property
    def gryd_communication_timeout(self) -> int:
        return int(self.get("GRYD_COMMUNICATION_TIMEOUT", 10))

    @property
    def gryd_communication_shutdown_timeout(self) -> int:
        return int(self.get("GRYD_COMMUNICATION_SHUTDOW_TIMEOUT", 43200))

    # ---------------- CONVERSATION SERVICES ----------------
    @property
    def convers_service_name(self) -> str:
        return self.get("CONVERS_SERVICE_NAME", "autocrm-conversation")

    @property
    def convers_task_name(self) -> str:
        return self.get("CONVERS_TASK_NAME", "converse")

    # ---------------- CAMPAIGN CONFIG ----------------
    @property
    def whatsapp_message_split_length(self) -> int:
        return int(self.get("WHATSAPP_MESSAGE_SPLIT_LENGTH", 4000))

    @property
    def campaign_max_batch_size(self) -> int:
        return int(self.get("CAMPAIGN_MAX_BATCH_SIZE", 100))

    @property
    def campaign_max_trigger(self) -> int:
        return int(self.get("CAMPAIGN_MAX_TRIGGER", 10000))

    @property
    def campaign_batch_sleep_time(self) -> int:
        return int(self.get("CAMPAIGN_BATCH_SLEEP_TIME", 100))

    @property
    def voice_campaign_base_url(self) -> str:
        return self.get("VOICE_CAMPAIGN_BASE_URL", "https://ambal.loca.lt")
    @property
    def max_model_conn_retry(self) -> int:
        return int(self.get("MAX_MODEL_CONN_RETRY", 5)) or 5

    # ---------------- MESSAGING + PERFORMANCE ----------------
    @property
    def sleep_over_message(self) -> float:
        value = float(self.get("SLEEP_OVER_MESSAGE", 0.5)) or 0.5
        # clamp between 0.7 and 1.0
        return min(max(value, 0.7), 1.0)

    @property
    def file_chunk_size(self) -> int:
        return int(self.get("FILE_CHUNK_SIZE", 1024 * 1024))

    @property
    def db_timezone(self) -> str:
        return self.get("DB_TIMEZONE", "Asia/Kolkata")

    # ---------------- Representation ----------------
    def __repr__(self):
        return f"<DynamicConfig env={self.environment} port={self.port}>"
    @property
    def gryd_communication_webhook_async(self) -> bool:
        return self.get_bool("GRYD_COMMUNICATION_WEBHOOK_ASYNC",True) #it shd be set to false by default later change it
    
    @property
    def gryd_campaign_user_detail(self)->str:
        '''Gryd Model to store user campaign details'''
        return self.get("GRYD_CAMPAIGN_USER_DETAIL","gryd_campaign_user_detail")
    
    @property
    def WHATSAPP_MAX_MESSAGE_PER_DAY(self)->int:
        return int(self.get("WHATSAPP_MAX_MESSAGE_PER_DAY",100000))

    @property
    def EMAIL_MAX_MESSAGE_PER_DAY(self)->int:
        return int(self.get("EMAIL_MAX_MESSAGE_PER_DAY",100000))

    @property
    def VOICE_MAX_MESSAGE_PER_DAY(self)->int:
        return int(self.get("VOICE_MAX_MESSAGE_PER_DAY",20000))

    @property
    def GRYD_CAMPAIGN_USER_DETAIL(self)->str:
        return str(self.get("GRYD_CAMPAIGN_USER_DETAIL","gryd_campaign_user_detail"))
    @property    
    def GRYD_CAMPAIGN_USER_DETAIL_ARCHIVE(self)->str:
        return str(self.get("GRYD_CAMPAIGN_USER_DETAIL_ARCHIVE","gryd_campaign_user_detail_archive"))
    @property 
    def GRYD_CAMPAIGN_USER_INTERACTION(self)->str:
        return str(self.get("GRYD_CAMPAIGN_USER_INTERACTION","gryd_campaign_user_interaction"))
    
    @property
    def GRYD_CAMPAIGN(self)->str:
        return str(self.get("GRYD_CAMPAIGN","gryd_campaign"))
    
    
    @property
    def GRYD_CAMPAIGN_STATUS_CHECK(self)->str:
        return str(self.get("GRYD_CAMPAIGN_STATUS_CHECK","gryd_campaign_status_check"))
    
    @property
    def ENVIRONMENT(self)->str:
        return str(self.get("ENVIRONMENT","test"))
    
    @property
    def CONVERSATION_BASE_URL(self)->str:
        return str(self.get("CONVERSATION_BASE_URL","https://test.iamdave.ai"))
    