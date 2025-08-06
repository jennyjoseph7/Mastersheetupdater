from gryd_worker import gryd
from utils import GRYD_SERVICE, GRYD_CONFIG, get_logger
import json

logger = get_logger(__name__)

gryd.SERVICE = GRYD_SERVICE
gryd.set_queue_manager(config = GRYD_CONFIG)
gryd.ENVIRONMENT = "-local"

sync_job = [{
            "task": "autobot_agents_trigger",
            "service": GRYD_SERVICE,
            "kwargs": {
                "source" : {
    "uuid": "123e4567-e89b-12d3-a456-426614174000",
    "name": "G. Gananth",
    "phone": "9980838165",
    "email": "ggananth@yahoo.com",
    "city": "Bengaluru",
    "pincode": "560103",
    "device": "laptop",
    "os": "MacOS",
    "interested_models": ["Grand Vitara"],
    "preferred_contact_time": "Evening",
    "lead_status": "Interested",
    "source": "website",
    "utm": {
      "source": "facebook",
      "medium": "ppc",
      "campaign": "monsoon_promotional_campaign",
      "term": "best budget suv",
      "content": "banner ad"
    }
},
                "execution_mode" : "async"
            },
            "args": (None)
    }]

sync_result = list(gryd.yield_results(sync_job))
logger.info(json.dumps(sync_result, indent = 4, default = str))
assert False