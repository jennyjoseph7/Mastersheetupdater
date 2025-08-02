import os 
import sys 
import traceback
from typing import Union, Dict, Any
from urllib.parse import urlparse
import requests
import json

class BaseAgent:
    def __init__(self):
        pass

    def _load_json(self, source : Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """Load JSON from a dict, local path, or URL."""
        if isinstance(source, dict):
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