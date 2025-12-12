TODO --
create a session_data_cache - iadd type setup to input all data about user into this. To be deleted at the end of all sessions
prompt template model(has template for primary prompt or other types of prompts that will have tags for diff scenarios and also have variables mentioned)

create tasks:-
converse
session_close
add_to_session_cache
get_primary_prompt
run_primary_prompt
run_orchestrator
response_pruning
filler_task


request comes in 
I get session id, person_id, any temp data, any custom info (TBD)
Get session data, get session_cache_data, get campaign_data or any other relevent data needed for my process and also dump that into the session_cache, all guidlines if specific to oem/dealership etc

Run the Primary Prompt, this will be selected based on caampaign id/ tags based on other settings or a "default inbound primary prompt".
All variables in this prompt will be fed in using the sessioncache data available with fallback values if not available.
    - session cache data
    - session info
    - history
    - brand/oem/dealership etc guidelines
    - campaign info
    - previous messages agents output prompt snippet

check if response generated, then send to channels.

if filler generated - run orchestrator

ORCH
orchestrator needs 
    - all services available and all agents present in them. 
    - customer_response
    - session_cache
    - brand/oem/dealership etc guidelines
    - message history
    - campaign details
    - scope of conversation
    - previous messages agents output prompt snippet

orchestrator will output 
1) plan(sequence of agents to be called to get the answers)
2) filler to send to user(some kind of rephrase of what the user said/ wants along with what its planning to do)
3) data to be passed to the agents based on the agents expected_input optional input
4) it will spawn tasks based on the sequence detected.
    a) if pure single sequence it will call it without doing sqs or anything
    b) if branching is there, then it will do yield results. if dependencies are there, then multi level yieldresults.

Every agent returning placeholder in async -
    first response sent as is
    second reponse onwards check if anything extra, rephrase if needed and then send to the channels


Important Notes
- When creating agents, access customer info from session_cache
- when updating user data, patch to the session_cache object
- DO NOT POST ENTIRE OBJECT TO session_cache. only attr you want to change
- if agent B depends_on Agent A, then make sure Agent B required_input fields are exactly the same as output data from agentA,
- when expected inputs are lets say var a,b,c and only a is recieved, output of agent should be {"placeholder":"asking user for the missing data","next_prompt_snippet" : "a prompt snippet to plug into primary prompt that can detect if user info expected was give. ", "data" : {key values to be used elsewhere}}
- Use AGENT BASE CLASS functions to yield or return from your agent. ---- yield return_data/return_converse_response/return_thinking_response/return_error_response
- ADD agent_type in your agent decorator--- conversation/default





CONVERSE TASK - 
inputs - 
{
        "intent" : "",
        "customer_response" : "",
        "session_id":""
        "channel":"whatsapp_chat",
        "temporary_data": {"channel_response_task":{"service":"channel_service_name_for_task","task":"send_reply_task_name","kwargs":{}}},
        "response_length":"full/sentence/paragraph/agent",
        "communication_data":{
            "whatsapp_message_id":"",
            "user_sent_time":"airtel webhook timestamp",
            "webhook_received_time":"comm webhook received time"
        }
    }

mandatory - provide session_id and channel(options found in session model), 
if channel is whatsapp, provide send_reply task details. a task name and service name which i will call to send back the responses.
rest send as and when required.

task flow.
    get or post session_data_cache
    get dealership data.
    get campaign data
    get lead data
    add additional data in cache
    run filler task
    run primary prompt
        - set kill status for filler task
        - kill filler task
        - start sending filler from here.
        - send primary prompt response if available
        - if primary prompt resp not available - run orchestrator
        - yield fillers while waiting for agents to respond - intermediate_timeout = seconds number. it returns NONE NONE....
        - yield first response from agent to fe
        - second yield onwards call response prude task. 


GET PRIMARY PROMPT/RUN PRIMARY PROMPT
inputs - 
    session_id
    session_data_cache data 
    customer_response

task flow - 
    if session_data_cache not available, get object from model
    frm cache get campaing id etc.
    fetch correct prompt template from model
    fill all variable data using cache. if data missing check if section optional else failure
    yield prompt/run prompt
    if run prompt, yield response
    if response is filler,
    start orchestrator task.



RUN ORCHESTRATOR - 
inputs - 
    session_id
    session_data_cache data 
    customer_response

task flow
    



Second service name in config.AUTOCRM_CONVERSATION_POST_PROCESS_SERVICE_NAME

task to call after session ends - post_session_process(session_id=<your session id>)

Post session process is a task that runs after a conversation is closed.
It takes in the session_id and session_data and updates the lead data and session data accordingly.
It also calls the sentiment agent to get the sentiment analysis of the conversation.
If the lead disposition is converted, it also gets the appointment date and time, and updates the lead data with it.
Finally, it updates the session data with the sentiment score and emotion analysis.
:param session_id: The unique identifier of the session.