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
            "batch_size": kwargs.get("batch_size", 10),
        }
        agent = ProductCohortGenerationAgent(**params)
        for event in agent.run_with_events(batch_size = 10):   
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
            "model_identifier": kwargs.get("model_identifier", "azure-gpt-4o")
        }

        cohort_generation_agent = ProductCohortGenerationAgent(
            **params
            )
        output = cohort_generation_agent.run(15)
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
        source = kwargs.get("source", None)
        brochure_url = kwargs.get("brochure_url", None)
        product_website_url = kwargs.get("product_website_url", None)
        model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
        affinity_score_agent = AffinityEngineAgent(interaction_json=source, brochure_url=brochure_url, product_website_url=product_website_url, model_identifier=model_identifier)
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


@gryd.is_a_task()
def campaign_idea_generation_agent(*args, **kwargs):
    try:
        from campaign_idea_generation_agent import CampaignIdeaGeneratorAgent

        source = kwargs.get("source", None)                                 # Custom Interaction Data in Dict
        classified_cohort = kwargs.get("classified_cohort", None)           # Cohort Classification Result 
        affinity_score = kwargs.get("affinity_score", None)                 # Custom Affinity Score Result
        brochure_url = kwargs.get("brochure_url", None)                     # Brochure URL
        product_website_url = kwargs.get("product_website_url", None)       # Product Website URL
        num_of_campaign_ideas = kwargs.get("num_of_campaign_ideas", 5)
        num_of_campaign_post_sets = kwargs.get("num_of_campaign_post_sets", 5)
        num_of_hashtags = kwargs.get("num_of_hashtags", 20)

        campaign_theme = kwargs.get("campaign_theme", None)
        core_message_direction = kwargs.get("core_message_direction", None)
        campaign_objective = kwargs.get("campaign_objective", None)
        consumer_insight = kwargs.get("consumer_insight", None)

        model_identifier = kwargs.get("model_identifier", "azure-gpt-4o")
        campaign_idea_generation_agent = CampaignIdeaGeneratorAgent(
            source=source, 
            classified_cohort=classified_cohort, 
            affinity_score=affinity_score,
            brochure_url=brochure_url,
            product_website_url=product_website_url,
            model_identifier=model_identifier)
        output = campaign_idea_generation_agent.run(
            num_of_campaign_ideas = num_of_campaign_ideas,
            num_of_campaign_post_sets = num_of_campaign_post_sets, 
            num_of_hashtags = num_of_hashtags,
            campaign_theme = campaign_theme,
            core_message_direction = core_message_direction,
            campaign_objective = campaign_objective,
            consumer_insight = consumer_insight
            )
        return {
            "task": inspect.currentframe().f_code.co_name, 
            "campaign_ideas": output
        }
    except Exception as e:
        logger.error(f"Campaign Idea Generation Agent Error: {e}")
        traceback.print_exc()
        return {
            "task": inspect.currentframe().f_code.co_name,
            "error": str(e).strip()
        }


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
    cohort_registry = cohort_generation_agent(
        brochure_url="https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/1f0e5109-ead3-42e9-8af8-b58b8942b10f-6966062a_New-Jeep-Meridian-Brochure.pdf",
        model_identifier="azure-gpt-4o"
    )

    print(json.dumps(cohort_registry, indent=4, default=str))
    assert False

    # 2. Cohort Classification

    classified_cohort = cohort_classification_agent(
        source="https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/1f0e5109-ead3-42e9-8af8-b58b8942b10f-6966062a_New-Jeep-Meridian-Brochure.pdf",
        brochure_url="https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/1f0e5109-ead3-42e9-8af8-b58b8942b10f-6966062a_New-Jeep-Meridian-Brochure.pdf",
        product_website_url="https://www.new-jeep.com/meridian",
        cohorts=cohort_registry,
        model_identifier="azure-gpt-4o"
    )

    # 3. Affinity Score
    # 4. Campaign Idea Generation



    