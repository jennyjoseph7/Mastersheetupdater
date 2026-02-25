import urllib.parse
import json
import time
import concurrent.futures
import uuid
import sys
import os
import pandas as pd
import requests
from pathlib import Path
from bp_utils import get_logger

from agents.variant_feature_agent import (
    ConverterAgent, 
    MasterVariantAgent, 
    ValidationAgent, 
    generate_bulk_questions
)
from agents.postProcessing import process_batch_extraction, finalize_results_json
from file_loader.gemini_loader import process_brochure_to_structure


logger = get_logger(__name__)
HERE = Path(__file__).resolve().parent
TEMP_DIR = HERE / "temp_files"
OUTPUT_DIR = HERE.parent / "outputs"  
MAX_CORRECTION_ATTEMPTS = 3

MAX_RETRIES = 5
RETRY_DELAY = 10

def download_file(url: str, dest_folder: Path) -> Path:
    """Downloads a file from a URL to a destination folder."""
    if not url:
        raise ValueError("No URL provided.")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        parsed_url = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed_url.path) or "downloaded_file.pdf"
        local_path = dest_folder / filename
        
        with open(local_path, 'wb') as f:
            f.write(response.content)
        return local_path
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        raise

def is_model_not_found_error(e: Exception) -> bool:
    msg = str(e).lower()
    return (
        "no model found" in msg or
        "model_identifier" in msg
    )

def execute_with_retry(func, *args, **kwargs):
    """
    Executes a function with retry logic for DB/Network AND Rate Limit errors.
    """
    last_exception = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            last_exception = e
            
            if "ratelimit" in error_str or "429" in error_str:
                wait_time = RETRY_DELAY * attempt + 10
                logger.warning(f"⚠️ Rate Limit Hit (429). Cooling down for {wait_time}s before Retry {attempt}/{MAX_RETRIES}...")
                time.sleep(wait_time)
                continue
            if "connection timed out" in error_str or "connection failed" in error_str or "operationalerror" in error_str:
                logger.warning(f"Network/DB Error. Retrying ({attempt}/{MAX_RETRIES}) in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            
            raise e
    
    logger.error(f"Max retries reached. Last error: {last_exception}")
    raise last_exception

def process_single_feature(row_data, car_name, brochure_text, brochure_url, master_variants, converter_agent, validation_agent):
    """
    Process a single feature row from the master CSV against all variants.
    """
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

    local_structured = []
    local_validation = []
    local_raw = []

    time.sleep(2) 

    while attempt_count < max_retries and not success:
        try:
            questions_text = generate_bulk_questions(
                car_name, 
                feature_name, 
                master_variants, 
                value_type, 
                description=feature_desc, 
                alias=feature_alias
            )
            
          
            extracted_data_list = execute_with_retry(converter_agent.run, questions_text, value_type, brochure_text)
            
            if isinstance(extracted_data_list, list):
                local_raw.extend(extracted_data_list)
            else:
                local_raw.append(extracted_data_list)

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
                        extracted_val = entry.get("value")         
                        if (extracted_val is True) and ("yes" in reasoning) and (("contradict" in reasoning) or ("mismatch" in reasoning)):
                            logger.warning(f"⚠️ Overriding Validation Logic Error for {entry.get('feature_name')} - {entry.get('variant')}. Reasoning was: {reasoning[:50]}...")
                            status = "Validated" 
                            validation_output["status"] = "Validated"

                    if status == "Validated": break 
                    attempts += 1
                    
                    if status == "Value Mismatch":
                        if not isinstance(validation_output, dict): validation_output = {}
                        correct_val = validation_output.get("ground_truth_value")
                        if correct_val is not None:
                            entry["value"] = correct_val
                            entry["value_type"] = entry.get("value_type", value_type)
                            entry["reconciliation_attempts"] = attempts
                            status = "Validated"
                            break
                        if str(entry.get("value_type", "")).lower() == "boolean":
                            entry["value"] = False
                            entry["reconciliation_attempts"] = attempts
                            status = "Validated"
                            break
                            
                    if status == "Invalidated" or status == "Not Found":
                        # --- FIX: Set null for non-booleans ---
                        if "boolean" in str(value_type).lower():
                            entry["value"] = False
                        else:
                            entry["value"] = None
                        # --------------------------------------
                        entry["reconciliation_attempts"] = attempts
                        status = "Validated" 
                        break
                        
                    if attempts >= MAX_CORRECTION_ATTEMPTS: break
                
                local_structured.append(entry)
                local_validation.append({"entry": entry, "final_validation_report": validation_output})
            success = True 
        except Exception as e:
            attempt_count += 1
            logger.error(f"Error on feature '{feature_name}': {e}")
            if attempt_count < max_retries: 
                time.sleep(5) 

    return local_structured, local_validation, local_raw

def save_chunk_locally(data, job_id):
    """
    Saves the worker's result directly to disk so the Orchestrator can pick it up
    without relying on the database connection.
    """
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

def process_brochure_chunk(brochure_url: str, features_chunk: list, cached_text: str = None, job_id: str = "unknown_job"):
    """
    Main entry point for a Worker.
    """
    all_raw_extractions = []
    all_structured_entries = []
    all_validation_results = []
    
    local_pdf_path = None

    try:
        os.makedirs(TEMP_DIR, exist_ok=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        master_variant_agent = MasterVariantAgent()
        converter_agent = ConverterAgent()
        validation_agent = ValidationAgent()

        if cached_text:
            logger.info("Worker using PRE-EXTRACTED text.")
            brochure_text = cached_text
        else:
            logger.info("No cached text provided. Worker downloading and extracting...")
            local_pdf_path = download_file(brochure_url, TEMP_DIR)
            logger.info("Extracting structure with Gemini Loader...")
            brochure_text = process_brochure_to_structure(str(local_pdf_path))
            
        logger.info("Identifying Car Model...")
        CAR_NAME = execute_with_retry(master_variant_agent.identify_car_model, brochure_text)
        
        if not CAR_NAME or len(CAR_NAME) < 2:
            CAR_NAME = "Unknown_Car"
        
        logger.info(f"Worker processing chunk for model: {CAR_NAME}")
        
        master_variants = execute_with_retry(master_variant_agent.run, brochure_text, CAR_NAME)
        
        rows_to_process = []
        for i, row_dict in enumerate(features_chunk):
            rows_to_process.append((i, pd.Series(row_dict)))

        logger.info(f"Worker starting Parallel Processing for {len(rows_to_process)} features...")

        MAX_WORKERS = min(2, len(rows_to_process))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_feature = {
                executor.submit(
                    process_single_feature, 
                    r_data, 
                    CAR_NAME, 
                    brochure_text, 
                    brochure_url, 
                    master_variants,
                    converter_agent,
                    validation_agent
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

        final_result = {
            "structured": all_structured_entries,
            "validation": all_validation_results
        }
        
        save_chunk_locally(final_result, job_id)

        return final_result

    except Exception as e:
        if is_model_not_found_error(e):
            logger.error("MODEL_NOT_FOUND_ERROR", exc_info=True)
            raise RuntimeError("MODEL_NOT_FOUND") from e
        else:
            logger.error("Fatal Chunk Error", exc_info=True)
            raise e

    finally:
        try:
            if local_pdf_path and os.path.exists(local_pdf_path):
                os.remove(local_pdf_path)
        except Exception as e:
            print(f"Error during cleanup: {e}")