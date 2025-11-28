

import os
from flask import Blueprint,Response, jsonify,request,session,flash,redirect,url_for, Flask, send_file, after_this_request, render_template, current_app as app, make_response
from flask_orjson import OrjsonProvider
from os.path import exists as ispath, dirname, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, encrypt as enc
from AppConfig.gryd_config import *
# from AppConfig.i2ceHeaders import *
from connectors.communication_configs import *

from connectors.gryd_communication import *
from connectors.connector_whatsapp import *
# from captcha.image import ImageCaptcha
from autocrm_db_helper import get_pg_connector
from config import AUTOCRM_COMMUNICATION_SERVICE_NAME
GRYD_COMMUNICATION_BROKER=os.environ.get("GRYD_COMMUNICATION_BROKER","sqs")
gryd.SERVICE = AUTOCRM_COMMUNICATION_SERVICE_NAME
gryd.BASE_PATH = abspath(dirname(__file__))
gryd.set_queue_manager()
QUEUE_MANAGER = gryd.get_queue_manager(AUTOCRM_COMMUNICATION_SERVICE_NAME)
gryd_routes.gryd = gryd
# gryd.load_service_models()
logger = hp.get_logger(__name__)
app = Flask(__name__)
app.config['SESSION_COOKIE_SECURE'] = True
app.json = OrjsonProvider(app)
host = '0.0.0.0'
HTTP = os.environ.get('HTTP', 'http')
SERVER_NAME = os.environ.get('SERVER_NAME', 'localhost:5031')
if SERVER_NAME != '__NULL__':
    app.config['SERVER_NAME'] = SERVER_NAME
app.config['STATIC_DIR'] = "static/uploads"
app.config['PREFERRED_URL_SCHEME'] = HTTP
app.config['TEMPLATES_AUTO_RELOAD'] = True if 'localhost' in SERVER_NAME else False
app.secret_key = 'zasxcdfvbghnmjk,aqwsderfgtyhjuiklop;zaqwsxcderfvbgtyhnmjuik,.lop;/'
port = int(os.environ.get('SERVER_PORT') or 5031)
app.register_blueprint(gryd_routes.gryd_routes)

def WARM_UP():
    logger.info("WARM_UP CALLED")
    with get_pg_connector() as pg:
        pass    
    return

if __name__ == "__main__":
    app.run(host=host, port = port, debug = True)