from gryd_worker import gryd
from gryd_worker.gryd_routes import gryd_result
from utils import GRYD_SERVICE, GRYD_CONFIG, get_logger, upload_file
from typing import Union, Dict, Any, Generator
import json
import traceback

logger = get_logger(__name__)

gryd.SERVICE = GRYD_SERVICE
gryd.set_queue_manager(config = GRYD_CONFIG)

@gryd.is_a_task()
def autobot_agents_trigger(*args, **kwargs):
    source : Union[Dict, str] = kwargs.get("source", None)
    if source is None:
        raise ValueError("'source' is required. Either pass a valid dict or a valid URL or filepath for JSON.")
    
    execution_mode = kwargs.get("execution_mode", "async").lower()

    aem_integration_agent_results = aem_integration_agent.execute(*args, **kwargs)
    kwargs['aem_integration_agent_results'] = aem_integration_agent_results
    kwargs['source'] = aem_integration_agent_results.get("updated_source")

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

    def result_handler(awaited_tasks : list[dict], execution_mode : str):
        task_results = []
        if execution_mode == "async":
            logger.info("🚀🚀 Running tasks asynchronously...")
            jobs = gryd.yield_results(awaited_tasks, timeout=120)
            for job in jobs:
                task_name, status, result_data = job[1], job[3], job[4]
                if status == "result":
                    logger.info(f"✅✅ Task '{task_name}' completed with result: {json.dumps(result_data, indent=4, default=str)}")
                    task_results.append(result_data)
                else:
                    logger.warning(f"Task '{task_name}' failed or still pending. Status: {status}")
        else:
            logger.info("Running tasks synchronously...")
            jobs = gryd.await_results(awaited_tasks, timeout=120)
            for job in jobs:
                task_results.append(job)
        return task_results

    task_results : list = result_handler(awaited_tasks, execution_mode=execution_mode)

    for task_result in task_results:
        if task_result.get("task") == "propensity_agent":
            kwargs["propensity_agent_results"] = task_result
        elif task_result.get("task") == "competitor_analysis_agent":
            kwargs["competitor_analysis_agent_results"] = task_result
        elif task_result.get("task") == "prioritization_agent":
            kwargs["prioritization_agent_results"] = task_result

    # Use Kwargs for Next agent execution and return final dict.
    sentiment_agent_results = sentiment_agent.execute(*args, **kwargs)
    kwargs['sentiment_analysis_agent_results'] = sentiment_agent_results

    personalization_agent_results = personalization_agent.execute(*args, **kwargs)
    kwargs['personalization_agent_results'] = personalization_agent_results

    communication_agent_results = communication_agent.execute(*args, **kwargs)
    kwargs['communication_agent_results'] = communication_agent_results

    task_results.extend([sentiment_agent_results, personalization_agent_results, communication_agent_results])
    task_result.append(0, aem_integration_agent_results)

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
        "sentiment_analysis_agent_results": sentiment_agent,
        "personalization_agent_results": personalization_agent,
        "communication_agent_results": communication_agent,
    }

    for key, agent in next_agents.items():
        result = agent.execute(*args, **kwargs)
        kwargs[key] = result
        yield result

@gryd.is_a_task()
def aem_integration_agent(*args, **kwargs):
    from agents.aem_integration_agent import AEMIntegrationAgent
    source = kwargs['source']
    model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
    aem_agent = AEMIntegrationAgent(source = source, model_identifier=model_identifier)
    updated_source = aem_agent.run()
    return {"task": "aem_integration_agent", "updated_source": updated_source}

    
@gryd.is_a_task()    
def propensity_agent(*args, **kwargs):
    try:
        from agents.propensity_agent import PropensityAgent
        source = kwargs["source"]
        model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
        propensity_agent = PropensityAgent(source = source, model_identifier=model_identifier)
        agent_response : dict = propensity_agent.run()
        scores = agent_response.get("scores")
        img_bytes = agent_response.get("img_bytes")
        reasoning = agent_response.get("reasoning")
        response = upload_file(img_bytes, {"autobot-agent": True})
        propensity_chart_url = response["cdn_url"] if isinstance(response, dict) else response
        filtered_results = {
            "task": "propensity_agent",
            "scores": scores,
            "propensity_chart_url": propensity_chart_url,
            "reasoning": reasoning
            # "propensity_chart_json": fig_json
        }
        logger.info(f"Propensity Agent Results: {json.dumps(filtered_results, indent = 4, default = str)}")
        return filtered_results
    except Exception as e:
        logger.error(f"Propensity Agent Error: \n\n")
        traceback.print_exc()

@gryd.is_a_task()
def personalization_agent(*args, **kwargs):
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
        "task": "personalization_agent",
        "personalization_agent_response": personalization_agent_results.get("response"),
        "reasoning": personalization_agent_results.get("ai-thinking")
    }
    return filtered_results

@gryd.is_a_task()
def competitor_analysis_agent(*args, **kwargs):
    from agents.competitor_analysis_agent.main import CompetitorAnalysis
    source = kwargs["source"]
    model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
    top_n = kwargs.get("top_n", 3)
    competitor_agent = CompetitorAnalysis(source = source, model_identifier=model_identifier,top_n=top_n)
    analysis = competitor_agent.get_analysis()
    filtered_results = {
        "task": "competitor_analysis_agent",
        "top_models": top_n,
        "compared_cars_data": analysis.get("compared_cars_data",""),
        "comparisons": analysis.get("comparisons",""),
        "common_points": analysis.get("common_points",""),
        "key_differences": analysis.get("key_differences",""),
        "user_choice_justification": analysis.get("user_choice_justification","")
    }
    return filtered_results

@gryd.is_a_task()
def prioritization_agent(*args, **kwargs):
    from agents.lead_prioritization_agent import LeadPrioritizationAgent
    source = kwargs["source"]
    model_identifier = kwargs.get("model_identifier","azure-gpt-4o")
    priority_agent = LeadPrioritizationAgent(source = source, model_identifier=model_identifier)
    lead_analysis = priority_agent.complete_analysis()
    filtered_results = {
        "task":"prioritization_agent",
        **lead_analysis
    }
    return filtered_results

@gryd.is_a_task()
def communication_agent(*args, **kwargs):
    from agents.communication_agent import CommunicationAgent
    source = kwargs["source"]
    model_identifier = kwargs.get("model_identifier","azure-gpt-4o")
    prioritization_results = kwargs.get("prioritization_agent_results") or {} 
    recommended_actions = prioritization_results.get("recommended_actions", [])
    if "personalized_email" not in recommended_actions:
        return {
            "task": "communication_agent",
            "email_draft": None,
            "communication_agent_result": "Email not sent as it's not a recommended action"
        }
    personalization_agent_results = kwargs.get("personalization_agent_results") or {}  
    user_message = personalization_agent_results.get("personalization_agent_response")
    if not user_message:
        logger.warning("No personalization message found. Cannot proceed with email drafting.")
        return {
            "task": "communication_agent",
            "email_draft": None,
            "communication_agent_result": "Email not sent - no personalization message available",
            "status": "failed",
            "error": "Missing personalization_agent_response"
        }
    try:
        communication_agent = CommunicationAgent(source=source, model_identifier=model_identifier)
        
        # Draft and send email
        communication_info = communication_agent.draft_and_send_email(
            cc="",
            user_message=user_message
        )
        
        filtered_results = {
            "task": "communication_agent",
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
            "task": "communication_agent",
            "email_draft": None,
            "communication_agent_result": f"Email sending failed: {str(e)}",
            "status": "error",
            "error": str(e)
        }

@gryd.is_a_task()
def sentiment_agent(*args, **kwargs):
    from agents.sentiment_agent import SentimentAnalysisAgent
    source = kwargs["source"]
    model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
    sentiment_agent = SentimentAnalysisAgent(source=source, model_identifier=model_identifier)
    analysis = sentiment_agent.run()

    filtered_results = {
        "task": "sentiment_analysis_agent",
        "user_input": analysis.get("input", {}).get("user_input", ""),
        "sentiment_score": analysis.get("expected_output", {}).get("sentiment_score", 0.0),
        "emotions": analysis.get("expected_output", {}).get("emotions", []),
        "justification": analysis.get("expected_output", {}).get("justification", "")
    }
    return filtered_results
