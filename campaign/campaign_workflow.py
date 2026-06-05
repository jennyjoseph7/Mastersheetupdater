import sys
import re
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from config import AUTOCRM_APP_ENTERPRISE_ID, \
    AUTOCRM_CAMPAIGN_SERVICE_NAME, AUTOCRM_AGENT_SERVICE_NAME, \
    gryd, hp, AutocrmModel, AUTOCRM_ALLOWED_CHANNELS, AUTOCRM_CHEAPEST_CHANNELS, \
    get_phone_code_from_dealership
from autocrm_db_helper import get_pg_connector
from typing import List, Union, Dict, Any
from functools import reduce

gryd.SERVICE = AUTOCRM_CAMPAIGN_SERVICE_NAME
gryd.set_queue_manager()
mlogger = gryd.hp.get_logger(gryd.SERVICE)

DEBUG_STATUS = None
DEBUG_LEAD = None
DEBUG_USER = None
DEBUG_CAMPAIGN = None
DEBUG_DEALERSHIP = None
DEBUG_CAMPAIGN_OBJECTIVE = None

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
    "attempted": ["attempted", "reached", "contacted", "failed", "error", "engaged", "converted"],
    "reached": ["reached", "contacted", "engaged", "converted"],
    "contacted": ["contacted", "engaged", "converted"],
    "engaged": ["engaged","converted"],
    "converted": ["converted"],
}

REQUIRED_RETRIGGER = {
    "switch_to_next_credential": True,
    "switch_to_next_channel": True,
    "follow_up_contact": False,
    "confirmation_message": False
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
    "queued": {
        "retries": 10,
        "delay": 0,
        "trigger": None
    },
    "failed": {
        "retries": 4,
        "delay_type": "exponential",
        "delay": 600,
        "trigger": "switch_to_next_credential"
    },
    "error": {
        "retries": 0,
        "trigger": "switch_to_next_credential"
    },
    "attempted": {
        "retries": 4,
        "delay_type": "exponential",
        "delay": 600,
        "trigger": "switch_to_next_credential"
    },
    "reached": {
        "retries": 0,
        "delay": 1200,
        "trigger": "switch_to_next_channel"
    },
    "contacted": {
        "retries": 0,
        "delay": 3600,
        "trigger": "switch_to_next_channel"
    },
    "engaged": {
        "retries": 3,
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

def process_phone_number(phone_number, dealership_id = None):
    phone_code = '91'
    if dealership_id:
        phone_code = get_phone_code_from_dealership(dealership_id, with_plus = False)
    phone_number = re.sub(r'\D', '', phone_number)
    if len(phone_number) > 10:
        return phone_number
    return f"{phone_code}{phone_number}"


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

def get_cheapest_channel(channels: list, channel_sequence = None):
    channel_sequence = channel_sequence or AUTOCRM_CHEAPEST_CHANNELS
    for c in channel_sequence:
        if c in channels:
            return c
    return channels[0]

def sort_channel_by_cheapest(channels: list, current_channel: str = None, channel_sequence = None, last_contacted_channel = None):
    channel_sequence = channel_sequence or AUTOCRM_CHEAPEST_CHANNELS
    rlist = sorted(channels, key=lambda x: channel_sequence.index(x))
    if last_contacted_channel in rlist:
        rlist.insert(0, rlist.pop(rlist.index(last_contacted_channel)))
    if current_channel and current_channel in rlist:
        rlist = rlist[rlist.index(current_channel):]
    return rlist

def get_highest_status(statuses: list):
    if not statuses:
        mlogger.info("No statuses, hence making it queued")
        return "queued"
    mstatuses = set(list(map(lambda x: DISPOSITION_MAP.get(x.get('provider_status'), x.get('provider_status')), statuses)))
    mlogger.info("Got statuses after transforming: %s", mstatuses)
    for k in ["contacted", "reached", "failed", "attempted", "error", "queued"]:
        if k in mstatuses:
            return k
    return "queued"

def get_attempts(statuses: list, status: str):
    return sum(1 for _ in filter(lambda x: DISPOSITION_MAP.get(x.get('provider_status'), x.get('provider_status')) == status, statuses))

def get_next_delay(status: str, attempts: int, workflow_stage: dict, timezone: str = None):
    timezone = timezone or "Asia/Kolkata"
    next_delay_type = workflow_stage.get('delay_type', 'linear')
    next_delay = workflow_stage.get('delay', 1) or 1
    if next_delay_type == "exponential":
        next_delay = next_delay * (2 ** (attempts - 1))
    elif next_delay_type == "linear":
        next_delay = next_delay * attempts
    #TODO: Make sure the delay falls in the calling/messaging timeslot according to the timezone
    next_time = hp.now(timezone) + hp.timedelta(seconds=next_delay)
    if next_time.hour < 9:
        return next_delay + (9 - next_time.hour) * 3600
    if next_time.hour > 18:
        return next_delay + (24 + 9 - next_time.hour) * 3600
    return next_delay

def get_remaining_retries(workflow_stage: dict, attempts: int = 0):
    return max(0, (workflow_stage.get('retries', 0) or 0) - attempts)

def get_statuses(channel: str, channel_type: str, channel_identifier: str, status_model: AutocrmModel = None, lead_id: str = None, campaign_id: str = None, dealership_id: str = None, logger=None):
    logger = logger or mlogger
    st = hp.time()
    status_model = status_model or AutocrmModel('contact_status')
    channel_type = CHANNEL_IDENTIFIER_MAP.get(channel)
    if not channel_type:
        raise ValueError(f"Invalid channel: {channel}, doing nothing.")
    if channel_type in ["phone_number"]:
        channel_identifier = process_phone_number(channel_identifier, dealership_id)
    kws = {"channel": channel, channel_type: channel_identifier, "_sort_by": "updated", "_sort_reverse": True, "_as_option":True, "_page_size":100}
    if lead_id:
        kws["lead_id"] = lead_id
    if campaign_id:
        kws["campaign_id"] = campaign_id
    if dealership_id:
        kws["dealership_id"] = dealership_id
    statuses = list(filter(lambda x: x.get('channel') == channel, DEBUG_STATUS)) if DEBUG_STATUS else status_model.list(**kws)
    logger.info(f"Time taken to get statuses: {hp.time() - st} seconds")
    if not statuses:
        return None
    return statuses

def get_channel_identifier_from_lead(channel: str, lead: dict, channel_identifier: str = None, logger=None):
    logger = logger or mlogger
    st = hp.time()
    channel_identifier_list = []
    channel_type = CHANNEL_IDENTIFIER_MAP.get(channel)
    if channel_type == "phone_number":
        channel_identifier_list = get_phone_number_identifier_from_lead(channel_type, lead, logger=logger)
    elif channel_type == "email":
        channel_identifier_list = get_email_identifier_from_lead(lead, logger=logger)
    else:
        logger.error(f"Invalid channel: {channel}, doing nothing. channel_type: {channel_type}")
    if channel_identifier:
        channel_identifier_list = channel_identifier_list[channel_identifier_list.index(channel_identifier):]
    logger.info(f"Time taken to get channel identifier: {hp.time() - st} seconds")
    return channel_identifier_list

@gryd.is_a_task(function_name="get_channel_from_lead", job_param='job', auth_param='auth', logger_param='logger')
def get_channel_from_lead(lead: dict, campaign_details: dict, enterprise_id: Union[str, None] = None, workflow = None, current_channel = None, current_channel_identifier = None, disposition = None, lead_id = None, logger=None, job=None, auth=None, *args, **kwargs):
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
    auth = auth or {}
    st = hp.time()
    logger.info("Loading models for get_channel_from_lead")
    enterprise_id = enterprise_id or auth.get('enterprise_id') or AUTOCRM_APP_ENTERPRISE_ID
    campaign_id = campaign_details.get('campaign_id')
    dealership_id = campaign_details.get('dealership_id')
    status_model = AutocrmModel('contact_status')
    region_model = AutocrmModel('region')
    region_subdivision_model = AutocrmModel('region_subdivision')
    workflow = workflow or CAMPAIGN_WORKFLOW
    logger.debug(f"Workflow: {workflow}")
    disposition = disposition or "queued"
    logger.info(f"Loaded models for get_channel_from_lead in {hp.time() - st} seconds")
    channels = campaign_details.get('channels') or ["voice_phone"]
    timezone = "Asia/Kolkata"
    if "region_subdivision_id" in campaign_details:
        region_subdivision = region_subdivision_model.get(campaign_details.get('region_subdivision_id'))
        timezone = region_subdivision.get('timezone') or "Asia/Kolkata"
    else:
        region = region_model.get(campaign_details.get('region_id'))
        timezone = hp.make_single(region.get('timezones'), default = "Asia/Kolkata", force = True)
    current_channel = current_channel or lead.get('last_contacted_channel')
    logger.info(f"Current channel: {current_channel}")
    channels = sort_channel_by_cheapest(channels, current_channel=current_channel, channel_sequence = campaign_details.get('channel_sequence'), last_contacted_channel = lead.get('last_contacted_channel'))
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
            statuses = get_statuses(channel, channel_type, channel_identifier, status_model=status_model, lead_id=lead_id, campaign_id=campaign_id, dealership_id=dealership_id, logger=logger)
            if not statuses:
                logger.info(f"No statuses found for channel: {channel} with channel identifier: {channel_identifier} for campaign_id={campaign_id}, enterprise_id={enterprise_id}, starting now.")
                return channel, channel_identifier, 0, None
            last_status = hp.make_single(statuses, force = True)
            highest_status = get_highest_status(statuses)
            logger.info(f"Highest status: {highest_status}")
            if highest_status == "queued":
                return channel, channel_identifier, 0, None
            if highest_status != "contacted":
                attempts = get_attempts(statuses, highest_status)
                logger.info("Got attempts for uncontacted: %s", attempts)
                workflow_stage = (workflow or {}).get(highest_status) or CAMPAIGN_WORKFLOW.get(highest_status)
                logger.info("Workflow stage taken: %s", workflow_stage)
                # We haven't contacted yet, so we need to try and find the right credential and channel to connect to.
                next_delay = get_next_delay(highest_status, attempts, workflow_stage, timezone=timezone)
                next_retries = get_remaining_retries(workflow_stage, attempts)
                logger.info("Next retries: %s, attempts: %s", next_retries, attempts)
                if next_retries > 0:
                    return channel, channel_identifier, next_delay, None
                trigger = workflow_stage.get('trigger', 'switch_to_next_credential')
            else:
                # We have connected, so we need to follow up with the contact.
                workflow_stage = (workflow or {}).get(disposition) or CAMPAIGN_WORKFLOW.get(disposition)
                logger.info(f"Workflow stage for disposition: {disposition} is {workflow_stage}")
                attempts = get_attempts(statuses, "contacted") # We need to count the number of times we have contacted.
                logger.info(f"Attempts: {attempts}")
                if disposition in ["engaged", "converted"]:
                    attempts /= max(workflow_stage.get('retries', 0), 1) # We need to calculate attempts per contact.
                    logger.info(f"Attempts per contact: {attempts}")
                next_delay = get_next_delay(highest_status, attempts, workflow_stage)
                logger.info(f"Next delay: {next_delay}")
                #TODO: If user has requested call-back, then we should get next delay from the lead follow_up_date attribue if available
                next_retries = get_remaining_retries(workflow_stage, attempts)
                logger.info(f"Next retries: {next_retries}")
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
        d = lead.get(ph)
        if d:
            d = process_phone_number(d, lead.get('dealership_id'))
            if d in rlist:
                continue
            logger.info(f"Adding {ph}: {d} to rlist")
            rlist.append(d)
    for person in lead.get('persons_involved', []):
        for ph in ph_list:
            if person.get(ph):
                d = process_phone_number(person.get(ph), lead.get('dealership_id'))
                if d in rlist:
                    continue
                logger.info(f"Adding {ph}: {d} to rlist for person {person.get('user_id')}")
                rlist.append(d)
        if person.get(channel_last_contacted_name) == ph:
            logger.info(f"Adding {ph} as last contacted channel from person")
            priority.append((person.get(f'updated'), person.get(channel_last_contacted_name)))
    priority.sort(key=lambda x: x[0])
    for p0, p1 in priority:
        if p1 in rlist:
            rlist.remove(p1)
        rlist.insert(0, p1)
    logger.info(f"List of phone numbers for lead {lead.get('pre_sales_lead_id') or lead.get('post_sales_lead_id')} is \"{', '.join(rlist)}\"")
    logger.info(f"Time taken to get phone number identifiers: {hp.time() - st} seconds")
    return rlist


def remap_workflow(workflows: dict, campaign_id: str, dealership_id: str, campaign_objective_id: str, campaign_type: str, logger=None):
    logger = logger or mlogger
    st = hp.time()
    ret = {}
    if not workflows:
        return CAMPAIGN_WORKFLOW
    def get_right_workflow(status):
        kws = {
            "dealership_id": dealership_id,
            "campaign_objective_id": campaign_objective_id,
            "campaign_type": campaign_type,
            "status": status
        }
        opts = ["dealership_id", "campaign_objective_id", "campaign_type", "status"]
        for k in range(len(opts)):
            rws = list(filter(lambda x: all(x.get(o) == kws.get(o) for o in opts), workflows))
            if rws:
                return hp.make_single(rws, force = True)
            opts.pop(0)
        return CAMPAIGN_WORKFLOW.get(status)

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
    for _id_attr, _model, _name, _debug, _required in [
            (lead_id_attr, lead_model, 'lead', DEBUG_LEAD, True), 
            (user_id_attr, user_model, 'user', DEBUG_USER, False), 
            ('campaign_id', campaign_model, 'campaign', DEBUG_CAMPAIGN, True), 
            ('dealership_id', dealership_model, 'dealership', DEBUG_DEALERSHIP, True), 
            ('campaign_objective_id', campaign_objective_model, 'campaign_objective', DEBUG_CAMPAIGN_OBJECTIVE, True)
        ]:
        _id_value = None
        _detail = {}
        if not lead:
            _detail = lead = DEBUG_LEAD or lead_model.get(lead_id)
            _id_value = lead_id
        else:
            _id_value = lead.get(_id_attr)
            _detail = _debug or _model.get(_id_value)
        if not _detail and _required:
            str_msg = f"No {_model.name} found for {_id_attr}={_id_value}, campaign_type={campaign_type}, enterprise_id={AUTOCRM_APP_ENTERPRISE_ID}"
            logger.error(str_msg)
            raise ValueError(str_msg)
        _values[_name] = {
            "id": _id_value,
            "object": _detail
        }
    return _values

@gryd.is_a_task(function_name="determine_campaign_next_action", job_param='job', auth_param='auth', logger_param='logger')
def determine_campaign_next_action(
        campaign_type: str,
        lead_id: str,
        channel: str = None,
        channel_identifier: str = None,
        disposition: str = None,
        disposition_detail: str = None,
        enterprise_id: Union[str, None] = None,
        call_process_single_lead: bool = False,
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
    auth = auth or {}
    enterprise_id = enterprise_id or auth.get('enterprise_id') or AUTOCRM_APP_ENTERPRISE_ID
    logger = logger or mlogger
    st = hp.time()
    campaign_type = campaign_type.lower().replace('_', '-')
    if isinstance(channel, str):
        channel = channel.lower()
    campaign_model, lead_model, user_model, user_id_attr, lead_id_attr = get_model_and_attrs(campaign_type)
    dealership_model = gryd.base_model.Model('dealership', enterprise_id)
    campaign_objective_model = gryd.base_model.Model('campaign_objective', enterprise_id)
    _values = get_values_from_details(campaign_type, lead_id, lead_id_attr, lead_model, user_id_attr, user_model, campaign_model, dealership_model, campaign_objective_model, logger = logger)
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
    disposition = disposition.lower() 
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
    logger.debug(f"Workflows before remapping: {workflows}")
    workflow = remap_workflow(workflows, campaign_id=campaign_details.get('campaign_id'), dealership_id=dealership_id, campaign_objective_id=campaign_details.get('campaign_objective_id'), campaign_type=campaign_type, logger=logger)
    logger.info(f"Workflow after remapping: {workflow}")
    channel, channel_identifier, delay, trigger = get_channel_from_lead(lead, campaign_details, workflow=workflow, channel=channel, disposition=disposition, lead_id=lead_id, logger=logger)
    logger.debug(f"Channel: {channel}, Channel identifier: {channel_identifier}, Delay: {delay}, Trigger: {trigger}")
    logger.info(f"Time taken to get channel from lead: {hp.time() - st} seconds")
    if kwargs.get('debug', False):
        return {
            "next_channel": channel,
            "next_channel_identifier": channel_identifier,
            "next_schedule_time": str(hp.now() + hp.timedelta(seconds=delay)),
            "trigger": trigger
        }
    if channel and channel_identifier:
        next_schedule_time = hp.epoch() + delay
    else:
        next_schedule_time = None
    if call_process_single_lead and channel and channel_identifier:
        # If we are calling the process_single_lead task, then we need to update the lead model to remove the next channel and channel identifier.
        # This is because we are calling the process_single_lead task to process the lead and we don't want to process the lead again.
        # We will update the lead model to remove the next channel and channel identifier and set the next schedule time and trigger to None.
        # We will return the async task response.
        logger.info(f"Calling process_single_lead task for channel: {channel}, channel_identifier: {channel_identifier}, delay: {delay}")
        r = gryd.create_async_task('process_single_lead', AUTOCRM_CAMPAIGN_SERVICE_NAME, args= [
            channel,
            lead,
            campaign_type,
            campaign_id,
        ], kwargs = {
            "user_id": _values.get('user', {}).get('id'),
            "disposition_tag": disposition,
            "disposition_detail_tag": lead.get('disposition_detail'),
            "channel_identifier": channel_identifier
        })
        lead_model.update(lead_id, {
            "next_channel": None,
            "next_channel_identifier": None,
            "next_schedule_time": None,
            "next_trigger": None
        })
        return r
    # We will update the lead model to set the next channel etc., so that cron job can pick it up and process the lead.
    logger.info(f"Updating lead model for channel: {channel}, channel_identifier: {channel_identifier}, delay: {delay}, trigger: {trigger}")
    return lead_model.update(lead_id, {
        "next_channel": channel,
        "next_channel_identifier": channel_identifier,
        "next_schedule_time": next_schedule_time,
        "next_trigger": trigger
    })

def get_previous_contacted_channel(statuses):
    if not statuses:
        return None
    for s in statuses:
        status = s.get('provider_status')
        if DISPOSITION_MAP[status] in ["contacted", "engaged", "converted"]:
            return s.get('channel')
    return None

def get_last_contacted_phone_number(statuses):
    if not statuses:
        return None
    for s in statuses:
        channel = s.get('channel')
        if channel not in ['voice_phone', 'rcs', 'sms', 'voicebot', 'voice']:
            continue
        status = s.get('provider_status')
        if DISPOSITION_MAP[status] in  ["contacted", "engaged", "converted"]:
            return s.get('phone_number')
    return None
    
def get_last_contacted_whatsapp_number(statuses):
    if not statuses:
        return None
    for s in statuses:
        channel = s.get('channel')
        if channel not in ['whatsapp', 'whatsapp_chat', 'whatsapp_voice_note', 'whatsapp_voice_call']:
            continue
        status = s.get('provider_status')
        if DISPOSITION_MAP[status] in  ["contacted", "engaged", "converted"]:
            return s.get('phone_number')
    return None

def get_last_contacted_email(statuses):
    if not statuses:
        return None
    for s in statuses:
        channel = s.get('channel')
        if channel not in ['email']:
            continue
        status = s.get('provider_status')
        if DISPOSITION_MAP[status] in  ["contacted", "engaged", "converted"]:
            return s.get('email')
    return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--lead-id", type=str, default="123")
    parser.add_argument("--no-debug", action="store_false", default=True)
    parser.add_argument("--channel-identifier", type=str, default=None)
    parser.add_argument("--campaign-type", type=str, default="pre-sales")
    parser.add_argument("--disposition", type=str, default="converted")
    args = parser.parse_args()
    lead_id = args.lead_id
    debug = args.no_debug
    channel_identifier = args.channel_identifier
    if lead_id == "123":
        channel_identifier = "919108310847"
        DEBUG_STATUS = [
            {
                "provider_status": "attempted",
                "channel": "whatsapp_chat",
            },
            {
                "provider_status": "contacted",
                "channel": "voice_phone",
            },
            {
                "provider_status": "attempted",
                "channel": "voice_phone",
            }
        ]
        DEBUG_LEAD = {
            "created": 1773214855.7515764,
            "pincode": "560098",
            "updated": 1773214855.75223,
            "region_id": "india",
            "campaign_id": "123",
            "dealer_name": "Stellantis",
            "disposition": "engaged",
            "person_name": "Shifa",
            "region_name": "India",
            "showroom_id": "stellantis-india",
            "lead_summary": "The user is repeatedly trying to **book a test drive** for the **Citroen Basalt**. The agent is attempting to confirm the user's **pincode (560098)** multiple times in response to the user's requests to book the test drive or explore the Basalt. The user's responses (\"Yes\") have not yet resolved the pincode confirmation loop.",
            "phone_number": "+919876543210",
            "audience_name": "Test lead",
            "campaign_name": "Tech Drive Booking Blitz",
            "campaign_type": "pre-sales",
            "dealership_id": "123",
            "campaign_offer": "",
            "last_session_id": "1bfb23db-4d93-3946-bee1-cb4ffe984ac7",
            "supported_brands": [
                "jeep",
                "citroen"
            ],
            "vehicle_category": "Passenger vehicles",
            "campaign_sub_type": "other",
            "conversation_tone": "- Respond like a friendly local showroom representative, not a product expert or scripted chatbot. \n - Keep messages short, simple, and easy to read. \n - Warm, calm, confident, and respectful in tone.  \n -Never rush or pressure the customer.  \n - When the customer responds, acknowledge what they said using phrases like: “Got it.” “That makes sense.” “Fair point.” “Absolutely.” - When a customer responds with brief cues such as “Okay,” “Got it,” “Sure,” “Yes,” “Right,” “Hmm,” or similar acknowledgements, do not let the conversation stall. Gently guide the user toward confirming a test drive.  \n - If you cannot clearly understand the customer’s message, politely ask for clarification in a friendly and respectful manner. \n  - If the customer says again “hello,” “hi,” or indicates confusion, quickly acknowledge your presence (e.g., “Hi, I’m here ”), and continue toward the purpose of confirming a test drive without repeating the full introduction.  \n - Do not repeat long welcome messages. Keep responses light and purposeful.  \n - When informing the user about vehicle features gently nudge the conversation toward confirming the test drive or learning more. \n - When describing a feature, keep it short, simple, and benefit-focused.  \n -- Always steer the conversation toward fulfilling the purpose of confirming a test drive.  \n - End every conversation politely, with warmth and gratitude: Thanks for your time. Really appreciate it.- Closure Rule (Very Important) Every conversation must end with one soft next step: Test drive booking, Follow-up time.",
            "pre_sales_lead_id": "123",
            "disposition_detail": "Enquired for Test Drive",
            "engine_capacity_cc": "Bangalore",
            "vehicle_model_name": "Basalt",
            "last_session_status": "completed",
            "campaign_description": "",
            "last_session_channel": "whatsapp_chat",
            "prioritization_score": 70,
            "campaign_objective_id": "123",
            "supported_brand_names": [
                "Jeep",
                "Citroen"
            ],
            "campaign_objective_name": "Confirm Test Drives Through Tech Appeal - WhatsApp",
            "prioritization_category": "WARM",
            "region_level_guardrails": "- Maintain professional communication standards. Ensure clear communication. Respect regional languages. Provide local language support. Be mindful of potential network issues or poor call quality \n -Trigger calls between 10am to 7pm",
            "region_level_guidelines": "Avoid slang, sarcasm, or culturally sensitive humor. Use polite, respectful, and neutral tone. Prefer simple sentences suitable for Tier-2/Tier-3 customers",
            "previous_contact_channel": "whatsapp_chat",
            "why_user_should_avail_this": "Core Differentiator, Context-aware AI assistant integrated with full vehicle systems, Understands natural, conversational commands (not keyword-based), Makes real-time decisions using live vehicle data, Connected Ecosystem, Remote AC pre-conditioning, Remote lock/unlock, Live vehicle diagnostics, Full sync with MyCitroen app, Infotainment & Interface, 10.25” lag-free touchscreen, Wireless Apple CarPlay & Android Auto, Wireless charging, 7” digital driver display",
            "other_important_information": "Tech Features: The Citroen Basalt features Cara, the intelligent voice assistant, giving you hands-free control and seamless interaction on the go. It also comes with a 10.25-inch floating touchscreen with wireless Apple CarPlay and Android Auto, a 7-inch digital cluster, Bluetooth connectivity, steering-mounted controls, and a wireless charger — making every drive smart, connected, and effortless \n - Apart from the technology, the Basalt also stands out for its bold design on the road, the comfort you actually feel every day, and the fact that you get premium features without paying extra just for a badge. \n - Beyond the tech, people also like the Basalt for its strong road presence, the everyday comfort it offers, and the premium feel — without the usual premium-brand pricing. \n - It’s also known for its bold road presence, great everyday comfort, and premium features — without charging you just for the brand name.",
            "seating_capacity_preference": "5 SEATER",
            "supported_brands_guidelines": {},
            "previous_interaction_details": {},
            "interested_vehicle_brand_name": "Citroen",
            "reasons_for_non_applicability": "- If the customer has already purchased a vehicle from another brand, you should say, 'Oh okay, congratulations on your new car! Just out of curiosity, what made you go with that brand? Your feedback helps us improve. And if you ever consider another vehicle in the future, feel free to reach out.' \n - If the customer has already purchased from your brand, you should say, 'That's great to hear! Congratulations on your purchase. Hope you're enjoying the ride. If you ever need any support or have questions about service, feel free to connect with us anytime.' \n - If the customer says they are no longer interested in buying a car, you should say, 'No problem at all. Can I ask what changed? Just trying to understand so we can serve you better if your plans change in the future. And if you know anyone looking for a vehicle, we'd love to help them out.' \n - If the customer's contact number is wrong or belongs to someone else, you should say, 'Oh, I see. Sorry for the confusion. Could you help me with the correct contact number for [customer name], or let me know if they're no longer interested so we can update our records?' \n - If the customer has relocated to a different city or country, you should say, 'Understood. If your new location has our dealership, I can connect you with the team there. Otherwise, I'll update our records. Safe travels, and feel free to reach out if you're ever back in the area.'",
            "campaign_guardrails_guidelines": "- When a customer asks for a feature comparison, respond with only factual and verified information, avoid speculation or exaggeration, and ensure the conversation remains neutral and respectful without criticising or attacking competitors. \n - You should not talk about competitor brands and cars. \n - Do not  say anything negative about the Citroen Basalt. \n - You should keep all responses positive and brand-focused. \n - avoid using over-technical jargon, dumping specifications, making exaggerated or uncertified claims (such as “most advanced in segment”), criticising competitors, overwhelming the user with long feature lists, or responding in a tone that sounds like marketing or brochure copy. \n - Do not mention discounts, pricing, urgency cues (such as “limited slots” or “ending soon”), or use scarcity tactics. \n - limit technical details to a 2-3 key features at a time, and avoid emotional hype. \n - All messaging should focus on the experience, emphasize hands-on interaction with the in-car system, and consistently maintain a technology-led theme throughout the invitation. \n - If Customer Shows Low Tech Interest, Do NOT continue pushing technology. Listen to their priorities and adjust conversation accordingly \n - Please read the pincode clearly, one digit at a time",
            "campaign_objective_description": "To engage digitally influenced buyers who prioritize infotainment, connectivity, and in-car technology, and drive Test Drive bookings through structured WhatsApp engagement.",
            "reasons_users_may_not_be_interested": "If customer seems low on tech interest - Don't ask to learn but speak to test a hypothesis and guage if they maybe interested in safety or family or another key feature. And then lead into it. Keep pitch warm and short. \n - If customer is busy “No problem at all. When would be a better time to call you back?” (Optional)  “I just want to make sure you don’t miss available test drive slots.” \n - If customer is just browsing “That’s completely fine. A test drive usually helps people decide faster.” “There’s no commitment at all.” “Would this weekend work, or sometime next week?” \n - If price feels high “I understand. Budget matters.” “There are financing and exchange options that often surprise people.” “Would you like me to quickly check what might work better for you?” \n - If comparing with other brands “That’s smart.” “Many customers compare before deciding.” “Instead of explaining, I’d suggest a short test drive — it gives real clarity.” “Would you like me to arrange that?”  \n - If they want to wait “I get that.” “Just so you know, current offers and availability may change later.” “I can keep you updated.” “What’s more important for you — timing or features?” \n - If they got a better deal elsewhere “Thanks for sharing that.” “Let me see what we can do on our side.” “What exactly did they offer?” \n - if they had a bad past experience “I’m really sorry to hear that.” “A lot has changed, especially service-wise.” “I’d love to give you a fresh experience — even just a drive.” \n - If family decision is involved “Of course, that makes sense.” “Would it help if everyone experienced the car together?” “I can arrange a family test drive.” \n - If worried about maintenance “That’s a valid concern.” “We have clear service packages — no surprises.” “I can explain that briefly or share it on WhatsApp.” \n - If unsure about variant “No worries — that’s very common.” “Let me ask you one or two quick questions and I’ll suggest what fits best.” \n - If they want time to think “Absolutely.” “I’ll send you the brochure and a short video.” “Would you like me to follow up, or should I wait for you to reach out?” "
        }
        DEBUG_LEAD["disposition"] = get_highest_status(DEBUG_STATUS) or DISPOSITION_MAP[DEBUG_STATUS[0]["status"]]
        DEBUG_LEAD["last_session_channel"] = get_previous_contacted_channel(DEBUG_STATUS)
        DEBUG_LEAD["last_interaction_time"] = hp.now()
        DEBUG_USER = {
            "user_id": "123",
            "email": "test@example.com",
            "phone_number": "+919876543210",
            "last_contacted_phone_number": "+919876543210",
            "last_contacted_whatsapp_number": "+919876543210",
            "timezone": "Asia/Kolkata",
        }
        DEBUG_USER["previous_contact_channel"] = get_previous_contacted_channel(DEBUG_STATUS)
        DEBUG_USER["last_contacted_phone_number"] = get_last_contacted_phone_number(DEBUG_STATUS)
        DEBUG_USER["last_contacted_whatsapp_number"] = get_last_contacted_whatsapp_number(DEBUG_STATUS)
        DEBUG_CAMPAIGN = {
            "ctas": [
                "book-test-drive"
            ],
            "purpose": "Confirm Test drive",
            "channels": [
                "whatsapp_chat",
                "voice_phone",
                "email",
                "rcs"
            ],
            "end_date": 1773792000,
            "languages": [
                "english"
            ],
            "region_id": "india",
            "start_date": 1773187200,
            "campaign_id": "123",
            "region_name": "India",
            "urgency_hook": "",
            "campaign_name": "Tech Drive Booking Blitz",
            "campaign_type": "pre-sales",
            "cost_per_lead": 0,
            "dealership_id": "123",
            "purpose_steps": [
                "- Ask if customer is interedted in booking test drive, if customer says yes, get the pincode of the customer from 'Who is the customer section' and cofirm if it is correct. If the pincode is not available, ask user to provide the pincode",
                "\n - Once they confirm the pincode, you should only respond with- 'Thank you. We'll arrange a test drive at your nearest dealership. You'll hear from our team shortly to coordinate the details. Is there anything else I can help you with?'"
            ],
            "campaign_offer": "",
            "campaign_status": "Active",
            "dealership_name": "Stellantis",
            "number_targeted": 1,
            "budget_allocated": 2.5655,
            "supported_brands": [
                "jeep",
                "citroen"
            ],
            "vehicle_category": "Passenger vehicles",
            "campaign_sub_type": "other",
            "conversation_tone": "- Respond like a friendly local showroom representative, not a product expert or scripted chatbot. \n - Keep messages short, simple, and easy to read. \n - Warm, calm, confident, and respectful in tone.  \n -Never rush or pressure the customer.  \n - When the customer responds, acknowledge what they said using phrases like: “Got it.” “That makes sense.” “Fair point.” “Absolutely.” - When a customer responds with brief cues such as “Okay,” “Got it,” “Sure,” “Yes,” “Right,” “Hmm,” or similar acknowledgements, do not let the conversation stall. Gently guide the user toward confirming a test drive.  \n - If you cannot clearly understand the customer’s message, politely ask for clarification in a friendly and respectful manner. \n  - If the customer says again “hello,” “hi,” or indicates confusion, quickly acknowledge your presence (e.g., “Hi, I’m here ”), and continue toward the purpose of confirming a test drive without repeating the full introduction.  \n - Do not repeat long welcome messages. Keep responses light and purposeful.  \n - When informing the user about vehicle features gently nudge the conversation toward confirming the test drive or learning more. \n - When describing a feature, keep it short, simple, and benefit-focused.  \n -- Always steer the conversation toward fulfilling the purpose of confirming a test drive.  \n - End every conversation politely, with warmth and gratitude: Thanks for your time. Really appreciate it.- Closure Rule (Very Important) Every conversation must end with one soft next step: Test drive booking, Follow-up time.",
            "campaign_description": "",
            "campaign_user_source": "file",
            "campaign_objective_id": "123",
            "campaign_objective_name": "Confirm Test Drives Through Tech Appeal - WhatsApp",
            "conversion_rate_percent": 0,
            "region_level_guardrails": "- Maintain professional communication standards. Ensure clear communication. Respect regional languages. Provide local language support. Be mindful of potential network issues or poor call quality \n -Trigger calls between 10am to 7pm",
            "region_level_guidelines": "Avoid slang, sarcasm, or culturally sensitive humor. Use polite, respectful, and neutral tone. Prefer simple sentences suitable for Tier-2/Tier-3 customers",
            "why_user_should_avail_this": "Core Differentiator, Context-aware AI assistant integrated with full vehicle systems, Understands natural, conversational commands (not keyword-based), Makes real-time decisions using live vehicle data, Connected Ecosystem, Remote AC pre-conditioning, Remote lock/unlock, Live vehicle diagnostics, Full sync with MyCitroen app, Infotainment & Interface, 10.25” lag-free touchscreen, Wireless Apple CarPlay & Android Auto, Wireless charging, 7” digital driver display",
            "other_important_information": "Tech Features: The Citroen Basalt features Cara, the intelligent voice assistant, giving you hands-free control and seamless interaction on the go. It also comes with a 10.25-inch floating touchscreen with wireless Apple CarPlay and Android Auto, a 7-inch digital cluster, Bluetooth connectivity, steering-mounted controls, and a wireless charger — making every drive smart, connected, and effortless \n - Apart from the technology, the Basalt also stands out for its bold design on the road, the comfort you actually feel every day, and the fact that you get premium features without paying extra just for a badge. \n - Beyond the tech, people also like the Basalt for its strong road presence, the everyday comfort it offers, and the premium feel — without the usual premium-brand pricing. \n - It’s also known for its bold road presence, great everyday comfort, and premium features — without charging you just for the brand name.",
            "supported_brands_guidelines": {},
            "reasons_for_non_applicability": "- If the customer has already purchased a vehicle from another brand, you should say, 'Oh okay, congratulations on your new car! Just out of curiosity, what made you go with that brand? Your feedback helps us improve. And if you ever consider another vehicle in the future, feel free to reach out.' \n - If the customer has already purchased from your brand, you should say, 'That's great to hear! Congratulations on your purchase. Hope you're enjoying the ride. If you ever need any support or have questions about service, feel free to connect with us anytime.' \n - If the customer says they are no longer interested in buying a car, you should say, 'No problem at all. Can I ask what changed? Just trying to understand so we can serve you better if your plans change in the future. And if you know anyone looking for a vehicle, we'd love to help them out.' \n - If the customer's contact number is wrong or belongs to someone else, you should say, 'Oh, I see. Sorry for the confusion. Could you help me with the correct contact number for [customer name], or let me know if they're no longer interested so we can update our records?' \n - If the customer has relocated to a different city or country, you should say, 'Understood. If your new location has our dealership, I can connect you with the team there. Otherwise, I'll update our records. Safe travels, and feel free to reach out if you're ever back in the area.'",
            "campaign_guardrails_guidelines": "- When a customer asks for a feature comparison, respond with only factual and verified information, avoid speculation or exaggeration, and ensure the conversation remains neutral and respectful without criticising or attacking competitors. \n - You should not talk about competitor brands and cars. \n - Do not  say anything negative about the Citroen Basalt. \n - You should keep all responses positive and brand-focused. \n - avoid using over-technical jargon, dumping specifications, making exaggerated or uncertified claims (such as “most advanced in segment”), criticising competitors, overwhelming the user with long feature lists, or responding in a tone that sounds like marketing or brochure copy. \n - Do not mention discounts, pricing, urgency cues (such as “limited slots” or “ending soon”), or use scarcity tactics. \n - limit technical details to a 2-3 key features at a time, and avoid emotional hype. \n - All messaging should focus on the experience, emphasize hands-on interaction with the in-car system, and consistently maintain a technology-led theme throughout the invitation. \n - If Customer Shows Low Tech Interest, Do NOT continue pushing technology. Listen to their priorities and adjust conversation accordingly \n - Please read the pincode clearly, one digit at a time",
            "campaign_objective_description": "To engage digitally influenced buyers who prioritize infotainment, connectivity, and in-car technology, and drive Test Drive bookings through structured WhatsApp engagement.",
            "custom_conversation_start_pattern": [
                "Thank you for considering the Citroen Basalt. What many tech-focused buyers are appreciating about the Basalt is how clean and intuitive the infotainment system is and a very driver-focused interface without overcomplicating things. I'd love to understand what matters most to you in your next car"
            ],
            "reasons_users_may_not_be_interested": "If customer seems low on tech interest - Don't ask to learn but speak to test a hypothesis and guage if they maybe interested in safety or family or another key feature. And then lead into it. Keep pitch warm and short. \n - If customer is busy “No problem at all. When would be a better time to call you back?” (Optional)  “I just want to make sure you don’t miss available test drive slots.” \n - If customer is just browsing “That’s completely fine. A test drive usually helps people decide faster.” “There’s no commitment at all.” “Would this weekend work, or sometime next week?” \n - If price feels high “I understand. Budget matters.” “There are financing and exchange options that often surprise people.” “Would you like me to quickly check what might work better for you?” \n - If comparing with other brands “That’s smart.” “Many customers compare before deciding.” “Instead of explaining, I’d suggest a short test drive — it gives real clarity.” “Would you like me to arrange that?”  \n - If they want to wait “I get that.” “Just so you know, current offers and availability may change later.” “I can keep you updated.” “What’s more important for you — timing or features?” \n - If they got a better deal elsewhere “Thanks for sharing that.” “Let me see what we can do on our side.” “What exactly did they offer?” \n - if they had a bad past experience “I’m really sorry to hear that.” “A lot has changed, especially service-wise.” “I’d love to give you a fresh experience — even just a drive.” \n - If family decision is involved “Of course, that makes sense.” “Would it help if everyone experienced the car together?” “I can arrange a family test drive.” \n - If worried about maintenance “That’s a valid concern.” “We have clear service packages — no surprises.” “I can explain that briefly or share it on WhatsApp.” \n - If unsure about variant “No worries — that’s very common.” “Let me ask you one or two quick questions and I’ll suggest what fits best.” \n - If they want time to think “Absolutely.” “I’ll send you the brochure and a short video.” “Would you like me to follow up, or should I wait for you to reach out?” "
        }
        DEBUG_DEALERSHIP = {
            "created": 1769694286.078878,
            "updated": 1773310349.6682038,
            "website": "https://www.stellantis.com/en",
            "channels": [
                "voice_phone",
                "whatsapp_chat",
                "email",
                "rcs"
            ],
            "logo_url": "https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/401fa9aa-b611-4e75-868c-d0035cad05dc-69b2900b_stellantis-logo-Default.png",
            "languages": [
                "english"
            ],
            "region_id": "india",
            "dealer_name": "Stellantis",
            "region_name": "India",
            "dealer_status": "active",
            "dealership_id": "123",
            "credits_balance": 37967.95300000011,
            "dealership_type": "Multi Brand",
            "supported_brands": [
                "jeep",
                "citroen"
            ],
            "vehicle_category": "Passenger vehicles",
            "power_law_discount": True,
            "dark_theme_logo_url": "https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/9c2a787e-ab4b-4044-a1c2-e04f70d9adbb-69b29060_stellantis-logo-White.png",
            "discount_percentage": 0,
            "light_theme_logo_url": "https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/image/b4451d58-5397-4189-a3de-1cf1ab2a8af6-69b29098_stellantis-logo-Black.png",
            "dealership_legal_name": "Stellantis",
            "showroom_center_count": 75,
            "supported_brand_names": [
                "Jeep",
                "Citroen"
            ],
            "region_level_guardrails": "- Maintain professional communication standards. Ensure clear communication. Respect regional languages. Provide local language support. Be mindful of potential network issues or poor call quality ",
            "region_level_guidelines": "Avoid slang, sarcasm, or culturally sensitive humor. Use polite, respectful, and neutral tone. Prefer simple sentences suitable for Tier-2/Tier-3 customers",
            "region_discount_percentage": 0,
            "supported_brands_guidelines": {},
            "deduct_payment_gateway_charges": False
        } 
        DEBUG_CAMPAIGN_OBJECTIVE = { 
            "campaign_objective_id": "123",
            "campaign_objective_name": "Confirm Test Drives Through Tech Appeal - WhatsApp",
            "conversion_rate_percent": 0,
            "region_level_guardrails": "- Maintain professional communication standards. Ensure clear communication. Respect regional languages. Provide local language support. Be mindful of potential network issues or poor call quality \n -Trigger calls between 10am to 7pm",
            "region_level_guidelines": "Avoid slang, sarcasm, or culturally sensitive humor. Use polite, respectful, and neutral tone. Prefer simple sentences suitable for Tier-2/Tier-3 customers",
            "why_user_should_avail_this": "Core Differentiator, Context-aware AI assistant integrated with full vehicle systems, Understands natural, conversational commands (not keyword-based), Makes real-time decisions using live vehicle data, Connected Ecosystem, Remote AC pre-conditioning, Remote lock/unlock, Live vehicle diagnostics, Full sync with MyCitroen app, Infotainment & Interface, 10.25” lag-free touchscreen, Wireless Apple CarPlay & Android Auto, Wireless charging, 7” digital driver display",
            "other_important_information": "Tech Features: The Citroen Basalt features Cara, the intelligent voice assistant, giving you hands-free control and seamless interaction on the go. It also comes with a 10.25-inch floating touchscreen with wireless Apple CarPlay and Android Auto, a 7-inch digital cluster, Bluetooth connectivity, steering-mounted controls, and a wireless charger — making every drive smart, connected, and effortless \n - Apart from the technology, the Basalt also stands out for its bold design on the road, the comfort you actually feel every day, and the fact that you get premium features without paying extra just for a badge. \n - Beyond the tech, people also like the Basalt for its strong road presence, the everyday comfort it offers, and the premium feel — without the usual premium-brand pricing. \n - It’s also known for its bold road presence, great everyday comfort, and premium features — without charging you just for the brand name.",
            "supported_brands_guidelines": {},
            "reasons_for_non_applicability": "- If the customer has already purchased a vehicle from another brand, you should say, 'Oh okay, congratulations on your new car! Just out of curiosity, what made you go with that brand? Your feedback helps us improve. And if you ever consider another vehicle in the future, feel free to reach out.' \n - If the customer has already purchased from your brand, you should say, 'That's great to hear! Congratulations on your purchase. Hope you're enjoying the ride. If you ever need any support or have questions about service, feel free to connect with us anytime.' \n - If the customer says they are no longer interested in buying a car, you should say, 'No problem at all. Can I ask what changed? Just trying to understand so we can serve you better if your plans change in the future. And if you know anyone looking for a vehicle, we'd love to help them out.' \n - If the customer's contact number is wrong or belongs to someone else, you should say, 'Oh, I see. Sorry for the confusion. Could you help me with the correct contact number for [customer name], or let me know if they're no longer interested so we can update our records?' \n - If the customer has relocated to a different city or country, you should say, 'Understood. If your new location has our dealership, I can connect you with the team there. Otherwise, I'll update our records. Safe travels, and feel free to reach out if you're ever back in the area.'",
            "campaign_guardrails_guidelines": "- When a customer asks for a feature comparison, respond with only factual and verified information, avoid speculation or exaggeration, and ensure the conversation remains neutral and respectful without criticising or attacking competitors. \n - You should not talk about competitor brands and cars. \n - Do not  say anything negative about the Citroen Basalt. \n - You should keep all responses positive and brand-focused. \n - avoid using over-technical jargon, dumping specifications, making exaggerated or uncertified claims (such as “most advanced in segment”), criticising competitors, overwhelming the user with long feature lists, or responding in a tone that sounds like marketing or brochure copy. \n - Do not mention discounts, pricing, urgency cues (such as “limited slots” or “ending soon”), or use scarcity tactics. \n - limit technical details to a 2-3 key features at a time, and avoid emotional hype. \n - All messaging should focus on the experience, emphasize hands-on interaction with the in-car system, and consistently maintain a technology-led theme throughout the invitation. \n - If Customer Shows Low Tech Interest, Do NOT continue pushing technology. Listen to their priorities and adjust conversation accordingly \n - Please read the pincode clearly, one digit at a time",
            "campaign_objective_description": "To engage digitally influenced buyers who prioritize infotainment, connectivity, and in-car technology, and drive Test Drive bookings through structured WhatsApp engagement.",
            "custom_conversation_start_pattern": [
                "Thank you for considering the Citroen Basalt. What many tech-focused buyers are appreciating about the Basalt is how clean and intuitive the infotainment system is and a very driver-focused interface without overcomplicating things. I'd love to understand what matters most to you in your next car"
            ],
            "reasons_users_may_not_be_interested": "If customer seems low on tech interest - Don't ask to learn but speak to test a hypothesis and guage if they maybe interested in safety or family or another key feature. And then lead into it. Keep pitch warm and short. \n - If customer is busy “No problem at all. When would be a better time to call you back?” (Optional)  “I just want to make sure you don’t miss available test drive slots.” \n - If customer is just browsing “That’s completely fine. A test drive usually helps people decide faster.” “There’s no commitment at all.” “Would this weekend work, or sometime next week?” \n - If price feels high “I understand. Budget matters.” “There are financing and exchange options that often surprise people.” “Would you like me to quickly check what might work better for you?” \n - If comparing with other brands “That’s smart.” “Many customers compare before deciding.” “Instead of explaining, I’d suggest a short test drive — it gives real clarity.” “Would you like me to arrange that?”  \n - If they want to wait “I get that.” “Just so you know, current offers and availability may change later.” “I can keep you updated.” “What’s more important for you — timing or features?” \n - If they got a better deal elsewhere “Thanks for sharing that.” “Let me see what we can do on our side.” “What exactly did they offer?” \n - if they had a bad past experience “I’m really sorry to hear that.” “A lot has changed, especially service-wise.” “I’d love to give you a fresh experience — even just a drive.” \n - If family decision is involved “Of course, that makes sense.” “Would it help if everyone experienced the car together?” “I can arrange a family test drive.” \n - If worried about maintenance “That’s a valid concern.” “We have clear service packages — no surprises.” “I can explain that briefly or share it on WhatsApp.” \n - If unsure about variant “No worries — that’s very common.” “Let me ask you one or two quick questions and I’ll suggest what fits best.” \n - If they want time to think “Absolutely.” “I’ll send you the brochure and a short video.” “Would you like me to follow up, or should I wait for you to reach out?”",
        }
    if not channel_identifier:
        channel_identifier = args.channel_identifier
    if not channel_identifier:
        raise ValueError("Channel identifier is required")
    print(f"lead_id: {lead_id}, channel_identifier: {channel_identifier}")
    print(determine_campaign_next_action(
        campaign_type=args.campaign_type,
        lead_id=lead_id,
        channel="voice_phone",
        channel_identifier=channel_identifier,
        disposition=args.disposition,
        debug = debug
    ))
