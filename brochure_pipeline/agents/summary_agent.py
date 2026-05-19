import os
import json
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(dirname(abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from bp_utils import get_logger
from ai_service import ai_service_app
from brochure_pipeline.agents.base_agent import BaseAgent

logger = get_logger(__name__)


llm_service = lambda x: ai_service_app.get_llm_response(
    messages=x,
    model_identifier="gcp-gemini-2.5-flash",
    temperature=0.1 
)

class VectorIngestionAgent(BaseAgent):
    def __init__(self, **kwargs) -> None:
        """Initialize the vector ingestion agent"""
        self.config = kwargs if kwargs else {}
        logger.info("VectorIngestionAgent initialized")
        
        prompt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "prompt", "summary_prompt.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_instruction = f.read().strip()
            logger.info(f"Loaded vector instruction from: {prompt_path}")
        except FileNotFoundError:
            logger.error(f"FATAL: Prompt file not found at {prompt_path}")
            self.system_instruction = ""

    def messages_vector_gen(self, brochure_text: str, expected_variants: list) -> list:
        """Payload for Vector Summary Generation"""
        
        prompt = f"""
        Please generate the vector database summaries for the following brochure data.
        
        === EXPECTED VARIANTS MAP ===
        Use this list to map the "variant_id" in your JSON output:
        {json.dumps(expected_variants, indent=2)}
        
        === BROCHURE TEXT ===
        {brochure_text}
        """
        return [
            {"role": "system", "content": self.system_instruction},
            {"role": "user", "content": prompt}
        ]

    def run(self, brochure_text: str, expected_variants: list) -> dict:
        """Executes the Vector Summary Generation"""
        if not self.system_instruction: 
            return {}
            
        messages = self.messages_vector_gen(brochure_text, expected_variants)
        response = llm_service(messages)
        
        # Use your BaseAgent's JSON extraction
        parsed_json = self.extract_json_from_llm_response(response)
        
        # Validation: Ensure we got a dictionary back
        if isinstance(parsed_json, dict):
             # Handle cases where the LLM wraps the result in a "data" key (common in your previous agent)
            if "data" in parsed_json:
                return parsed_json["data"]
            return parsed_json
            
        return {}