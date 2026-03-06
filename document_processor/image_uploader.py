import requests
import logging
from io import BytesIO
from time import sleep

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_URL = "https://file-prod.gryd.in/media/image"

HEADERS = {
    "X-I2CE-API-KEY": "a3cc56a5-657c-3641-adef-18b77ae7d1bc",
    "X-I2CE-ENTERPRISE-ID": "gryd_file_system",
    "X-I2CE-USER-ID": "balaji+file-gryd@iamdave.ai",
}

def upload_image_to_cloud(pil_image, page_no, retries=3):
    """
    Uploads a PIL image to the cloud and returns the CDN URL.
    Includes retry logic for robustness.
    """
    buffer = BytesIO()
    pil_image.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)
    
    file_name = f"page_{page_no}.jpg"
    
    files = {
        "file": (file_name, buffer, "image/jpeg")
    }

    data = {
        "file_name": f"page_{page_no}",
        "category": "brochure",
        "sub_category": "brochure",
        "tags": "[maruthi]",
        "enterprise_id": "gryd_file_system"
    }

    for attempt in range(retries):
        try:
            logger.info(f"Uploading image for page {page_no} (Attempt {attempt+1}/{retries})...")
            buffer.seek(0) 
            
            resp = requests.post(
                UPLOAD_URL,
                headers=HEADERS,
                files=files,
                data=data,
                timeout=60
            )
            resp.raise_for_status()
            cdn_url = resp.json().get("cdn_url")
            if cdn_url:
                logger.info(f"Successfully uploaded: {cdn_url}")
                return cdn_url
            else:
                logger.warning(f"Upload successful but no 'cdn_url' in response: {resp.text}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to upload image for page {page_no}: {e}")
            if attempt < retries - 1:
                sleep(2) # Wait before retry
            else:
                logger.error("Max retries reached. Returning None.")
                return None
    
    return None
