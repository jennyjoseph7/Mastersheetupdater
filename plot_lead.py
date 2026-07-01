import json

from config import AutocrmModel
from autocrm_validator import plot_lead_session_history_func


def main(campaign_id, lead_type):
    model_name = f"{lead_type}_lead"
    lead_id_field = f"{lead_type}_lead_id"

    lead_model = AutocrmModel(model_name)
    leads = list(lead_model.list(campaign_id=campaign_id, _as_option=True))

    if not leads:
        print(f"No leads found for campaign_id={campaign_id}")
        return

    print(f"Found {len(leads)} leads for campaign_id={campaign_id}")

    for lead in leads:
        lead_id = lead.get(lead_id_field) or lead.get("id")

        if not lead_id:
            print(f"Skipping lead without {lead_id_field}:")
            print(json.dumps(lead, default=str))
            continue

        timeline = plot_lead_session_history_func(
            ins=None,
            lead_attribute=lead_id
        )

        lead_model.update(lead_id, {"lead_timeline": timeline})
        print(f"{lead_id}: {timeline}")


if __name__ == "__main__":
    main("addceeb8-b6ae-3568-b95b-32aa8189ff29", "pre_sales")
    # main("1803639a-d9e0-31cb-a799-c79df03313b3", "pre_sales")