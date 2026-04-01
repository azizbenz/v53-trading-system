"""Tests for UI contracts and dashboard view edge cases."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from interface_contracts import AlertCategory, AlertSeverity, PairHealthLevel, ProfileId, RuntimeMode
from monitoring import (
    AlertHistoryEntry,
    EngineMetrics,
    HealthDashboardPayload,
    OperatorRuntimeProjection,
    PairMetrics,
)
from ui import build_light_dashboard_view
from ui.contracts import (
    DashboardCard,
    DashboardSection,
    LightDashboardView,
    LockedControlSurface,
    OperatorActionType,
)


def _payload(**overrides) -> HealthDashboardPayload:
    defaults = dict(
        timestamp_ms=1_700_000_000_000,
        correlation_id="corr-ui-test",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        headline_status="healthy",
        active_alert_count=0,
        active_alert_ids=(),
        alert_history=(),
        stale_pair_count=0,
        queue_backlog=0,
        backlog_high_water_mark=0,
        drop_rate_pct=0.0,
        stale_spike_count=0,
        recovery_retry_count=0,
        capital_deployed_usdt=1000.0,
        pnl_net_usdt=12.0,
        gross_capacity_used_pct=25.0,
        loss_capacity_used_pct=5.0,
        beta_utilization=0.2,
        ce_net=0.001,
        dominant_cluster="cluster_a",
        risk_breaches=(),
        pairs=(
            PairMetrics(
                pair="BTCUSDT",
                health=PairHealthLevel.HEALTHY,
                freshness_ms=500,
            ),
        ),
        engines=(
            EngineMetrics(
                engine_id="engine_a",
                emitted_signals=2,
                net_edge_bps=3.0,
                expected_cost_bps=1.0,
                ce_expected=0.0004,
                useful_frequency=1.5,
            ),
        ),
        reconnect_count=0,
        dtr_loss_count=0,
        log_loss_count=0,
        elw_bps=0.3,
        expected_cost_bps=1.0,
        realized_cost_bps=1.0,
        partial_fill_count=0,
        fill_latency_ms_p95=120,
        reconciliation_alert_count=0,
        cpu_pct=15.0,
        ram_pct=20.0,
        dtr_coverage=0.95,
        cra_sterilization_rate=0.05,
        cra_alert_count=0,
        break_even_drift_scopes=(),
        edge_credible_count=2,
        edge_degraded_count=0,
        edge_surveillance_count=0,
        future_learning_diagnostics=0,
        future_learning_hypotheses=0,
        deployment_state="shadow",
        last_transition_summary="entered shadow",
        shadow_status="healthy",
        micro_live_status="planned",
        live_light_status="planned",
    )
    defaults.update(overrides)
    return HealthDashboardPayload(**defaults)


class TestLockedControlSurface:
    def test_all_controls_disabled_by_default(self):
        surface = LockedControlSurface()
        assert surface.profile_selector_enabled is False
        assert surface.engine_cd_toggle_enabled is False
        assert surface.complete_pairs_enabled is False
        assert surface.hard_guard_override_enabled is False
        assert surface.max_light_pairs == 6
        assert surface.suspendable_engines == ("engine_a", "engine_b")

    def test_surface_is_frozen(self):
        surface = LockedControlSurface()
        import pytest
        with pytest.raises(Exception):
            surface.profile_selector_enabled = True


class TestDashboardCard:
    def test_card_with_detail(self):
        card = DashboardCard(key="test", label="Test", value="42", status="info", detail="extra")
        assert card.detail == "extra"

    def test_card_without_detail(self):
        card = DashboardCard(key="test", label="Test", value="0", status="healthy")
        assert card.detail is None or card.detail == ""

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            DashboardCard(key="test", label="Test", value="0", status="unknown")


class TestDashboardSections:
    def test_health_section_present(self):
        view = build_light_dashboard_view(_payload())
        health = next(s for s in view.sections if s.title == "Health")
        assert len(health.cards) == 2
        assert health.cards[0].key == "headline_status"
        assert health.cards[1].key == "stale_pairs"

    def test_portfolio_section_present(self):
        view = build_light_dashboard_view(_payload())
        portfolio = next(s for s in view.sections if s.title == "Portfolio")
        assert len(portfolio.cards) == 3
        assert portfolio.cards[0].key == "capital_deployed"
        assert portfolio.cards[1].key == "pnl_net"
        assert portfolio.cards[2].key == "ce_net"

    def test_meta_section_present(self):
        view = build_light_dashboard_view(_payload())
        meta = next(s for s in view.sections if s.title == "Meta")
        assert len(meta.cards) == 3
        assert {c.key for c in meta.cards} == {"dtr_coverage", "cra_sterilization", "edge_status"}

    def test_future_learning_section_present(self):
        view = build_light_dashboard_view(_payload())
        fl = next(s for s in view.sections if s.title == "Future Learning")
        assert len(fl.cards) == 2
        assert fl.cards[0].status == "planned"

    def test_profile_state_section_present(self):
        view = build_light_dashboard_view(_payload())
        profile = next(s for s in view.sections if s.title == "Profile & State")
        assert len(profile.cards) == 4
        assert profile.cards[0].key == "profile"
        assert profile.cards[1].key == "deployment_state"
        assert profile.cards[2].key == "last_transition"
        assert profile.cards[3].key == "controls_locked"

    def test_pairs_and_engines_sections_present(self):
        view = build_light_dashboard_view(_payload())
        pairs = next(s for s in view.sections if s.title == "Pairs")
        engines = next(s for s in view.sections if s.title == "Engines")
        assert pairs.cards[0].key == "pair_btcusdt"
        assert engines.cards[0].key == "engine_engine_a"

    def test_risk_execution_infra_and_alert_sections_present(self):
        view = build_light_dashboard_view(_payload())
        risk = next(s for s in view.sections if s.title == "Risk")
        execution = next(s for s in view.sections if s.title == "Execution")
        infra = next(s for s in view.sections if s.title == "Data & Infra")
        alerts = next(s for s in view.sections if s.title == "Alerts & Events")
        assert len(risk.cards) == 3
        assert len(execution.cards) == 3
        assert len(infra.cards) == 4
        assert len(alerts.cards) == 4

    def test_exactly_eleven_sections(self):
        view = build_light_dashboard_view(_payload())
        assert len(view.sections) == 11

    def test_each_section_has_expected_card_count(self):
        view = build_light_dashboard_view(_payload())
        counts = {section.title: len(section.cards) for section in view.sections}
        assert counts == {
            "Health": 2,
            "Profile & State": 4,
            "Portfolio": 3,
            "Pairs": 1,
            "Engines": 1,
            "Risk": 3,
            "Execution": 3,
            "Data & Infra": 4,
            "Meta": 3,
            "Alerts & Events": 4,
            "Future Learning": 2,
        }


class TestDashboardStatusMapping:
    def test_healthy_headline_maps_to_card(self):
        view = build_light_dashboard_view(_payload(headline_status="healthy"))
        health = next(s for s in view.sections if s.title == "Health")
        assert health.cards[0].value == "healthy"
        assert health.cards[0].status == "healthy"

    def test_warning_headline_maps_to_card(self):
        view = build_light_dashboard_view(_payload(headline_status="warning"))
        health = next(s for s in view.sections if s.title == "Health")
        assert health.cards[0].status == "warning"

    def test_critical_headline_maps_to_card(self):
        view = build_light_dashboard_view(_payload(headline_status="critical"))
        health = next(s for s in view.sections if s.title == "Health")
        assert health.cards[0].status == "critical"

    def test_stale_pairs_zero_shows_healthy(self):
        view = build_light_dashboard_view(_payload(stale_pair_count=0))
        health = next(s for s in view.sections if s.title == "Health")
        assert health.cards[1].status == "healthy"

    def test_stale_pairs_nonzero_shows_warning(self):
        view = build_light_dashboard_view(_payload(stale_pair_count=3))
        health = next(s for s in view.sections if s.title == "Health")
        assert health.cards[1].status == "warning"

    def test_negative_ce_shows_warning(self):
        view = build_light_dashboard_view(_payload(ce_net=-0.001))
        portfolio = next(s for s in view.sections if s.title == "Portfolio")
        assert portfolio.cards[2].status == "warning"

    def test_positive_ce_shows_healthy(self):
        view = build_light_dashboard_view(_payload(ce_net=0.001))
        portfolio = next(s for s in view.sections if s.title == "Portfolio")
        assert portfolio.cards[2].status == "healthy"

    def test_negative_pnl_shows_warning(self):
        view = build_light_dashboard_view(_payload(pnl_net_usdt=-5.0))
        portfolio = next(s for s in view.sections if s.title == "Portfolio")
        assert portfolio.cards[1].status == "warning"

    def test_profile_state_projects_rollout_summary(self):
        view = build_light_dashboard_view(
            _payload(
                deployment_state="degraded",
                last_transition_summary="shadow -> degraded",
                shadow_status="warning",
                micro_live_status="planned",
                live_light_status="planned",
            )
        )
        profile = next(s for s in view.sections if s.title == "Profile & State")
        assert profile.cards[1].value == "degraded"
        assert profile.cards[1].detail == "shadow=warning / micro=planned / live=planned"
        assert profile.cards[2].value == "shadow -> degraded"

    def test_high_dtr_coverage_healthy(self):
        view = build_light_dashboard_view(_payload(dtr_coverage=0.95))
        meta = next(s for s in view.sections if s.title == "Meta")
        dtr_card = next(c for c in meta.cards if c.key == "dtr_coverage")
        assert dtr_card.status == "healthy"

    def test_low_dtr_coverage_warning(self):
        view = build_light_dashboard_view(_payload(dtr_coverage=0.60))
        meta = next(s for s in view.sections if s.title == "Meta")
        dtr_card = next(c for c in meta.cards if c.key == "dtr_coverage")
        assert dtr_card.status == "warning"

    def test_high_sterilization_warning(self):
        view = build_light_dashboard_view(_payload(cra_sterilization_rate=0.35))
        meta = next(s for s in view.sections if s.title == "Meta")
        cra_card = next(c for c in meta.cards if c.key == "cra_sterilization")
        assert cra_card.status == "warning"

    def test_low_sterilization_healthy(self):
        view = build_light_dashboard_view(_payload(cra_sterilization_rate=0.10))
        meta = next(s for s in view.sections if s.title == "Meta")
        cra_card = next(c for c in meta.cards if c.key == "cra_sterilization")
        assert cra_card.status == "healthy"


class TestDashboardFuturePanels:
    def test_future_panels_contain_expected_keys(self):
        view = build_light_dashboard_view(_payload())
        assert "build9x_diagnostics" in view.future_panels
        assert "strategy_onboarding" in view.future_panels
        assert "artifact_import" in view.future_panels

    def test_allowed_actions_are_governed_and_locked(self):
        view = build_light_dashboard_view(_payload())
        assert view.allowed_actions == (
            OperatorActionType.VIEW_CRITICAL_SCREENS,
            OperatorActionType.SUSPEND_PAIR,
            OperatorActionType.REQUEST_PAIR_RESUME,
            OperatorActionType.SUSPEND_ENGINE,
            OperatorActionType.SET_HALTED,
            OperatorActionType.VIEW_ALERT_HISTORY,
            OperatorActionType.ACKNOWLEDGE_CRITICAL_ALERT,
        )

    def test_event_log_starts_with_screen_open(self):
        view = build_light_dashboard_view(_payload())
        assert view.event_log[0].message == "screen opened: overview"
        assert view.event_log[0].accepted is True

    def test_notification_contract_is_defined_even_without_network_impl(self):
        view = build_light_dashboard_view(_payload())
        assert view.notification_contract.critical_delivery_required is True
        assert view.notification_contract.implementation_status == "contract_only"

    def test_future_learning_values_projected(self):
        view = build_light_dashboard_view(_payload(
            future_learning_diagnostics=5,
            future_learning_hypotheses=3,
        ))
        fl = next(s for s in view.sections if s.title == "Future Learning")
        assert fl.cards[0].value == "5"
        assert fl.cards[1].value == "3"

    def test_view_preserves_profile_and_mode(self):
        view = build_light_dashboard_view(_payload())
        assert view.profile == ProfileId.LIGHT
        assert view.runtime_mode == RuntimeMode.SHADOW

    def test_view_preserves_timestamp_and_correlation_id(self):
        view = build_light_dashboard_view(_payload())
        assert view.timestamp_ms == 1_700_000_000_000
        assert view.correlation_id == "corr-ui-test"

    def test_health_card_detail_projects_alerts_and_backlog(self):
        view = build_light_dashboard_view(_payload(active_alert_count=4, queue_backlog=88))
        health = next(s for s in view.sections if s.title == "Health")
        assert health.cards[0].detail == "4 active alert(s)"
        assert health.cards[1].detail == "Queue backlog 88"

    def test_edge_status_detail_projects_break_even_scope_count(self):
        view = build_light_dashboard_view(
            _payload(break_even_drift_scopes=("engine_a", "engine_b"))
        )
        meta = next(s for s in view.sections if s.title == "Meta")
        edge_card = next(c for c in meta.cards if c.key == "edge_status")
        assert edge_card.detail == "Break-even drift scopes: 2"

    def test_future_learning_cards_stay_planned_at_zero(self):
        view = build_light_dashboard_view(_payload())
        future = next(s for s in view.sections if s.title == "Future Learning")
        assert tuple(card.status for card in future.cards) == ("planned", "planned")

    def test_alert_history_section_uses_short_history_when_available(self):
        view = build_light_dashboard_view(_payload(
            active_alert_count=1,
            active_alert_ids=("corr-ui-test:backlog",),
            alert_history=(
                AlertHistoryEntry(
                    alert_id="corr-ui-test:backlog",
                    severity=AlertSeverity.WARNING,
                    category=AlertCategory.INFRA,
                    message="Queue backlog elevated",
                    status="open",
                    opened_ms=1_700_000_000_000,
                    last_seen_ms=1_700_000_000_000,
                ),
            ),
        ))
        alerts = next(s for s in view.sections if s.title == "Alerts & Events")
        assert alerts.cards[0].detail == "corr-ui-test:backlog"
        assert alerts.cards[1].detail == "open: Queue backlog elevated"

    def test_alert_section_projects_operator_runtime_when_provided(self):
        view = build_light_dashboard_view(_payload(
            operator_runtime=OperatorRuntimeProjection(
                event_count=4,
                latest_event_type="critical_alert_acknowledged",
                latest_event_message="critical alert acknowledged",
                pending_notification_count=1,
                pending_notification_alert_ids=("corr-ui-test:loss",),
                acknowledged_notification_count=2,
                latest_acknowledged_alert_id="corr-ui-test:loss-prev",
            )
        ))
        alerts = next(s for s in view.sections if s.title == "Alerts & Events")
        assert alerts.cards[2].value == "4"
        assert alerts.cards[2].detail == "critical alert acknowledged"
        assert alerts.cards[3].value == "pending=1 / ack=2"
        assert alerts.cards[3].detail == "corr-ui-test:loss"
