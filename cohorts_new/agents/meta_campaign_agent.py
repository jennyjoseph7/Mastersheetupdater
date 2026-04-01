"""
Meta Ad Agent
=============
Generates a full Meta Ads tree (Campaign → AdSet → Ad → Creative)
from customer/cohort/affinity inputs and scraped product context.

All inputs are accepted at __init__. Scraping happens at init time via
your existing fetch functions. Generation is strictly sequential —
one Campaign, then its AdSets one by one, then creatives one by one —
to keep token usage predictable.

"""

import json
from typing import Optional
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import json
from pydantic import BaseModel
import plotly.graph_objects as go
from ai_service import ai_service_app
from cohorts_new.utils.utility import *
from cohorts_new.utils.common_utils import *
from typing import *
import traceback
import requests 
import numpy as np
from typing import List, Dict

logger = get_logger(__name__)

valid_campaign_objectives = ["OUTCOME_LEADS", "OUTCOME_SALES", "OUTCOME_ENGAGEMENT", "OUTCOME_AWARENESS", "OUTCOME_TRAFFIC", "OUTCOME_APP_PROMOTION"]
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

valid_billing_events = [    
    "APP_INSTALLS"
    "CLICKS"
    "IMPRESSIONS"
    "LINK_CLICKS"
    "OFFER_CLAIMS"
    "PAGE_LIKES"
    "POST_ENGAGEMENT"
    "VIDEO_VIEWS"
]


class MetaAdCampaignAgent(UtilityMixin):
    def __init__(
        self,
        source: Optional[dict] = None,
        classified_cohort: Optional[dict] = None,
        affinity_score: Optional[dict] = None,
        brochure_url: Optional[str] = None,
        product_website_url: Optional[str] = None,
        num_of_campaign_ideas: int = 1,
        model_identifier: str = "azure-gpt-4o",
        batch_size: int = 1,
        additional_instruction: Optional[str] = None
    ):
        
        self.source = self._load_json(source=source)
        self.classified_cohort = classified_cohort
        self.affinity_score = affinity_score

        self.brochure_url = brochure_url
        self.product_website_url = product_website_url

        self.brochure_content: dict = (self.fetch_brochure_content(brochure_url=self.brochure_url) if self.brochure_url else {})
        self.product_website_content: dict = (self.fetch_product_details_from_website(website_url=self.product_website_url) if self.product_website_url else {})

        self.num_of_campaign_ideas = num_of_campaign_ideas
        self.model_identifier = model_identifier
        self.batch_size = batch_size
        self.additional_instruction = additional_instruction

        self.llm = lambda messages: ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        self._context: str = ""

        
    @property
    def campaign_schema(self) -> str:
        return json.dumps(
            [
                {
                    "campaign_name": "string",
                    "campaign_id" : "string",
                    "objective": (
                        "OUTCOME_LEADS", "OUTCOME_SALES", "OUTCOME_ENGAGEMENT", "OUTCOME_AWARENESS", "OUTCOME_TRAFFIC", "OUTCOME_APP_PROMOTION"
                    ),
                    "special_ad_category": (
                        "NONE | CREDIT | EMPLOYMENT | HOUSING | ISSUES_ELECTIONS_POLITICS"
                    ),
                    "buying_type": "AUCTION | REACH_AND_FREQUENCY",
                    "campaign_budget_optimisation": True,
                    "daily_budget_usd": 0.0,
                    "lifetime_budget_usd": 0.0,
                    "bid_strategy": (
                        "LOWEST_COST_WITHOUT_CAP | LOWEST_COST_WITH_BID_CAP | "
                        "COST_CAP | VALUE_OPTIMISATION"
                    ),
                    "target_audience_summary": "string — plain language summary of who this reaches",
                    "strategy": "string — 2-3 sentences tying cohort/affinity data to this campaign",
                    "key_message": "string — core value proposition to communicate",
                }
            ],
            indent=2,
        )
    
    def _build_context(self) -> str:
        parts = ["## Audience Intelligence"]
        if self.source:
            parts.append(f"### Raw Customer Interaction\n{json.dumps(self.source, indent=2)}")
        if self.classified_cohort:
            parts.append(f"### Classified Cohort\n{json.dumps(self.classified_cohort, indent=2)}")
        if self.affinity_score:
            parts.append(f"### Affinity Scores\n{json.dumps(self.affinity_score, indent=2)}")

        if self.product_website_url:
            parts.append(f"### Product Website URL\n{self.product_website_url}")
        if self.brochure_url:
            parts.append(f"### Brochure URL\n{self.brochure_url}")
            
        parts.append("## Product Context")
 
        brochure_text = self.brochure_content.get("page_content", "")
        website_text = self.product_website_content.get("page_content", "")

        if brochure_text:
            parts.append(f"### Brochure\n{brochure_text.strip()}")
        if website_text:
            parts.append(f"### Website\n{website_text.strip()}")
        if not brochure_text and not website_text:
            parts.append("No product content provided — infer from audience signals.")

        if self.additional_instruction:
            parts.append(f"## Additional Instruction\n{self.additional_instruction}")

        return "\n\n".join(parts)
 
    def _call_llm_json(self, prompt: str) -> list | dict:
        """Wraps exec_json_llm_with_retry using self.llm."""
        messages = [{"role": "user", "content": prompt}]
        return self.exec_json_llm_with_retry(self.llm, messages=messages)
    
    def _coerce_list(self, result: Any) -> list:
        """Ensure LLM result is always a list."""
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return list(result.values())
        return [result]
    
    def yield_items(self, items: list, chunk_size: int = None):
        """Yield successive chunks of `chunk_size` from `items`."""
        size = chunk_size or self.batch_size or 1
        for i in range(0, len(items), size):
            yield items[i : i + size]

    def _plan_campaign_ids(self) -> List[str]:
        """One cheap call → list of N distinct snake_case campaign IDs."""

        prompt = f"""
        {self._context}
        ---
        You are a Meta Ads strategist planning a campaign structure.

        Rules:
        1. Consider Product Information, Audience Intelligence, and Product Context when planning campaign ids.
        
        Generate exactly {self.num_of_campaign_ideas} distinct snake_case campaign IDs.
        Each ID should reflect a unique objective or audience angle (e.g. smb_awareness_remote_teams).
        All IDs must be unique — no duplicates.
        
        Return ONLY a JSON array of strings. Example: ["id_one", "id_two"]
        No markdown. No explanation. JSON array only."""
        
        llm_response = self._call_llm_json(prompt=prompt)
        return self._coerce_list(llm_response)
    
    def _generate_campaigns(self, campaign_ids: List[str]) -> List[dict]:
        """Generate campaign objects in batches, one batch per LLM call."""
        results = []
        for batch in self.yield_items(campaign_ids, self.batch_size):
            print(f"Batch: {batch}")
            ids_str = json.dumps(batch)
            prompt = f"""
            {self._context}
            ---
            You are a Meta Ads strategist.
            
            Generate full campaign objects for these campaign IDs: {ids_str}
            Each campaign must have a distinct objective and audience angle matching its ID.
            Do NOT reuse angles or objectives across campaigns.
            
            Return ONLY a JSON array of objects (one per ID, in the same order).
            Each object must match this schema exactly:
            {self.campaign_schema}
            
            No markdown. No explanation. JSON array only."""
            batch_result = self._call_llm_json(prompt)
            results.extend(self._coerce_list(batch_result))
        return results
    
    def run(self):
        self._context = self._build_context()
        campaign_ids = self._plan_campaign_ids()

        campaigns = self._generate_campaigns(campaign_ids)

        return {"campaign_ids": campaign_ids, "campaigns": campaigns}

# -------------------------------------------------------------------------------------------------------------------------------------------------------------# 
# -------------------------------------------------------------------------------------------------------------------------------------------------------------# 

class MetaAdAdsetAgent(UtilityMixin):
    def __init__(
        self,
        source: Optional[dict] = None,
        classified_cohort: Optional[dict] = None,
        affinity_score: Optional[dict] = None,
        brochure_url: Optional[str] = None,
        product_website_url: Optional[str] = None,
        fb_campaigns: Optional[List[dict]] = None,
        num_of_adsets: int = 1,
        model_identifier: str = "azure-gpt-4o",
        batch_size: int = 1,
        additional_instruction: Optional[str] = None
    ):
        
        self.source = self._load_json(source=source)
        self.classified_cohort = classified_cohort
        self.affinity_score = affinity_score

        self.brochure_url = brochure_url
        self.product_website_url = product_website_url

        self.brochure_content: dict = (self.fetch_brochure_content(brochure_url=self.brochure_url) if self.brochure_url else {})
        self.product_website_content: dict = (self.fetch_product_details_from_website(website_url=self.product_website_url) if self.product_website_url else {})

        self.fb_campaigns = fb_campaigns
        self.num_of_adsets = num_of_adsets
        self.model_identifier = model_identifier
        self.batch_size = batch_size
        self.additional_instruction = additional_instruction
        
        self.llm = lambda messages: ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        
        self._context = ""


    @property
    def adset_schema(self) -> str:
        return json.dumps(
            [
                {
                    "adset_name": "string",
                    "adset_id": "string",
                    "campaign_id": "string - Reference to the campaign this adset belongs to. If campaign data is not there, keep it None.",
                    "title" : "Title for the adset.",
                    "daily_budget": 10000,
                    "optimization_goal" : "\n".join(valid_optimization_goals),
                    "billing_event" : "\n".join(valid_billing_events),
                    "targeting": {
                        "age_min": 18,
                        "age_max": 65,
                        "genders": "0=All | 1=Male | 2=Female",
                        "targeting_automation" : {
                            "advantage_audience" : "0=No (0 means static audience) | 1=Yes (1 means AI will target appropriate audience)",
                        },
                        "geo_locations": {
                            "countries": ["IN", "US", "CA"],
                            "cities": [
                                {"key": "string", "name": "string", "region": "string"}
                            ],
                        },
                    },
                }
            ],
            indent=2,
        )
    
    def _build_context(self) -> str:
        parts = ["## Audience Intelligence"]
        if self.source:
            parts.append(f"### Raw Customer Interaction\n{json.dumps(self.source, indent=2)}")
        if self.classified_cohort:
            parts.append(f"### Classified Cohort\n{json.dumps(self.classified_cohort, indent=2)}")
        if self.affinity_score:
            parts.append(f"### Affinity Scores\n{json.dumps(self.affinity_score, indent=2)}")

        if self.product_website_url:
            parts.append(f"### Product Website URL\n{self.product_website_url}")
        if self.brochure_url:
            parts.append(f"### Brochure URL\n{self.brochure_url}")
 
        parts.append("## Product Context")
 
        brochure_text = self.brochure_content.get("page_content", "")
        website_text = self.product_website_content.get("page_content", "")

        if brochure_text:
            parts.append(f"### Brochure\n{brochure_text.strip()}")
        if website_text:
            parts.append(f"### Website\n{website_text.strip()}")
        if not brochure_text and not website_text:
            parts.append("No product content provided — infer from audience signals.")

        if self.additional_instruction:
            parts.append(f"## Additional Instruction\n{self.additional_instruction}")
 
        return "\n\n".join(parts)
 
    def _call_llm_json(self, prompt: str) -> list | dict:
        """Wraps exec_json_llm_with_retry using self.llm."""
        messages = [{"role": "user", "content": prompt}]
        return self.exec_json_llm_with_retry(self.llm, messages=messages)
    
    def _coerce_list(self, result: Any) -> list:
        """Ensure LLM result is always a list."""
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return list(result.values())
        return [result]
    
    def yield_items(self, items: list, chunk_size: int = None):
        """Yield successive chunks of `chunk_size` from `items`."""
        size = chunk_size or self.batch_size or 1
        for i in range(0, len(items), size):
            yield items[i : i + size]


    def _generate_adset_ids(self) -> list:
        num_of_campaigns = len(self.fb_campaigns)
        get_campaign_ids = [campaign.get("campaign_id", None) for campaign in self.fb_campaigns]

        # So if num_of_adsets is 2 and num_of_campaign ideas are 2, then we get 2 unique adset ids per campaign means 4.
        all_adset_ids = []
        for batch in self.yield_items(self.fb_campaigns, self.batch_size):
            campaign_ids_batch = [c.get("campaign_id") for c in batch]
            ids_str = json.dumps(campaign_ids_batch)
            prompt = f"""
            {self._context}
            ---
            You are a Meta Ads strategist planning an adset structure.

            Rules:
            1. Consider Product Information, Audience Intelligence, and Product Context when planning adset ids.
            2. Each campaign must have exactly {self.num_of_adsets} adset(s).

            Generate exactly {self.num_of_adsets} distinct snake_case adset IDs for EACH of these campaign IDs: {ids_str}
            Each adset ID should reflect a unique audience segment or targeting angle for its campaign
            All IDs must be unique across all campaigns — no duplicates.

            Return ONLY a JSON object where each key is a campaign_id and the value is an array of adset ID strings.
            Example: {{"campaign_id_one": ["adset_id_1", "adset_id_2"], "campaign_id_two": ["adset_id_3", "adset_id_4"]}}
            No markdown. No explanation. JSON object only."""

            llm_response = self._call_llm_json(prompt=prompt)
            if isinstance(llm_response, dict):
                for adset_ids in llm_response.values():
                    if isinstance(adset_ids, list):
                        all_adset_ids.extend(adset_ids)
            elif isinstance(llm_response, list):
                all_adset_ids.extend(llm_response)
        return all_adset_ids

    def _generate_adsets(self, adset_ids: List[str]) -> List[dict]:
        """Generate adset objects in batches, one batch per LLM call."""
        results = []
        for batch in self.yield_items(adset_ids, self.batch_size):
            print(f"Adset Batch: {batch}")
            ids_str = json.dumps(batch)

            # Build a campaign context summary for the LLM
            campaigns_summary = json.dumps(self.fb_campaigns, indent=2,)

            prompt = f"""
            {self._context}
            ---
            You are a Meta Ads strategist.

            Here are the parent campaigns these adsets belong to:
            {campaigns_summary}

            Generate full adset objects for these adset IDs: {ids_str}
            Each adset must:
            - Be linked to the most relevant parent campaign based on its ID naming.
            - Have a distinct targeting angle matching its ID.
            - Not reuse targeting angles or audience segments across adsets.

            Return ONLY a JSON array of objects (one per ID, in the same order).
            Each object must match this schema exactly:
            {self.adset_schema}

            No markdown. No explanation. JSON array only."""

            batch_result = self._call_llm_json(prompt)
            results.extend(self._coerce_list(batch_result))
        return results

    def run(self):
        self._context = self._build_context()
        adset_ids = self._generate_adset_ids()

        adsets = self._generate_adsets(adset_ids)

        return {"adset_ids": adset_ids, "adsets": adsets}
    


# -------------------------------------------------------------------------------------------------------------------------------------------------------------# 
# -------------------------------------------------------------------------------------------------------------------------------------------------------------# 


class MetaAdCreativeAgent(UtilityMixin):
    def __init__(
        self,
        source: Optional[dict] = None,
        classified_cohort: Optional[dict] = None,
        affinity_score: Optional[dict] = None,
        brochure_url: Optional[str] = None,
        product_website_url: Optional[str] = None,
        fb_campaigns: Optional[List[dict]] = None,
        fb_adsets: Optional[List[dict]] = None,
        num_of_creatives: int = 1,
        model_identifier: str = "azure-gpt-4o",
        batch_size: int = 1,
        additional_instruction: Optional[str] = None
    ):
        self.source = self._load_json(source=source)
        self.classified_cohort = classified_cohort
        self.affinity_score = affinity_score

        self.brochure_url = brochure_url
        self.product_website_url = product_website_url

        self.brochure_content: dict = (self.fetch_brochure_content(brochure_url=self.brochure_url) if self.brochure_url else {})
        self.product_website_content: dict = (self.fetch_product_details_from_website(website_url=self.product_website_url) if self.product_website_url else {})

        self.fb_campaigns = fb_campaigns or []
        self.fb_adsets = fb_adsets or []
        self.num_of_creatives = num_of_creatives
        self.model_identifier = model_identifier
        self.batch_size = batch_size
        self.additional_instruction = additional_instruction

        self.llm = lambda messages: ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        self._context: str = ""

    @property
    def creative_schema(self) -> str:
        return json.dumps(
            [
                {
                    "creative_id": "string — snake_case unique identifier",
                    "adset_id": "string — parent adset this creative belongs to",
                    "campaign_id": "string — parent campaign this creative belongs to",
                    "creative_name": "string",
                    "image_hash": None,
                    "video_hash": None,
                    "status": "PAUSED",
                    "format": "IMAGE",
                    "headline": "string — max 40 chars, punchy and benefit-driven",
                    "primary_text": "string — max 125 chars, hooks the audience immediately",
                    "description": "string — max 30 chars, supports the headline",
                    "call_to_action": "\n".join(valid_call_to_action_values),
                    "destination_url": "string — landing page URL or product page URL or brochure URL",
                }
            ],
            indent=2,
        )

    def _build_context(self) -> str:
        parts = ["## Audience Intelligence"]
        if self.source:
            parts.append(f"### Raw Customer Interaction\n{json.dumps(self.source, indent=2)}")
        if self.classified_cohort:
            parts.append(f"### Classified Cohort\n{json.dumps(self.classified_cohort, indent=2)}")
        if self.affinity_score:
            parts.append(f"### Affinity Scores\n{json.dumps(self.affinity_score, indent=2)}")


        if self.product_website_url:
            parts.append(f"### Product Website URL\n{self.product_website_url}")
        if self.brochure_url:
            parts.append(f"### Brochure URL\n{self.brochure_url}")


        parts.append("## Product Context")

        brochure_text = self.brochure_content.get("page_content", "")
        website_text = self.product_website_content.get("page_content", "")

        if brochure_text:
            parts.append(f"### Brochure\n{brochure_text.strip()}")
        if website_text:
            parts.append(f"### Website\n{website_text.strip()}")
        if not brochure_text and not website_text:
            parts.append("No product content provided — infer from audience signals.")

        if self.fb_campaigns:
            slim_campaigns = [
                {
                    "campaign_id": c.get("campaign_id"),
                    "campaign_name": c.get("campaign_name"),
                    "objective": c.get("objective"),
                    "target_audience_summary": c.get("target_audience_summary"),
                    "strategy": c.get("strategy"),
                    "key_message": c.get("key_message"),
                }
                for c in self.fb_campaigns
            ]
            parts.append(f"## Campaign Context\n{json.dumps(slim_campaigns, indent=2)}")

        if self.fb_adsets:
            slim_adsets = [
                {
                    "adset_id": a.get("adset_id"),
                    "adset_name": a.get("adset_name"),
                    "title": a.get("title"),
                    "targeting": a.get("targeting"),
                }
                for a in self.fb_adsets
            ]
            parts.append(f"## Adset Context\n{json.dumps(slim_adsets, indent=2)}")

        if self.additional_instruction:
            parts.append(f"## Additional Instructions\n{self.additional_instruction}")

        return "\n\n".join(parts)

    def _call_llm_json(self, prompt: str) -> list | dict:
        messages = [{"role": "user", "content": prompt}]
        return self.exec_json_llm_with_retry(self.llm, messages=messages)

    def _coerce_list(self, result: Any) -> list:
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return list(result.values())
        return [result]

    def yield_items(self, items: list, chunk_size: int = None):
        size = chunk_size or self.batch_size or 1
        for i in range(0, len(items), size):
            yield items[i : i + size]

    def _plan_creative_ids(self) -> List[str]:
        """One cheap call → list of N distinct snake_case creative IDs per adset."""

        adset_ids = [a.get("adset_id") for a in self.fb_adsets] if self.fb_adsets else []
        adset_ids_str = json.dumps(adset_ids)

        prompt = f"""
        {self._context}
        ---
        You are a Meta Ads creative strategist planning a creative structure.

        Rules:
        1. Consider Audience Intelligence, Campaign Context, Adset Context, and Product Context when planning creative ids.
        2. Generate exactly {self.num_of_creatives} creative ID(s) per adset.
        3. Each creative ID should reflect a unique copy angle or format variation
           (e.g. sierra_ice_young_professional_video, sierra_ice_family_carousel_weekend).
        4. All IDs must be unique — no duplicates.

        Adset IDs to generate creatives for: {adset_ids_str}

        Return ONLY a JSON object where each key is an adset_id and the value is an array of creative ID strings.
        Example: {{"adset_id_one": ["creative_id_1", "creative_id_2"], "adset_id_two": ["creative_id_3"]}}
        No markdown. No explanation. JSON object only."""

        llm_response = self._call_llm_json(prompt=prompt)

        # Flatten to list while preserving adset mapping for later use
        self._creative_adset_map: dict = llm_response if isinstance(llm_response, dict) else {}
        all_ids = []
        for ids in self._creative_adset_map.values():
            if isinstance(ids, list):
                all_ids.extend(ids)
        return all_ids

    def _generate_creatives(self, creative_ids: List[str]) -> List[dict]:
        """Generate creative objects in batches, one batch per LLM call."""
        results = []
        for batch in self.yield_items(creative_ids, self.batch_size):
            print(f"Creative Batch: {batch}")
            ids_str = json.dumps(batch)

            prompt = f"""
            {self._context}
            ---
            You are a Meta Ads creative strategist.

            Generate full creative objects for these creative IDs: {ids_str}

            Rules:
            1. Infer the parent adset_id and campaign_id from the creative ID naming convention.
            2. Each creative must have a distinct copy angle and format — do NOT reuse angles across creatives.
            3. Tailor headline, primary_text, and visual_direction to the specific audience defined in the adset targeting.
            4. Anchor the key message to the parent campaign's objective and key_message.
            5. visual_direction should be actionable enough for a creative team to brief a designer or photographer.

            Return ONLY a JSON array of objects (one per ID, in the same order).
            Each object must match this schema exactly:
            {self.creative_schema}

            No markdown. No explanation. JSON array only."""

            batch_result = self._call_llm_json(prompt)
            results.extend(self._coerce_list(batch_result))
        return results

    def run(self):
        self._context = self._build_context()
        creative_ids = self._plan_creative_ids()
        creatives = self._generate_creatives(creative_ids)

        return {
            "creative_ids": creative_ids,
            "creatives": creatives,
            "creative_adset_map": self._creative_adset_map,
        }


# -------------------------------------------------------------------------------------------------------------------------------------------------------------# 
# -------------------------------------------------------------------------------------------------------------------------------------------------------------# 

class MetaAdAgent(UtilityMixin):
 
    def __init__(
        self,
        source: Optional[dict] = None,
        classified_cohort: Optional[dict] = None,
        affinity_score: Optional[dict] = None,
        brochure_url: Optional[str] = None,
        product_website_url: Optional[str] = None,
        num_of_campaign_ideas: int = 1,
        num_of_adsets: int = 1,
        num_of_ad_creatives: int = 1,
        model_identifier: str = "azure-gpt-4o",
        batch_size: int = 1,
    ):
        if not any([source, classified_cohort, affinity_score]):
            raise ValueError(
                "Provide at least one of: source, classified_cohort, affinity_score."
            )
 
        self.source = self._load_json(source=source)
        self.classified_cohort = classified_cohort
        self.affinity_score = affinity_score
 
        self.brochure_url = brochure_url
        self.product_website_url = product_website_url
 
        self.brochure_content: dict = (
            self.fetch_brochure_content(brochure_url=self.brochure_url)
            if self.brochure_url
            else {}
        )
        self.product_website_content: dict = (
            self.fetch_product_details_from_website(
                website_url=self.product_website_url
            )
            if self.product_website_url
            else {}
        )
 
        self.num_of_campaign_ideas = num_of_campaign_ideas
        self.num_of_adsets = num_of_adsets
        self.num_of_ad_creatives = num_of_ad_creatives
        self.batch_size = batch_size
 
        self.model_identifier = model_identifier
        self.llm = lambda messages: ai_service_app.get_llm_response(
            messages=messages,
            model_identifier=self.model_identifier,
        )
 
        self._context: str = ""
 
    # ─────────────────────────────────────────────────────────────────────────
    # Schemas
    # ─────────────────────────────────────────────────────────────────────────
 
    @property
    def campaign_schema(self) -> str:
        return json.dumps(
            [
                {
                    "campaign_name": "string",
                    "campaign_id" : "string",
                    "objective": (
                        "OUTCOME_LEADS", "OUTCOME_SALES", "OUTCOME_ENGAGEMENT", "OUTCOME_AWARENESS", "OUTCOME_TRAFFIC", "OUTCOME_APP_PROMOTION"
                    ),
                    "special_ad_category": (
                        "NONE | CREDIT | EMPLOYMENT | HOUSING | ISSUES_ELECTIONS_POLITICS"
                    ),
                    "buying_type": "AUCTION | REACH_AND_FREQUENCY",
                    "campaign_budget_optimisation": True,
                    "daily_budget_usd": 0.0,
                    "lifetime_budget_usd": 0.0,
                    "bid_strategy": (
                        "LOWEST_COST_WITHOUT_CAP | LOWEST_COST_WITH_BID_CAP | "
                        "COST_CAP | VALUE_OPTIMISATION"
                    ),
                    "target_audience_summary": "string — plain language summary of who this reaches",
                    "strategy": "string — 2-3 sentences tying cohort/affinity data to this campaign",
                    "key_message": "string — core value proposition to communicate",
                }
            ],
            indent=2,
        )
 
    @property
    def adset_schema(self) -> str:
        return json.dumps(
            [
                {
                    "adset_name": "string",
                    "adset_id": "string",
                    "targeting": {
                        "age_min": 18,
                        "age_max": 65,
                        "genders": "0=All | 1=Male | 2=Female",
                        "geo_locations": {
                            "countries": ["IN", "US"],
                            "cities": [
                                {"key": "string", "name": "string", "region": "string"}
                            ],
                            "location_types": ["home", "recent"],
                        },
                        "interests": ["string 1", "string 2", "string 3"],
                        "behaviours": ["string 1", "string 2", "string 3"],
                        "custom_audiences": ["string 1", "string 2", "string 3"],
                        "lookalike_audiences": ["string 1", "string 2", "string 3"],
                        "excluded_custom_audiences": [
                            "string 1",
                            "string 2",
                            "string 3",
                        ],
                        "publisher_platforms": [
                            "facebook",
                            "instagram",
                            "audience_network",
                            "messenger",
                        ],
                        "facebook_positions": [
                            "feed",
                            "video_feeds",
                            "marketplace",
                            "story",
                            "search",
                            "instream_video",
                        ],
                        "instagram_positions": ["stream", "story", "reels", "explore"],
                        "device_platforms": "mobile | desktop | all",
                        "user_os": ["iOS", "Android"],
                    },
                    "budget_type": "DAILY | LIFETIME",
                    "budget_usd": 0.0,
                    "bid_strategy": (
                        "LOWEST_COST_WITHOUT_CAP | LOWEST_COST_WITH_BID_CAP | "
                        "COST_CAP | VALUE_OPTIMISATION"
                    ),
                    "bid_amount_usd": 0.0,
                    "optimization_goal": (
                        "REACH | IMPRESSIONS | LINK_CLICKS | LANDING_PAGE_VIEWS | "
                        "LEAD_GENERATION | CONVERSIONS | VALUE | APP_INSTALLS | "
                        "VIDEO_VIEWS | THRUPLAY | POST_ENGAGEMENT | PAGE_LIKES"
                    ),
                    "billing_event": (
                        "IMPRESSIONS | LINK_CLICKS | APP_INSTALLS | VIDEO_VIEWS | THRUPLAY"
                    ),
                    "pacing_type": "standard | day_parting",
                    "day_parting_schedule": [],
                    "start_time": "ISO-8601 or null",
                    "end_time": "ISO-8601 or null",
                    "attribution_setting": {
                        "click_window_days": 7,
                        "view_window_days": 1,
                        "dataset_id": "string or null",
                    },
                    "frequency_cap": {
                        "max_frequency": 3,
                        "interval_days": 7,
                    },
                }
            ],
            indent=2,
        )
 
    @property
    def creative_schema(self) -> str:
        return json.dumps(
            [
                {
                    "ad_name": "string",
                    "ad_id": "string",
                    "status": "ACTIVE | PAUSED",
                    "format": (
                        "SINGLE_IMAGE | CAROUSEL | VIDEO | COLLECTION | INSTANT_EXPERIENCE"
                    ),
                    "headline": "string — max 40 chars",
                    "primary_text": "string — max 125 chars (main ad body copy)",
                    "description": "string — max 30 chars (shown under link preview)",
                    "display_link": "string — vanity URL shown on ad e.g. example.com/offer",
                    "cta": (
                        "LEARN_MORE | SHOP_NOW | SIGN_UP | GET_QUOTE | "
                        "CONTACT_US | BOOK_NOW | DOWNLOAD | SUBSCRIBE | WATCH_MORE"
                    ),
                    "image_brief": "null",
                    "video_brief": "null",
                    "carousel_cards": "null",
                    "pixel_id": "string or null",
                    "conversion_event": (
                        "PURCHASE | LEAD | COMPLETE_REGISTRATION | ADD_TO_CART | null"
                    ),
                    "url_parameters": (
                        "utm_source=facebook&utm_medium=paid"
                        "&utm_campaign={{campaign.name}}&utm_content={{ad.name}}"
                    ),
                    "landing_page_url": "string — final destination URL",
                    "landing_page_note": (
                        "string — what the LP should emphasise for this specific audience"
                    ),
                }
            ],
            indent=2,
        )
    
    # "carousel_cards": [
    #                     {
    #                         "card_headline": "string",
    #                         "card_description": "string",
    #                         "card_cta": "string",
    #                         "card_image_brief": "string",
    #                     }
    #                 ],
 
 
    def _build_context(self) -> str:
        parts = ["## Audience Intelligence"]
        if self.source:
            parts.append(
                f"### Raw Customer Interaction\n{json.dumps(self.source, indent=2)}"
            )
        if self.classified_cohort:
            parts.append(
                f"### Classified Cohort\n{json.dumps(self.classified_cohort, indent=2)}"
            )
        if self.affinity_score:
            parts.append(
                f"### Affinity Scores\n{json.dumps(self.affinity_score, indent=2)}"
            )
 
        parts.append("## Product Context")
 
        brochure_text = self.brochure_content.get("page_content", "")
        website_text = self.product_website_content.get("page_content", "")
 
        if brochure_text:
            parts.append(f"### Brochure\n{brochure_text.strip()}")
        if website_text:
            parts.append(f"### Website\n{website_text.strip()}")
        if not brochure_text and not website_text:
            parts.append("No product content provided — infer from audience signals.")
 
        return "\n\n".join(parts)
 
    def _call_llm_json(self, prompt: str) -> list | dict:
        """Wraps exec_json_llm_with_retry using self.llm."""
        messages = [{"role": "user", "content": prompt}]
        return self.exec_json_llm_with_retry(self.llm, messages=messages)
 
    def _coerce_list(self, result: Any) -> list:
        """Ensure LLM result is always a list."""
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return list(result.values())
        return [result]
 
 
    def _plan_campaign_ids(self) -> List[str]:
        """One cheap call → list of N distinct snake_case campaign IDs."""

        prompt = f"""
        {self._context}
        ---
        You are a Meta Ads strategist planning a campaign structure.
        
        Generate exactly {self.num_of_campaign_ideas} distinct snake_case campaign IDs.
        Each ID should reflect a unique objective or audience angle (e.g. smb_awareness_remote_teams).
        All IDs must be unique — no duplicates.
        
        Return ONLY a JSON array of strings. Example: ["id_one", "id_two"]
        No markdown. No explanation. JSON array only."""
        
        llm_response = self._call_llm_json(prompt=prompt)
        return self._coerce_list(llm_response)

 
    def _plan_adset_ids(self, campaign_id: str) -> List[str]:
        """One cheap call → list of N distinct snake_case adset IDs for a given campaign."""

        prompt = f"""
        {self._context}
        ---
        Campaign ID: {campaign_id}
        
        Generate exactly {self.num_of_adsets} distinct snake_case AdSet IDs for this campaign.
        Each ID should reflect a different audience slice or placement angle
        (e.g. {campaign_id}__ig_reels_25_34, {campaign_id}__fb_feed_lookalike).
        All IDs must be unique and prefixed with the campaign ID.
        
        Return ONLY a JSON array of strings.
        No markdown. No explanation. JSON array only."""

        llm_response = self._call_llm_json(prompt=prompt)
        return self._coerce_list(llm_response)
 
    def _plan_creative_ids(self, campaign_id: str, adset_id: str) -> List[str]:
        """One cheap call → list of N distinct snake_case creative IDs for a given adset."""

        prompt = f"""
        {self._context}
        ---
        Campaign ID: {campaign_id}
        AdSet ID: {adset_id}
        
        Generate exactly {self.num_of_ad_creatives} distinct snake_case Ad Creative IDs.
        Each ID should reflect a different creative angle or format
        (e.g. {adset_id}__carousel_productivity, {adset_id}__single_img_trial).
        All IDs must be unique and prefixed with the adset ID.
        
        Return ONLY a JSON array of strings.
        No markdown. No explanation. JSON array only."""
        
        llm_response = self._call_llm_json(prompt=prompt)
        return self._coerce_list(llm_response)
 
 
    def _generate_campaigns(self, campaign_ids: List[str]) -> List[dict]:
        """Generate campaign objects in batches, one batch per LLM call."""
        results = []
        for batch in self.yield_items(campaign_ids, self.batch_size):
            ids_str = json.dumps(batch)
            prompt = f"""
            {self._context}
            ---
            You are a Meta Ads strategist.
            
            Generate full campaign objects for these campaign IDs: {ids_str}
            Each campaign must have a distinct objective and audience angle matching its ID.
            Do NOT reuse angles or objectives across campaigns.
            
            Return ONLY a JSON array of objects (one per ID, in the same order).
            Each object must match this schema exactly:
            {self.campaign_schema}
            
            No markdown. No explanation. JSON array only."""
            batch_result = self._call_llm_json(prompt)
            results.extend(self._coerce_list(batch_result))
        return results
 
    def _generate_adsets(self, 
        campaign: dict, 
        adset_ids: List[str]
    ) -> List[dict]:
        """Generate adset objects in batches for a given campaign."""
        results = []
        for batch in self.yield_items(adset_ids, self.batch_size):
            ids_str = json.dumps(batch)
            prompt = f"""
            {self._context}
            ---
            Campaign:
            {json.dumps(campaign, indent=2)}
            
            You are a Meta Ads targeting specialist.
            
            Generate full AdSet objects for these AdSet IDs: {ids_str}
            Each AdSet must target a different audience slice or placement strategy matching its ID.
            Do NOT reuse targeting or placements across adsets.
            
            Return ONLY a JSON array of objects (one per ID, in the same order).
            Each object must match this schema exactly:
            {self.adset_schema}
            
            No markdown. No explanation. JSON array only."""
            batch_result = self._call_llm_json(prompt)
            results.extend(self._coerce_list(batch_result))
        return results
 
    def _generate_creatives(self, 
        campaign: dict, 
        adset: dict, 
        creative_ids: List[str]
    ) -> List[dict]:
        """Generate creative objects in batches for a given campaign + adset."""

        results = []
        for batch in self.yield_items(creative_ids, self.batch_size):
            ids_str = json.dumps(batch)
            prompt = f"""
            {self._context}
            ---
            Campaign:
            {json.dumps(campaign, indent=2)}
            
            AdSet:
            {json.dumps(adset, indent=2)}
            
            You are a Meta Ads creative director.
            
            Generate full Ad Creative objects for these creative IDs: {ids_str}
            Each creative must have a distinct format or copy angle matching its ID.
            Tailor tone and copy to the cohort data and affinity scores.
            Do NOT reuse headlines or copy across creatives.
            
            Return ONLY a JSON array of objects (one per ID, in the same order).
            Each object must match this schema exactly:
            {self.creative_schema}
            
            No markdown. No explanation. JSON array only."""
            batch_result = self._call_llm_json(prompt)
            results.extend(self._coerce_list(batch_result))
        return results
 
    def yield_items(self, items: list, chunk_size: int = None):
        """Yield successive chunks of `chunk_size` from `items`."""
        size = chunk_size or self.batch_size or 1
        for i in range(0, len(items), size):
            yield items[i : i + size]


    def _generate_all_ids(self):
        self._context = self._build_context()
        campaign_ids = self._plan_campaign_ids()

        adset_ids_map = {}
        creative_ids_map = {}

        for campaign_id in campaign_ids:
            adset_ids = self._plan_adset_ids(campaign_id=campaign_id)
            adset_ids_map[campaign_id] = adset_ids

            creative_ids_map[campaign_id] = {}
            for adset_id in adset_ids:
                creative_ids = self._plan_creative_ids(campaign_id=campaign_id, adset_id=adset_id)
                creative_ids_map[campaign_id][adset_id] = creative_ids

        return {
            "campaign_ids": campaign_ids,
            "adset_ids_map": adset_ids_map,
            "creative_ids_map": creative_ids_map
        }



    def run(self) -> Dict[str, Any]:
        all_ids = self._generate_all_ids()

        logger.info(f"{json.dumps(all_ids, indent=2)}")

        # assert False


        campaign_ids = all_ids["campaign_ids"]
        adset_ids_map = all_ids["adset_ids_map"]
        creative_ids_map = all_ids["creative_ids_map"]


 
        # ── Phase 2: generate full objects ────────────────────────────────
        logger.info(
            f"\nGenerating {len(campaign_ids)} campaign(s) [batch_size={self.batch_size}]..."
        )
        campaigns: List[dict] = self._generate_campaigns(campaign_ids)
 
        output_campaigns: List[dict] = []
 
        for campaign, campaign_id in zip(campaigns, campaign_ids):
            logger.info(f"  Generating adsets for [{campaign_id}]...")
            adset_ids = adset_ids_map[campaign_id]
            adsets: List[dict] = self._generate_adsets(campaign, adset_ids)
 
            # Build the campaign node with nested adsets + creatives
            campaign_node = {**campaign, "campaign_id": campaign_id, "adsets": []}
 
            for adset, adset_id in zip(adsets, adset_ids):
                logger.info(f"    Generating creatives for [{adset_id}]...")
                creative_ids = creative_ids_map[campaign_id][adset_id]
                creatives: List[dict] = self._generate_creatives(
                    campaign, adset, creative_ids
                )
 
                # FIX: tag each creative with its ID, then attach to adset
                for creative, creative_id in zip(creatives, creative_ids):
                    creative["creative_id"] = creative_id
 
                adset_node = {
                    **adset,
                    "adset_id": adset_id,
                    "ad_creatives": creatives,
                }
 
                # FIX: actually append the completed adset node
                campaign_node["adsets"].append(adset_node)
 
            output_campaigns.append(campaign_node)
 
        logger.info("Done. Full ad tree built successfully.")
 
        # FIX: return the completed structure instead of returning None
        return {"campaigns": output_campaigns}
 
# ─────────────────────────────────────────────────────────────────────────────
# Example usage
# ─────────────────────────────────────────────────────────────────────────────
 
if __name__ == "__main__":


    from ai_service import ai_service_app

    # ai_service_app.add_or_update_ai_model(
    #     model_name="gpt-3.5-turbo",
    #     model_family="gpt",
    #     model_type="llm",
    #     model_version="3.5-turbo",
    #     cloud="azure",
    #     api_type="azure",
    #     url="https://openai-chatbots.openai.azure.com/openai/deployments/daveai-deployment/chat/completions?api-version=2023-05-15",
    #     api_key="1vClzSasfgkzFnt8D3F5DqUNgfnvPjbMUZsH6WmDBkGVtb0tYX9cJQQJ99BAAC77bzfXJ3w3AAABACOGRCDN",
    #     input_pricing_units="1M tokens",
    #     output_pricing_units="1M tokens",
    #     input_pricing_dollars=1,
    #     output_pricing_dollars=2,
    # )

    # ai_service_app.list_models(cloud="azure")

    # ai_service_app.get_llm_response(messages=)

    # ai_service_app.add_or_update_ai_model(
    #     model_family="gcp-gemini-2.5-flash",
    # )

    source=None,
    classified_cohort={
        "cohort_name" : "Tech & Performance Enthusiasts",
        "description" : "Tech & Performance Enthusiasts",
    },
    affinity_score={
        "remote_work": 0.95,
        "productivity": 0.88,
        "collaboration": 0.82,
        "pricing_sensitivity": 0.75,
    },
    brochure_url=None,
    product_website_url="https://cars.tatamotors.com/sierra/ice.html",
    num_of_campaign_ideas=3,
    batch_size=2,
    additional_instruction=None

    agent1 = MetaAdCampaignAgent(
        source=None,
        classified_cohort=classified_cohort,
        affinity_score=affinity_score,
        brochure_url=None,
        product_website_url="https://cars.tatamotors.com/sierra/ice.html",
        num_of_campaign_ideas=2,
        model_identifier="azure-gpt-4o",
        batch_size=2,
        additional_instruction=additional_instruction       
    )

    campaign_data = agent1.run()

    print(json.dumps(campaign_data, indent=2))
    print("**" * 50)


    agent2 = MetaAdAdsetAgent(
        source=None,
        classified_cohort=classified_cohort,
        affinity_score=affinity_score,
        brochure_url=None,
        product_website_url="https://cars.tatamotors.com/sierra/ice.html",
        fb_campaigns=campaign_data["campaigns"],
        num_of_adsets=1,
        model_identifier="azure-gpt-4o",
        batch_size=2
    )


    adset_data = agent2.run()

    print(json.dumps(adset_data, indent=2))
    print("**" * 50)

    agent3 = MetaAdCreativeAgent(
    source=None,
    classified_cohort=classified_cohort,
    affinity_score=affinity_score,
    product_website_url="https://cars.tatamotors.com/sierra/ice.html",
    fb_campaigns=campaign_data["campaigns"],
    fb_adsets=adset_data["adsets"],
    num_of_creatives=1,
    model_identifier="azure-gpt-4o",
    batch_size=2,
    additional_instruction=additional_instruction
    )

    creative_data = agent3.run()
    print(json.dumps(creative_data, indent=2))
    print("**" * 50)

    assert False
 
 
    agent = MetaAdAgent(
        source=None,
        classified_cohort={
            "segment": "SMB",
            "industry": "Tech / SaaS",
            "company_size": "10-50 employees",
            "decision_maker": "Operations Manager",
        },
        affinity_score={
            "remote_work": 0.95,
            "productivity": 0.88,
            "collaboration": 0.82,
            "pricing_sensitivity": 0.75,
        },
        brochure_url=None,
        product_website_url="https://cars.tatamotors.com/sierra/ice.html",
        num_of_campaign_ideas=1,
        num_of_adsets=1,
        num_of_ad_creatives=1,
        batch_size=1,           # generate 2 items per LLM call; set to 1 for fully sequential
    )
 
    result = agent.run()
    print(json.dumps(result, indent=2))