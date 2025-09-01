# from gryd_worker import gryd
# from utils import GRYD_SERVICE, GRYD_CONFIG, get_logger
# import json

# logger = get_logger(__name__)

# gryd.SERVICE = GRYD_SERVICE
# gryd.set_queue_manager(config = GRYD_CONFIG)
# gryd.ENVIRONMENT = "-local"

# async_job = [{
#     "task": "autobot_agents_trigger_generator",
#     "service": GRYD_SERVICE,
#     "kwargs": {
#         "source" : {
#             "uuid": "123e4567-e89b-12d3-a456-426614174000",
#             "name": "G. Gananth",
#             "phone": "9980838165",
#             "email": "ggananth@yahoo.com",
#             "city": "Bengaluru",
#             "pincode": "560103",
#             "device": "laptop",
#             "os": "MacOS",
#             "interested_models": ["Grand Vitara"],
#             "preferred_contact_time": "Evening",
#             "lead_status": "Interested",
#             "source": "website",
#             "utm": {
#               "source": "facebook",
#               "medium": "ppc",
#               "campaign": "monsoon_promotional_campaign",
#               "term": "best budget suv",
#               "content": "banner ad"
#             }
#         },
#       "execution_mode" : "async"
#     },
#     "args": (None)
# }]

# for job in gryd.yield_results(async_job):
#     task_name, status, result_data = job[1], job[3], job[4]
#     if job[3] == "result":
#         logger.info(f"Task '{task_name}' completed with result: \n\n{json.dumps(result_data, indent = 4, default = str)}")

# assert False

from agents.competitor_analysis_agent.main import CompetitorAnalysis

fp = "/home/prince-hazarika/Documents/DaveAI LLMs/autobot_agents_/autobot_agents/aem_mock_data/1.json"
comp_agent = CompetitorAnalysis(fp, model_identifier='azure-gpt-4o')
print(comp_agent.get_analysis())