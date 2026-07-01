import os
import sys
import types
import re
import unittest
from unittest.mock import Mock, patch


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class FakeRouteMobileTemplateMigrator:
    def __init__(self, communication_credential_id):
        self.communication_credential_id = communication_credential_id

    def _extract_ordered_variables(self, message):
        extracted = re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", message)
        seen = set()
        return [v for v in extracted if not (v in seen or seen.add(v))]

    def _process_message_variables(self, message, ordered_vars):
        processed = message
        for idx, var_name in enumerate(ordered_vars, start=1):
            pattern = r"\{\{\s*" + re.escape(var_name) + r"\s*\}\}"
            processed = re.sub(pattern, "{{" + str(idx) + "}}", processed)
        return processed

    def _build_components(self, processed_message, ordered_vars, buttons):
        body = {"text": processed_message}
        if ordered_vars:
            body["example"] = ordered_vars
        components = {"body": body}
        quick_reply_elements = [
            {"text": btn.get("buttonText") or btn.get("text") or btn.get("label")}
            for btn in buttons
            if btn.get("buttonText") or btn.get("text") or btn.get("label")
        ]
        if quick_reply_elements:
            components["buttons"] = {
                "type": "quick_reply",
                "elements": quick_reply_elements,
            }
        return components

    def _normalize_template_name(self, name):
        return re.sub(r"[^a-z0-9_]", "_", name.lower())

    def _submit_to_rml(self, *args, **kwargs):
        return "fake-template-id"


class FakeWhatsAppTemplateMigrator:
    LANG_TO_CODE = {"English": "en"}


class FakeLogger:
    def info(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


fake_generic_template_migrator = types.ModuleType("agents.generic_template_migrator")
fake_generic_template_migrator.RouteMobileTemplateMigrator = (
    FakeRouteMobileTemplateMigrator
)
fake_generic_template_migrator.WhatsAppTemplateMigrator = FakeWhatsAppTemplateMigrator

fake_config = types.ModuleType("config")
fake_config.AUTOCRM_APP_ENTERPRISE_ID = "autocrm"
fake_config.gryd = Mock()
fake_config.hp = Mock()
fake_config.hp.get_logger.return_value = FakeLogger()

sys.modules["agents.generic_template_migrator"] = fake_generic_template_migrator
sys.modules["config"] = fake_config

from agents.whatsapp_template_agents import post_rml_templates as subject


class PostRMLTemplatesTest(unittest.TestCase):
    def test_rml_helpers_prepare_variables_and_components(self):
        migrator = subject.RouteMobileTemplateMigrator("rml-whatsapp_chat-test")
        message = "Hi {{person_name}}, car {{ reg_number }} for {{person_name}}"

        ordered_vars = migrator._extract_ordered_variables(message)
        processed_message = migrator._process_message_variables(
            message, ordered_vars
        )
        components = migrator._build_components(
            processed_message,
            ordered_vars,
            [{"text": "Book Service"}, {"buttonText": "Call Back"}],
        )

        self.assertEqual(ordered_vars, ["person_name", "reg_number"])
        self.assertEqual(
            processed_message,
            "Hi {{1}}, car {{2}} for {{1}}",
        )
        self.assertEqual(
            components["buttons"]["elements"],
            [{"text": "Book Service"}, {"text": "Call Back"}],
        )
        self.assertIn("example", components["body"])

    def test_rml_components_omit_example_without_variables(self):
        migrator = subject.RouteMobileTemplateMigrator("rml-whatsapp_chat-test")

        components = migrator._build_components("Hello there", [], [])

        self.assertEqual(components, {"body": {"text": "Hello there"}})

    @patch.object(subject, "RouteMobileTemplateMigrator")
    @patch.object(subject, "_get_model")
    def test_posts_record_after_successful_approval(
        self, get_model_mock, migrator_cls_mock
    ):
        credential = {
            "provider_name": "Rml",
            "auth_creds": {"username": "user", "password": "pass"},
        }
        credential_model = Mock()
        credential_model.get.return_value = credential
        template_model = Mock()
        get_model_mock.side_effect = [credential_model, template_model]

        migrator = Mock()
        migrator._extract_ordered_variables.return_value = [
            "person_name",
            "reg_number",
        ]
        migrator._process_message_variables.return_value = "Hi {{1}}, {{2}}"
        migrator._normalize_template_name.return_value = "service_due_123"
        migrator._submit_to_rml.return_value = "rml-template-id"
        migrator_cls_mock.return_value = migrator

        result = subject.post_rml_template_for_approval(
            {
                "template_name": "Service Due",
                "template_message": "Hi {{person_name}}, {{reg_number}}",
                "campaign_type": "post-sales",
                "buttons": [{"text": "Book Service"}],
            },
            "rml-whatsapp_chat-test",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["template_id"], "rml-template-id")
        self.assertEqual(result["template_variables"], ["person_name", "reg_number"])
        template_model.post.assert_called_once()
        posted_record = template_model.post.call_args.args[0]
        self.assertEqual(posted_record["status"], "pending")
        self.assertEqual(posted_record["template_name"], "service_due_123")
        self.assertEqual(
            posted_record["communication_credentials_id"], "rml-whatsapp_chat-test"
        )

    @patch.object(subject, "RouteMobileTemplateMigrator")
    @patch.object(subject, "_get_model")
    def test_failed_approval_does_not_post(self, get_model_mock, migrator_cls_mock):
        credential_model = Mock()
        credential_model.get.return_value = {"provider_name": "rml"}
        template_model = Mock()
        get_model_mock.side_effect = [credential_model, template_model]

        migrator = Mock()
        migrator._extract_ordered_variables.return_value = []
        migrator._process_message_variables.return_value = "Hello"
        migrator._normalize_template_name.return_value = "hello_123"
        migrator._submit_to_rml.side_effect = RuntimeError("bad request")
        migrator_cls_mock.return_value = migrator

        result = subject.post_rml_template_for_approval(
            {"template_name": "Hello", "template_message": "Hello"},
            "rml-whatsapp_chat-test",
        )

        self.assertFalse(result["success"])
        template_model.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
