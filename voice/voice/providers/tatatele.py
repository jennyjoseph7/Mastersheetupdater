
import requests
import hashlib
import hmac
import json 
from typing import Dict, Any
import asyncio
import os, sys, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
import config

TATATELE_BASE_URL = os.environ.get("TATATELE_BASE_URL", "https://api-smartflo.tatateleservices.com/v1")
TATATELE_API_TOKEN = os.environ.get("TATATELE_API_TOKEN", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI3MDEzNTciLCJjciI6ZmFsc2UsImlzcyI6Imh0dHBzOi8vY2xvdWRwaG9uZS50YXRhdGVsZXNlcnZpY2VzLmNvbS90b2tlbi9nZW5lcmF0ZSIsImlhdCI6MTc2MzM2MzI0MiwiZXhwIjoyMDYzMzYzMjQyLCJuYmYiOjE3NjMzNjMyNDIsImp0aSI6ImV3UzJOUnRCQkpWaXl6NkoifQ.7vZB9svDAOvyEqNRLykrZBJOr2HQkvBSwOwFZuwSkvI")



class CloudPhoneAPI:
    def __init__(self,TATATELE_API_TOKEN, TATATELE_BASE_URL):
        self.TATATELE_BASE_URL = TATATELE_BASE_URL
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {TATATELE_API_TOKEN}"
        }

    def click_to_call(self, agent_number, customer_number, caller_id = None, custom_id=None, timeout=1200):
        #first make call to agent then connect to customer - need voice packets first
        url = f"{self.TATATELE_BASE_URL}/click_to_call"
        body = {
            "agent_number":agent_number,
            "destination_number": customer_number,
            "caller_id": caller_id or agent_number,
            "async": 1,
            "custom_identifier": custom_id,
            "call_timeout": timeout,
        }
        response = requests.post(url, headers=self.headers, json=body)
        return response.json()

    def click_to_call_support(self, caller_id, customer_number, api_key = None, custom_id=None, timeout=1200):
        #first make call to agent then connect to customer - need voice packets first
        url = f"{self.TATATELE_BASE_URL}/click_to_call_support"
        body = {
            "customer_number": customer_number,
            "caller_id": caller_id,
            "api_key": os.environ.get("TATATELE_CLICK_TO_SUPPORT_API_KEY","076702b7-12ef-427f-8026-dfcefc844b7d"), #api key for ramani:  a808d1c2-436b-4280-bf37-0a69dbdfedc7
            "async": 1,
            "custom_identifier": custom_id,
            "call_timeout": timeout,
        }
        response = requests.post(url, headers=self.headers, json=body)
        return response.json()

    def get_call_records(self):
        url = f"{TATATELE_BASE_URL}/call/records"
        response = requests.get(url, headers=self.headers)
        return response.json()

    def hangup_call(self, call_id):
        url = f"{TATATELE_BASE_URL}/call/hangup"
        body = {"call_id": call_id}
        response = requests.post(url, headers=self.headers, json=body)
        return response.json()
