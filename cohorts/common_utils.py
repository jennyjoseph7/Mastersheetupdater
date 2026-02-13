import logging
import hashlib
import time

def get_logger(name, log_level = "info"):
    log_level = log_level.upper()
    if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        raise ValueError("Invalid log level. Please use one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    # logging.Formatter.converter = time.gmtime
    logging.Formatter.converter = lambda *args: time.localtime(time.time() + 5.5*3600)
    logging.basicConfig(
        format = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s", 
        level = getattr(logging, log_level))
    logger = logging.getLogger(name)
    return logger

logger = get_logger(__name__)

def generate_id_using_string(string: str, length: int = 16) -> str:
    if string is None:
        string = ""
    return hashlib.sha256(string.encode()).hexdigest()[:length]