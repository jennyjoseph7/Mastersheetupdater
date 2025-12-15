#!/usr/bin/python
# -*- coding: utf-8 -*-
# from connectors.user_source_connectors.source_connector import CampaignSourceBase,CampaignSourceFactory

from connectors.user_source_connectors.source_connector import *
from typing import Optional
from gryd_worker import gryd, gryd_db_helper as db, gryd_helpers as hp
import json
import requests
logger=hp.get_logger(__name__)

# ---------------- API SOURCE ----------------
class I2CEAPICampaignSource(CampaignSourceBase):
    """Fetch campaign users from an external API with pagination, retry policy, and field mapping."""

    def __init__(self, enterprise_id: str, campaign_details_data:dict, campaign_user_source: dict):
        # Config
        config = campaign_user_source.get("config", {})
        self.api_url = campaign_user_source.get("connection",{}).get("endpoint")
        self.api_headers = campaign_user_source.get("connection",{}).get("headers")
        self.default_batch_size = config.get("batch_size", 100)
        self.default_filters = config.get("filters", {}).copy()
        self.field_mapping = campaign_user_source.get("field_mapping", {})
        self.retry_policy = config.get("retry_policy", {"max_retries": 3, "backoff": "exponential"})
        self.method = config.get("method", "GET").upper()
        self.params_key = config.get("params_key", "_page")  # Optional if your API uses ?_page=X
        self.campaign_id=campaign_details_data.get("campaign_id")
        self.campaign_detail_id= campaign_details_data.get("campaign_detail_id")
        max_per_day = config.get("max_per_day") or campaign_details_data.get("max_per_day")
        super().__init__(enterprise_id, campaign_details_data, max_per_day=max_per_day)

    def fetch_next_batch(self, batch_size: Optional[int] = None, api_params: Optional[dict] = None):
        batch_size = batch_size or self.default_batch_size
        api_params = api_params or self.default_filters.copy()

        # Check rate limits
        limit_block = self._check_rate_limits()
        if limit_block:
            return limit_block

        last_page = int(self.status.get("last_page", 0))
        page = last_page + 1
        api_params["_page"] = page
        api_params["_page_size"] = batch_size
        api_params["_fresh"] = True

        logger.info(f"[Campaign:{self.campaign_id}] Fetching users from API: {self.api_url}")
        logger.info(f"Params: {json.dumps(api_params, indent=4, default=str)}")

        # Retry logic
        max_retries = self.retry_policy.get("max_retries", 3)
        retry_count = 0
        user_data = None

        while retry_count < max_retries:
            try:
                if self.method == "GET":
                    response = requests.get(self.api_url, headers=self.api_headers, params=api_params, timeout=120)
                else:
                    response = requests.post(self.api_url, headers=self.api_headers, json=api_params, timeout=120)

                response.raise_for_status()
                user_data = response.json()

                # Handle API returning empty data or non-list
                if not user_data or (isinstance(user_data, dict) and not user_data.get("data")):
                    user_data = user_data.get("data", []) if isinstance(user_data, dict) else []
                user_data = user_data.get("data", [])
                if user_data:
                    break

            except Exception as e:
                retry_count += 1
                wait_time = 2 ** retry_count if self.retry_policy.get("backoff") == "exponential" else 2
                logger.warning(f"[Campaign:{self.campaign_id}] Retry {retry_count}/{max_retries} due to error: {e}. Waiting {wait_time}s")
                hp.sleep(wait_time)

        # Stop if no user data returned
        if not user_data:
            msg = f"[Campaign:{self.campaign_id}] All users processed or no more data available from API."
            logger.info(msg)
            return {"error": True, "error_reason": msg, "_raise": True, "_raise_message": msg}

        # Apply field mapping (if provided)
        if self.field_mapping:
            logger.info(f"Applying field mapping for [Campaign:{self.campaign_id}]")
            mapped_data = []
            for row in user_data:
                mapped_row = dict(row)
                for target_key, source_key in self.field_mapping.items():
                    if source_key in row:
                        mapped_row[target_key] = row[source_key]
                mapped_data.append(mapped_row)
            user_data = mapped_data

        # Update rate counters & status
        self._update_rate_counters(len(user_data))
        try:
            self.status_model.patch(self.status_id, {"last_page": page, "model_filters": api_params})
        except KeyError:
            self.status_model.post({
                "campaign_id": self.campaign_id,
                "campaign_detail_id": self.campaign_detail_id,
                "campaign_status": "started",
                "last_page": page,
                "model_filters": api_params,
                "campaign_status_check_id": self.status_id
            })

        self.status = self.status_model.get(self.status_id)

        logger.info(f"[Campaign:{self.campaign_id}] Fetched {len(user_data)} users from API page={page}")
        return user_data


# Register in factory
CampaignSourceFactory.register("i2ce_api", I2CEAPICampaignSource)
