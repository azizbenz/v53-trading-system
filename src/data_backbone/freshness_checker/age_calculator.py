"""
8.5.2 — Age Calculator: compute Δ_i = t_decision - t_last_update.

Invariant: age is always explicit and computable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgeResult(BaseModel, frozen=True):
    """Age calculation result for a pair+stream."""

    pair: str
    stream_type: str
    age_s: float
    last_update_time: float
    decision_time: float


def calculate_age(
    pair: str,
    stream_type: str,
    last_update_time: float,
    decision_time: float,
) -> AgeResult:
    """Calculate data age: Δ_i = t_decision - t_last_update."""
    return AgeResult(
        pair=pair,
        stream_type=stream_type,
        age_s=decision_time - last_update_time,
        last_update_time=last_update_time,
        decision_time=decision_time,
    )


def calculate_ages_for_pair(
    pair: str,
    stream_updates: dict[str, float],  # stream_type -> last_update_time
    decision_time: float,
) -> tuple[AgeResult, ...]:
    """Calculate ages for all streams of a pair."""
    return tuple(
        calculate_age(pair, stream, ts, decision_time)
        for stream, ts in stream_updates.items()
    )
