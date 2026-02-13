import sys
import os, re, tempfile
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from gryd_worker import gryd, gryd_helpers as hp
json = hp.json
APP_DIR = dirname(abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.append(APP_DIR)
from config import OPENAI_API_KEY, \
    OPENAI_IMAGE_MODEL, \
    OPENAI_IMAGE_SIZE, \
    OPENAI_INPUT_TEXT_TOKEN_PRICE, \
    OPENAI_OUTPUT_TEXT_TOKEN_PRICE, \
    OPENAI_INPUT_IMAGE_TOKEN_PRICE, \
    OPENAI_OUTPUT_IMAGE_TOKEN_PRICE
from combine_images import merge_layers
from check_distortion import analyze_image, pad_and_resize_image
from spdl_comfy import comfy_image_generation_task
from spark_helpers import func_gryd_file_system, download_file
SERVICE = 'spark'
gryd.SERVICE = SERVICE
gryd.set_queue_manager()
DEFAULT_OUTPUT_PATH = joinpath(APP_DIR, "output", "openai_image_generation")
hp.mkdir_p(DEFAULT_OUTPUT_PATH)
mlogger = gryd.hp.get_logger(gryd.SERVICE)


@gryd.is_a_task(function_name="distortion_report", job_param='job', logger_param='logger')
def distortion_report(image_path: str, model: str = None, min_dim: int = 1024, max_aspect_ratio: float = 3, job: dict = None, logger: hp.logging.Logger = None):
    logger = logger or mlogger
    return analyze_image(image_path, model=model, min_dim=min_dim, max_aspect_ratio=max_aspect_ratio, verbose = True, logger=logger)

@gryd.is_a_task(function_name="merge_layers", job_param='job', logger_param='logger')
def merge_layers(base_png: str, png_layers: list[tuple[str, float, int, int]] = None, svg_layers: list[tuple[str, float, int, int]] = None, output_path: str = None, job: dict = None, logger: hp.logging.Logger = None):
    logger = logger or mlogger
    output_path = merge_layers(base_png, png_layers=png_layers, svg_layers=svg_layers, output_path=output_path, job=job, logger=logger)
    cdn_url = func_gryd_file_system(output_path, media_type='image', logger=logger)
    return cdn_url

@gryd.is_a_task(function_name="pad_and_resize_image", job_param='job', logger_param='logger')
def pad_and_resize_image(image_path: str, output_dimensions: list = None, job: dict = None, logger: hp.logging.Logger = None):
    logger = logger or mlogger
    return pad_and_resize_image(image_path, output_dimensions=output_dimensions, logger=logger)



@gryd.is_a_task(function_name = "comfy_image_generation", job_param = 'job', logger_param = 'logger')
def comfy_image_generation(
    input_image_url,
    prompt,
    number_of_images=1,
    job = None,
    logger = None,
    **kwargs):
    logger = logger or mlogger
    return comfy_image_generation_task(input_image_url, prompt, number_of_images, logger = logger, **kwargs)


@gryd.is_a_task(function_name = "openai_image_generation", job_param = 'job', logger_param = 'logger')
def openai_image_generation(
    input_image_url,
    prompt,
    number_of_images = 1,
    job = None,
    logger = None,
    **kwargs):
    logger = logger or mlogger
    start_time = hp.time()

    def replace_background_with_gpt(input_image_url, prompt):
        """
        Uses OpenAI image API to swap image background per prompt, keeping foreground intact.

        Args:
            input_image_url (str): URL or path to the input image.
            prompt (str): Textual prompt describing the desired background.
            logger: Optional logger.
            **kwargs: Extra args for future extensibility.

        Returns:
            str: The URL or path to the image with swapped background.
        """
        import requests

        api_key = OPENAI_API_KEY
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not found or not valid in configuration or environment.")
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            local_img_path = f.name
            download_file(input_image_url, local_img_path)
            edit_prompt = f"{prompt.strip()} (Do not change the subject/foreground.)"

            headers = {
                "Authorization": f"Bearer {api_key}"
            }
            api_url = "https://api.openai.com/v1/images/edits"
            files = {
                "image": open(local_img_path, "rb"),
            }
            data = {
                "model": OPENAI_IMAGE_MODEL,
                "prompt": edit_prompt,
                "n": number_of_images,
                "size": kwargs.get("size", OPENAI_IMAGE_SIZE),
            }

            resp = requests.post(api_url, headers=headers, files=files, data=data)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenAI image edit API error: {resp.text}")

            result = resp.json()
            output_urls = [x for x in result.get("data", [])]
            
            if not output_urls:
                raise RuntimeError("No edited image returned from OpenAI.")
            ourls = []
            for url in output_urls:
                if 'b64_json' in url:
                    url = hp.base64.b64decode(url['b64_json'])
                    with tempfile.NamedTemporaryFile(suffix=".png") as f:
                        f.write(url)
                        f.flush()
                        url = f.name
                        file_url = func_gryd_file_system(url, media_type='image')
                    ourls.append(file_url)
                elif 'url' in url:
                    ourls.append(url['url'])
            if not ourls:
                raise RuntimeError(f"Invalid Response from OpenAI")
            input_text_token_count = result.get("usage", {}).get("input_tokens_details", {}).get("text_tokens", 0)
            input_image_token_count = result.get("usage", {}).get("input_tokens_details", {}).get("image_tokens", 0)
            output_text_token_count = result.get("usage", {}).get("output_tokens_details", {}).get("text_tokens", 0)
            output_image_token_count = result.get("usage", {}).get("output_tokens_details", {}).get("image_tokens", 0)
            input_cost = OPENAI_INPUT_TEXT_TOKEN_PRICE * input_text_token_count + OPENAI_INPUT_IMAGE_TOKEN_PRICE * input_image_token_count
            output_cost = OPENAI_OUTPUT_TEXT_TOKEN_PRICE * output_text_token_count + OPENAI_OUTPUT_IMAGE_TOKEN_PRICE * output_image_token_count
            total_cost = input_cost + output_cost + (hp.time() - start_time) * gryd.EXECUTION_COST
            return {
                "image_urls": hp.make_single(ourls),
                "input_text_token_count": input_text_token_count,
                "input_image_token_count": input_image_token_count,
                "output_text_token_count": output_text_token_count,
                "output_image_token_count": output_image_token_count,
                "input_cost": input_cost,
                "output_cost": output_cost,
                "total_cost": total_cost,
                "total_time": hp.time() - start_time,
                "currency": "USD",
            }
    # Entry point for task
    return replace_background_with_gpt(
        input_image_url=input_image_url,
        prompt=prompt
    )

if __name__ == "__main__":
    input_image_url = "https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp"
    prompt = "Change the background to scenic view from the suburbs of Mumbai"
    number_of_images = 1
    print(openai_image_generation(input_image_url, prompt, number_of_images))

    

