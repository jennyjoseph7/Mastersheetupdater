from flask import Blueprint, Response, request, stream_with_context
import json
from gryd_worker import gryd, gryd_helpers
from utility import *
from typing import *

cohort_bp_params = {
    "name": "cohort_bp",
    "import_name" : __name__ ,
    "url_prefix": "/cohorts",
}

gryd_orchestration_bp_params = {
    "name": "gryd_orchestration_bp",
    "import_name" : __name__ ,
    "url_prefix": "/cohorts/gryd",
}

cohort_bp = Blueprint(**cohort_bp_params)
gryd_orchestration_bp = Blueprint(**gryd_orchestration_bp_params)


def setup_gryd():
    gryd.SERVICE = GRYD_SERVICE_NAME
    gryd.set_queue_manager(config = GRYD_CONFIG)
    environment = os.getenv("ENVIRONMENT", "-local")
    if not environment.startswith("-"):
        environment = f"-{environment}"
    gryd.ENVIRONMENT = environment

setup_gryd()

def run_gryd_job(task_name: str, params: dict, stream: bool = False) -> Union[dict, Iterator[dict]]:
    jobs = [{
        "task": task_name,
        "service": GRYD_SERVICE_NAME,
        "kwargs": params,
        "args": (None,)
    }]
    for job in gryd.yield_results(jobs):
        task_name, status, result_data = job[1], job[3], job[4]
        if status == "result":
            logger.info(f"Task '{task_name}' yielded result:\n{result_data}\n")
            if stream:
                yield result_data
            else:
                return result_data


@cohort_bp.route("/health", methods=["POST"])
def health():
    return {"status": "ok"}

@cohort_bp.route("/stream", methods=["POST"])
def stream_cohorts():
    data = request.get_json(force=True) or {}
    _params = {
        "brochure_url": data.get("brochure_url"),
        "product_website_url": data.get("product_website_url"),
        "model_identifier": data.get("model_identifier", "azure-gpt-4o"),
        "num_of_cohorts": data.get("num_of_cohorts", 30),
    }

    _batch_size = data.get("batch_size", 10)

    def generate():
        from cohort_generation_agent import ProductCohortGenerationAgent
        agent = ProductCohortGenerationAgent(**_params)

        for event in agent.run_with_events(batch_size=_batch_size):
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@cohort_bp.route("/generate", methods=["POST"])
def get_cohorts():
    from cohort_generation_agent import ProductCohortGenerationAgent
    data = request.get_json(force=True) or {}
    _params = {
        "brochure_url": data.get("brochure_url"),
        "product_website_url": data.get("product_website_url"),
        "model_identifier": data.get("model_identifier", "azure-gpt-4o"),
        "num_of_cohorts": data.get("num_of_cohorts", 30),
    }
    _batch_size = data.get("batch_size", 10)
    agent = ProductCohortGenerationAgent(**_params)
    result = agent.run(batch_size=_batch_size)
    return result

@cohort_bp.route("/classify", methods=["POST"])
def classify():
    from cohort_classification_agent import CohortClassificationAgent
    data = request.get_json(force=True) or {}
    _params = {
        "source": data.get("source"),
        "cohorts": data.get("cohorts"),
        "brochure_url": data.get("brochure_url"),
        "product_website_url": data.get("product_website_url"),
        "model_identifier": data.get("model_identifier", "azure-gpt-4o"),
    }
    agent = CohortClassificationAgent(**_params)
    result = agent.run()
    return result


@cohort_bp.route("/affinity", methods=["POST"])
def affinity():
    from affinity_agent import AffinityEngineAgent
    data = request.get_json(force=True) or {}
    _params = {
        "interaction_json": data.get("interaction_json", None),
        "brochure_url": data.get("brochure_url", None),
        "product_website_url": data.get("product_website_url", None),
        "model_identifier": data.get("model_identifier", "azure-gpt-4o"),
        "domain": data.get("domain", None),
        "custom_affinity_dimensions": data.get("custom_affinity_dimensions", None)
    }
    affinity_score_agent = AffinityEngineAgent(**_params)
    result = affinity_score_agent.run()
    return result

@cohort_bp.route("/campaign_ideas", methods=["POST"])
def campaign_ideas():
    from campaign_idea_generation_agent import CampaignIdeaGeneratorAgent
    data = request.get_json(force=True) or {}
    source = data.get("source", None)                                 # Custom Interaction Data in Dict
    classified_cohort = data.get("classified_cohort", None)           # Cohort Classification Result 
    affinity_score = data.get("affinity_score", None)                 # Custom Affinity Score Result
    brochure_url = data.get("brochure_url", None)                     # Brochure URL
    product_website_url = data.get("product_website_url", None)       # Product Website URL
    num_of_campaign_ideas = data.get("num_of_campaign_ideas", 5)
    num_of_campaign_post_sets = data.get("num_of_campaign_post_sets", 5)
    num_of_hashtags = data.get("num_of_hashtags", 20)

    campaign_theme = data.get("campaign_theme", None)
    core_message_direction = data.get("core_message_direction", None)
    campaign_objective = data.get("campaign_objective", None)
    consumer_insight = data.get("consumer_insight", None)

    model_identifier = data.get("model_identifier", "azure-gpt-4o")
    campaign_idea_generation_agent = CampaignIdeaGeneratorAgent(
        source=source, 
        classified_cohort=classified_cohort, 
        affinity_score=affinity_score,
        brochure_url=brochure_url,
        product_website_url=product_website_url,
        model_identifier=model_identifier)
    result = campaign_idea_generation_agent.run(
        num_of_campaign_ideas = num_of_campaign_ideas,
        num_of_campaign_post_sets = num_of_campaign_post_sets, 
        num_of_hashtags = num_of_hashtags,
        campaign_theme = campaign_theme,
        core_message_direction = core_message_direction,
        campaign_objective = campaign_objective,
        consumer_insight = consumer_insight
        )
    return result


@gryd_orchestration_bp.route("/stream", methods=["POST"])
def gryd_stream_cohorts():
    data = request.get_json(force=True) or {}
    _params = {
        "brochure_url": data.get("brochure_url"),
        "product_website_url": data.get("product_website_url"),
        "model_identifier": data.get("model_identifier", "azure-gpt-4o"),
        "num_of_cohorts": data.get("num_of_cohorts", 30),
        "batch_size" : data.get("batch_size", 10)
    }

    def generate():
        for result in run_gryd_job("cohort_generation_agent_async", _params, stream=True):
                yield f"data: {json.dumps(result, default=str)}\n\n"
    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@gryd_orchestration_bp.route("/generate", methods=["POST"])
def gryd_get_cohorts():
    data = request.get_json(force=True) or {}
    _params = {
        "brochure_url": data.get("brochure_url"),
        "product_website_url": data.get("product_website_url"),
        "model_identifier": data.get("model_identifier", "azure-gpt-4o"),
        "num_of_cohorts": data.get("num_of_cohorts", 30),
        "batch_size" : data.get("batch_size", 10)
    }

    result = run_gryd_job("cohort_generation_agent", _params)
    return result


@gryd_orchestration_bp.route("/classify", methods=["POST"])
def gryd_classify():
    data = request.get_json(force=True) or {}
    _params = {
        "source": data.get("source"),
        "cohorts": data.get("cohorts"),
        "brochure_url": data.get("brochure_url"),
        "product_website_url": data.get("product_website_url"),
        "model_identifier": data.get("model_identifier", "azure-gpt-4o"),
    }
    result = run_gryd_job("cohort_classification_agent", _params)
    return result


@gryd_orchestration_bp.route("/affinity", methods=["POST"])
def gryd_affinity():
    data = request.get_json(force=True) or {}
    _params = {
        "interaction_json": data.get("interaction_json", None),
        "brochure_url": data.get("brochure_url", None),
        "product_website_url": data.get("product_website_url", None),
        "model_identifier": data.get("model_identifier", "azure-gpt-4o"),
        "domain": data.get("domain", None),
        "custom_affinity_dimensions": data.get("custom_affinity_dimensions", None)
    }
    result = run_gryd_job("affinity_agent", _params)
    return result


@gryd_orchestration_bp.route("/campaign_ideas", methods=["POST"])
def gryd_campaign_ideas():    
    data = request.get_json(force=True) or {}
    params_ = {
        "source": data.get("source", None),
        "classified_cohort": data.get("classified_cohort", None),
        "affinity_score": data.get("affinity_score", None),
        "brochure_url": data.get("brochure_url", None),
        "product_website_url": data.get("product_website_url", None),
        "model_identifier": data.get("model_identifier", "azure-gpt-4o"),
        "num_of_campaign_ideas": data.get("num_of_campaign_ideas", 5),
        "num_of_campaign_post_sets": data.get("num_of_campaign_post_sets", 5),
        "num_of_hashtags": data.get("num_of_hashtags", 20),
        "campaign_theme": data.get("campaign_theme", None),
        "core_message_direction": data.get("core_message_direction", None),
        "campaign_objective": data.get("campaign_objective", None),
        "consumer_insight": data.get("consumer_insight", None),
    }
    result = run_gryd_job("campaign_idea_generation_agent", params_)
    return result