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

logger = get_logger(__name__)

class BaseAgent:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def _load_json(self, source : Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """Load JSON from a dict, local path, or URL."""
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
    
    def extract_json_from_llm_response(self, response: str) -> dict:
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
                    return None
                if not stack:
                    json_str = response[start:i + 1]
                    try:
                        return json.loads(json_str)
                    except Exception:
                        return None
        return None
    
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
        from file_loaders.website_loader import WebsiteLoader
        if website_url and self.strict_url_validator(website_url) is True:
            try:
                loader = WebsiteLoader(url=website_url)
                docs = loader.load()
                f = {}
                for doc in docs:
                    f['page_content'] = doc.page_content
                    # f['metadata'] = doc.metadata | For now we will just get the page content
                    logger.info(f"{json.dumps(f, indent=4, default=str)}")
                return f
            except Exception as e:
                logger.error(f"Error downloading brochure PDF: {e}")
                traceback.print_exc()
                return None

    def fetch_brochure_content(self, brochure_url : str):
        from file_loaders.pdf_loader import PDFLoader
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
                # logger.info(f"1st Doc : \n {docs[0].page_content if len(docs) > 0 else ''}")
                f = {}
                for doc in docs:
                    f['page_content'] = doc.page_content
                    # f['metadata'] = doc.metadata
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