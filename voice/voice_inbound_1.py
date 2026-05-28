import inbound_call
from inbound_call import *
import config
import os, sys, json, time
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp

gryd.SERVICE = getattr(config, "AUTOCRM_VOICE_INBOUND_SERVICE_NAME_1")
gryd.set_queue_manager()

@gryd.is_a_task(function_name="start_call_from_inbound")
def start_call_from_inbound(*args, **kwargs):
    list(inbound_call.start_call_from_inbound(*args, **kwargs))
    yield
