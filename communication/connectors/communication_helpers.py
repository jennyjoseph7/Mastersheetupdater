# from autocrm_db_helper import get_pg_connector
import functools
import os
import sys
import json
import time
import uuid
import base64
import pprint
import requests
import orjson
from dateutil.relativedelta import relativedelta 
from decimal import Decimal
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union, Callable,Tuple,Generator
# from urllib.parse import urlparse
from os.path import (
    exists as ispath,
    dirname,
    abspath,
    basename,
    join as joinpath,
    split as pathsplit,
    splitext,
    sep as dirsep,
    isfile
)

#TEST from validate_email import validate_email

# --- Set import path for internal modules ---
sys.path.insert(0, dirname(dirname(abspath(__file__))))

# ------- Load All Configs ----------------------
from connectors.communication_configs import *
# ------------------------------------------------
# Path to parent folder
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PARENT_DIR)

from autocrm_db_helper import get_pg_connector

GRYD_BASE_URL="http://127.0.0.1:5000"
GRYD_HEADERS= {
  'Content-Type': 'application/json',
  'X-GRYD-ENTERPRISE-ID': 'autocrm',
  'X-GRYD-TOKEN': '53014452-7df1-351c-9b79-af13d3d6b92f',
  'X-GRYD-SESSION-ID': '94b970d4-5c2b-3762-bf65-272901d0ad53',
  'Accept': 'application/json',
  'X-GRYD-ROLE': 'agent'
}

# import dbConnector
# from dbConnector import *

# try:
#     @gryd.is_a_task(function_name="resetdbCreds")
#     def resetdbCreds(*args, **kwargs):
#         logger.info("[TASK resetdbCreds] Started task to reload WhatsApp credentials")
#         try:
#             dbConnector.LoadGloablWhatsappCreds(*args, **kwargs)
#             logger.info("[TASK resetdbCreds] WhatsApp credentials reloaded successfully")
#         except Exception as e:
#             logger.error(f"[TASK resetdbCreds] Failed to reload credentials: {str(e)}", exc_info=True)
# except Exception as e:
#     logger.error("Unable to load reset creds")
#     pass

# --- Model loaders ---
default_get_or_load_model = gryd.load_gryd_model
NullEmptyCheck=[None, "", "null", "None"]



# api methods to use it from Gryd 

def get_all_objects(model_name):
    payload = {
        "args": [
            "list",
            model_name
        ]
    }
    # logger.info(f"TEST in get_all_objects func- payload-{payload}- GRYD_BASE_URL-{GRYD_BASE_URL}-GRYD_HEADERS-{GRYD_HEADERS}")
    
    r=requests.post(f'{GRYD_BASE_URL}/gryd/api/db/get_api_functions',
                headers=GRYD_HEADERS,
                json=payload)
    r=r.json()
    try:
        data = r.get("data")

        if not data:
            # logger.info("TEST get_all_objects --- [] (empty result)")
            return None 

        # logger.info(f"TEST get_all_objects --- {data}")
        return data[0]
    
    except Exception:
        return {"error": "Invalid JSON response", "text": r.text}

def get_objects_by_filter(model_name, filter):
    payload = {
        "args": ["list", model_name],
        "kwargs": {"data": filter}
    }

    r = requests.post(
        f'{GRYD_BASE_URL}/gryd/api/db/get_api_functions',
        headers=GRYD_HEADERS,
        json=payload
    )
    r = r.json()

    try:
        data = r.get("data")

        if not data:
            # logger.info("TEST get_objects_by_filter --- [] (empty result)")
            return None 

        # logger.info(f"TEST get_objects_by_filter --- {data}")
        return data[0]

    except Exception as e:
        return {"error": "Invalid JSON response", "text": str(r)}

def post_data(model_name,data):
    payload={
        "args": [
            "post",
            model_name
        ],
        "kwargs": {
            "data": data
        }
    }
    r=requests.post(f'{GRYD_BASE_URL}/gryd/api/db/post_api_functions',
                headers=GRYD_HEADERS,
                json=payload)
    
    r=r.json()
    try:
        data = r.get("data")

        if not data:
            # logger.info("TEST post_data --- [] (empty result)")
            return None 

        # logger.info(f"TEST post_data --- {data}")
        return data[0]

    except Exception as e:
        return {"error": "Invalid JSON response", "text": str(r)}    
    
# ######################## Common Helper ######################################
def reload_model_ref(model_name,enteprise_id):
        logger.info(f"Getting Model Connection for model_name: {model_name} and enteprise_id : {enteprise_id}")
        for model_conn_retry in range(MAX_MODEL_CONN_RETRY):
            try:
                return gryd.load_gryd_model(model_name,enteprise_id)
            except Exception as e:
                hp.print_error()
                logger.error(f"Unable to load model retrying for {model_conn_retry+1}")
                time.sleep(20)
        logger.info(f"Max Retry of {MAX_MODEL_CONN_RETRY} done..Unable to load the model...")
        raise ConnectionError("Unable to connect the model")

def is_within_last_minute(ts: str, fmt: str = "%Y-%m-%dT%H:%M:%S") -> bool:
    """
    Check if the given timestamp string is within the last 60 seconds.
    
    Args:
        ts (str): Timestamp string (e.g., "2025-09-07T10:35:21")
        fmt (str): Format of the timestamp string
    
    Returns:
        bool: True if within last 60 seconds, else False
    """
    try:
        given_time = datetime.strptime(ts, fmt)
    except ValueError:
        return False

    now = datetime.utcnow()
    return (now - given_time) <= timedelta(seconds=60)


def _wait_for_next_minute(last_minute_ts: str):
    """Sleep until the next minute boundary based on last_minute_ts."""
    last_dt = datetime.fromisoformat(last_minute_ts)
    next_window = last_dt + timedelta(minutes=1)
    now = datetime.utcnow()
    wait_seconds = (next_window - now).total_seconds()
    if wait_seconds > 0:
        logger.info(f"Rate limit reached. Sleeping for {int(wait_seconds)} seconds...")
        time.sleep(wait_seconds + 1)  # +1 sec buffer

def yield_gryd_task_results(*args, **kwargs):
    task,service_name=args[0],args[1]
    jobs = [
        {
            "task": task,
            "service": service_name,
            "kwargs": kwargs,
            "args": (None)
        }
    ]
    logger.info(f"Jobs: {json.dumps(jobs, indent = 4, default = str)} \n")
    for job in gryd.yield_results(jobs):
        task_name, status, result_data = job[1], job[3], job[4]
        logger.info(f"Task '{task_name}' status: {status} \n")
        if job[3] == "result":
            logger.info(f"Task '{task_name}' yielded result: {json.dumps(result_data, indent = 4, default = str)} \n")
            return result_data.get("result")
        logger.info("No got any response yet wating....")

# ✅ Universal execution time logger with warning support
def timelogger(label: Optional[str] = None, warn_threshold: float = 10.0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            instance = args[0] if args else None
            class_name = type(instance).__name__ if hasattr(instance, "__class__") and not isinstance(instance, type) else ""
            func_label = label or func.__name__
            full_label = f"{class_name}.{func_label}" if class_name else func_label

            start_time = time.time()
            logger.info(f"[⏱️ START] {full_label} at {datetime.now().isoformat()}")

            try:
                result = func(*args, **kwargs)
                logger.debug(f"[🔁 RETURN] {full_label} => {result}")
                return result
            except Exception as e:
                logger.error("Arguments passed to function:")
                logger.error(f"args: {pprint.pformat(args)}")
                logger.error(f"kwargs: {pprint.pformat(kwargs)}")
                hp.print_error()
            finally:
                duration = round(time.time() - start_time, 3)
                if duration > warn_threshold:
                    logger.warning(f"[⚠️ SLOW] {full_label} took {duration}s (>{warn_threshold}s)")
                else:
                    logger.info(f"[✅ DONE] {full_label} completed in {duration}s")
        return wrapper
    return decorator


def datetime_to_epoch(date_str, tz="Asia/Kolkata"):
    import time
    import pytz
    from datetime import datetime
    if not date_str: return None

    # Define a comprehensive list of potential date formats
    date_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
        "%B %d, %Y %H:%M:%S",
        "%B %d, %Y %H:%M",
        "%B %d, %Y",
        "%b %d, %Y %H:%M:%S",  # Abbreviated month name
        "%b %d, %Y %H:%M",
        "%b %d, %Y",
        "%Y-%m-%dT%H:%M:%S",  # ISO 8601
        "%Y-%m-%dT%H:%M:%S.%f",  # ISO 8601 with milliseconds
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
        "%d %B %Y %H:%M:%S",
        "%d %B %Y",
        "%d %b %Y %H:%M:%S",  # Abbreviated month name
        "%d %b %Y",
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d %H:%M:%S %z",
        "%Y-%m-%d %H:%M:%S.%f",  # With milliseconds
        # Add more formats as needed
    ]

    # Try parsing the date string with the given formats
    dt = None
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            break  # Exit loop if parsing is successful
        except ValueError:
            continue  # Try the next format

    # If dt is still None, all formats failed
    if dt is None:
        raise ValueError("Date string is in an unrecognized format.")

    # Set the timezone based on the provided string
    local_tz = pytz.timezone(tz)

    # Localize the datetime object to the specified timezone
    localized_dt = local_tz.localize(dt)

    # Convert to UTC for epoch conversion
    utc_dt = localized_dt.astimezone(pytz.utc)

    # Convert to epoch time
    epoch_time = int((utc_dt - datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds())
    return epoch_time


def get_date_data(date=None,**kwargs):
    if date:
      now=datetime.strptime(date, '%Y-%m-%d')
    else:  
        now=hp.now(tz='Asia/Kolkata')
    cur_date= hp.now(tz='Asia/Kolkata').date()
    current_date={
        'now':now,
        'month_character':now.strftime("%b"),
        "today_month":now.strftime("%m"),
        "today_date":now.strftime("%d"),
        "today_year":now.strftime("%Y"),
        'date_number': now.day,
        'current_date':now.date().strftime('%Y-%m-%d'),
        'next_date':(now+hp.timedelta(days=1)).strftime('%Y-%m-%d'),
        'dd_format':now.date().strftime('%d-%m-%Y'),
        "current_time_minus_min":(now-hp.timedelta(minutes=kwargs.get("min_diff",5))).strftime('%Y-%m-%d %H:%M:00 %z'),
        "current_time_minus_1":(now-hp.timedelta(hours=1)).strftime('%Y-%m-%d %H:00:00 %z'),
        "current_time_minus_1_z":(now-hp.timedelta(hours=1)).strftime('%Y-%m-%d %H:00:00'),
        "current_time_round_of":(now).strftime('%Y-%m-%d %H:00:00 %z'),
        "current_time_round_of_z":(now).strftime('%Y-%m-%d %H:00:00'),
        'current_time':now.time(),
        'time_formatted':now.time().strftime('%p'),
        'previous_date':(now-hp.timedelta(days=1)).strftime('%Y-%m-%d'),
        'previous_date_dd_format':(now-hp.timedelta(days=1)).strftime('%d-%m-%Y'),
        "starting_date": hp.datetime(cur_date.year, cur_date.month, 1).date().strftime('%Y-%m-%d'),
        "first_half_start":datetime.combine(now, datetime.min.time()),
        "first_half_end":datetime.combine(cur_date, datetime.min.time())+ hp.timedelta(hours=14),
        "second_half_start":datetime.combine(cur_date, datetime.min.time())+ hp.timedelta(hours=14),
        "second_half_end":datetime.combine(cur_date + hp.timedelta(days=1), datetime.min.time()),
        "today":datetime.today()
        }
    current_date['new_column_name']=str("{} {}".format(current_date.get("month_character"),current_date.get("date_number")))
    current_date['current_date_epoch']=datetime_to_epoch(current_date.get("current_date"))
    today=current_date.get("today")
    current_month_start = current_date.get("today").replace(day=1)
    current_date["current_month_start"]=current_month_start.strftime("%Y-%m-%d")
    current_date["next_month_start"]= (
        today.replace(year=today.year + 1, month=1, day=1)
        if today.month == 12
        else today.replace(month=today.month + 1, day=1)
    ).strftime("%Y-%m-%d")
    # jd=hp.json.dumps
    # logger.info(jd(current_date,indent=4))
    return current_date


def format_box_log(log_dict, message=''):
    # Convert all values to strings first
    str_items = {str(k): str(v) for k, v in log_dict.items()}
    max_key_len = max(len(k) for k in str_items.keys())
    max_val_len = max(len(v) for v in str_items.values())

    border = "+" + "-" * (max_key_len + 2) + "+" + "-" * (max_val_len + 2) + "+"
    lines = [border]
    
    for key, value in str_items.items():
        line = f"| {key:<{max_key_len}} | {value:<{max_val_len}} |"
        lines.append(line)
        lines.append(border)
    
    # return "\n".join(lines)
    
    log_output = "\n" + "\n".join(lines) + "\n"
    logger.info(f"{message} \n {log_output}")



def safe_orjson_dumps(obj, pretty: bool = True, sort_keys: bool = False) -> str:
    """
    Safely serialize a Python object to JSON using orjson.
    Supports datetime, Decimal, UUID, and falls back to string for unknown types.
    
    Args:
        obj: The Python object to serialize (dict, list, etc.)
        pretty: If True, pretty-print with indentation.
        sort_keys: If True, sort keys in the output JSON.

    Returns:
        JSON string
    """
    
    def default(o):
        if isinstance(o, (datetime, Decimal, UUID)):
            return str(o)
        return str(o)  # fallback for other unsupported types

    options = 0
    if pretty:
        options |= orjson.OPT_INDENT_2
    if sort_keys:
        options |= orjson.OPT_SORT_KEYS

    try:
        return orjson.dumps(obj, default=default, option=options).decode('utf-8')
    except Exception as e:
        return f'{{"error": "Failed to serialize", "exception": "{str(e)}"}}'

def make_uuid(*ids):
    # join all ids into a single string
    s = ''.join(map(str, ids))
    # encode to bytes
    s_bytes = s.encode("utf-8")
    # base64 encode
    b64 = base64.urlsafe_b64encode(s_bytes)
    # convert back to string and replace padding
    return b64.decode("utf-8").replace('=', '_')

def truncate_values(data, max_len=50):
    """Recursively truncate long string values in dict/list"""
    if isinstance(data, dict):
        return {k: truncate_values(v, max_len) for k, v in data.items()}
    elif isinstance(data, list):
        return [truncate_values(v, max_len) for v in data]
    elif isinstance(data, str) and len(data) > max_len:
        return data[:max_len] + f"... (truncated, {len(data)} chars)"
    else:
        return data

def get_template_details(template_id):
    
    with get_pg_connector() as pg:
        template_details=pg.get("template","template_id",template_id)
        return template_details

# ####################### IMPORTANT For Whatsapp Communication ###################################
# @gryd.is_a_task(function_name="upsert_message_status")
# @timelogger()
# def upsert_message_status(
#     model_name: str = None,
#     enterprise_id: str = None,
#     message_id: str = None,
#     patch_dict: dict = None,
#     skip_check: bool = False,
#     id_attr: str = "message_id",
#     *args,
#     **kwargs
# ):
#     """
#     Insert or update a message in the specified table using CommonServiceConnector.

#     Args:
#         model_name (str): Table name (e.g., "whatsapp_message")
#         enterprise_id (str): Tenant or business ID
#         message_id (str): Unique ID for the message (optional if skipping check)
#         patch_dict (dict): Data to insert or update
#         skip_check (bool): If True, always insert without checking existence
#         id_attr (str): ID column name (default: "message_id")
#     """
#     try:
#         if not model_name or not enterprise_id or not patch_dict:
#             raise ValueError("Missing required arguments for upsert_message_status")
#         connector =  get_connector(enterprise_id, model_name, id_attr)
#         if not connector:

#             # Initialize connector
#             connector = CommonServiceConnector(
#                 enterprise_id=enterprise_id,
#                 model_name=model_name,
#                 id_attr=id_attr
#             )

#         # Skip existence check if flag is set
#         if not skip_check and message_id:
#             existing_record = connector.get_record(message_id)
#         else:
#             existing_record = None
#             message_id = patch_dict.get("message_id")
            


#         if existing_record:
#             logger.info(f"[UPSERT PATCH] {model_name} | {id_attr}={message_id}")
#         else:
#             logger.info(f"[UPSERT INSERT] {model_name} | {id_attr}={message_id}")

#         # logger.info(f"patch_dict:: {json.dumps(patch_dict,indent=4,default=str)}")

#         # Use update_record which handles upsert
#         result = connector.update_record(
#             table_name=model_name,
#             record_id=message_id,
#             data=patch_dict,
#             id_attr=id_attr
#         )

#         logger.debug(f"[UPSERT RESULT] {result}")
#         return result

#     except Exception as e:
#         logger.error(
#             f"[ERROR] upsert_message_status | model={model_name}, message_id={message_id} | {e}",
#             exc_info=True
#         )
#         return {"error": str(e)}



CountyCodeDefaultMapper={
    "rml":"+91",
    "default":"91"
}

class AuthManager:
    def __init__(self, provider_name):
        self.provider_name = provider_name
        # self.auth_model = "whatsapp_auth_cred" #change it
        self.auth_model = "communication_credential" #change it
        

    def format_number(self, number: str, country_code: str = "91", add_plus: str = None):
        number = str(number)
        if len(number) <= 10:
            number = country_code + number
        if len(number) == 12 and add_plus:
            number = "+" + number
        return number

  
    def get_headers(self, channel_number: str, enterprise_id: str, complete_data=False) -> Dict[str, str]:
        """
        Retrieve authentication headers for a given channel number and enterprise ID.

        Logic:
        - Normalize channel number.
        - Try multiple number variants to increase hit rate.
        - Lookup order:
            1. Postgres: communication_credential.sender
            2. Fallback DB model (default_get_or_load_model)
        - Returns either auth_headers or full credential object based on `complete_data`.
        """
        logger.info("[AuthManager]::: GETTING CREDS")

        # if not enterprise_id:
        #     logger.warning("[HEADERS] Enterprise ID missing. Returning empty headers.")
        #     return {}

        start_time = time.time()

        channel_number = self.format_number(channel_number)
        logger.info(f"[HEADERS] Fetching headers for channel={channel_number}, enterprise={enterprise_id}")

        candidates = [channel_number]

        if len(channel_number) > 12:
            if channel_number.startswith("+91"):
                candidates.append(channel_number[3:])   
            elif channel_number.startswith("91"):
                candidates.append(channel_number[2:])  
        elif len(channel_number) == 10:
            candidates.append("91" + channel_number)    

        tried_numbers = set()

        for num in candidates:
            if num in tried_numbers:
                continue
            tried_numbers.add(num)

            try:
                t0 = time.time()
                
                with get_pg_connector() as pg:
                    creds = list(pg.list("communication_credential", {"sender": num}))
                    creds = creds[0]
                    if creds:
                        logger.info(
                            f"[HEADERS] Found credentials via PG for {num} and creds: {creds}"
                            f"| Time: {time.time() - t0:.3f}s"
                        )
                        return creds.get("auth_headers", {}) if not complete_data else creds

                # Fallback: DB model
                model = default_get_or_load_model(self.auth_model, enterprise_id)
                if model:
                    auth = model.get(num) or {}
                    if auth.get("auth_headers"):
                        logger.info(f"[HEADERS] Found credentials via DB model for {num}")
                        return auth.get("auth_headers", {}) if not complete_data else auth

            except Exception as e:
                logger.exception(f"[HEADERS] Error while checking number {num}: {e}")

        logger.warning(
            f"[HEADERS] No credentials found for {channel_number} "
            f"after {len(candidates)} attempts | Total time: {time.time() - start_time:.3f}s"
        )

        return {}



if __name__ == "__main__":
    # reset_rml_creds()
    
    # yield_gryd_task_results("createPerson",CONVERS_SERVICE_NAME,**{
    #         "mobile_number": "919113687241",
    #         "enterprise_id": "no_code_low_code"
    #     })
    get_all_objects("communication_credential")
    pass



