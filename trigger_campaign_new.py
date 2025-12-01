# from communication.connectors.campaign_manager import trigger_campaign

# from communication.connectors.connector_whatsapp import trigger_campaign
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from campaign.campaign_worker import trigger_campaign
if __name__ == "__main__":
    
    # trigger_campaign("pre-sales","63d8d5e1-640b-363f-bbe4-e298772149c8")
    trigger_campaign("post-sales","c2a04796-bb67-3b19-bdaa-b27243fdf770")




    # template_data=gryd.create_async_task(
    #     "get_template_from_lead",
    #     AUTOCRM_CAMPAIGN_SERVICE_NAME,
    #     args=[lead_id],
    #     kwargs={}
    #     )
    
    # template_data=yield_gryd_task_results("get_template_from_lead",AUTOCRM_CAMPAIGN_SERVICE_NAME,{"lead_id":lead_id})