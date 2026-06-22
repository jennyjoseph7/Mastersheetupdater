import os, sys
from pprint import pprint
from agents.base_agent import gryd


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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
                "text": "Book Test Drive",
                "type": "QUICK_REPLY"
            }
        ],
        "campaign_objective_name" : "Inbound Lead Handling",
        "campaign_type": "pre-sales",
        "channel": "whatsapp_chat",
        "communication_credentials_id": "rml-whatsapp_chat-919187238014",
        "language": "english",
        "status": "Approved",
        "template_id": "1333573168732645",
        "template_message": """Hi, Would you like to visit our showroom for a test drive""",
        "template_name": "media_testing_template_for_rml",
        "media_id" : "4::aW1hZ2UvcG5n:ARZl-aEvC5O4Zf-hf3DaD0UoAKUEZfS6YH4vSldIAHFXFsIJhbwXTm0k69UTlw_Ugo1a0LRFtqJrKyVolgIktcwng0th3-1B0lJhXx252zj4nQ:e:1782048478:688867587520075:100067191205380:ARaMz43nygnufqJ2eAw",
        "media_type" : "image",
        "media_url" : "https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9ff08e25-12e8-4582-92de-58d6672fe0f3-6a352e0a_sign_1.jpg",
        "template_type": "media",
        "media_file_name": "images.png",
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