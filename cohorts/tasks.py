from gryd_worker import gryd
from typing import *
from common_utils import *
from utility import *
import json
import traceback
import os
import inspect

logger = get_logger(__name__)

def setup_gryd():
    gryd.SERVICE = GRYD_SERVICE_NAME
    gryd.set_queue_manager(config = GRYD_CONFIG)
    environment = os.getenv("ENVIRONMENT", "-local")
    if not environment.startswith("-"):
        environment = f"-{environment}"
    gryd.ENVIRONMENT = environment

setup_gryd()

@gryd.is_a_task()
def cohort_generation_agent_async(*args, **kwargs):
    try:
        from cohort_generation_agent import ProductCohortGenerationAgent
        params = {
            "brochure_url": kwargs.get("brochure_url", None),
            "product_website_url": kwargs.get("product_website_url", None),
            "model_identifier": kwargs.get("model_identifier", "azure-gpt-4o"),
            "additional_instruction": kwargs.get("additional_instruction", None),
            "num_of_cohorts": kwargs.get("num_of_cohorts", 30),
        }
        agent = ProductCohortGenerationAgent(**params)
        for event in agent.run_with_events(batch_size = kwargs.get("batch_size", 10)):   
            yield {
                "task": inspect.currentframe().f_code.co_name,
                **event
            }
    except Exception as e:
        logger.error(traceback.format_exc())
        yield {
            "task": inspect.currentframe().f_code.co_name,
            "status": "error",
            "error": str(e)
        }


@gryd.is_a_task()
def cohort_generation_agent(*args, **kwargs):
    try:
        from cohort_generation_agent import ProductCohortGenerationAgent

        params = {
            "brochure_url": kwargs.get("brochure_url", None),
            "product_website_url": kwargs.get("product_website_url", None),
            "model_identifier": kwargs.get("model_identifier", "azure-gpt-4o"),
            "additional_instruction": kwargs.get("additional_instruction", None),
            "num_of_cohorts": kwargs.get("num_of_cohorts", 30),
        }

        batch_size = kwargs.get("batch_size", 10)   

        cohort_generation_agent = ProductCohortGenerationAgent(**params)
        output = cohort_generation_agent.run(batch_size=batch_size)
        return {
            "task": inspect.currentframe().f_code.co_name, 
            **output
        }
    except Exception as e:
        logger.error(f"Cohort Generation Agent Error: {e}")
        traceback.print_exc()
        return {
            "task": inspect.currentframe().f_code.co_name,
            "error": str(e).strip()
        }


@gryd.is_a_task()
def cohort_classification_agent(*args, **kwargs):
    try:
        from cohort_classification_agent import CohortClassificationAgent

        params = {
            "source": kwargs.get("source", None),
            "brochure_url": kwargs.get("brochure_url", None),
            "product_website_url": kwargs.get("product_website_url", None),
            "cohorts": kwargs.get("cohorts", None),
            "additional_instruction": kwargs.get("additional_instruction", None),
            "model_identifier": kwargs.get("model_identifier", "azure-gpt-4o")
        }

        cohort_classification_agent = CohortClassificationAgent(**params)
        output = cohort_classification_agent.run()
        return {
            "task": inspect.currentframe().f_code.co_name, 
            **output
        }
    except Exception as e:
        logger.error(f"Cohort Classification Agent Error: {e}")
        traceback.print_exc()
        return {
            "task": inspect.currentframe().f_code.co_name,
            "error": str(e).strip()
        }

@gryd.is_a_task()
def affinity_score_agent(*args, **kwargs):
    try:
        from affinity_agent  import AffinityEngineAgent
        params_ = {
            "interaction_json": kwargs.get("interaction_json", None),
            "brochure_url": kwargs.get("brochure_url", None),
            "product_website_url": kwargs.get("product_website_url", None),
            "model_identifier": kwargs.get("model_identifier", "azure-gpt-4o"),
            "domain": kwargs.get("domain", None),
            "custom_affinity_dimensions": kwargs.get("custom_affinity_dimensions", None)
        }
        affinity_score_agent = AffinityEngineAgent(**params_)
        output = affinity_score_agent.run()
        return {
            "task": inspect.currentframe().f_code.co_name, 
            **output
        }
    except Exception as e:
        logger.error(f"Affinity Score Agent Error: {e}")
        traceback.print_exc()
        return {
            "task": inspect.currentframe().f_code.co_name,
            "error": str(e).strip()
        }


# @gryd.is_a_task()
# def campaign_idea_generation_agent(*args, **kwargs):
#     try:
#         from campaign_idea_generation_agent import CampaignIdeaGeneratorAgent

#         source = kwargs.get("source", None)                                 # Custom Interaction Data in Dict
#         classified_cohort = kwargs.get("classified_cohort", None)           # Cohort Classification Result 
#         affinity_score = kwargs.get("affinity_score", None)                 # Custom Affinity Score Result
#         brochure_url = kwargs.get("brochure_url", None)                     # Brochure URL
#         product_website_url = kwargs.get("product_website_url", None)       # Product Website URL
#         num_of_campaign_ideas = kwargs.get("num_of_campaign_ideas", 5)
#         num_of_campaign_post_sets = kwargs.get("num_of_campaign_post_sets", 5)
#         num_of_hashtags = kwargs.get("num_of_hashtags", 20)

#         campaign_theme = kwargs.get("campaign_theme", None)
#         core_message_direction = kwargs.get("core_message_direction", None)
#         campaign_objective = kwargs.get("campaign_objective", None)
#         consumer_insight = kwargs.get("consumer_insight", None)

#         model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
#         campaign_idea_generation_agent = CampaignIdeaGeneratorAgent(
#             source=source, 
#             classified_cohort=classified_cohort, 
#             affinity_score=affinity_score,
#             brochure_url=brochure_url,
#             product_website_url=product_website_url,
#             model_identifier=model_identifier)
#         output = campaign_idea_generation_agent.run(
#             num_of_campaign_ideas = num_of_campaign_ideas,
#             num_of_campaign_post_sets = num_of_campaign_post_sets, 
#             num_of_hashtags = num_of_hashtags,
#             campaign_theme = campaign_theme,
#             core_message_direction = core_message_direction,
#             campaign_objective = campaign_objective,
#             consumer_insight = consumer_insight
#             )
#         return {
#             "task": inspect.currentframe().f_code.co_name, 
#             "campaign_ideas": output
#         }
#     except Exception as e:
#         logger.error(f"Campaign Idea Generation Agent Error: {e}")
#         traceback.print_exc()
#         return {
#             "task": inspect.currentframe().f_code.co_name,
#             "error": str(e).strip()
#         }


@gryd.is_a_task(function_name="campaign_idea_generation_agent", job_param='job', logger_param='logger')
def campaign_idea_generation_agent(*args, **kwargs):
    try:
        from campaign_idea_generation_agent_async import CampaignIdeaGeneratorAgent
        _params = {
            "source": kwargs.get("source", None),                                 # Custom Interaction Data in Dict
            "classified_cohort": kwargs.get("classified_cohort", None),           # Cohort Classification Result 
            "affinity_score": kwargs.get("affinity_score", None),                 # Custom Affinity Score Result
            "brochure_url": kwargs.get("brochure_url", None),                     # Brochure URL
            "product_website_url": kwargs.get("product_website_url", None),       # Product Website URL
            "campaign_theme": kwargs.get("campaign_theme", None),
            "core_message_direction": kwargs.get("core_message_direction", None),
            "campaign_objective": kwargs.get("campaign_objective", None),
            "consumer_insight": kwargs.get("consumer_insight", None),
            "additional_instruction": kwargs.get("additional_instruction", None),
            "num_of_campaign_ideas": kwargs.get("num_of_campaign_ideas", 3), 
            "num_of_campaign_post_sets": kwargs.get("num_of_campaign_post_sets", 3), 
            "num_of_hashtags": kwargs.get("num_of_hashtags", 20),
            "model_identifier": kwargs.get("model_identifier", "azure-gpt-4o")
        }
        agent = CampaignIdeaGeneratorAgent(**_params)
        output = agent.run(batch_size=kwargs.get("batch_size", 2))
        return {
            "task": inspect.currentframe().f_code.co_name, 
            **output
        }
    except Exception as e:
        logger.error(f"Campaign Idea Generation Agent Error: {e}")
        raise e
@gryd.is_a_task(function_name="campaign_idea_generation_agent_async", job_param='job', logger_param='logger')
def campaign_idea_generation_agent_async(*args, **kwargs):
    try:
        from campaign_idea_generation_agent_async import CampaignIdeaGeneratorAgent
        _params = {
            "source": kwargs.get("source", None),                                 # Custom Interaction Data in Dict
            "classified_cohort": kwargs.get("classified_cohort", None),           # Cohort Classification Result 
            "affinity_score": kwargs.get("affinity_score", None),                 # Custom Affinity Score Result
            "brochure_url": kwargs.get("brochure_url", None),                     # Brochure URL
            "product_website_url": kwargs.get("product_website_url", None),       # Product Website URL
            "campaign_theme": kwargs.get("campaign_theme", None),
            "core_message_direction": kwargs.get("core_message_direction", None),
            "campaign_objective": kwargs.get("campaign_objective", None),
            "consumer_insight": kwargs.get("consumer_insight", None),
            "additional_instruction": kwargs.get("additional_instruction", None),
            "num_of_campaign_ideas": kwargs.get("num_of_campaign_ideas", 3), 
            "num_of_campaign_post_sets": kwargs.get("num_of_campaign_post_sets", 3), 
            "num_of_hashtags": kwargs.get("num_of_hashtags", 20),
            "model_identifier": kwargs.get("model_identifier", "azure-gpt-4o")
        }
        agent = CampaignIdeaGeneratorAgent(**_params)
        output = agent.run_with_events(batch_size=kwargs.get("batch_size", 2))
        for event in output:
            yield {
                "task": inspect.currentframe().f_code.co_name,
                **event
            }
    except Exception as e:
        logger.error(f"Campaign Idea Generation Agent Error: {e}")
        raise e     


if __name__ == "__main__":

    # 1. Cohort Generation Async
    # result_generator = cohort_generation_agent_async(
    #     brochure_url="https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/1f0e5109-ead3-42e9-8af8-b58b8942b10f-6966062a_New-Jeep-Meridian-Brochure.pdf",
    #     model_identifier="azure-gpt-4o"
    # )

    # cohort_registry = []
    # for event in result_generator:
    #     if event.get("status") == "cohort":
    #         cohorts = event.get("cohorts", [])
    #         cohort_registry.extend(cohorts)

    # print(json.dumps(cohort_registry, indent=4, default=str)) 
    # assert False

    # 1. Cohort Generation
    # cohort_registry = cohort_generation_agent(
    #     brochure_url="https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/1f0e5109-ead3-42e9-8af8-b58b8942b10f-6966062a_New-Jeep-Meridian-Brochure.pdf",
    #     model_identifier="azure-gpt-4o"
    # )

    # print(json.dumps(cohort_registry, indent=4, default=str))
    # assert False

    # 2. Cohort Classification

    # classified_cohort = cohort_classification_agent(
    #     source="https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/1f0e5109-ead3-42e9-8af8-b58b8942b10f-6966062a_New-Jeep-Meridian-Brochure.pdf",
    #     brochure_url="https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/1f0e5109-ead3-42e9-8af8-b58b8942b10f-6966062a_New-Jeep-Meridian-Brochure.pdf",
    #     product_website_url="https://www.new-jeep.com/meridian",
    #     cohorts=cohort_registry,
    #     model_identifier="azure-gpt-4o"
    # )

    # 3. Affinity Score

    t_json ={
        "persona": "Design & Configurator Enthusiast",
        "user_id": "u_20251204_sierra_config_001",
        "fbp": "fb.1.1733300100.2847593021",
        "fbc": "fb.1.1733300100.IwAR_sierra_config_id",
        "ga_client_id": "GA1.2.2847593021.1733300000",
        "session_id": "sess_20251204_sierra_config_01",
        "session_start": "2025-12-04T14:25:18Z",
        "session_end": "2025-12-04T14:43:55Z",
        "session_duration_seconds": 1117,
        "utm": {
        "utm_source": "instagram",
        "utm_medium": "social",
        "utm_campaign": "sierra_3d_configurator",
        "utm_adgroup": "interactive_design_showcase",
        "utm_keyword": None,
        "utm_referrer": "https://www.instagram.com/"
        },
        "device": {
        "type": "mobile",
        "os": "iOS",
        "browser": "Safari",
        "screen_resolution": "1170x2532",
        "network_type": "5G"
        },
        "user_profile": {
        "visit_number": 2,
        "is_returning_user": True,
        "previous_visits": ["2025-12-01"]
        },
        "page_context": {
        "model": "Tata Sierra 2025",
        "page_url": "https://cars.tatamotors.com/sierra/ice.html",
        "page_category": "model_overview"
        },
        "interaction": {
        "clicked_sections": [
            "3D Configurator",
            "Exterior Gallery",
            "Color Options",
            "Wheel Options",
            "Accessories & Packs",
            "Interior Gallery"
        ],
        "click_counts": {
            "3D Configurator": 42,
            "Exterior Gallery": 24,
            "Color Options": 31,
            "Wheel Options": 18,
            "Accessories & Packs": 22,
            "Interior Gallery": 15,
            "Variants": 4,
            "Specifications": 2,
            "Performance": 1
        },
        "time_spent_per_section": {
            "3D Configurator": 524,
            "Color Options": 298,
            "Exterior Gallery": 167,
            "Accessories & Packs": 89,
            "Interior Gallery": 39
        },
        "images_viewed": {
            "exterior_images": 38,
            "interior_images": 22,
            "color_variants": 18,
            "wheel_options": 9
        },
        "3d_interactions": {
            "rotations": 78,
            "zoom_in": 42,
            "zoom_out": 35,
            "view_switches": [
            "exterior",
            "interior",
            "wheels",
            "roof_rails",
            "rear_view",
            "side_profile",
            "dashboard"
            ],
            "configurator": {
            "viewed": True,
            "color_changed": 15,
            "wheel_options_changed": 6,
            "accessories_added": [
                "Roq Edition Pack",
                "Elevated Executive Pack",
                "Roof Rails",
                "Chrome Exterior Kit"
            ],
            "configurations_saved": 4,
            "360_view_used": True
            }
        },
        "variant_interactions": {
            "variants_viewed": ["Accomplished", "Accomplished+"],
            "most_viewed_variant": "Accomplished+"
        },
        "color_preferences": {
            "colors_viewed": [
            "Andaman Adventure",
            "Bengal Rouge",
            "Coorg Clouds",
            "Munnar Mist",
            "Pristine White",
            "Pure Grey"
            ],
            "most_viewed_color": "Bengal Rouge",
            "color_view_count": {
            "Bengal Rouge": 9,
            "Andaman Adventure": 7,
            "Coorg Clouds": 5,
            "Munnar Mist": 4
            }
        }
        }

    }
    # a = affinity_score_agent(
    #     interaction_json=t_json,
    #     brochure_url="https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/1f0e5109-ead3-42e9-8af8-b58b8942b10f-6966062a_New-Jeep-Meridian-Brochure.pdf",
    #     product_website_url="https://www.new-jeep.com/meridian",
    #     model_identifier="azure-gpt-4o",
    #     custom_affinity_dimensions = ["price", "features", "performance", "design", "interior", "exterior"]
    # )

    # print(f"Affinity Result : \n\n {json.dumps(a, indent=4)}")

    # 4. Campaign Idea Generation

    classified_cohort = {
        "cohort_id": "configurator_and_color_options_explorer",
        "description": "Customers who have interacted with 3D Configurator and Color Options",
    }

    # result = campaign_idea_generation_agent(
    #     source = t_json,
    #     classified_cohort = classified_cohort,
    #     affinity_score = None,
    #     product_website_url="https://cars.tatamotors.com/sierra/ice.html",)

    # print(f"Campaign Idea Generation Result : \n\n {json.dumps(result, indent=4)}")


    async_ = campaign_idea_generation_agent_async(
        source = t_json,
        classified_cohort = classified_cohort,
        affinity_score = None,
        product_website_url="https://cars.tatamotors.com/sierra/ice.html",
        num_of_campaign_ideas = 3,
        num_of_campaign_post_sets = 3,
        num_of_hashtags = 20,
        model_identifier = "azure-gpt-4o"
    )


    for event in async_:
        print(json.dumps(event, indent=4))

    # print(f"Campaign Idea Generation Async Result : \n\n {json.dumps(async_, indent=4)}")



    