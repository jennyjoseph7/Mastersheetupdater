from ai_service import ai_service_app
import json
import os
from agents.base_agent import BaseAgent

class PersonalizationAgent(BaseAgent):
    def __init__(self, source: dict, model_identifier='azure-gpt-4o'):
        self.source = self._load_json(source=source)
        self.model_identifier = model_identifier

    def messages(self):
        prompt = f"""
        You are a Personalization Agent for a car dealership or automotive brand.
        
        **Task**: Given a customer's interaction history (from website, walk-in, or WhatsApp), generate a short personalized promotional script. This script will be used for follow-up messages (via SMS, email, WhatsApp, or phone) and should:
        - Be personalized based on the user's engagement and preferences.
        - Promote a car, service, or accessory that aligns with what the user has already shown interest in.
        - Encourage the next step (e.g., visit showroom, schedule test drive, check out an offer, etc.).
        - NOT include a product or variant recommendation (leave decision-making to other agents).
        - Be friendly, persuasive, and concise (2-5 sentences max).
        
        **Input**: A JSON object containing customer interaction data such as:
        - Source of interaction: website, walk-in, or WhatsApp
        - Car models browsed or test driven
        - Features explored (safety, tech, interior, etc.)
        - Marketing campaign info (UTM params, keywords)
        - Location and preferred dealer
        - Engagement level (e.g., test drive booked, comparisons made, flow abandoned)
        - Date and time
        
        **Note**: Do not suggest which model or variant to choose. Just use interaction signals to create a customized message that improves user engagement.
        
        Now generate the message for the following input:
        {json.dumps(self.source, indent=2)}
        
        Respond only with a single short message in plain text.
        """
        message_log = [] 
        input =  {"role" : "user", "content" : prompt}
        message_log.append(input)
        return message_log

    def run(self):
        response = ai_service_app.get_llm_response(messages = self.messages(), model_identifier=self.model_identifier)
        return response

# **Output Format**:
# Return a JSON with this structure:
# {
#     "personalized_message": "<personalized promotional script based on engagement>"
# }