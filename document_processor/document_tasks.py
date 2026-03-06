
import os
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from gryd_worker import gryd
import time
import json
from typing import List,Dict
from docling_parser import DoclingParser
from document_builder_vlm import VLMHierarchyProcessor
from chunk_model_wrapper import ModelWrapper
from config import  AUTOCRM_APP_ENTERPRISE_ID,AUTOCRM_DOCUMENT_PROCESSOR_PIPELINE_SERVICE_NAME
logger = gryd.hp.get_logger(__name__)

gryd.SERVICE = AUTOCRM_DOCUMENT_PROCESSOR_PIPELINE_SERVICE_NAME
gryd.set_queue_manager(config={
                                "broker_type":"sqs",
                                "timeout": 5
                                })

try:
    model_wrapper = ModelWrapper()
    logger.info("Global ModelWrapper initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize global ModelWrapper: {e}")
    model_wrapper = None
    
@gryd.is_a_task()
def run_document_parsing(**kwargs) -> Dict:
    """
    Task to process a document and save the objects in chunk saver model.
    Requires: document_id, filepath,
    Optional: document_description
    """
    filepath = kwargs.get("filepath") or kwargs.get("input_path", "")
    document_id = kwargs.get("document_id", os.path.basename(filepath))
    
    logger.info(f"Starting document parsing for {filepath} with document_id: {document_id}")
    
    if model_wrapper is None:
         return {
            "status": "failed",
            "error": "Global ModelWrapper failed to initialize"
        }

    try:
        doc_parser = DoclingParser()
        vlm_processor = VLMHierarchyProcessor()

        description = kwargs.get("description") or kwargs.get("doc_description") or kwargs.get("document_description") or ""

        page_count = 0
        object_count = 0
        
        for page_data in doc_parser.process_pdf_stream(filepath):
            page_no = page_data.get("page_no")
            logger.info(f"Processing page {page_no}...")
            
            try:
                rag_objects = vlm_processor.process_page(
                    page_json=page_data, 
                    description=description
                )

                for obj in rag_objects:
                    obj["document_id"] = document_id
                    try:
                        logger.info(f"Attempting to post object to chunk_saver. Hierarchy: {obj.get('hierarchy_path', 'N/A')}")
                        resp = model_wrapper.post_object(obj)
                        logger.info(f"Successfully posted object to chunk_saver. Response: {resp}")
                        object_count += 1
                    except Exception as post_err:
                        logger.error(f"Failed to post object to chunk_saver. Error: {str(post_err)}")
                
                page_count += 1
                
            except Exception as e:
                logger.exception(f"Failed to process/save page {page_no}")
        
        logger.info(f"Completed parsing {filepath}. Processed {page_count} pages, {object_count} objects posted to chunk_saver.")
        return {
            "status": "success",
            "pages_processed": page_count,
            "objects_created": object_count,
            "document_id": document_id
        }

    except Exception as e:
        logger.exception(f"Fatal error in run_document_parsing for {filepath}")
        return {
            "status": "failed",
            "stage": "document_parsing_streaming",
            "error": str(e),
            "filepath": filepath
        }
