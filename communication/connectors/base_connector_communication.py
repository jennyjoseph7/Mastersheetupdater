from connectors.communication_helpers import *
# This triggers auto-registration for all the connectors
# import connectors.user_source_connectors 
# import communication.mail_connectors
# import connectors.whatsapp_connectors

from connectors.user_source_connectors.source_connector import CampaignSourceFactory
from connectors.whatsapp_connectors.source_connectors import WhatsappMessangerConnector, WhatsappReceiverConnector, BaseCampaingStatusUpdator,WhatsappCampaignTemplate
# from communication.mail_connectors.source_connector import MailSourceFactory

logger= hp.get_logger(__name__)
logger.info("---------------- Base Connector File Loaded------------------")

'''
This is the main Orchestration for all the communication medium

1.Whatsapp (Incomming message via Webhook And Incomming message from Converse)
    - Supported Whatsapp Provider
        1. Airtel
        2. Meta
        3. RML
        4. GupShup
        5. Concord (For Specific Project)
2.Email (For Sending Email Via Worker or API)
    - Supported Email Provider
        1. AWS
        2. SMTP
    
'''

