"""
Build-5 / penalty_aggregator / penalty_cap_guard
Prevent sum of soft penalties from becoming a disguised veto.

If penalties exceed a cap, clamp and flag phantom risk.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class PenaltyCapVerdict(StrEnum):
    NORMAL = "normal"
    CAPPED = "capped"
    PHANTOM_RISK = "phantom_risk"


class PenaltyCapResult(BaseModel, frozen=True):
    """Result of penalty cap evaluation."""

    original_score_penalty: float
    capped_score_penalty: float
    original_size_multiplier: float
    capped_size_multiplier: float
    verdict: PenaltyCapVerdict
    reason: str = ""


def evaluate_penalty_cap(
    score_penalty: float,
    size_multiplier: float,
    max_score_penalty: float,
    min_size_multiplier: float,
    raw_score: float,
    expected_cost: float = 0.0,
) -> PenaltyCapResult:
    """Evaluate and cap penalties.

    Phantom risk: x_i · E[r_i] ≤ c_i^op + ε
    Approximation: if adjusted_score * size_multiplier is near zero relative to cost.
    """
    capped_sp = min(score_penalty, max_score_penalty)
    capped_sm = max(size_multiplier, min_size_multiplier)

    adjusted_score = raw_score - capped_sp
    effective_value = adjusted_score * capped_sm

    is_capped = capped_sp < score_penalty or capped_sm > size_multiplier

    # Phantom risk: effective value near zero or negative relative to expected cost
    is_phantom = effective_value <= expected_cost and raw_score > 0

    if is_phantom:
        verdict = PenaltyCapVerdict.PHANTOM_RISK
        reason = (
            f"effective value {effective_value:.4f} <= expected cost {expected_cost:.4f} "
            f"— trade is economically non-monetizable"
        )
    elif is_capped:
        verdict = PenaltyCapVerdict.CAPPED
        reason = "penalties capped to prevent disguised veto"
    else:
        verdict = PenaltyCapVerdict.NORMAL
        reason = ""

    return PenaltyCapResult(
        original_score_penalty=score_penalty,
        capped_score_penalty=capped_sp,
        original_size_multiplier=size_multiplier,
        capped_size_multiplier=capped_sm,
        verdict=verdict,
        reason=reason,
    )
