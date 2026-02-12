
from communication_helpers import *


class RCSConnectorBase:
    """Abstract base for all RCS providers."""

    provider_name = "base"

    def __init__(self, credentials: Dict[str, Any]):
        self.credentials = credentials

    def send_rcs(self, to_number: str, message: str, **kwargs) -> Dict[str, Any]:
        """Send an RCS message — must be implemented by providers."""
        raise NotImplementedError("send_rcs must be implemented by subclass")

    def format_response(self, status: str, provider_response: Any) -> Dict[str, Any]:
        """Standardize RCS response."""
        return {
            "provider": self.provider_name,
            "status": status,
            "response": provider_response
        }