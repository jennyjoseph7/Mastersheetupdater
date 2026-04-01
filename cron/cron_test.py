import json
import sys
import os
#python -m cron.cron_test


from gryd_worker import gryd

# Configure service name
gryd.SERVICE = 'autocrm-agent'
gryd.set_queue_manager()

# Ensure root folder is added to path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from cron.cron import create_campaign_templates, update_template_status




worker_result = update_template_status(dealership_id="daveai")
print(json.dumps(worker_result, ensure_ascii=False, indent=2))
