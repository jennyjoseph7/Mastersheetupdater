from gryd_worker import gryd, gryd_routes, gryd_helpers as hp
import os, sys, csv
AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")
AUTOCRM_ADMIN_ID = os.environ.get("AUTOCRM_ADMIN_ID", "ananth+autocrm-app@i2ce.in")
AUTOCRM_ADMIN_PHONE_NUMBER = os.environ.get("AUTOCRM_ADMIN_PHONE_NUMBER", "99980838165")
AUTOCRM_ADMIN_PASSWORD = os.environ.get("AUTOCRM_ADMIN_PASSWORD", "D@vei2ce")
AUTOCRM_CRON_SERVICE_NAME = os.environ.get("AUTOCRM_CRON_SERVICE_NAME", "autocrm-cron")
AUTOCRM_CONVERSATION_SERVICE_NAME = os.environ.get("AUTOCRM_CONVERSATION_SERVICE_NAME", "autocrm-conversation")
AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME = os.environ.get("AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME", "autocrm-conversation-post-process")
AUTOCRM_AGENT_SERVICE_NAME = os.environ.get("AUTOBOT_AGENT_SERVICE_NAME", "autocrm-agent")
AUTOCRM_VOICE_SERVICE_NAME = os.environ.get("AUTOCRM_VOICE_SERVICE_NAME", "autocrm-voice")
AUTOCRM_COMMUNICATION_SERVICE_NAME = os.environ.get("AUTOCRM_COMMUNICATION_SERVICE_NAME", "autocrm-communication")
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
AUTOCRM_CORE_SERVICE_NAME = os.environ.get("AUTOCRM_CORE_SERVICE_NAME", "autocrm-core")
AUTOCRM_CAMPAIGN_SERVICE_NAME = os.environ.get("AUTOCRM_CAMPAIGN_SERVICE_NAME", "autocrm-campaign")
GRYD_FILE_USER_ID = os.environ.get("GRYD_FILE_USER_ID")
GRYD_FILE_API_KEY = os.environ.get("GRYD_FILE_API_KEY")
GRYD_FILE_SERVER_URL = os.environ.get("GRYD_FILE_SERVER_URL", "https://file-prod.gryd.in")
AUTOCRM_CALL_CONNECTED_PRICE = os.environ.get("AUTOCRM_CALL_CONNECTED_PRICE", 2)
AUTOCRM_CALL_CONNECTED_ITEM = "call_connected"
AUTOCRM_CALL_CONNECTED_UNITS = "count"
AUTOCRM_CALL_COMPLETED_PRICE = os.environ.get("AUTOCRM_CALL_COMPLETED_PRICE", 0.167)
AUTOCRM_CALL_COMPLETED_UNITS = "seconds"
AUTOCRM_CALL_COMPLETED_ITEM = "call_completed"
AUTOCRM_CURRENCY = os.environ.get("AUTOCRM_CURRENCY", "INR")
AUTOCRM_WEBSOCKET_BASE_URL = os.environ.get("AUTOCRM_WEBSOCKET_BASE_URL", "wss://autobot-messenger.gryd.in/ws")
AUTOCRM_MESSAGE_DELIVERED_PRICE = os.environ.get("AUTOCRM_MESSAGE_DELIVERED_PRICE", 0.75)
AUTOCRM_MESSAGE_DELIVERED_UNITS = "count"
AUTOCRM_MESSAGE_DELIVERED_ITEM = "message_delivered"
AUTOCRM_RESPONSE_PROVIDED_PRICE = os.environ.get("AUTOCRM_RESPONSE_PROVIDED_PRICE", 0.90)
AUTOCRM_RESPONSE_PROVIDED_UNITS = "500_characters"
AUTOCRM_RESPONSE_PROVIDED_ITEM = "response_to_query"
WHATSAPP_PROVIDER_NAME="airtel"
WHATSAPP_PROVIDER_NUMBER="917795030574"
VOICE_PROVIDER_NAME ="tata-tele"
MAX_AUDIENCE_ERRORS = os.environ.get("MAX_AUDIENCE_ERRORS", 10)
DEFAULT_OTP = os.environ.get("DEFAULT_OTP", "560102")
ALLOWED_COUNTRY_CODES = list(map(str.strip, os.environ.get("ALLOWED_COUNTRY_CODES", "+971,+966,+62,+63,+91,+1").split(",")))
OTP_TEMPLATE_ID = os.environ.get("OTP_TEMPLATE_ID", "01kckk7efvtft7gqwg3cfwfsqe")

#model names
SESSION_MODEL_NAME = "session"
BILLING_MODEL_NAME = "billing"

#razorpay
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_htVSSrrdDO0Mvj")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "1fanIuyzO7pmq6WPsAehnbF6")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "AUTOBOT_DAVEAI_2025")

BASE_PATH = hp.dirname(hp.abspath(__file__))
DATA_DIR = hp.joinpath(BASE_PATH, "data")
SERVICE = os.environ.get("SERVICE", "autocrm-app")
if BASE_PATH not in sys.path:
    sys.path.append(BASE_PATH)

clogger = hp.get_logger(__name__)


class AutocrmModel:

    def __init__(self, model_name, logger = None):
        self.model_name = model_name
        self.logger = logger or clogger
        self.model = gryd.base_model.Model(model_name, AUTOCRM_APP_ENTERPRISE_ID)

    def get_model(self):
        return self.model
   
    @property
    def name(self):
        return self.model.name

    def get_attributes(self, *args, **kwargs):
        return self.model.get_attributes(*args, **kwargs)

    @property
    def attributes(self):
        return self.model._model_ref.attributes

    def post(self, data):
        self.model.post(data)
        self.logger.info(f"Data posted successfully: {self.model_name}")

    def get(self, id):
        return self.model.get(id)

    def update(self, id, data):
        self.model.update(id, data)
        self.logger.info(f"Data updated successfully: {self.model_name}")

    def delete(self, id):
        self.model.delete(id)
        self.logger.info(f"Data deleted successfully: {self.model_name}")

    def filter(self, **kwargs):
        return self.model.yield_list(**kwargs)

    def list(self, **kwargs):
        return self.model.list(**kwargs)

    def count(self, **kwargs):
        return self.model.count(**kwargs)

    def delete_many(self, filters, **kwargs):
        self.model.delete_many(filters, **kwargs)
        self.logger.info(f"Data deleted successfully: {self.model_name}")
    
    def update_many(self, instance, filters = None,  **kwargs):
        self.model.update_many(instance, filters, **kwargs)
        self.logger.info(f"Data updated successfully: {self.model_name}")

    def iadd(self, id, attribute, value):
        self.model.iadd(id, attribute, value)
        self.logger.info(f"Data added successfully: {self.model_name}")

    def iupdate(self, id, instance):
        self.model.iupdate(id, instance)
        self.logger.info(f"Data updated successfully: {self.model_name}")

def load_autocrm_models(logger = None):
    logger = logger or clogger
    models = {}
    with hp.read_file(DATA_DIR, "model_sequence.json") as model_sequence:
        for model_name in model_sequence:
            models[model_name] = AutocrmModel(model_name, logger = logger)
            logger.info(f"Loaded model: {model_name}")
    return models

def post_autocrm_model(model_name, enterprise = None, logger = None):
    logger = logger or clogger
    enterprise = enterprise or gryd.base_model.Enterprise(AUTOCRM_APP_ENTERPRISE_ID)
    with hp.read_file(DATA_DIR, f"{model_name}.json") as model_json:
        logger.info(f"Posting model: {model_name}")
        try:
            enterprise.post_model(model_name, model = model_json)
            logger.info(f"Model posted successfully: {model_name}")
            return gryd.base_model.Model(model_name, AUTOCRM_APP_ENTERPRISE_ID)
        except Exception as e:
            logger.error(f"Error posting model: {model_name}")
            raise


def post_json_file(filename_json, autocrm_model, start_from = 0, logger = None):
    logger = logger or clogger
    m = autocrm_model
    if isinstance(autocrm_model, str):
        m = AutocrmModel(model_name = autocrm_model, logger = logger)
    data_name = m.name
    index = 0
    try:
        logger.info(f"Posting data: {data_name} from filename: {filename_json}")
        with hp.read_file(filename_json) as data_json:
            for data in data_json:
                if index < start_from:
                    index += 1
                    continue
                m.post(data)
                logger.info(f"Data posted successfully: {data_name}, index {index}")
                index += 1
        return m
    except Exception as e:
        logger.error(f"{e}\nError posting data for: {data_name} for index {index} in {filename_json}")
        raise

def post_csv_file(filename_csv, autocrm_model, start_from = 0, logger = None):
    logger = logger or clogger
    m = autocrm_model
    if isinstance(autocrm_model, str):
        m = AutocrmModel(model_name = autocrm_model, logger = logger)
    data_name = m.name
    linenum = 0
    list_keys = list(map(lambda x: x[0], (filter(lambda x: x[1].type in ('list', 'string_list', 'stringlist', 'number_list', 'numberlist'),  m.attributes.items()))))
    object_keys = list(map(lambda x: x[0], (filter(lambda x: x[1].type in ('nested_object'),  m.attributes.items()))))
    object_list_keys = list(map(lambda x: x[0], (filter(lambda x: x[1].type in ('object_list'),  m.attributes.items()))))
    bool_keys = list(map(lambda x: x[0], (filter(lambda x: x[1].type in ('bool'),  m.attributes.items()))))
    logger.info(f"Posting data: {data_name} from filename: {filename_csv}")
    try:
        with open(filename_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            logger.info(f"Headers for {data_name}: {headers}")
            for linenum, row in enumerate(reader, 2):
                if linenum < start_from:
                    continue
                row = {k.strip(): v.strip() for k, v in row.items()}
                for k in bool_keys:
                    if row[k].lower() in ['true', '1', 'yes']:
                        row[k] = True
                    elif row[k].lower() in ['false', '0', 'no']:
                        row[k] = False
                    elif row[k]:
                        raise ValueError(f"Incorrect boolean value {row[k]}")
                for k in list_keys:
                    rk = row[k]
                    row[k] = list(map(lambda x: x.strip(), rk.split(',')))
                    logger.info("Converting list attribute %s: %s -> %s", k, rk, row[k])
                for k in object_keys:
                    r = {}
                    mr = list(map(lambda x: x.strip(), row[k].split(',')))
                    try:
                        r = {x[0].strip():x[1].strip() for x in mr.split(":")}
                    except ValueError as e:
                        raise ValueError(f"Value for for attribute {k} is not parseable into nested_object: {row[k]}")
                    else:
                        row[k] = r
                for k in object_list_keys:
                    r = []
                    mrl = list(map(lambda x: x.strip(), row[k].split('|')))
                    for mk in mrl:
                        try:
                            rk = {x[0].strip():x[1].strip() for x in mk.split(":")}
                        except ValueError as e:
                            raise ValueError(f"Value for for attribute {k} is not parseable into nested_object: {row[k]}")
                        else:
                            r.append(rk)
                    row[k] = r
                row = {k:v for k, v in row.items() if v not in (None, '')}
                m.post(row)
                logger.info(f"Data posted successfully: {data_name}, linenum {linenum}")
    except Exception as e:
        logger.error(f"{e}\nError posting data for: {data_name} for linenum {linenum} in {filename_csv}")
        raise

def post_autocrm_data(data_name, logger = None, reseed = False, start_from = 0):
    logger = logger or clogger
    filename_json = hp.joinpath(BASE_PATH, "seed", f"{data_name}s.json")
    filename_csv = hp.joinpath(BASE_PATH, "seed", f"{data_name}s.csv")
    m = AutocrmModel(model_name = data_name, logger = logger)
    if reseed:
        m.delete_many()
    if hp.isfile(filename_csv):
        post_csv_file(filename_csv, m, start_from = start_from, logger = logger)
    elif hp.isfile(filename_json):
        post_json_file(filename_json, m, start_from = start_from, logger = logger)
    else:
        logger.error(f"File: {filename_csv} or {filename_json} not found")
        raise FileNotFoundError(f"Seed file for : {data_name} not found")


