import sys, os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR in sys.path:
    sys.path.remove(BASE_DIR)
sys.path.insert(0, BASE_DIR)
from core.core import generate_otp, dealership_signup, reset_password
from core.razorpay_service import razorpay_webhook_handler
import json
import hmac
import hashlib
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp, beats as cron_worker
from gryd_worker.gryd_routes import payload_decorator, signup_decorator
from models import model as base_model
from analytics.loader import load_stored_procedures
from ai_service import ai_service_app
# from communication.connectors.connector_whatsapp import process_forwarded_webhook
from db_routes import db_routes, ai_service_app
from voice.voice.providers.twilio import app as twilio_routes
from voice.voice.providers.elevanlabs_tatatele import app as elevanlabs_tatatele_routes
from voice.voice.providers.elevanlabs_tatatele_inbound import app as elevanlabs_tatatele_inbound_routes
from voice.voice.providers.elevanlab import app as elevanlab_routes
from trigger_and_run_campaign import app as campaign_test_routes
from core.razorpay_service import razorpay_webhook_handler
from core.core import generate_otp, dealership_signup, reset_password
from cohorts_new.routes.routes import cohort_bp, gryd_orchestration_bp
import os
from flask import Flask,request,jsonify
from config import *
import requests
import autocrm_validator

gryd.SERVICE = f"{AUTOCRM_APP_ENTERPRISE_ID}-app"   
QM = gryd.set_queue_manager()
logger = gryd.hp.get_logger(AUTOCRM_APP_ENTERPRISE_ID)
app_dict = gryd_routes.make_app(__name__, current_module = __name__)                                                                 
app = app_dict['app']

def SETUP(skip_models = False, skip_data = False, start_models_from = None, start_data_from = None, skip_cron = False, skip_sp = False, new_db = False, new_environment = False, reseed = False):
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
                post_autocrm_data(data_name, reseed = reseed or new_db)
    if not skip_sp or new_db:
        load_stored_procedures()
    if (not skip_cron) or new_environment:
        cron_worker.add_cron_job(AUTOCRM_APP_ENTERPRISE_ID, "clear_otp_cache", "cron", "*/15 * * * *", logger = logger)
        # cron_worker.add_cron_job(
        #      enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
        #        task="overall_campaign_summary",
        #        service=AUTOCRM_CRON_SERVICE_NAME,
        #        schedule = "*/10 * * * *",
        #        add_schedule_to_queue=False
        # )
        cron_worker.add_cron_job(
            enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
              task="manage_active_sessions",
              service=AUTOCRM_CRON_SERVICE_NAME,
              schedule = "*/10 * * * *",
              kwargs={"inactivity_timeout_seconds": 10, "only_for_channels":["whatsapp_chat"],"post_process_interval_seconds":10},
              add_schedule_to_queue=False
        )
        cron_worker.add_cron_job(
            enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
              task="template_summary",
              service=AUTOCRM_CRON_SERVICE_NAME,
              schedule = "0 */2 * * *",
              add_schedule_to_queue=False
        )
        
        cron_worker.add_cron_job(
            enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
              task="performance_summary",
              service=AUTOCRM_CRON_SERVICE_NAME,
              schedule = "*/30 * * * *",
              add_schedule_to_queue=False
        )
        cron_worker.add_cron_job(
            enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
              task="reset_auth_creds",
              service=AUTOCRM_CRON_SERVICE_NAME,
              schedule = "*/45 * * * *",
              kwargs={"channel":"whatsapp_chat","provider_name":"Rml"},
              add_schedule_to_queue=False
        )
        
        cron_worker.add_cron_job(
            enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
              task="daily_dealership_summary",
              service=AUTOCRM_CRON_SERVICE_NAME,
            schedule = "*/30 * * * *",
              add_schedule_to_queue=False
        )
        
        cron_worker.add_cron_job(
            enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
              task="scale_down_voice",
              service=AUTOCRM_CRON_SERVICE_NAME,
              schedule = "0 15 * * *",  # Voice workers stop at 8:30 p.m. IST
              add_schedule_to_queue=False
        )
        
        cron_worker.add_cron_job(
            enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
              task="scale_up_voice",
              service=AUTOCRM_CRON_SERVICE_NAME,
              schedule = "0 3 * * *", #Voice workers start at 8.30 a.m. IST
              add_schedule_to_queue=False
        )

        cron_worker.add_cron_job(
            enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
            task="process_all_dealerships_for_voice",
            service=AUTOCRM_CRON_SERVICE_NAME,
            schedule = "*/20 3-13 * * *", #till 7:10pm it runs..
            kwargs={"voice_batch_size": 30},
            add_schedule_to_queue=False
        )
        
        cron_worker.add_cron_job(
            enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
            task="process_dealerships_non_voice",
            service=AUTOCRM_CRON_SERVICE_NAME,
            schedule = "*/20 3-13 * * *", #till 7:10pm it runs..
            kwargs={},
            add_schedule_to_queue=False
        )
        
        cron_worker.add_cron_job(
            enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
              task="mark_inactive_dealerships",
              service=AUTOCRM_CRON_SERVICE_NAME,
              schedule = "15 0 * * *",
              kwargs={"inactive_days": 14},
              add_schedule_to_queue=False
        )
        
        cron_worker.add_cron_job(
            enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
              task="end_campaigns",
              service=AUTOCRM_CRON_SERVICE_NAME,
              schedule="30 13 * * *", 
              kwargs={},
              add_schedule_to_queue=False
        )

@app.route("/list-services", methods = ["GET"])
@app.route("/list-services/<frmt>", methods = ["GET"])
def get_worker_versions(frmt = None):
    from tabulate import tabulate
    environment = gryd.get_environment()
    c = gryd.get_service_connection()
    headers = ["Service", "Version", "Build", "Worker count", "Thread count", "Queue Length"]
    table = list(map(
        lambda x: (x.get(k) for k in ('service', 'version', 'build', 'worker_count', 'worker_job_count', 'queue_length')),
        sorted(c.list_services(environment), key = lambda x: x.get('service'))
    ))
    if not frmt:
        user_agent = request.headers.get('User-Agent', '').lower()
        frmt = 'html' if any(b in user_agent for b in ('mozilla', 'chrome', 'safari', 'firefox', 'edge')) else 'github'
    return tabulate(table, headers = headers, tablefmt=frmt), 200, {"Access-Control-Allow-Origin": "*"}

        
@app.route("/webhook/<channel>/<channel_provider>", methods = ["GET","POST"])
@app.route("/webhook/<channel>/<channel_provider>/<enterprise_id>", methods = ["GET","POST"])
@app.route("/webhook/<channel>/<channel_provider>/<enterprise_id>/<conversation_id>", methods = ["GET","POST"])
def webhook(channel, channel_provider, enterprise_id = AUTOCRM_APP_ENTERPRISE_ID, conversation_id = None):
    # payload = request.get_json(silent=True) or hp.parse_forms_dict(request.values.to_dict(flat=False))
    
    payload = request.get_json(silent=True) or request.form.to_dict() or request.data.decode()
    language = payload.get("language", "english")

    payload.update({
        "channel": channel,
        "enterprise_id": enterprise_id,
        "ent_id":enterprise_id,
        "conversation_id": conversation_id,
        "whatsapp_provider": channel_provider,
        "language": language
    })
    logger.info(f"Webhook payload: {json.dumps(payload, indent=4)}")
    
    logger.info(f"Webhook received for channel={channel}, provider={channel_provider}, enterprise={enterprise_id}, conversation={conversation_id}, language={language}")
    if channel in ["whatsapp", "whatsapp_chat", "whatsapp_voice_note", "whatsapp_voice_call"]:
        arg_d=(channel, conversation_id)
        gryd.create_async_task("process_forwarded_webhook", AUTOCRM_COMMUNICATION_SERVICE_NAME, args=arg_d, kwargs=payload)
    elif channel == "email":
        #.... do the stuff .... 
        pass
    elif channel in ["voice_phone", "voice_call", "voice"]:
        #.... do the stupayloadff ....
        pass
    elif channel in ["rcs"]:
        logger.info(f"RCs webhook received for channel={channel}, provider={channel_provider}")
        gryd.create_async_task("process_rcs_webhook", AUTOCRM_COMMUNICATION_SERVICE_NAME, args=[], kwargs=payload)
    else:
        return gryd_routes.jsonify({"status": "error", "message": "Invalid channel"}), 400, {"Access-Control-Allow-Origin": "*"}
    return gryd_routes.jsonify({"status": "ok"}), 200, {"Access-Control-Allow-Origin": "*"}

@app.route("/webhook/ses-status", methods=["POST", "GET"])
def handle_ses_webhook():
    logger.info(f"SES Webhook received")
    payload = request.get_json(silent=True) or request.form.to_dict() or request.data.decode()
    logger.info(f"SES Webhook payload: {json.dumps(payload, indent=4)}")
    return gryd_routes.jsonify({"status": "ok"}), 200, {"Access-Control-Allow-Origin": "*"}

@app.route("/webhook/sns-incoming-messages", methods=["POST", "GET"])
def handle_sns_incoming_messages_webhook():
    logger.info(f"SNS Incoming Messages Webhook received")
    payload = request.get_json(silent=True) or request.form.to_dict() or request.data.decode()
    logger.info(f"SNS Incoming Messages Webhook payload: {json.dumps(payload, indent=4)}")
    return gryd_routes.jsonify({"status": "ok"}), 200, {"Access-Control-Allow-Origin": "*"}

@app.route("/webhook/rcs-status", methods = ["GET","POST"])
def get_rcs_status():
    payload = request.get_json(silent=True) or request.form.to_dict() or request.data.decode()
    gryd.create_async_task("get_rcs_status", AUTOCRM_COMMUNICATION_SERVICE_NAME, args=[], kwargs=payload)
    return gryd_routes.jsonify({"status": "ok"}), 200, {"Access-Control-Allow-Origin": "*"}


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

@app.route('/dealership_signup', methods = ["POST"])
@gryd_routes.signup_decorator
def dealership_signup_api(**params):
    return dealership_signup(*params.pop('args', []), **params.pop('kwargs', {}))

@app.route('/generate_otp', methods = ["POST"])
@gryd_routes.signup_decorator
def generate_otp_api(**params):
    return generate_otp(*params.pop('args', []), **params.pop('kwargs', {}))

@app.route('/reset_password', methods = ["POST"])
@gryd_routes.signup_decorator
def reset_password_api(**params):
    return reset_password(*params.pop('args', []), **params.pop('kwargs', {}))

@app.route('/get-dealership-details/<agent_user_id>', methods = ["GET"])
@gryd_routes.payload_decorator()
def get_dealership_details(agent_user_id, *args, **kwargs):
    ha = AutocrmModel("human_agent")
    aid = ha.get(agent_user_id)
    if not aid:
        raise ValueError("No such user id: %s for enterprise %s", agent_user_id, AUTOCRM_APP_ENTERPRISE_ID) 
    dealership_id = aid.get('dealership_id')
    if not dealership_id:
        raise ValueError("Dealership is mis-configured for user id: %s", agent_user_id)
    dm = AutocrmModel("dealership")
    dealership = dm.get(dealership_id)
    if not dealership:
        raise ValueError("Dealership is mis-configured for user id: %s", agent_user_id)
    return dealership

@app.route('/blacklist-number/<phone_number>', methods = ["GET", "POST", "DELETE"])
@gryd_routes.payload_decorator()
def blacklist_a_number_func(phone_number, **kwargs):
    logger.info("Kwargs: %s", kwargs)
    params = {}
    for k in ('dealership_id', 'region_id', 'channel'):
        if kwargs.get(k):
            params[k] = kwargs.get(k)
    if request.method.upper() == 'POST':
        return blacklist_a_number(phone_number = phone_number, **params)
    elif request.method.upper() == 'DELETE':
        return remove_a_number_from_blacklist(phone_number = phone_number, **params)
    return is_blacklisted_number(phone_number, **params)




app.register_blueprint(ai_service_app.ai_service_routes)
app.register_blueprint(db_routes)
app.register_blueprint(elevanlabs_tatatele_routes)
app.register_blueprint(elevanlabs_tatatele_inbound_routes)
app.register_blueprint(twilio_routes)
app.register_blueprint(elevanlab_routes)
app.register_blueprint(cohort_bp)
app.register_blueprint(gryd_orchestration_bp)
app.register_blueprint(campaign_test_routes)


logger.info("Gryd's tasks: %s", gryd.LIST_OF_TASKS.keys())

@app.route('/campaign/workflows', methods=["GET"])
@app.route('/campaign/workflows/<frmt>', methods=["GET"])
def get_campaign_workflows(frmt=None):
    try:
        # Load campaign objectives from server model
        m = AutocrmModel('campaign_objective')
        items = m.list() or []

        from tabulate import tabulate
        headers = ["Campaign Objective Name", "Campaign Type", "Campaign Sub Type", "Workflows"]
        table = []
        for it in items:
            name = it.get('campaign_objective_name') or it.get('campaign_objective_id') or ''
            ctype = it.get('campaign_type') or ''
            csub = it.get('campaign_sub_type') or ''
            wfs = it.get('workflows') or []
            if isinstance(wfs, (list, tuple)):
                wfs_val = ', '.join(wfs)
            else:
                wfs_val = str(wfs)
            table.append((name, ctype, csub, wfs_val))

        if not frmt:
            user_agent = request.headers.get('User-Agent', '').lower()
            frmt = 'html' if any(b in user_agent for b in ('mozilla', 'chrome', 'safari', 'firefox', 'edge')) else 'github'

        if str(frmt).lower() == 'json':
            return gryd_routes.jsonify({"status": "ok", "headers": headers, "rows": [list(r) for r in table]}), 200, {"Access-Control-Allow-Origin": "*"}
        return tabulate(table, headers = headers, tablefmt=frmt), 200, {"Access-Control-Allow-Origin": "*"}
    except Exception:
        logger.exception("Failed to load campaign workflows")
        return gryd_routes.jsonify({"status": "error", "message": "internal error"}), 500, {"Access-Control-Allow-Origin": "*"}


def verify_webhook_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    generated_signature = hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(generated_signature, signature)


@app.route("/razorpay/webhook", methods=["POST"])
def razorpay_webhook():
    payload_body = request.get_data(as_text=False)
    signature = request.headers.get("X-Razorpay-Signature", "")
    logger.info(payload_body)
    if not verify_webhook_signature(payload_body, signature, RAZORPAY_WEBHOOK_SECRET):
        return jsonify({"status": "error : razorpay webhook signature verification failed"}), 400

    payload = json.loads(payload_body)
    response = jsonify({"status": "ok"}), 200

    try:
        razorpay_webhook_handler(payload)
    except Exception:
        logger.exception("Webhook processing failed")

    return response



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Run the app/setup')
    parser.add_argument('--port', type=int, help='Port', default=app_dict['port'])
    parser.add_argument('--host', type=str, help='Host', default=app_dict['host'])
    parser.add_argument('--debug', type=bool, help='Debug', default=True)
    parser.add_argument('--setup', action='store_true', help='Setup', default=False)
    parser.add_argument('--skip-models', action='store_true', help='Skip models', default=False)
    parser.add_argument('--skip-data', action='store_true', help='Skip data', default=False)
    parser.add_argument('--skip-cron', action='store_true', help='Skip cron', default=False)
    parser.add_argument('--skip-sp', action='store_true', help='Skip sp', default=False)
    parser.add_argument('--reseed', action='store_true', help='Reseed', default=False)
    parser.add_argument('--start-models-from', type=str, help='Start models from', default=None)
    parser.add_argument('--start-data-from', type=str, help='Start data from', default=None)
    parser.add_argument('--new-db', action='store_true', help='New db', default=False)
    parser.add_argument('--new-environment', action='store_true', help='New environment', default=False)
    args = parser.parse_args()
    if args.setup:
        SETUP(skip_models = args.skip_models, skip_data = args.skip_data, skip_cron = args.skip_cron, reseed = args.reseed, start_models_from = args.start_models_from, start_data_from = args.start_data_from, skip_sp = args.skip_sp, new_db = args.new_db, new_environment = args.new_environment)
    app.run(debug=args.debug, host=args.host, port=args.port)

