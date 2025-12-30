import os
from autocrm_db_helper import get_pg_connector
def load_stored_procedures():
    
    """
    Loads stored procedures from sql files in the same directory as this script.

    The files must end with ".sql" and will be loaded in alphabetical order.

    This function is intended to be used once during the setup of the app..
    """
    base_dir = os.path.dirname(__file__)

    for file in sorted(os.listdir(base_dir)):
        if not file.endswith(".sql"):
            continue

        path = os.path.join(base_dir, file)
        with open(path) as f:
            sql = f.read()

        print(f"[SP LOAD] {file}")
        with get_pg_connector() as pg:
            pg.execute_write(sql, _fetch=False)

    return
