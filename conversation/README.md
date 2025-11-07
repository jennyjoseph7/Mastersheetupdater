TODO --
create a session_data_cache - iadd type setup to input all data about user into this. To be deleted at the end of all sessions
prompt template model(has template for primary prompt or other types of prompts that will have tags for diff scenarios and also have variables mentioned)




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



