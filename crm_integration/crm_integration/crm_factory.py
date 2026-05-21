from connectors.google_docs_crm import GoogleDocsCRM


def CRMFactory(name):

    if name=="google":
        return GoogleDocsCRM(
           "CRM Demo"
        )

    raise Exception(
      "Unsupported CRM"
    )