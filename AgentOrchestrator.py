import json
import os
import traceback
import requests
from typing import Any, Dict, Union, List
from urllib.parse import urlparse
# from tasks import *
from utils import *
from ai_service import ai_service_app
from dataclasses import dataclass, field
from typing import Callable, List, Dict, Any, Iterator
import functools, inspect
from gryd_worker import gryd
from collections import OrderedDict

logger = get_logger(__name__)

# gryd.SERVICE = GRYD_SERVICE
# gryd.set_queue_manager(config = GRYD_CONFIG)

def environment(environment: str = "-local"):
    if not environment.startswith("-"):
        environment = f"-{environment}"
    gryd.ENVIRONMENT = environment
    message = {"message": f"Environment set to '{environment}'"}
    logger.info(message)
    return message

GLOBAL_AGENT_REGISTRY = OrderedDict()

# GRYD_ENVIRONMENT = os.getenv("ENVIRONMENT", "-local")
# environment(environment = GRYD_ENVIRONMENT)

@dataclass
class AgentConfig:
    name: str
    description: str
    execute: Callable[..., Any]
    depends_on: List[str] = field(default_factory=list)
    # expected_outputs: Dict[str, Any] = field(default_factory=dict)

def timer(view_type=float):
    if view_type not in (int, float):
        raise ValueError("view_type must be either float or int")
    def decorator(func):
        if inspect.isgeneratorfunction(func):  # Handling generators
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                gen = func(*args, **kwargs)
                for value in gen:
                    yield value
                end = time.perf_counter()
                elapsed = end - start
                if view_type is int:
                    print(f"'{func.__name__}' executed in {int(elapsed)} sec")
                else:
                    print(f"'{func.__name__}' executed in {elapsed:.6f} sec")
            return wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                end = time.perf_counter()
                elapsed = end - start
                if view_type is int:
                    print(f"'{func.__name__}' executed in {int(elapsed)} sec")
                else:
                    print(f"'{func.__name__}' executed in {elapsed:.6f} sec")
                return result
            return wrapper
    return decorator 

def register_agent(name:str=None, description:str=None, depends_on:list[str]=None):
    depends_on = depends_on or []
    """
    Decorator to register a function as an agent in the orchestrator's AGENT_REGISTRY.
    :param name: Optional name for the agent (default: function name)
    :param description: Description of the agent
    :param depends_on: List of agent names this agent depends on
    """
    def decorator(func):
        agent_name = name or func.__name__
        agent_description = description or func.__doc__
        GLOBAL_AGENT_REGISTRY[agent_name] = {
            "name": agent_name,
            "description": agent_description.strip(),
            "execute": func,
            "depends_on": depends_on
        }
        return func
    return decorator

class AgentOrchestrator:
    def __init__(self, model_identifier: str = "azure-gpt-4o"):
        self.model_identifier : str = model_identifier
        self.AGENT_REGISTRY: List[AgentConfig] = []

        for name, meta in GLOBAL_AGENT_REGISTRY.items():
            self.AGENT_REGISTRY.append(
                AgentConfig(
                    name=name,
                    description=meta.get("description", ""),
                    execute=meta.get("execute"),
                    depends_on=meta.get("depends_on", [])
                )
            )

        self.JSON_PLAN = {
            "plan": [
                {
                    "task": agent.name,
                    "kwargs": {},
                    "args": (None),  
                    "depends_on": agent.depends_on
                }
                for agent in self.AGENT_REGISTRY
            ],
            "reasoning" : None
        }
    @property
    def agent_descriptions(self) -> List[str]:
        return [f"{idx}.{agent.name}: {agent.description} (depends_on: {agent.depends_on})" for idx, agent in enumerate(self.AGENT_REGISTRY, start=1)]
    
    @property
    def default_plan(self) -> dict:
        return self.JSON_PLAN['Plan']
    
    def extract_json_from_llm_response(self, response: str) -> dict:
        stack, start = [], None
        for i, ch in enumerate(response):
            if ch in "{[":
                if not stack:
                    start = i
                stack.append(ch)
            elif ch in "}]":
                if not stack:
                    continue
                opening = stack.pop()
                if (opening == "{" and ch != "}") or (opening == "[" and ch != "]"):
                    return None
                if not stack:
                    json_str = response[start:i + 1]
                    try:
                        return json.loads(json_str)
                    except Exception:
                        return None
        return None

    def load_json(self, source: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """Load JSON from a dict, local path, or URL."""
        if isinstance(source, (dict, list)):
            return source
        if isinstance(source, str):
            parsed = urlparse(source)
            if parsed.scheme in ("http", "https"):
                response = requests.get(source)
                response.raise_for_status()
                return response.json()
            elif os.path.isfile(source):
                with open(source, 'r') as f:
                    return json.load(f)
        raise ValueError(f"Invalid JSON source: {source}")

    # ---------- Core Methods ----------
    def llm_generate_plan(self, query: str, model_identifier: str = None, **agent_kwargs) -> List[Dict[str, Any]]:
        if model_identifier:
            self.model_identifier = model_identifier
        
        source_data = self.load_json(agent_kwargs)
        logger.info("-------------------SOURCE DATA LOADED-------------------")
        logger.info(f"{json.dumps(source_data, indent=4, default=str)}")
        logger.info("-------------------SOURCE DATA ENDED-------------------")
        logger.info(f"Query: {query}\n\n")

        system_prompt = f"""
        You are an Smart AI Agent planning assistant.
        You will create a structured execution plan for a pipeline of agents.
        Rules:
        - Each agent has a `task` (agent name), `kwargs`, `args`, and `depends_on`.
        - Use only available agents.
        - Return valid JSON list only (no extra text).
        - Always respect dependency order:
            - aem_integration_agent must run first.
            - Always expand dependencies recursively:
            - If an agent depends on other agents, include those agents first.
            - If those agents themselves have dependencies, include them as well, recursively.
            - Make sure no agent appears twice in the plan.
            Example: 
            * Query: send final email
            * Relevant agent: communication_agent
            * Dependencies: aem_integration_agent, prioritization_agent, personalization_agent
            * personalization_agent depends on: aem_integration_agent, propensity_agent, sentiment_analysis_agent, prioritization_agent, competitor_analysis_agent
            * Plan should include: 
            aem_integration_agent -> propensity_agent -> sentiment_analysis_agent -> competitor_analysis_agent -> prioritization_agent -> personalization_agent -> communication_agent
        - If `source` is empty, just pass it as an empty dict in kwargs.
        - All inputs must be passed in `kwargs` as key-value pairs. 
            Example:
            "kwargs": {{"source": <source_data>}}
            "kwargs": {{"some_key": "some_data"}}
        - Keep `args` as null unless there is a very strong reason otherwise (default: null).
        - Only include agents directly relevant to the query.
        - Do not include unrelated agents, Only add if they are dependencies of other downstream agents.

        JSON schema (follow exactly): 
        - Add a 'reasoning' key with a description of what the LLM is doing While generating the plan, describe your reasoning step by step: explain why you select each agent, what role it plays, and how it contributes to answering the user query. After summarizing your thought process, conclude with a sentence like 'Based on this reasoning, let's build an execution plan and begin executing. Should be 5-6 sentences max. Make it look like a human would write it. (Sentences like Hmm, Let me think...etc are encouraged)'. Give agent execution steps like below in reasoning: aem_integration_agent -> propensity_agent -> sentiment_analysis_agent -> ...etc.

        - Strictly follow the Plan order while respecting dependencies.
        {json.dumps(self.JSON_PLAN, indent=4)}
        """

        # - If the query is only about prioritization, run aem_integration_agent first (for enrichment) and then prioritization_agent only.
        user_prompt = (
            f"Query: {query}\n\n"
            f"Context kwargs: {json.dumps(source_data, indent=4)}\n\n"
            f"Available Agents with dependencies:\n{self.agent_descriptions}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        logger.info(f"-------------------LLM RESPONSE RAW-------------------")
        logger.info(f"{response} \n\n")
        logger.info(f"-------------------END LLM RESPONSE RAW-------------------")
        
        try:
            plan = self.extract_json_from_llm_response(response)
            # logger.info(f"Extracted JSON from LLM Response: {json.dumps(plan, indent=2)}")
            return plan
        except Exception:
            traceback.print_exc()
            logger.error("Failed to parse plan JSON, fallback to default dependency plan.")
            plan = self.JSON_PLAN
        return plan
    
    def conclusive_reasoning(self, accumulated_results: dict) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                "You are an smart AI agent summarizing assistant."
                "You will summarize the results of a pipeline of agents in a concise and clear way. Create a short and clear summary of the results of the pipeline of agents."
                "Include pointers from produced results to the original query."
                ),
            },
            {
                "role": "user", 
                "content": json.dumps(accumulated_results, indent=4)
            },
        ]
        response = ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        return response
    @timer(view_type=float)
    def orchestrator(self, user_query: str, *args, **agent_kwargs):
        if user_query is None:
            raise ValueError("'query' is required")

        f_plan : dict = self.llm_generate_plan(query = user_query, **agent_kwargs)
        plan, reasoning = f_plan["plan"], f_plan["reasoning"]
        if reasoning is None:
            reasoning = "I am analyzing the user query to determine which agents are most suitable for each part of the task. For every step, I consider the agent's capabilities and how it can contribute to producing the correct result. I prioritize agents that can handle complex reasoning, data retrieval, or processing efficiently. Based on this reasoning, let's build an execution plan and begin executing."
        # logger.info(f"Reasoning: {reasoning}")
        yield {"reasoning": reasoning}

        agents_lineup = [step.get("task") for step in plan]
        yield {"agents_lineup": agents_lineup}

        results_accumulator = {}
        aem_result = None  # Special case to enrich data with AEM and dump this step from plan.

        logger.info(f"Final Execution Plan: \n{json.dumps(f_plan, indent=4)}")
        for step in plan:
            if step.get("task").lower() == "aem_integration_agent":
                jobs = gryd.await_results({
                    "task": step.get("task"),
                    "service": GRYD_SERVICE,
                    "args": step.get("args"),
                    "kwargs": step.get("kwargs")
                })
                aem_result = jobs[0]
                if "error" in aem_result:
                    yield aem_result
                    return
                agent_key = f"{step['task']}_result"
                results_accumulator[agent_key] = aem_result
                yield {agent_key: aem_result}
                plan.remove(step)
                break

        for step in plan:
            logger.info(f"Running step: {step}")
            if aem_result:
                step["kwargs"]["source"] = aem_result.get("updated_source", {})  
            step_kwargs = step.get("kwargs") or {}
            enriched_kwargs = {**results_accumulator, **step_kwargs}
            # logger.info(f"Enriched Kwargs: {json.dumps(enriched_kwargs, indent=4, default=str)}")
            jobs = gryd.await_results({
                "task": step.get("task"),
                "service": GRYD_SERVICE,
                "args": step.get("args"),
                "kwargs": enriched_kwargs
            })
            result_dict = jobs[0]
            if "error" in result_dict:
                yield result_dict
                return
            agent_key = f"{step['task']}_results"
            results_accumulator[agent_key] = result_dict
            yield {agent_key: result_dict}

        yield {"conclusive_reasoning": self.conclusive_reasoning(results_accumulator)}
if __name__ == "__main__":
    while True:
        query = str(input("Enter Query: "))
        #query = "what's the sentiment of this customer? also find closest dealers to the customer"
        #query = "find closest dealers to the customer"
        source_data = "/home/shreyasvaishnav/autobot_agents/aem_mock_data/5.json"
        a = AgentOrchestrator()
        for idx, update in enumerate(a.orchestrator(user_query=query, source=source_data), start=1):
            print(f"Yielded Iteration {idx}: {json.dumps(update, indent=4, default=str)}")