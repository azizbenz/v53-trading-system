"""
Build-5 / ranking_router / ranking_score_builder
Compute relative priority of candidates.

R_i = ω₁·S_i + ω₂·CE_i - ω₃·Cost_i - ω₄·CorrPenalty_i - ω₅·RiskPenalty_i
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RankingWeights(BaseModel, frozen=True):
    """Versioned ranking weights."""

    w_score: float = 1.0
    w_ce: float = 0.5
    w_cost: float = 0.3
    w_corr: float = 0.2
    w_risk: float = 0.2
    version: str = "1.0"


class RankedCandidate(BaseModel, frozen=True):
    """Candidate with computed ranking score."""

    engine_id: str
    pair: str
    penalized_score: float
    expected_ce: float
    expected_cost: float
    corr_penalty: float = 0.0
    risk_penalty: float = 0.0
    ranking_score: float = 0.0
    rank: int = 0


def compute_ranking_scores(
    candidates: tuple[dict[str, float | str], ...],
    weights: RankingWeights,
) -> tuple[RankedCandidate, ...]:
    """Compute R_i for each candidate and sort descending.

    Each candidate dict must have: engine_id, pair, penalized_score, expected_ce,
    expected_cost. Optional: corr_penalty, risk_penalty.
    """
    scored: list[RankedCandidate] = []

    for c in candidates:
        s = float(c.get("penalized_score", 0.0))
        ce = float(c.get("expected_ce", 0.0))
        cost = float(c.get("expected_cost", 0.0))
        corr = float(c.get("corr_penalty", 0.0))
        risk = float(c.get("risk_penalty", 0.0))

        r = (
            weights.w_score * s
            + weights.w_ce * ce
            - weights.w_cost * cost
            - weights.w_corr * corr
            - weights.w_risk * risk
        )

        scored.append(RankedCandidate(
            engine_id=str(c.get("engine_id", "")),
            pair=str(c.get("pair", "")),
            penalized_score=s,
            expected_ce=ce,
            expected_cost=cost,
            corr_penalty=corr,
            risk_penalty=risk,
            ranking_score=r,
        ))

    # Sort descending by ranking_score
    scored.sort(key=lambda x: x.ranking_score, reverse=True)

    # Assign ranks
    ranked = tuple(
        RankedCandidate(
            engine_id=c.engine_id,
            pair=c.pair,
            penalized_score=c.penalized_score,
            expected_ce=c.expected_ce,
            expected_cost=c.expected_cost,
            corr_penalty=c.corr_penalty,
            risk_penalty=c.risk_penalty,
            ranking_score=c.ranking_score,
            rank=i + 1,
        )
        for i, c in enumerate(scored)
    )

    return ranked
