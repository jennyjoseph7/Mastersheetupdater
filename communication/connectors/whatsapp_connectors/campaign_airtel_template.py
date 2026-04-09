from connectors.whatsapp_connectors.source_connectors import *

from typing import Any
class AirtelCampaignManager:
    def __init__(self,*args,**kwargs):
        self.template_func_dict = {
            "text": self._create_text_template,
            "media": self._create_media_template,
            "carousel": self._create_carousel_template,
            "carousal": self._create_carousel_template
        }

        self.MEDIA_MAPPER={
            "image": "IMAGE",
            "video": "VIDEO",
            "document": "DOCUMENT",
            "audio": "AUDIO"
        }

    def create_template(self,message_data :dict , params_data:Any=None) -> dict:
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
        template_type= message_data.get("template_type")
        params_data = params_data or {}

        if template_type not in self.template_func_dict:
            raise ValueError(f"Unsupported template type: {template_type}")

        return self.template_func_dict[template_type](message_data, params_data)

    def _create_text_template(self, message_data, params_data={}):
        """
        Creates a text-based template payload for Airtel.
        """

        template_id = message_data.get("template_id") or message_data.get("template_name", "")
        response_type = message_data.get("type", "template")
        variable_params = message_data.get("template_variables", [])
        payload = message_data.get("template_buttons_payload", []) or message_data.get("template_button_payloads", [])

        # logger.info(f"TEST message_data ----{message_data}, variable_params ----{variable_params}")
        # Resolve variables from params_data
        variables = [params_data.get(param, '') for param in variable_params]
        variables = [] if all(item in ("", None) for item in variables) else variables

        # logger.info(f"TEST variables ----{variables}")
        # logger.info(f"TEST payload ----{payload}")
        return {
            "airtel_function_sequence": ["template"],
            "type": response_type,
            "template_id": template_id,
            "message": {
                "payload": payload,
                "variables": variables
            }
        }
    def _limit_buttons(self, buttons, max_buttons=2):
        return buttons[:max_buttons] if buttons else []
    
    def _resolve_variables_and_payload(self, message_data, params_data):
        variables = [params_data.get(p, '') for p in message_data.get("template_variables", [])]
        variables = [] if all(v in ("", None) for v in variables) else variables
        payload = message_data.get("template_button_payloads", []) or message_data.get("template_button_payloads", [])
        logger.info(f"TEST payload ----{payload} , variables ----{variables}")
        return variables, payload


    def _create_carousel_template(self, message_data, params_data):
        """
        Creates a carousel template with dynamic input handling.
        """
        template_id = message_data.get("template_id", "")
        carousel_items = message_data.get("carousel_items", [])
        template_type = message_data.get("type", "template")
        if not template_id:
            raise ValueError("template_id or template_name is required.")

        if template_type == "carousel" and not isinstance(carousel_items, list):
            raise ValueError("carousel_items must be a list of items.")

        
        carousel = []
        for item in carousel_items:
            buttons = item.get("buttons", [])
            if not buttons:
                buttons = [{"type": "QUICK_REPLY", "payload": item.get("payload", "VOICE")}]

            buttons = self._limit_buttons(buttons)  # Max 2 buttons allowed
            formatted_buttons = [
                {"type": "QUICK_REPLY","index": i, **button} for i, button in enumerate(buttons)
            ]

            carousel.append({
                "media_id": item.get("media_id"),
                "variables": [],
                "buttons": formatted_buttons
            })

        return {
            "type":template_type,
            "airtel_function_sequence": ["template"],
            "template_id": template_id,
            "carousel": carousel
        }


    def _create_media_template(self, message_data, params_data):
        """
        Creates a media-based template payload for Airtel with IMAGE/VIDEO type and variable support.
        """
        # logger.info(f"MEDIA TEMPLATE message_data ----{message_data}. params_data ----{params_data}")
        template_id = message_data.get("template_id") or message_data.get("template_name", "")
        response_type = message_data.get("type", "template")
        media_type = (message_data.get("media_type") or "").lower()
        media_id = message_data.get("media_id")
        variables, payload = self._resolve_variables_and_payload(message_data, params_data)

        if not media_id:
            raise ValueError("Media ID is required.")
        # Build media_attachment
        media_attachment = {
            "type": self.MEDIA_MAPPER.get(media_type, "IMAGE"),
            "id": media_id
        }

        # Optional: Include media_file_name and media_url if provided
        media_file_name = message_data.get("media_file_name")
        media_url = message_data.get("media_url")
        
        if media_file_name:
            media_attachment["file_name"] = media_file_name
        if media_url:
            media_attachment["url"] = media_url

        return {
            "airtel_function_sequence": ["template"],
            "type": response_type,
            "template_id": template_id,
            "media_attachment": media_attachment,
            "message": {
                "variables": variables,
                "payload": payload
            }
        }

WhatsappCampaignTemplate.register("airtel",AirtelCampaignManager)
