import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp
from gryd_worker.gryd_routes import payload_decorator
from models import model as base_model
from ai_service import ai_service_app

gryd.SERVICE = os.environ.get("AUTOBOT_CONVERSATION_SERVICE_NAME","autocrm-communication")

gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(__name__)


@gryd.is_task()
def post_contact_status(data, *args, **kwargs):
    """
    Posts contact status updates when a campaign trigger occurs.

    For each lead, this function posts a new status object while keeping the 
    same `message_id` across updates. The function yields a structured dictionary 
    representing the current contact status, which can be sent to downstream 
    systems or stored for tracking.

    Example yielded data:
        {
            "message_id": "msh123abcd",
            "channel_provider": "twilio",
            "channel": "voice_phone",
            "phone_number": "8850988794",
            "response_id": "sid12323123",
            "campaign_id": "campaign_pre_sales_123",
            "provider_status": "initiated"
        }

    Typical provider statuses may include:
        - "initiated"
        - "queued"
        - "in-progress"
        - "completed"
        - "failed"

    Args:
        ...: (Describe any parameters here, such as campaign data or status input.)

    Yields:
        dict: A dictionary containing the contact status details for each lead.
    """


    yield  {
        "message_id":"msh123abcd",
        "channel_provider": "twilio",
        "channel":"voice_phone",
        "phone_number":"8850988794",
        "response_id":"sid12323123",
        "campaign_id" : "campaign_pre_sales_123",
        "provider_status": "initiated"
    }
    

@gryd.is_task()
def send_template_for_approval(data, *args, **kwargs):
    """
    Send a WhatsApp template to the Airtel API for approval.

    This function prepares and forwards the template payload to Airtel's 
    template approval API. On success, Airtel returns a template ID that 
    can later be used to check the template's approval status.

    Expected Input for text template (example):
    {
        "templateName": "SaleCarousel",
        "wabaId": "113485138500957",
        "customerId": "SOCIOGRAPH_uu76NiJRbNmsq5zPgu5V",
        "category": "MARKETING",
        "subAccountId": "965a92cd-ac2e-4674-87ab-99fc174e071f",
        "templateContent": {
            "language": "en",
            "body": "This is just for testing for autobot demo",
            "buttons": [
                {
                    "type": "QUICK_REPLY",
                    "buttonText": "Button1"
                },
                {
                    "type": "QUICK_REPLY",
                    "buttonText": "Button2"
                },
                {
                    "type": "CALL_TO_ACTION",
                    "buttonText": "Website",
                    "subType": "URL",
                    "url": "https://www.google.com"
                }
            ]
        }
    }

    Returns:
        dict: Response from Airtel containing the `template_id`.
              This ID can be used to track approval status.

    """
    
    yield {
        "template_id": "template_id_123",
    }


@gryd.is_task()    
def check_or_create_session(self, phone_number):
    """
    Process an incoming WhatsApp message and resolve the correct Person,
    Campaign context, Dealership, and Session data for the conversation.

    Workflow:
        1. Identify or create a Person based on the phone number.
        2. Check the contact_status model to determine whether the incoming
           message is related to a previously sent campaign.
        3. If a campaign is found:
               - Extract campaign_id and dealership_id.
               - Pass these into the session creation logic.
           If no campaign is found:
               - Determine dealership_id from communication_credential
                 based on the sender phone number.
        4. Create or retrieve an active session based on the resolved payload.

    Parameters:
        phone_number (str): The user's WhatsApp mobile number from which the 
                            message was received.

    """
    
    yield {
        "session_id": "session_id_123",
        "conversation_id": "conversation_id_123",
        "session_live": True,
        "status": "active",
        "application": "whatsapp",
        "user_id": "user_id_123",
        "dealership_id": "dealership_id_123"
    }


def process_Webhook(data, *args, **kwargs):
    """
    Handle an incoming WhatsApp webhook and trigger the conversation engine.

    This task:
        - Validates and parses the incoming WhatsApp webhook payload.
        - Extracts message text, timestamps, identifiers, and routing metadata.
        - Resolves the correct session, person, and dealership context.
        - Constructs the `converse_kwargs` dictionary required by the
          conversation engine.
        - Forwards `converse_kwargs` to the appropriate conversation task
          (e.g., `converse`, `receive_converse_response`, etc.).
        - Yields a lightweight status object for task acknowledgment.

    The constructed `converse_kwargs` (passed internally to the conversation engine)
    follows this structure:
        {
            "customer_response": <text message sent by the user>,
            "session_id": "<session identifier>",
            "channel": "whatsapp_chat",
            "temporary_data": {
                "channel_response_task": {
                    "service": "autocrm-communication",
                    "task": "receive_converse_response",
                    "kwargs": <temporary_data>
                }
            },
            "response_length": "agent",
            "communication_data": {
                "whatsapp_message_id": "<provider message id>",
                "user_sent_time": "<timestamp when user sent message>",
                "webhook_received_time": "<timestamp when webhook reached server>"
            }
        }

    Args:
        data (dict): Raw webhook payload received from the WhatsApp provider.
        *args: Additional positional arguments.
        **kwargs: Contains context such as provider name, route metadata,
                  signature headers, or token data.

    
    calls the converse task to get the response back.
    gryd.create_async_task(
            CONVERS_TASK_NAME,
            CONVERS_SERVICE_NAME,
            kwargs=converse_kwargs
        )

    
    """

    

