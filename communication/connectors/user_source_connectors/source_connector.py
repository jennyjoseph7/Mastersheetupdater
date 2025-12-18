#!/usr/bin/python
# -*- coding: utf-8 -*-
from connectors.communication_helpers import *
from connectors.communication_helpers import _wait_for_next_minute
logger=hp.get_logger(__name__)
import sys
import os
from models import validators as val

# ---------------- CONFIG ----------------
FILE_CHUNK_SIZE = 5* 1024 * 1024  # 5 MB
DB_TIMEZONE = "Asia/Kolkata"   # adjust as per env
DEFAULT_MAX_PER_DAY=999999999


# ---------------- BASE CLASS ----------------
class CampaignSourceBase:
    """Base class for campaign sources (DB, file, API, etc.)."""
    """
    Handles creation or retrieval of a campaign status record.
    Automatically generates a deterministic campaign_status_check_id
    based on campaign and channel identifiers.
    """
    # MODEL_NAME= M_GRYD_CAMPAIGN_STATUS_CHECK

    def __init__(self, enterprise_id: str, campaign_details_data: dict, max_per_day: int = None):
        self.enterprise_id = enterprise_id
        self.campaign_details_data = campaign_details_data
        self.max_per_day = max_per_day

        self.campaign_id = campaign_details_data.get("campaign_id")
        self.campaign_detail_id = campaign_details_data.get("campaign_detail_id")

        # Generate unique deterministic ID
        self.status_id = val.name_to_id_func(
            {},
            campaign_details_data,
            "campaign_status_check_id",
            "campaign_id",
            "channel",
            "channel_provider",
            attribute_join="",
            is_unique=True,
            separator="-",
        )

        logger.info("TEST CampaignSourceBase")
        
    # def _get_or_create_status(self) -> Dict[str, Any]:
    #     """Retrieve existing campaign status or create a new one if missing."""
    #     try:
    #         status = self.status_model.get(self.status_id)
    #         logger.info(f"[Campaign:{self.campaign_id}] Existing status found: {status}")
    #         return status
    #     except Exception:
    #         logger.warning(f"[Campaign:{self.campaign_id}] Status not found. Creating new entry.")

    #     payload = {
    #         "campaign_status_check_id": self.status_id,
    #         "campaign_id": self.campaign_id,
    #         "campaign_detail_id": self.campaign_detail_id,
    #         "max_per_day": self.campaign_details_data.get("max_per_day") or DEFAULT_MAX_PER_DAY,
    #         "campaign_user_source": self.campaign_details_data.get("campaign_user_source") or {},
    #         "channel": self.campaign_details_data.get("channel"),
    #         "channel_provider": self.campaign_details_data.get("channel_provider"),
    #     }

    #     logger.info(f"[Campaign:{self.campaign_id}] Creating campaign status:\n{json.dumps(payload, indent=2)}")

    #     try:
    #         response = self.status_model.post(payload)
    #         logger.info(f"[Campaign:{self.campaign_id}] Campaign status created successfully: {response}")
    #         return response
    #     except Exception as e:
    #         logger.error(f"[Campaign:{self.campaign_id}] Failed to create campaign status.", exc_info=True)
    #         hp.print_error()
    #         raise

    # def get_status(self) -> Dict[str, Any]:
    #     """Return the current campaign status data."""
    #     return self.status
    
    # ---------------- RATE LIMIT HELPERS ----------------
    def _check_rate_limits(self):
        today_sent = int(self.status.get("today_sent", 0))
        today_date = hp.today(tz=DB_TIMEZONE, as_date=False)
        last_date = str(self.status.get("last_date") or "")

        # Reset daily counter if new day
        if last_date != today_date:
            logger.info(f"[Campaign:{self.campaign_id}] Resetting daily counter (new day)")
            today_sent = 0

        max_per_day = int(self.status.get("max_per_day", CAMPAIGN_MAX_TRIGGER))
        if today_sent >= max_per_day:
            logger.warning(
                f"[Campaign:{self.campaign_id}] Daily cap reached ({today_sent}/{max_per_day})"
            )
            return {
                "sucess": True,
                "sucess_reason": "Daily cap reached",
                "_raise": True,
                "_raise_message": f"[Campaign:{self.campaign_id}] Daily cap reached ({today_sent}/{max_per_day})",
                "last_date": last_date,
                "today_date": today_date
            }

        # Per-minute rate limit
        last_minute_count = int(self.status.get("last_minute_count", 0))
        last_minute_ts = self.status.get("last_minute_ts")
        max_per_minute = int(self.status.get("max_per_minute", 100))

        if last_minute_ts and is_within_last_minute(last_minute_ts):
            if last_minute_count >= max_per_minute:
                logger.warning(
                    f"[Campaign:{self.campaign_id}] Per-minute limit reached ({last_minute_count}/{max_per_minute})"
                )
                _wait_for_next_minute(last_minute_ts)
                self.status["last_minute_count"] = 0
        else:
            self.status["last_minute_count"] = 0
        
        self.status = self.status_model.get(self.status_id)
        if self.status.get("campaign_status",'').lower() in ["stoped","pause","end"]:
            logger.error("Stopping the current campaign......")
            return {
                "error":True,
                "error_reason":f'Campaign Status is {self.status.get("campaign_status","")}',
                "_raise": True,
                "campaign_status_check_id": self.status_id
            }
        

        return None

    def _update_rate_counters(self, batch_size: int):
        today_date = hp.today(tz=DB_TIMEZONE, as_date=False)

        updated = {
            "sent_count": int(self.status.get("sent_count", 0)) + batch_size,
            "today_sent": int(self.status.get("today_sent", 0)) + batch_size,
            "last_date": today_date,
            "last_minute_ts": hp.now(tz=DB_TIMEZONE,as_datetime=False),
            "last_minute_count": int(self.status.get("last_minute_count", 0)) + batch_size,
            "last_update": hp.now(tz=DB_TIMEZONE, as_datetime=False),
            "campaign_status": "started",
            "campaign_status_check_id": self.status_id
        }

        if not self.status_model.get(self.status_id):
            self.status_model.post(updated)
        else:
            self.status_model.patch(self.status_id, updated)

        self.status = self.status_model.get(self.status_id)

        logger.info(
            f"[Campaign:{self.campaign_id}] Updated progress: sent={updated['sent_count']}, "
            f"today_sent={updated['today_sent']}, last_minute_count={updated['last_minute_count']}"
        )

    # ---------------- ABSTRACT ----------------
    def fetch_next_batch(self, *args, **kwargs):
        raise NotImplementedError



class CampaignSourceFactory:
    _registry = {}

    @classmethod
    def register(cls, source_type: str, source_class: type):
        cls._registry[source_type.lower()] = source_class
        # logger.info(f"✅ Registered source: {source_type} -> {source_class.__name__}")

    @classmethod
    def create_from_source_json(cls, enterprise_id:str, campaign_details_data:dict, campaign_user_source:dict):
        """
        Create a campaign source from a given source JSON.

        Args:
            enterprise_id (str): The ID of the enterprise.
            campaign_details_data (dict): The campaign details data.
            campaign_user_source (dict): The campaign user source data.

        Returns:
            CampaignSource: The campaign source object.

        Raises:
            ValueError: If the source type is not supported.
            Exception: If unable to create the campaign source from the given source JSON.
        """
        try:
            logger.info("Intializing create_from_source_json")
            src_type = (campaign_user_source or {}).get("source_type", "").lower()
            
            if not src_type:
                raise ValueError("Missing 'type' in campaign_user_source")
            logger.info(f"Loading campaign src_type: {src_type}")
            source_class = cls._registry.get(src_type)
            if not source_class:
                raise ValueError(f"Unsupported source type: {src_type}")

            return source_class(
                enterprise_id=enterprise_id,
                campaign_details_data=campaign_details_data,
                campaign_user_source=campaign_user_source,
            )
        except Exception as e:
            hp.print_error()
            raise Exception(f"Unable Create User data from the source")
        
