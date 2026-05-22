import json
import os
import traceback
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from gryd_worker import gryd, gryd_helpers as hp
from document_processor.chunk_model_wrapper import ModelWrapper
from document_processor.vlm_orchestrator import run_orchestrator
from config import AUTOCRM_DOCUMENT_PROCESSOR_PIPELINE_SERVICE_NAME,AUTOCRM_APP_ENTERPRISE_ID
logger = hp.get_logger(__name__)
gryd.SERVICE = AUTOCRM_DOCUMENT_PROCESSOR_PIPELINE_SERVICE_NAME
gryd.set_queue_manager(config={"broker_type": "sqs", "timeout": 5})
__version__="0.0.1"

model_wrapper = ModelWrapper(
    model_name="chunk_saver",
    enterprise_id=AUTOCRM_APP_ENTERPRISE_ID,
    service=AUTOCRM_DOCUMENT_PROCESSOR_PIPELINE_SERVICE_NAME,
)



@gryd.is_a_task()
def run_document_parsing(**kwargs) -> dict:
    """
    Process a PDF document end-to-end using the image-only VLM pipeline:
        1. Render each PDF page as an image with PyMuPDF (+ optional tile crops)
        2. Upload all images to the Gryd CDN
        3. Call the VLM per page with only images (no Docling text extraction)
        4. Parse VLM JSON → build chunk records → post to chunk_saver model

    Returns a summary dict with processing statistics.
    """
    filepath    = kwargs.get("filepath") or kwargs.get("input_path", "")
    document_id = kwargs.get("document_id", os.path.basename(filepath))
    description = (
        kwargs.get("description")
        or kwargs.get("doc_description")
        or kwargs.get("document_description")
        or ""
    )
    enable_tiles = kwargs.get("enable_tiles", True)

    logger.info(
        f"Worker received job — document_id={document_id}, "
        f"filepath={filepath}, description={description!r}, "
        f"enable_tiles={enable_tiles}"
    )

    try:
        model_wrapper.load_gryd_model()

        summary = run_orchestrator(
            document_id=document_id,
            filepath=filepath,
            doc_description=description,
            model_wrapper=model_wrapper,
            enable_tiles=enable_tiles,
        )

        summary["status"] = "success"
        logger.info(f"Worker finished successfully: {json.dumps(summary)}")
        return summary

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(f"Worker failed — document_id={document_id} — {error_msg}")
        logger.debug(traceback.format_exc())
        return {
            "document_id": document_id,
            "status":      "error",
            "error":       error_msg,
        }
