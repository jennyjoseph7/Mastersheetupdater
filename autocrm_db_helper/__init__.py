from contextlib import contextmanager
from collections.abc import Generator
import psycopg
from autocrm_db_helper.PGConnector import AutoCRMPGConnector
import time
from gryd_worker import gryd
import os

logger = gryd.hp.get_logger(__name__)

AUTOCRM_APP_ENTERPRISE_ID =  os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")


JOB_CONNECT = {}
@ contextmanager
def get_pg_connector(enterprise_id=AUTOCRM_APP_ENTERPRISE_ID, close_on_exit = True) -> Generator[AutoCRMPGConnector, None, None]:
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
        if not isinstance(JOB_CONNECT, dict):
            JOB_CONNECT = {}
        if enterprise_id not in JOB_CONNECT or getattr(JOB_CONNECT[enterprise_id], 'is_connected', False):
            t = time.time()
            ex = t + 120
            while time.time() < ex:
                try:
                    conn = AutoCRMPGConnector(enterprise_id)
                    if not close_on_exit:
                        JOB_CONNECT[enterprise_id] = conn
                except psycopg.errors.ConnectionTimeout as e:
                    logger.error("Connection timed out, trying again: %s", e)
                    time.sleep(5)
                else:
                    break
            logger.info("creating pg_con for enterprise {} in {} seconds".format(enterprise_id, time.time() - t))
        else:
            conn = JOB_CONNECT.get(enterprise_id)
        yield conn
    except Exception as e:
        gryd.hp.print_error(e)
        raise
    finally:
        if close_on_exit:
            logger.info("Closing connection")
            conn.close()
