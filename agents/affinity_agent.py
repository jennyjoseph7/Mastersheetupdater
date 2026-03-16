import json
from typing import Dict
from pydantic import BaseModel
import plotly.graph_objects as go
from ai_service import ai_service_app
from utils import *
from typing import *
from agents.base_agent import BaseAgent
import traceback

logger = get_logger(__name__)

DOMAIN_IDENTIFIERS = [
    "Automotive", "Healthcare", "Finance", "Insurance", "Retail",
    "Ecommerce", "Real Estate", "Travel", "Hospitality", "Education",
    "Manufacturing", "Technology / SaaS", "Telecom", "Energy", "Media & Entertainment",
    "Logistics", "FMCG", "Other"
]

DOMAIN_AFFINITY_DIMENSIONS = {
    "Automotive": {
        "dimensions": ["adventure", "offroad", "performance", "identity", "family", "price_comfort", "achievement", "community"],
        "descriptions": {
            "adventure": "Desire for exploration, new experiences, taking the road less traveled",
            "offroad": "Interest in rugged terrain, outdoor activities, capability over comfort",
            "performance": "Value placed on speed, power, handling, driving dynamics",
            "identity": "Using vehicle as self-expression, status symbol, personal brand",
            "family": "Focus on safety, space, practicality for family needs",
            "price_comfort": "Value consciousness, comfort features, practical luxury",
            "achievement": "Vehicle as success marker, premium brands, aspirational ownership",
            "community": "Belonging to owner groups, brand loyalty, social connection"
        }
    },
    "Healthcare": {
        "dimensions": ["wellness", "prevention", "convenience", "trust", "technology", "cost_sensitivity", "personalization", "community"],
        "descriptions": {
            "wellness": "Focus on holistic health, lifestyle medicine, proactive care",
            "prevention": "Interest in preventive care, early detection, health screening",
            "convenience": "Value placed on accessibility, telehealth, minimal wait times",
            "trust": "Importance of provider relationships, credentials, reputation",
            "technology": "Adoption of health tech, wearables, digital health tools",
            "cost_sensitivity": "Price consciousness, insurance coverage, value for money",
            "personalization": "Desire for customized care plans, individual attention",
            "community": "Support groups, patient communities, shared experiences"
        }
    },
    "Finance": {
        "dimensions": ["growth", "security", "convenience", "education", "prestige", "cost_sensitivity", "independence", "community"],
        "descriptions": {
            "growth": "Focus on wealth accumulation, investment returns, financial goals",
            "security": "Risk aversion, capital preservation, stable returns",
            "convenience": "Digital banking, easy access, streamlined processes",
            "education": "Interest in financial literacy, market insights, learning",
            "prestige": "Premium services, exclusive access, status symbols",
            "cost_sensitivity": "Fee consciousness, value seeking, cost optimization",
            "independence": "Self-directed investing, autonomy in decisions",
            "community": "Social trading, peer insights, advisor relationships"
        }
    },
    "Insurance": {
        "dimensions": ["protection", "peace_of_mind", "convenience", "trust", "value", "customization", "digital_engagement", "loyalty"],
        "descriptions": {
            "protection": "Comprehensive coverage, risk mitigation, safety net",
            "peace_of_mind": "Security against uncertainty, worry reduction",
            "convenience": "Easy claims, digital tools, hassle-free service",
            "trust": "Insurer reputation, claim settlement record, transparency",
            "value": "Competitive pricing, coverage-to-cost ratio, discounts",
            "customization": "Tailored policies, flexible coverage, add-ons",
            "digital_engagement": "App usage, online management, tech adoption",
            "loyalty": "Long-term relationships, multi-policy holdings, referrals"
        }
    },
    "Retail": {
        "dimensions": ["value", "experience", "convenience", "quality", "discovery", "brand_affinity", "social_influence", "sustainability"],
        "descriptions": {
            "value": "Price consciousness, deals, promotions, bargain hunting",
            "experience": "In-store ambiance, customer service, shopping enjoyment",
            "convenience": "Location, hours, easy returns, quick checkout",
            "quality": "Product durability, premium materials, craftsmanship",
            "discovery": "New products, trends, exploration, novelty seeking",
            "brand_affinity": "Brand loyalty, emotional connection, identity alignment",
            "social_influence": "Peer recommendations, social proof, trending items",
            "sustainability": "Eco-friendly products, ethical sourcing, social responsibility"
        }
    },
    "Ecommerce": {
        "dimensions": ["convenience", "value", "variety", "speed", "trust", "personalization", "social_proof", "mobile_first"],
        "descriptions": {
            "convenience": "Easy browsing, one-click ordering, saved preferences",
            "value": "Price comparison, discounts, free shipping thresholds",
            "variety": "Product selection, niche items, comparison shopping",
            "speed": "Fast delivery, same-day shipping, instant gratification",
            "trust": "Secure payments, return policy, authentic products",
            "personalization": "Recommendations, curated feeds, personalized offers",
            "social_proof": "Reviews, ratings, user-generated content",
            "mobile_first": "App usage, mobile shopping, on-the-go purchases"
        }
    },
    "Real Estate": {
        "dimensions": ["investment", "lifestyle", "location", "space", "prestige", "community", "sustainability", "flexibility"],
        "descriptions": {
            "investment": "Property value appreciation, rental income, portfolio building",
            "lifestyle": "Living experience, amenities, quality of life",
            "location": "Neighborhood, proximity to work/schools, accessibility",
            "space": "Square footage, layout, room for growth",
            "prestige": "Address status, luxury features, architectural significance",
            "community": "Neighbors, local culture, social environment",
            "sustainability": "Energy efficiency, green building, eco-friendly features",
            "flexibility": "Future resale, adaptability, multi-use potential"
        }
    },
    "Travel": {
        "dimensions": ["adventure", "relaxation", "culture", "luxury", "value", "convenience", "social", "sustainability"],
        "descriptions": {
            "adventure": "New experiences, outdoor activities, thrill-seeking",
            "relaxation": "Rest, rejuvenation, stress relief, comfort",
            "culture": "Historical sites, local experiences, learning, immersion",
            "luxury": "Premium accommodations, fine dining, exclusive experiences",
            "value": "Budget consciousness, deals, all-inclusive packages",
            "convenience": "Easy booking, seamless travel, minimal planning",
            "social": "Group travel, meeting people, shared experiences",
            "sustainability": "Eco-tourism, responsible travel, minimal impact"
        }
    },
    "Hospitality": {
        "dimensions": ["comfort", "service", "experience", "value", "location", "amenities", "prestige", "loyalty"],
        "descriptions": {
            "comfort": "Room quality, bedding, cleanliness, ambiance",
            "service": "Staff attentiveness, personalized care, responsiveness",
            "experience": "Unique offerings, memorable moments, special touches",
            "value": "Price-to-quality ratio, packages, promotions",
            "location": "Proximity to attractions, accessibility, views",
            "amenities": "Pool, gym, spa, dining options, business facilities",
            "prestige": "Brand reputation, luxury status, exclusivity",
            "loyalty": "Rewards programs, repeat stays, brand preference"
        }
    },
    "Education": {
        "dimensions": ["career_growth", "learning_style", "flexibility", "reputation", "community", "cost", "innovation", "support"],
        "descriptions": {
            "career_growth": "Job prospects, skill development, professional advancement",
            "learning_style": "Hands-on vs theoretical, pace, teaching methods",
            "flexibility": "Online options, part-time, self-paced learning",
            "reputation": "Institution prestige, accreditation, rankings",
            "community": "Peer network, alumni connections, collaborative learning",
            "cost": "Tuition, financial aid, return on investment",
            "innovation": "Cutting-edge curriculum, technology integration, modern facilities",
            "support": "Mentorship, career services, academic advising"
        }
    },
    "Technology / SaaS": {
        "dimensions": ["innovation", "efficiency", "scalability", "integration", "support", "cost", "security", "customization"],
        "descriptions": {
            "innovation": "Cutting-edge features, AI/ML capabilities, forward-thinking",
            "efficiency": "Time savings, automation, productivity gains",
            "scalability": "Growth accommodation, enterprise readiness, performance",
            "integration": "API availability, ecosystem compatibility, data portability",
            "support": "Customer service, documentation, training resources",
            "cost": "Pricing models, ROI, total cost of ownership",
            "security": "Data protection, compliance, privacy standards",
            "customization": "Configuration options, white-labeling, extensibility"
        }
    },
    "Other": {
        "dimensions": ["value", "quality", "convenience", "trust", "innovation", "service", "brand_affinity", "community"],
        "descriptions": {
            "value": "Price consciousness, cost-benefit ratio, deals",
            "quality": "Product/service excellence, reliability, durability",
            "convenience": "Ease of use, accessibility, time savings",
            "trust": "Reputation, reliability, transparency",
            "innovation": "New features, modern approach, cutting-edge",
            "service": "Customer support, responsiveness, care",
            "brand_affinity": "Brand loyalty, emotional connection, identity",
            "community": "User groups, social connection, shared values"
        }
    }
}

for domain in ["Manufacturing", "Telecom", "Energy", "Media & Entertainment", "Logistics", "FMCG"]:
    if domain not in DOMAIN_AFFINITY_DIMENSIONS:
        DOMAIN_AFFINITY_DIMENSIONS[domain] = DOMAIN_AFFINITY_DIMENSIONS["Other"]



class AffinityEngineAgent(BaseAgent):
    def __init__(self, 
            interaction_json: dict, 
            brochure_url: str = None, 
            product_website_url: str = None, 
            model_identifier='azure-gpt-4o',
            domain: str = None,
            custom_affinity_dimensions:list[str] = None
        ):
        
        try:
            super().__init__(
                interaction_json=interaction_json, 
                brochure_url=brochure_url, 
                product_website_url=product_website_url, 
                model_identifier=model_identifier
                )
        except Exception as e:
            traceback.print_exc()
            pass 
        
        self.interaction_json:dict = self._load_json(interaction_json) 
        self.model_identifier = model_identifier
        self.llm:Callable = lambda messages:ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        self.brochure_url:str = brochure_url
        self.product_website_url:str = product_website_url
        self.domain:str = domain or "Automotive"

        if custom_affinity_dimensions:
            self.affinity_dimensions = custom_affinity_dimensions
        else:
            self.affinity_dimensions = self.fetch_affinity_dimensions(domain = self.domain)

        logger.info(f"Affinity Dimensions set to: {self.affinity_dimensions}")
        self.brochure_content = self.fetch_brochure_content(brochure_url = self.brochure_url)
        self.product_website_content = self.fetch_product_details_from_website(website_url = self.product_website_url)
        

    def fetch_affinity_dimensions(self, domain: str = "Automotive") -> list:    
        """
        Fetch domain-specific affinity dimensions and their descriptions.
        * domain: The business domain (e.g., "Automotive", "Healthcare")
        Returns Dictionary containing dimensions list and descriptions
        """
        domain_key = domain.strip()
        if domain_key in DOMAIN_AFFINITY_DIMENSIONS:
            return DOMAIN_AFFINITY_DIMENSIONS[domain_key].get("dimensions")
        else:
            logger.warning(f"Domain '{domain}' not found, using 'Other' dimensions")
            return DOMAIN_AFFINITY_DIMENSIONS["Other"].get("dimensions")

    def _determine_input_type(self, interaction_json: dict) -> str:
        customer_indicators = ['customer_id', 'interaction', 'lead_info', 'preferences', 'behavior', 'customer_name']
        cohort_indicators = ['cohort', 'segment', 'cluster', 'group', 'cohort_id', 'cohort_name']

        json_str = json.dumps(interaction_json, indent=4)
        has_customer = any(indicator in json_str for indicator in customer_indicators)
        has_cohort = any(indicator in json_str for indicator in cohort_indicators)

        if has_customer and not has_cohort:
            return "customer"
        elif has_cohort and not has_customer:
            return "cohort"
        elif has_customer and has_cohort:
            return "customer"
        else:
            return "customer"

    def _build_prompt(self) -> list:
        """
        Build the prompt messages for the LLM based on input type.
        """
        messages = []
        input_type = self._determine_input_type(self.interaction_json)

        # Logic is not yet implemented. This is to modify the prompt based on the input type
        if input_type == "customer":
            context_description = """
                a customer interaction or lead information JSON containing details about an individual customer's:
                - Profile and demographics
                - Behavioral patterns and interactions
                - Stated preferences and goals
                - Purchase history or intent signals
                - Communication history
                """
            
            analysis_instruction = """
                Analyze this INDIVIDUAL CUSTOMER and assign affinity scores based on:
                - Their specific behaviors and interactions
                - Stated preferences and needs
                - Observed patterns in their engagement
                - Their demographic and psychographic profile
                """
        else:  # cohort
            context_description = """
            a cohort classification JSON containing aggregated information about a customer segment or group, including:
            - Shared characteristics and demographics
            - Common behavioral patterns
            - Segment-level preferences
            - Group tendencies and traits
            """
            
            analysis_instruction = """
            Analyze this CUSTOMER COHORT/SEGMENT and assign affinity scores based on:
            - Common characteristics across the group
            - Typical behaviors and patterns for this segment
            - Shared preferences and needs
            - Demographic and psychographic profile of the cohort
            """

        system_prompt = f"""
        You are an Automotive Affinity Scoring Agent specializing in analyzing customer data to generate dimensional affinity scores.
        You will be provided with a JSON, It can be a customer interaction JSON or a Cohort Classification JSON.

        Analyze the provided JSON and assign affinity scores
        between 0 and 1 for each dimension listed below.

        Dimensions:
        {", ".join(self.affinity_dimensions)}

        Guidelines:
        - Understand the provided JSON. (Either a customer interaction JSON or a Cohort Classification JSON). If it is a customer interaction JSON, Please understand the customer's profile, behavior, preferences, and goals. It can be a customer lead information or Interaction JSON or Cohort Classification JSON.
        - Final affinity scores would be for this customer or cohort only.
        - Scores must be floats between 0 and 1
        - Use ONLY observed interactions
        - Provide a short reasoning for each score
        - Base scores on evidence, not assumptions
        - If no evidence for a dimension, score it low (0.0-0.2)
        - Return STRICT JSON only

        Expected Output Format Example:
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
        "llm_reasoning": "<Your analysis here (5-6 sentences max). Explain the key factors that influenced the scores, citing specific data points from the JSON.>"
        }}

        Interaction JSON:
        {json.dumps(self.interaction_json, indent=2)}
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

    @property
    def additional_product_context(self):
        return """
            Consider the following product information when scoring affinities. 
            Match customer/cohort characteristics with product features that would appeal to each dimension.
            For example:
            - If product has off-road features and customer shows outdoor interests → higher offroad score
            - If product emphasizes luxury/premium and customer values status → higher achievement/identity scores
            - If product highlights safety/space and customer has family → higher family score
        """
    def run(self):
        prompt = self._build_prompt()
        product_context_parts = []
        if self.brochure_content:
            product_context_parts.append(f"PRODUCT BROCHURE:\n{json.dumps(self.brochure_content, indent=2)}")
        if self.product_website_content:
            product_context_parts.append(f"PRODUCT WEBSITE:\n{json.dumps(self.product_website_content, indent=2)}")
        if product_context_parts:
            product_context = "\n\n".join(product_context_parts)
            prompt.append(
                {
                    "role": "user",
                    "content": f"{self.additional_product_context}\n{product_context}"
                }
            )
        parsed = self.exec_json_llm_with_retry(self.llm, messages=prompt)
        for k in parsed["affinity_scores"]:
            parsed["affinity_scores"][k] = max(0.0, min(1.0, parsed["affinity_scores"][k]))

        fig_json = self._create_spider_chart(parsed["affinity_scores"])

        return {
            "affinity_scores": parsed["affinity_scores"],
            "llm_reasoning": parsed["llm_reasoning"],
            "affinity_fig_json": fig_json
        }
