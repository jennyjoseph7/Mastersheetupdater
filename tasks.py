from gryd_worker import gryd
from utils import GRYD_SERVICE, GRYD_CONFIG

gryd.SERVICE = GRYD_SERVICE
gryd.set_queue_manager(config = GRYD_CONFIG)

@gryd.is_a_task(function_name="autobot_agents_trigger")
def autobot_agents_trigger(*args, **kwargs):
    json_file : str = kwargs.get("file", None)
    if json_file is None:
        raise ValueError("File is required")
    
    propensity_agent = [{
                "task": "propensity_agent",
                "service": GRYD_SERVICE,
                "args": (None),
                "kwargs": kwargs
            }]
    
    competitor_analysis_agent = [{
                "task": "competitor_analysis_agent",
                "service": GRYD_SERVICE,
                "args": (None),
                "kwargs": kwargs
            }]
    
    prioritization_agent = [{
                "task": "prioritization_agent",
                "service": GRYD_SERVICE,
                "args": (None),
                "kwargs": kwargs
            }]
    
    execution_mode = kwargs.get("execution_mode", "sync")
    if execution_mode == "sync":
        propensity_agent_results = gryd.await_results(propensity_agent)
        competitor_analysis_agent_results = gryd.await_results(competitor_analysis_agent)
        prioritization_agent_results = gryd.await_results(prioritization_agent)
        return propensity_agent_results, competitor_analysis_agent_results, prioritization_agent_results
    
    
def propensity_agent(*args, **kwargs):
    return "propensity_agent_results"

def competitor_analysis_agent(*args, **kwargs):
    return "competitor_analysis_agent_results"

def prioritization_agent(*args, **kwargs):
    return "prioritization_agent_results"

