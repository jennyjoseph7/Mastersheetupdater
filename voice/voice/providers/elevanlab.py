from elevenlabs import ElevenLabs
import os, sys, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
import utils
from flask import Flask, app, request, jsonify, Blueprint
import datetime
from datetime import datetime
import pytz


logger = utils.get_logger(__name__)


app = Blueprint('elevanlab_provider', __name__)

API_KEY = os.environ.get("EXTERNAL_LLM_API_KEY", "sk_3f302b2e36acc353d040152b3d6c9bc7bf728955483bce75")
AGENT_ID = os.environ.get("DEFAULT_AGENT_ID", "agent_6501kg4h48mbfhp8cryeh1a66t3j")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "phnum_8201k1anbf9wet6v915q8arr1vmz")


def make_call_elevanlab(session_data, *args, **kwargs):
    elevenlabs_client = ElevenLabs(api_key=API_KEY)
    number = session_data.get("phone_number", "918850988794") #for test
    session_id = session_data.get('session_id')
    agent_id = session_data.get('agent_id')

        

    initial_config = {
        "type": "conversation_initiation_client_data",
        "dynamic_variables": session_data.get("dynamic_variables", {}),
        "user_id": session_id, 
    }
    
    if session_data.get("prompt"):
        initial_config["conversation_config_override"] = {
            "agent": {}
        }

        initial_config["conversation_config_override"]["agent"].update({
            "prompt": {
                "prompt": session_data.get("prompt")
            }
        })

        if session_data.get("first_message"):
            initial_config["conversation_config_override"]["agent"].update({"first_message": session_data.get("first_message")})

        if session_data.get("language"):
            initial_config["conversation_config_override"]["agent"].update({"language": session_data.get("language")})

    response = elevenlabs_client.conversational_ai.twilio.outbound_call(
        agent_id=agent_id,
        agent_phone_number_id=PHONE_NUMBER_ID,
        to_number=number,
        conversation_initiation_client_data=initial_config
    )
    return response.dict()


app.route("/twilio-conversation", methods=["POST", "GET"])
def process():
    data = request.get_json(silent=True) or {}
    logger.info(f"Elevenlab Webhook data received: {data}")
    
    session_history = format_transcript(data.get('transcript'), data.get('metadata').get('accepted_time_unix_secs'))


    return jsonify({"status": "ok"}), 200, {"Access-Control-Allow-Origin": "*"}


def twilio_callback_events(data: dict):
    data = dict(data)
    logger.info(f"Twilio callback event data: {dict(data)}")

    if data.get('full_audio'):
        return 
    
    if data.get('failure_reason'):
        data = data.get('metadata', {}).get('body', {})
        logger.info(f"Twilio callback event data from metadata: {dict(data)}")    
    elif data.get('status')=="done":
        data["CallSid"] = data.get("metadata",{}).get('phone_call',{}).get('call_sid')
        data["CallStatus"] = "completed"
    #---------------

    logger.info(f"Final Twilio callback event data: {json.dumps(data, indent=2)}")


    call_status = data.get('CallStatus')
    
    if call_status in ["queued", 'initiated', 'ringing', 'answered',"in-progress"]:
        pass
    elif call_status in ['completed', 'done']:
       pass
    elif call_status in ["no-answer", "busy", "canceled", 'failed', 'error', 'unknown']:
        pass





def format_transcript(transcript, start_time_unix):
    session_history = []
    func = lambda x: datetime.fromtimestamp(start_time_unix+float(x), tz=pytz.timezone("UTC")).strftime("%Y-%m-%d %I:%M:%S %p %z")
    for msg in transcript:
        session_history.append({
            "role":msg.get('role'),
            "message":msg.get('message','').replace('.','') if msg.get('message') else '',
            "timestamp": func(msg.get('time_in_call_secs',0.0))
        })
    
    return session_history