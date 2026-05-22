
import os
import requests
from io import BytesIO
from PIL import Image
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from gryd_worker import gryd_helpers as hp

logger = hp.get_logger(__name__)
from config import GRYD_FILE_SERVER_URL, GRYD_FILE_USER_ID, GRYD_FILE_API_KEY

def gryd_image_upload(
    image,
    page_no,
    media_type: str = "image",
    document_name: str = "document",
    retries: int = 3,
) -> str | None:
    """
    Upload a PIL Image or raw bytes to the Gryd file CDN.

    Args:
        image:         PIL.Image or bytes
        page_no:       Page number / tile label (used in the filename)
        media_type:    CDN media type (default: "image")
        document_name: Prefix for the filename
        retries:       Number of upload attempts

    Returns:
        CDN URL string on success, None on failure.
    """
    url = f"{GRYD_FILE_SERVER_URL}/media/{media_type}"
    file_name = f"{document_name}_page_{page_no}.jpg"
    headers = {
        "X-I2CE-ENTERPRISE-ID": "gryd_file_system",
        "X-I2CE-USER-ID": GRYD_FILE_USER_ID,
        "X-I2CE-API-KEY": GRYD_FILE_API_KEY,
    }

    logger.info(f"Uploading image to CDN — file={file_name}")

    for attempt in range(1, retries + 1):
        buffer = None
        try:
            if isinstance(image, bytes):
                buffer = BytesIO(image)
            else:
                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=85)
                buffer.seek(0)

            files = {"file": (file_name, buffer, "image/jpeg")}
            response = requests.post(url, headers=headers, files=files, timeout=30)
            logger.info(f"CDN response (attempt {attempt}): {response.status_code} — {response.text[:200]}")

            if response.status_code == 200:
                cdn_url = response.json().get("cdn_url")
                return cdn_url
        except Exception as e:
            logger.error(f"Upload attempt {attempt} failed for {file_name}: {e}")
        finally:
            if buffer:
                buffer.close()

    logger.error(f"All {retries} upload attempts failed for {file_name}")
    return None
