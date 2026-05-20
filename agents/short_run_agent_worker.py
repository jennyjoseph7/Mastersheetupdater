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
from campaign_idea_creator import gryd
