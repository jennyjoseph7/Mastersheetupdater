import requests
import json
from ai_service import ai_service,ai_service_app

try:
    from .base_agent import BaseAgent
except:
    from base_agent import  BaseAgent
    
class CommunicationAgent(BaseAgent):
    def __init__(self,source,model_identifier='azure-gpt-4o'):
        self.data = self._load_json(source=source)
        self.model_identifier = model_identifier
        


    def _convert_message_to_html(self,message:str) ->str:
        """
        Convert a plain text message to a simple HTML string.
        """
        html_message = message.replace("\n", "<br>")
        html_content = f"<html><body><p>{html_message}</p></body></html>"
        return html_content
    
    def _message_formatter(self,raw_text,channel="email"):
        messages = []
        prompt = f"""
            You are a message formatting assistant.
            The channel is: {channel}.
            For email, output in clean, inline-styled HTML.
            For WhatsApp, keep it plain text but add line breaks and subtle emojis for emphasis.

            Keep brand tone professional but friendly.
            Content to format:
            {raw_text}
            """
        user_message = {"role": "user", "content": prompt}
        messages.append(user_message)
        return ai_service_app.get_llm_response(messages=messages,model_identifier=self.model_identifier)
            
    def _extract_json_from_text(self, raw_llm_response):
        """
        Extracts the first complete JSON object from raw LLM response,
        even if it includes nested objects.
        """
        raw_text = raw_llm_response.strip()
        print(raw_text)
        start = None
        brace_stack = []

        for i, char in enumerate(raw_text):
            if char == '{':
                if not brace_stack:
                    start = i
                brace_stack.append('{')
            elif char == '}':
                if brace_stack:
                    brace_stack.pop()
                    if not brace_stack and start is not None:
                        json_candidate = raw_text[start:i + 1]
                        try:
                            return json.loads(json_candidate)
                        except json.JSONDecodeError as e:
                            print(f"Invalid JSON segment: {e}")
                            continue

        raise ValueError("No valid JSON object found in LLM response.")
    def draft_email(self, user_message: str) -> dict:
        """
        Draft an email with subject and message body based on user input.
        Returns a JSON object with 'subject' and 'message' keys.
        """
        messages = []
        prompt = f"""
            You are an email drafting assistant. Based on the user's message, create a professional email with an appropriate subject line.
            
            User message: {user_message}
            
            Please generate a response in the following JSON format only (no additional text):
            {{
                "subject": "Generated subject line here",
                "message": "Professional email body here with proper formatting and line breaks where needed"
            }}
            
            Guidelines:
            - Keep the subject line concise and descriptive
            - Make the email professional but friendly
            - Include proper greetings and closing
            - Use appropriate formatting with line breaks
            - this email is sent from the team Dave
        """
        
        user_message_obj = {"role": "user", "content": prompt}
        messages.append(user_message_obj)
        
        raw_response = ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        
        try:
            email_draft = self._extract_json_from_text(raw_response)
            return email_draft
        except ValueError as e:
            print(f"Error extracting JSON: {e}")
            # Fallback response
            return {
                "subject": "Important Message",
                "message": user_message
            }

    def draft_and_send_email(self, cc: str, user_message: str):
        """
        Draft an email based on user message and send it.
        """

        email_draft = self.draft_email(user_message)
        email_id = self.data.get("email")
        if not email_id:
            return {
                "draft": None,
                "send_response": "Email not sent - no recipient email ID available"
            }
        
        
        subject = email_draft.get('subject', 'Important Message')
        message = email_draft.get('message', user_message)


        response = self.send_email(
            email_id=email_id,
            subject=subject,
            cc=cc,
            message=message
        )
        
        return {
            "draft": email_draft,
            "send_response": response
        }

    def send_email(self,email_id: str, subject: str, cc: str, message: str):
        """
        Send email using AWS sender API.
        """
        url = "https://gryd-webapp-dev-334553189554.asia-south1.run.app/gryd/api/communication/communication_sender/test"

        payload = {
            "args": [],
            "kwargs": {
                "ent_id": "no_code_low_code",
                "enterprise_id": "no_code_low_code",
                "sender": {
                    "name": "info",
                    "email": "info@iamdave.ai"
                },
                "receiver": {
                    "emails": [email_id]
                },
                "cc": cc,
                "html_string": self._convert_message_to_html(message),
                "subject": subject,
                "provider": "AwsSender"
            }
        }

        headers = {
            'accept': '*/*',
            'content-type': 'application/json',
            'x-gryd-enterprise-id': 'no_code_low_code',
            'x-gryd-session-id': 'aadfbfd5-2f54-31f5-aa5f-4e35d350d12d',
            'x-gryd-token': 'b39dfdbb-2a36-3501-9595-6458f9878bfa'
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        return response.text


    def send_whatsapp(self,phone_number: str, message: str):
        pass

if __name__ == "__main__":
    # Send Email
    communication_agent = CommunicationAgent(source='/home/balaji/one/autobot_agents/agents/test.json',model_identifier='azure-gpt-4o')
    email_resp = communication_agent.draft_and_send_email(
        cc="nbalaji743@gmail.com",
        user_message="im intrested in the grand vitara"
    )
    print("Email Response:", email_resp)

    # Send WhatsApp
    # whatsapp_resp = communication_agent.send_whatsapp(
    #     phone_number="+911234567890",
    #     message="Hello! This is a WhatsApp test message"
    # )
    # print("WhatsApp Response:", whatsapp_resp)
