"""Consistency guard for governed LOCAL_REPLAY runs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


class RunConsistencyGuardReport(BaseModel, frozen=True):
    """Audit-ready comparison of two replay runs on the same historical input."""

    reference_label: str = Field(..., min_length=1)
    candidate_label: str = Field(..., min_length=1)
    compared_records: int = Field(default=0, ge=0)
    missing_record_ids: tuple[str, ...] = ()
    decision_drift_ids: tuple[str, ...] = ()
    penalty_drift_ids: tuple[str, ...] = ()
    final_size_drift_ids: tuple[str, ...] = ()
    hard_block_drift_ids: tuple[str, ...] = ()
    consistent: bool = False
    summary: str = Field(..., min_length=1)


def compare_replay_runs(
    reference_records: tuple[DTRRecord, ...],
    candidate_records: tuple[DTRRecord, ...],
    *,
    reference_label: str = "shadow_fidelity_mode",
    candidate_label: str = "candidate_run",
    score_tolerance: float = 1e-9,
    size_tolerance: float = 1e-9,
) -> RunConsistencyGuardReport:
    """Compare two replay outputs and flag any business-decision drift."""

    reference_map = {record.dtr_id: record for record in reference_records}
    candidate_map = {record.dtr_id: record for record in candidate_records}
    missing_record_ids = tuple(
        sorted(set(reference_map).symmetric_difference(candidate_map))
    )
    compared_ids = tuple(sorted(set(reference_map).intersection(candidate_map)))

    decision_drift_ids: list[str] = []
    penalty_drift_ids: list[str] = []
    final_size_drift_ids: list[str] = []
    hard_block_drift_ids: list[str] = []

    for dtr_id in compared_ids:
        reference = reference_map[dtr_id]
        candidate = candidate_map[dtr_id]
        if (
            reference.decision_state != candidate.decision_state
            or reference.ranking_position != candidate.ranking_position
            or abs(reference.final_score - candidate.final_score) > score_tolerance
        ):
            decision_drift_ids.append(dtr_id)
        if abs(reference.penalized_score - candidate.penalized_score) > score_tolerance:
            penalty_drift_ids.append(dtr_id)
        if abs(reference.final_size - candidate.final_size) > size_tolerance:
            final_size_drift_ids.append(dtr_id)
        if reference.hard_block_reasons != candidate.hard_block_reasons:
            hard_block_drift_ids.append(dtr_id)

    consistent = not (
        missing_record_ids
        or decision_drift_ids
        or penalty_drift_ids
        or final_size_drift_ids
        or hard_block_drift_ids
    )
    return RunConsistencyGuardReport(
        reference_label=reference_label,
        candidate_label=candidate_label,
        compared_records=len(compared_ids),
        missing_record_ids=missing_record_ids,
        decision_drift_ids=tuple(decision_drift_ids),
        penalty_drift_ids=tuple(penalty_drift_ids),
        final_size_drift_ids=tuple(final_size_drift_ids),
        hard_block_drift_ids=tuple(hard_block_drift_ids),
        consistent=consistent,
        summary=(
            f"reference={reference_label} / candidate={candidate_label} / "
            f"compared={len(compared_ids)} / consistent={'yes' if consistent else 'no'}"
        ),
    )


__all__ = [
    "RunConsistencyGuardReport",
    "compare_replay_runs",
]
