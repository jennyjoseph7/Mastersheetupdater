import json
import os
import sys
from typing import Any

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def transform_template_records(input_file: str, output_file: str) -> None:
    def normalize_campaign_objective(value: Any) -> str:
        if isinstance(value, list):
            return value[0] if value else ""
        if value is None:
            return ""
        return str(value)

    def split_disposition_tags(tags: Any) -> tuple[str, str | None]:
        if not isinstance(tags, list) or not tags:
            return "", None

        disposition = str(tags[0]).strip() if len(tags) >= 1 else ""
        disposition_details = str(tags[1]).strip() if len(tags) >= 2 else None

        return disposition, disposition_details

    with open(input_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError("Input JSON must contain a list of records.")

    transformed_records = []

    for record in records:
        if not isinstance(record, dict):
            transformed_records.append(record)
            continue

        new_record = record.copy()

        new_record["campaign_objective"] = normalize_campaign_objective(
            new_record.get("campaign_objective")
        )

        tags = new_record.get("disposition_tags")

        if isinstance(tags, list) and tags:
            disposition, disposition_details = split_disposition_tags(tags)

            if disposition:
                new_record["disposition"] = disposition

            if disposition_details:
                new_record["disposition_details"] = disposition_details

        new_record.pop("disposition_tags", None)

        transformed_records.append(new_record)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(transformed_records, f, indent=4, ensure_ascii=False)

    print(f"Transformed {len(transformed_records)} records and saved to {output_file}")



transform_template_records(
    os.path.join(PROJECT_ROOT, "templates.json"),
    os.path.join(PROJECT_ROOT, "templates_updated.json"),
)