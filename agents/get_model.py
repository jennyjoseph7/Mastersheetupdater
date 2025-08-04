



import requests
import json
def get_model(brand=None, model=None, variant=None):
    url = f"https://test.iamdave.ai/objects/model_variant_analysis?brand={brand}"

    payload = {}
    headers = {
    'Content-Type': 'application/json',
    'X-I2CE-ENTERPRISE-ID': 'automobile_service',
    'X-I2CE-USER-ID': 'ananth+automobile_service@i2ce.in',
    'X-I2CE-API-KEY': 'bcc85ca9-8695-31bd-9b5e-276859efa3ba',
    'Cookie': 'x-chkp-csrf-token=5819e602-f246-4bf5-92bd-5fef4bc8f517; x-chkp-csrf-token=21d90977-021c-409f-8d87-944647fcc5a4'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    return (response.json)
