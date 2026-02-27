import os
import json
import re
from bp_utils import get_logger
from ai_service import ai_service_app
from agents.base_agent import BaseAgent

logger = get_logger(__name__)

llm_service = lambda x: ai_service_app.get_llm_response(
    messages=x,
    model_identifier="gcp-gemini-2.5-flash",
    temperature=0.1 
)

class ColourAgent(BaseAgent):
    def __init__(self, **kwargs) -> None:
        self.config = kwargs if kwargs else {}
        logger.info("ColourAgent initialized")
        
        prompt_path = os.path.join("prompt", "colour_prompt.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_instruction = f.read().strip()
            logger.info(f"Loaded colour instruction from: {prompt_path}")
        except FileNotFoundError:
            logger.error(f"FATAL: Prompt file not found at {prompt_path}")
            self.system_instruction = ""

    def clean_json_string(self, raw_string: str) -> str:
        """Helper to strip markdown code blocks from LLM response"""
        # Remove ```json and ``` markers
        if "```" in raw_string:
            # Pattern to extract content between ```json (optional) and ```
            match = re.search(r"```(?:json)?\s*(.*)\s*```", raw_string, re.DOTALL)
            if match:
                return match.group(1).strip()
        return raw_string.strip()

    def messages_colour(self, brochure_text: str) -> list:
        prompt = f"""
        Analyze the structured brochure data below and extract all colour definitions 
        (Exterior Paints, Interior Trims, Roof Colours, Accents).
        
        Brochure Data:
        {brochure_text}
        """
        return [
            {"role": "system", "content": self.system_instruction},
            {"role": "user", "content": prompt}
        ]

    def run(self, brochure_text: str, model_year_id: str) -> list:
        if not self.system_instruction: 
            return []
            
        messages = self.messages_colour(brochure_text)
        
        try:
            raw_response = llm_service(messages)
            
            # --- DEBUGGING: LOG THE RAW RESPONSE ---
            # This ensures we see what the model actually said
            logger.info(f"Raw LLM Response: {raw_response[:500]}...") # Log first 500 chars
            
            cleaned_response = self.clean_json_string(raw_response)
            parsed_json = json.loads(cleaned_response)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parsing Failed: {str(e)}")
            logger.error(f"Full Failed Content: {raw_response}") # Log full content on error
            return []
        except Exception as e:
            logger.error(f"LLM Service Error: {str(e)}")
            return []
        
        results = []
        if "data" in parsed_json and isinstance(parsed_json["data"], list):
            results = parsed_json["data"]
            
        final_data = []
        for entry in results:
            if isinstance(entry, dict):
                entry["model_year_id"] = model_year_id
                if "finish_type" not in entry or not entry["finish_type"]:
                    entry["finish_type"] = "Metallic"
                final_data.append(entry)
                
        return final_data