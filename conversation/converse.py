import os
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from config import AUTOCRM_CONVERSATION_SERVICE_NAME,AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_RESPONSE_PROVIDED_UNITS, AUTOCRM_RESPONSE_PROVIDED_PRICE, AUTOCRM_RESPONSE_PROVIDED_UNITS, AUTOCRM_RESPONSE_PROVIDED_ITEM,AUTOCRM_CORE_SERVICE_NAME, AUTOCRM_CAMPAIGN_SERVICE_NAME
from gryd_worker import gryd, gryd_helpers as hp
from autocrm_db_helper import get_pg_connector
from conversation.prompt import yield_primary_prompt, run_prompt_sync
from yield_response import yield_result,yield_error, yield_status
import math
from datetime import datetime
json = hp.json
import autocrm_validator

CHARACTER_COUNT_TO_CREDIT = 500
PER_TOKEN_COST = 1
TOKEN_COST_CURRENCY = "credits"
gryd.SERVICE = AUTOCRM_CONVERSATION_SERVICE_NAME
THREADS_PER_SESSION = 0.25
gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(gryd.SERVICE)

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
    conversation_process_start_time = hp.time()
    logger = kargs.get("logger",mlogger)
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
        logger.info("got session data == {}".format(session_data))
        if not session_data:
            yield from yield_error("error","session_data fetching failed",*args, **pass_kwargs)
            return
        if not session_data.get("campaign_id"):
            yield from yield_error("error","campaign_id is required",*args, **pass_kwargs)
            return
    message_id = str(gryd.hp.make_uuid3(hp.time(),session_id,request_data.get("user_id"),request_data.get("customer_response")))
    
    ###TODO Post incoming message object
    incoming_message_object = {}

    

    
    
    pass_kwargs["reply_to"] = message_id
    pass_kwargs["incoming_message_id"] = incoming_message_object
    pass_kwargs["session_id"] = session_id  
    pass_kwargs["reply_to_id"] = message_id
    pass_kwargs["session_data"] = session_data
    pass_kwargs["channel"] = channel
    pass_kwargs["session_data_cache"] = setup_session_data_cache(*args, **pass_kwargs)
    pass_kwargs["responses"] = []
    pass_kwargs["first_message_time"] = hp.time()
    dealership_id = pass_kwargs.get("session_data_cache",{}).get("data").get("campaign_data",{}).get("dealership_id")
    # if not dealership_id:
    #     yield from yield_error("error","dealer_id not set in campaign data",*args, **pass_kwargs)
    customer_response = kargs.get("customer_response","")
    if request_data.get("channel") in ["web_chat_voice","voice_phone","whatsapp_voice_note","whatsapp_voice_call"] and not request_data.get("orchestrate"):
        yield from yield_primary_prompt(*args, **pass_kwargs)
        return
    do_orchestrate = True

    out_put_text = ""
    for ppresp in execute_primary_prompt(*args, **pass_kwargs):
        if isinstance(ppresp,dict):
            if ppresp.get("intent","") != "filler":
                do_orchestrate = False
            
            if "_job" in ppresp:
                yield ppresp
                mlogger.info("job == {}".format(ppresp))
                return
        ppresp["index"] = response_index
        response_index += 1
        out_put_text += ppresp.get("placeholder","")
        yield from prune_response(ppresp, **pass_kwargs)
    #if not do_orchestrate and request_data.get("orchestrate"):
    if do_orchestrate:
        for orch_res in run_orchestrator(*args, **pass_kwargs):
            orch_res["index"] = response_index
            response_index += 1
            yield from prune_response(orch_res,*args, **pass_kwargs)

    conversation_process_end_time = hp.time()
    with get_pg_connector() as pg:
        pg.update("session","session_id",session_id,{"last_response_time":hp.time()})
    ###TODO add in all needed data to be passed for this task
    post_messages_data(*args, **pass_kwargs) 
    logger.info("my messages == {}".format(pass_kwargs.get("responses")))
    logger.info("conversation_process_end_time == {}".format(conversation_process_end_time))
    logger.info("conversation_process_start_time == {}".format(conversation_process_start_time))
    logger.info("conversation_process_time == {}".format(conversation_process_end_time-conversation_process_start_time))
    yield post_billing_data(customer_response, out_put_text, pass_kwargs.get("session_data_cache",{}).get("data").get("campaign_data"), dealership_id, channel, request_data)

    return

def post_billing_data(customer_response, out_put_text, campaign_data, dealership_id, channel, request_data):
    in_length = len(customer_response)
    out_length = len(out_put_text)
    total_length = in_length + out_length
    credits = math.ceil(total_length/CHARACTER_COUNT_TO_CREDIT)
    tme = hp.now(as_datetime=False)
    timmm = hp.time()

    campaign_type = campaign_data.get("campaign_type")
    campaign_objective = campaign_data.get("campaign_objective")
    campaign_name = campaign_data.get("campaign_name")
    
    provider = request_data.get("provider") or "unknown"
    contact = request_data.get("contact") or "unknown"
    transaction_type = "debit"
    currency = TOKEN_COST_CURRENCY
    item_desc =  f"{campaign_type} - {campaign_objective} - {campaign_name} - {channel} - {provider} - {contact}"
    return {
        "_job":{
            "task": "post_billing",
            "service" : AUTOCRM_CORE_SERVICE_NAME,
            "args": [dealership_id, transaction_type, "conversation", item_desc, tme, credits, AUTOCRM_RESPONSE_PROVIDED_PRICE, AUTOCRM_RESPONSE_PROVIDED_UNITS, currency,campaign_data.get("campaign_id"), channel],
        }
    }

@gryd.is_a_task()
def post_all_messages_for_session(*args, **pass_kwargs):
    """
    Example input:
    [{
        "reply_to": "1234",
        "customer_response": "hello",
        "request_data": {
            "customer_response": "hello"
        },
        "session_id": "1234",
        "user_id": "5678",
        "responses": [
            {
                "intent": "llm_response",
                "placeholder": "hello",
                "index": 1,
                "created": 1234567890,
                "updated": 1234567890
            }
        ]
    },{
        "reply_to": "1234",
        "customer_response": "hello",
        "request_data": {
            "customer_response": "hello"
        },
        "session_id": "1234",
        "user_id": "5678",
        "responses": [
            {
                "intent": "llm_response",
                "placeholder": "hello",
                "index": 1,
                "created": 1234567890,
                "updated": 1234567890
            }
        ]
    }]
    """
    for x in pass_kwargs.get("history"):
        post_messages_data(*args, **x)


@gryd.is_a_task()
def post_messages_data(*args, **pass_kwargs):
    """
    Saves messages to the session data cache.

    Example input:
    {
        "reply_to": "1234",
        "customer_response": "hello",
        "request_data": {
            "customer_response": "hello"
        },
        "session_id": "1234",
        "user_id": "5678",
        "responses": [
            {
                "intent": "greeting",
                "placeholder": "hello",
                "index": 1,
                "created": 1234567890,
                "updated": 1234567890
            }
        ]
    }

    :param reply_to: The message ID of the message to reply to.
    :param customer_response: The message sent by the user.
    :param request_data: The request data object.
    :param session_id: The ID of the session.
    :param user_id: The ID of the user.
    :param responses: A list of response objects.
    :return: The result of the task.
    """
    mlogger.info("post_messages_data called with data == {}".format(pass_kwargs))
    with get_pg_connector() as pg:
        new_messages = []
        if not pass_kwargs.get("reply_to"):
            in_message_id = str(gryd.hp.make_uuid3(hp.time(),pass_kwargs.get("session_id"),pass_kwargs.get("user_id"),pass_kwargs.get("customer_response")))

        incoming_message = {
            "reply_to":"",
            "message_id":pass_kwargs.get("reply_to") or in_message_id,
            "message":pass_kwargs.get("customer_response") or pass_kwargs.get("request_data",{}).get("customer_response",""),
            "session_id":pass_kwargs.get("session_id"),
            "created" : pass_kwargs.get("first_message_time") or hp.time(),
            "updated" : pass_kwargs.get("first_message_time") or hp.time(),
            "index" : 0
            }
        # mlogger.info("incoming_message {}".format(incoming_message))
        first_message = pg.update("message","message_id",pass_kwargs.get("reply_to"),incoming_message)
        new_messages.append(first_message)
        mlogger.info("first_message {}".format(first_message))
        for message in pass_kwargs.get("responses"):
            message_id = str(gryd.hp.make_uuid3(hp.time(),pass_kwargs.get("session_id"),message.get("intent"),message.get("placeholder")))
            out_message = {
                    "reply_to":pass_kwargs.get("reply_to"),
                    "message_id":message_id,
                    "message":message.get("placeholder"),
                    "session_id":pass_kwargs.get("session_id"),
                    "intent" : message.get("intent","unknown_intent"),
                    "index" : message.get("index",0),
                    "created" : message.get("created",hp.time()),
                    "updated" : message.get("updated",hp.time())
                }
            # mlogger.info(f"out_message --{out_message}")
            respper = pg.update("message","message_id",message_id,out_message)
            if not respper:
                mlogger.info("message not saved for message_id {}".format(message_id))
                continue
            new_messages.append(respper)
        mlogger.info("session_id in post_messages_data {}".format(pass_kwargs.get("session_id")))
        session_data_cache = setup_session_data_cache(session_id=pass_kwargs.get("session_id"))
        session_data_cache_data = pass_kwargs.get("session_data_cache",session_data_cache).get("data",{})
        current_cache_messages = session_data_cache_data.get("messages",[])
        current_cache_messages.extend(new_messages)
        session_data_cache_data["messages"] = current_cache_messages
        pg.update("session_data_cache","session_id",pass_kwargs.get("session_id"),{"data":session_data_cache_data})
        

        
def setup_session_data_cache(*args, **kwargs):
    logger = kwargs.get("logger",mlogger)
    logger.info("setup_session_cache_data called with data \n {} \n\n ---------------".format(kwargs))
    cache_data = kwargs.get("session_data_cache",{})
    if cache_data:
        return cache_data
    session_id = kwargs.get("session_id")

    with get_pg_connector() as pg:
        session_data = kwargs.get("session_data")
        if not session_data:
            session_data = pg.get("session","session_id",session_id)
    with get_pg_connector() as pg:
        session_data_cache = pg.get("session_data_cache","session_id",session_id) or {}
        mlogger.info("session_data_cache fetched == {}".format(session_data)) 
        if not session_data_cache or not session_data_cache.get("data",{}).get("campaign_data") or not session_data_cache.get("data",{}).get("user_data"):
            campaign_model_name = session_data.get("campaign_model")
            lead_model_name = session_data.get("lead_model")
            mlogger.info("campaign_model_name == {}, lead_model_name == {}".format(campaign_model_name,lead_model_name))
            mlogger.info("campaign_id == {}".format(session_data.get("campaign_id")))
            campaign_data = pg.get(campaign_model_name,"campaign_id",session_data.get("campaign_id")) or {}
            mlogger.info("campaign_data == {}".format(campaign_data))
            dealership_id = campaign_data.get("dealership_id")
            dealership_data = pg.get("dealership","dealership_id",dealership_id)
            lead_data = pg.get(session_data.get("lead_model"),"{}_id".format(lead_model_name),session_data.get("lead_id")) or {}
            current_data = session_data_cache.get("data",{})
            current_data["campaign_data"] = campaign_data
            current_data["user_data"] = lead_data
            current_data["dealership_data"] = dealership_data
            postable = {"session_id":session_id,"data":current_data}
            mlogger.info("postable == {}".format(postable))
            session_data_cache = pg.update("session_data_cache","session_id",session_id,postable)
            
    return session_data_cache or {}


@gryd.is_a_task()
def get_primary_prompt(*args, **kwargs):
    '''
    For voice_call channel, get campaign, person, lead data from kwargs and use that info to generate the primary prompt instead of using session etc.
    '''
    logger = kwargs.get("logger",mlogger)
    logger.info("get_primary_prompt called")
    kwargs["session_data_cache"] = setup_session_data_cache(*args, **kwargs)
    if not kwargs.get("channel"):
        kwargs["channel"] = "voice_phone"
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
    mlogger.info("response == ##{}##".format(response))
    if response == "PHONE":

        phone_job = {
                    "_job":{
                        "task":"nada_pre_sales",
                        "service" : AUTOCRM_CAMPAIGN_SERVICE_NAME ,
                        "kwargs" : {
                            "channel" : "voice_phone",
                            "session_id" : kwargs.get("session_id")
                        } 
                    }
                }
        yield phone_job
        mlogger.info("phone_job == {}".format(phone_job))
        return
    elif "WHATSAPP" in response:
        whatsapp_job = {
                    "_job":{
                        "task":"nada_pre_sales",
                        "service" : AUTOCRM_CAMPAIGN_SERVICE_NAME ,
                        "kwargs" : {
                            "channel" : "whatsapp_chat",
                            "session_id" : kwargs.get("session_id")
                        } 
                    }
                }
        mlogger.info("whatsapp_job == {}".format(whatsapp_job))
        yield whatsapp_job
        return
    else:
        yield {"intent" : "llm_response","placeholder":response}



      
    

    

@gryd.is_a_task()
def run_orchestrator(*args, **kwargs):
    logger = kwargs.get("logger",mlogger)
    logger.info("run_orchestrator called")
    reply_to = str(hp.time())
    


    yield {"placeholder":"agent 1 response","intent" : "agent_one","reply_to":reply_to, "message_id" : str(hp.time()),"is_last":False,"index" : 1}
    yield {"placeholder":"agent 2 response","intent" : "agent_two","reply_to":reply_to, "message_id" : str(hp.time()),"is_last":False,"index" : 2}
    yield {"placeholder":"agent 3 response","intent" : "agent_three","reply_to":reply_to, "message_id" : str(hp.time()),"is_last":True,"index" : 3}
    return

def prune_response( response, *args, **kargs):
    logger = kargs.get("logger",mlogger)
    logger.info("prune_response called")
    request_data = kargs.get("request_data")
    if request_data.get("channel") in ["whatsapp_chat"]:
        response_task_data = request_data.get("temporary_data",{}).get("channel_response_task",{})
        ret =  {"temporary_data": response_task_data.get("kwargs",{})}
        
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
    response["created"] = hp.time()
    response["updated"] = response["created"]
    response["reply_to"] = kargs.get("reply_to")
    kargs["responses"].append(response)
    yield response
    return






