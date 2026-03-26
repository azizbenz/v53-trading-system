"""
5.5.3 — Gap Fill Controller: decide if a data gap is acceptable to fill via REST.

Invariant: gap too large = explicit rejection. REST must not become the real-time feed.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class GapFillDecision(StrEnum):
    FILL = "fill"
    REJECT_TOO_LARGE = "reject_too_large"
    REJECT_RATE_LIMITED = "reject_rate_limited"


class GapFillRequest(BaseModel, frozen=True):
    pair: str
    gap_start: float
    gap_end: float
    gap_size_s: float


class GapFillResult(BaseModel, frozen=True):
    request: GapFillRequest
    decision: GapFillDecision
    message: str = ""


def evaluate_gap_fill(
    pair: str,
    gap_start: float,
    gap_end: float,
    max_gap_s: float = 300.0,
    rate_limited: bool = False,
) -> GapFillResult:
    """Decide whether to fill a gap via REST.

    Rules:
    - Gap > max_gap_s → reject (too large)
    - Rate limited → reject
    - Otherwise → fill
    """
    gap_size = gap_end - gap_start
    request = GapFillRequest(
        pair=pair, gap_start=gap_start, gap_end=gap_end, gap_size_s=gap_size,
    )

    if rate_limited:
        return GapFillResult(
            request=request,
            decision=GapFillDecision.REJECT_RATE_LIMITED,
            message="REST rate limit reached",
        )

    if gap_size > max_gap_s:
        return GapFillResult(
            request=request,
            decision=GapFillDecision.REJECT_TOO_LARGE,
            message=f"Gap {gap_size:.1f}s exceeds max {max_gap_s:.1f}s",
        )

    return GapFillResult(
        request=request,
        decision=GapFillDecision.FILL,
        message=f"Gap {gap_size:.1f}s accepted for fill",
    )
