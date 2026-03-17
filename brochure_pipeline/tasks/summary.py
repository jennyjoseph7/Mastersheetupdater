import os
import json
import uuid
import copy
import urllib.parse
from pathlib import Path
from bp_utils import get_logger
from gryd_worker import gryd
from agents.summary_agent import VectorIngestionAgent
from dotenv import load_dotenv
from config import AutocrmModel

load_dotenv()
logger = get_logger(__name__)


def fetch_db_variants(model_year_id: str) -> list:
    """Fetches real variants from the DB using the exact model year ID."""
    try:
        if not model_year_id:
            logger.warning("No model_year_id provided to fetch_db_variants.")
            return []
            
        variant_model = AutocrmModel('variant')
        variants = variant_model.list()
        
        variant_list = variants.get("data", []) if isinstance(variants, dict) else variants
        
        # Filter by model_year_id instead of vehicle_model_name
        return [v for v in variant_list if str(v.get("model_year_id", "")).lower() == model_year_id.lower()]
    except Exception as e:
        logger.error(f"Failed to fetch variants from DB for ID {model_year_id}: {e}")
    return []


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

def format_for_gryd_vector(vector_summaries: dict, doc_id_prefix: str, real_db_variants: list) -> list:
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
        
    # --- PROGRAMMATIC EXPANSION: VARIANTS ---
    for i, v in enumerate(vector_summaries.get("variants", [])):
        base_variant_name = v.get("structured_info", {}).get("Variant Name", "").strip()
        
        # Match with DB
        matched_db_variants = [
            db_v for db_v in real_db_variants 
            if base_variant_name.lower() in str(db_v.get("variant_name", "")).lower()
        ]
        
        if not matched_db_variants:
            # Fallback if no DB match
            v_id = base_variant_name.replace(" ", "_").lower() if base_variant_name else f"var_{i}"
            gryd_tasks.append(create_payload(v, "Variant_Detail", f"variant_{v_id}"))
        else:
            # Expand for every DB combination
            for db_variant in matched_db_variants:
                v_clone = copy.deepcopy(v)
                specific_name = db_variant.get("variant_name")
                v_id = specific_name.replace(" ", "_").lower()
                
                # Inject DB specific data
                v_clone["structured_info"]["Variant Name"] = specific_name
                v_clone["structured_info"]["Engine"] = db_variant.get("engine_type", "")
                v_clone["structured_info"]["Transmission"] = db_variant.get("transmission_type", "")
                v_clone["structured_info"]["Drivetrain"] = db_variant.get("drivetrain", "")
                
                # Update text for vector search
                if base_variant_name in v_clone["summary_text"]:
                    v_clone["summary_text"] = v_clone["summary_text"].replace(base_variant_name, specific_name)
                else:
                    v_clone["summary_text"] = f"{v_clone['summary_text']} {specific_name}"
                    
                gryd_tasks.append(create_payload(v_clone, "Variant_Detail", f"variant_{v_id}"))

    # Feature Categories (Unchanged)
    for i, f in enumerate(vector_summaries.get("feature_categories", [])):
        c_id = f.get("structured_info", {}).get("Category Name", f"cat_{i}").replace(" ", "_").lower()
        gryd_tasks.append(create_payload(f, "Feature_Category", f"feature_category_{c_id}"))
        
    # --- PROGRAMMATIC EXPANSION: SPECIFIC FEATURES ---
    for i, s in enumerate(vector_summaries.get("specific_features", [])):
        availability_str = str(s.get("structured_info", {}).get("Availability", "")).lower()
        
        # Parse the comma-separated bases from the LLM
        base_variants_in_avail = [x.strip() for x in availability_str.split(",")]
        is_standard = "all variants" in availability_str or "standard" in availability_str
        
        matched_db_variants = []
        for db_v in real_db_variants:
            db_v_name = str(db_v.get("variant_name", "")).lower()
            if is_standard or any(base in db_v_name for base in base_variants_in_avail if base):
                matched_db_variants.append(db_v)
                
        if not matched_db_variants:
            s_id = s.get("structured_info", {}).get("Feature Name", f"spec_{i}").replace(" ", "_").lower()
            gryd_tasks.append(create_payload(s, "Specific_Feature_DeepDive", f"feature_deep_{s_id}"))
        else:
            for db_variant in matched_db_variants:
                s_clone = copy.deepcopy(s)
                spec_var_name = db_variant.get("variant_name")
                feature_name = s_clone.get('structured_info', {}).get('Feature Name', f'spec_{i}')
                s_id = f"{feature_name}_{spec_var_name}".replace(" ", "_").lower()
                
                s_clone["summary_text"] = f"{s_clone['summary_text']} for {spec_var_name}"
                s_clone["structured_info"]["Applicable_Variant"] = spec_var_name
                
                gryd_tasks.append(create_payload(s_clone, "Specific_Feature_DeepDive", f"feature_deep_{s_id}"))

    return gryd_tasks

def run_summary_dispatcher(document_id: str, model_year_id: str):
    """
    Fetches the parsed text from API and yields a job to the worker for LLM summarization.
    """
    logger.info(f"🚀 Dispatching Summary | Doc: {document_id} | Model Year ID: {model_year_id}")
    brochure_text = fetch_brochure_text_from_api(document_id)
    
    if not brochure_text: 
        logger.error("❌ Failed to fetch brochure text from API.")
        return {"status": "failed"}

    worker_payload = [{
        "task": "summary_worker_task", 
        "service": "brochure-pipeline",
        "args": [],
        "kwargs": {
            "brochure_text": brochure_text, 
            "model_year_id": model_year_id
        }
    }]

    job_iterator = gryd.yield_results(worker_payload)
    results = [res for res in job_iterator]

    return {"status": "completed", "model_year_id": model_year_id, "results": results}

def run_summary_worker(brochure_text: str, model_year_id: str):
    """
    Calls Gemini to summarize the text structure, then expands variants programmatically.
    """
    logger.info(f"🤖 [Worker] Generating summaries for Model Year ID: {model_year_id}")
    
    agent = VectorIngestionAgent()
    vector_summaries = agent.run(brochure_text)
    
    if not vector_summaries: 
        logger.error("❌ Vector summaries failed to generate.")
        return {"status": "failed"}

    # Fetch DB variants using the ID
    logger.info(f"🔍 Fetching DB Variants for model_year_id: {model_year_id}...")
    real_db_variants = fetch_db_variants(model_year_id)

    # Use the model_year_id as the prefix for all vector IDs (much cleaner!)
    doc_prefix = (model_year_id or str(uuid.uuid4())).replace(" ", "_").lower()
    
    # Programmatic expansion
    gryd_tasks = format_for_gryd_vector(vector_summaries, doc_prefix, real_db_variants)
    
    print(f"\n--- Generated Vector Tasks Payload for {model_year_id} ---")
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