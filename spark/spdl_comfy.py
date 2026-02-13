
import os
import json
import time
import uuid
import logging
import requests


# -------------------- BASE DIR --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -------------------- LOGGING --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
mlogger = logging.getLogger("spdl_comfy")

# -------------------- COMFY CONFIG --------------------
COMFY_HOST = os.getenv("COMFY_HOST")

WORKFLOW_PATH = os.path.join(
    BASE_DIR,
    "comfy_workflows",
    "sdpl.json"
)

COMFY_INPUT_DIR = os.getenv("COMFY_INPUT_DIR")
COMFY_OUTPUT_DIR = os.getenv("COMFY_OUTPUT_DIR")

# -------------------- GRYD CONFIG --------------------
GRYD_URL = os.getenv("GRYD_URL")

HEADERS = {
    "X-I2CE-ENTERPRISE-ID": os.getenv("GRYD_ENTERPRISE_ID"),
    "X-I2CE-USER-ID": os.getenv("GRYD_USER_ID"),
    "X-I2CE-API-KEY": os.getenv("GRYD_API_KEY"),
}

# -------------------- HELPERS --------------------
def load_workflow():
    with open(WORKFLOW_PATH, "r") as f:
        return json.load(f)


def download_image(url, save_path):
    start = time.time()
    mlogger.info(f"Downloading image: {url}")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(r.content)
    mlogger.info(f"Download completed in {time.time() - start:.2f} sec")


def upload_to_gryd(file_path):
    start = time.time()
    mlogger.info(f"Uploading to GRYD: {file_path}")
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "image/png")}
        r = requests.post(GRYD_URL, headers=HEADERS, files=files, timeout=60)
        r.raise_for_status()
        mlogger.info(f"Upload completed in {time.time() - start:.2f} sec")
        return r.json().get("cdn_url")


def queue_prompt(workflow):
    start = time.time()
    mlogger.info("Sending prompt to ComfyUI...")
    r = requests.post(
        f"{COMFY_HOST}/prompt",
        json={"prompt": workflow},
        timeout=30
    )
    r.raise_for_status()
    prompt_id = r.json()["prompt_id"]
    mlogger.info(f"Prompt queued in {time.time() - start:.2f} sec | prompt_id={prompt_id}")
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


def extract_saveimage_outputs(history, save_node_id="9"):
    images = []
    outputs = history.get("outputs", {})
    if save_node_id in outputs:
        images.extend(outputs[save_node_id].get("images", []))
    return images


# -------------------- TASK --------------------
def comfy_image_generation_task(
    input_image_url,
    prompt,
    number_of_images=1,
    **kwargs
):
    logger = kwargs.pop('logger', None) or mlogger

    total_start_time = time.time()
    logger.info("===== Comfy Image Generation Task Started =====")
    logger.info(f"Prompt: {prompt}")
    logger.info(f"Number of images requested: {number_of_images}")

    number_of_images = 1

    try:
        os.makedirs(COMFY_INPUT_DIR, exist_ok=True)

        task_id = str(uuid.uuid4())[:8]
        input_filename = f"{task_id}.png"
        input_path = os.path.join(COMFY_INPUT_DIR, input_filename)

        # 1. Download input image
        download_image(input_image_url, input_path)

        image_urls = []

        for i in range(number_of_images):
            iteration_start = time.time()
            logger.info(f"----- Running ComfyUI ({i + 1}/{number_of_images}) -----")

            workflow = load_workflow()

            # ---- Inject image
            workflow["41"]["inputs"]["image"] = input_filename

            # ---- Inject prompts
            workflow["89:130"]["inputs"]["prompt"] = prompt

            # ---- Randomize seed per image
            seed = int(time.time() * 1000) % 2**63
            workflow["89:65"]["inputs"]["seed"] = seed
            logger.info(f"Seed used: {seed}")

            prompt_id = queue_prompt(workflow)
            logger.info(f"Comfy prompt_id={prompt_id}")

            history = wait_for_completion(prompt_id)

            images = extract_saveimage_outputs(history)

            for img in images:
                filename = img["filename"]
                subfolder = img.get("subfolder", "")
                output_path = os.path.join(COMFY_OUTPUT_DIR, subfolder, filename)

                if os.path.exists(output_path):
                    url = upload_to_gryd(output_path)
                    if url:
                        image_urls.append(url)

            logger.info(
                f"Image {i + 1} completed in {time.time() - iteration_start:.2f} sec"
            )

        # Cleanup input file
        if os.path.exists(input_path):
            os.remove(input_path)

        total_cost = (time.time() - total_start_time) * 0.0016
        logger.info(
            f"===== Total Task Completed in {time.time() - total_start_time:.2f} sec ====="
        )
        return {
            "image_urls": image_urls,
            "total_time": time.time() - total_start_time,
            "total_cost": total_cost,
            "currency": "USD",
        }

    except Exception as e:
        logger.exception("Comfy task failed")
        return {"error": str(e)}
