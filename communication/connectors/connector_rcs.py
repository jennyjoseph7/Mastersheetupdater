import os,json
from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
import sys
sys.path.insert(0, dirname(dirname(abspath(__file__))))
from communication.connectors.communication_helpers import *
from communication.connectors.rcs_connectors.source_connector import RCSMessengerConnector
from config import AUTOCRM_COMMUNICATION_SERVICE_NAME,EMAIL_PROVIDER_NAME,EMAIL_SENDER_NAME,AUTOCRM_APP_ENTERPRISE_ID
from gryd_worker import gryd, gryd_db_helper as db, gryd_helpers as hp
gryd.SERVICE = AUTOCRM_COMMUNICATION_SERVICE_NAME
gryd.set_queue_manager()
logger = gryd.hp.get_logger(gryd.SERVICE)

# # PDF generation
# def make_pdf(html: str, path: str) -> str | None:
#     try:
#         output_path = Path(path)
#         pdfkit.from_string(html, str(output_path))
#         logger.info(" PDF generated at: %s", output_path)
#         return str(output_path)
#     except Exception as e:
#         logger.error(" Error generating PDF: %s", e)
#         hp.print_error()
#         return None



@gryd.is_a_task(function_name="receive_converse_response_rcs")
def receive_converse_response_rcs(*args,**kwargs):
    logger.info(f"Received Converse Response with args :{args}")
    logger.info(f"Received Converse Response with kwargs :{json.dumps(kwargs,indent=4)}")
    temp_data=kwargs.get("temporary_data",{})
    user_data=temp_data.get("user_details",{})
    provider=user_data.get("provider","twilio")
    message_sent_at= temp_data.get("message_sent_at",0)

    if message_sent_at:
        logger.info(f"\n****Received Converse response at ** : {time.time()-float(message_sent_at)}")
    

    logger.info(f"_register :: {RCSMessengerConnector._registry}")
    if provider.lower() in RCSMessengerConnector._registry:
        logger.debug("Processing RCS Connector")
        gryd_send_rcs(provider,user_data.get("mobile_number"),user_data.get("to"),kwargs.get("response",{}).get("placeholder"),**kwargs)
        return 
    logger.error("No RCS Provider found in receive_converse_response")
    return

@gryd.is_a_task(function_name="process_rcs_webhook")
def process_rcs_webhook(*args, **kwargs):
    provider=kwargs.get("provider","twilio")
    
    # logger.info(f"_register :: {RCSMessengerConnector._registry}")
    if provider.lower() in RCSMessengerConnector._registry:
        logger.debug("Processing RCS Connector")
        provider=RCSMessengerConnector.get_provider(provider)
        res=provider.process_rcs_webhook(*args, **kwargs)
        return res
    logger.error("No RCS Provider found in receive_converse_response")
    return

@gryd.is_a_task(function_name="get_rcs_status")
def get_rcs_status(*args, **kwargs):
    provider=kwargs.get("provider","twilio")
    
    # logger.info(f"_register :: {RCSMessengerConnector._registry}")
    if provider.lower() in RCSMessengerConnector._registry:
        logger.debug("Processing RCS Connector")
        provider=RCSMessengerConnector.get_provider(provider)
        res=provider.get_rcs_status(*args, **kwargs)
        return res
    logger.error("No RCS Provider found in receive_converse_response")
    return

@gryd.is_a_task(function_name="gryd_send_rcs")
def gryd_send_rcs(*args, **kwargs):
    """
    Send a message via RCS (Rich Communication Services) and calling respective provider.
    """
    provider = args[0]
    try:
        rcs_sender= RCSMessengerConnector.get_provider(provider)
        logger.info("Preparing to send RCS via provider: %s", provider)
        response=rcs_sender.send_rcs(
            to_number=args[1],
            from_number=args[2],
            message=args[3]
        )
        logger.info(" RCS sent. Response: %s", response)
        return {
            "response": response,
        }
    except Exception as e:
        logger.error("Error sending RCS: %s", e)
        return {
            "provider": provider,
            "error": str(e),
            "status": "error"
        }
    
if __name__=="__main__":
    pass