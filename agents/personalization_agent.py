from ai_service import ai_service_app
import json
import os

try:
    from .base_agent import BaseAgent
except:
    from base_agent import BaseAgent

class PersonalizationAgent(BaseAgent):
    def __init__(self, source: dict, model_identifier='azure-gpt-4o'):
        self.source = self._load_json(source=source)
        self.model_identifier = model_identifier
        
    def thinking(self):
        think_prompt = f"""
            You are a Personalization Agent for a car dealership or automotive brand.

            Task: Given a customer's interaction history (from website, walk-in, or WhatsApp), your goal is to think through the data and understand how to generate a short, personalized promotional message. But here, you're not generating the message yet — you're just thinking.

            Your Thinking Process:
            - Analyze the customer interaction data.
            - Identify what the customer is interested in (car models, features, campaigns).
            - Consider the engagement level and where the user is in the buying journey.
            - Think about what would be a suitable next step for the user (e.g., visit showroom, schedule test drive).
            - Do not recommend a specific product or variant — that's handled by another agent.

            Think step by step like a human analyzing a lead:
            - Write 3-5 short sentences.
            - Show your reasoning process: What do you observe? What can you infer?
            - End with: "Now, let's greet the user with a personalized message."
            - Do NOT write the actual message here.
            - Proper analyzation of each JSON file is need to add, include all features, why better than competetors, all tyhe features, user sentiment, etc everything.
            """
            
        user_prompt = f""" 
            Input: Here is the customer interaction data:
            {json.dumps(self.source, indent=4)}
            - include a line of user_sentiments, sentiment_score,emotions and sentiment_justification from the user_sentiment json file. include a thinking line on it also.
            - Check for the prioritization_data file also, It contains very important data like Recommended Actions, Talking Points, Risk Factors, Customer Summary and  Task & Priority Info. consider it while thinking. I believe it will help you to think properly.
            - Check propensity scores, It contains customer Propensity Score Data. Basically it has propensity scores of the customer's interests like comfort, safety, etc
        """
        messages = [] 
        
        system_prompt_final = {
            "role" : "system",
            "content" : think_prompt
        }
        
        user_prompt_final = {
            "role" : "user",
            "content" : user_prompt
        }

        messages.append(system_prompt_final)
        messages.append(user_prompt_final)     
        return messages

    def messages(self):
        system_prompt = f"""
            You are a Personalization Agent for a car dealership or automotive brand.

            You will receive 4 input JSONs:
            1. Customer Engagement Data
            2. Customer Propensity Score Data. Basically it has propensity scores of the customer's interests like comfort, safety, etc
            3. Sentiment Result
            4. Competitor Analysis Data

            Your task is to generate a personalized sales-style message for the customer based on these inputs.

            Output Rules:

            - Return only the message — plain text, no formatting, no markdown, no \n characters.
            - Use emojis where appropriate to enhance tone (🚘, 💡, ⚡️, ✅, 🛞,👀,🛡️ ,✨,🥳,🤝, 😊).
            - Tone should be persuasive, emotionally engaging, human-like, and energetic — like a friendly car expert guiding the user.
            - Message should be 15-20 lines, clean and readable with spaces (not line breaks or \n).

            ---

            Message Structure:

            1. Greet the user:  
               - Use: “Hi <Name>!” (if the name can be extracted from the email — e.g., 'ggananth@yahoo.com' → Ananth).  
               - Else: use “Hi!” or “Hello!”

            2. Confirm model and selection:  
               - Mention the car model they explored, the selected final color (e.g., "Arctic White"), and show appreciation for their selection.

            3. Features they explored — as key-value style short explanations:  
               - Example:  
                 - EV Mode ⚡️: Glide through city streets silently while saving fuel.  
                 - Wireless Charging 🔋: No more tangled cables — stay powered up effortlessly.  
                 - 6 Airbags As Standard 🛡️: Safety across every seat, always on.

            4. Bullet-point list of standout features:  
               - Clearly call out standout or segment-first features.  
               - Example:  
                 - ✅ Segment-first Head-Up Display  
                 - ✅ Standard 6 Airbags across all variants  
                 - ✅ Intelligent Hybrid Powertrain  
                 - ✅ Wireless Phone Charging  

            5. Comparison with competitors:  
               - Start with: “Best in segment features because...” or “Comparable to others in the segment thanks to…”  
               - Then bullet-point comparisons like:  
                 - Grand Vitara has EV Mode – Fronx and Invicto don’t.  
                 - It offers 6 standard airbags – others offer only 2.  
                 - Comes with Head-Up Display, unlike most competitors.

            6. End message — personalized & engaging:  
               - If test drive booked:  
                 - “Can’t wait for you to feel it in action during your test drive! 🥳”  
               - If not:  
                 - “Whenever you're ready, this SUV will be waiting to impress. 😊”

            ---

            Example Output Style (DO NOT COPY THIS, generate dynamically):

            Hi Ananth!  

            We noticed you explored the Grand Vitara in Arctic White — a bold and elegant choice! 🚘 You're clearly someone who values innovation and safety. With this hybrid SUV, you’ve picked a feature-rich and future-ready vehicle.  

            Here’s what caught your attention and why it’s worth it:  
            - EV Mode ⚡️: Glide silently through city streets, saving fuel and reducing emissions — perfect for Bengaluru drives.  
            - Head-Up Display 👀: Keep your eyes on the road with real-time data projected right on your windshield.  
            - Wireless Charging 🔋: Ditch the cables and charge your phone seamlessly while you drive.  
            - 6 Airbags As Standard 🛡️: Safety that doesn’t compromise — protection for all passengers, always.  
            - Hill-Descent Control 🛞: Take on challenging terrains with confidence and control.  

            Best in segment features because:  
            - Grand Vitara offers 6 standard airbags while others like Fronx or Invicto offer only 2.  
            - It's one of the few in the segment with EV Mode, making it both eco-friendly and high-tech.  
            - Head-Up Display and Wireless Charging are rare at this price point — giving you features usually found in premium cars.  

            We're excited that you booked a test drive 🥳  
            You're going to experience everything first-hand — from smart tech to confident control.  

            Enjoy the ride and get ready to be impressed, Ananth! 😊

            ---

            Use this structure strictly as a template. Do not copy the same text — generate fresh content each time based on input JSON values.

            Output: Only the final message. No explanations. No labels.


        """
        user_prompt = f"""
            You are given a JSON file containing a user's interaction data (from website, walk-in, or WhatsApp). 

            Your task is to generate a personalized promotional message for the user. The message should have the following structure:

            1. Greet the user.
            2. Mention key features of the car, in this format:
               - Feature name: short explanation
            3. Highlight a few standout features as "best-in-segment" or "comparable to other cars in the segment".
            4. Include a brief comparison with competitor cars.
            5. End with a warm and personalized message encouraging the user to take the next step (like booking a test drive or reaching out).
            Check for the prioritization_data file also, It contains very important data like Recommended Actions, Talking Points, Risk Factors, Customer Summary and  Task & Priority Info. consider it while drafting message. I believe it will help you to draft a proper personalized message. 
            Check propensity scores, it contains a score of the vehicle in its important aspects like comfort , safety, and others. consider it while drafting your message.
            - Do not say anything negative about the selected or interested model, You should make sure we don't mention any aspect where the competitor is better than the car the the user is interested in. Instead focus on the aspects where the selected car is better. Do not mention competetor cars name.
            Here is the input JSON data:

            Input:
            {json.dumps(self.source, indent=2)}
        
        
        """
        
        message_log = [] 
        
        system_prompt_final = {"role": "system", "content": system_prompt}
        user_prompt_final  ={"role": "user", "content": user_prompt}
        
        message_log.append(system_prompt_final)
        message_log.append(user_prompt_final)
        return message_log

    def run(self):
        ai_thinking = ai_service_app.get_llm_response(messages = self.thinking(), model_identifier=self.model_identifier)
        response = ai_service_app.get_llm_response(messages = self.messages(), model_identifier=self.model_identifier)
        return {
            "response" : response,
            "ai-thinking" : ai_thinking
                
            }

# Output Format:
# Return a JSON with this structure:
# {
#     "personalized_message": "<personalized promotional script based on engagement>"
# }