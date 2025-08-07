
from ai_service import ai_service_app
from .prompts import *
from .utils import extract_valid_json_blocks, model_list
from .get_models import car_models
from utils import get_logger
from agents.base_agent import BaseAgent

logger = get_logger(__name__)

class CompetitorAnalysis(BaseAgent):


    def __init__(self, source, model_identifier='azure-gpt-4o',top_n=5,top_competitors=2):
        self.top_competitors=top_competitors
        self.top_n = top_n
        self.model_identifier = model_identifier
        source_data =self._load_json(source)
        self.source_data ={
            "user_choice" : source_data.get("model") or source_data.get("interested_models")[0]
        }        
        
    def validate_model(self,user_prompt):
        messages=create_model_match_prompt(user_prompt,[model for models in model_list.values() for model in models])
        try:
            
            raw_llm_response = ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        except Exception as e:
            return user_prompt
        return raw_llm_response

    def get_competitor(self,user_choice,models_not_user_brand):
        messages=get_competitor_model_prompt(user_choice,models_not_user_brand,top_n=self.top_competitors)
        try:
            raw_llm_response = ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        except Exception as e:
            return 'None'
        return eval(raw_llm_response)

    def get_compared_cars(self):
        compared=[]
        user_model=self.source_data.get("user_choice")
        logger.info(f"user model: {user_model}")
        user_choice = car_models(model=self.validate_model(user_model),top_n=self.top_n)
        if user_choice:
            user_brand=user_choice[0].get("brand")
            logger.info(f"user brand: {user_brand}")
        else:
            user_brand="None"
        models_not_user_brand = [model for brand, models in model_list.items() if brand != user_brand for model in models]

        compared_cars=self.get_competitor(user_model,models_not_user_brand)
        logger.info(f"compared_cars: {compared_cars}")
        if isinstance(compared_cars, list):
            for model in compared_cars:
                compared.append(car_models(model=self.validate_model(model),top_n=self.top_n))

        else:
            compared.append(car_models(model=self.validate_model(compared_cars),top_n=self.top_n))

        return compared,user_choice



    def get_analysis(self):
        compared_car_data, user_choice = self.get_compared_cars()
        system_prompt, user_prompt =comparison_prompt(user_choice, compared_car_data)
        messages = [
            {"role": "system", "content": system_prompt},
              {"role": "user", "content": user_prompt}
              ]
        logger.info(f"Using model: {self.model_identifier}")
        raw_llm_response = ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        try:
            formated_json=extract_valid_json_blocks(raw_llm_response)
            logger.info("Extracted and validated JSON:\n")
        except ValueError as e:
            formated_json={}
            logger.info(e)
        
        formated_json['compared_cars_data'] = compared_car_data
        return formated_json



if __name__=="__main__":
    fp = "/Users/daveai/Documents/SocioGraph/ppp.json"
    comp_agent = CompetitorAnalysis(fp, model_identifier='azure-gpt-4o')
    print(comp_agent.get_analysis())

