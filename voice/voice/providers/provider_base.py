import typing
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import utils

logger =  utils.get_logger(__name__)


class ProviderBase(ABC):
    """
    Base class for all voice providers (Twilio, Vapi, etc.).
    Handles conversion between provider-specific format and generic format.
    """

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        logger.info(f"Initialized {provider_name} provider")

    @abstractmethod
    def parse_incoming(self, raw_message: Dict[str, Any]) -> dict:
        """
        Convert provider-specific incoming message to generic format.

        Args:
            raw_message: Raw message from the provider

        Returns:
            GenericMessage: Standardized message for voice agent
        """
        pass

    @abstractmethod
    def format_outgoing(self, generic_message: dict) -> Dict[str, Any]:
        """
        Convert generic format to provider-specific outgoing message.

        Args:
            generic_message: Generic message from voice agent

        Returns:
            Dict: Provider-specific formatted message
        """
        pass

    def receive_message(self, raw_message: Dict[str, Any]) -> dict:
        """
        Public method to receive and convert incoming message.
        Used by InputManager.
        """
        logger.info(f"[{self.provider_name}] Receiving message: {raw_message.get('type', 'unknown')}")
        return self.parse_incoming(raw_message)

    def send_message(self, generic_message: dict) -> Dict[str, Any]:
        """
        Public method to convert and send outgoing message.
        Used by OutputManager.
        """
        logger.info(f"[{self.provider_name}] Sending message type: {generic_message.get('message_type')}")
        return self.format_outgoing(generic_message)

