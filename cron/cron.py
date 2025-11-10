import os
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from config import AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_CRON_SERVICE_NAME, AUTOCRM_AGENT_SERVICE_NAME, gryd, hp
from autocrm_db_helper import get_pg_connector
from typing import List, Union, Dict, Any

gryd.SERVICE = AUTOCRM_CRON_SERVICE_NAME
gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(gryd.SERVICE)

@gryd.is_a_task(logger_param='logger', job_param='job')
def create_campaign_ideas_for_dealerships(
        campaign_types:Union[List[str], None]=None, 
        campaign_objectives:Union[List[str], Dict[str, List[str]]]=None, 
        logger=None, job=None, *args, **kwargs
    ) -> Dict[str, int]:
    """
    This task creates campaign ideas for all dealerships.
    Args:
        campaign_types (list): The types of campaigns to create.
        campaign_objectives (list or dict): The objectives of the campaigns to create. If a dict, the key is the dealership id and the value is a list of objectives.
        depending on each campaign_type, for each dealership, we will be calling the create_campaign_idea task with the appropriate arguments.
        logger (Logger): The logger to use.
        job (Job): The job to use.
        return (dict): The number of campaign ideas created.
        *args: The arguments to pass to the task.
        **kwargs: The keyword arguments to pass to the task.
    """
    logger = logger or mlogger
    pre_sales_campaign_model = gryd.base_model.Model('pre_sales_campaign', AUTOCRM_APP_ENTERPRISE_ID)
    post_sales_campaign_model = gryd.base_model.Model('post_sales_campaign', AUTOCRM_APP_ENTERPRISE_ID)
    default_campaign_objectives = {
        'post-sales': post_sales_campaign_model._model_ref.attributes['campaign_objective'].options,
        'pre-sales': pre_sales_campaign_model._model_ref.attributes['campaign_objective'].options
    }
    campaign_types = hp.make_list(campaign_types or ['pre-sales', 'post-sales'])
    if isinstance(campaign_objectives, list):
        campaign_types = [campaign_types[0]]
        campaign_objectives = {campaign_types[0]: campaign_objectives}
    elif isinstance(campaign_objectives, dict):
        if any(k not in campaign_objectives for k in campaign_types):
            raise ValueError(f"All campaign_types {campaign_types} must be present in campaign_objectives dict. {campaign_objectives}")
    else:
        raise ValueError(f"campaign_objectives must be a list or dict. {campaign_objectives}")
    campaign_objectives = campaign_objectives or default_campaign_objectives
    dm = gryd.base_model.Model('dealership', AUTOCRM_APP_ENTERPRISE_ID)
    created_idea_count = 0
    for dealership in dm.yield_list():
        logger.info(f"Creating campaign ideas for dealership: {dealership['dealership_id']}")
        for campaign_type in campaign_types:
            logger.info(f"Creating campaign ideas for dealership: {dealership['dealership_id']} with campaign_type: {campaign_type}")
            for campaign_objective in campaign_objectives[campaign_type]:
                logger.info(f"Creating campaign idea for dealership: {dealership['dealership_id']} with campaign_type: {campaign_type} and campaign_objective: {campaign_objective}")
                dealership_idea = create_campaign_idea(dealership_id=dealership['dealership_id'], campaign_type=campaign_type, campaign_objective=campaign_objective, logger=logger, job=job)
                if dealership_idea:
                    created_idea_count += 1
                created_idea_count += 1
    return {
        "created_idea_count": created_idea_count,
    }


@gryd.is_a_task(logger_param='logger', job_param='job')
def create_campaign_idea(dealership_id:str, campaign_type:str, campaign_objective:str, languages:Union[List[str], None]=None, logger=None, job=None, *args, **kwargs) -> Dict[str, Any]:
    """
    This task creates a campaign idea for a dealership.
    Args:
        dealership_id (str): The id of the dealership.
        campaign_type (str): The type of campaign to create. Must be one of the campaign_types in the campaign_objectives dict.
        campaign_objective (str): The objective of the campaign to create. Must be one of the campaign_objectives in the campaign_objectives dict.
        languages (list): The languages to create the campaign idea in. If not provided, will use the default languages for the dealership.
        return (dict): The dealership idea created.
        logger (Logger): The logger to use.
        job (Job): The job to use.
        *args: The arguments to pass to the task.
        **kwargs: The keyword arguments to pass to the task.
    """
    logger = logger or mlogger
    dealership_idea_model = gryd.base_model.Model('dealership_idea', AUTOCRM_APP_ENTERPRISE_ID)
    kwargs.update({'dealership_id': dealership_id, 'languages': languages})
    logger.info(f"Creating campaign idea for dealership: {dealership_id} with campaign_type: {campaign_type} and campaign_objective: {campaign_objective} and languages: {languages}")
    dealership_idea = gryd.await_result(
        'generate_campaign_idea',AUTOCRM_AGENT_SERVICE_NAME, args=[campaign_type, campaign_objective], kwargs=kwargs, gryd_logger=logger, job_param=job
    )
    logger.info(f"Campaign idea created for dealership: {dealership_id} with campaign_type: {campaign_type} and campaign_objective: {campaign_objective} and languages: {languages}")
    return dealership_idea_model.post(dealership_idea)