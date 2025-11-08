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
    

    def _extract_pattern(self,input_data):
      formater={
        "brand_preference": "brand_name",
        "variant_preference": "variant_name",
        "color_preference": "available_colours",
        "model_preference": "product_name",
        "engine_type_preference": "engine",
        "transmission_preference": "transmission_type",
        "range_preference": "price",
        # "feature_preferences": "comfort_and_convenience",
        "seating_capacity_preference": "seating",
        "segment_preference": "vehicle_type"
        } 
      filter_keys = formater.keys()

      if "user_profile" not in input_data and "user_preference" not in input_data:
          
          data["user_profile"] = []
          data["user_preference"] = []

          for key, value in input_data.items():
              if key in filter_keys:
                  data["user_preference"].append({
                      "intent": key,
                      "answer": value
                  })
              else:
                  data["user_profile"].append({
                      "question": key.replace("_", " ").capitalize() + "?",
                      "answer": value
                  })


          fix_keys=[j for j in formater.keys()]
          for filter in data['user_preference']:
              intent=filter.get("intent")

              if intent in fix_keys:
                print("fixing the input intent")
                filter['intent']=[formater[intent]]
          print(data)
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



    input_data = {
          "brand_preference": ["Hyundai"],
          "product_name": ["Creta"],
          "range_preference": ["10-20 Lakh INR"],
          "usage_type": ["personal"],
          "lifestyle_type": ["family oriented"]
      }





    res=agent.main(input_data)
    da=(json.dumps(res, indent=4, default=str))
    print(da)

    with open("elon json.json", "w") as f:
        json.dump(res, f, indent=4)