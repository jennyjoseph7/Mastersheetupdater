
import os
import json
import traceback
import time
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from gryd_worker import gryd_helpers as hp

from document_processor.pdf_renderer import render_pdf_pages
from document_processor.vlm_caller  import build_user_query, call_vlm_with_retry, MODEL_IDENTIFIER
from document_processor.chunk_builder import build_chunk_record
from document_processor.chunk_model_wrapper import ModelWrapper

logger = hp.get_logger(__name__)


_PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "prompts",
    "vlm_chunker_image_only.txt",
)


def _load_system_prompt() -> str:
    with open(_PROMPT_PATH, "r") as f:
        return f.read()


def _save_failed_response(document_id: str, page_no: int, raw_response: str | None):
    """Save a failed/unparseable VLM response to disk for debugging."""
    try:
        log_dir = os.path.join("audit_logs", "failed_vlm_responses")
        os.makedirs(log_dir, exist_ok=True)
        filename = f"{document_id}_page_{page_no}_failed_raw.txt"
        with open(os.path.join(log_dir, filename), "w") as f:
            f.write(raw_response or "")
        logger.info(f"Saved failed VLM response to audit_logs/failed_vlm_responses/{filename}")
    except Exception as e:
        logger.error(f"Could not save failed VLM response: {e}")



def _process_page(
    page_no: int,
    full_page_url: str,
    tile_urls: list[str],
    hierarchy: dict,
    system_prompt: str,
    doc_description: str,
    document_id: str,
    max_tile_images: int = 4,
) -> tuple[list, dict, bool]:
    """
    Send one page to the VLM (image-only) and return (rag_objects, hierarchy, is_toc).

    Image list sent to VLM:
        IMAGE_0   — full rendered page
        IMAGE_1…N — tile crops (top/bottom, capped at max_tile_images)

    Args:
        page_no:         1-indexed page number.
        full_page_url:   CDN URL of the full page render.
        tile_urls:       CDN URLs of tile crops.
        hierarchy:       Running hierarchy state from previous page.
        system_prompt:   VLM system prompt text.
        doc_description: Document description string.
        document_id:     Used for audit log filenames.
        max_tile_images: Cap on the number of tile images passed to the VLM.

    Returns:
        (rag_objects, updated_hierarchy, is_toc_index)
        rag_objects is [] and hierarchy is unchanged on failure.
    """

    images = [full_page_url]
    if tile_urls:
        images.extend(tile_urls[:max_tile_images])

    user_query = build_user_query(page_no, hierarchy, doc_description)

    logger.info(f"Page {page_no}: calling VLM with {len(images)} image(s)")
    t0 = time.perf_counter()

    parsed, raw_response = call_vlm_with_retry(
        user_query=user_query,
        system_prompt=system_prompt,
        images=images,
    )

    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info(f"Page {page_no}: VLM call completed in {elapsed_ms:.0f} ms")

    if parsed is None:
        logger.warning(f"Page {page_no}: VLM returned unparseable response — skipping")
        _save_failed_response(document_id, page_no, raw_response)
        return [], hierarchy, False

    updated_hierarchy = parsed.get("updated_hierarchy", hierarchy)
    rag_objects       = parsed.get("rag_objects", [])
    logger.info(f"rag_objects that the VLM returned: {rag_objects}")
    is_toc_index      = parsed.get("_it_is_toc_index", False)

    logger.info(
        f"Page {page_no}: parsed {len(rag_objects)} rag_objects — "
        f"is_toc={is_toc_index}"
    )
    return rag_objects, updated_hierarchy, is_toc_index



def run_orchestrator(
    document_id: str,
    filepath: str,
    doc_description: str,
    model_wrapper: ModelWrapper,
    enable_tiles: bool = True,
) -> dict:
    """
    Run the complete image-only document processing pipeline.

    Args:
        document_id:     Unique document identifier.
        filepath:        Local path or HTTP(S) URL to the PDF.
        doc_description: Short document description for contextual VLM chunking.
        model_wrapper:   Initialized ModelWrapper for posting chunk records.
        enable_tiles:    If True, tall pages are also uploaded as tile crops.

    Returns:
        Summary dict:
            {
                "document_id":        str,
                "total_pages":        int,
                "pages_processed":    int,
                "total_chunks_saved": int,
                "failed_pages":       [int, ...],
            }
    """
    logger.info(f"[Orchestrator] Starting — document_id={document_id}, filepath={filepath}")


    logger.info("Step 1: Rendering PDF pages with PyMuPDF …")
    page_render_data = render_pdf_pages(
        pdf_path=filepath,
        document_id=document_id,
        enable_tiles=enable_tiles,
    )
    total_pages = len(page_render_data)
    logger.info(f"Step 1 done — {total_pages} pages rendered")

    system_prompt = _load_system_prompt()

    hierarchy = {
        "title":          None,
        "heading":        None,
        "sub_heading":    None,
        "sub_sub_heading": None,
    }

    total_chunks = 0
    failed_pages: list[int] = []

    sorted_page_nos = sorted(page_render_data.keys())

    for page_no in sorted_page_nos:
        render_info   = page_render_data[page_no]
        full_page_url = render_info.get("full_page_url")
        tile_urls     = render_info.get("tile_urls", [])

        if not full_page_url:
            logger.warning(f"Page {page_no}: no full-page URL — skipping VLM call")
            failed_pages.append(page_no)
            continue

        try:
            rag_objects, hierarchy, is_toc_index = _process_page(
                page_no=page_no,
                full_page_url=full_page_url,
                tile_urls=tile_urls,
                hierarchy=hierarchy,
                system_prompt=system_prompt,
                doc_description=doc_description,
                document_id=document_id,
            )

            if not rag_objects:
                logger.warning(f"Page {page_no}: no rag_objects returned")
                failed_pages.append(page_no)
                continue

            for split_no, rag_obj in enumerate(rag_objects, start=1):
                record = build_chunk_record(
                    rag_obj=rag_obj,
                    document_id=document_id,
                    page_no=page_no,
                    page_image_url=full_page_url,
                    page_split_no=split_no,
                    is_toc_index=is_toc_index,
                )
                try:
                    model_wrapper.post_object(record)
                    total_chunks += 1
                    logger.info(f"Page {page_no} chunk {split_no}: posted successfully")
                except Exception as post_err:
                    logger.error(f"Page {page_no} chunk {split_no}: post failed — {post_err}")

        except Exception as e:
            logger.error(f"Page {page_no}: orchestration error — {e}")
            logger.debug(traceback.format_exc())
            failed_pages.append(page_no)

    summary = {
        "document_id":        document_id,
        "total_pages":        total_pages,
        "pages_processed":    total_pages - len(failed_pages),
        "total_chunks_saved": total_chunks,
        "failed_pages":       failed_pages,
    }
    logger.info(f"[Orchestrator] Complete: {json.dumps(summary)}")
    return summary
