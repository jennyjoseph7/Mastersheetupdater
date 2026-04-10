# import sys, os
# # sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# _parent = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# if _parent not in sys.path:
#     sys.path.insert(0, _parent)
# import json
# import re
# from ai_service import ai_service_app
# import pandas as pd 
# from pathlib import Path
# import time
# from typing import *
# from cohorts_new.utils.utility import *
# from cohorts_new.utils.common_utils import *

# logger = get_logger(__name__)

# class CampaignIdeaGeneratorAgent(UtilityMixin):
#     def __init__(
#             self, 
#             source:dict=None, 
#             classified_cohort:dict=None, 
#             affinity_score:dict=None, 
#             brochure_url:str=None, 
#             product_website_url:str=None, 
#             campaign_theme:str=None,
#             core_message_direction:str=None,
#             campaign_objective:str=None,
#             consumer_insight:str=None,
#             additional_instruction:str=None,
#             num_of_campaign_ideas=3, 
#             num_of_campaign_post_sets=3, 
#             num_of_hashtags=20,
#             model_identifier:str='azure-gpt-4o'
#             ):
        
#         """
#         Description:
#             This class is used to generate campaign ideas for a given cohort and affinity score.

#         Args:
#             source (dict) : The customer interaction data for the campaign idea generation (if available).
#             classified_cohort (dict) : The classified cohort for the campaign idea generation.
#             affinity_score (dict) : The affinity score data for the campaign idea generation.
#             brochure_url (str) : The brochure url. 
#             product_website_url (str) : The product website url.
#             campaign_theme (str) : The campaign theme for the campaign idea generation.
#             core_message_direction (str) : The core message direction for the campaign idea generation.
#             campaign_objective (str) : The campaign objective for the campaign idea generation.
#             consumer_insight (str) : The consumer insight for the campaign idea generation.
#             additional_instruction (str) : The additional instruction for the campaign idea generation agent LLM.
#             num_of_campaign_ideas (int) : The number of campaign ideas to generate.
#             num_of_campaign_post_sets (int) : The number of campaign post sets to generate per campaign idea. 
#             num_of_hashtags (int) : The number of hashtags to generate per campaign idea.
#             model_identifier (str) : The LLM model to use to orchestrate.
#         """

#         self.source = self._load_json(source=source) 
#         self.classified_cohort = self._load_json(source=classified_cohort) 
#         self.affinity_score = affinity_score

#         def filter_affinity_dict(affinity_dict):
#             filtered_dict = {}
#             if affinity_dict is not None and not isinstance(affinity_dict, dict):
#                 raise ValueError(f'Affinity score must be a dictionary. Please run affinity_agent properly. Provided affinity_dict type is:{type(affinity_dict)}')
#             for k, v in affinity_dict.items():
#                 if k in ['fig', 'img_bytes', 'fig_json', 'fig_json_bytes', 'affinity_fig_json', 'affinity_fig_json_bytes',]:
#                     continue
#                 else:
#                     filtered_dict[k] = v
#             return filtered_dict
        
#         if self.affinity_score is not None:
#             self.affinity_score = filter_affinity_dict(self.affinity_score)

#         self.brochure_url = brochure_url
#         self.product_website_url = product_website_url
#         self.campaign_theme = campaign_theme
#         self.core_message_direction = core_message_direction
#         self.campaign_objective = campaign_objective
#         self.consumer_insight = consumer_insight
#         self.additional_instruction = additional_instruction

#         self.num_of_campaign_ideas = num_of_campaign_ideas
#         self.num_of_campaign_post_sets = num_of_campaign_post_sets
#         self.num_of_hashtags = num_of_hashtags

#         self.model_identifier = model_identifier

#         def get_llm_response(messages:List[dict], model_identifier:str="azure-gpt-4o"):
#             return ai_service_app.get_llm_response(messages=messages, model_identifier=model_identifier)
        
#         self.llm = get_llm_response

#         self.llm=lambda messages:ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
#         self.brochure_content:dict[str]=self.fetch_brochure_content(brochure_url = self.brochure_url) # Only page_content is there and needed
#         self.product_website_content:dict[str]=self.fetch_product_details_from_website(website_url = self.product_website_url) # Only page_content is there and needed


#     def yield_items(self, items, chunk_size=10):
#         """Helper func to generate chunks of items"""
#         len_of_items = len(items)
#         for i in range(0, len_of_items, chunk_size):
#             limit = i + chunk_size
#             yield items[i:limit]    

#     @property
#     def _additional_product_context(self) -> str:
#         return """
#     Analyze the brochure and website to extract core value propositions,
#     emotional triggers, differentiators, and target persona signals.
#     Use these insights to create strategically distinct campaign directions.
#     Each campaign idea must reflect real product strengths and represent
#     a different strategic angle (e.g., performance, lifestyle, safety, tech, aspiration).
#     Avoid generic or repetitive themes.
#     """

#     def _build_shared_user_context(self) -> list[str]:
#         """Builds the common user context parts reused across both prompts."""
#         parts = [
#             f"Customer Interaction Context (if available):\n{json.dumps(self.source, indent=2, ensure_ascii=False)}",
#             f"Classified Cohorts:\n{json.dumps(self.classified_cohort, indent=2, ensure_ascii=False)}",
#             f"Affinity Signals:\n{json.dumps(self.affinity_score, indent=2, ensure_ascii=False)}",
#             f"Campaign Theme:\n{self.campaign_theme}",
#             f"Core Message Direction:\n{self.core_message_direction}",
#             f"Campaign Objective:\n{self.campaign_objective}",
#             f"Consumer Insight:\n{self.consumer_insight}",
#             f"Additional Instructions:\n{self.additional_instruction}",
#         ]

#         product_parts = []
#         if self.brochure_content is not None:
#             product_parts.append(f"PRODUCT BROCHURE:\n{json.dumps(self.brochure_content, indent=2, ensure_ascii=False)}")
#         if self.product_website_content is not None:
#             product_parts.append(f"PRODUCT WEBSITE:\n{json.dumps(self.product_website_content, indent=2, ensure_ascii=False)}")
#         if product_parts:
#             product_parts.append(self._additional_product_context)
#             parts.append("\n\n".join(product_parts))

#         return parts


#     def _generate_campaign_ids(self) -> list[str]:
#         """Generates distinct, high-level campaign idea IDs."""
#         system_prompt = """
#     You are a senior automotive brand strategist.
#     Generate ONLY a JSON list of high-level campaign idea IDs — no descriptions, no explanations.
#     Each ID must:
#     - Represent a unique, strategically distinct creative direction
#     - Be 3-6 words, strictly snake_case, no numbers, no special characters
#     - Be emotionally expressive or strategically meaningful
#     - Cover fundamentally different angles (e.g. performance, lifestyle, safety, tech, aspiration, sustainability)
#     FORBIDDEN: Generic IDs like "brand_awareness_campaign". No repeated themes.
#     Return format (strict JSON only):
#     {
#         "campaign_idea_ids": ["idea_one", "idea_two"]
#     }
#     """
#         user_context_parts = self._build_shared_user_context()
#         user_prompt = "\n\n".join(user_context_parts)
#         user_prompt += f"\n\nGenerate exactly {self.num_of_campaign_ideas} distinct campaign idea IDs."

#         messages = [
#             {"role": "system", "content": system_prompt.strip()},
#             {"role": "user", "content": user_prompt.strip()},
#         ]

#         return self.exec_json_llm_with_retry(self.llm, messages=messages)


#     def campaign_ideas(self, campaign_batch: List[str]) -> List[dict]:
#         system_prompt = f"""
#         You are a Product-Driven Campaign Strategy & Creative AI Agent.
#         TASK:
#         Generate exactly {len(campaign_batch)} campaign idea(s) — one per campaign ID in the batch.
#         Return a JSON array of dictionaries. One dict per campaign ID. No extras, no skips.

#         ═══════════════════════════════
#         PRODUCT IDENTIFICATION (DO FIRST)
#         ═══════════════════════════════
#         - Extract the EXACT product name/model from brochure and website.
#         - Use it CONSISTENTLY in every field across all outputs.
#         - Fallback if unidentifiable: brand_name + product_category.

#         ═══════════════════════════════
#         OUTPUT SCHEMA (per campaign idea)
#         ═══════════════════════════════
#         {{
#         "campaign_idea_identifier": <exact ID from the batch>,
#         "campaign_objective": <string>,
#         "campaign_explanation": <string — for media planners; must name product, target audience, insight, channels, featured specs>,
#         "audience": [<string>, ...],   // If cohort information is available, Only that cohort should be included. Otherwise, use a generic audience but only one.
#         "cta": [<string>, ...],        // min 2; ALL must include product name
#         "hashtags": [<string>, ...],   // exactly {self.num_of_hashtags}; ≥60% product-specific (include model name)
#         "campaign_post_sets": [...]    // exactly {self.num_of_campaign_post_sets} items (see below)
#         }}

#         Each post set:
#         {{
#         "post_caption": [<string>],   // product name in first 10 words
#         "hooks":        [<string>],   // must reference product name/model
#         "slogan":       [<string>],   // must include or directly reference product name
#         "messages":     [<string>]    // 2-3 sentences; product name in first 2; ≥2-3 specific features; subtle emojis; optional closing question
#         }}

#         ═══════════════════════════════
#         HARD RULES
#         ═══════════════════════════════
#         ✓ campaign_idea_identifier must EXACTLY match a batch ID — no invention
#         ✓ Product name in: explanation, all captions, hooks, slogans, messages, CTAs
#         ✓ Features must be specific (e.g. "1.2L turbocharged engine", not "powerful engine")
#         ✓ Each post set must highlight different features at a distinct angle/tone
#         ✓ Personalise using cohort traits, affinity signals, and customer interaction where available
#         ✓ If "Opportunity Name" exists → likely customer name; "Opportunity Owner" → representative
#         ✓ Campaign Theme, Objective, Consumer Insight, Core Message Direction must anchor all ideas

#         ✗ No generic references: "our latest offering", "this amazing product", "Experience luxury" (without product name)
#         ✗ No brand-only hashtags (e.g. #BrandName alone)
#         ✗ No repeated captions, hooks, or slogans across post sets
#         ✗ No markdown, no explanations, no trailing comments — strict JSON only

#         TONE: Premium, confident, automotive-focused. Think product spotlight, not brand awareness.

#         Example Output:
#         [
#             {{
#                 "campaign_idea_identifier": "aircross_urban_performance_push",
#                 "campaign_objective": "Drive awareness and test drives for Citroen Aircross C3",
#                 "campaign_explanation": "This campaign targets urban millennials seeking versatile SUVs. The Citroen Aircross C3's key features like 210mm ground clearance and spacious cabin are highlighted to appeal to adventure-seekers who need practical daily drivers. Best channels: Instagram Reels, YouTube pre-roll.",
#                 "audience": ["Urban millennials 28-40", "Adventure enthusiasts"],
#                 "cta": ["Book Aircross C3 test drive", "Download Aircross brochure", "Explore Aircross features"],
#                 "hashtags": ["#CitroenAircross", "#AircrossC3", "#AircrossAdventure", "#CitroenAircrossIndia", "#AircrossFeatures", "#CompactSUV", "#UrbanAdventure", "#SUVLife"],
                
#                 "campaign_post_sets": [
#                     {{
#                         "post_caption": ["The Citroen Aircross C3 redefines urban adventure with 210mm ground clearance and bold design"],
#                         "hooks": ["Ready to conquer city streets? Meet the Aircross C3"],
#                         "slogan": ["Aircross: Built for Every Journey"],
#                         "messages": ["Hi! Looks like you've been eyeing compact SUVs 👀 The Citroën C3 Aircross might be your match — built for the city, ready for the weekend. Want to take one for a spin?"]
#                     }},
#                     {{
#                         "post_caption": ["Citroen Aircross C3: Where comfort meets capability in every drive"],
#                         "hooks": ["Your daily drive deserves the Aircross C3 upgrade"],
#                         "slogan": ["Aircross C3: Adventure Approved, City Ready"],
#                         "messages": ["The C3 Aircross isn't just practical — it's personal. Dual-tone colors, a connected cabin, and safety built-in as standard. Every detail, done right. Ready to see it in person?"]
#                     }}
#                 ]
#             }}
#         ]
#         """

#         # system_prompt = None 

#         # system_prompt = f"""
#         # You are a Product-Driven Campaign & Performance Marketing AI Agent.
#         # CRITICAL: Extract the EXACT product name from brochure/website first. Use it consistently everywhere — captions, hooks, slogans, CTAs, messages. Never say "our product" or "this vehicle".

#         # Generate exactly {len(campaign_batch)} campaigns — one per ID in the batch.
#         # Return a strict JSON array only. No markdown, no comments, no extra keys.

#         # Each campaign schema:
#         # {{
#         # "campaign_idea_identifier": <exact batch ID>,
#         # "campaign_objective": <string>,
#         # "campaign_explanation": <string — name product, audience, insight, channels, specs>,
#         # "performance_strategy": {{
#         #     "channels": [{{ "channel": "", "reasoning": "", "ad_formats": [] }}],
#         #     "budget_allocation": [{{ "channel": "", "budget_percent": 0 }}],
#         #     "funnel_strategy": {{ "TOF": "", "MOF": "", "BOF": "" }}
#         # }},
#         # "targeting": {{
#         #     "age_range": "", "gender": "", "locations": [], "languages": [],
#         #     "interests": [], "behaviors": [], "life_events": [], "job_titles": []
#         # }},
#         # "audience": [<string>],
#         # "cta": [<string>],         // min 2; ALL must include product name
#         # "hashtags": [<string>],    // exactly {self.num_of_hashtags}; ≥60% product/model-specific
#         # "campaign_post_sets": [    // exactly {self.num_of_campaign_post_sets} items. Each post set will have one post caption, one hook, one slogan, and one message
#         #     {{
#         #     "post_caption": [<string>],  // product name in first 10 words  // Only one post_caption
#         #     "hooks":        [<string>],  // must reference product name     // Only one hook
#         #     "slogan":       [<string>],  // must reference product name     // Only one slogan
#         #     "messages":     [<string>]   // 7-8 sentences; product name in first 2; ≥3 specific features; subtle emojis // Only one message
#         #     }}
#         # ]
#         # }}

#         # RULES:
#         # - Each post set: different feature angle, different emotional trigger
#         # - Features must be specific (e.g. "1.2L turbo", not "powerful engine")
#         # - Targeting derived from cohort, affinity signals, and product positioning
#         # - Channels: Facebook, Instagram, Snapchat, YouTube, Google Ads, TikTok
#         # - Personalize using cohort traits, affinity signals, and customer interaction context
#         # - "Opportunity Name" = likely customer; "Opportunity Owner" = sales rep
#         # """
        
#         shared_user_context = self._build_shared_user_context()
#         user_context_parts = [f"Campaign IDs for this batch (generate one idea per ID): {json.dumps(campaign_batch, ensure_ascii=False)}",] + shared_user_context
#         user_prompt = "\n\n".join(user_context_parts)
#         user_prompt += (
#             f"\n\nGenerate EXACTLY {len(campaign_batch)} campaign idea(s), "
#             f"one for each ID above. Match identifiers exactly."
#         )

#         messages = [
#             {"role": "system", "content": system_prompt.strip()},
#             {"role": "user", "content": user_prompt.strip()},
#         ]

#         return self.exec_json_llm_with_retry(self.llm, messages=messages)

#     def run_with_events(self, batch_size=2) -> Iterator[dict]:
#         def emit(event_type, data=None):
#             return {"type": event_type, "data": data}
        
#         campaign_idea_ids = self._generate_campaign_ids().get("campaign_idea_ids", [])
#         logger.info(f"Generated {len(campaign_idea_ids)} campaign idea IDs: {campaign_idea_ids}")
#         yield emit(event_type="campaign_ids_generated", data={"campaign_idea_ids": campaign_idea_ids})

#         campaign_idea_ids_chunks = list(self.yield_items(items=campaign_idea_ids, chunk_size=batch_size))
#         total_batches = len(campaign_idea_ids_chunks)

#         for batch_index, campaign_batch in enumerate(campaign_idea_ids_chunks):
#             logger.info(f"Processing batch {batch_index + 1}/{total_batches} — IDs: {campaign_batch}")
#             try:
#                 batch_ideas = self.campaign_ideas(campaign_batch=campaign_batch)
#                 yield emit(event_type="batch_completed", data={
#                     "batch_index": batch_index + 1,
#                     "total_batches": total_batches,
#                     "batch_ids": campaign_batch,
#                     "campaign_ideas": batch_ideas,
#                 })

#             except Exception as e:
#                 logger.error(f"Error in batch {batch_index + 1} ({campaign_batch}): {e}", exc_info=True)
#                 yield emit(event_type="batch_error", 
#                     data={
#                         "batch_index": batch_index + 1,
#                         "total_batches": total_batches,
#                         "batch_ids": campaign_batch,
#                         "error": str(e),
#                     })

#         yield emit("completed", {"total_batches": total_batches})

#     def run(self, batch_size=10) -> dict:
#         campaign_idea_ids = self._generate_campaign_ids().get("campaign_idea_ids", [])
#         logger.info(f"Generated {len(campaign_idea_ids)} campaign idea IDs: {campaign_idea_ids}")

#         all_campaign_ideas = []
#         for campaign_batch in self.yield_items(items=campaign_idea_ids, chunk_size=batch_size):
#             try:
#                 batch_ideas = self.campaign_ideas(campaign_batch=campaign_batch)
#                 all_campaign_ideas.extend(batch_ideas)
#             except Exception as e:
#                 logger.error(f"Error processing batch ({campaign_batch}): {e}", exc_info=True)

#         return {
#             "campaign_idea_ids": campaign_idea_ids,
#             "campaign_ideas": all_campaign_ideas,
#         }



import sys, os
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import json
import re
from ai_service import ai_service_app
import pandas as pd 
from pathlib import Path
import time
from typing import *
from cohorts_new.utils.utility import *
from cohorts_new.utils.common_utils import *

logger = get_logger(__name__)

class CampaignIdeaGeneratorAgent(UtilityMixin):
    def __init__(
            self, 
            source:dict=None, 
            classified_cohort:dict=None, 
            affinity_score:dict=None, 
            brochure_url:str=None, 
            product_website_url:str=None, 
            campaign_theme:str=None,
            core_message_direction:str=None,
            campaign_objective:str=None,
            consumer_insight:str=None,
            additional_instruction:str=None,
            num_of_campaign_ideas=3, 
            num_of_campaign_post_sets=3, 
            num_of_hashtags=20,
            title_max_length:int=None,
            hook_max_length:int=None,
            slogan_max_length:int=None,
            caption_max_length:int=None,
            message_max_length:int=None,
            cta_max_length:int=None,
            model_identifier:str='azure-gpt-4o'
            ):
        
        """
        Description:
            This class is used to generate campaign ideas for a given cohort and affinity score.

        Args:
            source (dict) : The customer interaction data for the campaign idea generation (if available).
            classified_cohort (dict) : The classified cohort for the campaign idea generation.
            affinity_score (dict) : The affinity score data for the campaign idea generation.
            brochure_url (str) : The brochure url. 
            product_website_url (str) : The product website url.
            campaign_theme (str) : The campaign theme for the campaign idea generation.
            core_message_direction (str) : The core message direction for the campaign idea generation.
            campaign_objective (str) : The campaign objective for the campaign idea generation.
            consumer_insight (str) : The consumer insight for the campaign idea generation.
            additional_instruction (str) : The additional instruction for the campaign idea generation agent LLM.
            num_of_campaign_ideas (int) : The number of campaign ideas to generate.
            num_of_campaign_post_sets (int) : The number of campaign post sets to generate per campaign idea. 
            num_of_hashtags (int) : The number of hashtags to generate per campaign idea.
            title_max_length (int) : Max character length for campaign titles/identifiers. No limit if None.
            hook_max_length (int) : Max character length for hooks in each post set. No limit if None.
            slogan_max_length (int) : Max character length for slogans in each post set. No limit if None.
            caption_max_length (int) : Max character length for post captions in each post set. No limit if None.
            message_max_length (int) : Max character length for messages in each post set. No limit if None.
            cta_max_length (int) : Max character length for each CTA string. No limit if None.
            model_identifier (str) : The LLM model to use to orchestrate.
        """

        self.source = self._load_json(source=source) 
        self.classified_cohort = self._load_json(source=classified_cohort) 
        self.affinity_score = affinity_score

        def filter_affinity_dict(affinity_dict):
            filtered_dict = {}
            if affinity_dict is not None and not isinstance(affinity_dict, dict):
                raise ValueError(f'Affinity score must be a dictionary. Please run affinity_agent properly. Provided affinity_dict type is:{type(affinity_dict)}')
            for k, v in affinity_dict.items():
                if k in ['fig', 'img_bytes', 'fig_json', 'fig_json_bytes', 'affinity_fig_json', 'affinity_fig_json_bytes',]:
                    continue
                else:
                    filtered_dict[k] = v
            return filtered_dict
        
        if self.affinity_score is not None:
            self.affinity_score = filter_affinity_dict(self.affinity_score)

        self.brochure_url = brochure_url
        self.product_website_url = product_website_url
        self.campaign_theme = campaign_theme
        self.core_message_direction = core_message_direction
        self.campaign_objective = campaign_objective
        self.consumer_insight = consumer_insight
        self.additional_instruction = additional_instruction

        self.num_of_campaign_ideas = num_of_campaign_ideas
        self.num_of_campaign_post_sets = num_of_campaign_post_sets
        self.num_of_hashtags = num_of_hashtags

        self.title_max_length = title_max_length
        self.hook_max_length = hook_max_length
        self.slogan_max_length = slogan_max_length
        self.caption_max_length = caption_max_length
        self.message_max_length = message_max_length
        self.cta_max_length = cta_max_length

        self.model_identifier = model_identifier

        def get_llm_response(messages:List[dict], model_identifier:str="azure-gpt-4o"):
            return ai_service_app.get_llm_response(messages=messages, model_identifier=model_identifier)
        
        self.llm = get_llm_response

        self.llm=lambda messages:ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        self.brochure_content:dict[str]=self.fetch_brochure_content(brochure_url = self.brochure_url) # Only page_content is there and needed
        self.product_website_content:dict[str]=self.fetch_product_details_from_website(website_url = self.product_website_url) # Only page_content is there and needed


    def yield_items(self, items, chunk_size=10):
        """Helper func to generate chunks of items"""
        len_of_items = len(items)
        for i in range(0, len_of_items, chunk_size):
            limit = i + chunk_size
            yield items[i:limit]    

    @property
    def _additional_product_context(self) -> str:
        return """
    Analyze the brochure and website to extract core value propositions,
    emotional triggers, differentiators, and target persona signals.
    Use these insights to create strategically distinct campaign directions.
    Each campaign idea must reflect real product strengths and represent
    a different strategic angle (e.g., performance, lifestyle, safety, tech, aspiration).
    Avoid generic or repetitive themes.
    """

    @property
    def _output_schema(self) -> str:
        """
        Returns the expected JSON output schema for campaign ideas,
        with field-level length constraints injected dynamically.
        """
        def _len_note(max_len: int | None, label: str) -> str:
            return f"max {max_len} characters" if max_len is not None else f"no fixed limit"

        schema = f"""
OUTPUT SCHEMA (per campaign idea) — strict JSON, no markdown, no extra keys:

{{
    "campaign_idea_identifier": <string — exact ID from the batch; {_len_note(self.title_max_length, 'title')}>,
    "campaign_objective": <string>,
    "campaign_explanation": <string — for media planners; must name product, target audience, insight, channels, featured specs>,
    "audience": [<string>, ...],
    "cta": [
        <string — {_len_note(self.cta_max_length, 'cta')}>,
        ...
    ],
    "hashtags": [<string>, ...],   // exactly {self.num_of_hashtags}; ≥60% product-specific (include model name)
    "campaign_post_sets": [        // exactly {self.num_of_campaign_post_sets} items
        {{
            "post_caption": [<string — {_len_note(self.caption_max_length, 'caption')}>],
            "hooks":        [<string — {_len_note(self.hook_max_length, 'hook')}>],
            "slogan":       [<string — {_len_note(self.slogan_max_length, 'slogan')}>],
            "messages":     [<string — {_len_note(self.message_max_length, 'message')}; 7-8 sentences; product name in first 2; ≥2-3 specific features; subtle emojis; optional closing question>]
        }},
        ...
    ]
}}
"""
        return schema.strip()

    def _build_shared_user_context(self) -> list[str]:
        """Builds the common user context parts reused across both prompts."""
        parts = [
            f"Customer Interaction Context (if available):\n{json.dumps(self.source, indent=2, ensure_ascii=False)}",
            f"Classified Cohorts:\n{json.dumps(self.classified_cohort, indent=2, ensure_ascii=False)}",
            f"Affinity Signals:\n{json.dumps(self.affinity_score, indent=2, ensure_ascii=False)}",
            f"Campaign Theme:\n{self.campaign_theme}",
            f"Core Message Direction:\n{self.core_message_direction}",
            f"Campaign Objective:\n{self.campaign_objective}",
            f"Consumer Insight:\n{self.consumer_insight}",
            f"Additional Instructions:\n{self.additional_instruction}",
        ]

        product_parts = []
        if self.brochure_content is not None:
            product_parts.append(f"PRODUCT BROCHURE:\n{json.dumps(self.brochure_content, indent=2, ensure_ascii=False)}")
        if self.product_website_content is not None:
            product_parts.append(f"PRODUCT WEBSITE:\n{json.dumps(self.product_website_content, indent=2, ensure_ascii=False)}")
        if product_parts:
            product_parts.append(self._additional_product_context)
            parts.append("\n\n".join(product_parts))

        return parts


    def _generate_campaign_ids(self) -> list[str]:
        """Generates distinct, high-level campaign idea IDs."""
        system_prompt = """
    You are a senior automotive brand strategist.
    Generate ONLY a JSON list of high-level campaign idea IDs — no descriptions, no explanations.
    Each ID must:
    - Represent a unique, strategically distinct creative direction
    - Be 3-6 words, strictly snake_case, no numbers, no special characters
    - Be emotionally expressive or strategically meaningful
    - Cover fundamentally different angles (e.g. performance, lifestyle, safety, tech, aspiration, sustainability)
    FORBIDDEN: Generic IDs like "brand_awareness_campaign". No repeated themes.
    Return format (strict JSON only):
    {
        "campaign_idea_ids": ["idea_one", "idea_two"]
    }
    """
        user_context_parts = self._build_shared_user_context()
        user_prompt = "\n\n".join(user_context_parts)
        user_prompt += f"\n\nGenerate exactly {self.num_of_campaign_ideas} distinct campaign idea IDs."

        messages = [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ]

        return self.exec_json_llm_with_retry(self.llm, messages=messages)


    def campaign_ideas(self, campaign_batch: List[str]) -> List[dict]:
        system_prompt = f"""
        You are a Product-Driven Campaign Strategy & Creative AI Agent.
        TASK:
        Generate exactly {len(campaign_batch)} campaign idea(s) — one per campaign ID in the batch.
        Return a JSON array of dictionaries. One dict per campaign ID. No extras, no skips.

        ═══════════════════════════════
        PRODUCT IDENTIFICATION (DO FIRST)
        ═══════════════════════════════
        - Extract the EXACT product name/model from brochure and website.
        - Use it CONSISTENTLY in every field across all outputs.
        - Fallback if unidentifiable: brand_name + product_category.

        ═══════════════════════════════
        {self._output_schema}
        ═══════════════════════════════

        ═══════════════════════════════
        HARD RULES
        ═══════════════════════════════
        ✓ campaign_idea_identifier must EXACTLY match a batch ID — no invention
        ✓ Product name in: explanation, all captions, hooks, slogans, messages, CTAs
        ✓ Features must be specific (e.g. "1.2L turbocharged engine", not "powerful engine")
        ✓ Each post set must highlight different features at a distinct angle/tone
        ✓ Personalise using cohort traits, affinity signals, and customer interaction where available
        ✓ If "Opportunity Name" exists → likely customer name; "Opportunity Owner" → representative
        ✓ Campaign Theme, Objective, Consumer Insight, Core Message Direction must anchor all ideas

        ✗ No generic references: "our latest offering", "this amazing product", "Experience luxury" (without product name)
        ✗ No brand-only hashtags (e.g. #BrandName alone)
        ✗ No repeated captions, hooks, or slogans across post sets
        ✗ No markdown, no explanations, no trailing comments — strict JSON only

        TONE: Premium, confident, automotive-focused. Think product spotlight, not brand awareness.

        Example Output:
        [
            {{
                "campaign_idea_identifier": "aircross_urban_performance_push",
                "campaign_objective": "Drive awareness and test drives for Citroen Aircross C3",
                "campaign_explanation": "This campaign targets urban millennials seeking versatile SUVs. The Citroen Aircross C3's key features like 210mm ground clearance and spacious cabin are highlighted to appeal to adventure-seekers who need practical daily drivers. Best channels: Instagram Reels, YouTube pre-roll.",
                "audience": ["Urban millennials 28-40", "Adventure enthusiasts"],
                "cta": ["Book Aircross C3 test drive", "Download Aircross brochure", "Explore Aircross features"],
                "hashtags": ["#CitroenAircross", "#AircrossC3", "#AircrossAdventure", "#CitroenAircrossIndia", "#AircrossFeatures", "#CompactSUV", "#UrbanAdventure", "#SUVLife"],
                
                "campaign_post_sets": [
                    {{
                        "post_caption": ["The Citroen Aircross C3 redefines urban adventure with 210mm ground clearance and bold design"],
                        "hooks": ["Ready to conquer city streets? Meet the Aircross C3"],
                        "slogan": ["Aircross: Built for Every Journey"],
                        "messages": ["Hi! We noticed you were exploring compact SUVs perfect for city adventures. The Citroen Aircross C3 might be exactly what you're looking for! 🚗 With an impressive 210mm ground clearance, this compact SUV handles everything from city potholes to weekend getaways effortlessly. The spacious cabin seats 5 comfortably, while the 315-liter boot space ensures you never leave anything behind. Powered by a 1.2L turbocharged engine, the Aircross C3 delivers peppy performance without compromising on fuel efficiency. The bold design with LED projector headlamps and signature dual-tone roof makes heads turn everywhere you go. Plus, the elevated driving position gives you commanding road visibility ✨ Would you like to experience the Aircross C3 firsthand with a test drive?"]
                    }},
                    {{
                        "post_caption": ["Citroen Aircross C3: Where comfort meets capability in every drive"],
                        "hooks": ["Your daily drive deserves the Aircross C3 upgrade"],
                        "slogan": ["Aircross C3: Adventure Approved, City Ready"],
                        "messages": ["The Citroen Aircross C3 is engineered for those who refuse to compromise! This versatile SUV brings together comfort, style, and performance in one compelling package 🌟 Inside, you'll find a thoughtfully designed cabin with class-leading shoulder room and flexible seating configurations. The 7-inch touchscreen infotainment system keeps you connected with Apple CarPlay and Android Auto. Safety isn't an afterthought—dual airbags, ABS with EBD, and rear parking sensors come standard. The Aircross C3's 180mm of approach angle means speed bumps and rough roads are no longer a concern. Available in vibrant dual-tone color combinations, it's a SUV that reflects your personality 💫 Ready to make every journey memorable?"]
                    }}
                ]
            }}
        ]
        """
        
        shared_user_context = self._build_shared_user_context()
        user_context_parts = [f"Campaign IDs for this batch (generate one idea per ID): {json.dumps(campaign_batch, ensure_ascii=False)}",] + shared_user_context
        user_prompt = "\n\n".join(user_context_parts)
        user_prompt += (
            f"\n\nGenerate EXACTLY {len(campaign_batch)} campaign idea(s), "
            f"one for each ID above. Match identifiers exactly."
        )

        messages = [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ]

        return self.exec_json_llm_with_retry(self.llm, messages=messages)

    def run_with_events(self, batch_size=2) -> Iterator[dict]:
        def emit(event_type, data=None):
            return {"type": event_type, "data": data}
        
        campaign_idea_ids = self._generate_campaign_ids().get("campaign_idea_ids", [])
        logger.info(f"Generated {len(campaign_idea_ids)} campaign idea IDs: {campaign_idea_ids}")
        yield emit(event_type="campaign_ids_generated", data={"campaign_idea_ids": campaign_idea_ids})

        campaign_idea_ids_chunks = list(self.yield_items(items=campaign_idea_ids, chunk_size=batch_size))
        total_batches = len(campaign_idea_ids_chunks)

        for batch_index, campaign_batch in enumerate(campaign_idea_ids_chunks):
            logger.info(f"Processing batch {batch_index + 1}/{total_batches} — IDs: {campaign_batch}")
            try:
                batch_ideas = self.campaign_ideas(campaign_batch=campaign_batch)
                yield emit(event_type="batch_completed", data={
                    "batch_index": batch_index + 1,
                    "total_batches": total_batches,
                    "batch_ids": campaign_batch,
                    "campaign_ideas": batch_ideas,
                })

            except Exception as e:
                logger.error(f"Error in batch {batch_index + 1} ({campaign_batch}): {e}", exc_info=True)
                yield emit(event_type="batch_error", 
                    data={
                        "batch_index": batch_index + 1,
                        "total_batches": total_batches,
                        "batch_ids": campaign_batch,
                        "error": str(e),
                    })

        yield emit("completed", {"total_batches": total_batches})

    def run(self, batch_size=10) -> dict:
        campaign_idea_ids = self._generate_campaign_ids().get("campaign_idea_ids", [])
        logger.info(f"Generated {len(campaign_idea_ids)} campaign idea IDs: {campaign_idea_ids}")

        all_campaign_ideas = []
        for campaign_batch in self.yield_items(items=campaign_idea_ids, chunk_size=batch_size):
            try:
                batch_ideas = self.campaign_ideas(campaign_batch=campaign_batch)
                all_campaign_ideas.extend(batch_ideas)
            except Exception as e:
                logger.error(f"Error processing batch ({campaign_batch}): {e}", exc_info=True)

        return {
            "campaign_idea_ids": campaign_idea_ids,
            "campaign_ideas": all_campaign_ideas,
        }