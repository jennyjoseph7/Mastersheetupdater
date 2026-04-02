from gryd_worker import gryd
import sys, os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from agents.get_whatsapp_template_agent import get_whatsapp_template

result = response = gryd.await_result(
    task="get_whatsapp_template",
    service="autocrm-agent",
    kwargs={
        "lead_id": "test-8277676778-dave-ai-india-1e8288f2-2cdc-31f9-8f53-fa09d6e8801f",
        "campaign_type": "pre-sales",
        "campaign_objective" : ["Confirm Test Drives Through Tech Appeal - WhatsApp"],
        #"lead_info": {},
        "dealership_id": "dave-ai-india"
    }
)


print(result)
