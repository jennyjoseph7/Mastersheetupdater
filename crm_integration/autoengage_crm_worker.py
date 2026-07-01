import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from gryd_worker import gryd

from config import AUTOCRM_CRM_UPDATE_SERVICE_NAME
from crm_integration.crm_integration.load_crm import load_crm


gryd.SERVICE=AUTOCRM_CRM_UPDATE_SERVICE_NAME
gryd.set_queue_manager()


# @gryd.is_a_task(logger_param="logger",job_param="job")
# def post_pre_sales_lead(crm_name,data,logger=None,job=None):

#     crm=load_crm(crm_name)

#     return crm.post_pre_sales_lead(
#        data
#     )


@gryd.is_a_task(logger_param="logger",job_param="job")
def read_leads_from_sheet(crm_name,last_updated=None,logger=None,job=None):
    crm=load_crm(crm_name)
    return crm.read_leads_from_sheet(
       last_updated=last_updated
    )


# @gryd.is_a_task(
#  logger_param="logger",
#  job_param="job"
# )
# def list_post_sales_leads(
#     crm_name,
#     last_updated=None,
#     logger=None,
#     job=None
# ):

#     crm = load_crm(crm_name)

#     return crm.list_post_sales_leads(
#         last_updated=last_updated
#     )


@gryd.is_a_task(logger_param="logger",job_param="job")
def fetch_crm_leads(campaign_id,crm_name,sheet_name,last_sync_timestamp=None,campaign_type="pre-sales",logger=None,job=None):
    """
    Called by the cron job to fetch NEW leads from an external CRM
    (e.g., Google Sheet) since the last sync.

    Args:
        campaign_id (str):          The campaign this sync belongs to.
        crm_name (str):             CRM connector key e.g. "googledocs".
        sheet_name (str):           Name of the Google Sheet / CRM source.
        last_sync_timestamp (str):  ISO datetime — only fetch rows newer than this.
                                    If None, fetches all rows.
        campaign_type (str):        "pre-sales" or "post-sales".

    Returns:
        dict: {
            "campaign_id": str,
            "campaign_type": str,
            "leads": [...],          # list of lead dicts in internal format
            "leads_count": int
        }
    """
    crm = load_crm(crm_name, sheet_name=sheet_name)

    leads = crm.read_leads_from_sheet(last_updated=last_sync_timestamp)

    return {
        "campaign_id":   campaign_id,
        "campaign_type": campaign_type,
        "leads":         leads,
        "leads_count":   len(leads)
    }


@gryd.is_a_task(logger_param="logger",job_param="job")
def update_lead_in_crm(crm_name,sheet_name,phone_number,status,logger=None,job=None):
    """
    Called after a lead is processed (call placed) to write the updated
    status back to the external CRM (Google Sheet).

    Args:
        crm_name (str):     CRM connector key e.g. "googledocs".
        sheet_name (str):   Name of the Google Sheet.
        phone_number (str): Phone number to identify the lead.
        status (str):       New status to write back.

    Returns:
        dict: {"updated": True/False}
    """
    crm = load_crm(crm_name, sheet_name=sheet_name)

    return crm.update_status_for_matching_rows(
        {"phone_number": phone_number},
        status
    )


# CALLBACK TASK — called by  system after a call ends

@gryd.is_a_task(logger_param="logger",job_param="job")
def update_lead_in_sheet(
    phone_number,
    sheet_url,      # full Google Sheet URL (preferred over sheet_name)
    sheet_name=None,
    credentials=None,    
    logger=None,
    job=None,
    **kwargs
):
    """
    Called by system at the END of a voice/whatsapp session.

    autobot will pass in any relevant data from the call as kwargs, e.g.:
        sheet_name   (str)  — Google Sheet name, e.g. "Ambal Sanganur Post-sales"
        phone_number (str)  — identifies which row to update
        **kwargs            — any call result data, e.g.:
                                disposition      = "engaged"
                                lead_summary     = "Customer was interested in BYD..."
                                sentiment        = "positive"
                                emotional_analysis = "curious"

    What this task does:
        1. Opens the Google Sheet by sheet_name
        2. Finds the row(s) where Mobile Number == phone_number
        3. For each key in kwargs:
             - If the column already exists  → update that cell
             - If the column does NOT exist  → create the header then update the cell
        4. Returns how many rows were updated and which columns were added

    Format autobot must use when calling this task:
        gryd.create_async_task(
            "update_lead_in_sheet",
            AUTOCRM_CONVERSATION_SERVICE_NAME,
            kwargs={
                "sheet_name":        "Ambal Sanganur Post-sales",
                "phone_number":      "7606770402",
                "disposition":       "engaged",
                "lead_summary":      "Customer declined test drive offer...",
                "sentiment":         "positive",
                "emotional_analysis": "curious",
            }
        )
    """
    logger = logger or print

    logger.info(f"Sheet URL: {sheet_url}")

    crm = load_crm(
        "googledocs",
        # credentials=credentials,   # dict from DB — takes priority
        sheet_url=sheet_url,       # full URL → open_by_key
        sheet_name=sheet_name,     # fallback legacy title
    )

    result = crm.update_row_by_phone_number(
        phone_number=str(phone_number).strip(),
        data=kwargs
    )

    

    return result

