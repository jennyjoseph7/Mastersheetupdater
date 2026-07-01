# import requests
# import json
# import os
# import sys

# with open("seed/temp.json", "r") as file:
#     templates = json.load(file)


# url = "https://api.autongage.com/gryd/login"

# payload = json.dumps({
#   "user_id": "ananth+autongageprod@iamdave.ai",
#   "password": "jzT0mF=3eKGs,2oX"
# })
# headers = {
#   'Content-Type': 'application/json',
#   'X-GRYD-ENTERPRISE-ID': 'autocrm',
#   'X-GRYD-SIGNUP-TOKEN': 'YXV0b2NybTE3NzIxOTgyNzEgNjE1NzEzNg__'
# }

# response = requests.request("POST", url, headers=headers, data=payload)
# response_data = response.json()
# token = response_data.get("token")
# session_id = response_data.get("session_id")



# url = "https://api.autongage.com/gryd/db/object/template"

# for i in templates:

#     template_name_lower = i["template_name"].lower()

#     i["template_button_payloads"] = [
#         f"{template_name_lower}-{btn['text'].lower().replace(' ', '_')}"
#         for btn in i["buttons"]
#     ]

#     payload = json.dumps(i)

#     headers = {
#       'Content-Type': 'application/json',
#       'X-GRYD-ENTERPRISE-ID': 'autocrm',
#       'X-GRYD-TOKEN': token,
#       'X-GRYD-SESSION-ID': session_id,
#       'Accept': 'application/json',
#       'X-GRYD-ROLE': 'agent'
#     }

#     response = requests.request("POST", url, headers=headers, data=payload)

#     print(response.text)

# print("Template migration completed successfully!")
import requests
import json

# with open("seed/temp.json", "r") as file:
#     templates = json.load(file)


templates = [{
        "buttons": [
            {
                "text": "Book Test Drive",
                "type": "QUICK_REPLY"
            },
            {
                "text": "Request Call Back",
                "type": "QUICK_REPLY"
            }
        ],
        "campaign_objective_name": "Anant cars Mahindra EV Presales WhatsApp (Video)",
        "campaign_type": "pre-sales",
        "channel": "whatsapp_chat",
        "communication_credentials_id": "airtel-whatsapp_chat-919108444914",
        "language": "english",
        "status": "approved",
        "template_id": "01kvqn084a0bxhz29egh1hnvh9",
        "template_message": """⚡🚘 BIG SAVINGS. 0 ROAD TAX. 🚘⚡

Now is the perfect time to switch to a Mahindra EV and maximize your savings.

🚘 BE 6 – Starting at ₹18.90 Lakhs*
🚘 XEV 9e – Starting at ₹21.90 Lakhs*

💥 Benefits up to ₹1.96 Lakhs*
🚗 0 Road Tax*
⏳ Limited Period Offer
🚗 Limited Stock Available

Watch the video and discover why now is the right time to bring home a Mahindra EV.

📍 Visit Anant Cars Showrooms:
Bannerghatta Road | Marathahalli | Mysore Road | KR Puram 

📞 Contact: 9900077177 | 9108444914

*T&C apply""",
        "template_name": "MahindraEV_Presales_offer",
        "template_type": "media",
        "media_type": "video",
        "media_file_name": "Anant_cars_EV_campaign.mp4",
        "media_url": "https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/video/f9be9b8d-20c3-4c20-a5b9-e5b045900364-6a394a6f_Anant_cars_EV_campaign.mp4",
        "template_variables": [],
    },{
          "buttons": [
            {
                "text": "Book Service",
                "type": "QUICK_REPLY"
            },
            {
                "text": "Request a Call Back",
                "type": "QUICK_REPLY"
            }
        ],
        "campaign_objective_name": "WhatsApp Monsoon Service Remainder Fortune Toyota (Text)",
        "campaign_type": "post-sales",
        "channel": "whatsapp_chat",
        "communication_credentials_id": "rml-whatsapp_chat-919187238015",
        "language": "english",
        "status": "approved",
        "template_id": "37693862156879288",
        "template_message": """Dear {{person_name}},
 
Your {{vehicle_model}} with registration No. {{reg_number}}is due for service. Don't miss Fortune Toyota's *Monsoon Service Camp*, packed with exclusive benefits to keep your vehicle performing at its best.
 
📅 *Offer Valid: 15th June – 30th June  2026*
🎁 FREE Oil Filter with OC & PMS
🔧 10% OFF on Selected Parts
🛡️ Comprehensive Monsoon Health Check-Up
🚘 Up to 25% OFF on Bodyshop Labor
🛞 ₹500 OFF on 4 Tyres
🔋 ₹200 OFF on Battery Purchase
⚙️ 10% OFF on Engine Flush & Injector Cleaner
 
Limited-period offers designed to ensure a safer, smoother, and worry-free drive this rainy season.
 
📞 *Shall I reserve a service slot for your vehicle?*""",
        "template_name": "fortune_monsoon_service_campaign_text",
        "template_type": "text",
        "template_variables": ["person_name", "vehicle_model", "reg_number"],
    },{
      "buttons": [
            {
                "text": "Book Test Drive",
                "type": "QUICK_REPLY"
            },
            {
                "text": "Request a Callback",
                "type": "QUICK_REPLY"
            }
        ],
        "campaign_objective_name": "Hyryder WhatsApp Fortune Telangana(Text)",
        "campaign_type": "pre-sales",
        "channel": "whatsapp_chat",
        "communication_credentials_id": "rml-whatsapp_chat-919187238015",
        "language": "english",
        "status": "approved",
        "template_id": "2126930878170075",
        "template_message": """Dear {{person_name}},
🚗 DON'T JUST EXCHANGE, UPGRADE! 🚗
 
Upgrade to the Toyota Hyryder and enjoy Exchange Bonus up to ₹1,00,000*.*
 
 
✅ Best Exchange Value
✅ Attractive Finance Offers
✅ Spot Evaluation
✅ Immediate Delivery Options
 
Visit Fortune Toyota today and drive home your dream Toyota.
 
📍 Tolichowki | Sanathnagar | Kushaiguda | Siddipet
📞 77997 21000
 
T&C Apply""",
        "template_name": "fortune_hyryrder_presales_test",
        "template_type": "text",
        "template_variables": ["person_name"],
    }
]


# ---------------- LOGIN ---------------- #

login_url = "https://api.autongage.com/gryd/login"

login_payload = {
    "user_id": "ananth+autongageprod@iamdave.ai",
    "password": "jzT0mF=3eKGs,2oX"
}

login_headers = {
    "Content-Type": "application/json",
    "X-GRYD-ENTERPRISE-ID": "autocrm",
    "X-GRYD-SIGNUP-TOKEN": "YXV0b2NybTE3NzIxOTgyNzEgNjE1NzEzNg__"
}

response = requests.post(
    login_url,
    headers=login_headers,
    json=login_payload
)

if response.status_code != 200:
    print("Login failed")
    print(response.text)
    exit()

response_data = response.json()

token = response_data.get("token")
session_id = response_data.get("session_id")

if not token or not session_id:
    print("Token/session_id missing")
    exit()

print("Login successful")

# ---------------- TEMPLATE MIGRATION ---------------- #

template_url = "https://api.autongage.com/gryd/db/object/template"

template_headers = {
    "Content-Type": "application/json",
    "X-GRYD-ENTERPRISE-ID": "autocrm",
    "X-GRYD-TOKEN": token,
    "X-GRYD-SESSION-ID": session_id,
    "Accept": "application/json",
    "X-GRYD-ROLE": "agent"
}

for template in templates:

    template_name_lower = template["template_name"].lower()

    buttons = template.get("buttons", [])

    template["template_button_payloads"] = [
        f"{template_name_lower}-{btn['text'].lower().replace(' ', '_')}"
        for btn in buttons
    ]

    response = requests.post(
        template_url,
        headers=template_headers,
        json=template
    )

    print("\n---------------------------")
    print(f"Template: {template['template_name']}")
    print(f"Status: {response.status_code}")
    print(response.text)

print("\nTemplate migration completed successfully!")