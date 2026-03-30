from gryd_worker import gryd
import sys, os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from agents.get_whatsapp_template_agent import get_whatsapp_template

result = response = gryd.await_result(
    task="get_whatsapp_template",
    service="autocrm-agent",
    kwargs={
        "lead_id": "test-user-8248913170-stellantis-india-52975526-a76b-3fd5-956d-1c1db2c4a318",
        "campaign_type": "pre-sales",
        "campaign_objective" : ["Test Drive Booking"],
        #"lead_info": {},
        "dealership_id": "daveai"
    }
)


print(result)
