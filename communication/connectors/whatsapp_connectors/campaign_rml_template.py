from connectors.whatsapp_connectors.source_connectors import *

logger= hp.get_logger(__name__,level=hp.logging.DEBUG)

class RMLCampaignManager:
    def __init__(self,*args,**kwargs):
        self.template_func_dict = {
            "text_template": self._create_text_template,
            "media_template": self._create_media_template,
            "carousal_template": self._create_carousel_template,
        }

        logger.info("RMLCampaignManager initialized with template functions: {}".format(self.template_func_dict.keys()))
        pass

    def create_template(self, message_data: dict, params_data: Any = None) -> dict:
        """
        Creates a template dynamically based on the template type.

        Args:
            message_data (dict): Input data for the template.
            params_data (dict, optional): Additional parameters for variable replacement. Defaults to an empty dictionary.

        Returns:
            dict: The structured template data.

        Raises:
            ValueError: If an unsupported template type is provided.
        """
        # logger.info(f"RML create_template message_data: {message_data}, params_data: {params_data}")
        template_type = message_data.get("template_type")
        params_data = params_data or {}
        # logger.info(f"Template type: {template_type}, message_data: {message_data}, params_data: {params_data}")
        if template_type not in self.template_func_dict:
            raise ValueError(f"Unsupported template type: {template_type}")

        return self.template_func_dict[template_type](message_data, params_data)
    

    def _create_media_template(self, message_data, params_data):
        """
        Creates a media-based template message (image/video/doc) for WhatsApp.
        Conditionally includes file_name in header if available.
        """
        
        # logger.info(f"RML media template message_data: {message_data}, params_data: {params_data}")

        template_id =message_data.get("template_name") or message_data.get("template_id",)
        lang_code = message_data.get("template_language_code", "en")
        media_type = (message_data.get("media_type") or "").lower()
        media_url = message_data.get("media_url", "")
        media_file_name = message_data.get("media_file_name", "")
        template_variables = message_data.get("template_variables", [])
        button_payloads = message_data.get("template_buttons_payload", [])

        # Resolve body variables
        resolved_variables = [
            {"text": params_data.get(var, "")} for var in template_variables if var
        ]
        def _decide_button_payload(idx,payload):
            if 'http' in payload:
                return {"button_no": str(idx), "url": payload}
            return {"button_no": str(idx), "text": payload}

        # Create buttons
        buttons = [
            _decide_button_payload(idx,payload) for idx, payload in enumerate(button_payloads) if payload
        ]

        # Build header with conditional file_name
        media_header = {"link": media_url}
        if media_file_name:
            media_header["file_name"] = media_file_name

        header = [{media_type: media_header}]  if media_type else []

        payload= {
            "type": "media_template",
            "lang_code": lang_code,
            "template_name": template_id
        }
        if header:
            payload["header"] = header
        if resolved_variables:
            payload["body"] = resolved_variables
        if buttons:
            payload["button"] = buttons
        return payload
    
    def _create_text_template(self, message_data, params_data):
        """
        Creates a text-only media template payload (no media header).
        """
        # logger.info(f"RML text template message_data: {message_data}, params_data: {params_data}")
        template_id =message_data.get("template_name") or message_data.get("template_id", "")
        lang_code = message_data.get("template_language_code", "eng")
        template_variables = message_data.get("template_variables", [])
        button_payloads = message_data.get("template_buttons_payload", [])
        
        # logger.info(f"RML TEXT template message_data: {message_data}, params_data: {params_data}")
        
        
        # Resolve body variables
        body = [{"text": params_data.get(var, "")} for var in template_variables]

        # Create buttons
        buttons = [
            {"button_no": idx, "url": payload}
            for idx, payload in enumerate(button_payloads)
        ]

        payload = {
            "type": "media_template",
            "template_name": template_id,
            "lang_code": lang_code,
        }
        if buttons:
            payload["button"] = buttons
        if body:
            payload["body"] = body
        # logger.info(f"RML TEXT template payload: {payload}")
        return payload
    
    def _create_carousel_template(self, message_data, params_data):
        """
        Creates a carousel-based media template payload with max 2 buttons per card.
        """

        template_id =message_data.get("template_name")  or message_data.get("template_id" )
        lang_code = message_data.get("template_language_code", "en")
        body_variables = message_data.get("template_variables", [])
        top_body = [{"text": params_data.get(var, "")} for var in body_variables]

        carousel_data = message_data.get("carousel", [])
        carousel = []

        for card in carousel_data:
            card_type = card.get("type", "image")
            url = card.get("url", "")
            
            # Optional: allow dynamic variables for body text
            card_body_vars = card.get("template_variables", [])
            card_body = [{"text": params_data.get(var, "")} for var in card_body_vars] if card_body_vars else card.get("body", [])

            # Get and filter buttons (max 2)
            raw_buttons = card.get("button", [])
            card_buttons = [
                {
                    "button_no": btn.get("button_no"),
                    "payload": btn.get("payload")
                }
                for btn in raw_buttons
                if btn.get("button_no") is not None and btn.get("payload")
            ][:2]  # limit to 2 buttons

            carousel.append({
                "type": card_type,
                "url": url,
                "body": card_body,
                "button": card_buttons
            })

        return {
            "type": "media_template",
            "template_name": template_id,
            "lang_code": lang_code,
            "body": top_body,
            "carousel": carousel
        }





WhatsappCampaignTemplate.register("rml",RMLCampaignManager)
