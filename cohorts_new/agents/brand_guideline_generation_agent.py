import json
import re
from ai_service import ai_service_app
import pandas as pd 
import os 
from pathlib import Path
import time
from  ..utility import UtilityMixin
from ..common_utils import *
from urllib.parse import urlparse
from typing import *
logger = get_logger(__name__)

class BrandGuidelineGeneratorAgent(UtilityMixin):
    def __init__(self, model_identifier='azure-gpt-4o', **kwargs):
        """
        Agent for generating brand guidelines for a product.

        Args & Kwargs:
            model_identifier (str): The identifier of the model to use for generating responses.
            brochure_url (str): The URL of the brochure for the product.
            product_website_url (str): The URL of the product's website.
        """
        super().__init__(model_identifier=model_identifier, **kwargs)
        self.model_identifier: str = model_identifier
        self.llm: Callable = lambda messages : ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)

        self.brochure_url = kwargs.get("brochure_url", None)
        self.product_website_url = kwargs.get("product_website_url", None)

        self.brochure_content = self.fetch_brochure_content(brochure_url = self.brochure_url)
        self.product_website_content = self.fetch_product_details_from_website(website_url = self.product_website_url)

    def run(self):
        pass 