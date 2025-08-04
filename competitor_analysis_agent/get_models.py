import requests
import json
def car_models(model=None):
    """
    Get a list of car models
    Parameters
    ----------
    model : str
        name of the car model
    Returns
    -------
    str

        json string containing the list of car models
    """
    if model:
        url = f"https://test.iamdave.ai/objects/model_variant_analysis?model={model}"
    else:
        url = "https://test.iamdave.ai/objects/model_variant_analysis"

    payload = {}
    headers = {
    'Content-Type': 'application/json',
    'X-I2CE-ENTERPRISE-ID': 'automobile_service',
    'X-I2CE-USER-ID': 'ananth+automobile_service@i2ce.in',
    'X-I2CE-API-KEY': 'bcc85ca9-8695-31bd-9b5e-276859efa3ba',
    'Cookie': 'x-chkp-csrf-token=5819e602-f246-4bf5-92bd-5fef4bc8f517; x-chkp-csrf-token=21d90977-021c-409f-8d87-944647fcc5a4'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    return json.loads(response.text)['data']



if __name__ == "__main__":
    print(car_models("DB11"))