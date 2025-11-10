import os 
import sys 
import traceback
from typing import Union, Dict, Any
from urllib.parse import urlparse
import requests
import json

from gryd_worker import gryd, gryd_routes

gryd.SERVICE = 'autocrm-agent'
gryd.set_queue_manager()
agent_app = gryd_routes.make_app('autocrm_agent_app')['app']

class BaseAgent:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def return_data(self,purpose = "",flags = {},message = "",data = {}):
        return {"purpose":purpose,"flags" : flags,"message" : message,"data" : data}
    def return_converse_response(self,pl,intent):
        return {"placeholder":pl,"intent" : intent}
    def return_thinking_response(self,pl,title,image_url):
        return {"placeholder":pl,"title" : title,"image_url":image_url}
    def return_error_response(self,pl):
        return {"placeholder":pl,"intent" : "error"}
    
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
