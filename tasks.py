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
        propensity_agent_results = propensity_agent.execute(*args, **kwargs)
        competitor_analysis_agent_results = competitor_analysis_agent.execute(*args, **kwargs)
        prioritization_agent_results = prioritization_agent.execute(*args, **kwargs)
        logger.info(propensity_agent_results)
        logger.info(competitor_analysis_agent_results)
        logger.info(prioritization_agent_results)
        return propensity_agent_results, competitor_analysis_agent_results, prioritization_agent_results
    
    tasks_details = []
    propensity_agent_task_details = gryd.create_async_task(function_name="propensity_agent", service=GRYD_SERVICE, args=(None), kwargs=kwargs)
    competitor_analysis_agent_task_details = gryd.create_async_task(function_name="competitor_analysis_agent", service=GRYD_SERVICE, args=(None), kwargs=kwargs)
    prioritization_agent_task_details = gryd.create_async_task(function_name="prioritization_agent", service=GRYD_SERVICE, args=(None), kwargs=kwargs)

    tasks_details.append(propensity_agent_task_details)
    tasks_details.append(competitor_analysis_agent_task_details)
    tasks_details.append(prioritization_agent_task_details)
    return tasks_details
    
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
    return {"task" : "propensity_agent", "results" : {"scores" : scores, "propensity_chart_url" : propensity_chart_url}}

@gryd.is_a_task()
def competitor_analysis_agent(*args, **kwargs):
    return {"task" : "competitor_analysis_agent", "results" : "competitor_analysis_agent_results"}

@gryd.is_a_task()
def prioritization_agent(*args, **kwargs):
    return {"task" : "prioritization_agent", "results" : "prioritization_agent_results"}

@gryd.is_a_task()
def results(*args, **kwargs):
    task_id = kwargs.get("task_id")
    task = gryd_result(task_id)
    return task


