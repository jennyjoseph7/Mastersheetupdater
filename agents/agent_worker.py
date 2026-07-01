import os
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
AGENT_DIR = dirname(abspath(__file__))
if AGENT_DIR not in sys.path:
    sys.path.insert(1, AGENT_DIR)
try:
    from .base_agent import BaseAgent, gryd
except ImportError:
    from base_agent import BaseAgent, gryd
THREADS_PER_SESSION = 0.1
__version__ = "0.0.1"
import whatsapp_template_agents.whatsapp_template_creator_agent
import whatsapp_template_agents.disposition_templates_creator
import whatsapp_template_agents.disposition_template_approval_updator
import get_disposition_template
import whatsapp_template_agents.template_status_update
import whatsapp_template_agents.bulk_send_for_approval
import whatsapp_template_agents.bulk_template_creator
import whatsapp_template_agents.edit_template
