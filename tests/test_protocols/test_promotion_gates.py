"""Tests for protocols.promotion_gates - HARD STATEMENT §0.6."""

import pytest

from protocols.promotion_gates import (
    PromotionGateResult,
    check_all_gates,
    check_complete_to_live,
    check_complete_to_micro_live,
    check_light_to_micro_live,
)
from protocols.shadow_day_counter import ShadowDayCounter, ShadowProfile


pytestmark = pytest.mark.build1


BASE_TS = 1_700_000_000.0
ONE_DAY = 86_400.0


def _complete_shadow_metrics(day_index: int) -> dict[str, float]:
    metrics: dict[str, float | str] = {
        "dtr_coverage": 1.0,
        "ce_net": 0.0012 + day_index * 0.000001,
        "estimated_cost_bps": 4.2,
        "edge_net": 0.0015,
        "drawdown_pct": 0.018,
        "stale_rate": 0.01,
        "economic_pass_rate": 0.67,
        "pair_health_ratio": 0.98,
        "backlog_avg": 2.0,
        "capital_simulated_usdt": 10_000.0,
        "gross_exposure_shadow_pct": 32.0,
        "loss_budget_shadow_pct": 11.0,
        "capital_free_usdt": 6_800.0,
        "beta_btc_shadow": 0.27,
        "dominant_cluster": "majors",
        "pnl_shadow": 12.5 + day_index,
        "dtr_loss_rate": 0.0,
        "log_loss_rate": 0.0,
        "event_latency_ms": 42.0,
        "hard_block_rate": 0.18,
        "phantom_trade_count": 0.0,
        "dtr_complete": 1.0,
        "decisions_reproducible": 1.0,
        "infra_stable": 1.0,
        "costs_plausible": 1.0,
        "break_even_visible": 1.0,
        "critical_alerts_visible": 1.0,
        "operator_actions_logged": 1.0,
        "ui_locked": 1.0,
        "go_no_go_rendered": 1.0,
    }
    for engine_id, gross_frequency in (
        ("engine_a", 8.0),
        ("engine_b", 7.0),
        ("engine_c", 6.0),
        ("engine_d", 5.0),
    ):
        metrics[f"{engine_id}.gross_frequency"] = gross_frequency
        metrics[f"{engine_id}.useful_frequency"] = gross_frequency * 0.4
        metrics[f"{engine_id}.estimated_cost_bps"] = 4.0
        metrics[f"{engine_id}.edge_net"] = 0.0012
        metrics[f"{engine_id}.economic_pass_rate"] = 0.66
        metrics[f"{engine_id}.conflict_rate"] = 0.04
        metrics[f"{engine_id}.marginal_edge"] = 0.0003
    for component_id, contribution_score in (
        ("build14_microstructure", 0.32),
        ("build14_regime", 0.28),
        ("build14_covariance", 0.25),
        ("build14_risk_contribution", 0.22),
        ("build14_edge_diversity", 0.20),
    ):
        metrics[f"{component_id}.contribution_score"] = contribution_score
        metrics[f"{component_id}.interaction_score"] = 0.08
    return metrics


@pytest.fixture
def gate_dir(repo_tmp_path):
    return repo_tmp_path


def _fill_shadow_days(
    state_dir,
    profile: ShadowProfile,
    count: int,
    *,
    with_complete_report: bool = False,
):
    """Helper: record N consecutive passing shadow days."""
    counter = ShadowDayCounter(state_dir=state_dir, profile=profile)
    for i in range(count):
        counter.record_shadow_day(
            passed_all_gates=True,
            metrics_summary=_complete_shadow_metrics(i) if with_complete_report else None,
            now=BASE_TS + i * ONE_DAY * 0.5,
        )


class TestLightToMicroLive:
    """Legacy compatibility LIGHT -> Micro-live gate."""

    def test_rejects_with_zero_days(self, gate_dir):
        result = check_light_to_micro_live(gate_dir)
        assert result.passed is False
        assert result.consecutive_days == 0
        assert result.remaining_days == 30
        assert "BLOCKED" in result.message

    def test_rejects_with_29_days(self, gate_dir):
        _fill_shadow_days(gate_dir, ShadowProfile.LIGHT, 29)
        result = check_light_to_micro_live(gate_dir)
        assert result.passed is False
        assert result.remaining_days == 1
        assert "1 days remaining" in result.message

    def test_accepts_with_30_days(self, gate_dir):
        _fill_shadow_days(
            gate_dir, ShadowProfile.LIGHT, 30, with_complete_report=True
        )
        result = check_light_to_micro_live(gate_dir)
        assert result.passed is True
        assert result.consecutive_days == 30
        assert result.remaining_days == 0
        assert result.message == "PASSED"

    def test_accepts_with_more_than_30_days(self, gate_dir):
        _fill_shadow_days(
            gate_dir, ShadowProfile.LIGHT, 35, with_complete_report=True
        )
        result = check_light_to_micro_live(gate_dir)
        assert result.passed is True

    def test_blocks_30_days_without_complete_shadow_report(self, gate_dir):
        _fill_shadow_days(gate_dir, ShadowProfile.LIGHT, 30)
        result = check_light_to_micro_live(gate_dir)
        assert result.passed is False
        assert "shadow report incomplete" in result.message

    def test_gate_name(self, gate_dir):
        result = check_light_to_micro_live(gate_dir)
        assert result.gate_name == "light_shadow_30j"
        assert result.profile == "light"


class TestCompleteToMicroLive:
    """Canonical COMPLETE -> Micro-live gate."""

    def test_rejects_with_zero_days(self, gate_dir):
        result = check_complete_to_micro_live(gate_dir)
        assert result.passed is False
        assert "BLOCKED" in result.message

    def test_rejects_with_15_days(self, gate_dir):
        _fill_shadow_days(gate_dir, ShadowProfile.COMPLETE, 15)
        result = check_complete_to_micro_live(gate_dir)
        assert result.passed is False
        assert result.remaining_days == 15

    def test_accepts_with_30_days(self, gate_dir):
        _fill_shadow_days(
            gate_dir, ShadowProfile.COMPLETE, 30, with_complete_report=True
        )
        result = check_complete_to_micro_live(gate_dir)
        assert result.passed is True
        assert result.message == "PASSED"

    def test_gate_name(self, gate_dir):
        result = check_complete_to_micro_live(gate_dir)
        assert result.gate_name == "complete_shadow_30j_for_micro_live"
        assert result.profile == "complete"


class TestCompleteToLive:
    """Canonical COMPLETE -> Live gate."""

    def test_rejects_with_zero_days(self, gate_dir):
        result = check_complete_to_live(gate_dir)
        assert result.passed is False
        assert "BLOCKED" in result.message

    def test_rejects_with_15_days(self, gate_dir):
        _fill_shadow_days(gate_dir, ShadowProfile.COMPLETE, 15)
        result = check_complete_to_live(gate_dir)
        assert result.passed is False
        assert result.remaining_days == 15

    def test_accepts_with_30_days(self, gate_dir):
        _fill_shadow_days(
            gate_dir, ShadowProfile.COMPLETE, 30, with_complete_report=True
        )
        result = check_complete_to_live(gate_dir)
        assert result.passed is True
        assert result.message == "PASSED"

    def test_gate_name(self, gate_dir):
        result = check_complete_to_live(gate_dir)
        assert result.gate_name == "complete_shadow_30j"
        assert result.profile == "complete"


class TestCheckAllGates:
    """Compatibility aggregate gate check."""

    def test_both_fail_with_empty_state(self, gate_dir):
        results = check_all_gates(gate_dir)
        assert len(results) == 2
        assert all(not result.passed for result in results)

    def test_light_passes_complete_fails(self, gate_dir):
        _fill_shadow_days(
            gate_dir, ShadowProfile.LIGHT, 30, with_complete_report=True
        )
        results = check_all_gates(gate_dir)
        light_result = [result for result in results if result.profile == "light"][0]
        complete_result = [result for result in results if result.profile == "complete"][0]
        assert light_result.passed is True
        assert complete_result.passed is False

    def test_both_pass(self, gate_dir):
        _fill_shadow_days(
            gate_dir, ShadowProfile.LIGHT, 30, with_complete_report=True
        )
        _fill_shadow_days(
            gate_dir, ShadowProfile.COMPLETE, 30, with_complete_report=True
        )
        results = check_all_gates(gate_dir)
        assert all(result.passed for result in results)


class TestResetTracking:
    """Reset count visible in gate results."""

    def test_resets_tracked_in_result(self, gate_dir):
        counter = ShadowDayCounter(state_dir=gate_dir, profile=ShadowProfile.LIGHT)
        counter.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        counter.record_shadow_day(passed_all_gates=True, now=BASE_TS + 200_000)
        result = check_light_to_micro_live(gate_dir)
        assert result.total_resets >= 1

