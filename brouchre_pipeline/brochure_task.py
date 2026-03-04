import os
from gryd_worker import gryd
from bp_utils import GRYD_SERVICE, GRYD_CONFIG, get_logger

logger = get_logger(__name__)

from tasks.variant_feature import process_brochure_chunk, run_brochure_orchestrator
from tasks.summary import run_summary_dispatcher, run_summary_worker, run_vector_ingestion
from tasks.table_updation import run_table_processor


def setup_environment(environment: str = "-local"):
    if environment is None:
        environment = "-local"
    if not environment.startswith("-"):
        environment = f"-{environment}"
    gryd.ENVIRONMENT = environment
    logger.info(f"Environment set to '{environment}'")

GRYD_ENVIRONMENT = os.environ.get("ENVIRONMENT")
setup_environment(GRYD_ENVIRONMENT)

gryd.SERVICE = GRYD_SERVICE 
gryd.set_queue_manager(config=GRYD_CONFIG)


@gryd.is_a_task()
def brochure_worker_task(**kwargs):
    """Worker task for extracting brochure feature batches."""
    document_id = kwargs.get("document_id")
    features_chunk = kwargs.get("features_chunk")
    cached_text = kwargs.get("cached_text")
    job_id = kwargs.get("job_id")
    real_db_variants = kwargs.get("real_db_variants", []) # New!
    car_name = kwargs.get("car_name", "Unknown_Car")      # New!
    
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
    return run_summary_dispatcher(document_id, job_id)

@gryd.is_a_task()
def summary_worker_task(**kwargs):
    """Worker task that runs the LLM summarization."""
    brochure_text = kwargs.get("brochure_text") 
    job_id = kwargs.get("job_id")
    return run_summary_worker(brochure_text, job_id)

@gryd.is_a_task()
def vector_ingestion_task(**kwargs):
    """Task that pushes saved summaries to the vector DB."""
    job_id = kwargs.get("job_id")
    return run_vector_ingestion(job_id)


@gryd.is_a_task()
def process_table_task(**kwargs):
    """Worker task for extracting tables from markdown."""
    chunk_id = kwargs.get("chunk_id")
    return run_table_processor(chunk_id)