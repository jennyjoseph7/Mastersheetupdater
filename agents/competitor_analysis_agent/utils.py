import re
import json

def extract_valid_json_blocks(text, expected_keys=None):
    """
    Extracts all candidate JSON blocks from the text and returns the first valid one
    that matches optional expected top-level keys.

    Args:
        text (str): Raw text output from an LLM that may contain embedded JSON.
        expected_keys (list, optional): List of required top-level keys in the JSON object.

    Returns:
        dict: Parsed JSON object if a valid one is found and meets requirements.

    Raises:
        ValueError: If no valid JSON object is found or none meet key expectations.
    """
    candidates = []
    brace_stack = []
    start_index = None

    for i, char in enumerate(text):
        if char == '{':
            if not brace_stack:
                start_index = i
            brace_stack.append('{')
        elif char == '}':
            if brace_stack:
                brace_stack.pop()
                if not brace_stack and start_index is not None:
                    json_block = text[start_index:i+1]
                    candidates.append(json_block)

    # Try parsing each candidate
    for idx, candidate in enumerate(candidates):
        try:
            parsed = json.loads(candidate)
            if expected_keys:
                if all(key in parsed for key in expected_keys):
                    return parsed
            else:
                return parsed
        except json.JSONDecodeError:
            continue  # Try next candidate

    raise ValueError("❌ No valid JSON object found or none matched the expected structure.")

# ===== Example usage =====
if __name__ == "__main__":
    llm_output = """Some intro text...
    ```json
    {
      "comparisons": {
        "A vs B": { "price": { "A": "10", "B": "20" } }
      },
      "common_points": ["shared feature"],
      "key_differences": { "A vs B": { "price": "A is cheaper" } },
      "user_choice_justification": { "reason": "A is affordable." }
    }
    ```... some outro."""

    try:
        json_data = extract_valid_json_blocks(
            llm_output,
            expected_keys=["comparisons", "common_points", "key_differences", "user_choice_justification"]
        )
        print("✅ Extracted and validated JSON:\n", )
    except ValueError as e:
        print(str(e))
