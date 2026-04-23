from connectors.whatsapp_connectors.source_connectors import *

logger= hp.get_logger(__name__,level=hp.logging.DEBUG)


class RMLWebhookConverter(BaseWebhookConverter):
    def __init__(self,whatsapp_provider,*args,**kwargs)-> None:
        super().__init__(whatsapp_provider=whatsapp_provider,*args,**kwargs)

        
    def extract_text_media(self, params):
        message = params.get("messages", [{}])[0]
        if not isinstance(message, dict):
            return {}

        extra = message.get("extra",'{}')
        if isinstance(extra, str) and extra.strip():
            try:
                extra = json.loads(extra)
            except json.JSONDecodeError:
                extra = {}

        message_type = message.get("type", "text").lower()
        whatsapp_number = message.get("from") or params.get("brand_msisdn", "")
        text = option_id = button_payload= media_url = media_type = filename = None

        if message_type == "text":
            text = message.get("text", {}).get("body", "")

        elif message_type == "button":
            button = message.get("button", {})
            text = button.get("text", "")
            button_payload = button.get("payload", "")

        elif message_type == "interactive":
            interactive = message.get("interactive", {})
            reply = interactive.get("list_reply") or interactive.get("button_reply") or {}
            title = (reply.get("title") or "").strip()
            description = (reply.get("description") or "").strip()
            option_id = reply.get("id", "")

            if title and description:
                text = f"{title} - {description}"
            else:
                text = title or description
        elif message_type=="location":
            location= message.get(message_type,{})
            text= json.dumps(location)
        elif message_type in ["image", "video", "document", "audio"]:
            media_data = message.get(message_type, {})
            media_url = media_data.get("media_url")
            text=media_url
            mime_type = media_data.get("mime_type")
            filename = media_data.get("filename") 

        elif message_type in ["flow"]:
            flow=message.get(message_type,{})
            response_json = flow.get("response_json",{})
            text= response_json
            
        # Extract context info if present
        context = message.get("context", {})
        context_info = {
            "message_context_id": context.get("id"),
            "message_context_request_id": context.get("from")
        } if context else {}

        # Construct the final dictionary
        message_info = {
            "message_type": message_type,
            "message_option_id": option_id,
            "message_text": text,
            "message_media_url": media_url,
            "message_media_type": media_type,
            "filename": filename,
            "button_payload":button_payload
        }

        message_info.update(context_info)
        go_to, intent,count= ("none", "none","none") if not option_id else (option_id.split("##") + ["",""])[:3]
        if message_type=="interactive":
            message_info.update({
                "go_to": go_to,
                "intent":intent,
            })
        if isinstance(extra,dict) and 'goto' in extra:
            message_info.update({k:v for k,v in extra.items() if v})
        

        # Return cleaned result without empty/null values
        return {
            k: v for k, v in message_info.items()
            if v not in NullEmptyCheck
        }


        

    def extract_media(services_params):
        pass
         

    def payload_converter(self, *args, **kwargs):
        start_time = time.time()
        logger.info(f"RML webhook process started at: {start_time}")
        try:
        # Process RML webhook payload here
        

            self.default_message_dict = {
                "whatsapp_provider": kwargs.get("whatsapp_provider"),
                "enterprise_id": kwargs.get("enterprise_id"),
                "conversation_id": kwargs.get("conversation_id"),
                "mobile_number": kwargs.get("messages", [{}])[0].get("from", "") or  kwargs.get("statuses", [{}])[0].get("recipient_id", ""),
                "from_number": kwargs.get("brand_msisdn", ""),
                "request_id":kwargs.get("request_id",),
                "message_id": kwargs.get("statuses", [{}])[0].get("id", ""),
                "message_request_id": kwargs.get("statuses", [{}])[0].get("message_id", "") or kwargs.get("statuses", [{}])[0].get("id", ""),
                "session_id": kwargs.get("statuses", [{}])[0].get("conversation", {}).get("id", ""),
                "message_status": kwargs.get("statuses", [{}])[0].get("status", "").upper(),
                "message_sort": None,
                "message_stream": None,
                "webhook_action": kwargs.get("webhook_action"),
                "webhook_received_time": kwargs.get("webhook_received_time"),
                "message_dict": kwargs.get("messages", [{}])[0],
                "message_type": kwargs.get("messages", [{}])[0].get("type", "text"),
                "message_text": kwargs.get("messages", [{}])[0].get("text", {}).get("body", ""),
                "message_voice": None,
                "message_image": None,
                "message_document": None,
                "message_location": None,
                "profile_name": kwargs.get("contacts", [{}])[0].get("profile", {}).get("name", ""),
                "message_parameters": kwargs.get("messageParameters", {}),
                "error": kwargs.get("statuses", [{}])[0].get("errors", [{}])[0],
                "status_timestamp": kwargs.get("statuses", [{}])[0].get("timestamp", None),
                "message_timestamp": kwargs.get("messages", [{}])[0].get("timestamp", None),
                "profile_id": kwargs.get("contacts", [{}])[0].get("wa_id", ""),
                "profile": kwargs.get("profile", {}),
                "language": kwargs.get("language", "en"),
            }
            # Flatten error details into self.default_message_dict
            error_details = self.default_message_dict.get("error", {})
            if isinstance(error_details, dict):
                self.default_message_dict.update({f"error_{key}": value for key, value in error_details.items()})
            # Extract and update additional context and media details
            # self.default_message_dict.update(self.extract_context_message(kwargs) or {})
            self.default_message_dict.update(self.extract_text_media(kwargs) or {})
            logger.info(f"RML webhook process endend at: {time.time()-start_time}")
           
        except Exception as e:
            logger.error(f"Error while processing incoming webhook: {e}", exc_info=True)
            return {"error": "Error while processing RML webhook payload"}
        


class RMLWhatsAppMessenger(BaseWhatsappMessenger):
    '''
    '''
    SUPPORTED_TEMPLATES = {"text_template", "media_template", "carousel_template"}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.temporary_data = {}
    def message_payload(self, message: str=None,**kwargs):
        response_data = kwargs.get("response_data") or {}
        payload = {"text": message or "Hey User!"}
        return payload
    
   
    def create_template(self, template_type: str, **kwargs) -> dict:
        """
        Unified template creation for text, media and carousel templates.
        Uses kwargs for flexible inputs.
        """
        logger.info("*****************")
        if template_type not in RMLWhatsAppMessenger.SUPPORTED_TEMPLATES:
            raise ValueError(f"Unsupported template type: {template_type}")

        template_name = (
            kwargs.get("template_id") or 
            kwargs.get("template_name", "")
        )
        lang_code = kwargs.get("template_language_code", "en")
        params_data = kwargs.get("params_data", {}) or {}
        template_variables = kwargs.get("template_variables", [])
        button_payloads = kwargs.get("template_buttons_payload", [])

        # ------ Body Resolution ------
        resolved_body = [
            {"text": params_data.get(var, "")}
            for var in template_variables
        ]

        # ------ Button Resolution ------
        def _make_button(idx, payload):
            if isinstance(payload, str) and payload.startswith("http"):
                return {"button_no": str(idx), "url": payload}
            return {"button_no": str(idx), "text": payload}

        buttons = [
            _make_button(idx, payload)
            for idx, payload in enumerate(button_payloads)
            if payload
        ]

        payload = {
            # "type": "media",
            "type": template_type,
            "template_name": template_name,
            "lang_code": lang_code
        }

        # ----------------------
        # CASE 1: MEDIA TEMPLATE
        # ----------------------
        if template_type == "media_template":
            media_type = (kwargs.get("media_type") or "").lower()
            media_url = kwargs.get("media_url", "")
            media_file_name = kwargs.get("media_file_name", "")

            if media_type:
                media_header = {"link": media_url}
                if media_file_name:
                    media_header["file_name"] = media_file_name

                payload["header"] = [{media_type: media_header}]

            if resolved_body:
                payload["body"] = resolved_body

            if buttons:
                payload["button"] = buttons

            return payload

        # ----------------------
        # CASE 2: TEXT TEMPLATE
        # ----------------------
        if template_type == "text_template":
            if resolved_body:
                payload["body"] = resolved_body
            if buttons:
                payload["button"] = buttons
            return payload

        # ----------------------
        # CASE 3: CAROUSEL TEMPLATE
        # ----------------------
        if template_type == "carousel_template":
            carousel_data = kwargs.get("carousel", [])
            carousel = []

            for card in carousel_data:
                card_type = card.get("type", "image")
                card_vars = card.get("template_variables", [])
                card_body = (
                    [{"text": params_data.get(v, "")} for v in card_vars]
                    if card_vars else card.get("body", [])
                )

                raw_buttons = card.get("button", [])[:2]
                card_buttons = [
                    {"button_no": b.get("button_no"), "payload": b.get("payload")}
                    for b in raw_buttons
                    if b.get("button_no") is not None and b.get("payload")
                ]
                payload_data={}
                if card_type:
                    payload_data.update({"type": card_type})
                if card_body:
                    payload_data.update({"body": card_body})
                if card_buttons:
                    payload_data.update({"button": card_buttons})
                if card.get("url"):
                    payload_data.update({"url": card.get("url")})
                if payload_data:
                    carousel.append(payload_data)

            if resolved_body:
                payload["body"] = resolved_body

            payload["carousel"] = carousel
            return payload

    
    def _handle_multi_message_type(self,message_type: str, data_key: str, response_data: dict,message=None,**kwargs):
            """
            Generic method to handle different message types (template, location, etc.).
            - Extracts data from `response_data` and sends the corresponding request.
            - Logs the payload for debugging purposes.
            
            :param message_type: The type of message being handled (e.g., "template", "location").
            :param data_key: The key used to extract data from the response_data.
            :param response_data: The incoming response data containing the message information.
            :param message: The incoming meesage used for location_request_message message information.
            """
            logger.info(f"TEST _handle_multi_message_type: {response_data}")
            if not (data := response_data.pop(data_key, None)) and  not response_data.pop("is_campaign",None):
                logger.warning(f"Not a {message_type} type message")
                return
            if data in NONE_TEMPLATE_TYPES:
                return
            if message_type=='location_request_message':
                location_request_message= data.get("location_request_message") or message
                payload = {"media":{"type":"location_request_message","body":location_request_message}}
                self._prepare_send_request(payload,**kwargs)
                return
            
            if message_type=="flow" and data.get("flow_type","dynamic")=="dynamic":
                flow_message= data.get("flow_message", ' ').strip() or message
                payload = {
                    "type": "flow",
                    "body":flow_message or ' ',
                    "footer":data.get("footer",' '),
                    "flow":{
                        "flow_token":data.get("flow_token","AQAAAAACS5FpgQ_cAAAAAD0QI3s"),
                        "flow_id":data.get("flow_id",),
                        "flow_cta":data.get("flow_cta"),
                        "flow_action":data.get("flow_action","data_exchange"),
                        "flow_action_payload":data.get("flow_action_payload",{})
                        }
                    }

                flow_action_payload = data.get("flow_action_payload")

                if flow_action_payload:
                    # Enforce screen presence
                    if "screen"  in flow_action_payload:
                        payload["flow"]["flow_action_payload"] = flow_action_payload
                    else:
                        logger.warning("Flow Action Payload is there but not screen name is missing")
                self._prepare_send_request(payload,**kwargs)
                return
            if message_type=="template":
                logger.info("*****************")
                logger.info(f"In RML Template {data}, response_data: {response_data}")
                # rt= self.create_template(data.pop("template_type",None),**data)
                rt= self.create_template(response_data.pop("type",None),**response_data)
                
                logger.info(json.dumps(rt,indent=4 ) )
                # {"media":rt}
                self._prepare_send_request({"media":rt},**kwargs)
                return
                 


            # message_type= response_data.get("type")    
            data = data if isinstance(data, dict) else response_data
            payload = {"media":{"type": message_type,**data}}
            self._prepare_send_request(payload,**kwargs)

    def process_request(
        self,
        payload_function: Callable[..., Dict[str, Any]],
        extra_payload: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        res_temp: Optional[Dict[str, Any]] = None,
        media_func: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        type: Optional[str] = None,
        **kwargs: Any
    ) -> Any:
        """
        Processes an API request by:
        - Generating payload using `payload_function`
        - Optionally attaching media (to first chunk or full payload)
        - Sending formatted payload(s) to WhatsApp API
        """

        self.api = joinpath(self.base_url)
        logger.info(f"Calling payload_function: {payload_function}")

        if not (payload := payload_function(response_data=res_temp, message=message, type=type)):
            return
        # Case 1: Batched interactive payload (e.g., paginated list picker)
        if isinstance(payload, types.GeneratorType) and type == "interactive_list":
            for idx, chunk in enumerate(payload):
                chunk_payload=  {"media":chunk}
                self._prepare_send_request(chunk_payload,extra_payload,None if idx == 0 else "View More",**kwargs)

        # Case 2: Single interactive payload
        elif type == "interactive_reply":
            logger.info(f"RML interactive_reply ::{payload} ")
            media_data = media_func(res_temp) if media_func else None
            payload= {"media":payload}
            if media_data:
                payload["media"].update({"header":media_data})
            self._prepare_send_request(payload, extra_payload, None, **kwargs)

        elif type=="interactive_cta":
            logger.info(f"RML interactive_cta ::{payload} ")
            final_payload= {
                "media":{
                    "type":"interactive_cta",
                    "body":message,
                    "action": {
                        "parameters": {
                            "display_text": res_temp.get("url_display_text","Click here"),
                            "url": res_temp.get("url","")
                        }
                    }
                }
            }
            self._prepare_send_request(final_payload, extra_payload, None, **kwargs)


        # Case 3: Plain text or fallback
        else:
            logger.info(f"RML text ::{payload} ")
            final_payload = {"text":  message}
            self._prepare_send_request(final_payload, extra_payload, message, **kwargs)

        return self.res
    
    def buttons_payload(self,response_data: dict=None, message: str = None,**kwargs) -> Optional[dict]:
        valid_options, use_description, _ = self.prepare_button_options(response_data)
        if not valid_options or use_description or len(valid_options) > 3:
            return
        return {
            
                "type": "interactive_reply",
                # "header":{"text": message or "Please choose an option",},
                "body":message or "Please choose an option",
                # "footer_text": "c@2021",
                "button": [
                        {
                            "id":f'{btn.get("go_to") or "none"}##{btn.get("intent") or "none"}##_{count}',
                            "title":btn["title"][:20],
                        }
                        for count,btn in enumerate(valid_options)
                    ]
        }
    def listpicker_payload(self, response_data: dict = None, message: str = None, **kwargs):
        valid_options, use_description, heading = self.prepare_button_options(response_data)
        if not valid_options:
            return

        def _generate_id(title: str, intent: str = "option") -> str:
            return f'{intent.lower()}__{title.strip().lower().replace(" ", "_")}'

        # Build cleaned_rows using your logic
        cleaned_rows = [
            {
                "id":f'{o.get("go_to") or "none"}##{o.get("intent") or "none"}##_{count}',
                "title": " " if use_description else o["title"][:24],
                "description": o["title"][:72] if use_description else o.get("description", "")[:72],
                
            }
            for count,o in enumerate(valid_options)
        ]

        is_first = True
        for i in range(0, len(cleaned_rows), 10):
            chunk = cleaned_rows[i:i + 10]
            yield {
                "type": "interactive_list",
                "body": message or "Please choose an option" if is_first else "Please choose an option",
                
                # "footer_text": kwargs.get("footer", ""),  //optional
                "button_text": kwargs.get("global_button", "Select Below"),
                
                "button": [
                    {
                        "section_title": heading,
                        # "subtitle": kwargs.get("subtitle", "Choose from below") if is_first else "",
                        "row": chunk
                    }
                ]
            }
            is_first = False



    def interactive_media_payload(
        self,
        response_data: Dict[str, Any],
        message: Optional[str] = None,
        media_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Constructs a dynamic WhatsApp payload for supported media types and
        removes the used media data from response_data.

        Args:
            response_data (dict): Media metadata dictionary.
            message (str, optional): Optional message.
            media_type (str, optional): Explicit media type.

        Returns:
            dict: WhatsApp media payload or empty dict.
        """
        if not response_data:
            logger.error("No response data found for media payload.")
            return {}

        media_order = response_data.get("media_order") or self.media_types
        media_type, media_meta = self.get_media_type_and_meta(response_data, self.media_types)
        if not media_type: return {}

        payload = {"type": media_type.lower()}

        if media_type != "location":
            url = media_meta.get("url") or media_meta.get("link")
            if not url:
                logger.warning(f"Missing URL/link for {media_type}.")
                return {}
            payload["url"] = url

            for field in ["file", "filename", "caption"]:
                if field=="filename" and field in media_meta:
                    payload["file"]=media_meta[field]
                elif field in media_meta:
                    payload[field] = media_meta[field]
        else:
            for field in ["longitude", "latitude", "name", "address"]:
                if field in media_meta:
                    payload[field] = media_meta[field]

        return payload


    def manage_rml_api(self, default_payload: Optional[Dict[str, Any]], *args, **kwargs):
        start_time= time.time()
        kwargs.update({"processing_start_time":start_time})
        self.res={}
        data = kwargs.pop("data", {})
        response_data = data.get("response_data", {})
        message = kwargs.pop("message",None)  or data.pop("placeholder",None)  or data.pop("message",None)
        session_id = kwargs.pop("session_id",None) or data.pop("session_id",None)
        self.default_payload=default_payload
        # self.default_payload.update({"sessionId": session_id}) if session_id else None
        logger.info(f"Response data for creating payload: {safe_orjson_dumps(response_data)}", )
        extra_payload= {
            "extra":json.dumps({"goto":response_data.get("goto"),"go_to":response_data.get("go_to"),"intent":response_data.get("intent")})}
        kwargs.update(extra_payload =extra_payload)
        
        def handle_media():
            payload=  self.interactive_media_payload(response_data)    
            if not payload:return
            payload= {"media":payload}
            self._prepare_send_request(payload,**kwargs)

        def handle_message():
            """
            Handles sending messages based on the message type and button configuration.

            This function supports:
            - Split messages using the '|' character. Each part is treated as a separate message.
            - Interactive buttons and list picker rendering based on button characteristics.
            - Dynamic selection of message payload type:
                - If there are ≤ 3 buttons and all titles are ≤ 20 characters, `buttons_payload` is used.
                - If there are > 3 buttons or any button title exceeds 20 characters (but ≤ 24), `listpicker_payload` is used.
                - If any button title exceeds 24 characters, the button's long text is moved to the description field.
                - If the button count exceeds 10, the payload is sent in batches of 10 using a generator.
            - Interactive media (images, videos, etc.) is attached only for `buttons_payload` (not for list picker).

            Conditions:
            - If `message` is empty, 'None', or 'null' (case-insensitive), the function logs an error and exits.
            - Message parts are matched with buttons via `split_option_index` in `response_data`.

            Returns:
                None. The function internally sends the message(s) using `self.process_request` and updates `self.res`.
            """

            is_msg_invalid = not message or message.strip().lower() in {'none', 'null'}
            has_buttons = isinstance(response_data.get("buttons"), list) and bool(response_data["buttons"])
            has_media = any(media in response_data for media in self.media_types)

            if is_msg_invalid and not has_buttons:  # and not has_media
                logger.warning("No valid message, buttons, or media found to send.")
                return
            is_url = response_data.get("url",'')
            is_valid_url=  True if is_url and is_url.startswith("http") else False



            # message_parts = message.split("|") if not is_msg_invalid else [""]
            message_parts =self.split_message_safely(message,is_msg_invalid)
            option_index =  len(message_parts)  if not response_data.get("split_option_index") else 1
            for msg_index, msg in enumerate(message_parts, start=1):
                temp_data = response_data if msg_index == option_index else {}

                temp_buttons = isinstance(temp_data.get("buttons"), list) and temp_data["buttons"]
                desc_check = self.check_descriptions(temp_data)

                payload_func, media_func, msg_type = self.message_payload, None, "text"

                if temp_buttons and len(temp_data["buttons"]) <= 3 and not desc_check:
                    payload_func = self.buttons_payload
                    media_func = self.interactive_media_payload
                    msg_type = "interactive_reply"
                elif temp_buttons:
                    payload_func = self.listpicker_payload
                    msg_type = "interactive_list"
                elif is_valid_url:
                    msg_type="interactive_cta"

                elif has_media:
                    media_func = self.interactive_media_payload
                logger.info(f"payload_func::: {payload_func}")
                self.res = self.process_request(
                    payload_function=payload_func,
                    message=msg,
                    res_temp=temp_data,
                    media_func=media_func,
                    type=msg_type,
                    **kwargs
                )
                SleepOverMessage()


        def handle_contact():
            """
            Handles the contact message type.
            Uses the generic _handle_multi_message_type method to process the template payload.
            """
            logger.error("Not impelemented")
            pass
        def handle_template():
            """
            Handles the template message type.
            Uses the generic _handle_multi_message_type method to process the template payload.
            """
            self._handle_multi_message_type(message_type="template", data_key="template", response_data=response_data,**kwargs)
            SleepOverMessage()

        def handle_location():
            """
            Handles the location message type.
            Uses the generic _handle_multi_message_type method to process the location payload.
            """
            self._handle_multi_message_type(message_type="location", data_key="location", response_data=response_data,**kwargs)
            SleepOverMessage()
        def handel_request_loaction():
            self._handle_multi_message_type(message_type="location_request_message", data_key="location_request_message", response_data=response_data,message=message,**kwargs)
            SleepOverMessage()
        def handle_flow():
            self._handle_multi_message_type(message_type="flow", data_key="flow", response_data=response_data,message=message,**kwargs)
            SleepOverMessage()



        # Function mapping
        seq_map = {
            'template': handle_template,
            'message': handle_message,
            'media': handle_media,
            'location': handle_location,
            'location_request_message':handel_request_loaction,
            'contact': handle_contact,
            "flow":handle_flow
        }

        function_sequence = response_data.get('message_send_sequence', ['template','location','location_request_message','contact','flow','message', 'media'])

        logger.info(f'Received function calling sequence: {function_sequence}' )

        for func_name in function_sequence:
            handler = seq_map.get(func_name)

            if not handler:
                logger.warning(
                    f'Function "{func_name}" not found in manage_rml_api.'
                )
                continue

            try:
                # -------- FLOW --------
                if func_name == "flow":
                    flow_data = response_data.get("flow")
                    if not flow_data:
                        continue

                    handler()

                    # If flow owns the UI, suppress plain text message
                    if not flow_data.get("flow_message"):
                        message = None

                # -------- LOCATION REQUEST --------
                elif func_name == "location_request_message":
                    loc_req = response_data.get("location_request_message")
                    if not loc_req:
                        continue

                    handler()

                    # If location request has its own body, suppress text
                    if not loc_req.get("location_request_message"):
                        message = None

                # -------- MESSAGE --------
                elif func_name == "message":
                    if not message:
                        continue

                    handler()

                # -------- OTHER TYPES --------
                else:
                    handler()

            except Exception as e:
                logger.error(
                    f"Error executing '{func_name}': {str(e)}",
                    exc_info=True
                )


        logger.info(f'Time taken to manage {self.whatsapp_provider} API for {default_payload.get("to")}: {time.time() - start_time} seconds' )
        return self.res




WhatsappReceiverConnector.register("rml",RMLWebhookConverter)
WhatsappMessangerConnector.register("rml",RMLWhatsAppMessenger)


 




