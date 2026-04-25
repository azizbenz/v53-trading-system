"""
Build-8 / arbitration_record
Typed Narang-style portfolio arbitration answers for promoted and rejected intents.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from portfolio_minimal.opportunity_selector.candidate_pool_builder import OpportunityCandidate
from portfolio_minimal.opportunity_selector.eligibility_filter import PortfolioSnapshot


class PortfolioArbitrationVerdict(StrEnum):
    PROMOTED = "promoted"
    REJECTED_SELECTION = "rejected_selection"
    REJECTED_ALLOCATION = "rejected_allocation"


class ArbitrationQuestionAnswer(BaseModel, frozen=True):
    """Answer to one of the five portfolio arbitration questions."""

    passed: bool
    observed_value: float
    benchmark_value: float
    preference: str


class PortfolioArbitrationRecord(BaseModel, frozen=True):
    """Frozen arbitration record attached to the canonical Build-8 portfolio rail."""

    pair: str
    engine_id: str
    rank: int
    verdict: PortfolioArbitrationVerdict
    reason_codes: tuple[str, ...] = ()
    ranking_score: float
    expected_ce: float
    final_size: float
    capital_lockup_utilisation: float
    correlated_budget_consumption: float
    hidden_structural_risk_addition: float
    best_net_score: ArbitrationQuestionAnswer
    best_expected_ce: ArbitrationQuestionAnswer
    best_capital_lockup_utilisation: ArbitrationQuestionAnswer
    lowest_correlated_budget_consumption: ArbitrationQuestionAnswer
    lowest_hidden_structural_risk_addition: ArbitrationQuestionAnswer


class PortfolioArbitrationSnapshot(BaseModel, frozen=True):
    """Internal typed snapshot used to compare candidates consistently."""

    pair: str
    engine_id: str
    rank: int
    ranking_score: float
    expected_ce: float
    final_size: float
    capital_lockup_utilisation: float
    correlated_budget_consumption: float
    hidden_structural_risk_addition: float


def _positive_scale(preferred: float, observed: float) -> float:
    if preferred > 0.0:
        return preferred
    if abs(observed) > 0.0:
        return abs(observed)
    return 1.0


def build_arbitration_snapshot(
    *,
    candidate: OpportunityCandidate,
    rank: int,
    ranking_score: float,
    final_size: float,
    initial_snapshot: PortfolioSnapshot,
) -> PortfolioArbitrationSnapshot:
    """Build comparable portfolio metrics from current repo-truth candidate inputs."""

    effective_holding_hours = candidate.holding_hours if candidate.holding_hours > 0.0 else 1.0
    capital_lockup_utilisation = candidate.ce_expected / effective_holding_hours

    size_ratio = 0.0
    if candidate.candidate_size > 0.0 and final_size > 0.0:
        size_ratio = final_size / candidate.candidate_size

    scaled_loss = candidate.estimated_loss * size_ratio
    scaled_beta = abs(candidate.beta_impact) * size_ratio
    cluster_scale = _positive_scale(
        initial_snapshot.remaining_cluster_capacity.get(candidate.cluster_id, 0.0),
        final_size,
    )
    beta_scale = _positive_scale(initial_snapshot.remaining_beta_capacity, scaled_beta)
    loss_scale = _positive_scale(initial_snapshot.remaining_loss_capacity, scaled_loss)

    correlated_budget_consumption = (final_size / cluster_scale) + (scaled_beta / beta_scale)
    hidden_structural_risk_addition = (scaled_loss / loss_scale) + (scaled_beta / beta_scale)

    return PortfolioArbitrationSnapshot(
        pair=candidate.pair,
        engine_id=candidate.engine_id,
        rank=rank,
        ranking_score=ranking_score,
        expected_ce=candidate.ce_expected,
        final_size=final_size,
        capital_lockup_utilisation=capital_lockup_utilisation,
        correlated_budget_consumption=correlated_budget_consumption,
        hidden_structural_risk_addition=hidden_structural_risk_addition,
    )


def _build_question_answer(
    *,
    observed_value: float,
    benchmark_value: float,
    preference: str,
    passed: bool,
) -> ArbitrationQuestionAnswer:
    return ArbitrationQuestionAnswer(
        passed=passed,
        observed_value=observed_value,
        benchmark_value=benchmark_value,
        preference=preference,
    )


def build_arbitration_record(
    *,
    snapshot: PortfolioArbitrationSnapshot,
    peers: tuple[PortfolioArbitrationSnapshot, ...],
    verdict: PortfolioArbitrationVerdict,
    reason_codes: tuple[str, ...],
) -> PortfolioArbitrationRecord:
    """Answer the five portfolio questions for one candidate on the current rail."""

    cohort = peers if peers else (snapshot,)
    best_net_score = max(peer.ranking_score for peer in cohort)
    best_expected_ce = max(peer.expected_ce for peer in cohort)
    best_lockup = max(peer.capital_lockup_utilisation for peer in cohort)
    lowest_correlation = min(peer.correlated_budget_consumption for peer in cohort)
    lowest_structural_risk = min(peer.hidden_structural_risk_addition for peer in cohort)

    is_promoted = verdict == PortfolioArbitrationVerdict.PROMOTED

    return PortfolioArbitrationRecord(
        pair=snapshot.pair,
        engine_id=snapshot.engine_id,
        rank=snapshot.rank,
        verdict=verdict,
        reason_codes=reason_codes,
        ranking_score=snapshot.ranking_score,
        expected_ce=snapshot.expected_ce,
        final_size=snapshot.final_size,
        capital_lockup_utilisation=snapshot.capital_lockup_utilisation,
        correlated_budget_consumption=snapshot.correlated_budget_consumption,
        hidden_structural_risk_addition=snapshot.hidden_structural_risk_addition,
        best_net_score=_build_question_answer(
            observed_value=snapshot.ranking_score,
            benchmark_value=best_net_score,
            preference="max",
            passed=is_promoted and snapshot.ranking_score >= best_net_score,
        ),
        best_expected_ce=_build_question_answer(
            observed_value=snapshot.expected_ce,
            benchmark_value=best_expected_ce,
            preference="max",
            passed=is_promoted and snapshot.expected_ce >= best_expected_ce,
        ),
        best_capital_lockup_utilisation=_build_question_answer(
            observed_value=snapshot.capital_lockup_utilisation,
            benchmark_value=best_lockup,
            preference="max",
            passed=is_promoted and snapshot.capital_lockup_utilisation >= best_lockup,
        ),
        lowest_correlated_budget_consumption=_build_question_answer(
            observed_value=snapshot.correlated_budget_consumption,
            benchmark_value=lowest_correlation,
            preference="min",
            passed=(
                is_promoted
                and snapshot.correlated_budget_consumption <= lowest_correlation
            ),
        ),
        lowest_hidden_structural_risk_addition=_build_question_answer(
            observed_value=snapshot.hidden_structural_risk_addition,
            benchmark_value=lowest_structural_risk,
            preference="min",
            passed=(
                is_promoted
                and snapshot.hidden_structural_risk_addition <= lowest_structural_risk
            ),
        ),
    )
