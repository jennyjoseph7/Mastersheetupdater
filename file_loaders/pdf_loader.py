import os
from typing import List, Optional
from utils import get_logger, generate_id_using_string
from pypdf import PdfReader
from munch import Munch

# from nltk.tokenize import word_tokenize
# from nltk.corpus import stopwords
# import nltk
from cleantext import clean

# nltk.download("stopwords")

logger = get_logger(__name__)


class PDFLoader:
    def __init__(self, file_path: str, source: Optional[str] = None, encoding: Optional[str] = None, tokenize: bool = False,):
        self.file_path = file_path
        self.source = source or self.file_path
        self.encoding = encoding
        self.tokenize = tokenize
        self.file_id = generate_id_using_string(string = self.file_path)

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
                    logger.info(f"Extracted text from page {text}")
                    if not text:
                        continue
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num + 1}: {e}")
                    continue

                content = text.strip()

                # ---------- Optional Tokenization ----------
                # if self.tokenize:
                #     logger.info("Performing tokenization with NLTK...")
                #     tokens = word_tokenize(content)
                #     stop_words = set(stopwords.words("english"))
                #     tokens = [
                #         word.lower()
                #         for word in tokens
                #         if word.isalpha() and word.lower() not in stop_words
                #     ]
                #     content = " ".join(tokens)

                # ---------- Cleaning ----------
                logger.info("Cleaning text content...")
                content = clean(
                    content,
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
                    "page_num": page_num + 1,
                    "filename": os.path.basename(self.file_path),
                    "file_id": self.file_id,
                }
                if "additional_metadata" in kwargs:
                    logger.info("Adding additional metadata...")
                    additional_metadata = kwargs["additional_metadata"]
                    metadata.update(additional_metadata)
                doc = Munch(page_content=content,metadata=metadata,)
                documents.append(doc)

        logger.info(f"Loaded {len(documents)} pages from PDF")
        return documents
