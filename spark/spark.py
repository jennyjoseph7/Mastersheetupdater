import sys
import os, re, tempfile
from ai_service import ai_service
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from gryd_worker import gryd, gryd_helpers as hp
json = hp.json
APP_DIR = dirname(abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.append(APP_DIR)
from config import AUTOCRM_APP_ENTERPRISE_ID, OPENAI_API_KEY, \
    OPENAI_IMAGE_MODEL, \
    OPENAI_IMAGE_SIZE, \
    OPENAI_INPUT_TEXT_TOKEN_PRICE, \
    OPENAI_OUTPUT_TEXT_TOKEN_PRICE, \
    OPENAI_INPUT_IMAGE_TOKEN_PRICE, \
    OPENAI_OUTPUT_IMAGE_TOKEN_PRICE, \
    VALIDATE_PROMPT_MODEL
from combine_images import merge_layers
from check_distortion import analyze_image, pad_and_resize_image, compare_images
from spdl_comfy import comfy_image_generation_task
from spdl_comfy import gemini_image_generation_task
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
def merge_layers_task(base_png: str, png_layers: list[tuple[str, float, int, int]] = None, svg_layers: list[tuple[str, float, int, int]] = None, output_path: str = None, job: dict = None, logger: hp.logging.Logger = None):
    logger = logger or mlogger
    output_path = merge_layers(base_png, png_layers=png_layers, svg_layers=svg_layers, output_path=output_path, job=job, logger=logger)
    cdn_url = func_gryd_file_system(output_path, media_type='image', logger=logger)
    return cdn_url

@gryd.is_a_task(function_name="pad_and_resize_image", job_param='job', logger_param='logger')
def pad_and_resize_image_task(image_path: str, output_dimensions: list = None, job: dict = None, logger: hp.logging.Logger = None):
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

@gryd.is_a_task(function_name = "gemini_image_generation", job_param = 'job', logger_param = 'logger')
def gemini_image_generation(
    input_image_url,
    prompt,
    number_of_images=1,
    job = None,
    logger = None,
    **kwargs):
    logger = logger or mlogger
    return gemini_image_generation_task(input_image_url, prompt, number_of_images, logger = logger, **kwargs)


@gryd.is_a_task(function_name="openai_image_generation", job_param='job', logger_param='logger')
def openai_image_generation(
    input_image_url,
    prompt,
    number_of_images=1,
    job=None,
    logger=None,
    **kwargs
):
    logger = logger or mlogger
    start_time = hp.time()

    logger.info("===== OpenAI Image Generation Task Started =====")
    logger.info(f"Prompt: {prompt}")
    logger.info(f"Input Image URL: {input_image_url}")
    logger.info(f"Job ID: {getattr(job, 'id', None)}")
    logger.info(f"Requested number_of_images: {number_of_images}")

    def replace_background_with_gpt(input_image_url, prompt):
        import requests
        import tempfile
        import os
        import uuid

        api_key = OPENAI_API_KEY
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not found or invalid.")

        fixed_number_of_images = 1
        logger.info(f"Forced number of images: {fixed_number_of_images}")

        # -------------------- DOWNLOAD INPUT IMAGE --------------------
        input_file = f"openai_input_{uuid.uuid4().hex}.png"
        local_img_path = os.path.join(tempfile.gettempdir(), input_file)

        logger.info(f"Downloading input image to: {local_img_path}")
        download_file(input_image_url, local_img_path)

        if not os.path.exists(local_img_path):
            raise RuntimeError("Downloaded image file not found.")

        logger.info(f"Input image downloaded successfully")
        logger.info(f"Input image size: {os.path.getsize(local_img_path)} bytes")

        edit_prompt = f"{prompt.strip()} (Preserve details and features of the car.)"
        logger.info(f"Edit prompt: {edit_prompt}")

        headers = {
            "Authorization": f"Bearer {api_key}"
        }

        api_url = "https://api.openai.com/v1/images/edits"

        logger.info(f"Calling OpenAI Image Edit API: {api_url}")
        logger.info(f"Model: {OPENAI_IMAGE_MODEL}")
        logger.info(f"Image size param: {kwargs.get('size', OPENAI_IMAGE_SIZE)}")

        files = {
            "image": open(local_img_path, "rb"),
        }

        data = {
            "model": OPENAI_IMAGE_MODEL,
            "prompt": edit_prompt,
            "n": fixed_number_of_images,
            "size": kwargs.get("size", OPENAI_IMAGE_SIZE),
        }

        resp = requests.post(api_url, headers=headers, files=files, data=data)

        logger.info(f"OpenAI response status: {resp.status_code}")

        # Clean input temp file
        try:
            os.remove(local_img_path)
            logger.info("Input temp file deleted")
        except Exception as e:
            logger.warning(f"Failed to delete input temp file: {e}")

        if resp.status_code != 200:
            logger.error(f"OpenAI API error response: {resp.text}")
            raise RuntimeError(f"OpenAI image edit API error: {resp.text}")

        result = resp.json()
        logger.info(f"OpenAI response keys: {list(result.keys())}")

        output_items = result.get("data", [])
        logger.info(f"Number of images returned: {len(output_items)}")

        if not output_items:
            raise RuntimeError("No edited image returned from OpenAI.")

        ourls = []

        # -------------------- HANDLE OUTPUT --------------------
        for idx, item in enumerate(output_items):
            logger.info(f"Processing image {idx+1}")

            if 'b64_json' in item:
                logger.info("Image received as base64")

                image_bytes = hp.base64.b64decode(item['b64_json'])

                file_name = f"openai_{uuid.uuid4().hex}.png"
                tmp_out_path = os.path.join(tempfile.gettempdir(), file_name)

                logger.info(f"Saving output image to: {tmp_out_path}")

                with open(tmp_out_path, "wb") as f:
                    f.write(image_bytes)

                file_url = func_gryd_file_system(tmp_out_path, media_type='image')
                logger.info(f"Uploaded image URL: {file_url}")

                try:
                    os.remove(tmp_out_path)
                    logger.info("Output temp file deleted")
                except Exception as e:
                    logger.warning(f"Failed to delete output temp file: {e}")

                if file_url:
                    ourls.append(file_url)

            elif 'url' in item:
                logger.info(f"Image URL received directly: {item['url']}")
                ourls.append(item['url'])

        if not ourls:
            raise RuntimeError("Invalid response from OpenAI.")

        logger.info(f"Final image URL list: {ourls}")

        # -------------------- USAGE / COST --------------------
        usage = result.get("usage", {})

        input_text_token_count = usage.get("input_tokens_details", {}).get("text_tokens", 0)
        input_image_token_count = usage.get("input_tokens_details", {}).get("image_tokens", 0)
        output_text_token_count = usage.get("output_tokens_details", {}).get("text_tokens", 0)
        output_image_token_count = usage.get("output_tokens_details", {}).get("image_tokens", 0)

        logger.info(
            f"Token usage — input_text: {input_text_token_count}, "
            f"input_image: {input_image_token_count}, "
            f"output_text: {output_text_token_count}, "
            f"output_image: {output_image_token_count}"
        )

        input_cost = (
            OPENAI_INPUT_TEXT_TOKEN_PRICE * input_text_token_count +
            OPENAI_INPUT_IMAGE_TOKEN_PRICE * input_image_token_count
        )

        output_cost = (
            OPENAI_OUTPUT_TEXT_TOKEN_PRICE * output_text_token_count +
            OPENAI_OUTPUT_IMAGE_TOKEN_PRICE * output_image_token_count
        )

        total_time = hp.time() - start_time
        total_cost = input_cost + output_cost + total_time * gryd.EXECUTION_COST

        logger.info(f"Input cost: {input_cost}")
        logger.info(f"Output cost: {output_cost}")
        logger.info(f"Total cost: {total_cost}")
        logger.info(f"Total time: {total_time:.2f} sec")

        final_result = {
            "image_urls": ourls,

            "input_text_token_count": input_text_token_count,
            "input_image_token_count": input_image_token_count,
            "output_text_token_count": output_text_token_count,
            "output_image_token_count": output_image_token_count,

            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,

            "total_time": total_time,
            "currency": "USD",
        }

        logger.info(f"Returning final result: {final_result}")
        logger.info("===== OpenAI Task Completed Successfully =====")

        return final_result

    return replace_background_with_gpt(
        input_image_url=input_image_url,
        prompt=prompt
    )


@gryd.is_a_task(function_name = "validate_prompt", job_param = 'job', logger_param = 'logger')
def validate_prompt(prompt: str, car_manufacturer: str = None, car_model: str = None, validate_prompt_model: str = None, job = None, logger = None):
    logger = logger or mlogger
    car_manufacturer = car_manufacturer or "Unknown"
    car_model = car_model or "Unknown model"
    validate_prompt_model = validate_prompt_model or VALIDATE_PROMPT_MODEL
    r = ai_service.get_llm_response(user_query=prompt, system_prompt=f"""
You are a prompt validator. 
You will be given a prompt and you will need to validate it to make sure the prompt
Car manufacturer: {car_manufacturer}
Car model: {car_model}
- does not contain any offensive or sensitive words. 
- does not contain any urls. 
- does not contain any email addresses. 
- does not contain any phone numbers. 
- does not contain any personal information. 
- does not contain any sensitive information. 
- does not contain any confidential information. 
- does not contain any proprietary information. 
- does not contain any confidential information. 
- does not contain any html tags. 
- does not contain any markdown tags. 
- does not contain any code. 
- does not contain any code blocks. 
- does not contain any code snippets. 
- does not contain any code examples. 
- only contains instructions which can be interpreted as asking for a specific background or theme
- does not contain any other instructions or instructions which are not related to background change
- should not contain information about any other car manufacturer or car model
- does not ask to modify the car which is the subject of the image in any way
- does not ask to add any other objects to the image
If the prompt is valid, you will return json valid: true. 
If the prompt is invalid, you will return json valid: false, reason: reason why it is invalid.
Strictly follow the json format.

Now validate the prompt:
""", model_identifier=validate_prompt_model, service = SERVICE, enterprise_id = AUTOCRM_APP_ENTERPRISE_ID)
    try:
        return json.loads(r)
    except Exception as e:
        logger.error(f"Error validating prompt: {e}")
        return {"valid": False, "reason": str(e)}


@gryd.is_a_task(function_name = "compare_images", job_param = 'job', logger_param = 'logger')
def compare_images_func(original_image_url: str, generated_image_url: str, model: str = None, job = None, logger = None):
    logger = logger or mlogger
    original_suffix = original_image_url.split('.')[-1]
    generated_suffix = generated_image_url.split('.')[-1]
    with tempfile.NamedTemporaryFile(suffix=f'.{original_suffix}') as original_temp_file:
        original_temp_file_path = download_file(original_image_url, original_temp_file.name)
        with tempfile.NamedTemporaryFile(suffix=f'.{generated_suffix}') as generated_temp_file:
            generated_temp_file_path = download_file(generated_image_url, generated_temp_file.name)
            return compare_images(
                original_temp_file_path, 
                generated_temp_file_path, 
                model=model, 
                verbose=False, 
                logger=logger
            )

# if __name__ == "__main__":
#     input_image_url = "https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp"
#     prompt = "Change the background to scenic view from the suburbs of Mumbai"
#     number_of_images = 1
#     print(openai_image_generation(input_image_url, prompt, number_of_images))

    

