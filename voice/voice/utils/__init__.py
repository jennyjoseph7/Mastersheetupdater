"""Utility helpers for voice package."""

import logging


def get_logger(module = None):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s:%(module)s:%(funcName)s:%(lineno)d - %(message)s"
    )
    return logging.getLogger(module or __name__)
