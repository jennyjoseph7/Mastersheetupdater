#!/usr/bin/python
# -*- coding: utf-8 -*-
import os,json
from os.path import exists as ispath, dirname, basename, join as joinpath, abspath, split as pathsplit, splitext, sep as dirsep, isfile
import sys
from urllib.parse import urlparse
sys.path.insert(0, dirname(dirname(abspath(__file__))))
from communication_helpers import *
logger=hp.get_logger(__name__)

import re
class SenderNotSetError(Exception):
	pass

def do_validate_email(email):
    for e in email.split(','):
        e = e.strip()
        if not validate_email(e):
            return False
    return True

class Mailsender(object):
    def __init__(self, sender = None, gryd_hook = None, gryd_hook_service =None,blacklist_hook = None, credentials = None, receive_hook = None, request_hook = None):
        self.gryd_hook= gryd_hook
        self.gryd_hook_service= gryd_hook_service or GRYD_COMMUNICATION_SERVICE
        self.sent_hook = gryd_hook
        self.receive_hook = receive_hook or gryd_hook
        self.blacklist_hook = blacklist_hook
        self.request_hook = request_hook
        self.sender = sender

    def _check_to_sender(self, to, sender=None):
        to = to if isinstance(to, (list, tuple)) else [to]
        if not (sender := sender or self.sender):
            raise SenderNotSetError("sender field is not set")
        return to, sender

    def sendMail(self, to, subject,enterprise_id,files=None,sender = None,**kwargs):
        pass
             
    def get_past_details(self,campaignName,campaign_id,**kwargs):
        pass

    def process_hook(self,event=None,payload=None,**params):
        pass

    def _report_status(self, status, enterprise_id, reason, kwargs):
        pass

    def get_tracking_pixel(self,tracking_id: str) -> str:
        SERVER_NAME= os.environ.get("SERVER_NAME","communication-test.gryd.in").strip("https://").strip("://").strip("/")
        HTTPS=os.environ.get("http","https")
        tracking_url = f"{HTTPS}://{SERVER_NAME}/track/open?tracking_id={tracking_id}"
        return f'<img src="{tracking_url}" alt="" width="1" height="1" style="display:none;" />'
    



class MailSourceFactory:
    _registry = {}
    _class_name = "MAIL SENDER"

    @classmethod
    def register(cls, source_type: str, source_class: type):
        cls._registry[source_type.lower()] = source_class
        # logger.info(f"✅ {cls._class_name} Registered source: {source_type} -> {source_class.__name__}")
    @classmethod
    def mail_sender(cls,source_type,gryd_hook,credentials):
        logger.info("Intializing MailSourceFactory mail_sender")
        src_type = source_type.lower()
        if not src_type:
            raise ValueError("Missing 'src_type' in campaign_user_source")

        logger.info(f"Loading campaign src_type: {src_type}")
        source_class = cls._registry.get(src_type)
        if not source_class:
            raise ValueError(f"Unsupported source type: {src_type}")
        
        return source_class(gryd_hook=gryd_hook, credentials=credentials)
        


