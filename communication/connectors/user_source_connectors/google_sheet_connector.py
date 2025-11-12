#!/usr/bin/python
# -*- coding: utf-8 -*-
from connectors.user_source_connectors.source_connector import *
logger=hp.get_logger(__name__)
try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    logger.warning("⚠️ gspread or google-auth not installed. Run: pip install gspread google-auth")
    # raise Exception("⚠️ gspread or google-auth not installed. Run: pip install gspread google-auth")

class GoogleSheetsCampaignSource(CampaignSourceBase):
    """Fetch campaign users from a Google Sheet in batches."""

    def __init__(self, enterprise_id: str, campaign_id: str, campaign_detail_id: str, campaign_user_source: dict):
        super().__init__(enterprise_id, campaign_id, campaign_detail_id)

        config = campaign_user_source.get("config", {})
        self.sheet_id = config.get("sheet_id")
        self.worksheet_name = config.get("worksheet_name", "Sheet1")
        self.credentials_file = config.get("credentials_file", "google_creds.json")
        self.batch_size = config.get("batch_size", 100)
        self.field_mapping = campaign_user_source.get("field_mapping", {})

        # Initialize Sheets connection
        logger.info(f"Initializing Google Sheets connection for sheet_id={self.sheet_id}")

        creds = Credentials.from_service_account_file(
            self.credentials_file,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        client = gspread.authorize(creds)
        self.sheet = client.open_by_key(self.sheet_id).worksheet(self.worksheet_name)

        self.all_rows = self.sheet.get_all_records()
        self.total_rows = len(self.all_rows)
        logger.info(f"Google Sheet contains {self.total_rows} rows")

    def fetch_next_batch(self, batch_size: Optional[int] = None, **kwargs):
        """Fetch next batch of users from the Google Sheet."""
        batch_size = batch_size or self.batch_size

        # Determine starting point
        last_page = int(self.status.get("last_page", 0))
        start = last_page * batch_size
        end = start + batch_size

        if start >= self.total_rows:
            msg = f"✅ All rows processed for Google Sheet {self.sheet_id}"
            logger.info(msg)
            return {"error": True, "error_reason": msg, "_raise": True, "_raise_message": msg}

        data_batch = self.all_rows[start:end]

        # Apply field mapping if present
        if self.field_mapping:
            mapped_data = []
            for row in data_batch:
                mapped_row = dict(row)
                for target_key, source_key in self.field_mapping.items():
                    if source_key in row:
                        mapped_row[target_key] = row[source_key]
                mapped_data.append(mapped_row)
            data_batch = mapped_data

        # Update status
        self.status_model.patch(
            self.status_id,
            {"last_page": last_page + 1, "total_processed": end}
        )
        self.status = self.status_model.get(self.status_id)

        logger.info(f"[Campaign:{self.campaign_id}] Fetched {len(data_batch)} users from Google Sheets (page={last_page + 1})")

        return data_batch


# Register connector in factory
CampaignSourceFactory.register("google_sheets", GoogleSheetsCampaignSource)
