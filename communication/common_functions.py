
import uuid
import json
from gryd_worker import gryd, gryd_helpers as hp,gryd_db_helper as db
logger=gryd.logger
from autocrm_db_helper import get_pg_connector

def generate_uid(data):
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data, sort_keys=True)
    else:
        data_str = str(data)

    uid = uuid.uuid3(uuid.NAMESPACE_DNS, data_str)
    return str(uid)


def get_communication_credential(dealership_id="daveai", channel=None, provider_name=None):
    logger.info(f"Getting communication credential for dealership - {dealership_id}")

    if not channel:
        logger.info(
            f"Channel not provided for dealership - {dealership_id}. Returning None."
        )
        return None
    _k={"dealership_id": dealership_id, "channel": channel,"provider_name":provider_name}
    _kwargs={k: v for k, v in _k.items() if v is not None}
    with get_pg_connector() as pg:
        creds = list(pg.list("communication_credential",_kwargs))
        if creds:
            return creds[0]

        # Fallback to default dealership "daveai" if no creds found for the dealership and channel
        if dealership_id != "daveai":
            logger.info(
                f"No credential found for dealership - {dealership_id}. "
                f"Falling back to default dealership - daveai for channel - {channel}"
            )
            creds = list(
                pg.list(
                    "communication_credential",
                    {"dealership_id": "daveai", "channel": channel}
                )
            )
            if creds:
                return creds[0]

    return None
   