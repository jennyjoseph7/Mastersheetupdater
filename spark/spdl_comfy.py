# import os
# import json
# import time
# import uuid
# import logging
# import requests
# import tempfile

# from gryd_worker import gryd
# # -------------------- BASE DIR --------------------
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# # -------------------- LOGGING --------------------
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # -------------------- COMFY CONFIG --------------------
# COMFY_HOST = "http://127.0.0.1:8000"
# WORKFLOW_PATH = os.path.join(
#     BASE_DIR,
#     "comfy_workflows",
#     "Qwen2511.json"
# )

# COMFY_INPUT_DIR  = r"C:\Users\Dave\Documents\ComfyUI\input"
# COMFY_OUTPUT_DIR = r"C:\Users\Dave\Documents\ComfyUI\output"

# # -------------------- GRYD CONFIG --------------------
# GRYD_URL = "https://file-prod.gryd.in/media/image"
# HEADERS = {
#     "X-I2CE-ENTERPRISE-ID": "gryd_file_system",
#     "X-I2CE-USER-ID": "siddhant.anchal+file-gryd@iamdave.ai",
#     "X-I2CE-API-KEY": "2a24bbde-6c29-3659-afc0-96d08b59ae3f",
# }

# gryd.SERVICE = "spark"
# gryd.set_queue_manager(config={"broker_type": "sqs", "timeout": 10})


# # -------------------- HELPERS --------------------
# def load_workflow():
#     with open(WORKFLOW_PATH, "r") as f:
#         return json.load(f)


# def download_image(image_url, save_path):
#     try:
#         logger.info(f"Downloading image: {image_url}")
#         response = requests.get(image_url)
#         response.raise_for_status()
#         with open(save_path, "wb") as f:
#             f.write(response.content)
#         return save_path
#     except Exception as e:
#         logger.error(f"Download failed: {e}")
#         return None


# def upload_to_gryd(file_path):
#     try:
#         logger.info(f"Uploading to Gryd: {file_path}")
#         with open(file_path, "rb") as f:
#             files = {"file": (os.path.basename(file_path), f, "image/png")}
#             response = requests.post(GRYD_URL, headers=HEADERS, files=files)
#             response.raise_for_status()
#             return response.json().get("cdn_url")
#     except Exception as e:
#         logger.error(f"Gryd upload failed: {e}")
#         return None


# def queue_prompt(workflow):
#     resp = requests.post(
#         f"{COMFY_HOST}/prompt",
#         json={"prompt": workflow},
#     )
#     resp.raise_for_status()
#     return resp.json()["prompt_id"]


# def wait_for_completion(prompt_id):
#     while True:
#         history = requests.get(f"{COMFY_HOST}/history/{prompt_id}").json()
#         if prompt_id in history:
#             return history[prompt_id]
#         time.sleep(1)


# def fetch_output_images(history):
#     images = []
#     for node in history["outputs"].values():
#         if "images" in node:
#             images.extend(node["images"])
#     return images


# # -------------------- GRYD TASK --------------------
# @gryd.is_a_task()
# def comfy_image_generation_task(
#     input_image_url,
#     prompt,
#     number_of_images=1,
#     **kwargs
# ):
#     try:
#         task_id = str(uuid.uuid4())[:8]
#         os.makedirs(COMFY_INPUT_DIR, exist_ok=True)

#         # -------- Save input image --------
#         input_image_path = os.path.join(COMFY_INPUT_DIR, f"{task_id}.png")
#         if not download_image(input_image_url, input_image_path):
#             return {"error": "Failed to download input image"}

# # -------- Load workflow --------
#         workflow = load_workflow()

# # -------- Inject values (API WORKFLOW) --------
# # LoadImage node
#         workflow["41"]["inputs"]["image"] = f"{task_id}.png"

# # Positive prompt node
#         workflow["89:68"]["inputs"]["prompt"] = prompt


#         image_urls = []

#         # -------- Run workflow N times --------
#         for i in range(number_of_images):
#             logger.info(f"Running ComfyUI ({i+1}/{number_of_images})")

#             prompt_id = queue_prompt(workflow)
#             history = wait_for_completion(prompt_id)
#             outputs = fetch_output_images(history)

#             for img in outputs:
#                 filename = img["filename"]
#                 output_path = os.path.join(COMFY_OUTPUT_DIR, filename)

#                 if not os.path.exists(output_path):
#                     continue

#                 uploaded_url = upload_to_gryd(output_path)
#                 if uploaded_url:
#                     image_urls.append(uploaded_url)

#         return {"image_urls": image_urls}

#     except Exception as e:
#         logger.error(f"Comfy task failed: {e}")
#         return {"error": str(e)}


# test 1 
# import os
# import json
# import time
# import uuid
# import logging
# import requests

# from gryd_worker import gryd

# # -------------------- BASE DIR --------------------
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# # -------------------- LOGGING --------------------
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("spdl_comfy")

# # -------------------- COMFY CONFIG --------------------
# COMFY_HOST = "http://127.0.0.1:8000"

# WORKFLOW_PATH = os.path.join(
#     BASE_DIR,
#     "comfy_workflows",
#     "Qwen2511.json"
# )

# COMFY_INPUT_DIR = r"C:\Users\Dave\Documents\ComfyUI\input"
# COMFY_OUTPUT_DIR = r"C:\Users\Dave\Documents\ComfyUI\output"

# # -------------------- GRYD CONFIG --------------------
# GRYD_URL = "https://file-prod.gryd.in/media/image"
# HEADERS = {
#     "X-I2CE-ENTERPRISE-ID": "gryd_file_system",
#     "X-I2CE-USER-ID": "siddhant.anchal+file-gryd@iamdave.ai",
#     "X-I2CE-API-KEY": "2a24bbde-6c29-3659-afc0-96d08b59ae3f",
# }

# gryd.SERVICE = "spark"
# gryd.set_queue_manager(config={"broker_type": "sqs", "timeout": 10})


# # -------------------- HELPERS --------------------
# def load_workflow():
#     with open(WORKFLOW_PATH, "r") as f:
#         return json.load(f)


# def download_image(url, save_path):
#     logger.info(f"Downloading image: {url}")
#     r = requests.get(url, timeout=30)
#     r.raise_for_status()
#     with open(save_path, "wb") as f:
#         f.write(r.content)


# def upload_to_gryd(file_path):
#     logger.info(f"Uploading to GRYD: {file_path}")
#     with open(file_path, "rb") as f:
#         files = {"file": (os.path.basename(file_path), f, "image/png")}
#         r = requests.post(GRYD_URL, headers=HEADERS, files=files, timeout=60)
#         r.raise_for_status()
#         return r.json().get("cdn_url")


# def queue_prompt(workflow):
#     r = requests.post(
#         f"{COMFY_HOST}/prompt",
#         json={"prompt": workflow},
#         timeout=30
#     )

#     if r.status_code != 200:
#         logger.error(f"ComfyUI rejected workflow: {r.text}")
#         r.raise_for_status()

#     return r.json()["prompt_id"]


# def wait_for_completion(prompt_id):
#     while True:
#         r = requests.get(f"{COMFY_HOST}/history/{prompt_id}", timeout=30)
#         history = r.json()
#         if prompt_id in history:
#             return history[prompt_id]
#         time.sleep(1)


# def extract_images(history):
#     images = []
#     for node in history.get("outputs", {}).values():
#         if "images" in node:
#             images.extend(node["images"])
#     return images


# # -------------------- TASK --------------------
# @gryd.is_a_task()
# def comfy_image_generation_task(
#     input_image_url,
#     prompt,
#     number_of_images=1,
#     **kwargs
# ):
#     try:
#         os.makedirs(COMFY_INPUT_DIR, exist_ok=True)

#         task_id = str(uuid.uuid4())[:8]
#         input_filename = f"{task_id}.png"
#         input_path = os.path.join(COMFY_INPUT_DIR, input_filename)

#         # ---- Download input image
#         download_image(input_image_url, input_path)

#         # ---- Load workflow (THIS WAS MISSING BEFORE)
#         workflow = load_workflow()

#         # ---- Inject image
#         workflow["41"]["inputs"]["image"] = input_filename

#         # ---- Inject POSITIVE prompt
#         workflow["89:68"]["inputs"]["prompt"] = prompt

#         # ---- Inject NEGATIVE prompt (CRITICAL)
#         workflow["89:69"]["inputs"]["prompt"] = (
#             "low quality, blurry, artifacts, distortion, watermark, text, ui"
#         )

#         image_urls = []

#         for i in range(number_of_images):
#             logger.info(f"Running ComfyUI ({i+1}/{number_of_images})")

#             prompt_id = queue_prompt(workflow)
#             history = wait_for_completion(prompt_id)

#             images = extract_images(history)

#             for img in images:
#                 filename = img["filename"]
#                 subfolder = img.get("subfolder", "")
#                 output_path = os.path.join(COMFY_OUTPUT_DIR, subfolder, filename)

#                 if os.path.exists(output_path):
#                     url = upload_to_gryd(output_path)
#                     if url:
#                         image_urls.append(url)

#         return {"image_urls": image_urls}

#     except Exception as e:
#         logger.exception("Comfy task failed")
#         return {"error": str(e)}


# test 3 
import os
import json
import time
import uuid
import logging
import requests

from gryd_worker import gryd

# -------------------- BASE DIR --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -------------------- LOGGING --------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("spdl_comfy")

# -------------------- COMFY CONFIG --------------------
COMFY_HOST = "http://127.0.0.1:8000"

WORKFLOW_PATH = os.path.join(
    BASE_DIR,
    "comfy_workflows",
    "Qwen2511.json"
)

COMFY_INPUT_DIR = r"C:\Users\Dave\Documents\ComfyUI\input"
COMFY_OUTPUT_DIR = r"C:\Users\Dave\Documents\ComfyUI\output"

# -------------------- GRYD CONFIG --------------------
GRYD_URL = "https://file-prod.gryd.in/media/image"
HEADERS = {
    "X-I2CE-ENTERPRISE-ID": "gryd_file_system",
    "X-I2CE-USER-ID": "siddhant.anchal+file-gryd@iamdave.ai",
    "X-I2CE-API-KEY": "2a24bbde-6c29-3659-afc0-96d08b59ae3f",
}

gryd.SERVICE = "spark"
gryd.set_queue_manager(config={"broker_type": "sqs", "timeout": 10})

# -------------------- HELPERS --------------------
def load_workflow():
    with open(WORKFLOW_PATH, "r") as f:
        return json.load(f)


def download_image(url, save_path):
    logger.info(f"Downloading image: {url}")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(r.content)


def upload_to_gryd(file_path):
    logger.info(f"Uploading to GRYD: {file_path}")
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "image/png")}
        r = requests.post(GRYD_URL, headers=HEADERS, files=files, timeout=60)
        r.raise_for_status()
        return r.json().get("cdn_url")


def queue_prompt(workflow):
    r = requests.post(
        f"{COMFY_HOST}/prompt",
        json={"prompt": workflow},
        timeout=30
    )
    r.raise_for_status()
    return r.json()["prompt_id"]


def wait_for_completion(prompt_id, timeout=300):
    start = time.time()
    while True:
        r = requests.get(f"{COMFY_HOST}/history/{prompt_id}", timeout=30)
        history = r.json()
        if prompt_id in history:
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
@gryd.is_a_task()
def comfy_image_generation_task(
    input_image_url,
    prompt,
    number_of_images=1,
    **kwargs
):
    try:
        os.makedirs(COMFY_INPUT_DIR, exist_ok=True)

        task_id = str(uuid.uuid4())[:8]
        input_filename = f"{task_id}.png"
        input_path = os.path.join(COMFY_INPUT_DIR, input_filename)

        # 1. Download input image
        download_image(input_image_url, input_path)

        image_urls = []

        for i in range(number_of_images):
            logger.info(f"Running ComfyUI ({i + 1}/{number_of_images})")

            workflow = load_workflow()

            # ---- Inject image
            workflow["41"]["inputs"]["image"] = input_filename

            # ---- Inject prompts
            workflow["89:68"]["inputs"]["prompt"] = prompt
            workflow["89:69"]["inputs"]["prompt"] = (
                "low quality, blurry, artifacts, distortion, watermark, text, ui"
            )

            # ---- Randomize seed per image
            workflow["89:65"]["inputs"]["seed"] = int(time.time() * 1000) % 2**32

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

        # Cleanup input file
        if os.path.exists(input_path):
            os.remove(input_path)

        return {"image_urls": image_urls}

    except Exception as e:
        logger.exception("Comfy task failed")
        return {"error": str(e)}
