import sys
import os, re, tempfile
import requests
import tempfile
import os
import uuid
import typing
from ai_service import ai_service
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from gryd_worker import gryd, gryd_helpers as hp
json = hp.json
APP_DIR = dirname(abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(1, APP_DIR)
from config import AUTOCRM_APP_ENTERPRISE_ID, OPENAI_API_KEY, \
    OPENAI_IMAGE_MODEL, \
    OPENAI_IMAGE_SIZE, \
    OPENAI_INPUT_TEXT_TOKEN_PRICE, \
    OPENAI_OUTPUT_TEXT_TOKEN_PRICE, \
    OPENAI_INPUT_IMAGE_TOKEN_PRICE, \
    OPENAI_OUTPUT_IMAGE_TOKEN_PRICE, \
    VALIDATE_PROMPT_MODEL, \
    AutocrmModel
from combine_images import merge_layers, DEFAULT_PNG_ELEMENTS, DEFAULT_SVG_ELEMENTS, replace_svg_text_by_id, DEFAULT_OFFER, DEFAULT_CAMPAIGN_DETAILS
from check_distortion import analyze_image, pad_and_resize_image, compare_images
from spdl_comfy import comfy_image_generation_task
from spdl_comfy import gemini_image_generation_task
from spark_helpers import func_gryd_file_system, download_file
SERVICE = 'spark'
gryd.SERVICE = SERVICE
gryd.set_queue_manager()
DEFAULT_OUTPUT_PATH = joinpath(APP_DIR, "output")
hp.mkdir_p(DEFAULT_OUTPUT_PATH)
mlogger = gryd.hp.get_logger(gryd.SERVICE)


@gryd.is_a_task(function_name="distortion_report", job_param='job', logger_param='logger')
def distortion_report(image_path: str, model: str = None, min_dim: int = 1024, max_aspect_ratio: float = 3, job: dict = None, logger: hp.logging.Logger = None):
    logger = logger or mlogger
    return analyze_image(image_path, model=model, min_dim=min_dim, max_aspect_ratio=max_aspect_ratio, verbose = True, logger=logger)

def do_download(url, files_to_delete, suffix='.png'):
    if not url:
        return None
    if hp.ispath(url):
        return url
    file_name = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    files_to_delete.append(file_name.name)
    return download_file(url, file_name.name)

def manage_svg(element: str, rooftop: dict, template: dict, files_to_delete: list, logger: hp.logging.Logger = None):
    logger = logger or mlogger
    if not rooftop:
        return None
    element_svg_path = template.get(DEFAULT_SVG_ELEMENTS[element]['url'])
    if not element_svg_path:
        return None
    text_to_ids = DEFAULT_SVG_ELEMENTS[element]['ids']
    element_svg_path = do_download(element_svg_path, files_to_delete, suffix='.svg')
    replace_svg_text_by_id(element_svg_path, {
        template.get(k): rooftop.get(v, "") for k, v in text_to_ids.items() if rooftop.get(v)
    }, logger=logger)
    return element_svg_path

def get_logo(brand, template, files_to_delete, logo_type: str = 'Brand', logger: hp.logging.Logger = None):
    logger = logger or mlogger
    if not brand:
        logger.warning(f"{logo_type.title()} not found: {brand}")
        return None
    if template.get('theme_type') == 'light':
        return do_download(brand.get('light_theme_logo_url') or brand.get('logo_url'), files_to_delete)
    elif template.get('theme_type') == 'dark':
        return do_download(brand.get('dark_theme_logo_url') or brand.get('logo_url'), files_to_delete)
    else:
        return do_download(brand.get('logo_url'), files_to_delete)

def do_the_merge(rooftop_type: str, base_png: str, template: dict, brand: dict, rooftop: dict = None, dealership: dict = None, offer: dict = None, campaign_details: dict = None, files_to_delete: list[str] = None, debug = False, logger: hp.logging.Logger = None):
    logger = logger or mlogger
    files_to_delete = files_to_delete or []
    try:
        base_png = do_download(base_png, files_to_delete)
        if not base_png:
            logger.error(f"Base PNG not found: {base_png}")
            raise ValueError(f"Base PNG not found: {base_png}")
        png_args = []
        brand_png = get_logo(brand, template, files_to_delete, logo_type='Brand', logger=logger)
        if brand_png:
            png_args.append((brand_png, template.get('brand_logo_scale', 1.0), template.get('brand_logo_position_x', 0.0), template.get('brand_logo_position_y', 0.0)))
        rooftop_png = get_logo(rooftop, template, files_to_delete, logo_type='Rooftop', logger=logger)
        if rooftop_png:
            png_args.append((rooftop_png, template.get('dealership_logo_scale', 1.0), template.get('dealership_logo_position_x', 0.0), template.get('dealership_logo_position_y', 0.0)))
        else:
            dealership_png = get_logo(dealership, template, files_to_delete, logo_type='Dealership', logger=logger)
            if dealership_png:
                png_args.append((dealership_png, template.get('dealership_logo_scale', 1.0), template.get('dealership_logo_position_x', 0.0), template.get('dealership_logo_position_y', 0.0)))
        svg_args = []
        dealership_details_svg_path = manage_svg("dealership_details", rooftop, template, files_to_delete)
        if dealership_details_svg_path:
            svg_args.append((dealership_details_svg_path, 1.0, 0, 0))
        offer_details_svg_path = manage_svg("offer_details", offer, template, files_to_delete)
        if offer_details_svg_path:
            svg_args.append((offer_details_svg_path, 1.0, 0, 0))
        slogan_svg_path = manage_svg("slogan", campaign_details, template, files_to_delete)
        if slogan_svg_path:
            svg_args.append((slogan_svg_path, 1.0, 0, 0))
        output_path = joinpath(DEFAULT_OUTPUT_PATH, f"{rooftop_type}_{hp.uuid.uuid4()}.png")
        merge_layers(base_png, png_args, svg_args, output_path=output_path, logger=logger)
        cdn_url = func_gryd_file_system(output_path, media_type='image', logger=logger)
    finally:
        for file in files_to_delete:
            if hp.ispath(file) and not debug:
                os.remove(file)
    return cdn_url

def get_rooftop_type(campaign_type: str):
    return {'pre-sales': 'showroom', 'post-sales': 'workshop', 'exchange': 'buyback_center'}.get(campaign_type)

def manage_hashtags(campaign_hashtags: typing.Union[list[str], str], previous_hashtags: str = None):
    previous_hashtags = previous_hashtags or ""
    campaign_hashtags = re.split(',|\\||;|:| |\n|\r', campaign_hashtags) if isinstance(campaign_hashtags, str) else campaign_hashtags
    campaign_hashtags = [hashtag.strip() for hashtag in campaign_hashtags]
    campaign_hashtags = [f"#{hashtag}" if not hashtag.startswith('#') else hashtag for hashtag in campaign_hashtags]
    return previous_hashtags + "".join(list(set(campaign_hashtags)))


@gryd.is_a_task(function_name="create_campaign_image", job_param='job', logger_param='logger')
def create_campaign_image(rooftop_type: str, template_id: str, base_png: str, campaign_title: str, campaign_hook: str, campaign_message: str, campaign_hashtags: typing.Union[list[str], str], campaign_caption: str, offer: dict = None, debug: bool = False, job: dict = None, logger: hp.logging.Logger = None):
    """
    # Generate a JSON payload template for the `create_campaign_image` task, including the args, kwargs, and help text.
    # This can be used to drive API docs, CLIs, or visual tools.

    create_campaign_image_payload = {
        "args": [
            "rooftop_type",
            "template_id",
            "base_png",
            "campaign_title",
            "campaign_hook",
            "campaign_message",
            "campaign_hashtags",
            "campaign_caption"
        ],
        "kwargs": {
            "offer": "Optional[dict] (default: None) - Offer details dictionary for the campaign.",
            "debug": "Optional[bool] (default: False) - Enable debug mode.",
            "job": "Optional[dict] (default: None) - Job dictionary (internal use).",
            "logger": "Optional[hp.logging.Logger] (default: None) - Logger for internal use."
        },
    }
    Create a campaign image for a dealership rooftop.

    Required Arguments:
    - rooftop_type (str): Type of rooftop, e.g., 'showroom', 'workshop', or 'buyback_center'.
    - template_id (str): The ID of the template to use for image generation.
    - base_png (str): URL or path to the base PNG image.
    - campaign_title (str): Title of the campaign.
    - campaign_hook (str): Campaign hook or tagline.
    - campaign_message (str): Campaign message content.
    - campaign_hashtags (str or list[str]): Hashtags to use for the campaign, as comma/pipe/space/semicolon separated string or list.
    - campaign_caption (str): Caption to appear with the campaign image.

    Optional Keyword Arguments:
    - offer (dict): (Optional) Offer information for the campaign.
    - debug (bool): (Optional) If True, files are not deleted and more verbose logging is used.
    - job (dict): (Optional) Internal job dictionary.
    - logger (hp.logging.Logger): (Optional) Logger instance.

    Returns:
    - cdn_url (str): CDN URL of the merged campaign image.

    Example usage:
    {
        "args": ["showroom", "india-default-theme", "https://cdn.example.com/base.png", "Limited Time Offer!", "Save Big Now", "Available for a short time", "LimitedTimeOffer|SaveBig", "Act fast and save!"],
        "kwargs": {
            "offer": {"discount": "15%", "valid_till": "2024-06-30"},
            "debug": false
        }
    }
    """
    logger = logger or mlogger
    template_model = AutocrmModel('autosphere_template')
    template = template_model.get(template_id)
    logger.info(f"Template: {template}")
    brand_model = AutocrmModel('brand')
    brand_id = template.get('brand_id')
    logger.info(f"Brand ID: {brand_id}")
    brand = brand_model.get(brand_id)
    offer = offer or DEFAULT_OFFER
    dealership_model = AutocrmModel('dealership')
    rooftop_model = get_rooftop_model(rooftop_type, logger=logger)
    logger.info(f"Brand ID: {brand_id}")
    rooftop = hp.make_single(rooftop_model.list(_page_size=1, _as_option=True, supported_brands=[brand_id], **{'logo_url~': None}), force=True)
    dealership_id = rooftop.get('dealership_id')
    dealership = dealership_model.get(dealership_id)
    logger.info(f"Dealership: {dealership}")
    campaign_hashtags = manage_hashtags(campaign_hashtags or [])
    campaign_hashtags = manage_hashtags(brand.get('hashtags') or [], previous_hashtags=campaign_hashtags)
    campaign_hashtags = manage_hashtags(rooftop.get('hashtags') or [], previous_hashtags=campaign_hashtags)
    campaign_details = {
        "title": campaign_title,
        "hook": campaign_hook,
        "message": campaign_message,
        "hashtags": campaign_hashtags,
        "caption": campaign_caption
    }
    return do_the_merge(template_id, base_png, template, brand, rooftop=rooftop, dealership=dealership, campaign_details=campaign_details, offer=offer, debug=debug, logger=logger)

def get_rooftop_model(rooftop_type: str, logger: hp.logging.Logger = None):
    logger = logger or mlogger
    if rooftop_type == "workshop":
        return AutocrmModel('workshop')
    elif rooftop_type == "showroom":
        return AutocrmModel('showroom')
    elif rooftop_type == "buyback_center":
        return AutocrmModel('buyback_center')
    else:
        raise ValueError(f"Invalid rooftop type: {rooftop_type}")

def get_rooftop_post_model(rooftop_type: str, logger: hp.logging.Logger = None):
    logger = logger or mlogger
    if rooftop_type == "workshop":
        return AutocrmModel('post_workshop')
    elif rooftop_type == "showroom":
        return AutocrmModel('post_showroom')
    elif rooftop_type == "buyback_center":
        return AutocrmModel('post_buyback_center')
    else:
        raise ValueError(f"Invalid rooftop type: {rooftop_type}")

def get_rooftop(rooftop_type: str, rooftop_id: str, logger: hp.logging.Logger = None, dealership_model: AutocrmModel = None):
    logger = logger or mlogger
    rooftop_model = get_rooftop_model(rooftop_type, logger=logger)
    rooftop = rooftop_model.get(rooftop_id)
    logger.info(f"Rooftop: {rooftop}")
    dealership_model = dealership_model or AutocrmModel('dealership')
    dealership = dealership_model.get(rooftop.get('dealership_id'))
    logger.info(f"Dealership: {dealership}")
    return rooftop, dealership, rooftop_model, dealership_model

def get_template_by_supported_brands(supported_brands: list[str], logger: hp.logging.Logger = None, brand_model: AutocrmModel = None, template_model: AutocrmModel = None):
    logger = logger or mlogger
    brand_model = brand_model or AutocrmModel('brand')
    template_model = template_model or AutocrmModel('autosphere_template')
    for brand_id in supported_brands:
        template = hp.make_single(template_model.list(_page_size=1, _as_option=True, brand_id=brand_id), force=True)
        if template:
            return template
    return None


@gryd.is_a_task(function_name="create_rooftop_image", job_param='job', logger_param='logger')
def create_rooftop_image(
    rooftop_type: str, 
    brand_id: str = None, # The ID of the brand to use for image generation, not required if rooftop_id is provided.
    rooftop_address: str = None, # Address of the rooftop, not required if rooftop_id is provided.
    rooftop_phone_number: str = None, # Phone number of the rooftop, not required if rooftop_id is provided.
    logo_url: str = None, # Logo URL of the rooftop, not required if rooftop_id is provided.
    rooftop_email: str = None, # Email of the rooftop, not required if rooftop_id is provided.
    theme_type: str = 'default', # Type of theme, e.g., 'light', 'dark', or 'default'.
    rooftop_id = None, # The ID of the rooftop to use for image generation, if provided, will override the other arguments.
    offer: dict = None, # Offer information for the campaign.
    campaign_details: dict = None, # Campaign details dictionary for the campaign.
    debug: bool = False, 
    job: dict = None, 
    logger: hp.logging.Logger = None
    ):
    """
    # Generate a JSON payload template for the `create_rooftop_image` task, including the args, kwargs, and help text.
    # This can be used to drive API docs, CLIs, or visual tools.
    create_rooftop_image_payload = {
        "args": [
            "rooftop_type", # Type of rooftop, e.g., 'showroom', 'workshop', or 'buyback_center'.
            "brand_id", # The ID of the brand to use for image generation.
            "theme_type", # Type of theme, e.g., 'light', 'dark', or 'default'.
            "rooftop_address": "str - Address of the rooftop.",
            "rooftop_phone_number": "str - Phone number of the rooftop.",
        ],
        "kwargs": {
            "rooftop_email": "Optional[str] (default: None) - Email of the rooftop.",
            "logo_url": "Optional[str] (default: None) - Logo URL of the rooftop.",
            "rooftop_id": "Optional[str] (default: None) - The ID of the rooftop to use for image generation.",
            "offer": "Optional[dict] (default: None) - Offer details dictionary for the campaign.",
        }
    }
    Create a rooftop image for a dealership rooftop.

    Required Arguments:
    - rooftop_type (str): Type of rooftop, e.g., 'showroom', 'workshop', or 'buyback_center'.
    Optional Argument Set:
    - brand_id (str) : The ID of the brand to use for image generation.
    - rooftop_address (str): Address of the rooftop.
    - rooftop_phone_number (str): Phone number of the rooftop.
    - logo_url (str): Logo URL of the rooftop.
    - rooftop_email (str): Email of the rooftop.
    - theme_type (str): Type of theme, e.g., 'light', 'dark', or 'default'.
    OR
    - rooftop_id (str): The ID of the rooftop to use for image generation.

    Optional Keyword Arguments:
    - offer (dict): (Optional) Offer information for the campaign.
    - campaign_details (dict): Campaign details dictionary for the campaign.
    - debug (bool): (Optional) If True, files are not deleted and more verbose logging is used.
    - job (dict): (Optional) Internal job dictionary.
    - logger (hp.logging.Logger): (Optional) Logger instance.

    Returns:
    - cdn_url (str): CDN URL of the merged rooftop image.

    Example usage:
    {
        "args": ["showroom", "jeep-jeep-india", "123 Main St", "123-456-7890", "https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp", "light"],
        "kwargs": {
            "rooftop_email": "info@jeep.com",
            "offer": {"offer_currency": "₹", "offer_amount": "10.55", "offer_units": "Lakh", "offer_terms": "*Valid for limited time only"},
            "campaign_details": {
                "title": "Limited Time Offer",
                "hook": "Save Big on Your Next Purchase",
                "message": "Don't miss out on this limited time offer. Act now to get the best price on your next purchase.",
                "hashtags": "#LimitedTimeOffer #SaveBig #ActNow",
                "caption": "Limited Time Offer: Save Big on Your Next Purchase"
            }
        }
    }
    """
    logger = logger or mlogger
    if rooftop_id:
        rooftop, dealership, rooftop_model, dealership_model = get_rooftop(rooftop_type, rooftop_id, logger=logger)
    else:
        if not all([rooftop_address, rooftop_phone_number, logo_url, brand_id]):
            raise ValueError(f"Missing required arguments: rooftop_address, rooftop_phone_number, rooftop_email, logo_url, brand_id")
        rooftop = {
            "address": rooftop_address,
            "phone_number": rooftop_phone_number,
            "email": rooftop_email,
            "supported_brands": [brand_id],
        }
        dealership = {}
        if theme_type == 'light':
            rooftop['light_theme_logo_url'] = logo_url
            dealership['light_theme_logo_url'] = logo_url
        elif theme_type == 'dark':
            rooftop['dark_theme_logo_url'] = logo_url
            dealership['dark_theme_logo_url'] = logo_url
        elif theme_type == 'default':
            rooftop['logo_url'] = logo_url
            dealership['logo_url'] = logo_url
    offer = offer or DEFAULT_OFFER
    brand_model = AutocrmModel('brand')
    post_idea_model = AutocrmModel('post_idea')
    template_model = AutocrmModel('autosphere_template')
    idea_params = {'brand_id': rooftop.get('supported_brands'), '_as_option': True}
    post_ideas = post_idea_model.list(**idea_params)
    if not post_ideas:
        raise ValueError(f"No ideas found for supported brands: {rooftop.get('supported_brands')}")
    post_idea = hp.random.choice(post_ideas)
    brand_id = post_idea.get('brand_id')
    brand = brand_model.get(brand_id)
    logger.info(f"Brand: {brand}")
    campaign_details = {
        "title": post_idea.get('slogan'),
        "hook": post_idea.get('hook'),
        "message": post_idea.get('message'),
        "hashtags": manage_hashtags(post_idea.get('hashtags', []) + post_idea.get('brand_hashtags', []) + post_idea.get('dealership_hashtags', [])),
        "caption": post_idea.get('caption')
    }
    template_id = post_idea.get('autosphere_template_id')
    template = template_model.get(template_id)
    logger.info(f"Template: {template}")
    base_png = post_idea.get('image_url')
    return do_the_merge(
        rooftop_type, 
        base_png, 
        template, 
        brand = None, 
        rooftop=rooftop, 
        dealership=None, 
        offer = offer, 
        debug=debug, 
        logger=logger
    )

@gryd.is_a_task(function_name="create_rooftop_images_batch", job_param='job', logger_param='logger')
def create_rooftop_images_batch(post_idea_id: str, debug: bool = False, job: dict = None, logger: hp.logging.Logger = None):
    logger = logger or mlogger
    post_idea_model = AutocrmModel('post_idea')
    brand_model = AutocrmModel('brand')
    template_model = AutocrmModel('autosphere_template')
    dealership_model = AutocrmModel('dealership')
    rooftop_type = {'pre-sales': 'showroom', 'post-sales': 'workshop', 'exchange': 'buyback_center'}.get(post_idea.get('campaign_type'))
    if not rooftop_type:
        raise ValueError(f"Invalid campaign type: {post_idea.get('campaign_type')}")
    rooftop_model = get_rooftop_model(rooftop_type, logger=logger)
    post_idea = post_idea_model.get(post_idea_id)
    if not post_idea:
        raise ValueError(f"Post idea not found: {post_idea_id}")
    region_id = post_idea.get('region_id')
    brand_id = post_idea.get('brand_id')
    brand = brand_model.get(brand_id)
    template_id = post_idea.get('template_id')
    template = template_model.get(template_id)
    rooftop_post_model = get_rooftop_post_model(rooftop_type, logger=logger)
    offer = DEFAULT_OFFER
    campaign_details = {
        "title": post_idea.get('slogan'),
        "hook": post_idea.get('hook'),
        "message": post_idea.get('message'),
        "hashtags": manage_hashtags(post_idea.get('hashtags', []) + post_idea.get('brand_hashtags', []) + post_idea.get('dealership_hashtags', [])),
        "caption": post_idea.get('caption')
    }
    offer = offer or DEFAULT_OFFER
    base_png = post_idea.get('image_url')
    base_png = do_download(base_png, files_to_delete)
    if not base_png:
        logger.error(f"Base PNG not found: {base_png}")
        raise ValueError(f"Base PNG not found: {base_png}")
    rooftop_params = {"region_id": region_id, "supported_brands": brand_id, '_as_option': True}
    any_rooftops = 0
    files_to_delete = []
    for rooftop in rooftop_model.model.yield_list(**rooftop_params):
        logger.info(f"Rooftop: {rooftop}")
        any_rooftops += 1
        rooftop_id = rooftop.get(f'{rooftop_type}_id')
        dealership = dealership_model.get(rooftop.get('dealership_id'))
        cdn_url = do_the_merge(rooftop_type, base_png, template, brand, rooftop=rooftop, dealership=dealership, debug=debug, logger=logger)
        yield {
            "rooftop_type": rooftop_type,
            "post_idea_id": post_idea_id,
            f"{rooftop_type}_id": rooftop_id,
            "template_id": template.get('template_id'),
            "dealership_id": dealership.get('dealership_id'),
            "region_id": dealership.get('region_id'),
            "brand_id": brand.get('brand_id'),
            "cdn_url": cdn_url,
        }
        rooftop_post_model.post({
            "post_idea_id": post_idea_id,
            f"{rooftop_type}_id": rooftop_id,
            "image_url": cdn_url,
            "campaign_objective_id": post_idea.get('campaign_objective_id')
        })
    if not any_rooftops:
        raise ValueError(f"No rooftops found for type: {rooftop_type} with params: {rooftop_params}")
    return {'rooftops': any_rooftops}

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

word_blacklist = {
    "person", "people", "human", "man", "woman", "boy", "girl", "child", "children", "baby", "infant"
    "toddler", "teen", "teenager", "adult", "elderly", "senior", "pedestrian", "driver", "passenger", "bystander", "crowd"
    "mob", "figure", "silhouette", "body", "face", "head", "hand", "arm", "leg", "foot", "eye"
    "mouth", "nose", "portrait", "selfie", "model", "avatar", "character", "individual", "subject", "rider", "cyclist"
    "motorcyclist", "pedestrians", "jogger", "runner", "walker", "tourist", "commuter", "shopper", "worker", "employee", "officer"
    "guard", "soldier", "cop", "police", "military", "protester", "activist", "demonstrator", "fan", "spectator", "audience"
    "couple", "family", "group", "team", "gang", "biker", "skater", "bmx", "trucker", "hitchhiker", "gun"
    "pistol", "rifle", "shotgun", "firearm", "weapon", "knife", "blade", "sword", "machete", "axe", "bomb"
    "explosive", "grenade", "missile", "rocket", "cannon", "artillery", "tank", "mortar", "landmine", "taser", "mace"
    "baton", "nightstick", "crossbow", "bow", "arrow", "spear", "dart", "dagger", "revolver", "snissor", "sniper"
    "assault", "automatic", "semi-automatic", "magazine", "ammo", "ammunition", "bullet", "shell", "cartridge", "holster", "suppressor"
    "silencer", "scope", "trigger", "barrel", "stock", "shooter", "gunman", "armed", "unarmed", "violence", "attack"
    "fight", "war", "combat", "battle", "conflict", "murder", "kill", "shoot", "stab", "slash", "explosion"
    "detonation", "blast", "fire", "arson", "flamethrower", "nuke", "nuclear", "chemical", "biological", "weapons", "armory"
    "arsenal", "militant", "terrorist", "criminal", "thug", "cartel", "mafia", "crash", "accident", "collision", "wreck"
    "smash", "totaled", "flipped", "rollover", "burning", "damaged", "dented", "broken", "destroyed", "flood", "submerged"
    "sinking", "wrecked", "abandoned", "derelict", "rusted", "junkyard", "scrapyard", "salvage", "towing", "breakdown", "stranded"
    "recall", "defect", "malfunction", "lemon", "faulty", "unsafe", "dangerous", "hazardous", "toxic", "polluting", "smoke"
    "exhaust", "fumes", "oil spill", "leak", "lawsuit", "scandal", "fraud", "theft", "stolen", "carjacking", "vandalized"
    "graffiti", "keyed", "slashed", "broken windows", "stripped", "racist", "racism", "nazi", "swastika", "kkk", "confederate"
    "hate", "slur", "offensive", "bigot", "sexist", "misogyny", "homophobic", "transphobic", "antisemitic", "islamophobic", "xenophobic"
    "supremacist", "extremist", "radical", "propaganda", "genocide", "massacre", "lynching", "slavery", "discrimination", "oppression", "derogatory"
    "vulgar", "obscene", "profane", "taboo", "banned", "illegal", "pornographic", "explicit", "nsfw", "sexual", "nudity"
    "nude", "erotic", "indecent", "lewd", "fetish", "drugs", "marijuana", "cannabis", "weed", "cocaine", "heroin"
    "meth", "methamphetamine", "lsd", "ecstasy", "mdma", "pills", "opioids", "narcotics", "alcohol", "drunk", "intoxicated"
    "wasted", "high", "stoned", "bong", "pipe", "syringe", "needle", "injection", "overdose", "addiction", "substance"
    "illicit", "contraband", "smuggling", "trafficking", "dealer", "dispensary", "420", "spliff", "blunt", "joint", "vape"
    "vaping", "smoking", "cigarette", "tobacco", "cigar", "flag", "political", "protest", "riot", "revolution", "government"
    "democracy", "communism", "fascism", "anarchy", "election", "campaign", "vote", "ballot", "party", "republican", "democrat"
    "liberal", "conservative", "socialist", "nationalist", "militia", "coup", "uprising", "insurrection", "religious", "church", "mosque"
    "temple", "shrine", "cross", "crucifix", "crescent", "star of david", "icon", "idol", "cult", "satanic", "occult"
    "voodoo", "superstition", "pagan", "ritual", "ceremony", "prayer", "worship", "blasphemy", "sacrilege", "toyota", "honda"
    "ford", "chevrolet", "chevy", "bmw", "mercedes", "audi", "volkswagen", "vw", "tesla", "nissan", "hyundai"
    "kia", "mazda", "subaru", "jeep", "dodge", "chrysler", "ram", "gmc", "cadillac", "buick", "lincoln"
    "acura", "lexus", "infiniti", "volvo", "peugeot", "renault", "citroen", "fiat", "alfa romeo", "ferrari", "lamborghini"
    "bugatti", "porsche", "mclaren", "aston martin", "bentley", "rolls royce", "maserati", "pagani", "koenigsegg", "rimac", "rivian"
    "lucid", "polestar", "genesis", "mitsubishi", "suzuki", "isuzu", "land rover", "jaguar", "skoda", "dacia", "lancia"
    "opel", "vauxhall", "saab", "pontiac", "oldsmobile", "plymouth", "mini", "smart", "seat", "street racing", "drag racing"
    "wrong way", "drunk driving", "hit and run", "road rage", "tailgating", "stunts", "wheelie", "donut", "handbrake", "joyriding", "heist"
    "robbery", "crime", "felony", "misdemeanor", "fugitive", "chase", "pursuit", "escape", "evasion", "police chase", "carjack"
    "hotwire", "hack", "tamper", "bypass", "fake", "counterfeit", "knockoff", "black market", "underground", "illegal modification", "ghost car"
    "kidnapping", "battlefield", "warzone", "military base", "prison", "jail", "cemetery", "graveyard", "morgue", "slaughterhouse", "brothel"
    "strip club", "casino", "drug den", "ghetto", "slum", "abandoned building", "condemned", "demolition", "landfill", "toxic waste", "nuclear plant"
    "meth lab", "crime scene", "accident scene", "disaster zone", "flood zone", "tsunami", "earthquake", "tornado", "hurricane", "wildfire", "war memorial"
    "execution", "gallows", "electric chair", "dungeon", "torture", "interrogation", "surveillance", "spy", "undercover", "sting operation", "license plate"
    "number plate", "registration", "vin", "serial number", "tracking", "gps", "location", "address", "personal data", "identity", "passport"
    "id card", "driver license", "face recognition", "biometric", "fingerprint", "stalking", "doxing", "hacking", "phishing", "malware", "ransomware"
    "data breach", "expose", "private", "confidential", "classified", "secret", "covert", "blood", "gore", "corpse", "dead"
    "death", "skull", "bones", "skeleton", "ghost", "demon", "devil", "evil", "curse", "haunted", "zombie"
    "virus", "plague", "pandemic", "epidemic", "infection", "contamination", "radiation", "biohazard", "skull and crossbones", "danger", "warning"
    "caution", "hazard", "poison", "venom", "flammable", "radioactive", "restricted", "forbidden", "prohibited", "blocked", "censored"
    "redacted", "top secret", "leaked", "whistleblower", "controversy", "inappropriate", "disturbing", "graphic", "violent", "18+", "adult only"
    "mature", "tits", "boobs", "jugs", "ass", "arse", "pussy", "vagina", "penis", "cock", "dick"
    "balls", "testicles", "asshole", "fuck", "shit", "piss", "cum", "jizz", "semen", "orgasm", "ejaculation"
    "erection", "masturbation", "porn", "pornography", "naked", "nakedness", "gonzo", "erotism", "eroticism", "milf", "busty"
    "titty", "double penetration", "kink", "rape", "raped", "raping", "rapist", "beastiality", "fuckfisting", "anal", "anus"
    "blowjob", "bj", "cunnilingus", 
}

@gryd.is_a_task(function_name = "validate_prompt", job_param = 'job', logger_param = 'logger')
def validate_prompt(prompt: str, car_manufacturer: str = None, car_model: str = None, validate_prompt_model: str = None, job = None, logger = None):
    logger = logger or mlogger
    car_manufacturer = car_manufacturer or "Unknown"
    car_model = car_model or "Unknown model"
    validate_prompt_model = validate_prompt_model or VALIDATE_PROMPT_MODEL
    prompt = prompt.lower().strip()
    car_manufacturer = car_manufacturer.lower().strip()
    car_model = car_model.lower().strip()
    lprompt = set(prompt.split())
    blw = set()
    cmf = set(car_manufacturer.split())
    cmm = set(car_model.split())
    for word in lprompt:
        if word in cmf or word in cmm:
            continue
        if word in word_blacklist:
            blw.add(word)
    if blw:
        return {"valid": False, "reason": f"Prompt contains blacklisted word(s): {', '.join(blw)}"}
    r = ai_service.get_llm_response(user_query=prompt, system_prompt=f"""
You are a prompt validator. 
*Allowed Car manufacturer or brand: {car_manufacturer}*
*Allowed Car model or variant: {car_model}*
*Allowed car manufacturer, brand, model or variant, are allowed to be used in the prompt, but not obligated to be used.*
You will be given a prompt and you will need to validate it to make sure the prompt
- only contains instructions which can be interpreted as asking for a specific background or theme, and not modifiying the car itself
- contains no information about car manufacturers except the allowed car manufacturer or brand
- contains no information about car models except the allowed car model or variant
- does not contain any offensive, curse words, or sensitive words, for example,
    racist, racism, nazi, nazis, swastika, kkk,
    confederate, hate, hateful, slur, offensive, bigot,
    bigotry, sexist, sexism, misogyny, homophobic, transphobic,
    antisemitic, islamophobic, xenophobic, supremacist,
    extremist, radical, terrorist, terrorism, propaganda,
    genocide, massacre, lynching, slavery, discrimination,
    oppression, derogatory, vulgar, obscene, profane,
    pornographic, explicit, nsfw, sexual, nudity, erotic,
    indecent, lewd, fetish, xxx, adult content
- does not contain any urls. 
- does not contain any email addresses. 
- does not contain any phone numbers. 
- does not contain any personal information. 
- does not contain any sensitive information. 
- does not contain any confidential information. 
- does not request identifiable personal data or surveillance imagery
- does not environment may not be suitable for a car brand background, such as 
    battlefield, warzone, war zone, military base, prison,
    jail, cemetery, graveyard, morgue, slaughterhouse,
    brothel, strip club, drug den, abandoned building,
    condemned, demolition, landfill, toxic waste, nuclear plant,
    meth lab, crime scene, accident scene, disaster zone,
    flood zone, execution, gallows, dungeon, interrogation,
    torture chamber, ghetto, slum, red light district, etc.
- does not depict the brand, manufacturer, or model of the car in any way that damages its name or value, such as
    crash, crashed, crashing, accident, collision, collide,
    wreck, wrecked, smash, smashed, totaled, flipped,
    rollover, fire, burning, on fire, exploding, explosion,
    damaged, dented, broken, destroyed, flood, flooded,
    submerged, sinking, sunken, wrecked, abandoned, derelict,
    rusted, rusty, junkyard, scrapyard, salvage, towing,
    towed, breakdown, stranded, recall, defect, malfunction,
    lemon, faulty, unsafe, dangerous, hazardous, toxic,
    polluting, smoke, exhaust fumes, oil spill, leak,
    lawsuit, scandal, fraud, theft, stolen, carjacking,
    vandalized, vandalism, graffiti, keyed, slashed,
    stripped, scrapped, demolition derby, junk, heap,
    clunker, beater, rust bucket
- does not depict illegal or reckless driving behaviour, with words such as
    speeding, racing, street racing, drag racing, wrong way,
    drunk driving, hit and run, road rage, tailgating, stunts,
    wheelie, donut, burnout, reckless, illegal, joyriding,
    stolen, heist, robbery, smuggling, trafficking, crime,
    felony, fugitive, chase, pursuit, escape, evasion,
    police chase, carjack, hotwire, tamper, counterfeit,
    underground, murder, kidnapping, getaway, fleeing,
    reckless driving, illegal driving, joyriding, stolen, heist,
    robbery, smuggling, trafficking, crime, felony,
    chase, pursuit, escape, evasion, police chase, carjack,
    hotwire, tamper, counterfeit, underground, murder, kidnapping,
    getaway, fleeing, etc.
- does not contain any proprietary information. 
- does not contain any confidential information. 
- does not contain any html tags. 
- does not contain any markdown tags. 
- does not contain any code. 
- does not contain any code blocks. 
- does not contain any code snippets. 
- does not contain any code examples. 
- does not contain any other instructions or instructions which are not related to background change
- does not ask to modify the car which is the subject of the image in any way
- does not ask to add any other objects to the image
- does not contain any content related to accident, harm, violence, danger, scene, fire, death, blood, gore, etc.
- does not contain any content related to sex, nudity, pornography, etc.
- does not contain any content related to drugs, alcohol, smoking, etc.
- does not contain any content related to religion, politics, etc.
- does not contain any content related to war, conflict, fire, explosion, guns, bombs, missiles, flood, tsunami, earthquake, tornado, hurricane, wildfire, etc.
    gun, guns, pistol, rifle, shotgun, firearm, firearms,
    weapon, weapons, knife, knives, blade, sword, machete,
    axe, hatchet, bomb", explosive, explosives, grenade,
    missile, rocket, cannon, artillery, tank, mortar,
    landmine, taser, mace, baton, nightstick, crossbow,
    bow, arrow", spear, dart, dagger, revolver, sniper,
    assault, automatic, semiautomatic, magazine, ammo",
    ammunition, bullet, bullets, shell, cartridge, holster,
    suppressor, silencer, scope, trigger, barrel, stock,
    shooter, gunman, armed, armory, arsenal, flamethrower,
    nuke, nuclear, chemical weapon, biological weapon,
    combat, warfare, battle, attack, raid, ambush,
    sniper, mercenary, militia, paramilitary, guerrilla
- does not contain any content related to humans, people or animals, words containing
    person, people, human, humans, man, men, woman, women,
    boy, boys, girl, girls, child, children, kid, kids,
    baby, infant, toddler, teen, teenager, adult, elderly,
    senior, pedestrian, pedestrians, driver, passenger, passengers,
    bystander, crowd, mob, portrait, selfie, model, avatar, character, individual,
    rider, cyclist, motorcyclist, jogger, runner, walker
    tourist, commuter, shopper, worker, employee, officer,
    guard, soldier, cop, police, military, protester, activist,
    demonstrator, fan, spectator, audience, couple, family,
    group, team, gang, biker, skater, trucker, hitchhiker, portrait
- does not contain any content related to parts of human or animal body, words containing
    figure, silhouette, body, face,
    head, hand, arm, leg, foot, eye, mouth, nose, torso, bust, headshot
- does not contain any content about shadows, reflections or silhouettes, words containing
    mannequin, dummy, ghost, skeleton, corpse
- does not contain any content related to other objects to be in contact with the car
If the prompt is valid, you will return json {{"valid": true}}. 
If the prompt is invalid, you will return json {{"valid": false, "reason": <reason why it is invalid>}}.
Strictly follow the json format and only json in the response, without the json block.

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
    with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{original_suffix}', delete=False) as f:
        original_temp_file_path = f.name
    with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{generated_suffix}', delete=False) as f:
        generated_temp_file_path = f.name
    try:
        original_temp_file_path = download_file(original_image_url, original_temp_file_path)
        generated_temp_file_path = download_file(generated_image_url, generated_temp_file_path)
        result = compare_images(
            original_temp_file_path, 
            generated_temp_file_path, 
            model=model, 
            verbose=False, 
            logger=logger
        )
        return result
    finally:
        os.remove(original_temp_file_path)
        os.remove(generated_temp_file_path)
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="""
    Spark CLI --
    --function <function_name> --kwargs <kwargs>
    Example:
    python spark.py --function openai_image_generation --kwargs input_image_url=https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp,prompt=Change the background to scenic view from the suburbs of Mumbai
    python spark.py --function comfy_image_generation --kwargs input_image_url=https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp,prompt=Change the background to scenic view from the suburbs of Mumbai
    python spark.py --function gemini_image_generation --kwargs input_image_url=https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp,prompt=Change the background to scenic view from the suburbs of Mumbai
    python spark.py --function compare_images --kwargs original_image_url=https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp,generated_image_url=https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp
    python spark.py --function validate_prompt --kwargs prompt=Change the background to scenic view from the suburbs of Mumbai,car_manufacturer=Maruti,car_model=Swift
    python spark.py --function distortion_report --kwargs image_path=https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp

    python spark.py --function create_rooftop_images_batch --kwargs "region_id=india,\
    brand_id=jeep-jeep-india,\
    rooftop_type=showroom,\
    base_png=https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/c06608a2-8f94-4e14-8122-8a6196e27df2-69c27292_Base_image.png,\
    rooftop_id=stellantis - kht-agencies-private-limited - bengaluru,\
    template_id=india-default-jeep-theme-jeep-jeep-india-meridian-jeep-jeep-default-1080x1350"
    
    
    python spark.py --function create_rooftop_image --kwargs "rooftop_type=showroom,\
    brand_id=jeep-jeep-india,\
    rooftop_address=Rajiv Gandhi Nagar Sector 1 New Delhi Delhi 110016,\
    rooftop_phone_number=+91 9876543210,\
    logo_url=https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp,\
    rooftop_email=info@jeep.com,\
    theme_type=dark"

    python spark.py --function create_campaign_image --kwargs "rooftop_type=showroom,\
    template_id=india-default-jeep-theme-jeep-jeep-india-meridian-jeep-jeep-default-1080x1350,\
    base_png=https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/c06608a2-8f94-4e14-8122-8a6196e27df2-69c27292_Base_image.png,\
    campaign_title=Limited Time Offer,\
    campaign_hook=Save Big on Your Next Purchase,\
    campaign_message=Don't miss out on this limited time offer. Act now to get the best price on your next purchase.,\
    campaign_hashtags=LimitedTimeOffer|SaveBig|ActNow,\
    campaign_caption=Limited Time Offer: Save Big on Your Next Purchase"


    python spark.py --function merge_layers --kwargs base_png=https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp,png_layers=https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp,svg_layers=https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp,output_path=https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp
    python spark.py --function pad_and_resize_image --kwargs image_path=https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp,output_dimensions=1024,1024"
    """)
    parser.add_argument("--function", type=str, required=True, help="Function to run")
    parser.add_argument("--kwargs", type=str, required=True, help="kwargs to pass to the function")
    args = parser.parse_args()
    kwargs = {}
    for a in args.kwargs.split(','):
        k = a.strip().split('=')
        kwargs[k[0]] = k[1]
    print(f"kwargs: {kwargs}")
    if args.function == "openai_image_generation":
        print(openai_image_generation(**kwargs))
    elif args.function == "comfy_image_generation":
        print(comfy_image_generation(**kwargs))
    elif args.function == "gemini_image_generation":
        print(gemini_image_generation(**kwargs))
    elif args.function == "compare_images":
        print(compare_images_func(**kwargs))
    elif args.function == "validate_prompt":
        print(validate_prompt(**kwargs))
    elif args.function == "distortion_report":
        print(distortion_report(**kwargs))
    elif args.function == "create_rooftop_images_batch":
        print(list(create_rooftop_images_batch(**kwargs, debug=True)))
    elif args.function == "create_rooftop_image":
        print(create_rooftop_image(**kwargs, debug=True))
    elif args.function == "create_campaign_image":
        print(create_campaign_image(**kwargs, debug=True))
    elif args.function == "merge_layers":
        print(merge_layers_task(**kwargs))
    elif args.function == "pad_and_resize_image":
        print(pad_and_resize_image_task(**kwargs))
    else:
        print(f"Invalid function: {args.function}")

#     input_image_url = "https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9f13e041-1014-4cd4-bf3c-dce4421f0cd9-6988a6cf_testimage.webp"
#     prompt = "Change the background to scenic view from the suburbs of Mumbai"
#     number_of_images = 1
#     print(openai_image_generation(input_image_url, prompt, number_of_images))

    

