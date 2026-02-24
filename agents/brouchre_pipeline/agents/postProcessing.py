import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

def process_batch_extraction(extracted_data_list: list, feature_info: dict, car_name: str, brochure_url: str) -> list:
    """
    Takes the raw list from ConverterAgent and formats it with metadata from the CSV.
    No IDs are generated here to avoid premature duplication.
    """
    enriched_entries = []
    
    # Extract metadata from the CSV row (feature_info)
    feature_name = feature_info.get("feature_name")
    feature_group = feature_info.get("feature_category")
    csv_value_type = feature_info.get("value_type", "Categorical") 
    csv_unit = feature_info.get("unit") 
    feature_desc = feature_info.get("feature_description")
    feature_alias = feature_info.get("aliases")

    current_time = datetime.now().isoformat()
    
    for item in extracted_data_list:
        # Build the enriched entry using only known base data
        enriched_entry = {
            "vehicle_model_name": car_name,
            "variant_name": item.get("variant"), # This is the BASE variant (e.g., "Plus")
            
            "feature_name": feature_name,
            "feature_category": feature_group,
            "feature_description": feature_desc if pd.notna(feature_desc) else None,
            "feature_alias": feature_alias if pd.notna(feature_alias) else None,
            "value_type": csv_value_type,
            "unit": csv_unit if pd.notna(csv_unit) else None,
            
            # Note: Changed key to "feature_value" to match your API expectation early
            "feature_value": item.get("value"), 
            
            "source_reference": item.get("source_reference"),
            "source_path": brochure_url,
            "source_date": current_time,
            "confidence_score": item.get("confidence_score", 0.0),
            "reconciliation_attempts": 0
        }
        
        enriched_entries.append(enriched_entry)
        
    return enriched_entries

def finalize_results_json(all_entries: list) -> dict:
    return {"data": all_entries}