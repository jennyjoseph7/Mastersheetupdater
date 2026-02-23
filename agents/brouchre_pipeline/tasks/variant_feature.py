import os
import sys
import json
import uuid
import time
import urllib.parse
import pandas as pd
import requests
import concurrent.futures
from pathlib import Path
from filelock import FileLock
from gryd_worker import gryd
from bp_utils import get_logger

# Import Agents and Loaders
from agents.variant_feature_agent import (
    ConverterAgent, 
    MasterVariantAgent, 
    ValidationAgent, 
    generate_bulk_questions
)

from agents.postProcessing import process_batch_extraction, finalize_results_json

from file_loader.gemini_loader import process_brochure_to_structure
import re
from dotenv import load_dotenv

load_dotenv()
logger = get_logger(__name__)


BASE_URL = os.getenv("GRYD_BASE_URL")
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "X-GRYD-ENTERPRISE-ID": os.getenv("GRYD_ENTERPRISE_ID"),
    "X-GRYD-ROLE": os.getenv("GRYD_ROLE"),
    "X-GRYD-SESSION-ID": os.getenv("GRYD_SESSION_ID"),
    "X-GRYD-TOKEN": os.getenv("GRYD_TOKEN"),
}

VARIANT_API_URL = f"{BASE_URL}/gryd/db/objects/variant"
UPLOAD_API_URL = f"{BASE_URL}/gryd/db/object/variant_feature"

def generate_feature_id(entry):
    fields = [entry.get("feature_category"), entry.get("feature_name"), entry.get("value_type"), entry.get("unit")]
    valid_parts = [str(f).strip() for f in fields if f is not None and str(f).strip() != ""]
    return re.sub(r'[^a-z0-9]+', '-', "-".join(valid_parts).lower()).strip('-')

def fetch_db_variants(car_name: str) -> list:
    try:
        response = requests.get(VARIANT_API_URL, headers=HEADERS)
        if response.status_code in [200, 201]:
            data = response.json()
            variants = data.get("data", []) if isinstance(data, dict) else data
            return [v for v in variants if str(v.get("vehicle_model_name", "")).lower() == car_name.lower()]
    except Exception as e:
        logger.error(f"Failed to fetch variants from API: {e}")
    return []

def stream_upload_chunk(extracted_entries: list, car_name: str):
    """Takes a worker's newly extracted features, expands them, and uploads immediately."""
    if not extracted_entries: return
    
    db_variants = fetch_db_variants(car_name)
    if not db_variants:
        logger.warning(f"⚠️ No DB variants found for '{car_name}'. Skipping streaming upload.")
        return

    success_count = 0
    for entry in extracted_entries:
        base_variant = str(entry.get("variant", entry.get("variant_name", ""))).strip().lower()
        matched_db_variants = [v for v in db_variants if base_variant in str(v.get("variant_name", "")).lower()]

        for db_variant in matched_db_variants:
            payload = {
                "variant_id": db_variant.get("variant_id"),
                "feature_id": generate_feature_id(entry),
                "vehicle_model_name": db_variant.get("vehicle_model_name"),
                "variant_name": db_variant.get("variant_name"),
                "engine_type": db_variant.get("engine_type", ""),
                "transmission_type": db_variant.get("transmission_type", ""),
                "drivetrain": db_variant.get("drivetrain", ""),
                "feature_name": entry.get("feature_name"),
                "feature_category": entry.get("feature_category"),
                "value_type": entry.get("value_type"),
                "unit": entry.get("unit"),
                "feature_value": entry.get("feature_value"),
                "source_reference": entry.get("source_reference"),
                "confidence_score": str(entry.get("confidence_score", 0.0))
            }
            try:
                resp = requests.post(UPLOAD_API_URL, headers=HEADERS, json=payload)
                if resp.status_code in [200, 201]:
                    success_count += 1
            except Exception as e:
                logger.error(f"Streaming Upload Error: {e}")
            time.sleep(0.05) # Rate limit protection
            
    logger.info(f"🚀 [Streaming Upload] Successfully posted {success_count} expanded features to DB.")



# ==============================================================================
# PATHS & CONSTANTS
# ==============================================================================
# Since this file is in tasks/, we need to point to the parent directory (root)
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent 
OUTPUT_DIR = PROJECT_ROOT / "outputs"
TEMP_DIR = PROJECT_ROOT / "temp_files"
MARKER_OUTPUT_DIR = PROJECT_ROOT / "marker_brochure_output"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(MARKER_OUTPUT_DIR, exist_ok=True)

MAX_FINAL_RETRY = 5
CHUNK_SIZE = 3
MAX_CORRECTION_ATTEMPTS = 3
MAX_RETRIES = 5
RETRY_DELAY = 10

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def download_file(url: str, dest_folder: Path) -> Path:
    if not url: raise ValueError("No URL provided.")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        filename = os.path.basename(urllib.parse.urlparse(url).path) or "downloaded_file.pdf"
        local_path = dest_folder / filename
        with open(local_path, 'wb') as f:
            f.write(response.content)
        return local_path
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        raise

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
        try:
            os.remove(lock_file)
        except Exception:
            pass

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

def prepare_brochure_data(brochure_url):
    parsed_url = urllib.parse.urlparse(brochure_url)
    base_name = os.path.splitext(os.path.basename(parsed_url.path) or "unknown.pdf")[0]
    cache_path = MARKER_OUTPUT_DIR / f"{base_name}.json"
    brochure_text = ""
    
    if cache_path.exists():
        logger.info(f"[Dispatcher] Found cached Structured output: {cache_path}")
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                brochure_text = f.read()
        except Exception: pass

    if not brochure_text:
        local_pdf_path = None
        try:
            local_pdf_path = download_file(brochure_url, TEMP_DIR)
            brochure_text = process_brochure_to_structure(str(local_pdf_path))
            if brochure_text:
                with open(cache_path, "w", encoding="utf-8") as f: f.write(brochure_text)
        except Exception as e:
            logger.error(f"Failed to prepare brochure: {e}")
            return None
        finally:
            if local_pdf_path and os.path.exists(local_pdf_path):
                os.remove(local_pdf_path)

    try:
        agent = MasterVariantAgent()
        car_name = agent.identify_car_model(brochure_text)
        variants = agent.run(brochure_text, car_name=car_name)
        return {"text": brochure_text, "variants": variants}
    except Exception as e:
        logger.error(f"Error identifying variants: {e}")
        return None

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


# ==============================================================================
# WORKER LOGIC
# ==============================================================================
def process_single_feature(row_data, car_name, brochure_text, brochure_url, master_variants, converter_agent, validation_agent):
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

            enriched_entries = process_batch_extraction(extracted_data_list, feature_info, car_name, brochure_url)
            
            for entry in enriched_entries:
                attempts = 0
                status = "Pending"
                validation_output = {}

                while attempts < MAX_CORRECTION_ATTEMPTS:
                    validation_report = execute_with_retry(validation_agent.run, brochure_text, entry)
                    validation_output = validation_report.get("validation_output", {})
                    status = validation_output.get("status")
                    reasoning = str(validation_output.get("reasoning", "")).lower()

                    if status == "Value Mismatch":
                        extracted_val = entry.get("feature_value") # Adjusted for new schema
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
                
                local_structured.append(entry)
                local_validation.append({"entry": entry, "final_validation_report": validation_output})
            success = True 
        except Exception as e:
            attempt_count += 1
            if attempt_count < max_retries: time.sleep(5) 

    return local_structured, local_validation, local_raw

def process_brochure_chunk(brochure_url: str, features_chunk: list, cached_text: str = None, job_id: str = "unknown_job"):
    all_raw_extractions, all_structured_entries, all_validation_results = [], [], []
    local_pdf_path = None

    try:
        master_variant_agent = MasterVariantAgent()
        converter_agent = ConverterAgent()
        validation_agent = ValidationAgent()

        if cached_text:
            brochure_text = cached_text
        else:
            local_pdf_path = download_file(brochure_url, TEMP_DIR)
            brochure_text = process_brochure_to_structure(str(local_pdf_path))
            
        CAR_NAME = execute_with_retry(master_variant_agent.identify_car_model, brochure_text)
        if not CAR_NAME or len(CAR_NAME) < 2: CAR_NAME = "Unknown_Car"
        
        master_variants = execute_with_retry(master_variant_agent.run, brochure_text, CAR_NAME)
        
        rows_to_process = [(i, pd.Series(row_dict)) for i, row_dict in enumerate(features_chunk)]

        MAX_WORKERS = min(2, len(rows_to_process))
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_feature = {
                executor.submit(
                    process_single_feature, r_data, CAR_NAME, brochure_text, brochure_url, 
                    master_variants, converter_agent, validation_agent
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
            logger.info(f"Initiating streaming upload for {len(all_structured_entries)} base entries...")
            stream_upload_chunk(all_structured_entries, CAR_NAME)
        except Exception as e:
            logger.error(f"Failed to execute streaming upload: {e}")

        # Continue saving to disk for backup / orchestrator harvesting
        save_chunk_locally(final_result, job_id)
        return final_result

    except Exception as e:
        if is_model_not_found_error(e): raise RuntimeError("MODEL_NOT_FOUND") from e
        else: raise e
    finally:
        if local_pdf_path and os.path.exists(local_pdf_path):
            try: os.remove(local_pdf_path)
            except Exception: pass



def run_brochure_orchestrator(brochure_url, job_id=None, feature_limit=None):
    if not brochure_url: return {"status": "error", "message": "Missing brochure_url"}

    if not job_id:
        job_id = str(uuid.uuid4())

    cleanup_stale_locks(OUTPUT_DIR)
    temp_partials_dir = OUTPUT_DIR / "partials" / job_id
    os.makedirs(temp_partials_dir, exist_ok=True)
    
    output_path = OUTPUT_DIR / f"Final_Extraction_{job_id}.json"

    # Recover orphaned partials
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
    
    # ---> NEW: Conditional limit logic <---
    if feature_limit is not None:
        feature_limit = int(feature_limit)
        df = df.head(feature_limit)
        logger.info(f"📋 Configuration set to process top {feature_limit} features from CSV.")
    else:
        logger.info(f"📋 Configuration set to process ALL {len(df)} features from CSV.")
        
    all_feature_rows = df.to_dict("records")
    logger.info(f"📋 Configuration set to process top {feature_limit} features from CSV.")

    prep_data = prepare_brochure_data(brochure_url)
    if not prep_data: return {"status": "failed", "error": "Dispatcher failed to extract text."}
    
    extracted_text = prep_data["text"]
    detected_variants = [str(v).strip() for v in prep_data["variants"] if v]

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
                "task": "brochure_worker_task", # Maps to parallel_task.py registration
                "service": "brochure-pipeline",
                "args": [],
                "kwargs": {
                    "brochure_url": brochure_url,
                    "features_chunk": chunk,
                    "job_id": job_id, 
                    "cached_text": extracted_text  
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
    
    # Optional: trigger pipeline_uploader here automatically
    # from pipeline_uploader import expand_and_upload
    # expand_and_upload(str(output_path), car_name)

    return {
        "status": "success",
        "job_id": job_id,
        "saved_path": str(output_path),
        "total_entries": len(final_results)
    }