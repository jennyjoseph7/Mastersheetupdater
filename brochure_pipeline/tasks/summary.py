import os
import json
import uuid
import urllib.parse
from pathlib import Path
from bp_utils import get_logger
from gryd_worker import gryd
from agents.summary_agent import VectorIngestionAgent
from dotenv import load_dotenv
from config import AutocrmModel

load_dotenv()
logger = get_logger(__name__)




def fetch_brochure_text_from_api(document_id: str) -> str:
    """Fetches extracted chunks from chunk_saver model and concatenates them."""
    try:
        chunk_saver_model = AutocrmModel('chunk_saver')
        chunks = chunk_saver_model.list(document_id=document_id, page_size=1000)
        
        extracted_text = []
        chunk_list = chunks.get("data", []) if isinstance(chunks, dict) else chunks
        
        for chunk in chunk_list:
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
    Calls Gemini to summarize the text structure, prints it, and returns the payload.
    """
    logger.info(f"🤖 [Worker] Generating summaries for Job: {job_id}")
    
    agent = VectorIngestionAgent()
    vector_summaries = agent.run(brochure_text)
    
    if not vector_summaries: 
        logger.error("❌ Vector summaries failed to generate.")
        return {"status": "failed"}

    model_name = (job_id or str(uuid.uuid4())).replace(" ", "_").lower()
    gryd_tasks = format_for_gryd_vector(vector_summaries, model_name)
    
    
    print(f"\n--- Generated Vector Tasks Payload for {job_id} ---")
    print(json.dumps(gryd_tasks, indent=2, ensure_ascii=False))
    print("---------------------------------------------------\n")
    
    logger.info(f"✅ [Worker] Generated {len(gryd_tasks)} tasks.")
   
    
    
    return {"status": "success", "tasks_payload": gryd_tasks}

def run_vector_ingestion(tasks_payload: list):
    """
    Takes the generated tasks payload directly and fires off vector upload commands.
    """
    if not tasks_payload:
        logger.error("❌ No tasks payload provided.")
        return {"status": "failed", "message": "Empty tasks_payload."}

    successful, failed = 0, 0
    logger.info(f"🚀 Starting ingestion of {len(tasks_payload)} items...")

    for item in tasks_payload:
        try:
            gryd.create_async_task(
                service=item.get("service", "vector_document"),
                function_name=item.get("function_name", "update_vector"),
                kwargs=item.get("kwargs", {})
            )
            successful += 1
        except Exception as e:
            failed += 1
            logger.error(f"❌ Failed to ingest item: {e}")

    return {"status": "completed", "sent": successful, "failed": failed}