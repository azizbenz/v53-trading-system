"""Tests for the stateful compatibility operator UI runtime."""

from __future__ import annotations

import shutil
from pathlib import Path

from interface_contracts import AlertCategory, AlertRecord, AlertSeverity, ProfileId, RuntimeMode
from monitoring import HealthDashboardPayload
from ui import (
    LockedOperatorUiRuntime,
    LockedOperatorUiRuntimeConfig,
    OperatorActionRequest,
    OperatorActionType,
)


def _payload() -> HealthDashboardPayload:
    return HealthDashboardPayload(
        timestamp_ms=1_700_000_000_000,
        correlation_id="corr-ui-runtime",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        headline_status="critical",
        active_alert_count=1,
        stale_pair_count=1,
        queue_backlog=75,
        capital_deployed_usdt=1200.0,
        gross_capacity_used_pct=35.0,
        loss_capacity_used_pct=8.0,
        ce_net=0.0012,
        dtr_coverage=0.85,
        cra_sterilization_rate=0.25,
        break_even_drift_scopes=("engine_b",),
        edge_credible_count=1,
        edge_degraded_count=1,
        edge_surveillance_count=0,
        future_learning_diagnostics=2,
        future_learning_hypotheses=1,
    )


def _critical_alert() -> AlertRecord:
    return AlertRecord(
        timestamp_ms=1_700_000_000_000,
        alert_id="corr-ui-runtime:loss",
        severity=AlertSeverity.CRITICAL,
        category=AlertCategory.INFRA,
        message="Critical loss detected",
        module="monitoring",
    )


def _scratch_dir(name: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("light_ui_runtime_tests", name)


def test_light_ui_runtime_builds_view_with_pending_critical_notifications():
    runtime = LockedOperatorUiRuntime()

    result = runtime.build_view(_payload(), alerts=(_critical_alert(),))
    alerts = next(section for section in result.view.sections if section.title == "Alerts & Events")

    assert result.view.notification_contract.supported_channels == (
        "slack_webhook_contract",
        "telegram_contract",
    )
    assert result.view.pending_notifications[0].alert_id == "corr-ui-runtime:loss"
    assert result.view.pending_notifications[0].delivery_state.value == "pending_contract"
    assert result.view.event_log[0].message == "screen opened: overview"
    assert alerts.cards[2].value == "1"
    assert alerts.cards[2].detail == "screen opened: overview"
    assert alerts.cards[3].value == "pending=1 / ack=0"


def test_light_ui_runtime_persists_history_across_restart():
    state_dir = _scratch_dir("persist")
    config = LockedOperatorUiRuntimeConfig(
        state_dir=state_dir,
        persist_history=True,
    )
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        runtime = LockedOperatorUiRuntime(config=config)
        runtime.build_view(_payload(), alerts=(_critical_alert(),))
        outcome = runtime.submit_action(
            OperatorActionRequest(
                timestamp_ms=1_700_000_000_100,
                correlation_id="corr-ui-runtime",
                profile=ProfileId.LIGHT,
                runtime_mode=RuntimeMode.SHADOW,
                action=OperatorActionType.SUSPEND_PAIR,
                target="BTCUSDT",
            ),
            allowed_pairs=("BTCUSDT",),
        )

        assert outcome.accepted is True

        reloaded = LockedOperatorUiRuntime(config=config)
        result = reloaded.build_view(_payload(), alerts=(_critical_alert(),))

        messages = tuple(entry.message for entry in result.view.event_log)
        assert "operator action accepted: suspend_pair" in messages
        assert result.state_path.endswith("light_ui_runtime_state.json")
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_light_ui_runtime_acknowledges_critical_alert_and_hides_pending_notification():
    runtime = LockedOperatorUiRuntime()
    runtime.build_view(_payload(), alerts=(_critical_alert(),))

    outcome = runtime.submit_action(
        OperatorActionRequest(
            timestamp_ms=1_700_000_000_200,
            correlation_id="corr-ui-runtime",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW,
            action=OperatorActionType.ACKNOWLEDGE_CRITICAL_ALERT,
            target="corr-ui-runtime:loss",
        ),
    )
    result = runtime.build_view(_payload(), alerts=(_critical_alert(),))
    alerts = next(section for section in result.view.sections if section.title == "Alerts & Events")

    assert outcome.accepted is True
    assert result.view.pending_notifications == ()
    assert any(entry.message == "critical alert acknowledged" for entry in result.view.event_log)
    assert alerts.cards[2].detail == "critical alert acknowledged"
    assert alerts.cards[3].value == "pending=0 / ack=1"
    assert alerts.cards[3].detail == "latest ack: corr-ui-runtime:loss"


def test_light_ui_runtime_projects_rejections_into_monitoring_log_tail():
    runtime = LockedOperatorUiRuntime()
    runtime.build_view(_payload(), alerts=(_critical_alert(),))

    outcome = runtime.submit_action(
        OperatorActionRequest(
            timestamp_ms=1_700_000_000_300,
            correlation_id="corr-ui-runtime",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW,
            action=OperatorActionType.MODIFY_RISK_CAPS,
            target="risk",
        ),
    )
    projection = runtime.get_operator_projection()

    assert outcome.accepted is False
    assert projection.rejection_event_count == 1
    assert projection.latest_rejection_reason == "risk cap changes are forbidden in the compatibility operator UI"
    assert projection.recent_event_log[-1].event_type == "operator_action_rejected"
    assert projection.recent_event_log[-1].rejection_reason == (
        "risk cap changes are forbidden in the compatibility operator UI"
    )


def test_light_ui_runtime_projects_latest_safing_request_from_accepted_manual_action():
    runtime = LockedOperatorUiRuntime()

    outcome = runtime.submit_action(
        OperatorActionRequest(
            timestamp_ms=1_700_000_000_400,
            correlation_id="corr-ui-runtime",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.LIVE,
            action=OperatorActionType.DOWNGRADE_TO_MICRO_LIVE,
            reason="execution drift requires step-down",
        ),
    )
    projection = runtime.get_operator_projection()

    assert outcome.accepted is True
    assert projection.latest_safing_action == "downgrade_to_micro_live"
    assert projection.latest_safing_source_runtime_mode == "live"
    assert projection.latest_safing_target_runtime_mode == "micro_live"
    assert projection.latest_safing_reason == "execution drift requires step-down"


def test_light_ui_runtime_corrupted_state_creates_backup_and_marks_last_error():
    state_dir = _scratch_dir("corrupted-state")
    config = LockedOperatorUiRuntimeConfig(
        state_dir=state_dir,
        persist_history=True,
    )
    shutil.rmtree(state_dir, ignore_errors=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / config.state_filename
    state_path.write_text("{ invalid json", encoding="utf-8")
    try:
        runtime = LockedOperatorUiRuntime(config=config)
        projection = runtime.get_operator_projection()

        assert state_path.with_suffix(".corrupted").exists()
        assert "state_file_corrupted" in runtime.get_state().last_error
        assert projection.last_error == runtime.get_state().last_error
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_light_ui_runtime_build_view_projects_last_error_from_recovered_state():
    state_dir = _scratch_dir("corrupted-view")
    config = LockedOperatorUiRuntimeConfig(
        state_dir=state_dir,
        persist_history=True,
    )
    shutil.rmtree(state_dir, ignore_errors=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / config.state_filename
    state_path.write_text("null", encoding="utf-8")
    try:
        runtime = LockedOperatorUiRuntime(config=config)
        result = runtime.build_view(_payload(), alerts=(_critical_alert(),))
        alerts = next(section for section in result.view.sections if section.title == "Alerts & Events")

        assert any(
            card.key == "operator_events" and "state_file_corrupted" in card.detail
            for card in alerts.cards
        )
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
