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
    sys.path.insert(0, BASE_DIR)

from config import AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_BROCHURE_PIPELINE_SERVICE_NAME, AutocrmModel

GRYD_SERVICE = AUTOCRM_BROCHURE_PIPELINE_SERVICE_NAME


def fetch_brochure_text_from_api(document_id: str) -> str:
    """Fetches extracted chunks from chunk_saver model and concatenates them."""
    logger_local = logging.getLogger(__name__)
    try:
        chunk_saver_model = AutocrmModel('chunk_saver')
        chunks = chunk_saver_model.list(document_id=document_id, page_size=1000)

        extracted_text = []
        chunk_list = chunks.get("data", []) if isinstance(chunks, dict) else chunks

        for chunk in chunk_list:
            if isinstance(chunk, dict):
                text = chunk.get("text_content", "")
                if text:
                    extracted_text.append(str(text))

        return "\n\n".join(extracted_text)
    except Exception as e:
        logger_local.error(f"Failed to fetch brochure text from chunk_saver API for {document_id}: {e}")
        return ""

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
