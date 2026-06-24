import os
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
import json
import re
from ai_service import ai_service_app
from agents.base_agent import BaseAgent
from gryd_worker import gryd, gryd_helpers as hp, gryd_audit_helper
mlogger = gryd.hp.get_logger(gryd.SERVICE)

class SentimentAnalysisAgent(BaseAgent):
    def __init__(self, source, model_identifier='azure-gpt-4o'):
        """
        SentimentAnalysisAgent performs multi-dimensional sentiment and emotion analytics
        on a given conversation JSON.

        Parameters:
        - source: JSON or path to JSON file containing customer interaction data.
        - model_identifier: LLM identifier (default: azure-gpt-4o)
        """
        self.model_identifier = model_identifier
        self.source = self._load_json(source=source)
        # self.data = self.source
        self.analytics = None

    def messages(self):
        """
        Builds the LLM prompt for comprehensive sentiment and emotion analysis.
        """
        prompt = f"""
        You are an advanced **Sentiment and Emotion Analysis Engine** specialized in analyzing customer interactions.

        Your task:
        - Given a JSON containing one or more customer conversations/interactions,
        - Perform **sentiment**, **emotion**, and **engagement** analysis,
        - And return the results as a **strictly valid JSON** object matching the schema below.

        ---

        ### 🧩 RESPONSE FORMAT (STRICT JSON ONLY)

        {{
        "user_input": "<short summary of what the user expressed or intended>",
        "language": "<detected language name, e.g., English, Hindi, Tamil>",

        "sentiment_score": <float between -1 and 1>,
        "emotions": [<list of emotions like 'interest', 'anger', 'satisfaction', 'confusion'>],
        "justification": "<concise reasoning supporting the sentiment classification>",
        "thinking": "<explain your analytical reasoning process step-by-step — how you derived sentiment and emotions>",

        "conversation_analytics": {{
        "total_conversations": <integer - total number of conversation turns detected>,
        "emotion_analysis": {{
            "<emotion_name>": <percentage or count>,
            ...
        }},
        "overall_sentiment_score": <float - average sentiment score across conversation>,
        "language_specific_sentiment": {{
            "<language_name>": <average sentiment score>,
            ...
        }},
        "emotional_triggers": [
            {{
            "trigger_phrase": "<key phrase or topic>",
            "associated_emotion": "<emotion>",
            "context": "<brief explanation of why it triggered this emotion>"
            }},
            ...
        ]
        }}
        }}

        ---

        ### 🧠 GUIDELINES
        1. Respond **only** with valid JSON — no extra text or commentary.
        2. Ensure **all numbers** (like scores or percentages) are **numeric values**, not strings.
        3. Use **neutral tone and evidence-based reasoning** in `justification`.
        4. The `"thinking"` field should **show your reasoning transparently**, but still in natural language (not technical logs).
        5. Focus on identifying **engagement level**, **interest**, **satisfaction**, and **emotional drivers** behind user actions.

        ---

        ### 🗂 INPUT DATA
        Below is the customer JSON to analyze:

        {json.dumps(self.source, indent=2)}

        ---

        Now, return your final JSON analysis following the exact schema above.
        """

        message_log = [
            {"role": "system", "content": "You are a factual AI sentiment analysis engine."},
            {"role": "user", "content": prompt}
        ]
        return message_log
    
    def extract_json_from_llm_response(self, response):
        return super().extract_json_from_llm_response(response)

    def run(self):
        response = ai_service_app.get_llm_response(
            messages=self.messages(),
            model_identifier=self.model_identifier
        )
        mlogger.info(f"Sentiment Analysis Response: {response}")
        try:
            parsed_json = self.extract_json_from_llm_response(response)
            return parsed_json
        except Exception as e:
            return {
                "error": str(e),
                "raw_response": response
            }
