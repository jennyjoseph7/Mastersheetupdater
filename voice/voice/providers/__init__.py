
from . import twilio
from . import elevanlabs_tatatele
from . import elevanlab
import requests

PROVIDERS = {
    'twilio': twilio,
    'tatatele': elevanlabs_tatatele,
    'elevanlab': elevanlab,
}

PROVDER_RESPONSE_FORMAT = {
    "twilio": {
        "call_sid": "sid",
        "message": "message", 
        "success": "success"
    },
    "tatatele": {
        "call_sid": "ref_id",
        "message": "message",
        "success": "success",
    },
    "elevanlab": {
        "call_sid": "call_sid",
        "message": "message",
        "success": "success",
    },
}



def get_provider(provider_name: str):
    """
    Factory function to get provider instance by name.

    Args:
        provider_name: Name of the provider ('twilio', 'tatatele', etc.)

    Returns:
        ProviderBase: Provider instance
    """
  
    try:
        provider = PROVIDERS[provider_name.lower()]
    except KeyError:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(PROVIDERS.keys())}")

    return provider

def make_call(provider_name: str, payload:dict,  *args, **kwargs):
    """
    Make a call using the specified provider.
    Specific provider function should be defined as make_call_<provider_name>
    e.g. def make_call_tatatele(payload, *args, **kwargs):
            #implementation
    """
    provider = get_provider(provider_name)
    func = getattr(provider, f'make_call_{provider_name.lower()}')

    if not func:
        raise NotImplementedError(f"make_call not implemented for provider: {provider_name}")
    
    if not callable(func):
        raise NotImplementedError(f"make_call not implemented for provider: {provider_name}")

    r =  func(payload, *args, **kwargs)
    return {
        "call_sid": r.get(PROVDER_RESPONSE_FORMAT[provider_name]["call_sid"]),
        "message": r.get(PROVDER_RESPONSE_FORMAT[provider_name]["message"]),
        "success": r.get(PROVDER_RESPONSE_FORMAT[provider_name]["success"]),
    }



