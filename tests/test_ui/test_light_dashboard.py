"""Tests for the locked Build-10 Light UI backend surface."""

from __future__ import annotations

import ui
from interface_contracts import AlertCategory, AlertSeverity, PairHealthLevel, ProfileId, RuntimeMode
from monitoring import (
    AlertHistoryEntry,
    EngineMetrics,
    HealthDashboardPayload,
    OperatorRuntimeProjection,
    PairMetrics,
)
from ui import build_light_dashboard_view


def _payload() -> HealthDashboardPayload:
    return HealthDashboardPayload(
        timestamp_ms=1_700_000_000_000,
        correlation_id="corr-ui",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        headline_status="warning",
        active_alert_count=3,
        active_alert_ids=("corr-ui:backlog", "corr-ui:loss"),
        alert_history=(
            AlertHistoryEntry(
                alert_id="corr-ui:backlog",
                severity=AlertSeverity.WARNING,
                category=AlertCategory.INFRA,
                message="Queue backlog elevated",
                status="open",
                opened_ms=1_700_000_000_000,
                last_seen_ms=1_700_000_000_000,
            ),
        ),
        stale_pair_count=1,
        queue_backlog=75,
        backlog_high_water_mark=220,
        drop_rate_pct=7.5,
        stale_spike_count=2,
        recovery_retry_count=1,
        capital_deployed_usdt=1200.0,
        pnl_net_usdt=-12.5,
        gross_capacity_used_pct=35.0,
        loss_capacity_used_pct=8.0,
        beta_utilization=0.4,
        ce_net=0.0012,
        dominant_cluster="btc-beta",
        risk_breaches=("beta_warning",),
        pairs=(
            PairMetrics(
                pair="BTCUSDT",
                health=PairHealthLevel.STALE,
                freshness_ms=9_000,
                backlog_depth=75,
                is_active=False,
                average_cost_bps=1.3,
                cost_p90_bps=2.1,
                ce_expected=0.0002,
                useful_frequency=1.2,
                suspension_reason="stale feed",
            ),
        ),
        engines=(
            EngineMetrics(
                engine_id="engine_a",
                emitted_signals=3,
                net_edge_bps=5.0,
                expected_cost_bps=1.5,
                ce_expected=0.0005,
                useful_frequency=1.8,
            ),
            EngineMetrics(
                engine_id="engine_b",
                emitted_signals=1,
                net_edge_bps=-0.5,
                expected_cost_bps=1.7,
                ce_expected=0.0,
                useful_frequency=0.6,
                stale=True,
            ),
        ),
        reconnect_count=2,
        dtr_loss_count=1,
        log_loss_count=0,
        elw_bps=0.8,
        expected_cost_bps=1.1,
        realized_cost_bps=1.6,
        partial_fill_count=2,
        fill_latency_ms_p95=240,
        reconciliation_alert_count=1,
        cpu_pct=30.0,
        ram_pct=45.0,
        dtr_coverage=0.85,
        cra_sterilization_rate=0.25,
        cra_alert_count=1,
        break_even_drift_scopes=("engine_b",),
        edge_credible_count=1,
        edge_degraded_count=1,
        edge_surveillance_count=0,
        future_learning_diagnostics=2,
        future_learning_hypotheses=1,
        deployment_state="degraded",
        last_transition_summary="shadow -> degraded",
        shadow_status="warning",
        micro_live_status="planned",
        live_light_status="planned",
        operator_runtime=OperatorRuntimeProjection(
            event_count=3,
            latest_event_type="operator_action_accepted",
            latest_event_message="operator action accepted: suspend_pair",
            pending_notification_count=1,
            pending_notification_alert_ids=("corr-ui:loss",),
            acknowledged_notification_count=2,
            latest_acknowledged_alert_id="corr-ui:critical-latency",
        ),
    )


def test_ui_exports_expected_symbols():
    assert {
        "DashboardCard",
        "DashboardSection",
        "LockedControlSurface",
        "LightDashboardView",
        "OperatorActionType",
        "evaluate_light_operator_action",
        "build_light_dashboard_view",
    }.issubset(set(ui.__all__))


def test_light_dashboard_view_is_locked_and_structured():
    view = build_light_dashboard_view(_payload())
    titles = {section.title for section in view.sections}

    assert {
        "Health",
        "Profile & State",
        "Portfolio",
        "Pairs",
        "Engines",
        "Risk",
        "Execution",
        "Data & Infra",
        "Meta",
        "Alerts & Events",
        "Future Learning",
    } == titles
    assert view.control_surface.profile_selector_enabled is False
    assert view.control_surface.engine_cd_toggle_enabled is False
    assert view.control_surface.complete_pairs_enabled is False
    assert view.control_surface.hard_guard_override_enabled is False
    assert view.control_surface.max_light_pairs == 6
    assert tuple(view.control_surface.suspendable_engines) == ("engine_a", "engine_b")
    assert "suspend_pair" in {action.value for action in view.allowed_actions}
    assert view.notification_contract.critical_delivery_required is True
    assert view.notification_contract.implementation_status == "contract_only"
    assert view.event_log[0].message == "screen opened: overview"


def test_light_dashboard_view_exposes_future_learning_panels_without_claiming_runtime():
    view = build_light_dashboard_view(_payload())
    future_cards = next(section for section in view.sections if section.title == "Future Learning")

    assert view.profile == ProfileId.LIGHT
    assert view.runtime_mode == RuntimeMode.SHADOW
    assert "build9x_diagnostics" in view.future_panels
    assert future_cards.cards[0].value == "2"
    assert future_cards.cards[1].value == "1"
    profile = next(section for section in view.sections if section.title == "Profile & State")
    assert any(card.key == "deployment_state" and card.value == "degraded" for card in profile.cards)
    assert any(card.key == "last_transition" and card.value == "shadow -> degraded" for card in profile.cards)


def test_light_dashboard_view_projects_pairs_engines_and_alert_history():
    view = build_light_dashboard_view(_payload())
    pairs = next(section for section in view.sections if section.title == "Pairs")
    engines = next(section for section in view.sections if section.title == "Engines")
    alerts = next(section for section in view.sections if section.title == "Alerts & Events")
    portfolio = next(section for section in view.sections if section.title == "Portfolio")

    assert pairs.cards[0].key == "pair_btcusdt"
    assert pairs.cards[0].status == "warning"
    assert engines.cards[1].key == "engine_engine_b"
    assert engines.cards[1].status == "warning"
    assert portfolio.cards[1].key == "pnl_net"
    assert portfolio.cards[1].value == "-12.50"
    assert portfolio.cards[1].status == "warning"
    assert alerts.cards[0].detail == "corr-ui:backlog, corr-ui:loss"
    assert alerts.cards[1].detail == "open: Queue backlog elevated"
    assert alerts.cards[2].detail == "operator action accepted: suspend_pair"
    assert alerts.cards[3].value == "pending=1 / ack=2"


def test_live_dashboard_view_exposes_manual_downgrade_actions():
    view = build_light_dashboard_view(
        _payload().model_copy(
            update={
                "runtime_mode": RuntimeMode.LIVE,
                "deployment_state": "live_complete",
                "live_light_status": "healthy",
                "micro_live_status": "healthy",
                "shadow_status": "healthy",
            }
        )
    )

    assert view.allowed_actions == (
        ui.OperatorActionType.VIEW_CRITICAL_SCREENS,
        ui.OperatorActionType.SUSPEND_PAIR,
        ui.OperatorActionType.REQUEST_PAIR_RESUME,
        ui.OperatorActionType.SUSPEND_ENGINE,
        ui.OperatorActionType.SET_HALTED,
        ui.OperatorActionType.DOWNGRADE_TO_MICRO_LIVE,
        ui.OperatorActionType.DOWNGRADE_TO_SHADOW,
        ui.OperatorActionType.VIEW_ALERT_HISTORY,
        ui.OperatorActionType.ACKNOWLEDGE_CRITICAL_ALERT,
    )
