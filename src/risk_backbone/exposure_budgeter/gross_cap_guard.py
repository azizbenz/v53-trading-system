"""
Build-4 / exposure_budgeter / gross_cap_guard
Enforce global gross exposure cap.

GrossExp ≤ X_gross,max
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class GrossCapVerdict(StrEnum):
    ACCEPTED = "accepted"
    REJECTED_POSITION_CAP = "rejected_position_cap"
    REJECTED_GROSS_CAP = "rejected_gross_cap"


class GrossCapResult(BaseModel, frozen=True):
    """Result of gross cap evaluation for a candidate trade."""

    pair: str
    candidate_size: float
    current_gross: float
    projected_gross: float
    position_cap: float
    gross_cap: float
    verdict: GrossCapVerdict
    reason: str = ""


def evaluate_gross_cap(
    pair: str,
    candidate_size: float,
    current_gross: float,
    position_cap: float,
    gross_cap: float,
    current_pair_exposure: float,
) -> GrossCapResult:
    """Evaluate both position cap and gross cap in a single pass."""
    projected = current_gross + candidate_size

    # Position cap: check projected pair exposure, not candidate alone
    projected_pair = current_pair_exposure + candidate_size
    if projected_pair > position_cap:
        return GrossCapResult(
            pair=pair,
            candidate_size=candidate_size,
            current_gross=current_gross,
            projected_gross=projected,
            position_cap=position_cap,
            gross_cap=gross_cap,
            verdict=GrossCapVerdict.REJECTED_POSITION_CAP,
            reason=f"{pair}: projected pair exposure {projected_pair} exceeds position cap {position_cap}",
        )

    # Gross cap
    if projected > gross_cap:
        return GrossCapResult(
            pair=pair,
            candidate_size=candidate_size,
            current_gross=current_gross,
            projected_gross=projected,
            position_cap=position_cap,
            gross_cap=gross_cap,
            verdict=GrossCapVerdict.REJECTED_GROSS_CAP,
            reason=f"Projected gross {projected} exceeds cap {gross_cap}",
        )

    return GrossCapResult(
        pair=pair,
        candidate_size=candidate_size,
        current_gross=current_gross,
        projected_gross=projected,
        position_cap=position_cap,
        gross_cap=gross_cap,
        verdict=GrossCapVerdict.ACCEPTED,
    )
