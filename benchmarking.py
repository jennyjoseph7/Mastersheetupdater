from ai_service import ai_service_app
import json
import os
from agents.base_agent import BaseAgent


class PersonalizationAgentBenchmarking(BaseAgent):
    def __init__(self, source: dict, model_identifier='azure-gpt-4o'):
        self.source = self._load_json(source=source)
        self.model_identifier = model_identifier
        
    def data_input():
        system_prompt = """"""
        user_prompt = """"""
        
        prompt = [
            {
                "role":"system",
                "content":system_prompt
            },
            {
                "role":"user",
                "content":user_prompt
            }
        ]
        