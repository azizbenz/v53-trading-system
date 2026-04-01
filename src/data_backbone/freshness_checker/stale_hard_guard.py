"""
8.5.4 - Stale Hard Guard: trigger explicit stale block when age exceeds threshold.

Invariant: stale hard block is traceable and explicit.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from interface_contracts import RuntimeMode


class StaleVerdict(StrEnum):
    FRESH = "fresh"
    DEGRADED = "degraded"
    HARD_STALE = "hard_stale"


class StaleGuardResult(BaseModel, frozen=True):
    """Result of stale hard guard evaluation."""

    pair: str
    stream_type: str
    age_s: float
    soft_threshold_s: float
    hard_threshold_s: float
    verdict: StaleVerdict
    blocked: bool = False


class ExchangeStalenessResult(BaseModel, frozen=True):
    """Explicit stale verdict from local vs exchange timestamps."""

    pair: str
    stream_type: str
    runtime_mode: RuntimeMode
    local_timestamp: float
    exchange_timestamp: float
    delta_s: float
    stale_threshold_s: float
    verdict: StaleVerdict
    blocked: bool = False
    logged: bool = True


def evaluate_staleness(
    pair: str,
    stream_type: str,
    age_s: float,
    soft_threshold_s: float = 5.0,
    hard_threshold_s: float = 30.0,
) -> StaleGuardResult:
    """Evaluate staleness with soft and hard thresholds."""
    if age_s >= hard_threshold_s:
        return StaleGuardResult(
            pair=pair,
            stream_type=stream_type,
            age_s=age_s,
            soft_threshold_s=soft_threshold_s,
            hard_threshold_s=hard_threshold_s,
            verdict=StaleVerdict.HARD_STALE,
            blocked=True,
        )

    if age_s >= soft_threshold_s:
        return StaleGuardResult(
            pair=pair,
            stream_type=stream_type,
            age_s=age_s,
            soft_threshold_s=soft_threshold_s,
            hard_threshold_s=hard_threshold_s,
            verdict=StaleVerdict.DEGRADED,
        )

    return StaleGuardResult(
        pair=pair,
        stream_type=stream_type,
        age_s=age_s,
        soft_threshold_s=soft_threshold_s,
        hard_threshold_s=hard_threshold_s,
        verdict=StaleVerdict.FRESH,
    )


def evaluate_exchange_staleness(
    pair: str,
    stream_type: str,
    *,
    local_timestamp: float,
    exchange_timestamp: float,
    runtime_mode: RuntimeMode,
    stale_threshold_s: float = 0.2,
) -> ExchangeStalenessResult:
    """Evaluate stale status from local vs exchange timestamps."""
    delta = max(0.0, local_timestamp - exchange_timestamp)
    if delta <= stale_threshold_s:
        return ExchangeStalenessResult(
            pair=pair,
            stream_type=stream_type,
            runtime_mode=runtime_mode,
            local_timestamp=local_timestamp,
            exchange_timestamp=exchange_timestamp,
            delta_s=delta,
            stale_threshold_s=stale_threshold_s,
            verdict=StaleVerdict.FRESH,
        )

    blocked = runtime_mode in {RuntimeMode.MICRO_LIVE, RuntimeMode.LIVE}
    verdict = StaleVerdict.HARD_STALE if blocked else StaleVerdict.DEGRADED
    return ExchangeStalenessResult(
        pair=pair,
        stream_type=stream_type,
        runtime_mode=runtime_mode,
        local_timestamp=local_timestamp,
        exchange_timestamp=exchange_timestamp,
        delta_s=delta,
        stale_threshold_s=stale_threshold_s,
        verdict=verdict,
        blocked=blocked,
    )
