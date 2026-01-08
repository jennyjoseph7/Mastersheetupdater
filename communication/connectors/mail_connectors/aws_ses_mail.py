import os, re, sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(dirname(dirname(abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from communication.connectors.mail_connectors.source_connector import *
from config import EMAIL_PROVIDER_REGION
class AwsSender(Mailsender):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        creds = kwargs.get('credentials', {}) or {}
        logger.info(f"Credentials: {creds}")
        self.credentials = self._merge_credentials(creds)
        self.client = boto3.client('ses', **self.credentials)
        logger.info(f"Client: {self.client}")
        # response = self.client.list_identities()
        # logger.info(f"Identities: {response}")
        self.provider = self.__class__.__name__

    DEFAULT_REGION = EMAIL_PROVIDER_REGION 
    
    def _merge_credentials(self, creds):
        defaults = {
            'region_name': self.DEFAULT_REGION,
            'aws_access_key_id': None,
            'aws_secret_access_key': None,
            'endpoint_url': None
        }
        merged = {**defaults, **creds}
        logger.info(f"Merged credentials: {merged}")
        
        # Optional: enforce required keys
        if not merged['aws_access_key_id'] or not merged['aws_secret_access_key']:
            logger.warning("AWS SES credentials missing — using IAM role or env vars.")
        return {k: v for k, v in merged.items() if v is not None}



    def sendMail(
        self,
        to: Union[str, List[str]],
        subject: str,
        enterprise_id: Optional[str],
        files: Optional[list] = None,
        sender: Optional[str] = None,
        **kwargs
    ) -> List[dict]:
        to, sender = self._check_to_sender(to, sender)
        logger.info("Sending emails to: %s", to)

        for recipient in to:
            start_time = time.time()
            self.tracking_id =  str(uuid.uuid4())
            cc_list = hp.make_list_from_csv(kwargs.get("cc", ""))
            bcc_list = hp.make_list_from_csv(kwargs.get("bcc", ""))

            if not isinstance(recipient, str) or not recipient.strip():
                logger.warning("Empty or invalid email for recipient %s", recipient)
                continue

            if not do_validate_email(recipient):
                logger.warning("Invalid email address: %s", recipient)
                if self.gryd_hook:
                    gryd.create_async_task(
                        self.gryd_hook,
                        self.gryd_hook_service,
                        args=['email', 'failed', enterprise_id, recipient],
                        enterprise_id=enterprise_id,
                        kwargs={"meta_data": {
                            "tracking_id":self.tracking_id,
                            "time_taken": round(time.time() - start_time, 2),
                            "provider": self.provider,
                            "to": recipient,
                            "sender": sender,
                            "subject": subject,
                            "cc": cc_list,
                            "bcc": bcc_list,
                            "error": "Invalid email address",
                            "communication_id":kwargs.get("communication_id")
                        }}
                    )
                continue

            destination = {
                "ToAddresses": [recipient],
                "CcAddresses": cc_list,
                "BccAddresses": bcc_list,
            }

            logger.info(f"CC: {cc_list}, BCC: {bcc_list}")
            tags = self._generate_tags(enterprise_id, kwargs.get("communication_id"))

            try:
                if not kwargs.get("html") and not files:
                    response = self._send_text_email(sender, recipient, subject, kwargs.get("text", ""), destination, tags)
                else:
                    response = self._send_raw_email(sender, recipient, subject, kwargs, files, tags)

                logger.info("Email sent successfully to: %s", recipient)
                self._send_gryd_event("sent", enterprise_id, recipient, sender, subject,cc_list, bcc_list, start_time, kwargs, response=response)
                return {
                    "status":"sent",
                    "enterprise_id":enterprise_id
                }

            except Exception as e:
                hp.print_error()
                logger.exception("Exception while sending email.")
                self._send_gryd_event("failed", enterprise_id, recipient, sender, subject,cc_list, bcc_list, start_time, kwargs, error=e)
                return {
                    "status":"failed",
                    "enterprise_id":enterprise_id
                }

    def _send_text_email(self, sender, recipient, subject, body, destination, tags):
        return self.client.send_email(
            Source=sender,
            Destination=destination,
            Message={
                'Subject': {'Data': subject, 'Charset': 'utf-8'},
                'Body': {'Text': {'Data': body, 'Charset': 'utf-8'}}
            },
            ReplyToAddresses=[sender],
            ReturnPath=sender,
            # Tags=tags,ConfigurationSetName='Communication-SES-Config'
        )

    def _send_raw_email(self, sender, recipient, subject, kwargs, files, tags):
        message = MIMEMultipart()
        message['Subject'] = subject
        message['From'] = sender
        message['To'] = recipient

        if cc := kwargs.get('cc'):
            message['Cc'] = cc
        if bcc := kwargs.get('bcc'):
            message['Bcc'] = bcc

        body_type = 'html' if kwargs.get('html') else 'plain'
        body_content = kwargs.get('html') or kwargs.get('text') or ''
        if body_type=="html":
            body_content+=self.get_tracking_pixel(self.tracking_id)

        message.attach(MIMEText(body_content, body_type))

        if files:
            for file_tuple in hp.make_list(files):
                filename, file_data = file_tuple[1]
                part = MIMEApplication(file_data.read())
                part.add_header('Content-Disposition', 'attachment', filename=filename)
                message.attach(part)

        recipients = hp.make_list(
            hp.make_list_from_csv(recipient) +
            hp.make_list_from_csv(kwargs.get('cc', '')) +
            hp.make_list_from_csv(kwargs.get('bcc', ''))
        )

        logger.info("Recipient list: %s", recipients)

        return self.client.send_raw_email(
            Source=sender,
            Destinations=recipients,
            RawMessage={'Data': message.as_string()},
            ConfigurationSetName='Communication-SES-Config',  # VERY IMPORTANT
            Tags=tags
        )
    def _sanitize_tag_value(self,value: str) -> str:
        """Keep only allowed characters: a-zA-Z0-9 _- . @"""
        return re.sub(r'[^a-zA-Z0-9_\-\.@]', '_', value)

    def _generate_tags(self, enterprise_id, communication_id):
        tags = []

        if enterprise_id:
            tags.append({
                'Name': 'enterprise_id',
                'Value': self._sanitize_tag_value(enterprise_id)
            })

        if server := os.environ.get('SERVER_NAME'):
            tags.append({
                'Name': 'server',
                'Value': self._sanitize_tag_value(server)
            })

        if communication_id:
            tags.append({
                'Name': 'communication_id',
                'Value': self._sanitize_tag_value(communication_id)
            })
        logger.info(f"Adding tags:: {tags}")
        return tags
    


    def _send_gryd_event(self, status, enterprise_id, recipient, sender, subject, cc_list, bcc_list, start_time, kwargs, response=None, error=None):
        """Send gryd tracking event for email status."""
        if not self.gryd_hook:
            return

        meta_data = {
            "tracking_id": self.tracking_id,
            "time_taken": round(time.time() - start_time, 2),
            "provider": self.provider,
            "to": recipient,
            "sender": sender,
            "subject": subject,
            "cc": cc_list,
            "bcc": bcc_list,
            "communication_id": kwargs.get("communication_id")
        }

        if response:
            meta_data.update({
                "message_id": response.get("MessageId"),
                "request_id": response.get("ResponseMetadata", {}).get("RequestId"),
                "http_status": str(response.get("ResponseMetadata", {}).get("HTTPStatusCode", "")),
            })

        if error:
            meta_data["error"] = str(error)

        gryd.create_async_task(
            self.gryd_hook,
            self.gryd_hook_service,
            args=['email', status, enterprise_id, recipient],
            enterprise_id=enterprise_id,
            kwargs={"meta_data": meta_data}
        )

    

MailSourceFactory.register("AwsSender",AwsSender)
MailSourceFactory.register("__default__",AwsSender)
