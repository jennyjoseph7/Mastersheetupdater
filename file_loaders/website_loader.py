import requests
from typing import List, Optional
from bs4 import BeautifulSoup
from munch import Munch
from cleantext import clean
from utils import get_logger, generate_id_using_string

logger = get_logger(__name__)

class WebsiteLoader:
    def __init__(
        self,
        url: str,
        source: Optional[str] = None,
        timeout: int = 20,
        headers: Optional[dict] = None,
    ):
        self.url = url
        self.source = source or url
        self.timeout = timeout
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (compatible; WebsiteLoader/1.0)"
        }
        self.file_id = generate_id_using_string(string=self.url)

    def load(self, *args, **kwargs) -> List[Munch]:
        """
        Loads the website raw content
        """
        logger.info(f"Loaded website: {self.url}")
        
        try:
            response = requests.get(self.url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Error fetching {self.url}: {e}")
            raise

        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text()

        metadata = {
            "source": self.source,
            "url": self.url,
            "file_id": self.file_id,
            "content_type": "website",
        }
        
        
        if soup.title and soup.title.string:
            metadata["title"] = soup.title.string.strip()
            
        meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta_desc and meta_desc.get("content"):
            metadata["description"] = meta_desc.get("content").strip()
            
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            metadata["language"] = html_tag.get("lang")

        if "additional_metadata" in kwargs:
            logger.info("Adding additional metadata...")
            metadata.update(kwargs["additional_metadata"])

        doc = Munch(page_content=text.strip(), metadata=metadata)
        return [doc]

    def _load(self, *args, **kwargs) -> List[Munch]:
        """
        Returns:
        [
            {
                page_content: str,
                metadata: dict
            }
        ]
        """
        logger.info(f"Loading website: {self.url}")

        try:
            response = requests.get(self.url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Error fetching {self.url}: {e}")
            raise

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]): # Remove noise
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)

        logger.info("Cleaning website text...")
        text = clean(
            text,
            fix_unicode=True,
            to_ascii=True,
            lower=True,
            no_line_breaks=False,
            no_urls=False,
            no_emails=False,
            no_phone_numbers=False,
            no_numbers=False,
            no_digits=False,
            no_currency_symbols=False,
            no_punct=False,
            replace_with_punct="",
            replace_with_url="<URL>",
            replace_with_email="<EMAIL>",
            replace_with_phone_number="<PHONE>",
            replace_with_number="<NUMBER>",
            replace_with_digit="0",
            replace_with_currency_symbol="<CUR>",
            lang="en",
        )

        metadata = {
            "source": self.source,
            "url": self.url,
            "file_id": self.file_id,
            "content_type": "website",
        }
        if "additional_metadata" in kwargs:
            logger.info("Adding additional metadata...")
            additional_metadata = kwargs["additional_metadata"]
            metadata.update(additional_metadata)
            
        doc = Munch(page_content=text, metadata=metadata)
        return [doc]