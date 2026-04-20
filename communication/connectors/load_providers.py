def load_providers(channel=None, provider_name=None):
    """
    Load connectors for a given channel.

    Args:
    channel (str or list): Channel name or list of channel names.
    provider_name (str): Name of the provider to load.

    Raises:
    ValueError: If channel or provider name is not supported.

    Returns:
    None
    """
    if isinstance(channel, list):
        for ch in channel:
            load_providers(ch)   # loading with default providers
        return

    if channel == "whatsapp":
        from .whatsapp_connectors.source_connectors import (
            WhatsappMessangerConnector,
            WhatsappReceiverConnector,
            WhatsappCampaignTemplate,
        )

        providers = {
            "airtel": lambda: _load_airtel(
                WhatsappMessangerConnector,
                WhatsappReceiverConnector,
                WhatsappCampaignTemplate,
            ),
            "twilio": lambda: _load_twilio(
                WhatsappMessangerConnector,
                WhatsappReceiverConnector,
                WhatsappCampaignTemplate,
            ),
        }

    elif channel == "email":
        from .mail_connectors.source_connector import (
            MailSourceFactory,
        )

        providers = {
            "awssender": lambda: _load_AwsSender(MailSourceFactory),
        }

    else:
        raise ValueError(f"Unsupported channel: {channel}")

    if provider_name:
        provider = provider_name.lower()
        loader = providers.get(provider)

        if not loader:
            raise ValueError(f"Unsupported provider: {provider_name}")

        loader()
    else:
        for loader in providers.values():
            loader()

def _load_airtel(
    WhatsappMessangerConnector,
    WhatsappReceiverConnector,
    WhatsappCampaignTemplate,
):
    print("Loading Airtel Connectors----")
    from connectors.whatsapp_connectors.airtel_connector import AirtelWebhookConverter,AirtelWhatsAppMessenger
    from connectors.whatsapp_connectors.campaign_airtel_template import AirtelCampaignManager

    WhatsappMessangerConnector.register("airtel", AirtelWhatsAppMessenger)
    WhatsappReceiverConnector.register("airtel", AirtelWebhookConverter)
    WhatsappCampaignTemplate.register("airtel",AirtelCampaignManager)
    
    
def _load_twilio(
    WhatsappMessangerConnector,
    WhatsappReceiverConnector,
    WhatsappCampaignTemplate,
):
    print("Loading Twilio Connectors----")
    from connectors.whatsapp_connectors.twilio_connector import TwilioWebhookConverter,TwilioWhatsAppMessenger
    from connectors.whatsapp_connectors.campaign_twilio_template import TwilioCampaignManager

    WhatsappMessangerConnector.register("twilio",TwilioWhatsAppMessenger)
    WhatsappReceiverConnector.register("twilio",TwilioWebhookConverter)
    WhatsappCampaignTemplate.register("twilio",TwilioCampaignManager)
    
def _load_AwsSender(MailSourceFactory):
    print("Loading Email Connectors----")
    
    from connectors.mail_connectors.aws_ses_mail import AwsSender

    MailSourceFactory.register("AwsSender", AwsSender)
    MailSourceFactory.register("__default__", AwsSender)