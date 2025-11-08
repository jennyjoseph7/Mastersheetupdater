


from contextlib import contextmanager
from collections.abc import Generator
from PGConnector import AutoCRMPGConnector
import time
from gryd_worker import gryd

logger = gryd.hp.get_logger(__name__)
@ contextmanager
def get_pg_connector(enterprise_id, close_on_exit = True) -> Generator[AutoCRMPGConnector, None, None]:
    """
    Context manager to get a job connector for a specific enterprise.

    This function checks if a job connector for the given enterprise ID already exists.
    If not, it creates a new instance of GrydCronConnector. It yields the connector
    for use within a context and ensures that the connector is closed after use.

    Parameters:
    enterprise_id (str): The ID of the enterprise for which to get the job connector.

    Yields:
    GrydCronConnector: The job connector for the specified enterprise.
    """
    global JOB_CONNECT
    try:
        if not enterprise_id:
            enterprise_id = "autobotcrm"
        if not JOB_CONNECT.get(enterprise_id):
            t = time.time()
            JOB_CONNECT[enterprise_id] = gryd.db.(enterprise_id)
            logger.info("creating pg_con for enterprise {} in {} seconds".format(enterprise_id, time.time() - t))
        yield JOB_CONNECT[enterprise_id]
    except Exception as e:
        gryd.hp.print_error(e)
        raise
    finally:
        if close_on_exit and (enterprise_id in JOB_CONNECT):
            JOB_CONNECT[enterprise_id].close()
            JOB_CONNECT.pop(enterprise_id, None)
