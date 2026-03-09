import sys, os
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from flask import Blueprint, Response, request, stream_with_context
from flask import request, jsonify
from werkzeug.utils import secure_filename
from io import StringIO
import json
from gryd_worker import gryd, gryd_helpers
from cohorts_new.utils.utility import *
from cohorts_new.utils.common_utils import *
from typing import *
import pandas as pd
import re
from copy import deepcopy

cohort_bp = Blueprint(**{"name": "cohort_bp", "import_name" : __name__ , "url_prefix": "/cohorts"})
gryd_orchestration_bp = Blueprint(**{"name": "gryd_orchestration_bp", "import_name" : __name__ , "url_prefix": "/cohorts/gryd"})
logger = get_logger(__name__)

def setup_gryd():
    gryd.SERVICE = GRYD_SERVICE_NAME
    gryd.set_queue_manager(config = GRYD_CONFIG)
    # environment = os.getenv("ENVIRONMENT", "-local")
    # if not environment.startswith("-"):
    #     environment = f"-{environment}"
    # gryd.ENVIRONMENT = environment

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
        from ..agents.cohort_generation_agent import ProductCohortGenerationAgent
        agent = ProductCohortGenerationAgent(**_params)

        for event in agent.run_with_events(batch_size=_batch_size):
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@cohort_bp.route("/generate", methods=["POST"])
def get_cohorts():
    from ..agents.cohort_generation_agent import ProductCohortGenerationAgent
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
    from ..agents.cohort_classification_agent import CohortClassificationAgent
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
    from ..agents.affinity_agent import AffinityEngineAgent
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

@cohort_bp.route("/embedding_affinity", methods=["POST"])
def embedding_affinity():
    from ..agents.affinity_agent import EmbeddingAffinityEngine
    data = request.get_json(force=True) or {}
    _params = {
        "interaction_json": data.get("interaction_json", None),
        "custom_affinity_dimensions": data.get("custom_affinity_dimensions", None)
    }
    affinity_score_agent = EmbeddingAffinityEngine(**_params)
    result = affinity_score_agent.calculate_affinity()
    return result

@cohort_bp.route("/campaign_ideas", methods=["POST"])
def campaign_ideas():
    from ..agents.campaign_idea_generation_agent import CampaignIdeaGeneratorAgent
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

@gryd_orchestration_bp.route("/embedding_affinity", methods=["POST"])
def gryd_embedding_affinity():
    data = request.get_json(force=True) or {}
    _params = {
        "interaction_json": data.get("interaction_json", None),
        "custom_affinity_dimensions": data.get("custom_affinity_dimensions", None)
    }
    result = run_gryd_job("embedding_affinity_score_agent", _params)
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



def standardize_cohorts(cohorts : Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]):
    """Standardizes cohort structure.
    Accepts:
        - list[dict]
        - dict with key "cohorts"
    """
    def snake_case(text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r"[^\w\s-]", "", text)   
        text = re.sub(r"[\s\-]+", "_", text) 
        return text
    if not isinstance(cohorts, (list, dict)):
        raise ValueError("cohorts must be a list of dicts or dict with 'cohorts' key")
    if isinstance(cohorts, dict):
        if "cohorts" not in cohorts:
            raise ValueError("dict input must contain 'cohorts' key")
        cohorts = cohorts["cohorts"]
    if not isinstance(cohorts, list):
        raise ValueError("'cohorts' must be a list")
    standardized = []
    d_cohorts = deepcopy(cohorts)
    for cohort in d_cohorts:
        if not isinstance(cohort, dict):
            raise ValueError("Each cohort must be a dictionary")
        name = cohort.get("name") or cohort.get("cohort_name")
        if not name:
            raise ValueError("Each cohort must have 'name' or 'cohort_name'")
        cohort["cohort_name"] = name.capitalize()
        if not cohort.get("cohort_id"):
            cohort["cohort_id"] = snake_case(name)
        standardized.append(cohort)
        if not "campaign_id" in cohort:
            raise ValueError("Each cohort must have 'campaign_id'")
    
    logger.info(f"Standardized cohorts: {json.dumps(standardized, indent=4,default=str)}")
    return standardized

@cohort_bp.route("/cohorts_assignment", methods=["POST"])
def cohorts_assignment():
    """
    Randomly populate lead data with provided cohorts.
    """
    from agents.cohort_classification_agent import random_assign_users

    try:
        if "lead_file" not in request.files:
            return jsonify({"error": "lead_file missing"}), 400
        if "cohorts" not in request.files:
            return jsonify({"error": "cohorts file required"}), 400

        lead_file = request.files["lead_file"]
        cohorts_file = request.files["cohorts"]
        seed = int(request.form.get("seed", 42))
        weights = request.form.get("weights", None)
        if weights is not None:
            logger.info(f"Weights: {weights}")
            logger.info(f"type of weights: {type(weights)}")
            weights = [round(float(w), 2) for w in json.loads(weights)]

        cohorts = json.load(cohorts_file)
        cohorts = standardize_cohorts(cohorts)
        stream = StringIO(lead_file.stream.read().decode("utf-8"))
        df = pd.read_csv(stream)
        users = df.to_dict(orient="records")
        assigned_users = random_assign_users(users=users, cohorts=cohorts, seed=seed, weights=weights)
        result_df = pd.DataFrame(assigned_users)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            temp_path = tmp.name
            result_df.to_csv(temp_path, index=False)
        logger.info(f"Temporary CSV created: {temp_path}")
        csv_url = func_gryd_file_system(local_path=temp_path, media_type="document", logger=logger)
        os.remove(temp_path)
        if not csv_url:
            return jsonify({"error": "Upload failed"}), 500
        return jsonify({
            "message": "Cohorts assigned successfully",
            "total_customers": len(assigned_users),
            "csv_url": csv_url
        })

    except Exception as e:
        logger.exception("Cohort assignment failed \n\n")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500