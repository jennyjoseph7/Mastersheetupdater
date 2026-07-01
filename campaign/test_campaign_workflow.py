"""
Campaign workflow test suite
============================

Exercises ``determine_campaign_next_action`` / ``get_channel_from_lead`` using
DEBUG_STATUS, DEBUG_LEAD, DEBUG_CAMPAIGN, and related debug fixtures (same
pattern as the ``__main__`` block in ``campaign_workflow.py``).

Workflow retries and delays come from ``CAMPAIGN_WORKFLOW`` in
``campaign_workflow.py``:

+----------------+---------+---------------------------+----------------------------------+
| Status         | Retries | Delay                     | Trigger                          |
+================+=========+===========================+==================================+
| queued         | 20      | 0                         | None (start immediately)         |
| failed         | 20      | linear, 4 h base          | switch_to_next_credential        |
| error          | 0       | —                         | switch_to_next_credential        |
| attempted      | 20      | linear, 6 h base          | switch_to_next_credential        |
| reached        | 20      | v_function (2h–5d window) | switch_to_next_credential        |
| contacted      | 20      | v_function                | switch_to_next_credential        |
| engaged        | 20      | v_function                | follow_up_contact                  |
| converted      | 0       | —                         | confirmation_message             |
+----------------+---------+---------------------------+----------------------------------+

Per-credential retry budget: ``ceil(retries / all_credentials_count)``.

Post-sales campaign **start** offsets (``ATTEMPT_TIME_ON_DUE_DATE`` in
``core/core.py``) — first outreach is scheduled relative to the due date:

+-------------------------------+------------------+
| Lead attribute                | Offset (seconds) |
+===============================+==================+
| next_service_due              | -7 days          |
| warranty_expiry_date          | -60 days         |
| insurance_expiry_date         | -45 days         |
| extended_warranty_expiry_date | -60 days         |
+-------------------------------+------------------+

Test case index
---------------

Pre-sales (no service / insurance due dates on lead)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
PS-01  Fresh lead — no DEBUG_STATUS on channel → start cheapest channel (voice_phone) now
PS-02  Queued provider status → start now (delay 0)
PS-03  Single failed attempt on whatsapp → retry same channel with linear delay
PS-04  Failed retries exhausted on whatsapp → advance to voice_phone
PS-05  Error on whatsapp (0 retries) → skip to next channel immediately
PS-06  Attempted on voice_phone → linear retry delay on same channel
PS-07  Reached (delivered) on whatsapp → schedule via v_function delay
PS-08  Highest contacted + disposition contacted → follow_up_contact
PS-09  Engaged + REQUESTED_CALLBACK → follow_up_contact
PS-10  Engaged without callback detail → no next action
PS-11  Converted disposition → confirmation_message trigger
PS-12  Multi-status history (attempted + contacted) → contacted wins
PS-13  Existing future next_schedule_time → do not schedule before it
PS-14  Existing next_schedule_time + longer workflow delay → keep later time

Post-sales (due-date driven)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
PO-01  next_service_due on lead → due date used for v_function scheduling
PO-02  insurance_expiry_date only → insurance date drives delay
PO-03  Both service + insurance → first DUE_DATE_ATTRIBUTES entry wins (service)
PO-04  No due date on lead → fallback to earliest status created timestamp
PO-05  Due date > stop_period in past → v_function returns None, no follow-up
PO-06  Service campaign start offset matches ATTEMPT_TIME_ON_DUE_DATE (-7 days)
PO-07  Insurance campaign start offset matches ATTEMPT_TIME_ON_DUE_DATE (-45 days)

Run
---
From the repository root (requires ``.venv`` and ``AWS_DEFAULT_REGION``)::

    AWS_DEFAULT_REGION=ap-south-1 .venv/bin/python -m unittest campaign.test_campaign_workflow -v

Delay assertions use a +/- 10 second tolerance (``DELAY_TOLERANCE_SECONDS``).

List documented cases only::

    AWS_DEFAULT_REGION=ap-south-1 .venv/bin/python -m campaign.test_campaign_workflow --list-cases
"""

from __future__ import annotations

import os
import sys
import unittest
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

# Ensure repo root is importable when running as a script.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")

import campaign.campaign_workflow as cw
from campaign.campaign_workflow import CAMPAIGN_WORKFLOW

ATTEMPT_TIME_ON_DUE_DATE = {
    "next_service_due": -7 * 3600 * 24,
    "warranty_expiry_date": -60 * 3600 * 24,
    "insurance_expiry_date": -45 * 3600 * 24,
    "extended_warranty_expiry_date": -60 * 3600 * 24,
}

PHONE = "+919876543210"
EMAIL = "customer@example.com"
DEALERSHIP_ID = "test-dealership"
CAMPAIGN_ID = "test-campaign"
DELAY_TOLERANCE_SECONDS = 10


def _now() -> float:
    return cw.hp.epoch()


def assert_delay_near(test_case, actual, expected, tolerance=DELAY_TOLERANCE_SECONDS):
    """Assert a workflow delay in seconds is within +/- tolerance of expected."""
    test_case.assertIsNotNone(actual, "Expected a delay in seconds")
    test_case.assertAlmostEqual(float(actual), float(expected), delta=tolerance)


def assert_delay_at_least(test_case, actual, minimum, tolerance=DELAY_TOLERANCE_SECONDS):
    """Assert delay is no more than tolerance below the minimum expected seconds."""
    test_case.assertIsNotNone(actual, "Expected a delay in seconds")
    test_case.assertGreaterEqual(float(actual), float(minimum) - tolerance)


@dataclass
class ScenarioResult:
    channel: str | None
    channel_identifier: str | None
    delay: int | float | None
    trigger: str | None


def _status(
    provider_status: str,
    channel: str,
    *,
    created: float | None = None,
    phone_number: str = PHONE,
) -> dict[str, Any]:
    return {
        "provider_status": provider_status,
        "channel": channel,
        "created": created if created is not None else _now(),
        "phone_number": phone_number,
    }


def _failed_statuses(count: int, channel: str = "whatsapp_chat") -> list[dict]:
    return [
        _status("failed", channel, created=_now() - (count - i) * 3600)
        for i in range(count)
    ]


def _pre_sales_lead(**overrides: Any) -> dict[str, Any]:
    lead = {
        "pre_sales_lead_id": "pre-lead-1",
        "campaign_id": CAMPAIGN_ID,
        "campaign_type": "pre-sales",
        "dealership_id": DEALERSHIP_ID,
        "phone_number": PHONE,
        "email": EMAIL,
        "disposition": "queued",
        "disposition_detail": "",
    }
    lead.update(overrides)
    return lead


def _post_sales_lead(**overrides: Any) -> dict[str, Any]:
    lead = {
        "post_sales_lead_id": "post-lead-1",
        "campaign_id": CAMPAIGN_ID,
        "campaign_type": "post-sales",
        "dealership_id": DEALERSHIP_ID,
        "phone_number": PHONE,
        "email": EMAIL,
        "vehicle_id": "vehicle-1",
        "disposition": "queued",
        "disposition_detail": "",
    }
    lead.update(overrides)
    return lead


def _campaign(campaign_type: str = "pre-sales", channels: list[str] | None = None) -> dict[str, Any]:
    return {
        "campaign_id": CAMPAIGN_ID,
        "campaign_type": campaign_type,
        "dealership_id": DEALERSHIP_ID,
        "region_id": "india",
        "channels": channels or ["whatsapp_chat", "voice_phone", "email"],
        "campaign_objective_id": "objective-1",
    }


def _debug_campaign_bundle(campaign_type: str = "pre-sales") -> dict[str, dict]:
    campaign = _campaign(campaign_type)
    return {
        "lead": _pre_sales_lead() if campaign_type == "pre-sales" else _post_sales_lead(),
        "campaign": campaign,
        "dealership": {
            "dealership_id": DEALERSHIP_ID,
            "campaign_timings": {"start_time": 9, "end_time": 18},
        },
        "campaign_objective": {"campaign_objective_id": "objective-1"},
        "user": {"vehicle_id": "vehicle-1", "phone_number": PHONE, "email": EMAIL},
    }


class WorkflowScenarioMixin:
    """Shared mocks for DB-backed helpers."""

    def assert_delay_near(self, actual, expected, tolerance=DELAY_TOLERANCE_SECONDS):
        assert_delay_near(self, actual, expected, tolerance)

    def assert_delay_at_least(self, actual, minimum, tolerance=DELAY_TOLERANCE_SECONDS):
        assert_delay_at_least(self, actual, minimum, tolerance)

    def assert_epoch_near(self, actual, expected, tolerance=DELAY_TOLERANCE_SECONDS):
        """Assert epoch timestamps match within +/- tolerance seconds."""
        assert_delay_near(self, actual, expected, tolerance)

    def setUp(self):
        self._patchers = [
            patch("campaign.campaign_workflow.AutocrmModel"),
            patch(
                "campaign.campaign_workflow.get_channel_identifier_from_lead",
                side_effect=self._channel_identifiers,
            ),
            patch(
                "campaign.campaign_workflow.process_phone_number",
                side_effect=lambda number, _dealership_id: number,
            ),
        ]
        self.mock_autocrm_model = self._patchers[0].start()
        self.mock_autocrm_model.side_effect = self._model_factory
        for patcher in self._patchers[1:]:
            patcher.start()

    def tearDown(self):
        cw.DEBUG_STATUS = None
        cw.DEBUG_LEAD = None
        cw.DEBUG_USER = None
        cw.DEBUG_CAMPAIGN = None
        cw.DEBUG_DEALERSHIP = None
        cw.DEBUG_CAMPAIGN_OBJECTIVE = None
        for patcher in reversed(self._patchers):
            patcher.stop()

    def _model_factory(self, name, *args, **kwargs):
        model = MagicMock(name=name)
        if name == "dealership":
            model.get.return_value = {
                "dealership_id": DEALERSHIP_ID,
                "campaign_timings": {"start_time": 9, "end_time": 18},
            }
        elif name == "region":
            model.get.return_value = {"timezones": "Asia/Kolkata"}
        elif name == "region_subdivision":
            model.get.return_value = None
        elif name == "campaign_workflow":
            model.list.return_value = []
        return model

    def _channel_identifiers(self, channel, lead, logger=None, channel_identifier=None):
        if channel == "email":
            identifiers = [lead.get("email") or EMAIL]
        else:
            identifiers = [lead.get("phone_number") or PHONE]
        if channel_identifier and channel_identifier in identifiers:
            identifiers = identifiers[identifiers.index(channel_identifier) :]
        return identifiers

    def run_channel_scenario(
        self,
        *,
        lead: dict,
        campaign: dict,
        statuses: list[dict] | None,
        disposition: str = "queued",
        channels: list[str] | None = None,
    ) -> ScenarioResult:
        if channels:
            campaign = {**campaign, "channels": channels}
        cw.DEBUG_STATUS = [] if statuses is None else statuses
        channel, identifier, delay, trigger = cw.get_channel_from_lead(
            lead,
            campaign,
            workflow=CAMPAIGN_WORKFLOW,
            disposition=disposition,
            logger=MagicMock(),
        )
        return ScenarioResult(channel, identifier, delay, trigger)

    def run_determine_next_action(
        self,
        *,
        campaign_type: str,
        lead: dict,
        campaign: dict,
        statuses: list[dict] | None,
        disposition: str = "queued",
    ) -> dict:
        bundle = _debug_campaign_bundle(campaign_type)
        bundle["lead"] = lead
        bundle["campaign"] = campaign
        cw.DEBUG_STATUS = [] if statuses is None else statuses
        cw.DEBUG_LEAD = lead
        cw.DEBUG_CAMPAIGN = campaign
        cw.DEBUG_DEALERSHIP = bundle["dealership"]
        cw.DEBUG_CAMPAIGN_OBJECTIVE = bundle["campaign_objective"]
        cw.DEBUG_USER = bundle["user"]
        lead_id = lead.get(f"{campaign_type.replace('-', '_')}_lead_id")
        with patch("campaign.campaign_workflow.gryd.create_async_task"):
            return cw.determine_campaign_next_action(
                campaign_type=campaign_type,
                lead_id=lead_id,
                channel=campaign["channels"][0],
                disposition=disposition,
                debug=True,
                logger=MagicMock(),
            )


class TestPreSalesWorkflow(WorkflowScenarioMixin, unittest.TestCase):
    """Pre-sales leads have no service / insurance due dates."""

    def test_ps01_fresh_lead_starts_on_cheapest_channel(self):
        """PS-01: No contact history → immediate outreach on cheapest channel (voice_phone)."""
        result = self.run_channel_scenario(
            lead=_pre_sales_lead(),
            campaign=_campaign(),
            statuses=None,
            channels=["whatsapp_chat", "voice_phone"],
        )
        self.assertEqual(result.channel, "voice_phone")
        self.assertEqual(result.channel_identifier, PHONE)
        self.assert_delay_near(result.delay, 0)
        self.assertIsNone(result.trigger)

    def test_ps02_queued_status_starts_immediately(self):
        """PS-02: Provider status queued → no delay."""
        result = self.run_channel_scenario(
            lead=_pre_sales_lead(),
            campaign=_campaign(channels=["whatsapp_chat"]),
            statuses=[_status("queued", "whatsapp_chat")],
        )
        self.assertEqual(result.channel, "whatsapp_chat")
        self.assert_delay_near(result.delay, 0)
        self.assertIsNone(result.trigger)

    def test_ps03_failed_single_attempt_retries_same_channel(self):
        """PS-03: One failed attempt → retry whatsapp with linear delay."""
        result = self.run_channel_scenario(
            lead=_pre_sales_lead(),
            campaign=_campaign(channels=["whatsapp_chat"]),
            statuses=[_status("failed", "whatsapp_chat")],
            disposition="failed",
        )
        self.assertEqual(result.channel, "whatsapp_chat")
        self.assertGreater(result.delay, 0)
        self.assertIsNone(result.trigger)
        expected_delay = CAMPAIGN_WORKFLOW["failed"]["delay"] * 1
        self.assert_delay_at_least(result.delay, expected_delay)

    def test_ps04_failed_retries_exhausted_switches_channel(self):
        """PS-04: Failed retries exhausted on whatsapp → voice_phone starts fresh."""
        per_credential_retries = int(cw.hp.np.ceil(CAMPAIGN_WORKFLOW["failed"]["retries"] / 1))
        statuses = _failed_statuses(per_credential_retries, "whatsapp_chat")
        result = self.run_channel_scenario(
            lead=_pre_sales_lead(),
            campaign=_campaign(channels=["whatsapp_chat", "voice_phone"]),
            statuses=statuses,
            disposition="failed",
        )
        self.assertEqual(result.channel, "voice_phone")
        self.assert_delay_near(result.delay, 0)
        self.assertIsNone(result.trigger)

    def test_ps05_error_skips_to_next_channel(self):
        """PS-05: Error status has 0 retries → next channel immediately."""
        result = self.run_channel_scenario(
            lead=_pre_sales_lead(),
            campaign=_campaign(channels=["whatsapp_chat", "voice_phone"]),
            statuses=[_status("error", "whatsapp_chat")],
            disposition="error",
        )
        self.assertEqual(result.channel, "voice_phone")
        self.assert_delay_near(result.delay, 0)

    def test_ps06_attempted_uses_linear_six_hour_backoff(self):
        """PS-06: Attempted status → linear retry delay on same channel."""
        result = self.run_channel_scenario(
            lead=_pre_sales_lead(),
            campaign=_campaign(channels=["voice_phone"]),
            statuses=[_status("attempted", "voice_phone")],
            disposition="attempted",
        )
        self.assertEqual(result.channel, "voice_phone")
        self.assert_delay_at_least(result.delay, CAMPAIGN_WORKFLOW["attempted"]["delay"])

    def test_ps07_reached_uses_v_function_delay(self):
        """PS-07: Reached (delivered) → v_function delay before retry."""
        result = self.run_channel_scenario(
            lead=_pre_sales_lead(),
            campaign=_campaign(channels=["whatsapp_chat"]),
            statuses=[_status("delivered", "whatsapp_chat")],
            disposition="reached",
        )
        self.assertEqual(result.channel, "whatsapp_chat")
        self.assertIsNotNone(result.delay)
        self.assert_delay_at_least(result.delay, CAMPAIGN_WORKFLOW["reached"]["minimum_delay"])

    def test_ps08_contacted_disposition_follow_up(self):
        """PS-08: Contact established → follow_up_contact trigger."""
        result = self.run_channel_scenario(
            lead=_pre_sales_lead(disposition_detail="Interested"),
            campaign=_campaign(channels=["whatsapp_chat"]),
            statuses=[_status("answered", "whatsapp_chat")],
            disposition="contacted",
        )
        self.assertEqual(result.channel, "whatsapp_chat")
        self.assertEqual(result.trigger, "follow_up_contact")
        self.assert_delay_at_least(result.delay, CAMPAIGN_WORKFLOW["contacted"]["minimum_delay"])

    def test_ps09_engaged_requested_callback_follow_up(self):
        """PS-09: Engaged + REQUESTED_CALLBACK → follow_up_contact."""
        result = self.run_channel_scenario(
            lead=_pre_sales_lead(disposition_detail="Requested Callback"),
            campaign=_campaign(channels=["voice_phone"]),
            statuses=[_status("answered", "voice_phone")],
            disposition="engaged",
        )
        self.assertEqual(result.trigger, "follow_up_contact")

    def test_ps10_engaged_without_callback_no_action(self):
        """PS-10: Engaged without eligible disposition detail → stop."""
        result = self.run_channel_scenario(
            lead=_pre_sales_lead(disposition_detail="Enquired for Test Drive"),
            campaign=_campaign(channels=["whatsapp_chat"]),
            statuses=[_status("answered", "whatsapp_chat")],
            disposition="engaged",
        )
        self.assertIsNone(result.channel)
        self.assertIsNone(result.trigger)

    def test_ps11_converted_confirmation_message(self):
        """PS-11: Converted → confirmation_message, no reschedule."""
        result = self.run_channel_scenario(
            lead=_pre_sales_lead(),
            campaign=_campaign(channels=["whatsapp_chat"]),
            statuses=[_status("answered", "whatsapp_chat")],
            disposition="converted",
        )
        self.assertIsNone(result.channel)
        self.assertEqual(result.trigger, "confirmation_message")

    def test_ps12_contacted_beats_attempted_in_history(self):
        """PS-12: Mixed history on one channel — contacted wins over attempted."""
        statuses = [
            _status("attempted", "whatsapp_chat", created=_now() - 7200),
            _status("answered", "whatsapp_chat", created=_now() - 3600),
        ]
        result = self.run_channel_scenario(
            lead=_pre_sales_lead(),
            campaign=_campaign(channels=["whatsapp_chat"]),
            statuses=statuses,
            disposition="contacted",
        )
        self.assertEqual(result.trigger, "follow_up_contact")


class TestNextScheduleTimeFloor(WorkflowScenarioMixin, unittest.TestCase):
    """Ensure computed delays never move next_schedule_time earlier than existing."""

    def test_floor_bumps_immediate_retry_to_existing_schedule(self):
        """Future next_schedule_time + zero workflow delay → wait until that time."""
        future = _now() + 3600
        lead = _pre_sales_lead(next_schedule_time=future)
        result = self.run_channel_scenario(
            lead=lead,
            campaign=_campaign(channels=["voice_phone"]),
            statuses=None,
        )
        self.assertEqual(result.channel, "voice_phone")
        self.assert_delay_near(result.delay, 3600)

    def test_floor_keeps_later_computed_delay(self):
        """When now + delay is already after next_schedule_time, keep computed delay."""
        future = _now() + 1800
        lead = _pre_sales_lead(next_schedule_time=future)
        result = self.run_channel_scenario(
            lead=lead,
            campaign=_campaign(channels=["whatsapp_chat"]),
            statuses=[_status("failed", "whatsapp_chat")],
            disposition="failed",
        )
        self.assertEqual(result.channel, "whatsapp_chat")
        expected = CAMPAIGN_WORKFLOW["failed"]["delay"] * 1
        self.assert_delay_at_least(result.delay, expected)
        self.assertGreater(result.delay, 1800)

    def test_floor_helper_no_existing_schedule(self):
        self.assert_delay_near(cw.apply_next_schedule_time_floor({}, 7200), 7200)

    def test_floor_helper_respects_existing_schedule(self):
        lead = _pre_sales_lead(next_schedule_time=_now() + 5000)
        self.assert_delay_near(cw.apply_next_schedule_time_floor(lead, 0), 5000)

    def test_floor_helper_does_not_shorten_later_delay(self):
        lead = _pre_sales_lead(next_schedule_time=_now() + 1000)
        self.assert_delay_near(cw.apply_next_schedule_time_floor(lead, 9000), 9000)


class TestPostSalesWorkflow(WorkflowScenarioMixin, unittest.TestCase):
    """Post-sales leads carry service / warranty / insurance due dates."""

    def test_po01_service_due_date_used_for_scheduling(self):
        """PO-01: next_service_due becomes v_function anchor."""
        service_due = _now() + 7 * 86400
        lead = _post_sales_lead(next_service_due=service_due)
        due_epoch = cw.get_due_date(lead, [_status("delivered", "whatsapp_chat")], logger=MagicMock())
        self.assert_epoch_near(due_epoch, cw.hp.to_epoch(service_due))

    def test_po02_insurance_due_date_when_no_service(self):
        """PO-02: insurance_expiry_date used when service date absent."""
        insurance_due = _now() + 45 * 86400
        lead = _post_sales_lead(insurance_expiry_date=insurance_due)
        due_epoch = cw.get_due_date(lead, [_status("delivered", "whatsapp_chat")], logger=MagicMock())
        self.assert_epoch_near(due_epoch, cw.hp.to_epoch(insurance_due))

    def test_po03_service_date_precedence_over_insurance(self):
        """PO-03: DUE_DATE_ATTRIBUTES order — service wins over insurance."""
        service_due = _now() + 10 * 86400
        insurance_due = _now() + 45 * 86400
        lead = _post_sales_lead(
            next_service_due=service_due,
            insurance_expiry_date=insurance_due,
        )
        due_epoch = cw.get_due_date(lead, [_status("delivered", "whatsapp_chat")], logger=MagicMock())
        self.assert_epoch_near(due_epoch, cw.hp.to_epoch(service_due))

    def test_po04_no_due_date_falls_back_to_first_status(self):
        """PO-04: Missing due dates → earliest status created timestamp."""
        created = _now() - 86400
        statuses = [_status("failed", "whatsapp_chat", created=created)]
        lead = _post_sales_lead()
        due_epoch = cw.get_due_date(lead, statuses, logger=MagicMock())
        self.assert_epoch_near(due_epoch, cw.hp.to_epoch(created))

    def test_po05_past_due_beyond_stop_period_stops_follow_up(self):
        """PO-05: Last attempt well after due date + stop_period → no delay."""
        due_date = _now() - 40 * 86400
        last_attempt = _now() - 5 * 86400
        delay = cw.v_function(
            last_attempt,
            due_date,
            minimum_delay=CAMPAIGN_WORKFLOW["reached"]["minimum_delay"],
            maximum_delay=CAMPAIGN_WORKFLOW["reached"]["maximum_delay"],
            stop_period=CAMPAIGN_WORKFLOW["reached"]["stop_period"],
        )
        self.assertIsNone(delay)

    def test_po06_service_campaign_start_offset(self):
        """PO-06: Initial schedule = max(now, service_due + (-7 days))."""
        service_due = _now() + 30 * 86400
        offset = ATTEMPT_TIME_ON_DUE_DATE["next_service_due"]
        expected_start = max(_now(), service_due + offset)
        self.assertEqual(offset, -7 * 86400)
        self.assertLess(expected_start, service_due)

    def test_po07_insurance_campaign_start_offset(self):
        """PO-07: Initial schedule = max(now, insurance_due + (-45 days))."""
        insurance_due = _now() + 60 * 86400
        offset = ATTEMPT_TIME_ON_DUE_DATE["insurance_expiry_date"]
        expected_start = max(_now(), insurance_due + offset)
        self.assertEqual(offset, -45 * 86400)
        self.assertLess(expected_start, insurance_due)

    def test_po08_post_sales_reached_with_service_due(self):
        """Post-sales reached on whatsapp with service due → retry with delay."""
        service_due = _now() + 14 * 86400
        result = self.run_channel_scenario(
            lead=_post_sales_lead(next_service_due=service_due),
            campaign=_campaign("post-sales", channels=["whatsapp_chat"]),
            statuses=[_status("delivered", "whatsapp_chat")],
            disposition="reached",
        )
        self.assertEqual(result.channel, "whatsapp_chat")
        self.assert_delay_at_least(result.delay, CAMPAIGN_WORKFLOW["reached"]["minimum_delay"])


class TestWorkflowHelpers(unittest.TestCase):
    """Unit tests for retry math and status aggregation."""

    def test_remaining_retries_divides_by_credentials(self):
        stage = CAMPAIGN_WORKFLOW["failed"]
        self.assertEqual(cw.get_remaining_retries(stage, attempts=0, all_credentials_count=4), 5)
        self.assertEqual(cw.get_remaining_retries(stage, attempts=5, all_credentials_count=4), 0)

    def test_highest_status_priority(self):
        statuses = [
            _status("failed", "whatsapp_chat"),
            _status("delivered", "whatsapp_chat"),
        ]
        self.assertEqual(cw.get_highest_status(statuses), "reached")

    def test_sort_channel_by_cheapest_respects_current_channel(self):
        ordered = cw.sort_channel_by_cheapest(
            ["email", "whatsapp_chat", "voice_phone"],
            current_channel="voice_phone",
        )
        self.assertEqual(ordered[0], "voice_phone")


TEST_CASES = [
    ("PS-01", "Pre-sales fresh lead", TestPreSalesWorkflow.test_ps01_fresh_lead_starts_on_cheapest_channel),
    ("PS-02", "Pre-sales queued", TestPreSalesWorkflow.test_ps02_queued_status_starts_immediately),
    ("PS-03", "Pre-sales failed retry", TestPreSalesWorkflow.test_ps03_failed_single_attempt_retries_same_channel),
    ("PS-04", "Pre-sales failed channel switch", TestPreSalesWorkflow.test_ps04_failed_retries_exhausted_switches_channel),
    ("PS-05", "Pre-sales error channel switch", TestPreSalesWorkflow.test_ps05_error_skips_to_next_channel),
    ("PS-06", "Pre-sales attempted backoff", TestPreSalesWorkflow.test_ps06_attempted_uses_linear_six_hour_backoff),
    ("PS-07", "Pre-sales reached v_function", TestPreSalesWorkflow.test_ps07_reached_uses_v_function_delay),
    ("PS-08", "Pre-sales contacted follow-up", TestPreSalesWorkflow.test_ps08_contacted_disposition_follow_up),
    ("PS-09", "Pre-sales engaged callback", TestPreSalesWorkflow.test_ps09_engaged_requested_callback_follow_up),
    ("PS-10", "Pre-sales engaged no action", TestPreSalesWorkflow.test_ps10_engaged_without_callback_no_action),
    ("PS-11", "Pre-sales converted", TestPreSalesWorkflow.test_ps11_converted_confirmation_message),
    ("PS-12", "Pre-sales mixed statuses", TestPreSalesWorkflow.test_ps12_contacted_beats_attempted_in_history),
    ("PS-13", "Respect existing next_schedule_time", TestNextScheduleTimeFloor.test_floor_bumps_immediate_retry_to_existing_schedule),
    ("PS-14", "Keep delay after next_schedule_time", TestNextScheduleTimeFloor.test_floor_keeps_later_computed_delay),
    ("PO-01", "Post-sales service due date", TestPostSalesWorkflow.test_po01_service_due_date_used_for_scheduling),
    ("PO-02", "Post-sales insurance due date", TestPostSalesWorkflow.test_po02_insurance_due_date_when_no_service),
    ("PO-03", "Post-sales date precedence", TestPostSalesWorkflow.test_po03_service_date_precedence_over_insurance),
    ("PO-04", "Post-sales status fallback due", TestPostSalesWorkflow.test_po04_no_due_date_falls_back_to_first_status),
    ("PO-05", "Post-sales stop period", TestPostSalesWorkflow.test_po05_past_due_beyond_stop_period_stops_follow_up),
    ("PO-06", "Campaign start service offset", TestPostSalesWorkflow.test_po06_service_campaign_start_offset),
    ("PO-07", "Campaign start insurance offset", TestPostSalesWorkflow.test_po07_insurance_campaign_start_offset),
    ("PO-08", "Post-sales reached with service due", TestPostSalesWorkflow.test_po08_post_sales_reached_with_service_due),
]


def print_test_case_index():
    print(__doc__.split("Test case index")[1].split("Run")[0].strip())
    print("\nRegistered tests:")
    for case_id, title, _ in TEST_CASES:
        print(f"  {case_id:6}  {title}")


if __name__ == "__main__":
    if "--list-cases" in sys.argv:
        print_test_case_index()
    else:
        unittest.main()
