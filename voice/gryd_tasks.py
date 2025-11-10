import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp
from gryd_worker.gryd_routes import payload_decorator
from models import model as base_model
from ai_service import ai_service_app

gryd.SERVICE = os.environ.get("AUTOBOT_CONVERSATION_SERVICE_NAME","autocrm-voice")

gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(__name__)




@gryd.is_task()
def trigger_voice_call(user_data, *args, **kwargs):
    """
    Trigger a call to user: 
    It will create data for session and person and keep until call gets connected to user.
    Data use to generate prompt : {
      "user_name":"",
      "<vehicle_specific>" : "<value>"
      ......

      "campaign_id":"",
      "campaign_workflow_id":""

    }

    """


    yield {
        "seesion_id":"",
        "user_id":"",
        "call_sid": "<voice_provider_response_sid>",
        "campaign_id": "<campaign_id>"
    }