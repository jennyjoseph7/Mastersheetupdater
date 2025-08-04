from gryd_worker import gryd
from gryd_worker.gryd_routes import gryd_result
from utils import GRYD_SERVICE, GRYD_CONFIG, get_logger, upload_file
from typing import Union, Dict, Any
import json

logger = get_logger(__name__)

gryd.SERVICE = GRYD_SERVICE
gryd.set_queue_manager(config = GRYD_CONFIG)

@gryd.is_a_task()
def autobot_agents_trigger(*args, **kwargs):
    source : Union[Dict, str] = kwargs.get("source", None)
    if source is None:
        raise ValueError("'source' is required. Either pass a valid dict or a valid URL or filepath for JSON.")
    
    execution_mode = kwargs.get("execution_mode", "sync").lower()
    if execution_mode == "sync":
        # Step 1: Running Propensity Agent
        propensity_agent_results = propensity_agent.execute(*args, **kwargs)
        kwargs['propensity_agent_results'] = propensity_agent_results

        # Step 2: Running Personalization Agent        
        competitor_analysis_agent_results = competitor_analysis_agent.execute(*args, **kwargs)
        kwargs['competitor_analysis_agent_results'] = competitor_analysis_agent_results

        # Step 3: Running Prioritization Agent
        prioritization_agent_results = prioritization_agent.execute(*args, **kwargs)
        kwargs['prioritization_agent_results'] = prioritization_agent_results

        # Step 4: Running Personalization Agent
        personalization_agent_results = personalization_agent.execute(*args, **kwargs)
        kwargs['personalization_agent_results'] = personalization_agent_results

        # Step 5: Running Communication Agent
        communication_agent_results = communication_agent.execute(*args, **kwargs)
        kwargs['communication_agent_results'] = communication_agent_results
    
        return propensity_agent_results, personalization_agent_results, competitor_analysis_agent_results, prioritization_agent_results


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

    task_results = []
    for job in gryd.yield_results(awaited_tasks, timeout=120):
        task_name, status, result_data = job[1], job[3], job[4]
        if status == "result":
            logger.info(f"Task '{task_name}' completed with result: {json.dumps(result_data, indent=4, default=str)}")
            task_results.append(result_data)
        else:
            logger.warning(f"Task '{task_name}' failed or still pending. Status: {status}")

    logger.info(f"Parallel Task results: {json.dumps(task_results, indent=4, default=str)}")

    for task_result in task_results:
        if task_result.get("task") == "propensity_agent":
            kwargs["propensity_agent_results"] = task_result
        elif task_result.get("task") == "competitor_analysis_agent":
            kwargs["competitor_analysis_agent_results"] = task_result
        elif task_result.get("task") == "prioritization_agent":
            kwargs["prioritization_agent_results"] = task_result

    # Use Kwargs for Next agent execution and return final dict.
    personalization_agent_results = personalization_agent.execute(*args, **kwargs)
    communication_agent_results = communication_agent.execute(*args, **kwargs)
    task_results.extend([personalization_agent_results, communication_agent_results])

    logger.info(f"Final Task results: {json.dumps(task_results, indent=4, default=str)}")
    return task_results
    
@gryd.is_a_task()    
def propensity_agent(*args, **kwargs):
    from agents.propensity_agent import PropensityAgent
    source = kwargs["source"]
    model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
    propensity_agent = PropensityAgent(source = source, model_identifier=model_identifier)
    scores, fig, img_bytes = propensity_agent.run()
    logger.info(f"Propensity Agent Results: {json.dumps(scores, indent = 4, default = str)}")
    response = upload_file(img_bytes, {"autobot-agent": True})
    logger.info(f"Propensity Agent Image Response: {response}")
    propensity_chart_url = response["cdn_url"] if isinstance(response, dict) else response
    return {"task" : "propensity_agent", "scores" : scores, "propensity_chart_url" : propensity_chart_url}

@gryd.is_a_task()
def personalization_agent(*args, **kwargs):
    # Your implementation goes here
    return {"task" : "personalization_agent", "results" : "personalization_agent_results"}

@gryd.is_a_task()
def competitor_analysis_agent(*args, **kwargs):
    from agents.competitor_analysis_agent.main import CompetitorAnalysis
    source = kwargs["source"]
    model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
    competitor_agent = CompetitorAnalysis(source = source, model_identifier=model_identifier)
    analysis = competitor_agent.get_analysis()
    filtered_results = {
        "task": "competitor_analysis_agent",
        "compared_cars_data": analysis.get("compared_cars_data",""),
        "comparisons": analysis.get("comparisons",""),
        "common_points": analysis.get("common_points",""),
        "key_differences": analysis.get("key_differences",""),
        "user_choice_justification": analysis.get("key_differences","")
    }

    return filtered_results

@gryd.is_a_task()
def prioritization_agent(*args, **kwargs):
    return {"task" : "prioritization_agent", "results" : "prioritization_agent_results"}

@gryd.is_a_task()
def communication_agent(*args, **kwargs):
    return {"task" : "communication_agent", "results" : "communication_agent_results"}

@gryd.is_a_task()
def results(*args, **kwargs):
    task_id = kwargs.get("task_id")
    task = gryd_result(task_id)
    return task