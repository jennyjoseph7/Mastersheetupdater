import os 
import traceback 
import logging
import time
import requests
import uuid
from typing import Union
import sys
import hashlib
from os.path import dirname, abspath, join as joinpath

BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from config import AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_BROCHURE_PIPELINE_SERVICE_NAME

GRYD_SERVICE = AUTOCRM_BROCHURE_PIPELINE_SERVICE_NAME

def get_logger(name, log_level = "info"):
    log_level = log_level.upper()
    if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        raise ValueError("Invalid log level. Please use one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    logging.basicConfig(
        format = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s", 
        level = getattr(logging, log_level))
    logging.Formatter.converter = time.gmtime
    logger = logging.getLogger(name)
    return logger

logger = get_logger(__name__)

def deterministic_uuid(content: Union[str, bytes]) -> str:
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
    elif isinstance(content, bytes):
        content_bytes = content
    else:
        raise ValueError(f"Content type {type(content)} not supported !")

    hash_object = hashlib.sha256(content_bytes)
    hash_hex = hash_object.hexdigest()
    namespace = uuid.UUID("00000000-0000-0000-0000-000000000000")
    content_uuid = str(uuid.uuid5(namespace, hash_hex))
    return content_uuid

def generate_model_id(model_name: str) -> str:
    if not model_name:
        return None
    short_hash = hashlib.md5(model_name.lower().encode()).hexdigest()[:6].upper()
    return f"MOD_{short_hash}"

def generate_feature_id(feature_name: str, feature_group: str = "") -> str:
    base_string = (feature_group or "") + "_" + (feature_name or "")
    short_hash = hashlib.md5(base_string.lower().encode()).hexdigest()[:6].upper()
    return f"FEAT_{short_hash}"

def generate_variant_id(model_id: str, feature_id: str, variant_value: str) -> str:
    base_string = (model_id or "") + "_" + (feature_id or "") + "_" + (variant_value or "")
    short_hash = hashlib.md5(base_string.lower().encode()).hexdigest()[:6].upper()
    return f"VAR_{short_hash}"
