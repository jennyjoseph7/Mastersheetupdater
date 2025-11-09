"""Input Manager: handles incoming audio, response_id generation and queueing."""

from queue import Queue
import uuid


class InputManager:
    def __init__(self, request_queue: Queue):
        self.request_queue = request_queue

    def push_input(self, audio_payload: str) -> str:
        """Create a response_id for the incoming audio and enqueue it.

        Returns the created response_id.
        """
        response_id = str(uuid.uuid4())
        self.request_queue.put({"response_id": response_id, "audio": audio_payload})
        return response_id
