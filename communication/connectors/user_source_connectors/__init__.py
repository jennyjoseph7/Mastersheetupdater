
import importlib
import pkgutil
from collections import abc
from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
import sys
_connectors_dir = dirname(dirname(abspath(__file__)))
_communication_dir = dirname(_connectors_dir)
_project_root = dirname(_communication_dir)
for path in (_project_root, _communication_dir):
    if path not in sys.path:
        sys.path.insert(0, path)
from connectors.communication_helpers import *
from gryd_worker import gryd_helpers as hp
logger=hp.get_logger(__name__,level=hp.logging.DEBUG)
# from . import default_connector
for _, module_name, _ in pkgutil.iter_modules(__path__):
    if module_name not in ["source_connector","base_connector"]:
        importlib.import_module(f"{__name__}.{module_name}")
        logger.info(f"✅ Auto-imported connector module: {module_name}")