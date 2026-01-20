import json
from typing import Dict
from pydantic import BaseModel
import plotly.graph_objects as go
from agents.base_agent import BaseAgent
from ai_service import ai_service_app
from utils import *

logger = get_logger(__name__)

AFFINITY_DIMENSIONS = [
    "adventure",
    "offroad",
    "performance",
    "identity",
    "family",
    "price_comfort",
    "achievement",
    "community"
]

class AffinityEngineAgent(BaseAgent):
    def __init__(self):
        self.llm = lambda messages : ai_service_app.get_llm_response(messages=messages, model_identifier="azure-gpt-4o")

    def _build_prompt(self, interaction_json: dict) -> str:
        messages = []
        system_prompt = f"""
        You are an Automotive Affinity Scoring Agent.
        You will be provided with a JSON, It can be a customer interaction JSON or a Cohort Classification JSON.

        Analyze the provided JSON and assign affinity scores
        between 0 and 1 for each dimension listed below.

        Dimensions:
        {", ".join(AFFINITY_DIMENSIONS)}

        Guidelines:
        - Understand the provided JSON. (Either a customer interaction JSON or a Cohort Classification JSON). If it is a customer interaction JSON, Please understand the customer's profile, behavior, preferences, and goals. It can be a customer lead information or Interaction JSON or Cohort Classification JSON.
        - Final affinity scores would be for this customer or cohort only.
        - Scores must be floats between 0 and 1
        - Use ONLY observed interactions
        - Provide a short reasoning for each score
        - Return STRICT JSON only

        Expected Output Format:
        {{
        "affinity_scores": {{
            "adventure": 0.0,
            "offroad": 0.0,
            "performance": 0.0,
            "identity": 0.0,
            "family": 0.0,
            "price_comfort": 0.0,
            "achievement": 0.0,
            "community": 0.0
        }},
        "llm_reasoning": "<your reasoning here in natural language 5-6 sentences max. Customer/Cohort information reasoning can work better.>",
        }}

        Interaction JSON:
        {json.dumps(interaction_json, indent=2)}
        """

        messages.append({"role": "system", "content": system_prompt})
        return messages

    def _create_spider_chart(self, affinity_scores: Dict[str, float]) -> Dict:
        labels = list(affinity_scores.keys())
        values = list(affinity_scores.values())

        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=labels + [labels[0]],
            fill='toself',
            name='User Affinity',
            line=dict(color='red'),
            # fillcolor='rgba(255,0,0,0.3)'
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )
            ),
            showlegend=False,
            # paper_bgcolor="rgba(0,0,0,0)",
            # plot_bgcolor="rgba(0,0,0,0)"
        )

        return fig.to_plotly_json()

    def run(self, interaction_json: dict, brochure_url = None, product_website_url=None):
        prompt = self._build_prompt(interaction_json)

        
        add_on = f"""
        Analyze the Product brochure and website. Understand the Product's features, specifications etc."""
        if brochure_url:
            brochure_content = self.fetch_brochure_content(brochure_url = brochure_url)
            prompt.append({
                "role": "assistant", 
                "content": f"Product brochure content: {json.dumps(brochure_content, indent=2)} \n {add_on}"
                })

        if product_website_url:
            product_website_content = self.fetch_product_details_from_website(website_url = product_website_url)
            prompt.append({
                "role": "assistant", 
                "content": f" Product website content: {json.dumps(product_website_content, indent=2)} \n {add_on}"
                })

        llm_response = self.llm(prompt)
        parsed = self.extract_json_from_llm_response(llm_response)

        # Safety clamp
        for k in parsed["affinity_scores"]:
            parsed["affinity_scores"][k] = max(
                0.0, min(1.0, parsed["affinity_scores"][k])
            )

        fig_json = self._create_spider_chart(parsed["affinity_scores"])

        return {
            "affinity_scores": parsed["affinity_scores"],
            "llm_reasoning": parsed["llm_reasoning"],
            "affinity_fig_json": fig_json
        }
