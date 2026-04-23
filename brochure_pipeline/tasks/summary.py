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

def format_for_gryd_vector(llm_data: dict, doc_id_prefix: str) -> list:
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
                    "information": entry.get('toon_text', '') 
                },
                "i2ce_headers": {"Content-Type": "application/json"}
            }
        }
    
    # 1. Models & Years
    if "vehicle_model" in llm_data:
        gryd_tasks.append(create_payload(llm_data["vehicle_model"], "Brand_Model", "general"))
    if "model_year" in llm_data:
        gryd_tasks.append(create_payload(llm_data["model_year"], "Brand_Model_Year", "year_spec"))
        
    # 2. Variants (Directly from LLM output now)
    for i, v in enumerate(llm_data.get("variants", [])):
        v_id = v.get("variant_id", f"var_{i}").replace(" ", "_").lower()
        gryd_tasks.append(create_payload(v, "Variant_Detail", f"variant_{v_id}"))

    # 3. Categories & Features
    for i, f in enumerate(llm_data.get("feature_categories", [])):
        c_id = f.get("summary_text", f"cat_{i}").replace(" ", "_").lower()
        gryd_tasks.append(create_payload(f, "Feature_Category", f"feature_category_{c_id}"))
        
    for i, s in enumerate(llm_data.get("specific_features", [])):
        s_id = s.get("summary_text", f"spec_{i}").replace(" ", "_").lower()
        gryd_tasks.append(create_payload(s, "Specific_Feature_DeepDive", f"feature_deep_{s_id}"))

    return gryd_tasks

def update_autocrm_summaries(db_updates: dict, vehicle_model_id: str, model_year_id: str):
    """
    Updates the feature_summary fields in vehicle_model, model_year, and variant models.
    """
    logger.info(f"🔄 Starting AutoCRM Database updates for Model Year ID: {model_year_id}")
    
    # 1. Update Model Year
    my_toon = db_updates.get("model_year", {}).get("toon_text")
    if model_year_id and my_toon and my_toon != "N/A":
        try:
            model_year_db = AutocrmModel('model_year')
            model_year_db.update(id=model_year_id, data={"feature_summary": my_toon})
            logger.info(f"✅ SUCCESSFULLY updated model_year [{model_year_id}]")
        except Exception as e:
            logger.error(f"❌ FAILED to update model_year for {model_year_id}. Error: {e}")
    else:
        logger.warning(f"⚠️ SKIPPED model_year update. ID or TOON text is empty.")

    # 2. Update Vehicle Model
    vm_toon = db_updates.get("vehicle_model", {}).get("toon_text")
    if vehicle_model_id and vm_toon and vm_toon != "N/A":
        try:
            vehicle_model_db = AutocrmModel('vehicle_model')
            vehicle_model_db.update(id=vehicle_model_id, data={"feature_summary": vm_toon})
            logger.info(f"✅ SUCCESSFULLY updated vehicle_model [{vehicle_model_id}]")
        except Exception as e:
            logger.error(f"❌ FAILED to update vehicle_model for {vehicle_model_id}. Error: {e}")
    else:
        logger.warning(f"⚠️ SKIPPED vehicle_model update. Missing ID ({vehicle_model_id}) or TOON text empty.")

    # 3. Update Variants
    variants_to_update = db_updates.get("variants", [])
    success_count, fail_count = 0, 0
    
    if variants_to_update:
        variant_db = AutocrmModel('variant')
        for v in variants_to_update:
            v_id = v.get("variant_id")
            v_toon = v.get("toon_text")
            v_name = v.get("variant_name", "Unknown")
            
            # Skip if LLM returned UNKNOWN for ID
            if v_id and v_id != "UNKNOWN" and v_toon and v_toon != "N/A":
                try:
                    variant_db.update(id=v_id, data={"feature_summary": v_toon})
                    logger.info(f"✅ SUCCESSFULLY updated variant [{v_name}] (ID: {v_id})")
                    success_count += 1
                except Exception as e:
                    logger.error(f"❌ FAILED to update variant [{v_name}] (ID: {v_id}). Error: {e}")
                    fail_count += 1
            else:
                logger.warning(f"⚠️ SKIPPED variant [{v_name}]. Missing/UNKNOWN ID or TOON text empty.")
                fail_count += 1
                
        logger.info(f"📊 Variant Update Summary: {success_count} Successful | {fail_count} Failed/Skipped")
    else:
        logger.info("ℹ️ No variants mapped for database update.")

def run_summary_dispatcher(document_id: str, job_id: str, vehicle_model_id: str, model_year_id: str, expected_variants: list):
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
            "vehicle_model_id": vehicle_model_id,
            "model_year_id": model_year_id,
            "expected_variants": expected_variants
        }
    }]

    job_iterator = gryd.yield_results(worker_payload)
    results = [res for res in job_iterator]

    return {"status": "completed", "model_year_id": model_year_id, "results": results}

def run_summary_worker(brochure_text: str, vehicle_model_id: str, model_year_id: str, expected_variants: list):
    logger.info(f"🤖 [Worker] Generating TOON summaries for Model Year ID: {model_year_id}")
    
    agent = VectorIngestionAgent()
    llm_response = agent.run(brochure_text, expected_variants)
    
    if not llm_response: 
        logger.error("❌ Summaries failed to generate.")
        return {"status": "failed"}

    doc_prefix = (model_year_id or str(uuid.uuid4())).replace(" ", "_").lower()

    # --- 1. BUILD AUTOCRM DB UPDATES ---
    db_updates = {
        "vehicle_model": {
            "toon_text": llm_response.get("vehicle_model", {}).get("toon_text", "")
        },
        "model_year": {
            "toon_text": llm_response.get("model_year", {}).get("toon_text", "")
        },
        "variants": []
    }

    # Extract variant mapping directly from LLM response
    for v in llm_response.get("variants", []):
        db_updates["variants"].append({
            "variant_id": v.get("variant_id", "UNKNOWN"), 
            "variant_name": v.get("variant_name", "Unknown"),
            "toon_text": v.get("toon_text", "")
        })

    # --- 2. BUILD VECTOR TASKS ---
    gryd_tasks = format_for_gryd_vector(llm_response, doc_prefix)
    
    # --- 3. POST TO AUTOCRM DB ---
    logger.info("Triggering direct AutoCRM Model updates...")
    update_autocrm_summaries(db_updates, vehicle_model_id, model_year_id)
    
    logger.info(f"✅ [Worker] Finished DB updates. Generated {len(gryd_tasks)} vector tasks.")
    
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