from gryd_worker import gryd
from gryd_worker.gryd_routes import gryd_result
from utils import GRYD_SERVICE, GRYD_CONFIG, get_logger, upload_file
from typing import Union, Dict, Any, Generator
import json
import traceback, os
import AgentOrchestrator  
import inspect
logger = get_logger(__name__)

gryd.SERVICE = GRYD_SERVICE
gryd.set_queue_manager(config = GRYD_CONFIG)

def environment(environment: str = "-local"):
    if not environment.startswith("-"):
        environment = f"-{environment}"
    gryd.ENVIRONMENT = environment
    message = {"message": f"Environment set to '{environment}'"}
    logger.info(message)
    return message

GRYD_ENVIRONMENT = os.getenv("ENVIRONMENT", "-local")
environment(environment = GRYD_ENVIRONMENT)

def get_function_name():
    # return inspect.currentframe().f_back.f_code.co_name
    return inspect.currentframe().f_code.co_name

@gryd.is_a_task()
def autobot_agents_trigger(*args, **kwargs):
    source: Union[dict, str] = kwargs.get("source", None)
    if source is None:
        raise ValueError("'source' is required. Either pass a valid dict or a valid URL or filepath for JSON.")

    execution_mode = kwargs.get("execution_mode", "async").lower()

    aem_integration_agent_results = aem_integration_agent.execute(*args, **kwargs)
    kwargs["aem_integration_agent_results"] = aem_integration_agent_results
    kwargs["source"] = aem_integration_agent_results.get("updated_source")

    awaited_tasks = [
        {"task": "propensity_agent", "service": GRYD_SERVICE, "kwargs": kwargs},
        {"task": "competitor_analysis_agent", "service": GRYD_SERVICE, "kwargs": kwargs},
        {"task": "prioritization_agent", "service": GRYD_SERVICE, "kwargs": kwargs},
        {"task": "sentiment_analysis_agent", "service": GRYD_SERVICE, "kwargs": kwargs},
    ]

    def result_handler(awaited_tasks: list[dict], execution_mode: str):
        task_results = []
        if execution_mode == "async":
            logger.info("🚀 Running tasks asynchronously...")
            jobs = gryd.yield_results(awaited_tasks, timeout=120)
            for job in jobs:
                task_name, status, result_data = job[1], job[3], job[4]
                if status == "result":
                    logger.info(f"✅ Task '{task_name}' completed with result: {json.dumps(result_data, indent=4, default=str)}")
                    task_results.append(result_data)
                else:
                    logger.warning(f"⚠️ Task '{task_name}' failed or still pending. Status: {status}")
        else:
            logger.info("Running tasks synchronously...")
            jobs = gryd.await_results(awaited_tasks, timeout=120)
            for job in jobs:
                task_results.append(job)
        return task_results

    task_results: list = result_handler(awaited_tasks, execution_mode=execution_mode)

    task_key_map = {
        "propensity_agent": "propensity_agent_results",
        "competitor_analysis_agent": "competitor_analysis_agent_results",
        "prioritization_agent": "prioritization_agent_results",
        "sentiment_analysis_agent": "sentiment_analysis_agent_results",
    }

    for task_result in task_results:
        task_name = task_result.get("task")
        if task_name in task_key_map:
            task_result_key = task_key_map[task_name]
            kwargs[task_result_key] = task_result

    next_agents = {
        "personalization_agent_results": personalization_agent,
        "communication_agent_results": communication_agent,
    }

    for result_key, agent in next_agents.items():
        result = agent.execute(*args, **kwargs)
        kwargs[result_key] = result
        task_results.append(result)
    task_results.insert(0, aem_integration_agent_results)
    logger.info(f"✅✅ Final Task results: {json.dumps(task_results, indent=4, default=str)}")
    return task_results


@gryd.is_a_task()
def autobot_agents_trigger_generator(*args, **kwargs) -> Generator:
    source: Union[Dict, str] = kwargs.get("source", None)
    if source is None:
        raise ValueError("'source' is required. Either pass a valid dict or a valid URL or filepath for JSON.")
    execution_mode = kwargs.get("execution_mode", "async").lower()
    aem_integration_agent_results = aem_integration_agent.execute(*args, **kwargs)
    kwargs['aem_integration_agent_results'] = aem_integration_agent_results
    kwargs['source'] = aem_integration_agent_results.get("updated_source")
    yield aem_integration_agent_results
    awaited_tasks = [
        {
            "task": "propensity_agent",
            "service": GRYD_SERVICE,
            "kwargs": kwargs
        },
        {
            "task": "competitor_analysis_agent",
            "service": GRYD_SERVICE,
            "kwargs": kwargs
        },
        {
            "task": "prioritization_agent",
            "service": GRYD_SERVICE,
            "kwargs": kwargs
        }
    ]
    if execution_mode == "async":
        logger.info("🚀 Running tasks asynchronously...")
        jobs = gryd.yield_results(awaited_tasks, timeout=120)
        for job in jobs:
            task_name, status, result_data = job[1], job[3], job[4]
            if status == "result":
                task_name = result_data.get("task")
                logger.info(f"✅✅ Task '{task_name}' completed.")
                kwargs_key = f"{task_name}_results"
                kwargs[kwargs_key] = result_data
                yield result_data
            else:
                logger.warning(f"⚠️ Task '{task_name}' failed or pending.")
    else:
        logger.info("Running tasks synchronously...")
        jobs = gryd.await_results(awaited_tasks, timeout=120)
        for job in jobs:
            task_name = job.get("task")
            kwargs_key = f"{task_name}_results"
            kwargs[kwargs_key] = job
            yield job
    
    next_agents = {
        "sentiment_analysis_agent_results": sentiment_analysis_agent,
        "personalization_agent_results": personalization_agent,
        "communication_agent_results": communication_agent,
    }

    for key, agent in next_agents.items():
        result = agent.execute(*args, **kwargs)
        kwargs[key] = result
        yield result


# ---------- Global Agents Start ----------
        
@AgentOrchestrator.register_agent(name=None, depends_on=[], expected_input={"source": "dict"})
@gryd.is_a_task()
def aem_integration_agent(*args, **kwargs):
    """
    Enriches customer data with AEM data. AEM tracks customer interactions on the website (pages viewed, actions taken, preferences) and, with Adobe Analytics/AEP, builds a real-time profile to enable personalization and insights.
    """
    function_name = inspect.currentframe().f_code.co_name #get_function_name()
    try:
        from agents.aem_integration_agent import AEMIntegrationAgent
        source = kwargs['source']
        model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
        aem_agent = AEMIntegrationAgent(source = source, model_identifier=model_identifier)
        updated_source = aem_agent.run()
        return {"task": function_name, "updated_source": updated_source}
    except Exception as e:
        logger.error(f"AEM Integration Agent Error: \n\n")
        traceback.print_exc()
        return {"task": function_name, "error": str(e).strip()}

@AgentOrchestrator.register_agent(name=None, depends_on=['aem_integration_agent'], expected_input={"source": "dict"})
@gryd.is_a_task()
def dealer_locator_agent(*args, **kwargs):
    """
    Locates the nearest dealer to the customer based on their location.
    """
    function_name = inspect.currentframe().f_code.co_name #get_function_name()
    try:
        from agents.dealer_locator_agent import DealerLocatorAgent
        source = kwargs["source"]
        model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
        location_agent = DealerLocatorAgent(source = source, model_identifier = model_identifier)
        location = location_agent.run()
        filtered_results = {
            "task": function_name,
            "location": location
        }
        return filtered_results
    except Exception as e:
        traceback.print_exc()
        error_message = {
            "task": function_name,
            "error": f"Failed to locate nearest dealer : {str(e)}"
        }
        return error_message
    
@gryd.is_a_task()    
@AgentOrchestrator.register_agent(name=None, depends_on=["aem_integration_agent"], expected_input={"source": "dict"})
def propensity_agent(*args, **kwargs):
    """
    This agent focuses on identifying what the customer really cares about in a car. 
    It looks at their interaction patterns. for example: - Which product pages they've visited the most. - Whether they've spent more time reading about performance specs or checking out interior design. - If they clicked comparison charts, explored specific trims, or viewed certain features multiple times. From all these behavioral signals, the agent calculates a propensity score — essentially a number that tells us how strongly the customer is leaning towards certain feature sets, such as performance & handling, interior comfort & technology, or brand image & aesthetics
    """
    function_name = inspect.currentframe().f_code.co_name #get_function_name()
    try:
        from agents.propensity_agent import PropensityAgent
        source = kwargs["source"]
        model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
        propensity_agent = PropensityAgent(source = source, model_identifier=model_identifier)
        agent_response : dict = propensity_agent.run()
        scores = agent_response.get("scores")
        img_bytes = agent_response.get("img_bytes")
        reasoning = agent_response.get("reasoning")
        fig_json = agent_response.get("fig_json")
        response = upload_file(img_bytes, {"autobot-agent": True})
        propensity_chart_url = response["cdn_url"] if isinstance(response, dict) else response
        filtered_results = {
            "task": function_name,
            "scores": scores,
            "propensity_chart_url": propensity_chart_url,
            "reasoning": reasoning,
            "propensity_chart_json": fig_json
        }
        logger.info(f"Propensity Agent Results: {json.dumps(filtered_results, indent = 4, default = str)}")
        return filtered_results
    except Exception as e:
        logger.error(f"Propensity Agent Error: \n\n")
        traceback.print_exc()
        return {"task": function_name, "error": str(e).strip()}

@gryd.is_a_task()
@AgentOrchestrator.register_agent(
    name=None, 
    depends_on=[
        "aem_integration_agent", "propensity_agent", 
        "sentiment_analysis_agent", "prioritization_agent", 
        "competitor_analysis_agent"],
    expected_input={
        "source": "dict",
        "propensity_agent_results": "dict",
        "sentiment_analysis_agent_results": "dict",
        "prioritization_agent_results": "dict",
        "competitor_analysis_agent_results": "dict"
    })
def personalization_agent(*args, **kwargs):
    """
    Personalization agent generates a personalized email to the customer.
    """
    function_name = inspect.currentframe().f_code.co_name #get_function_name()
    try:
        from agents.personalization_agent import PersonalizationAgent
        source = kwargs.get("source", "")
        model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")

        # Propensity Agent Results
        propensity_agent_results = kwargs.get("propensity_agent_results") or {}  
        propensity_score = propensity_agent_results.get("scores","")
        
        #sentiment analysis agent results:
        
        sentiment_results = kwargs.get("sentiment_analysis_agent_results") or {} 
        sentiment_score = sentiment_results.get("sentiment_score","")
        emotions = sentiment_results.get("emotions","")
        sentiment_justification = sentiment_results.get("justification","")
        
        #prioritization agent results:
        prioritization_results = kwargs.get("prioritization_agent_results") or {} 
        
        # Competitor Analysis Agent Results
        competitor_analysis_agent_results = kwargs.get("competitor_analysis_agent_results") or {}
        comparison_cars_json = competitor_analysis_agent_results.get("compared_cars_data", "")
        comparison_json = competitor_analysis_agent_results.get("comparisons", "")
        common_points_json = competitor_analysis_agent_results.get("common_points", "")
        key_differences_json = competitor_analysis_agent_results.get("key_differences", "")
        user_choice_justification_json = competitor_analysis_agent_results.get("user_choice_justification", "")

        combined_input = {
            "source" : source,
            "propensity_score" : propensity_score,
            "comparison" : comparison_json,
            "comparison_cars" : comparison_cars_json,
            "common_points" : common_points_json,
            "key_differences" : key_differences_json,
            "user_choice_justification" : user_choice_justification_json,
            "user_sentiments" : sentiment_results,
            "sentiment_score" : sentiment_score,
            "emotions" : emotions,
            "sentiment_justification" : sentiment_justification,
            "prioritization_data" : prioritization_results
            
            
        }
        agent = PersonalizationAgent(source=combined_input, model_identifier=model_identifier)
        personalization_agent_results = agent.run()
        filtered_results = {
            "task": function_name,
            "personalization_agent_response": personalization_agent_results.get("response"),
            "reasoning": personalization_agent_results.get("ai-thinking")
        }
        return filtered_results
    except Exception as e:
        logger.error(f"Personalization Agent Error: \n\n")
        traceback.print_exc()
        return {"task": function_name, "error": str(e).strip()}

@gryd.is_a_task()
@AgentOrchestrator.register_agent(name=None, depends_on=["aem_integration_agent"], expected_input={"source": "dict"})
def competitor_analysis_agent(*args, **kwargs):
    """
    This agent ensures we understand the competitive landscape from the customer's perspective. 
    It identifies rival cars in the same category or price range and pulls in their specifications, pricing, performance numbers, and standout features.
    """
    function_name = inspect.currentframe().f_code.co_name #get_function_name()
    try:
        from agents.competitor_analysis_agent.main import CompetitorAnalysis
        source = kwargs["source"]
        model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
        top_n = kwargs.get("top_n", 3)
        competitor_agent = CompetitorAnalysis(source = source, model_identifier=model_identifier,top_n=top_n)
        analysis = competitor_agent.get_analysis()
        filtered_results = {
            "task": function_name,
            "top_models": top_n,
            "compared_cars_data": analysis.get("compared_cars_data",""),
            "comparisons": analysis.get("comparisons",""),
            "common_points": analysis.get("common_points",""),
            "key_differences": analysis.get("key_differences",""),
            "user_choice_justification": analysis.get("user_choice_justification","")
        }
        return filtered_results
    except Exception as e:
        logger.error(f"Competitor Analysis Agent Error: \n\n")
        traceback.print_exc()
        return {"task": function_name, "error": str(e).strip()}

@gryd.is_a_task()
@AgentOrchestrator.register_agent(name=None, depends_on=["aem_integration_agent"], expected_input={"source": "dict"})
def prioritization_agent(*args, **kwargs):
    """
    Suggests lead/deal prioritization. This agent decides how important and urgent this lead is for us. 
    If the customer has interacted multiple times, they're likely a warm lead — someone worth immediate follow-up. Basically a lead scoring agent.
    """
    function_name = inspect.currentframe().f_code.co_name #get_function_name()
    try:
        from agents.lead_prioritization_agent import LeadPrioritizationAgent
        source = kwargs["source"]
        model_identifier = kwargs.get("model_identifier","azure-gpt-4o")
        priority_agent = LeadPrioritizationAgent(source = source, model_identifier=model_identifier)
        lead_analysis = priority_agent.complete_analysis()
        filtered_results = {
            "task" : function_name,
            **lead_analysis
        }
        return filtered_results
    except Exception as e:
        logger.error(f"Prioritization Agent Error: \n\n")
        traceback.print_exc()
        return {"task": function_name, "error": str(e).strip()}

@gryd.is_a_task()
@AgentOrchestrator.register_agent(
    name=None, depends_on=["aem_integration_agent", "prioritization_agent", "personalization_agent"],
    expected_input={"source": "dict", "prioritization_agent_results": "dict", "personalization_agent_results": "dict"})
def communication_agent(*args, **kwargs):
    """
    This agent sends final communication via email/WhatsApp to the customer.
    """
    function_name = inspect.currentframe().f_code.co_name #get_function_name()
    from agents.communication_agent import CommunicationAgent

    logger.info(f"Running communication agent... \n {json.dumps(kwargs, indent=4)}")
    source = kwargs["source"]
    model_identifier = kwargs.get("model_identifier","azure-gpt-4o")
    prioritization_results = kwargs.get("prioritization_agent_results") or {} 
    recommended_actions = prioritization_results.get("recommended_actions", [])
    if "personalized_email" not in recommended_actions:
        return {
            "task": function_name,
            "email_draft": None,
            "status": "failed",
            "error": "Email not sent as it's not a recommended action",
            "communication_agent_result": "Email not sent as it's not a recommended action"
        }
    personalization_agent_results = kwargs.get("personalization_agent_results") or {}  
    user_message = personalization_agent_results.get("personalization_agent_response")
    if not user_message:
        logger.warning("No personalization message found. Cannot proceed with email drafting.")
        return {
            "task": function_name,
            "email_draft": None,
            "status": "failed",
            "error": "Missing personalization_agent_response",
            "communication_agent_result": "Email not sent - no personalization message available"
        }
    try:
        communication_agent = CommunicationAgent(source=source, model_identifier=model_identifier)
        
        # Draft and send email
        communication_info = communication_agent.draft_and_send_email(
            cc="",
            user_message=user_message
        )
        
        filtered_results = {
            "task": function_name,
            "email_draft": communication_info.get("draft"),
            "communication_agent_result": communication_info.get("send_response"),
            "status": "success"
        }
        
        logger.info(f"Communication Agent Results: {json.dumps(filtered_results, indent=4, default=str)}")
        return filtered_results
        
    except Exception as e:
        logger.error(f"Communication Agent Error: {str(e)}")
        traceback.print_exc()
        return {
            "task": function_name,
            "email_draft": None,
            "communication_agent_result": f"Email sending failed: {str(e)}",
            "status": "error",
            "error": str(e)
        }

@gryd.is_a_task()
@AgentOrchestrator.register_agent(name=None, depends_on=["aem_integration_agent"], expected_input={"source": "either string or dict"})
def sentiment_analysis_agent(*args, **kwargs):
    """
    This agent analyzes customer sentiment and emotion patterns based on their interactions with the website or system data.
    """
    function_name = inspect.currentframe().f_code.co_name #get_function_name()
    try:
        from agents.sentiment_agent import SentimentAnalysisAgent
        source = kwargs["source"]
        model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
        sentiment_agent = SentimentAnalysisAgent(source=source, model_identifier=model_identifier)
        analysis = sentiment_agent.run()
        filtered_results = {
            "task": function_name,
            "user_input": analysis.get("user_input", ""),
            "language": analysis.get("language", ""),
            "sentiment_score": analysis.get("sentiment_score", 0.0),
            "emotions": analysis.get("emotions", []),
            "justification": analysis.get("justification", ""),
            "thinking": analysis.get("thinking", ""),
            "conversation_analytics": analysis.get("conversation_analytics", {})
        }

        return filtered_results

    except Exception as e:
        logger.error(f"Sentiment Analysis Agent Error: {e}")
        traceback.print_exc()
        return {
            "task": function_name,
            "error": str(e).strip()
        }

@gryd.is_a_task()
@AgentOrchestrator.register_agent(name=None, depends_on=[])
def get_current_datetime(*args, **kwargs):
    """
    This agent returns the current date and time.
    """
    import datetime
    func_name = inspect.currentframe().f_code.co_name #get_function_name()
    current_datetime = datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")
    return {
        "task": func_name,
        "current_datetime": current_datetime
    }

@gryd.is_a_task()
@AgentOrchestrator.register_agent(name=None, depends_on=[], expected_input={"user_query": "str"})
def get_greeting(*args, **kwargs):
    """
    This agent returns a random greeting.
    """
    import random
    query = kwargs.get("user_query")
    func_name = inspect.currentframe().f_code.co_name #get_function_name()
    random_greetings = [
        "Hello", "Hi", "Hey", "Howdy", "Hola", "Hello there", "Hi there", "Hey there", "Howdy there", "Hola there",
    ]
    return {
        "task": func_name,
        "greeting": random.choice(random_greetings)
        }


@gryd.is_a_task()
@AgentOrchestrator.register_agent(name=None, depends_on=["aem_integration_agent"], expected_input={"source": "dict"})
def call_analytics_agent(*args, **kwargs):
    """
    This agent calls an analytics agent to process customer data. 
    """
    function_name = inspect.currentframe().f_code.co_name #get_function_name()
    try:
        from agents.call_analytics_agent import CallQualityAnalysisAgent
        source = kwargs["source"]
        model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
        analytics_agent = CallQualityAnalysisAgent(source=source, model_identifier=model_identifier)
        output = analytics_agent.run()
        return {
            "task": function_name, **output
        }
    except Exception as e:
        logger.error(f"Analytics Agent Error: {e}")
        traceback.print_exc()
        return {
            "task": function_name,
            "error": str(e).strip()
        }

# ------------------ Global Agents Finish ------------------

from dataclasses import asdict
a = AgentOrchestrator.AgentOrchestrator()
agents_list = []
for agent in a.AGENT_REGISTRY:
    agents_list.append({
        "name": agent.name,
        "description": agent.description,
        "depends_on": agent.depends_on,
        "expected_input": agent.expected_input,
        "expected_output": agent.expected_output
    })
# agent_dicts = [asdict(agent) for agent in a.AGENT_REGISTRY]
print(json.dumps(agents_list, indent=4))

# for agent in a.AGENT_REGISTRY:
#     logger.info(f"Agent: {agent.name}, Description: {agent.description}, Depends on: {agent.depends_on}")
# logger.info(f"Local Agents: {json.dumps(a.AGENT_REGISTRY, indent=4, default=str)}")
# logger.info(f"Global Agents: {json.dumps(AgentOrchestrator.GLOBAL_AGENT_REGISTRY, indent=4, default=str)}")
@gryd.is_a_task()
def query_orchestrator(*args, **kwargs):
    from AgentOrchestrator import AgentOrchestrator
    user_query = kwargs['user_query']
    source = kwargs["source"]
    model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
    # model_identifier = "groq-llama-3.3-70b"
    a = AgentOrchestrator(model_identifier=model_identifier)
    response = a.orchestrator(user_query, source=source)
    for r in response:
        yield r