# from connectors.whatsapp_connectors.source_connectors import BaseWebhookConverter,BaseWhatsappMessenger,WhatsappReceiverConnector,WhatsappMessangerConnector,SleepOverMessage
# from connectors.communication_helpers import truncate_values,safe_orjson_dumps,NullEmptyCheck
# from communication_configs import *
# from typing import Optional,Dict,Any, List, Union, Callable,Tuple,Generator
# import os
# import uuid
# import requests
# import base64
import types
# import time
# # from captcha.image import ImageCaptcha
# # from PIL import Image
# from PIL import Image
# from io import BytesIO


from connectors.whatsapp_connectors.source_connectors import *

class AirtelWebhookConverter(BaseWebhookConverter):
    logger.info("AirtelWebhookConverter initialized")
    def __init__(self,whatsapp_provider,*args,**kwargs)-> None:
        super().__init__(*args,**kwargs)

        

    # @timelogger()
    def download_and_save_whatsapp_opus(self,
        media_id: str,
        whatsapp_number: str,
        output_dir: str = 'output_audio',
        headers: Optional[Dict[str, str]] = None,
        enterprise_id= None,
        media_type=None,
        **kwargs
    ) -> dict:
        """
        Downloads WhatsApp media and saves it as an .opus file with UUID name.

        :param media_id: Media ID from WhatsApp
        :param whatsapp_number: WhatsApp phone number
        :param auth_token: Base64-encoded Basic Auth string
        :param output_dir: Directory to save audio
        :return: dict with UUID and file path or error
        """
        os.makedirs(output_dir, exist_ok=True)

        headers = self.get_headers(whatsapp_number,enterprise_id=enterprise_id)

        file_uuid = str(uuid.uuid4())

        url = (
            "https://iqwhatsapp.airtel.in/gateway/airtel-xchange/"
            "whatsapp-content-manager/v1/media"
        )
        if not headers:
            
                logger.error("No headers or auth token provided for the request")
                return {"error": "No headers or auth token provided for the request"}
        

        headers.setdefault("X-Correlation-Id", "abc")
        headers.setdefault("Content-Type", "application/json")

        params = {
            "mediaId": media_id,
            "customerId": "SOCIOGRAPH_uu76NiJRbNmsq5zPgu5V",
            "phoneNumber": whatsapp_number
        }

        try:
            logger.info(f"Sending request to URL: {url}")
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            logger.info(f"Response received: Status Code {response.status_code}")

            response_data = response.json()
            logger.info(f"Response JSON: {truncate_values(response_data)}")

            if (byte_data := response_data.get("bytes")) is None:
                logger.error("Missing 'bytes' field in base64 response")
                return {"error": "Missing 'bytes' field in base64 response"}

            content = base64.b64decode(byte_data)
            ext = "." + response_data.get("contentType", {}).get("subtype", "opus")
            opus_path = os.path.join(output_dir, f"{file_uuid}{ext}")

            logger.info(f"Saving file to: {opus_path}")
            with open(opus_path, 'wb') as f:
                f.write(content)

            bucket_url= hp.upload_to_s3(opus_path,enterprise_id=enterprise_id, )

            logger.info(f"File saved successfully with UUID: {file_uuid}")
            r={
                "uuid": file_uuid,
                "file_path": bucket_url,
                "content":self.audio_to_text_converter(bucket_url) if media_type=="audio" else None
            }
            if isinstance(r.get("content"), dict) and "customer_response" in r["content"]:
                r["customer_response"] = r["content"]["customer_response"]

            logger.info(f"MEDIA-CONTENT::  {safe_orjson_dumps(r)}")
            return r

        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            return {"error": f"Request error: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"error": f"Unexpected error: {e}"}

    
    def convert_audio_text(self,):
        pass

    def extract_context_message(self,params):
        message_parameter = params.get("messageParameters",{})
        context = message_parameter.get("context",{})
        context_id =context.get("id")
        context_request_id= context.get("messageRequestId")
        context_info = {
            "message_context_id":context_id,
            "message_context_request_id":context_request_id,
        }
        context_info = {key: value for key, value in context_info.items() if value and value not in NullEmptyCheck}
        return context_info
    def extract_text_media(self, params):
        """
        Extracts text, option_id, and media details from the incoming WhatsApp message.

        Supports: text, button, interactive (list/button reply), audio/image/document.
        """
        message = params.get("message", {})
        message_type = message.get("type", "text").lower()
        enterprise_id = params.get("enterprise_id")
        whatsapp_number = params.get("sourceAddress") or params.get("to")

        text, option_id, media_url, media_mime = None, None, None, None
        if message_type == "text":
            text = message.get("text", {}).get("body")
            # logger.info(f"TEST message_text--{text}")
            

        elif message_type == "button":
            button_data = message.get("button", {})
            text = button_data.get("text")
            option_id = button_data.get("payload")

        elif message_type == "interactive":
            interactive = message.get("interactive", {})
            reply = interactive.get("list_reply") or interactive.get("button_reply", {})
            text = reply.get("title")
            option_id = reply.get("id")
            description =  reply.get("description")

            if text and text.strip():
                pass
            else:
                text=description

        else:  # Media (audio/image/document/video)
            media_data = message.get(message_type, {})
            media_id = media_data.get("id")
            media_mime = media_data.get("mime_type")
            filename = media_data.get("filename")

            if media_id:
                media_url = self.download_and_save_whatsapp_opus(
                    whatsapp_number=whatsapp_number,
                    enterprise_id=enterprise_id,
                    media_id=media_id,
                    filename=filename,
                    media_type=message_type
                )

                if message_type == "audio" and isinstance(media_url, dict):
                    content = media_url.get("content")
                    if isinstance(content, dict):
                        text = content.get("customer_response")
        # Construct final clean message info
        result = {
            "message_type": message_type,
            "message_option_id": option_id,
            "message_text": text,
            "message_media_url": media_url,
            "message_media_type": media_mime
        }

        # Parse option ID for intent if available (only in interactive)
        if option_id and message_type == "interactive":
            go_to, intent, *_ = (option_id.split("##") + ["", ""])
            result.update({
                "go_to": go_to or "none",
                "intent": intent or "none"
            })

        # Return cleaned non-null fields
        return {k: v for k, v in result.items() if v not in NullEmptyCheck}

    def payload_converter(self, *args, **kwargs):
        """
        Converts incoming webhook payload into a standardized format.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments containing webhook details.

        Updates:
            self.default_message_dict: Stores structured message data.
        """
        try:
            # Extract required parameters
            message = kwargs.get("message", {})
            profile = kwargs.get("profile", {})
            error_details = kwargs.get("error", {})
        
            # Update default message dictionary
            self.safe_update_dict({
                "whatsapp_provider": kwargs.get("whatsapp_provider"),
                "enterprise_id": kwargs.get("enterprise_id"),
                "conversation_id": kwargs.get("conversation_id"),
                "mobile_number": kwargs.get("recipientAddress", "") or kwargs.get("from", ""),
                "from_number": kwargs.get("sourceAddress", "") or kwargs.get("to", ""),
                "message_id": kwargs.get("messageId"),
                "message_request_id": kwargs.get("messageRequestId", ""),
                "session_id": kwargs.get("sessionId"),
                "message_status": kwargs.get("msgStatus", "").upper(),
                "message_sort": kwargs.get("msgSort"),
                "message_stream": kwargs.get("msgStream"),
                "message_dict": message,
                "webhook_action": kwargs.get("webhook_action"),
                "webhook_recieved_time": kwargs.get("webhook_recieved_time"),
                "profile": profile,
                "error": error_details,
                "message_parameters": kwargs.get("messageParameters"),
                "status_timestamp": kwargs.get("createdDate"),
                "message_timestamp": message.get("timestamp"),
                "profile_name": profile.get("name"),
                "language": kwargs.get("language"),
                "webhook_received_time":kwargs.get("webhook_received_time")
            })

            # Flatten error details into self.default_message_dict
            if isinstance(error_details, dict):
                self.safe_update_dict({f"error_{key}": value for key, value in error_details.items()})


            logger.info(f"Airtel webhook payload_converter: {kwargs}")
            # Extract and update additional context and media details
            self.safe_update_dict(self.extract_context_message(kwargs) or {})
            self.safe_update_dict(self.extract_text_media(kwargs) or {})
        except Exception as e:
            logger.error(f"Error while processing incoming webhook: {e}", exc_info=True)


class AirtelWhatsAppMessenger(BaseWhatsappMessenger):
    """
    A class to manage WhatsApp messaging functionality via Airtel's messaging service.
    """
    def __init__(self,*args,**kwargs):
        """
        Initialize the AirtelWhatsAppMessenger class.
        Any setup related to the service can be added here in the future.
        """
        super().__init__(self,*args,**kwargs)
        self.temporary_data={}
    def process_request(
        self,
        api_path: str,
        payload_function: Callable[..., Dict[str, Any]],
        extra_payload: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        res_temp: Optional[Dict[str, Any]] = None,
        media_func:Optional[Dict[str,Any]]=None,
        **kwargs: Any
    ) -> Any:
        """
        Processes an API request by generating a payload, optionally updating it, and making the API call.
        """
        # Call the payload function
        payload_result = payload_function(res_temp)
        # Check if payload_result is a generator
        if isinstance(payload_result, types.GeneratorType):
            first_batch = True
            for batch_payload in payload_result:
                self._prepare_send_request(
                    batch_payload, 
                    extra_payload, 
                    message or "Select Below Options" if first_batch else "View More",  # Send message only for the first batch
                    custom_api_path=api_path,
                    **kwargs
                )
                first_batch = False  
        else:
            # Single payload
            if media_func:
                payload_result.update(media_func(res_temp))
            if message or kwargs.get("message_type"):
                self._prepare_send_request(payload_result or {}, extra_payload, message, media_func=media_func,custom_api_path=api_path,**kwargs)
            
        return self.res
    
    def message_payload(self, message: str, res_temp: Optional[Dict[str, Any]] = None):
        if not message: return None
        res_temp = res_temp or {}
        payload = {}
        payload["message"] = {"text": message}
        return payload
    
    def interactive_media_payload(self, response_data: Optional[Dict[str, Any]], type: Any = None) -> Dict[str, Any]:
        if not response_data:
            return {}

        media_type, media_meta = self.get_media_type_and_meta(response_data, self.media_types)
        if not media_type:
            return {}

        media_fields = self.extract_common_media_fields(media_meta)
        media_url = media_fields["url"]
        media_id = media_meta.get("media_id", "")
        use_url = media_url.startswith("http")

        if media_type == "IMAGE" and use_url:
            try:
                media_reference = self.convert_to_jpeg(media_url)
            except Exception as e:
                logger.exception("Image conversion failed")
                return {}
        else:
            media_reference = media_url if use_url else media_id

        payload = {
            "mediaAttachment": {
                "type": media_type,
                "fileName": media_fields["filename"]  if "document"!= media_type.lower()  else media_meta.get("title",""),
                "caption": media_fields["caption"],
                "url" if use_url else "id": media_reference
            }
        }
        return payload
    
    def convert_to_jpeg(self, media_url: str) -> str:
        try:
            response = requests.get(media_url, timeout=10)
            response.raise_for_status()

            img = Image.open(BytesIO(response.content))
            original_format = img.format.upper()

            # Return original URL if the image is JPEG or PNG
            if original_format in ("JPEG", "PNG"):
                logger.info(f"Image format is {original_format}. Returning original URL.")
                return media_url

            path = hp.joinpath('static/uploads/', self.enterprise_id, 'jpeg_images')
            hp.mkdir_p(path)

            # Convert image to RGB if needed
            if img.mode != "RGB":
                logger.info(f"Converting image mode from {img.mode} to RGB")
                img = img.convert("RGB")

            filename = os.path.basename(media_url).split("?")[0]
            jpeg_filename = os.path.splitext(filename)[0] + '.jpeg'
            jpeg_path = os.path.join(path, jpeg_filename)

            img.save(jpeg_path, format='JPEG', quality=95)

            final_url = '{}://{}/{}'.format(
                os.environ.get('HTTP', 'http'),
                hp.os.environ.get('SERVER_NAME', 'localhost:5000'),
                jpeg_path
            )
            logger.info(f"JPEG image saved: {jpeg_path} | Accessible at: {final_url}")
            return final_url

        except Exception as e:
            logger.exception(f"Error converting image to JPEG: {e}")
            return media_url  # fallback to original if conversion fails
    
    def template_payload(self, response_data: Optional[Dict[str, Any]]):
        payload = {}
        payload["templateId"] = response_data.get(
            "template_id",
        )
        payload["message"] = {
            "variables": response_data.get("variables", []),
            "payload": response_data.get("buttons", []),
            'suffix': response_data.get('suffix', '')
        }

        if response_data.get("carousel"):
            payload["message"] = {
                "variables": response_data.get("variables", []),
                "carouselCard": [
                    {
                        "index": i,
                        "carouselMediaId": v["media_id"],
                        "carouselMediaType": v.get("media_type", "IMAGE").upper(),
                        "carouselBodyVariables": v["variables"],
                        "carouselButtons": [
                            {
                                "index": j,
                                "type": k.get("type", "QUICK_REPLY").upper(),
                                "payload": k.get("payload", "Text"),
                            }
                            for j, k in enumerate(v["buttons"])
                        ],
                    }
                    for i, v in enumerate(response_data.get("carousel"))
                ],
            }
        elif response_data.get("media_attachment") or any(
            response_data.get(i) for i in self.media_types
        ):
            payload["mediaAttachment"] = response_data.get(
                "media_attachment", {}
            ) or self.interactive_media_payload(response_data).get("mediaAttachment", {})
        
        return payload

    def long_text(self,message:str, limit:int=1024):
        return True  if len(str(message)) > limit else False
    
    def map_payload(self, response_data: Optional[Dict[str, Any]]):
        return  {'location': response_data.get('location', {})}
    
    def buttons_payload(self,response_data: Optional[Dict[str, Any]]):
        valid_options, use_description, _ = self.prepare_button_options(response_data)
        if not valid_options or use_description or len(valid_options) > 3:
            return  # Not suitable for simple buttons

        return {
            "buttons": [
                {
                    "tag": f'{o.get("go_to") or "none"}##{o.get("intent") or "none"}##_{count}',
                    "title": o.get("title", "")
                }
                for count,o in enumerate(valid_options) if isinstance(o, dict)
            ]
        }

    def listpicker_payload(self,response_data: Optional[Dict[str, Any]]):
        valid_options, use_description, heading = self.prepare_button_options(response_data)
        if not valid_options:
            return

        def _generate_tag(title: str) -> str:
            return f'{title.lower().replace(" ", "_")}__{hp.id_generator(2)}'

        cleaned_options = [
            {
                "tag": f'{o.get("go_to") or "none"}##{o.get("intent") or "none"}##_{count}',
                "title": " " if use_description else o["title"],
                "description": o["title"] if use_description else ""
            }
            for count , o in enumerate(valid_options)
        ]

        for i in range(0, len(cleaned_options), 10):
            yield {
                "list": {
                    "heading": heading,
                    "options": cleaned_options[i:i + 10]
                }
            }
    
    def manage_airtel_api(self, default_payload: Optional[Dict[str, Any]], **kwargs):
        """
        Manages Airtel API calls based on the provided response data and function sequence.
        Supports template, message, media, location, and contact types.
        """
        self.__init__(**kwargs)
        start_time = time.time()
        kwargs.update({"processing_start_time":start_time})

        # logger.info(f"TEST manage_airtel_api --{json.dumps(kwargs,indent=4)}")
        self.res = {}

        data = kwargs.pop("data", {})
        response_data = data.get("response_data", {})

        nested_placeholder = (
            data
                .get("response", {})
                # .get("placeholder", {})
                .get("placeholder")
        )

        message = (kwargs.pop("message", None) or nested_placeholder or data.get("message"))

        session_id = kwargs.pop("session_id", None) or data.get("session_id")

        self.default_payload = default_payload
        
        # Update the default payload with session ID
        self.default_payload.update({"sessionId": session_id}) if session_id else None

        # logger.info(f"Response data for creating payload: {safe_orjson_dumps(response_data)}", )
        
        def handle_media():
            """
            Iterates over supported media types and sends each as a formatted payload
            if present in the response_data. Supports: image, document, audio, video.
            """
            for media_type in ["image", "document", "audio", "video"]:
                if (media := response_data.get(media_type)):
                    media_url = media.get("url", "") or media.get("link","")
                    media_id = media.get("media_id", "")
                    use_url = media_url.startswith("http")

                    if media_type.upper() == "IMAGE" and use_url:
                        try:
                            media_reference = self.convert_to_jpeg(media_url)
                        except Exception as e:
                            hp.print_error()
                            logger.exception(f"Failed to convert image to JPEG: {e}")
                            return {}
                    else:
                        media_reference = media_url if use_url else media_id

                    payload = {
                        "mediaAttachment": {
                            "type": media_type.upper(),
                            "fileName": media.get("filename", "") if "document"!= media_type.lower()  else media.get("title",""),
                            "caption": media.get("caption", ""),
                            "url" if use_url else "id": media_reference
                        }
                    }
                    url=f"{self.base_url}/session/send/media"
                    self._prepare_send_request(payload,custom_api_path=url)
                    SleepOverMessage()
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
            nonlocal message
            is_msg_invalid = not message or message.strip().lower() in {'none', 'null'}
            has_buttons = isinstance(response_data.get("buttons"), list) and bool(response_data["buttons"])
            has_media = any(media in response_data for media in self.media_types)

            if is_msg_invalid and not has_buttons:  # and not has_media
                logger.error("No valid message, buttons, or media found to send.")
                return

            # message_parts = message.split("|") if not is_msg_invalid else [""]
            message_parts =self.split_message_safely(message,is_msg_invalid)
            # option_index = len(message_parts)  or int(response_data.get("split_option_index", 1))
            option_index =  len(message_parts)  if not response_data.get("split_option_index") else 1
            logger.info(f"message_parts:: {len(message_parts)}  option_index :: {option_index}")
            for msg_index, msg in enumerate(message_parts, start=1):
                temp_data = response_data if msg_index == option_index else {}

                temp_buttons = isinstance(temp_data.get("buttons"), list) and temp_data["buttons"]
                desc_check = self.check_descriptions(temp_data)

                payload_func, media_func, msg_type = self.message_payload, None, "text"

                if temp_buttons and len(temp_data["buttons"]) <= 3 and not desc_check:
                    payload_func = self.buttons_payload
                    media_func = self.interactive_media_payload
                    msg_type = "interactive"
                    api_path =f"{self.base_url}/session/send/interactive/buttons"
                elif temp_buttons:
                    payload_func = self.listpicker_payload
                    msg_type = "interactive"
                    api_path = f"{self.base_url}/session/send/interactive/list"
                else:
                    api_path =f"{self.base_url}/session/send/text"

                self.res = self.process_request(
                    api_path,
                    payload_function=payload_func,
                    extra_payload=None,
                    message=msg,
                    res_temp=temp_data,
                    media_func=media_func,
                    type=msg_type,
                    **kwargs
                )
                SleepOverMessage()
            message=None

        
        def handle_template():
            # logger.info(f"response_data::: {safe_orjson_dumps(response_data)}")
            if any(response_data.get(i) for i in ['template', 'template_id']) or response_data.get("is_campaign"):
                if response_data.get("template", "").lower() in NONE_TEMPLATE_TYPES or response_data.get("template_id", "").lower() in NONE_TEMPLATE_TYPES:
                    logger.info("Template not found or marked to skip")
                    return

                extra_payload = {"message": response_data.get("message")} if "message" in response_data else {}
                logger.info(f"[HANDLE_TEMPLATE] Sending template with payload: {extra_payload}")
                self.res = self.process_request(
                    f"{self.base_url}/template/send",
                    self.template_payload,
                    extra_payload=extra_payload,
                    res_temp=response_data,
                    message_type="template",
                    **kwargs
                )
                SleepOverMessage()

        def handle_location():
            if any(response_data.get(i) for i in ['location', 'geolocation', 'latitude', 'longitude']):
                self.res = self.process_request(f"{self.base_url}/session/send/location", self.map_payload,res_temp=response_data,**kwargs)
                SleepOverMessage()
        def handle_contact():
            if response_data.get('contact'):
                self.res = self.process_request(f"{self.base_url}/session/send/contacts", lambda _: {"contacts": response_data.get('contact', [])},res_temp=response_data,**kwargs)
                SleepOverMessage()
        # Function mapping
        seq_map = {
            'template': handle_template,
            'message': handle_message,
            'media': handle_media,
            'location': handle_location,
            'contact': handle_contact
        }

        # Execute functions based on the sequence
        function_sequence = response_data.get('message_send_sequence', ['template', 'location', 'contact','message', 'media', ])
        logger.info(f'Received function calling sequence: {function_sequence}' )

        for func_name in function_sequence:
            handler = seq_map.get(func_name)
            if handler:
                try:
                    handler()
                except Exception as e:
                    logger.error(f"Error executing '{func_name}': {str(e)}", exc_info=True)
            else:
                logger.warning(f'Function "{func_name}" not found in manage_airtel_api.', )

        logger.info(f'Time taken to manage Airtel API for {default_payload.get("to")}: {time.time() - start_time} seconds' )
        return self.res
    
    def handle_custom_template(self,*args,**kwargs):
        logger.info(f"[trigger custom template---]--{kwargs}")
        extra_payload = {"message": kwargs.get("message")} if "message" in kwargs else {}
        logger.info(f"[HANDLE_TEMPLATE] Sending template with payload: {extra_payload}")
        res = self.template_payload(response_data=kwargs)
        res["from"]=self._format_mobile_number(kwargs.get("sender"))
        res["to"]=self._format_mobile_number(kwargs.get("mobile_number"))
        url = f"{kwargs.get('base_url')}/template/send"
        headers=kwargs.get("headers")  
        self.post_api(url, res, headers)
        

WhatsappReceiverConnector.register("airtel",AirtelWebhookConverter)
WhatsappMessangerConnector.register("airtel",AirtelWhatsAppMessenger)



