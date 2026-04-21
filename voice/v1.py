from gryd_tasks import *
import gryd_tasks
from gryd_worker import gryd, gryd_routes, gryd_helpers as hp, gryd_db_helper as dbhp
import config

gryd.SERVICE = config.AUTOCRM_VOICE_SERVICE_NAME_V1
gryd.set_queue_manager()



@gryd.is_a_task(function_name="trigger_voice_call")
def trigger_voice_call(*args, **kwargs):
    """
    This function is a gryd task that triggers a voice call. It takes in arguments and keyword arguments, and then calls the `trigger_voice_call` function from the `gryd_routes` module with those arguments.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        The result of the `trigger_voice_call` function from the `gryd_routes` module.
    """
    list(gryd_tasks.trigger_voice_call(*args, **kwargs))
    yield 
