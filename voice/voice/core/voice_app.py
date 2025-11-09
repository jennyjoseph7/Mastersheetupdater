"""Voice App core: orchestrates job handling, prompt generation and managers."""


class VoiceApp:
    """Placeholder for the Voice App orchestration class.

    Responsibilities (to implement):
    - receive jobs and classify type
    - generate dynamic prompts
    - create calls via providers
    - start/stop input & output managers
    """

    def __init__(self, provider=None, orchestrator=None):
        self.provider = provider
        self.orchestrator = orchestrator

    def start(self):
        """Start main loop (placeholder)."""
        raise NotImplementedError
