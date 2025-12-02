from typing import Union, Dict, Any
from ai_service import ai_service_app
from agents.base_agent import BaseAgent
import requests
from utils import *

logger = get_logger(__name__)

class ConversationAgent(BaseAgent):
    def __init__(self, source=None, segment_classifier_result=None, propensity_result=None, model_identifier="azure-gpt-4o", initial_prompt=None):
        super().__init__(
                source=source, 
                segment_classifier_result=segment_classifier_result,
                model_identifier=model_identifier
            )
        
        self.data=self._load_json(source=source)

        self.segment_classifier_result=segment_classifier_result 
        self.segment=self.segment_classifier_result["detected_segment"]
        self.promo_message=self.segment_classifier_result["promotional_message"]
        self.media_links=self.segment_classifier_result["media_links"]

        self.propensity_result=propensity_result
        self.propensity_score=self.propensity_result["scores"]
        self.propensity_reasoning=self.propensity_result["reasoning"]

        self.llm=lambda messages: ai_service_app.get_llm_response(messages=messages, model_identifier=model_identifier)
        self.initial_prompt=initial_prompt  

    def system_prompt(self):
        base_prompt = f"""
        You are a Conversational Conversion AI designed to engage potential car buyers.

        ### Detected Customer Segment:
        {self.segment}

        ### Initial Promotional Message:
        {self.promo_message}

        ### Propensity Score based on User Interaction Data:
        {self.propensity_score}

        ### Propensity Reasoning:
        {self.propensity_reasoning}

        ### User Interaction Data:
        {self.data}

        ### Your Goals:
        1. Start by showing the promotional message ONLY on first turn and ask a conversational starter question.
        2. Answer customer questions accurately (features, variants, price, comparisons, offers).
        3. Maintain tone according to their segment.
        4. Build trust, give helpful information.
        5. Slowly guide the user toward sharing personal info (name, phone, email).
        6. Ask for details *only after answering 2-3 queries*.
        7. Never come off as pushy.
        """
        if self.initial_prompt:
            return f"{self.initial_prompt}\n{base_prompt}"

        return base_prompt
    
    # ### Output Format:
    #     ALWAYS return valid JSON. This is a strictly defined format.:
    #     {{
    #         "response": "<bot reply>",
    #         "stage": "<info|assist|lead_capture>"
    #     }}
    
    def trim_history(self, history, max_turns=5):
        max_messages = max_turns * 2
        return history[-max_messages:]

    def chat(self, user_message: str, history: list = []):
        if not history:
            return {"response": self.promo_message, "stage": "promo"}

        messages = [{"role": "system", "content": self.system_prompt()}]

        logger.info(f"history: {history}, type: {type(history)}, length: {len(history)}") #, type(history[0]), len(history))

        history = self.trim_history(history)
        messages += history
        messages.append({"role": "user", "content": user_message})

        llm_result = self.llm(messages)
        bot_json = {"response": llm_result, "stage": "info"}
        # bot_json = self.extract_json_from_llm_response(llm_result)
        logger.info(f"bot_json: {bot_json}")
        if not isinstance(bot_json, dict) or bot_json is None:
            bot_json = {"response": "I'm sorry, I might have missed that. Could you please rephrase?", "stage": "crash"}
        return bot_json

