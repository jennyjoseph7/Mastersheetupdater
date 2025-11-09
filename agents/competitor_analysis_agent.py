from ai_service import ai_service_app
from src.prompts import *
try:
    from .base_agent import BaseAgent
except ImportError:
    from base_agent import BaseAgent
import random
import json
import os
import requests
import logging
import time

def get_logger(name , log_level = 'info'):
    log_level = log_level.upper()
    if log_level not in ["DEBUG","INFO","WARNING","ERROR","CRITICAL"]:
        raise ValueError("Invalid log level .please use one of DEBUG,INFO,WARNING,ERROR,CRITICAL")
    logging.basicConfig(
        format = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s",
        level = getattr(logging,log_level))
    logging.Formatter.converter = time.gmtime
    logger = logging.getLogger(name)
    return logger

logger = get_logger(__name__)
enp_id = os.environ.get("CARDB_ENTERPRISE_ID")
user_id = os.environ.get("CARDB_USER_ID")
api_key = os.environ.get("CARDB_API_KEY")

def get_model(datas):
  dict_={}
  for data in datas:

    brand=data.get('brand_name')
    model=data.get('product_name')
    if brand in dict_: # Check if brand is already a key
      dict_[brand].append(model)
    else:
      dict_[brand]=[model] # Initialize the key with a list containing the model
  return dict_
def car_models(top_n=5, model=None, exclude=None,all_=False):
    if model and exclude:
        url = f"https://test.iamdave.ai/objects/model_variant_analysis?product_name={model}&brand_name~={exclude}"
    elif all_:
        url = f"https://test.iamdave.ai/objects/model_variant_analysis?_as_option=True"
    elif model:
        url = f"https://test.iamdave.ai/objects/model_variant_analysis?product_name={model}"
    else:
        url = "https://test.iamdave.ai/objects/model_variant_analysis"

    headers = {
        'Content-Type': 'application/json',
        'X-I2CE-ENTERPRISE-ID': enp_id,
        'X-I2CE-USER-ID': user_id,
        'X-I2CE-API-KEY': api_key,
    }

    response = requests.get(url, headers=headers)
    logger.info(f"Status Code: {response.status_code}")
    logger.info(f"Response Body: {response.text}")



    try:
        resp_json = response.json()
        if all_:
            return resp_json
        return resp_json.get("data", [])[:top_n]
    except json.JSONDecodeError:

        logger.info("Invalid JSON response")
        return []


model_list=get_model(car_models(all_=True))
logger.info(f">>>>>>>>>>> {model_list}")


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
    "fronx": load_special_json("./agents/competitor_analysis_agent/maruti_models/fronx.json"),
    "grand_vitara": load_special_json("./agents/competitor_analysis_agent/maruti_models/grand_vitara.json"),
    "baleno": load_special_json("./agents/competitor_analysis_agent/maruti_models/baleno.json"),
    "invicto": load_special_json("./agents/competitor_analysis_agent/maruti_models/invicto.json"),
}
def extract_valid_json_blocks(text, expected_keys=None):
    """
    Extracts all candidate JSON blocks from the text and returns the first valid one
    that matches optional expected top-level keys.

    Args:
        text (str): Raw text output from an LLM that may contain embedded JSON.
        expected_keys (list, optional): List of required top-level keys in the JSON object.

    Returns:
        dict: Parsed JSON object if a valid one is found and meets requirements.

    Raises:
        ValueError: If no valid JSON object is found or none meet key expectations.
    """
    candidates = []
    brace_stack = []
    start_index = None

    for i, char in enumerate(text):
        if char == '{':
            if not brace_stack:
                start_index = i
            brace_stack.append('{')
        elif char == '}':
            if brace_stack:
                brace_stack.pop()
                if not brace_stack and start_index is not None:
                    json_block = text[start_index:i+1]
                    candidates.append(json_block)

    # Try parsing each candidate
    for idx, candidate in enumerate(candidates):
        try:
            parsed = json.loads(candidate)
            if expected_keys:
                if all(key in parsed for key in expected_keys):
                    return parsed
            else:
                return parsed
        except json.JSONDecodeError:
            continue  # Try next candidate

    raise ValueError("❌ No valid JSON object found or none matched the expected structure.")






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
            user_choice = car_list if car_list else {}
            #user_choice = car_list[0] if car_list else {}

        logger.info(f"User choidee: {user_choice}")

        user_brand = user_choice[0].get("brand_name", "None")
        logger.info(f"User brand: {user_brand}")

        # Prepare competitor list
        models_not_user_brand = [
            model for brand, models in model_list.items() if brand != user_brand for model in models
        ]

        compared_cars = self.get_competitor(user_model, models_not_user_brand)
        if not compared_cars:
            compared_cars = random.sample(models_not_user_brand, 2)

        logger.info(f"Compared cars: {compared_cars}")

        if isinstance(compared_cars, list):
            for model in compared_cars:
                logger.info(f"model: {model}")
                logger.info(f"validated model:{self.validate_model(model)}")
                models_data = car_models(model=self.validate_model(model), top_n=self.top_n)
                if models_data:
                    compared.append(models_data)
        else:
            models_data = car_models(model=self.validate_model(compared_cars), top_n=self.top_n)
            if models_data:
                compared.append(models_data)


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
    fp = "/Users/daveai/auto_crm/autobot_agents/agents/src/test_agent.json"
    comp_agent = CompetitorAnalysis(fp, model_identifier="azure-gpt-4o")
    print(comp_agent.get_analysis())
