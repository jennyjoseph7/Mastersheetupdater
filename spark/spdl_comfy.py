import os
import json
import time
import uuid
import logging
import requests
import vertexai
import tempfile
from openai import OpenAI
from vertexai.preview.vision_models import Image, ImageGenerationModel
import google.genai as genai
from google.genai import types as genai_types
from google.genai.local_tokenizer import LocalTokenizer
from gryd_worker import gryd
from config import AUTOCRM_SPARK_COMFY_SERVICE_NAME
from prompt_formatter import convert_prompt as _convert_prompt

# -------------------- BASE DIR --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -------------------- LOGGING --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
mlogger = logging.getLogger("spdl_comfy")

mlogger.info(f"BASE_DIR: {BASE_DIR}")

# -------------------- ENV VARS --------------------
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = "global"
COMFY_HOST = os.getenv("COMFY_HOST")
COMFY_INPUT_DIR = os.getenv("COMFY_INPUT_DIR")
COMFY_OUTPUT_DIR = os.getenv("COMFY_OUTPUT_DIR")
GRYD_URL = os.getenv("GRYD_FILE_URL")
HEADERS = {
    "X-I2CE-ENTERPRISE-ID": os.getenv("GRYD_FILE_ENTERPRISE_ID"),
    "X-I2CE-USER-ID": os.getenv("GRYD_FILE_USER_ID"),
    "X-I2CE-API-KEY": os.getenv("GRYD_FILE_API_KEY"),
}

mlogger.info(f"PROJECT_ID: {PROJECT_ID}")
mlogger.info(f"LOCATION: {LOCATION}")

# -------------------- WORKFLOW --------------------
WORKFLOW_PATH = os.path.join(BASE_DIR, "comfy_workflows", "Flex.json")
mlogger.info(f"WORKFLOW_PATH: {WORKFLOW_PATH}")
SERVICE = AUTOCRM_SPARK_COMFY_SERVICE_NAME
gryd.SERVICE = SERVICE
THREADS_PER_SESSION = 0.3
gryd.set_queue_manager()

# -------------------- HELPERS --------------------
def load_workflow():
    mlogger.info(f"Loading workflow from: {WORKFLOW_PATH}")
    with open(WORKFLOW_PATH, "r") as f:
        workflow = json.load(f)
    mlogger.info(f"Workflow loaded successfully with {len(workflow)} nodes")
    return workflow

def download_image(url, save_path):
    start = time.time()
    mlogger.info(f"Downloading image from URL: {url} -> {save_path}")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(r.content)
    mlogger.info(f"Download completed in {time.time() - start:.2f} sec")
    mlogger.info(f"File exists after download: {os.path.exists(save_path)}")

def upload_to_gryd(file_path):
    start = time.time()
    mlogger.info(f"Uploading to GRYD: {file_path}")
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "image/png")}
        r = requests.post(GRYD_URL, headers=HEADERS, files=files, timeout=60)
        r.raise_for_status()
        mlogger.info(f"Upload completed in {time.time() - start:.2f} sec")
        response_json = r.json()
        mlogger.info(f"GRYD Response: {response_json}")
        return response_json.get("cdn_url")

def queue_prompt(workflow):
    start = time.time()
    mlogger.info("Sending prompt to ComfyUI...")
    r = requests.post(f"{COMFY_HOST}/prompt", json={"prompt": workflow}, timeout=30)
    r.raise_for_status()
    prompt_id = r.json().get("prompt_id")
    mlogger.info(f"Prompt queued | prompt_id={prompt_id} | time={time.time() - start:.2f} sec")
    return prompt_id

def wait_for_completion(prompt_id, timeout=300):
    start = time.time()
    mlogger.info(f"Waiting for Comfy completion... prompt_id={prompt_id}")

    while True:
        r = requests.get(f"{COMFY_HOST}/history/{prompt_id}", timeout=30)
        history = r.json()
        if prompt_id in history:
            mlogger.info(f"Comfy execution completed in {time.time() - start:.2f} sec")
            return history[prompt_id]
        if time.time() - start > timeout:
            raise TimeoutError("ComfyUI execution timed out")
        time.sleep(1)

def extract_saveimage_outputs(history, save_node_id="105"):
    mlogger.info(f"Extracting images from node_id={save_node_id}")
    images = []
    outputs = history.get("outputs", {})
    if save_node_id in outputs:
        images.extend(outputs[save_node_id].get("images", []))
    mlogger.info(f"Extracted {len(images)} images")
    return images

# -------------------- TASK --------------------
def comfy_image_generation_task(input_image_url, prompt, number_of_images=1, **kwargs):
    logger = kwargs.pop('logger', None) or mlogger

    total_start_time = time.time()
    logger.info("===== Comfy Image Generation Task Started =====")
    logger.info(f"Prompt: {prompt}")
    logger.info(f"Requested number_of_images: {number_of_images}")

   
    number_of_images = 1

    try:
        os.makedirs(COMFY_INPUT_DIR, exist_ok=True)
        os.makedirs(COMFY_OUTPUT_DIR, exist_ok=True)
        logger.info(f"Input dir exists: {os.path.exists(COMFY_INPUT_DIR)}")
        logger.info(f"Output dir exists: {os.path.exists(COMFY_OUTPUT_DIR)}")

        task_id = str(uuid.uuid4())[:8]
        input_filename = f"{task_id}.png"
        input_path = os.path.join(COMFY_INPUT_DIR, input_filename)
        logger.info(f"Generated input filename: {input_filename}")

        # 1. Download input image
        download_image(input_image_url, input_path)

        image_urls = []

        for i in range(number_of_images):
            iteration_start = time.time()
            logger.info(f"----- Running ComfyUI ({i + 1}/{number_of_images}) -----")

            workflow = load_workflow()

            # ---- Inject image
            workflow["76"]["inputs"]["image"] = input_filename
            logger.info(f"Injected image into workflow node 76")

            # ---- Inject prompts
            workflow["75:74"]["inputs"]["text"] = prompt
            logger.info(f"Injected prompt into workflow node 75:74")

            # ---- Randomize seed per image
            seed = int(time.time() * 1000) % 2**63
            workflow["75:73"]["inputs"]["noise_seed"] = seed
            logger.info(f"Seed used: {seed}")

            prompt_id = queue_prompt(workflow)
            logger.info(f"Comfy prompt_id={prompt_id}")

            history = wait_for_completion(prompt_id)

            images = extract_saveimage_outputs(history)

            for img in images:
                filename = img["filename"]
                subfolder = img.get("subfolder", "")
                output_path = os.path.join(COMFY_OUTPUT_DIR, subfolder, filename)
                logger.info(f"Processing output image: {output_path}")

                if os.path.exists(output_path):
                    url = upload_to_gryd(output_path)
                    if url:
                        image_urls.append(url)
                        logger.info(f"Uploaded to GRYD, URL: {url}")
                else:
                    logger.warning(f"Output image not found: {output_path}")

            logger.info(f"Image {i + 1} completed in {time.time() - iteration_start:.2f} sec")

        # Cleanup input file
        if os.path.exists(input_path):
            os.remove(input_path)
            logger.info(f"Removed input file: {input_path}")

        total_cost = (time.time() - total_start_time) * 0.0007
        logger.info(f"===== Total Task Completed in {time.time() - total_start_time:.2f} sec =====")
        logger.info(f"Estimated cost: {total_cost:.4f} USD")

        return {
            "image_urls": image_urls,
            "total_time": time.time() - total_start_time,
            "total_cost": total_cost,
            "currency": "USD",
        }

    except Exception as e:
        logger.exception("Comfy task failed")
        return {"error": str(e)}


# nano banana
def gemini_image_generation_task(
    input_image_url,
    prompt,
    number_of_images=1,
    temperature=0.2,
    top_p=0.95,
    **kwargs
):
    logger = kwargs.pop("logger", None) or mlogger

    total_start = time.time()

    logger.info("===== Gemini Image Generation Task Started =====")
    logger.info(f"Prompt: {prompt}")
    logger.info(f"Input Image URL: {input_image_url}")

    number_of_images = 1
    logger.info(f"Number of images: {number_of_images}")

    logger.info(f"Temperature: {temperature}, Top_p: {top_p}")

    try:
        # -------------------- CLIENT --------------------
        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=LOCATION
        )

        model = "gemini-3-pro-image-preview"

        task_dir = tempfile.mkdtemp(prefix="gemini_")
        image_urls = []

        total_prompt_tokens = 0
        total_output_tokens = 0

        GEMINI_INPUT_TOKEN_PRICE = 2 / 1_000_000
        GEMINI_OUTPUT_TOKEN_PRICE = 120 / 1_000_000

        for i in range(number_of_images):

            iteration_start = time.time()
            logger.info(f"----- Generating image ({i+1}/{number_of_images}) -----")

            image_part = genai_types.Part.from_uri(
                file_uri=input_image_url,
                mime_type="image/jpeg"
            )

            text_part = genai_types.Part.from_text(text=prompt)

            contents = [
                genai_types.Content(
                    role="user",
                    parts=[image_part, text_part]
                )
            ]

            config = genai_types.GenerateContentConfig(
                temperature=temperature,
                top_p=top_p,
                max_output_tokens=32768,
                response_modalities=["TEXT", "IMAGE"],
                safety_settings=[
                    genai_types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                    genai_types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
                    genai_types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
                    genai_types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
                    genai_types.SafetySetting(category="HARM_CATEGORY_IMAGE_HATE", threshold="OFF"),
                    genai_types.SafetySetting(category="HARM_CATEGORY_IMAGE_DANGEROUS_CONTENT", threshold="OFF"),
                    genai_types.SafetySetting(category="HARM_CATEGORY_IMAGE_HARASSMENT", threshold="OFF"),
                    genai_types.SafetySetting(category="HARM_CATEGORY_IMAGE_SEXUALLY_EXPLICIT", threshold="OFF"),
                ],
            )

            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )

            for candidate in response.candidates:
                for part in candidate.content.parts:

                    if getattr(part, "inline_data", None):

                        file_name = f"gemini_{uuid.uuid4().hex}.png"
                        output_path = os.path.join(task_dir, file_name)

                        with open(output_path, "wb") as f:
                            f.write(part.inline_data.data)

                        url = upload_to_gryd(output_path)

                        if url:
                            image_urls.append(url)

                        os.remove(output_path)
                        break

            # -------------------- TOKEN METADATA --------------------
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = response.usage_metadata

                prompt_tokens = getattr(usage, "prompt_token_count", 0)
                output_tokens = getattr(usage, "candidates_token_count", 0)

                total_prompt_tokens += prompt_tokens
                total_output_tokens += output_tokens

                logger.info(
                    f"Tokens — Prompt: {prompt_tokens}, Output: {output_tokens}"
                )

            logger.info(
                f"Image {i+1} completed in {time.time() - iteration_start:.2f} sec"
            )

        # -------------------- COST CALCULATION --------------------
        total_time = time.time() - total_start

        input_cost = GEMINI_INPUT_TOKEN_PRICE * total_prompt_tokens
        output_cost = GEMINI_OUTPUT_TOKEN_PRICE * total_output_tokens

        total_cost = (
            input_cost +
            output_cost +
            total_time * gryd.EXECUTION_COST
        )

        logger.info("===== Gemini Task Completed =====")
        logger.info(f"Total Time: {total_time:.2f} sec")
        logger.info(f"Total Prompt Tokens: {total_prompt_tokens}")
        logger.info(f"Total Output Tokens: {total_output_tokens}")
        logger.info(f"Total Cost: ${total_cost:.6f}")

        # -------------------- RETURN --------------------
        return {
            "image_urls": image_urls,

            "input_token_count": total_prompt_tokens,
            "output_token_count": total_output_tokens,
            "total_token_count": total_prompt_tokens + total_output_tokens,

            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,

            "total_time": total_time,
            "currency": "USD"
        }

    except Exception as e:
        logger.exception("Gemini task failed")
        return {"error": str(e)}


@gryd.is_a_task(function_name = "comfy_image_generation", job_param = 'job', logger_param = 'logger')
def comfy_image_generation(
    input_image_url,
    prompt,
    number_of_images=1,
    job = None,
    logger = None,
    **kwargs):
    logger = logger or mlogger
    if kwargs.get('optimise_prompt',True):
        prompt, elapsed = _convert_prompt(prompt)
    return comfy_image_generation_task(input_image_url, prompt, number_of_images, logger = logger, **kwargs)

