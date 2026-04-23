import gryd_tasks
from gryd_tasks import *
import config
import os, sys, json, time
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp

gryd.SERVICE = getattr(config, "AUTOCRM_VOICE_SERVICE_NAME_1")
gryd.set_queue_manager()

@gryd.is_a_task(function_name="trigger_voice_call")
def trigger_voice_call(*args, **kwargs):
    list(gryd_tasks.trigger_voice_call(*args, **kwargs))
    yield
<<<<<<< HEAD

=======
>>>>>>> staging
