import json
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from ai_service import ai_service_app
from urllib.parse import urlparse
import requests
import os
import io
import re
from typing import Union, Dict, Any

# print(ai_service_app.list_models(cloud="azure"))
# assert False

FEATURES = [
    'branding_and_looks',
    'safety_and_environment',
    'comfort_and_convenience',
    'technology_and_performance',
    'infotainment_and_connectivity'
]

class PropensityAgent:
    def __init__(self, source, model_identifier='azure-gpt-4o'):
        self.model_identifier = model_identifier
        self.data = self._load_json(source=source)
        self.scores = None

    def _load_json(self, source : Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """Load JSON from a dict, local path, or URL."""
        if isinstance(source, dict):
            return source 

        if isinstance(source, str):
            parsed = urlparse(source)
            if parsed.scheme in ("http", "https"):
                response = requests.get(source)
                response.raise_for_status()
                return response.json()
            elif os.path.isfile(source):
                with open(source, 'r') as f:
                    return json.load(f)

        raise ValueError(f"Invalid JSON source: {source}")

    def extract_json_from_text(self, text):
        json_pattern = r"\{.*?\}"
        matches = re.findall(json_pattern, text, re.DOTALL)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        raise ValueError("No valid JSON object found in LLM response.")

    def _build_messages(self):
        messages = []
        prompt = f"""
        You are a product analytics assistant.

        A user has interacted with a car model website. Here's the raw data:
        {json.dumps(self.data, indent=2)}

        Your task is to analyze the user's behavior and output a JSON object with exactly these five keys:
        {FEATURES}

        Each key should have a float score between 0 and 1 representing how likely the user is interested in that feature category.

        Respond with ONLY a valid JSON object like:
        {{"branding_and_looks": 0.7, "safety_and_environment": 0.8, ...}}
        Strictly follow this format.
        """
        user_message = {"role": "user", "content": prompt}
        messages.append(user_message)
        return messages
    def get_propensity_scores(self):
        messages = self._build_messages()
        response = ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        self.scores = self.extract_json_from_text(response)
        return self.scores

    def plot_spider_chart(self, format="png", scale=2):
        if self.scores is None:
            raise ValueError("Propensity scores not found. Run get_propensity_scores() first.")
        values = [self.scores.get(k, 0) for k in FEATURES]
        values += values[:1]  # Close the loop
        labels = FEATURES + [FEATURES[0]]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=labels,
            fill='toself',
            name='Propensity Scores',
            line=dict(color='royalblue', width=2)
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )
            ),
            showlegend=False,
            title="Feature Propensity Radar Chart"
        )
        img_bytes = fig.to_image(format=format, scale=scale)
        return fig, img_bytes
    
    def run(self):
        scores = self.get_propensity_scores()
        fig, img_bytes = self.plot_spider_chart()
        return scores, fig, img_bytes
    
if __name__ == "__main__":
    fp = "/home/shreyasvaishnav/autobot_agents/propensity_test_file.json"
    propensity_agent = PropensityAgent(fp, model_identifier='azure-gpt-4o')
    scores, fig, img_bytes = propensity_agent.run()
    print(scores)
