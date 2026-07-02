import os,json
from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
import sys

_connectors_dir = dirname(abspath(__file__))
_communication_dir = dirname(_connectors_dir)
_project_root = dirname(_communication_dir)
for path in (_project_root, _communication_dir):
    if path not in sys.path:
        sys.path.insert(0, path)

from connectors.communication_helpers import *
# logger.info(f"{gryd.__CUSTOM_MODULE__} Module Initialized Sucessfully")
