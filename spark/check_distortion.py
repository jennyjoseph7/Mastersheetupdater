import sys, os
from gryd_worker import gryd, gryd_helpers as hp
import json
from typing import Any, Dict
from PIL import Image
import re, time
from ai_service import ai_service

mlogger = hp.get_logger(__name__)

DEFAULT_MODEL = "gcp-gemini-2.0-flash"

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

def analyze_image(
    image_path: str,
    model: str = DEFAULT_MODEL,
    min_dim: int = None,
    max_aspect_ratio: float = None,
    verbose: bool = False,
    logger: hp.logging.Logger = None,
) -> Dict[str, Any]:
    """
    Analyze an image for clarity, completeness, soundness, and lighting.
    args:
        image_path: Path to the image file.
        model: Model to use for analysis, (default: gcp-gemini-2.0-flash)
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
    start_time = time.time()
    valid_size, width, height = check_image_size(image_path, min_dim, max_aspect_ratio)
    logger.info(f"Valid size for image: {image_path} is {valid_size}, width: {width}, height: {height}")
    model = model or DEFAULT_MODEL
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


def main():
    import argparse

    parser = argparse.ArgumentParser(description="""
Analyze car image quality and completeness. 
In order to install,
pip install openai
pip install pillow

To run,
python test_distort.py <image_path>

Example:
python test_distort.py data/images/car_1.jpg
""")
    parser.add_argument("image_path", help="Path to an image file")
    parser.add_argument("--model", help="OpenAI model name", default=DEFAULT_MODEL)
    parser.add_argument("--min-dim", help="Minimum dimension of the image", default=1024)
    parser.add_argument("--max-aspect-ratio", help="Maximum aspect ratio of the image", default=3)
    parser.add_argument("-v", "--verbose", help="Verbose output", action="store_true", default=False)
    args = parser.parse_args()

    try:
        result = analyze_image(
            args.image_path, 
            model=args.model, 
            min_dim=int(args.min_dim), 
            max_aspect_ratio=float(args.max_aspect_ratio),
            verbose=args.verbose
        )
        print(json.dumps(result, indent=4))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

