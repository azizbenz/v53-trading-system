"""
8.5.4 — Stale Hard Guard: trigger explicit stale block when Δ_i > Δ_hard.

Invariant: stale hard block is traceable and explicit.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class StaleVerdict(StrEnum):
    FRESH = "fresh"
    DEGRADED = "degraded"  # past soft threshold, penalty applies
    HARD_STALE = "hard_stale"  # past hard threshold, blocked


class StaleGuardResult(BaseModel, frozen=True):
    """Result of stale hard guard evaluation."""

    pair: str
    stream_type: str
    age_s: float
    soft_threshold_s: float
    hard_threshold_s: float
    verdict: StaleVerdict
    blocked: bool = False


def evaluate_staleness(
    pair: str,
    stream_type: str,
    age_s: float,
    soft_threshold_s: float = 5.0,
    hard_threshold_s: float = 30.0,
) -> StaleGuardResult:
    """Evaluate staleness with soft (degraded) and hard (blocked) thresholds.

    - age < soft → FRESH
    - soft ≤ age < hard → DEGRADED (penalty applies, not blocked)
    - age ≥ hard → HARD_STALE (blocked)
    """
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
