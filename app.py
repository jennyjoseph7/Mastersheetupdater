from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp
from gryd_worker.gryd_routes import payload_decorator
from models import model as base_model
from ai_service import ai_service_app
#from communication import process_webhook
#from voice import process_webhook
import os
from flask import request
from config import *

gryd.SERVICE = f"{AUTOCRM_APP_ENTERPRISE_ID}-app"
QM = gryd.set_queue_manager()
logger = gryd.hp.get_logger(AUTOCRM_APP_ENTERPRISE_ID)
app_dict = gryd_routes.make_app(__name__, current_module = __name__)                                                                 
app = app_dict['app']

def SETUP(skip_models = False, skip_data = False, start_models_from = None, start_data_from = None):
    gryd.setup_gryd_enterprise(AUTOCRM_APP_ENTERPRISE_ID, email = AUTOCRM_ADMIN_ID, phone_number = AUTOCRM_ADMIN_PHONE_NUMBER, password = AUTOCRM_ADMIN_PASSWORD)
    enterprise = base_model.Enterprise("core")
    if not skip_models:
        with hp.read_file(DATA_DIR, "model_sequence.json") as model_sequence:
            for model_name in model_sequence:
                if start_models_from and model_name != start_models_from:
                    logger.info(f"Skipping model: {model_name}, starting from: {start_models_from}")
                    continue
                start_models_from = None
                with hp.read_file(DATA_DIR, f"{model_name}.json") as model_json:
                    logger.info(f"Posting model: {model_name}")
                    try:
                        enterprise.post_model(model_name, model = model_json)
                    except Exception as e:
                        logger.error(f"Error posting model: {model_name}")
                        raise
                    logger.info(f"Model posted successfully: {model_name}")
    if not skip_data:
        with hp.read_file(BASE_DIR, "seed", "data_sequence.json") as data_sequence:
            for data_name in data_sequence:
                if start_data_from and data_name != start_data_from:
                    logger.info(f"Skipping data: {data_name}, starting from: {start_data_from}")
                    continue
                start_data_from = None
                filename = hp.joinpath(BASE_DIR, "seed", f"{data_name}s.json")
                logger.info(f"Posting data: {data_name} from filename: {filename}")
                try:
                    gryd.post_objects_from_data(data_name, AUTOCRM_APP_ENTERPRISE_ID, filename = filename)
                except Exception as e:
                    logger.error(f"Error posting data for: {data_name} from filename: {filename}")
                    raise
                logger.info(f"Data posted successfully: {data_name}")


@app.route("/webhook/<channel>/<channel_provider>", methods = ["GET","POST"])
@app.route("/webhook/<channel>/<channel_provider>/<enterprise_id>", methods = ["GET","POST"])
@app.route("/webhook/<channel>/<channel_provider>/<enterprise_id>/<conversation_id>", methods = ["GET","POST"])
def webhook(channel, channel_provider, enterprise_id = AUTOCRM_APP_ENTERPRISE_ID, conversation_id = None):
    payload = request.get_json(silent = True) or hp.parse_forms_dict(request.values.to_dict(flat = False))
    logger.info(f"Webhook received for channel: {channel}, channel provider: {channel_provider}, enterprise id: {enterprise_id}, conversation id: {conversation_id}")
    logger.info(f"Payload: {payload}")
    if channel in ["whatsapp", "whatsapp_chat", "whatsapp_voice_note", "whatsapp_voice_call"]:
        #.... do the stuff ....
        pass
    elif channel == "email":
        #.... do the stuff .... 
        pass
    elif channel in ["voice_phone", "voice_call", "voice"]:
        #.... do the stuff ....
        pass
    else:
        return gryd_routes.jsonify({"status": "error", "message": "Invalid channel"}), 400, {"Access-Control-Allow-Origin": "*"}
    return gryd_routes.jsonify({"status": "ok"}), 200, {"Access-Control-Allow-Origin": "*"}

if __name__ == "__main__":
    app.register_blueprint(ai_service_app.ai_service_routes)
    app.register_blueprint(gryd_routes.gryd_routes)
    app.run(debug=True, host=app_dict['host'], port=app_dict['port'])

