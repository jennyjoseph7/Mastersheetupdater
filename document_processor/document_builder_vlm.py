import typing
from copy import deepcopy
import json
import os
import logging
from ai_service import ai_service 

logger = logging.getLogger(__name__)

class VLMHierarchyProcessor:
    """
    semantic hierarchy processor for RAG.
    Converts page-level PDF extraction into meaningful RAG objects
    using a Vision Language Model.
    """

    def __init__(
        self,
        model_identifier: str = "gcp-gemini-2.5-flash-lite",
        temperature: float = 0.2,
        prompts_path: str = "prompts.json"
    ):
        self.model_identifier = model_identifier
        self.temperature = temperature
        self.hierarchy_state = {
            "title": None,
            "heading": None,
            "sub_heading": None,
            "sub_sub_heading": None
        }
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, prompts_path)
        
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                self.prompts = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load prompts from {full_path}: {e}")
            self.prompts = {
                "vlm_system_prompt": "You are a helpful AI assistant.",
                "vlm_user_prompt_template": "Analyze this page: {page_json}"
            }

    def process_doc(
        self,
        doc_json: dict,
        model_identifier: typing.Optional[str] = None,
        temperature: typing.Optional[float] = None
    ) -> dict:
        """
        Process an entire document (all pages) and return a consolidated JSON.
        """
        all_rag_objects = []
        pages = doc_json.get("pages", [])
        total_pages = len(pages)
        
        pages.sort(key=lambda x: x.get("page_no", 0))

        for i, page in enumerate(pages):
            page_no = page.get("page_no", "?")
            logger.info(f"Processing page {page_no}/{total_pages}...")
            

            
            page_objects = self.process_page(
                page_json=page,
                model_identifier=model_identifier,
                temperature=temperature
            )
            all_rag_objects.extend(page_objects)

        return {
            "rag_objects": all_rag_objects,
            "final_hierarchy": self.hierarchy_state
        }

    def process_page(
        self,
        page_json: dict,
        model_identifier: typing.Optional[str] = None,
        temperature: typing.Optional[float] = None,
        description: str = "" 
    ) -> list:
        """
        Process a single page and return semantic RAG-ready objects.
        """

        payload = {
            "page_no": page_json.get("page_no"),
            "page_image": page_json.get("page_image"), # Keep for VLM
            "previous_hierarchy": deepcopy(self.hierarchy_state),
            "items": self._compact_items(page_json.get("items", []))
        }

        user_query = self._user_prompt(payload, description)
        
        response = ai_service.get_vlm_response(
            system_prompt=self._system_prompt(),
            user_query=user_query,
            images=[payload["page_image"]] if payload.get("page_image") else None,
            temperature= temperature if temperature is not None else self.temperature,
            model_identifier= model_identifier or self.model_identifier,
        )

        parsed = self._safe_parse(response)

        if "updated_hierarchy" in parsed:
            self.hierarchy_state.update(parsed["updated_hierarchy"])

        rag_objects = parsed.get("rag_objects", [])
        original_items = page_json.get("items", [])
        
        # Manual Injection: Restore cells and ensures images are linked
        for obj in rag_objects:
             if obj.get("tables"):
                 for table in obj["tables"]:
                     # 2. Table Image via ref_id 
                     ref_id = table.get("ref_id")
                     if ref_id is not None and isinstance(ref_id, int) and 0 <= ref_id < len(original_items):
                         original_item = original_items[ref_id]
                         if original_item.get("type") == "table":
                             if not table.get("table_image_url") and original_item.get("image_url"):
                                 table["table_image_url"] = original_item.get("image_url")


        final_objects = []
        for idx, obj in enumerate(rag_objects):

            if not obj.get("page_no"):
                 p_no = page_json.get("page_no")
                 if p_no:
                     obj["page_no"] = p_no
                 elif obj.get("metadata") and obj["metadata"].get("page"):
                     obj["page_no"] = obj["metadata"].get("page")
            
            obj["page_split_no"] = idx + 1

            if page_json.get("page_image"):
                obj["page_image_url"] = page_json.get("page_image")


            if "metadata" in obj and "hierarchy_path" in obj["metadata"]:
                obj["hierarchy_path"] = obj["metadata"].pop("hierarchy_path")
            
            if "hierarchy_path" not in obj:
                obj["hierarchy_path"] = deepcopy(self.hierarchy_state)


            if isinstance(obj.get("hierarchy_path"), dict):
                h = obj["hierarchy_path"]
                obj["title"] = h.get("title")
                obj["heading"] = h.get("heading")
                obj["sub_heading"] = h.get("sub_heading")
                obj["sub_sub_heading"] = h.get("sub_sub_heading")

            if "question" not in obj:
                obj["question"] = []
            if "keywords" not in obj:
                obj["keywords"] = []

            final_objects.append(obj)
            
        return final_objects
                                 
        return rag_objects



    def _compact_items(self, items: list) -> list:
        """
        Reduce token usage: keep only fields required for reasoning.
        Filters out bbox, table cells, and prefers markdown over raw text.
        """
        compact = []

        for i, it in enumerate(items):
            obj = {
                "type": it.get("type"),
                "page_no": it.get("page_no"),
                "ref_id": i,
                "bbox": it.get("bbox")
            }
            
            if it.get("type") == "table":
                obj["table_text"] = it.get("markdown") or it.get("text")
                if it.get("image_url"):
                     obj["image_url"] = it.get("image_url")
            elif it.get("type") == "image":
                 if it.get("image_url"):
                     obj["image_url"] = it.get("image_url")
            else:
                obj["text"] = it.get("text")

            if it.get("type") == "header":
                obj["level"] = it.get("level")

            compact.append(obj)

        return compact


    def _system_prompt(self) -> str:
        return self.prompts.get("vlm_system_prompt", "")

    def _user_prompt(self, payload: dict, description: str = "") -> str:
        template = self.prompts.get("vlm_user_prompt_template", "")
        payload_str = json.dumps(payload, indent=2)
        try:
             return template.format(page_json=payload_str, description=description)
        except KeyError:
            # Fallback if template keys don't match
            return f"{template}\n\nDocument Description: {description}\n\nContext:\n{payload_str}"

    def _safe_parse(self, text: str) -> dict:
        try:
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text)
        except Exception:
            return {
                "updated_hierarchy": {},
                "rag_objects": []
            }
