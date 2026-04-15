import os 
import sys 
_parent = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
if _parent not in sys.path:
    sys.path.insert(0, _parent)
import traceback
from typing import Union, Dict, Any
from urllib.parse import urlparse
import requests
import json
import validators
import tempfile
from cohorts_new.utils.common_utils import get_logger
# from .common_utils import get_logger
from cohorts_new.file_loaders.website_loader import WebsiteLoader
from cohorts_new.file_loaders.pdf_loader import PDFLoader
import time
from gryd_worker import gryd
import time

GRYD_SERVICE_NAME = "autocrm-campaign-agents"
GRYD_CONFIG = {
    "broker_type" : "sqs", 
    "timeout" : 10,
    "wait_time_to_shutdown" : 43200
}

logger = get_logger(__name__)


class UtilityMixin:
    """Utility functions"""
    def _load_json(self, source : Union[Dict[str, Any], str, None]) -> Dict[str, Any]:
        """Load JSON from a dict, local path, or URL."""
        if source is None:
            return {}
        if isinstance(source, (dict, list)):
            return source 
        if isinstance(source, str):
            parsed = urlparse(source)
            if parsed.scheme in ("http", "https"):
                response = requests.get(source)
                response.raise_for_status()
                return response.json()
            elif os.path.isfile(source):
                with open(source, 'r') as f:
                    return json.load(f)
        raise ValueError(f"Invalid JSON source: {source}")
    
    def exec_json_llm_with_retry(self, func, *args, **kwargs):
        MAX_RETRIES = 3
        last_exception = None
        for attempt in range(1, MAX_RETRIES+1):
            try:
                func_response = func(*args, **kwargs)
                # logger.info(f"response from {func.__name__}: {func_response}")
                response = self.extract_json_from_llm_response(func_response)
                return response
            except Exception as e:
                last_exception = e
                logger.exception(f"Attempt {attempt}/{MAX_RETRIES} failed in {func.__name__}")
                if attempt < MAX_RETRIES:
                    time.sleep(2)
        raise last_exception
    
    def extract_json_from_llm_response(self, response: str):
        stack, start = [], None
        for i, ch in enumerate(response):
            if ch in "{[":
                if not stack:
                    start = i
                stack.append(ch)

            elif ch in "}]":
                if not stack:
                    continue

                opening = stack.pop()
                if (opening == "{" and ch != "}") or (opening == "[" and ch != "]"):
                    raise ValueError("Mismatched JSON brackets in response")

                if not stack:
                    json_str = response[start:i + 1]
                    try:
                        return json.loads(json_str)
                    except Exception as e:
                        raise ValueError(f"Invalid JSON content: {e}")

        raise ValueError("No valid JSON object found in response")

    def validate_url(self, url:str) -> bool: 
        try:
            if not isinstance(url, str):
                return False
            result = urlparse(url)
            if result.scheme not in ("http", "https"):
                return False
            if not result.netloc:
                return False
            return True
        except Exception as e:
            logger.error(f"Error validating URL: {e}")
            return False
    
    def strict_url_validator(self, url:str) -> bool:
        return validators.url(url)
    
    def fetch_product_details_from_website(self, website_url : str): 
        if website_url and self.strict_url_validator(website_url) is True:
            try:
                loader = WebsiteLoader(url=website_url)
                docs = loader.load()
                combined_content = "\n\n".join(doc.page_content for doc in docs)
                f = {'page_content': combined_content}
                # logger.info(f"{json.dumps(f, indent=4, default=str)}")
                return f
            except Exception as e:
                logger.error(f"Error downloading brochure PDF: {e}")
                traceback.print_exc()
                return None
        else:
            return None

    def fetch_brochure_content(self, brochure_url : str):
        if brochure_url and self.strict_url_validator(brochure_url) is True:
            temp_pdf_path = None
            try:
                response = requests.get(brochure_url, timeout=30)
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "").lower()
                if "application/pdf" not in content_type:
                    raise ValueError(f"Unsupported brochure format. Only PDF allowed. Received Content-Type: {content_type}")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(response.content)
                    temp_pdf_path = tmp.name
                logger.info(f"PDF downloaded temporarily at: {os.path.abspath(temp_pdf_path)}")
                loader = PDFLoader(file_path=temp_pdf_path)
                docs = loader.load()
                logger.info(f"Number of Documents: {len(docs)}")
                combined_content = "\n\n".join(doc.page_content for doc in docs)
                f = {'page_content': combined_content}
                logger.info(f"{json.dumps(f, indent=4, default=str)}")
                return f
            except Exception as e:
                logger.error(f"Error downloading brochure PDF: {e}")
                traceback.print_exc()
                return None
            finally:
                if temp_pdf_path and os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
                    logger.info(f"Temporary PDF file deleted: {temp_pdf_path}")
        else:
            return None