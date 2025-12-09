import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from config import AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_CAMPAIGN_SERVICE_NAME, AUTOCRM_AGENT_SERVICE_NAME, gryd, hp
from autocrm_db_helper import get_pg_connector
from typing import List, Union, Dict, Any

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
    'failed': 'failed',
    'error': 'error',
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
}

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
    campaign_model = None
    lead_model = None
    user_model = None
    user_id_attr = None
    if campaign_type == "pre-sales":
        campaign_model = "pre_sales_campaign"
        lead_model = "pre_sales_lead"
        user_model = "person"
        user_id_attr = "user_id"
    elif campaign_type == "post-sales":
        campaign_model = "post_sales_campaign"
        lead_model = "post_sales_lead"
        user_model = "vehicle"
        user_id_attr = "vehicle_id"
    elif campaign_type == "dealership":
        campaign_model = "dealership_campaign"
        lead_model = "dealership_lead"
        user_model = "dealership"
        user_id_attr = "dealership_id"
    else:
        raise ValueError(f"Invalid campaign type: {campaign_type}")
    channel_identifier_name = CHANNEL_IDENTIFIER_MAP.get(channel)
    if not channel_identifier_name:
        msg = f"Invalid channel: {channel} for campaign_id={campaign_id}, campaign_type={campaign_type}, enterprise_id={enterprise_id}, doing nothing."
        logger.error(msg)
        raise ValueError(msg)
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
    # if lead_id:
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

def get_user_details(enterprise_id: str, campaign_id: str, channel: str, user_id: str, i2ce_headers: Union[dict, None] = None, **kwargs):
    i2ce_headers = i2ce_headers or I2CE_HEADERS
    if channel.upper() == 'WHATSAPP':
        if 'started' in kwargs:
            kwargs['created'] = kwargs.pop('started')
            kwargs['initiated_timestamp~'] = None
        user_detail_model = gryd.load_gryd_model('gryd_campaign_user_detail', enterprise_id)
        user_detail_archive_model = gryd.load_gryd_model('gryd_campaign_user_detail_archive', enterprise_id)
        try:
            user_details = user_detail_model.list(_page_size=1, _as_option=True, campaign_id=campaign_id, mobile_number=[user_id, user_id[-10:]], **kwargs)
        except Exception as e:
            hp.print_error(e)
            logger.error(f"Error getting user details for campaign_id={campaign_id}, channel={channel}, user_id={user_id}, error={e}")
            user_details = []
        try:
            user_detail_archive = user_detail_archive_model.list(_as_option=True, campaign_id=campaign_id, mobile_number=[user_id, user_id[-10:]], **kwargs)
        except Exception as e:
            hp.print_error(e)
            logger.error(f"Error getting user detail archive for campaign_id={campaign_id}, channel={channel}, user_id={user_id}, error={e}")
            user_detail_archive = []
        user_details = user_details + user_detail_archive
        return user_details
    elif channel.upper() in ['VOICE', 'VOICEBOT']:
        i2ce_headers = i2ce_headers or I2CE_HEADERS
        params = {
            "campaign_id": campaign_id,
            "user_id": user_id,
            "_sort_by": "started",
            "application": "voicebot",
            "_sort_reverse": True,
        }
        params.update(**kwargs)
        user_details = get_i2ce_response(f"{I2CE_BASE_URL}/objects/person_session", headers=i2ce_headers, params=params)
        user_details = user_details.get('data', [])
        return user_details

def get_campaign_detail(enterprise_id: str, campaign_id: str, channel: str, i2ce_headers: Union[dict, None] = None):
    if channel.upper() == 'WHATSAPP':
        campaign_detail_model = gryd.load_gryd_model('gryd_campaign_detail', enterprise_id)
        campaign_detail = campaign_detail_model.list(_page_size=1, _as_option=True, campaign_id=campaign_id, source = channel.lower(), _sort_by="created", _sort_reverse=True)
        if not campaign_detail:
            logger.info(f"No campaign detail found for campaign_id={campaign_id}, channel={channel}, doing nothing.")
            return
        return hp.make_single(campaign_detail, force = True)
    elif channel.upper() in ['VOICE', 'VOICEBOT']:  
        i2ce_headers = i2ce_headers or I2CE_HEADERS
        campaign_detail = get_i2ce_response(f"{I2CE_BASE_URL}/objects/campaign_detail",
            headers=i2ce_headers,
            params={
                "campaign_id": campaign_id,
                "_sort_by": "created",
                "_sort_reverse": True,
                "_page_size": 1
            })
        campaign_detail = hp.make_single(campaign_detail.get('data', []), force = True)
        return campaign_detail
    else:
        logger.info(f"No campaign detail found for campaign_id={campaign_id}, channel={channel}, doing nothing.")
        return

def get_proceed_status(user_details: list, max_attempts: int = 3, max_failed: int = 10):
    disposition_options = {
        "error": ["error", "queued"],
        "failed": ["failed", "queued"],
        "attempted": ["attempted", "queued", "engaged", "converted", "reached", "contacted"],
        "reached": ["reached", "queued", "contacted", "engaged", "converted", "attempted"],
        "contacted": ["contacted", "queued", "engaged", "converted"],
        "engaged": ["engaged", "queued", "converted"],
        "converted": ["converted", "queued"],
    }
    if not user_details:
        return True
    user_detail = hp.make_single(user_details, force = True)
    channel = user_detail.get('channel')
    campaign_id = user_detail.get('campaign_id')
    user_id = user_detail.get('user_id')
    is_contacted = len([s for s in user_details if s.get('disposition', '') in ["engaged", "converted"]]) > 0
    if is_contacted:
        logger.info(f"User {user_id} has already been contacted for campaign_id={campaign_id}, channel={channel}, doing nothing.")
        return False
    is_error = len([s for s in user_details if s.get('disposition', '') in ["error", "queued"]]) > 0
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

def determine_campaign_next_action(enterprise_id: str, campaign_id: str, channel: str, user_id: str, session_id: str, disposition: str, i2ce_headers: Union[dict, None] = None):
    # Get the campaign workflow for this campaign and channel
    workflow_model = gryd.load_gryd_model('campaign_workflow', enterprise_id)
    workflow = workflow_model.list(_page_size=1, _as_option=True, campaign_id=campaign_id, channel=channel)

    if not workflow:
        logger.info(f"No workflow found for campaign_id={campaign_id}, channel={channel}, doing nothing.")
        return
        
    workflow = hp.make_single(workflow)
    
    # Get the campaign details
    campaign_detail_model = gryd.load_gryd_model('gryd_campaign_detail', enterprise_id)
    campaign_detail = campaign_detail_model.list(_page_size=1, _as_option=True, campaign_id=campaign_id, channel = channel.lower())
    if not campaign_detail:
        logger.info(f"No campaign detail found for campaign_id={campaign_id}, channel={channel}, doing nothing.")
        return
    
    campaign_detail = hp.make_single(campaign_detail, force = True)
    
    
    # Get the campaign user detail to check status history

    user_details = get_user_details(enterprise_id, campaign_id, channel, user_id)
    if not user_details:
        logger.info(f"No user details found for campaign_id={campaign_id}, channel={channel}, user_id={user_id}, doing nothing.")
        return
        
    # Map disposition to workflow triggers
    trigger_map = {
        'error': ('on_error_trigger', 'on_error_retries', 'on_error_delay'),
        'failed': ('on_failed_trigger', 'on_failed_retries', 'on_failed_delay'),
        'attempted': ('on_attempted_trigger', 'on_attempted_retries', 'on_attempted_delay'),
        'reached': ('on_reached_trigger', 'on_reached_retries', 'on_reached_delay'),
        'contacted': ('on_contacted_trigger', 'on_contacted_retries', 'on_contacted_delay'),
        'engaged': ('on_engaged_trigger', 'on_engaged_retries', 'on_engaged_delay'),
        'converted': ('on_converted_trigger', None, None)
    }
    
    # Get trigger details based on disposition
    converted_disposition = DISPOSITION_MAP.get(disposition, '')
    logger.info(f"Converted disposition: {converted_disposition} for disposition={disposition} in channel={channel}")
    if not converted_disposition:
        logger.info(f"No disposition found for disposition={disposition} in DISPOSITION_MAP, doing nothing.")
        return
    trigger_field, retries_field, delay_field = trigger_map.get(converted_disposition, (None, None, None))
    
    if not trigger_field or not workflow.get(trigger_field):
        logger.info(f"No trigger field found for disposition={converted_disposition} in workflow={workflow}, doing nothing.")
        return
        
    # Check if we've exceeded retries
    status_count = len([s for s in user_details if s.get('disposition', '') == converted_disposition])
    ## Get from campagign_user_detail, and campaign_user_detail_archive
    max_retries = workflow.get(retries_field, 0) if retries_field else 0
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
