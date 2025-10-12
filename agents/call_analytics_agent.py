import json
import re
from ai_service import ai_service_app
from agents.base_agent import BaseAgent


class CallQualityAnalysisAgent(BaseAgent):
    def __init__(self, source, model_identifier='azure-gpt-4o'):
        """
        CallQualityAnalysisAgent performs detailed quality, tone, and engagement
        analysis on a given call transcription or JSON.

        Parameters:
        - source: Transcribed call text or JSON containing call metadata.
        - model_identifier: LLM identifier (default: azure-gpt-4o)
        """
        self.model_identifier = model_identifier
        self.source = self._load_json(source=source)
        self.analytics = None

    def messages(self):
        """
        Builds the LLM prompt for comprehensive call quality and behavioral analysis.
        """
        prompt = f"""
        You are an expert **Call Quality and Transcription Analysis Engine** specializing in customer service and voice conversation evaluation.

        Your task:
        - Given a call transcription or call-related JSON,
        - Analyze **call quality**, **tone**, **empathy**, **clarity**, **response handling**, and **conversation dynamics**,
        - And return results as a **strictly valid JSON** object following the schema below.

        ---

        ### 🧩 RESPONSE FORMAT (STRICT JSON ONLY)

        {{
        "call_summary": "<brief summary of what the call was about>",
        "language": "<detected language name, e.g., English, Hindi, Tamil>",
        "call_quality_score": <float between 0 and 1>,
        "clarity_score": <float between 0 and 1>,
        "tone_score": <float between 0 and 1>,
        "empathy_score": <float between 0 and 1>,
        "responsiveness_score": <float between 0 and 1>,
        "key_issues_detected": [<list of major issues or concerns, if any>],
        "positive_highlights": [<list of good aspects of the call>],
        "justification": "<concise reasoning explaining the overall quality evaluation>",
        "thinking": "<transparent explanation of your analytical reasoning — how scores and insights were derived>",

        "call_analytics": {{
            "total_duration_minutes": <float>,
            "total_speaker_turns": <int>,
            "agent_to_customer_talk_ratio": <float>,
            "sentiment_distribution": {{
                "positive": <float>,
                "neutral": <float>,
                "negative": <float>
            }},
            "detected_issues": [
                {{
                "timestamp": "<hh:mm:ss if available>",
                "issue_type": "<e.g., delay, interruption, unclear speech>",
                "context": "<brief explanation>"
                }},
                ...
            ],
            "recommendations": [
                "<specific actionable feedback to improve call quality>"
            ]
        }}
        }}

        ---

        ### 🧠 GUIDELINES
        1. Respond **only** with valid JSON — no extra text or commentary.
        2. Ensure **all scores and numeric values** are floats (not strings).
        3. Base analysis on linguistic tone, empathy, and professionalism indicators.
        4. The `"thinking"` field should explain your reasoning in natural, human-readable form.
        5. If call data is incomplete, make a note under `"key_issues_detected"`.

        ---

        ### 🗂 INPUT DATA
        Below is the call transcription / JSON to analyze:

        {json.dumps(self.source, indent=2)}

        ---

        Now, return your final JSON analysis following the schema above.
        """

        message_log = [
            {"role": "system", "content": "You are a professional AI call quality and tone analysis system."},
            {"role": "user", "content": prompt}
        ]
        return message_log

    def extract_json_from_llm_response(self, response):
        """
        Extract valid JSON block from LLM response.
        """
        return super().extract_json_from_llm_response(response)

    def run(self):
        """
        Execute the LLM analysis and return parsed results.
        """
        response = ai_service_app.get_llm_response(
            messages=self.messages(),
            model_identifier=self.model_identifier
        )
        print(f"Call Quality Analysis Response: {response}")
        try:
            parsed_json = self.extract_json_from_llm_response(response)
            return parsed_json
        except Exception as e:
            return {
                "error": str(e),
                "raw_response": response
            }
