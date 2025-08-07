import requests
import json
import os
enp_id=os.environ.get("CARDB_ENTERPRISE_ID")
user_id=os.environ.get("CARDB_USER_ID")
api_key=os.environ.get("CARDB_API_KEY")

def car_models(top_n,model=None,exclude=None):
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
    if model and exclude:
        url = f"https://test.iamdave.ai/objects/model_variant_analysis?model={model}&brand~={exclude}"
    elif model:
        url = f"https://test.iamdave.ai/objects/model_variant_analysis?model={model}"
    else:
        url = "https://test.iamdave.ai/objects/model_variant_analysis"

    headers = {
    'Content-Type': 'application/json',
    'X-I2CE-ENTERPRISE-ID': enp_id,
    'X-I2CE-USER-ID': user_id,
    'X-I2CE-API-KEY': api_key,
    }

    response = requests.request("GET", url, headers=headers)

    return json.loads(response.text)['data'][:top_n]

if __name__ == "__main__":
    print(car_models("DB11"))