import json
import re
import ast
import io
import logging
from pypdf import PdfReader
from bp_utils import get_logger
from ai_service import ai_service_app

logger = get_logger(__name__)

# Config
MODEL_ID = 'gcp-gemini-2.5-flash'

def extract_text_from_pdf_path(file_path):
    """
    Reads a local PDF file and extracts raw text using pypdf.
    """
    logger.info(f"Extracting raw text from: {file_path}")
    try:
        reader = PdfReader(file_path)
        full_text = []
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                full_text.append(f"--- PAGE {i+1} START ---\n{text}\n--- PAGE {i+1} END ---")
        
        combined_text = "\n\n".join(full_text)
        return combined_text

    except Exception as e:
        logger.error(f"PyPDF extraction failed: {e}")
        return None

def extract_hierarchical_data(raw_text):
    """
    Uses Gemini to convert raw text into a Structured Dictionary with Metadata.
    """
    if not raw_text:
        return {}

    prompt = """
    You are an expert Automotive Data Analyst.
    The text below is the RAW CONTENT of a car brochure.
    
    YOUR TASK:
    1. Identify the **Car Brand** (e.g., "Maruti Suzuki", "Hyundai", "Jeep").
    2. Identify the **Car Model Name** (e.g., "Meridian", "Brezza", "Baleno").
    3. Reconstruct the table data into a **Hierarchical Python Dictionary**.

    
    1. OUTPUT PURE JSON ONLY
    - Start directly with `{` and end with `}`.
    - NO markdown code blocks.
    - NO comments.
    - NO placeholders such as "...".
    - NO trailing commas.
    - Use ONLY valid JSON syntax.

    2. STRUCTURE:
    You must return a JSON object with EXACTLY two top-level keys: "meta" and "data".

    The structure MUST be:

    {
    "meta": {
        "brand": "Extract Brand Name Here or null",
        "car_name": "Extract Car Model Name Here or null"
    },
    "data": {
        "Safety": {
        "Airbags": {
            "LXi": "Not Available",
            "VXi": "2 Airbags"
        }
        },
        "Infotainment": {}
    }
    }

    IMPORTANT:
    - This is a STRUCTURAL EXAMPLE ONLY.
    - Do NOT copy example values.
    - Do NOT include empty placeholder keys unless data exists.

    3. DATA EXTRACTION RULES (Apply to the "data" block):
    - Organize features by SECTION (Safety, Infotainment, Engine, etc.).
    - Section names MUST NOT be treated as features.
    - Inside each section:
    - Keys = Feature names EXACTLY as written in the brochure.
    - Values = { Variant: Value }
    - Use ONLY double quotes for all keys and values.
    - Use "Available" / "Not Available" exactly as strings.


    --------------------------------------------------
    RAW PDF TEXT:
    --------------------------------------------------
    """ + raw_text

    messages = [{"role": "user", "content": prompt}]
    
    try:
        response = ai_service_app.get_llm_response(
            messages=messages,
            model_identifier=MODEL_ID,
            temperature=0.0
        )
        
        if isinstance(response, str):
            # Clean Markdown wrappers
            clean_str = re.sub(r'```python\s*|```json\s*|```', '', response).strip()
            
            # Extract dictionary part
            match = re.search(r'(\{.*\})', clean_str, re.DOTALL)
            if match:
                clean_str = match.group(1)
            
            # Parse to ensure it is valid Python/JSON
            data = ast.literal_eval(clean_str)
            return data
            
        return response

    except Exception as e:
        logger.error(f"Error from ai_service: {e}")
        return {}

def process_brochure_to_structure(file_path):
    """
    Main entry point for the pipeline.
    Returns a JSON string representation of the brochure, 
    which serves as the 'Brochure Text' for subsequent agents.
    """
    # 1. Extract Raw Text
    raw_text = extract_text_from_pdf_path(file_path)
    
    if not raw_text:
        logger.error("Failed to extract raw text.")
        return ""

    # 2. Structure with Gemini
    structured_dict = extract_hierarchical_data(raw_text)
    
    # 3. Return as JSON String
    return json.dumps(structured_dict, indent=2)