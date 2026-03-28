"""Tests for UI contracts and dashboard view edge cases."""

from __future__ import annotations

from interface_contracts import ProfileId, RuntimeMode
from monitoring import HealthDashboardPayload
from ui import build_light_dashboard_view
from ui.contracts import DashboardCard, DashboardSection, LightDashboardView, LockedControlSurface


def _payload(**overrides) -> HealthDashboardPayload:
    defaults = dict(
        timestamp_ms=1_700_000_000_000,
        correlation_id="corr-ui-test",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        headline_status="healthy",
        active_alert_count=0,
        stale_pair_count=0,
        queue_backlog=0,
        capital_deployed_usdt=1000.0,
        gross_capacity_used_pct=25.0,
        loss_capacity_used_pct=5.0,
        ce_net=0.001,
        dtr_coverage=0.95,
        cra_sterilization_rate=0.05,
        break_even_drift_scopes=(),
        edge_credible_count=2,
        edge_degraded_count=0,
        edge_surveillance_count=0,
        future_learning_diagnostics=0,
        future_learning_hypotheses=0,
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
        assert len(portfolio.cards) == 2
        assert portfolio.cards[0].key == "capital_deployed"
        assert portfolio.cards[1].key == "ce_net"

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

    def test_exactly_four_sections(self):
        view = build_light_dashboard_view(_payload())
        assert len(view.sections) == 4


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
        assert portfolio.cards[1].status == "warning"

    def test_positive_ce_shows_healthy(self):
        view = build_light_dashboard_view(_payload(ce_net=0.001))
        portfolio = next(s for s in view.sections if s.title == "Portfolio")
        assert portfolio.cards[1].status == "healthy"

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
