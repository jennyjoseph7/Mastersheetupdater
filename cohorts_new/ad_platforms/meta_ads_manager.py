import os
import sys 
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
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
    from facebook_business.adobjects.page import Page
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.user import User
    from facebook_business.adobjects.targetingsearch import TargetingSearch
except ImportError:
    raise ImportError("This module requires the facebook_business package to be installed. Please run 'pip install facebook_business'")

from cohorts_new.utils.utility import *
from cohorts_new.utils.common_utils import *

logger = get_logger(__name__)

CAMPAIGN_FIELDS = [
    "id",
    "name",
    "status",
    "objective",
    "created_time",
    "updated_time",
    "start_time",
    "stop_time",
    "daily_budget",
    "lifetime_budget",
    "buying_type",
    "special_ad_categories",
    "objective"
]

ADSET_FIELDS = [
    "id",
    "name",
    "status",
    "campaign_id",
    "daily_budget",
    "lifetime_budget",
    "billing_event",
    "optimization_goal",
    "targeting",
    "start_time",
    "end_time"
]

AD_FIELDS = [
    "id",
    "name",
    "status",
    "adset_id",
    "creative",
    "created_time",
    "updated_time"
]

CREATIVE_FIELDS = [
    "id",
    "name",
    "object_story_spec",
    "image_url",
    "thumbnail_url",
    "body",
    "title"
]

valid_campaign_objectives = [
    "OUTCOME_LEADS", "OUTCOME_SALES", "OUTCOME_ENGAGEMENT", "OUTCOME_AWARENESS", "OUTCOME_TRAFFIC", "OUTCOME_APP_PROMOTION"
]

valid_optimization_goals = [
    "NONE",
    "APP_INSTALLS",
    "AD_RECALL_LIFT",
    "ENGAGED_USERS",
    "EVENT_RESPONSES",
    "IMPRESSIONS",
    "LEAD_GENERATION",
    "QUALITY_LEAD",
    "LINK_CLICKS",
    "OFFSITE_CONVERSIONS",
    "PAGE_LIKES",
    "POST_ENGAGEMENT",
    "QUALITY_CALL",
    "REACH",
    "LANDING_PAGE_VIEWS",
    "VISIT_INSTAGRAM_PROFILE",
    "ENGAGED_PAGE_VIEWS",
    "VALUE",
    "THRUPLAY",
    "DERIVED_EVENTS",
    "APP_INSTALLS_AND_OFFSITE_CONVERSIONS",
    "CONVERSATIONS",
    "IN_APP_VALUE",
    "MESSAGING_PURCHASE_CONVERSION",
    "SUBSCRIBERS",
    "REMINDERS_SET",
    "MEANINGFUL_CALL_ATTEMPT",
    "PROFILE_VISIT",
    "PROFILE_AND_PAGE_ENGAGEMENT",
    "ADVERTISER_SILOED_VALUE",
    "AUTOMATIC_OBJECTIVE",
    "MESSAGING_APPOINTMENT_CONVERSION"
]

valid_call_to_action_values = [
    "BOOK_TRAVEL",
    "CONTACT_US",
    "DONATE",
    "DONATE_NOW",
    "DOWNLOAD",
    "GET_DIRECTIONS",
    "GO_LIVE",
    "INTERESTED",
    "LEARN_MORE",
    "SEE_DETAILS",
    "LIKE_PAGE",
    "MESSAGE_PAGE",
    "RAISE_MONEY",
    "SAVE",
    "SEND_TIP",
    "SHOP_NOW",
    "SIGN_UP",
    "VIEW_INSTAGRAM_PROFILE",
    "INSTAGRAM_MESSAGE",
    "LOYALTY_LEARN_MORE",
    "PURCHASE_GIFT_CARDS",
    "PAY_TO_ACCESS",
    "SEE_MORE",
    "TRY_IN_CAMERA",
    "WHATSAPP_LINK",
    "GET_IN_TOUCH",
    "TRY_NOW",
    "ASK_A_QUESTION",
    "START_A_CHAT",
    "CHAT_NOW",
    "ASK_US",
    "CHAT_WITH_US",
    "BOOK_NOW",
    "CHECK_AVAILABILITY",
    "ORDER_NOW",
    "WHATSAPP_MESSAGE",
    "GET_MOBILE_APP",
    "INSTALL_MOBILE_APP",
    "USE_MOBILE_APP",
    "INSTALL_APP",
    "USE_APP",
    "PLAY_GAME",
    "TRY_DEMO",
    "WATCH_VIDEO",
    "WATCH_MORE",
    "OPEN_LINK",
    "NO_BUTTON",
    "LISTEN_MUSIC",
    "MOBILE_DOWNLOAD",
    "GET_OFFER",
    "GET_OFFER_VIEW",
    "BUY_NOW",
    "BUY_TICKETS",
    "UPDATE_APP",
    "BET_NOW",
    "ADD_TO_CART",
    "SELL_NOW",
    "GET_SHOWTIMES",
    "LISTEN_NOW",
    "GET_EVENT_TICKETS",
    "REMIND_ME",
    "SEARCH_MORE",
    "PRE_REGISTER",
    "SWIPE_UP_PRODUCT",
    "SWIPE_UP_SHOP",
    "PLAY_GAME_ON_FACEBOOK",
    "VISIT_WORLD",
    "OPEN_INSTANT_APP",
    "JOIN_GROUP",
    "GET_PROMOTIONS",
    "SEND_UPDATES",
    "INQUIRE_NOW",
    "VISIT_PROFILE",
    "CHAT_ON_WHATSAPP",
    "EXPLORE_MORE",
    "CONFIRM",
    "JOIN_CHANNEL",
    "MAKE_AN_APPOINTMENT",
    "ASK_ABOUT_SERVICES",
    "BOOK_A_CONSULTATION",
    "GET_A_QUOTE",
    "BUY_VIA_MESSAGE",
    "ASK_FOR_MORE_INFO",
    "VIEW_PRODUCT",
    "VIEW_CHANNEL",
    "WATCH_LIVE_VIDEO",
    "IMAGINE",
    "CALL",
    "MISSED_CALL",
    "CALL_NOW",
    "CALL_ME",
    "APPLY_NOW",
    "BUY",
    "GET_QUOTE",
    "SUBSCRIBE",
    "RECORD_NOW",
    "VOTE_NOW",
    "GIVE_FREE_RIDES",
    "REGISTER_NOW",
    "OPEN_MESSENGER_EXT",
    "EVENT_RSVP",
    "CIVIC_ACTION",
    "SEND_INVITES",
    "REFER_FRIENDS",
    "REQUEST_TIME",
    "SEE_MENU",
    "SEARCH",
    "TRY_IT",
    "TRY_ON",
    "LINK_CARD",
    "DIAL_CODE",
    "FIND_YOUR_GROUPS",
    "START_ORDER"
]


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
        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"
        self.ad_account_id = ad_account_id

        self.page_id = page_id

        if not all([self.app_id, self.app_secret, self.access_token, self.ad_account_id]):
            raise ValueError("Missing Meta credentials. Please configure environment variables.")

        FacebookAdsApi.init(
            app_id          = self.app_id,
            app_secret      = self.app_secret,
            access_token    = self.access_token,
            api_version     = api_version
        )

        self.ad_account = AdAccount(self.ad_account_id)
        logger.info(f"Meta Ads API initialized for account {self.ad_account_id}")


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

    def list_all_campaigns(self):
        # all_fields = list(Campaign.Field.__dict__.values())
        # all_fields = [f for f in all_fields if f is not None]
        # logger.info(f"Fields: {all_fields}")
        result = self.ad_account.get_campaigns(fields=CAMPAIGN_FIELDS)
        return self.cursor_to_json(result)
    
    def get_campaign_by_name(self, name):
        campaigns = self.ad_account.get_campaigns(fields=["name", "id"])
        for c in campaigns:
            if c["name"] == name:
                return c
        return None

    def get_ad_sets_in_campaign(self, campaign_id: str):
        campaign = Campaign(campaign_id)
        result = campaign.get_ad_sets(fields=ADSET_FIELDS)
        return self.cursor_to_json(result)


    def get_ads_in_adset(self, ad_set_id: str):
        adset = AdSet(ad_set_id)
        result = adset.get_ads(fields=AD_FIELDS)
        return self.cursor_to_json(result)


    def get_creative(self, creative_id: str):
        creative = AdCreative(creative_id)
        result = creative.api_get(fields=CREATIVE_FIELDS)
        object_story_spec = result["object_story_spec"]

        logger.info(f"Object Story Spec: {object_story_spec}")

        result["object_story_spec"] = {key :val for key, val in object_story_spec.items()}

        return dict(result)
    

    # _______________________________________________________________________________
    def test_connection(self):
        """Test Meta Ads API connection and permissions.  Prints basic account, page and campaign info."""
        logger.info("----- META API TEST START -----")
        try:
            # 1. Test Ad Account Access
            logger.info("Checking Ad Account access...")
            account = self.ad_account.api_get(fields=["id","name","account_status","currency","timezone_name"])
            # account = self.ad_account.api_get()
            logger.info("Ad Account Details:")
            logger.info(json.dumps(account.export_all_data(), indent=4, default=str))
        except Exception as e:
            raise Exception(f"Ad Account access failed: {e}")

        try:
            # 2. Test Campaign Fetch
            logger.info("\nFetching campaigns...")
            campaigns = self.ad_account.get_campaigns(
                fields=[
                    "id",
                    "name",
                    "status",
                    "objective"
                ],
                params={"limit": 5}
            )

            # campaigns = self.ad_account.get_campaigns(params={"limit": 5})

            campaign_list = list(campaigns)
                
            if campaign_list:
                logger.info("Campaigns found:")
                for c in campaign_list:
                    logger.info(c.export_all_data())
            else:
                logger.info("No campaigns found")

        except Exception as e:
            raise Exception(f"Campaign access failed: {e}")


        try:
            # 3. Test Page Access
            print("\nChecking Page access...")

            

            page = Page(self.page_id)
            page_info = page.api_get(fields=[
                "id",
                "name",
                "fan_count"
            ])

            print("Page Details:")
            print(page_info)

        except Exception as e:
            print("Page access failed")
            print(e)


        print("\n----- META API TEST COMPLETE -----")

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
        import pytz

        ist = pytz.timezone('Asia/Kolkata')
        logger.info(f"Creating ad set: {name}")
        start_time = (datetime.now(ist) + timedelta(minutes=10)).isoformat()
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

        if destination_url:
            params[AdSet.Field.promoted_object] = {"link": destination_url}

        adset = self.ad_account.create_ad_set(params=params)
        logger.info(f"AdSet created: {adset.get_id()}")
        return adset

    def create_image_ad_creative(
            self,
            name: str,
            image_hash: str,
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
    
    def preview_creative(self, creative_id: str, ad_format: str = "DESKTOP_FEED_STANDARD"):
        """
        Get rendered HTML preview of an ad creative for a specific placement.
        Same preview as shown in Meta Ads Manager.
        """
        AD_FORMATS = [
            "DESKTOP_FEED_STANDARD",
            "MOBILE_FEED_STANDARD",
            "INSTAGRAM_STANDARD",
            "INSTAGRAM_STORY",
            "MOBILE_STORY",
            "DESKTOP_RIGHT_COLUMN_STANDARD",
            "AUDIENCE_NETWORK_INSTREAM_VIDEO",
            "FACEBOOK_REELS",
            "INSTAGRAM_REELS"
        ]

        if ad_format not in AD_FORMATS:
            raise ValueError(f"Invalid ad format: {ad_format}. Supported formats: {AD_FORMATS}")

        creative = AdCreative(creative_id)

        previews = creative.get_previews(params={
            "ad_format": ad_format
        })

        results = []
        for p in previews:
            results.append({
                "format": ad_format,
                "body": p.get("body"),      # HTML iframe
            })

        return results

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


if __name__ == "__main__":

    app_id =        "your_app_id"
    app_secret =    "your_app_secret"
    access_token =  "your_access_token"
    page_id =       "your_page_id"
    account_id =    "your_account_id"




    manager = MetaAdsManager(
        app_id=app_id,
        app_secret=app_secret,
        access_token=access_token,
        ad_account_id=account_id,
        page_id=page_id
    )


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

    # adset = manager.create_ad_set(
    #     campaign_id=tata_sierra_campaign_id,
    #     name="Tata Sierra - India Audience Targeting Test",
    #     daily_budget=10000,
    #     targeting=targeting,
    #     # destination_url="https://cars.tatamotors.com/sierra/ice.html",
    #     optimization_goal="LANDING_PAGE_VIEWS",
    #     billing_event="IMPRESSIONS"
    # )

    # logger.info(f"Adset created: {adset}")


    adset_for_tata_sierra = "120245325100150664"

    creative = manager.create_image_ad_creative(
        name="Tata Sierra Creative",
        image_hash=image_hash,
        title="The Icon Returns 🚙",
        body="Experience the all-new Tata Sierra. Built for adventure.",
        link_url="https://cars.tatamotors.com/sierra/ice.html",
        call_to_action = "LEARN_MORE",
        description="Explore design, features & book your drive"
    )

    logger.info(f"Creative created: {creative}")

    



    # logger.info(f"Campaign created: {tata_sierra_campaign}")


    assert False



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

