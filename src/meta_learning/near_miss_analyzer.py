"""Identify governed near misses from Build-9 DTR records."""

from __future__ import annotations

from meta_learning.contracts import DiagnosticResult
from meta_learning.enums import DiagnosticSeverity
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


_NEAR_MISS_STATES = {
    DecisionState.HARD_BLOCKED,
    DecisionState.REJECTED_RANKING,
    DecisionState.EVALUATED,
}


def analyze_near_misses(
    correlation_id: str,
    records: tuple[DTRRecord, ...],
    *,
    final_score_threshold: float = 0.70,
) -> tuple[DiagnosticResult, ...]:
    """Surface high-score opportunities that stopped before execution."""

    near_misses: list[DiagnosticResult] = []

    for index, record in enumerate(records, start=1):
        if record.final_score < final_score_threshold:
            continue
        if record.decision_state not in _NEAR_MISS_STATES:
            continue

        near_misses.append(DiagnosticResult(
            diagnostic_id=f"{correlation_id}:near_miss:{index}",
            correlation_id=correlation_id,
            category="near_miss",
            summary=(
                f"Near miss on {record.pair}: final_score={record.final_score:.2f}, "
                f"state={record.decision_state}"
            ),
            severity=DiagnosticSeverity.WARNING,
            evidence_refs=(record.dtr_id,),
            structured_log_key="build9x.diagnostic.near_miss",
        ))

    return tuple(near_misses)


__all__ = [
    "analyze_near_misses",
]
