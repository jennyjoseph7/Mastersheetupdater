from models import validators as val
import json, os, sys
import requests
import datetime, time




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

def resolve_and_search_in_model_func(ins,**kwargs):

    model_name = kwargs.pop('model_name', None)
    attribute_name = kwargs.pop('attribute_name', None)
    lead_id = kwargs.pop('lead_id', None)
    _get_lead_id = kwargs.pop('_get_lead_id', False)
    if not model_name:
        raise ValueError("model_name is required for search_in_model")

    if model_name and lead_id and _get_lead_id:
        lead_model_id=f"{model_name}_id"
        kwargs[lead_model_id]=lead_id
        
    return val.search_among_model_func(
        ins,
        model_name,
        attribute_name,
        **kwargs
    )
 
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