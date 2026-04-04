"""Tests for protocols.shadow_day_counter — HARD STATEMENT §0.6."""

import json
import pytest

from protocols.shadow_day_counter import (
    ShadowCounterState,
    ShadowDayCounter,
    ShadowDayRecord,
    ShadowProfile,
    _MAX_GAP_SECONDS,
)


pytestmark = pytest.mark.build1


BASE_TS = 1_700_000_000.0  # Reference timestamp
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
        metrics[f"{engine_id}.estimated_cost_bps"] = 4.0 + 0.1 * day_index
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
    for reader_name, signal_family, observed_value, severity_score, status in (
        ("market_toxicity_snapshot", "microstructure", 0.46, 0.5, "elevated"),
        ("execution_fragility_score", "ai_edge", 0.42, 0.5, "elevated"),
        ("lob_deep_filter_vwa", "microstructure", 0.28, 0.0, "nominal"),
        ("order_book_imbalance", "microstructure", 0.19, 0.0, "nominal"),
        ("false_breakout_model", "microstructure", 0.31, 0.0, "nominal"),
        ("hurst_regime_classifier", "regime", 0.47, 0.5, "elevated"),
        ("competition_monitor", "risk", 0.18, 0.0, "nominal"),
    ):
        metric_prefix = f"build14_reader.{reader_name}"
        metrics[f"{metric_prefix}.observed_value"] = observed_value
        metrics[f"{metric_prefix}.severity_score"] = severity_score
        metrics[f"{metric_prefix}.status"] = status
        metrics[f"{metric_prefix}.signal_family"] = signal_family
        metrics[f"{metric_prefix}.detail"] = f"{reader_name} detail"
        metrics[f"{metric_prefix}.structured_log_key"] = (
            f"build14.shadow_enabled.{reader_name}"
        )
    return metrics


@pytest.fixture
def counter_dir(repo_tmp_path):
    return repo_tmp_path


class TestDayCountIncrement:
    """Correct day counting."""

    def test_first_day_increments_to_1(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        rec = c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        assert rec.day_number == 1
        assert rec.passed_all_gates is True
        assert c.get_status().consecutive_days == 1

    def test_consecutive_days_increment(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        for i in range(5):
            c.record_shadow_day(passed_all_gates=True, now=BASE_TS + i * ONE_DAY * 0.9)
        assert c.get_status().consecutive_days == 5

    def test_failed_gate_does_not_count(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        rec = c.record_shadow_day(passed_all_gates=False, now=BASE_TS + ONE_DAY * 0.5)
        assert rec.passed_all_gates is False
        assert c.get_status().consecutive_days == 1  # unchanged

    def test_30_days_reaches_promotion(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        for i in range(30):
            c.record_shadow_day(passed_all_gates=True, now=BASE_TS + i * ONE_DAY * 0.9)
        assert c.is_promotion_ready() is True
        assert c.get_status().remaining_days == 0

    def test_29_days_not_ready(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        for i in range(29):
            c.record_shadow_day(passed_all_gates=True, now=BASE_TS + i * ONE_DAY * 0.9)
        assert c.is_promotion_ready() is False
        assert c.get_status().remaining_days == 1


class TestGapReset:
    """24h gap resets counter — HARD STATEMENT."""

    def test_gap_over_24h_resets(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS + ONE_DAY * 0.5)
        assert c.get_status().consecutive_days == 2
        # Gap > 24h
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS + ONE_DAY * 3)
        assert c.get_status().consecutive_days == 1  # reset then +1
        assert c.get_status().resets == 1

    def test_exactly_24h_does_not_reset(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        # Exactly 24h gap is NOT > 24h
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS + _MAX_GAP_SECONDS)
        assert c.get_status().consecutive_days == 2
        assert c.get_status().resets == 0

    def test_just_over_24h_resets(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        # 24h + 1 second
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS + _MAX_GAP_SECONDS + 1)
        assert c.get_status().consecutive_days == 1
        assert c.get_status().resets == 1

    def test_multiple_resets_tracked(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        for reset_round in range(3):
            c.record_shadow_day(passed_all_gates=True, now=BASE_TS + reset_round * ONE_DAY * 5)
        assert c.get_status().resets == 2  # 2 gaps > 24h


class TestPersistence:
    """State survives restart."""

    def test_persist_and_reload(self, counter_dir):
        c1 = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        for i in range(10):
            c1.record_shadow_day(passed_all_gates=True, now=BASE_TS + i * ONE_DAY * 0.5)
        # Simulate restart
        c2 = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        assert c2.get_status().consecutive_days == 10

    def test_state_file_is_valid_json(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        state_file = counter_dir / "shadow_counter_light.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["consecutive_days"] == 1
        assert data["profile"] == "light"

    def test_complete_profile_separate_file(self, counter_dir):
        c_light = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c_complete = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.COMPLETE)
        c_light.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        c_complete.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        c_complete.record_shadow_day(passed_all_gates=True, now=BASE_TS + 1000)
        assert c_light.get_status().consecutive_days == 1
        assert c_complete.get_status().consecutive_days == 2

    def test_corrupted_state_starts_fresh(self, counter_dir):
        state_file = counter_dir / "shadow_counter_light.json"
        state_file.write_text("CORRUPTED!!!", encoding="utf-8")
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        assert c.get_status().consecutive_days == 0


class TestReport:
    """Report generation."""

    def test_generate_report_structure(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        report = c.generate_report()
        assert report["profile"] == "light"
        assert report["consecutive_days"] == 1
        assert report["required_days"] == 30
        assert report["remaining_days"] == 29
        assert report["is_complete"] is False

    def test_save_report_creates_file(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        report_path = c.save_report()
        assert report_path.exists()
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["consecutive_days"] == 1
        assert data["shadow_report_ready"] is False

    def test_report_at_30_days_shows_complete(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.COMPLETE)
        for i in range(30):
            c.record_shadow_day(passed_all_gates=True, now=BASE_TS + i * ONE_DAY * 0.5)
        report = c.generate_report()
        assert report["is_complete"] is True
        assert report["remaining_days"] == 0

    def test_report_ready_requires_full_build11_sections(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        for i in range(30):
            c.record_shadow_day(
                passed_all_gates=True,
                metrics_summary=_complete_shadow_metrics(i),
                now=BASE_TS + i * ONE_DAY * 0.5,
            )
        report = c.generate_report()
        assert report["shadow_report_ready"] is True
        assert report["data_infra_report_ready"] is True
        assert report["decisions_dtr_report_ready"] is True
        assert report["costs_break_even_report_ready"] is True
        assert report["portfolio_report_ready"] is True
        assert report["ui_alerting_report_ready"] is True
        assert report["go_no_go_report_ready"] is True
        assert report["inter_engine_comparison_ready"] is True
        assert report["build14_contribution_ready"] is True
        assert report["dominant_cluster"] == "majors"
        assert report["phantom_trade_count"] == 0
        assert len(report["rendered_sections"]) == 7
        assert len(report["inter_engine_comparison"]) == 4
        assert len(report["build14_contribution"]) == 5
        assert len(report["build14_reader_contribution"]) == 7
        assert report["build14_reader_contribution"][0]["reader_name"] == "market_toxicity_snapshot"


class TestMetricsSummary:
    """Metrics recording in day records."""

    def test_metrics_recorded_in_day(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        metrics = {"pnl": 0.02, "sharpe": 1.5}
        rec = c.record_shadow_day(passed_all_gates=True, metrics_summary=metrics, now=BASE_TS)
        assert rec.metrics_summary == metrics
