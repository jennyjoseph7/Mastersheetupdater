import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from config import AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_CAMPAIGN_SERVICE_NAME, AUTOCRM_AGENT_SERVICE_NAME, gryd, hp, AutocrmModel, AUTOCRM_ALLOWED_CHANNELS, AUTOCRM_CHEAPEST_CHANNELS
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


CHANNEL_IDENTIFIER_MAP = {
    "whatsapp": "phone_number",
    "whatsapp_chat": "phone_number",
    "voice_phone": "phone_number",
    "voice": "phone_number",
    "voicebot": "phone_number",
    "email": "email",
    "sms": "phone_number",
    "rcs": "phone_number",
    "whatsapp_voice_note": "phone_number",
    "whatsapp_voice_call": "phone_number"
}

CHANNEL_LAST_CONTACTED_MAP = {
    "whatsapp": "whatsapp_number",
    "whatsapp_chat": "whatsapp_number",
    "voice_phone": "phone_number",
    "voice": "phone_number",
    "voicebot": "phone_number",
    "email": "email",
    "sms": "phone_number",
    "rcs": "phone_number",
    "whatsapp_voice_note": "phone_number",
    "whatsapp_voice_call": "phone_number"
}

CAMPAIGN_WORKFLOW = {
    "failed": {
        "retries": 10,
        "delay_type": "exponential",
        "delay": 60,
        "trigger": "switch_to_next_credential"
    },
    "error": {
        "retries": 0,
        "trigger": "switch_to_next_credential"
    },
    "attempted": {
        "retries": 3,
        "delay": 3600,
        "trigger": "switch_to_next_credential"
    },
    "reached": {
        "retries": 0,
        "delay": 3600,
        "trigger": "switch_to_next_channel"
    },
    "contacted": {
        "retries": 0,
        "delay": 3600,
        "trigger": "switch_to_next_channel"
    },
    "engaged": {
        "retries": 10,
        "delay": 86400,
        "trigger": "follow_up_contact"
    },
    "converted": {
        "retries": 0,
        "delay": 0,
        "trigger": "confirmation_message"
    }
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


def get_proceed_status(channels: list, lead_detail: dict, max_attempts: int = 3, max_failed: int = 10, logger=None):
    logger = logger or mlogger
    status_model = AutocrmModel('contact_status')


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
def get_channel_from_lead(lead: dict, campaign_details: dict, enterprise_id: Union[str, None] = None, workflow = None, logger=None, job=None, auth=None, *args, **kwargs):
    """
    This function is used to get the next channel and channel identifier from the lead.
    Args:
        lead: The lead dictionary.
        campaign_details: The campaign details dictionary.
        enterprise_id: The enterprise ID.
        logger: The logger object.
        job: The job object.
        auth: The auth object.
    Returns:
        A tuple containing the (next channel, channel identifier, delay, and trigger).
        (next_channel, next_channel_identifier, next_delay, trigger)
        or None if no next action is found, we have to continue with the same action.
    """
    logger = logger or mlogger
    st = hp.time()
    logger.info("Loading models for get_channel_from_lead")
    enterprise_id = enterprise_id or auth.get('enterprise_id') or AUTOCRM_APP_ENTERPRISE_ID
    campaign_id = campaign_details.get('campaign_id')
    status_model = AutocrmModel('contact_status')
    email_status_model = AutocrmModel('email_status')
    phone_status_model = AutocrmModel('phone_number_status')
    logger.info(f"Loaded models for get_channel_from_lead in {hp.time() - st} seconds")
    channels = campaign_details.get('channels') or ["voice_phone"]
    logger.info(f"Channels: {channels} for campaign_id={campaign_id}, enterprise_id={enterprise_id}")
    for c in AUTOCRM_CHEAPEST_CHANNELS:
        # Sort by cheapest to most expensive
        if c in channels:
            channels.remove(c)
            channels.insert(0, c)
    logger.info(f"Sorted channels: {channels} for campaign_id={campaign_id}, enterprise_id={enterprise_id}")
    for channel in channels:
        channel_type = CHANNEL_IDENTIFIER_MAP.get(channel)
        logger.info(f"Processing channel: {channel} with type: {channel_type} for campaign_id={campaign_id}, enterprise_id={enterprise_id}")
        channel_identifier_list = []
        if channel_type == "phone_number":
            logger.info(f"Getting phone number identifiers for channel: {channel} for campaign_id={campaign_id}, enterprise_id={enterprise_id}")
            st1 = hp.time()
            channel_identifier_list = get_phone_number_identifier_from_lead(channel, lead)
            logger.info(f"Time taken to get phone number identifiers: {hp.time() - st1} seconds")
        elif channel_type == "email":
            logger.info(f"Getting email identifiers for channel: {channel} for campaign_id={campaign_id}, enterprise_id={enterprise_id}")
            st1 = hp.time()
            channel_identifier_list = get_email_identifier_from_lead(lead)
            logger.info(f"Time taken to get email identifiers: {hp.time() - st1} seconds")
        else:
            logger.error(f"Invalid channel: {channel} for campaign_id={campaign_id}, enterprise_id={enterprise_id}, doing nothing.")
            continue
        if not channel_identifier_list:
            logger.error(f"No channel identifiers found for channel: {channel} for campaign_id={campaign_id}, enterprise_id={enterprise_id}, doing nothing.")
            continue
        change_channel = False
        for channel_identifier in channel_identifier_list:
            logger.info(f"Processing channel identifier: {channel_identifier} for channel: {channel} for campaign_id={campaign_id}, enterprise_id={enterprise_id}")
            kws = {channel_type: channel_identifier}
            if channel_type == "phone_number":
                kws["channel"] = channel
            status = hp.make_single(status_model.list(_page_size=1, _as_option=True, **kws))
            if status:
                status_status = status.get('status', 'queued')
                attempts = status.get('attempts', 0)
                workflow_stage = (workflow or {}).get(status_status) or CAMPAIGN_WORKFLOW.get(status_status)
                next_delay_type = workflow_stage.get('delay_type', 'linear')
                next_delay = workflow_stage.get('delay', 0)
                if next_delay_type == "exponential":
                    next_delay = next_delay * 2 ** (attempts - 1)
                elif next_delay_type == "linear":
                    next_delay = next_delay * attempts
                next_retries = workflow_stage.get('retries', 0)
                if attempts < next_retries:
                    return channel, channel_identifier, next_delay, None
                trigger = workflow_stage.get('trigger', 'switch_to_next_credential')
                if trigger == "switch_to_next_credential":
                    continue
                elif trigger == "switch_to_next_channel":
                    change_channel = True
                    continue
                elif trigger == "follow_up_contact":
                    logger.info(f"Following up contact for channel: {channel} with channel identifier: {channel_identifier} for campaign_id={campaign_id}, enterprise_id={enterprise_id}")
                    logger.info(f"Time taken to get channel from lead: {hp.time() - st} seconds")
                    return channel, channel_identifier, next_delay, "follow_up_contact"
                elif trigger == "confirmation_message":
                    logger.info(f"Sending confirmation message for channel: {channel} with channel identifier: {channel_identifier} for campaign_id={campaign_id}, enterprise_id={enterprise_id}")
                    logger.info(f"Time taken to get channel from lead: {hp.time() - st} seconds")
                    return channel, channel_identifier, next_delay, "confirmation_message"
                continue
            if change_channel:
                break
    logger.info(f"No next action found for channel: {channel} for campaign_id={campaign_id}, enterprise_id={enterprise_id}, doing nothing.")
    logger.info(f"Time taken to get channel from lead: {hp.time() - st} seconds")
    return None, None, 0, None

def get_email_identifier_from_lead(lead: dict):
    rlist = []
    priority = []
    email_list = ["email", "alt_email_2", "alt_email_3", "alt_email_4"]
    email_last_contacted_name = "last_contacted_email"
    for email in email_list:
        if lead.get(email):
            if lead.get(email) in rlist:
                continue
            rlist.append(lead.get(email))
    for person in lead.get('persons_involved', []):
        for email in email_list:
            if person.get(email):
                if person.get(email) in rlist:
                    continue
                rlist.append(person.get(email))
                if person.get(email_last_contacted_name) == email:
                    priority.append((person.get(f'updated'), person.get(email_last_contacted_name)))
    priority.sort(key=lambda x: x[0])
    for p0, p1 in priority:
        if p1 in rlist:
            rlist.remove(p1)
        rlist.insert(0, p1)
    return rlist

def get_phone_number_identifier_from_lead(channel: str, lead: dict):
    rlist = []
    priority = []
    ph_list = ["phone_number", "alt_phone_number_2", "alt_phone_number_3", "alt_phone_number_4"]
    channel_last_contacted_name = CHANNEL_LAST_CONTACTED_MAP.get(channel)
    for ph in ph_list:
        if lead.get(ph):
            if lead.get(ph) in rlist:
                continue
            rlist.append(lead.get(ph))
    for person in lead.get('persons_involved', []):
        for ph in ph_list:
            if person.get(ph):
                if person.get(ph) in rlist:
                    continue
                rlist.append(person.get(ph))
        if person.get(channel_last_contacted_name) == ph:
            priority.append((person.get(f'updated'), person.get(channel_last_contacted_name)))
    priority.sort(key=lambda x: x[0])
    for p0, p1 in priority:
        if p1 in rlist:
            rlist.remove(p1)
        rlist.insert(0, p1)
    return rlist


def remap_workflow(workflows: dict, campaign_id: str, dealership_id: str, campaign_objective_id: str, campaign_type: str):
    ret = {}
    for status in PROVIDER_STATUS_MAP:
        for k in trigger_map:
            ret[k] = {
                'trigger': workflow.get(trigger_map.get(k)[0], CAMPAIGN_WORKFLOW.get(status).get('trigger')),
                'retries': workflow.get(trigger_map.get(k)[2], None),
                'delay': workflow.get(trigger_map.get(k)[3], None)
            }
    return ret

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
        "queued": ["queued"],
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
    workflow_stage = disposition_options.get(disposition, ['queued'])
    workflows = workflow_model.list(
        _page_size=1, 
        _as_option=True, 
        campaign_type=campaign_type, 
        channel=channel, 
        campaign_objective_id=_values.get('campaign_objective', {}).get('id'),
        workflow_stage=workflow_stage
    )
    next_workflow = hp.make_single(workflows, force = True)
    if next_workflow:
        next_workflow = remap_workflow(next_workflow)
    else:
        next_workflow = CAMPAIGN_WORKFLOW
    # Map disposition to workflow triggers
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

    gryd.create_async_task('RunCampaignOrCreater', AUTOCRM_CAMPAIGN_SERVICE_NAME, kwargs=kwargs)
    return





