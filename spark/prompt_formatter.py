import os
import re
import time
from transformers import AutoModelForCausalLM, AutoTokenizer

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

SYSTEM_PROMPT = """You are a background prompt formatter. Your only job is to rewrite the user input as one sentence.

Rules (follow exactly):
- Output ONLY: Change the background to [location] with [details from input].
- Use ONLY words the user gave you. Do NOT add any new words, adjectives, or descriptions.
- ONE sentence. Stop at the first period.
- NEVER add: majestic, stunning, beautiful, dramatic, sweeping, or any adjective the user did not write.
- NEVER mention: camera, lens, angle, view, horizon, survey, aerial, overhead, or shot type.
- IGNORE any camera/angle/view words in the input silently — do not include them in output.

Example:
Input: kyoto temple district, morning fog
Output: Change the background to a Kyoto temple district with morning fog.

Example:
Input: sunset beach, golden hour, ocean waves
Output: Change the background to a sunset beach with golden hour light and ocean waves.

Example:
Input: mountain glacier, crevasse patterns
Output: Change the background to a mountain glacier with crevasse patterns.

Example:
Input: background, top-down aerial view of bellendur, camera directly above
Output: Change the background to Bellandur lake."""

STRIP_PATTERNS = [
    r"\bhigh\b",
    r"\baerial\b",
    r"\btop\s+view\b",
    r"\bview\s+of\b",
    r"\b8k\b",
    r"\bdslr\b",
    r"\bresolution\b",
    r"\bultra\s+realistic\b",
    r"camera\s+\w+[^,\.]{0,40}",
    r"survey\s+style",
    r"alpine\s+survey[^,\.]{0,20}",
    r"aerial\s+view",
    r"top[\s-]?down(?: view)?",
    r"bird'?s[\s-]?eye(?: view)?",
    r"drone\s+(?:shot|view)",
    r"overhead(?: view| shot)?",
    r"directly above",
    r"above at \d+[^,\.]{0,20}",
    r"at \d+\s*degrees?[^,\.]{0,20}",
    r"(?:90|45)[\s-]?degrees?",
    r"map[\s-]?like\s+perspective",
    r"no horizon",
    r"patterns?\s+visible",
    r"clearly visible",
    r"close[\s-]?up(?: shot)?",
    r"wide[\s-]?shot",
    r"low[\s-]?angle(?: shot)?",
    r"high[\s-]?angle(?: shot)?",
    r"\bpov\b",
    r"fisheye(?: lens)?",
    r"(?:side|front|rear|eye[\s-]?level)\s+view",
    r"neutral outdoor background",
    r",?\s*while preserving all the details of the car\.?",
    r",?\s*preserving all the details of the car\.?",
]

VIEW_TERMS = re.compile(
    r" (background|top[\s-]?down|aerial|camera|directly|above|below|survey|style|"
    r"overhead|bird.?s.?eye|drone|map.?like|no horizon|patterns?\s+visible|"
    r"crevasse\s+patterns?\s+visible|alpine|at\s+\d+\s*deg\w*|\d+\s*deg\w*) ",
    re.IGNORECASE
)

# Module-level cache so the model loads only once per worker process
_model = None
_tokenizer = None


def _get_model():
    global _model, _tokenizer
    if _model is None or _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype="auto",
            device_map="auto",
        )
    return _model, _tokenizer


def clean(text: str) -> str:
    for pattern in STRIP_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    match = re.search(r"Change the background", text, re.IGNORECASE)
    if match:
        text = text[match.start():]

    text = re.sub(r",\s*,+", ",", text)
    text = re.sub(r",\s*\.", ".", text)
    text = re.sub(r"\band\s*,", ",", text)
    text = re.sub(r",\s*and\s*\.", ".", text)
    text = re.sub(r"\bwith\s*,", "with", text)
    text = re.sub(r",\s*and\s*a\s*[,\.]", ".", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = text.strip().rstrip(",").strip()

    if not text.endswith("."):
        text = text.rstrip(".,")

    return text


def is_broken(text: str) -> bool:
    patterns = [
        r"\ba of\b",
        r"\bthe of\b",
        r",\s*and\s*a[,\s]",
        r"\bwith\s*,",
        r"\bto\s*,",
        r"\band\s*\.",
        r"\bwith\s+and\b",
        r"to a of",
        r",\s*a\s*\.",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def run_model(messages, model, tokenizer, max_new_tokens=100) -> str:
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        temperature=0.3,
        top_p=0.9,
        do_sample=True,
        repetition_penalty=1.3,
        pad_token_id=tokenizer.eos_token_id,
    )
    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    raw = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    match = re.search(r"(Change the background[^.]+\.)", raw, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    if "." in raw:
        return raw[:raw.index(".") + 1].strip()
    return raw


def extract_scene_terms(user_input: str) -> str:
    cleaned = VIEW_TERMS.sub("", user_input)
    cleaned = re.sub(r"[,;\s]{2,}", ", ", cleaned).strip(", ").strip()
    cleaned = re.sub(r"^view of\s+", "", cleaned, flags=re.IGNORECASE).strip(", ").strip()
    return cleaned if len(cleaned) > 3 else user_input


def convert_prompt(user_input: str, model=None, tokenizer=None) -> tuple[str, float]:
    if model is None or tokenizer is None:
        model, tokenizer = _get_model()

    t0 = time.time()

    scene_input = extract_scene_terms(user_input)
    cleaned_input = clean(scene_input)
    if len(cleaned_input.strip(".").strip()) < 5:
        cleaned_input = scene_input

    result = run_model([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": cleaned_input}
    ], model, tokenizer)

    result = clean(result)

    if is_broken(result):
        result = run_model([
            {"role": "system", "content": "Fix this broken sentence so it reads naturally. Remove fragments. Output only the fixed sentence."},
            {"role": "user", "content": result}
        ], model, tokenizer, max_new_tokens=100)
        result = clean(result)

    elapsed = time.time() - t0
    return result, elapsed
