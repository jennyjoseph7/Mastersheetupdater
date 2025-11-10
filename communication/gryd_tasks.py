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
    Post contact status: Has to post when campaign trigger happen. 
    For each lead provider status should be posted as new object keeping same message id.
    {
        "message_id":"msh123abcd",
        "channel_provider": <twilio>
        "channel":"voice_phone",
        "phone_number":"8850988794",
        "response_id":"sid12323123",
        "campaign_id" : "campaign_pre_sales_123",
        "provider_status": "initiated"
    }
    
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