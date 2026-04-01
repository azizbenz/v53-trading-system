"""Tests for governed operator actions in the locked Light UI."""

from __future__ import annotations

from interface_contracts import ProfileId, RuntimeMode
from ui import (
    OperatorActionRequest,
    OperatorActionType,
    OperatorEventType,
    build_light_allowed_actions,
    evaluate_light_operator_action,
    record_screen_open,
)


def _request(
    action: OperatorActionType,
    *,
    target: str = "",
    requested_pair_count: int = 0,
) -> OperatorActionRequest:
    return OperatorActionRequest(
        timestamp_ms=1_700_000_000_000,
        correlation_id="corr-operator",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        action=action,
        target=target,
        requested_pair_count=requested_pair_count,
    )


def test_allowed_action_surface_matches_light_spec():
    assert build_light_allowed_actions() == (
        OperatorActionType.VIEW_CRITICAL_SCREENS,
        OperatorActionType.SUSPEND_PAIR,
        OperatorActionType.REQUEST_PAIR_RESUME,
        OperatorActionType.SUSPEND_ENGINE,
        OperatorActionType.SET_HALTED,
        OperatorActionType.VIEW_ALERT_HISTORY,
        OperatorActionType.ACKNOWLEDGE_CRITICAL_ALERT,
    )


def test_authorized_pair_suspend_is_accepted_and_logged():
    outcome = evaluate_light_operator_action(
        _request(OperatorActionType.SUSPEND_PAIR, target="BTCUSDT"),
        allowed_pairs=("BTCUSDT", "ETHUSDT"),
    )

    assert outcome.accepted is True
    assert outcome.resulting_state == "pair_suspended"
    assert tuple(entry.event_type for entry in outcome.log_entries) == (
        OperatorEventType.ACTION_REQUESTED,
        OperatorEventType.ACTION_ACCEPTED,
    )


def test_resume_requires_conditions_lifted_evidence():
    outcome = evaluate_light_operator_action(
        _request(OperatorActionType.REQUEST_PAIR_RESUME, target="BTCUSDT"),
        resumable_pairs=(),
    )

    assert outcome.accepted is False
    assert outcome.rejection_reason == "pair resume requires conditions_lifted evidence"
    assert outcome.log_entries[-1].event_type == OperatorEventType.ACTION_REJECTED
    assert outcome.log_entries[-1].rejection_reason == outcome.rejection_reason


def test_engine_c_activation_is_explicitly_rejected():
    outcome = evaluate_light_operator_action(
        _request(OperatorActionType.ACTIVATE_ENGINE, target="engine_c"),
    )

    assert outcome.accepted is False
    assert outcome.rejection_reason == "activating engines C/D is forbidden in Light"


def test_activating_more_than_six_pairs_is_rejected():
    outcome = evaluate_light_operator_action(
        _request(OperatorActionType.ACTIVATE_PAIRS, requested_pair_count=12),
    )

    assert outcome.accepted is False
    assert outcome.rejection_reason == "activating more than 6 pairs is forbidden in Light"


def test_acknowledging_visible_critical_alert_emits_dedicated_log_event():
    outcome = evaluate_light_operator_action(
        _request(OperatorActionType.ACKNOWLEDGE_CRITICAL_ALERT, target="corr-operator:loss"),
        critical_alert_ids=("corr-operator:loss",),
    )

    assert outcome.accepted is True
    assert outcome.resulting_state == "critical_alert_acknowledged"
    assert outcome.log_entries[-1].event_type == OperatorEventType.CRITICAL_ALERT_ACKNOWLEDGED
    assert outcome.log_entries[-1].message == "critical alert acknowledged"


def test_record_screen_open_creates_auditable_entry():
    entry = record_screen_open(
        correlation_id="corr-operator",
        timestamp_ms=1_700_000_000_000,
        screen_id="overview",
    )

    assert entry.event_type == OperatorEventType.SCREEN_OPENED
    assert entry.accepted is True
    assert entry.message == "screen opened: overview"
