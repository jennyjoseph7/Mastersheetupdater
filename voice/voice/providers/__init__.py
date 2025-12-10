
import twilio


PROVIDERS = {
    'twilio': twilio
}

def get_provider(provider_name: str):
    """
    Factory function to get provider instance by name.

    Args:
        provider_name: Name of the provider ('twilio', 'vapi', etc.)

    Returns:
        ProviderBase: Provider instance
    """
  
    try:
        provider = PROVIDERS[provider_name.lower()]
    except KeyError:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(PROVIDERS.keys())}")

    return provider
