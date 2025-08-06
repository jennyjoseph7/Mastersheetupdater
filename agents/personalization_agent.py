from ai_service import ai_service_app
import json
import os
from agents.base_agent import BaseAgent

class PersonalizationAgent(BaseAgent):
    def __init__(self, source: dict, model_identifier='azure-gpt-4o'):
        self.source = self._load_json(source=source)
        self.model_identifier = model_identifier
        
    def thinking(self):
        think_prompt = f"""
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
        
        So, Here, You you will act as a thinker, how you will think during analyzing the data, You need to show your thinking steps and process here according to the task and the given data.
        {json.dumps(self.source, indent=2)}
        Think step-by-step (as a human would), and express your analysis briefly.
        - Keep it short (3-5 sentences max)
        - Sound like you're reasoning through the data
        - End with: "Now, let's greet the user with a personalized message."
        Do NOT include any personalized message here.
        Respond as if you're thinking out loud.
        
        """
        think = [] 
        input =  {"role" : "user", "content" : think_prompt}
        think.append(input)        
        return think

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
        ai_thinking = ai_service_app.get_llm_response(messages = self.thinking(), model_identifier=self.model_identifier)
        response = ai_service_app.get_llm_response(messages = self.messages(), model_identifier=self.model_identifier)
        return {
            "response" : response,
            "ai-thinking" : ai_thinking
                
            }

# **Output Format**:
# Return a JSON with this structure:
# {
#     "personalized_message": "<personalized promotional script based on engagement>"
# }