
from ai_service import ai_service_app
from prompts import *
import re 
from utils import extract_valid_json_blocks
import json 
from get_models import car_models
from autobot_agents.agents.base_agent import BaseAgent
class CompetitorAnalysis(BaseAgent):

    def __init__(self, source, model_identifier='azure-gpt-4o'):
        self.model_identifier = model_identifier
        source_data = _load_json(source)
        self.source_data ={
            "compared_cars" : source_data.get("compared_cars","None"),
            "user_choice" : source_data.get("model")
        }        
        self.user_choice= car_models(self.source_data.get("user_choice"))
        

    def get_compared_cars(self):
        compared=[]
        if isinstance(self.source_data.get("compared_cars"), list):
            for model in self.source_data.get("compared_cars"):
                compared.append(car_models(model))
        else:
            compared.append(car_models(self.source_data.get("compared_cars")))
        return compared



    def get_analysis(self):
        compared_car_data = self.get_compared_cars()
        system_prompt, user_prompt =comparison_prompt(self.user_choice, compared_car_data)
        messages = [
            {"role": "system", "content": system_prompt},
              {"role": "user", "content": user_prompt}
              ]
        raw_llm_response = ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        formated_json=extract_valid_json_blocks(raw_llm_response)
        formated_json['compared_cars_data'] = compared_car_data
        return formated_json


if __name__=="__main__":
    fp = "/Users/daveai/Documents/SocioGraph/autobot_agents/competitor_analysis_agent/test_file.json"
    comp_agent = CompetitorAnalysis(fp, model_identifier='azure-gpt-4o')
    print(comp_agent.get_analysis())

