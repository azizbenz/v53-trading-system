"""
BS-next regression tests — engine_c_runtime.py
Guard: next() without default would raise StopIteration when scoring audit is absent.
Fix: next(..., None) + explicit HARD_BLOCKED return path.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from engines.engine_c import EngineCRuntime, EngineCRuntimeInput, EngineCRuntimeStatus
from engines.engine_c.engine_c_runner import EngineCInput
from interface_contracts import EngineId, Side
from protocols.engine_coordination_rules import EngineCoordinationInput, evaluate_engine_coordination
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker
from risk_backbone.risk_runtime import RiskLimits, RiskRuntime
from scoring_backbone.hard_block_gate.blocker_reporter import BlockerStats
from scoring_backbone.penalty_aggregator.penalty_registry import (
    PenaltyDefinition,
    PenaltyRegistry,
    PenaltyType,
)
from scoring_backbone.penalty_aggregator.penalty_reporter import PenaltyStats
from scoring_backbone.ranking_router.candidate_pool_builder import CandidatePool
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState
from scoring_backbone.ranking_router.ranking_reporter import RankingStats
from scoring_backbone.ranking_router.selection_resolver import SelectionResult
from scoring_backbone.raw_score_builder.score_reporter import ScoreStats
from scoring_backbone.scoring_runtime import ScoringRoundResult, ScoringRuntime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _good_engine_inputs(**overrides) -> EngineCInput:
    defaults = dict(
        pair="BTCUSDT",
        breakout_strength=0.88,
        range_quality=0.78,
        compression_quality=0.74,
        volume_confirmation=0.81,
        followthrough_room=0.76,
        extension_pct=0.24,
        retrace_risk=0.18,
        rejection_wick_ratio=0.12,
        regime="breakout",
        regime_favorability=0.80,
        pair_health=0.92,
        data_freshness=0.95,
        flow_coherence=0.79,
        expected_gain=0.012,
        expected_cost=0.0025,
        candidate_size=1000.0,
        holding_period=3.0,
        entry_price=105.0,
        breakout_level=101.0,
        range_low=97.5,
        range_high=101.0,
        realized_vol_current=2.0 / 105.0,
        realized_vol_at_break=2.0 / 105.0,
        atr=2.0,
        engine_a_overlap_ratio=0.28,
        marginal_portfolio_gain=9.2,
        covered_share_by_engine_a=0.22,
        keff_contribution=0.31,
        scoring_version="engine_c.v1",
    )
    defaults.update(overrides)
    return EngineCInput(**defaults)


def _penalty_registry() -> PenaltyRegistry:
    registry = PenaltyRegistry()
    registry.register(PenaltyDefinition(penalty_id="ctx_soft", name="Context soft", penalty_type=PenaltyType.SCORE))
    return registry


def _scoring_runtime() -> ScoringRuntime:
    return ScoringRuntime(_penalty_registry())


def _risk_runtime() -> RiskRuntime:
    return RiskRuntime(
        RiskLimits(
            gross_cap=5000.0,
            position_cap=3000.0,
            loss_cap=500.0,
            beta_cap=5000.0,
            cluster_cap=5000.0,
        )
    )


def _portfolio_state() -> PortfolioState:
    return PortfolioState(
        remaining_gross_capacity=5000.0,
        remaining_loss_capacity=500.0,
        remaining_beta_capacity=5000.0,
        remaining_cluster_capacity={"btc_majors": 5000.0},
    )


def _runtime_input(**overrides) -> EngineCRuntimeInput:
    defaults = dict(
        engine_inputs=_good_engine_inputs(),
        timestamp_ms=1_700_000_000_000,
        portfolio=_portfolio_state(),
        projected_size=1000.0,
        projected_loss=50.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.8,
        cluster_id="btc_majors",
        coordination_input=_coordination_input_c(),
    )
    defaults.update(overrides)
    return EngineCRuntimeInput(**defaults)


def _coordination_input_c(**overrides: object) -> EngineCoordinationInput:
    defaults = dict(
        evaluated_at_ns=1_700_000_000_000_000_000,
        engine_id=EngineId.C,
        pair="BTCUSDT",
        side=Side.BUY,
    )
    defaults.update(overrides)
    return EngineCoordinationInput(**defaults)


def _breaker_state_dir(repo_tmp_path: Path, name: str) -> Path:
    state_dir = repo_tmp_path / ".codex_kill_switch_tests" / name
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def _runtime(repo_tmp_path: Path, name: str, **overrides) -> EngineCRuntime:
    return EngineCRuntime(
        scoring_runtime=overrides.pop("scoring_runtime", _scoring_runtime()),
        risk_runtime=overrides.pop("risk_runtime", _risk_runtime()),
        circuit_breaker=overrides.pop(
            "circuit_breaker",
            EmergencyCircuitBreaker(state_dir=_breaker_state_dir(repo_tmp_path, name)),
        ),
        coordination_evaluator=overrides.pop("coordination_evaluator", evaluate_engine_coordination),
        **overrides,
    )


def _empty_scoring_round() -> ScoringRoundResult:
    """Minimal valid ScoringRoundResult with no audits — triggers missing-audit path."""
    return ScoringRoundResult(
        audits=(),
        candidate_pool=CandidatePool(),
        selection_result=SelectionResult(),
        score_stats=ScoreStats(),
        penalty_stats=PenaltyStats(),
        blocker_stats=BlockerStats(),
        ranking_stats=RankingStats(),
    )


# ---------------------------------------------------------------------------
# BS-next regression tests
# ---------------------------------------------------------------------------

def test_missing_audit_returns_hard_blocked_not_stop_iteration(repo_tmp_path: Path):
    """
    BS-next: When scoring_round.audits yields no engine_c/BTCUSDT match,
    runtime must return HARD_BLOCKED instead of raising StopIteration.
    """
    runtime = _runtime(repo_tmp_path, "engine_c_bs_next_hard_block")

    with patch.object(runtime._scoring_runtime, "run_round", return_value=_empty_scoring_round()):
        result = runtime.evaluate(_runtime_input(), now=10.0)

    assert result.status == EngineCRuntimeStatus.HARD_BLOCKED
    assert result.scoring_audit is None
    assert result.risk_evaluation is None


def test_missing_audit_emits_diagnostic_log_entry(repo_tmp_path: Path):
    """
    BS-next: The HARD_BLOCKED path must log event='engine_c_scoring_audit_missing'
    with a human-readable reason.
    """
    runtime = _runtime(repo_tmp_path, "engine_c_bs_next_log")

    with patch.object(runtime._scoring_runtime, "run_round", return_value=_empty_scoring_round()):
        result = runtime.evaluate(_runtime_input(), now=10.0)

    audit_missing_logs = [e for e in result.log_entries if e.event == "engine_c_scoring_audit_missing"]
    assert len(audit_missing_logs) == 1
    assert any("hard blocked" in r.lower() for r in audit_missing_logs[0].reasons)


def test_missing_audit_preserves_signal_candidate(repo_tmp_path: Path):
    """
    BS-next: The signal candidate built before the scoring round is preserved in
    the HARD_BLOCKED result for auditability.
    """
    runtime = _runtime(repo_tmp_path, "engine_c_bs_next_signal")

    with patch.object(runtime._scoring_runtime, "run_round", return_value=_empty_scoring_round()):
        result = runtime.evaluate(_runtime_input(), now=10.0)

    assert result.signal_candidate is not None
    assert result.signal_candidate.pair == "BTCUSDT"


def test_missing_audit_scoring_round_still_attached(repo_tmp_path: Path):
    """
    BS-next: Even on HARD_BLOCKED the scoring_round itself is preserved in the
    result so callers can inspect the empty/mismatched round.
    """
    runtime = _runtime(repo_tmp_path, "engine_c_bs_next_round")
    empty_round = _empty_scoring_round()

    with patch.object(runtime._scoring_runtime, "run_round", return_value=empty_round):
        result = runtime.evaluate(_runtime_input(), now=10.0)

    assert result.scoring_round is empty_round


def test_missing_audit_no_risk_evaluation(repo_tmp_path: Path):
    """
    BS-next: Risk evaluation must NOT run when the scoring audit is absent —
    the HARD_BLOCKED return must happen before reaching risk.
    """
    runtime = _runtime(repo_tmp_path, "engine_c_bs_next_no_risk")

    with patch.object(runtime._scoring_runtime, "run_round", return_value=_empty_scoring_round()):
        result = runtime.evaluate(_runtime_input(), now=10.0)

    assert result.risk_evaluation is None


def test_normal_path_not_affected_by_fix(repo_tmp_path: Path):
    """
    BS-next: Verify the normal acceptance path still works after the fix is in place.
    Real scoring runtime produces the correct audit — must be ACCEPTED.
    """
    runtime = _runtime(repo_tmp_path, "engine_c_bs_next_normal")
    result = runtime.evaluate(_runtime_input(), now=10.0)

    assert result.status == EngineCRuntimeStatus.ACCEPTED
    assert result.scoring_audit is not None
    assert result.scoring_audit.engine_id == "engine_c"
    assert result.scoring_audit.pair == "BTCUSDT"
