import os
import json
import uuid
import urllib.parse
from pathlib import Path
import requests
from bp_utils import get_logger
from gryd_worker import gryd
from agents.summary_agent import VectorIngestionAgent
from dotenv import load_dotenv

load_dotenv()
logger = get_logger(__name__)

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent 
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "summary"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# API CONFIGURATION & HEADERS

BASE_URL = os.getenv("GRYD_BASE_URL", "https://autobot-webapp-dev.gryd.in")


HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "X-GRYD-ENTERPRISE-ID": os.getenv("GRYD_ENTERPRISE_ID"),
    "X-GRYD-ROLE": os.getenv("GRYD_ROLE"),
    "X-GRYD-SESSION-ID": os.getenv("GRYD_SESSION_ID"),
    "X-GRYD-TOKEN": os.getenv("GRYD_TOKEN"),
}

def fetch_brochure_text_from_api(document_id: str) -> str:
    """Fetches extracted chunks from chunk_saver API and concatenates them."""
    url = f"{BASE_URL}/gryd/db/objects/chunk_saver?document_id={document_id}&page_size=1000"
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        response_json = response.json()
        
        
        chunks = response_json.get("data", [])
        
        extracted_text = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                
                text = chunk.get("text_content", "")
                if text:
                    extracted_text.append(str(text))
                    
     
        return "\n\n".join(extracted_text)
    except Exception as e:
        logger.error(f"Failed to fetch brochure text from chunk_saver API for {document_id}: {e}")
        return ""

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

def run_summary_dispatcher(document_id: str, job_id: str):
    """
    Fetches the parsed text from API and yields a job to the worker for LLM summarization.
    """
    logger.info(f"🚀 Dispatching Summary Job: {job_id} for Document: {document_id}")
    brochure_text = fetch_brochure_text_from_api(document_id)
    
    if not brochure_text: 
        logger.error("❌ Failed to fetch brochure text from API.")
        return {"status": "failed"}

    worker_payload = [{
        "task": "summary_worker_task", 
        "service": "brochure-pipeline",
        "args": [],
        "kwargs": {"brochure_text": brochure_text, "job_id": job_id}
    }]

    job_iterator = gryd.yield_results(worker_payload)
    results = [res for res in job_iterator]

    return {"status": "completed", "job_id": job_id, "results": results}

def run_summary_worker(brochure_text: str, job_id: str):
    """
    Calls Gemini to summarize the text structure and saves the formatted payload to disk.
    """
    logger.info(f"🤖 [Worker] Generating summaries for Job: {job_id}")
    
    agent = VectorIngestionAgent()
    
    
    vector_summaries = agent.run(brochure_text)
    
    if not vector_summaries: 
        logger.error("❌ Vector summaries failed to generate.")
        return {"status": "failed"}

   
    model_name = (job_id or str(uuid.uuid4())).replace(" ", "_").lower()
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