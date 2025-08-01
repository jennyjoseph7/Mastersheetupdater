from gryd_worker import gryd
from gryd_worker.gryd_routes import gryd_result
from utils import GRYD_SERVICE, GRYD_CONFIG, get_logger

logger = get_logger(__name__)

gryd.SERVICE = GRYD_SERVICE
gryd.set_queue_manager(config = GRYD_CONFIG)

@gryd.is_a_task()
def autobot_agents_trigger(*args, **kwargs):
    json_file : str = kwargs.get("file", None)
    if json_file is None:
        raise ValueError("File is required")
    
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
    return {"task" : "propensity_agent", "results" : "propensity_agent_results"}

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


