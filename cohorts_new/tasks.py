import sys 
import os
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from gryd_worker import gryd
from typing import *
from cohorts_new.utils.utility import *
from cohorts_new.utils.common_utils import get_logger
import json
import traceback
import os
import inspect

from config import AUTOCRM_COHORT_CAMPAIGN_SERVICE_NAME
GRYD_SERVICE_NAME = AUTOCRM_COHORT_CAMPAIGN_SERVICE_NAME
GRYD_CONFIG = {
    "broker_type" : "sqs", 
    "timeout" : 10,
    "wait_time_to_shutdown" : 43200
}

logger = get_logger(__name__)

def setup_gryd():
    gryd.SERVICE = GRYD_SERVICE_NAME
    gryd.set_queue_manager(config = GRYD_CONFIG)
    # environment = os.getenv("ENVIRONMENT", "-local")
    # if not environment.startswith("-"):
    #     environment = f"-{environment}"
    # gryd.ENVIRONMENT = environment

setup_gryd()
# gryd.ENVIRONMENT = "-local"

@gryd.is_a_task(function_name="post_cohorts_to_model",)
def post_cohorts_to_model(*args, **kwargs):
    pass 

@gryd.is_a_task()
def cohort_generation_agent_async(*args, **kwargs):
    """
    This function is used to generate cohorts for a product in async manner.

    :param: brochure_url: brochure url of the product
    :param: product_website_url: website url of the product
    :param: num_of_cohorts: number of cohorts to generate
    :param: model_identifier: identifier of the model to use
    :param: additional_instruction: additional instruction to the model

    :return: list of dictionaries of cohorts
    """
    try:
        from agents.cohort_generation_agent import ProductCohortGenerationAgent
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
    """
    This function is used to generate cohorts for a product in sync manner.

    :param: brochure_url: brochure url of the product
    :param: product_website_url: website url of the product
    :param: num_of_cohorts: number of cohorts to generate
    :param: model_identifier: identifier of the model to use
    :param: additional_instruction: additional instruction to the model

    :return: list of dictionaries of cohorts
    """

    try:
        from agents.cohort_generation_agent import ProductCohortGenerationAgent

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
    """
    This function is used to classify user interaction data to one of the provided cohort.

    :param: source: custom data source, interaction data.
    :param: brochure_url: brochure url of the product. (Optional)
    :param: product_website_url: website url of the product (Optional)
    :param: model_identifier: identifier of the model to use (azure-gpt-4o)
    :param: cohorts: list of cohorts.
    :param: additional_instruction: additional instruction to the model
    :return: dict of classified cohort.

    """
    try:
        from agents.cohort_classification_agent import CohortClassificationAgent

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
    """
    This function is used to calculate affinity score between user interaction data and product brochure.

    :param: interaction_json: custom data source, interaction data.
    :param: brochure_url: brochure url of the product. (Optional)
    :param: product_website_url: website url of the product (Optional)
    :param: model_identifier: identifier of the model to use (azure-gpt-4o)
    :param: domain: domain of the product (Optional)
    :param: custom_affinity_dimensions: custom affinity dimensions (Optional)
    :return: dict of affinity score.

    """
    try:
        from agents.affinity_agent  import AffinityEngineAgent
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

        for key in ["affinity_fig_json", "fig_json"]:
            output.pop(key, None)

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
    

@gryd.is_a_task(function_name="embedding_affinity_score_agent", job_param='job', logger_param='logger')
def embedding_affinity_score_agent(*args, **kwargs):
    """
    This function is used to calculate affinity score between user interaction data and product brochure.

    :param: interaction_json: custom data source, interaction data.
    :param: brochure_url: brochure url of the product. (Optional)
    :param: product_website_url: website url of the product (Optional)
    :param: model_identifier: identifier of the model to use (azure-gpt-4o)
    :param: domain: domain of the product (Optional)
    :param: custom_affinity_dimensions: custom affinity dimensions (Optional)
    :return: dict of affinity score.

    """
    try:
        from agents.affinity_agent  import EmbeddingAffinityEngine
        params_ = {
            "interaction_json": kwargs.get("interaction_json", None),
            "custom_affinity_dimensions": kwargs.get("custom_affinity_dimensions", None)
        }
        affinity_score_agent = EmbeddingAffinityEngine(**params_)
        output = affinity_score_agent.calculate_affinity()
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


@gryd.is_a_task(function_name="campaign_idea_generation_agent", job_param='job', logger_param='logger')
def campaign_idea_generation_agent(*args, **kwargs):
    try:
        from agents.campaign_idea_generation_agent_async import CampaignIdeaGeneratorAgent
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
        from agents.campaign_idea_generation_agent_async import CampaignIdeaGeneratorAgent
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

@gryd.is_a_task(function_name="performance_marketing_campaign_agent")
def performance_marketing_campaign_agent(*args, **kwargs):
    _params = {
        "brand_name" : kwargs.get("brand_name", None),
        "product_name" : kwargs.get("product_name", None),
        "objective" : kwargs.get("objective", None),
        "budget" : kwargs.get("budget", None),
        "landing_page" : kwargs.get("landing_page", None),
        "geography" : kwargs.get("geography", None),
        "model_identifier" : kwargs.get("model_identifier", "azure-gpt-4o")
    }

    try:
        from agents.campaign_idea_generation_agent_async import PerformanceMarketingCampaignAgent
        agent = PerformanceMarketingCampaignAgent(**_params)
        output = agent.run()
        return {
            "task": inspect.currentframe().f_code.co_name, 
            **output
        }
    except Exception as e:
        logger.error(f"Performance Marketing Campaign Agent Error: {e}")
        raise e

@gryd.is_a_task(function_name="csv_to_cohort_classification")
def csv_to_cohort_classification(*args, **kwargs):
    import uuid
    _params = {
        "csv_url": kwargs.get("csv_url", None),
        "cohorts" : kwargs.get("cohorts", []),
        "model_identifier" : kwargs.get("model_identifier", "azure-gpt-4o")
    }
    task_id = str(uuid.uuid4())

    f_payload = {
        **_params,
        "task_id": task_id
    }
    gryd.create_async_task()
    pass 


@gryd.is_a_task(function_name="cohort_classification_agent_randomizer", job_param='job', logger_param='logger')
def cohort_classification_agent_randomizer(*args, **kwargs):
    _params = {
        "file_path": kwargs.get("file_path", None),
        "cohorts" : kwargs.get("cohorts", []),
        "random_seed" : kwargs.get("random_seed", 42)
    }

    # TODO : Create gryd task for this. Currently Dinesh will directly call API. 
    return {
        "task": inspect.currentframe().f_code.co_name,}


    
if __name__ == "__main__":

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


    # Testing all agents one by one 

    # 1. Cohort Generation 

    # cohorts = cohort_generation_agent(
    #     brochure_url="https://static-cdn.cars24.com/prod/vehicles/tata/sierra/the-all-new-tata-sierra-escape-mediocre-xTDLloobrGLs2WRt.pdf",
    #     product_website_url="https://cars.tatamotors.com/sierra/ice.html",
    #     model_identifier="gcp-gemini-2.5-flash",
    #     num_of_cohorts=5
    #     )
    
    # print(f"Cohorts: {json.dumps(cohorts, indent=4, default=str)}")

    cohort_registry = {
    "task": "cohort_generation_agent",
    "cohorts": [
        {
            "idx": 1,
            "cohort_id": "design_aspirational_suv_seekers",
            "cohort_name": "Design Aspirational SUV Seekers",
            "description": "This cohort is drawn to the Tata Sierra's award-winning, bold, and iconic design. They prioritize aesthetics, uniqueness, and making a statement, valuing the Red Dot recognition and distinctive exterior features that help them 'arrive differently'.",
        },
        {
            "idx": 2,
            "cohort_id": "advanced_tech_comfort_explorers",
            "cohort_name": "Advanced Tech & Comfort Explorers",
            "description": "This cohort seeks the ultimate in automotive innovation and luxurious comfort in the Tata Sierra. They are attracted to its cutting-edge technology like the Horizon View Triple Screen, HypAR HUD, ADAS L2+, and premium features such as the PanoraMax sunroof and JBL Dolby Atmos sound system.",
        },
        {
            "idx": 3,
            "cohort_id": "family_safety_assurance_seekers",
            "cohort_name": "Family Safety & Assurance Seekers",
            "description": "This cohort prioritizes the safety and comfort of their family above all else when considering the Tata Sierra. They are keen on its comprehensive safety suite, including 6 airbags, ADAS L2+, ESP with 21 features, ISOFIX, and family-friendly comforts like spacious interiors and rear AC.",
        },
        {
            "idx": 4,
            "cohort_id": "dynamic_drive_terrain_conquerors",
            "cohort_name": "Dynamic Drive & Terrain Conquerors",
            "description": "This cohort consists of enthusiasts who seek an exhilarating and commanding driving experience from the Tata Sierra. They value its powerful engine options (Hyperion, Kryojet), advanced driving dynamics like Terrain Modes, Sport Mode, and robust suspension designed to 'escape limits' and dominate varied terrains.",
        },
        {
            "idx": 5,
            "cohort_id": "aspirational_first_time_suv_buyers",
            "cohort_name": "Aspirational First-Time SUV Buyers",
            "description": "This cohort represents customers making their first foray into the SUV segment, drawn to the Tata Sierra's aspirational brand positioning and accessible entry price point. They seek a balance of modern features, style, and the experience of 'owning an iconic car', often considering the Pure or Smart+ variants as their entry into the segment.",
        }
        ]
    }


    from config import post_autocrm_model, AutocrmModel

    # m = post_autocrm_model(model_name="cohort_registry")
    # print(f"Cohort Registry Model: \n {json.dumps(m, indent=4, default=str)}")

    m = AutocrmModel(model_name="cohort_registry")

    cr = {"cohorts": []}
    cohort_registry = cohort_registry["cohorts"]
    for i in cohort_registry:
        temp = {}
        for k, v in i.items():
            if k in ["idx"]:
                continue
            else:
                temp[k] = v
        
        cr["cohorts"].append(temp)
    
    
    _payload = {
        "oem_name": "Tata",
        "product_name": "Sierra",
        "cohort_version" : "v1",
        "cohort_registry": cr
    }

    # obj = m.post(data = _payload)

    # print(f"Cohort Registry Data: \n {json.dumps(obj, indent=4, default=str)}")

    # assert False


    all_data = m.list(_as_optional=True)
    print(f"Cohort Registry Data: \n {json.dumps(all_data, indent=4, default=str)}")

    assert False


    # 2. Cohort Classification
    classified_users = cohort_classification_agent(
        source=t_json,
        cohorts=cohort_registry,
        model_identifier="gcp-gemini-2.5-flash"
    )

    print(f"Classified Users: {json.dumps(classified_users, indent=4, default=str)}")

    assert False


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



    # with open("Untitled (1).json", "r") as f:
    #     mohit = json.load(f)
    
    # a = affinity_score_agent(
    #     interaction_json=mohit,
    #     # brochure_url="https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/1f0e5109-ead3-42e9-8af8-b58b8942b10f-6966062a_New-Jeep-Meridian-Brochure.pdf",
    #     # product_website_url="https://www.new-jeep.com/meridian",
    #     model_identifier="azure-gpt-4o",
    #     custom_affinity_dimensions = ["safety_feature", "customer_experience", "visuals", "usage_frequency"]
    # )

    # print(f"Affinity Result : \n\n {json.dumps(a, indent=4)}")
    # assert False


    # from agents.affinity_agent import EmbeddingAffinityEngine
    # func = EmbeddingAffinityEngine._get_embedding_via_ai_service

    result = embedding_affinity_score_agent(
        interaction_json=t_json,
        model_identifier="azure-gpt-4o",
        custom_affinity_dimensions = ["price", "features", "performance", "design", "interior", "exterior"]
    )

    # result = func(texts=["hello", "world"])

    print(f"Embedding Result : \n\n {json.dumps(result, indent=4)}")

    assert False

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



    