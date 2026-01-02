# from communication.connectors.campaign_manager import trigger_campaign

# from communication.connectors.connector_whatsapp import trigger_campaign
import sys, os
from gryd_worker import gryd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from campaign.campaign_worker import trigger_campaign,process_single_lead
import time
from communication.connectors.load_providers import load_providers
from config import WHATSAPP_PROVIDER_NAME,EMAIL_PROVIDER_NAME
from communication.connectors.whatsapp_connectors.source_connectors import BaseWebhookConverter
from cron.cron import check_inactive_sessions
from agents.get_whatsapp_template_agent import get_whatsapp_template

# from communication.connectors.whatsapp_connectors.airtel_connector import *


if __name__ == "__main__":
    
    load_providers(["whatsapp","email"])
    
    # trigger_campaign("pre-sales","63d8d5e1-640b-363f-bbe4-e298772149c8")
    # trigger_campaign("post-sales","626952a0-1ac7-3a7c-85aa-c46d30897ea4")
    
    # trigger_campaign("pre-sales","63d8d5e1-640b-363f-bbe4-e298772149c8")
    # trigger_campaign("post-sales","626952a0-1ac7-3a7c-85aa-c46d30897ea4")
    
    # gryd.create_async_task(
    #     "trigger_campaign",
    #     "autocrm-campaign",
    #     args=[],
    #     kwargs={"campaign_id":"b93ddf25-eeae-3328-a723-85fca5274150","campaign_type":"post-sales"}
    # )
    
    # gryd.create_async_task(
    #         "process_single_lead",
    #         "autocrm-campaign",
    #         args=["whatsapp_chat", "tn37dm7087-ambal-auto-ambal-auto---service-center-scheduled-service-reminder","post-sales","626952a0-1ac7-3a7c-85aa-c46d30897ea4"],
    #         kwargs={}
    #     )
    
    # gryd.create_async_task(
    #         "process_single_lead",
    #         "autocrm-campaign",
    #         args=["whatsapp_chat", "tn37dm7087-ambal-auto-scheduled-service-reminder","post-sales","74f260b8-e8dc-3c52-ab8d-31bd0fc49943"],
    #         kwargs={}
    #     )
    
    gryd.create_async_task(
            "process_single_lead",
            "autocrm-campaign",
            args=["email", "tn37dm7087-ambal-auto-scheduled-service-reminder","post-sales","74f260b8-e8dc-3c52-ab8d-31bd0fc49943"],
            kwargs={}
        )
    
    
    # gryd.create_async_task(
    #     "end_session",
    #     "autocrm-communication",
    #     args=[],
    #     kwargs={"session_id":"2f7a2c16541d3348"}
    # )
    
    # BaseWebhookConverter.send_custom_template(**{"template_id":"01kc8ysb0dtefxm874zamjfbc7","mobile_number":"9113687241"})
    # BaseWebhookConverter.send_otp_template(**{"template_id":"01kckk7efvtft7gqwg3cfwfsqe","mobile_number":"9113687241","otp":"1234abc"})
    
    # BaseWebhookConverter.end_session(**{"session_id":"a1f05f1c7f6834ef"})
    
    # while True:
    #     check_inactive_sessions(
    #         inactivity_time=5,
    #         only_for_channels=["whatsapp_chat", "whatsapp"]
    #     )
    #     time.sleep(60)
    
    # template_data = get_whatsapp_template(
    #         lead_id="tn37dm7087-ambal-auto-scheduled-service-reminder",
    #         campaign_type="post-sales",
    #         campaign_objective=campaign_details.get("campaign_objective"),
    #         # campaign_objective= [
    #         #     "Service Reminder"
    #         # ],
    #         dealership_id = "ambal-auto-south-india",
    #         lead_info={}
    #     )