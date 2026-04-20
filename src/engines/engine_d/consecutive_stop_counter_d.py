"""Explicit Engine D consecutive-stop state helpers."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


_MIN_EPOCH_NS = 1_000_000_000_000_000_000
_MAX_EPOCH_NS = 9_999_999_999_999_999_999
_NS_PER_HOUR = 3_600_000_000_000
DEFAULT_D_CONSECUTIVE_STOP_LIMIT = 1
DEFAULT_D_RESET_FAILSAFE_NS = 24 * _NS_PER_HOUR


class ConsecutiveStopStateD(BaseModel):
    """Frozen state snapshot for Engine D reset / consecutive-stop governance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    consecutive_stop_count: int = Field(default=0, ge=0)
    last_stop_at_ns: int | None = Field(default=None, ge=_MIN_EPOCH_NS, le=_MAX_EPOCH_NS)
    last_fresh_a_detection_at_ns: int | None = Field(
        default=None,
        ge=_MIN_EPOCH_NS,
        le=_MAX_EPOCH_NS,
    )
    failsafe_override_available: bool = False


class EngineDResetStateStatus(StrEnum):
    CLEAR = "clear"
    RESET_REQUIRED = "reset_required"
    FAILSAFE_OVERRIDE_ACTIVE = "failsafe_override_active"


class EngineDResetStateInspection(BaseModel):
    """Inspectability-only view of D reset/failsafe state. Not a rule engine."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: EngineDResetStateStatus = EngineDResetStateStatus.CLEAR
    reset_required: bool = False
    stop_limit_reached: bool = False
    fresh_a_detection_after_last_stop: bool = False
    failsafe_override_available: bool = False
    failsafe_override_active: bool = False
    stop_limit: int = Field(default=DEFAULT_D_CONSECUTIVE_STOP_LIMIT, ge=1)
    reset_failsafe_ns: int = Field(default=DEFAULT_D_RESET_FAILSAFE_NS, gt=0)
    time_since_last_stop_ns: int | None = Field(default=None, ge=0)
    failsafe_override_eligible_at_ns: int | None = Field(
        default=None,
        ge=_MIN_EPOCH_NS,
        le=_MAX_EPOCH_NS + DEFAULT_D_RESET_FAILSAFE_NS,
    )
    failsafe_override_remaining_ns: int | None = Field(default=None, ge=0)


def record_engine_d_stop(
    state: ConsecutiveStopStateD,
    *,
    stopped_at_ns: int,
) -> ConsecutiveStopStateD:
    """Append a governed Engine D stop event to the explicit reset state."""

    return state.model_copy(
        update={
            "consecutive_stop_count": state.consecutive_stop_count + 1,
            "last_stop_at_ns": stopped_at_ns,
        }
    )


def record_fresh_a_detection(
    state: ConsecutiveStopStateD,
    *,
    detected_at_ns: int,
) -> ConsecutiveStopStateD:
    """Record fresh Engine A structural support and reset the D stop state when valid."""

    reset_count = (
        0
        if state.last_stop_at_ns is None or detected_at_ns > state.last_stop_at_ns
        else state.consecutive_stop_count
    )
    return state.model_copy(
        update={
            "consecutive_stop_count": reset_count,
            "last_fresh_a_detection_at_ns": detected_at_ns,
        }
    )


def to_coordination_fields(
    state: ConsecutiveStopStateD,
) -> dict[str, int | bool | None]:
    """Expose the current state in the protocol coordination-field shape."""

    return {
        "consecutive_d_stop_count": state.consecutive_stop_count,
        "last_d_stop_at_ns": state.last_stop_at_ns,
        "last_fresh_a_detection_at_ns": state.last_fresh_a_detection_at_ns,
        "d_failsafe_override_available": state.failsafe_override_available,
    }


def inspect_engine_d_reset_state(
    state: ConsecutiveStopStateD,
    *,
    evaluated_at_ns: int,
    stop_limit: int = DEFAULT_D_CONSECUTIVE_STOP_LIMIT,
    reset_failsafe_ns: int = DEFAULT_D_RESET_FAILSAFE_NS,
) -> EngineDResetStateInspection:
    """Return an additive reset/failsafe summary for audit and assembly surfaces."""

    stop_limit_reached = state.consecutive_stop_count >= stop_limit
    fresh_a_detection_after_last_stop = (
        state.last_stop_at_ns is not None
        and state.last_fresh_a_detection_at_ns is not None
        and state.last_fresh_a_detection_at_ns > state.last_stop_at_ns
    )
    reset_required = stop_limit_reached and not fresh_a_detection_after_last_stop
    time_since_last_stop_ns = None
    failsafe_override_eligible_at_ns = None
    failsafe_override_remaining_ns = None
    if state.last_stop_at_ns is not None:
        time_since_last_stop_ns = max(0, evaluated_at_ns - state.last_stop_at_ns)
        failsafe_override_eligible_at_ns = state.last_stop_at_ns + reset_failsafe_ns
        failsafe_override_remaining_ns = max(0, reset_failsafe_ns - time_since_last_stop_ns)
    failsafe_override_active = (
        reset_required
        and state.failsafe_override_available
        and time_since_last_stop_ns is not None
        and time_since_last_stop_ns >= reset_failsafe_ns
    )
    status = (
        EngineDResetStateStatus.FAILSAFE_OVERRIDE_ACTIVE
        if failsafe_override_active
        else EngineDResetStateStatus.RESET_REQUIRED
        if reset_required
        else EngineDResetStateStatus.CLEAR
    )
    return EngineDResetStateInspection(
        status=status,
        reset_required=reset_required,
        stop_limit_reached=stop_limit_reached,
        fresh_a_detection_after_last_stop=fresh_a_detection_after_last_stop,
        failsafe_override_available=state.failsafe_override_available,
        failsafe_override_active=failsafe_override_active,
        stop_limit=stop_limit,
        reset_failsafe_ns=reset_failsafe_ns,
        time_since_last_stop_ns=time_since_last_stop_ns,
        failsafe_override_eligible_at_ns=failsafe_override_eligible_at_ns,
        failsafe_override_remaining_ns=failsafe_override_remaining_ns,
    )


__all__ = [
    "ConsecutiveStopStateD",
    "DEFAULT_D_CONSECUTIVE_STOP_LIMIT",
    "DEFAULT_D_RESET_FAILSAFE_NS",
    "EngineDResetStateInspection",
    "EngineDResetStateStatus",
    "inspect_engine_d_reset_state",
    "record_engine_d_stop",
    "record_fresh_a_detection",
    "to_coordination_fields",
]
