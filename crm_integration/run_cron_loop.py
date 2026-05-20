import time

from crm_integration.cron import sync_crm_campaigns

while True:
    print("\n===== RUNNING CRM CRON =====\n")

    try:
        result = sync_crm_campaigns(batch_size=3)
        print(result)

    except Exception as e:
        print("CRON ERROR:", e)

    print("\n===== WAITING 20 MINUTES =====\n")

    time.sleep(20 * 60)

