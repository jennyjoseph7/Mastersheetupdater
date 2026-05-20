from crm_integration.connectors.google_docs_crm import GoogleDocsCRM
from crm_integration.connectors.salesforce_crm import SalesforceCRM
# from crm_integration.connectors.autounify_crm import AutoUnifyCRM
# from crm_integration.connectors.leadsquare_crm import LeadSquaredCRM


def load_crm(crm_name, credentials=None, sheet_name=None):

    crm_map={

      "googledocs":
         lambda: GoogleDocsCRM(
             sheet_name=sheet_name or "Ambal Sanganur Post-sales"
         ),

      "salesforce":
         lambda: SalesforceCRM(
             credentials=credentials or {}
         ),

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