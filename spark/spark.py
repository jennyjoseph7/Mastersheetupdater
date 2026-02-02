import sys
import os, re
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from gryd_worker import gryd, gryd_helpers as hp
json = hp.json
APP_DIR = dirname(abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.append(APP_DIR)
from combine_images import merge_layers
from check_distortion import analyze_image
from core import func_gryd_file_system
SERVICE = 'spark'
gryd.SERVICE = SERVICE
gryd.set_queue_manager()
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



