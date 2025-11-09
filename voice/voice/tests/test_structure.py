"""Basic import tests for the voice package structure."""

import importlib


def test_imports():
    importlib.import_module('voice')
    importlib.import_module('voice.core')
    importlib.import_module('voice.input_manager')
    importlib.import_module('voice.output_manager')
    importlib.import_module('voice.agent')
    importlib.import_module('voice.orchestrator')
    importlib.import_module('voice.providers')
    importlib.import_module('voice.utils')
    importlib.import_module('voice.clients')
    importlib.import_module('voice.demo')
