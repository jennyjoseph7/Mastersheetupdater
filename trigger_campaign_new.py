# from communication.connectors.campaign_manager import trigger_campaign

# from communication.connectors.connector_whatsapp import trigger_campaign
import sys, os
from gryd_worker import gryd
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
# from campaign.campaign_worker import trigger_campaign,process_single_lead
from communication.connectors.whatsapp_connectors.source_connectors import BaseWebhookConverter
if __name__ == "__main__":
    
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
    
    gryd.create_async_task(
            "process_single_lead",
            "autocrm-campaign",
            args=["whatsapp_chat", "test-8277676778-test@iamdave.ai-dave-ai-us-india-12a55ed4-5db5-3287-91c2-5aa09beae444","pre-sales","12a55ed4-5db5-3287-91c2-5aa09beae444"],
            kwargs={
                "templateID":"787147271056124"
                # "templateID":"2130646657782594"
            }
        )



    # tn99t7877-ambal-auto-scheduled-service-reminder
    
    # gryd.create_async_task(
    #     "end_session",
    #     "autocrm-communication",
    #     args=[],
    #     kwargs={"session_id":"2f7a2c16541d3348"}
    # )
    
    # BaseWebhookConverter.end_session(**{"session_id":"a1f05f1c7f6834ef"})
    
    