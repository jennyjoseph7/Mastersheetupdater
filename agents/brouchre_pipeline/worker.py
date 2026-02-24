import os
from gryd_worker import gryd
from bp_utils import GRYD_SERVICE, GRYD_CONFIG, get_logger

logger = get_logger(__name__)


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

from tasks.variant_feature import process_brochure_chunk, run_brochure_orchestrator

@gryd.is_a_task()
def brochure_worker_task(**kwargs):
    """Worker task for extracting brochure feature batches."""
    # Extract explicitly
    brochure_url = kwargs.get("brochure_url")
    features_chunk = kwargs.get("features_chunk")
    cached_text = kwargs.get("cached_text")
    job_id = kwargs.get("job_id")
    
    # Execute
    return process_brochure_chunk(brochure_url, features_chunk, cached_text, job_id)

@gryd.is_a_task()
def brochure_dispatcher_task(**kwargs):
    """Dispatcher task for managing the variant feature pipeline."""
    # Extract explicitly
    brochure_url = kwargs.get("brochure_url")
    job_id = kwargs.get("job_id")
    
    # Defaults to None if not provided in the trigger
    feature_limit = kwargs.get("feature_limit", None) 
    
    # Execute
    return run_brochure_orchestrator(brochure_url, job_id, feature_limit)


# ==========================================
# 3. SUMMARY TASKS
# ==========================================
from tasks.summary import run_summary_dispatcher, run_summary_worker, run_vector_ingestion

@gryd.is_a_task()
def summary_dispatcher_task(**kwargs):
    """Dispatcher task for managing summary generation."""
    # Extract explicitly
    brochure_url = kwargs.get("brochure_url")
    job_id = kwargs.get("job_id")
    
    # Execute
    return run_summary_dispatcher(brochure_url, job_id)

@gryd.is_a_task()
def summary_worker_task(**kwargs):
    """Worker task that runs the LLM summarization."""
    # Extract explicitly
    brochure_data = kwargs.get("brochure_data")
    job_id = kwargs.get("job_id")
    
    # Execute
    return run_summary_worker(brochure_data, job_id)

@gryd.is_a_task()
def vector_ingestion_task(**kwargs):
    """Task that pushes saved summaries to the vector DB."""
    # Extract explicitly
    job_id = kwargs.get("job_id")
    
    # Execute
    return run_vector_ingestion(job_id)


from tasks.table_updation import run_table_processor

@gryd.is_a_task()
def process_table_task(**kwargs):
    """Worker task for extracting tables from markdown."""
    # Extract explicitly
    chunk_id = kwargs.get("chunk_id")
    
    # Execute
    return run_table_processor(chunk_id)