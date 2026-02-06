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

DISPOSITION_OPTIONS = {
    "queued": ["queued"],
    "error": ["error", "queued"],
    "failed": ["failed", "queued"],
    "attempted": ["attempted", "queued", "engaged", "converted", "reached", "contacted"],
    "reached": ["reached", "queued", "contacted", "engaged", "converted", "attempted"],
    "contacted": ["contacted", "queued", "engaged", "converted"],
    "engaged": ["engaged", "queued", "converted"],
    "converted": ["converted", "queued"],
}

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

def get_cheapest_channel(channels: list):
    for c in AUTOCRM_CHEAPEST_CHANNELS:
        if c in channels:
            return c
    return channels[0]

def sort_channel_by_cheapest(channels: list, current_channel: str = None):
    rlist = sorted(channels, key=lambda x: AUTOCRM_CHEAPEST_CHANNELS.index(x))
    if current_channel:
        rlist = rlist[rlist.index(current_channel):]
    return rlist

def get_highest_status(statuses: list):
    if not statuses:
        return "queued"
    mstatuses = set(map(lambda x: x.get('status'), statuses))
    for k in ["contacted", "reached", "attempted", "failed", "error", "queued"]:
        if k in mstatuses:
            return k
    return "queued"

def get_attempts(statuses: list, status: str):
    return sum(1 for _ in filter(lambda x: x.get('status') == status, statuses))

def get_next_delay(status: str, attempts: int, workflow_stage: dict):
    next_delay_type = workflow_stage.get('delay_type', 'linear')
    next_delay = workflow_stage.get('delay', 0)
    if next_delay_type == "exponential":
        next_delay = next_delay * 2 ** (attempts - 1)
    elif next_delay_type == "linear":
        next_delay = next_delay * attempts
    return next_delay

def get_remaining_retries(workflow_stage: dict, attempts: int = 0):
    return max(0, workflow_stage.get('retries', 0) - attempts)

def get_statuses(channel: str, channel_type: str, channel_identifier: str, status_model: AutocrmModel = None, campaign_id: str = None, dealership_id: str = None, logger=None):
    logger = logger or mlogger
    st = hp.time()
    status_model = status_model or AutocrmModel('contact_status')
    channel_type = CHANNEL_IDENTIFIER_MAP.get(channel)
    if not channel_type:
        raise ValueError(f"Invalid channel: {channel}, doing nothing.")
    kws = {"channel": channel, channel_type: channel_identifier, "_sort_by": "updated", "_sort_reverse": True, "_as_option":True, "_page_size":100}
    if channel_type == "phone_number":
        kws["channel"] = channel
    if campaign_id:
        kws["campaign_id"] = campaign_id
    if dealership_id:
        kws["dealership_id"] = dealership_id
    statuses = status_model.list(**kws)
    if not statuses and dealership_id:
        kws.pop("dealership_id", None)
        statuses = status_model.list(**kws)
    if not statuses and campaign_id:
        kws.pop("campaign_id", None)
        statuses = status_model.list(**kws)
    logger.info(f"Time taken to get statuses: {hp.time() - st} seconds")
    if not statuses:
        return None
    return statuses

def get_channel_identifier_from_lead(channel: str, lead: dict, channel_identifier: str = None, logger=None):
    logger = logger or mlogger
    st = hp.time()
    channel_identifier_list = []
    if channel == "phone_number":
        channel_identifier_list = get_phone_number_identifier_from_lead(channel, lead, logger=logger)
    elif channel == "email":
        channel_identifier_list = get_email_identifier_from_lead(lead, logger=logger)
    else:
        logger.error(f"Invalid channel: {channel}, doing nothing.")
    if channel_identifier:
        channel_identifier_list = channel_identifier_list[channel_identifier_list.index(channel_identifier):]
    logger.info(f"Time taken to get channel identifier: {hp.time() - st} seconds")
    return channel_identifier_list

@gryd.is_a_task(function_name="get_channel_from_lead", job_param='job', auth_param='auth', logger_param='logger')
def get_channel_from_lead(lead: dict, campaign_details: dict, enterprise_id: Union[str, None] = None, workflow = None, current_channel = None, current_channel_identifier = None, disposition = None, logger=None, job=None, auth=None, *args, **kwargs):
    """
    This function is used to get the next channel and channel identifier from the lead.
    Args:
        lead: The lead dictionary.
        campaign_details: The campaign details dictionary.
        enterprise_id: The enterprise ID.
        workflow: The workflow dictionary.
        channel: The channel string.
        disposition: The disposition string.
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
    workflow = workflow or CAMPAIGN_WORKFLOW
    disposition = disposition or "queued"
    logger.info(f"Loaded models for get_channel_from_lead in {hp.time() - st} seconds")
    channels = campaign_details.get('channels') or ["voice_phone"]
    channels = sort_channel_by_cheapest(channels, current_channel=current_channel)
    logger.info(f"Checking for channels: {channels} for campaign_id={campaign_id}, enterprise_id={enterprise_id}")
    for channel in channels:
        channel_type = CHANNEL_IDENTIFIER_MAP.get(channel)
        logger.info(f"Processing channel: {channel} with type: {channel_type} for campaign_id={campaign_id}, enterprise_id={enterprise_id}")
        channel_identifier_list = get_channel_identifier_from_lead(channel, lead, channel_identifier=current_channel_identifier, logger=logger)
        if not channel_identifier_list:
            logger.error(f"No channel identifiers found for channel: {channel} for campaign_id={campaign_id}, enterprise_id={enterprise_id}, doing nothing.")
            continue
        change_channel = False
        for channel_identifier in channel_identifier_list:
            logger.info(f"Processing channel identifier: {channel_identifier} for channel: {channel} for campaign_id={campaign_id}, enterprise_id={enterprise_id}")
            statuses = get_statuses(channel, channel_type, channel_identifier, status_model=status_model, campaign_id=campaign_id, dealership_id=enterprise_id, logger=logger)
            if not statuses:
                logger.info(f"No statuses found for channel: {channel} with channel identifier: {channel_identifier} for campaign_id={campaign_id}, enterprise_id={enterprise_id}, starting now.")
                return channel, channel_identifier, 0, None
            last_status = hp.make_single(statuses)
            highest_status = get_highest_status(statuses)
            if highest_status != "contacted":
                attempts = get_attempts(statuses, highest_status)
                workflow_stage = (workflow or {}).get(highest_status) or CAMPAIGN_WORKFLOW.get(highest_status)
                # We haven't contacted yet, so we need to try and find the right credential and channel to connect to.
                next_delay = get_next_delay(highest_status, attempts, workflow_stage)
                next_retries = get_remaining_retries(workflow_stage, attempts)
                if next_retries > 0:
                    return channel, channel_identifier, next_delay, None
                trigger = workflow_stage.get('trigger', 'switch_to_next_credential')
            else:
                # We have connected, so we need to follow up with the contact.
                workflow_stage = (workflow or {}).get(disposition) or CAMPAIGN_WORKFLOW.get(disposition)
                attempts = get_attempts(statuses, "contacted") # We need to count the number of times we have contacted.
                if disposition in ["engaged", "converted"]:
                    attempts /= workflow_stage.get('retries', 0) # We need to calculate attempts per contact.
                next_delay = get_next_delay(highest_status, attempts, workflow_stage)
                next_retries = get_remaining_retries(workflow_stage, attempts)
                if next_retries > 0:
                    return channel, channel_identifier, next_delay, None
                trigger = workflow_stage.get('trigger', 'follow_up_contact')
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
            if change_channel:
                break
    logger.info(f"No next action found for channel: {channel} for campaign_id={campaign_id}, enterprise_id={enterprise_id}, doing nothing.")
    logger.info(f"Time taken to get channel from lead: {hp.time() - st} seconds")
    return None, None, 0, None

def get_email_identifier_from_lead(lead: dict, logger=None):
    logger = logger or mlogger
    st = hp.time()
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
    logger.info(f"Time taken to get email identifiers: {hp.time() - st} seconds")
    return rlist

def get_phone_number_identifier_from_lead(channel: str, lead: dict, logger=None):
    logger = logger or mlogger
    st = hp.time()
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
    logger.info(f"Time taken to get phone number identifiers: {hp.time() - st} seconds")
    return rlist


def remap_workflow(workflows: dict, campaign_id: str, dealership_id: str, campaign_objective_id: str, campaign_type: str, logger=None):
    logger = logger or mlogger
    st = hp.time()
    ret = {}
    def get_right_workflow(status):
        kws = {
            "dealership_id": dealership_id,
            "campaign_objective_id": campaign_objective_id,
            "campaign_type": campaign_type,
            "status": status
        }
        opts = ["dealership_id", "campaign_objective_id", "campaign_type", "status"]
        for k in range(len(opts)):
            rws = filter(lambda x: all(x.get(o) == kws.get(o) for o in opts), workflows)
            if rws:
                return hp.make_single(rws)
            opts.pop(0)
        return CAMPAIGN_WORKFLOW

    for status in PROVIDER_STATUS_MAP:
        workflow = get_right_workflow(status)
        ret[status] = {
             'trigger': workflow.get('trigger'),
             'retries': workflow.get('retries'),
             'delay': workflow.get('delay')
         }
    logger.info(f"Time taken to remap workflow: {hp.time() - st} seconds")
    return ret

def get_values_from_details(campaign_type, lead_id, lead_id_attr, lead_model, user_id_attr, user_model, campaign_model, dealership_model, campaign_objective_model, lead = None, logger = None):
    logger = logger or mlogger
    _values = {}
    for _id_attr, _model, _name in [
            (lead_id_attr, lead_model, 'lead'), 
            (user_id_attr, user_model, 'user'), 
            ('campaign_id', campaign_model, 'campaign'), 
            ('dealership_id', dealership_model, 'dealership'), 
            ('campaign_objective_id', campaign_objective_model, 'campaign_objective')
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
        _values[_name] = {
            "id": _id_value,
            "object": _detail
        }

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
    campaign_type = campaign_type.lower().replace('_', '-')
    if isinstance(channel, str):
        channel = channel.lower()
    campaign_model, lead_model, user_model, user_id_attr, lead_id_attr = get_model_and_attrs(campaign_type)
    dealership_model = gryd.base_model.Model('dealership', enterprise_id)
    campaign_objective_model = gryd.base_model.Model('campaign_objective', enterprise_id)
    _values = get_values_from_details(campaign_type, lead_id, lead, lead_id_attr, lead_model, user_id_attr, user_model, campaign_model, dealership_model, campaign_objective_model, logger)
    lead = _values.get('lead', {}).get('object')
    campaign_details = _values.get('campaign', {}).get('object')
    campaign_id = _values.get('campaign', {}).get('id') 
    dealership_id = _values.get('dealership', {}).get('id')
    workflow = _values.get('workflow', {}).get('object')
    if not channel:
        channel = AUTOCRM_CHEAPEST_CHANNELS[0]
    workflow_model = gryd.base_model.Model('campaign_workflow', enterprise_id)
    if not disposition:
        disposition = "queued"
    dispostion = dispostion.lower() 
    disposition = DISPOSITION_MAP.get(disposition)
    if not disposition:
        str_msg = f"Invalid disposition: {disposition} for campaign_type={campaign_type}, channel={channel}, enterprise_id={enterprise_id}"
        logger.error(str_msg)
        raise ValueError(str_msg)
    if disposition not in DISPOSITION_OPTIONS:
        str_msg = f"Invalid disposition: {disposition} for campaign_type={campaign_type}, channel={channel}, enterprise_id={enterprise_id}"
        logger.error(str_msg)
        raise ValueError(str_msg)
    workflow_stage = DISPOSITION_OPTIONS.get(disposition, ['queued'])
    workflows = workflow_model.list(
        _page_size=1, 
        _as_option=True, 
        campaign_type=campaign_type, 
        channel=channel, 
        campaign_objective_id=_values.get('campaign_objective', {}).get('id'),
        workflow_stage=workflow_stage
    )
    workflow = remap_workflow(workflows, campaign_id=campaign_details.get('campaign_id'), dealership_id=dealership_id, campaign_objective_id=campaign_details.get('campaign_objective_id'), campaign_type=campaign_type, logger=logger)
    channel, channel_identifier, delay, trigger = get_channel_from_lead(lead, campaign_details, workflow=workflow, channel=channel, disposition=disposition, logger=logger)
    gryd.create_async_task('process_single_lead', AUTOCRM_CAMPAIGN_SERVICE_NAME, args= [
        channel,
        lead,
        campaign_type,
        campaign_id,
    ], kwargs = {
        "user_id": _values.get('user', {}).get('id'),
        "disposition_tag": disposition,
        "disposition_detail_tag": lead.get('disposition_detail'),
        "channel_identifier": channel_identifier
    }, delay = delay)
    return





