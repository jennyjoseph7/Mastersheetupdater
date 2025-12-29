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


class AffinityAgentOutput(BaseModel):
    affinity_scores: Dict[str, float]
    llm_reasoning: Dict[str, str]
    affinity_fig_json: Dict


class AffinityEngineAgent(BaseAgent):
    def __init__(self):
        self.llm = lambda messages : ai_service_app.get_llm_response(messages=messages, model_identifier="azure-gpt-4o")

    def _build_prompt(self, interaction_json: dict) -> str:
        messages = []
        system_prompt = f"""
        You are an Automotive Affinity Scoring Agent.

        Analyze the following user interaction JSON and assign affinity scores
        between 0 and 1 for each dimension listed below.

        Dimensions:
        {", ".join(AFFINITY_DIMENSIONS)}

        Rules:
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
        "llm_reasoning": "<your reasoning here in natural language 5 sentences max.>",
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

    def run(self, interaction_json: dict) -> AffinityAgentOutput:
        prompt = self._build_prompt(interaction_json)

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
