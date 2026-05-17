"""Governed Local IA Lab ablation study between baseline and candidate replay exports."""

from __future__ import annotations

from pydantic import BaseModel, Field

from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


class LocalLabAblationStudy(BaseModel, frozen=True):
    """Audit-ready ablation comparison for candidate vs baseline Local IA Lab evidence."""

    correlation_id: str = Field(..., min_length=1)
    candidate_export_dir: str = Field(..., min_length=1)
    baseline_export_dir: str | None = None
    candidate_run_id: str = Field(..., min_length=1)
    baseline_run_id: str | None = None
    candidate_dataset_manifest_id: str = Field(..., min_length=1)
    baseline_dataset_manifest_id: str | None = None
    selected_pair: str | None = None
    selected_engine_id: str | None = None
    aligned_record_count: int = Field(default=0, ge=0)
    candidate_executed_count: int = Field(default=0, ge=0)
    baseline_executed_count: int = Field(default=0, ge=0)
    candidate_net_pnl: float = 0.0
    baseline_net_pnl: float = 0.0
    ablation_delta_net_pnl: float = 0.0
    candidate_ce_mean: float | None = None
    baseline_ce_mean: float | None = None
    ablation_delta_ce: float | None = None
    candidate_block_rate: float = 0.0
    baseline_block_rate: float = 0.0
    block_rate_delta: float = 0.0
    candidate_non_execution_rate: float = 0.0
    baseline_non_execution_rate: float = 0.0
    non_execution_rate_delta: float = 0.0
    block_rate_proxy_label: str = "non_execution_rate"
    study_ready: bool = False
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()


def build_pending_local_lab_ablation_study(
    *,
    correlation_id: str,
    candidate_export_dir: str,
    candidate_run_id: str,
    candidate_dataset_manifest_id: str,
    selected_pair: str | None,
    selected_engine_id: str | None,
) -> LocalLabAblationStudy:
    """Return the explicit fail-closed ablation state when no baseline is provided."""

    return LocalLabAblationStudy(
        correlation_id=correlation_id,
        candidate_export_dir=candidate_export_dir,
        candidate_run_id=candidate_run_id,
        candidate_dataset_manifest_id=candidate_dataset_manifest_id,
        selected_pair=selected_pair,
        selected_engine_id=selected_engine_id,
        study_ready=False,
        blocking_reasons=("ABLATION_BASELINE_EXPORT_DIR_REQUIRED",),
    )


def _filter_records(
    records: tuple[DTRRecord, ...],
    *,
    pair: str | None,
    engine_id: str | None,
) -> tuple[DTRRecord, ...]:
    filtered = records
    if pair is not None:
        filtered = tuple(record for record in filtered if record.pair == pair)
    if engine_id is not None:
        filtered = tuple(record for record in filtered if record.engine_id == engine_id)
    return filtered


def _net_pnl(records: tuple[DTRRecord, ...]) -> float:
    return sum(
        record.gross_return - record.realized_cost
        for record in records
        if record.decision_state == "executed"
    )


def _ce_mean(records: tuple[DTRRecord, ...]) -> float | None:
    if not records:
        return None
    return sum(record.ce_expected for record in records) / len(records)


def _block_rate(records: tuple[DTRRecord, ...]) -> float:
    if not records:
        return 1.0
    executed_count = sum(1 for record in records if record.decision_state == "executed")
    return max(0.0, min(1.0, 1.0 - (executed_count / len(records))))


def build_local_lab_ablation_study(
    *,
    correlation_id: str,
    candidate_export_dir: str,
    baseline_export_dir: str,
    candidate_run_id: str,
    baseline_run_id: str,
    candidate_dataset_manifest_id: str,
    baseline_dataset_manifest_id: str,
    candidate_records: tuple[DTRRecord, ...],
    baseline_records: tuple[DTRRecord, ...],
    selected_pair: str | None = None,
    selected_engine_id: str | None = None,
) -> LocalLabAblationStudy:
    """Build a bounded ablation study on aligned DTR ids."""

    blocking_reasons: list[str] = []
    caution_flags: list[str] = []

    filtered_candidate = _filter_records(
        candidate_records,
        pair=selected_pair,
        engine_id=selected_engine_id,
    )
    filtered_baseline = _filter_records(
        baseline_records,
        pair=selected_pair,
        engine_id=selected_engine_id,
    )

    if candidate_dataset_manifest_id != baseline_dataset_manifest_id:
        blocking_reasons.append("ABLATION_DATASET_MANIFEST_ID_MISMATCH")
    if not filtered_candidate:
        blocking_reasons.append("ABLATION_CANDIDATE_SCOPE_EMPTY")
    if not filtered_baseline:
        blocking_reasons.append("ABLATION_BASELINE_SCOPE_EMPTY")

    candidate_ids = {record.dtr_id for record in filtered_candidate}
    baseline_ids = {record.dtr_id for record in filtered_baseline}
    if filtered_candidate and filtered_baseline and candidate_ids != baseline_ids:
        blocking_reasons.append("ABLATION_DTR_ID_MISMATCH")

    aligned_ids = tuple(sorted(candidate_ids & baseline_ids))
    candidate_by_id = {record.dtr_id: record for record in filtered_candidate}
    baseline_by_id = {record.dtr_id: record for record in filtered_baseline}
    aligned_candidate = tuple(candidate_by_id[dtr_id] for dtr_id in aligned_ids)
    aligned_baseline = tuple(baseline_by_id[dtr_id] for dtr_id in aligned_ids)

    if not aligned_ids:
        blocking_reasons.append("ABLATION_ALIGNED_RECORDS_REQUIRED")

    candidate_ce_mean = _ce_mean(aligned_candidate)
    baseline_ce_mean = _ce_mean(aligned_baseline)
    if candidate_ce_mean is None or baseline_ce_mean is None:
        blocking_reasons.append("ABLATION_CE_EVIDENCE_MISSING")

    candidate_executed_count = sum(
        1 for record in aligned_candidate if record.decision_state == "executed"
    )
    baseline_executed_count = sum(
        1 for record in aligned_baseline if record.decision_state == "executed"
    )
    if candidate_executed_count <= 0 or baseline_executed_count <= 0:
        blocking_reasons.append("ABLATION_EXECUTED_RECORDS_REQUIRED")

    candidate_net_pnl = _net_pnl(aligned_candidate)
    baseline_net_pnl = _net_pnl(aligned_baseline)
    ablation_delta_net_pnl = candidate_net_pnl - baseline_net_pnl
    ablation_delta_ce = (
        None
        if candidate_ce_mean is None or baseline_ce_mean is None
        else candidate_ce_mean - baseline_ce_mean
    )
    candidate_block_rate = _block_rate(aligned_candidate)
    baseline_block_rate = _block_rate(aligned_baseline)
    block_rate_delta = max(candidate_block_rate - baseline_block_rate, 0.0)

    if block_rate_delta > 0.0:
        caution_flags.append("ABLATION_BLOCK_RATE_WORSE_THAN_BASELINE")

    return LocalLabAblationStudy(
        correlation_id=correlation_id,
        candidate_export_dir=candidate_export_dir,
        baseline_export_dir=baseline_export_dir,
        candidate_run_id=candidate_run_id,
        baseline_run_id=baseline_run_id,
        candidate_dataset_manifest_id=candidate_dataset_manifest_id,
        baseline_dataset_manifest_id=baseline_dataset_manifest_id,
        selected_pair=selected_pair,
        selected_engine_id=selected_engine_id,
        aligned_record_count=len(aligned_ids),
        candidate_executed_count=candidate_executed_count,
        baseline_executed_count=baseline_executed_count,
        candidate_net_pnl=candidate_net_pnl,
        baseline_net_pnl=baseline_net_pnl,
        ablation_delta_net_pnl=ablation_delta_net_pnl,
        candidate_ce_mean=candidate_ce_mean,
        baseline_ce_mean=baseline_ce_mean,
        ablation_delta_ce=ablation_delta_ce,
        candidate_block_rate=candidate_block_rate,
        baseline_block_rate=baseline_block_rate,
        block_rate_delta=block_rate_delta,
        candidate_non_execution_rate=candidate_block_rate,
        baseline_non_execution_rate=baseline_block_rate,
        non_execution_rate_delta=block_rate_delta,
        study_ready=not blocking_reasons,
        blocking_reasons=tuple(blocking_reasons),
        caution_flags=tuple(caution_flags),
    )


__all__ = [
    "LocalLabAblationStudy",
    "build_local_lab_ablation_study",
    "build_pending_local_lab_ablation_study",
]
