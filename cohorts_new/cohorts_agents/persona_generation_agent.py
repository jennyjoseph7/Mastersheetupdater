import os 
import sys 
_parent = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
if _parent not in sys.path:
    sys.path.insert(0, _parent)
import json
import re
from ai_service import ai_service_app
from cohorts_new.utils.utility import *
from cohorts_new.utils.common_utils import *
from datetime import datetime
import uuid

logger = get_logger(__name__)


class PersonaGenerationAgent(UtilityMixin):

    def __init__(self, source, model_identifier='azure-gpt-4o'):
        self.raw_data = self._load_json(source)
        self.model_identifier = model_identifier
        self.llm = lambda messages : ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
    def _system(self, content):
        return {"role": "system", "content": content}
    def _user(self, content):
        return {"role": "user", "content": content}
    def _assistant(self, content):
        return {"role": "assistant", "content": content}
    def _extract_identifiers(self):
        system_prompt = """
        You are a data extraction assistant.
        Given a list of user session objects, extract all unique user identifiers.

        Return ONLY a valid JSON object in this exact shape:
        {
            "uids":   ["..."],
            "gaids":  ["..."],
            "fbcids": ["..."],
            "gids":   ["..."],
            "fids":   ["..."]
        }

        Rules:
        - Include only non-null, non-empty values.
        - De-duplicate values within each list.
        - If a field has no values, return an empty list.
        - Return nothing but the JSON object.
        """

        user_message = f"""
        Here are the user sessions. Extract all unique identifiers.

        Sessions:
        {json.dumps(self.raw_data, indent=2)}
        """
        messages = [
            self._system(system_prompt),
            self._user(user_message)
        ]

        logger.info("Calling LLM to extract identifiers...")
        identifiers = self.exec_json_llm_with_retry(self.llm, messages=messages)
        logger.info(f"Identifiers extracted: {identifiers}")
        return identifiers

    def _generate_persona(self, identifiers):
        system_prompt = """
You are an expert marketing analyst and customer intelligence AI.
Analyse the provided user interaction data and return a single JSON object.

The JSON must follow this exact shape:
{
    "applications": ["list of application_id values the user interacted with"],
    "human_summary": "2-3 sentence plain-English summary of the user's behaviour and intent",
    "product_profile": {
        "<category>": <float 0.0-1.0>,
        ...
    },
    "behavioral_signals": {
        "purchase_intent":  <float 0.0-1.0>,
        "research_depth":   <float 0.0-1.0>,
        "price_sensitivity":<float 0.0-1.0>,
        "brand_loyalty":    <float 0.0-1.0>,
        "urgency":          <float 0.0-1.0>
    },
    "engagement_profile": {
        "engagement_level": "low | medium | high | very_high",
        "preferred_device": "mobile | tablet | desktop",
        "session_pattern":  "researcher | browser | decisive | comparison_shopper"
    },
    "next_best_action": {
        "action":   "<specific action name>",
        "channel":  "email | sms | facebook | google_ads | push_notification | retargeting | whatsapp",
        "hook":     "<short personalised message or offer>",
        "timing":   "immediate | 24h | 3days | 1week",
        "priority": "low | medium | high | critical"
    },
    "predicted_segments": ["<segment1>", "<segment2>"],
    "lifecycle_stage": "awareness | consideration | decision | loyalty | advocacy"
}

Guidelines:
- Derive product_profile categories directly from pages visited and interactions (e.g. SUV_interest, pricing_interest, ev_interest).
- Propensity scores must reflect actual signal strength — do not default everything to 0.5.
- next_best_action must be specific and grounded in the data.
- Return ONLY the JSON object, no extra text, no markdown fences.
"""

        user_message = f"""
Analyse the following user sessions and generate the persona profile.

Sessions:
{json.dumps(self.raw_data, indent=2)}
"""

        messages = [
            self._system(system_prompt),
            self._user(user_message)
        ]

        logger.info("Calling LLM to generate persona...")
        persona = self.exec_json_llm_with_retry(self.llm, messages=messages)
        logger.info(f"Persona generated successfully. {persona}")
        return persona

    def run(self):
        logger.info(f"Starting persona generation for {len(self.raw_data)} sessions...")

        identifiers = self._extract_identifiers()
        persona = self._generate_persona(identifiers)

        virtual_profile = {
            "virtual_profile_id": f"VP_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
            "generated_at": datetime.now().isoformat(),
            "session_count": len(self.raw_data) if isinstance(self.raw_data, list) else 0,
            "identifiers": identifiers,
            **persona
        }

        logger.info(f"Virtual profile ready: {virtual_profile['virtual_profile_id']}")
        return virtual_profile


if __name__ == "__main__":
    agent = PersonaGenerationAgent(source="/home/shreyasvaishnav/autobot_agents_branch_master/autobot_agents/cohorts_new/test_files/all_session_for_a_user.json")
    profile = agent.run()
    print(json.dumps(profile, indent=2))