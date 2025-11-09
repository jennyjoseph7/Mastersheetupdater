"""Output Manager: polls response queue and sends chunks to provider (placeholder)."""

from queue import Queue


class OutputManager:
    def __init__(self, response_queue: Queue):
        self.response_queue = response_queue

    def collect_for_response(self, response_id: str):
        """Collect chunks for a given response_id. Placeholder implementation."""
        collected = []
        while not self.response_queue.empty():
            item = self.response_queue.get()
            if item.get("response_id") == response_id:
                collected.append(item.get("chunk"))
        return "".join(collected)
