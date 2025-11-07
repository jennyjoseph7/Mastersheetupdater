from models import validators as val
import json, os, sys
import requests
import datetime, time




def calulate_total_billing_amount_func(ins, model, action, **kwargs):
  
    filter = ''
    if ins.get('quick_select'):
        filter = ins.get('quick_select')
    elif ins.get('start_date'):
        filter = f"{ins.get('start_date')},"
    elif ins.get('end_date'):
        if not ins.get('start_date'):
            filter = f',{ins.get('end_date')}'
    else:
        filter = filter + ins.get('end_date')

    #TODO:  complete this

def generate_billing_invoice_func(ins, mode, *args, **kwagrs):
    pass

def get_campaign_end_date_func(ins, campaign_id, campaign_end_date, **kwargs):
    pass

val.make_function(
    calulate_total_billing_amount_func,
    "calulate_total_billing_amount",
    given_args="instance",
    is_idempotent=False, 
    help_string = "Function to calculate billing total amount for dealership."
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