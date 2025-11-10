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