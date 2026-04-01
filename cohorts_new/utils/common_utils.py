
import os, sys
_parent = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

import logging
import time 
import hashlib
import requests


def get_logger(name, log_level = "info"):
    log_level = log_level.upper()
    if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        raise ValueError("Invalid log level. Please use one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    # logging.Formatter.converter = time.gmtime
    logging.Formatter.converter = lambda *args: time.localtime(time.time() + 5.5*3600)
    logging.basicConfig(
        format = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s", 
        level = getattr(logging, log_level))
    logger = logging.getLogger(name)
    return logger

def generate_id_using_string(string: str, length: int = 16) -> str:
    if string is None:
        string = ""
    return hashlib.sha256(string.encode()).hexdigest()[:length]


logger = get_logger(__name__)

MIME_TYPES = {
    'aac': 'audio/aac',
    'flac': 'audio/flac',
    'wma': 'audio/x-ms-wma',
    'mpa': 'audio/mpeg',
    'aiff': 'audio/x-aiff',
    'xm': 'audio/xm',
    'm4a': 'audio/mp4',
    'pls': 'audio/x-scpls',
    'ape': 'audio/ape',  'wav': 'audio/wav',
    'au': 'audio/basic',
    'mp3': 'audio/mpeg',
    'avif': 'image/avif',
    'ps': 'application/postscript',
    'bmp': 'image/bmp',
    'jpeg': 'image/jpeg',
    'webp': 'image/webp',
    'tif': 'image/tiff',
    'jpg': 'image/jpeg',
    'tiff': 'image/tiff',
    'png': 'image/png',
    'svg': 'image/svg+xml',
    'gif': 'image/gif',
    'heif': 'image/heif',
    'webm': 'video/webm',
    'm4p': 'video/mp4',
    'mpeg': 'video/mpeg',
    'mov': 'video/quicktime',
    'gifv': 'video/gifv', 'mkv': 'video/x-matroska',
    'mp4': 'video/mp4',
    'flv': 'video/x-flv',
    'avi': 'video/x-msvideo',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'pdf': 'application/pdf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'log': 'text/plain',
    'csv': 'text/csv',
    'xls': 'application/vnd.ms-excel',
    'wpd': 'application/wordperfect',
    'ods': 'application/vnd.oasis.opendocument.spreadsheet',
    'ico': 'image/vnd.microsoft.icon',
    'md': 'text/markdown',
    'ppt': 'application/vnd.ms-powerpoint',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'txt': 'text/plain',
    'wps': 'application/vnd.ms-works',
    'msg': 'application/vnd.ms-outlook',
    'json': 'application/json',
    'yaml': 'application/x-yaml',
    'yml': 'application/x-yaml',
    'csv': 'text/csv',
}

GRYD_FILE_SERVER_URL = os.environ.get('GRYD_FILE_SERVER_URL', 'https://file-dev.gryd.in')
GRYD_FILE_USER_ID = os.environ.get('GRYD_FILE_USER_ID', 'gryd_file_system')
GRYD_FILE_API_KEY = os.environ.get('GRYD_FILE_API_KEY', 'gryd_file_system')

def func_gryd_file_system(local_path, media_type = 'document', logger = None):
    """
    Uploads a file to the Gryd File System.
    Args:
        local_path: The path to the local file to upload.
        logger: The logger to use.
        **kwargs: Additional keyword arguments.
    Returns:
        The URL of the uploaded file.
    """
    logger.info(f"Uploading file to Gryd File System: {local_path} with media type: {media_type}")
    url = f"{GRYD_FILE_SERVER_URL}/media/{media_type}"

    ext = os.path.splitext(local_path)[1].replace('.','').lower()
    content_type = MIME_TYPES[ext]

    logger.info(f'Local Path: {local_path}')
    logger.info(f'Content Type: {content_type}')

    headers = {
        'X-I2CE-ENTERPRISE-ID': 'gryd_file_system',
        'X-I2CE-USER-ID': GRYD_FILE_USER_ID,
        'X-I2CE-API-KEY': GRYD_FILE_API_KEY
    }
    with open(local_path, 'rb') as f:
        files = [('file',(os.path.basename(local_path), f, content_type))]
        response = requests.request("POST", url, headers=headers, files=files)
        logger.info(f'Gryd File System Response: {response.text}')
        if response.status_code == 200:
            resp_json = response.json()
            return resp_json.get('cdn_url')
    return None