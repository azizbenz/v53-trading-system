"""Tests for the locked Build-10 Light UI backend surface."""

from __future__ import annotations

import ui
from interface_contracts import ProfileId, RuntimeMode
from monitoring import HealthDashboardPayload
from ui import build_light_dashboard_view


def _payload() -> HealthDashboardPayload:
    return HealthDashboardPayload(
        timestamp_ms=1_700_000_000_000,
        correlation_id="corr-ui",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        headline_status="warning",
        active_alert_count=3,
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


def test_ui_exports_expected_symbols():
    assert {
        "DashboardCard",
        "DashboardSection",
        "LockedControlSurface",
        "LightDashboardView",
        "build_light_dashboard_view",
    }.issubset(set(ui.__all__))


def test_light_dashboard_view_is_locked_and_structured():
    view = build_light_dashboard_view(_payload())
    titles = {section.title for section in view.sections}

    assert {"Health", "Portfolio", "Meta", "Future Learning"} == titles
    assert view.control_surface.profile_selector_enabled is False
    assert view.control_surface.engine_cd_toggle_enabled is False
    assert view.control_surface.complete_pairs_enabled is False
    assert view.control_surface.hard_guard_override_enabled is False


def test_light_dashboard_view_exposes_future_learning_panels_without_claiming_runtime():
    view = build_light_dashboard_view(_payload())
    future_cards = next(section for section in view.sections if section.title == "Future Learning")

    assert view.profile == ProfileId.LIGHT
    assert view.runtime_mode == RuntimeMode.SHADOW
    assert "build9x_diagnostics" in view.future_panels
    assert future_cards.cards[0].value == "2"
    assert future_cards.cards[1].value == "1"
