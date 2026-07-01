from os.path import dirname, abspath, join as joinpath
import sys


BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from crm_integration.crm_integration.connectors.google_docs_crm import GoogleDocsCRM
from crm_integration.crm_integration.connectors.salesforce_crm import SalesforceCRM
# from crm_integration.connectors.autounify_crm import AutoUnifyCRM
# from crm_integration.connectors.leadsquare_crm import LeadSquaredCRM

def load_crm(crm_name, credentials=None, sheet_name=None, sheet_url=None):

    crm_map={

      "googledocs":
        lambda: GoogleDocsCRM(
            #  credentials=credentials,       
            sheet_url=sheet_url,           
            sheet_name=sheet_name      
         ),

      "salesforce":
        lambda: SalesforceCRM(
            credentials=credentials or {}
        )

      # "leadsquared":
      #    lambda: LeadSquaredCRM(),

      # "tekion":
      #    lambda: AutoUnifyCRM(
      #       crm_name="tekion"
      #    ),

      # "cdk":
      #    lambda: AutoUnifyCRM(
      #       crm_name="cdk"
      #    )

    }

    if crm_name not in crm_map:
       raise ValueError(
           f"{crm_name} unsupported"
       )

    return crm_map[crm_name]()