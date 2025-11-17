import os,sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import json
from gryd_worker import gryd_db_helper as db


class AutoCRMPGConnector(db.GrydPGConnector):
    def __init__(self, enterprise_id, *args, **kwargs):
        super().__init__(enterprise_id, *args, **kwargs)
    
    def update(self, table_name, id_attr, id, data, additional = "", additional_values = None):
        return super().update(table_name, id, data, id_attr, additional, additional_values) 
    def get(self, table_name, id_attr, id):

#         if table_name == "pre_sales_campaign":
#             return {
#     "dealership_id": "nexa-delhi-south",
#     "dealer_name": "NEXA Delhi South",
#     "dealership_type": "Single Brand",
#     "region_name": "North India",
#     "campaign_name": "Baleno Test Drive Campaign",
#     "campaign_type": "pre-sales",
#     "campaign_user_source": {
#       "source_type": "crm_database",
#       "filter_criteria": {
#         "interest_level": "high",
#         "vehicle_interest": "Baleno",
#         "customer_status": "active"
#       }
#     },
#     "campaign_objective": "Test Drive Reminder / Showroom Visit Reminder / Follow-Up",
#     "campaign_objective_type": "lead volume",
#     "campaign_sub_type": "lead generation",
#     "campaign_offer": "Free test drive with home pickup and drop service",
#     "campaign_description": "Generate test drive bookings for Baleno by targeting interested customers",
#     "start_date": 1704067200,
#     "end_date": 1735689600,
#     "channels": [
#       "whatsapp_chat",
#       "email",
#       "web_chat",
#       "voice_phone"
#     ],
#     "languages": [
#       "english",
#       "hindi"
#     ],
#     "urgency_hook": "Limited slots available! Book your test drive today and experience the premium Baleno.",
#     "ctas": [
#       "Book Test Drive",
#       "Schedule Visit",
#       "Know More"
#     ],
#     "number_targeted": 1000,
#     "number_reached": 900,
#     "number_contacted": 750,
#     "number_engaged": 500,
#     "number_converted": 200,
#     "budget_allocated": 100000,
#     "actual_spent": 85000,
#     "campaign_status": "Active",
#     "responsible_person": "Rahul Mehta",
#     "remarks": "Focus on customers who have shown interest in Baleno in the past 30 days",
#     "created": 1704067200,
#     "updated": 1704067200,
#     "campaign_id": "pre_sales_camp",
#     "conversion_rate_percent": 0,
#     "cost_per_lead": 0
#   }
#         if table_name == "post_sales_campaign":
#             return {
#     "workshop_id": "nexa-delhi-south-workshop-1",
#     "dealership_name": "NEXA Delhi South",
#     "region_name": "North India",
#     "workshop_code": "NDS-WS-001",
#     "workshop_name": "NEXA Delhi South - Service Center",
#     "campaign_name": "Scheduled Service Reminder",
#     "campaign_type": "post-sales",
#     "campaign_user_source": {
#       "source_type": "vehicle_database",
#       "filter_criteria": {
#         "service_due_date_range": "30_days",
#         "vehicle_status": "active"
#       }
#     },
#     "campaign_objective": "Scheduled Service Reminder",
#     "campaign_sub_type": "workshop awareness",
#     "campaign_objective_type": "lead volume",
#     "campaign_offer": "10% discount on service charges for bookings made within 7 days",
#     "campaign_description": "Remind customers about their upcoming scheduled service appointments",
#     "start_date": 1704067200,
#     "end_date": 1735689600,
#     "channels": [
#       "whatsapp_chat",
#       "email",
#       "voice_phone"
#     ],
#     "languages": [
#       "english",
#       "hindi"
#     ],
#     "urgency_hook": "Your vehicle service is due in 30 days. Book now to avoid last-minute rush!",
#     "ctas": [
#       "Book Service",
#       "Schedule Appointment",
#       "Call Now"
#     ],
#     "number_targeted": 500,
#     "number_reached": 450,
#     "number_contacted": 380,
#     "number_engaged": 250,
#     "number_converted": 120,
#     "budget_allocated": 50000,
#     "actual_spent": 42000,
#     "campaign_status": "Active",
#     "responsible_person": "Rajesh Kumar",
#     "remarks": "Focus on high-value customers with service history",
#     "created": 1704067200,
#     "updated": 1704067200,
#     "campaign_id": "post_sales_camp",
#     "conversion_rate_percent": 0,
#     "cost_per_lead": 0
#   }
#         if table_name == "session":
#             return {
#                 "session_id" : "alpha_Test",
#                 "campaign_id" : "post_sales_camp",
#                 "dealership_id" : "nexa-delhi-south",
#             }
        
        return super().get(table_name, id, id_attr) 
    def list(self, table_name, where):
        where  = "WHERE dict @> '{}'".format(json.dumps(where))
        return super().list(table_name, where)