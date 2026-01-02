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



def format_phone_number(phone_number, country_code="+91"):
    """Format phone number to E.164 format."""
    phone_number = phone_number.strip().replace(" ", "").replace("-", "")
    
    if not phone_number.startswith("+"):
        if len(phone_number) == 10:
            phone_number = country_code + phone_number
        elif phone_number.startswith("0"):
            phone_number = country_code + phone_number[1:]
        elif len(phone_number) > 10 and phone_number.startswith(country_code.lstrip("+")):
            phone_number = "+" + phone_number
    return phone_number