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

            **Task**: Given a customer's interaction history (from website, walk-in, or WhatsApp), your goal is to think through the data and understand how to generate a short, personalized promotional message. But here, you're not generating the message yet — you're just thinking.

            **Your Thinking Process**:
            - Analyze the customer interaction data.
            - Identify what the customer is interested in (car models, features, campaigns).
            - Consider the engagement level and where the user is in the buying journey.
            - Think about what would be a suitable next step for the user (e.g., visit showroom, schedule test drive).
            - Do not recommend a specific product or variant — that’s handled by another agent.

            **Input**: Here is the customer interaction data:
            {json.dumps(self.source, indent=2)}
            - include a line of thinking about the user's sentiments and emotional condition from the user_sentiment json file 

            Think step by step like a human analyzing a lead:
            - Write 3–5 short sentences.
            - Show your reasoning process: What do you observe? What can you infer?
            - End with: "Now, let's greet the user with a personalized message."
            - Do NOT write the actual message here.
            """

        think = [] 
        input =  {"role" : "user", "content" : think_prompt}
        think.append(input)        
        return think

    def messages(self):
        prompt = f"""
            You are a Personalization Agent for a car dealership or automotive brand.
            
            Task:
            Based on a customer's interaction history (from website, walk-in, or WhatsApp), generate a short, friendly promotional message that can be used across channels (SMS, WhatsApp, email, phone, website).
            
            Your job:
            - Personalize the message based on the customer’s specific interaction type — whether they explored a car, checked specific features, booked a test drive, received a service reminder, or were recommended accessories.

                For example:
                If they explored a car or its features → highlight those features in the message
                If they booked a test drive → remind or excite them about the upcoming experience.
                If it’s a service reminder → mention past service or due date positively
                If accessories were recommended → tailor the message like:
                “Based on your preferences and style, you might love these accessories 🚗✨”
                Make each message context-aware and emotionally engaging.
            - Promote the car, service, or accessory the user showed interest in.
            - Do NOT recommend a variant, car model, or suggest comparisons.
            - Keep it persuasive, clear, and human-like (2–5 short lines only).
            - Mention one or two standout features the user explored and say something like “With those, you’ve made a great choice!” (without recommending).
            - Use emojis (e.g. 🚘, 💡, ⚡️, ✅, 🛞,👀,🛡️ ,✨,🥳,🤝, 😊) to create a positive tone.
            - Use line breaks for readability.
            - do not include any '\n' in the message, just proper space.
            - Start the message with:
                - "Hi <name>!" — if the name is clearly extractable from input JSON. Check before adding it, Names are like Prince, Nikit, Shreyas, Jay, Megha,Richa, Nikita etc, Not like Ggananth, its Ananth, Not ppprince, its Prince. Extract Properly otherwise do not include it. 
                - "Hi!" or "Hello!" — if name is missing or ambiguous (e.g., messy email prefix).
            
            Input:
            {json.dumps(self.source, indent=2)}
            
            This file also contains a user_sentiments json file, It contains user's emotional condition. analyze it and react accordingly. 
            
            Output:
            Return only the personalized message as plain text, with emojis and spaces, Not line breaks.
            Do not include any extra formatting like markdown, labels, or JSON.
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