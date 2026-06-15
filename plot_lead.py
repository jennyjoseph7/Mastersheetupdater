import json

from config import AutocrmModel
from autocrm_validator import plot_lead_session_history_func


# CAMPAIGN_ID = "ae334312-9c54-3e45-9a78-18f50634c257"
# LEAD_ID_FIELD = "post_sales_lead_id"


def main(campaign_id, lead_id_field ):
    lead_model = AutocrmModel("post_sales_lead")
    leads = list(lead_model.list(campaign_id=campaign_id, _as_option=True))

    if not leads:
        print(f"No post-sales leads found for campaign_id={campaign_id}")
        return

    print(f"Found {len(leads)} leads for campaign_id={campaign_id}")
    for lead in leads:
        lead_id = lead.get(lead_id_field) or lead.get("id")
        if not lead_id:
            print(f"Skipping lead without {lead_id_field}:", json.dumps(lead, default=str))
            continue

        timeline = plot_lead_session_history_func(ins=None, lead_attribute=lead_id)
        lead_model.update(lead_id, {"lead_timeline": timeline})
        print(f"{lead_id}: {timeline}")


if __name__ == "__main__":
    main()
