import json
import sys
import os

from gryd_worker import gryd

# Configure service name
gryd.SERVICE = 'autocrm-agent'
gryd.set_queue_manager()

# Ensure root folder is added to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cron.cron import create_campaign_templates, update_template_status




worker_result = update_template_status(dealership_id="daveai")
print(json.dumps(worker_result, ensure_ascii=False, indent=2))
