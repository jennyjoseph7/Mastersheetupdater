from connectors.communication_helpers import *

from connectors.user_source_connectors.source_connector import CampaignSourceFactory
from connectors.whatsapp_connectors.source_connectors import WhatsappMessangerConnector, WhatsappReceiverConnector, BaseCampaingStatusUpdator,WhatsappCampaignTemplate

from gryd_worker import gryd, gryd_helpers as hp
logger=gryd.logger
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

