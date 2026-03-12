import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import typing
import json
import re

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.datamodel.document import DocItem, SectionHeaderItem, TableItem, PictureItem, TextItem

try:
    from document_processor.image_uploader import upload_image_to_cloud
except ImportError:
    from image_uploader import upload_image_to_cloud
    
logger = logging.getLogger(__name__)

class DoclingParser:
    def __init__(self):
        self.pipeline_options = PdfPipelineOptions()
        self.pipeline_options.generate_page_images = True
        self.pipeline_options.generate_picture_images = True
        self.pipeline_options.generate_table_images = True
        self.pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
        
        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF : PdfFormatOption(pipeline_options=self.pipeline_options)
            }
        )
    def _get_bbox(self, item: DocItem) -> Optional[tuple]:
        if item.prov and item.prov[0].bbox:
            return item.prov[0].bbox.as_tuple()
        return None

        if item.prov:
            return item.prov[0].page_no
        return None

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _extract_json(self, doc, conv_res) -> Dict[str, Any]:
        page_map: Dict[int, Dict[str, Any]] = {}

        for page in conv_res.pages:
            page_no = page.page_no + 1

            page_img = None
            if hasattr(page, "get_image"):
                page_img = page.get_image()
            elif hasattr(page, "image"):
                page_img = page.image

            page_img_url = (
                upload_image_to_cloud(page_img, page_no)
                if page_img is not None
                else None
            )

            page_map[page_no] = {
                "page_no": page_no,
                "page_image": page_img_url,
                "items": []   
            }

        for item, level in doc.iterate_items():
            if not item.prov:
                continue

            page_no = item.prov[0].page_no
            if page_no not in page_map:
                continue

            bbox = (
                item.prov[0].bbox.as_tuple()
                if item.prov and item.prov[0].bbox
                else None
            )

            item_dict = {
                "type": None,
                "page_no": page_no,
                "bbox": bbox
            }

            if isinstance(item, SectionHeaderItem):
                item_dict.update({
                    "type": "header",
                    "text": item.text,
                    "level": item.level
                })

            elif isinstance(item, TextItem):
                item_dict.update({
                    "type": "text",
                    "text": item.text
                })

            elif isinstance(item, TableItem):
                table_img_url = None
                table_img = item.get_image(doc)
                if table_img:
                    table_img_url = upload_image_to_cloud(table_img, page_no)
                table_text = ""
                table_markdown = None
                table_cells = []

                if hasattr(item, "export_to_dataframe"):
                    try:
                        df = item.export_to_dataframe(doc) 
                        table_text = df.to_markdown(index=False)
                    except Exception:
                        try:
                            table_text = df.to_string(index=False)
                        except Exception:
                            pass

                if hasattr(item, "export_to_markdown"):
                    try:
                        table_markdown = item.export_to_markdown(doc)
                    except Exception as e:
                        logger.warning(f"Failed to export table to markdown: {e}")
                
                # Cleanup
                table_text = self._clean_text(table_text)
                if table_markdown:
                    table_markdown = self._clean_text(table_markdown)

                if hasattr(item, "data") and hasattr(item.data, "grid"):
                    try:
                        unique_cells = {}
                        for r_idx, row in enumerate(item.data.grid):
                            for c_idx, cell in enumerate(row):
                                # Deduplicate based on the cell's starting position (if spans exist)
                                # or just object identity. Using start indices is safer/cleaner.
                                # Use getattr defaults just in case
                                start_row = getattr(cell, "start_row_offset_idx", r_idx)
                                start_col = getattr(cell, "start_col_offset_idx", c_idx)
                                
                                key = (start_row, start_col)
                                if key not in unique_cells:
                                    unique_cells[key] = {
                                        "text": getattr(cell, "text", ""),
                                        "row": start_row,
                                        "col": start_col,
                                        "row_span": getattr(cell, "row_span", 1),
                                        "col_span": getattr(cell, "col_span", 1),
                                        "bbox": cell.bbox.as_tuple() if getattr(cell, "bbox", None) else None
                                    }
                        table_cells = list(unique_cells.values())
                    except Exception as e:
                        logger.warning(f"Failed to extract table cells: {e}")

                item_dict.update({
                    "type": "table",
                    "text": table_text,
                    "markdown": table_markdown,
                    "cells": table_cells,
                    "image_url": table_img_url
                })


            elif isinstance(item, PictureItem):
                img_url = None
                img = item.get_image(doc)
                if img:
                    img_url = upload_image_to_cloud(img, page_no)

                item_dict.update({
                    "type": "image",
                    "image_url": img_url
                })

            else:
                continue

            page_map[page_no]["items"].append(item_dict)


        pages = [page_map[p] for p in sorted(page_map.keys())]
        return {"pages": pages}

    def _process_item(self, item: DocItem, doc: Any, page_no: int) -> Optional[Dict[str, Any]]:
        bbox = (
            item.prov[0].bbox.as_tuple()
            if item.prov and item.prov[0].bbox
            else None
        )

        item_dict = {
            "type": None,
            "page_no": page_no,
            "bbox": bbox
        }

        if isinstance(item, SectionHeaderItem):
            item_dict.update({
                "type": "header",
                "text": item.text,
                "level": item.level
            })

        elif isinstance(item, TextItem):
            item_dict.update({
                "type": "text",
                "text": item.text
            })

        elif isinstance(item, TableItem):
            table_img_url = None
            try:
                table_img = item.get_image(doc)
                if table_img:
                    table_img_url = upload_image_to_cloud(table_img, page_no)
            except Exception as e:
                logger.warning(f"Failed to extract/upload table image: {e}")
                
            table_text = ""
            table_markdown = None

            if hasattr(item, "export_to_dataframe"):
                try:
                    df = item.export_to_dataframe(doc) 
                    table_text = df.to_markdown(index=False)
                except Exception:
                    try:
                        table_text = df.to_string(index=False)
                    except Exception:
                        pass

            if hasattr(item, "export_to_markdown"):
                try:
                    table_markdown = item.export_to_markdown(doc)
                except Exception as e:
                    logger.warning(f"Failed to export table to markdown: {e}")

            table_text = self._clean_text(table_text)
            if table_markdown:
                table_markdown = self._clean_text(table_markdown)

            table_cells = []
            if hasattr(item, "data") and hasattr(item.data, "grid"):
                try:
                    unique_cells = {}
                    for r_idx, row in enumerate(item.data.grid):
                        for c_idx, cell in enumerate(row):
                            start_row = getattr(cell, "start_row_offset_idx", r_idx)
                            start_col = getattr(cell, "start_col_offset_idx", c_idx)
                            key = (start_row, start_col)
                            if key not in unique_cells:
                                unique_cells[key] = {
                                    "text": getattr(cell, "text", ""),
                                    "row": start_row,
                                    "col": start_col,
                                    "row_span": getattr(cell, "row_span", 1),
                                    "col_span": getattr(cell, "col_span", 1),
                                    "bbox": cell.bbox.as_tuple() if getattr(cell, "bbox", None) else None
                                }
                    table_cells = list(unique_cells.values())
                except Exception as e:
                    logger.warning(f"Failed to extract table cells: {e}")

            item_dict.update({
                "type": "table",
                "text": table_text,
                "markdown": table_markdown,
                "cells": table_cells,
                "image_url": table_img_url
            })

        elif isinstance(item, PictureItem):
            img_url = None
            img = item.get_image(doc)
            if img:
                img_url = upload_image_to_cloud(img, page_no)

            item_dict.update({
                "type": "image",
                "image_url": img_url
            })

        else:
            return None

        return item_dict

    def process_pdf_stream(
        self,
        pdf_path: str,
    ) -> typing.Generator[Dict[str, Any], None, None]:
        """
        Yeilds page dictionaries one by one.
        """
        logger.info(f"Starting Docling conversion for stream: {pdf_path}")
        con_res = self.doc_converter.convert(pdf_path)
        doc = con_res.document

        page_image_map = {}
        for page in con_res.pages:
            page_no = page.page_no + 1
            page_img = None
            if hasattr(page, "get_image"):
                page_img = page.get_image()
            elif hasattr(page, "image"):
                page_img = page.image

            page_img_url = (
                upload_image_to_cloud(page_img, page_no)
                if page_img is not None
                else None
            )
            page_image_map[page_no] = page_img_url

        current_page_no = -1
        current_page_items = []
        
        
        for item, level in doc.iterate_items():
            if not item.prov:
                continue
            
            page_no = item.prov[0].page_no

            if current_page_no == -1:
                current_page_no = page_no
            
            if page_no != current_page_no:

                yield {
                    "page_no": current_page_no,
                    "page_image": page_image_map.get(current_page_no),
                    "items": current_page_items
                }
                current_page_no = page_no
                current_page_items = []
            
            item_dict = self._process_item(item, doc, page_no)
            if item_dict:
                current_page_items.append(item_dict)
                
        if current_page_no != -1:
             yield {
                "page_no": current_page_no,
                "page_image": page_image_map.get(current_page_no),
                "items": current_page_items
            }

    def process_pdf(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process PDF using Docling and return a flattened JSON
        containing text, headers, tables, figures, images, bbox, page_no.
        """
        logger.info(f"Starting Docling conversion for: {pdf_path}")

        con_res = self.doc_converter.convert(pdf_path)
        doc = con_res.document

        extracted_json = self._extract_json(doc, con_res)

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            out_path = Path(output_dir) / "document.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(extracted_json, f, indent=2, ensure_ascii=False)

        return extracted_json
