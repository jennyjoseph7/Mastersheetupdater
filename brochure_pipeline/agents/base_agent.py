import json
import re
import ast
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(dirname(abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from typing import Any, Dict, Optional
from autobot_agents.brochure_pipeline.bp_utils import get_logger

logger = get_logger(__name__)


class BaseAgent:
    """
    Minimal base agent used by other agents (e.g., ConverterAgent).
    Provides basic init and a helper to extract/parse JSON from LLM responses.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        logger.info(f"{self.__class__.__name__} initialized.")

    def _extract_text(self, response: Any) -> str:
        """
        Normalize possible LLM response shapes to a single text string.
        Supports:
          - plain string
          - dict with keys like 'content', 'message', 'text'
          - dict with 'choices' (OpenAI-like) where choices[0].message.content or choices[0].text exists
        """
        if response is None:
            return ""
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            # common shapes
            if "content" in response and isinstance(response["content"], str):
                return response["content"]
            if "message" in response:
                msg = response["message"]
                if isinstance(msg, dict) and "content" in msg:
                    return msg["content"]
                if isinstance(msg, str):
                    return msg
            if "text" in response and isinstance(response["text"], str):
                return response["text"]
            if "choices" in response and isinstance(response["choices"], list) and response["choices"]:
                first = response["choices"][0]
                if isinstance(first, dict):
                    if "message" in first and isinstance(first["message"], dict) and "content" in first["message"]:
                        return first["message"]["content"]
                    if "text" in first and isinstance(first["text"], str):
                        return first["text"]
                    if "content" in first and isinstance(first["content"], str):
                        return first["content"]
        # fallback: stringify
        try:
            return str(response)
        except Exception:
            return ""

    def extract_json_from_llm_response(self, response: Any) -> Dict[str, Any]:
        """
        Try to parse JSON from an LLM response. Returns a dict with the parsed JSON if found,
        otherwise returns {'raw': <text>}.

        Strategy:
          1. Normalize response to text.
          2. Search for the first JSON object/array substring.
          3. Try json.loads -> ast.literal_eval as fallback.
        """
        text = self._extract_text(response).strip()
        if not text:
            logger.warning("Empty LLM response received.")
            return {"raw": ""}

        # Try to parse entire text first
        try:
            parsed = json.loads(text)
            return {"data": parsed}
        except Exception:
            pass

        # Find first JSON-looking substring (object or array)
        m = re.search(r'(\{(?:.|\s)*\}|\[(?:.|\s)*\])', text, re.DOTALL)
        if m:
            candidate = m.group(1)
            # Try json.loads
            try:
                parsed = json.loads(candidate)
                return {"data": parsed}
            except Exception:
                # Try ast.literal_eval (more forgiving)
                try:
                    parsed = ast.literal_eval(candidate)
                    return {"data": parsed}
                except Exception as e:
                    logger.debug(f"Failed to parse candidate JSON with json and ast: {e}")

        # If no JSON parsed, return raw text for debugging
        logger.warning("Could not parse JSON from LLM response; returning raw text.")
        return {"raw": text}