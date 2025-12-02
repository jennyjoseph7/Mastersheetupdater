import os
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from config import AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME
from gryd_worker import gryd, gryd_helpers as hp
from autocrm_db_helper import get_pg_connector
from prompt import yield_primary_prompt, run_prompt_sync
json = hp.json
from yield_response import yield_response,yield_error, yield_status
gryd.SERVICE = AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME
gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(gryd.SERVICE)


def WARM_UP():
    mlogger.info("WARM_UP CALLED")
    with get_pg_connector() as pg:
        pass    
    return


@gryd.is_a_task()
def session_close(*args, **kwargs):
    '''
    Called when session is over (1 day since last message/phone call cut). 
    calls agents to analyse call history
    deletes session_data_cache
    sets disposition and disposition description
    '''
    logger = kwargs.get("logger",mlogger)
    logger.info("session_close called")

    ##TODO call all closing tasks for getting stats etc.
    awaited_tasks = []
    awaited_tasks.append({
        "task": "update_lead_data",
        "kwargs": kwargs
    })
    awaited_tasks.append({
        "task": "update_person_data",
        "kwargs": kwargs
    })
    task_result_generator = gryd.yield_results(awaited_tasks)

    for task_result in task_result_generator:
        logger.info(f"Task '{task_result[1]}' status: {task_result[3]} \n") 
    with get_pg_connector() as pg:
        if kwargs.get("history"):
            ##TODO post history into message model
            pass

        if kwargs.get("session_data_cache"):
            pass
        pg.delete("session_data_cache","session_id",kwargs.get("session_id"))

    yield {"status" : "complete","session_id":kwargs.get("session_id")}

@gryd.is_a_task()
def add_to_session_cache(*args, **kwargs):
    logger = kwargs.get("logger",mlogger)
    logger.info("add_to_session_cache called")
    new_session_data = kwargs.get("session_data_cache_data")
    if not new_session_data:
        yield from yield_error("error","session_data_cache_data not found",*args, **kwargs)
        return
    session_id = kwargs.get("session_id")
    with get_pg_connector() as pg:
        session_data_old = pg.get("session_data_cache","session_id",session_id)
        session_data_cache_updated = pg.update("session_data_cache","session_id",session_id,{"session_id":session_id,"data":session_data_old.get("data",{}).update(new_session_data)})
    yield from yield_status("success","added_to_session_cache",*args, **kwargs)
    yield {"session_data_cache":session_data_cache_updated}
    return



@gryd.is_a_task(
        # function_name = "update_person_vehicle", #custom name of function
        # job_param = "job_params", #provide a job param attr with this name
        # auth_param= "auth_params", #provide a auth param attr with this name
        # logger_param = "logger", #provide a logger attr with this name
        # service = "autocrm-conversation", #set name of service under which you want to create the task
        # is_special_task = False, #IGNORE for result queue etc
        # input_generator = None, #function to generate input for testing #MANDATORY
        # result_verifier = None, #function to verify result should return True or False
        # sample_input = None, #Dict[str, Any]
        # is_agent = True, # True if agent. make sure you adhere to agent input and output 
        # depends_on = None, #:Union[List[Tuple[str, str]], List[str], None] either pass list of service,task or just list of task
        # expected_input = {"fruit_one":"text","fruit_two" : "number"}, #:Union[Dict[str, str], None] 
        # optional_input = {"vegetable" : "text"}, #:Union[Dict[str, str], None] 
        # capability_function = None #:Union[Dict[str, str], None] Defaults to using Docstring
        )
def update_person_vehicle(*args, **kwargs):
    '''
    This task called to update the person or vehicle data based on lead model and conversation history from message model.
    '''
    logger = kwargs.get("logger",mlogger)
    logger.info("test_agent called")
    return


@gryd.is_a_task()
def update_lead_data(*args, **pass_kwargs):
    '''
    look at message history for a session and then check the person and existin lead data nad update the lead model attrs
    '''
    pass
@gryd.is_a_task()
def post_visit_data(*args, **pass_kwargs):
    '''
    agent to update the showroom/workshop visit model object based on messages for session
    '''

    session_id = pass_kwargs.get("session_id")
    if not session_id:
        yield from yield_error("error","session_id not passed in kwargs",*args, **pass_kwargs)
    with get_pg_connector() as pg:
        messages = list(pg.list("message","message_id",None,{"session_id":pass_kwargs.get("session_id")}))
        
    pass

@gryd.is_a_task()
def set_feedback(*args, **pass_kwargs):
    '''
    agent to analyse the feedback/review and also post the data to the session model
    '''
    if not pass_kwargs.get("session_id"):
        yield from yield_error("error","session_id not found",*args, **pass_kwargs)
        return
    
    
    pass
