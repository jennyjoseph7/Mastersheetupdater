import re
import time
from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
import sys
import json
import requests
from flask import Blueprint, request, jsonify

_root = dirname(dirname(abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from campaign.campaign_manager import BaseCampaignCreater,determine_campaign_next_action, get_or_create_person
from gryd_worker import gryd, gryd_db_helper as db, gryd_helpers as hp

logger = hp.get_logger(__name__)

import config
app = Blueprint("test_campaign", __name__)

def load_and_create_campaign_data(payload):
    
    campaign_model= f'{payload.get("campaign_type", "pre-sales").lower().replace("-", "_")}_campaign'
    m=config.AutocrmModel(model_name=campaign_model)
    
    a={
        "ctas": [
            "book-your-free-service"
        ],
        "channels": payload.get("channels",["voice_phone","whatsapp"]),
        "dealership_id": payload.get("dealership_id",""),
        "languages": payload.get("languages",["english"]),
        "campaign_objective_id": payload.get("campaign_objective_id",None),
        "campaign_name": payload.get("campaign_name","test campaign"),
        "campaign_type": payload.get("campaign_type","pre-sales"),
        "end_date": time.time() + 86400,
        "start_date": time.time(),
        "urgency_hook": "Claim your free service before it’s too late!",
        "cost_per_lead": 0.0,
        "campaign_offer": "Hey there! Just a friendly reminder that you have free service due. Take advantage of this awesome offer and keep your car in top shape. We’re here to help you every step of the way!",
        "campaign_status": "Active",
        "number_targeted": 0,
        "budget_allocated": 0,
        
        "campaign_description": "Hey there! Just a friendly reminder that you have free service due. Take advantage of this awesome offer and keep your car in top shape. We’re here to help you every step of the way!",
        "campaign_user_source": "auto_generated",
        "target_audience_tags": [
            "free-service-due",
            "purchase-date-less-than-1year",
            "warranty-active",
            "active-customer",
            "low-mileage-vehicle",
            "battery_health_alert",
            "tyre_health_alert",
            "tyre-rotation-due",
            "engine-oil-check",
            "brake_inspection_recommended",
            "suspension_check_recommended",
            "wheel_alignment_recommended",
            "car-washing-recommended"
        ],
        "conversion_rate_percent": 0.0
    }
    
    n=m.post(a)
    payload.update(n)
    post_lead_and_trigger_campaign(**payload)
    return n.get('campaign_id')
    

def post_lead_and_trigger_campaign(*args, **kwargs):
    
    logger.info(f"------ Post Lead And Trigger Campaign ------{kwargs}")
    
    if not kwargs.get("phone_number"):
        logger.error("Missing required kwargs. Got: phone_number")
        return
    
    # 1. Extract Details from kwargs with fallbacks (optional)
    campaign_id = kwargs.get("campaign_id")
    dealership_id = kwargs.get("dealership_id")
    campaign_type = kwargs.get("campaign_type", "pre-sales")
    campaign_objective_id = kwargs.get("campaign_objective_id")

    
    # Validation check to ensure required params are present
    if not all([campaign_id, dealership_id, campaign_objective_id]):
        error_msg = f"Missing required kwargs. Got: campaign_id={campaign_id}, dealership_id={dealership_id}"
        logger.error(error_msg)
        return

    models = BaseCampaignCreater.load_models(campaign_type)
    lead_model = models.get('lead_model')

    row = {
        "person_name": kwargs.get("person_name","Test User"),
        "phone_number": kwargs.get("phone_number"),
        "campaign_id": campaign_id,
        "dealership_id": dealership_id,
        "campaign_objective_id": campaign_objective_id,
        **kwargs
    }
    logger.info(f"Constructed row for manual registration: {row}")
    allowed_keys = [
        "phone_number", "email", "person_name", "campaign_id", "dealership_id", 
        "campaign_objective_id", "last_contacted_whatsapp_number", "last_contacted_email", 
        "last_contacted_phone_number", "brand_preference", "model_preference", 
        "variant_preference", "color_preference", "engine_type_preference", 
        "transmission_preference", "range_preference", "feature_preferences", 
        "segment_preference", "competitor_brands", "competitor_models", "emotions", 
        "engagement_events", "previous_interaction_ids", "lead_tags", 
        "interested_vehicle_competitor_vehicles"
    ]
    
    data = {k: row.get(k) for k in allowed_keys if row.get(k) is not None}

    try:
        logger.info(f"Posting {data}")
        # 1. Post the lead to the model
        lead = lead_model.post(data)
        
        if not lead:
            raise ValueError("Lead model post returned empty result.")

        # 2. KEY MAPPING
        if not lead.get('lead_id'):
            lead['lead_id'] = lead.get('pre_sales_lead_id') or lead.get('id')

        actual_id = lead.get('lead_id')
        logger.info(f"Triggering campaign for lead_id: {actual_id}, person: {lead.get('person_name')}, phone: {lead.get('phone_number')}")

        # 3. Trigger Campaign
        # # Note: Using campaign_id and campaign_type extracted from kwargs
        # gryd.create_async_task(
        #     "process_single_lead",
        #     AUTOCRM_CAMPAIGN_SERVICE_NAME,
        #     args=["voice_phone", lead, campaign_type, campaign_id],
        #     kwargs={}
        # )
        lead_table_id="pre_sales_lead_id" if campaign_type == "pre-sales" else "post_sales_lead_id"
        person = get_or_create_person(lead.get("phone_number"),lead.get("dealership_id"))
        
        lead_model.patch(lead.get(lead_table_id), {"user_id": person.get("user_id")})
        list(determine_campaign_next_action(campaign_type,lead.get(lead_table_id),call_process_single_lead=True))

        return {"_result": {
            "status": "success",
            "lead_id": actual_id,
            "message": f"Lead created for {lead.get('phone_number')} and campaign triggered."
        }}

    except Exception as e:
        logger.error(f"Manual registration/trigger failed: {str(e)}")
        raise
    
@app.route('/test_run_campaign', methods = ["POST"])
def test_run_campaign(*args,**kwargs):
    payload=request.get_json(silent=True) or request.form.to_dict() or request.data.decode()
    logger.info(f"Trigger And Run Campaign payload: {json.dumps(payload, indent=4)}")
    a=["phone_number","campaign_objective_id","dealership_id"]
    if not all([payload.get(i) for i in a]):
        logger.error(f"Missing required kwargs. Got: {a}")
        return jsonify({"error": f"Missing required kwargs. Got: {a}"}), 400
    
    m=load_and_create_campaign_data(kwargs)
    return jsonify({"status": f"campaign {m} triggered."}), 200
    
    


# if __name__ == "__main__":
#     test_run_campaign(**{
#     "campaign_objective_id":"pre-sales-test-drive-booking",
#     "dealership_id":"dave-ai-india",
#     "phone_number":"9113687241",
#     "channels":["voice_phone"],
#     "languages":["english"]
# })

