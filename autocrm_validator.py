from models import validators as val
import json, os, sys
import requests
import datetime, time
BASE_PATH = os.path.dirname(os.path.dirname(__file__))
if BASE_PATH not in sys.path:
    sys.path.append(BASE_PATH)

from gryd_worker import gryd, gryd_helpers as hp
from config import (
    AUTOCRM_APP_ENTERPRISE_ID, 
    AutocrmModel,
)

def calulate_total_billing_func(ins, model, attribute, action, **kwargs):
  
    filter = ''
    if ins.get('quick_select'):
        filter = ins.get('quick_select')
    elif ins.get('start_date'):
        filter = f"{ins.get('start_date')},"
    elif ins.get('end_date'):
        if not ins.get('start_date'):
            filter = f"{ins.get('end_date')}"
    else:
        filter = filter + ins.get('end_date')

    #TODO:  complete this


def generate_billing_invoice_func(ins, mode, *args, **kwagrs):
    pass

def get_transaction_id(ins, *args, **kwargs):
    pass

def get_campaign_end_date_func(ins, campaign_id, campaign_end_date, **kwargs):
    pass

def resolve_and_search_in_model_func(ins,_default=None,**kwargs):

    model_name = kwargs.pop('model_name', None)
    attribute_name = kwargs.pop('attribute_name', None)
    lead_id = kwargs.pop('lead_id', None)
    _get_lead_id = kwargs.pop('_get_lead_id', False)
    if not model_name:
        raise ValueError("model_name is required for search_in_model")

    if model_name and lead_id and _get_lead_id:
        lead_model_id=f"{model_name}_id"
        kwargs[lead_model_id]=lead_id
    m=gryd.base_model.Model(model_name,AUTOCRM_APP_ENTERPRISE_ID)
    r = hp.make_single(m.list(_page_size=1, _as_option=True,
                       **kwargs), force=True, default={})
    if _default is None:
        _default = ""
    if attribute_name:
        return r.get(attribute_name, _default)
    return r or _default

def plot_lead_session_history_func(ins, lead_attribute, **kwargs):
    model_name = kwargs.pop('model_name', 'session')
    
    if not model_name:
        raise ValueError("model_name is required for plot_lead_session_history")

    # if not lead_id:
    #     lead_id = ins.get(f"{model_name}_id")
        
    if not lead_attribute:
        return ""

    sm = AutocrmModel("session")
    sessions = sm.list(lead_id=lead_attribute, _sort_by="updated", _as_option = True)
    
    if not sessions:
        return ""
        
    history = []
    for s in sessions:
        channel = s.get('channel', 'unknown')
        disposition = s.get('disposition', 'unknown')
        if channel and disposition:
            history.append(f"{channel}({disposition})")
            
    return " -> ".join(history)

val.make_function(
    calulate_total_billing_func,
    "calulate_total_billing_amount",
    given_args="instance",
    is_idempotent=False, 
    help_string = "Function to calculate billing total amount for dealership."
)

val.make_function(
    resolve_and_search_in_model_func,
    "resolve_and_search_in_model",
    given_args="instance",
    is_idempotent=False, 
    help_string = "Resolve model and attribute dynamically, then search and return the first matching result or attribute value."
)

val.make_function(
    plot_lead_session_history_func,
    "plot_lead_session_history",
    given_args="instance",
    is_idempotent=False, 
    help_string = "Plot all sessions of a lead in the format channel-disposition -> channel-disposition"
)
val.make_function(
    generate_billing_invoice_func,
    "generate_billing_invoice",
    given_args="instance",
    is_idempotent=False, 
    help_string = "Function to generate invoice for dealership based on filters."
)

val.make_function(
    get_campaign_end_date_func,
    "get_campaign_end_date",
    given_args="instance",
    is_idempotent=False, 
    help_string = "Get campaign end date based on campaign id and campaign type"
)


val.make_function(
    get_transaction_id,
    "generate_transaction_id",
    given_args="instance",
    is_idempotent=False, 
    help_string = "Get transaction id from payment gateway"
)