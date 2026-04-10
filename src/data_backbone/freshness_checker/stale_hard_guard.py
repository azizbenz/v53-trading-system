"""
8.5.4 - Stale Hard Guard: trigger explicit stale block when age exceeds threshold.

Invariant: stale hard block is traceable and explicit.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

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

    policy_id: str = Field(..., min_length=1)
    pair: str
    stream_type: str
    runtime_mode: RuntimeMode
    local_timestamp: float
    exchange_timestamp: float
    delta_s: float
    signed_delta_s: float
    stale_threshold_s: float
    verdict: StaleVerdict
    blocked: bool = False
    logged: bool = True


class ExchangeStalenessPolicy(BaseModel, frozen=True):
    """Typed policy for exchange staleness evaluation."""

    policy_id: str = Field(..., min_length=1)
    stale_threshold_s: float = Field(..., ge=0.0)
    blocking_runtime_modes: frozenset[RuntimeMode] = frozenset()


CANONICAL_EXCHANGE_STALENESS_POLICY = ExchangeStalenessPolicy(
    policy_id="exchange_staleness_policy.v1",
    stale_threshold_s=0.2,
    blocking_runtime_modes=frozenset(
        {RuntimeMode.SHADOW, RuntimeMode.MICRO_LIVE, RuntimeMode.LIVE}
    ),
)


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
    policy: ExchangeStalenessPolicy = CANONICAL_EXCHANGE_STALENESS_POLICY,
) -> ExchangeStalenessResult:
    """Evaluate stale status from local vs exchange timestamps."""
    signed_delta = local_timestamp - exchange_timestamp
    delta = abs(signed_delta)
    if delta <= policy.stale_threshold_s:
        return ExchangeStalenessResult(
            policy_id=policy.policy_id,
            pair=pair,
            stream_type=stream_type,
            runtime_mode=runtime_mode,
            local_timestamp=local_timestamp,
            exchange_timestamp=exchange_timestamp,
            delta_s=delta,
            signed_delta_s=signed_delta,
            stale_threshold_s=policy.stale_threshold_s,
            verdict=StaleVerdict.FRESH,
        )

    blocked = runtime_mode in policy.blocking_runtime_modes
    verdict = StaleVerdict.HARD_STALE if blocked else StaleVerdict.DEGRADED
    return ExchangeStalenessResult(
        policy_id=policy.policy_id,
        pair=pair,
        stream_type=stream_type,
        runtime_mode=runtime_mode,
        local_timestamp=local_timestamp,
        exchange_timestamp=exchange_timestamp,
        delta_s=delta,
        signed_delta_s=signed_delta,
        stale_threshold_s=policy.stale_threshold_s,
        verdict=verdict,
        blocked=blocked,
    )
