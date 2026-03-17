import os
import sys 
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)), '..')
from datetime import datetime, timedelta
from typing import * 

try:
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.campaign import Campaign
    from facebook_business.adobjects.adset import AdSet
    from facebook_business.adobjects.ad import Ad
    from facebook_business.adobjects.adcreative import AdCreative
    from facebook_business.adobjects.adimage import AdImage
except ImportError:
    raise ImportError("This module requires the facebook_business package to be installed.")

from cohorts_new.utils.utility import *
from cohorts_new.utils.common_utils import *

logger = get_logger(__name__)

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
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        ad_account_id: Optional[str] = None,
        page_id: Optional[str] = None,
        api_version: str = "v19.0"
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

        self.app_id = app_id 
        self.app_secret = app_secret 
        self.access_token = access_token 
        self.ad_account_id = ad_account_id 
        self.page_id = page_id

        if not all([self.app_id, self.app_secret, self.access_token, self.ad_account_id, self.page_id]):
            raise ValueError(
                "Missing Meta credentials. Please configure environment variables."
            )

        FacebookAdsApi.init(
            app_id=self.app_id,
            app_secret=self.app_secret,
            access_token=self.access_token,
            api_version=api_version
        )

        self.ad_account = AdAccount(self.ad_account_id)
        logger.info(f"Meta Ads API initialized for account {self.ad_account_id}")

    def upload_image(self, image_path: str, image_name: Optional[str] = None) -> str:
        """Upload an image to Meta Ads image library.
        Parameters
        ----------
        image_path : str
            Local path to the image
        Returns
        ----------
        str
            Image hash used for creatives
        """

        logger.info(f"Uploading image: {image_path}")
        image = AdImage(parent_id=self.ad_account_id)
        image[AdImage.Field.filename] = image_path
        image.remote_create()
        image_hash = image[AdImage.Field.hash]
        logger.info(f"Image uploaded. Hash: {image_hash}")
        return image_hash

    def create_campaign(
            self,
            name: str,
            objective: str = "OUTCOME_TRAFFIC",
            status: str = "PAUSED",
            special_ad_categories: Optional[list] = None
    ) -> Campaign:
        """
        Create a campaign.

        Returns
        -------
        Campaign
        """
        logger.info(f"Creating campaign: {name}")
        params = {
            Campaign.Field.name: name,
            Campaign.Field.objective: objective,
            Campaign.Field.status: status,
            Campaign.Field.special_ad_categories: special_ad_categories or []
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
        optimization_goal: str = "LINK_CLICKS",
        billing_event: str = "IMPRESSIONS"
    ) -> AdSet:
        """
        Create an Ad Set.
        Parameters
        ----------
        daily_budget : int
            Budget in cents (5000 = $50)
        """
        logger.info(f"Creating ad set: {name}")
        start_time = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        params = {
            AdSet.Field.name: name,
            AdSet.Field.campaign_id: campaign_id,
            AdSet.Field.daily_budget: daily_budget,
            AdSet.Field.billing_event: billing_event,
            AdSet.Field.optimization_goal: optimization_goal,
            AdSet.Field.targeting: targeting,
            AdSet.Field.start_time: start_time,
            AdSet.Field.status: "PAUSED",
            AdSet.Field.bid_strategy: "LOWEST_COST_WITHOUT_CAP"
        }
        adset = self.ad_account.create_ad_set(params=params)
        logger.info(f"AdSet created: {adset.get_id()}")
        return adset

    def create_ad_creative(
        self,
        name: str,
        image_hash: str,
        title: str,
        body: str,
        link_url: str,
        call_to_action: str = "LEARN_MORE",
        page_id: Optional[str] = None
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
                "link": link_url,
                "message": body,
                "name": title,
                "call_to_action": {
                    "type": call_to_action,
                    "value": {"link": link_url}
                }
            }
        }
        params = {
            AdCreative.Field.name: name,
            AdCreative.Field.object_story_spec: object_story_spec
        }
        creative = self.ad_account.create_ad_creative(params=params)
        logger.info(f"Creative created: {creative.get_id()}")
        return creative

    def create_ad(
        self,
        ad_set_id: str,
        creative_id: str,
        name: str,
        status: str = "PAUSED"
    ) -> Ad:
        """
        Create an Ad.
        """
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
        creative = self.create_ad_creative(
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


if __name__ == "__main__":

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

