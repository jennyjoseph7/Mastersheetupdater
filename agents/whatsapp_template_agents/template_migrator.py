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
                "text": "Book Service",
                "type": "QUICK_REPLY"
            },
            {
                "text": "Request a Call Back",
                "type": "QUICK_REPLY"
            }
        ],
        "campaign_objective_name": "whatsApp service reminder(perfect riders)",
        "campaign_type": "post-sales",
        "channel": "whatsapp_chat",
        "communication_credentials_id": "rml-whatsapp_chat-919187238016",
        "language": "english",
        "status": "approved",
        "template_id": "2194575164714900",
        "template_message": """Hi {{person_name}},
Your {{vehicle_model}} registration number {{reg_number}} is due for service before {{next_service_due}}. May I book a service appointment for you?""",
        "template_name": "perfect_riders_india_service_booking_reminder",
        "template_type": "text",
        "template_variables": ["person_name", "vehicle_model", "reg_number", "next_service_due"],
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