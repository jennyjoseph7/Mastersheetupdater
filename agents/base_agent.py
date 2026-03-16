import os 
import sys 
import traceback
from typing import Union, Dict, Any
from urllib.parse import urlparse
import requests
import json
import validators
from utils import *
import tempfile
from file_loaders.website_loader import WebsiteLoader
from file_loaders.pdf_loader import PDFLoader

logger = get_logger(__name__)

from gryd_worker import gryd, gryd_routes

gryd.SERVICE = 'autocrm-agent'
gryd.set_queue_manager()
agent_app = gryd_routes.make_app('autocrm_agent_app')['app']

class BaseAgent:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

<<<<<<< HEAD
    def return_data(self,purpose = "",flags = {},message = "",data = {}):
        return {"purpose":purpose,"flags" : flags,"message" : message,"data" : data}
    def return_converse_response(self,pl,intent):
        return {"placeholder":pl,"intent" : intent}
    def return_thinking_response(self,pl,title,image_url):
        return {"placeholder":pl,"title" : title,"image_url":image_url}
    def return_error_response(self,pl):
        return {"placeholder":pl,"intent" : "error"}
    
    def _load_json(self, source : Union[Dict[str, Any], str]) -> Dict[str, Any]:
=======
    def _load_json(self, source : Union[Dict[str, Any], str, None]) -> Dict[str, Any]:
>>>>>>> 58a7aa97328e83fa1bc7551219071ee799f0471d
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
<<<<<<< HEAD
                    except Exception:
                        return None
        return None
=======
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
    
    def strict_url_validator(self, url:str) ->bool:
        return validators.url(url)
    
    def fetch_product_details_from_website(self, website_url : str): 
        if website_url and self.strict_url_validator(website_url) is True:
            try:
                loader = WebsiteLoader(url=website_url)
                docs = loader.load()
                combined_content = "\n\n".join(doc.page_content for doc in docs)
                f = {'page_content': combined_content}
                logger.info(f"{json.dumps(f, indent=4, default=str)}")
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
>>>>>>> 58a7aa97328e83fa1bc7551219071ee799f0471d
