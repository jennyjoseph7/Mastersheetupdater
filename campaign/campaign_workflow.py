import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from config import AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_CAMPAIGN_SERVICE_NAME, AUTOCRM_AGENT_SERVICE_NAME, gryd, hp, AutocrmModel
from autocrm_db_helper import get_pg_connector
from typing import List, Union, Dict, Any
from functools import reduce

gryd.SERVICE = AUTOCRM_CAMPAIGN_SERVICE_NAME
gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(gryd.SERVICE)

DISPOSITION_MAP = {
    "sent": "attempted",
    "delivered": "reached",
    "read": "contacted",
    "failed": "failed",
    "fail": "failed",
    "error": "error",
    "unsubscribed": "error",
    "spam": "failed",
    "bounced": "error",
    "complaint": "error",
    "forward": "reached",
    "engaged": "engaged",
    'attempted': 'attempted',
    'reached': 'reached',
    'contacted': 'contacted',
    'engaged': 'engaged',
    'converted': 'converted',
    "reply": "engaged",
    "converted": "converted",
    "dnd": "error",
    "blocked": "error", 
    "greeting_completed": "contacted",
    "not_reachable": "failed",
    "rejected": "failed",
    "busy": "failed",
    "no_answer": "failed",
    "no-answer": "failed",
    "voicemail": "contacted",
    "called": "attempted",
    "invalid_number": "error",
    "user_part_of_experiment": "failed",
    "message_undeliverable": "error",
    "unable_to_send": "error",
    "unable_to_deliver": "error",
    "message_undelivered_to_maintain_health": "failed",
    "cancelled": "failed",
    "queued": "queued",
    "ringing": "reached",
    "answered":"contacted",
    "in-progress": "contacted",
    "completed": "engaged",
    "no-answer": "failed",
    "initiated": "queued",
}

def dict_appender(a, b):
    a[b[1]].append(b[0])
    return a

PROVIDER_STATUS_MAP = reduce(dict_appender,
    DISPOSITION_MAP.items(),
    {s: [] for s in set(DISPOSITION_MAP.values())}
)

DISPOSITION_DETAIL_MAP = {

}

CHANNEL_IDENTIFIER_MAP = {
    "whatsapp": "phone_number",
    "voice": "phone_number",
    "voicebot": "phone_number",
    "email": "email",
    "sms": "phone_number"
}

mlogger = gryd.hp.get_logger(gryd.SERVICE)


def get_model_and_attrs(campaign_type: str, enterprise_id: str = None):
    enterprise_id = enterprise_id or AUTOCRM_APP_ENTERPRISE_ID
    if campaign_type == "pre-sales":
        campaign_model = gryd.base_model.Model("pre_sales_campaign", enterprise_id)
        lead_model = gryd.base_model.Model("pre_sales_lead", enterprise_id)
        user_model = gryd.base_model.Model("person", enterprise_id)
        user_id_attr = "user_id"
        lead_id_attr = "pre_sales_lead_id"
    elif campaign_type == "post-sales":
        campaign_model = gryd.base_model.Model("post_sales_campaign", enterprise_id)
        lead_model = gryd.base_model.Model("post_sales_lead", enterprise_id)
        user_model = gryd.base_model.Model("vehicle", enterprise_id)
        user_id_attr = "vehicle_id"
        lead_id_attr = "post_sales_lead_id"
    elif campaign_type == "dealership":
        campaign_model = gryd.base_model.Model("dealership_campaign", enterprise_id)
        lead_model = gryd.base_model.Model("dealership_lead", enterprise_id)
        user_model = gryd.base_model.Model("dealership", enterprise_id)
        user_id_attr = "dealership_id"
        lead_id_attr = "dealership_lead_id"
    else:
        raise ValueError(f"Invalid campaign type: {campaign_type}")
    return campaign_model, lead_model, user_model, user_id_attr, lead_id_attr

@gryd.is_a_task(function_name="run_workflow", job_param='job', auth_param='auth', logger_param='logger')
def run_workflow(
        campaign_id: str, 
        campaign_type: str,
        channel: str, 
        channel_identifier: str,
        next_flow_dict: dict, 
        lead_id: Union[str, None] = None,
        user_id: Union[str, None] = None, 
        session_id: Union[str, None] = None, 
        delay:int = 0, 
        enterprise_id: Union[str, None] = None, 
        logger=None, job=None, auth=None, *args, **kwargs
    ):
    enterprise_id = enterprise_id or auth.get('enterprise_id') or AUTOCRM_APP_ENTERPRISE_ID
    logger = logger or mlogger
    campaign_type = campaign_type.lower()
    channel = channel.lower()
    campaign_model, lead_model, user_model, user_id_attr, lead_id_attr = get_model_and_attrs(campaign_type)
    channel_identifier_name = CHANNEL_IDENTIFIER_MAP.get(channel)
    if not channel_identifier_name:
        msg = f"Invalid channel: {channel} for campaign_id={campaign_id}, campaign_type={campaign_type}, enterprise_id={enterprise_id}, doing nothing."
        logger.error(msg)
        raise ValueError(msg)
    campaign_workflow = gryd.base_model.Model('campaign_workflow', enterprise_id)
    campaign_workflow = campaign_workflow.list(_page_size=1, _as_option=True, campaign_id=campaign_id, channel=channel)
    if not campaign_workflow:
        msg = f"No campaign workflow found for campaign_id={campaign_id}, channel={channel}, enterprise_id={enterprise_id}, doing nothing."
        logger.error(msg)
        raise ValueError(msg)
    campaign_workflow = hp.make_single(campaign_workflow)
    logger.info(f"Running next workflow for {channel_identifier_name}={channel_identifier} for campaign_id={campaign_id}, campaign_type={campaign_type}, enterprise_id={enterprise_id}")
    logger.info(f"next_flow_dict={hp.json.dumps(next_flow_dict, hp.json.OPT_INDENT_2)}, delay={delay}")
    lead_model = gryd.load_gryd_model(lead_model, enterprise_id)
    session_model = gryd.load_gryd_model('session', enterprise_id)
    user_model = gryd.load_gryd_model(user_model, enterprise_id)
    campaign = campaign_model.get(campaign_id)
    if not campaign:
        msg = f"No campaign found for campaign_id={campaign_id}, campaign_type={campaign_type}, enterprise_id={enterprise_id}, doing nothing."
        logger.error(msg)
        raise ValueError(msg)
    if not lead_id:
        if session_id:
            last_session = session_model.get(session_id)
            lead_id = last_session.get('lead_id')
        if not lead_id:
            msg = f"No lead_id found for session_id={session_id}, campaign_id={campaign_id}, campaign_type={campaign_type}, enterprise_id={enterprise_id}, doing nothing."
            logger.error(msg)
            raise ValueError(msg)
    if not user_id and session_id:
        last_session = session_model.get(session_id)
        user_id = last_session.get('user_id')
    if not user_id and last_session:
        user_id = last_session.get('user_id')
    if not user_id and lead:
        user_id = lead.get('user_id')
    if not session_id:
        last_session = session_model.list(_page_size=1, _as_option=True, campaign_id=campaign_id, channel=channel, **{channel_identifier_name: channel_identifier}, _sort_by="updated", _sort_reverse=True)
    else:
        last_session = session_model.get(session_id)
    if not user_id and last_session:
        user_id = last_session.get('user_id')
    if user_id:
        user = user_model.get(user_id)
    elif last_session:
        user
        user = None
    if lead_id:
        lead = lead_model.get(lead_id)
    kwargs = {
        "enterprise_id": enterprise_id,
        'campaign_id': campaign_id,
        'campaign_type': campaign_type,
        'channel': channel,
        'lead': lead,
    }
    kwargs[channel_identifier_name] = channel_identifier
    kwargs[f'{campaign_type.replace("-", "_")}_id'] = lead_id
    gryd.create_async_task('RunCampaignOrCreater', AUTOCRM_CAMPAIGN_SERVICE_NAME, kwargs=kwargs)

def get_proceed_status(channels: list, lead_detail: dict, max_attempts: int = 3, max_failed: int = 10, logger=None):
    logger = logger or mlogger
    status_model = AutocrmModel('contact_status')
    for channel in channels:


    channel = lead_detail.get('channel')
    campaign_id = lead_detail.get('campaign_id')
    lead_id = lead_detail.get('lead_id')
    disposition = lead_detail.get('disposition')
    disposition_detail = lead_detail.get('disposition_detail')
    if disposition in ["engaged", "converted"]:
        return False
    is_error = len([s for s in lead_detail if s.get('disposition', '') in ["error", "queued"]]) > 0
    if is_error:
        logger.info(f"Contact with user {user_id} in channel {channel} has already resulted in error for campaign_id={campaign_id}, doing nothing.")
        return False
    is_failed = len([s for s in user_details if s.get('disposition', '') in ["failed", "queued"]]) > max_failed
    if is_failed:
        logger.info(f"Contact with user {user_id} in channel {channel} has already failed {max_failed} times for campaign_id={campaign_id}, doing nothing.")
        return False
    is_un_contacted = len([s for s in user_details if s.get('disposition', '') in ["reached", "attempted"]]) > max_attempts
    if is_un_contacted:
        logger.info(f"Contact with user {user_id} in channel {channel} has been attempted {max_attempts} times for campaign_id={campaign_id}, doing nothing.")
        return False
    return True

@gryd.is_a_task(function_name="get_channel_from_lead", job_param='job', auth_param='auth', logger_param='logger')
def get_channel_from_lead(lead: dict, campaign_details: dict, enterprise_id: Union[str, None] = None, logger=None, job=None, auth=None, *args, **kwargs):
    enterprise_id = enterprise_id or auth.get('enterprise_id') or AUTOCRM_APP_ENTERPRISE_ID
    logger = logger or mlogger
    # TODO: Implement this
    channel = "voice_phone"
    channel_identifier = lead.get('phone_number') or lead.get('alt_phone_number_2') or lead.get('alt_phone_number_3') or lead.get('alt_phone_number_4')
    return channel, channel_identifier

@gryd.is_a_task(function_name="determine_campaign_next_action", job_param='job', auth_param='auth', logger_param='logger')
def determine_campaign_next_action(
        campaign_type: str,
        lead_id: str,
        channel: str = None,
        channel_identifier: str = None,
        disposition: str = None,
        disposition_detail: str = None,
        enterprise_id: Union[str, None] = None,
        logger=None, job=None, auth=None, 
        *args, **kwargs):
    """
    This function is used to determine the next action for a campaign.
    1. Get the channel id from lead model
    2. Get the campaign id
    3. Extract all the channel identifiers from the lead, including the person model
    4. If there is a last contacted information, we can start with that and the iterate over the other credentials provided.
    5. Check if there any are inactive numbers and remove them from the list
    6. Iterate over the list and chexk which ones are failed or error in that channel and how many times
    7. If the number of times threshold is completed, then we go to the next number on the list for same channel 
    8. If all the attempts have failed or attempted then go to next channel
    10. If we have connected, then we will try again for N times with a delay
    11. If we have interacted, then we will process based on disposition detail.
    12. If all avenues and channels are exhausted we will do nothing.
    Args:
        campaign_type: The type of campaign.
        lead_id: The ID of the lead.
        channel: The channel of the campaign.
        channel_identifier: The channel identifier of the campaign.
        disposition: The disposition of the campaign.
        disposition_detail: The disposition detail of the campaign.
        enterprise_id: The ID of the enterprise.
        logger: The logger object.
        job: The job object.
        auth: The auth object.
        args: The arguments.
        kwargs: The keyword arguments.
    Returns:
        A dictionary containing the next action for a campaign.
        {
            "next_channel": "channel",
            "next_channel_identifier": "channel_identifier",
            "template_id": "template_id",
            "template_variables": "template_variables"
        }
        or None if no next action is found.
    """
    enterprise_id = enterprise_id or auth.get('enterprise_id') or AUTOCRM_APP_ENTERPRISE_ID
    logger = logger or mlogger
    campaign_type = campaign_type.lower()
    channel = channel.lower()
    campaign_model, lead_model, user_model, user_id_attr, lead_id_attr = get_model_and_attrs(campaign_type)
    dealership_model = gryd.base_model.Model('dealership', enterprise_id)
    campaign_objective_model = gryd.base_model.Model('campaign_objective', enterprise_id)
    lead = None
    _values = {}
    for _id_attr, _model in [
            (lead_id_attr, lead_model), 
            (user_id_attr, user_model), 
            ('campaign_id', campaign_model), 
            ('dealership_id', dealership_model), 
            ('campaign_objective_id', campaign_objective_model)
        ]:
        if not lead:
            _detail = lead = lead_model.get(lead_id)
            _id_value = lead_id
        else:
            _id_value = lead.get(_id_attr)
            _detail = _model.get(_id_value)
        if not _detail:
            str_msg = f"No {_model.name} found for {_id_attr}={_id_value}, campaign_type={campaign_type}, enterprise_id={enterprise_id}"
            logger.error(str_msg)
            raise ValueError(str_msg)
        _values[_model.name] = {
            "id": _id_value,
            "object": _detail
        }
    campaign_details = _values.get('campaign', {}).get('object')
    if not channel:
        channel, channel_identifier = get_channel_from_lead(lead, campaign_details)
    workflow_model = gryd.base_model.Model('campaign_workflow', enterprise_id)
    dispostion = dispostion.lower() 
    disposition_options = {
        "error": ["error", "queued"],
        "failed": ["failed", "queued"],
        "attempted": ["attempted", "queued", "engaged", "converted", "reached", "contacted"],
        "reached": ["reached", "queued", "contacted", "engaged", "converted", "attempted"],
        "contacted": ["contacted", "queued", "engaged", "converted"],
        "engaged": ["engaged", "queued", "converted"],
        "converted": ["converted", "queued"],
    }
    disposition = DISPOSITION_MAP.get(disposition)
    if not disposition:
        str_msg = f"Invalid disposition: {disposition} for campaign_type={campaign_type}, channel={channel}, enterprise_id={enterprise_id}"
        logger.error(str_msg)
        raise ValueError(str_msg)
    if disposition not in disposition_options:
        str_msg = f"Invalid disposition: {disposition} for campaign_type={campaign_type}, channel={channel}, enterprise_id={enterprise_id}"
        logger.error(str_msg)
        raise ValueError(str_msg)
    workflow_stage = disposition_options.get(disposition, [])
    workflows = workflow_model.list(
        _page_size=1, 
        _as_option=True, 
        campaign_type=campaign_type, 
        channel=channel, 
        campaign_objective_id=_values.get('campaign_objective', {}).get('id'),
        workflow_stage=workflow_stage
    )
    if not workflows:
        str_msg = f"No workflow found for campaign_type={campaign_type}, channel={channel}, campaign_objective_id={_values.get('campaign_objective', {}).get('id')}, disposition={disposition}, workflow_stage={workflow_stage}, enterprise_id={enterprise_id}, doing nothing."
        logger.info(str_msg)
        return
    next_workflow = hp.make_single(workflows, force = True)
    # Map disposition to workflow triggers
    trigger_map = {
        'error': ('on_error_trigger', 'on_error_trigger_id', 'on_error_retries', 'on_error_delay'),
        'failed': ('on_failed_trigger', 'on_failed_trigger_id', 'on_failed_retries', 'on_failed_delay'),
        'attempted': ('on_attempted_trigger', 'on_attempted_trigger_id', 'on_attempted_retries', 'on_attempted_delay'),
        'reached': ('on_reached_trigger', 'on_reached_trigger_id', 'on_reached_retries', 'on_reached_delay'),
        'contacted': ('on_contacted_trigger', 'on_contacted_trigger_id', 'on_contacted_retries', 'on_contacted_delay'),
        'engaged': ('on_engaged_trigger', 'on_engaged_trigger_id', 'on_engaged_retries', 'on_engaged_delay'),
        'converted': ('on_converted_trigger', 'on_converted_trigger_id', None, None)
    }
    # Get trigger details based on disposition
    trigger_field, trigger_id_field, retries_field, delay_field = trigger_map.get(disposition, (None, None, None, None))
    
    if not (trigger_field or (trigger_id_field and next_workflow.get(trigger_id_field))):
        str_msg = f"No trigger field found for disposition={disposition} in workflow={next_workflow}, doing nothing."
        logger.info(str_msg)
        return
    contact_status_model = gryd.base_model.Model('contact_status', enterprise_id)
    channel_identifier_name = CHANNEL_IDENTIFIER_MAP.get(channel)
    provider_statuses = PROVIDER_STATUS_MAP.get(disposition, [])
    cs_params = {
       channel_identifier_name : channel_identifier,
       'campaign_type': campaign_type,
       'campaign_id': _values.get('campaign', {}).get('id'),
       'channel': channel,
       'provider_status': provider_statuses,
       "_sort_by": "created",
       "_sort_reverse": True
    }
    contact_statuses = contact_status_model.list(_page_size=500, _as_option=True, **cs_params)
    status_count = len(contact_statuses)
    # Check if we've exceeded retries
    ## Get from campagign_user_detail, and campaign_user_detail_archive
    max_retries = next_workflow.get(retries_field, 0) if retries_field else 0
    logger.info(f"Max retries: {max_retries}, Status count: {status_count} for disposition={converted_disposition} in channel={channel}")

    if not max_retries or status_count > max_retries:
        logger.info(f"Max retries={max_retries} exceeded for disposition={converted_disposition} in channel={channel}, checking for next workflow.")
        # here i have to trigger the next workflow
        next_workflow = workflow.get(trigger_field, None)
        if not next_workflow:
            logger.info(f"No next workflow found for campaign_id={campaign_id}, channel={channel}, user_id={user_id}, session_id={session_id}, doing nothing.")
            return
        next_channel = next_workflow.get('channel', channel)
        if next_channel != channel:
            logger.info(f"Checking if next channel {next_channel} has already been triggered for this campaign")
            user_detail_proceed = get_user_details(enterprise_id, campaign_id, next_channel, user_id, started=f'{hp.time() - 86400},')
            is_proceed = get_proceed_status(user_detail_proceed)
            if not is_proceed:
                logger.info(f"User {user_id} has already been contacted today for campaign_id={campaign_id}, channel={channel}, doing nothing.")
                return
        run_workflow(
            enterprise_id, campaign_id, next_channel, user_id, session_id, 
            next_workflow, 0, hp.make_single(user_details, force = True), campaign_detail, i2ce_headers
        )
        logger.info(f"Triggered next workflow={hp.json.dumps(next_workflow, hp.json.OPT_INDENT_2)} for campaign_id={campaign_id}, channel={channel}, user_id={user_id}, session_id={session_id}")
        return
    # Create async task to send the message again
    if isinstance(max_retries, (int, float)) and max_retries > 0 and (max_retries - status_count) > 0:
        delay = workflow.get(delay_field, 0) if delay_field else 0
        logger.info(f"max_retries={max_retries}, status_count={status_count} for disposition={converted_disposition} in channel={channel}, triggering again with delay={delay}")
        run_workflow(
            enterprise_id, campaign_id, channel, user_id, session_id, 
            {}, delay, hp.make_single(user_details, force = True), campaign_detail, i2ce_headers)
        logger.info(f"Triggered message again for campaign_id={campaign_id}, channel={channel}, user_id={user_id}, session_id={session_id}")
        return
    logger.info(f"No more retries allowed for campaign_id={campaign_id}, channel={channel}, user_id={user_id}, session_id={session_id}, doing nothing.")
    return





