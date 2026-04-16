"""Private helper functions for the Engine A runtime facade."""

from __future__ import annotations

import math

from interface_contracts import (
    BetStructure,
    ConditioningFamily,
    ConditioningRecord,
    EngineId,
    ForecastHorizonClass,
    ForecastSignalCandidate,
    ForecastTargetClass,
    RegimeId,
    Side,
    SignalCandidate as DecisionSignalCandidate,
    SignalType,
)
from scoring_backbone.scoring_runtime import ScoringCandidateAudit, ScoringRoundResult

from .engine_a_runner import EngineAInput, EngineAOutput


def _resolve_runtime_now(timestamp_ms: int, now: float | None, *, context: str) -> float:
    """Resolve an audit timestamp from the explicit arg or the governed input."""

    if now is None:
        if timestamp_ms <= 0:
            raise ValueError(f"{context} requires timestamp_ms > 0 when now is omitted")
        return timestamp_ms / 1000.0
    if not math.isfinite(now):
        raise ValueError(f"{context} requires finite now")
    if now <= 0.0:
        raise ValueError(f"{context} requires now > 0")
    return now


def _require_scoring_version(scoring_version: str, *, context: str) -> str:
    """Reject empty audit versions on the open engine runtime rail."""

    normalized = scoring_version.strip()
    if not normalized:
        raise ValueError(f"{context} requires non-empty scoring_version")
    return normalized


def _resolve_scoring_audit(
    scoring_round: ScoringRoundResult,
    *,
    engine_id: str,
    pair: str,
    context: str,
) -> ScoringCandidateAudit:
    matches = [
        audit
        for audit in scoring_round.audits
        if audit.engine_id == engine_id and audit.pair == pair
    ]
    if not matches:
        raise ValueError(f"{context} is missing scoring audit for {engine_id}/{pair}")
    if len(matches) > 1:
        raise ValueError(f"{context} found duplicate scoring audits for {engine_id}/{pair}")
    return matches[0]


def _build_signal_candidate(
    inputs: EngineAInput,
    engine_output: EngineAOutput,
    timestamp_ms: int,
) -> DecisionSignalCandidate:
    stop_loss = None
    if engine_output.invalidation is not None:
        for rule in engine_output.invalidation.rules:
            if rule.level is not None:
                stop_loss = rule.level
                break

    take_profit = None
    if inputs.entry_price > 0 and inputs.expected_gain > 0:
        take_profit = inputs.entry_price * (1.0 + inputs.expected_gain)

    max_hold_ms = None
    if engine_output.holding_hours > 0:
        max_hold_ms = int(engine_output.holding_hours * 3600 * 1000)

    return DecisionSignalCandidate(
        timestamp_ms=timestamp_ms,
        pair=engine_output.pair,
        engine_id=EngineId.A,
        signal_type=SignalType.ENTRY,
        side=Side.BUY,
        confidence=max(0.0, min(1.0, engine_output.raw_score)),
        regime=_to_regime_id(inputs.regime),
        entry_price=inputs.entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        max_hold_ms=max_hold_ms,
        reason=f"engine_a:{engine_output.conviction.value}",
    )


def _build_forecast_signal_candidate(
    *,
    strategy_id: str | None,
    timestamp_ms: int,
    engine_inputs: EngineAInput,
    engine_output: EngineAOutput,
    signal_candidate: DecisionSignalCandidate,
    scoring_audit: ScoringCandidateAudit,
) -> ForecastSignalCandidate | None:
    if strategy_id is None:
        return None
    return ForecastSignalCandidate.from_decision_signal(
        signal_candidate,
        strategy_id=strategy_id,
        forecast_direction=1.0 if signal_candidate.side == Side.BUY else -1.0,
        forecast_strength=max(0.0, min(20.0, engine_output.raw_score * 20.0)),
        forecast_horizon_class=_resolve_forecast_horizon_class(
            holding_period_hours=engine_inputs.holding_period,
            signal_candidate=signal_candidate,
        ),
        forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
        bet_structure=_resolve_bet_structure(signal_candidate.side),
        conditioning_state=_build_conditioning_state(
            timestamp_ms=timestamp_ms,
            engine_output=engine_output,
            scoring_audit=scoring_audit,
        ),
        expected_cost=engine_output.expected_cost,
        expected_break_even=engine_output.expected_cost + engine_inputs.delta_safe,
        expected_ce=engine_output.ce_expected,
        expected_gain=engine_inputs.expected_gain,
        invalidation_ref=_resolve_invalidation_ref(engine_output),
        reason_codes=_build_forecast_reason_codes(engine_output, scoring_audit),
        versions=_build_forecast_versions(
            scoring_version=engine_output.scoring_version or engine_inputs.scoring_version,
            engine_output=engine_output,
        ),
        confidence_band=signal_candidate.confidence,
    )


def _build_conditioning_state(
    *,
    timestamp_ms: int,
    engine_output: EngineAOutput,
    scoring_audit: ScoringCandidateAudit,
) -> tuple[ConditioningRecord, ...]:
    records = [
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_a.conviction.{engine_output.conviction.value}",
            value=engine_output.raw_score,
            triggered_no_trade=False,
        )
    ]
    for penalty in scoring_audit.score_penalty_result.penalties:
        records.append(
            ConditioningRecord(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.SCORING,
                code=f"scoring.penalty.{penalty.penalty_id}",
                value=penalty.value,
                triggered_no_trade=False,
            )
        )
    return tuple(records)


def _build_forecast_reason_codes(
    engine_output: EngineAOutput,
    scoring_audit: ScoringCandidateAudit,
) -> tuple[str, ...]:
    reason_codes = [f"engine_a.conviction.{engine_output.conviction.value}"]
    reason_codes.extend(
        f"scoring.penalty.{penalty.penalty_id}"
        for penalty in scoring_audit.score_penalty_result.penalties
    )
    return tuple(dict.fromkeys(reason_codes))


def _build_forecast_versions(
    *,
    scoring_version: str,
    engine_output: EngineAOutput,
) -> dict[str, str]:
    return {
        "scoring_version": scoring_version,
        "calibration_profile_id": engine_output.calibration_profile_id,
        "calibration_status": engine_output.calibration_status,
        "physics_calibration_profile_id": engine_output.physics_calibration_profile_id,
        "physics_calibration_status": engine_output.physics_calibration_status,
    }


def _resolve_invalidation_ref(engine_output: EngineAOutput) -> str | None:
    invalidation = engine_output.invalidation
    if invalidation is None:
        return None
    primary = invalidation.primary_invalidation.strip()
    if primary:
        return primary
    return None


def _resolve_forecast_horizon_class(
    *,
    holding_period_hours: float,
    signal_candidate: DecisionSignalCandidate,
) -> ForecastHorizonClass:
    max_hold_ms = signal_candidate.max_hold_ms
    if max_hold_ms is None:
        max_hold_ms = int(holding_period_hours * 3600 * 1000)
    if max_hold_ms < 60_000:
        return ForecastHorizonClass.INTRABAR
    if max_hold_ms <= 15 * 60_000:
        return ForecastHorizonClass.SHORT
    if max_hold_ms <= 4 * 60 * 60_000:
        return ForecastHorizonClass.MEDIUM
    return ForecastHorizonClass.LONG


def _resolve_bet_structure(side: Side) -> BetStructure:
    if side == Side.BUY:
        return BetStructure.DIRECTIONAL_LONG
    return BetStructure.DIRECTIONAL_SHORT


def _to_regime_id(value: str) -> RegimeId:
    normalized = value.strip().lower()
    try:
        return RegimeId(normalized)
    except ValueError:
        return RegimeId.UNKNOWN


__all__ = [
    "_build_forecast_signal_candidate",
    "_build_signal_candidate",
    "_require_scoring_version",
    "_resolve_runtime_now",
    "_resolve_scoring_audit",
]
