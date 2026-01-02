def load_providers(provider_name=None):
    from .source_connectors import (
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
        # "rml": lambda: _load_rml(
        #     WhatsappMessangerConnector,
        #     WhatsappReceiverConnector,
        #     WhatsappCampaignTemplate,
        # ),
    }

    if provider_name:
        print("provider_name---",provider_name)
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
    
    
    
