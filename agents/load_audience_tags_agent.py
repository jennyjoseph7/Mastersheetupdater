
# ps
# I/P :
# vehicle id, purchased date, odometer reading, when taken odometer reading,



# Catagory

# process : avd odo reading




# O/P :

import json
import os
from datetime import datetime
from ai_service import ai_service_app

try:
    from .base_agent import BaseAgent, gryd
except ImportError:
    from base_agent import BaseAgent, gryd 

class loadAudianceTags(BaseAgent):


    """Audience Tagging Agent

    This agent processes customer vehicle data and service history to generate
    intelligent audience tags such as predicted odometer usage, next service date,
    lost-customer detection, and customer overtaked by competitor-workshop detection.

    It is designed to be used inside automated CRM and service-reminder pipelines
    where customer segmentation and personalization depend on updated vehicle usage
    insights.

    inputs will be :
    {
        args : [],
        kwargs : {
            "vehicle_id" : "id of the vehicle",
            "purchase_date" : "Date of buy",
            "odometer_reading" : "last odometer reading recorded",
            "odometer_reading_record_date" : "Date of the odometer reading",
            "last_service_date" : "Last service date"
        }
    
    
    } 


    Output will be :
    {
        expected_service_date : "Next service date based on time/ odometer prediction",
        message_text : "draft of the message to be send to the user"
        customer_tags : "
                        "service_date_in_7days" : true/false,
                        "service_date_in_15days" : true/false,
                        "customer_overtaked_by_other_workshop" : true/false,
                        "customer_lost" : true/false
                        "
    
    
    }
    
    """


    def __init__(self,source : dict,**kwargs):
        self.source = source
        self.odometer_reading = source.get("odometer_reading")
        self.purchase_date = source.get("purchase_date")
        self.odometer_reading_date = source.get("odometer_reading_date")


    def odometer_reading_predictor(self):
        """Wll do odometer reading prediction for next service"""
        pass


    def service_time_predictor(self):
        """if odometer reading is low, it will calculate next service date according to the last service date"""
        pass

    def lost_customer_detector(self):
        """Will detect the customer who left the workshop for servicing calculated by odometer and time of not serviced
        IP : Service history data
        """
        pass


    def competetor_overtaked_predictor(self):
        
        """this will detect the customer who did the last service in an another workshop
        IP : Service history data
        """
        pass
        

@gryd.is_a_task('load_audiance_tags', logger_param='logger', job_param='job')
def load_audiance_tags(vehicle_info=None, logger=None, job=None):
    logger = logger or gryd.hp.get_logger(__name__)
    logger.info(f"Creating load audian tags for : {vehicle_info}")
    
    result = {
        
        "expected_service_date" : "18-11-2025", #Maybe null in case of customer lost
        "message_text" : "Hi, Your last service was on 18th June, As of the next service is due on completion of 5 months, Your next service should be completed by 18th Nov", #Maybe null in case of customer lost
        "customer_tags" : {
                        "service_date_in_7days" : True,
                        "service_date_in_15days" : False,
                        "customer_overtaked_by_other_workshop" : False,
                        "customer_lost" : False
                        }
    


    }
        
    return result
        


