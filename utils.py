import os 
import traceback 
import logging
import time
import requests

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

GRYD_SERVICE = "autobot-agents"
GRYD_CONFIG = {
    "broker_type" : "sqs", 
    "timeout" : 10,
    "wait_time_to_shutdown" : 43200
}

#GRYD FILE_SYSTEM
GRYD_FILESYSTEM_URL = os.environ.get('GRYD_FILESYSTEM_URL', "https://file-dev.gryd.in")

#dave auth config
AUTH_HOST = os.environ.get("AUTH_HOST", "https://dashboard.iamdave.ai")
ENTERPRISE_ID = os.environ.get("AUTH_HOST_ENTERPRISE_ID")
USER_ID = os.environ.get("AUTH_HOST_USER_ID")
API_KEY = os.environ.get("AUTH_HOST_API")

AUTH_HOST_HEADERS = {
  'Content-Type': 'application/json',
  'X-I2CE-ENTERPRISE-ID': ENTERPRISE_ID,
  'X-I2CE-USER-ID': USER_ID,
  'X-I2CE-API-KEY': API_KEY
}

class GrydFileSysError(Exception):
    pass
    
def upload_file(image_byte, additional_payload = {}):
    DEFAULT_MIME_TYPE = "application/octet-stream"
    GRYD_HEADERS = AUTH_HOST_HEADERS
    GRYD_HEADERS.pop('Content-Type', None)
    file_name = "plot.png"
    gryd_api_url = f"{GRYD_FILESYSTEM_URL}/media/image"
    files = [("file", (file_name, image_byte, DEFAULT_MIME_TYPE))]

    response = requests.request("POST", gryd_api_url, headers=GRYD_HEADERS, data=additional_payload, files=files)
    if response.status_code == 200:
        return response.json()
    else:
        logger.info(f"Failed to upload file. Status code: {response.status_code}, Response: {response.text}")
        raise GrydFileSysError(str(response.json()))