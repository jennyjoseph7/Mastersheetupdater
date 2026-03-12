import os
import sys 
import traceback
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from typing import Optional, Literal
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adimage import AdImage

from cohorts_new.utils.utility import *
from cohorts_new.utils.common_utils import *

logger = get_logger(__name__)

class MetaAdsManager:
    def __init__(
            self,
            app_id: Optional[str] = None,
            app_secret: Optional[str] = None,
            access_token: Optional[str] = None,
            ad_account_id: Optional[str] = None
        ):

        self.app_id = app_id 
        self.app_secret = app_secret 
        self.access_token = access_token 
        self.ad_account_id = ad_account_id 

        if not all([self.app_id, self.app_secret, self.access_token, self.ad_account_id]):
            raise ValueError(
                "Missing required parameters: app_id, app_secret, access_token, ad_account_id"
                "Credentials not found. Please set app_id, app_secret, access_token, ad_account_id"
            )
        FacebookAdsApi.init(app_id=self.app_id, app_secret=self.app_secret, access_token=self.access_token)
        self.ad_account = AdAccount(self.ad_account_id)
        logger.info(f"MetaAdsManager initialized with \n app_id: '{self.app_id}', app_secret: '{self.app_secret}', access_token: '{self.access_token}', ad_account_id: '{self.ad_account_id}'") 
    
    def upload_image(self, image_path: str, image_name: Optional[str] = None) -> str:
        try:
            image = AdImage(parent_id=self.ad_account_id)
            image[AdImage.Field.filename] = image_path
            if image_name:
                image[AdImage.Field.name] = image_name
            image.remote_create()
            image_hash = image[AdImage.Field.hash]
            return image_hash
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            raise e

    def create_campaign(self, name: str, objective: str = "OUTCOME_TRAFFIC", status: str = "PAUSED", special_ad_categories: Optional[list] = None) -> Campaign:
        try:
            params = {Campaign.Field.name: name, Campaign.Field.objective: objective, Campaign.Field.status: status,}
            if special_ad_categories:
                params[Campaign.Field.special_ad_categories] = special_ad_categories
            params['is_adset_budget_sharing_enabled'] = False
            campaign = self.ad_account.create_campaign(params=params)
            return campaign
        except Exception as e:
            logger.error(f"Error creating campaign: {str(e)}")
            raise e
    def create_ad_set(self, 
            campaign_id: str, name: str, daily_budget: int, 
            targeting: dict, optimization_goal: str = "LINK_CLICKS", 
            billing_event: str = "IMPRESSIONS", bid_amount: Optional[int] = None) -> AdSet:
        try:
            params = {
                AdSet.Field.name: name,
                AdSet.Field.campaign_id: campaign_id,
                AdSet.Field.daily_budget: daily_budget,
                AdSet.Field.billing_event: billing_event,
                AdSet.Field.optimization_goal: optimization_goal,
                AdSet.Field.targeting: targeting,
                AdSet.Field.status: 'PAUSED',
            }
            if bid_amount:
                params[AdSet.Field.bid_amount] = bid_amount
            else:
                params[AdSet.Field.bid_amount] = int(daily_budget * 0.1)
            ad_set = self.ad_account.create_ad_set(params=params)
            return ad_set

        except Exception as e:
            logger.error(f"Error creating ad set: {str(e)}")
            raise e



