#!/usr/bin/python
# -*- coding: utf-8 -*-
from connectors.user_source_connectors.source_connector import *
logger=hp.get_logger(__name__)
import time

# ---------------- FILE SOURCE ----------------
class FileCampaignSource(CampaignSourceBase):
    """Campaign source: stream users from file (CSV, JSON, TXT). Supports retry, field mapping, and batch control."""

    def __init__(self, enterprise_id, campaign_details_data:dict, campaign_user_source: dict):

        # Parse configuration
        config = campaign_user_source.get("config", {})
        max_per_day = config.get("max_per_day") or campaign_details_data.get("max_per_day")

        connection = campaign_user_source.get("connection", {})
        self.file_path_or_url = connection.get("endpoint")
        self.local_path, self.file_type = self._ensure_local_file(self.file_path_or_url)
        self.campaign_id=campaign_details_data.get("campaign_id")
        self.campaign_detail_id= campaign_details_data.get("campaign_detail_id")

        # Defaults
        self.default_batch_size = config.get("batch_size", 100)
        self.field_mapping = campaign_user_source.get("field_mapping", {})
        self.retry_policy = config.get("retry_policy", {"max_retries": 3, "backoff": "exponential"})
        super().__init__(enterprise_id, campaign_details_data,max_per_day=max_per_day)

    
    # ---------------- FILE HANDLING ----------------
    def _ensure_local_file(self, file_path_or_url, cache_dir="/tmp"):
        if not file_path_or_url:
            raise ValueError("File path or URL is missing in campaign_user_source.connection.endpoint")

        if not file_path_or_url.startswith("http"):
            local_path = file_path_or_url
        else:
            os.makedirs(cache_dir, exist_ok=True)
            local_path = os.path.join(cache_dir, os.path.basename(file_path_or_url))
            if not os.path.exists(local_path):
                logger.info(f"Downloading file from {file_path_or_url} -> {local_path}")
                resp = requests.get(file_path_or_url, stream=True, timeout=60)
                resp.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=FILE_CHUNK_SIZE):
                        f.write(chunk)

        _, ext = os.path.splitext(local_path)
        return local_path, ext.lower().lstrip(".")

    # ---------------- FETCH NEXT BATCH ----------------
    def fetch_next_batch(self, batch_size=None):
        batch_size = batch_size or self.default_batch_size
        limit_block = self._check_rate_limits()
        if limit_block:
            return limit_block

        last_offset = int(self.status.get("last_offset", 0) or 0)
        users = []
        max_retries = self.retry_policy.get("max_retries", 3)
        retry_count = 0

        # Retry mechanism for transient read errors
        while retry_count < max_retries:
            try:
                users = self._read_file_chunk(last_offset, batch_size)
                break
            except Exception as e:
                retry_count += 1
                wait_time = 2 ** retry_count if self.retry_policy.get("backoff") == "exponential" else 2
                logger.warning(f"[Campaign:{self.campaign_id}] File read retry {retry_count}/{max_retries} after error: {e}. Waiting {wait_time}s")
                time.sleep(wait_time)

        if not users:
            logger.info(f"[Campaign:{self.campaign_id}] File exhausted or empty batch. No more users.")
            return {
                "error": True,
                "error_reason": "No more user records found in file",
                "_raise": True,
                "_raise_message": "No more user records left"
            }
        
        # Apply field mapping (preserving all fields)
        if self.field_mapping:
            logger.info(f"Applying field mapping (preserving all original fields) for [Campaign:{self.campaign_id}]")
            mapped_users = []
            for row in users:
                mapped_row = dict(row)
                for target_key, source_key in self.field_mapping.items():
                    if source_key in row:
                        mapped_row[target_key] = row[source_key]
                mapped_users.append(mapped_row)
            users = mapped_users
        # make all the key to lower and remove space as these key attribute will store in db and DB doesn't suppost Spaces and Capital letter
        users = [
        {
                k.replace(" ", "_").replace(".", "").strip().lower(): v
                for k, v in d.items()
            }
            for d in users
        ]

        # Update progress and counters
        self._update_rate_counters(len(users))
        self.status_model.patch(self.status_id, {"last_offset": last_offset + len(users)})
        self.status = self.status_model.get(self.status_id)

        logger.info(f"[Campaign:{self.campaign_id}] Fetched {len(users)} users from file (offset={last_offset})")
        return users

    # ---------------- INTERNAL READ HELPER ----------------
    def _read_file_chunk(self, start: int, size: int):
        users = []
        if self.file_type == "csv":
            with open(self.local_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in islice(reader, start, start + size):
                    users.append(row)

        elif self.file_type == "json":
            with open(self.local_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for row in islice(data, start, start + size):
                    users.append(row)

        elif self.file_type == "txt":
            with open(self.local_path, "r", encoding="utf-8") as f:
                for line in islice(f, start, start + size):
                    users.append({"line": line.strip()})
        else:
            raise ValueError(f"Unsupported file type: {self.file_type}")

        return users
    
CampaignSourceFactory.register("file", FileCampaignSource)


