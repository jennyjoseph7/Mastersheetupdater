import os,json
from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
import sys
sys.path.insert(0, dirname(dirname(abspath(__file__))))
from connectors.communication_helpers import *
# from connectors.communication_configs import *
from config import AUTOCRM_COMMUNICATION_SERVICE_NAME
from gryd_worker import gryd, gryd_db_helper as db, gryd_helpers as hp
gryd.SERVICE = AUTOCRM_COMMUNICATION_SERVICE_NAME
gryd.set_queue_manager()
logger = gryd.hp.get_logger(gryd.SERVICE)
START_MAIL_TASK="gryd_start_mail"
CHANNEL_ALIASES = {
    "email": {"email", "mail"},
    "sms": {"sms", "message"},
    "push_notification": {"push_notification", "notification"}
}

@gryd.is_a_task(function_name="communication_hook")
def communication_hook(channel, event_name, enterprise_id, recipient=None, reason=None, communication_id=None, **data):
    """
    This function is a hook to all communication mediums. It takes in a channel,
    event name, enterprise id, recipient, reason, and communication id. It returns
    a response in the form of a communication object.

    Args:
        channel (str): the channel of the communication (e.g. email, sms)
        event_name (str): the event name of the communication (e.g. welcome, abandoned_cart)
        enterprise_id (str): the id of the enterprise
        recipient (str): the recipient of the communication (e.g. customer, lead)
        reason (str): the reason for the communication (e.g. order confirmation, password reset)
        communication_id (str): the id of the communication (if it exists)

    Returns:
        dict: a communication object with the following keys:
            communication_id (str): the id of the communication
            event (str): the event name of the communication
            channel (str): the channel of the communication
            reason (str): the reason for the communication
            data (dict): the data of the communication
            recipient (str): the recipient of the communication
    """
    logger.info(f"[HOOK] channel={channel}, event_name={event_name}, enterprise_id={enterprise_id}")
    
    com_obj = {}
    if communication_id:
        com_obj = fetch_record(enterprise_id, "communication", communication_id, id_attr="communication_id") or {}

    meta_data = {}
    if isinstance(data.get("meta_data"), dict):
        meta_data = data.pop("meta_data")
    elif "meta_data" in data:
        logger.warning(f"[HOOK] meta_data is not a dict, ignoring: {type(data['meta_data'])}")
        data.pop("meta_data", None)

    post_obj = {
        "event": event_name,
        "channel": channel,
        "reason": reason if reason is not None else com_obj.get("reason"),
        "data": data if data else com_obj.get("data"),
        "recipient": recipient if recipient is not None else com_obj.get("recipient")
    }
    post_obj.update(meta_data)

    if communication_id:
        post_obj["communication_id"] = make_uuid(communication_id, channel, event_name)
        if com_obj:
            logger.info(f"[HOOK] Existing communication found: {post_obj['communication_id']}")
            return com_obj
    else:
        post_obj["communication_id"] = make_uuid(hp.now())

    logger.info("[HOOK] Posting Communication: %s", json.dumps(post_obj, default=str))

    # response = update_model_record(
    #     enterprise_id,
    #     "communication",
    #     post_obj["communication_id"],
    #     post_obj,
    #     id_attr="communication_id"
    # ) or {}

    # if not response.get("communication_id"):
    #     response["communication_id"] = post_obj["communication_id"]
    response = post_obj
    logger.info("[HOOK] Response Communication: %s", json.dumps(response, default=str))
    return response



@gryd.is_a_task(function_name="communication_sender")
def communication_sender(*args, **kwargs):
    enterprise_id = kwargs.get("enterprise_id") or kwargs.get("ent_id")
    comm = Communication(enterprise_id)
    return comm.send(**kwargs)





class Communication:
    def __init__(self, enterprise_id, role='admin', test=False, user_id=None):
        self.enterprise_id = enterprise_id
        self.role = role
        self.test = test
        self.user_id = user_id

        try:
            self.enterprise = fetch_record("core","enterprise",enterprise_id,id_attr="enterprise_id")
            if isinstance(self.enterprise,tuple):
                self.enterprise= self.enterprise[0]
        except Exception as e:
            logger.error(f"Error while fetching enterprise: {e}")
            self.enterprise = {}

    def get_preferred_channels(self, receiver, channels=None):
        for channel_key, aliases in CHANNEL_ALIASES.items():
            if receiver.get(f'{channel_key}s') and (not channels or set(channels) & aliases):
                yield channel_key

    def _prepare_sender(self, kwargs):
        sender = kwargs.get("sender", {}).copy()
        sender_email = sender.get("email") or self.enterprise.get("email")
        sender_name = sender.get("name") or self.enterprise.get("name", "")
        sender_name = f"{sender_name} <{sender_email}>" if "@" not in sender_name else sender_name
        return {"email": sender_email, "name": sender_name}
    


    def _prepare_email_task(self, recipient, subject, html, sender_name, view_type, idx, total, kwargs, provider, credentials):
        delete_after_send = idx == total and kwargs.get("delete_after_send", True)
        com_obj = communication_hook('email', 'created', self.enterprise_id, recipient=recipient, provider=provider)
        logger.info("com_obj :: %s", com_obj)

        args = [recipient, subject, html, sender_name, view_type]
        task_kwargs = {
            "enterprise_id": self.enterprise_id,
            "cc": kwargs.get("cc") or kwargs.get("_cc"),
            "bcc": kwargs.get("bcc") or kwargs.get("_bcc"),
            "pdf": kwargs.get("pdf") or kwargs.get("_pdf"),
            "pdf_html": html,
            "text": html or kwargs.get("message"),
            "provider": provider,
            "credentials": credentials,
            "test": self.test,
            "files": self.files,
            "delete_after_send": delete_after_send,
            "communication_id": com_obj["communication_id"],
            "gryd_hook": "communication_hook",
            "gryd_hook_service": GRYD_COMMUNICATION_SERVICE,
            "reply_email": kwargs.get("reply_email", {}),
            "to_track":kwargs.get("to_track",False)
        }
        return args, task_kwargs

    def send_mail(self, **kwargs):
        receiver_emails = kwargs.get("receiver", {}).get("emails", [])
        if not receiver_emails:
            logger.error("❌ No receiver emails found")
            return {"error": "No receiver email data found"}

        total = len(receiver_emails)
        sender = self._prepare_sender(kwargs)
        subject = kwargs.get("subject") or kwargs.get("title") or f"Message from {kwargs.get('email_from_name') or self.enterprise.get('name')}"
        html = kwargs.get("html_string") or kwargs.get("email_template") or kwargs.get("html_template")
        view_type = kwargs.get("view_type", "transaction")
        provider = kwargs.get("provider") or self.enterprise.get("email_provider", "__default__")
        credentials = (
            kwargs.get("credentials") or
            kwargs.get("_credentials") or
            self.enterprise.get("email_provider_credentials", {})
        )
        communication_ids=[]
        task_ids={}
        for idx, recipient in enumerate(receiver_emails, 1):
            args, task_kwargs = self._prepare_email_task(
                recipient, subject, html, sender["name"], view_type,
                idx, total, kwargs, provider, credentials
            )
            logger.info(f"📤 Sending email to: {recipient}")
            logger.debug(f"ARGS: {args}")
            logger.debug(f"KWARGS: {task_kwargs}")
            if  kwargs.get("_run_async",True):
                res =gryd.create_async_task(START_MAIL_TASK, GRYD_COMMUNICATION_SERVICE, args=args, kwargs=task_kwargs)
                communication_ids.append({
                                        "communication_id":task_kwargs.get("communication_id"),
                                        "task_id":res.get("job",{}).get("task_id"),
                                        "job_id":res.get("job",{}).get("job_id"),
                                        "run_from":"EMAIL-GRYD-TASK",
            })
            else:
                try:
                    from communication import gryd_connector_mail
                    task_response=gryd_connector_mail.gryd_start_mail(*args,**task_kwargs)
                    communication_ids.append(
                        {
                            "communication_id":task_kwargs.get("communication_id"),
                            "run_from":"EMAIL-API",
                            "task_response":task_response
                        })
                except Exception as e:
                    hp.print_error()
                    logger.error(f"Unable To send the mail")
        return {"email_status":"Task Placed Successfully" if communication_ids else "Failed To Place Email Task","communication_ids":communication_ids }

    def send(self, **kwargs):
        receiver = kwargs.get("receiver") or kwargs.get("recipient") or {}
        logger.info("Receiver: %s", receiver)
        self.files = kwargs.get("files", [])

        for field in {"emails", "phone_number"}:
            if (val := receiver.get(field)):
                receiver[field] = val.split(",") if isinstance(val, str) else hp.make_list(val)
            else:
                receiver[field] = []

        for channel in self.get_preferred_channels(receiver, kwargs.get("channels")):
            if channel in {"email", "mail"}:
                return self.send_mail(**kwargs)




if __name__=='__main__':
    communication_sender(**{
        "ent_id":"test1",
        "enterprise_id":"test1",
        "sender":{
            "name":"info",
            "email":"info@iamdave.ai"
        },
        "receiver":{
            "emails":["praveen@iamdave.ai"]
        },
        "cc":"ntssahu485@gmail.com",
        "html_string":"<p>Hi Nitesh THis a test mail</p>",
        "subject":"TEST EMAIL",
        "provider":"AwsSender",
        "files":[
            ["https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/bde3c8c1-5053-47cf-8b2a-fbe8c1b8dc4f-68e8b8e4_SwiftTechnicalSpecification.pdf"]
        ],
        # "_run_async":False
        
    },
    )

    # communication_sender(**{
    #     "enterprise_id":"test1",
    #     "sender":{
    #         "name":"info",
    #         "email":"nitesh@iamdave.ai"
    #     },
    #     "receiver":{
    #         "emails":["ntssahu485@gmail.com"]
    #     },
        
    #     "html_string":"<p>Thank you for your message. We will get back to you shortly.</p>",
    #     "subject":"Re: Test drive booking request",
    #     "provider":'SmtpSender',"credentials":{
    #         'host': 'smtp.zoho.com',
    #         'port': 465,
    #         'username': 'nitesh@iamdave.ai',
    #         'password': 'VBTQckYNYyrx',
    #         'use_ssl': True
    #     },
    #     "reply_email":{
    #         "in_reply_to": "cah4jjlvde1+fsmhah95gkzogv12oj1_6xf1e_mmoxjcffxhemw@mail.gmail.com",
    #         "references": "<CAH4JJLX8X8tg=d5q9W86d-OPpage_25dQoMYJn96p9tfGe4XzQ@mail.gmail.com>\r\n <196af921e5d.10f68b4d61099910.8029631709341991170@iamdave.ai>\r\n <CAH4JJLVsZxVc7d=nO+5RyTwaEGW-0tYsg8LRAT9eMkjPh4Tz5Q@mail.gmail.com> <196b133587f.cbef08381298526.3362301239191577867@iamdave.ai>"

    #     }
    # },
    # )
    # {
#             "from_email": "nitesh@iamdave.ai",
#             "to_email": "nitesh sahu <ntssahu485@gmail.com>",
#             "cc": [],
#             "subject": "Re: Test drive booking request",
#             "body": "Thank you for your message. We will get back to you shortly.",
#             "in_reply_to": "cah4jjlvde1+fsmhah95gkzogv12oj1_6xf1e_mmoxjcffxhemw@mail.gmail.com",
#             "references": "<CAH4JJLX8X8tg=d5q9W86d-OPpage_25dQoMYJn96p9tfGe4XzQ@mail.gmail.com>\r\n <196af921e5d.10f68b4d61099910.8029631709341991170@iamdave.ai>\r\n <CAH4JJLVsZxVc7d=nO+5RyTwaEGW-0tYsg8LRAT9eMkjPh4Tz5Q@mail.gmail.com> <196b133587f.cbef08381298526.3362301239191577867@iamdave.ai>"
#         }

    pass



