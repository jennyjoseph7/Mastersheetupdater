import sys
import os, re
from os.path import dirname, abspath, join as joinpath
import requests
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from config import hp, \
    GRYD_FILE_USER_ID, \
    GRYD_FILE_API_KEY, \
    GRYD_FILE_SERVER_URL

mlogger = hp.get_logger(__name__)

MIME_TYPES = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'webp': 'image/webp',
    'svg': 'image/svg+xml',
    'pdf': 'application/pdf',
}

def download_file(url, local_path = None, logger = None):
    logger = logger or mlogger
    logger.info(f"Downloading file from URL: {url}")
    response = requests.get(url)
    response.raise_for_status()
    if not local_path:
        return response.content
    with open(local_path, 'wb') as f:
        f.write(response.content)
    logger.info(f"File downloaded and saved to: {local_path}")
    return local_path

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
    logger = logger or mlogger
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
