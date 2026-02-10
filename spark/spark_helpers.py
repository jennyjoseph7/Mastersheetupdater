import sys
import os, re
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from config import hp, \
    GRYD_FILE_USER_ID, \
    GRYD_FILE_API_KEY, \
    GRYD_FILE_SERVER_URL

mlogger = hp.get_logger(__name__)

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
