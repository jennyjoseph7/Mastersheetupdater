import os
import sys
from os.path import dirname, abspath, join as joinpath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from config import AutocrmModel, clogger, AUTOCRM_APP_ENTERPRISE_ID, AUTOCRM_COMMUNICATION_SERVICE_NAME, AUTOCRM_CAMPAIGN_SERVICE_NAME
from gryd_worker import gryd, gryd_helpers as hp, gryd_audit_helper

gryd.SERVICE = AUTOCRM_CAMPAIGN_SERVICE_NAME
# Delay importing prompt helpers to function scope to avoid circular imports

module_logger = clogger


class BaseWorkflow(ABC):
    """Base class for campaign workflows.

    Responsibilities:
    - Load campaign objective model data
    - Provide DB helper methods (list targets, update status)
    - Define abstract `run` method for concrete workflows
    """

    def __init__(self, campaign_objective_id: str, dealership_id: Optional[str] = None, logger=None):
        self.logger = logger or module_logger
        self.campaign_objective_id = campaign_objective_id
        self.dealership_id = dealership_id
        self._model = AutocrmModel('campaign_objective')
        self._objective = None

    def load_objective(self) -> Dict[str, Any]:
        if self._objective is None:
            self.logger.info(f"Loading campaign objective: {self.campaign_objective_id}")
            self._objective = self._model.get(self.campaign_objective_id) or {}
        return self._objective

    def detect_intent(self, session_id: Optional[str] = None, messages: Optional[List[Dict[str, Any]]] = None, summary: Optional[str] = None) -> str:
        """Detect primary intent from messages or summary using LLM via run_prompt_sync.

        Returns a short intent phrase (underscore_separated) or empty string.
        """
        try:
            # import prompt helpers here to avoid circular imports at module load
            from conversation.prompt import run_prompt_sync, get_prompt_file

            # load template from prompts folder using shared helper
            template = get_prompt_file('detect_intent.txt') or get_prompt_file('detect_intent')

            convo_msgs = messages[-8:] if isinstance(messages, list) else messages or []
            convo_text = '\n'.join([m.get('message') or m.get('customer_response') or str(m) for m in convo_msgs])

            if template:
                prompt_text = template.format(summary=summary or '', conversation=convo_text)
            else:
                # Minimal fallback prompt when template file is not available.
                if summary:
                    prompt_text = f"Summary: {summary}"
                else:
                    prompt_text = f"Conversation:\n{convo_text}"

            resp = run_prompt_sync(user_query=" ", system_prompt=prompt_text, history=[], audit_params={"session_id": session_id}, temperature=0.0, **{"model_identifier":"gcp-gemini-3.1-flash-lite-preview", "session_id": session_id})
            intent_raw = ''
            if isinstance(resp, dict):
                intent_raw = (resp.get('output') or resp.get('text') or resp.get('result') or str(resp))
            else:
                intent_raw = str(resp)
            import re
            m = re.search(r"([a-zA-Z0-9_\- ]+)", intent_raw)
            intent_phrase = m.group(1).strip().lower().replace(' ', '_') if m else intent_raw.strip().lower().replace(' ', '_')
            return intent_phrase
        except Exception:
            self.logger.exception('Intent detection failed')
            return ''

    def list_targets(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Return list of target contacts/leads for the workflow.

        By default this is a placeholder and should be overridden by subclasses
        when more specific queries are required.
        """
        filters = filters or {}
        # Placeholder model name; concrete implementations should use correct model
        target_model = AutocrmModel('pre_sales_lead') if (self.load_objective().get('campaign_type') == 'pre-sales') else AutocrmModel('post_sales_lead')
        self.logger.info(f"Listing targets using filters: {filters}")
        return list(target_model.list(filters=filters))

    def update_target(self, target_id: str, updates: Dict[str, Any]) -> Any:
        """Update target record with given changes."""
        model_name = 'pre_sales_lead' if (self.load_objective().get('campaign_type') == 'pre-sales') else 'post_sales_lead'
        m = AutocrmModel(model_name)
        self.logger.info(f"Updating target {target_id} in {model_name} with {updates}")
        return m.update(target_id, updates)

    def run(self, *args, **kwargs):
        """Default run: detect intent and dispatch to matching workflow handler.

        Subclasses should implement `get_handlers()` returning a mapping of
        normalized workflow keys -> callables. Handlers receive same args/kwargs.
        """
        session_id = kwargs.get('session_id')
        messages = kwargs.get('messages')
        summary = kwargs.get('summary')

        intent = kwargs.get('intent') or self.detect_intent(session_id=session_id, messages=messages, summary=summary)
        if not intent:
            self.logger.info('No intent detected; nothing to run')
            return {"status": "no_intent"}

        handlers = self.get_handlers()

        # direct handler by normalized intent name
        norm_intent = self._normalize(intent)
        handler = handlers.get(norm_intent)
        if handler:
            return handler(*args, **kwargs)

        # fallback: token match between intent and workflow names
        import re
        intent_tokens = set(re.split(r"[^a-z0-9]+", intent.lower()))
        for key, h in handlers.items():
            key_tokens = set(re.split(r"[^a-z0-9]+", key.lower()))
            if intent_tokens & key_tokens:
                return h(*args, **kwargs)

        # if nothing matched, return no-op
        self.logger.info(f"No handler matched for intent={intent}")
        return {"status": "no_matching_handler", "intent": intent}

    def get_handlers(self) -> Dict[str, Callable]:
        """Return mapping of normalized workflow keys to handler callables.

        Default implementation discovers instance methods named `wf_<name>`
        and returns a mapping of `<name>` -> callable. Subclasses may override
        to provide custom handler mappings.
        """
        handlers: Dict[str, Callable] = {}
        for attr in dir(self):
            if not attr.startswith('wf_'):
                continue
            fn = getattr(self, attr)
            if callable(fn):
                key = attr[len('wf_'):]
                handlers[key] = fn
        return handlers

    def load_objective_workflows(self) -> List[str]:
        """Helper: return the `workflows` field from the campaign objective record."""
        obj = self.load_objective() or {}
        w = obj.get('workflows')
        return w if isinstance(w, list) else []

    @abstractmethod
    def supported_workflows(self) -> List[str]:
        """Return list of workflow display names supported by this workflow class.

        Subclasses must implement this to declare which workflows they expose.
        They may call `load_objective_workflows()` to use the DB-stored list.
        """
        raise NotImplementedError()

    def _normalize(self, name: str) -> str:
        if not name:
            return ''
        return ''.join(c.lower() if c.isalnum() else '_' for c in name).strip('_')

    def handle_workflow(self, workflow_name: str, *args, **kwargs):
        """Dispatch to a handler method for the given workflow name.

        Handler methods should follow the naming convention `wf_<normalized_name>`.
        """
        if not workflow_name:
            raise ValueError('workflow_name required')
        key = self._normalize(workflow_name)
        handlers = self.get_handlers()
        handler = handlers.get(key)
        if callable(handler):
            return handler(*args, **kwargs)
        raise NotImplementedError(f'Workflow handler not implemented: {workflow_name}')

    def wf_sop_alert(self, *args, **kwargs):
        """Workflow handler to send SOP alert emails.

        Expects kwargs: session_id, session_data, session_mdl_obj, updated_lead_data, sentiment_classification
        """
        try:
            session_id = kwargs.get('session_id')
            session_data = kwargs.get('session_data') or {}
            session_mdl_obj = kwargs.get('session_mdl_obj') or {}
            updated_lead_data = kwargs.get('updated_lead_data') or {}
            sentiment_classification = kwargs.get('sentiment_classification') or ''

            if not session_id:
                self.logger.info('sop_alert: missing session_id, skipping')
                return {'status': 'missing_session_id'}

            receiver_emails = [
                "eshwar@iamdave.ai",
                "sahib@iamdave.ai",
                "shanjai@iamdave.ai",
            ]

            subject = f"SOP Alert: {updated_lead_data.get('disposition_detail','').strip()}"
            html = f"""
            <p>Hi Team,</p>
            <p>A customer interaction was classified as <b>{sentiment_classification}</b> for session <b>{session_id}</b>.</p>
            <p><b>Disposition:</b> {updated_lead_data.get('disposition')}</p>
            <p><b>Detail:</b> {updated_lead_data.get('disposition_detail')}</p>
            <p><b>Lead ID:</b> {session_data.get('lead_id')}</p>
            <p><b>Campaign:</b> {session_data.get('campaign_id')} / {session_data.get('campaign_name')}</p>
            <p><b>Conversation summary:</b></p>
            <pre>{session_mdl_obj.get('summary','')}</pre>
            <p>Message history:</p>
            <pre>{session_mdl_obj.get('history',[])}</pre>
            <p>Please review the SOPs and take corrective action.</p>
            """

            email_payload = {
                "enterprise_id": AUTOCRM_APP_ENTERPRISE_ID,
                "sender": {"name": "AutoCRM Alerts"},
                "receiver": {"emails": receiver_emails},
                "html_string": html,
                "subject": subject,
            }
            try:
                from communication.connectors.email_communication import communication_sender
                communication_sender(**email_payload)
                self.logger.info(f'sop_alert: email sent for session {session_id}')
                return {'status': 'email_sent'}
            except Exception:
                self.logger.exception('sop_alert: failed to send email')
                return {'status': 'email_failed'}

        except Exception:
            self.logger.exception('sop_alert: unexpected error')
            return {'status': 'error'}


class PresalesWorkflow(BaseWorkflow):
    def supported_workflows(self) -> List[str]:
        return [
            'Test drive booking-l',
            'Test drive feedback',
            'Test drive remainder',
            'Showroom launch-l',
        ]

    def get_handlers(self) -> Dict[str, Callable]:
        return {
            'test_drive_booking_l': self.wf_test_drive_booking_l,
            'test_drive_feedback': self.wf_test_drive_feedback,
            'test_drive_remainder': self.wf_test_drive_remainder,
            'showroom_launch_l': self.wf_showroom_launch_l,
        }

    def run(self, *args, **kwargs):
        obj = self.load_objective()
        self.logger.info(f"Running PresalesWorkflow for {self.campaign_objective_id}: {obj.get('campaign_objective_name')}")
        # Example: list targets and perform a simple action (placeholder)
        targets = self.list_targets(kwargs.get('filters'))
        for t in targets:
            # Placeholder action: mark as contacted in a local flag
            try:
                self.update_target(t.get('id') or t.get('lead_id') or t.get('pre_sales_lead_id'), {'last_workflow_run': obj.get('campaign_objective_id')})
            except Exception:
                self.logger.exception('Failed updating target')
        return {'status': 'ok', 'processed': len(targets)}

    def wf_test_drive_feedback(self, *args, **kwargs):
        """Handler for 'Test drive feedback' workflow."""
        # Placeholder: implement feedback collection or status update
        filters = kwargs.get('filters')
        targets = self.list_targets(filters)
        processed = 0
        for t in targets:
            try:
                self.update_target(t.get('id') or t.get('lead_id'), {'test_drive_feedback_requested': True})
                processed += 1
            except Exception:
                self.logger.exception('Failed updating target for test drive feedback')
        return {'status': 'ok', 'processed': processed}


class PostSalesWorkflow(BaseWorkflow):
    def supported_workflows(self) -> List[str]:
        return [
            'Post sales feedback-l',
            'Post Service Feedback-l',
            'Service remainder-l',
            'Insurance renewal-l',
        ]

    def get_handlers(self) -> Dict[str, Callable]:
        return {
            'post_sales_feedback_l': self.wf_post_sales_feedback_l,
            'post_service_feedback_l': self.wf_post_service_feedback_l,
            'service_remainder_l': self.wf_service_remainder_l,
            'insurance_renewal_l': self.wf_insurance_renewal_l,
        }

    def run(self, *args, **kwargs):
        obj = self.load_objective()
        self.logger.info(f"Running PostSalesWorkflow for {self.campaign_objective_id}: {obj.get('campaign_objective_name')}")
        targets = self.list_targets(kwargs.get('filters'))
        # Example: queue follow-up or update status
        processed = 0
        for t in targets:
            try:
                self.update_target(t.get('id') or t.get('lead_id'), {'post_sales_last_run': obj.get('campaign_objective_id')})
                processed += 1
            except Exception:
                self.logger.exception('Failed updating target')
        return {'status': 'ok', 'processed': processed}

    def wf_post_sales_feedback_l(self, *args, **kwargs):
        """Handler for 'Post sales feedback-l' workflow."""
        filters = kwargs.get('filters')
        targets = self.list_targets(filters)
        processed = 0
        for t in targets:
            try:
                self.update_target(t.get('id') or t.get('lead_id'), {'post_sales_feedback_requested': True})
                processed += 1
            except Exception:
                self.logger.exception('Failed updating target for post sales feedback')
        return {'status': 'ok', 'processed': processed}

    def wf_post_service_feedback_l(self, *args, **kwargs):
        """Handler for 'Post Service Feedback-l' workflow."""
        filters = kwargs.get('filters')
        targets = self.list_targets(filters)
        processed = 0
        for t in targets:
            try:
                self.update_target(t.get('id') or t.get('lead_id'), {'post_service_feedback_requested': True})
                processed += 1
            except Exception:
                self.logger.exception('Failed updating target for post service feedback')
        return {'status': 'ok', 'processed': processed}


class OthersWorkflow(BaseWorkflow):
    def supported_workflows(self) -> List[str]:
        # default to objective-defined workflows for 'others'
        return self.load_objective_workflows()

    def run(self, *args, **kwargs):
        obj = self.load_objective()
        self.logger.info(f"Running OthersWorkflow for {self.campaign_objective_id}: {obj.get('campaign_objective_name')}")
        # Implement other types of workflows (e.g., wishes)
        return {'status': 'ok'}


class WorkflowFactory:
    _mapping = {
        'pre-sales': PresalesWorkflow,
        'post-sales': PostSalesWorkflow,
        'others': OthersWorkflow,
    }

    @classmethod
    def get_workflow(cls, campaign_objective_id: str, dealership_id: Optional[str] = None) -> BaseWorkflow:
        model = AutocrmModel('campaign_objective')
        obj = model.get(campaign_objective_id) or {}
        ctype = (obj.get('campaign_type') or '').lower()
        if ctype == 'pre-sales' or ctype == 'pre_sales' or ctype == 'pre sales':
            klass = cls._mapping.get('pre-sales')
        elif ctype == 'post-sales' or ctype == 'post_sales' or ctype == 'post sales':
            klass = cls._mapping.get('post-sales')
        else:
            klass = cls._mapping.get('others')
        return klass(campaign_objective_id, dealership_id)


def trigger_workflow(campaign_objective_id: str, dealership_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    wf = WorkflowFactory.get_workflow(campaign_objective_id, dealership_id)
    return wf.run(**kwargs)


def send_sop_alert(session_id: str, session_data: dict = None, session_mdl_obj: dict = None, updated_lead_data: dict = None, sentiment_classification: str = '') -> Dict[str, Any]:
    """Send SOP alert email using the workflow handler even when no campaign objective is present.

    This creates a lightweight `OthersWorkflow` instance and calls its `wf_sop_alert`.
    """
    try:
        session_data = session_data or {}
        session_mdl_obj = session_mdl_obj or {}
        updated_lead_data = updated_lead_data or {}
        wf = OthersWorkflow(campaign_objective_id='system')
        return wf.wf_sop_alert(session_id=session_id, session_data=session_data, session_mdl_obj=session_mdl_obj, updated_lead_data=updated_lead_data, sentiment_classification=sentiment_classification)
    except Exception:
        module_logger.exception('send_sop_alert: failed')
        return {'status': 'error'}
