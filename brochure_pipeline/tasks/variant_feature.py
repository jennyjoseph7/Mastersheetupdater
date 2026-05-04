import os
import sys
import json
import uuid
import time
import pandas as pd

import concurrent.futures
from pathlib import Path
from filelock import FileLock
from gryd_worker import gryd
from bp_utils import get_logger
import re
from dotenv import load_dotenv

from brochure_pipeline.agents.variant_feature_agent import (
    ConverterAgent, 
    MasterVariantAgent, 
    ValidationAgent, 
    generate_bulk_questions
)
from brochure_pipeline.agents.postProcessing import process_batch_extraction, finalize_results_json
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(dirname(abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from config import AutocrmModel

load_dotenv()
logger = get_logger(__name__)





# PATHS & CONSTANTS

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent 
OUTPUT_DIR = PROJECT_ROOT / "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MAX_FINAL_RETRY = 5
CHUNK_SIZE = 3
MAX_CORRECTION_ATTEMPTS = 3
MAX_RETRIES = 5
RETRY_DELAY = 10


# DB & API HELPER FUNCTIONS

def fetch_brochure_text_from_api(document_id: str) -> str:
    """Fetches extracted chunks using AutocrmModel and concatenates them."""
    try:
        chunk_saver_model = AutocrmModel('chunk_saver')
        # Assuming .list() returns the data list directly based on your config.py
        chunks = chunk_saver_model.list(document_id=document_id, page_size=1000)
        
        extracted_text = []
        # Handle both dict responses (if wrapped in 'data') or direct lists
        chunk_list = chunks.get("data", []) if isinstance(chunks, dict) else chunks
        
        for chunk in chunk_list:
            if isinstance(chunk, dict):
                text = chunk.get("text_content", "")
                if text:
                    extracted_text.append(str(text))
                    
        return "\n\n".join(extracted_text)
    except Exception as e:
        logger.error(f"Failed to fetch brochure data from chunk_saver API for {document_id}: {e}")
        return ""

def generate_feature_id(entry):
    fields = [entry.get("feature_category"), entry.get("feature_name"), entry.get("value_type"), entry.get("unit")]
    valid_parts = [str(f).strip() for f in fields if f is not None and str(f).strip() != ""]
    return re.sub(r'[^a-z0-9]+', '-', "-".join(valid_parts).lower()).strip('-')

def fetch_db_variants(car_name: str) -> list:
    try:
        variant_model = AutocrmModel('variant')
        variants = variant_model.list()
        
        # Handle dict wrapping just in case
        variant_list = variants.get("data", []) if isinstance(variants, dict) else variants
        
        return [v for v in variant_list if str(v.get("vehicle_model_name", "")).lower() == car_name.lower()]
    except Exception as e:
        logger.error(f"Failed to fetch variants from DB: {e}")
    return []

def stream_upload_chunk(expanded_entries: list, document_id: str): 
    if not expanded_entries: return
    
    variant_feature_model = AutocrmModel('variant_feature')
    success_count = 0
    
    for entry in expanded_entries:
        if not entry.get("variant_id"):
            continue

        payload = {
            "variant_id": entry.get("variant_id"),
            "feature_id": generate_feature_id(entry),
            "vehicle_model_name": entry.get("vehicle_model_name"),
            "variant_name": entry.get("variant_name"),
            "engine_type": entry.get("engine_type", ""),
            "transmission_type": entry.get("transmission_type", ""),
            "drivetrain": entry.get("drivetrain", ""),
            "feature_name": entry.get("feature_name"),
            "feature_category": entry.get("feature_category"),
            "value_type": entry.get("value_type"),
            "unit": entry.get("unit"),
            "feature_value": entry.get("feature_value"),
            "source_reference": entry.get("source_reference"),
            "source_path": document_id, 
            "confidence_score": str(entry.get("confidence_score", 0.0))
        }
        
        try:
            variant_feature_model.post(payload)
            success_count += 1
        except Exception as e:
            logger.error(f"Streaming Upload Error: {e}")
        time.sleep(0.05) 
            
    logger.info(f"🚀 [Streaming Upload] Successfully posted {success_count} expanded features to DB.")

def is_model_not_found_error(e: Exception) -> bool:
    msg = str(e).lower()
    return "no model found" in msg or "model_identifier" in msg

def execute_with_retry(func, *args, **kwargs):
    last_exception = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            last_exception = e
            if "ratelimit" in error_str or "429" in error_str:
                wait_time = RETRY_DELAY * attempt + 10
                logger.warning(f"⚠️ Rate Limit (429). Cooldown {wait_time}s... Retry {attempt}/{MAX_RETRIES}")
                time.sleep(wait_time)
                continue
            if "connection timed out" in error_str or "operationalerror" in error_str:
                logger.warning(f"Network/DB Error. Retrying ({attempt}/{MAX_RETRIES}) in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            raise e
    raise last_exception

def cleanup_stale_locks(directory: Path):
    if not directory.exists(): return
    for lock_file in directory.glob("*.lock"):
        try: os.remove(lock_file)
        except Exception: pass

def flush_output(path: Path, data):
    for attempt in range(3):
        try:
            lock = FileLock(str(path) + ".lock", timeout=30)
            with lock:
                tmp_path = path.with_suffix(".tmp")
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, path)
                logger.info(f"✅ SUCCESSFULLY WROTE {len(data)} entries to {path.name}")
                return True
        except Exception as e:
            if attempt < 2: time.sleep(1)
            else: logger.error(f"❌ CRITICAL: Failed to write {path}: {e}")
    return False

def safe_read_json(path: Path):
    for attempt in range(3):
        try:
            lock = FileLock(str(path) + ".lock", timeout=30)
            with lock:
                if not path.exists(): return []
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    return json.loads(content) if content else []
        except Exception as e:
            if attempt < 2: time.sleep(1)
            else: return []
    return []

def harvest_and_merge(job_id, output_path):
    partials_dir = OUTPUT_DIR / "partials" / str(job_id)
    if not partials_dir.exists(): return
    partial_files = list(partials_dir.glob("*.json"))
    if not partial_files: return

    current_data = safe_read_json(output_path)
    existing_keys = set()
    for item in current_data:
        entry = item.get("entry", {})
        fname = entry.get("feature_name")
        variant = entry.get("variant") or entry.get("variant_name")
        if fname and variant:
            existing_keys.add((fname.strip(), variant.strip()))

    merged_items = []
    for p_file in partial_files:
        try:
            with open(p_file, "r", encoding="utf-8") as f:
                chunk_data = json.load(f)
            structured = chunk_data.get("structured", [])
            validation = chunk_data.get("validation", [])
            for i, entry in enumerate(structured):
                fname = entry.get("feature_name")
                variant = entry.get("variant")
                if fname and variant:
                    key = (fname.strip(), variant.strip())
                    if key in existing_keys: continue
                    existing_keys.add(key)
                
                merged_items.append({
                    "entry": entry,
                    "final_validation_report": validation[i].get("final_validation_report") if i < len(validation) else None
                })
            os.remove(p_file)
        except Exception as e:
            logger.error(f"⚠️ Failed to harvest {p_file.name}: {e}")

    if merged_items:
        current_data.extend(merged_items)
        flush_output(output_path, current_data)

def save_chunk_locally(data, job_id):
    try:
        chunk_id = str(uuid.uuid4())[:8]
        save_dir = OUTPUT_DIR / "partials" / str(job_id)
        os.makedirs(save_dir, exist_ok=True)
        save_path = save_dir / f"worker_chunk_{chunk_id}.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 [Worker] Physically saved output to: {save_path}")
        return str(save_path)
    except Exception as e:
        logger.error(f"❌ [Worker] Failed to save local chunk: {e}")
        return None


# PIPELINE LOGIC

def prepare_brochure_data(document_id):
    brochure_text = fetch_brochure_text_from_api(document_id)
    if not brochure_text: return None
    try:
        agent = MasterVariantAgent()
        car_name = agent.identify_car_model(brochure_text)
        variants = agent.run(brochure_text, car_name=car_name)
        return {"text": brochure_text, "variants": variants, "car_name": car_name} # Added car_name
    except Exception as e:
        logger.error(f"Error identifying variants: {e}")
        return None
    


def expand_to_db_variants(entry, real_db_variants):
    """Maps a single extracted brochure variant to multiple specific DB variants."""
    expanded_entries = []
    base_variant = str(entry.get("variant", entry.get("variant_name", ""))).strip().lower()

    matched_db_variants = [
        db_v for db_v in real_db_variants 
        if base_variant in str(db_v.get("variant_name", "")).lower()
    ]
   
    if not matched_db_variants:
        return [entry]
    
    for db_variant in matched_db_variants:
        new_entry = dict(entry) # Deep copy
        new_entry["variant_name"] = db_variant.get("variant_name")
        new_entry["variant_id"] = db_variant.get("variant_id")
        new_entry["engine_type"] = db_variant.get("engine_type", "")
        new_entry["transmission_type"] = db_variant.get("transmission_type", "")
        new_entry["drivetrain"] = db_variant.get("drivetrain", "")
        new_entry["vehicle_model_name"] = db_variant.get("vehicle_model_name", "")
        expanded_entries.append(new_entry)

    return expanded_entries

def process_single_feature(row_data, car_name, brochure_text, document_id, master_variants, converter_agent, validation_agent, real_db_variants):
    idx, row = row_data
    feature_info = row.to_dict()
    feature_name = feature_info.get("feature_name")
    if not feature_name: return [], [], []

    feature_desc = feature_info.get("feature_description", "")
    feature_alias = feature_info.get("aliases", "")
    value_type = feature_info.get("value_type", "Category")
    
    max_retries = 3   
    attempt_count = 0
    success = False

    local_structured, local_validation, local_raw = [], [], []
    time.sleep(2) 

    while attempt_count < max_retries and not success:
        try:
            questions_text = generate_bulk_questions(
                car_name, feature_name, master_variants, value_type, 
                description=feature_desc, alias=feature_alias
            )
            extracted_data_list = execute_with_retry(converter_agent.run, questions_text, value_type, brochure_text)
            
            if isinstance(extracted_data_list, list): local_raw.extend(extracted_data_list)
            else: local_raw.append(extracted_data_list)

            enriched_entries = process_batch_extraction(extracted_data_list, feature_info, car_name, document_id)
            
            for entry in enriched_entries:
                # ... [Validation logic remains exactly the same as your current code until the break] ...
                attempts = 0
                status = "Pending"
                validation_output = {}

                while attempts < MAX_CORRECTION_ATTEMPTS:
                    validation_report = execute_with_retry(validation_agent.run, brochure_text, entry)
                    validation_output = validation_report.get("validation_output", {})
                    status = validation_output.get("status")
                    reasoning = str(validation_output.get("reasoning", "")).lower()

                    if status == "Value Mismatch":
                        extracted_val = entry.get("feature_value") 
                        if (extracted_val is True) and ("yes" in reasoning) and (("contradict" in reasoning) or ("mismatch" in reasoning)):
                            status = "Validated" 
                            validation_output["status"] = "Validated"

                    if status == "Validated": break 
                    attempts += 1
                    
                    if status == "Value Mismatch":
                        correct_val = validation_output.get("ground_truth_value")
                        if correct_val is not None:
                            entry["feature_value"] = correct_val
                            entry["reconciliation_attempts"] = attempts
                            status = "Validated"
                            break
                        if str(entry.get("value_type", "")).lower() == "boolean":
                            entry["feature_value"] = False
                            entry["reconciliation_attempts"] = attempts
                            status = "Validated"
                            break
                            
                    if status in ["Invalidated", "Not Found"]:
                        if "boolean" in str(value_type).lower(): entry["feature_value"] = False
                        else: entry["feature_value"] = None
                        entry["reconciliation_attempts"] = attempts
                        status = "Validated" 
                        break
                        
                    if attempts >= MAX_CORRECTION_ATTEMPTS: break
                
                # --- THE MAGIC EXPANSION HAPPENS HERE ---
                expanded_variants = expand_to_db_variants(entry, real_db_variants)
                
                for exp_entry in expanded_variants:
                    local_structured.append(exp_entry)
                    local_validation.append({"entry": exp_entry, "final_validation_report": validation_output})
                # ----------------------------------------
                    
            success = True 
        except Exception as e:
            attempt_count += 1
            if attempt_count < max_retries: time.sleep(5) 

    return local_structured, local_validation, local_raw

def process_brochure_chunk(document_id: str, features_chunk: list, cached_text: str = None, job_id: str = "unknown_job", real_db_variants: list = None, car_name: str = "Unknown_Car"):
    all_raw_extractions, all_structured_entries, all_validation_results = [], [], []

    try:
        master_variant_agent = MasterVariantAgent()
        converter_agent = ConverterAgent()
        validation_agent = ValidationAgent()

        brochure_text = cached_text if cached_text else fetch_brochure_text_from_api(document_id)
        
        # We now skip re-identifying the car name if it was passed from orchestrator
        if car_name == "Unknown_Car":
            car_name = execute_with_retry(master_variant_agent.identify_car_model, brochure_text)
            if not car_name or len(car_name) < 2: car_name = "Unknown_Car"
        
        master_variants = execute_with_retry(master_variant_agent.run, brochure_text, car_name)
        
        # Fallback fetch if running the worker directly without orchestrator
        if real_db_variants is None:
            real_db_variants = fetch_db_variants(car_name)

        rows_to_process = [(i, pd.Series(row_dict)) for i, row_dict in enumerate(features_chunk)]

        MAX_WORKERS = min(2, len(rows_to_process))
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_feature = {
                executor.submit(
                    process_single_feature, r_data, car_name, brochure_text, document_id, 
                    master_variants, converter_agent, validation_agent, real_db_variants # Pass it down!
                ): r_data for r_data in rows_to_process
            }
            for future in concurrent.futures.as_completed(future_to_feature):
                try:
                    struct_data, valid_data, raw_data = future.result()
                    all_structured_entries.extend(struct_data)
                    all_validation_results.extend(valid_data)
                    all_raw_extractions.extend(raw_data)
                except Exception as e:
                    logger.error(f"Thread execution failed: {e}")

        final_result = {"structured": all_structured_entries, "validation": all_validation_results}
        
        try:
            logger.info(f"Initiating streaming upload for {len(all_structured_entries)} EXPANDED entries...")
            stream_upload_chunk(all_structured_entries) # We don't need car_name here anymore!
        except Exception as e:
            logger.error(f"Failed to execute streaming upload: {e}")

        save_chunk_locally(final_result, job_id)
        return final_result

    except Exception as e:
        if is_model_not_found_error(e): raise RuntimeError("MODEL_NOT_FOUND") from e
        else: raise e


def run_brochure_orchestrator(document_id, job_id=None, feature_limit=None):
    if not document_id: return {"status": "error", "message": "Missing document_id"}

    if not job_id:
        job_id = str(uuid.uuid4())

    cleanup_stale_locks(OUTPUT_DIR)
    temp_partials_dir = OUTPUT_DIR / "partials" / job_id
    os.makedirs(temp_partials_dir, exist_ok=True)
    
    output_path = OUTPUT_DIR / f"Final_Extraction_{job_id}.json"

   
    partials_root = OUTPUT_DIR / "partials"
    if partials_root.exists():
        for job_folder in partials_root.iterdir():
            if job_folder.is_dir() and job_folder.name != job_id:
                harvest_and_merge(job_folder.name, output_path)

    aggregated_results = safe_read_json(output_path)
    received_feature_keys = set()
    for item in aggregated_results:
        entry = item.get("entry", {})
        fname = entry.get("feature_name") 
        variant = entry.get("variant") or entry.get("variant_name")
        if fname and variant:
            received_feature_keys.add((fname.strip(), variant.strip()))

    if not aggregated_results: flush_output(output_path, [])

    # LOAD CSV
    MASTER_CSV_URL = "https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/40b73d2f-63e4-4f6e-a898-52ce1cd34c87-6980a0fa_Master_sheet.csv"
    df = pd.read_csv(MASTER_CSV_URL)
    df = df.dropna(subset=["feature_name"]).fillna("") 
    
    if feature_limit is not None:
        feature_limit = int(feature_limit)
        df = df.head(feature_limit)
        logger.info(f"📋 Configuration set to process top {feature_limit} features from CSV.")
    else:
        logger.info(f"📋 Configuration set to process ALL {len(df)} features from CSV.")
        
    all_feature_rows = df.to_dict("records")

    prep_data = prepare_brochure_data(document_id)
    if not prep_data: return {"status": "failed", "error": "Dispatcher failed to extract text from API."}
    
    extracted_text = prep_data["text"]
    detected_variants = [str(v).strip() for v in prep_data["variants"] if v]
    car_name = prep_data["car_name"]

    logger.info(f"🔍 Fetching Real DB Variants for {car_name}...")
    real_db_variants = fetch_db_variants(car_name)

    retry_attempt = 0
    while retry_attempt < MAX_FINAL_RETRY:
        aggregated_results = safe_read_json(output_path)
        received_feature_keys.clear()
        
        for item in aggregated_results:
            entry = item.get("entry", {})
            fname = entry.get("feature_name")
            variant = entry.get("variant") or entry.get("variant_name")
            if fname and variant: received_feature_keys.add((fname.strip(), variant.strip()))

        missing_features_list = []
        for feature in all_feature_rows:
            fname = feature.get("feature_name", "").strip()
            if not fname: continue
            
            is_still_missing = False
            for v in detected_variants:
                if (fname, v) not in received_feature_keys:
                    is_still_missing = True
                    break
            if is_still_missing: missing_features_list.append(feature)

        if not missing_features_list: break

        if retry_attempt > 0: time.sleep(5) 

        retry_jobs = []
        chunked_retries = [missing_features_list[i:i + CHUNK_SIZE] for i in range(0, len(missing_features_list), CHUNK_SIZE)]

        for chunk in chunked_retries:
            retry_jobs.append({
                "task": "brochure_worker_task", 
                "service": "brochure-pipeline",
                "args": [],
                "kwargs": {
                    "document_id": document_id,
                    "features_chunk": chunk,
                    "job_id": job_id, 
                    "cached_text": extracted_text,
                    "real_db_variants": real_db_variants, 
                    "car_name": car_name                  
                }
            })
            
        if not retry_jobs: break

        job_iterator = gryd.yield_results(retry_jobs)
        active = True
        while active:
            try:
                _ = next(job_iterator)
                harvest_and_merge(job_id, output_path)
            except StopIteration:
                for i in range(30):
                    time.sleep(10)
                    harvest_and_merge(job_id, output_path)
                active = False
            except Exception as e:
                harvest_and_merge(job_id, output_path)
                active = False
        
        harvest_and_merge(job_id, output_path)
        retry_attempt += 1

    final_results = safe_read_json(output_path)

    return {
        "status": "success",
        "job_id": job_id,
        "saved_path": str(output_path),
        "total_entries": len(final_results)
    }
