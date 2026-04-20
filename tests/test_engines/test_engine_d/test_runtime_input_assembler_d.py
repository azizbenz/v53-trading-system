from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from data_backbone.microstructure.realized_kernel_vol import RealizedKernelVolRecord
from engines.engine_d import (
    ConsecutiveStopStateD,
    EngineDRuntime,
    EngineDResetStateStatus,
    assemble_engine_d_runtime_input,
    record_engine_d_stop,
)
from engines.engine_d.engine_d_runner import EngineDInput
from interface_contracts import BetStructure, EngineId, ForecastHorizonClass, ForecastTargetClass, Side
from protocols.closed_episode_journal import ClosedEpisodeJournal, EpisodeCloseReason, EpisodeRef
from protocols.engine_coordination_rules import (
    EngineCoordinationInput,
    EngineCoordinationThresholds,
    evaluate_engine_coordination,
)
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker
from risk_backbone.risk_runtime import RiskLimits, RiskRuntime
from scoring_backbone import (
    EngineDCoordinationThresholdResolverConfig,
    EngineDFirstEpisodeThresholdResolverConfig,
    build_engine_d_coordination_threshold_updates,
    build_engine_d_first_episode_threshold_updates,
)
from scoring_backbone.penalty_aggregator.penalty_registry import PenaltyRegistry
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState
from scoring_backbone.scoring_runtime import ScoringRuntime


_NOW_NS = 1_700_000_000_000_000_000
_TIMESTAMP_MS = 1_700_000_000_000


def _realized_kernel_record(*, value: float, pair: str = "BTCUSDT") -> RealizedKernelVolRecord:
    return RealizedKernelVolRecord(
        value=value,
        kernel_variance=value * value,
        bandwidth=3,
        low_sample_confidence=False,
        insufficient_variation=False,
        n_events_received=12,
        window_used=(12, 3_600.0),
        n_events_used=12,
        method_version_hash="c" * 64,
        pair=pair,
        computed_at_ns=_NOW_NS,
        input_data_hash="d" * 64,
    )


def _episode_ref(
    suffix: int,
    *,
    close_reason: EpisodeCloseReason = EpisodeCloseReason.TIME_STOP,
    closed_at_ns: int | None = None,
) -> EpisodeRef:
    return EpisodeRef(
        episode_id=UUID(f"41111111-1111-1111-1111-{suffix:012d}"),
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


def _journal(*episodes: EpisodeRef) -> ClosedEpisodeJournal:
    journal = ClosedEpisodeJournal()
    journal.append_batch(tuple(episodes))
    return journal


def _write_signed_first_episode_yaml(path: Path, *, lookback_hours: float) -> None:
    payload = {
        "artifact_id": "engine-d-first-episode-thresholds",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-19T23:20:00Z",
        "thresholds": [
            {
                "threshold_id": "THR-D_LOOKBACK",
                "value": lookback_hours,
                "source_module": "src/scoring_backbone/engine_d_first_episode_thresholds.py",
                "calibration_artifact": "config/calibration/v1/engine_d_first_episode.yml",
            },
            {
                "threshold_id": "THR-D_MIN_GAP",
                "value": 15.0,
                "source_module": "src/scoring_backbone/engine_d_first_episode_thresholds.py",
                "calibration_artifact": "config/calibration/v1/engine_d_first_episode.yml",
            },
        ],
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-19T23:21:00Z",
        },
    }
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


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


def _portfolio() -> PortfolioState:
    return PortfolioState(
        remaining_gross_capacity=5000.0,
        remaining_loss_capacity=500.0,
        remaining_beta_capacity=5000.0,
        remaining_cluster_capacity={"btc_majors": 5000.0},
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


def _runtime_with_first_episode_lookback(
    repo_tmp_path: Path,
    *,
    lookback_hours: float,
) -> EngineDRuntime:
    calibration_tmpdir = repo_tmp_path / "engine_d_first_episode_runtime_thresholds"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_first_episode_yaml(
        version_dir / "engine_d_first_episode.yml",
        lookback_hours=lookback_hours,
    )
    updates = build_engine_d_first_episode_threshold_updates(
        EngineDFirstEpisodeThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            lookback_threshold_id="THR-D_LOOKBACK",
            min_gap_threshold_id="THR-D_MIN_GAP",
        )
    )
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
        first_episode_lookback_ns=updates["lookback_ns"],
        first_episode_min_gap_ns=updates["min_gap_ns"],
    )


def _runtime_with_coordination_thresholds(
    repo_tmp_path: Path,
    *,
    d_reset_failsafe_hours: float,
    d_consecutive_stop_limit: int,
) -> EngineDRuntime:
    updates = build_engine_d_coordination_threshold_updates(
        EngineDCoordinationThresholdResolverConfig(
            d_reset_failsafe_hours=d_reset_failsafe_hours,
            d_consecutive_stop_limit=d_consecutive_stop_limit,
        )
    )
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
        coordination_thresholds=EngineCoordinationThresholds(**updates),
    )


def test_runtime_input_assembler_resolves_episode_and_builds_runtime_input() -> None:
    assembly = assemble_engine_d_runtime_input(
        coordination_input_factory=EngineCoordinationInput,
        journal=_journal(_episode_ref(1, closed_at_ns=_NOW_NS - 20), _episode_ref(2, closed_at_ns=_NOW_NS - 5)),
        engine_inputs=_engine_inputs(),
        timestamp_ms=_TIMESTAMP_MS,
        portfolio=_portfolio(),
        projected_size=800.0,
        projected_loss=40.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.7,
        cluster_id="btc_majors",
    )

    assert assembly.coordination_assembly.first_episode_resolution.found is True
    assert assembly.coordination_assembly.coordination_input.first_episode_ref is not None
    assert assembly.runtime_input.coordination_input is not None
    assert assembly.reset_state_inspection.status == EngineDResetStateStatus.CLEAR
    assert assembly.runtime_input.coordination_input.reference_size == pytest.approx(800.0)


def test_runtime_input_assembler_surfaces_missing_episode_as_runtime_hard_block(repo_tmp_path: Path) -> None:
    assembly = assemble_engine_d_runtime_input(
        coordination_input_factory=EngineCoordinationInput,
        journal=ClosedEpisodeJournal(),
        engine_inputs=_engine_inputs(),
        timestamp_ms=_TIMESTAMP_MS,
        portfolio=_portfolio(),
        projected_size=800.0,
        projected_loss=40.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.7,
        cluster_id="btc_majors",
    )

    result = _runtime(repo_tmp_path).evaluate(assembly.runtime_input, now=10.0)

    assert assembly.coordination_assembly.first_episode_resolution.found is False
    assert assembly.reset_state_inspection.status == EngineDResetStateStatus.CLEAR
    assert result.status.value == "hard_blocked"
    assert result.coordination_outcome is not None
    assert result.coordination_outcome.reason_codes == ("hard_block.d_no_historical_linkage",)


def test_runtime_input_assembler_carries_explicit_stop_state_into_runtime(repo_tmp_path: Path) -> None:
    stop_state = record_engine_d_stop(ConsecutiveStopStateD(), stopped_at_ns=_NOW_NS - 1)
    assembly = assemble_engine_d_runtime_input(
        coordination_input_factory=EngineCoordinationInput,
        journal=_journal(_episode_ref(1, closed_at_ns=_NOW_NS - 5)),
        engine_inputs=_engine_inputs(),
        timestamp_ms=_TIMESTAMP_MS,
        portfolio=_portfolio(),
        projected_size=800.0,
        projected_loss=40.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.7,
        cluster_id="btc_majors",
        stop_state=stop_state,
    )

    result = _runtime(repo_tmp_path).evaluate(assembly.runtime_input, now=10.0)

    assert assembly.runtime_input.coordination_input is not None
    assert assembly.runtime_input.coordination_input.consecutive_d_stop_count == 1
    assert assembly.reset_state_inspection.status == EngineDResetStateStatus.RESET_REQUIRED
    assert result.status.value == "hard_blocked"
    assert result.coordination_outcome is not None
    assert result.coordination_outcome.reason_codes == ("hard_block.d_consecutive_stops_reset_required",)


def test_runtime_public_evaluate_from_historical_state_uses_governed_assembler(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path)

    result = runtime.evaluate_from_historical_state(
        coordination_input_factory=EngineCoordinationInput,
        journal=ClosedEpisodeJournal(),
        engine_inputs=_engine_inputs(),
        timestamp_ms=_TIMESTAMP_MS,
        portfolio=_portfolio(),
        projected_size=800.0,
        projected_loss=40.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.7,
        cluster_id="btc_majors",
        now=10.0,
    )

    assert result.status.value == "hard_blocked"
    assert result.coordination_outcome is not None
    assert result.coordination_outcome.reason_codes == ("hard_block.d_no_historical_linkage",)
    assert result.historical_state_inspection is not None
    assert result.historical_state_inspection.status == EngineDResetStateStatus.CLEAR


def test_runtime_public_evaluate_from_historical_state_attaches_failsafe_inspection(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path)
    stop_state = ConsecutiveStopStateD(
        consecutive_stop_count=1,
        last_stop_at_ns=_NOW_NS - (30 * 3_600_000_000_000),
        failsafe_override_available=True,
    )

    result = runtime.evaluate_from_historical_state(
        coordination_input_factory=EngineCoordinationInput,
        journal=_journal(_episode_ref(1, closed_at_ns=_NOW_NS - 5)),
        engine_inputs=_engine_inputs(),
        timestamp_ms=_TIMESTAMP_MS,
        portfolio=_portfolio(),
        projected_size=800.0,
        projected_loss=40.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.7,
        cluster_id="btc_majors",
        stop_state=stop_state,
        now=10.0,
    )

    assert result.status.value == "accepted"
    assert result.historical_state_inspection is not None
    assert result.historical_state_inspection.status == EngineDResetStateStatus.FAILSAFE_OVERRIDE_ACTIVE
    assert result.historical_state_inspection.failsafe_override_active is True


def test_runtime_public_historical_entry_uses_governed_d_threshold_updates(repo_tmp_path: Path) -> None:
    runtime = _runtime_with_coordination_thresholds(
        repo_tmp_path,
        d_reset_failsafe_hours=12.0,
        d_consecutive_stop_limit=2,
    )
    stop_state = ConsecutiveStopStateD(
        consecutive_stop_count=2,
        last_stop_at_ns=_NOW_NS - (13 * 3_600_000_000_000),
        failsafe_override_available=True,
    )

    result = runtime.evaluate_from_historical_state(
        coordination_input_factory=EngineCoordinationInput,
        journal=_journal(_episode_ref(1, closed_at_ns=_NOW_NS - 5)),
        engine_inputs=_engine_inputs(),
        timestamp_ms=_TIMESTAMP_MS,
        portfolio=_portfolio(),
        projected_size=800.0,
        projected_loss=40.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.7,
        cluster_id="btc_majors",
        stop_state=stop_state,
        now=10.0,
    )

    assert result.status.value == "accepted"
    assert result.coordination_outcome is not None
    assert result.coordination_outcome.reason_codes == ("coordination.d_failsafe_override",)
    assert result.historical_state_inspection is not None
    assert result.historical_state_inspection.stop_limit == 2
    assert result.historical_state_inspection.reset_failsafe_ns == 12 * 3_600_000_000_000
    assert result.historical_state_inspection.status == EngineDResetStateStatus.FAILSAFE_OVERRIDE_ACTIVE


def test_runtime_public_historical_entry_uses_governed_first_episode_lookback(repo_tmp_path: Path) -> None:
    runtime = _runtime_with_first_episode_lookback(
        repo_tmp_path,
        lookback_hours=12.0,
    )

    result = runtime.evaluate_from_historical_state(
        coordination_input_factory=EngineCoordinationInput,
        journal=_journal(_episode_ref(1, closed_at_ns=_NOW_NS - (13 * 3_600_000_000_000))),
        engine_inputs=_engine_inputs(),
        timestamp_ms=_TIMESTAMP_MS,
        portfolio=_portfolio(),
        projected_size=800.0,
        projected_loss=40.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.7,
        cluster_id="btc_majors",
        now=10.0,
    )

    assert result.status.value == "hard_blocked"
    assert result.coordination_outcome is not None
    assert result.coordination_outcome.reason_codes == ("hard_block.d_no_historical_linkage",)


def test_runtime_input_assembler_surfaces_first_episode_gap_block_when_not_elapsed() -> None:
    assembly = assemble_engine_d_runtime_input(
        coordination_input_factory=EngineCoordinationInput,
        journal=_journal(_episode_ref(1, closed_at_ns=_NOW_NS - 5)),
        engine_inputs=_engine_inputs(),
        timestamp_ms=_TIMESTAMP_MS,
        portfolio=_portfolio(),
        projected_size=800.0,
        projected_loss=40.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.7,
        cluster_id="btc_majors",
        min_gap_ns=10,
    )

    assert assembly.first_episode_gap_inspection is not None
    assert assembly.first_episode_gap_inspection.blocked is True
    assert assembly.first_episode_gap_inspection.reason_code == "hard_block.d_min_gap_not_elapsed"
    assert assembly.runtime_input.first_episode_gap_inspection is not None


def test_runtime_public_historical_entry_uses_governed_first_episode_min_gap(repo_tmp_path: Path) -> None:
    runtime = _runtime_with_first_episode_lookback(
        repo_tmp_path,
        lookback_hours=12.0,
    )

    result = runtime.evaluate_from_historical_state(
        coordination_input_factory=EngineCoordinationInput,
        journal=_journal(_episode_ref(1, closed_at_ns=_NOW_NS - (5 * 60_000_000_000))),
        engine_inputs=_engine_inputs(),
        timestamp_ms=_TIMESTAMP_MS,
        portfolio=_portfolio(),
        projected_size=800.0,
        projected_loss=40.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.7,
        cluster_id="btc_majors",
        now=10.0,
    )

    assert result.status.value == "hard_blocked"
    assert result.coordination_outcome is None
    assert result.first_episode_gap_inspection is not None
    assert result.first_episode_gap_inspection.blocked is True
    assert result.refusal_record is not None
    assert "hard_block.d_min_gap_not_elapsed" in result.refusal_record.reason_codes
    assert any(entry.event == "engine_d_first_episode_gap_blocked" for entry in result.log_entries)


def test_runtime_input_assembler_populates_realized_vol_from_shared_canonical_records() -> None:
    assembly = assemble_engine_d_runtime_input(
        coordination_input_factory=EngineCoordinationInput,
        journal=_journal(_episode_ref(1, closed_at_ns=_NOW_NS - 5)),
        engine_inputs=_engine_inputs().model_copy(
            update={
                "realized_vol_current": None,
                "realized_vol_post_close": None,
            }
        ),
        timestamp_ms=_TIMESTAMP_MS,
        portfolio=_portfolio(),
        projected_size=800.0,
        projected_loss=40.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.7,
        cluster_id="btc_majors",
        realized_vol_current_record=_realized_kernel_record(value=0.018),
        realized_vol_post_close_record=_realized_kernel_record(value=0.015),
    )

    assert assembly.runtime_input.engine_inputs.realized_vol_current == pytest.approx(0.018)
    assert assembly.runtime_input.engine_inputs.realized_vol_post_close == pytest.approx(0.015)


def test_runtime_public_historical_entry_can_populate_realized_vol_from_shared_records(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path)

    result = runtime.evaluate_from_historical_state(
        coordination_input_factory=EngineCoordinationInput,
        journal=_journal(_episode_ref(1, closed_at_ns=_NOW_NS - 5)),
        engine_inputs=_engine_inputs().model_copy(
            update={
                "realized_vol_current": None,
                "realized_vol_post_close": None,
            }
        ),
        timestamp_ms=_TIMESTAMP_MS,
        portfolio=_portfolio(),
        projected_size=800.0,
        projected_loss=40.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.7,
        cluster_id="btc_majors",
        strategy_id="strategy-d-reentry",
        realized_vol_current_record=_realized_kernel_record(value=0.018),
        realized_vol_post_close_record=_realized_kernel_record(value=0.015),
        now=10.0,
    )

    assert result.status.value == "accepted"
    assert result.forecast_signal_candidate is not None
    assert "engine_d.forecast.volatility_proxy.realized_vol_post_close" in (
        result.forecast_signal_candidate.reason_codes
    )


def test_runtime_input_assembler_rejects_conflicting_realized_vol_ownership() -> None:
    with pytest.raises(ValueError, match="conflicting Engine D microstructure field: realized_vol_current"):
        assemble_engine_d_runtime_input(
            coordination_input_factory=EngineCoordinationInput,
            journal=_journal(_episode_ref(1, closed_at_ns=_NOW_NS - 5)),
            engine_inputs=_engine_inputs().model_copy(
                update={
                    "realized_vol_current": 0.03,
                    "realized_vol_post_close": None,
                }
            ),
            timestamp_ms=_TIMESTAMP_MS,
            portfolio=_portfolio(),
            projected_size=800.0,
            projected_loss=40.0,
            current_equity=10_000.0,
            session_peak_equity=10_000.0,
            pair_beta=0.7,
            cluster_id="btc_majors",
            realized_vol_current_record=_realized_kernel_record(value=0.018),
        )
