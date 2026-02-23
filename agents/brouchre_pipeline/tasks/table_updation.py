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
    
    # 1. Fetch the full response from DB
    db_response = fetch_chunk_data_by_id(chunk_id)
    
    if not db_response or 'data' not in db_response:
        logger.error(f"❌ No data found for Chunk ID: {chunk_id}")
        return {"status": "failed", "reason": "No data found"}

    items_processed = 0
    
    # 2. Iterate and Process
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
            
            # Debug Log
            md_len = len(raw_markdown) if raw_markdown else 0
            logger.info(f"📋 Table Ref {ref_id} | Markdown Length: {md_len} chars")

            if raw_markdown:
                logger.info(f"🤖 Calling LLM for Table Ref ID: {ref_id}...")
                
                # CALL GEMINI
                structured_data = extract_hierarchical_data_from_markdown(raw_markdown, context_text)
                
                if structured_data and isinstance(structured_data, dict):
                    # PRINTING TO TERMINAL ONLY
                    logger.info(f"✅ Table Ref {ref_id} structured successfully. Outputting below:")
                    print(f"\n{'='*60}")
                    print(f"📊 Structured Table Data (Ref ID: {ref_id})")
                    print(f"{'='*60}")
                    print(json.dumps(structured_data, indent=2, ensure_ascii=False))
                    print(f"{'='*60}\n")
                else:
                    logger.warning(f"⚠️ LLM extraction failed or empty for Ref {ref_id}.")

        items_processed += 1

    # 3. Return success
    logger.info(f"🎉 Finished processing {items_processed} items for chunk {chunk_id}")
    return {"status": "success", "processed_items": items_processed}