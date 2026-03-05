import os
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
AGENT_DIR = dirname(abspath(__file__))
if AGENT_DIR not in sys.path:
    sys.path.append(AGENT_DIR)
try:
    from .base_agent import BaseAgent, gryd
except ImportError:
    from base_agent import BaseAgent, gryd
import whatsapp_template_creator_agent
import get_whatsapp_template_agent
