import os
import json
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(dirname(abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from bp_utils import get_logger
from ai_service import ai_service_app

# Import BaseAgent from its separate file
from brochure_pipeline.agents.base_agent import BaseAgent

logger = get_logger(__name__)



llm_service = lambda x: ai_service_app.get_llm_response(
    messages=x,
    model_identifier="gcp-gemini-2.5-flash",
    temperature=0.1 
)



def generate_bulk_questions(car_name: str, feature_name: str, variant_list: list, value_type: str, description: str = "", alias: str = "") -> str:
    """
    Generates a single formatted string containing questions for ALL variants.
    Includes Feature Description and Alias (if available) to provide context to the LLM.
    """
    context_lines = [f"### FEATURE CONTEXT"]
    context_lines.append(f"Target Feature: {feature_name}")
    
    if alias and str(alias).lower() not in ["nan", "none", "", "null"]:
        context_lines.append(f"Also Known As (Alias): {alias}")
        
    if description and str(description).lower() not in ["nan", "none", "", "null"]:
        context_lines.append(f"Description: {description}")
    context_lines.append(f"Data Type: {value_type}")
    
    context_lines.append(f"INSTRUCTION: Use the description and alias above to identify this feature in the text, even if the wording differs slightly.")
    context_lines.append("-" * 20) 

    header = "\n".join(context_lines)
    
    questions = []
    v_type = str(value_type).lower().strip()
    
    for variant in variant_list:
        if "boolean" in v_type:
            q = f"Does the {car_name} {variant} variant have this feature? (Yes/No)"
        elif "number" in v_type:
            q = f"What is the count/number of this feature in the {car_name} {variant} variant?"
        else: 
            q = f"What is the specific value/type of this feature in the {car_name} {variant} variant?"
            
        questions.append(f"- Variant '{variant}': {q}")
        
    return header + "\n" + "\n".join(questions)



# AGENT CLASSES


class ConverterAgent(BaseAgent):
    def __init__(self, **converter_kwargs) -> None:
        super().__init__(config=converter_kwargs)
        logger.info("ConverterAgent initialized")
        
        batch_prompt_path = os.path.join("prompt", "converter_prompt.txt")
        try:
            with open(batch_prompt_path, "r", encoding="utf-8") as f:
                self.system_instruction = f.read().strip()
        except FileNotFoundError:
            logger.error(f"FATAL: Prompt file not found at {batch_prompt_path}")
            self.system_instruction = ""

        correction_prompt_path = os.path.join("prompt", "correction_prompt.txt")
        try:
            with open(correction_prompt_path, "r", encoding="utf-8") as f:
                self.correction_instruction = f.read().strip()
        except FileNotFoundError:
            logger.error(f"FATAL: Prompt file not found at {correction_prompt_path}")
            self.correction_instruction = ""

    def messages_batch(self, questions_text: str, value_type: str, brochure_text: str) -> list:
        prompt = f"""
        Target Feature Value Type: {value_type}
        
        Variant Questions List:
        {questions_text}
        
        Brochure Text:
        {brochure_text}
        """
        return [
            {"role": "system", "content": self.system_instruction},
            {"role": "user", "content": prompt}
        ]

    def messages_correction(self, json_entry: dict, reasoning: str, brochure_text: str) -> list:
        entry_str = json.dumps(json_entry, indent=2)
        prompt = f"""
        Target JSON Entry:
        {entry_str}

        Validation Error:
        {reasoning}

        Brochure Text:
        {brochure_text}
        """
        return [
            {"role": "system", "content": self.correction_instruction},
            {"role": "user", "content": prompt}
        ]

    def run(self, questions_text: str, value_type: str, brochure_text: str) -> list:
        if not self.system_instruction: return []
        messages = self.messages_batch(questions_text, value_type, brochure_text)
        response = llm_service(messages)
        parsed_json = self.extract_json_from_llm_response(response)
        
        if "data" in parsed_json and isinstance(parsed_json["data"], list):
            return parsed_json["data"]
        return []

    def run_correction(self, json_entry: dict, validation_reasoning: str, brochure_text: str) -> dict:
        if not self.correction_instruction: 
            return {}
            
        messages = self.messages_correction(json_entry, validation_reasoning, brochure_text)
        response = llm_service(messages)
        parsed_json = self.extract_json_from_llm_response(response)
        
        if "data" in parsed_json and isinstance(parsed_json["data"], dict):
            return parsed_json["data"]
        return {}


class MasterVariantAgent(BaseAgent):
    def __init__(self, **kwargs) -> None:
        super().__init__(config=kwargs)
        logger.info("MasterVariantAgent initialized")
        
        prompt_path = os.path.join("prompt", "master_variant_prompt.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_instruction = f.read().strip()
        except FileNotFoundError:
            logger.error(f"FATAL: Prompt file not found at {prompt_path}")
            self.system_instruction = ""

    def messages(self, brochure_text: str, car_name: str) -> list:
        prompt = f"Car Model: {car_name}\n\nBrochure Text:\n{brochure_text}"
        return [
            {"role": "system", "content": self.system_instruction},
            {"role": "user", "content": prompt}
        ]

    def run(self, brochure_text: str, car_name: str) -> list:
        if not self.system_instruction:
            return []
            
        logger.info(f"Extracting master variant list for {car_name}...")
        messages = self.messages(brochure_text, car_name)
        response = llm_service(messages) 
        
        parsed_json = self.extract_json_from_llm_response(response)

        if "data" in parsed_json and isinstance(parsed_json["data"], list):
            return parsed_json["data"]
        return []

    def identify_car_model(self, brochure_text: str) -> str:
        snippet = brochure_text[:3000]
        prompt = f"""
        Analyze the following brochure text and identify the primary Car Model Name (e.g., 'Baleno', 'Brezza', 'Swift', 'Grand Vitara').
        
        Brochure Text Snippet:
        {snippet}
        
        Return ONLY the model name as a string. Do not add "Maruti Suzuki" unless it's part of the model name (usually it's not).
        """
        messages = [
            {"role": "system", "content": "You are a car model identifier. Return only the model name."},
            {"role": "user", "content": prompt}
        ]
        
        logger.info("Identifying car model from brochure...")
        response = llm_service(messages) 
        
        car_name = response.strip().replace('"', '').replace("'", "").split('\n')[0]
        return car_name


class ValidationAgent(BaseAgent):
    def __init__(self, **kwargs) -> None:
        super().__init__(config=kwargs)
        logger.info("ValidationAgent initialized")
        
        prompt_path = os.path.join("prompt", "validation_prompt.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_instruction = f.read().strip()
        except FileNotFoundError:
            logger.error(f"FATAL: Prompt file not found at {prompt_path}")
            self.system_instruction = ""

    def messages(self, brochure_text: str, json_item_to_validate: dict) -> list:
        item_as_string = json.dumps(json_item_to_validate, indent=2)
        prompt = f"""
        Brochure_Text:
        \"\"\"
        {brochure_text}
        \"\"\"

        JSON_Item_To_Validate:
        \"\"\"
        {item_as_string}
        \"\"\"
        
        Please respond only with the validation JSON as requested.
        """
        return [
            {"role": "system", "content": self.system_instruction},
            {"role": "user", "content": prompt}
        ]

    def run(self, brochure_text: str, json_item_to_validate: dict) -> dict:
        if not self.system_instruction:
            return {"error": "Missing system instruction"}

        if not brochure_text or not json_item_to_validate:
            return {"error": "Missing inputs"}

        logger.info(f"Validating feature: {json_item_to_validate.get('feature_name')}")
        
        messages = self.messages(brochure_text, json_item_to_validate)
        response = llm_service(messages)
        parsed_json = self.extract_json_from_llm_response(response)

        if "data" in parsed_json and isinstance(parsed_json["data"], dict):
            validation_output = parsed_json["data"]
        else:
            validation_output = {
                "status": "Error", 
                "reasoning": "Could not parse LLM response.", 
                "ground_truth_value": None,
                "scores": {"semantic_match_score": 0.0},
                "raw_response": response
            }

        return {
            "validation_input": json_item_to_validate,
            "validation_output": validation_output
        }