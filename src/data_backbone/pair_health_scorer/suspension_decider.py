"""
10.5.2 — Suspension Decider: suspend pair if health below threshold.

Invariant: every suspension has an explicit reason.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SuspensionReason(StrEnum):
    HEALTH_BELOW_THRESHOLD = "health_below_threshold"
    HARD_STALE = "hard_stale"
    CONSISTENCY_FAILURE = "consistency_failure"
    MANUAL = "manual"


class SuspensionDecision(BaseModel, frozen=True):
    """Decision about whether to suspend a pair."""

    pair: str
    should_suspend: bool
    reason: SuspensionReason | None = None
    health_score: float = 0.0
    threshold: float = 0.0
    message: str = ""


def evaluate_suspension(
    pair: str,
    health_score: float,
    threshold: float = 0.3,
    hard_stale: bool = False,
    consistency_failed: bool = False,
) -> SuspensionDecision:
    """Decide if a pair should be suspended.

    Suspension triggers:
    - health_score < threshold
    - hard_stale flag
    - consistency_failed flag
    """
    if hard_stale:
        return SuspensionDecision(
            pair=pair,
            should_suspend=True,
            reason=SuspensionReason.HARD_STALE,
            health_score=health_score,
            threshold=threshold,
            message=f"{pair}: hard stale detected",
        )

    if consistency_failed:
        return SuspensionDecision(
            pair=pair,
            should_suspend=True,
            reason=SuspensionReason.CONSISTENCY_FAILURE,
            health_score=health_score,
            threshold=threshold,
            message=f"{pair}: consistency check failed",
        )

    if health_score < threshold:
        return SuspensionDecision(
            pair=pair,
            should_suspend=True,
            reason=SuspensionReason.HEALTH_BELOW_THRESHOLD,
            health_score=health_score,
            threshold=threshold,
            message=f"{pair}: health {health_score:.3f} < threshold {threshold:.3f}",
        )

    return SuspensionDecision(
        pair=pair,
        should_suspend=False,
        health_score=health_score,
        threshold=threshold,
        message=f"{pair}: healthy ({health_score:.3f})",
    )
