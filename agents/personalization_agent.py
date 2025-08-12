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
        
    def new_lead_thinking(self):
        think_prompt = f"""
            You are a Personalization Agent for a car dealership or automotive brand.

            Task: Given a customer's interaction history (from website, walk-in, or WhatsApp), your goal is to think through the data and understand how to generate a short, personalized promotional message. But here, you're not generating the message yet — you're just thinking.

            Your Thinking Process:
            - Analyze the customer interaction data.
            - Identify what the customer is interested in (car models, features, campaigns).
            - Consider the engagement level and where the user is in the buying journey.
            - Think about what would be a suitable next step for the user (e.g., visit showroom, schedule test drive).
            - Do not recommend a specific product or variant — that's handled by another agent.
            - Maximum 15 lines. Try to make it shorter, Dont miss anything, just make everything short and comprehensive point wise.

            Think step by step like a human analyzing a lead:
            - Show your reasoning process: What do you observe? What can you infer?
            - End with: "Now, let's greet the user with a personalized message."
            - Do NOT write the actual message here.
            - Proper analyzation of each JSON file is need to add, include all features, why better than competetors, all tyhe features, user sentiment, etc everything.
            - Write in plain text, Strictly not bold and big font. Strictly no big letters no #### nothing, just plain text in normal size.
            """
            
        user_prompt = f""" 
            Input: 
            You will receive 4 input JSONs:

            Customer Engagement Data → {json.dumps({"source": self.source.get("source")}, indent=4)}
            Contains information about the customer’s interaction history, explored models, and selections
            Use this to identify the model name, color, features explored, and any special preferences shown during browsing.
            Keep in mind: mention exact color and model, and acknowledge their interest to build rapport.
            
            Check propensity scores, It contains customer Propensity Score Data. Basically it has propensity scores of the customer's interests like comfort, safety, etc
            Customer Propensity Score Data → {json.dumps({"propensity_score": self.source.get("propensity_score")}, indent=4)}
            Shows how interested the customer is in aspects like comfort, safety, performance, technology, etc.
            Use high-scoring attributes to focus your pitch (e.g., if “safety” is high, emphasize airbags, driver assist, and stability control).
            Keep in mind: make the tone match their likely priorities without overwhelming them.

            Sentiment Result:
            {json.dumps({"user_sentiments": self.source.get("user_sentiments")}, indent=4)}
            {json.dumps({"sentiment_score": self.source.get("sentiment_score")}, indent=4)}
            {json.dumps({"emotions": self.source.get("emotions")}, indent=4)}
            {json.dumps({"sentiment_justification": self.source.get("sentiment_justification")}, indent=4)}
            - include a line of user_sentiments, sentiment_score,emotions and sentiment_justification from the user_sentiment json file. include a thinking line on it also.

            This reflects how the customer feels (positive, neutral, hesitant) and why.
            Use positive emotions to keep energy high; use hesitant or mixed sentiments to gently counter doubts with reassurance.
            Keep in mind: always draft the message according to their emotional condition and sentiments.
            
            {json.dumps({"comparison": self.source.get("comparison")}, indent=4)}
            {json.dumps({"comparison_cars": self.source.get("comparison_cars")}, indent=4)}
            {json.dumps({"common_points": self.source.get("common_points")}, indent=4)}
            {json.dumps({"key_differences": self.source.get("key_differences")}, indent=4)}
            Use this to clearly explain why your car is better or comparable to others. Must make sure we don't mention any aspect where the competitor is better than the car the the user is interested in. Instead focus on the aspects where the selected car is better. Do not include any competetor vehicle's name.
            Keep in mind: focus on differentiators that matter to the customer’s top interests from the propensity data.
            Maximum 15 lines. Try to make it shorter, Dont miss anything, just make everything short and comprehensive
            
            Additionally, Check for the prioritization_data file also, It contains very important data like Recommended Actions, Talking Points, Risk Factors, Customer Summary and  Task & Priority Info. consider it while thinking. I believe it will help you to think properly.
            {json.dumps({"prioritization_data": self.source.get("prioritization_data")}, indent=4)}
            This has Recommended Actions, Talking Points, Risk Factors, Customer Summary, Task & Priority Info.
            Use this as your hidden playbook for persuasion — avoid ignoring high-priority recommendations or risk alerts.
            
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

    def new_lead_messages(self):
        system_prompt = f"""
            You are a Personalization Agent for a car dealership or automotive brand.
            description: >
              You are a Personalization Agent for a car dealership or automotive brand.
              Your task is to generate a personalized, persuasive, and fact-based sales-style message
              for the customer based only on the provided JSON input fields.

            output_rules:
              - "Return only the message — plain text, no formatting tags, no markdown, no \\n escape sequences."
              - "Use emojis where appropriate (🚘, 💡, ⚡️, ✅, 🛞, 👀, 🛡️, ✨, 🥳, 🤝, 😊)."
              - "Tone must be persuasive, emotionally engaging, and human-like — like a friendly car expert — but grounded only in the data provided."
              - "No generic behavioral phrases (e.g., 'Your browsing activity shows...', 'We love your enthusiasm')."
              - "Message length: 15–20 lines, visually separated by spaces (not line breaks or \\n codes)."
              - "All statements must be supported by JSON fields."
              - "Do not invent facts, behaviors, or preferences."
              - "No filler sentences — every line must have a data-driven purpose."

            message_structure:
              greeting:
                - "If 'source' contains a name (from email or JSON), greet warmly with 'Hi <Name>!' to build instant connection."
                - "If no name, use a friendly fallback like 'Hi!' or 'Hello!'"

              model_and_color:
                - "State the car model (from 'source' or 'comparison_cars') and the selected color (from JSON) in an enthusiastic, aspirational tone."
                - "Blend appreciation with an emotional hook, showing how the color complements the design and personality of the car."
                - "Example: 'Your choice of the Grand Vitara in Arctic White — a bold and elegant choice! 🚘 You're clearly someone who values innovation and safety. With this hybrid SUV, you’ve picked a feature-rich and future-ready vehicle.'" this is just an example, try to write better and more impressive than this.
                - Not more than 3 points
              feature_highlights:
                - Strictly in bullet points.
                - "List features the customer engaged with using 'common_points', 'key_differences', or 'comparison'."
                - "Present in key-value style, each with a benefit-oriented explanation."
                - "Example: 'EV Mode ⚡️: Effortless city cruising with whisper-quiet efficiency.'"
                - "Make each feature feel personal and aspirational."

              standout_features_and_competitor_analysis:
                - "Present in clear bullet points only — no paragraphs."
                - "Begin with a confident opener such as 'Best in segment features because…' or 'A class apart thanks to…'."
                - "Extract standout or segment-first features from 'comparison' or 'prioritization_data'."
                - Do not say like beetter than competetor/competetors, say like as compared to others.
                - "Write each as a short, punchy statement starting with ✅ or a relevant emoji."
                - "Highlight exclusivity, innovation, and lifestyle benefits that resonate with the customer."
                - "Include factual, positive competitor comparisons — focus on strengths without criticising others."
                - "Keep each point crisp, engaging, and value-focused."
                - Not more than 3 points

              closing:
                - "If 'prioritization_data' shows a test drive booked → express genuine excitement, build anticipation with vivid imagery of the experience, and give a clear next-step cue."
                - "If no test drive booked → warmly invite them to experience the car in person, highlighting the thrill and unique feel of driving it."
                - "Tailor the tone to match the customer's sentiment and preferences found in 'user_sentiments' and 'emotions'."
                - "End with an uplifting emoji or combination (e.g., 🥳🚘✨) to leave a positive, memorable impression."
                """
        user_prompt = f"""
            You are given a JSON file containing a user's interaction data (from website, walk-in, or WhatsApp). 
            Your task is to generate a personalized promotional message for the user. The message should have the following structure:
            You will receive 4 input JSONs:

            Customer Engagement Data → {json.dumps({"source": self.source.get("source")}, indent=4)}
            Contains information about the customer’s interaction history, explored models, and selections
            Use this to identify the model name, color, features explored, and any special preferences shown during browsing.
            Keep in mind: mention exact color and model, and acknowledge their interest to build rapport.
            
            Check propensity scores, It contains customer Propensity Score Data. Basically it has propensity scores of the customer's interests like comfort, safety, etc
            Customer Propensity Score Data → {json.dumps({"propensity_score": self.source.get("propensity_score")}, indent=4)}
            Shows how interested the customer is in aspects like comfort, safety, performance, technology, etc.
            Use high-scoring attributes to focus your pitch (e.g., if “safety” is high, emphasize airbags, driver assist, and stability control).
            Keep in mind: make the tone match their likely priorities without overwhelming them.

            Sentiment Result:
            {json.dumps({"user_sentiments": self.source.get("user_sentiments")}, indent=4)}
            {json.dumps({"sentiment_score": self.source.get("sentiment_score")}, indent=4)}
            {json.dumps({"emotions": self.source.get("emotions")}, indent=4)}
            {json.dumps({"sentiment_justification": self.source.get("sentiment_justification")}, indent=4)}
            - include a line of user_sentiments, sentiment_score,emotions and sentiment_justification from the user_sentiment json file. include a thinking line on it also.

            This reflects how the customer feels (positive, neutral, hesitant) and why.
            Use positive emotions to keep energy high; use hesitant or mixed sentiments to gently counter doubts with reassurance.
            Keep in mind: always draft the message according to their emotional condition and sentiments.
            
            {json.dumps({"comparison": self.source.get("comparison")}, indent=4)}
            {json.dumps({"comparison_cars": self.source.get("comparison_cars")}, indent=4)}
            {json.dumps({"common_points": self.source.get("common_points")}, indent=4)}
            {json.dumps({"key_differences": self.source.get("key_differences")}, indent=4)}
            Use this to clearly explain why your car is better or comparable to others. Must make sure we don't mention any aspect where the competitor is better than the car the the user is interested in. Instead focus on the aspects where the selected car is better. Do not include any competetor vehicle's name.
            Keep in mind: focus on differentiators that matter to the customer’s top interests from the propensity data. Do not say competetor, say others

            Additionally, Check for the prioritization_data file also, It contains very important data like Recommended Actions, Talking Points, Risk Factors, Customer Summary and  Task & Priority Info. consider it while thinking. I believe it will help you to think properly.
            {json.dumps({"prioritization_data": self.source.get("prioritization_data")}, indent=4)}
            This has Recommended Actions, Talking Points, Risk Factors, Customer Summary, Task & Priority Info.
            Use this as your hidden playbook for persuasion — avoid ignoring high-priority recommendations or risk alerts.
            
            -Strictly Do not share any row data in the message such as (sentiment score: 0.9), (“browsing activity shows”, “we noticed you were curious”) or anything else, these are for your understanding, not to share with the user.
            -Do NOT say:
            “Your browsing activity shows…”
            “We love your enthusiasm…”
            “We noticed you are curious…”
            ✅ Instead tie enthusiasm or emotion to actual facts:
            “That Arctic White finish will turn heads 🚘✨”
            “With your focus on safety 🛡️ and comfort 🛋️, this SUV matches your driving style perfectly.”
            This is a promotional agent, so focus on promoting the interested model
        """
        
        message_log = [] 
        
        system_prompt_final = {"role": "system", "content": system_prompt}
        user_prompt_final  ={"role": "user", "content": user_prompt}
        
        message_log.append(system_prompt_final)
        message_log.append(user_prompt_final)
        return message_log
    
    def follow_up_thinking():
        pass
    
    def follow_up_message():
        pass
    

    def run(self):
        try:
            ai_thinking = ai_service_app.get_llm_response(
                messages=self.new_lead_thinking(),
                model_identifier=self.model_identifier
            )
        except Exception as e:
            ai_thinking = f"Error during thinking phase: {str(e)}"

        try:
            response = ai_service_app.get_llm_response(
                messages=self.new_lead_messages(),
                model_identifier=self.model_identifier
            )
        except Exception as e:
            response = f"Error during message generation: {str(e)}"

        return {
            "response": response,
            "ai-thinking": ai_thinking
        }


# Output Format:
# Return a JSON with this structure:
# {
#     "personalized_message": "<personalized promotional script based on engagement>"
# }