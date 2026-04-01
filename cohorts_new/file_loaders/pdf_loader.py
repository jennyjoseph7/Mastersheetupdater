import sys, os
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_parent = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from typing import List, Optional
from cohorts_new.utils.common_utils import *
from pypdf import PdfReader
from munch import Munch
from cleantext import clean

logger = get_logger(__name__)

class PDFLoader:
    def __init__(
            self, 
            file_path: str, 
            source: Optional[str] = None, 
            encoding: Optional[str] = None, 
            tokenize: bool = False,
            extra_metadata: Optional[dict] = None
        ):
        self.file_path = file_path
        self.filename = os.path.basename(self.file_path)
        self.source = source or self.file_path
        self.encoding = encoding
        self.tokenize = tokenize
        self.file_id = generate_id_using_string(string = self.file_path)
        self.extra_metadata = extra_metadata or {}

    def load(self, *args, **kwargs) -> List[Munch]:
        """
        Returns a list of parsed objects:
        [{
            page_content: str,
            metadata: dict
        }]
        """
        documents: List[Munch] = []
        logger.info(f"Loading PDF: {self.file_path}")
        with open(self.file_path, "rb") as pdf_file:
            reader = PdfReader(pdf_file)
            for page_num, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    # logger.info(f"Extracted text from page {text}")
                    if not text:
                        continue
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num + 1}: {e}")
                    continue
                content = text.strip()
                # logger.info("Cleaning text content...")
                # content = clean(
                #     content,
                #     # fix_unicode=True,
                #     to_ascii=True,
                #     lower=True,
                #     no_line_breaks=False,
                #     no_urls=False,
                #     no_emails=False,
                #     no_phone_numbers=False,
                #     no_numbers=False,
                #     no_digits=False,
                #     no_currency_symbols=False,
                #     no_punct=False,
                #     replace_with_punct="",
                #     replace_with_url="<URL>",
                #     replace_with_email="<EMAIL>",
                #     replace_with_phone_number="<PHONE>",
                #     replace_with_number="<NUMBER>",
                #     replace_with_digit="0",
                #     replace_with_currency_symbol="<CUR>",
                #     lang="en",
                # )
                base_metadata = {
                    "source": self.source,
                    "page_num": page_num + 1,
                    "filename": self.filename,
                    "file_id": self.file_id,
                }

                base_metadata.update(self.extra_metadata)
                metadata = base_metadata
                
                doc = Munch(page_content=content,metadata=metadata,)
                documents.append(doc)

        logger.info(f"Loaded {len(documents)} pages from PDF")
        return documents
