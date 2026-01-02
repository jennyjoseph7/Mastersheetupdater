from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp, beats as cron_worker
from gryd_worker.gryd_routes import payload_decorator, signup_decorator
from models import model as base_model
from analytics.loader import load_stored_procedures
from ai_service import ai_service_app
# from communication.connectors.connector_whatsapp import process_forwarded_webhook
from db_routes import db_routes, ai_service_app
# from voice.voice.providers.twilio import app as twilio_routes
# from voice.voice.providers.elevanlabs_tatatele import app as elevanlabs_tatatele_app
import os
from flask import request,jsonify, send_file
from config import *
import autocrm_validator
import io
import json
import requests
import hmac
import hashlib
from core.razorpay_service import razorpay_webhook_handler

gryd.SERVICE = f"{AUTOCRM_APP_ENTERPRISE_ID}-app"   
QM = gryd.set_queue_manager()
logger = gryd.hp.get_logger(AUTOCRM_APP_ENTERPRISE_ID)
app_dict = gryd_routes.make_app(__name__, current_module = __name__)                                                                 
app = app_dict['app']




def SETUP(skip_models = False, skip_data = False, start_models_from = None, start_data_from = None, skip_cron = False, skip_sp = False, new_db = False, new_environment = False):
    gryd.setup_gryd_enterprise(AUTOCRM_APP_ENTERPRISE_ID, email = AUTOCRM_ADMIN_ID, phone_number = AUTOCRM_ADMIN_PHONE_NUMBER, password = AUTOCRM_ADMIN_PASSWORD)
    enterprise = base_model.Enterprise(AUTOCRM_APP_ENTERPRISE_ID)
    if (not skip_models) or new_db:
        with hp.read_file(DATA_DIR, "model_sequence.json") as model_sequence:
            for model_name in model_sequence:
                if start_models_from and model_name != start_models_from:
                    logger.info(f"Skipping model: {model_name}, starting from: {start_models_from}")
                    continue
                start_models_from = None
                post_autocrm_model(model_name, enterprise = enterprise)
    if (not skip_data) or new_db:
        with hp.read_file(BASE_PATH, "seed", "data_sequence.json") as data_sequence:
            for data_name in data_sequence:
                if start_data_from and data_name != start_data_from:
                    logger.info(f"Skipping data: {data_name}, starting from: {start_data_from}")
                    continue
                start_data_from = None
                post_autocrm_data(data_name)
    if not skip_sp:
        load_stored_procedures()
    if (not skip_cron) or new_environment:
        # cron_worker.add_cron_job(AUTOCRM_APP_ENTERPRISE_ID, "clear_otp_cache", "cron", "*/15 * * * *", logger = logger)
        cron_worker.add_cron_job(
            enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
              task="overall_campaign_summary",
              service=AUTOCRM_CRON_SERVICE_NAME,
              schedule = "*/20 * * * *",
              add_schedule_to_queue=False
            )
        cron_worker.add_cron_job(
            enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
              task="check_inactive_sessions",
              service=AUTOCRM_CRON_SERVICE_NAME,
              schedule = "*/15 * * * *",
              kwargs={"inactivity_time": 1440, "only_for_channels":["whatsapp_chat"]},
              add_schedule_to_queue=False
        )
        cron_worker.add_cron_job(
            enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
              task="template_approval",
              service=AUTOCRM_CRON_SERVICE_NAME,
              schedule = "*/20 * * * *",
              add_schedule_to_queue=False
        )
        
        cron_worker.add_cron_job(
            enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
              task="performance_summary",
              service=AUTOCRM_CRON_SERVICE_NAME,
              schedule = "*/20 * * * *",
              add_schedule_to_queue=False
        )
        
        
@app.route("/webhook/<channel>/<channel_provider>", methods = ["GET","POST"])
@app.route("/webhook/<channel>/<channel_provider>/<enterprise_id>", methods = ["GET","POST"])
@app.route("/webhook/<channel>/<channel_provider>/<enterprise_id>/<conversation_id>", methods = ["GET","POST"])
def webhook(channel, channel_provider, enterprise_id = AUTOCRM_APP_ENTERPRISE_ID, conversation_id = None):
    payload = request.get_json(silent=True) or hp.parse_forms_dict(request.values.to_dict(flat=False))
    language = payload.get("language", "english")
    logger.info(f"Webhook received for channel={channel}, provider={channel_provider}, enterprise={enterprise_id}, conversation={conversation_id}, language={language}")
    if channel in ["whatsapp", "whatsapp_chat", "whatsapp_voice_note", "whatsapp_voice_call"]:
        arg_d=(channel, conversation_id)
        gryd.create_async_task("process_forwarded_webhook", "autocrm-communication",args=arg_d , kwargs=payload)
    elif channel == "email":
        #.... do the stuff .... 
        pass
    elif channel in ["voice_phone", "voice_call", "voice"]:
        #.... do the stupayloadff ....
        pass
    else:
        return gryd_routes.jsonify({"status": "error", "message": "Invalid channel"}), 400, {"Access-Control-Allow-Origin": "*"}
    return gryd_routes.jsonify({"status": "ok"}), 200, {"Access-Control-Allow-Origin": "*"}


@app.route("/webhook/ses-status", methods=["POST", "GET"])
def handle_ses_webhook():
    logger.info(f"SES Webhook received")
    return 


@app.route('/test_voice_agent/<provider>/<session_id>', methods = ["POST"])
def test_voice_agent(provider, session_id):
    import voice
    payload = request.get_json(silent=True) or hp.parse_forms_dict(request.values.to_dict(flat=False))
    prompt = payload.get("prompt")
    
    if not prompt:
        user_data = payload.get('user_data')
        conversation_id = payload.get('conversation_id')
        campaign_id = payload.get('campaign_id')
    

    response = {
        "status":"connected",  #failed 
        "wss_url":"<websocket_url>"
    }
    return gryd_routes.jsonify(response), 200, {"Access-Control-Allow-Origin": "*"}





app.register_blueprint(ai_service_app.ai_service_routes)
app.register_blueprint(db_routes)
# app.register_blueprint(twilio_routes)
# app.register_blueprint(elevanlabs_tatatele_app)



WEBHOOK_SECRET = "AUTOBOT_DAVEAI_2025"

def verify_webhook_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    
    generated_signature = hmac.new(
        bytes(secret, "utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(generated_signature, signature)


@app.route("/webhook/razorpay", methods=["POST"])
def razorpay_webhook():
    payload_body = request.data 
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not verify_webhook_signature(payload_body, signature, WEBHOOK_SECRET):
        return jsonify({"status": "error", "message": "Invalid signature"}), 400

    payload = request.json

    try:
        razorpay_webhook_handler(payload)  
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == "__main__":

    app.run(debug=True, host=app_dict['host'], port=app_dict['port'])

