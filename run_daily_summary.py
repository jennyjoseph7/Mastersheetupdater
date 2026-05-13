from autocrm_db_helper import get_pg_connector

def run_summary():
    print("Running update_daily_dealership_summary...")
    with get_pg_connector() as pg:
        pg.execute_write("CALL update_daily_dealership_summary();", _fetch=False)
    print("Done!")

if __name__ == "__main__":
    run_summary()
