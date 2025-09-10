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


class DealerLocatorAgent(BaseAgent):
    def __init__(self, source, model_identifier='azure-gpt-4o') -> None:
        self.model_identifier : str = model_identifier
        self.data : Union[dict, list] = self._load_json(source=source)
    
    def _extract_pincode_from_source(self):
        if isinstance(self.data, dict):
            if 'pincode' in self.data:
                return self.data['pincode']
            elif 'dealer_pincode' in self.data:
                return self.data['dealer_pincode']
    
        prompt = f"""
        You are given a customer JSON object:
        {self.data}

        Task: Find and return the most likely **pincode** value.
        - A pincode is usually a 6-digit number in India (e.g., 400001, 110075).
        - If multiple candidates exist, return the most relevant one.
        - Respond ONLY with the pincode string, nothing else.
        - If no pincode is found, return "None"
        """

        conversation = [
            {
                "role": "user",       
                "content": prompt
            }
        ]

        response = ai_service_app.get_llm_response(messages = conversation, model_identifier=self.model_identifier)
        if isinstance(response, str) and not "None" in response:
            response = int(response.strip())
        elif isinstance(response, str) and "None" in response:
            response = None
        return response
    
    def _request_data(self, pincode : int = None, latitude : float = None, longitude : float = None, distance : int = None, city : str = None) -> list[dict]:
        """
        Requests dealer data from the Maruti Core API.

        Parameters:
            pincode (int): The pincode for which to retrieve dealers.
            latitude (float): The latitude for which to retrieve dealers.
            longitude (float): The longitude for which to retrieve dealers.
            distance (int): The distance in kilometers to retrieve dealers for.
            city (str): The city for which to retrieve dealers.

        Returns:
            list[dict]: A list of dealers matching the given parameters.
        """
        base_url = "https://msil-core.iamdave.ai/objects/dealer?is_active=true&duplicate=True"
        if pincode:
            url = f"{base_url}&dealer_pincode={pincode}"
        elif latitude and longitude and distance:
            url = f"{base_url}&location={latitude},{longitude},{distance}"
        elif city:
            url = f"{base_url}&dealer_city={city}"
        else:
            raise ValueError("Invalid request parameters. Please provide either pincode, latitude, longitude, distance, or city.")
        headers = {
            'Content-Type': 'application/json',
            'X-I2CE-ENTERPRISE-ID': os.environ.get('DEALER_ENTERPRISE_ID'),
            'X-I2CE-API-KEY': os.environ.get('DEALER_API_KEY'),
            'X-I2CE-USER-ID': os.environ.get('DEALER_USER_ID')
        }
        try:
            response = requests.request("GET", url, headers=headers, data={})
            if "error" in response.json():
                return {"error": response.json()['error']}
        except Exception as e:
            return {"error": str(e)}

        data = response.json()['data']
        
        if data:
            return data
        else:
            return [] 

    def run(self):
        pincode = self._extract_pincode_from_source()
        data = self._request_data(pincode=pincode)
        return data

if __name__ == "__main__":
    agent = DealerLocatorAgent(source={'pincode': '110001'})
    fp = "/home/shreyasvaishnav/autobot_agents/aem_mock_data/5.json"
    agent = DealerLocatorAgent(source=fp)

    data = agent.run()
    print(json.dumps(data, indent=4, default=str))
