import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


from gryd_worker import gryd
from autocrm_db_helper import get_pg_connector
from prompt import yield_primary_prompt


import time
import json


gryd.SERVICE = os.environ.get("AUTOBOT_CONVERSATION_SERVICE_NAME","autocrm-conversation")

gryd.set_queue_manager()
logger = gryd.hp.get_logger(__name__)








def WARM_UP():
    logger.info("WARM_UP CALLED")
    with get_pg_connector() as pg:
        pass    
    return

@gryd.is_a_task(
        # function_name = "test_agent", #custom name of function
        # job_param = "job_params", #provide a job param attr with this name
        # auth_param= "auth_params", #provide a auth param attr with this name
        # logger_param = "logger", #provide a logger attr with this name
        # service = "autocrm-conversation", #set name of service under which you want to create the task
        # is_special_task = False, #IGNORE for result queue etc
        # input_generator = None, #function to generate input for testing #MANDATORY
        # result_verifier = None, #function to verify result should return True or False
        # sample_input = None, #Dict[str, Any]
        # is_agent = False, # True if agent. make sure you adhere to agent input and output 
        # depends_on = None, #:Union[List[Tuple[str, str]], List[str], None] either pass list of service,task or just list of task
        # expected_input = None, #:Union[Dict[str, str], None] 
        # optional_input = None, #:Union[Dict[str, str], None] 
        # capability_function = None #:Union[Dict[str, str], None] Defaults to using Docstring
        )
def converse(*args, **kwargs):
    logger = kwargs.get("logger")
    logger.info("converse")
    awaited_tasks= [
            {
                "task":"get_primary_prompt",
                "service" : gryd.SERVICE,
                "kwargs" : {
                    "attr1" : "value1",
                    "attr2" : "value2"
                }
            }
        ]
    loopers = gryd.yield_results(awaited_tasks, timeout=30)
    for result in loopers:
        logger.info(result)
    yield {"placeholder" : "here praveen enjoy my response","intent" : "wow_intent","message_id":str(time.time()),"reply_to" : str(time.time()-1000),"is_last":True}
    return

@gryd.is_a_task(
        # function_name = "test_agent", #custom name of function
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
        # expected_input = None, #:Union[Dict[str, str], None] 
        # optional_input = None, #:Union[Dict[str, str], None] 
        # capability_function = None #:Union[Dict[str, str], None] Defaults to using Docstring
        )
def test_agent(*args, **kwargs):
    '''
    This is my doc string
    '''
    logger = kwargs.get("logger",logger)
    logger.info("test_agent")

    return

@gryd.is_a_task()
def get_primary_prompt(*args, **kwargs):
    logger = kwargs.get("logger",logger)
    logger.info("get_primary_prompt")
    yield from yield_primary_prompt(*args, **kwargs)
    

@gryd.is_a_task()
def session_close(*args, **kwargs):
    logger = kwargs.get("logger",logger)
    logger.info("session_close")
    yield {"status" : "complete","session_id":kwargs.get("session_id")}

@gryd.is_a_task()
def add_to_session_cache(*args, **kwargs):
    logger = kwargs.get("logger",logger)
    logger.info("add_to_session_cache")
    yield {"status" : "complete","session_id":kwargs.get("session_id")}

@gryd.is_a_task()
def run_orchestrator(*args, **kwargs):
    logger = kwargs.get("logger",logger)
    logger.info("run_orchestrator")
    reply_to = str(time.time())
    yield {"placeholder":"agent 1 response","intent" : "agent_one","reply_to":reply_to, "message_id" : str(time.time()),"is_last":False,"index" : 1}
    yield {"placeholder":"agent 2 response","intent" : "agent_two","reply_to":reply_to, "message_id" : str(time.time()),"is_last":False,"index" : 2}
    yield {"placeholder":"agent 3 response","intent" : "agent_three","reply_to":reply_to, "message_id" : str(time.time()),"is_last":True,"index" : 3}
