import os
import sys
_parent = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
if _parent not in sys.path:
    sys.path.insert(0, _parent)
from datetime import datetime, timedelta
from typing import * 
from pathlib import Path

try:
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.campaign import Campaign
    from facebook_business.adobjects.adset import AdSet
    from facebook_business.adobjects.ad import Ad
    from facebook_business.adobjects.adcreative import AdCreative
    from facebook_business.adobjects.adimage import AdImage
    from facebook_business.adobjects.page import Page
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.user import User
    from facebook_business.adobjects.targetingsearch import TargetingSearch
except ImportError:
    raise ImportError("This module requires the facebook_business package to be installed. Please run 'pip install facebook_business'")

from cohorts_new.utils.utility import *
from cohorts_new.utils.common_utils import *


logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent
logger.info(f"BASE_DIR : {BASE_DIR}")
def load_default_meta_values():
    json_path = BASE_DIR.parent / "utils" / "meta_sdk_default_values.json"
    logger.info(f"Loading default meta values from {json_path}")
    with open(json_path, "r") as f:
        return json.load(f)

default_meta_values = load_default_meta_values()

def check_valid_values(_check_value_for : str) -> Union[list[str], Dict[str, list[str]]]:
    value_map = {
        "valid_campaign_objectives"     : default_meta_values.get("valid_campaign_objectives"),
        "valid_call_to_action_values"   : default_meta_values.get("valid_call_to_action_values"),
        "valid_optimization_goals"      : default_meta_values.get("valid_optimization_goals"),
        "valid_preview_formats"         : default_meta_values.get("valid_preview_formats"),
        "valid_billing_events"          : default_meta_values.get("valid_billing_events"),
        "valid_campaign_status"         : default_meta_values.get("valid_campaign_status"),
        "valid_special_ad_categories"   : default_meta_values.get("valid_special_ad_categories")
    }

    _check_value_for = _check_value_for.lower()
    if _check_value_for == "all":
        return value_map
    
    if _check_value_for not in value_map:
        raise ValueError(f"Invalid value for: {_check_value_for}")
    _valid_values = value_map.get(_check_value_for)
    return _valid_values

CAMPAIGN_FIELDS = default_meta_values.get("CAMPAIGN_FIELDS", [])
ADSET_FIELDS = default_meta_values.get("ADSET_FIELDS", [])
AD_FIELDS = default_meta_values.get("AD_FIELDS", [])
CREATIVE_FIELDS = default_meta_values.get("CREATIVE_FIELDS", [])

class MetaGraphAPIException(Exception):
    def __init__(self, error_message, *args, **kwargs):
        self.error = error_message
        self.trace = traceback.format_exc()
        super().__init__(self.error)
    
    def to_dict(self):
        return {
            "error": self.error,
            "trace": self.trace
        }

class MetaAdsManager:
    """
    * Meta Ads Manager
    ========================================
    A lightweight wrapper around the Meta Marketing API for creating Facebook / Instagram ad campaigns programmatically.
    This class simplifies the process of creating campaigns, ad sets, creatives, and ads using the Meta Marketing API.
    ----------------------------------------
    * Features
    ----------------------------------------
    - Upload ad images
    - Create campaigns
    - Create ad sets
    - Create creatives
    - Create ads
    - End-to-end ad creation pipeline
    ----------------------------------------
    * Requirements
    ----------------------------------------
    [pip install facebook_business]
    """

    def __init__(
        self,
        app_id          : Optional[str] = None,
        app_secret      : Optional[str] = None,
        access_token    : Optional[str] = None,
        ad_account_id   : Optional[str] = None,
        page_id         : Optional[str] = None,
        api_version     : str           = "v19.0"
    ):
        """
        Initialize Meta Ads API.
        Parameters
        ----------
        app_id : str        | Meta App ID
        app_secret : str    | Meta App secret
        access_token : str  | User access token
        ad_account_id : str | Ad account id (format: act_XXXX)
        page_id : str       | Page id
        api_version : str   | Marketing API version
        """

        self.app_id =  app_id 
        self.app_secret =  app_secret 
        self.access_token = access_token 

        if ad_account_id is not None and isinstance(ad_account_id, str) and not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"
        self.ad_account_id = ad_account_id

        self.page_id = page_id
        self.api_version = api_version

        # if not all([self.app_id, self.app_secret, self.access_token, self.ad_account_id]):
        #     raise ValueError("Missing Meta credentials. Please configure environment variables.")

        try:
            FacebookAdsApi.init(
                app_id          = self.app_id,
                app_secret      = self.app_secret,
                access_token    = self.access_token,
                api_version     = self.api_version
            )

            self.ad_account = AdAccount(self.ad_account_id)
            logger.info(f"Meta Ads API initialized for account {self.ad_account_id}")
        except:
            pass 


    def _helper(self):
        """

        AdAccount: act_123
        Campaign
        ├── Campaign A
        │      ├── AdSet A1
        │      │      ├── Ad 1
        │      │      │     └── Creative
        │      │      └── Ad 2
        │      │             └── Creative
        │      │
        │      └── AdSet A2
        │             └── Ad 3
        │                    └── Creative
        └── Campaign B
                ├── AdSet B1
                │      └── Ad 4
                │             └── Creative
                └── AdSet B2
                    └── Ad 5
                           └── Creative

        """

    # def cursor_to_json(self, cursor):
    #     return [dict(obj) for obj in cursor]
    
    def cursor_to_json(self, cursor):
        results = []
        for obj in cursor:
            clean = {}
            for k, v in dict(obj).items():
                if hasattr(v, "_data"):
                    clean[k] = v._data
                else:
                    clean[k] = v
            results.append(clean)
        return results

    def set_page_id(self, page_id: str):
        self.page_id = page_id
        logger.info(f"Page ID set to {self.page_id}")
        return self.page_id
        
    def get_campaigns(self, fields: list | None = None, effective_status: list | None = None):
        fields = fields or [
            Campaign.Field.id,
            Campaign.Field.name,
            Campaign.Field.status,
            Campaign.Field.objective,
            Campaign.Field.effective_status,
            Campaign.Field.created_time,
        ]
        params = {}
        if effective_status:
            params["effective_status"] = effective_status
        campaigns = self.ad_account.get_campaigns(fields=fields, params=params)
        results = [c.export_all_data() for c in campaigns]
        return results
    
    def get_adsets(self, campaign_id: str | None = None, fields: list | None = None):
        fields = fields or [
            AdSet.Field.id,
            AdSet.Field.name,
            AdSet.Field.status,
            AdSet.Field.campaign_id,
            AdSet.Field.daily_budget,
            AdSet.Field.billing_event,
            AdSet.Field.optimization_goal,
            AdSet.Field.effective_status,
        ]

        params = {}
        if campaign_id:
            params["campaign_id"] = campaign_id

        adsets = self.ad_account.get_ad_sets(fields=fields, params=params)
        results = [a.export_all_data() for a in adsets]
        return results
    
    def get_ads(self, adset_id: str | None = None, campaign_id: str | None = None, fields: list | None = None):
        fields = fields or [
            Ad.Field.id,
            Ad.Field.name,
            Ad.Field.status,
            Ad.Field.adset_id,
            Ad.Field.campaign_id,
            Ad.Field.creative,
            Ad.Field.effective_status,
        ]

        params = {}
        if adset_id:
            params["adset_id"] = adset_id
        if campaign_id:
            params["campaign_id"] = campaign_id

        ads = self.ad_account.get_ads(fields=fields, params=params)
        results = [ad.export_all_data() for ad in ads]
        return results


    def get_creative(self, creative_id: str):
        creative = AdCreative(creative_id)
        result = creative.api_get(fields=CREATIVE_FIELDS)
        object_story_spec = result["object_story_spec"]
        logger.info(f"Object Story Spec: {object_story_spec}")
        result["object_story_spec"] = {key :val for key, val in object_story_spec.items()}
        return dict(result)

    def list_pages(self):
        me = User("me")
        pages = me.get_accounts(fields=["id", "name"])
        logger.info("Pages available to token: \n")
        for page in pages:
            logger.info(page)

    def upload_image(
        self,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
        image_name: Optional[str] = None
    ) -> str:
        """
        Upload an image to Meta Ads image library.

        Supports:
        - Local file upload
        - URL-based upload
        """

        if not image_path and not image_url:
            raise ValueError("Either image_path or image_url must be provided")

        logger.info(f"Uploading image: {image_path or image_url}")

        image = AdImage(parent_id=self.ad_account_id)

        if image_path:
            image[AdImage.Field.filename] = image_path 
        elif image_url:
            image[AdImage.Field.url] = image_url        

        if image_name:
            image[AdImage.Field.name] = image_name

        image.remote_create()

        image_hash = image[AdImage.Field.hash]

        logger.info(f"Image uploaded. Hash: {image_hash}")

        return image_hash
    
    def upload_image(
        self,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
        image_name: Optional[str] = None
    ) -> str:
        MIME_EXTENSION_MAP = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "image/bmp": ".bmp",
            "image/tiff": ".tiff",
        }

        if not image_path and not image_url:
            raise ValueError("Either image_path or image_url must be provided")
        
        temp_file_path = None 


        if image_url:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").split(";")[0].lower()
            suffix = MIME_EXTENSION_MAP.get(content_type, ".jpg")  # fallback
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(response.content)
            tmp.close()
            temp_file_path = tmp.name
            image_path = temp_file_path

        params = {"filename": image_path}

        if image_name:
            params["name"] = image_name
            
        image = self.ad_account.create_ad_image(params=params)
        image_hash = image["hash"]

        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        return image_hash

    def create_campaign(
            self,
            name: str,
            objective: str = "OUTCOME_TRAFFIC",
            status: str = "PAUSED",
            special_ad_categories: Optional[list] = None,
            is_adset_budget_sharing_enabled: bool = False
    ) -> Campaign:
        """
        Create a campaign.

        Returns
        -------
        Campaign
        """
        existing_campaign = self.get_campaign_by_name(name)
        if existing_campaign:
            logger.info(f"Found existing campaign: {name}")
            return existing_campaign
        
        if objective not in default_meta_values.get("valid_campaign_objectives"):
            raise ValueError(f"Invalid campaign objective: '{objective}'. Supported objectives: {default_meta_values.get('valid_campaign_objectives')}") 

        if status not in default_meta_values.get("valid_campaign_status"):
            raise ValueError(f"Invalid campaign status: '{status}'. Supported statuses: {default_meta_values.get('valid_campaign_status')}")
        
        if special_ad_categories is not None:
            if special_ad_categories not in default_meta_values.get("valid_special_ad_categories"):
                raise ValueError(f"Invalid special ad categories: '{special_ad_categories}'. Supported categories: {default_meta_values.get('valid_special_ad_categories')}")

        logger.info(f"Creating campaign: {name}")
        params = {
            Campaign.Field.name: name,
            Campaign.Field.objective: objective,
            Campaign.Field.status: status,
            Campaign.Field.special_ad_categories: special_ad_categories or [],
            Campaign.Field.is_adset_budget_sharing_enabled: is_adset_budget_sharing_enabled
        }
        campaign = self.ad_account.create_campaign(params=params)
        logger.info(f"Campaign created: {campaign.get_id()}")
        return campaign

    def create_ad_set(
        self,
        campaign_id: str,
        name: str,
        daily_budget: int,
        targeting: Dict,
        destination_url: Optional[str] = None,
        status: str = "PAUSED",
        optimization_goal: str = "LINK_CLICKS",
        billing_event: str = "IMPRESSIONS",
        bid_strategy: str = "LOWEST_COST_WITHOUT_CAP"
    ) -> AdSet:
        """
        Create an Ad Set.
        Parameters
        ----------
        daily_budget : int
            Budget in cents (5000 = 50 rupee or $50)
        """

        logger.info(f"Ensuring ad set exists : {name}")
        existing_adsets = self.ad_account.get_ad_sets(
            fields=[
                AdSet.Field.name,
                AdSet.Field.campaign_id
            ],
            params={
                "filtering": [
                    {
                        "field": "name",
                        "operator": "EQUAL",
                        "value": name
                    },
                    {
                        "field": "campaign.id",
                        "operator": "EQUAL",
                        "value": campaign_id
                    }
                ]
            }
        )

        for adset in existing_adsets:
            adset_id = adset[AdSet.Field.id]
            logger.info(f"Found existing ad set: {name}. Returning : {adset_id}")
            return AdSet(adset_id)
        
        if optimization_goal not in default_meta_values.get("valid_optimization_goals"):
            raise ValueError(f"Invalid optimization goal: '{optimization_goal}'. Supported goals: {default_meta_values.get('valid_optimization_goals')}")

        if billing_event not in default_meta_values.get("valid_billing_events"):
            raise ValueError(f"Invalid billing event: '{billing_event}'. Supported events: {default_meta_values.get('valid_billing_events')}")

        if bid_strategy not in default_meta_values.get("valid_bid_strategies"):
            raise ValueError(f"Invalid bid strategy: '{bid_strategy}'. Supported strategies: {default_meta_values.get('valid_bid_strategies')}")

        import pytz
        ist = pytz.timezone('Asia/Kolkata')
        logger.info(f"Creating ad set: {name}")
        # start_time = (datetime.now(ist) + timedelta(minutes=10)).isoformat()
        params = {
            AdSet.Field.name: name,
            AdSet.Field.campaign_id: campaign_id,
            AdSet.Field.daily_budget: daily_budget,
            AdSet.Field.billing_event: billing_event,
            AdSet.Field.optimization_goal: optimization_goal,
            AdSet.Field.targeting: targeting,
            # AdSet.Field.start_time: start_time,
            AdSet.Field.status: status,
            AdSet.Field.bid_strategy: bid_strategy
        }

        # if destination_url:
        #     params[AdSet.Field.promoted_object] = {"link": destination_url}

        adset = self.ad_account.create_ad_set(params=params)
        logger.info(f"AdSet created: {adset.get_id()}")
        return adset

    def create_image_ad_creative(
            self,
            name: str,
            image_hash: str,
            # image_url: str,
            title: str,
            body: str,
            link_url: str,
            call_to_action: str = "LEARN_MORE",
            page_id: Optional[str] = None,
            description: Optional[str] = None
        ) -> AdCreative:
        """
        Create ad creative.
        """

        page_id = page_id or self.page_id

        if not page_id:
            raise ValueError("META_PAGE_ID not configured")
        
        logger.info(f"Creating creative: {name}")
        object_story_spec = {
            "page_id": page_id,
            "link_data": {
                "image_hash": image_hash,
                # "image_url": image_url,
                "link": link_url,
                "message": body,
                "name": title,
                "description": description or "",
                "call_to_action": {
                    "type": call_to_action,
                    "value": {
                        "link": link_url
                        }
                }
            }
        }

        if hasattr(self, "instagram_actor_id") and self.instagram_actor_id:
            logger.info(f"Adding instagram_actor_id: {self.instagram_actor_id}")
            object_story_spec["instagram_actor_id"] = self.instagram_actor_id

        params = {
            AdCreative.Field.name: name,
            AdCreative.Field.object_story_spec: object_story_spec
        }
        creative = self.ad_account.create_ad_creative(params=params)
        logger.info(f"Creative created: {creative.get_id()}")
        return creative

    def create_ad(self, ad_set_id: str, creative_id: str, name: str, status: str = "PAUSED") -> Ad:
        """Create an Ad."""

        logger.info(f"Ensuring ad exists : {name}")
        existing_ads = self.ad_account.get_ads(
            fields=[
                Ad.Field.id,
                Ad.Field.name,
                Ad.Field.adset_id,
                Ad.Field.creative,
                Ad.Field.status,
            ],
            params={
                "adset_id": ad_set_id
            }
        )

        for ad in existing_ads:
            ad_creative = ad.get("creative", {})
            existing_creative_id = ad_creative.get("id")
            if ad.get("name") == name and existing_creative_id == creative_id:
                logger.info(f"Ad already exists. Reusing Ad ID: {ad.get_id()}")
                return ad
            

        logger.info(f"Creating ad: {name}")
        params = {
            Ad.Field.name: name,
            Ad.Field.adset_id: ad_set_id,
            Ad.Field.creative: {"creative_id": creative_id},
            Ad.Field.status: status
        }
        ad = self.ad_account.create_ad(params=params)
        logger.info(f"Ad created: {ad.get_id()}")
        return ad
    
    def preview_creative(self, creative_id: str, ad_format: str = "DESKTOP_FEED_STANDARD"):
        """Get rendered HTML preview of an ad creative for a specific placement. Same preview as shown in Meta Ads Manager."""
        valid_preview_formats = default_meta_values.get("valid_preview_formats")
        if ad_format not in valid_preview_formats:
            raise ValueError(f"Invalid ad format: {ad_format}. Supported formats: {valid_preview_formats}")
        creative = AdCreative(creative_id)
        previews = creative.get_previews(params={"ad_format": ad_format})

        results = []
        for p in previews:
            results.append({
                "format": ad_format,
                "body": p.get("body"),      # HTML iframe
            })

        return results
    
    def get_account_insights(self,  since: str, until: str):
        insights = self.ad_account.get_insights(
            fields=[
                "campaign_name",
                "campaign_id",
                "adset_name",
                "adset_id",
                "ad_name",
                "ad_id",
                "spend",
                "impressions",
                "clicks",
                "ctr",
                "cpc",
            ],
            params={
                "time_range": {"since": since, "until": until},
                "level": "ad",
            },
        )
        return [dict(i) for i in insights]
    
    def get_ad_insights(self, ad_id: str, since: str, until: str):
        ad = Ad(ad_id)

        insights = ad.get_insights(
            fields=[
                "ad_name",
                "impressions",
                "clicks",
                "ctr",
                "cpc",
                "spend",
                "actions",
                "video_30_sec_watched_actions",
            ],
            params={
                "time_range": {"since": since, "until": until},
                "level": "ad",
            },
        )

        return [dict(i) for i in insights]
    
    def get_adset_insights(self, adset_id: str, since: str, until: str):
        adset = AdSet(adset_id)

        insights = adset.get_insights(
            fields=["adset_name", "spend", "impressions", "clicks", "ctr"],
            params={
                "time_range": {"since": since, "until": until},
                "level": "adset",
            },
        )

        return [dict(i) for i in insights]
    

    def get_campaign_insights(self, campaign_id: str, since: str, until: str):
        campaign = Campaign(campaign_id)

        insights = campaign.get_insights(
            fields=[
                "campaign_name",
                "impressions",
                "reach",
                "clicks",
                "ctr",
                "cpc",
                "cpm",
                "spend",
                "actions",
                "cost_per_action_type",
                "date_start",
                "date_stop",
            ],
            params={
                "time_range": {"since": since, "until": until},
                "level": "campaign",
            },
        )

        return [dict(i) for i in insights]

    def create_complete_ad(
        self,
        campaign_name: str,
        ad_name: str,
        image_path: str,
        title: str,
        body: str,
        link_url: str,
        daily_budget: int,
        targeting: Dict
    ) -> Dict:
        """
        Create a complete ad pipeline:
        Campaign → AdSet → Creative → Ad
        """
        logger.info("Starting complete ad creation pipeline")
        image_hash = self.upload_image(image_path)
        campaign = self.create_campaign(campaign_name)
        adset = self.create_ad_set(
            campaign_id=campaign.get_id(),
            name=f"{ad_name} AdSet",
            daily_budget=daily_budget,
            targeting=targeting
        )
        creative = self.create_image_ad_creative(
            name=f"{ad_name} Creative",
            image_hash=image_hash,
            title=title,
            body=body,
            link_url=link_url
        )
        ad = self.create_ad(
            ad_set_id=adset.get_id(),
            creative_id=creative.get_id(),
            name=ad_name
        )
        result = {
            "campaign_id": campaign.get_id(),
            "adset_id": adset.get_id(),
            "creative_id": creative.get_id(),
            "ad_id": ad.get_id(),
            "image_hash": image_hash
        }
        logger.info("Complete ad pipeline finished")
        return result
    
    from typing import Optional, Dict, List

    def create_complete_ad(
        self,
        # ---------------- CAMPAIGN ----------------
        campaign_name: str,
        campaign_objective: str = "OUTCOME_TRAFFIC",
        campaign_status: str = "PAUSED",
        special_ad_categories: Optional[List[str]] = None,
        is_adset_budget_sharing_enabled: bool = False,

        # ---------------- AD SET ----------------
        adset_name: str = "",
        daily_budget: int = 0,
        targeting: Dict = None,
        destination_url: Optional[str] = None,
        optimization_goal: str = "LINK_CLICKS",
        billing_event: str = "IMPRESSIONS",

        # ---------------- IMAGE ----------------
        image_url: Optional[str] = None,
        image_name: Optional[str] = None,

        # ---------------- CREATIVE ----------------
        creative_name: str = "",
        title: str = "",
        body: str = "",
        link_url: str = "",
        call_to_action: str = "LEARN_MORE",
        page_id: Optional[str] = None,
        description: Optional[str] = None,

        # ---------------- AD ----------------
        ad_name: str = "",
        ad_status: str = "PAUSED",
    ) -> Dict[str, str]:
        """
        Complete flow:
        Campaign → Ad Set → Image → Creative → Ad
        """

        if not targeting:
            raise ValueError("targeting dict is required")

        # ---------------- CAMPAIGN ----------------
        campaign = self.create_campaign(
            name=campaign_name,
            objective=campaign_objective,
            status=campaign_status,
            special_ad_categories=special_ad_categories,
            is_adset_budget_sharing_enabled=is_adset_budget_sharing_enabled
        )
        campaign_id = campaign.get_id()

        # ---------------- AD SET ----------------
        adset = self.create_ad_set(
            campaign_id=campaign_id,
            name=adset_name,
            daily_budget=daily_budget,
            targeting=targeting,
            destination_url=destination_url or link_url,
            optimization_goal=optimization_goal,
            billing_event=billing_event
        )
        adset_id = adset.get_id()

        # ---------------- IMAGE UPLOAD ----------------
        image_hash = self.upload_image(
            image_url = image_url,
            image_name = image_name
        )

        # ---------------- CREATIVE ----------------
        creative = self.create_image_ad_creative(
            name=creative_name,
            image_hash=image_hash,
            title=title,
            body=body,
            link_url=link_url,
            call_to_action=call_to_action,
            page_id=page_id,
            description=description
        )
        creative_id = creative.get_id()

        # ---------------- AD ----------------
        ad = self.create_ad(
            ad_set_id=adset_id,
            creative_id=creative_id,
            name=ad_name,
            status=ad_status
        )
        ad_id = ad.get_id()

        return {
            "campaign_id": campaign_id,
            "adset_id": adset_id,
            "creative_id": creative_id,
            "ad_id": ad_id,
            "image_hash": image_hash
        }

                           
    
    def get_meta_ads_insights(self, since: str, until: str, page_size: int = 500):
        def _extract_action_value(action_list: list, action_type: str) -> str:
            for item in action_list or []:
                if item.get("action_type") == action_type:
                    return item.get("value", "0")
            return "0"
        
        FIELDS = [
            "date_start", "date_stop",
            "campaign_id", "campaign_name",
            "adset_id", "adset_name",
            "ad_id", "ad_name",
            "impressions", "reach", "frequency",
            "clicks", "unique_clicks", "ctr", "cpc", "cpm", "spend",
            "actions", "action_values", "cost_per_action_type",
            "purchase_roas",
            "quality_ranking",
            "engagement_rate_ranking",
            "conversion_rate_ranking",
            "outbound_clicks",
            "video_p50_watched_actions",
        ]

        ACTION_KEYS = {
            "landing_page_views": "landing_page_view",
            "video_views_3s":     "video_view",
            "leads":              "lead",
            "purchases":          "purchase",
        }

        params = {
            "level": "ad",
            "time_range": {"since": since, "until": until},
            "limit": page_size,
        }

        try:
            insights_cursor = self.ad_account.get_insights(fields=FIELDS, params=params)
        except Exception as e:
            logger.error("Failed to fetch Meta Ads insights: %s", e)
            raise

        results = []

        for row in insights_cursor:
            try:
                data = row.export_all_data()
            except Exception as e:
                logger.warning("Skipping row due to export error: %s", e)
                continue

            actions = data.get("actions", [])
            for field_name, action_type in ACTION_KEYS.items():
                data[field_name] = _extract_action_value(actions, action_type)       

            data["video_views_50p"] = _extract_action_value(
                data.get("video_p50_watched_actions") or [],
                "video_p50_watched_actions",
            )

            data["outbound_clicks_count"] = _extract_action_value(
                 data.get("outbound_clicks") or [],
                "outbound_click",
            )
            results.append(data)
            logger.info(
                "Fetched %d ad insight rows for range %s → %s",
                len(results), since, until,
            )


        return results
    

    def post_text(self, message: str) -> dict:
        try:
            api_ver = self.api_version or "v19.0"
            url = f"https://graph.facebook.com/{api_ver}/{self.page_id}/feed"
            resp = requests.post(url, data={
                "message": message,
                "access_token": self.access_token
            })
            return resp.json()
        except Exception as e:
            raise e 

    def post_image_url(self, image_url: str, caption: str = "") -> dict:
        api_ver = self.api_version or "v19.0"
        url = f"https://graph.facebook.com/{api_ver}/{self.page_id}/photos"
        resp = requests.post(url, data={
            "url": image_url,
            "caption": caption,
            "access_token": self.access_token
        })
        return resp.json()
    
    def schedule_post(self, message: str, publish_time_unix: int) -> dict:
        api_ver = self.api_version or "v19.0"
        url = f"https://graph.facebook.com/{api_ver}/{self.page_id}/feed"
        resp = requests.post(url, data={
            "message": message,
            "published": "false",
            "scheduled_publish_time": publish_time_unix,
            "access_token": self.access_token
        })
        return resp.json()
    
    def post_video(self, video_path: str, description: str = "") -> dict:
        api_ver = self.api_version or "v19.0"
        url = f"https://graph-video.facebook.com/{api_ver}/{self.page_id}/videos"
        with open(video_path, "rb") as f:
            resp = requests.post(url, files={
                "source": f
            }, data={
                "description": description,
                "access_token": self.access_token
            })

        return resp.json()



if __name__ == "__main__":

    app_id =        "your_app_id"
    app_secret =    "your_app_secret"
    access_token =  "your_access_token"
    page_id =       "your_page_id"
    account_id =    "your_account_id"

    manager = MetaAdsManager(
        app_id          =   app_id,
        app_secret      =   app_secret,
        access_token    =   access_token,
        ad_account_id   =   account_id,
        page_id         =   page_id
    )


    results = manager.get_campaigns()
    logger.info(f"All Campaigns: {json.dumps(results, indent=4, default=str)}")

    results = manager.get_adsets()
    logger.info(f"All Adsets: {json.dumps(results, indent=4, default=str)}")

    results = manager.get_ads()
    logger.info(f"All Ads: {json.dumps(results, indent=4, default=str)}")
    assert False

    # ---------------- TARGETING (broad India desktop/mobile example) ----------------
    targeting = {
        "geo_locations": {
            "countries": ["IN"]
        },
        "age_min": 21,

        "publisher_platforms": ["facebook", "instagram"],
        "facebook_positions": ["feed"],
        "instagram_positions": ["stream"],

        "targeting_automation": {
            "advantage_audience": 0
        }
    }

    result = manager.create_complete_ad(
        # ---------------- CAMPAIGN ----------------
        campaign_name="IAMDAVE | Traffic | April - Meta SDK Testing Shreyas",
        campaign_objective="OUTCOME_TRAFFIC",
        campaign_status="PAUSED",
        special_ad_categories=[],
        is_adset_budget_sharing_enabled=False,

        # ---------------- AD SET ----------------
        adset_name="India Broad | Traffic Test",
        daily_budget=10000, 
        targeting=targeting,
        destination_url="https://www.iamdave.ai/",
        optimization_goal="LINK_CLICKS",
        billing_event="IMPRESSIONS",

        # ---------------- IMAGE ----------------
        image_url="https://img.freepik.com/free-vector/gradient-npl-illustration_52683-80462.jpg",
        image_name=None,

        # ---------------- CREATIVE ----------------
        creative_name="IAMDAVE Main Image Creative",
        title="Turn Your Ideas into AI Workflows",
        body="Automate research, content, and workflows with Dave. Start in seconds.",
        link_url="https://www.iamdave.ai/",
        call_to_action="LEARN_MORE",
        page_id=None,  # uses manager.page_id
        description="AI tools to automate your daily work",

        # ---------------- AD ----------------
        ad_name="IAMDAVE Traffic Ad v1",
        ad_status="PAUSED"
    )

    print(json.dumps(result, indent=4, default=str))

    assert False







    

    data = manager.post_text("Abhishek is the greatest developer of all time..")

    print(f"data : {json.dumps(data, indent=4, default=str)}")

    assert False

    # data = manager.get_meta_ads_insights(since="2026-01-01", until="2026-04-21")
    tata_sierra_campaign = manager.create_campaign(
        name="My Test Campaign for Tata Sierra",
        objective="OUTCOME_TRAFFIC",
        status="PAUSED",
        is_adset_budget_sharing_enabled=False
    )


    tata_sierra_campaign_id = "120245319830110664"
    image_hash = "b9f3057f32414077053e76b205a34e2c"

    # image_hash = manager.upload_image(image_path="/home/shreyasvaishnav/autobot_agents_branch_product/autobot_agents/cohorts_new/ad_platforms/tata_sierra_test_image.jpg")

    # logger.info(f"Image hash: {image_hash}")
    # assert False

    targeting = {
        "geo_locations": {
            "countries": ["IN"]
        },
        "age_min": 25,
        "age_max": 65,
        "targeting_automation": {
            "advantage_audience": 1
        }
    }

    adset = manager.create_ad_set(
        campaign_id=tata_sierra_campaign_id,
        name="Tata Sierra - India Audience Targeting Test",
        daily_budget=10000,
        targeting=targeting,
        # destination_url="https://cars.tatamotors.com/sierra/ice.html",
        optimization_goal="LANDING_PAGE_VIEWS",
        billing_event="IMPRESSIONS"
    )

    logger.info(f"Adset created: {adset}")


    # insights = manager.get_account_insights(since="2025-12-01", until="2026-04-14")
    # logger.info(f"Insights: {json.dumps(insights, indent=2, default=str)}")

    # ad_insights = manager.get_ad_insights(ad_id=120245458007230664, since="2025-12-01", until="2026-04-14")

 #    logger.info(f"Ad insights: {json.dumps(ad_insights, indent=2, default=str)}")


    

    adset_for_tata_sierra = "120245325100150664"

    # creative = manager.create_image_ad_creative(
    #     name="Tata Sierra Creative",
    #     image_hash=image_hash,
    #     title="The Icon Returns 🚙",
    #     body="Experience the all-new Tata Sierra. Built for adventure.",
    #     link_url="https://cars.tatamotors.com/sierra/ice.html",
    #     call_to_action = "LEARN_MORE",
    #     description="Explore design, features & book your drive"
    # )

    # logger.info(f"Creative created: {creative}")
    # assert False


    creative_id = "1564283655700763"

    ad= manager.create_ad(
        ad_set_id=adset_for_tata_sierra,
        creative_id=creative_id,
        name="Tata Sierra Ad",
        status="PAUSED"
    )

    logger.info(f"Ad created: {ad}")

    assert False

    ad_id = "120245955023010664"

    preview = manager.preview_creative(creative_id="120245456058310664", ad_format="FACEBOOK_PROFILE_FEED_DESKTOP")

    logger.info(f"Preview: {preview}")


    # logger.info(f"Campaign created: {tata_sierra_campaign}")






    params = {
        'q': 'baseball',
        'type': 'adinterest',
    }

    results = TargetingSearch.search(params=params)

    print(f"Found {len(results)} results for 'baseball' targeting:")

    for target in results:
        print(f"* ID: {target['id']}, Name: {target['name']}, Audience Size: {target.get('audience_size', 'N/A')}")
    
    assert False


    # manager.test_connection()
    # manager.list_pages()


    # all_campaigns = manager.list_all_campaigns()
    # logger.info(f"All Campaigns: {json.dumps(all_campaigns, indent=4, default=str)}")

    

    # adsets = manager.get_ad_sets_in_campaign(campaign_id="120237185605140664")
    # logger.info(f"ad sets: {json.dumps(adsets, indent=4, default=str)}")

    # ads = manager.get_ads_in_adset("120237185606350664")
    # logger.info(f"ads: {json.dumps(ads, indent=4, default=str)}")


    creative = manager.get_creative("710615072057217")
    logger.info(f"creative: {json.dumps(creative, indent=4, default=str)}")

    assert False

    

    manager.get_ad(ad_id)

    result = manager.get_ad(ad_id="120237185606350664")
    logger.info(f"ad: {json.dumps(result, indent=4, default=str)}")
    
    


    manager = MetaAdsManager(
        app_id="your_app_id",
        app_secret="your_app_secret",
        access_token="your_access_token",
        page_id="your_page_id"
    )

    targeting = {
        "geo_locations": {"countries": ["BR"]},
        "age_min": 25,
        "age_max": 55,
        "publisher_platforms": ["facebook", "instagram"],
        "facebook_positions": ["feed"],
        "instagram_positions": ["stream"]
    }

    # Step 1. Upload Image
    image_hash = manager.upload_image(image_path="./generated_images/apartment.png")
    print("Image Hash:", image_hash)

    # Step 2. Create Campaign
    campaign = manager.create_campaign(
        name="Real Estate Campaign",
        objective="OUTCOME_LEADS"
    )
    print("Campaign ID:", campaign.get_id())

    # Step 3. Create AdSet
    adset = manager.create_ad_set(
        campaign_id=campaign.get_id(),
        name="Luxury Apartment AdSet",
        daily_budget=5000,
        targeting=targeting
    )

    print("AdSet ID:", adset.get_id())

    # Step 4. Create AdCreative
    creative = manager.create_ad_creative(
        name="Luxury Apartment Creative",
        image_hash=image_hash,
        title="Luxury Apartment with Ocean View",
        body="Discover your dream property today.",
        link_url="https://example.com/property",
        call_to_action="LEARN_MORE"
    )

    print("Creative ID:", creative.get_id())

    # Step 5. Create Ad
    ad = manager.create_ad(
        ad_set_id="ADSET_ID_HERE",
        creative_id=creative.get_id(),
        name="Luxury Apartment Ad"
    )   




    result = manager.create_complete_ad(
        campaign_name="Real Estate Campaign",
        ad_name="Luxury Apartment Ad",
        image_path="./generated_images/apartment.png",
        title="Luxury Apartment with Ocean View",
        body="Discover your dream property today.",
        link_url="https://example.com/property",
        daily_budget=5000,
        targeting=targeting
    )

    print(result)

