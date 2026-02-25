import os
import json
import uuid
import urllib.parse
from pathlib import Path
from bp_utils import get_logger
from gryd_worker import gryd
from agents.summary_agent import VectorIngestionAgent

# Import utilities
try:
    from agents.main import download_file
    from file_loader.gemini_loader import process_brochure_to_structure
except ImportError:
    download_file = None
    process_brochure_to_structure = None

logger = get_logger(__name__)


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent 
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "summary"
TEMP_DIR = PROJECT_ROOT / "temp_files"
MARKER_OUTPUT_DIR = PROJECT_ROOT / "marker_brochure_output"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(MARKER_OUTPUT_DIR, exist_ok=True)


def prepare_brochure_json(brochure_url: str):
    parsed_url = urllib.parse.urlparse(brochure_url)
    base_name = os.path.splitext(os.path.basename(parsed_url.path))[0]
    cache_path = MARKER_OUTPUT_DIR / f"{base_name}.json"

    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f: 
                return json.load(f)
        except Exception as e: 
            logger.warning(f"Cache read error: {e}")

    local_pdf_path = None
    try:
        if not download_file: 
            return None
            
        local_pdf_path = download_file(brochure_url, TEMP_DIR)
        
        if process_brochure_to_structure:
            raw = process_brochure_to_structure(str(local_pdf_path))
            data = json.loads(raw) if isinstance(raw, str) else raw
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return data
    except Exception as e:
        logger.error(f"Error preparing brochure JSON: {e}")
        return None
    finally:
        if local_pdf_path and os.path.exists(local_pdf_path): 
            os.remove(local_pdf_path)

def format_for_gryd_vector(vector_summaries: dict, doc_id_prefix: str) -> list:
    gryd_tasks = []
    
    def create_payload(entry, level, suffix):
        return {
            "service": "vector_document",
            "function_name": "update_vector",
            "kwargs": {
                "texts": entry.get('summary_text', ''),
                "pipeline": "RAG",
                "conversation_id": "autocrm_ingestion",
                "metadata": {
                    "document_id": f"{doc_id_prefix}_{suffix}",
                    "level": level,
                    "information": entry.get('structured_info', {})
                },
                "i2ce_headers": {"Content-Type": "application/json"}
            }
        }
    
 
    if "brand_model" in vector_summaries:
        gryd_tasks.append(create_payload(vector_summaries["brand_model"], "Brand_Model", "general"))
        
    if "brand_model_year" in vector_summaries:
        gryd_tasks.append(create_payload(vector_summaries["brand_model_year"], "Brand_Model_Year", "year_spec"))
        
    for i, v in enumerate(vector_summaries.get("variants", [])):
        v_id = v.get("structured_info", {}).get("Variant Name", f"var_{i}").replace(" ", "_").lower()
        gryd_tasks.append(create_payload(v, "Variant_Detail", f"variant_{v_id}"))
        
    for i, f in enumerate(vector_summaries.get("feature_categories", [])):
        c_id = f.get("structured_info", {}).get("Category Name", f"cat_{i}").replace(" ", "_").lower()
        gryd_tasks.append(create_payload(f, "Feature_Category", f"feature_category_{c_id}"))
        
    for i, s in enumerate(vector_summaries.get("specific_features", [])):
        s_id = s.get("structured_info", {}).get("Feature Name", f"spec_{i}").replace(" ", "_").lower()
        gryd_tasks.append(create_payload(s, "Specific_Feature_DeepDive", f"feature_deep_{s_id}"))

    return gryd_tasks




def run_summary_dispatcher(brochure_url: str, job_id: str):
    """
    Downloads/parses the PDF and yields a job to the worker for LLM summarization.
    """
    logger.info(f"🚀 Dispatching Summary Job: {job_id}")
    brochure_data = prepare_brochure_json(brochure_url)
    
    if not brochure_data: 
        logger.error("❌ Failed to parse brochure data.")
        return {"status": "failed"}

    # Dispatch Worker
    worker_payload = [{
        "task": "summary_worker_task", 
        "service": "brochure-pipeline",
        "args": [],
        "kwargs": {"brochure_data": brochure_data, "job_id": job_id}
    }]

    job_iterator = gryd.yield_results(worker_payload)
    results = [res for res in job_iterator]

    return {"status": "completed", "job_id": job_id, "results": results}


def run_summary_worker(brochure_data: dict, job_id: str):
    """
    Calls Gemini to summarize the JSON structure and saves the formatted payload to disk.
    """
    logger.info(f"🤖 [Worker] Generating summaries for Job: {job_id}")
    
    agent = VectorIngestionAgent()
    vector_summaries = agent.run(brochure_data)
    
    if not vector_summaries: 
        logger.error("❌ Vector summaries failed to generate.")
        return {"status": "failed"}

    model_name = brochure_data.get('model', job_id).replace(" ", "_").lower()
    gryd_tasks = format_for_gryd_vector(vector_summaries, model_name)
    
    output_path = OUTPUT_DIR / f"summary_{job_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(gryd_tasks, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ [Worker] Saved {len(gryd_tasks)} tasks to {output_path}")
    logger.info("ℹ️  NOTE: Vector ingestion was NOT triggered automatically.")
    
    return {"status": "success", "file_saved": str(output_path)}


def run_vector_ingestion(job_id: str):
    """
    Reads the previously generated summary tasks JSON and fires off vector upload commands.
    """
    input_file = OUTPUT_DIR / f"summary_{job_id}.json"
    
    if not input_file.exists():
        logger.error(f"❌ File not found: {input_file}")
        return {"status": "failed", "message": "Summary file not found. Run summary dispatcher first."}

    logger.info(f"📂 Loading tasks from: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        tasks_payload = json.load(f)

    successful, failed = 0, 0
    logger.info(f"🚀 Starting ingestion of {len(tasks_payload)} items...")

    for item in tasks_payload:
        try:
            gryd.create_async_task(
                service=item["service"],
                function_name=item["function_name"],
                kwargs=item["kwargs"]
            )
            successful += 1
        except Exception as e:
            failed += 1
            logger.error(f"❌ Failed to ingest item: {e}")

    return {"status": "completed", "sent": successful, "failed": failed}