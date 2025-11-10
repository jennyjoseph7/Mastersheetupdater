import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


from gryd_worker import gryd
from autocrm_db_helper import get_pg_connector
from prompt import yield_primary_prompt, run_prompt_sync


import time
import json


gryd.SERVICE = os.environ.get("AUTOBOT_CONVERSATION_SERVICE_NAME","autocrm-conversation")

gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(__name__)

def WARM_UP():
    mlogger.info("WARM_UP CALLED")
    with get_pg_connector() as pg:
        pass    
    return

@gryd.is_a_task(
        function_name = "converse", #custom name of function
        job_param = "job_params", #provide a job param attr with this name
        auth_param= "auth_params", #provide a auth param attr with this name
        logger_param = "logger", #provide a logger attr with this name
        input_generator = None, #function to generate input for testing #MANDATORY
        result_verifier = None, #function to verify result should return True or False
        is_agent = False, # True if agent. make sure you adhere to agent input and output 
        depends_on = None, #:Union[List[Tuple[str, str]], List[str], None] either pass list of service,task or just list of task
        expected_input = None, #:Union[Dict[str, str], None] 
        optional_input = None, #:Union[Dict[str, str], None] 
        capability_function = None #:Union[Dict[str, str], None] Defaults to using Docstring
        )
def converse(*args, **kargs):
    '''
    Converse task to setup what to reply and call task avaibale in temporary data depending on channel.
    sample kwargs :- 
    {
        "intent" : "",
        "customer_response" : "",
        "session_id":""
        "channel":"whatsapp_chat",
        "temporary_data": {"channel_response_task":{"service":"channel_service_name_for_task","task":"send_reply_task_name"}},
        "response_length":"full/sentence/paragraph/agent",
        "communication_data":{
            "whatsapp_message_id":"",
            "user_sent_time":"airtel webhook timestamp",
            "webhook_received_time":"comm webhook received time"
        }
    }
    '''
    conversation_process_start_time = time.time()
    logger = kargs.get("logger")
    logger.info("converse called with kwargs == {}".format(kargs))
    request_data = kargs
    response_index = 1
    pass_kwargs = {"request_data":request_data}

    session_id = request_data.get("session_id")

    if not session_id:
        yield from yield_error("error","session_id is required",*args, **pass_kwargs)
        return
    channel = request_data.get("channel")
    if not channel:
        yield from yield_error("error","channel is required",*args, **pass_kwargs)
        return
    with get_pg_connector() as pg:
        session_data = pg.get("session","session_id",session_id)
        if not session_data:
            yield from yield_error("error","session_data fetching failed",*args, **pass_kwargs)
            # return
    message_id = gryd.hp.make_uuid3(time.time(),session_id,request_data.get("user_id"),request_data.get("customer_response"))
    
    ###TODO Post incoming message object
    incoming_message_object = {}

    

    with get_pg_connector() as pg:
        session_data_cache = pg.get("session_data_cache","session_data_cache_id",session_id)
        if not session_data_cache:
            session_data_cache = pg.update("session_data_cache","session_data_cache_id",None,{"session_id":session_id})
            if not session_data_cache:
                yield {"status" : "error","message" : "session_data_cache fetching/creation failed"}
                # return
    if not session_data_cache:
        yield {"status" : "error","message" : "session_data_cache fetching/creation failed"}
    
    pass_kwargs["reply_to"] = message_id
    pass_kwargs["incoming_message_id"] = incoming_message_object
    pass_kwargs["session_id"] = session_id  
    pass_kwargs["reply_to_id"] = message_id
    pass_kwargs["session_data"] = session_data
    pass_kwargs["channel"] = channel
    pass_kwargs["session_data_cache"] = session_data_cache
    pass_kwargs["responses"] = []

    if request_data.get("channel") in ["web_chat_voice","voice_phone","whatsapp_voice_note","whatsapp_voice_call"] and not request_data.get("orchestrate"):
        yield from yield_primary_prompt(*args, **pass_kwargs)
    
    do_orchestrate = True
    for ppresp in execute_primary_prompt(*args, **pass_kwargs):
        if isinstance(ppresp,dict):
            if ppresp.get("intent","") != "filler":
                do_orchestrate = False
        ppresp["index"] = response_index
        response_index += 1
        yield from prune_response(ppresp, **pass_kwargs)
    if do_orchestrate:
        for orch_res in run_orchestrator(*args, **pass_kwargs):
            orch_res["index"] = response_index
            response_index += 1
            yield from prune_response(orch_res,*args, **pass_kwargs)

    conversation_process_end_time = time.time()
    
    ###TODO add in all needed data to be passed for this task
    post_messages_data(*args, **pass_kwargs) 
    
    return


@gryd.is_a_task()
def get_primary_prompt(*args, **kwargs):
    logger = kwargs.get("logger",mlogger)
    logger.info("get_primary_prompt called")

    yield from yield_primary_prompt(*args, **kwargs)
@gryd.is_a_task()
def execute_primary_prompt(*args, **kwargs):
    logger = kwargs.get("logger",mlogger)
    logger.info("execute_primary_prompt called")
    request_data = kwargs.get("request_data")
    prompt = ""
    for i in yield_primary_prompt(*args, **kwargs):
        if isinstance(i,dict):
            if "prompt" in i:
                prompt = i.get("prompt")
    if not prompt:
        yield from yield_error("error","primary prompt not generated required",*args, **kwargs)
        return
    logger.info("prompt == {}".format(prompt))
    
    response = run_prompt_sync(user_query=kwargs.get("request_data").get("customer_response"),system_prompt=prompt,**kwargs)

    yield {"intent" : "llm_response","placeholder":response}



      
    

    

@gryd.is_a_task()
def session_close(*args, **kwargs):
    logger = kwargs.get("logger",mlogger)
    logger.info("session_close called")
    yield {"status" : "complete","session_id":kwargs.get("session_id")}

@gryd.is_a_task()
def add_to_session_cache(*args, **kwargs):
    logger = kwargs.get("logger",mlogger)
    logger.info("add_to_session_cache called")
    yield from yield_status("success","added_to_session_cache",*args, **kwargs)

@gryd.is_a_task()
def run_orchestrator(*args, **kwargs):
    logger = kwargs.get("logger",mlogger)
    logger.info("run_orchestrator called")
    reply_to = str(time.time())
    


    yield {"placeholder":"agent 1 response","intent" : "agent_one","reply_to":reply_to, "message_id" : str(time.time()),"is_last":False,"index" : 1}
    yield {"placeholder":"agent 2 response","intent" : "agent_two","reply_to":reply_to, "message_id" : str(time.time()),"is_last":False,"index" : 2}
    yield {"placeholder":"agent 3 response","intent" : "agent_three","reply_to":reply_to, "message_id" : str(time.time()),"is_last":True,"index" : 3}
    return

@gryd.is_a_task()
def prune_response( resp_message, *args, **kargs):
    logger = kargs.get("logger",mlogger)
    logger.info("prune_response called")
    request_data = kargs.get("request_data")
    response = {}
    if request_data.get("channel") in ["whatsapp_chat"]:
        response_task_data = request_data.get("temporary_data",{}).get("channel_response_task",{})
        ret =  {"temporary_data": response_task_data.get("kwargs",{})}
        response = {
            "placeholder":resp_message,
            "intent" : "agent_one",
            "message_id" : str(time.time()),
            "is_last":False,
            "index" : 1
        }
        ret["response"] = response
        logger.info("sending response to task {}".format(ret))
        # x = gryd.yield_results({"task": response_task_data.get("task"),"service": response_task_data.get("service"),"kwargs" : ret})
        if response_task_data.get("task") and response_task_data.get("service"):
            yield {
                    "_job":{
                        "task":response_task_data.get("task"),
                        "service" :  response_task_data.get("service"),
                        "kwargs" : ret                    }
                }
    kargs["responses"].append(response)
    yield response
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
        is_agent = True, # True if agent. make sure you adhere to agent input and output 
        # depends_on = None, #:Union[List[Tuple[str, str]], List[str], None] either pass list of service,task or just list of task
        expected_input = {"fruit_one":"text","fruit_two" : "number"}, #:Union[Dict[str, str], None] 
        optional_input = {"vegetable" : "text"}, #:Union[Dict[str, str], None] 
        # capability_function = None #:Union[Dict[str, str], None] Defaults to using Docstring
        )
def test_agent(*args, **kwargs):
    '''
    This is my doc string
    '''
    logger = kwargs.get("logger",mlogger)
    logger.info("test_agent called")
    return

def post_messages_data(*args, **kwargs):
    '''
        Picks up all messages sent and posts it to message model
    '''
    pass    

def yield_result(*args, **kwargs):
    pass

def yield_error(error_type, error_description, *args, **kwargs):
    yield {"status" : "error","error_type":error_type, "error_description":error_description,"session_id":kwargs.get("request_data").get("session_id"),"message_id" : kwargs.get("reply_to")}


def yield_status(status_id, status_description, *args, **kwargs):
    yield {"status" : status_id,"message":status_description,"session_id":kwargs.get("request_data").get("session_id"),"message_id" : kwargs.get("reply_to")}




