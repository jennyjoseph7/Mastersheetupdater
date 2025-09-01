# from ai_service import ai_service_app
# from .prompts import *
# from .utils import extract_valid_json_blocks, model_list
# from .get_models import car_models
# from utils import get_logger
# from agents.base_agent import BaseAgent
# import random
# import json
# import os

# logger = get_logger(__name__)

# # Preload special model JSONs
# def load_special_json(file_name):
#     try:
#         with open(file_name, "r") as f:
#             logger.info(json.load(f))
#             return json.load(f)
#     except Exception as e:
#         logger.error(f"Error loading {file_name}: {e}")
#         return None

# special_models = {
#     "fronx": load_special_json("./agents/competitor_analysis_agent/fronx.json"),
#     "grand_vitara": load_special_json("./agents/competitor_analysis_agent/grand_vitara.json"),
#     "baleno": load_special_json("./agents/competitor_analysis_agent/baleno.json"),
#     "invicto": load_special_json("./agents/competitor_analysis_agent/invicto.json"),
# }



# class CompetitorAnalysis(BaseAgent):

#     def __init__(self, source, model_identifier='azure-gpt-4o', top_n=5, top_competitors=2):
#         self.top_competitors = top_competitors
#         self.top_n = top_n
#         self.model_identifier = model_identifier
#         source_data = self._load_json(source)
#         self.source_data = {
#             "user_choice": source_data.get("model") or source_data.get("interested_models", [None])[0]
#         }

#     def validate_model(self, user_prompt):
#         messages = create_model_match_prompt(
#             user_prompt,
#             [model for models in model_list.values() for model in models]
#         )
#         try:
#             raw_llm_response = ai_service_app.get_llm_response(
#                 messages=messages, model_identifier=self.model_identifier
#             )
#         except Exception as e:
#             logger.error(f"Validation fallback for {user_prompt}: {e}")
#             return user_prompt
#         return raw_llm_response

#     def get_competitor(self, user_choice, models_not_user_brand):
#         messages = get_competitor_model_prompt(
#             user_choice, models_not_user_brand, top_n=self.top_competitors
#         )
#         try:
#             raw_llm_response = ai_service_app.get_llm_response(
#                 messages=messages, model_identifier=self.model_identifier
#             )
#         except Exception as e:
#             logger.error(f"Competitor selection fallback: {e}")
#             return models_not_user_brand
#         try:
#             return eval(raw_llm_response)
#         except Exception:
#             return models_not_user_brand

#     def get_compared_cars(self):
#         compared = []
#         user_model = str(self.source_data.get("user_choice", "")).lower()
#         logger.info(user_model)
#         #user_choice = None

#         # Load special JSON only when that model is chosen
#         user_choice = load_special_json(user_model)

#         # If not a special model, fallback to dynamic fetch
#         if not user_choice:
#             user_choice = car_models(model=self.validate_model(user_model), top_n=self.top_n)

#         logger.info(f"user model: {user_model}")

#         if user_choice:
#             user_brand = user_choice[0].get("brand_name")
#             logger.info(f"user brand: {user_brand}")
#         else:
#             user_brand = "None"

#         models_not_user_brand = [
#             model for brand, models in model_list.items() if brand != user_brand for model in models
#         ]

#         compared_cars = self.get_competitor(user_model, models_not_user_brand)
#         logger.info(f"compared_cars: {compared_cars}")

#         if isinstance(compared_cars, list):
#             for model in compared_cars:
#                 compared.append(car_models(model=self.validate_model(model), top_n=self.top_n))
#         else:
#             compared.append(car_models(model=self.validate_model(compared_cars), top_n=self.top_n))

#         if not compared:
#             compared = random.sample(models_not_user_brand, 2)

#         return compared, user_choice

#     def get_analysis(self):
#         compared_car_data, user_choice = self.get_compared_cars()
#         system_prompt, user_prompt = comparison_prompt(user_choice, compared_car_data)
#         messages = [
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_prompt}
#         ]
#         logger.info(f"Using model: {self.model_identifier}")

#         raw_llm_response = ai_service_app.get_llm_response(
#             messages=messages, model_identifier=self.model_identifier
#         )
#         try:
#             formated_json = extract_valid_json_blocks(raw_llm_response)
#             logger.info("Extracted and validated JSON:\n")
#         except ValueError as e:
#             formated_json = {}
#             logger.info(e)

#         formated_json['compared_cars_data'] = compared_car_data
#         logger.info(f"""**********************{formated_json},  """)
#         return formated_json


# if __name__ == "__main__":
#     fp = "/Users/daveai/Documents/SocioGraph/ppp.json"
#     comp_agent = CompetitorAnalysis(fp, model_identifier='azure-gpt-4o')
#     print(comp_agent.get_analysis())










from ai_service import ai_service_app
from .prompts import *
from .utils import extract_valid_json_blocks, model_list
from .get_models import car_models
from utils import get_logger
from agents.base_agent import BaseAgent
import random
import json
import os

logger = get_logger(__name__)

# Preload special model JSONs
def load_special_json(file_name):
    try:
        with open(file_name, "r") as f:
            data = json.load(f)
            logger.info(f"Loaded special model JSON: {file_name}")
            return data
    except Exception as e:
        logger.error(f"Error loading {file_name}: {e}")
        return None


special_models = {
    "fronx": load_special_json("./agents/competitor_analysis_agent/fronx.json"),
    "grand_vitara": load_special_json("./agents/competitor_analysis_agent/grand_vitara.json"),
    "baleno": load_special_json("./agents/competitor_analysis_agent/baleno.json"),
    "invicto": load_special_json("./agents/competitor_analysis_agent/invicto.json"),
}


class CompetitorAnalysis(BaseAgent):

    def __init__(self, source, model_identifier="azure-gpt-4o", top_n=5, top_competitors=2):
        self.top_competitors = top_competitors
        self.top_n = top_n
        self.model_identifier = model_identifier
        source_data = self._load_json(source)
        self.source_data = {
            "user_choice": source_data.get("model") or source_data.get("interested_models", [None])[0]
        }

    def validate_model(self, user_prompt):
        messages = create_model_match_prompt(
            user_prompt, [model for models in model_list.values() for model in models]
        )
        try:
            raw_llm_response = ai_service_app.get_llm_response(
                messages=messages, model_identifier=self.model_identifier
            )
        except Exception as e:
            logger.error(f"Validation fallback for {user_prompt}: {e}")
            return user_prompt
        return raw_llm_response

    def get_competitor(self, user_choice, models_not_user_brand):
        messages = get_competitor_model_prompt(
            user_choice, models_not_user_brand, top_n=self.top_competitors
        )
        try:
            raw_llm_response = ai_service_app.get_llm_response(
                messages=messages, model_identifier=self.model_identifier
            )
        except Exception as e:
            logger.error(f"Competitor selection fallback: {e}")
            return models_not_user_brand
        try:
            return eval(raw_llm_response)
        except Exception:
            return models_not_user_brand

    def get_compared_cars(self):
        compared = []
        user_model = str(self.source_data.get("user_choice", "")).lower()
        logger.info(f"User model: {user_model}")

        # Try special model first
        user_choice = special_models.get(user_model.replace(" ", "_"))

        # Fallback to dynamic fetch
        if not user_choice:
            car_list = car_models(model=self.validate_model(user_model), top_n=self.top_n)
            user_choice = car_list[0] if car_list else {}

        user_brand = user_choice[0].get("brand_name", "None")
        logger.info(f"User brand: {user_brand}")

        # Prepare competitor list
        models_not_user_brand = [
            model for brand, models in model_list.items() if brand != user_brand for model in models
        ]

        compared_cars = self.get_competitor(user_model, models_not_user_brand)
        logger.info(f"Compared cars: {compared_cars}")

        if isinstance(compared_cars, list):
            for model in compared_cars:
                print(model)
                print(self.validate_model(model))
                models_data = car_models(model=self.validate_model(model), top_n=self.top_n)
                print(models_data)
                if models_data:
                    compared.append(models_data)
        else:
            models_data = car_models(model=self.validate_model(compared_cars), top_n=self.top_n)
            if models_data:
                compared.append(models_data)

        if not compared:
            compared = random.sample(models_not_user_brand, 2)

        return compared, user_choice

    def get_analysis(self):
        compared_car_data, user_choice = self.get_compared_cars()
        system_prompt, user_prompt = comparison_prompt(user_choice, compared_car_data)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        logger.info(f"Using model: {self.model_identifier}")

        raw_llm_response = ai_service_app.get_llm_response(
            messages=messages, model_identifier=self.model_identifier
        )
        try:
            formated_json = extract_valid_json_blocks(raw_llm_response)
            logger.info("Extracted and validated JSON successfully.")
        except ValueError as e:
            formated_json = {}
            logger.warning(f"Failed to extract JSON: {e}")

        formated_json["compared_cars_data"] = compared_car_data
        logger.info(f"Final analysis JSON: {formated_json}")
        return formated_json


if __name__ == "__main__":
    fp = "/Users/daveai/Documents/SocioGraph/ppp.json"
    comp_agent = CompetitorAnalysis(fp, model_identifier="azure-gpt-4o")
    print(comp_agent.get_analysis())
