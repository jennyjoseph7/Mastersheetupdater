import sys, os
from gryd_worker import gryd, gryd_helpers as hp
import json
from typing import Any, Dict
from PIL import Image, ImageOps
import re, time, typing
from ai_service import ai_service
from os.path import dirname, abspath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from config import ANALYZE_IMAGE_MODEL
mlogger = hp.get_logger(__name__)


def check_image_size(image_path: str, min_dim: int = 1024, max_aspect_ratio: float = 3) -> tuple[bool, int, int]:
    """
    Args:
        image_path: Path to the image file.
        min_dim: Minimum dimension of the image.
        max_aspect_ratio: Maximum aspect ratio of the image.
    Returns a tuple of (valid_size, width, height) 
        where valid_size is True 
        if both dimensions of the image exceed min_dim 
            and aspect ratio is less than max_aspect_ratio (i.e. not too wide or tall).
        width and height are the dimensions of the image."""
    with Image.open(image_path) as img:
        width, height = img.size
        aspect_ratio = max(width / height, height / width)
        valid_size = (width >= min_dim or height >= min_dim) and (aspect_ratio <= max_aspect_ratio)
        return valid_size, width, height


def pad_and_resize_image(image_path:str, output_dimensions:typing.Union[list[int, int], list[int, int, int]], output_image_path:str = None, grey_color:tuple = None, logger:hp.logging.Logger = None):
    logger = logger or mlogger
    grey_color = grey_color or (175, 175, 175)
    output_image_path = output_image_path or image_path
    if not isinstance(output_dimensions, list) or len(output_dimensions) not in [2, 3]:
        raise ValueError("output_dimentions must be a list of 2 or 3 integers")
    with Image.open(image_path) as img:
        width, height = img.size
        if len(output_dimensions) == 2:
            if img.mode == "RGB":
                channels = 3
            elif img.mode == "RGBA":
                channels = 4
            else:
                channels = 1
            output_dimensions.append(channels)
        req_width, req_height, channels = output_dimensions
        if width > req_width or height > req_height:
            width_ratio = req_width / width
            height_ratio = req_height / height
            if width_ratio <= height_ratio: # it is easier to shrink the width than the height
                new_width = req_width
                new_height = int(height * width_ratio)
            else:
                # it is easier to shrink the height than the width
                new_height = req_height
                new_width = int(width * height_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            width = new_width
            height = new_height
        pad_width = req_width - width
        pad_height = req_height - height
        # INSERT_YOUR_CODE
        # First, create a new blank (grey) image with the requested output size.
        if img.mode == "RGBA" or channels == 4:
            mode = "RGBA"
            grey_color = grey_color + (255,)
        else:
            mode = "RGB"
        background = Image.new(mode, (req_width, req_height), grey_color)
        # Compute left and top offsets for centering
        left = (pad_width) // 2
        top = (pad_height) // 2
        if left + width > req_width:
            left = max(0, req_width - width)
        if top + height > req_height:
            top = max(0, req_height - height)
        # Paste the resized image onto the grey background, centered
        background.paste(img, (left, top))
        background.save(output_image_path)
        return output_image_path

def analyze_image(
    image_path: str,
    model: str = ANALYZE_IMAGE_MODEL,
    min_dim: int = None,
    max_aspect_ratio: float = None,
    verbose: bool = False,
    logger: hp.logging.Logger = None,
) -> Dict[str, Any]:
    """
    Analyze an image for clarity, completeness, soundness, and lighting.
    args:
        image_path: Path to the image file.
        model: Model to use for analysis, (default: gcp-gemini-2.5-flash)
        min_dim: Minimum dimension of the image, (default: 1024)
        max_aspect_ratio: Maximum aspect ratio of the image, (default: 3)
        verbose: Whether to print verbose output, (default: False)
        logger: Logger to use for logging, (default: mlogger)
    Returns:
        A dictionary with the following keys:
        - clarity: Score from 0 to 1, where 0 is blurred/shaky and 1 is well focused.
        - completeness: Boolean, true or false, is a car or automobile fully visible with no occlusions/cropping/clipping and without the edges missing?
        - integrity: Score from 0 to 1, 0 = if it is a photo of a photo or screen with artefacts, or glare, reflections, perspective distortion, unnatural shadows, etc., 1 = seems like photo of the original car.
        - lighting: Score from 0 to 1, 0 = parts are dark or in shadow, 1 = well lit and all parts are visible.
        - photo_angle: Score from 0 to 1, 0 = the camera is not parallel to the ground, 1 = the camera is parallel to the ground.
        - comments: Why we got this score for each of the above attributes.
        - valid_size: Whether the image is valid size.
        - width: Width of the image.
        - height: Height of the image.
    """
    logger = logger or mlogger
    start_time = time.time()
    valid_size, width, height = check_image_size(image_path, min_dim, max_aspect_ratio)
    logger.info(f"Valid size for image: {image_path} is {valid_size}, width: {width}, height: {height}")
    model = model or ANALYZE_IMAGE_MODEL
    min_dim = min_dim or 1024
    max_aspect_ratio = max_aspect_ratio or 3
    verbose = verbose or False
    logger = logger or mlogger
    system_prompt = (
        "You are an expert photo assessor for the photograph of a car. "
        "Given an image, analyze and produce a JSON structured as follows:\n"
        "{\n"
        '   "clarity": <score from 0 to 1, where 0 is blurred/shaky and 1 is well focused>,\n'
        '   "completeness": <boolean, true or false, is a car or automobile fully visible with no occlusions/cropping/clipping and without the edges missing?>,\n'
        '   "integrity": <score from 0 to 1, 0 = if it is a photo of a photo or screen with artefacts, or glare, reflections, perspective distortion, unnatural shadows, etc., 1 = seems like photo of the original car>,\n'
        '   "lighting": <score from 0 to 1, 0 = parts are dark or in shadow, 1 = well lit and all parts are visible>,\n'
        '   "photo_angle": <score from 0 to 1, 0 = the camera is not parallel to the ground, 1 = the camera is parallel to the ground>,\n'
        '   "comments": why we got this score for each of the above attributes,\n'
        "}\n"
        "Just reply with the JSON. Pay attention to: sharpness, if a car is fully visible, presence of artifacts, and lighting."
    )
    logger.info(f"Analyzing image: {image_path} with model: {model} and min_dim: {min_dim} and max_aspect_ratio: {max_aspect_ratio} and verbose: {verbose}")
    output_txt = ai_service.get_vlm_response(
        user_query = "Please assess this image.",
        images = [
            image_path    
        ],
        system_prompt = system_prompt,
        temperature=0.2,
    )
    logger.info(f"Response: {output_txt}")
    # Parse JSON from the response

    json_match = re.search(r'(\{.*\})', output_txt, re.DOTALL)
    logger.info(f"JSON match to response: {json_match}")
    if not json_match:
        raise ValueError("Could not find a JSON structure in the model's response.")
    try:
        assessments = json.loads(json_match.group(1))
    except Exception as ex:
        raise ValueError(f"Error parsing result: {ex}, output={output_txt}")
    
    assessments["valid_size"] = valid_size
    assessments["width"] = width
    assessments["height"] = height
    if verbose:
        assessments["model"] = model
        assessments["time_taken"] = time.time() - start_time
    logger.info(f"Assessments: {assessments}")
    return assessments

def compare_images(
    original_image_path: str,
    generated_image_path: str,
    model: str = ANALYZE_IMAGE_MODEL,
    verbose: bool = False,
    logger: hp.logging.Logger = None,
) -> Dict[str, Any]:
    """
    Compare two images and return a score for the difference between them, speficially in terms of the accuracy of the car in the image.
    args:
        original_image_path: Path to the original image file.
        generated_image_path: Path to the generated image file.
        model: Model to use for analysis, (default: gcp-gemini-2.5-flash)
        verbose: Whether to print verbose output, (default: False)
        logger: Logger to use for logging, (default: mlogger)
    Returns:
        A dictionary with the following keys:
        - score: Score from 0 to 1, where 0 is the images are identical and 1 is the images are completely different in terms of the accuracy of the car in the image.
        - comments: Why we got this score.
    """
    logger = logger or mlogger
    start_time = time.time()
    model = model or ANALYZE_IMAGE_MODEL
    verbose = verbose or False
    system_prompt = (
        "You are a very strict expert automobile assessor for the physical accuracy of the car in the image. "
        "You will be given two images of the same car, but with different backgrounds. "
        "The first image is the original image and the second image is the generated image. "
        "The minute details of the car are very important at a pixel level. "
        "Pay special attention to the brand logo, the model text/logo, tyres, cap and treadings, antenna, bracers, sensors, fog lights, the headlights, tail lights, wheels, mirrors, grill, bumpers, contours, etc. "
        "Pay attention to the overall clarity, shape, color and dimensions of the car. "
        "The generated image (second image) should be as close as possible to the original image (first image) in terms of these details. "
        "Reduce the score if the generated image (second image) is not clear, blurry, or have artefacts. "
        "Reduce the score if the generated image (second image) looks unnatural or unrealistic. "
        "You don't give a perfect score even if there are some minor differences in the physical and structural details of the car."
        "You need to analyze and produce a JSON structured as follows:\n"
        "{\n"
        '   "score": <score from 0 to 1, where 1 only and only if the car in the images are exactly identical and 0 if the image of the car are completely different>,\n'
        '   "<part of the car>": <what the inaccruacies of the <part of the car> in the generated image (second image) are compared to the original image (first image)>,\n'
        "}\n"
        "Just return the JSON. Do not add any other text or comments."
    )
    logger.info(f"Comparing images: {original_image_path} and {generated_image_path} with model: {model} and verbose: {verbose}")
    output_txt = ai_service.get_vlm_response(
        user_query = "Please compare these images.", 
        images = [original_image_path, generated_image_path], 
        system_prompt = system_prompt, 
        temperature=0.2,
    )
    logger.info(f"Response: {output_txt}")
    json_match = re.search(r'(\{.*\})', output_txt, re.DOTALL)
    logger.info(f"JSON match to response: {json_match}")
    if not json_match:
        raise ValueError("Could not find a JSON structure in the model's response.")
    try:
        result = json.loads(json_match.group(1))
        if verbose:
            result["model"] = model
            result["time_taken"] = time.time() - start_time
        return result
    except Exception as ex:
        raise ValueError(f"Error parsing result: {ex}, output={output_txt}")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="""
Analyze car image quality and completeness.. OR
Compare two images and return a score for the difference between them, speficially in terms of the accuracy of the car in the image.
In order to install,
pip install openai
pip install pillow

To run,
python check_distortion.py 'analyze' <image_path>
python check_distortion.py 'compare' <original_image_path> <generated_image_path>

Example:
python check_distortion.py data/images/car_1.jpg
""")
    parser.add_argument("mode", help="Mode to use", choices=["analyze", "compare"])
    parser.add_argument("image_path", help="Path to an image file")
    parser.add_argument("--generated_image_path", help="Path to the generated image file")
    parser.add_argument("--model", help="Image Analysis Model name", default=ANALYZE_IMAGE_MODEL)
    parser.add_argument("--min-dim", help="Minimum dimension of the image", default=1024)
    parser.add_argument("--max-aspect-ratio", help="Maximum aspect ratio of the image", default=3)
    parser.add_argument("-v", "--verbose", help="Verbose output", action="store_true", default=False)
    args = parser.parse_args()

    try:
        if args.mode == "analyze":
            result = analyze_image(
                args.image_path, 
                model=args.model, 
                min_dim=int(args.min_dim), 
                max_aspect_ratio=float(args.max_aspect_ratio),
                verbose=args.verbose
            )
        elif args.mode == "compare":
            if not args.generated_image_path:
                raise ValueError("Generated image path is required for compare mode")
            result = compare_images(
                args.image_path,
                args.generated_image_path,
                model=args.model,
                verbose=args.verbose
            )
        else:
            raise ValueError(f"Invalid mode: {args.mode}")
        mlogger.info(f"Result: {result}")
    except Exception as e:
        mlogger.error(f"Error: {e}")
        raise(e)
    mlogger.info("Finished main")

if __name__ == "__main__":
    main()

