import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import autocrm_validator
from config import AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_CORE_SERVICE_NAME, \
    gryd


gryd.SERVICE = AUTOCRM_CORE_SERVICE_NAME
gryd.set_queue_manager()
logger = gryd.hp.get_logger(gryd.SERVICE)


BillingModel = gryd.base_model.Model("billing", AUTOCRM_APP_ENTERPRISE_ID)

result = BillingModel.list(_as_option=True)

logger.info(result)