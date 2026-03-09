import json
import re
from bp_utils import get_logger
from ai_service import ai_service_app

logger = get_logger(__name__)
MODEL_ID = 'gcp-gemini-2.5-flash' 

def extract_hierarchical_data_from_markdown(markdown_text, context_text=""):
    """
    Uses LLM to convert Automotive Markdown Tables into structured, hierarchical JSON.
    Enforces strict row-by-row extraction for car specifications.
    """
    if not markdown_text or len(markdown_text) < 20:
        return {}

    # --- DEBUG: Log input length ---
    logger.info(f"--- DEBUG: Structuring Table (Length: {len(markdown_text)} chars) ---")

    prompt = f"""
You are an expert Automotive Data Specialist. Your ONLY job is to convert Markdown car specification tables into strict JSON.
You must transcribe EVERY SINGLE ROW. Do not summarize. Do not skip rows.

INPUT CONTEXT:
The input is a "Technical Specifications" table for a vehicle.
It contains SECTIONS (e.g., Dimensions, Engine, Brakes) and VARIANTS (Columns like Petrol, Diesel, CNG).

--------------------------------------------------
STRICT RULES:
1. **FULL EXTRACTION:** You must extract data for every single row in the table. If the table has 50 rows, your JSON must have 50 entries.
2. **SECTION DETECTION:**
   - The table has section headers like "DIMENSIONS", "ENGINE", "WEIGHT", "BRAKES".
   - Use these as the ROOT keys of your JSON.
   - If a row says "TECHNICAL SPECIFICATIONS", ignore it as a root key; look deeper for the actual sub-sections.
3. **COLUMN MAPPING:**
   - Identify the Variant Names from the header row (e.g., "PETROL", "CNG", "MT", "AMT", "LXi", "VXi").
   - Map every value to these keys.
4. **MERGED CELLS:** If a value is the same for all columns (e.g., "Disc Brakes" for all variants), repeat the value for every variant key.

--------------------------------------------------
EXAMPLE (Car Brochure Case):

**Input Markdown:**
| ENGINE | Petrol | Diesel |
| Displacement | 1197 cc | 1498 cc |
| Max Power | 88 bhp | 98 bhp |
| DIMENSIONS | | |
| Length (mm) | 3995 | 3995 |
| Width (mm) | 1735 | 1735 |
| BRAKES | | |
| Front | Disc | Disc |

**Output JSON:**
{{
  "ENGINE": {{
     "Displacement": {{ "Petrol": "1197 cc", "Diesel": "1498 cc" }},
     "Max Power": {{ "Petrol": "88 bhp", "Diesel": "98 bhp" }}
  }},
  "DIMENSIONS": {{
     "Length (mm)": {{ "Petrol": "3995", "Diesel": "3995" }},
     "Width (mm)": {{ "Petrol": "1735", "Diesel": "1735" }}
  }},
  "BRAKES": {{
     "Front": {{ "Petrol": "Disc", "Diesel": "Disc" }}
  }}
}}

--------------------------------------------------
REAL INPUT DATA:
{markdown_text}
"""

    messages = [
        {"role": "system", "content": "You are a rigid data extractor for car brochures. You never skip rows. You output valid JSON only."},
        {"role": "user", "content": prompt}
    ]

    try:
        response = ai_service_app.get_llm_response(
            messages=messages,
            model_identifier=MODEL_ID,
            temperature=0.0
        )

        if isinstance(response, str):
            # --- DEBUG: Log the first 500 chars to check structure ---
            logger.info(f"--- DEBUG: Raw LLM Response Start ---\n{response[:500]}...")
            
            # 1. Clean Markdown wrappers
            clean_str = re.sub(r'```json\s*|```', '', response).strip()
            
            # 2. Extract JSON object
            match = re.search(r'(\{.*\})', clean_str, re.DOTALL)
            if match:
                clean_str = match.group(1)
            
            return json.loads(clean_str)

        return response

    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON Parsing Error: {e}")
        logger.error(f"Bad JSON content: {clean_str[:500]}...") 
        return {}
    except Exception as e:
        logger.error(f"❌ LLM Extraction Error: {e}")
        return {}