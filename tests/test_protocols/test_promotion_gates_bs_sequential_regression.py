"""
BS-gates regression tests — promotion_gates.py
Guard: check_complete_to_live was functionally identical to check_complete_to_micro_live
(both called the same underlying gate). Fix: live gate chains on micro-live gate,
enforcing sequential promotion: shadow → micro-live → live.
"""

from __future__ import annotations

import pytest

from protocols.promotion_gates import check_complete_to_live, check_complete_to_micro_live
from protocols.shadow_day_counter import ShadowDayCounter, ShadowProfile


BASE_TS = 1_700_000_000.0
ONE_DAY = 86_400.0


def _complete_shadow_metrics(day_index: int) -> dict:
    metrics: dict = {
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
        ("engine_a", 8.0), ("engine_b", 7.0), ("engine_c", 6.0), ("engine_d", 5.0),
    ):
        metrics[f"{engine_id}.gross_frequency"] = gross_frequency
        metrics[f"{engine_id}.useful_frequency"] = gross_frequency * 0.4
        metrics[f"{engine_id}.estimated_cost_bps"] = 4.0
        metrics[f"{engine_id}.edge_net"] = 0.0012
        metrics[f"{engine_id}.economic_pass_rate"] = 0.66
        metrics[f"{engine_id}.conflict_rate"] = 0.04
        metrics[f"{engine_id}.marginal_edge"] = 0.0003
    for component_id, score in (
        ("build14_microstructure", 0.32), ("build14_regime", 0.28),
        ("build14_covariance", 0.25), ("build14_risk_contribution", 0.22),
        ("build14_edge_diversity", 0.20),
    ):
        metrics[f"{component_id}.contribution_score"] = score
        metrics[f"{component_id}.interaction_score"] = 0.08
    return metrics


def _fill_complete_days(state_dir, count: int, *, with_report: bool = False) -> None:
    counter = ShadowDayCounter(state_dir=state_dir, profile=ShadowProfile.COMPLETE)
    for i in range(count):
        counter.record_shadow_day(
            passed_all_gates=True,
            metrics_summary=_complete_shadow_metrics(i) if with_report else None,
            now=BASE_TS + i * ONE_DAY * 0.5,
        )


# ---------------------------------------------------------------------------
# BS-gates regression tests
# ---------------------------------------------------------------------------

def test_live_gate_blocked_when_micro_live_gate_blocked(repo_tmp_path):
    """
    BS-gates: When micro-live gate is blocked (0 days), live gate must also be blocked.
    Before the fix, both gates were identical — this still holds, but is now explicit.
    """
    ml = check_complete_to_micro_live(repo_tmp_path)
    live = check_complete_to_live(repo_tmp_path)

    assert ml.passed is False
    assert live.passed is False


def test_live_gate_message_references_micro_live_when_blocked(repo_tmp_path):
    """
    BS-gates: The live gate message must explain that the block comes from the
    micro-live prerequisite, giving operators a clear diagnostic.
    """
    live = check_complete_to_live(repo_tmp_path)

    assert live.passed is False
    assert "micro-live gate not passed" in live.message


def test_live_gate_carries_remaining_days_from_micro_live(repo_tmp_path):
    """
    BS-gates: The remaining_days in the live gate result must reflect the
    micro-live gate's value so the operator knows how many days are left.
    """
    _fill_complete_days(repo_tmp_path, 15)

    ml = check_complete_to_micro_live(repo_tmp_path)
    live = check_complete_to_live(repo_tmp_path)

    assert ml.passed is False
    assert live.remaining_days == ml.remaining_days


def test_live_gate_passes_only_after_micro_live_gate_passes(repo_tmp_path):
    """
    BS-gates: Live gate must pass when micro-live gate passes.
    Confirms the sequential chain: 30 shadow days → both gates pass together.
    """
    _fill_complete_days(repo_tmp_path, 30, with_report=True)

    ml = check_complete_to_micro_live(repo_tmp_path)
    live = check_complete_to_live(repo_tmp_path)

    assert ml.passed is True
    assert live.passed is True


def test_live_gate_name_and_profile_unchanged(repo_tmp_path):
    """
    BS-gates: The gate_name and profile of check_complete_to_live must remain
    unchanged after the fix — existing callers must not break.
    """
    live = check_complete_to_live(repo_tmp_path)

    assert live.gate_name == "complete_shadow_30j"
    assert live.profile == "complete"


def test_live_gate_cannot_pass_before_micro_live(repo_tmp_path):
    """
    BS-gates: Core invariant — live.passed implies micro_live.passed.
    (The reverse is allowed: micro_live can pass without live having been called.)
    """
    _fill_complete_days(repo_tmp_path, 30, with_report=True)

    ml = check_complete_to_micro_live(repo_tmp_path)
    live = check_complete_to_live(repo_tmp_path)

    if live.passed:
        assert ml.passed, "live gate passed but micro-live gate did not — sequential chain violated"
