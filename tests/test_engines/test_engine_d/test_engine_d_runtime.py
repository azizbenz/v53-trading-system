from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from engines.engine_d import (
    EngineDReentryValidationInput,
    EngineDReentryValidationOutcome,
    EngineDRuntime,
    EngineDRuntimeInput,
    EngineDRuntimeStatus,
)
from engines.engine_d.engine_d_runner import EngineDInput
from interface_contracts import EngineId, RegimeId, Side, SignalType
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker, KillSwitchReason
from risk_backbone.risk_runtime import RiskLimits, RiskRuntime
from scoring_backbone.hard_block_gate.blocker_evaluator import BlockerCondition
from scoring_backbone.penalty_aggregator.penalty_registry import (
    PenaltyDefinition,
    PenaltyRegistry,
    PenaltyType,
)
from scoring_backbone.penalty_aggregator.score_penalty_builder import ScorePenaltyItem
from scoring_backbone.penalty_aggregator.size_penalty_builder import SizePenaltyItem
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState
from scoring_backbone.scoring_runtime import ScoringCandidateInput, ScoringRuntime


def _good_engine_inputs(**overrides) -> EngineDInput:
    defaults = dict(
        pair="BTCUSDT",
        origin_context_id="ctx-btc-01",
        origin_trade_id="trade-btc-01",
        link_type="prior_trade",
        first_episode_id="episode-btc-01",
        first_episode_engine_id="engine_a",
        first_episode_close_reason="time_stop",
        consecutive_stop_count=1,
        last_stop_at_ns=1_700_000_000_000_000_000,
        last_fresh_a_detection_at_ns=1_700_000_100_000_000_000,
        anti_revenge_state="reset_required",
        prior_trade_quality=0.85,
        reformation_quality=0.77,
        pullback_quality=0.73,
        continuation_room=0.70,
        concentration_headroom=0.78,
        marginal_edge=0.72,
        reentry_lateness=0.18,
        structure_reformed_detected=True,
        regime="trending_up",
        regime_favorability=0.78,
        pair_health=0.90,
        data_freshness=0.94,
        flow_coherence=0.81,
        expected_gain=0.009,
        expected_cost=0.0020,
        candidate_size=800.0,
        holding_period=2.0,
        entry_price=104.0,
        reentry_anchor_price=101.5,
        atr=1.8,
        duplication_overlap_with_engine_a=0.24,
        marginal_portfolio_gain=6.0,
        covered_share_by_engine_a=0.18,
        scoring_version="engine_d.v1",
    )
    defaults.update(overrides)
    return EngineDInput(**defaults)


def _penalty_registry() -> PenaltyRegistry:
    registry = PenaltyRegistry()
    registry.register(PenaltyDefinition(penalty_id="context_soft", name="Context soft", penalty_type=PenaltyType.SCORE))
    registry.register(PenaltyDefinition(penalty_id="size_soft", name="Size soft", penalty_type=PenaltyType.SIZE))
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


def _portfolio_state(**overrides) -> PortfolioState:
    defaults = dict(
        remaining_gross_capacity=5000.0,
        remaining_loss_capacity=500.0,
        remaining_beta_capacity=5000.0,
        remaining_cluster_capacity={"btc_majors": 5000.0},
    )
    defaults.update(overrides)
    return PortfolioState(**defaults)


def _runtime_input(**overrides) -> EngineDRuntimeInput:
    defaults = dict(
        engine_inputs=_good_engine_inputs(),
        timestamp_ms=1_700_000_000_000,
        portfolio=_portfolio_state(),
        projected_size=800.0,
        projected_loss=40.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.7,
        cluster_id="btc_majors",
    )
    defaults.update(overrides)
    return EngineDRuntimeInput(**defaults)


def _breaker_state_dir(repo_tmp_path: Path, name: str) -> Path:
    state_dir = repo_tmp_path / name
    shutil.rmtree(state_dir, ignore_errors=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def _runtime(repo_tmp_path: Path, name: str, **overrides) -> EngineDRuntime:
    return EngineDRuntime(
        scoring_runtime=overrides.pop("scoring_runtime", _scoring_runtime()),
        risk_runtime=overrides.pop("risk_runtime", _risk_runtime()),
        circuit_breaker=overrides.pop(
            "circuit_breaker",
            EmergencyCircuitBreaker(state_dir=_breaker_state_dir(repo_tmp_path, name)),
        ),
        **overrides,
    )


def _blocking_reentry_hook(_: EngineDReentryValidationInput) -> EngineDReentryValidationOutcome:
    return EngineDReentryValidationOutcome(
        accepted=False,
        reason_codes=("ARTIFACT_REENTRY_BLOCK",),
        detail="artifact veto on engine_d re-entry validation",
        episode_reference_id="episode-btc-01",
        anti_revenge_state="cooldown_active",
        observability_tags=("backtest.anti_revenge_state",),
    )


def test_runtime_emits_signal_and_accepts_through_risk(repo_tmp_path: Path):
    runtime = _runtime(repo_tmp_path, "engine_d_accepts")
    result = runtime.evaluate(_runtime_input(), now=10.0)
    assert result.status == EngineDRuntimeStatus.ACCEPTED
    assert result.signal_candidate is not None
    assert result.signal_candidate.engine_id == EngineId.D
    assert result.signal_candidate.signal_type == SignalType.ENTRY
    assert result.signal_candidate.side == Side.BUY
    assert result.signal_candidate.regime == RegimeId.TRENDING_UP
    assert result.signal_candidate.reason == "engine_d:high:prior_trade:trade-btc-01"
    assert result.signal_candidate.stop_loss is not None
    assert result.signal_candidate.take_profit is not None
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is True
    accepted_log = next(entry for entry in result.log_entries if entry.event == "engine_d_accepted")
    assert accepted_log.origin_context_id == "ctx-btc-01"
    assert accepted_log.duplication_overlap_with_engine_a == 0.24


def test_runtime_blocks_before_scoring_when_circuit_breaker_is_tripped(repo_tmp_path: Path):
    breaker = EmergencyCircuitBreaker(state_dir=_breaker_state_dir(repo_tmp_path, "engine_d"))
    breaker.trip(KillSwitchReason.OPERATOR_MANUAL, "manual stop")
    runtime = EngineDRuntime(
        scoring_runtime=_scoring_runtime(),
        risk_runtime=_risk_runtime(),
        circuit_breaker=breaker,
    )

    result = runtime.evaluate(_runtime_input(), now=11.0)

    assert result.status == EngineDRuntimeStatus.CIRCUIT_BREAKER_BLOCKED
    assert result.signal_candidate is None
    assert result.scoring_round is None
    assert result.scoring_audit is None
    assert result.risk_evaluation is None
    assert result.engine_output.decision == "no_trade"
    assert any(entry.event == "engine_d_circuit_breaker_blocked" for entry in result.log_entries)


def test_runtime_requires_explicit_circuit_breaker():
    with pytest.raises(ValueError, match="requires a circuit_breaker"):
        EngineDRuntime(
            scoring_runtime=_scoring_runtime(),
            risk_runtime=_risk_runtime(),
            circuit_breaker=None,
        )


def test_runtime_rejects_blank_scoring_version(repo_tmp_path: Path):
    runtime = _runtime(repo_tmp_path, "engine_d_blank_version")

    with pytest.raises(ValueError, match="requires non-empty scoring_version"):
        runtime.evaluate(
            _runtime_input(engine_inputs=_good_engine_inputs(scoring_version="   ")),
            now=12.0,
        )


def test_runtime_can_be_blocked_by_reentry_validation_hook(repo_tmp_path: Path):
    runtime = _runtime(
        repo_tmp_path,
        "engine_d_hook_blocked",
        reentry_validation_hook=_blocking_reentry_hook,
    )

    result = runtime.evaluate(_runtime_input(), now=12.5)

    assert result.status == EngineDRuntimeStatus.HOOK_BLOCKED
    assert result.signal_candidate is None
    assert result.scoring_round is None
    blocked_logs = [entry for entry in result.log_entries if entry.event == "engine_d_hook_blocked"]
    assert len(blocked_logs) == 1
    assert blocked_logs[0].reasons == ("ARTIFACT_REENTRY_BLOCK",)
    assert result.hook_outcome is not None
    assert result.hook_outcome.episode_reference_id == "episode-btc-01"
    assert result.hook_outcome.anti_revenge_state == "cooldown_active"


def test_runtime_surfaces_anti_revenge_observability_for_backtest(repo_tmp_path: Path) -> None:
    captured: dict[str, EngineDReentryValidationInput] = {}

    def _capturing_hook(hook_input: EngineDReentryValidationInput) -> EngineDReentryValidationOutcome:
        captured["hook_input"] = hook_input
        return EngineDReentryValidationOutcome(
            accepted=True,
            episode_reference_id=hook_input.first_episode_id,
            anti_revenge_state=hook_input.anti_revenge_state,
            observability_tags=("backtest.anti_revenge_state", "backtest.episode_ref"),
        )

    runtime = _runtime(
        repo_tmp_path,
        "engine_d_backtest_observability",
        reentry_validation_hook=_capturing_hook,
    )

    result = runtime.evaluate(_runtime_input(), now=13.0)

    assert result.status == EngineDRuntimeStatus.ACCEPTED
    assert captured["hook_input"].first_episode_id == "episode-btc-01"
    assert captured["hook_input"].first_episode_engine_id == "engine_a"
    assert captured["hook_input"].first_episode_close_reason == "time_stop"
    assert captured["hook_input"].consecutive_stop_count == 1
    assert captured["hook_input"].anti_revenge_state == "reset_required"
    assert result.hook_outcome is not None
    assert result.hook_outcome.episode_reference_id == "episode-btc-01"
    assert result.hook_outcome.anti_revenge_state == "reset_required"
    accepted_log = next(entry for entry in result.log_entries if entry.event == "engine_d_accepted")
    assert accepted_log.first_episode_id == "episode-btc-01"
    assert accepted_log.anti_revenge_state == "reset_required"


def test_runtime_hard_blocked_logs_reasons(repo_tmp_path: Path):
    runtime = _runtime(repo_tmp_path, "engine_d_hard_blocked")
    result = runtime.evaluate(
        _runtime_input(blocker_conditions=BlockerCondition(is_stale_hard=True, is_pair_suspended=True)),
        now=20.0,
    )
    assert result.status == EngineDRuntimeStatus.HARD_BLOCKED
    joined = " ".join(
        reason
        for entry in result.log_entries
        if entry.event == "engine_d_hard_blocked"
        for reason in entry.reasons
    ).lower()
    assert "stale" in joined
    assert "suspended" in joined


def test_runtime_rejected_by_ranking_is_auditable(repo_tmp_path: Path):
    runtime = _runtime(repo_tmp_path, "engine_d_rejected_ranking")
    peer = ScoringCandidateInput(
        engine_id="engine_a",
        pair="ETHUSDT",
        raw_features={"structure": 0.99},
        allowed_features=frozenset({"structure"}),
        weights={"structure": 1.0},
        scoring_version="engine_a.v1",
        expected_cost=0.0005,
        expected_ce=0.003,
        projected_size=500.0,
        projected_loss=20.0,
        projected_beta_impact=0.0,
        cluster_id="eth_ecosystem",
    )
    result = runtime.evaluate(
        _runtime_input(
            peer_candidates=(peer,),
            max_selections=1,
            portfolio=_portfolio_state(remaining_cluster_capacity={"btc_majors": 5000.0, "eth_ecosystem": 5000.0}),
            score_penalties=(ScorePenaltyItem(penalty_id="context_soft", value=0.25, reason="context soft"),),
            size_penalties=(SizePenaltyItem(penalty_id="size_soft", multiplier=0.9, reason="size soft"),),
        ),
        now=30.0,
    )
    assert result.status == EngineDRuntimeStatus.REJECTED_RANKING
    assert any(entry.event == "engine_d_rejected_by_ranking" for entry in result.log_entries)


def test_runtime_rejected_by_portfolio_is_auditable(repo_tmp_path: Path):
    runtime = _runtime(repo_tmp_path, "engine_d_rejected_portfolio")
    result = runtime.evaluate(_runtime_input(portfolio=_portfolio_state(remaining_gross_capacity=10.0)), now=40.0)
    assert result.status == EngineDRuntimeStatus.REJECTED_PORTFOLIO
    assert any(entry.event == "engine_d_rejected_by_portfolio" for entry in result.log_entries)


def test_runtime_cannot_bypass_risk_runtime(repo_tmp_path: Path):
    risk_runtime = RiskRuntime(
        RiskLimits(
            gross_cap=500.0,
            position_cap=2000.0,
            loss_cap=500.0,
            beta_cap=5000.0,
            cluster_cap=5000.0,
        )
    )
    runtime = _runtime(repo_tmp_path, "engine_d_risk_runtime", risk_runtime=risk_runtime)
    result = runtime.evaluate(_runtime_input(projected_size=1000.0), now=50.0)
    assert result.status == EngineDRuntimeStatus.RISK_REJECTED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is False
