"""Build governed improvement candidates from hypotheses."""

from __future__ import annotations

from interface_contracts import StrategyClassification
from meta_learning.contracts import ImprovementCandidate, LearningHypothesis
from meta_learning.enums import CandidateKind


def build_improvement_candidates(
    correlation_id: str,
    strategy_classification: StrategyClassification,
    hypotheses: tuple[LearningHypothesis, ...],
) -> tuple[ImprovementCandidate, ...]:
    """Turn governed hypotheses into replay-only candidates."""

    candidates: list[ImprovementCandidate] = []

    for index, hypothesis in enumerate(hypotheses, start=1):
        if hypothesis.category == "no_issue":
            continue

        if hypothesis.category == "trace_coverage":
            kind = CandidateKind.OBSERVABILITY_ONLY
        elif strategy_classification == StrategyClassification.BUILD14_ENABLER:
            kind = CandidateKind.BUILD14_READ_ONLY
        elif hypothesis.category in {"cost_drift", "sterilization"}:
            kind = CandidateKind.GUARD_TIGHTENING
        else:
            kind = CandidateKind.PARAMETER_TUNING

        candidates.append(ImprovementCandidate(
            candidate_id=f"{correlation_id}:candidate:{index}",
            correlation_id=correlation_id,
            hypothesis_ids=(hypothesis.hypothesis_id,),
            classification=strategy_classification,
            kind=kind,
            summary=f"Validate {hypothesis.title.lower()} in LOCAL_REPLAY",
        ))

    return tuple(candidates)


__all__ = [
    "build_improvement_candidates",
]
