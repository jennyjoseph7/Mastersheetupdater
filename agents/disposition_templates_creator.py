import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple

from ai_service import ai_service_app

try:
    from .base_agent import BaseAgent, gryd
except ImportError:
    from base_agent import BaseAgent, gryd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import AUTOCRM_AGENT_SERVICE_NAME

gryd.SERVICE = AUTOCRM_AGENT_SERVICE_NAME
gryd.set_queue_manager()

from autocrm_db_helper.PGConnector import AutoCRMPGConnector

pg = AutoCRMPGConnector(enterprise_id="autocrm")

try:
    from .whatsapp_template_creator_agent import WhatsappTemplateCreatorAgent
except ImportError:
    from whatsapp_template_creator_agent import WhatsappTemplateCreatorAgent  # type: ignore

try:
    from .generic_template_migrator import (
        RouteMobileTemplateMigrator,
        WhatsAppTemplateMigrator,
    )
except ImportError:
    from generic_template_migrator import (  # type: ignore
        RouteMobileTemplateMigrator,
        WhatsAppTemplateMigrator,
    )

AUTOCRM_APP_ENTERPRISE_ID = os.environ.get("AUTOCRM_APP_ENTERPRISE_ID", "autocrm")


def _slugify(text: str) -> str:
    """'Follow Up Required' → 'follow-up-required' (lowercased, hyphenated)."""
    return re.sub(r"[\s_]+", "-", (text or "").strip().lower())


# Purpose prefixes shared across grouped "engaged" disposition cases. Each prefix
# tells the WhatsApp template generator how to frame the follow-up message.

# Type 1 — a simple follow-up reminder (another variation of the standard nudge).
_FOLLOW_UP_REQUIRED_PURPOSE = (
    "Follow-up reminder WhatsApp template: the customer was engaged in a previous "
    "conversation and an explicit follow-up was requested. Write a fresh variation of "
    "the standard campaign follow-up that re-engages the customer and gently nudges "
    "them towards the campaign objective, using ONLY the placeholders provided. Keep it "
    "warm and concise — this is a reminder, not a first-time outreach."
)

# Type 2 — we attempted a call but could not complete it (audio/connection issues,
# they asked to be called back, wanted a human, or said they'd visit on their own).
_TRIED_TO_REACH_PURPOSE = (
    "Missed-contact WhatsApp template: we recently tried to reach the customer on a "
    "call but could not complete the conversation (for example audio/connection "
    "problems, they asked to be called back, wanted to talk to a human, or said they "
    "would visit the showroom themselves). Write a polite message acknowledging that we "
    "tried to call but could not connect to take this forward, and invite them to "
    "continue over WhatsApp or take the next step towards the campaign objective, using "
    "ONLY the placeholders provided. Do not blame the customer for the missed call."
)

# Type 3 — the customer asked for time to decide; some time has now passed and we are
# checking back in. Must NOT name the campaign objective explicitly in the message.
_DECISION_TIMEFRAME_PURPOSE = (
    "Decision follow-up WhatsApp template: the customer was engaged earlier and asked "
    "for time to decide, and that time has now passed since our last contact. Write a "
    "courteous, marketing-style follow-up that references that we connected with them a "
    "while ago and confidently invites them to take the next step now. IMPORTANT: do NOT "
    "mention or name the campaign objective explicitly in the message, and do NOT phrase "
    "it as a yes/no question — prompt the action directly in a warm, benefit-led way "
    "(e.g. 'Now is a great time to move forward, let us help you get started!'). Use "
    "ONLY the placeholders provided."
)

# disposition_details values that all map to the "we tried to reach you" framing.
_TRIED_TO_REACH_TAGS = [
    "Audio Issue",
    "Call Quality Issue",
    "Connection Issue",
    "Will call showroom themselves",
    "Requested Callback",
    "Talk to Human",
]

# disposition_details values that all map to the "decide later" framing.
_DECISION_TIMEFRAME_TAGS = [
    "Will decide tomorrow",
    "Will decide within 1 to 3 days",
    "Will decide within 4 to 7 days",
    "Will decide within 8 to 14 days",
    "Will decide within 15 to 30 days",
    "Will decide within 31 to 60 days",
    "Will decide within 61 to 90 days",
    "Will decide after 90 days",
]

# Known disposition cases with specialized handling. Anything not listed here is
# still supported: templates are generated generically from the input
# disposition / disposition_details.
KNOWN_DISPOSITION_CASES = {
    "language-barrier": {
        "expected_disposition": "engaged",
        "purpose_prefix": (
            "Language-barrier follow-up: translate existing approved campaign templates "
            "into the customer's requested language while preserving placeholders and intent."
        ),
    },
    "converted": {
        "expected_disposition": "converted",
        "purpose_prefix": (
            "Post-conversion WhatsApp template: the customer has ALREADY completed the "
            "campaign purpose. Write a confirmation / next-steps message relevant to this "
            "campaign objective after conversion — thank them, confirm what was completed, "
            "and share practical follow-up details (visit, test drive, service booking, etc.) "
            "using ONLY the placeholders provided. Do not ask them to complete the purpose again."
        ),
    },
    "follow-up-required": {
        "expected_disposition": "engaged",
        "purpose_prefix": _FOLLOW_UP_REQUIRED_PURPOSE,
    },
}


def _register_engaged_cases(tags: List[str], purpose_prefix: str) -> None:
    """Register many disposition_details values that share one purpose prefix."""
    for tag in tags:
        KNOWN_DISPOSITION_CASES[_slugify(tag)] = {
            "expected_disposition": "engaged",
            "purpose_prefix": purpose_prefix,
        }


_register_engaged_cases(_TRIED_TO_REACH_TAGS, _TRIED_TO_REACH_PURPOSE)
_register_engaged_cases(_DECISION_TIMEFRAME_TAGS, _DECISION_TIMEFRAME_PURPOSE)

PROVIDER_MIGRATORS = {
    "airtel": WhatsAppTemplateMigrator,
    "rml": RouteMobileTemplateMigrator,
}

# Post-conversion templates: one template per variable set (per language).
CONVERTED_VARIABLE_SETS = [
    ["pincode"],
    ["dealership_name", "address"],
    ["date"],
    ["date", "time"],
    ["dealership_name", "address", "date"],
    ["dealership_name", "address", "date", "time"],
]

# RML requires sample/example values in components.body.example (not raw var names).
RML_VARIABLE_EXAMPLES = {
    # Converted disposition variables
    "pincode": "560001",
    "dealership_name": "Citroen Experience Centre Indiranagar",
    "address": "100 MG Road, Indiranagar, Bangalore, Karnataka",
    "date": "30 May 2026",
    "time": "11:00 AM",
    # Language-barrier / lead attributes 
    "person_name": "Rahul Sharma",
    "name": "Rahul Sharma",
    "reg_number": "KA01AB1234",
    "car_model": "Aircross",
    "vehicle_model": "Aircross",
    "service_due_date": "15 Jun 2026",
    "workshop_name": "Elite Auto Care",
    "dealer_name": "Stellantis India",
    "campaign_offer": "Test drive confirmed with exclusive benefits",
    "warranty_expiry_date": "31 Dec 2026",
    "nearest_dealership": "Citroen Downtown Bangalore",
    "offer_details": "Complimentary accessories worth Rs 15,000",
    "offer_validity": "30 Jun 2026",
}


class DispositionTemplatesCreator(BaseAgent):
    """
    Creates WhatsApp disposition templates, submits them for provider approval
    (Airtel or RML), and posts to the template model.

    The disposition and disposition_details are taken from the input and stored
    as-is on each posted template record, so any disposition case can be handled:

    - Language barrier: fetches all approved base campaign templates (any language),
      translates each to every target language in ``languages``, then approves and posts.

    - Converted: for each language, creates 6 templates (one per variable set):
        pincode | dealership_name+address | date | date+time |
        dealership_name+address+date | dealership_name+address+date+time

    - Any other disposition (e.g. "not interested - price concern"): for each
      language, generates a follow-up template tailored to the input disposition
      details using the campaign objective's attributes.

    Input source:
        - campaign_objective_id (required)
        - disposition (required)
        - disposition_details (required)
        - dealership_id (required)
        - languages (required) — target languages to translate into; no defaults
        - communication_credential_id (optional) — resolved from dealership if omitted
    """

    MODEL_IDENTIFIER = "databricks-gpt-5.5"

    def __init__(self, source, *args, **kwargs):
        super().__init__(**kwargs)

        if not source or not isinstance(source, dict):
            raise ValueError("source must be a non-empty dictionary")

        self.source = source
        self.campaign_objective_id = source.get("campaign_objective_id", "")
        if not self.campaign_objective_id:
            raise ValueError("campaign_objective_id is required in source")

        raw_details = source.get("disposition_details")
        if not raw_details:
            raise ValueError("disposition_details is required in source")
        self.disposition_tag, self.disposition_description = self._parse_disposition_details(
            raw_details
        )

        self.disposition = (source.get("disposition") or "").strip().lower()
        if not self.disposition:
            raise ValueError("disposition is required in source")

        self.dealership_id = source.get("dealership_id", "")
        if not self.dealership_id:
            raise ValueError("dealership_id is required in source")

        self.languages = self._require_languages(source.get("languages"))
        self.communication_credential_id = source.get("communication_credential_id", "")
        # Optional: attributes actually present on the lead (from
        # data_attribute_retriever). When provided, generated templates only use
        # variables that exist on the lead — never a variable the lead lacks.
        self.lead_attributes = self._normalize_lead_attributes(
            source.get("lead_attributes")
        )
        self.logger = kwargs.get("logger") or gryd.hp.get_logger(__name__)

        self._validate_supported_disposition()

    @staticmethod
    def _normalize_lead_attributes(value) -> List[str]:
        """Flatten lead attributes (flat list, list-of-lists, or string) to a
        de-duplicated ordered list of attribute names."""
        if not value:
            return []
        flattened: List[str] = []
        if isinstance(value, str):
            flattened.append(value.strip())
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, (list, tuple)):
                    flattened.extend(str(v).strip() for v in item if str(v).strip())
                elif str(item).strip():
                    flattened.append(str(item).strip())
        seen: set = set()
        return [a for a in flattened if a and not (a in seen or seen.add(a))]

    def _constrain_to_lead(self, attribute_names: List[str]) -> List[str]:
        """Drop any attribute the lead doesn't have. No-op when lead attributes
        were not supplied (e.g. bulk creation without a specific lead)."""
        if not self.lead_attributes:
            return list(attribute_names)
        return [a for a in attribute_names if a in self.lead_attributes]

    @staticmethod
    def _require_languages(languages) -> List[str]:
        if isinstance(languages, str) and languages.strip():
            return [languages.strip()]
        if isinstance(languages, list):
            normalized = [str(lang).strip() for lang in languages if str(lang).strip()]
            if normalized:
                return normalized
        raise ValueError(
            "languages is required and must be a non-empty string or list of languages"
        )

    @staticmethod
    def _parse_disposition_details(raw_details) -> Tuple[str, str]:
        if isinstance(raw_details, str):
            return raw_details.strip(), raw_details.strip()

        if isinstance(raw_details, (list, tuple)) and raw_details:
            first = raw_details[0]
            if isinstance(first, (list, tuple)) and len(first) >= 2:
                return str(first[0]).strip(), str(first[1]).strip()
            if isinstance(first, dict):
                return (
                    str(first.get("tag") or first.get("disposition_detail") or "").strip(),
                    str(first.get("details") or first.get("description") or "").strip(),
                )
            tag = str(first).strip()
            description = (
                str(raw_details[1]).strip() if len(raw_details) > 1 else tag
            )
            return tag, description

        raise ValueError(
            "disposition_details must be a non-empty string, list, or (tag, description) pair"
        )

    def _validate_supported_disposition(self):
        key = self._slugify(self.disposition_tag)
        case = KNOWN_DISPOSITION_CASES.get(key)
        if not case:
            self.logger.info(
                f"disposition_details '{self.disposition_tag}' has no specialized "
                f"handling; templates will be generated generically from the input"
            )
            return

        expected = case["expected_disposition"]
        if self.disposition != expected:
            self.logger.warning(
                f"disposition '{self.disposition}' does not match typical value "
                f"'{expected}' for '{self.disposition_tag}'"
            )

    def _get_disposition_record_fields(self) -> Dict[str, Any]:
        """Disposition values (from input) stored on each posted template record.

        disposition is stored lowercased and disposition_details is stored
        slugified (e.g. "will-call-themself") so retrieval/matching
        (get_disposition_template_agent and the other get_*_template agents,
        which all query with a slugified disposition_details) lines up.
        """
        return {
            "disposition": self.disposition,
            "disposition_details": self._slugify(self.disposition_description),
            "disposition_tags": [
                self.disposition,
                self._slugify(self.disposition_tag),
            ],
        }

    @staticmethod
    def _slugify(text: str) -> str:
        return _slugify(text)

    @staticmethod
    def _variable_set_slug(attribute_names: List[str]) -> str:
        return "-".join(attribute_names)

    @staticmethod
    def _sanitize_template_name_part(name: str) -> str:
        """Lowercase alphanumerics + underscores only (RML/WhatsApp constraint)."""
        cleaned = name.lower().strip()
        cleaned = re.sub(r"[\s-]+", "_", cleaned)
        return re.sub(r"[^a-z0-9_]", "_", cleaned)

    @staticmethod
    def _build_template_name(
        provider: str,
        base_name: str,
        disposition_slug: str,
        name_suffix: str = "",
    ) -> str:
        """Build provider-specific template names before approval.

        Airtel: descriptive name with disposition slug (hyphens ok), e.g.
            autobot_service_reminder_language-barrier_pincode

        RML: short underscore-only base name; disposition is stored in
        disposition_tags / disposition_details. Uniqueness is added later by
        RouteMobileTemplateMigrator._normalize_template_name (timestamp suffix),
        same as agents.whatsapp_template_agents.post_rml_templates.post_rml_template_for_approval.
        """
        base = DispositionTemplatesCreator._sanitize_template_name_part(
            base_name or "autobot_disposition_template"
        )
        if provider == "rml":
            var_part = DispositionTemplatesCreator._sanitize_template_name_part(
                name_suffix.replace("-", "_")
            )
            return "_".join(part for part in (base, var_part) if part)
        parts = [base, disposition_slug]
        if name_suffix:
            parts.append(name_suffix)
        return "_".join(parts)

    @staticmethod
    def _generate_rml_example_values(ordered_vars: List[str]) -> List[str]:
        """Sample values for RML template approval (one per {{var}} in order)."""
        examples = []
        for var in ordered_vars:
            if var in RML_VARIABLE_EXAMPLES:
                examples.append(RML_VARIABLE_EXAMPLES[var])
            else:
                # Never send the raw placeholder name to RML
                examples.append(f"Sample {var.replace('_', ' ').title()}")
        return examples

    def fetch_campaign_objective(self) -> dict:
        try:
            model = gryd.base_model.Model("campaign_objective", AUTOCRM_APP_ENTERPRISE_ID)
            record = model.get(self.campaign_objective_id)
            if record:
                return record
        except Exception as e:
            self.logger.warning(f"Gryd model fetch failed, trying PG: {e}")

        records = pg.get(
            "campaign_objective",
            "campaign_objective_id",
            self.campaign_objective_id,
        )
        if not records:
            raise ValueError(
                f"Campaign objective not found for id: {self.campaign_objective_id}"
            )
        return records[0] if isinstance(records, list) else records

    def fetch_communication_credential(self) -> dict:
        if self.communication_credential_id:
            cred = gryd.base_model.Model(
                "communication_credential", AUTOCRM_APP_ENTERPRISE_ID
            ).get(self.communication_credential_id)
            if cred:
                return cred
            raise ValueError(
                f"communication_credential not found: {self.communication_credential_id}"
            )

        records = list(
            pg.list(
                table_name="communication_credential",
                where={
                    "dealership_id": self.dealership_id,
                    "channel": "whatsapp_chat",
                },
            )
        )
        if not records:
            raise ValueError(
                f"No whatsapp_chat credential for dealership_id={self.dealership_id}"
            )
        return records[0]

    @staticmethod
    def _resolve_provider(credential: dict) -> str:
        provider = (credential.get("provider_name") or "").strip().lower()
        if provider not in PROVIDER_MIGRATORS:
            supported = ", ".join(sorted(PROVIDER_MIGRATORS))
            raise ValueError(
                f"Unsupported provider '{credential.get('provider_name')}'. "
                f"Supported: {supported}"
            )
        return provider

    def _fetch_source_campaign_templates(
        self,
        campaign_objective: dict,
        credential: dict,
    ) -> List[dict]:
        """
        Fetch all approved base WhatsApp templates for the campaign objective
        (same filters as get_whatsapp_template_agent.pick_from_model, non-disposition).
        """
        cred_id = credential.get("communication_credentials_id")
        campaign_type = campaign_objective.get("campaign_type", "")
        campaign_objective_name = campaign_objective.get("campaign_objective_name", "")

        records = list(
            pg.list(
                table_name="template",
                where={
                    "campaign_type": campaign_type,
                    "campaign_objective_name": campaign_objective_name,
                    "channel": "whatsapp_chat",
                    "status": "approved",
                    "communication_credentials_id": cred_id,
                },
            )
        )

        base_templates = [
            t
            for t in records
            if not t.get("disposition") and not t.get("disposition_details")
        ]
        self.logger.info(
            f"Found {len(base_templates)} base templates to translate "
            f"(from {len(records)} approved)"
        )
        return base_templates

    @staticmethod
    def _normalize_template_variables(tpl_vars: Any) -> List[str]:
        if isinstance(tpl_vars, list):
            return tpl_vars
        if isinstance(tpl_vars, str):
            if tpl_vars.startswith("{") and tpl_vars.endswith("}"):
                return [v.strip() for v in tpl_vars.strip("{}").split(",") if v.strip()]
            try:
                parsed = json.loads(tpl_vars)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        return []

    @staticmethod
    def _parse_json_llm_response(text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        raise ValueError("LLM response did not contain valid JSON")

    def _translate_template_content(
        self, source_template: dict, target_language: str
    ) -> Dict:
        language = (source_template.get("language") or "english").strip().lower()
        buttons = source_template.get("buttons") or []
        button_texts = [
            btn.get("text") or btn.get("buttonText") or "" for btn in buttons
        ]

        payload = {
            "template_message": source_template.get("template_message", ""),
            "button_texts": button_texts,
        }

        system_prompt = f"""You are a professional translation engine for WhatsApp marketing templates.

Translate ONLY the template body and CTA button labels from {language} to colloquial {target_language}.

Rules:
1. Return a single JSON object with keys: "template_message", "button_texts" only.
2. Translate nothing else — no template names, payloads, or metadata.
3. Keep every {{{{variable_name}}}} placeholder exactly unchanged (same names, double braces).
4. Do not translate text inside double curly braces.
5. Do not translate URLs, phone numbers, brand/model names, or dealership names.
6. button_texts must be the same length as input; translate each CTA label only.
7. Output JSON only — no markdown fences or commentary.
8. You must provide appropriate nextline (\n) characters for proper whatsapp message structure. 
    Eg: < Hi {{person_name}},\nYour test drive is confirmed.\nVisit us at {{dealership_name}} on {{date}}. Thank you! >
9. Keep CTA character count under 20. This is a must follow rule for translation."""

        user_prompt = f"""Translate this template content to {target_language}:

{json.dumps(payload, ensure_ascii=False, indent=2)}"""

        response = ai_service_app.get_llm_response(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model_identifier="databricks-gpt-5.5",
            temperature = 1
        )
        translated = self._parse_json_llm_response(response)

        return {
            "template_message": translated.get(
                "template_message", payload["template_message"]
            ),
            "button_texts": translated.get("button_texts") or button_texts,
        }

    @staticmethod
    def _merge_translated_button_labels(
        source_buttons: List[dict], translated_labels: List[str]
    ) -> List[dict]:
        """Keep button structure/types/payloads; only replace visible CTA text."""
        merged = []
        for idx, btn in enumerate(source_buttons or []):
            out = dict(btn)
            if idx < len(translated_labels) and translated_labels[idx]:
                label = translated_labels[idx]
                if "text" in out:
                    out["text"] = label
                if "buttonText" in out:
                    out["buttonText"] = label
            merged.append(out)
        return merged

    _TEMPLATE_COPY_SKIP_KEYS = frozenset(
        {"template_id", "created", "updated", "status", "_id", "_rev"}
    )

    def _build_translated_template_record(
        self,
        source_template: dict,
        translated: dict,
        target_language: str,
    ) -> dict:
        """Copy source template as-is; only message, button labels, and language change."""
        template = {
            k: v
            for k, v in source_template.items()
            if k not in self._TEMPLATE_COPY_SKIP_KEYS
        }
        template["template_message"] = translated["template_message"]
        template["buttons"] = self._merge_translated_button_labels(
            source_template.get("buttons") or [],
            translated.get("button_texts") or [],
        )
        template["language"] = target_language.lower()
        template.update(self._get_disposition_record_fields())
        # template_name, template_button_payloads, template_variables, lead_tags, etc. unchanged
        return template

    def _translate_approve_and_post(
        self,
        source_template: dict,
        target_language: str,
        campaign_objective: dict,
        credential: dict,
    ) -> dict:
        translated = self._translate_template_content(source_template, target_language)
        template = self._build_translated_template_record(
            source_template, translated, target_language
        )

        approval = self.submit_template_for_approval(template, credential)
        if not approval.get("success"):
            raise RuntimeError(
                f"Approval failed for '{source_template.get('template_name')}' "
                f"→ {target_language}: {approval.get('error')}"
            )

        db_record = self.post_template_to_model(
            template,
            approval,
            credential,
            campaign_objective,
            preserve_source_variables=True,
        )

        source_variables = self._normalize_template_variables(
            source_template.get("template_variables")
        )

        return {
            **template,
            "template_id": approval["template_id"],
            "template_variables": source_variables,
            "communication_credentials_id": credential.get("communication_credentials_id"),
            "provider_name": credential.get("provider_name"),
            "record": db_record,
        }

    def _get_template_attributes(self, campaign_objective: dict) -> list:
        required = campaign_objective.get("required_attributes") or []
        if required:
            return list(required)

        audience_attrs = campaign_objective.get("audience_attributes") or []
        names = [
            a.get("attribute_name")
            for a in audience_attrs
            if isinstance(a, dict) and a.get("attribute_name")
        ]
        if names:
            return names

        return ["person_name"]

    @staticmethod
    def _format_ctas(ctas: list) -> list:
        if not ctas:
            return ["Request a Call Back"]
        formatted = []
        for cta in ctas:
            if not cta:
                continue
            label = str(cta).replace("-", " ").replace("_", " ").strip()
            formatted.append(label.title())
        if not any("call back" in c.lower() for c in formatted):
            formatted.append("Request a Call Back")
        return formatted[:3]

    def _build_objective_context(self, campaign_objective: dict) -> List[str]:
        purpose_steps = campaign_objective.get("purpose_steps") or []
        steps_text = "\n".join(f"- {s}" for s in purpose_steps) if purpose_steps else ""

        parts = [
            f"Campaign objective: {campaign_objective.get('campaign_objective_name', '')}.",
            f"Description: {campaign_objective.get('campaign_objective_description', '')}.",
            f"Purpose: {campaign_objective.get('purpose', '')}.",
        ]
        if steps_text:
            parts.append(f"Purpose steps (already completed by customer):\n{steps_text}")
        if campaign_objective.get("why_user_should_avail_this"):
            parts.append(
                f"Why user should avail: {campaign_objective['why_user_should_avail_this']}"
            )
        if campaign_objective.get("guardrails_guidelines"):
            parts.append(
                f"Guardrails: {campaign_objective['guardrails_guidelines']}"
            )
        return parts

    def _build_template_purpose(
        self,
        campaign_objective: dict,
        language: str,
        attribute_names: List[str],
    ) -> str:
        key = self._slugify(self.disposition_tag)
        case = KNOWN_DISPOSITION_CASES.get(key)
        placeholders = ", ".join(f"{{{{{a}}}}}" for a in attribute_names)

        purpose_prefix = (
            case["purpose_prefix"]
            if case
            else (
                f"Disposition follow-up WhatsApp template: the customer's last "
                f"interaction ended with disposition '{self.disposition}' "
                f"({self.disposition_description}). Write a follow-up message that "
                f"directly addresses this outcome and nudges the customer towards "
                f"the campaign objective, using ONLY the placeholders provided."
            )
        )
        context_parts = [purpose_prefix, *self._build_objective_context(campaign_objective)]

        if key == "converted":
            context_parts.append(
                f"Use ONLY these placeholders in template_text (all required, no extras): "
                f"{placeholders}."
            )
            context_parts.append(
                "Message must be post-conversion: confirm completion, share next-step "
                "details naturally (nearest dealership, scheduled date/time, pincode area, etc.) "
                "based on which placeholders are available."
            )
        else:
            context_parts.append(
                f"Use ONLY these placeholders in template_text: {placeholders}."
            )
            context_parts.append(
                "These are follow-up WhatsApp templates for previously reached customers."
            )

        context_parts.append(
            f"Write the entire template_text in colloquial {language} only. "
            f"Disposition: '{self.disposition_tag}' — {self.disposition_description}."
        )
        return " ".join(context_parts)

    def _build_whatsapp_agent_source(
        self, campaign_objective: dict, attribute_names: list, language: str
    ) -> dict:
        return {
            "campaign_type": campaign_objective.get("campaign_type", ""),
            "campaign_objective": campaign_objective.get("campaign_objective_name", ""),
            "dealership_id": self.dealership_id,
            "languages": [language],
            "cta_buttons": self._format_ctas(campaign_objective.get("ctas") or []),
            "data": {
                "purpose": self._build_template_purpose(
                    campaign_objective, language, attribute_names
                ),
                "attribute_name": attribute_names,
                "disposition": self.disposition,
                "disposition_tag": self.disposition_tag,
                "disposition_details": self.disposition_description,
                "campaign_objective_description": campaign_objective.get(
                    "campaign_objective_description", ""
                ),
                "purpose_steps": campaign_objective.get("purpose_steps", []),
                "campaign_purpose": campaign_objective.get("purpose", ""),
            },
        }

    @staticmethod
    def _standard_buttons(template_data: dict) -> list:
        return [
            {
                "type": btn.get("type", "QUICK_REPLY"),
                "buttonText": btn.get("buttonText") or btn.get("text"),
            }
            for btn in (template_data.get("buttons") or [])
        ]

    def _submit_airtel_for_approval(
        self,
        template_data: dict,
        credential: dict,
        cred_id: str,
    ) -> Dict:
        migrator = WhatsAppTemplateMigrator(communication_credential_id=cred_id)
        template_name = template_data["template_name"]
        template_message = template_data["template_message"]
        ordered_vars = migrator._extract_ordered_variables(template_message)
        processed_message = migrator._process_message_variables(
            template_message, ordered_vars
        )
        buttons = self._standard_buttons(template_data)

        lang_raw = (template_data.get("language") or "").strip().capitalize()
        lang_code = WhatsAppTemplateMigrator.LANG_TO_CODE.get(lang_raw, "en")

        template_id = migrator._submit_for_approval(
            template_name,
            credential,
            processed_message,
            buttons,
            ordered_vars,
            lang_code,
        )
        return {
            "success": True,
            "template_id": template_id,
            "template_variables": ordered_vars,
            "template_name": template_name,
        }

    def _submit_rml_for_approval(
        self,
        template_data: dict,
        credential: dict,
        cred_id: str,
    ) -> Dict:
        migrator = RouteMobileTemplateMigrator(communication_credential_id=cred_id)
        template_message = template_data["template_message"]
        ordered_vars = migrator._extract_ordered_variables(template_message)
        processed_message = migrator._process_message_variables(
            template_message, ordered_vars
        )
        buttons = template_data.get("buttons") or []
        rml_examples = self._generate_rml_example_values(ordered_vars)

        # RML body.example must be real sample strings, not placeholder names.
        migrator._generate_example_values = lambda ovs: self._generate_rml_example_values(ovs)

        lang_raw = (template_data.get("language") or "").strip().capitalize()
        lang_code = WhatsAppTemplateMigrator.LANG_TO_CODE.get(lang_raw, "en")

        normalized_name = migrator._normalize_template_name(template_data["template_name"])
        self.logger.info(
            f"RML submit '{normalized_name}' | vars={ordered_vars} | examples={rml_examples}"
        )
        template_id = migrator._submit_to_rml(
            normalized_name,
            credential,
            processed_message,
            buttons,
            ordered_vars,
            lang_code,
            category=template_data.get("campaign_type", "marketing"),
        )
        if not template_id:
            return {
                "success": False,
                "error": "RML approval response did not include a template id",
            }
        return {
            "success": True,
            "template_id": template_id,
            "template_variables": ordered_vars,
            "template_name": normalized_name,
            "rml_sample_variables": rml_examples,
        }

    def submit_template_for_approval(
        self, template_data: dict, credential: dict
    ) -> Dict:
        cred_id = credential.get("communication_credentials_id") or self.communication_credential_id
        if not cred_id:
            return {"success": False, "error": "communication_credentials_id missing"}

        provider = self._resolve_provider(credential)
        try:
            if provider == "airtel":
                return self._submit_airtel_for_approval(template_data, credential, cred_id)
            return self._submit_rml_for_approval(template_data, credential, cred_id)
        except Exception as e:
            self.logger.error(f"{provider} approval failed: {e}")
            return {"success": False, "error": str(e)}

    def post_template_to_model(
        self,
        template_data: dict,
        approval: dict,
        credential: dict,
        campaign_objective: dict,
        preserve_source_variables: bool = False,
    ) -> dict:
        cred_id = credential.get("communication_credentials_id")
        provider = self._resolve_provider(credential)
        template_name = approval.get("template_name", template_data["template_name"])

        if preserve_source_variables:
            # Translation: keep EXACTLY the source template's variables (even if
            # the source list is empty) — the translated message preserves the
            # same {{vars}}, neither more nor fewer.
            template_variables = self._normalize_template_variables(
                template_data.get("template_variables") or []
            )
            # RML stores the normalized name (with timestamp suffix) from approval;
            # Airtel keeps the descriptive source template name.
            if provider != "rml":
                template_name = template_data["template_name"]
        else:
            # New creation: WhatsappTemplateCreatorAgent doesn't carry a
            # template_variables key, so store the placeholders actually present
            # in the generated message (extracted during approval). Otherwise the
            # record would store an empty list even though {{vars}} exist,
            # breaking variable-based retrieval matching.
            template_variables = approval.get("template_variables") or []

        campaign_objective_value = template_data.get("campaign_objective")
        if not campaign_objective_value:
            campaign_objective_value = [
                campaign_objective.get("campaign_objective_name", "")
            ]

        record = {
            "template_id": approval["template_id"],
            "communication_credentials_id": cred_id,
            "channel": template_data.get("channel", "whatsapp_chat"),
            "status": "pending",
            "language": template_data.get("language").lower(),
            "template_name": template_name,
            "template_type": template_data.get("template_type", "text"),
            "template_message": template_data["template_message"],
            "template_variables": template_variables,
            "buttons": template_data.get("buttons"),
            "template_button_payloads": template_data.get("template_button_payloads"),
            "campaign_type": template_data.get("campaign_type")
            or campaign_objective.get("campaign_type"),
            "campaign_objective": campaign_objective_value,
            "campaign_objective_name": template_data.get("campaign_objective_name")
            or campaign_objective.get("campaign_objective_name", ""),
            "dealership_id": template_data.get("dealership_id") or self.dealership_id,
            **self._get_disposition_record_fields(),
            "lead_tags": template_data.get("lead_tags", []),
            "provider_name": credential.get("provider_name"),
        }

        gryd.base_model.Model("template", AUTOCRM_APP_ENTERPRISE_ID).post(record)
        self.logger.info(
            f"Posted template '{record['template_name']}' | id={record['template_id']}"
        )
        return record

    def _generate_approve_and_post(
        self,
        campaign_objective: dict,
        credential: dict,
        attribute_names: List[str],
        language: str,
        name_slug: str,
        name_suffix: str,
    ) -> dict:
        agent = WhatsappTemplateCreatorAgent(
            source=self._build_whatsapp_agent_source(
                campaign_objective, attribute_names, language
            ),
            logger=self.logger,
        )
        template = agent.run()

        provider = self._resolve_provider(credential)
        template["template_name"] = self._build_template_name(
            provider,
            template.get("template_name") or "autobot_disposition_template",
            name_slug,
            name_suffix,
        )
        template["language"] = language.lower()
        template["campaign_type"] = campaign_objective.get("campaign_type", "")
        template["dealership_id"] = self.dealership_id
        template["attributes_used"] = attribute_names

        approval = self.submit_template_for_approval(template, credential)
        if not approval.get("success"):
            raise RuntimeError(
                f"Template approval failed | language={language} | "
                f"vars={attribute_names} | error={approval.get('error')}"
            )

        db_record = self.post_template_to_model(
            template, approval, credential, campaign_objective
        )

        return {
            **template,
            "template_id": approval["template_id"],
            "template_variables": approval["template_variables"],
            "communication_credentials_id": credential.get(
                "communication_credentials_id"
            ),
            "provider_name": credential.get("provider_name"),
            "record": db_record,
        }

    def _get_variable_sets(self, campaign_objective: dict) -> List[List[str]]:
        """Variable sets to generate templates for, based on the disposition.

        Each set is constrained to the lead's attributes (when supplied) so a
        generated template never references a variable the lead doesn't have.
        """
        if self._slugify(self.disposition_tag) == "converted":
            sets = CONVERTED_VARIABLE_SETS
        else:
            sets = [self._get_template_attributes(campaign_objective)]
        return [self._constrain_to_lead(s) for s in sets]

    def _create_generated_templates(
        self,
        campaign_objective: dict,
        credential: dict,
        name_slug: str,
    ) -> List[dict]:
        results = []
        for language in self.languages:
            for attribute_names in self._get_variable_sets(campaign_objective):
                var_slug = self._variable_set_slug(attribute_names)
                self.logger.info(
                    f"Generating '{self.disposition_tag}' template | "
                    f"language={language} | variables={attribute_names}"
                )
                results.append(
                    self._generate_approve_and_post(
                        campaign_objective,
                        credential,
                        attribute_names,
                        language,
                        name_slug,
                        var_slug,
                    )
                )
        return results

    def _create_language_barrier_templates(
        self,
        campaign_objective: dict,
        credential: dict,
    ) -> List[dict]:
        source_templates = self._fetch_source_campaign_templates(
            campaign_objective, credential
        )
        if not source_templates:
            raise ValueError(
                f"No approved base templates found for campaign_type="
                f"'{campaign_objective.get('campaign_type')}', "
                f"campaign_objective_name="
                f"'{campaign_objective.get('campaign_objective_name')}'"
            )

        results = []
        for target_language in self.languages:
            for source_template in source_templates:
                language = (source_template.get("language") or "english").strip().lower()
                if target_language.lower() == language:
                    self.logger.warning(
                        f"Skipping target language '{target_language}' — same as "
                        f"template language for '{source_template.get('template_name')}'"
                    )
                    continue

                self.logger.info(
                    f"Translating template '{source_template.get('template_name')}' "
                    f"| {language} → {target_language}"
                )
                results.append(
                    self._translate_approve_and_post(
                        source_template,
                        target_language,
                        campaign_objective,
                        credential,
                    )
                )
        return results

    def _create_follow_up_required_templates(
        self,
        campaign_objective: dict,
        credential: dict,
    ) -> List[dict]:
        """
        Follow-up-required: for EVERY approved base template of this campaign
        objective (regardless of its variable set), generate another follow-up
        version using that template's own variables. This guarantees the
        disposition set covers the same variable combinations as the base
        templates; get_disposition_template_agent later returns only the single
        version whose variables best match the lead at retrieval time.
        """
        source_templates = self._fetch_source_campaign_templates(
            campaign_objective, credential
        )
        if not source_templates:
            raise ValueError(
                f"No approved base templates found for campaign_type="
                f"'{campaign_objective.get('campaign_type')}', "
                f"campaign_objective_name="
                f"'{campaign_objective.get('campaign_objective_name')}'"
            )

        name_slug = self._slugify(self.disposition_description)
        results = []
        for language in self.languages:
            for index, source_template in enumerate(source_templates):
                attribute_names = self._constrain_to_lead(
                    self._normalize_template_variables(
                        source_template.get("template_variables")
                    )
                )
                var_slug = self._variable_set_slug(attribute_names) or "no_vars"
                name_suffix = f"{var_slug}_v{index + 1}"
                self.logger.info(
                    f"Generating 'follow-up-required' version of "
                    f"'{source_template.get('template_name')}' | "
                    f"language={language} | variables={attribute_names}"
                )
                results.append(
                    self._generate_approve_and_post(
                        campaign_objective,
                        credential,
                        attribute_names,
                        language,
                        name_slug,
                        name_suffix,
                    )
                )
        return results

    def create_disposition_templates(self) -> List[dict]:
        campaign_objective = self.fetch_campaign_objective()
        credential = self.fetch_communication_credential()
        self.communication_credential_id = credential.get("communication_credentials_id", "")

        disposition_key = self._slugify(self.disposition_tag)
        disposition_fields = self._get_disposition_record_fields()

        self.logger.info(
            f"Loaded objective '{campaign_objective.get('campaign_objective_name')}' | "
            f"provider={credential.get('provider_name')} | "
            f"target_languages={self.languages} | "
            f"disposition={disposition_fields['disposition']} | "
            f"disposition_details={disposition_fields['disposition_details']}"
        )

        if disposition_key == "language-barrier":
            return self._create_language_barrier_templates(
                campaign_objective, credential
            )
        if disposition_key == "follow-up-required":
            return self._create_follow_up_required_templates(
                campaign_objective, credential
            )
        return self._create_generated_templates(
            campaign_objective,
            credential,
            self._slugify(disposition_fields["disposition_details"]),
        )

    def _enqueue_approval_status_poll(self, results: List[dict]) -> None:
        template_ids = [
            result.get("template_id")
            for result in (results or [])
            if isinstance(result, dict) and result.get("template_id")
        ]
        if not template_ids:
            return

        cred_id = self.communication_credential_id
        if not cred_id:
            self.logger.warning(
                "No communication_credential_id; skipping approval status poll"
            )
            return

        try:
            gryd.await_result(
                task = "update_disposition_template_approval",
                service = AUTOCRM_AGENT_SERVICE_NAME,
                kwargs={
                    "template_ids": template_ids,
                    "communication_credentials_id": cred_id,
                },
                gryd_logger=self.logger,
            )
            self.logger.info(
                f"Enqueued approval status poll for {len(template_ids)} template(s)"
            )
        except Exception as e:
            self.logger.error(f"Failed to enqueue approval status poll: {e}")

    def run(self):
        results = self.create_disposition_templates()
        self._enqueue_approval_status_poll(results)
        return results


#EXAMPLE PAYLOAD:
# {
#     "campaign_objective_id": "<>",
#     "disposition": "<>",
#     "disposition_details": "<>",
#     "dealership_id": "<>",
#     "languages": "[<>,<>,<>,<>,<>,<>]"
# }
@gryd.is_a_task("create_disposition_templates", logger_param="logger", job_param="job")
def create_disposition_templates(source=None, logger=None, job=None, **kwargs):
    logger = logger or gryd.hp.get_logger(__name__)
    logger.info("Starting disposition templates creation...")

    try:
        payload = source or kwargs.get("source") or kwargs
        if not isinstance(payload, dict):
            raise ValueError("source must be a dictionary")

        agent = DispositionTemplatesCreator(source=payload, logger=logger)
        return agent.run()

    except Exception as e:
        logger.error(f"Disposition template creation failed: {e}")
        raise