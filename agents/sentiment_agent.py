import json
import re
from ai_service import ai_service_app
from agents.base_agent import BaseAgent

class SentimentAnalysisAgent(BaseAgent):
    def __init__(self, source, model_identifier='azure-gpt-4o'):
        self.model_identifier = model_identifier
        self.source = self._load_json(source=source)
        self.data = self._load_json(source=source)
        self.scores = None

    def messages(self):
        prompt = (
            "You are a sentiment analysis engine. Given a customer interaction JSON, return the most likely:\n"
            "- user_input (short description of the user's behavior or intention)\n"
            "- sentiment_score (float between -1 and 1)\n"
            "- emotions (list of relevant emotions like 'anger', 'satisfaction', 'confusion')\n"
            "- justification (why you believe this sentiment is appropriate)\n\n"
            "Respond strictly in this format:\n"
            "{\n"
            '  "input": {\n'
            '    "user_input": "<description of user behavior>"\n'
            "  },\n"
            '  "expected_output": {\n'
            '    "sentiment_score": float,\n'
            '    "emotions": [list of strings],\n'
            '    "justification": "<short explanation>"\n'
            "  }\n"
            "}\n\n"
            f"Here is the customer JSON:\n{json.dumps(self.source, indent=2)}"
        )

        message_log = [
            {"role": "system", "content": "Answer only using factual knowledge."},
            {"role": "user", "content": prompt}
        ]
        return message_log

    def extract_json(self, text: str):
        match = re.search(r'{[\s\S]+}', text)
        if match:
            return json.loads(match.group(0))
        else:
            raise ValueError("❌ LLM response did not contain a valid JSON block.")

    def run(self):
        response = ai_service_app.get_llm_response(
            messages=self.messages(),
            model_identifier=self.model_identifier
        )
        try:
            result = self.extract_json(response)
            return result
        except Exception as e:
            return {
                "error": str(e),
                "raw_response": response
            }
