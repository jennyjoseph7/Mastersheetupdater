
import os,sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from gryd_worker import gryd
gryd.SERVICE = os.environ.get("AUTOBOT_CONVERSATION_SERVICE_NAME","autocrm-conversation")
import json

from ai_service import ai_service_app

mlogger = gryd.hp.get_logger(__name__)

def yield_primary_prompt(*args, **kwargs):
    request_data = kwargs.get("request_data")
    ###TODO check prompt template model to find the correct prompt for this user and campaign
    yield {"prompt":"Hello World get_primary_prompt"}

def specific_prompt(*args, **kwargs):
    ###TODO find prompt based on filters provided
    yield {"prompt":"Hello World get_specific_prompt"}


def run_prompt_sync(user_query="",system_prompt="",history="", messages=[], **kwargs):
    request_data = kwargs.get("request_data")
    resp = ""
    if messages:
        resp = ai_service_app.get_llm_response(messages=messages,audit_params={"session_id":request_data.get("session_id")},**{"model_identifier":request_data.get("temporary_data").get("model_identifier","gcp-gemini-2.5-flash-lite")})
    else:
        resp = ai_service_app.get_llm_response(user_query=user_query,system_prompt=system_prompt,history=history,audit_params={"session_id":kwargs.get("session_id")},**{"model_identifier":request_data.get("temporary_data").get("model_identifier","gcp-gemini-2.5-flash-lite")})
    
    ###TODO write valid json detector and retry if not valid
    return resp