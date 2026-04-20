from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from engines.engine_d import (
    ConsecutiveStopStateD,
    EngineDRuntime,
    EngineDResetStateStatus,
    assemble_engine_d_coordination_input,
    record_engine_d_stop,
)
from engines.engine_d.engine_d_runtime import EngineDRuntimeInput
from engines.engine_d.engine_d_runner import EngineDInput
from interface_contracts import BetStructure, EngineId, ForecastHorizonClass, ForecastTargetClass, Side
from protocols.closed_episode_journal import ClosedEpisodeJournal, EpisodeCloseReason, EpisodeRef
from protocols.engine_coordination_rules import EngineCoordinationInput, evaluate_engine_coordination
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker
from risk_backbone.risk_runtime import RiskLimits, RiskRuntime
from scoring_backbone.penalty_aggregator.penalty_registry import PenaltyRegistry
from scoring_backbone.scoring_runtime import ScoringRuntime


_NOW_NS = 1_700_000_000_000_000_000


def _episode_ref(
    suffix: int,
    *,
    close_reason: EpisodeCloseReason = EpisodeCloseReason.TIME_STOP,
    closed_at_ns: int | None = None,
) -> EpisodeRef:
    return EpisodeRef(
        episode_id=UUID(f"31111111-1111-1111-1111-{suffix:012d}"),
        engine_id_of_origin=EngineId.A,
        pair="BTCUSDT",
        side=Side.BUY,
        entry_level=Decimal("100.0"),
        exit_level=Decimal("104.0"),
        bet_structure=BetStructure.DIRECTIONAL_LONG,
        forecast_horizon_class=ForecastHorizonClass.SHORT,
        forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
        closed_at_ns=closed_at_ns or (_NOW_NS + suffix),
        close_reason=close_reason,
        realized_pnl_decimal=Decimal("4.0"),
    )


def _journal_with_episode(*episodes: EpisodeRef) -> ClosedEpisodeJournal:
    journal = ClosedEpisodeJournal()
    journal.append_batch(tuple(episodes))
    return journal


def _engine_inputs() -> EngineDInput:
    return EngineDInput(
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
        realized_vol_current=1.8 / 104.0,
        realized_vol_post_close=1.8 / 104.0,
        atr=1.8,
        duplication_overlap_with_engine_a=0.24,
        marginal_portfolio_gain=6.0,
        covered_share_by_engine_a=0.18,
        scoring_version="engine_d.v1",
    )


def _runtime_input(coordination_input: EngineCoordinationInput | None) -> EngineDRuntimeInput:
    return EngineDRuntimeInput(
        engine_inputs=_engine_inputs(),
        timestamp_ms=1_700_000_000_000,
        portfolio={"remaining_gross_capacity": 5000.0, "remaining_loss_capacity": 500.0, "remaining_beta_capacity": 5000.0, "remaining_cluster_capacity": {"btc_majors": 5000.0}},
        projected_size=800.0,
        projected_loss=40.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.7,
        cluster_id="btc_majors",
        coordination_input=coordination_input,
    )


def _runtime(repo_tmp_path: Path) -> EngineDRuntime:
    return EngineDRuntime(
        scoring_runtime=ScoringRuntime(PenaltyRegistry()),
        risk_runtime=RiskRuntime(
            RiskLimits(
                gross_cap=5000.0,
                position_cap=3000.0,
                loss_cap=500.0,
                beta_cap=5000.0,
                cluster_cap=5000.0,
            )
        ),
        circuit_breaker=EmergencyCircuitBreaker(state_dir=repo_tmp_path / "breaker"),
        coordination_evaluator=evaluate_engine_coordination,
    )


def test_assembler_resolves_first_episode_and_builds_coordination_input() -> None:
    journal = _journal_with_episode(
        _episode_ref(1, closed_at_ns=_NOW_NS - 20),
        _episode_ref(2, close_reason=EpisodeCloseReason.STOP_OUT, closed_at_ns=_NOW_NS - 10),
        _episode_ref(3, closed_at_ns=_NOW_NS - 5),
    )
    stop_state = record_engine_d_stop(ConsecutiveStopStateD(), stopped_at_ns=_NOW_NS - 100)

    assembly = assemble_engine_d_coordination_input(
        coordination_input_factory=EngineCoordinationInput,
        journal=journal,
        evaluated_at_ns=_NOW_NS,
        pair="btcusdt",
        side=Side.BUY,
        stop_state=stop_state,
        reference_size=800.0,
    )

    assert assembly.first_episode_resolution.found is True
    assert assembly.first_episode_resolution.episode_ref is not None
    assert assembly.first_episode_resolution.episode_ref.episode_id == _episode_ref(3, closed_at_ns=_NOW_NS - 5).episode_id
    assert assembly.coordination_input.first_episode_ref is not None
    assert assembly.coordination_input.consecutive_d_stop_count == 1
    assert assembly.reset_state_inspection.status == EngineDResetStateStatus.RESET_REQUIRED
    assert assembly.reset_state_inspection.reset_required is True
    assert assembly.coordination_input.reference_size == pytest.approx(800.0)


def test_assembler_missing_episode_produces_hard_blockable_coordination_input() -> None:
    assembly = assemble_engine_d_coordination_input(
        coordination_input_factory=EngineCoordinationInput,
        journal=ClosedEpisodeJournal(),
        evaluated_at_ns=_NOW_NS,
        pair="BTCUSDT",
        side=Side.BUY,
    )

    assert assembly.first_episode_resolution.found is False
    assert assembly.reset_state_inspection.status == EngineDResetStateStatus.CLEAR
    outcome = evaluate_engine_coordination(assembly.coordination_input)
    assert outcome.blocked is True
    assert outcome.reason_codes == ("hard_block.d_no_historical_linkage",)


def test_runtime_accepts_assembled_coordination_input(repo_tmp_path: Path) -> None:
    journal = _journal_with_episode(_episode_ref(1, closed_at_ns=_NOW_NS - 5))
    assembly = assemble_engine_d_coordination_input(
        coordination_input_factory=EngineCoordinationInput,
        journal=journal,
        evaluated_at_ns=_NOW_NS,
        pair="BTCUSDT",
        side=Side.BUY,
        reference_size=800.0,
    )

    result = _runtime(repo_tmp_path).evaluate(_runtime_input(assembly.coordination_input), now=10.0)

    assert result.status.value == "accepted"
    assert result.coordination_outcome is not None
    assert assembly.reset_state_inspection.status == EngineDResetStateStatus.CLEAR
    assert result.coordination_outcome.resolved_size == pytest.approx(400.0)
