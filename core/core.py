import sys
import os
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from config import AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_CORE_SERVICE_NAME, \
    gryd, hp, \
    GRYD_FILE_USER_ID, \
    GRYD_FILE_API_KEY, \
    GRYD_FILE_SERVER_URL
from autocrm_db_helper import get_pg_connector
from typing import List, Union, Dict, Any
import csv
import requests
import tempfile

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
    data = {}
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
    lead = models['lead_model'].post(data)
    return lead.get('lead_id')

def process_dealership_lead_row(row, models, missing_reason = None, rooftop_id = None, logger = None):
    logger = logger or mlogger
    logger.info(f"Processing dealership lead row: {row}")
    missing_reason = missing_reason or []
    data = {}
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

def process_headers(headers, mapping, workshop_id, typ, logger = None):
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
    if typ == 'post-sales':
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

def create_temporary_files(csv_file_link, logger = None):
    logger = logger or mlogger
    logger.info(f"Creating temporary files for CSV file: {csv_file_link}")
    csv_path = None
    error_csv_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            csv_path = hp.download_or_copy(csv_file_link, path = temp_file.name, raise_error_downloading=True, force = True, force_copy = True)
    except Exception as e:
        wind_up(csv_path)
        raise Exception(f"Failed to create temporary file: {str(e)}")
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
    typ = (campaign_type or '').lower().strip().replace('_','-').replace(' ','-')
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
    models = load_models(typ)
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
            headers = process_headers(original_headers, mapping, workshop_id, typ, logger = logger)
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
                    row, missing_reason = process_common_row(typ, row, models, missing_reason, dealership_id, campaign_id = campaign_id, campaign_objective_id = campaign_objective_id, audience_name = audience_name, rooftop_type = rooftop_type, rooftop_id = rooftop_id, logger = logger)
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
                            processed += 1
                    if (total % 10) == 0:
                        percent = int(100.0 * total / (reader.line_num or (total + error)))
                        yield {"_status": f"{percent}% completed"}
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