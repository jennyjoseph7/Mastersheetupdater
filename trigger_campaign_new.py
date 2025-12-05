# from communication.connectors.campaign_manager import trigger_campaign

# from communication.connectors.connector_whatsapp import trigger_campaign
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from campaign.campaign_worker import trigger_campaign
if __name__ == "__main__":
    
    # trigger_campaign("pre-sales","63d8d5e1-640b-363f-bbe4-e298772149c8")
    trigger_campaign("post-sales","626952a0-1ac7-3a7c-85aa-c46d30897ea4")
