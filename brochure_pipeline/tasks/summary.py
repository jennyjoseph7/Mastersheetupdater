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

def format_for_gryd_vector(llm_data: dict, doc_id_prefix: str, real_db_variants: list) -> list:
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
                    "information": entry.get('toon_text', '') # Using TOON text directly
                },
                "i2ce_headers": {"Content-Type": "application/json"}
            }
        }
    
    # 1. Models & Years
    if "vehicle_model" in llm_data:
        gryd_tasks.append(create_payload(llm_data["vehicle_model"], "Brand_Model", "general"))
    if "model_year" in llm_data:
        gryd_tasks.append(create_payload(llm_data["model_year"], "Brand_Model_Year", "year_spec"))
        
    # 2. Variants (Programmatic Expansion)
    for i, v in enumerate(llm_data.get("variants", [])):
        base_variant_name = v.get("variant_name", "").strip()
        matched_db_variants = [
            db_v for db_v in real_db_variants 
            if base_variant_name.lower() in str(db_v.get("variant_name", "")).lower()
        ]
        
        if not matched_db_variants:
            v_id = base_variant_name.replace(" ", "_").lower() if base_variant_name else f"var_{i}"
            gryd_tasks.append(create_payload(v, "Variant_Detail", f"variant_{v_id}"))
        else:
            for db_variant in matched_db_variants:
                v_clone = copy.deepcopy(v)
                specific_name = db_variant.get("variant_name")
                v_id = specific_name.replace(" ", "_").lower()
                # Update text for vector search
                if base_variant_name in v_clone["summary_text"]:
                    v_clone["summary_text"] = v_clone["summary_text"].replace(base_variant_name, specific_name)
                else:
                    v_clone["summary_text"] = f"{v_clone['summary_text']} {specific_name}"
                    
                gryd_tasks.append(create_payload(v_clone, "Variant_Detail", f"variant_{v_id}"))

    # 3. Categories & Features
    for i, f in enumerate(llm_data.get("feature_categories", [])):
        c_id = f.get("summary_text", f"cat_{i}").replace(" ", "_").lower()
        gryd_tasks.append(create_payload(f, "Feature_Category", f"feature_category_{c_id}"))
        
    for i, s in enumerate(llm_data.get("specific_features", [])):
        s_id = s.get("summary_text", f"spec_{i}").replace(" ", "_").lower()
        gryd_tasks.append(create_payload(s, "Specific_Feature_DeepDive", f"feature_deep_{s_id}"))

    return gryd_tasks

def update_autocrm_summaries(db_updates: dict, model_year_id: str):
    """
    Updates the feature_summary fields in vehicle_model, model_year, and variant models.
    Includes robust logging for tracing success and failures.
    """
    logger.info(f"🔄 Starting AutoCRM Database updates for Model Year ID: {model_year_id}")
    
    # 1. Update Model Year
    my_toon = db_updates.get("model_year", {}).get("toon_text")
    if my_toon and my_toon != "N/A":
        try:
            model_year_db = AutocrmModel('model_year')
            # Fetch to get parent vehicle_model_id for the next step
            current_my_record = model_year_db.get(id=model_year_id) 
            
            # Update the Model Year
            model_year_db.update(id=model_year_id, data={"feature_summary": my_toon})
            logger.info(f"✅ SUCCESSFULLY updated model_year [{model_year_id}]")
            
            # 2. Update Vehicle Model (Using the parent ID from Model Year)
            vm_id = current_my_record.get("data", {}).get("vehicle_model_id")
            vm_toon = db_updates.get("vehicle_model", {}).get("toon_text")
            
            if vm_id and vm_toon and vm_toon != "N/A":
                vehicle_model_db = AutocrmModel('vehicle_model')
                vehicle_model_db.update(id=vm_id, data={"feature_summary": vm_toon})
                logger.info(f"✅ SUCCESSFULLY updated vehicle_model [{vm_id}]")
            else:
                logger.warning(f"⚠️ SKIPPED vehicle_model update. Missing ID ({vm_id}) or TOON text empty.")
                
        except Exception as e:
            logger.error(f"❌ FAILED to update model_year or vehicle_model for {model_year_id}. Error: {e}")
    else:
        logger.warning(f"⚠️ SKIPPED model_year update. TOON text is empty for {model_year_id}")

    # 3. Update Variants
    variants_to_update = db_updates.get("variants", [])
    success_count, fail_count = 0, 0
    
    if variants_to_update:
        variant_db = AutocrmModel('variant')
        for v in variants_to_update:
            v_id = v.get("variant_id")
            v_toon = v.get("toon_text")
            v_name = v.get("variant_name", "Unknown")
            
            if v_id and v_toon and v_toon != "N/A":
                try:
                    variant_db.update(id=v_id, data={"feature_summary": v_toon})
                    logger.info(f"✅ SUCCESSFULLY updated variant [{v_name}] (ID: {v_id})")
                    success_count += 1
                except Exception as e:
                    logger.error(f"❌ FAILED to update variant [{v_name}] (ID: {v_id}). Error: {e}")
                    fail_count += 1
            else:
                logger.warning(f"⚠️ SKIPPED variant [{v_name}]. Missing ID or TOON text empty.")
                fail_count += 1
                
        logger.info(f"📊 Variant Update Summary: {success_count} Successful | {fail_count} Failed/Skipped")
    else:
        logger.info("ℹ️ No variants mapped for database update.")

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
    logger.info(f"🤖 [Worker] Generating TOON summaries for Model Year ID: {model_year_id}")
    
    agent = VectorIngestionAgent()
    llm_response = agent.run(brochure_text)
    
    if not llm_response: 
        logger.error("❌ Summaries failed to generate.")
        return {"status": "failed"}

    # Fetch DB variants to get their IDs
    real_db_variants = fetch_db_variants(model_year_id)
    doc_prefix = (model_year_id or str(uuid.uuid4())).replace(" ", "_").lower()

    # --- 1. BUILD AUTOCRM DB UPDATES ---
    db_updates = {
        "vehicle_model": {
            "toon_text": llm_response.get("vehicle_model", {}).get("toon_text", "")
        },
        "model_year": {
            "model_year_id": model_year_id,
            "toon_text": llm_response.get("model_year", {}).get("toon_text", "")
        },
        "variants": []
    }

    # Match LLM variants to DB variants to grab the variant_id
    for v in llm_response.get("variants", []):
        base_name = v.get("variant_name", "").strip().lower()
        for db_v in real_db_variants:
            if base_name in str(db_v.get("variant_name", "")).lower():
                db_updates["variants"].append({
                    "variant_id": db_v.get("variant_id", ""), 
                    "variant_name": db_v.get("variant_name", ""),
                    "toon_text": v.get("toon_text", "")
                })

    # --- 2. BUILD VECTOR TASKS ---
    gryd_tasks = format_for_gryd_vector(llm_response, doc_prefix, real_db_variants)
    
    # --- 3. POST TO AUTOCRM DB ---
    # -> THIS IS THE FIX: Actually call the function to run the DB updates! <-
    logger.info("Triggering direct AutoCRM Model updates...")
    update_autocrm_summaries(db_updates, model_year_id)
    
    logger.info(f"✅ [Worker] Finished DB updates. Generated {len(gryd_tasks)} vector tasks.")
    
    # Return ONLY the vector tasks to the frontend/terminal. 
    # The DB updates are already done!
    return {
        "status": "success", 
        "vector_tasks_payload": gryd_tasks
    }

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