from crm_integration.gryd_worker import gryd
from crm_integration.load_crm import load_crm

gryd.SERVICE = "autoengage-crm"
gryd.set_queue_manager()


@gryd.is_a_task(logger_param="logger", job_param="job")
def post_pre_sales_lead(crm_name, data, logger=None, job=None):
    crm = load_crm(crm_name, sheet_name="Ambal Sanganur Post-sales")
    return crm.post_pre_sales_lead(data)


@gryd.is_a_task(logger_param="logger", job_param="job")
def list_pre_sales_leads(crm_name, logger=None, job=None):
    crm = load_crm(crm_name, sheet_name="Ambal Sanganur Post-sales")
    return crm.list_pre_sales_leads()


@gryd.is_a_task(logger_param="logger", job_param="job")
def get_pre_sales_lead(crm_name, search_data, logger=None, job=None):
    crm = load_crm(crm_name, sheet_name="Ambal Sanganur Post-sales")
    return crm.get_pre_sales_lead(search_data)


@gryd.is_a_task(logger_param="logger", job_param="job")
def patch_pre_sales_lead(crm_name, search_data, status, logger=None, job=None):
    crm = load_crm(crm_name, sheet_name="Ambal Sanganur Post-sales")
    return crm.patch_pre_sales_lead(search_data, status)