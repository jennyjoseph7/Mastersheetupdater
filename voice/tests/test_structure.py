"""Basic tests to ensure voice package structure imports cleanly."""


def test_imports():
    import importlib
    importlib.import_module('voice.core')
    importlib.import_module('voice.input_manager')
    importlib.import_module('voice.output_manager')
    importlib.import_module('voice.agent')
    importlib.import_module('voice.orchestrator')
    importlib.import_module('voice.providers')
    importlib.import_module('voice.utils')
    importlib.import_module('voice.clients')
