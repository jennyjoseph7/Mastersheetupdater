import os
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from gryd_worker import gryd_helpers as hp

logger = hp.get_logger(__name__)


def build_chunk_record(
    rag_obj: dict,
    document_id: str,
    page_no: int,
    page_image_url: str | None,
    page_split_no: int,
    is_toc_index: bool = False,
) -> dict:
    """
    Map a single VLM rag_object to the chunk_saver model schema.

    Schema fields:
        document_id      – pass through
        title            – from rag_obj
        heading          – from rag_obj
        sub_heading      – from rag_obj
        sub_sub_heading  – from rag_obj
        text_content     – from rag_obj (required — fallback to heading)
        page_no          – pass through
        page_split_no    – position within the page's rag_objects list
        page_image_url   – full-page CDN URL
        images           – [{url, caption}] — url is null (no ref_id resolution)
        tables           – [{table_text, table_summary, table_image_url, ref_id}]
        hierarchy_path   – from rag_obj.metadata.hierarchy_path
        metadata         – section_type, section_id, variant_tags, page
        question         – string list
        keywords         – string list
        it_is_toc_index  – bool

    Args:
        rag_obj:        Single rag_object dict from the VLM JSON response.
        document_id:    Document identifier.
        page_no:        1-indexed page number.
        page_image_url: CDN URL of the full rendered page image.
        page_split_no:  Index of this chunk within the page (1-based).
        is_toc_index:   Whether the page was classified as a TOC/Index page.

    Returns:
        dict ready to be posted to the chunk_saver model.
    """
    text_content = rag_obj.get("text_content")
    if not text_content or str(text_content).strip().lower() in ("none", ""):
        text_content = (
            rag_obj.get("heading")
            or rag_obj.get("title")
            or "N/A"
        )

    metadata_block = rag_obj.get("metadata", {})
    hierarchy_path = metadata_block.get(
        "hierarchy_path",
        {
            "title":          rag_obj.get("title"),
            "heading":        rag_obj.get("heading"),
            "sub_heading":    rag_obj.get("sub_heading"),
            "sub_sub_heading": rag_obj.get("sub_sub_heading"),
        },
    )

    images = []
    for img in rag_obj.get("images") or []:
        images.append({
            "url":     img.get("url"),        
            "caption": img.get("caption", ""),
        })

    tables = []
    for tbl in rag_obj.get("tables") or []:
        tables.append({
            "table_text":      tbl.get("table_text", ""),
            "table_summary":   tbl.get("table_summary", ""),
            "table_image_url": tbl.get("table_image_url"),   
            "ref_id":          tbl.get("ref_id"),
        })

    record = {
        "document_id":     document_id,
        "title":           rag_obj.get("title"),
        "heading":         rag_obj.get("heading"),
        "sub_heading":     rag_obj.get("sub_heading"),
        "sub_sub_heading": rag_obj.get("sub_sub_heading"),
        "text_content":    text_content,
        "page_no":         page_no,
        "page_split_no":   page_split_no,
        "page_image_url":  page_image_url,
        "images":          images,
        "tables":          tables,
        "hierarchy_path":  hierarchy_path,
        "metadata": {
            "section_type": rag_obj.get("section_type"),
            "section_id":   rag_obj.get("section_id", ""),
            "variant_tags": rag_obj.get("variant_tags", {}),
            "page":         metadata_block.get("page", page_no),
        },
        "question":        rag_obj.get("question", []),
        "keywords":        rag_obj.get("keywords", []),
        "it_is_toc_index": is_toc_index,
    }

    return record
