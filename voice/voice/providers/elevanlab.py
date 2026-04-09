from elevenlabs import ElevenLabs
import os, sys, json
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)
import utils
from flask import Flask, app, request, jsonify, Blueprint
from ..utils import helpers as voice_helpers
import datetime
from datetime import datetime
import pytz
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp
import config


logger = utils.get_logger(__name__)


app = Blueprint('elevanlab_provider', __name__)

API_KEY = os.environ.get("EXTERNAL_LLM_API_KEY", "sk_e232d2802c87154961d0fcdf71f5b418735282cc9a61a179")
AGENT_ID = os.environ.get("DEFAULT_AGENT_ID", "agent_6501kg4h48mbfhp8cryeh1a66t3j")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "phnum_8201k1anbf9wet6v915q8arr1vmz")


# enterprise api key - sk_e232d2802c87154961d0fcdf71f5b418735282cc9a61a179

def format_transcript(transcript, start_time_unix):
    from datetime import datetime
    session_history = []
    if not transcript:
        return []
    func = lambda x: start_time_unix + float(x)
    for msg in transcript:
        session_history.append({
            "role":msg.get('role'),
            "message":msg.get('message','').replace('.','') if msg.get('message') else '',
            "timestamp": func(msg.get('time_in_call_secs',0.0))
        })
    
    return session_history

def make_call_twilio(session_data, *args, **kwargs):
    elevenlabs_client = ElevenLabs(api_key=API_KEY)
    number = session_data.get("phone_number", "918850988794") #for test
    session_id = session_data.get('session_id')
    agent_id = session_data.get('agent_id')

        

    initial_config = {
        "type": "conversation_initiation_client_data",
        "dynamic_variables": session_data.get("dynamic_variables", {}),
        "user_id": session_id, 
    }
    # Set language presets
    initial_config["conversation_config"] = {
        "language_presets": {
            "en": {
                "overrides": {
                    "agent": {
                        "first_message": "",
                        "language": "en"
                    }
                }
            },
            "hi": {
                "overrides": {
                    "agent": {
                        "first_message": "",
                        "language": "hi"
                    }
                }
            }
        }
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

    logger.info(f"Initiating call with config: {json.dumps(initial_config, indent=2)}")
    logger.info(f"Using phone number: {number} and agent_id: {agent_id}")
    logger.info(f"Using phone number ID: {PHONE_NUMBER_ID}")
    response = elevenlabs_client.conversational_ai.twilio.outbound_call(
        agent_id=agent_id,
        agent_phone_number_id= session_data.get("agent_number", PHONE_NUMBER_ID),
        to_number=number,
        conversation_initiation_client_data=initial_config
    )
    return response.dict()

#https://ambal.loca.lt/twilio-conversation
#https://autobot-dev.gryd.in/twilio-conversation
@app.route("/twilio-conversation", methods=["POST"])
def process():
    data = request.get_json(silent=True) or {}
    twilio_callback_events(data)
    return jsonify({"status": "ok"}), 200, {"Access-Control-Allow-Origin": "*"}


def twilio_callback_events(data: dict):
    import gryd_tasks
    data = dict(data)
    body = data.get("data", {})
    if data.get("type") == "post_call_audio":
        session_id = body.get("user_id", "2f7a2c16541d3348")
        local_path = voice_helpers.save_audio_buffer_to_file(body.get("full_audio", ""), ext="mp3")
        audio_url = voice_helpers.func_gryd_file_system(local_path, media_type="audio")
        os.remove(local_path)
        body["recording_url"] = audio_url

        session_model = config.AutocrmModel(config.SESSION_MODEL_NAME, logger = logger )
        session_model.update(session_id, {"call_recording": body.get("recording_url")})
        return     

    if data.get('type') == "call_initiation_failure":
        session_id = body.get("user_id", "2f7a2c16541d3348")
        body = body.get('metadata', {}).get('body', {})
        logger.info(f"Twilio callback event data from metadata: {dict(body)}")
    elif data.get("type")=="post_call_transcription":
        session_id = body.get("user_id", "2f7a2c16541d3348")
        body["CallSid"] = body.get("metadata",{}).get('phone_call',{}).get('call_sid')
        body["CallStatus"] = "completed"

    logger.info(f"Final Twilio callback event data: {json.dumps(body, indent=2)}")

    call_status = body.get('CallStatus')

    if call_status in ['completed', 'done']:
        ## NOTE: updating billing for reached in post call because we dont get events/callbacks when call is connected.
        yy = gryd_tasks.post_billing_object("reached", session_id)

        duration = float(body.get("metadata", {}).get("call_duration_secs", 0.0))
        xx = gryd_tasks.post_billing_object("completed", session_id, duration)

        session_history = format_transcript(body.get('transcript'), body.get('metadata', {}).get('accepted_time_unix_secs'))
        logger.info(f"SESSION_HISTOR: {session_history}")
        transcript_summary = body.get("analysis",{}).get("transcript_summary")

        gryd_tasks.gryd.create_async_task(
            "end_session_and_post_process",
            config.AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME,
            args  = [],
            kwargs={
                "session_id": session_id,
                "additional_dict":{
                    "history": session_history,
                    "status": "completed",
                    "summary": transcript_summary
                },
                "channel": "voice_phone"
            })
        
    elif call_status in ["queued", 'initiated', 'ringing', 'answered',"in-progress"]:
        gryd_tasks.post_contact_status_voice(session_id = session_id, message_id=session_id, **{"status": call_status})
    elif call_status in ["no-answer", "busy", "canceled", 'failed', 'error', 'unknown']:
        gryd_tasks.post_contact_status_voice(session_id = session_id, message_id=session_id, **{"status": call_status})


