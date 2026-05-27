import os
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
import json
import re
import time
from ai_service import ai_service
from gryd_worker import gryd_helpers as hp

logger = hp.get_logger(__name__)

MODEL_IDENTIFIER = os.environ.get("VLM_MODEL_IDENTIFIER","gcp-gemini-3.1-flash-lite-preview")
MAX_VLM_RETRIES  = 2
VLM_RETRY_DELAY  = 1      




def build_user_query(
    page_no: int,
    hierarchy: dict,
    doc_description: str,
) -> str:
    """
    Build the per-page user query sent alongside the page images.

    Unlike the original pipeline, we do NOT include extracted text elements
    here — the VLM reads all content directly from the images.

    Args:
        page_no:         1-indexed page number.
        hierarchy:       Running hierarchy state carried from the previous page.
        doc_description: Short description of the document for contextual chunking.

    Returns:
        Multi-line string query.
    """
    parts = [
        f"Page Number: {page_no}",
        f"Document Description: {doc_description}",
        f"Previous Page Hierarchy: {json.dumps(hierarchy)}",
        (
            "Instructions: Analyze the page image(s) provided. "
            "IMAGE_0 is the full rendered page. "
            "IMAGE_1 and IMAGE_2 (if present) are overlapping top/bottom tile crops "
            "of the same page — use them to read fine text and details more clearly. "
            "Extract all semantic content visible in the images and return structured JSON."
        ),
    ]
    return "\n\n".join(parts)




def _repair_json(s: str) -> str:
    """Escape internal unescaped double-quotes that break JSON parsing."""
    s = re.sub(r'(\w)"(\w)',    r'\1\"\2', s)
    s = re.sub(r'(\w)"(\s+\w)', r'\1\"\2', s)
    s = re.sub(r'(\w\s+)"(\w)', r'\1\"\2', s)
    return s


def parse_vlm_response(raw_text: str) -> dict | None:
    """
    Parse and validate the VLM's raw text response as JSON.

    Handles:
      - Markdown code fence stripping
      - JSON block extraction
      - Common quote-escaping issues

    Returns:
        Parsed dict on success, None on failure.
    """
    if not raw_text:
        return None

    cleaned = raw_text.strip()

    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$",          "", cleaned).strip()

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        logger.warning("No JSON object found in VLM response")
        return None

    cleaned = match.group(0)


    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(_repair_json(cleaned))
    except json.JSONDecodeError:
        logger.warning("JSON parse failed even after repair")
        return None



def call_vlm_with_retry(
    user_query: str,
    system_prompt: str,
    images: list[str],
    model_identifier: str = MODEL_IDENTIFIER,
    max_retries: int = MAX_VLM_RETRIES,
    retry_delay: float = VLM_RETRY_DELAY,
) -> tuple[dict | None, str | None]:
    """
    Call the VLM and retry on API errors or unparseable JSON responses.

    Args:
        user_query:       Per-page text query (metadata + instructions).
        system_prompt:    The full VLM system prompt.
        images:           List of CDN image URLs to pass to the VLM.
                          [full_page_url, tile_url_0, tile_url_1, ...]
        model_identifier: VLM model identifier string.
        max_retries:      Number of additional retries after the first attempt.
        retry_delay:      Seconds to wait between retries.

    Returns:
        (parsed_dict, raw_response_text)
        parsed_dict is None if all attempts failed.
    """
    raw_response = None
    last_error   = None

    for attempt in range(1, max_retries + 2):   
        try:
            logger.info(f"VLM call attempt {attempt} — {len(images)} image(s)")

            raw_response = ai_service.get_vlm_response(
                user_query=user_query,
                system_prompt=system_prompt,
                images=images,
                temperature=0,
                model_identifier=model_identifier,
                response_mime_type="application/json",
            )

            logger.info(f"VLM response length: {len(raw_response or '')}")
            parsed = parse_vlm_response(raw_response)

            if parsed is not None:
                return parsed, raw_response

            logger.warning(f"Attempt {attempt}: JSON parse failed")

        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt}: VLM call raised exception — {e}")

        if attempt <= max_retries:
            logger.info(f"Retrying VLM in {retry_delay}s …")
            time.sleep(retry_delay)

    logger.error(f"VLM call failed after {max_retries + 1} attempts. Last error: {last_error}")
    return None, raw_response
