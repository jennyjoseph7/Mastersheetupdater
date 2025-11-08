from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp
from gryd_worker.gryd_routes import payload_decorator
from models import model as base_model
from ai_service import ai_service_app
import os
AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")
AUTOCRM_ADMIN_ID = os.environ.get("AUTOCRM_ADMIN_ID", "ananth+autocrm-app@i2ce.in")
AUTOCRM_ADMIN_PHONE_NUMBER = os.environ.get("AUTOCRM_ADMIN_PHONE_NUMBER", "99980838165")
AUTOCRM_ADMIN_PASSWORD = os.environ.get("AUTOCRM_ADMIN_PASSWORD", "D@vei2ce")
BASE_DIR = hp.dirname(__file__)
DATA_DIR = hp.join(BASE_DIR, "data")

gryd.SERVICE = f"{AUTOCRM_APP_ENTERPRISE_ID}-app"
QM = gryd.set_queue_manager()
logger = gryd.hp.get_logger(AUTOCRM_APP_ENTERPRISE_ID)

def SETUP():
    gryd.setup_gryd_enterprise(AUTOCRM_APP_ENTERPRISE_ID, email = AUTOCRM_ADMIN_ID, phone_number = AUTOCRM_ADMIN_PHONE_NUMBER, password = AUTOCRM_ADMIN_PASSWORD)
    enterprise = base_model.Enterprise("core")
    with hp.read_file(DATA_DIR, "model_sequence.json") as f:
        model_sequence = hp.json.load(f)
    for model_name in model_sequence:
        with hp.read_file(DATA_DIR, f"{model_name}.json") as f:
            model_json = hp.json.load(f)
            enterprise.post_model(model_name, model = model_json)
    with hp.read_file(DATA_DIR, "data_sequence.json") as f:
        data_sequence = hp.json.load(f)
    for data_name in data_sequence:
        filename = hp.joinpath(BASE_DIR, "seed", f"{data_name}s.json")
        gryd.post_objects_from_data(data_name, AUTOCRM_APP_ENTERPRISE_ID, filename = filename)


if __name__ == "__main__":
    app_dict = gryd_routes.make_app(__name__, current_module = __name__)                                                                 
    app = app_dict['app']
    app.register_blueprint(ai_service_app.ai_service_routes)
    app.register_blueprint(gryd_routes.gryd_routes)
    app.run(debug=True, host=app_dict['host'], port=app_dict['port'])

