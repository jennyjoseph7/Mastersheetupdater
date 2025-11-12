#!/usr/bin/python
# -*- coding: utf-8 -*-
from connectors.user_source_connectors.source_connector import *
logger=hp.get_logger(__name__)
# ---------------- DEFAULT CAMPAIGN SOURCE ----------------
class DefaultCampaignSource(CampaignSourceBase):
    """
    Fetch campaign users from a predefined list (`campaign_users`) with support
    for batching, field mapping, retry policy, and rate limiting.
    """

    def __init__(self, enterprise_id: str, campaign_details_data:dict,campaign_user_source: dict):
        # Config
        config = campaign_user_source.get("config", {})
        max_per_day = config.get("max_per_day") or campaign_details_data.get("max_per_day")
        self.default_batch_size = config.get("batch_size", 100)
        self.default_filters = config.get("filters", {}).copy()
        self.field_mapping = campaign_user_source.get("field_mapping", {})
        self.retry_policy = config.get("retry_policy", {"max_retries": 3, "backoff": "exponential"})
        self.campaign_id=campaign_details_data.get("campaign_id")
        self.campaign_detail_id= campaign_details_data.get("campaign_detail_id")
        
        # Predefined users
        self.campaign_users = campaign_user_source.get("campaign_users", [])
        self._current_index = 0  # track batch position
        
        super().__init__(enterprise_id, campaign_details_data, max_per_day=max_per_day)

    def fetch_next_batch(self, batch_size: int = None, *args, **kwargs):
        batch_size = batch_size or self.default_batch_size

        # Check rate limits
        limit_block = self._check_rate_limits()
        if limit_block:
            return limit_block

        # Determine the next batch
        start = self._current_index
        end = start + batch_size
        batch = self.campaign_users[start:end]
        self._current_index = end

        if not batch:
            msg = f"[Campaign:{self.campaign_id}] All users processed from default list."
            return {"error": True, "error_reason": msg, "_raise": True, "_raise_message": msg}

        # Apply field mapping
        if self.field_mapping:
            mapped_batch = []
            for row in batch:
                mapped_row = dict(row)
                for target_key, source_key in self.field_mapping.items():
                    if source_key in row:
                        mapped_row[target_key] = row[source_key]
                mapped_batch.append(mapped_row)
            batch = mapped_batch

        # Update counters & status
        self._update_rate_counters(len(batch))
        try:
            last_page = int(self.status.get("last_page", 0)) + 1
            self.status_model.patch(
                self.status_id,
                {"last_page": last_page, "model_filters": self.default_filters}
            )
        except KeyError:
            self.status_model.post({
                "campaign_id": self.campaign_id,
                "campaign_detail_id": self.campaign_detail_id,
                "campaign_status": "started",
                "last_page": 1,
                "model_filters": self.default_filters,
                "campaign_status_check_id": self.status_id
            })

        self.status = self.status_model.get(self.status_id)
        return batch


# Register connector in factory
CampaignSourceFactory.register("default", DefaultCampaignSource)