import json
from bp_utils import get_logger
from file_loader.table_structure import extract_hierarchical_data_from_markdown
from file_loader.db_utils import fetch_chunk_data_by_id

logger = get_logger(__name__)

def run_table_processor(chunk_id: str):
    """
    Main logic to fetch chunk data, extract table markdown, and get structured output.
    """
    logger.info(f"🚀 Processing Chunk ID: {chunk_id}")
    
    extracted_tables = []
    
    db_response = fetch_chunk_data_by_id(chunk_id)
    
    if not db_response or 'data' not in db_response:
        logger.error(f"❌ No data found for Chunk ID: {chunk_id}")
        return {"status": "failed", "reason": "No data found"}

    items_processed = 0
    
  
    for item in db_response['data']:
        if item.get('chunk_id') != chunk_id:
            continue

        tables = item.get('tables', [])
        context_text = item.get('text_content', '') 
        
        if not tables:
            logger.info(f"ℹ️ Chunk {chunk_id} has no tables.")
            continue
            
        for table_obj in tables:
            raw_markdown = table_obj.get('table_text', '')
            ref_id = table_obj.get('ref_id', 'Unknown')
            
      
            md_len = len(raw_markdown) if raw_markdown else 0
            logger.info(f"📋 Table Ref {ref_id} | Markdown Length: {md_len} chars")

            if raw_markdown:
                logger.info(f"🤖 Calling LLM for Table Ref ID: {ref_id}...")
                
                
                structured_data = extract_hierarchical_data_from_markdown(raw_markdown, context_text)
                
                if structured_data and isinstance(structured_data, dict):
                    
                    extracted_tables.append({
                        "ref_id": ref_id,
                        "data": structured_data
                    })
                else:
                    logger.warning(f"⚠️ LLM extraction failed or empty for Ref {ref_id}.")

        items_processed += 1

    logger.info(f"🎉 Finished processing {items_processed} items for chunk {chunk_id}")
    return {
        "status": "success", 
        "processed_items": items_processed,
        "extracted_tables": extracted_tables 
    }