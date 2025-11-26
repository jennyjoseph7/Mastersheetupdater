"""Utility helpers for voice package."""

import logging
from gryd_worker import gryd_helpers as hp

def get_logger(module = None):
    return hp.get_logger(module or __name__)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s:%(module)s:%(funcName)s:%(lineno)d - %(message)s"
    )
    return logging.getLogger(module or __name__)
