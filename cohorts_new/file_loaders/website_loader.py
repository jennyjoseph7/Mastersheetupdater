import sys, os
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import requests
from typing import List, Optional
from bs4 import BeautifulSoup
from munch import Munch
from cleantext import clean
from cohorts_new.utils.common_utils import *
from langchain_community.document_loaders import WebBaseLoader

logger = get_logger(__name__)

class WebsiteLoader:
    def __init__(
        self,
        url: str,
        source: Optional[str] = None,
        timeout: int = 20,
        headers: Optional[dict] = None,
        extra_metadata: Optional[dict] = None
    ):
        self.url = url
        self.source = source or url
        self.timeout = timeout
        self.headers = headers or {"User-Agent": "Mozilla/5.0 (compatible; WebsiteLoader/1.0)"}
        self.file_id = generate_id_using_string(string=self.url)
        self.loader = WebBaseLoader(self.url,)
        self.extra_metadata = extra_metadata or {} 

    def load(self, *args, **kwargs) -> List[Munch]:
        documents = []
        logger.info(f"Loaded website: {self.url}")
        lang_docs = self.loader.load()
        for doc in lang_docs:
            base_metadata = {
                "source": self.source,
                "url": self.url,
                "file_id": self.file_id,
                "content_type": "website",
            }
            doc.metadata.update(base_metadata)
            doc.metadata.update(self.extra_metadata)
            doc = Munch(page_content=doc.page_content.strip(),metadata=doc.metadata)
            documents.append(doc)
        return documents