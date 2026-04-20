"""Typed engine coordination rules before deeper C/D doctrinal migration."""

from __future__ import annotations

from interface_contracts import (
    ConditioningFamily,
    ConditioningRecord,
    EngineId,
    EngineCoordinationAction,
    EngineCoordinationInput,
    EngineCoordinationOutcome,
    EngineCoordinationThresholds,
    RefusalCategory,
    RefusalRecord,
    Side,
)

_NS_PER_HOUR = 3_600_000_000_000

_R_AC_1 = "R-AC-1"
_R_AC_2 = "R-AC-2"
_R_D_1 = "R-D-1"
_R_D_2 = "R-D-2"
_R_D_3 = "R-D-3"

_CODE_AC_HOLDING = "hard_block.ac_mutual_exclusion.a_holding"
_CODE_AC_RECENT_FIRE = "hard_block.ac_recent_fire"
_CODE_D_NO_LINKAGE = "hard_block.d_no_historical_linkage"
_CODE_D_CONSECUTIVE_STOPS = "hard_block.d_consecutive_stops_reset_required"
_CODE_D_FAILSAFE_OVERRIDE = "coordination.d_failsafe_override"


def evaluate_engine_coordination(
    coordination_input: EngineCoordinationInput,
    *,
    thresholds: EngineCoordinationThresholds | None = None,
) -> EngineCoordinationOutcome:
    """Evaluate the doc20 coordination rules without inventing extra runtime state."""

    effective_thresholds = thresholds or EngineCoordinationThresholds()

    if coordination_input.engine_id == EngineId.C:
        if coordination_input.a_holding_block_active:
            return _build_hard_block_outcome(
                coordination_input,
                rule_id=_R_AC_1,
                reason_code=_CODE_AC_HOLDING,
                detail="Engine C blocked while Engine A holding block is active on same pair/direction.",
            )
        if _is_recent_a_fire_block_active(coordination_input, effective_thresholds):
            return _build_hard_block_outcome(
                coordination_input,
                rule_id=_R_AC_2,
                reason_code=_CODE_AC_RECENT_FIRE,
                detail="Engine C blocked by recent Engine A fire on the same structural setup.",
            )
        return EngineCoordinationOutcome()

    if coordination_input.engine_id != EngineId.D:
        return EngineCoordinationOutcome()

    linkage_block = _resolve_d_linkage_block(coordination_input)
    if linkage_block is not None:
        return linkage_block

    if _requires_d_reset(coordination_input, effective_thresholds):
        if _failsafe_override_is_active(coordination_input, effective_thresholds):
            return _build_d_permit_outcome(
                coordination_input,
                thresholds=effective_thresholds,
                rule_hits=(_R_D_3,),
                reason_codes=(_CODE_D_FAILSAFE_OVERRIDE,),
                detail="Engine D permitted via explicit failsafe override after reset timer expiry.",
            )
        return _build_hard_block_outcome(
            coordination_input,
            rule_id=_R_D_2,
            reason_code=_CODE_D_CONSECUTIVE_STOPS,
            detail="Engine D blocked until a fresh Engine A detection resets consecutive stop state.",
        )

    return _build_d_permit_outcome(
        coordination_input,
        thresholds=effective_thresholds,
    )


def _is_recent_a_fire_block_active(
    coordination_input: EngineCoordinationInput,
    thresholds: EngineCoordinationThresholds,
) -> bool:
    recent_a_fire_at_ns = coordination_input.recent_a_fire_same_setup_at_ns
    if recent_a_fire_at_ns is None:
        return False
    return (
        coordination_input.evaluated_at_ns - recent_a_fire_at_ns
        <= thresholds.recent_fire_block_ns
    )


def _resolve_d_linkage_block(
    coordination_input: EngineCoordinationInput,
) -> EngineCoordinationOutcome | None:
    episode_ref = coordination_input.first_episode_ref
    if episode_ref is None:
        return _build_hard_block_outcome(
            coordination_input,
            rule_id=_R_D_1,
            reason_code=_CODE_D_NO_LINKAGE,
            detail="Engine D requires a completed A/C episode reference on the same pair/direction.",
        )
    if episode_ref.pair != coordination_input.pair or episode_ref.side != coordination_input.side:
        return _build_hard_block_outcome(
            coordination_input,
            rule_id=_R_D_1,
            reason_code=_CODE_D_NO_LINKAGE,
            detail="Engine D episode reference does not match the evaluated pair/direction.",
        )
    return None


def _requires_d_reset(
    coordination_input: EngineCoordinationInput,
    thresholds: EngineCoordinationThresholds,
) -> bool:
    if coordination_input.consecutive_d_stop_count < thresholds.d_consecutive_stop_limit:
        return False
    last_stop_at_ns = coordination_input.last_d_stop_at_ns
    fresh_a_at_ns = coordination_input.last_fresh_a_detection_at_ns
    if last_stop_at_ns is None or fresh_a_at_ns is None:
        return True
    return fresh_a_at_ns <= last_stop_at_ns


def _failsafe_override_is_active(
    coordination_input: EngineCoordinationInput,
    thresholds: EngineCoordinationThresholds,
) -> bool:
    if not coordination_input.d_failsafe_override_available:
        return False
    if coordination_input.last_d_stop_at_ns is None:
        return False
    return (
        coordination_input.evaluated_at_ns - coordination_input.last_d_stop_at_ns
        >= thresholds.d_reset_failsafe_ns
    )


def _build_hard_block_outcome(
    coordination_input: EngineCoordinationInput,
    *,
    rule_id: str,
    reason_code: str,
    detail: str,
) -> EngineCoordinationOutcome:
    timestamp_ms = coordination_input.evaluated_at_ns // 1_000_000
    conditioning_record = ConditioningRecord(
        timestamp_ms=timestamp_ms,
        family=ConditioningFamily.HARD_BLOCK,
        code=reason_code,
        value=1.0,
        triggered_no_trade=True,
    )
    refusal_record = RefusalRecord(
        timestamp_ms=timestamp_ms,
        pair=coordination_input.pair,
        engine_id=coordination_input.engine_id,
        category=RefusalCategory.HARD_BLOCK,
        reason_codes=(reason_code,),
    )
    return EngineCoordinationOutcome(
        blocked=True,
        action=EngineCoordinationAction.HARD_BLOCK,
        rule_hits=(rule_id,),
        reason_codes=(reason_code,),
        detail=detail,
        conditioning_state=(conditioning_record,),
        refusal_record=refusal_record,
    )


def _build_d_permit_outcome(
    coordination_input: EngineCoordinationInput,
    *,
    thresholds: EngineCoordinationThresholds,
    rule_hits: tuple[str, ...] = (),
    reason_codes: tuple[str, ...] = (),
    detail: str = "",
) -> EngineCoordinationOutcome:
    resolved_size = None
    if coordination_input.reference_size is not None:
        resolved_size = coordination_input.reference_size * thresholds.d_reentry_size_multiplier
    return EngineCoordinationOutcome(
        blocked=False,
        action=EngineCoordinationAction.SIZE_REDUCED,
        rule_hits=rule_hits,
        reason_codes=reason_codes,
        detail=detail,
        size_multiplier=thresholds.d_reentry_size_multiplier,
        resolved_size=resolved_size,
    )


__all__ = [
    "EngineCoordinationAction",
    "EngineCoordinationInput",
    "EngineCoordinationOutcome",
    "EngineCoordinationThresholds",
    "evaluate_engine_coordination",
]
