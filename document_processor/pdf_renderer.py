
import io
import time
import requests
import fitz                         
from PIL import Image
from gryd_worker import gryd_helpers as hp
from document_processor.utils import gryd_image_upload

logger = hp.get_logger(__name__)


RENDER_SCALE       = 2.0      # Matrix scale factor (roughly 144 DPI at 2x)
TILE_OVERLAP_RATIO = 0.15     # 15 % vertical overlap between top and bottom tiles
MIN_PAGE_HEIGHT_PX = 1200     # Only tile pages taller than this (after scaling)
TILE_QUALITY       = 85       # JPEG quality for tile images


def _open_pdf(pdf_path: str) -> fitz.Document:
    """Open a PDF from a local path or HTTP(S) URL."""
    if pdf_path.startswith("http://") or pdf_path.startswith("https://"):
        logger.info(f"Downloading PDF from URL: {pdf_path}")
        resp = requests.get(pdf_path, timeout=60)
        resp.raise_for_status()
        return fitz.open("pdf", resp.content)
    return fitz.open(pdf_path)


def _render_page(page: fitz.Page, scale: float = RENDER_SCALE) -> Image.Image:
    """Render a single fitz Page to a PIL Image."""
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def _make_tiles(
    page_img: Image.Image,
    overlap_ratio: float = TILE_OVERLAP_RATIO,
) -> list[Image.Image]:
    """
    Split a tall page image into two overlapping vertical tiles:
        tile_0 — top portion (0 → split + overlap)
        tile_1 — bottom portion (split - overlap → end)

    Returns an empty list if the page is too short to warrant tiling.
    """
    w, h = page_img.size
    if h < MIN_PAGE_HEIGHT_PX:
        return []

    overlap_px = int(h * overlap_ratio)
    mid = h // 2

    top_tile    = page_img.crop((0, 0,               w, mid + overlap_px))
    bottom_tile = page_img.crop((0, mid - overlap_px, w, h))
    return [top_tile, bottom_tile]


def render_pdf_pages(
    pdf_path: str,
    document_id: str,
    enable_tiles: bool = True,
    render_scale: float = RENDER_SCALE,
) -> dict:
    """
    Render every page of a PDF and upload images to the Gryd CDN.

    Args:
        pdf_path:     Local file path or HTTP(S) URL pointing to the PDF.
        document_id:  Unique document identifier — used as the CDN filename prefix.
        enable_tiles: If True, tall pages are also uploaded as top/bottom tile crops.
        render_scale: PyMuPDF render scale (2.0 ≈ 144 DPI — good balance of quality
                      and VLM token cost).

    Returns:
        {
            page_no: {
                "full_page_url": str | None,
                "tile_urls":     [str, ...],
            },
            ...
        }
    """
    doc = _open_pdf(pdf_path)
    total_pages = len(doc)
    logger.info(f"PDF opened — {total_pages} pages — document_id={document_id}")

    result: dict = {}

    for idx in range(total_pages):
        page_no = idx + 1   # 1-indexed
        page_data: dict = {"full_page_url": None, "tile_urls": []}

        try:
            t0 = time.perf_counter()
            page = doc.load_page(idx)
            page_img = _render_page(page, scale=render_scale)
            render_ms = (time.perf_counter() - t0) * 1000
            logger.info(
                f"Page {page_no}: rendered {page_img.size[0]}×{page_img.size[1]}px "
                f"in {render_ms:.0f} ms"
            )
            full_url = gryd_image_upload(
                page_img,
                page_no,
                media_type="image",
                document_name=document_id,
            )
            if full_url:
                page_data["full_page_url"] = full_url
                logger.info(f"Page {page_no}: full-page CDN URL = {full_url}")
            else:
                logger.warning(f"Page {page_no}: full-page upload returned None")

            if enable_tiles:
                tiles = _make_tiles(page_img)
                for tile_idx, tile_img in enumerate(tiles):
                    tile_label = f"{page_no}_tile{tile_idx}"
                    tile_url = gryd_image_upload(
                        tile_img,
                        tile_label,
                        media_type="image",
                        document_name=document_id,
                    )
                    if tile_url:
                        page_data["tile_urls"].append(tile_url)
                        logger.info(f"Page {page_no} tile {tile_idx}: CDN URL = {tile_url}")
                    else:
                        logger.warning(f"Page {page_no} tile {tile_idx}: upload returned None")

        except Exception as e:
            logger.error(f"Page {page_no}: render/upload failed — {e}")

        result[page_no] = page_data

    doc.close()
    logger.info(
        f"Rendering complete — {sum(1 for v in result.values() if v['full_page_url'])} "
        f"/ {total_pages} pages uploaded"
    )
    return result
