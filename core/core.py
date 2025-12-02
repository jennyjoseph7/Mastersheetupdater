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


MIME_TYPES = {'aac': 'audio/aac','flac': 'audio/flac','wma': 'audio/x-ms-wma','mpa': 'audio/mpeg','aiff': 'audio/x-aiff','xm': 'audio/xm','m4a': 'audio/mp4','pls': 'audio/x-scpls','ape': 'audio/ape',  'wav': 'audio/wav','au': 'audio/basic','mp3': 'audio/mpeg','avif': 'image/avif','ps': 'application/postscript','bmp': 'image/bmp','jpeg': 'image/jpeg','webp': 'image/webp','tif': 'image/tiff','jpg': 'image/jpeg','tiff': 'image/tiff','png': 'image/png','svg': 'image/svg+xml','gif': 'image/gif','heif': 'image/heif','webm': 'video/webm','m4p': 'video/mp4','mpeg': 'video/mpeg','mov': 'video/quicktime','gifv': 'video/gifv', 'mkv': 'video/x-matroska','mp4': 'video/mp4','flv': 'video/x-flv','avi': 'video/x-msvideo','xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','pdf': 'application/pdf','doc': 'application/msword','docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document','log': 'text/plain','csv': 'text/csv','xls': 'application/vnd.ms-excel','wpd': 'application/wordperfect','ods': 'application/vnd.oasis.opendocument.spreadsheet','ico': 'image/vnd.microsoft.icon','md': 'text/markdown','ppt': 'application/vnd.ms-powerpoint','pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation','txt': 'text/plain','wps': 'application/vnd.ms-works','msg': 'application/vnd.ms-outlook','json': 'application/json','yaml': 'application/x-yaml','yml': 'application/x-yaml'}

def func_gryd_file_system(local_path, logger = None, **kwargs):
    logger = logger or mlogger
    logger.info(f"Uploading file to Gryd File System: {local_path}")
    url = f"{GRYD_FILE_SERVER_URL}/media/{kwargs.get('media_type','document')}"

    ext = os.path.splitext(local_path)[1].replace('.','').lower()
    content_type = MIME_TYPES[ext]

    logger.info(f'Local Path: {local_path}')
    logger.info(f'Content Type: {content_type}')

    with open(local_path, 'rb') as f:
        files = [('file',(os.path.basename(local_path), f, content_type))]
    headers = {
        'X-I2CE-ENTERPRISE-ID': 'gryd_file_system',
        'X-I2CE-USER-ID': GRYD_FILE_USER_ID,
        'X-I2CE-API-KEY': GRYD_FILE_API_KEY
    }
    response = requests.request("POST", url, headers=headers, files=files)
    logger.info(f'Gryd File System Response: {response.text}')
    if response.status_code == 200:
        resp_json = response.json()
        return resp_json.get('file_url')
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
    vehicles = vehicle_model.list(_as_option=True, _page_size=1, reg_number=row.get('reg_number'))
    if vehicles:
        vehicle_id = vehicles[0].get('vehicle_id')
        row['vehicle_id'] = vehicle_id
        return row, missing_reason
    data = {}
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
            "purchase_date",
            "registration_date",
            "original_delivery_date",
            "vehicle_age_months",
            "last_service_date",
            "last_service_type",
            "service_history",
            "service_advisor",
            "service_plan_type",
            "service_plan_expiry_date",
            "next_service_due",
            "service_feedback",
            "feedback_rating",
            "feedback_sentiment_score",
            "warranty_expiry_date",
            "extended_warranty_purchased",
            "avg_service_cost",
            "service_frequency",
            "loan_end_date",
            "odometer_reading",
            "odometer_reading_date",
            "avg_monthly_mileage",
            "vehicle_usage_category",
            "battery_health",
            "battery_warranty_expiry_date",
            "battery_change_date",
            "battery_service_date",
            "oil_change_date",
            "brake_pad_change_date",
            "tyre_change_date",
            "tyre_change_details",
            "tyre_health",
            "wheel_alignment",
            "suspension_check_date",
            "coolant_radiator_service_date",
            "ac_vent_cleaning_date",
            "underbody_coating_date",
            "car_wash_date",
            "brake_oil_change_date",
            "oil_filter_replacement_date",
            "polishing_and_waxing_date",
            "ac_vent_cleaning_date",
            "repair_notes",
            "first_owner_name",
            "ownership_status",
            "finance_loan_status",
            "loan_provider",
            "loan_account_number",
            "loan_amount",
            "emi_amount",
            "emi_due_date",
            "insurance",
            "puc",
            "customer_score"
        ]:
        if k in row:
            data[k] = row.get(k)
    for k in [ 
            "last_service_date",
            "next_service_due",
            "warranty_expiry_date",
            "insurance_expiry_date",
            "purchase_date",
            "registration_date",
            "original_delivery_date",
        ]:
        if k in row and row.get(k):
            data[k] = hp.to_epoch(row.get(k))
    if data.get('customer_score'):
        data['customer_score'] = int(data['customer_score'])
    if not data:
        missing_reason.append("No vehicle data found")
        return row, missing_reason
    try:
        vehicle = vehicle_model.post(data)
    except Exception as e:
        missing_reason.append(f"Failed to find suitable vehicle: {str(e)}")
        return row, missing_reason
    row['vehicle_id'] = vehicle.get('vehicle_id')
    return row, missing_reason


def process_post_sales_lead_row(row, models, missing_reason = None, rooftop_id = None, logger = None):
    logger = logger or mlogger
    logger.info(f"Processing post-sales lead row: {row}")
    missing_reason = missing_reason or []
    ws_val = rooftop_id or row.get('workshop_id')
    if not ws_val:
        if row.get('workshop_name'):
            ws_val = hp.make_single(
                models['rooftop_model'].list(
                    _as_option=True, 
                    _page_size=1,
                    workshop_name=f"~{row.get('workshop_name')}"
                ),
                force = True
            )
            ws_val = ws_val.get('workshop_id')
    if not ws_val:
        missing_reason.append("Workshop ID or workshop_name not found")
    row['workshop_id'] = ws_val
    if not any([row.get(k) for k in ['next_service_due', 'warranty_expiry_date', 'insurance_expiry_date']]):
        missing_reason.append("Either one of next service due date, warranty expiry date, or insurance expiry date is required")
    if row.get('next_service_due'):
        row['service_due_timestamp'] = hp.to_epoch(row.get('next_service_due'))
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
        if k in row:
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
        if k in row:
            data[k] = row.get(k)
    dealership = models['lead_model'].post(data)
    return dealership.get('dealership_id')

def get_persons_involved(row, models, missing_reason = None, logger = None):
    logger = logger or mlogger
    logger.info(f"Getting persons involved for row: {row}")
    missing_reason = missing_reason or []
    person_model = models['person_model']
    phone = row.get('phone_number') or row.get('mobile') or ""
    email = row.get('email') or ""
    if not phone and not email:
        missing_reason.append("Missing phone_number and email, required one of them")
    persons_involved = []
    for k in ["phone_number", "alt_phone_number_2", "alt_phone_number_3", "alt_phone_number_4"]:
        phone = row.get(k)
        if phone:
            for l in ["phone_number", "alt_phone_number_2", "alt_phone_number_3", "alt_phone_number_4"]:
                persons = person_model.list(_as_option=True, _page_size=1, **{l: f"{phone}^"})
                if persons:
                    persons_involved.extend(persons)
                    break
    for k in ["email", "alt_email_2", "alt_email_3", "alt_email_4"]:
        email = row.get(k)
        if email:
            for l in ["email", "alt_email_2", "alt_email_3", "alt_email_4"]:
                persons = models['person_model'].list(_as_option=True, _page_size=1, **{l: f"{email}^"})
                if persons:
                    persons_involved.extend(persons)
                    break
    if not persons_involved:
        data = {}
        for k in person_model._model_ref.attr_seq:
            if k in row:
                data[k] = row.get(k)
            mlogger.info(f"Data: {data}")
            try:
                person = person_model.post(data)
            except Exception as e:
                missing_reason.append(f"Failed to post person: {str(e)}")
            else:
                persons_involved.append(person)
    return row, missing_reason


def process_common_row(campaign_type, row, models, missing_reason = None, dealership_id = None, campaign_id = None, campaign_objective_id = None, rooftop_type = None, rooftop_id = None, logger = None):
    logger = logger or mlogger
    logger.info(f"Processing common row: {row}")
    missing_reason = missing_reason or []
    row['dealership_id'] = dealership_id
    row['campaign_id'] = campaign_id
    row['campaign_objective_id'] = campaign_objective_id
    row['campaign_type'] = campaign_type
    if campaign_type == 'pre-sales':
        row, missing_reason = process_pre_sales_lead_row(row, models, missing_reason, rooftop_id, logger = logger)
    elif campaign_type == 'post-sales':
        row, missing_reason = process_post_sales_lead_row(row, models, missing_reason, rooftop_id, logger = logger)
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
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            error_csv_path = temp_file.name
    except Exception as e:
        wind_up(csv_path, error_csv_path)
        raise Exception(f"Failed to create error CSV file: {str(e)}")
    return csv_path, error_csv_path

def validate_campaign_or_campaign_objective_id(campaign_id, campaign_objective_id, models, logger = None):
    logger = logger or mlogger
    logger.info(f"Validating campaign or campaign objective ID: {campaign_id}, {campaign_objective_id}")
    if campaign_id:
        found = models['campaign_model'].get(campaign_id)
        if not found:
            raise ValueError(f"Campaign ID '{campaign_id}' not found in {models['campaign_model']}")
        return found
    elif campaign_objective_id:
        found = models['campaign_model'].list(_as_option=True, _page_size=1, campaign_objective_id=campaign_objective_id)
        if not found:
            raise ValueError(f"Campaign objective ID '{campaign_objective_id}' not found in {models['campaign_model']}")
        return found
    else:
        raise ValueError("Campaign ID or campaign objective ID is required")
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
            - campaign_id
            - mapping: header mapping
            - workshop_id
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
    enterprise_id = kwargs.get("enterprise_id") or AUTOCRM_APP_ENTERPRISE_ID
    mapping = kwargs.get("mapping", {})
    workshop_id = kwargs.get("workshop_id")
    showroom_id = kwargs.get("showroom_id")
    rooftop_type = "workshop" if workshop_id else "showroom" if showroom_id else "dealership"
    rooftop_id = workshop_id if rooftop_type == 'workshop' else showroom_id if rooftop_type == 'showroom' else dealership_id
    campaign_objective_id = kwargs.get("campaign_objective_id")
    logger.info(f"Importing leads from CSV for campaign_type: {campaign_type}, dealership_id: {dealership_id}, csv_file_link: {csv_file_link}, campaign_id: {campaign_id}, enterprise_id: {enterprise_id}, mapping: {mapping}, {rooftop_type}_id: {rooftop_id}")
    # Model selection
    models = load_models(typ)
    csv_path = None
    error_csv_path = None
    try:
        csv_path, error_csv_path = create_temporary_files(csv_file_link, logger = logger)
        logger.info(f"CSV path: {csv_path}, error_csv_path: {error_csv_path}")
        # Campaign ID validation
        campaign = validate_campaign_or_campaign_objective_id(campaign_id, campaign_objective_id, models, logger = logger)
        campaign_id = campaign.get('campaign_id')
        campaign_objective_id = campaign.get('campaign_objective_id')
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
                total = 0
                error = 0
                processed = 0
                # Main CSV processing loop
                for i, row in enumerate(reader, 2):
                    total += 1
                    missing_reason = [f"Line {i}: "]
                    row = {headers[i]: row.get(k) for i, k in enumerate(row.keys())}
                    logger.info(f"Row: {row}")
                    row, missing_reason = process_common_row(typ, row, models, missing_reason, dealership_id, campaign_id, campaign_objective_id, rooftop_type, rooftop_id, logger = logger)
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
                            models['lead_model'].post(row)
                        except Exception as e:
                            error += 1
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



    if typ == "pre-sales":
        lead_model = models["lead_model"]
        person_model = models["person_model"]
        lead_attr_seq = attr_seqs.get("lead_model", [])
        person_attr_seq = attr_seqs.get("person_model", [])

        # Check if lead exists by phone/email
        query = {}
        if phone:
            query["phone_number"] = phone
        elif email:
            query["email"] = email
        found_leads = lead_model.list(_as_option=True, _page_size=1, **query)
        if found_leads:
            # Copy and make new lead (not update/overwrite)
            existing_lead = found_leads[0]
            new_data = dict(existing_lead)
            for attr in lead_attr_seq:
                if row_data.get(attr):
                    new_data[attr] = row_data[attr]
            new_data["dealership_id"] = dealership_id
            new_data["campaign_id"] = campaign_id
            new_data["workshop_id"] = ws_val
            posted = lead_model.post(new_data)
            return posted, None
        else:
            # Create person
            person_data = {k: v for k, v in row_data.items() if k in person_attr_seq}
            if phone:
                person_data["phone_number"] = phone
            if email:
                person_data["email"] = email
            p = person_model.post(person_data)
            # Create the lead and link to person
            lead_data = {k: v for k, v in row_data.items() if k in lead_attr_seq}
            lead_data["dealership_id"] = dealership_id
            lead_data["campaign_id"] = campaign_id
            lead_data["workshop_id"] = ws_val
            lead_data["user_id"] = p.get("person_id")
            posted = lead_model.post(lead_data)
            return posted, None

    elif typ == "post-sales":
        lead_model = models["lead_model"]
        vehicle_model = models["vehicle_model"]
        person_model = models["person_model"]
        lead_attr_seq = attr_seqs.get("lead_model", [])
        vehicle_attr_seq = attr_seqs.get("vehicle_model", [])
        person_attr_seq = attr_seqs.get("person_model", [])

        veh_reg = row_data.get("vehicle_registration_number", "")

        # Find or create vehicle
        vehicle_q = {"vehicle_registration_number": veh_reg}
        vehicles = vehicle_model.list(_as_option=True, _page_size=1, **vehicle_q)
        if vehicles:
            vehicle = vehicles[0]
            vehicle_id = vehicle.get("vehicle_id")
        else:
            vehicle_data = {k: v for k, v in row_data.items() if k in vehicle_attr_seq}
            vehicle_data["vehicle_registration_number"] = veh_reg
            v = vehicle_model.post(vehicle_data)
            vehicle_id = v.get("vehicle_id")

        # Find or create person by phone/email
        person = None
        if phone:
            pquery = {"phone_number": phone}
            people = person_model.list(_as_option=True, _page_size=1, **pquery)
            if people:
                person = people[0]
        if not person and email:
            pquery = {"email": email}
            people = person_model.list(_as_option=True, _page_size=1, **pquery)
            if people:
                person = people[0]
        if not person:
            person_data = {k: v for k, v in row_data.items() if k in person_attr_seq}
            if phone:
                person_data["phone_number"] = phone
            if email:
                person_data["email"] = email
            person = person_model.post(person_data)

        # Create the lead
        lead_data = {k: v for k, v in row_data.items() if k in lead_attr_seq}
        lead_data["dealership_id"] = dealership_id
        lead_data["campaign_id"] = campaign_id
        lead_data["workshop_id"] = ws_val
        lead_data["vehicle_id"] = vehicle_id
        lead_data["user_id"] = person.get("person_id")
        posted = lead_model.post(lead_data)
        return posted, None

    elif typ == "dealership":
        lead_model = models["lead_model"]
        dealership_model = models["dealership_model"]
        lead_attr_seq = attr_seqs.get("lead_model", [])
        dealership_query = {}
        if row_data.get("dealership_id"):
            dealership_query["dealership_id"] = row_data.get("dealership_id")
        elif dealership_id:
            dealership_query["dealership_id"] = dealership_id
        elif row_data.get("dealer_name"):
            dealership_query["dealer_name"] = row_data.get("dealer_name")
        dealership_obj = None
        if dealership_query:
            ds = dealership_model.list(_as_option=True, _page_size=1, **dealership_query)
            if ds:
                dealership_obj = ds[0]

        # Compose the lead data
        lead_data = {k: v for k, v in row_data.items() if k in lead_attr_seq}
        lead_data["dealership_id"] = dealership_obj.get("dealership_id") if dealership_obj else dealership_id
        lead_data["campaign_id"] = campaign_id
        lead_data["workshop_id"] = ws_val
        posted = lead_model.post(lead_data)
        return posted, None


if __name__ == "__main__":

    #gryd_task_import_leads_from_csv.execute("post-sales", "ambal-auto-south-india", "https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/485b7cbc-55d5-44d2-b5b9-0e6d6e405f4c-692977e5_afinallead.csv", campaign_id = "74f260b8-e8dc-3c52-ab8d-31bd0fc49943", workshop_id = 12)    
    gryd_task_import_leads_from_csv.execute(
        "post-sales", 
        "ambal-auto-south-india", 
        "/Users/ggananth/Downloads/afinallead.csv", 
        campaign_id = "74f260b8-e8dc-3c52-ab8d-31bd0fc49943", 
        workshop_id = 12
    )    
