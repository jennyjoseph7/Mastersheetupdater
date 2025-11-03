import json
import numpy as np
from ai_service import ai_service_app
from urllib.parse import urlparse
import requests
import os
import io
import re
from typing import Union, Dict, Any
try:
    from .base_agent import BaseAgent
except:
    from base_agent import BaseAgent


class RecommendationAgent(BaseAgent):
    def __init__(self, source=None, model_identifier='azure-gpt-4o') -> None:
        self.model_identifier : str = model_identifier
        # self.data : Union[dict, list] = self._load_json(source=source)
    

    def _extract_pattern(self,data):
        # with open("/agent/pattern.json", "r") as f:    
        #     data = json.load(f)
        return data

    def _request_data(self, data:dict) -> list[dict]:

        base_url = "https://gryd-webapp-dev-334553189554.asia-south1.run.app//gryd/api/autobot_dev/car_recommendation"

        payload = json.dumps({
        "kwargs": data
        })
        headers = {
        'X-GRYD-SESSION-ID': os.environ.get("GRYD_SESSION_ID"),
        'X-GRYD-ENTERPRISE-ID': os.environ.get('GRYD_ENTERPRISE_ID'),
        'X-GRYD-TOKEN': os.environ.get("GRYD_TOKEN"),
        'Content-Type': 'application/json',
        'X-GRYD-ROLE': 'admin',
        'X-GRYD-USER-ID': os.environ.get("GRYD_USER_ID")
        }


        try:
            response = requests.request("POST", base_url, headers=headers, data=payload)

            if "error" in response.json():
                return {"error": response.json()['error']}
        except Exception as e:
            return {"error": str(e)}

        data = response.json()
        
        if data:
            return data
        else:
            return [] 

    def main(self,data):
        data = self._extract_pattern(data)
        result = self._request_data(data)
        return result

if __name__ == "__main__":
    
    agent = RecommendationAgent()
    # fp = "/home/shreyasvaishnav/autobot_agents/aem_mock_data/5.json"
    data= {
    "user_profile": [
      {
        "question": "Got a budget in mind?",
        "answer": [
          678894557
        ]
      }
    ],
    "user_preference": [
      {
        "intent": "brand_name",
        "answer": [
          "Mahindra & Mahindra"
        ]
      },
      {
        "intent": "product_name",
        "answer": [
          "Bolero"
        ]
      }
    ],
    "Max number":   10,
    "collection": "autobot_test_22"
  }


    res=agent.main(data)
    da=(json.dumps(res, indent=4, default=str))
    print(da)

    with open("elon json.json", "w") as f:
        json.dump(res, f, indent=4)