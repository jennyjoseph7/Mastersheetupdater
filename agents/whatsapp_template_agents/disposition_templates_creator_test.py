from gryd_worker import gryd
import sys, os

# agents/whatsapp_template_agents/<this file> → up three levels = project root
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.whatsapp_template_agents.disposition_templates_creator import (
    create_disposition_templates,
)

# disposition / disposition_details are taken from input and stored as-is on
# each created template. "language barrier" triggers translation of existing
# approved templates; "converted" generates per-variable-set templates; any
# other disposition_details (e.g. "not interested - price concern") generates
# follow-up templates tailored to that disposition.
result = gryd.await_result(
    task="create_disposition_templates",
    service="autocrm-agent",
    kwargs={
        "campaign_objective_id": "post-sales-free-service-due-reminder-ambal-auto-south-india",
        "disposition": "engaged",
        "disposition_details": "language barrier",
        "dealership_id": "daveai",
        "languages": ["Assamese"],
        # "communication_credential_id": "airtel-whatsapp_chat-917795030574",
    },
)

# template_ids = ["01kt3z7tz57x60pret74551r95", "01kt3z80zbzjyeetpz52t28fvr"]
# cred_id = "airtel-whatsapp_chat-917795030574"
# result = gryd.await_result(
#     task="update_disposition_template_approval",
#     service="autocrm-agent",
#     kwargs={
#         "template_ids": template_ids,
#         "communication_credentials_id": cred_id,
#     },
# )
print(result)
