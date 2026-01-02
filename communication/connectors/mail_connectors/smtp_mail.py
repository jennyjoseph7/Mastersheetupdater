from communication.connectors.mail_connectors.source_connector import *

class SmtpSender(Mailsender):
    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        credentials = kwargs.get('credentials') or {}
        self.host = credentials.get('host', 'smtp.mailgun.org')
        self.port = credentials.get('port', 465)
        self.use_tls = credentials.get('use_tls', False)
        self.use_ssl = credentials.get('use_ssl', True)
        self.username = credentials.get('username', '@.in')
        self.password = str(credentials.get('password', ''))
        self.provider="SmtpSender"
        # msg["Message-ID"] = make_msgid()

    def sendMail(
        self,
        to: Union[str, list[str]],
        subject: str,
        enterprise_id: str,
        files: Optional[list[tuple[str, Any]]] = None,
        sender: Optional[str] = None,
        **kwargs: Any
    ) -> list[dict]:
        to, sender = self._check_to_sender(to, sender)
        logger.info("Sending mails to: %s", to)


        for recipient in to:
            start_time = time.time()
            cc_list = hp.make_list_from_csv(kwargs.get('cc'))
            bcc_list = hp.make_list_from_csv(kwargs.get('bcc'))

            if not (isinstance(recipient, str) and recipient):
                logger.warning(f"Empty email  {recipient}", )
                continue

            logger.info("Processing recipient: %s", recipient)

            # if kwargs.get('test') or os.environ.get('ENVIRONMENT', 'dev').strip() != 'production':
            #     logger.info("Original recipient: %s", recipient)
            #     user = os.environ.get('I2CE_USER', 'dinesh')
            #     recipient = f"{user}+{recipient.replace('@', '_').replace('.', '_')}@i2ce.in"
            #     logger.info("Using debug address: %s", recipient)

            if not do_validate_email(recipient):
                logger.warning("Invalid email address: %s", recipient)
                if self.gryd_hook:
                    gryd.create_async_task(
                        self.gryd_hook,
                        self.gryd_hook_service,
                        args=['email', 'failed', enterprise_id, recipient],
                        enterprise_id=enterprise_id,
                        kwargs={"meta_data": {
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
            logger.info("CC List: %s", cc_list)
            logger.info("BCC List: %s", bcc_list)

            msg = EmailMessage()
            msg['From'] = sender
            msg['To'] = ', '.join(hp.make_list_from_csv(recipient))

            if (cc := hp.make_list_from_csv(kwargs.get('cc'))):
                msg['Cc'] = ', '.join(cc)
            if (bcc := hp.make_list_from_csv(kwargs.get('bcc'))):
                msg['Bcc'] = ', '.join(bcc)

            msg['Subject'] = subject

        if reply_email := kwargs.get("reply_email"):
            def ensure_brackets(mid: str) -> str:
                if not mid:
                    return ""
                mid = mid.strip()
                return mid if mid.startswith("<") and mid.endswith(">") else f"<{mid.strip('<>')}>"

            # Get original message ID (for In-Reply-To and References)
            original_msg_id = (
                reply_email.get("message_id")
                or reply_email.get("in_reply_to")
                or reply_email.get("msg_id")
            )
            wrapped_msg_id = ensure_brackets(original_msg_id)

            # Set In-Reply-To
            if wrapped_msg_id:
                msg["In-Reply-To"] = wrapped_msg_id

            # Collect references (clean and deduplicated)
            raw_references = str(reply_email.get("references") or "")
            extracted_refs = re.findall(r"<[^>]+>", raw_references)
            cleaned_refs_set = {ref.strip() for ref in extracted_refs}

            # Add wrapped original_msg_id if not already present
            if wrapped_msg_id and wrapped_msg_id not in cleaned_refs_set:
                cleaned_refs_set.add(wrapped_msg_id)

            if cleaned_refs_set:
                # Ensure order is preserved (optional)
                sorted_refs = sorted(cleaned_refs_set)
                msg["References"] = " ".join(sorted_refs) 
                           
    
        html = kwargs.get('html')
        text = kwargs.get('text')
        tracking_id =  str(uuid.uuid4())

        if html and tracking_id:
            logger.info("Appending tracking pixel")
            if kwargs.get("to_track"):
                logger.info("Adding tracking Pixle in SMTP mail...")
                html += self.get_tracking_pixel(tracking_id)
        if html and text:
            logger.info("Adding plain text and HTML content")
            msg.set_content(text)
            msg.add_alternative(html, subtype='html')
        elif html:
            logger.info("Adding HTML content only")
            msg.add_alternative(html, subtype='html')
        elif text:
            logger.info("Adding plain text content only")
            msg.set_content(text)



        if files:
            logger.info("Attaching files")
            for f in hp.make_list(files):
                filename, fileobj = f[1][0], f[1][1]
                mimetype = mimetypes.guess_type(filename)[0]
                maintype, subtype = mimetype.split('/') if mimetype else ('application', 'octet-stream')
                msg.add_attachment(fileobj.read(), maintype=maintype, subtype=subtype, filename=filename)
                logger.info("Attached file: %s", filename)

        try:
            all_recipients = hp.make_list_from_csv(recipient) + cc_list + bcc_list
            logger.info("All recipients: %s", all_recipients)
            logger.info(f"message-- string : {msg.as_string()}")

            if self.use_ssl:
                logger.info("Using SMTP_SSL")
                logger.info(self.host)
                logger.info(self.port)
                with smtplib.SMTP_SSL(self.host, self.port) as server:
                    server.login(self.username, self.password)
                    server.send_message(msg, from_addr=sender, to_addrs=all_recipients)
            else:
                logger.info("Using SMTP")
                with smtplib.SMTP(self.host, self.port) as server:
                    if self.use_tls:
                        logger.info("Starting TLS")
                        server.starttls()
                    server.login(self.username, self.password)
                    server.send_message(msg, from_addr=sender, to_addrs=all_recipients)

            logger.info("Email sent successfully to: %s", all_recipients)
            self._send_gryd_event(
                            status="sent",
                            enterprise_id=enterprise_id,
                            recipient=recipient,
                            sender=sender,
                            subject=subject,
                            cc_list=cc_list,
                            bcc_list=bcc_list,
                            start_time=start_time,
                            kwargs=kwargs
            )

            return {
                    "status":"sent",
                    "enterprise_id":enterprise_id
                }
        except Exception as e:
            hp.print_error()
            logger.error("Failed to send email to %s: %s", recipient, str(e))

            self._send_gryd_event(
                status="failed",
                enterprise_id=enterprise_id,
                recipient=recipient,
                sender=sender,
                subject=subject,
                cc_list=cc_list,
                bcc_list=bcc_list,
                start_time=start_time,
                kwargs=kwargs,
                error=e
            )
            return {
                "status":"failed",
                "enterprise_id":enterprise_id
            }

    
    def _send_gryd_event(self, status, enterprise_id, recipient, sender, subject, cc_list, bcc_list, start_time, kwargs, error=None):
        """Trigger gryd hook events for email send status."""
        if not self.gryd_hook:
            return

        meta_data = {
            "time_taken": round(time.time() - start_time, 2),
            "provider": self.provider,
            "to": recipient,
            "sender": sender,
            "subject": subject,
            "cc": cc_list,
            "bcc": bcc_list,
            "communication_id": kwargs.get("communication_id")
        }

        if error:
            meta_data["error"] = str(error)

        gryd.create_async_task(
            self.gryd_hook,
            self.gryd_hook_service,
            args=['email', status, enterprise_id, recipient],
            enterprise_id=enterprise_id,
            kwargs={"meta_data": meta_data}
        )


MailSourceFactory.register("SmtpSender",SmtpSender)