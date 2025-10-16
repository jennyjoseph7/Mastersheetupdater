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


# r = ai_service_app.list_models(cloud="groq")
# logger.info(f"AI Models: {json.dumps(r, indent=4)}")
# assert False

def environment(environment: str = "-local"):
    if not environment.startswith("-"):
        environment = f"-{environment}"
    gryd.ENVIRONMENT = environment
    message = {"message": f"Environment set to '{environment}'"}
    logger.info(message)
    return message

# GRYD_ENVIRONMENT = os.getenv("ENVIRONMENT", "-local")
# environment(environment = GRYD_ENVIRONMENT)

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
                    logger.info(f"'{func.__name__}' executed in {int(elapsed)} sec")
                else:
                    logger.info(f"'{func.__name__}' executed in {elapsed:.6f} sec")
            return wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                end = time.perf_counter()
                elapsed = end - start
                if view_type is int:
                    logger.info(f"'{func.__name__}' executed in {int(elapsed)} sec")
                else:
                    logger.info(f"'{func.__name__}' executed in {elapsed:.6f} sec")
                return result
            return wrapper
    return decorator 

# -------------------AGENT REGISTRY, DECORATORS & ORCHESTRATOR------------------->

GLOBAL_AGENT_REGISTRY = OrderedDict()

@dataclass
class AgentConfig:
    """
    Agent configuration class.
    
    :param name (str): Name of the agent.
    :param description (str): Description of the agent.
    :param execute (Callable[..., Any]): Function to execute the agent.
    :param depends_on (List[str], optional): List of agent names this agent depends on.
    :param expected_input (Dict[str, str], optional): Expected input format for the agent.
    :param expected_output (Dict[str, str], optional): Expected output format for the agent.
    """
    name: str
    description: str
    execute: Callable[..., Any]
    depends_on: List[str] = field(default_factory=list)
    expected_input: Dict[str, str] = field(default_factory=dict) 
    expected_output: Dict[str, str] = field(default_factory=dict)

def register_agent(name:str=None, description:str=None, depends_on:list[str]=None, expected_input:dict[str]=None, expected_output:dict[str]=None):
    """
    Decorator to register a function as an agent in the orchestrator's AGENT_REGISTRY.
    
    :param name: Optional name for the agent (default: function name)
    :param description: Description of the agent (default: function docstring)
    :param depends_on: List of agent names this agent depends on
    :param expected_input: Expected input format for the agent [optional]
    :param expected_output: Expected output format for the agent [optional]
    """
    def decorator(func):
        # nonlocal name, description, depends_on, expected_input, expected_output
        dep_ = depends_on or []
        exp_i = expected_input or {}
        exp_o = expected_output or {}
        agent_name = name or func.__name__
        agent_description = (description or func.__doc__ or "").strip()
        GLOBAL_AGENT_REGISTRY[agent_name] = {
            "name": agent_name,
            "description": agent_description,
            "execute": func,
            "depends_on": dep_,
            "expected_input": exp_i,
            "expected_output": exp_o
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
                    description=meta.get("description"),
                    execute=meta.get("execute"),
                    depends_on=meta.get("depends_on"),
                    expected_input=meta.get("expected_input"),
                    expected_output=meta.get("expected_output"),
                )
            )

        self.JSON_PLAN = {
            "plan": [
                {
                    "task": agent.name,
                    "kwargs": {},
                    "args": (None),  
                    "depends_on": agent.depends_on,
                    "expected_input": agent.expected_input,
                    "expected_output": agent.expected_output
                }
                for agent in self.AGENT_REGISTRY
            ],
            "reasoning" : None
        }

    def inspect_func_schema(self, func):
        "Work in progress. We can try to find end to end function schema for better orchestration"
        sig = inspect.signature(func)
        return sig

    @property
    def agent_descriptions(self) -> List[dict]:
        agent_descriptions = []
        for idx, agent in enumerate(self.AGENT_REGISTRY, start=1):
            agent_descriptions.append({
                "index": idx,
                "name": agent.name,
                "description": agent.description,
                "depends_on": agent.depends_on,
                "expected_input": agent.expected_input,
                "expected_output": agent.expected_output
            })
        return agent_descriptions
        # return [f"{idx}.{agent.name}: {agent.description} (depends_on: {agent.depends_on})" for idx, agent in enumerate(self.AGENT_REGISTRY, start=1)]
    
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
    @timer(view_type=float)
    def llm_generate_plan(self, query: str, model_identifier: str = None, **agent_kwargs) -> List[Dict[str, Any]]:
        if model_identifier:
            self.model_identifier = model_identifier
        
        source_data = self.load_json(agent_kwargs)
        logger.info("-------------------SOURCE DATA LOADED-------------------")
        print(f"{json.dumps(source_data, indent=4, default=str)}")
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
        - Understand 'expected_input' and 'expected_output' for each agent if given.
        - All inputs must be passed in `kwargs` as key-value pairs. 
            Example:
            "kwargs": {{"source": <source_data>}}
            "kwargs": {{"some_key": "some_data"}}
        - Keep `args` as null unless there is a very strong reason otherwise (default: null).
        - Only include agents directly relevant to the query.
        - Do not include unrelated agents, Only add if they are dependencies of other downstream agents.
        - If the query is unrelated to any agent, just return an empty plan and don't include any agents. (Maybe in reasoning, mention that the query is unrelated to any agent and thus no plan is needed. Give an good understanding of available agents, what they do and how they can be used to answer the query maybe with some examples. Explain in a natural way with 6-7 sentences max so it doesn't feel too long.)

        JSON schema (follow exactly): 

        - Add a 'reasoning' key that describes what the LLM is thinking while generating the plan. Write it in a step-by-step, natural way — like a human would explain their thought process. Use casual phrases like "Hmm, let me think…" or "Next, I'll…". Explain why each agent is chosen, the role it plays, and how it contributes to answering the user query (e.g., aem_integration_agent → propensity_agent → sentiment_analysis_agent → …). 
        For each agent, explain why it is selected, what it does, and how it depends on or supports the next agent (e.g., aem_integration_agent → propensity_agent → sentiment_analysis_agent → …). Clearly mention the dependency flow — why one agent's output is needed for the next.
        After laying out the reasoning, end with a short summary like: “Based on this reasoning, let's build an execution plan and begin executing.” Keep it 6-7 sentences max so it doesn't feel too long.

        - Strictly follow the Plan order while respecting dependencies.
        {json.dumps(self.JSON_PLAN, indent=4)}
        """

        # - Add a 'reasoning' key with a description of what the LLM is doing While generating the plan, describe your reasoning step by step: explain why you select each agent, what role it plays, and how it contributes to answering the user query. After summarizing your thought process, conclude with a sentence like 'Based on this reasoning, let's build an execution plan and begin executing. Should be 5-6 sentences max. Make it look like a human would write it. (Sentences like Hmm, Let me think...etc are encouraged)'. Give agent execution steps like below in reasoning: aem_integration_agent -> propensity_agent -> sentiment_analysis_agent -> ...etc.
        # - If the query is only about prioritization, run aem_integration_agent first (for enrichment) and then prioritization_agent only.
        logger.info(f"Agent Descriptions: {json.dumps(self.agent_descriptions, indent=4)}")
        user_prompt = (
            f"Query: {query}\n\n"
            f"Context kwargs: {json.dumps(source_data, indent=4)}\n\n"
            f"Available Agents with dependencies:\n{json.dumps(self.agent_descriptions, indent=4)}"
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
    
    # Full Example: {{
    # "task": "some_agent",
    # "kwargs": {{"source": <source_data>}},
    # "args": [],
    # "depends_on": ["some_agent_1", "some_agent_2"]
    # }} or 
    # "task": "some_agent",
    # "kwargs": {{"query": <source_data>}},
    # "args": [],
    # "depends_on": ["some_agent_1", "some_agent_2"]
    # }}
    
    def conclusive_reasoning(self, query: str, accumulated_results: dict) -> str:
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
                "content": f"Query: {query}\n\nAccumulated Results: {json.dumps(accumulated_results, indent=4)}"
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
            f_plan["reasoning"] = reasoning
        # logger.info(f"Reasoning: {reasoning}")
        yield f_plan
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
                # if "error" in aem_result:
                #     yield aem_result
                #     return
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
            # if "error" in result_dict:
            #     yield result_dict
            #     return
            agent_key = f"{step['task']}_results"
            results_accumulator[agent_key] = result_dict
            yield {agent_key: result_dict}

        yield {"conclusive_reasoning": self.conclusive_reasoning(user_query, results_accumulator)}
if __name__ == "__main__":
    while True:
        query = str(input("Enter Query: "))
        #query = "what's the sentiment of this customer? also find closest dealers to the customer"
        #query = "find closest dealers to the customer"
        source_data = "/home/shreyasvaishnav/autobot_agents/aem_mock_data/5.json"
        a = AgentOrchestrator()
        for idx, update in enumerate(a.orchestrator(user_query=query, source=source_data), start=1):
            print(f"Yielded Iteration {idx}: {json.dumps(update, indent=4, default=str)}")