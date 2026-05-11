import os
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from gryd_worker import gryd
from bp_utils import GRYD_SERVICE, get_logger

logger = get_logger(__name__)

from tasks.summary import run_summary_dispatcher, run_summary_worker, run_vector_ingestion
from tasks.variant_feature import process_brochure_chunk, run_brochure_orchestrator

gryd.SERVICE = GRYD_SERVICE 
gryd.set_queue_manager()


@gryd.is_a_task()
def brochure_worker_task(**kwargs):
    """Worker task for extracting brochure feature batches."""
    document_id = kwargs.get("document_id")
    features_chunk = kwargs.get("features_chunk")
    cached_text = kwargs.get("cached_text")
    job_id = kwargs.get("job_id")
    real_db_variants = kwargs.get("real_db_variants", [])
    car_name = kwargs.get("car_name", "Unknown_Car")
    
    return process_brochure_chunk(
        document_id, features_chunk, cached_text, job_id, real_db_variants, car_name
    )

@gryd.is_a_task()
def brochure_dispatcher_task(**kwargs):
    """Dispatcher task for managing the variant feature pipeline."""
    document_id = kwargs.get("document_id")
    job_id = kwargs.get("job_id")
    feature_limit = kwargs.get("feature_limit", None) 
    return run_brochure_orchestrator(document_id, job_id, feature_limit)


@gryd.is_a_task()
def summary_dispatcher_task(**kwargs):
    """Dispatcher task for managing summary generation."""
    document_id = kwargs.get("document_id") 
    job_id = kwargs.get("job_id")
    vehicle_model_id = kwargs.get("vehicle_model_id")
    model_year_id = kwargs.get("model_year_id")
    expected_variants = kwargs.get("expected_variants", [])
    
    return run_summary_dispatcher(document_id, job_id, vehicle_model_id, model_year_id, expected_variants)

@gryd.is_a_task()
def summary_worker_task(**kwargs):
    """Worker task that runs the LLM summarization."""
    brochure_text = kwargs.get("brochure_text") 
    vehicle_model_id = kwargs.get("vehicle_model_id")
    model_year_id = kwargs.get("model_year_id")
    expected_variants = kwargs.get("expected_variants", [])
    
    return run_summary_worker(brochure_text, vehicle_model_id, model_year_id, expected_variants)

@gryd.is_a_task()
def vector_ingestion_task(**kwargs):
    tasks_payload = kwargs.get("tasks_payload", [])
    
    if not tasks_payload:
        logger.error("❌ No tasks payload provided to vector_ingestion_task.")
        return {"status": "failed", "message": "Empty tasks_payload."}
        
    return run_vector_ingestion(tasks_payload)