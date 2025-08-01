import os 
import traceback 
import logging
import time

GRYD_SERVICE = "autobot-agents"
GRYD_CONFIG = {
    "broker_type" : "sqs", 
    "timeout" : 10
    }

def get_logger(name, log_level = "info"):
    log_level = log_level.upper()
    if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        raise ValueError("Invalid log level. Please use one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    logging.basicConfig(
        format = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s", 
        level = getattr(logging, log_level))
    logging.Formatter.converter = time.gmtime
    logger = logging.getLogger(name)
    return logger