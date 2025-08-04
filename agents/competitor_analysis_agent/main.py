
from ai_service import ai_service_app
from .prompts import *
from .utils import extract_valid_json_blocks, model_list
from .get_models import car_models
import json
from agents.base_agent import BaseAgent

class CompetitorAnalysis(BaseAgent):


    def __init__(self, source, model_identifier='azure-gpt-4o',top_n=5):
        self.top_n = top_n
        self.model_identifier = model_identifier
        source_data =self._load_json(source)
        self.source_data ={
            "compared_cars" : source_data.get("compared_cars","None"),
            "user_choice" : source_data.get("model")
        }        
        
    def validate_model(self,user_prompt):
        messages=create_model_match_prompt(user_prompt,model_list)
        try:
            raw_llm_response = ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        except Exception as e:
            return user_prompt
        return raw_llm_response


    def get_compared_cars(self):
        compared=[]
        if isinstance(self.source_data.get("compared_cars"), list):
            for model in self.source_data.get("compared_cars"):
                compared.append(car_models(model=self.validate_model(model),top_n=self.top_n))

        else:
            compared.append(car_models(model=self.validate_model(self.source_data.get("compared_cars")),top_n=self.top_n))
        user_choice = car_models(model=self.validate_model(self.source_data.get("user_choice")),top_n=self.top_n)
        return compared,user_choice



    def get_analysis(self):
        compared_car_data, user_choice = self.get_compared_cars()
        system_prompt, user_prompt =comparison_prompt(user_choice, compared_car_data)
        messages = [
            {"role": "system", "content": system_prompt},
              {"role": "user", "content": user_prompt}
              ]
        raw_llm_response = ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        formated_json=extract_valid_json_blocks(raw_llm_response)
        formated_json['compared_cars_data'] = compared_car_data
        return formated_json



if __name__=="__main__":
    fp = "/Users/daveai/Documents/SocioGraph/ppp.json"
    comp_agent = CompetitorAnalysis(fp, model_identifier='azure-gpt-4o')
    print(comp_agent.get_analysis())

