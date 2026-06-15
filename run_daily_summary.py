from autocrm_db_helper import get_pg_connector
from analytics.loader import load_stored_procedures

def run_summary():
    print("Loading stored procedures...")
    load_stored_procedures()
    print("Running update_daily_dealership_summary...")
    with get_pg_connector() as pg:
        pg.execute_write("CALL update_daily_dealership_summary();", _fetch=False)
    print("Done!")

if __name__ == "__main__":
    run_summary()
