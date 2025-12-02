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


class TwilioProvider(ProviderBase):
    """Twilio-specific provider implementation"""

    def __init__(self):
        super().__init__("Twilio")

    def parse_incoming(self, raw_message: Dict[str, Any]) -> dict:
        """Convert Twilio message to generic format"""
        msg_type = raw_message.get('event')
        if msg_type == 'start':
            return dict(
                message_type='stream_start',
                metadata={
                    'stream_sid': raw_message.get('streamSid'),
                    'call_sid': raw_message.get('callSid'),
                    'media_format': raw_message.get('mediaFormat', {}),
                    'custom_params': raw_message.get("customParameters", {})
                }
            )
            #stream_start, audio_input - in
            #audio_output, clear_buffer - out
            
        elif msg_type == 'media':
            # Twilio sends mulaw, convert to PCM16 for generic format
            audio_mulaw = raw_message.get('media',{}).get('payload')
            audio_pcm16 = self._mulaw_to_pcm16(audio_mulaw) if audio_mulaw else None

            return dict(
                message_type='audio_input',
                audio_data=audio_pcm16,
                metadata={
                    'stream_sid': raw_message.get('streamSid')
                }
            )
        else:
            # Unknown type, pass through
            return dict(
                message_type=msg_type or 'unknown',
                metadata=raw_message
            )

    def format_outgoing(self, generic_message: dict) -> Dict[str, Any]:
        """Convert generic format to Twilio message"""
        msg_type = generic_message.get('message_type')

        if msg_type == 'audio_output':
            # Convert PCM16 to mulaw for Twilio
            audio_mulaw = self._pcm16_to_mulaw(generic_message.get('audio_data')) if generic_message.get('audio_data') else None

            return {
                'event': 'media',
                'streamSid': generic_message.get('metadata').get('stream_sid'),
                'media':{
                    'payload': audio_mulaw
                }
            }

        elif msg_type == 'clear_buffer':
            return {
                'event': 'clear',
                'streamSid': generic_message.get('metadata').get('stream_sid')
            }

        elif msg_type == 'mark':
            return {
                'event': 'mark',
                'mark': generic_message.get('metadata').get('mark', 'default'),
                'streamSid': generic_message.get('metadata').get('stream_sid')
            }

        elif msg_type == 'end_stream':
            return {
                'event': 'stop',
                'streamSid': generic_message.get('metadata').get('stream_sid')
            }

        else:
            # Default passthrough
            return {
                'event': msg_type,
                **generic_message.get('metadata')
            }

    def _mulaw_to_pcm16(self, mulaw_b64: str) -> typing.Union[str, bytes]:
        """Convert base64 mulaw to base64 PCM16"""
        import base64
        import audioop

        mulaw_bytes = base64.b64decode(mulaw_b64)
        pcm_bytes = audioop.ulaw2lin(mulaw_bytes, 2)
        return pcm_bytes
        # return base64.b64encode(pcm_bytes).decode('utf-8')

    def _pcm16_to_mulaw(self, pcm16_b64: str) -> str:
        """Convert base64 PCM16 to base64 mulaw"""
        import base64
        import audioop

        pcm_bytes = base64.b64decode(pcm16_b64)
        mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)
        return base64.b64encode(mulaw_bytes).decode('utf-8')



def get_provider(provider_name: str) -> ProviderBase:
    """
    Factory function to get provider instance by name.

    Args:
        provider_name: Name of the provider ('twilio', 'vapi', etc.)

    Returns:
        ProviderBase: Provider instance
    """
    providers = {
        'twilio': TwilioProvider
    }

    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(providers.keys())}")

    return provider_class()
