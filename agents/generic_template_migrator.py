import json
import os
import re
import sys
import time
from abc import ABC, abstractmethod
from os.path import abspath, dirname
from typing import Dict, List, Optional

import requests

try:
    from .base_agent import BaseAgent
except ImportError:
    from base_agent import BaseAgent

BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from config import (
    AUTOCRM_APP_ENTERPRISE_ID,
    AUTOCRM_COMMUNICATION_SERVICE_NAME,
    AUTOCRM_SHORT_RUN_AGENT_SERVICE_NAME,
    AutocrmModel,
    gryd,
    hp,
)

gryd.SERVICE = AUTOCRM_SHORT_RUN_AGENT_SERVICE_NAME
gryd.set_queue_manager()

from autocrm_db_helper.PGConnector import AutoCRMPGConnector

m = AutocrmModel("dealership_idea")
pg = AutoCRMPGConnector(enterprise_id="autocrm")
logger = hp.get_logger("TemplateMigratorAgent")


class TemplateMigrationAbortError(Exception):
    """Raised by a migrator to abort the entire batch immediately.

    Use this when continuing the loop is pointless (e.g. provider-side
    auth failures that will repeat for every template). Carries a
    ``user_message`` that is safe to surface to end users / the frontend.
    """

    def __init__(self, user_message: str, *args):
        super().__init__(user_message, *args)
        self.user_message = user_message


class TemplateMigratorAgent(BaseAgent, ABC):
    """Abstract base for migrating WhatsApp communication templates to new credentials.

    Uses the Template Method pattern: the migration workflow is fixed in
    ``migrate_templates_to_new_credential``, while channel-specific behaviour
    is delegated to the abstract hooks listed below.

    Subclasses **must** implement:
      - ``channel``  (property) – the channel name this migrator handles.
      - ``build_migration_record()`` – builds the new template record.

    Subclasses **may** override:
      - ``validate_template()`` – channel-specific pre-migration validation.
    """

    SUPPORTED_CHANNELS = ["whatsapp_chat"]
    MIGRATION_DELAY_SECONDS = 1

    def __init__(self, communication_credential_id: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not communication_credential_id:
            raise ValueError("communication_credential_id is required")
        self.communication_credential_id = communication_credential_id
        self.name = self.__class__.__name__
        self.description = (
            "Agent to migrate communication templates to a new credential "
            "identified by communication_credential_id."
        )

    # ── Abstract interface ──

    @property
    @abstractmethod
    def channel(self) -> str:
        """The channel this migrator handles (e.g. ``'whatsapp_chat'``)."""
        ...

    @abstractmethod
    def build_migration_record(
        self, template: dict, credential: dict, cred_id: str
    ) -> Optional[dict]:
        """Build the record to POST for a single template migration.

        Returns:
            A dict representing the new template, or ``None`` to skip.

        Raises:
            Exception: to mark the template as *failed*.
        """
        ...

    # ── Overridable hook ──

    def validate_template(self, template: dict) -> bool:
        """Return ``True`` if the template is eligible for migration."""
        return True

    # ── Shared variable helpers ──

    def _extract_ordered_variables(self, message: str) -> List[str]:
        variable_pattern = r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}"
        extracted = re.findall(variable_pattern, message)
        seen: set = set()
        return [v for v in extracted if not (v in seen or seen.add(v))]

    def _process_message_variables(
        self, message: str, ordered_vars: List[str]
    ) -> str:
        processed = message
        for idx, var_name in enumerate(ordered_vars, start=1):
            pat = r"\{\{\s*" + re.escape(var_name) + r"\s*\}\}"
            processed = re.sub(pat, "{{" + str(idx) + "}}", processed)
        return processed

    # ── Concrete helpers ──
    def _get_comm_cred_model(self):
        return gryd.base_model.Model(
            "communication_credential", AUTOCRM_APP_ENTERPRISE_ID
        )

    def _get_template_model(self):
        return gryd.base_model.Model("template", AUTOCRM_APP_ENTERPRISE_ID)

    def _fetch_credential(self) -> dict:
        """Fetch the communication credential by ``self.communication_credential_id``."""
        return self._get_comm_cred_model().get(
            self.communication_credential_id
        )

    @staticmethod
    def _attach_common_fields(record: dict, template: dict) -> dict:
        """Copy disposition fields from the source template when present."""
        if template.get("disposition"):
            record["disposition"] = template["disposition"]
        if template.get("disposition_details"):
            record["disposition_details"] = template["disposition_details"]
        return record

    # ── Main workflow (Template Method) ──

    def migrate_templates_to_new_credential(self, job=None) -> Dict:
        """Migrate all templates for the configured ``communication_credential_id``."""
        cred_id = self.communication_credential_id
        credential = self._fetch_credential()

        if not credential:
            logger.error(f"No credential found for id: {cred_id}")
            return {"error": f"No credential found for id: {cred_id}"}

        logger.info(f"Processing credential: {cred_id} (channel={self.channel})")

        template_model = self._get_template_model()
        # Retrieve only "generic" templates from DB (boolean filter).
        templates = list(
            pg.list(
                table_name="template",
                where={"channel": self.channel, "is_generic": True},
            )
        )
        logger.info(f"Found {len(templates)} '{self.channel}' templates to migrate")

        # Edge case: if the generic templates already belong to the target
        # credential, there is nothing to migrate. Since all generic templates
        # share the same source credential, checking the first one is enough.
        if templates:
            source_cred_id = templates[0].get("communication_credentials_id")
            if source_cred_id == cred_id:
                msg = (
                    f"Source and target communication_credentials_id are the "
                    f"same ('{cred_id}'). Nothing to migrate — aborting."
                )
                logger.error(msg)
                return {
                    "error": msg,
                    "communication_credentials_id": cred_id,
                    "channel": self.channel,
                    "total": len(templates),
                    "success": 0,
                    "failed": 0,
                    "skipped": 0,
                }

        results = {
            "communication_credentials_id": cred_id,
            "channel": self.channel,
            "total": len(templates),
            "success": 0,
            "failed": 0,
            "skipped": 0,
        }

        for i, tmpl in enumerate(templates):
            if not self.validate_template(tmpl):
                logger.warning(
                    f"Skipping invalid template: {tmpl.get('template_id', '?')}"
                )
                results["skipped"] += 1
                continue

            try:
                new_record = self.build_migration_record(
                    tmpl, credential, cred_id
                )
            except TemplateMigrationAbortError as abort:
                # Hard-stop signal from a migrator (e.g. RML auth failure).
                # Continuing the loop would re-trigger the same error for
                # every remaining template, so we bail out with a clean
                # user-facing message for the frontend.
                logger.error(
                    f"Migration aborted for {cred_id}: {abort.user_message}"
                )
                results["error"] = abort.user_message
                return results
            except Exception as e:
                logger.error(f"Failed to build migration record: {e}")
                results["failed"] += 1
                time.sleep(self.MIGRATION_DELAY_SECONDS)
                continue

            if new_record is None:
                results["skipped"] += 1
                continue

            new_record = self._attach_common_fields(new_record, tmpl)

            # Ensure `is_generic` is never carried over to the migrated record.
            new_record.pop("is_generic", None)

            try:
                template_model.post(new_record)
                results["success"] += 1
                logger.info(
                    f"Posted template [{i + 1}/{len(templates)}] for {cred_id}"
                )
            except Exception as e:
                logger.error(f"Failed to post template into model: {e}")
                results["failed"] += 1

            time.sleep(self.MIGRATION_DELAY_SECONDS)

        logger.info(
            f"Credential {cred_id} ({self.channel}) done — "
            f"success={results['success']}, "
            f"failed={results['failed']}, "
            f"skipped={results['skipped']}"
        )

        return results


# Concrete channel migrators

class WhatsAppTemplateMigrator(TemplateMigratorAgent):
    """Submits templates to the Airtel API for approval, then stores the
    returned ``templateId`` in the new record."""

    AIRTEL_TEMPLATE_URL = (
        "https://iqwhatsapp.airtel.in/gateway/airtel-xchange/"
        "whatsapp-content-manager/v1/template"
    )

    LANG_TO_CODE = {
        "English": "en", "Hindi": "hi", "Assamese": "as", "Bengali": "bn",
        "Gujarati": "gu", "Kannada": "kn", "Kashmiri": "ks", "Malayalam": "ml",
        "Marathi": "mr", "Nepali": "ne", "Odia": "or", "Punjabi": "pa",
        "Sanskrit": "sa", "Sindhi": "sd", "Tamil": "ta", "Telugu": "te",
        "Urdu": "ur", "Konkani": "kok", "Manipuri": "mni", "Maithili": "mai",
        "Santali": "sat", "Dogri": "doi", "Bodo": "bdo",
    }

    @property
    def channel(self) -> str:
        return "whatsapp_chat"

    def validate_template(self, template: dict) -> bool:
        return bool(
            template.get("template_name") and template.get("template_message")
        )

    def _submit_for_approval(
        self, template_name: str, credential: dict,
        processed_message: str, buttons: list,
        ordered_vars: List[str], lang_code: str,
    ) -> str:
        payload = {
            "templateName": template_name,
            "wabaId": credential.get("waba_id"),
            "customerId": credential.get("customer_id"),
            "category": "MARKETING",
            "subAccountId": credential.get("sub_account_id"),
            "templateContent": {
                "language": lang_code,
                "body": processed_message,
                "buttons": buttons,
                "sample": {"variables": ordered_vars},
            },
        }
        if not ordered_vars:
            payload["templateContent"].pop("sample", None)

        resp = requests.post(
            self.AIRTEL_TEMPLATE_URL,
            headers=credential.get("auth_headers"),
            data=json.dumps(payload),
        )
        if not resp.ok:
            raise RuntimeError(
                f"Airtel API error for '{template_name}': "
                f"{resp.status_code} — {resp.text}"
            )

        new_template_id = resp.json().get("template", {}).get("templateId")
        if not new_template_id:
            raise RuntimeError(
                f"No templateId returned for '{template_name}': {resp.json()}"
            )
        return new_template_id

    def build_migration_record(
        self, template: dict, credential: dict, cred_id: str
    ) -> dict:
        template_name = template["template_name"]
        template_message = template["template_message"]

        buttons = [
            {
                "type": btn.get("type", "QUICK_REPLY"),
                "buttonText": btn.get("buttonText") or btn.get("text"),
            }
            for btn in (template.get("buttons") or [])
        ]

        ordered_vars = self._extract_ordered_variables(template_message)
        processed_message = self._process_message_variables(
            template_message, ordered_vars
        )

        lang_raw = (template.get("language") or "english").strip().capitalize()
        lang_code = self.LANG_TO_CODE.get(lang_raw, "en")

        new_template_id = self._submit_for_approval(
            template_name, credential, processed_message,
            buttons, ordered_vars, lang_code,
        )

        return {
            "buttons": template.get("buttons"),
            "channel": "whatsapp_chat",
            "language": template.get("language", "english"),
            "template_id": new_template_id,
            "campaign_type": template.get("campaign_type"),
            "template_name": template_name,
            "template_type": template.get("template_type", "text"),
            "template_message": template_message,
            "campaign_objective_name": template.get("campaign_objective_name"),
            "template_variables": template.get("template_variables", []),
            "template_button_payloads": template.get(
                "template_button_payloads", []
            ),
            "communication_credentials_id": cred_id,
        }


class RouteMobileTemplateMigrator(TemplateMigratorAgent):
    """Migrates templates using Route Mobile (RML) WhatsApp Business API.

    Endpoint and payload follow the Route Mobile WBS OpenAPI spec:
    https://routemobile.github.io/WhatsApp-Business-API/WBS.html
      tag: WhatsApp-Messaging-Template-API  op: createTemplate

    Auth: we always mint a fresh ``JWTAUTH`` via the Login API
    (``POST /auth/v1/login/``) using ``credential['auth_creds']``
    (``username`` + ``password``). Any stored ``Authorization`` on
    ``credential['auth_headers']`` is ignored — the spec states JWTs
    are only valid for one hour.
    Spec: https://routemobile.github.io/WhatsApp-Business-API/WBS.html
      #tag/WhatsApp-Login/operation/loginApi2
    """

    RML_TEMPLATE_URL = "https://apis.rmlconnect.net/wba/template/create"
    RML_LOGIN_URL = "https://apis.rmlconnect.net/auth/v1/login/"

    # Support inbox notified when the RML Login API rejects the stored
    # credentials (typically a stale/rotated password). The dealership's
    # primary contact is added alongside it as the receiver.
    RML_SUPPORT_NOTIFY_EMAIL = "support@autongage.com"

    # Route Mobile only accepts these three template categories.
    _VALID_RML_CATEGORIES = {"MARKETING", "UTILITY", "AUTHENTICATION"}

    def __init__(self, communication_credential_id: str, *args, **kwargs):
        super().__init__(communication_credential_id, *args, **kwargs)
        # JWT is minted lazily on first API call and reused across the batch
        # (one migration run may submit many templates).
        self._jwt: Optional[str] = None

    @property
    def channel(self) -> str:
        return "whatsapp_chat"

    def validate_template(self, template: dict) -> bool:
        return bool(
            template.get("template_name") and template.get("template_message")
        )

    def _login_for_jwt(self, credential: dict) -> str:
        """Call RML's Login API and return a fresh ``JWTAUTH`` string.

        Raises:
            RuntimeError: if ``auth_creds`` is missing or login fails.
        """
        auth_creds = credential.get("auth_creds") or {}
        if not isinstance(auth_creds, dict):
            raise RuntimeError(
                "RML: credential.auth_creds is missing or not a dict; "
                "cannot mint JWT."
            )
        username = auth_creds.get("username")
        password = auth_creds.get("password")
        if not username or not password:
            raise RuntimeError(
                "RML: credential.auth_creds.username / password is missing; "
                "cannot mint JWT."
            )

        try:
            resp = requests.post(
                self.RML_LOGIN_URL,
                headers={"Content-Type": "application/json"},
                data=json.dumps({"username": username, "password": password}),
            )
        except Exception as e:
            raise RuntimeError(f"RML: login request failed: {e}") from e

        if not resp.ok:
            raise RuntimeError(
                f"RML: login failed: {resp.status_code} — "
                f"{resp.text[:500] if resp.text else '<empty>'}"
            )

        try:
            body = resp.json()
        except Exception as e:
            raise RuntimeError(f"RML: login response not JSON: {e}") from e

        jwt = body.get("JWTAUTH") or body.get("jwtauth") or body.get("token")
        if not jwt:
            raise RuntimeError(f"RML: login response missing JWTAUTH: {body}")

        logger.info("RML: login succeeded; obtained fresh JWTAUTH")
        return jwt

    def _generate_example_values(self, ordered_vars: List[str]) -> List[str]:
        """Return one example value per variable (flat list, RML format)."""
        mapping = {
            "person_name": "Rahul",
            "name": "Rahul",
            "reg_number": "KA01AB1234",
            "car_model": "Honda City",
            "vehicle_model": "Hyundai Creta",
            "service_due_date": "15 Feb 2026",
            "workshop_name": "Elite Auto Care",
            "dealer_name": "Prime Motors",
            "campaign_offer": "Flat 20% off on service",
            "warranty_expiry_date": "31 Dec 2026",
            "time": "10:30 AM",
        }
        return [mapping.get(v, v) for v in ordered_vars]

    def _map_category(self, raw_category: Optional[str]) -> str:
        """Map internal ``campaign_type`` to a valid RML template category."""
        if not raw_category:
            return "MARKETING"
        normalized = raw_category.strip().upper().replace("-", "_")
        if normalized in self._VALID_RML_CATEGORIES:
            return normalized
        # Route Mobile rejects anything outside the allowed set, so fall back
        # to MARKETING for business categories like "POST_SALES", "PRE_SALES",
        # etc. Callers can override by setting campaign_type explicitly.
        return "MARKETING"

    def _build_headers(self, credential: dict) -> dict:
        """Build request headers for the RML API.

        The ``Authorization`` JWT is always freshly minted via the Login
        API using ``credential['auth_creds']`` (``username``/``password``),
        then cached on the instance for the remainder of the migration batch.
        Any stored ``credential['auth_headers']`` / ``credential['api_key']``
        is intentionally ignored.
        """
        if not self._jwt:
            try:
                self._jwt = self._login_for_jwt(credential)
            except Exception as e:
                # Bad/expired RML password is the dominant failure here; alert
                # the support team and the dealership's primary contact so the
                # credentials can be refreshed before the migration is retried.
                self._notify_login_failure(credential, str(e))
                # Hard-stop the batch — every subsequent template would hit
                # the same auth wall and re-spam the support inbox.
                raise TemplateMigrationAbortError(
                    "Invalid login password"
                ) from e
        return {
            "Content-Type": "application/json",
            "Authorization": self._jwt,
        }

    def _resolve_primary_contact_email(self, credential: dict) -> Optional[str]:
        """Resolve the dealership's primary contact email for RML alerts.

        Prefers the value already projected onto the credential (via a
        ``refers`` to the parent dealership). Falls back to fetching the
        ``dealership`` model when not present, so this works even on
        credentials whose schema doesn't expose the field directly.
        """
        email = credential.get("primary_contact_email")
        if email:
            return email

        dealership_id = credential.get("dealership_id")
        if not dealership_id:
            return None

        try:
            dealership = gryd.base_model.Model(
                "dealership", AUTOCRM_APP_ENTERPRISE_ID
            ).get(dealership_id)
        except Exception as e:
            hp.print_error()
            logger.warning(
                f"RML notify: failed to fetch dealership '{dealership_id}' "
                f"for primary_contact_email: {e}"
            )
            return None

        return (dealership or {}).get("primary_contact_email")

    def _notify_login_failure(self, credential: dict, error_message: str) -> None:
        """Email support + dealership primary contact on RML login failure.

        Best-effort: never raises — a notification failure must not mask
        the underlying login error that the caller is about to surface.
        """
        try:
            primary_contact_email = self._resolve_primary_contact_email(credential)

            receiver_emails = [self.RML_SUPPORT_NOTIFY_EMAIL]
            if primary_contact_email and primary_contact_email not in receiver_emails:
                receiver_emails.append(primary_contact_email)

            dealership_id = credential.get("dealership_id", "")
            dealer_name = credential.get("dealer_name", "")
            sender_number = credential.get("sender", "")
            channel = credential.get("channel", "")
            waba_id = credential.get("waba_id", "")
            cred_id = self.communication_credential_id

            html_string = f"""
                <p>Hi Team,</p>

                <p><b>RML whatsapp api login failed during generic template migration, It could be due to change of username/password or deactivation of account</b></p>

                <p><b>Details:</b></p>
                <ul>
                    <li><b>Dealership Id:</b> {dealership_id}</li>
                    <li><b>Dealer Name:</b> {dealer_name}</li>
                    <li><b>Sender Number:</b> {sender_number}</li>
                    <li><b>Channel:</b> {channel}</li>
                    <li><b>Communication Credential Id:</b> {cred_id}</li>
                    <li><b>Waba Id :</b> {waba_id}</li>
                </ul>

                <p><b>Error Response:</b></p>
                <pre style="background:#f4f4f4;padding:12px;border-radius:6px;font-size:13px;white-space:pre-wrap;">{error_message}</pre>

                <p>Please check the RML credentials (username/password) or account status.</p>
            """

            email_kwargs = {
                "enterprise_id": AUTOCRM_APP_ENTERPRISE_ID,
                "sender": {
                    "name": "info",
                    "email": "info@iamdave.ai",
                },
                "receiver": {
                    "emails": receiver_emails,
                },
                "html_string": html_string,
                "subject": (
                    f"⚠️ RML Credential Failure for {dealer_name} "
                    f"{sender_number} - {cred_id}"
                ),
            }

            enqueue_result = gryd.create_async_task(
                "communication_sender",
                "communication",
                kwargs=email_kwargs,
                environment="test"
            )
            logger.info(
                f"RML notify: credential-failure email enqueued to "
                f"{receiver_emails} for credential '{cred_id}': "
                f"{enqueue_result}"
            )
        except Exception as notify_exc:
            logger.error(
                f"RML notify: failed to enqueue login-failure email: "
                f"{notify_exc}"
            )

    def _build_components(
        self,
        processed_message: str,
        ordered_vars: List[str],
        buttons: list,
    ) -> dict:
        """Build the RML ``components`` object (body + optional buttons)."""
        body: Dict = {"text": processed_message}
        if ordered_vars:
            body["example"] = self._generate_example_values(ordered_vars)

        components: Dict = {"body": body}

        if buttons:
            # Route Mobile expects `text` (not `label`) on quick_reply button
            # elements. The Quick Reply example in their OpenAPI doc shows
            # `label` but the server rejects it with 422 "Unknown field"; the
            # Carousel/Multi-Product examples in the same spec correctly use
            # `text`, which is what the API actually accepts.
            quick_reply_elements = [
                {
                    "text": (
                        btn.get("buttonText")
                        or btn.get("text")
                        or btn.get("label")
                    )
                }
                for btn in buttons
                if (btn.get("buttonText") or btn.get("text") or btn.get("label"))
            ]
            if quick_reply_elements:
                components["buttons"] = {
                    "type": "quick_reply",
                    "elements": quick_reply_elements,
                }

        return components

    def _submit_to_rml(
        self,
        template_name: str,
        credential: dict,
        processed_message: str,
        buttons: list,
        ordered_vars: List[str],
        lang_code: str,
        category: str,
    ) -> str:

        payload = {
            "template_name": template_name,
            "language": [lang_code],
            "template_type": "template",
            "template_category": self._map_category(category),
            "components": self._build_components(
                processed_message, ordered_vars, buttons
            ),
        }

        headers = self._build_headers(credential)

        resp = requests.post(
            self.RML_TEMPLATE_URL,
            headers=headers,
            json=payload,
        )

        if not resp.ok:
            raise RuntimeError(
                f"RML API error for '{template_name}': "
                f"{resp.status_code} — {resp.text}"
            )

        data = resp.json()
        return data.get("id") or data.get("template_id")

    def build_migration_record(
        self, template: dict, credential: dict, cred_id: str
    ) -> dict:

        template_name = template["template_name"]
        template_message = template["template_message"]

        ordered_vars = self._extract_ordered_variables(template_message)
        processed_message = self._process_message_variables(
            template_message, ordered_vars
        )

        lang_raw = (template.get("language") or "english").strip().capitalize()
        lang_code = WhatsAppTemplateMigrator.LANG_TO_CODE.get(lang_raw, "en")

        buttons = template.get("buttons") or []

        template_name = self._normalize_template_name(template_name)

        new_template_id = self._submit_to_rml(
            template_name,
            credential,
            processed_message,
            buttons,
            ordered_vars,
            lang_code,
            category=template.get("campaign_type", "marketing"),
        )

        return {
            "buttons": template.get("buttons"),
            "channel": "whatsapp_chat",
            "language": template.get("language", "english"),
            "template_id": new_template_id,
            "campaign_type": template.get("campaign_type"),
            "template_name": template_name,
            "template_type": template.get("template_type", "text"),
            "template_message": template_message,
            "campaign_objective_name": template.get("campaign_objective_name"),
            "template_variables": template.get("template_variables", []),
            "template_button_payloads": template.get(
                "template_button_payloads", []
            ),
            "communication_credentials_id": cred_id,
        }

    def _normalize_template_name(self, name: str) -> str:
        # Route Mobile/WhatsApp only allow lowercase alphanumerics + `_`.
        name = name.lower()
        name = re.sub(r"[^a-z0-9_]", "_", name)
        return f"{name}_{int(time.time())}"[:100]


class UniversalTemplateMigrator:
    """Provider-agnostic migrator that auto-detects the provider from the
    ``communication_credentials`` model and delegates to the correct
    concrete migrator (Airtel → ``WhatsAppTemplateMigrator``,
    RML → ``RouteMobileTemplateMigrator``).
    """

    PROVIDER_MIGRATOR_MAP = {
        "airtel": WhatsAppTemplateMigrator,
        "rml": RouteMobileTemplateMigrator,
    }

    def __init__(self, communication_credential_id: str):
        if not communication_credential_id:
            raise ValueError("communication_credential_id is required")
        self.communication_credential_id = communication_credential_id

    def _fetch_credential(self) -> dict:
        model = gryd.base_model.Model(
            "communication_credential", AUTOCRM_APP_ENTERPRISE_ID
        )
        return model.get(self.communication_credential_id)

    def _resolve_provider(self, credential: dict) -> str:
        provider = (credential.get("provider_name") or "").strip().lower()
        if not provider:
            raise ValueError(
                f"No 'provider_name' field on communication_credential "
                f"'{self.communication_credential_id}'"
            )
        return provider

    def _get_migrator(self, provider: str) -> TemplateMigratorAgent:
        migrator_cls = self.PROVIDER_MIGRATOR_MAP.get(provider)
        if migrator_cls is None:
            supported = ", ".join(sorted(self.PROVIDER_MIGRATOR_MAP))
            raise ValueError(
                f"Unsupported provider '{provider}' for credential "
                f"'{self.communication_credential_id}'. "
                f"Supported providers: {supported}"
            )
        return migrator_cls(
            communication_credential_id=self.communication_credential_id
        )

    def migrate(self, job=None) -> Dict:
        """Detect the provider and run the appropriate migrator."""
        credential = self._fetch_credential()
        if not credential:
            msg = f"No credential found for id: {self.communication_credential_id}"
            logger.error(msg)
            return {"error": msg}

        provider = self._resolve_provider(credential)
        logger.info(
            f"Resolved provider '{provider}' for credential "
            f"'{self.communication_credential_id}'"
        )

        migrator = self._get_migrator(provider)
        return migrator.migrate_templates_to_new_credential(job=job)