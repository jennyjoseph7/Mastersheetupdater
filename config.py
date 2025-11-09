from gryd_worker import gryd, gryd_routes, gryd_helpers as hp
import os, sys
AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")
AUTOCRM_ADMIN_ID = os.environ.get("AUTOCRM_ADMIN_ID", "ananth+autocrm-app@i2ce.in")
AUTOCRM_ADMIN_PHONE_NUMBER = os.environ.get("AUTOCRM_ADMIN_PHONE_NUMBER", "99980838165")
AUTOCRM_ADMIN_PASSWORD = os.environ.get("AUTOCRM_ADMIN_PASSWORD", "D@vei2ce")
BASE_DIR = hp.dirname(hp.abspath(__file__))
DATA_DIR = hp.joinpath(BASE_DIR, "data")
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
