# from communication.connectors.campaign_manager import trigger_campaign

# from communication.connectors.connector_whatsapp import trigger_campaign
import sys, os
from gryd_worker import gryd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from campaign.campaign_worker import trigger_campaign,process_single_lead
if __name__ == "__main__":
    
    # trigger_campaign("pre-sales","63d8d5e1-640b-363f-bbe4-e298772149c8")
    # trigger_campaign("post-sales","626952a0-1ac7-3a7c-85aa-c46d30897ea4")
    
    gryd.create_async_task(
            "process_single_lead",
            "autocrm-campaign",
            args=["None", "dl9cay2838-ambal-auto-scheduled-service-reminder","post-sales","74f260b8-e8dc-3c52-ab8d-31bd0fc49943"],
            kwargs={}
        )