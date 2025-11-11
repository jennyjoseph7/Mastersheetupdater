#!/usr/bin/python
# -*- coding: utf-8 -*-
from connectors.user_source_connectors.source_connector import *
logger=hp.get_logger(__name__)
# ---------------- DB SOURCE ----------------
class DBCampaignSource(CampaignSourceBase):
    """Fetch campaign users from GryD DB model, with field mapping and retry policy support."""

    def __init__(self, enterprise_id: str, campaign_details_data:dict, campaign_user_source: dict):
        self.model_name = campaign_user_source.get("config",{}).get("source_model")
        self.user_model = reload_model_ref(self.model_name, enterprise_id)
        self.campaign_id=campaign_details_data.get("campaign_id")
        self.campaign_detail_id= campaign_details_data.get("campaign_detail_id")

        # Defaults
        config = campaign_user_source.get("config", {})
        max_per_day = config.get("max_per_day") or campaign_details_data.get("max_per_day")
        self.default_batch_size = config.get("batch_size", 100)
        self.default_filters = config.get("filters", {}).copy()
        self.field_mapping = campaign_user_source.get("field_mapping", {})
        self.retry_policy = config.get("retry_policy", {"max_retries": 3, "backoff": "exponential"})
        super().__init__(enterprise_id, campaign_details_data,max_per_day=max_per_day)


        

    def fetch_next_batch(self, batch_size: Optional[int] = None, model_filters: Optional[dict] = None):
        batch_size = batch_size or self.default_batch_size
        model_filters = model_filters or self.default_filters.copy()

        # Check rate limits
        limit_block = self._check_rate_limits()
        if limit_block:
            return limit_block

        last_page = int(self.status.get("last_page", 0))
        model_filters["_page_number"] = last_page + 1
        model_filters["_page_size"] = batch_size
        model_filters["_as_option"] = True
        # model_filters[f"{self.campaign_id}-{self.campaign_detail_id}"] = None

        logger.info(f"[Campaign:{self.campaign_id}] Fetching users from DB with filters: {json.dumps(model_filters,indent=4,default=str)}")

        # Retry logic
        max_retries = self.retry_policy.get("max_retries", 3)
        retry_count = 0
        user_data = None
        while retry_count < max_retries:
            try:
                user_data = self.user_model.list(**model_filters)
                if user_data:  # only break if data returned
                    break
            except Exception as e:
                retry_count += 1
                wait_time = 2 ** retry_count if self.retry_policy.get("backoff") == "exponential" else 2
                logger.warning(
                    f"[Campaign:{self.campaign_id}] Retry {retry_count}/{max_retries} due to error: {e}. Waiting {wait_time}s"
                )
                hp.sleep(wait_time)

        if not user_data:
            msg = f"[Campaign:{self.campaign_id}] All users processed for DB model={self.model_name}"
            logger.info(msg)
            return {"error": True, "error_reason": msg, "_raise": True, "_raise_message": msg}


        # Apply field mapping
        if self.field_mapping:
            logger.info(f"Applying field mapping (preserving all original fields) for [Campaign:{self.campaign_id}]")
            mapped_data = []

            for row in user_data:
                # Start with all original fields
                mapped_row = dict(row)

                # Apply mappings: destination_key = mapped from source_key
                for target_key, source_key in self.field_mapping.items():
                    if source_key in row:
                        mapped_row[target_key] = row[source_key]

                mapped_data.append(mapped_row)

            user_data = mapped_data


        # Update counters & status
        self._update_rate_counters(len(user_data))
        try:
            self.status_model.patch(
                self.status_id,
                {"last_page": last_page + 1, "model_filters": model_filters}
            )
        except KeyError as KE:
            logger.info(f"Status Id {self.status_id} Not Found in the DB. Posting New Id With Data")
            res= self.status_model.post({"campaign_id":self.campaign_id,"campaign_detail_id":self.campaign_detail_id,"campaign_status":"started","last_page": last_page + 1, "model_filters": model_filters,"campaign_status_check_id":self.status_id})
            logger.info(f"Posting:: {json.dumps(res,indent=4,default=str)}")

        self.status = self.status_model.get(self.status_id)

        logger.info(f"[Campaign:{self.campaign_id}] Fetched {len(user_data)} users from DB page={last_page + 1}")
        return user_data


CampaignSourceFactory.register("gryd", DBCampaignSource)