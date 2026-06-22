from gryd_worker import gryd
import sys, os

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.whatsapp_template_agents.bulk_send_for_approval import (
    bulk_send_templates_for_approval,
)
from agents.whatsapp_template_agents.edit_template import edit_template

# A single bulk call submits a mixed batch of template types for approval and
# returns the list of Airtel templateId(s).
result = gryd.await_result(
    task="bulk_send_templates_for_approval",
    service="autocrm-agent",
    kwargs={
        "dealership_id": "perfect-riders-india",
        "campaign_objective_id": "post-sales-whatsapp-service-reminder-perfect-riders-perfect-riders-india",
        "templates": [
            # Static text body
            # {
            #     "template_name": "autobot_bulk_static_demo",
            #     "template_message": "Great Indian Festival is now live.",
            #     "language": "English",
            # },
            # # Text body with variables
            # {
            #     "template_name": "autobot_bulk_variables_demo",
            #     "template_message": "Hey {{person_name}}, your {{car_model}} test drive is ready to book!",
            #     "language": "English",
            #     "buttons": [
            #         {"type": "QUICK_REPLY", "text": "Book Test Drive"},
            #         {"type": "QUICK_REPLY", "text": "Request a Call Back"},
            #     ],
            # },
            # # Header - body - footer
            # {
            #     "template_name": "autobot_bulk_header_footer_demo",
            #     "header": "Exclusive Offer",
            #     "template_message": "Hi {{person_name}}, grab special benefits on your next visit.",
            #     "footer": "Grab offers",
            #     "language": "English",
            #     "buttons": [
            #         {"type": "QUICK_REPLY", "text": "Know More"},
            #     ],
            # },
            # # Media template (URL based, not id based)
            # {
            #     "template_name": "autobot_bulk_media_demo",
            #     "template_message": "Hi {{person_name}}, check out our latest arrivals!",
            #     "footer": "Visit us today",
            #     "language": "English",
            #     "media_type": "image",
            #     "media_url": "https://upload.wikimedia.org/wikipedia/commons/f/f5/Lotus_flower_%28978659%29.jpg",
            #     "buttons": [
            #         {"type": "QUICK_REPLY", "text": "Book Test Drive"},
            #     ],
            # },
            {
                "dealership_id" : "perfect-riders-india",
                "template_name": "perfect_riders_india_service_booking_reminder",
                "template_message": """Hi {{person_name}},
Your {{car_model}} registration number {{reg_number}} is due for service before {{service_due_date}}. May I book a service appointment for you?""",
                "language": "English",
                "buttons": [
                    {"type": "QUICK_REPLY", "text": "Book Service"},
                    {"type": "QUICK_REPLY", "text": "Request a Call Back"},
                ],
                
            }
        ],
    },
)

print(result)


# Edit an existing template: input is the updated template with template_id inside.
# edit_result = gryd.await_result(
#     task="edit_template",
#     service="autocrm-agent",
#     kwargs={
#         "template": {
#             "template_id": "01j6rmpxaypjmrv3pe5n4naqdp",
#             "template_name": "autobot_bulk_variables_demo",
#             "template_message": "Hey {{person_name}}, your {{car_model}} test drive slot is confirmed!",
#             "language": "English",
#             "buttons": [
#                 {"type": "QUICK_REPLY", "text": "Reschedule"},
#                 {"type": "QUICK_REPLY", "text": "Request a Call Back"},
#             ],
#         }
#     },
# )
# print(edit_result)
