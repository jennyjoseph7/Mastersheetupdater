import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from config import AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_CORE_SERVICE_NAME, AUTOCRM_AGENT_SERVICE_NAME, gryd, hp
from autocrm_db_helper import get_pg_connector
from typing import List, Union, Dict, Any

gryd.SERVICE = AUTOCRM_CORE_SERVICE_NAME
gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(gryd.SERVICE)
import csv
import os
import tempfile


def wind_up(*files):
    for file in files:
        if os.path.exists(file):
            os.remove(file)
    return

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
    logger.info(f"Importing leads from CSV for campaign_type: {campaign_type}, dealership_id: {dealership_id}, csv_file_link: {csv_file_link}, campaign_id: {campaign_id}, enterprise_id: {enterprise_id}, mapping: {mapping}, workshop_id: {workshop_id}")
    # Model selection
    model_info = {
        'pre-sales': {
            'lead_model': 'pre_sales_lead',
            'person_model': 'person',
            'campaign_model': 'pre_sales_campaign'
        },
        'post-sales': {
            'lead_model': 'post_sales_lead',
            'vehicle_model': 'vehicle',
            'person_model': 'person',
            'campaign_model': 'post_sales_campaign'
        },
        'dealership': {
            'lead_model': 'dealership_lead',
            'dealership_model': 'dealership',
            'campaign_model': 'dealership_campaign'
        }
    }
    if typ not in model_info:
        yield {"_error": f"Unsupported campaign_type: {campaign_type}"}
        return
    csv_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            csv_path = hp.download_or_copy(csv_file_link, path = temp_file.name, raise_error_downloading=True)
    except Exception as e:
        logger.error(f"Failed to download or copy CSV file: {str(e)}", exc_info=True)
        yield {"_error": f"Failed to download or copy CSV file: {str(e)}"}
        return
    finally:
        wind_up(csv_path, error_csv_path)
    # Models
    models = {}
    info = model_info[typ]
    for k, v in info.items():
        models[k] = gryd.base_model.Model(v, enterprise_id)

    # Prepare attr_seqs
    attr_seqs = {}
    for k, mdl in models.items():
        if hasattr(mdl, "_model_ref") and hasattr(mdl._model_ref, "attr_seq"):
            attr_seqs[k] = mdl._model_ref.attr_seq
        else:
            attr_seqs[k] = []

    # Campaign ID validation
    if campaign_id:
        try:
            found = models['campaign_model'].get(campaign_id)
            if not found:
                yield {"_error": f"Campaign ID '{campaign_id}' not found in {info['campaign_model']}"}
                return
        except Exception as e:
            yield {"_error": f"Error validating Campaign ID '{campaign_id}': {str(e)}"}
            return

    error_csv_path = None
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        error_csv_path = temp_file.name
    if error_csv_path:
        yield {"_error": f"Failed to create error CSV file: {str(e)}"}
        return

    # CSV error handling infrastructure
    error_lines = []
    total = 0
    errored = 0
    processed = 0

    # Open CSV and preparation
    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            if not headers:
                yield {"_error": f"CSV file has no headers"}
                return
            headers = [mapping.get(h, h).lower().strip().replace(' ', '_').replace('-', '_') for h in headers]
            # HEADER/REQUIRED FIELD checks (common, then type-specific)
            required_contact = ["phone_number", "email"]
            has_contact = any(h in headers for h in required_contact)
            if not has_contact:
                yield {"_error": f"CSV missing at least one required contact field: {required_contact}"}
                return

            if not "workshop_id" in headers and not workshop_id and not "workshop_name" in headers:
                yield {"_error": "Either workshop_id or workshop_name must be present as a column or argument"}
                return

            # campaign specific field check
            if typ == 'post-sales':
                if "reg_number" not in headers:
                    yield {"_error": "CSV is missing 'reg_number' which is required for post-sales campaign."}
                    return


            # Error csv
            tmp_dir = tempfile.gettempdir()
            error_csv_path = os.path.join(
                tmp_dir,
                f"import-{typ}-leads-errors-{campaign_id or 'tmp'}.csv"
            )
            error_csv_headers = headers + ["_error"]

            # Main CSV processing loop
            for i, row in enumerate(reader, 2):
                total += 1
                row_data = {mapping.get(h, h): v for h, v in row.items()}
                phone = row_data.get("phone_number") or row_data.get("mobile") or ""
                email = row_data.get("email") or ""
                ws_val = row_data.get('workshop_id') or workshop_id or row_data.get('workshop_name')

                error_prefix = f"Line {i}: "
                row_ctx = {
                  "line_num": i,
                  "row": row,
                  "row_data": row_data,
                  "phone": phone,
                  "email": email,
                  "workshop": ws_val,
                  "dealership_id": dealership_id,
                  "campaign_id": campaign_id,
                  "enterprise_id": enterprise_id
                }
                # Validate row mandatory fields
                missing_reason = None
                if not phone and not email:
                    missing_reason = error_prefix + "Missing phone_number and email"
                if not ws_val:
                    missing_reason = error_prefix + "Missing workshop_id or workshop_name"
                if typ == 'post-sales' and not row_data.get("vehicle_registration_number", ""):
                    missing_reason = error_prefix + "Missing vehicle_registration_number"
                if missing_reason:
                    yield {"_error": missing_reason, "row": row}
                    row["_error"] = missing_reason
                    error_lines.append(row)
                    errored += 1
                    continue

                try:
                    result, err = _process_lead_row_by_type(
                        typ, row_ctx, models, attr_seqs, kwargs
                    )
                    if err:
                        raise Exception(err)
                    processed += 1
                except Exception as e:
                    error_msg = f"{error_prefix}{str(e)}"
                    yield {"_error": error_msg, "row": row}
                    row["_error"] = error_msg
                    error_lines.append(row)
                    errored += 1

                if (total % 10) == 0:
                    percent = int(100 * total / (reader.line_num or total + errored))
                    yield {"_status": f"{percent}% completed"}

            # Write error CSV
            if error_lines:
                with open(error_csv_path, "w", newline="", encoding="utf-8") as fe:
                    writer = csv.DictWriter(fe, fieldnames=error_csv_headers)
                    writer.writeheader()
                    for err_row in error_lines:
                        for h in error_csv_headers:
                            if h not in err_row:
                                err_row[h] = ""
                        writer.writerow(err_row)
                yield {"_result": error_csv_path}
            else:
                yield {"_result": "No errors"}

    except Exception as e:
        yield {"_error": f"Failed to process CSV: {str(e)}"}


def _process_lead_row_by_type(typ, ctx, models, attr_seqs, extra_kwargs):
    """
    Processes a single csv row according to type.
    Args:
        typ: one of pre-sales, post-sales, dealership
        ctx: dict from main function per row, including row, row_data, etc
        models: dict of model objects
        attr_seqs: dict of attr_seq for each model
        extra_kwargs: all original kwargs
    Returns:
        result, errstr (errstr is None if ok)
    """
    row_data = ctx["row_data"]
    campaign_id = ctx["campaign_id"]
    dealership_id = ctx["dealership_id"]
    ws_val = ctx["workshop"]
    phone = ctx["phone"]
    email = ctx["email"]

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

    return None, "Model type not implemented"



