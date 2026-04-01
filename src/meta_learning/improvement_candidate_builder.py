"""Build governed improvement candidates from hypotheses."""

from __future__ import annotations

import hashlib

from interface_contracts import StrategyClassification
from meta_learning.contracts import ImprovementCandidate, LearningHypothesis
from meta_learning.enums import CandidateGovernanceStage, CandidateKind


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
            kind = CandidateKind.BUILD14_ENABLER
        elif hypothesis.category in {"cost_drift", "sterilization"}:
            kind = CandidateKind.GUARD_TIGHTENING
        else:
            kind = CandidateKind.PARAMETER_TUNING

        tests_required = (
            "tests/test_meta_learning/test_contracts.py",
            "tests/test_meta_learning/test_build9x_integration.py",
        )
        if hypothesis.category in {"cost_drift", "sterilization"}:
            tests_required += ("tests/test_meta_learning/test_build9x_candidates.py",)
        if hypothesis.category == "near_miss":
            tests_required += (
                "tests/test_meta_learning/test_near_miss_and_candidates.py",
            )

        candidates.append(ImprovementCandidate(
            candidate_id=f"{correlation_id}:candidate:{index}",
            correlation_id=correlation_id,
            hypothesis_ids=(hypothesis.hypothesis_id,),
            classification=strategy_classification,
            kind=kind,
            summary=f"Validate {hypothesis.title.lower()} in LOCAL_REPLAY",
            candidate_version=f"{correlation_id}:candidate:{index}.v1",
            tests_required=tests_required,
            replay_scope=(
                hypothesis.required_replay_scope
                or f"{hypothesis.category}:local_replay"
            ),
            shared_core_hash=hashlib.sha256(
                (
                    hypothesis.source_version
                    or f"{correlation_id}:{strategy_classification.value}"
                ).encode("utf-8")
            ).hexdigest(),
            governance_stage=CandidateGovernanceStage.PREPARED,
        ))

    return tuple(candidates)


__all__ = [
    "build_improvement_candidates",
]
