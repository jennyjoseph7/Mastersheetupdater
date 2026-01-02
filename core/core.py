from calendar import c
import sys
import os, re
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from config import AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_CORE_SERVICE_NAME, \
    gryd, gryd_routes, hp, \
    GRYD_FILE_USER_ID, \
    GRYD_FILE_API_KEY, \
    GRYD_FILE_SERVER_URL, \
    MAX_AUDIENCE_ERRORS, \
    DEFAULT_OTP, \
    ALLOWED_COUNTRY_CODES, \
    OTP_TEMPLATE_ID, \
    AutocrmModel
from autocrm_db_helper import get_pg_connector
from typing import List, Union, Dict, Any
import csv
import requests
import tempfile
from communication.connectors.whatsapp_connectors.source_connectors import BaseWebhookConverter
from communication.connectors.whatsapp_connectors.airtel_connector import *
import autocrm_validator

from razorpay_service import create_credit_purchase, confirm_payment_success, mark_payment_failed, mark_payment_cancelled

gryd.SERVICE = AUTOCRM_CORE_SERVICE_NAME
gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(gryd.SERVICE)

MIME_TYPES = {
    'aac': 'audio/aac',
    'flac': 'audio/flac',
    'wma': 'audio/x-ms-wma',
    'mpa': 'audio/mpeg',
    'aiff': 'audio/x-aiff',
    'xm': 'audio/xm',
    'm4a': 'audio/mp4',
    'pls': 'audio/x-scpls',
    'ape': 'audio/ape',  'wav': 'audio/wav',
    'au': 'audio/basic',
    'mp3': 'audio/mpeg',
    'avif': 'image/avif',
    'ps': 'application/postscript',
    'bmp': 'image/bmp',
    'jpeg': 'image/jpeg',
    'webp': 'image/webp',
    'tif': 'image/tiff',
    'jpg': 'image/jpeg',
    'tiff': 'image/tiff',
    'png': 'image/png',
    'svg': 'image/svg+xml',
    'gif': 'image/gif',
    'heif': 'image/heif',
    'webm': 'video/webm',
    'm4p': 'video/mp4',
    'mpeg': 'video/mpeg',
    'mov': 'video/quicktime',
    'gifv': 'video/gifv', 'mkv': 'video/x-matroska',
    'mp4': 'video/mp4',
    'flv': 'video/x-flv',
    'avi': 'video/x-msvideo',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'pdf': 'application/pdf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'log': 'text/plain',
    'csv': 'text/csv',
    'xls': 'application/vnd.ms-excel',
    'wpd': 'application/wordperfect',
    'ods': 'application/vnd.oasis.opendocument.spreadsheet',
    'ico': 'image/vnd.microsoft.icon',
    'md': 'text/markdown',
    'ppt': 'application/vnd.ms-powerpoint',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'txt': 'text/plain',
    'wps': 'application/vnd.ms-works',
    'msg': 'application/vnd.ms-outlook',
    'json': 'application/json',
    'yaml': 'application/x-yaml',
    'yml': 'application/x-yaml',
    'csv': 'text/csv',
}

def func_gryd_file_system(local_path, logger = None, **kwargs):
    """
    Uploads a file to the Gryd File System.
    Args:
        local_path: The path to the local file to upload.
        logger: The logger to use.
        **kwargs: Additional keyword arguments.
    Returns:
        The URL of the uploaded file.
    """
    logger = logger or mlogger
    logger.info(f"Uploading file to Gryd File System: {local_path}")
    url = f"{GRYD_FILE_SERVER_URL}/media/{kwargs.get('media_type','document')}"

    ext = os.path.splitext(local_path)[1].replace('.','').lower()
    content_type = MIME_TYPES[ext]

    logger.info(f'Local Path: {local_path}')
    logger.info(f'Content Type: {content_type}')

    headers = {
        'X-I2CE-ENTERPRISE-ID': 'gryd_file_system',
        'X-I2CE-USER-ID': GRYD_FILE_USER_ID,
        'X-I2CE-API-KEY': GRYD_FILE_API_KEY
    }
    with open(local_path, 'rb') as f:
        files = [('file',(os.path.basename(local_path), f, content_type))]
        response = requests.request("POST", url, headers=headers, files=files)
        logger.info(f'Gryd File System Response: {response.text}')
        if response.status_code == 200:
            resp_json = response.json()
            return resp_json.get('cdn_url')
    return None



def wind_up(*files):
    for file in files:
        if file and os.path.exists(file):
            os.remove(file)
    return


def get_vehicle_id(vehicle_model, row, missing_reason = None, logger = None):
    logger = logger or mlogger
    logger.info(f"Getting vehicle ID for row: {row}")
    missing_reason = missing_reason or []
    data = {}
    for k in [ 
            "emi_due_date",
            "oil_change_date",
            "tyre_change_date",
            "original_delivery_date",
            "brake_pad_change_date",
            "suspension_check_date",
            "coolant_radiator_service_date",
            "car_wash_date",
            "brake_oil_change_date",
            "oil_filter_replacement_date",
            "polishing_and_waxing_date",
            "ac_vent_cleaning_date",
            "ac_vent_cleaning_date",
            "underbody_coating_date",
            "odometer_reading_date",
            "last_service_date",
            "warranty_expiry_date",
            "extended_warranty_expiry_date",
            "battery_warranty_expiry_date",
            "battery_change_date",
            "battery_service_date",
            "insurance_expiry_date",
            "purchase_date",
            "registration_date",
            "original_delivery_date",
        ]:
        if is_valid_value(row, k):
            try:
                data[k] = hp.to_epoch(row.get(k))
                row[k] = data[k]
            except Exception as e:
                missing_reason.append(f"Failed to convert {k} to date-time: {str(e)}")
    vehicles = vehicle_model.list(_as_option=True, _page_size=1, reg_number=row.get('reg_number'))
    if vehicles:
        vehicle_id = vehicles[0].get('vehicle_id')
        row['vehicle_id'] = vehicle_id
        return row, missing_reason
    for k in [
            "reg_number",
            "vehicle_brand_name",
            "vehicle_model_name",
            "vehicle_model_year",
            "variant_name",
            "vehicle_color_name",
            "vehicle_category",
            "vehicle_type",
            "transmission",
            "engine_type",
            "engine_capacity_cc",
            "drivetrain",
            "vin_number",
            "engine_number",
            "chassis_number",
            "accessories",
            "registration_date",
            "vehicle_age_months",
            "last_service_type",
            "service_history",
            "service_advisor",
            "service_plan_type",
            "service_plan_expiry_date",
            "next_service_due",
            "service_feedback",
            "feedback_rating",
            "feedback_sentiment_score",
            "extended_warranty_purchased",
            "avg_service_cost",
            "service_frequency",
            "loan_end_date",
            "odometer_reading",
            "avg_monthly_mileage",
            "vehicle_usage_category",
            "battery_health",
            "tyre_change_details",
            "tyre_health",
            "wheel_alignment",
            "repair_notes",
            "first_owner_name",
            "ownership_status",
            "finance_loan_status",
            "loan_provider",
            "loan_account_number",
            "loan_amount",
            "emi_amount",
            "insurance",
            "puc"
        ]:
        if is_valid_value(row, k):
            data[k] = row.get(k)
    if is_valid_value(row, 'customer_score'):
        row['customer_score'] = int(row['customer_score'])
        data['customer_score'] = row['customer_score']
    if not data:
        missing_reason.append("No vehicle data found")
        return row, missing_reason
    try:
        vehicle = vehicle_model.post(data)
    except Exception as e:
        missing_reason.append(f"Failed to find suitable vehicle: {str(e)}")
    else:
        row['vehicle_id'] = vehicle.get('vehicle_id')
    return row, missing_reason


def process_post_sales_lead_row(row, models, missing_reason = None, rooftop_id = None, logger = None):
    logger = logger or mlogger
    logger.info(f"Processing post-sales lead row: {row}")
    missing_reason = missing_reason or []
    ws_val = rooftop_id or get_valid_value(row, 'workshop_id')
    if not ws_val:
        if is_valid_value(row, 'workshop_name'):
            ws_val = hp.make_single(
                models['rooftop_model'].list(
                    _as_option=True, 
                    _page_size=1,
                    workshop_name=f"~{row.get('workshop_name')}"
                ),
                force = True,
                default = {}
            )
            ws_val = ws_val.get('workshop_id')
    if not ws_val:
        missing_reason.append("Workshop ID or workshop_name not found")
    row['workshop_id'] = ws_val
    if not any([get_valid_value(row, k) for k in ['next_service_due', 'warranty_expiry_date', 'insurance_expiry_date', 'extended_warranty_expiry_date']]):
        missing_reason.append("Either one of next service due date, warranty expiry date, or insurance expiry date is required")
    if is_valid_value(row, 'next_service_due'):
        try:
            row['service_due_timestamp'] = hp.to_epoch(row.get('next_service_due'))
        except Exception as e:
            missing_reason.append(f"Failed to convert next service due date to epoch: {str(e)}")
    row, missing_reason = get_vehicle_id(models['vehicle_model'], row, missing_reason, logger = logger)
    row, missing_reason = get_persons_involved(row, models, missing_reason, logger = logger)
    return row, missing_reason


def process_pre_sales_lead_row(row, models, missing_reason = None, rooftop_id = None, logger = None):
    logger = logger or mlogger
    logger.info(f"Processing pre-sales lead row: {row}")
    missing_reason = missing_reason or []
    data = row
    for k in [
        "phone_number",
        "email",
        "name",
        "last_contacted_whatsapp_number",
        "last_contacted_email",
        "last_contacted_phone_number"
    ]:
        if is_valid_value(row, k):
            data[k] = row.get(k)
        else:
            data[k] = None

    lead = models['lead_model'].post(data)
    return lead, ""

def process_dealership_lead_row(row, models, missing_reason = None, rooftop_id = None, logger = None):
    logger = logger or mlogger
    logger.info(f"Processing dealership lead row: {row}")
    missing_reason = missing_reason or []
    data = row
    for k in [
        "dealership_id",
        "dealer_name",
        "supported_brands",
        "region_id",
        "region_name"
    ]:
        if is_valid_value(row, k):
            data[k] = row.get(k)
    dealership = models['lead_model'].post(data)
    return dealership.get('dealership_id')

def get_unique_persons_involved(persons_involved):
    person_ids = list(set([p.get('user_id') for p in persons_involved]))
    r = []
    while person_ids:
        person_id  = person_ids.pop(0)
        for person in persons_involved:
            if person.get('user_id') == person_id:
                r.append(person)
                break
    return r

def get_persons_involved(row, models, missing_reason = None, logger = None):
    logger = logger or mlogger
    logger.info(f"Getting persons involved for row: {row}")
    missing_reason = missing_reason or []
    person_model = models['person_model']
    person_vehicle_model = models['person_vehicle_model']
    phone = get_valid_value(row, 'phone_number') or get_valid_value(row, 'mobile')
    email = get_valid_value(row, 'email')
    if not phone and not email:
        missing_reason.append("Missing phone_number and email, required one of them")
    persons_involved = []
    for k in ["phone_number", "alt_phone_number_2", "alt_phone_number_3", "alt_phone_number_4"]:
        phone = get_valid_value(row, k)
        if phone:
            for l in ["phone_number", "alt_phone_number_2", "alt_phone_number_3", "alt_phone_number_4"]:
                persons = person_model.list(_as_option=True, _page_size=1, **{l: f"{phone}^"})
                if persons:
                    persons_involved.extend(persons)
    for k in ["email", "alt_email_2", "alt_email_3", "alt_email_4"]:
        email = get_valid_value(row, k)
        if email:
            for l in ["email", "alt_email_2", "alt_email_3", "alt_email_4"]:
                persons = models['person_model'].list(_as_option=True, _page_size=1, **{l: f"{email}^"})
                if persons:
                    persons_involved.extend(persons)
    if persons_involved:
        persons_involved = get_unique_persons_involved(persons_involved)
    vehicle_id = get_valid_value(row, 'vehicle_id')
    if persons_involved and vehicle_id:
        for person in persons_involved:
            person_vehicles = person_vehicle_model.list(_as_option=True, _page_size=50, user_id=person.get('user_id'), vehicle_id=vehicle_id)
            if not person_vehicles:
                person_vehicle = person_vehicle_model.post({
                    'user_id': person.get('user_id'),
                    'vehicle_id': vehicle_id,
                    'relationship_type': 'owner',
                })
    if not persons_involved:
        data = {}
        for k in person_model._model_ref.attr_seq:
            if is_valid_value(row, k):
                data[k] = row.get(k)
            try:
                person = person_model.post(data)
                if vehicle_id:
                    person_vehicle = person_vehicle_model.post({
                        'user_id': person.get('user_id'),
                        'vehicle_id': vehicle_id
                    })
            except Exception as e:
                missing_reason.append(f"Failed to post person: {str(e)}")
            else:
                persons_involved.append(person)
    return row, missing_reason


def is_valid_value(row, key):
    value = row.get(key)
    return value and isinstance(value, str) and value.strip().lower() not in ('', '-', 'n/a', 'na', 'nan', 'none', 'null')

def get_valid_value(row, key):
    value = row.get(key)
    if not is_valid_value(row, key):
        return None
    return value

def process_common_row(campaign_type, row, models, missing_reason = None, dealership_id = None, campaign_id = None, campaign_objective_id = None, audience_name = None, rooftop_type = None, rooftop_id = None, logger = None):
    logger = logger or mlogger
    logger.info(f"Processing common row: {row}")
    missing_reason = missing_reason or []
    row['dealership_id'] = dealership_id
    row['campaign_id'] = campaign_id
    row['campaign_objective_id'] = campaign_objective_id
    row['campaign_type'] = campaign_type
    row['audience_name'] = audience_name
    row[f"{rooftop_type}_id"] = rooftop_id if rooftop_type else None
    logger.info(f"Processing common row after adding common columns: {row}")
    if is_valid_value(row, 'customer_score'):
        row['customer_score'] = int(row['customer_score'])
    if campaign_type == 'pre-sales':
        row, missing_reason = process_pre_sales_lead_row(row, models, missing_reason, rooftop_id, logger = logger)
    elif campaign_type == 'post-sales':
        row, missing_reason = process_post_sales_lead_row(row, models, missing_reason, rooftop_id, logger = logger)
        logger.info(f"Post-sales lead processed: {row}")
    elif campaign_type == 'dealership':
        row, missing_reason = process_dealership_lead_row(row, models, missing_reason, rooftop_id, logger = logger)
    else:
        raise ValueError(f"Invalid campaign type: {campaign_type}")
    return row, missing_reason

def process_headers(headers, mapping, workshop_id, campaign_type, logger = None):
    logger = logger or mlogger
    logger.info(f"Processing headers: {headers}")
    if not headers:
        raise ValueError("CSV file has no headers")
    headers = [mapping.get(h, h).lower().strip().replace(' ', '_').replace('-', '_') for h in headers]
    required_contact = ["phone_number", "email"]
    has_contact = any(h in headers for h in required_contact)
    if not has_contact:
        raise ValueError(f"CSV missing at least one required contact field: {required_contact}")
    if not "workshop_id" in headers and not workshop_id and not "workshop_name" in headers:
        raise ValueError("Either workshop_id or workshop_name must be present as a column or argument")
    if campaign_type == 'post-sales':
        if "reg_number" not in headers:
            raise ValueError("CSV is missing 'reg_number' which is required for post-sales campaign.")
    return headers

def load_models(campaign_type, logger = None):
    logger = logger or mlogger
    logger.info(f"Loading models for campaign type: {campaign_type}")
    model_info = {
        'pre-sales': {
            'lead_model': 'pre_sales_lead',
            'person_model': 'person',
            'campaign_model': 'pre_sales_campaign',
            'rooftop_model': 'showroom',
        },
        'post-sales': {
            'lead_model': 'post_sales_lead',
            'vehicle_model': 'vehicle',
            'person_model': 'person',
            'person_vehicle_model': 'person_vehicle',
            'campaign_model': 'post_sales_campaign',
            'rooftop_model': 'workshop',
        },
        'dealership': {
            'lead_model': 'dealership_lead',
            'campaign_model': 'dealership_campaign',
            'rooftop_model': 'dealership',
        }
    }
    if campaign_type not in model_info:
        raise ValueError(f"Invalid campaign type: {campaign_type}")
    models = {}
    for k, v in model_info[campaign_type].items():
        models[k] = gryd.base_model.Model(v, AUTOCRM_APP_ENTERPRISE_ID)
    return models

def create_csv_path(csv_file_link, logger = None):
    logger = logger or mlogger
    csv_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            csv_path = hp.download_or_copy(csv_file_link, path = temp_file.name, raise_error_downloading=True, force = True, force_copy = True)
    except Exception as e:
        wind_up(csv_path)
        raise Exception(f"Failed to create temporary file: {str(e)}")
    return csv_path

def create_temporary_files(csv_file_link, logger = None):
    logger = logger or mlogger
    logger.info(f"Creating temporary files for CSV file: {csv_file_link}")
    csv_path = create_csv_path(csv_file_link, logger = logger)
    error_csv_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            error_csv_path = temp_file.name
    except Exception as e:
        wind_up(csv_path, error_csv_path)
        raise Exception(f"Failed to create error CSV file: {str(e)}")
    return csv_path, error_csv_path

def validate_campaign_or_campaign_objective_id(campaign_id, audience_name, campaign_objective_id, models, campaign_type, logger = None):
    logger = logger or mlogger
    logger.info(f"Validating campaign or campaign objective ID or audience_name: {campaign_id}, {campaign_objective_id}, {audience_name}")
    if campaign_id:
        found = models['campaign_model'].get(campaign_id)
        if not found:
            raise ValueError(f"Campaign ID '{campaign_id}' not found in {models['campaign_model']}")
        return found
    elif campaign_objective_id and audience_name:
        found = gryd.base_model.Model('campaign_objective', AUTOCRM_APP_ENTERPRISE_ID).get(campaign_objective_id)
        if not found:
            raise ValueError(f"Campaign objective ID '{campaign_objective_id}' not found in {models['campaign_model']}")
        if found.get('campaign_type') != campaign_type:
            raise ValueError(f"Campaign objective provided {campaign_objective_id} is not aligned with the campaign_type")
        return found
    else:
        raise ValueError("Campaign ID or campaign objective ID  and audience_name is required")
    return found


@gryd.is_a_task(function_name="extract_csv_headers", job_param='job', logger_param='logger')
def extract_csv_headers(csv_file_link, job = None, logger = None):
    csv_path = create_csv_path(csv_file_link, logger = logger)
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        logger.info(f"Headers: {headers}")
        return headers


@gryd.is_a_task(function_name="reset_password", job_param='job', logger_param='logger', auth_param='auth')
def reset_password(phone_number_or_email:str, channel:str, new_password:str, confirm_password:str, token:str, otp:str, logger = None, job = None, auth = None):
    logger = logger or mlogger
    logger.info(f"Resetting password for {channel}: {phone_number_or_email}")
    if channel not in ['whatsapp', 'email']:
        raise ValueError(f"Invalid channel: {channel}. Allowed channels are: whatsapp, email")
    kwargs = {}
    if channel in ['whatsapp', 'phone_number']:
        channel = 'whatsapp'
        kwargs['phone_number'] = phone_number_or_email
    elif channel == 'email':
        kwargs['email'] = phone_number_or_email
    verify_otp(token, otp, channel = channel, identifier = phone_number_or_email, response_prefix = f'{channel} ', logger = logger, job = job, auth = auth)
    verify_password_compliance(new_password, confirm_password, logger = logger, job = job, auth = auth)
    human_agent_model = gryd.base_model.Model('human_agent', AUTOCRM_APP_ENTERPRISE_ID)
    existing_human_agent = human_agent_model.list(_as_option=True, _page_size=1, **kwargs)
    if not existing_human_agent:
        raise ValueError(f"No user found for {channel}: {phone_number_or_email}")
    existing_human_agent = hp.make_single(existing_human_agent)
    human_agent_id = existing_human_agent.get('human_agent_id')
    human_agent_model.update(human_agent_id, {
        'password': new_password,
        'password_expiry': hp.epoch() + 2592000 # 30 days
    })
    return f"Password reset successfully for {channel}: {phone_number_or_email}"

@gryd.is_a_task(function_name="generate_otp", job_param='job', logger_param='logger')
def generate_otp(phone_number_or_email:str, channel:str = 'whatsapp', region_id: str = None, signup = True, logger = None, job = None, auth = None):
    f"""
    Unified gryd task to generate OTP for a phone number or email
    Args:
        phone_number_or_email: phone number or email to generate OTP for
        channel: channel to generate OTP for
        region_id: region id to generate OTP for
        signup: If True, the OTP is generated for signup, else for password reset
    Returns:
        token: token of the OTP cache
    Errors:
        ValueError: If the channel is invalid
        ValueError: If the region_id is invalid
        ValueError: If the phone number is invalid or already exists, in case of signup
        ValueError: If the email is invalid or already exists, in case of signup
    """
    logger = logger or mlogger
    if channel not in ['whatsapp', 'email']:
        raise ValueError(f"Invalid channel: {channel}. Allowed channels are: whatsapp, email")
    logger.info(f"Generating OTP for {channel}: {phone_number_or_email}")
    region_codes = ALLOWED_COUNTRY_CODES or ['+91']
    if region_id:
        region = gryd.base_model.Model('region', AUTOCRM_APP_ENTERPRISE_ID).get(region_id)
        if not region:
            raise ValueError(f"Invalid region_id: {region_id}")
        region_codes = hp.make_list(region.get('country_phone_code', ['+91']))
    human_agent_model = gryd.base_model.Model('human_agent', AUTOCRM_APP_ENTERPRISE_ID)
    otp = hp.id_generator(6, chars = "0123456789")
    logger.info(f"OTP for {channel} {phone_number_or_email} : {otp}")
    expiry = hp.epoch() + 10 * 60 # 10 minutes
    if channel == 'whatsapp':
        phone_number = verify_phone_number(phone_number_or_email, region_codes = region_codes, human_agent_model = human_agent_model, signup = signup, logger = logger, job = job)
        BaseWebhookConverter().send_otp_template(**{"template_id":OTP_TEMPLATE_ID,"mobile_number":phone_number,"otp":otp})
    elif channel == 'email':
        email = verify_email(phone_number_or_email, human_agent_model = human_agent_model, signup = signup, logger = logger, job = job)
        # TODO: Send email OTP
    with get_pg_connector() as db:
        otp_cache_id = str(hp.make_uuid3(otp, expiry))
        db.update('otp_cache', 'otp_cache_id', otp_cache_id, {
            'otp': otp,
            'expiry': expiry,
            'max_attempts': 3,
            'remaining_attempts': 3,
            'last_attempt_time': hp.epoch(),
            'otp_cache_id': otp_cache_id,
            "channel": channel,
            "identifier": phone_number_or_email
        })
        return {'token': otp_cache_id}

@gryd.is_a_task(function_name="verify_otp", job_param='job', logger_param='logger')
def verify_otp(token:str, otp:str, channel:str, identifier:str, response_prefix: str = '', logger = None, job = None, auth = None):
    """
    Unified gryd task to verify OTP for a token and otp
    Args:
        token: token to verify OTP for
        otp: OTP to verify
    Returns:
        response: response from the task
    Errors:
        AuthError: If the token is invalid
        AuthError: If the OTP is invalid
        AuthError: If the OTP is expired
        AuthError: If the OTP is max attempts reached
    Example API:
    POST /gryd/task/autocrm-core/verify_otp
    Payload:
    {
        "args": [
            "1234567890",
            "123456"
        ],
        "kwargs": {
            "response_prefix": "Phone Number"
        }
    }
    Response:
    {
        "response": "OTP verified"
    }
    """
    logger = logger or mlogger
    logger.info(f"Verifying OTP for otp_cache_id: {token}, otp: {otp}")
    nct = hp.epoch()
    if DEFAULT_OTP and otp == DEFAULT_OTP:
        with get_pg_connector() as db:
            db.delete('otp_cache', 'otp_cache_id', token)
        return f"Default {response_prefix}OTP verified"
    with get_pg_connector() as db:
        otp_cache = db.get('otp_cache', 'otp_cache_id', token)
        if not otp_cache:
            raise gryd_routes.AuthError(f"Invalid token to verify {response_prefix}OTP or {response_prefix}OTP attempts expired")
        if nct > int(otp_cache.get('expiry')):
            raise gryd_routes.AuthError(f"{response_prefix}OTP expired")
        if otp_cache.get('identifier') != identifier or otp_cache.get('channel') != channel or otp_cache.get('otp') != otp:
            if otp_cache.get('remaining_attempts') <= 0:
                raise gryd_routes.AuthError(f"{response_prefix}OTP max attempts reached")
            db.update('otp_cache', 'otp_cache_id', token, {
                'remaining_attempts': otp_cache.get('remaining_attempts') - 1,
                'last_attempt_time': hp.epoch()
            })
            raise gryd_routes.AuthError(f"Invalid {response_prefix}OTP, or identifier mismatch, remaining attempts: {otp_cache.get('remaining_attempts')}")
        db.delete('otp_cache', 'otp_cache_id', token)
        return f"{response_prefix}OTP verified"

@gryd.is_a_task(function_name="verify_email", job_param='job', logger_param='logger')
def verify_email(email:str, human_agent_model:gryd.base_model.Model = None, signup = True, logger = None, job = None):
    """
    Unified gryd task to verify email
    Args:
        email: email to verify
        human_agent_model: human agent model
        signup: signup flag
    Returns:
        email: verified email
    Errors:
        ClientError: If the email is invalid
        ClientError: If the email is already in use and signup is True
    Example API:
    POST /gryd/task/autocrm-core/verify_email
    Payload:
    {
        "args": ["test@example.com"],
        "kwargs": {
            "signup": true
        }
    }
    Response:
    {
        "email": "test@example.com"
    }
    """
    logger = logger or mlogger
    logger.info(f"Verifying email: {email}")
    email = email.lower().strip()
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise gryd_routes.ClientError(f"Invalid email: {email}")
    human_agent_model = human_agent_model or gryd.base_model.Model('human_agent', AUTOCRM_APP_ENTERPRISE_ID)
    existing_human_agent = human_agent_model.list(_as_option=True, _page_size=1, email=email)
    if existing_human_agent:
        if signup:
            raise gryd_routes.ClientError(f"Dealersip Admin with email {email} already exists")
        else:
            return hp.make_single(existing_human_agent).get('email')
    return email

@gryd.is_a_task(function_name="verify_phone_number", job_param='job', logger_param='logger')
def verify_phone_number(phone_number:str, region_codes:list[str] = None, human_agent_model:gryd.base_model.Model = None, signup = True, logger = None, job = None, auth = None):
    logger = logger or mlogger
    logger.info(f"Verifying phone number: {phone_number}")
    region_codes = hp.make_list(region_codes or ALLOWED_COUNTRY_CODES or ['+91'])
    phone_number = phone_number.lower().strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    if not any(phone_number.startswith(p) for p in region_codes):
        raise gryd_routes.ClientError(f"Unsupported country code: {phone_number}, allowed country codes: {region_codes}")
    if not re.match(r'^\+?[1-9]\d{9,14}$', phone_number):
        raise gryd_routes.ClientError(f"Invalid phone number: {phone_number}")
    human_agent_model = human_agent_model or gryd.base_model.Model('human_agent', AUTOCRM_APP_ENTERPRISE_ID)
    existing_human_agent = human_agent_model.list(_as_option=True, _page_size=1, phone_number=phone_number)
    if existing_human_agent:
        if signup:
            raise gryd_routes.ClientError(f"Dealersip Admin with phone number {phone_number} already exists")
        else:
            return hp.make_single(existing_human_agent).get('phone_number')
    return phone_number

@gryd.is_a_task(function_name="verify_password_compliance", job_param='job', logger_param='logger')
def verify_password_compliance(password:str, confirm_password:str, logger = None, job = None, auth = None):
    logger = logger or mlogger
    logger.info(f"Verifying password compliance for password: {password}, confirm_password: {confirm_password}")
    if not password == confirm_password:
        raise gryd_routes.ClientError("Password and confirm password do not match")
    if len(password) < 8:
        raise gryd_routes.ClientError("Password must be at least 8 characters long")
    if not any(char.isdigit() for char in password):
        raise gryd_routes.ClientError("Password must contain at least one digit")
    if not any(char.isalpha() for char in password):
        raise gryd_routes.ClientError("Password must contain at least one letter")
    if not any(char.isupper() for char in password):
        raise gryd_routes.ClientError("Password must contain at least one uppercase letter")
    if not any(char.islower() for char in password):
        raise gryd_routes.ClientError("Password must contain at least one lowercase letter")
    return "Password complies with the requirements"

@gryd.is_a_task(function_name="dealership_signup", job_param='job', auth_param='auth', logger_param='logger')
def dealership_signup(
    dealer_name:str, 
    region_id:str, 
    primary_contact_name:str, 
    primary_contact_email:str, 
    primary_contact_phone:str, 
    password:str,
    confirm_password:str,
    email_otp:str,
    phone_number_otp:str,
    email_otp_token:str,
    phone_number_otp_token:str,
    vehicle_category:str = 'Passenger Vehicle', 
    dealership_type:str = 'Single Brand', 
    languages:list[str] = ['english'], 
    supported_brands:list[str] = [], 
    aliases = None, pan_number = None, gstin = None, website = None, job = None, logger = None, auth = None, **kwargs):
    """
    Unified gryd task to sign up a dealership
    Args:
        dealer_name: name of the dealership
        region_id: id of the region
        primary_contact_name: name of the primary contact
        primary_contact_email: email of the primary contact
        primary_contact_phone: phone number of the primary contact
        password: password for the dealership
        confirm_password: confirm password for the dealership
        email_otp: email OTP for the dealership
        phone_number_otp: phone number OTP for the dealership
        email_otp_token: email OTP token for the dealership
        phone_number_otp_token: phone number OTP token for the dealership
    Kwargs:
        vehicle_category: category of the vehicle
        dealership_type: type of the dealership
        languages: languages supported by the dealership
        supported_brands: brands supported by the dealership
        aliases: aliases of the dealership, list of strings
        pan_number: PAN number of the dealership, string
        gstin: GSTIN of the dealership, string
        website: website of the dealership, string
        kwargs: other kwargs to pass to the dealership model, dict
    Returns:
        dealership: dealership object, which includes the dealership details and login_token

    Example:
        dealership_signup(
            dealer_name = "Ambal Auto",
            region_id = "south-india",
            primary_contact_name = "Ambal Auto",
            primary_contact_email = "ambalauto@gmail.com",
            primary_contact_phone = "+91-9876543201",
            password = "MyWellMadePass@123",
            confirm_password = "MyWellMadePass@123",
            email_otp = "123456",
            phone_number_otp = "123456",
            email_otp_token = "token received while sending email OTP",
            phone_number_otp_token = "token received while sending phone number OTP",
            vehicle_category = "car",
            dealership_type = "Single Brand",
            supported_brands = ["maruti-suzuki-nexa", "maruti-suzuki-arena"],
            languages = ["english", "hindi"],
        )
    Throws Error:
        ValueError: If the dealership already exists
        ValueError: If region_id is not valid
        ValueError: If primary contact name is not valid or already in use
        ValueError: If primary contact email is not valid or already in use
        ValueError: If primary contact phone is not valid or already in use
        ValueError: If password and confirm password do not match
        ValueError: If password does not comply with the requirements
        ValueError: If email OTP or phone number OTP are incorrect

    Example:
        dealership_signup(
            dealer_name = "Ambal Auto",
            region_id = "south-india",
            vehicle_category = "car",
            dealership_type = "Multi Brand",
            languages = ["english", "hindi"],
            supported_brands = ["maruti-suzuki-nexa", "maruti-suzuki-arena", "hyundai"],
            primary_contact_name = "Ambal Auto",
            primary_contact_email = "ambalauto@gmail.com",
            primary_contact_phone = "+91-9876543201",
            aliases = ["Ambal Auto", "Ambal Auto - Service Center"],
            pan_number = "ABCD1234567890",
            gstin = "ABCD1234567890",
            website = "https://ambalauto.com",
        )
    # Example input JSON format for dealership_signup:
    # {
    #   "args": [
    #     "Ambal Auto",
    #     "south-india",
    #     "car",
    #     "Multi Brand",
    #     ["english", "hindi"],
    #     ["maruti-suzuki-nexa", "maruti-suzuki-arena", "hyundai"],
    #     "Ambal Auto",
    #     "ambalauto@gmail.com",
    #     "+91-9876543201"
    #   ],
    #   "kwargs": {
    #     "aliases": ["Ambal Auto", "Ambal Auto - Service Center"],
    #     "pan_number": "ABCD1234567890",
    #     "gstin": "ABCD1234567890",
    #     "website": "https://ambalauto.com"
    #   }
    # }
    Returns:
        dealership: dealership object, which includes the dealership details and login_token
    """
    logger = logger or mlogger
    logger.info(f"Dealer signing up for dealership: {dealer_name}, {region_id}, {vehicle_category}, {dealership_type}")
    dealership_model = gryd.base_model.Model('dealership', AUTOCRM_APP_ENTERPRISE_ID)
    previous_dealership = dealership_model.list(_as_option=True, _page_size=1, dealer_name=f"~{dealer_name}", region_id=region_id, vehicle_category=vehicle_category)
    if previous_dealership:
        previous_dealership_names = ', '.join(list(map(lambda x: x.get('dealer_name'), previous_dealership))) 
        raise ValueError(f"Dealer with name similar to {dealer_name} ({previous_dealership_names}), region {region_id}, vehicle category {vehicle_category} already exists.")
    region_model = gryd.base_model.Model('region', AUTOCRM_APP_ENTERPRISE_ID)
    region = region_model.get(region_id)
    if not region:
        raise ValueError(f"Region {region_id} not found")
    verify_password_compliance(password, confirm_password)
    verify_otp(email_otp_token, email_otp, channel = 'email', identifier = primary_contact_email, response_prefix = 'Email ')
    verify_otp(phone_number_otp_token, phone_number_otp, channel = 'whatsapp', identifier = primary_contact_phone, response_prefix = 'Phone number ')
    kwargs.update({
        'dealer_name': dealer_name,
        'region_id': region_id,
        'vehicle_category': vehicle_category,
    })
    for k in ['dealership_type', 'languages', 'supported_brands', 'aliases', 'pan_number', 'gstin', 'website']:
        if kwargs.get(k):
            kwargs[k] = kwargs.get(k)
    human_agent_model = gryd.base_model.Model('human_agent', AUTOCRM_APP_ENTERPRISE_ID)
    primary_contact_email = verify_email(primary_contact_email, human_agent_model, logger = logger, job = job)
    primary_contact_phone = verify_phone_number(primary_contact_phone, region_codes = region.get('country_phone_code'), human_agent_model = human_agent_model, logger = logger, job = job)
    kwargs['primary_contact_name'] = primary_contact_name
    kwargs['primary_contact_email'] = primary_contact_email
    kwargs['primary_contact_phone'] = primary_contact_phone
    with human_agent_model.objects._db._transaction() as db_transaction:
        dealership = dealership_model.post(kwargs)
        human_agent = human_agent_model.post({
            'dealership_id': dealership.get('dealership_id'),
            'agent_name': primary_contact_name,
            'password': password,
            'email': primary_contact_email,
            'phone_number': primary_contact_phone,
            'role': 'Dealership Admin'
        })
        logger.info(f"Human agent created: {human_agent}")
        login_token = gryd_routes.return_login_token(
            enterprise_id = AUTOCRM_APP_ENTERPRISE_ID, 
            user_id = human_agent.get('human_agent_id'), 
            role = 'human_agent',
            application_id = "autocrm",
        )
        dealership['login_token'] = login_token
    return dealership

@gryd.is_a_task(function_name="verify_website", job_param='job', logger_param='logger')
def verify_website(website:str, dealer_name:str, logger = None, job = None, auth = None):
    logger = logger or mlogger
    logger.info(f"Verifying website: {website}")
    website = website.lower().strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
    if not website.startswith('http'):
        website = 'https://' + website
    if not re.match(r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', website):
        raise gryd_routes.ClientError(f"Invalid website: {website}")
    return website
    ## TODO: Implement website verification
    #try:
    #    website_content = requests.get(website, timeout=30)
    #except requests.exceptions.ConnectTimeout as e:
    #    raise gryd_routes.ClientError(f"Website {website} is not reachable: {e}")
    #if not website_content.ok:
    #    raise gryd_routes.ClientError(f"Website {website} is not reachable")
    #website_content = website_content.text
    #if not dealer_name.lower() in website_content.lower():
    #    raise gryd_routes.ClientError(f"Website {website} does not contain dealer name Dealership: {dealer_name} in the content")
    #return website
    ##

@gryd.is_a_task(function_name="verify_pan_number", job_param='job', logger_param='logger')
def verify_pan_number(pan_number:str, logger = None, job = None, auth = None):
    logger = logger or mlogger
    logger.info(f"Verifying PAN number: {pan_number}")
    if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan_number):
        raise gryd_routes.ClientError(f"Invalid PAN number: {pan_number}")
    return pan_number

@gryd.is_a_task(function_name="verify_gstin", job_param='job', logger_param='logger')
def verify_gstin(gstin:str, logger = None, job = None, auth = None):
    logger = logger or mlogger
    logger.info(f"Verifying GSTIN: {gstin}")
    if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', gstin):
        raise gryd_routes.ClientError(f"Invalid GSTIN: {gstin}")
    return gstin

@gryd.is_a_task(function_name="dealership_update_details", job_param='job', auth_param='auth', logger_param='logger')
def dealership_update_details(
    dealership_id:str,
    supported_brands:list[str],
    dealership_type:str,
    languages:list[str] = None,
    aliases:list[str] = None,
    pan_number:str = None,
    gstin:str = None,
    website:str = None,
    vehicle_category:str = None,
    logger = None,
    job = None,
    auth = None,
    **kwargs
):
    """
    Unified gryd task to update dealership details
    Args:
        dealership_id: id of the dealership
        supported_brands: list of supported brands
        dealership_type: type of the dealership
        languages: list of languages
        pan_number: PAN number
        gstin: GSTIN
        website: website
    Kwargs:
        vehicle_category: category of the vehicle
    Errors:
        ValueError: If the vehicle category is invalid
        ValueError: If the dealership type is invalid
        ValueError: If the languages are invalid
        ValueError: If all of GSTIN, PAN number, or website are required, and invalid
        ValueError: If supported brands are required, and invalid
        ValueError: If the dealership is not found
        ValueError: If the brands are not supported in the region
        ValueError: If dealership is not found
    Returns:
        dealership: dealership object, which includes the dealership details
    Example Json:
    {
        "args": [
            "dealership_id",
            "supported_brands",
            "dealership_type",
            "languages",
            "pan_number",
            "gstin",
            "website"
        ],
        "kwargs": {
            "vehicle_category": "Passenger Vehicle"
        }
    }
    """
    logger = logger or mlogger
    logger.info(f"Updating dealership details for dealership: {dealership_id}, supported_brands: {supported_brands}, dealership_type: {dealership_type}, languages: {languages}, pan_number: {pan_number}, gstin: {gstin}, website: {website}, vehicle_category: {vehicle_category}")
    dealership_model = gryd.base_model.Model('dealership', AUTOCRM_APP_ENTERPRISE_ID)
    dealership = dealership_model.get(dealership_id)
    if not dealership:
        raise ValueError(f"Dealership with id {dealership_id} not found")
    if vehicle_category and vehicle_category not in ['Passenger Vehicle', 'Commercial Vehicle', 'Two Wheeler', 'Three Wheeler', 'Truck', 'Bus']:
        raise ValueError(f"Invalid vehicle category: {vehicle_category}")
    if dealership_type not in ['Single Brand', 'Multi Brand']:
        raise ValueError(f"Invalid dealership type: {dealership_type}")
    if any(lang not in ['english', 'hindi', 'kannada', 'telugu', 'tamil', 'malayalam', 'odia', 'bengali', 'marathi', 'gujarati', 'bengali', 'assamese', 'punjabi', 'spanish', 'arabic'] for lang in languages):
        raise ValueError(f"Invalid languages: {languages}")
    if pan_number:
        pan_number = verify_pan_number(pan_number, logger = logger, job = job, auth = auth)
    if gstin:
        gstin = verify_gstin(gstin, logger = logger, job = job, auth = auth)
    if website:
        website = verify_website(website, dealership.get('dealer_name'), logger = logger, job = job)
    if not any((pan_number, gstin, website)):
        raise ValueError("Either GSTIN, PAN number, or website is required.")
    if not supported_brands:
        raise ValueError("Supported brands are required")
    brand_model = gryd.base_model.Model('brand', AUTOCRM_APP_ENTERPRISE_ID)
    brands = list(map(lambda x: x.get('brand_id'), brand_model.list(_as_option=True, _page_size=1, brand_id=supported_brands, region_id=dealership.get('region_id'))))
    logger.info(f"Supported Brands for region {dealership.get('region_id')}: {brands}")
    if any(brand not in brands for brand in supported_brands):
        unsupported_brands = list(filter(lambda brand: brand not in brands, supported_brands))
        raise ValueError(f"Brands {unsupported_brands} not supported in region {dealership.get('region_id')}")
    kwargs.update({
        'supported_brands': supported_brands,
        'dealership_type': dealership_type,
        'languages': languages,
        'aliases': aliases,
        'pan_number': pan_number,
        'gstin': gstin,
        'website': website
    })
    dealership = dealership_model.update(dealership_id, {k: v for k, v in kwargs.items() if v is not None})
    logger.info(f"Dealership details updated: {dealership}")
    return dealership

@gryd.is_a_task(function_name="import_leads_from_csv", job_param='job', auth_param='auth', logger_param='logger')
def gryd_task_import_leads_from_csv(
    campaign_type: str,
    dealership_id: str,
    csv_file_link: str,
    job=None,
    auth=None,
    logger=None,
    *args,
    **kwargs
):
    """
    Unified gryd task to import leads from CSV for pre-sales, post-sales, or dealership campaigns
    Args:
        campaign_type: One of 'pre-sales', 'post-sales', 'dealership'
        dealership_id: id of the dealership
        csv_file_link: local path to CSV file
        kwargs:
            - audience_name
            - campaign_id
            - mapping: header mapping
            - workshop_id
            - lead_tags
            - campaign_objective_id
            - etc.
    Yields:
        - {"_error": ...} for errors
        - {"_status": ...} status after every 10 records
        - {"_result": error csv path}
    """
    logger = logger or mlogger
    campaign_type = (campaign_type or '').lower().strip().replace('_','-').replace(' ','-')
    campaign_id = kwargs.get('campaign_id')
    audience_name = kwargs.get('audience_name')
    enterprise_id = kwargs.get("enterprise_id") or AUTOCRM_APP_ENTERPRISE_ID
    mapping = kwargs.get("mapping", {})
    workshop_id = str(kwargs.get("workshop_id"))
    showroom_id = str(kwargs.get("showroom_id"))
    rooftop_type = "workshop" if workshop_id else "showroom" if showroom_id else "dealership"
    rooftop_id = workshop_id if rooftop_type == 'workshop' else showroom_id if rooftop_type == 'showroom' else dealership_id
    campaign_objective_id = kwargs.get("campaign_objective_id")
    logger.info(f"Importing leads from CSV for campaign_type: {campaign_type}, dealership_id: {dealership_id}, csv_file_link: {csv_file_link}, campaign_id: {campaign_id}, enterprise_id: {enterprise_id}, mapping: {mapping}, {rooftop_type}_id: {rooftop_id}, audience_name: {audience_name}")
    # Model selection
    models = load_models(campaign_type)
    csv_path = None
    error_csv_path = None
    try:
        csv_path, error_csv_path = create_temporary_files(csv_file_link, logger = logger)
        logger.info(f"CSV path: {csv_path}, error_csv_path: {error_csv_path}")
        # Campaign ID validation
        campaign = validate_campaign_or_campaign_objective_id(campaign_id, audience_name, campaign_objective_id, models, campaign_type, logger = logger)
        campaign_id = campaign.get('campaign_id')
        campaign_objective_id = campaign.get('campaign_objective_id')
        total = 0
        error = 0
        processed = 0
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            logger.info(f"Headers: {headers}")
            original_headers = headers
            headers = process_headers(original_headers, mapping, workshop_id, campaign_type, logger = logger)
            with open(error_csv_path, "w", newline="", encoding="utf-8") as fe:
                # Error csv
                error_csv_headers = ["line_num"] + headers + ["_error"]
                writer = csv.DictWriter(fe, fieldnames=error_csv_headers)
                writer.writeheader()
                # Main CSV processing loop
                for i, row in enumerate(reader, 2):
                    total += 1
                    missing_reason = [f"Line {i}: "]
                    row = {headers[i]: row.get(k) for i, k in enumerate(row.keys()) if is_valid_value(row, k)}
                    logger.info(f"Row: {row}")
                    row, missing_reason = process_common_row(campaign_type, row, models, missing_reason, dealership_id, campaign_id = campaign_id, campaign_objective_id = campaign_objective_id, audience_name = audience_name, rooftop_type = rooftop_type, rooftop_id = rooftop_id, logger = logger)
                    row_ctx = {
                      "line_num": i,
                      **row
                    }
                    if len(missing_reason) > 1:
                        error += 1
                        row_ctx['_error'] = ', '.join(missing_reason)
                        writer.writerow({k: row_ctx.get(k, "") for k in error_csv_headers})
                        yield {"_error": row_ctx}
                    else:
                        try:
                            # post the lead
                            logger.info(f"Posting lead: {row}")
                            models['lead_model'].post(row)
                        except Exception as e:
                            error += 1
                            logger.error(f"Failed to post lead: {str(e)}")
                            row_ctx['_error'] = f"Failed to post lead: {str(e)}"
                            writer.writerow({k: row_ctx.get(k) for k in error_csv_headers})
                            yield {"_error": row_ctx}
                        else:
                            logger.info(f"Finished posted lead row: {row}")
                            processed += 1
                    percent = int(100.0 * total / (reader.line_num or (total + error)))
                    yield {"_status": f"{percent}% completed"}
                    if error > MAX_AUDIENCE_ERRORS:
                        # too many errors, stop the task
                        logger.error(f"Too many errors, stopping the task")
                        break
            # Write error CSV
            if error > 0:
                url = func_gryd_file_system(error_csv_path, logger = logger)
                yield {"_result":  {'error_csv_url': url, 'total': total, 'error': error, 'processed': processed}}
            else:
                yield {"_result": {'total': total, 'error': error, 'processed': processed}}
    except Exception as e:
        wind_up(csv_path, error_csv_path)
        raise ValueError(f"Failed to create temporary files: {str(e)}") from e
    wind_up(csv_path, error_csv_path)
    return

@gryd.is_a_task()
def post_billing(dealership_id, transaction_type, item_name, item_description, transaction_date, item_quantity, item_price, item_unit, currency, campaign_id, channel,**kwarg):
    """
    Post a billing transaction to the database to debit credits from dealership and create billing object. 

    Parameters:
    dealership_id (str): The dealership ID. Mandatory
    transaction_type (str): The type of transaction (e.g. debit, credit).
    item_name (str): The name of the item, eg - conversation.
    item_description (str): The description of the item - "campaign type - campaign objective - campaign name - channel - provider - phone number or email".
    transaction_date (datetime): The date of the transaction timestamp.
    item_quantity (float): The quantity of the item number of credits.
    item_price (float): The price of the item per credit cost.
    item_unit (str): The unit of the item (e.g. credits).
    currency (str): The currency of the transaction - example - ["credits", "INR", "USD", "EUR", "GBP", "AED", "SAR", "JPY"].
    campaign_id (str): The campaign ID if applicable else 'inbound'.
    channel (str): The channel of the transaction (e.g. "rcs","email", "web_chat", "web_chat_voice","fb_chat","insta_chat","twitter_chat","voice_phone","whatsapp_chat","whatsapp_voice_note","whatsapp_voice_call","zoom_bot","ms_teams").
    Returns:
    None
    """
    if not dealership_id:
        raise ValueError("Post Billing called without dealership_id")

    timmm = hp.time()
    tme = transaction_date
    if not transaction_date:
        tme = hp.now(as_datetime=False)
    
    new_balance = 0
    current_balance = 0

    with get_pg_connector() as db:
        dealership = db.get("dealership","dealership_id", dealership_id)
        if not dealership:
            raise ValueError("Post Billing called without dealership_id")
        current_balance = float(dealership.get('credits_balance',0))
        deductable=item_quantity
        if transaction_type == "debit":
            deductable = -1*item_quantity
        db.iadd("dealership","dealership_id", dealership_id, "credits_balance", deductable)
    
    
    
    m = AutocrmModel("billing", logger = logger)

    if transaction_type == "credit":        
        update_data = {
            "status" : "success",
            "razorpay_order_id": kwarg.get("razorpay_order_id"),
            "razorpay_payment_id": kwarg.get("razorpay_payment_id"),
            "razorpay_signature": kwarg.get("razorpay_signature"),
            "raw_razorpay_payload": kwarg.get("raw_razorpay_payload"),       
            "credit_balance_before" : current_balance,
            "credit_balance_after" : current_balance + item_quantity,
        }

        m.update(kwarg.get("billing_id"),update_data)
        return

    new_balance = current_balance - item_quantity
    if new_balance <= 0:
        logger.info(f"Dealership {dealership_id} has no credits left")
        ##TODO maybe send email or some action here.

    postable = {
        "transaction_date" : tme,
        "transaction_type" : transaction_type,
        "item_name" : item_name,
        "item_description" : item_description,
        "item_quantity" : item_quantity, ## credits used or added
        "item_price" : item_price,
        "item_total" : item_quantity*item_price,
        "item_units" : item_unit,
        "currency" : currency,
        "dealership_id" : dealership_id,
        "status" : "success",
        "credit_balance_before" : current_balance,
        "credit_balance_after" : new_balance,
        "campaing_id" : campaign_id or "inbound",
        "channel" : channel
    }
    
    m.post(postable)

    
@gryd.is_a_task(function_name="payment_service")
def payment_service(*args, **kwargs):

    def validate_kwargs(required_fields, kwargs):
        missing = [field for field in required_fields if not kwargs.get(field)]
        if missing:
            raise ValueError(f"Missing required parameters: {', '.join(missing)}")

    if not args:
        raise ValueError("service name is required")

    service = args[0]

    if service == "purchase_credit":
        validate_kwargs(
            ["dealership_id", "credits"],
            kwargs
        )

        return create_credit_purchase(
            kwargs["dealership_id"],
            kwargs["credits"]
        )

    elif service == "verify_payment":
        validate_kwargs(["payment_data"], kwargs)

        return confirm_payment_success(kwargs["payment_data"])
    
    elif service == "payment_failed":
        validate_kwargs(["order_id"], kwargs)

        return mark_payment_failed(kwargs["order_id"], kwargs["reason"])
    
    elif service == "payment_cancelled":
        validate_kwargs(["order_id"], kwargs)

        return mark_payment_cancelled(kwargs["order_id"])
    
    else:
        raise ValueError(f"Unsupported payment service: {service}")

if __name__ == "__main__":

    #gryd_task_import_leads_from_csv.execute("post-sales", "ambal-auto-south-india", "https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/485b7cbc-55d5-44d2-b5b9-0e6d6e405f4c-692977e5_afinallead.csv", campaign_id = "74f260b8-e8dc-3c52-ab8d-31bd0fc49943", workshop_id = 12)    
    for out in gryd_task_import_leads_from_csv(
            "post-sales", 
            "ambal-auto-south-india", 
            "/Users/ggananth/Downloads/afinallead.csv", 
            #campaign_id = "74f260b8-e8dc-3c52-ab8d-31bd0fc49943",
            audience_name = "Ambal Auto - Service Center - New data",
            campaign_objective_id = "post-sales-warranty-expiry-offer-nexa-mumbai-west-nexa-dealer-group-west-india",
            workshop_id = "ambal-auto - ambal-auto---service-center - coimbatore"
        ):    
        print(hp.json.dumps(out, hp.json.OPT_INDENT_2))
