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


def get_gryd_docs():
    docs = gryd.LIST_OF_DOCS
    return docs 


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
        {"task": "propensity_agent", "service": GRYD_SERVICE, "kwargs": kwargs},
        {"task": "competitor_analysis_agent", "service": GRYD_SERVICE, "kwargs": kwargs},
        {"task": "prioritization_agent", "service": GRYD_SERVICE, "kwargs": kwargs},
        {"task": "sentiment_analysis_agent", "service": GRYD_SERVICE, "kwargs": kwargs},
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
    This agent locates the nearest dealer to the customer based on their location. 
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
        
        # Sentiment analysis agent results:
        
        sentiment_results = kwargs.get("sentiment_analysis_agent_results") or {} 
        sentiment_score = sentiment_results.get("sentiment_score","")
        emotions = sentiment_results.get("emotions","")
        sentiment_justification = sentiment_results.get("justification","")
        
        # Prioritization agent results:
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
def recommendation_agent_v1(*args, **kwargs):
    """
    This agent recommends vehicles to the customer based on their preferences and previous interactions.
    The agent takes in a dictionary of the customer's preferences and previous interactions and returns a list of recommended vehicles.
"""
    function_name = inspect.currentframe().f_code.co_name #get_function_name()
    try:
        from agents.recommendation_agent import RecommendationAgent
        source = kwargs["source"]
        model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
        max_number = kwargs.get("Max number")g
        maintainer_agent = RecommendationAgent(model_identifier=model_identifier)
        recommended_data = maintainer_agent.main(data=source)
        filtered_results = {
            "task": function_name,
            "Max number": max_number,
            "next_offset": recommended_data.get("next_offset",0),
            "top_vehicles": recommended_data.get("top_vehicles",""),
            "total_vehicles_found": recommended_data.get("total_vehicles_found",""),
            "match_refining_questions": recommended_data.get("match_refining_questions",""),

        }
        return filtered_results
    except Exception as e:
        logger.error(f"Recommendation Agent Error: \n\n")
        traceback.print_exc()
        return {"task": function_name, "error": str(e).strip()}

<<<<<<< HEAD





=======
>>>>>>> 04bb0015d723ed95f0cbab28ba31ec922db67795
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
        "Hello", "Hi", "Hey", 
        "Howdy", "Hola", "Hello there", 
        "Hi there", "Hey there", 
        "Howdy there", "Hola there",
    ]
    return {
        "task": func_name,
        "greeting": random.choice(random_greetings)
        }

@gryd.is_a_task()
@AgentOrchestrator.register_agent(name=None, depends_on=[], expected_input={"user_query": "str"})
def general_query_agent(*args, **kwargs):
    """
    This agent will handle general purpose queries. The kind of queries that can be handled by this agent are not limited to anything specific task.
    """
    function_name = inspect.currentframe().f_code.co_name
    try:
        from ai_service import ai_service_app
        llm_function = lambda x : ai_service_app.get_llm_response(messages=x, model_identifier="azure-gpt-4o")
        query = kwargs.get("user_query")
        messages = [
            {
                "role": "system",
                "content" : "You are a general purpose AI assistant. You will answer any general purpose question."
            },
            {
                "role": "user",
                "content": query
            }
        ]
        response = llm_function(x = messages)
        return {
            "task": function_name,
            "response": response
        }
    except Exception as e:
        logger.error(f"General Query Agent Error: {e}")
        traceback.print_exc()
        return {
            "task": function_name,
            "error": str(e).strip()
        }

@gryd.is_a_task()
@AgentOrchestrator.register_agent(depends_on=[], expected_input={"source": "dict"}) # , capability_function = "gryd_task_name"
def weather_agent(*args, **kwargs):
    """
    This agent fetches the current weather and forecast for a given city.
    """
    import asyncio
    import python_weather

    func_name = inspect.currentframe().f_code.co_name
    source = kwargs.get("source")
    
    city = None
    for key in ["city", "location", "dealer_city", "dealer_location"]:
        if key in source:
            city = source[key]
            break

    if not city:
        return {
            "task": func_name, 
            "error": "City not found in source"
            }

    async def fetch_weather():
        async with python_weather.Client(unit=python_weather.METRIC) as client:
            weather = await client.get(city)
            forecast = []
            for daily in weather:
                # logger.info(f"daily: {daily}")
                daily_info = {
                    "date": str(daily.date),
                    "temperature": daily.temperature,
                    "hourly": []
                }
                for hourly in daily:
                    daily_info["hourly"].append({
                        "time": str(hourly.time),
                        "temperature": hourly.temperature
                    })
                forecast.append(daily_info)

            return {
                "task": func_name,
                "city": city,
                "temperature": weather.temperature,
                "unit": "°C",
                "forecast": forecast
            }
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    result = asyncio.run(fetch_weather())
    return result


STATE_ALIASES_MAP = {
    "Andhra Pradesh": ["andhra", "ap", "andhrapradesh", "andhra pradesh"],
    "Assam": ["asm", "assam"],
    "Bihar": ["br", "bihar"],
    "Chandigarh": ["ch", "chd", "chandigarh"],
    "Chhattisgarh": ["cg", "chhattis", "chattisgarh"],
    "Delhi": ["dl", "delhi", "new delhi"],
    "Goa": ["ga", "goa"],
    "Gujarat": ["gj", "guj", "gujrath", "gujarat"],
    "Haryana": ["hr", "haryana", "harayna"],
    "Himachal Pradesh": ["hp", "himachal", "himachal pradesh"],
    "Jammu and Kashmir": ["jk", "j&k", "jammu", "kashmir", "jammu and kashmir"],
    "Jharkhand": ["jh", "jharkhand", "jharkand"],
    "Karnataka": ["ka", "karnataka", "karnatka"],
    "Kerala": ["kl", "keral", "kerala"],
    "Madhya Pradesh": ["mp", "madhyapradesh", "madhya pradesh"],
    "Maharashtra": ["mh", "maha", "maharastra", "maharashtr"],
    "Odisha": ["od", "orissa", "odisha"],
    "Punjab": ["pb", "punjab"],
    "Rajasthan": ["rj", "rajas", "rajsthan"],
    "Tamil Nadu": ["tn", "tamlnadu", "tamilnadu", "tamil nadu"],
    "Telangana": ["ts", "tel", "telangana"],
    "Uttar Pradesh": ["up", "uttarpradesh", "uttar pradesh"],
    "Uttarakhand": ["uk", "uttaranchal", "uttarkhand"],
    "West Bengal": ["wb", "bengal", "westbengal", "west bengal"],
}

VALID_STATES = list(STATE_ALIASES_MAP.keys())
CUSTOM_ALIASES = {}
import difflib
def normalize_state_name(state_name, learn=True):
    if not state_name or not isinstance(state_name, str):
        raise ValueError("Invalid input: 'state_name' must be a non-empty string.")
    clean = state_name.strip().lower().replace(".", "").replace(",", "")
    logger.info(f"Normalizing state name: {state_name} -> {clean}")
    if clean in CUSTOM_ALIASES:
        return CUSTOM_ALIASES[clean]
   
    for state in VALID_STATES:
        if state.lower() == clean:
            return state
        
    for state, aliases in STATE_ALIASES_MAP.items():
        if clean in [a.lower() for a in aliases]:
            return state
        
    for state in VALID_STATES:
        if clean in state.lower():
            if learn:
                CUSTOM_ALIASES[clean] = state
            return state

    all_aliases_flat = [a.lower() for aliases in STATE_ALIASES_MAP.values() for a in aliases]
    possible_matches = difflib.get_close_matches(clean, all_aliases_flat + [s.lower() for s in VALID_STATES], n=3, cutoff=0.6)
    if possible_matches:
        matched = possible_matches[0]
        for state, aliases in STATE_ALIASES_MAP.items():
            if matched in [a.lower() for a in aliases] or matched == state.lower():
                if learn:
                    CUSTOM_ALIASES[clean] = state
                return state
    raise ValueError(
        f"State '{state_name}' not recognized.\n"
        f"Available states: {', '.join(VALID_STATES)}"
    )

@gryd.is_a_task()
@AgentOrchestrator.register_agent(depends_on=[], expected_input={"source": "dict"})
def compute_on_road_price(*args, **kwargs):
    function_name = inspect.currentframe().f_code.co_name # get_function_name()
    ENGINE_TYPES = ["petrol", "diesel", "cng", "ev", "hybrid"]

    # --- Static base charges --- # 
    BASE_CHARGES = {
        "registration_charges": {"amount": 600, "unit": "INR", "is_applicable": True, "description": "RTO registration fees for new vehicle"},
        "hypothecation_charges": {"amount": 1500, "unit": "INR", "is_applicable": "if_loan", "description": "Applicable if car is purchased on loan"},
        "number_plate_charges": {"amount": 400, "unit": "INR", "is_applicable": True, "description": "HSRP number plate cost"},
        "parking_fee_charges": {"amount": {"below_4_lakh": 2000, "above_4_lakh": 4000},"unit": "INR","is_applicable": "state_specific","description": "MCD or state parking/development fees"},
        "temporary_registration_charges": {"amount": 2500,"unit": "INR","is_applicable": "if_temp_registration","description": "Temporary registration valid for up to 1 month"},
        "road_tax_charges": {"amount": "state_specific","unit": "percent","is_applicable": True,"description": "State-wise applicable road tax rate"},
        "fasttag_charges": {"amount": 600,"unit": "INR","is_applicable": True,"description": "FasTag issue cost"}
    }

    try:
        source = kwargs.get("source", {})

        state = source.get("state", None)
        ex_showroom_price = source.get("ex_showroom_price", 0)
        is_company_vehicle = source.get("is_company_vehicle", False)
        is_on_loan = source.get("is_on_loan", False)
        has_temp_registration = source.get("has_temp_registration", True)
        engine_type = source.get("engine_type", "petrol").lower()
        gst_rate = source.get("gst_rate", None)
        engine_capacity = source.get("engine_capacity", 0)

        if gst_rate is None and engine_capacity == 0:
            raise ValueError("Either 'gst_rate' or 'engine_capacity' must be provided.")

        if gst_rate is not None and engine_capacity != 0:
            raise ValueError("Both 'gst_rate' and 'engine_capacity' cannot be provided.")
        
        if gst_rate is None and engine_capacity != 0:
            if engine_type in ["petrol", "hybrid"] and engine_capacity < 1200 and ex_showroom_price < 400000:
                gst_rate = 18
            elif engine_type == "diesel" and engine_capacity < 1500 and ex_showroom_price < 400000:
                gst_rate = 18
            elif engine_type in ["petrol", "diesel"] and (engine_capacity >= 1200 or ex_showroom_price >= 400000):
                gst_rate = 40
            elif engine_type == "ev":
                gst_rate = 5
            elif engine_type == "ambulance":
                gst_rate = 18
            else:
                gst_rate = 40

        gst_amount = ex_showroom_price * (gst_rate / 100)
        ex_showroom_price = ex_showroom_price + gst_amount

        if engine_type.lower() not in ENGINE_TYPES:
            error = f"Invalid engine type: '{engine_type}'. Valid engine types are: '{ENGINE_TYPES}'"
            return {"task": function_name, "error": error}
        
        all_road_tax_data : list[dict] = json.load(open("road_tax_data.json", "r"))

        try:
            state = normalize_state_name(state)
        except ValueError as e:
            return {"error": str(e)}
        ALL_STATES = [i['state'] for i in all_road_tax_data]
        if state not in ALL_STATES:
            error = f"Invalid state: '{state}'. Valid states are: '{ALL_STATES}'"
            return {"task": function_name, "error": error}

        road_tax_data = None
        for data in all_road_tax_data:
            if data['state'] == state:
                road_tax_data = data
                break

        if not road_tax_data:
            error = f"Road tax data not found for state: {state}"
            return {"task": function_name, "error": error}
        
        tax_slabs = road_tax_data.get("tax_slabs", {})
        registration_charges = road_tax_data.get("registration_charges", 0)
        additional_charges_data = road_tax_data.get("additional_charges", [])

        vehicle_type_key = None
        if "all_vehicle" in tax_slabs:
            vehicle_type_key = "all_vehicle"
        else:
            if is_company_vehicle:
                vehicle_type_key = "commercial_vehicle"
            else:
                vehicle_type_key = "private_vehicle"
        
        engine_slabs = tax_slabs.get(vehicle_type_key, {}).get(engine_type, [])

        if not engine_slabs:
            error = f"Engine slabs not found for state: {state}, vehicle_type: {vehicle_type_key}, engine_type: {engine_type}"
            return {"task": function_name, "error": error}

        applicable_rate = None
        for slab in engine_slabs:
            min_val = slab["min"]
            max_val = slab["max"]
            if max_val is None or (ex_showroom_price >= min_val and ex_showroom_price <= max_val):
                applicable_rate = slab["rate"]
                break

        road_tax = (ex_showroom_price * applicable_rate) / 100
        additional_charge = 0
        for add in additional_charges_data:
            min_val = add["min"]
            max_val = add["max"]
            if max_val is None or (ex_showroom_price >= min_val and ex_showroom_price <= max_val):
                if add["type"] == "percentage":
                    additional_charge = ex_showroom_price * (add["rate"] / 100)
                else:
                    additional_charge = add["rate"]
                break

        # --- Optional local charges --- # 
        total_misc_charges = 0

        total_misc_charges += BASE_CHARGES["registration_charges"]["amount"]
        
        parking_fee = 0
        if ex_showroom_price <= 400000:
            parking_fee = BASE_CHARGES["parking_fee_charges"]["amount"]["below_4_lakh"]
        else:
            parking_fee = BASE_CHARGES["parking_fee_charges"]["amount"]["above_4_lakh"]
        total_misc_charges += parking_fee

        total_misc_charges += BASE_CHARGES["number_plate_charges"]["amount"]

        total_misc_charges += BASE_CHARGES["fasttag_charges"]["amount"]

        if is_on_loan:
            total_misc_charges += BASE_CHARGES["hypothecation_charges"]["amount"]

        if has_temp_registration:
            total_misc_charges += BASE_CHARGES["temporary_registration_charges"]["amount"]
        
        total_on_road_price = ex_showroom_price + road_tax + total_misc_charges + additional_charge
        DISCLAIMER = (
            "The prices are calculated based on the currently available data." 
            "All prices are subject to change without prior notice."  
            "Please check with the dealer for exact details." )
        final_result = {
            "task": function_name,
            "state": state,
            "gst_rate": gst_rate,
            "gst_cost": round(gst_amount, 2),
            "engine_type": engine_type,
            "engine_capacity": engine_capacity,
            "is_company_vehicle": is_company_vehicle,
            "ex_showroom_price": ex_showroom_price,
            "road_tax_rate": applicable_rate,
            "road_tax": round(road_tax, 2),
            "registration_charges": registration_charges,
            "misc_charges_breakdown": {
                "parking_fee": parking_fee,
                "number_plate": BASE_CHARGES["number_plate_charges"]["amount"],
                "fasttag": BASE_CHARGES["fasttag_charges"]["amount"],
                "hypothecation": BASE_CHARGES["hypothecation_charges"]["amount"] if is_on_loan else 0,
                "temporary_registration": BASE_CHARGES["temporary_registration_charges"]["amount"] if has_temp_registration else 0
            },
            "additional_charge": additional_charge,
            "total_misc_charges": total_misc_charges,
            "total_on_road_price": round(total_on_road_price, 2),
            "disclaimer": DISCLAIMER
        }
        return final_result
    except Exception as e:
        logger.error(f"Compute On Road Price Error: {e}")
        traceback.print_exc()
        return {
            "task": function_name,
            "error": str(e).strip()
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
print(json.dumps(agents_list, indent=4))


@gryd.is_a_task()
def query_orchestrator(*args, **kwargs):
    from AgentOrchestrator import AgentOrchestrator
    agent_kwargs = kwargs
    logger.info(f"Agent Kwargs: {json.dumps(agent_kwargs, indent=4, default=str)}")
    a = AgentOrchestrator(model_identifier="azure-gpt-4o")
    response = a.orchestrator(**agent_kwargs)
    for r in response:
        yield r

if __name__ == "__main__":
    r = compute_on_road_price(source = {"state" : "maha", "engine_type" : "ev", "ex_showroom_price" : 950000, "gst_rate" : 18})
    logger.info(f"Result: {json.dumps(r, indent=4, default=str)}")




# def compute_on_road_price(ex_showroom_price: float,
#                           engine_type: str,
#                           state: str,
#                           enterprise_id: str) -> dict:
#     """
#     Compute on-road price breakdown using dynamic models.
#     - Engine-type–specific data (registration, road tax) comes from dedicated models.
#     - State-only charges (like number plate, fast tag, parking, etc.) come from a common model.
#     """

#     # --- Engine-type dependent models ---
#     registration_rate_model = model.Model("state_registration_charges", enterprise_id)
#     road_tax_rate_model = model.Model("state_road_tax_charges", enterprise_id)

#     # --- Common model for state-only fixed charges ---
#     state_flat_charges_model = model.Model("state_flat_charges", enterprise_id)
#     # Example structure of this model:
#     # {
#     #   "Karnataka": {
#     #       "number_plate_charges": 1000,
#     #       "temporary_registration_charges": 500,
#     #       "fast_tag_charges": 500,
#     #       "parking_fee_state_development_charges": 2000,
#     #       "hypothecation_charges": 0
#     #   },
#     #   "Tamil Nadu": {...}
#     # }

#     # --- Fetch engine-type specific rates ---
#     reg_rate = registration_rate_model.get(state, {}).get(engine_type)
#     road_rate = road_tax_rate_model.get(state, {}).get(engine_type)

#     # --- Fetch state-only flat charges ---
#     state_flat = state_flat_charges_model.get(state, {})

#     # Safety checks
#     if reg_rate is None or road_rate is None:
#         raise ValueError(f"Rates not defined for state={state}, engine_type={engine_type}")

#     # --- Compute each component ---
#     reg_charges = ex_showroom_price * reg_rate
#     road_tax_charges = ex_showroom_price * road_rate

#     hypothecation_charges = state_flat.get("hypothecation_charges", 0)
#     number_plate_charges = state_flat.get("number_plate_charges", 0)
#     parking_dev_charges = state_flat.get("parking_fee_state_development_charges", 0)
#     temp_registration_charges = state_flat.get("temporary_registration_charges", 0)
#     fast_tag_charges = state_flat.get("fast_tag_charges", 0)

#     # --- Aggregate all ---
#     result = {
#         "ex_showroom_price": round(ex_showroom_price, 2),
#         "registration_charges": round(reg_charges, 2),
#         "hypothecation_charges": round(hypothecation_charges, 2),
#         "number_plate_charges": round(number_plate_charges, 2),
#         "parking_fee_state_development_charges": round(parking_dev_charges, 2),
#         "temporary_registration_charges": round(temp_registration_charges, 2),
#         "road_tax_charges": round(road_tax_charges, 2),
#         "fast_tag_charges": round(fast_tag_charges, 2),
#     }

#     result["on_road_price"] = round(sum(result.values()), 2)

#     return result


# rm = gryd.get_service_connection()                      service_id = str(gryd.hp.make_uuid3(service, gryd.ENVIRONMENT))
# r = rm.get_worker(service_id)
# rr = r.get('list_of_docs', {})


# rm = gryd.get_service_connection() 
# list(rm.list())