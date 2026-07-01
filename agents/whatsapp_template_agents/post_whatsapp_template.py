import os
import sys
from pprint import pprint

# agents/whatsapp_template_agents/<this file> → up three levels = project root
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
AGENTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if AGENTS_DIR not in sys.path:
    sys.path.insert(0, AGENTS_DIR)

try:
    from agents.base_agent import gryd
except ImportError:
    from base_agent import gryd

from autocrm_db_helper.PGConnector import AutoCRMPGConnector
pg = AutoCRMPGConnector(enterprise_id="autocrm")
AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")

def post_template_into_model(template_data):
    try:
        dim = gryd.base_model.Model('template', AUTOCRM_APP_ENTERPRISE_ID)
        print(f"Posting result to model 'templates' under enterprise '{AUTOCRM_APP_ENTERPRISE_ID}'")
        dim.post(template_data)
        print("Post completed successfully!")
    except Exception as db_error:
        print(f"Failed posting to Gryd model: {db_error}")

template_data = [
    {
        "buttons": [
            {
                "text": "Book a Test Drive",
                "type": "QUICK_REPLY"
            }
        ],
        "campaign_objective_name" : "Test Drive Booking",
        "campaign_type": "pre-sales",
        "dealership_id": "dave-ai-india",
        "channel": "whatsapp_chat",
        "communication_credentials_id": "airtel-whatsapp_chat-919187210945",
        "language": "english",
        "status": "Approved",
        "template_id": "01kvt10nn7q2s6etxn1dh3mrv3",
        "template_message": """Hi, Ready for your testdrive?""",
        "template_type": "text",
        "template_name": "test_drive_testing_template",
        "media_type" : "image",
        "template_variables": [],
    }
]


for i in template_data:
    template_name_lower = i["template_name"].lower()
    i["template_button_payloads"] = [
        f"{template_name_lower}-{btn['text'].lower().replace(' ', '_')}"
        for btn in i["buttons"]
    ]
    
    
    post_template_into_model(template_data=i)



# st jeep : airtel-whatsapp_chat-919187210940
# st citroen : airtel-whatsapp_chat-919187210943
# dave-ai-india : airtel-whatsapp_chat-919187210945
# daveai : airtel-whatsapp_chat-917795030574
# dave-ai-sociograph-solutions-india : rml-whatsapp_chat-919187238014