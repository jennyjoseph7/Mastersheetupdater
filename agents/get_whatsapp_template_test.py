from gryd_worker import gryd
import sys, os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.whatsapp_template_agents.get_whatsapp_template_agent import get_whatsapp_template

# result = response = gryd.await_result(
#     task="get_disposition_template",
#     service="autocrm-short-run-agent",
#     kwargs={
#         #"lead_id": "vandana-8401586512-daveai-1825982b-baae-3c0e-b59e-a8e2b2e80484",
#         "lead_id": "test-8277676778-test@iamdave.ai-dave-ai-us-india-428604e5-a04e-37ca-8c7c-26f0c4082d28",
#         "campaign_objective_id": "pre-sales-test-drive-booking",
#         #"disposition": "engaged",
#         #"disposition_details": "Will decide after 90 days",
#         "dealership_id": "dave-ai-us-india",
#         "language": "English",
#     }
# )


result = response = gryd.await_result(
    task="get_whatsapp_template",
    service="autocrm-short-run-agent",
    kwargs={
 #"lead_id": "vandana-8401586512-daveai-1825982b-baae-3c0e-b59e-a8e2b2e80484",
        "lead_id": "test-8277676778-test@iamdave.ai-dave-ai-us-india-428604e5-a04e-37ca-8c7c-26f0c4082d28",
        "campaign_objective_id": "pre-sales-test-drive-booking",
        #"disposition": "engaged",
        #"disposition_details": "Will decide after 90 days",
        "dealership_id": "dave-ai-us-india",
        "language": "English",
    }
)

print(result)
# [{'sender': '919187210940', 'status': 'approved', 'buttons': [{'text': 'Book A Test Drive', 'type': 'QUICK_REPLY'}, {'text': 'Request A Callback', 'type': 'QUICK_REPLY'}, {'text': 'Request a Call Back', 'type': 'QUICK_REPLY'}], 'channel': 'whatsapp_chat', 'created': 1781604404.7416213, 'updated': 1781604404.7426858, 'language': 'english', 'lead_tags': ['test-drive-interested', 'follow-up', 'high-intent'], 'dealer_name': 'Stellantis- Jeep', 'disposition': 'engaged', 'region_name': 'South India', 'search_term': 'autobot_90day_drive_followup_will-decide-after-90-days text english pre-sales test drive booking we connected a while ago and the time you needed to decide has passed. now is a great time to move forward—experience the comfort smooth performance and smart features in person. book your slot today', 'template_id': '01kv7yb9aa4e7k8g0crdwd5ae3', 'campaign_type': 'pre-sales', 'dealership_id': 'stellantis--jeep-india', 'provider_name': 'Airtel', 'template_name': 'autobot_90day_drive_followup_will-decide-after-90-days', 'template_type': 'text', 'disposition_tags': ['engaged', 'will-decide-after-90-days'], 'template_message': 'We connected a while ago, and the time you needed to decide has passed. Now is a great time to move forward—experience the comfort, smooth performance, and smart features in person. Book your slot today!', 'campaign_objective': ['Test Drive Booking'], 'template_variables': [], 'disposition_details': 'will-decide-after-90-days', 'campaign_objective_name': 'Test Drive Booking', 'template_button_payloads': ['autobot_90day_drive_followup-book_a_test_drive', 'autobot_90day_drive_followup-request_a_callback', 'autobot_90day_drive_followup-request_a_call_back'], 'communication_credentials_id': 'airtel-whatsapp_chat-919187210940'}]
