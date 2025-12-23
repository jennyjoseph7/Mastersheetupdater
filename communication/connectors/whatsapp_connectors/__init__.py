
import importlib
import pkgutil
from collections import abc
from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
import sys
sys.path.insert(0, dirname(dirname(abspath(__file__))))
from connectors.communication_helpers import *
from gryd_worker import gryd_helpers as hp
logger=gryd.logger

for _, module_name, _ in pkgutil.iter_modules(__path__):
    # logger.info(f"TEST connector module: {module_name}")
    if module_name not in ["source_connector"]:
        importlib.import_module(f"{__name__}.{module_name}")
        logger.info(f"✅ Auto-imported connector module: {module_name}")