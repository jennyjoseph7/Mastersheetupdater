from gryd_worker import gryd
import sys, os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from agents.get_whatsapp_template_agent import get_whatsapp_template

result = response = gryd.await_result(
    task="get_whatsapp_template",
    service="autocrm-agent",
    kwargs={
        "lead_id": "dl9cay4010-sree-saradhambal-automobiles-pvt-ltd-ambal-auto---service-center-keep-your-ride-smooth---service-reminder",
        "campaign_type": "post-sales",
        "campaign_objective" : ["Free Service Due Reminder"],
        #"lead_info": {},
        #"dealership_id": "daveai"
    }
)


print(result)
