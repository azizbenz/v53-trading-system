"""Patch 6 batch 1 — Storage budget pre-flight estimator and report.

Used to refuse Data Factory / Strategy Ladder runs whose estimated silver
output exceeds an explicit storage budget. The default safety net is 50 GB,
which is large enough for single-pair short windows in production but small
enough to catch accidental 322 GB trade re-expansions from broad scans.

Important: this estimator is *coarse* — it walks the discovered raw files and
applies a pessimistic expansion ratio per data type. It never opens files,
never hashes, and is safe to run before the heavy work begins.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.storage_budget_support import (
    estimate_silver_size_for_paths,
    normalize_silver_storage_format,
)
from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.strategy_ladder_data_factory_models import (
    finalize_hashed_model,
)


class StorageBudgetReport(BaseModel, frozen=True):
    """Typed pre-flight storage estimator output."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str = ""
    output_root: str = ""
    raw_size_bytes: int = Field(default=0, ge=0)
    raw_size_estimate: int = Field(default=0, ge=0)
    gold_size_bytes: int = Field(default=0, ge=0)
    phase1_gold_size: int = Field(default=0, ge=0)
    phase1_candidate_export_size: int = Field(default=0, ge=0)
    candidate_count: int = Field(default=0, ge=0)
    candidate_window_count: int = Field(default=0, ge=0)
    phase2_window_size_estimate: int = Field(default=0, ge=0)
    raw_window_cache_size: int = Field(default=0, ge=0)
    silver_size_bytes: int = Field(default=0, ge=0)
    silver_size_estimate: int = Field(default=0, ge=0)
    storage_format: str = "jsonl"
    silver_storage_format: str = "jsonl"
    silver_storage_status: str = "SILVER_STORAGE_NOT_PROVEN"
    silver_bloat_ratio: float | None = None
    storage_budget_status: str = "STORAGE_BUDGET_NOT_PROVEN"
    storage_budget_limit_bytes: int = Field(default=0, ge=0)
    storage_budget_reason_codes: tuple[str, ...] = ()
    recommendation: str = ""
    blocker_severity: str = "READY"
    artifact_hash: str | None = None
    created_at: datetime | None = None


def build_storage_budget_report(
    *,
    run_id: str,
    output_root: Path,
    raw_paths: tuple[Path, ...],
    storage_format: str = "jsonl",
    storage_budget_limit_bytes: int = 53_687_091_200,  # 50 GB default
    candidate_count: int = 0,
    candidate_window_count: int = 0,
    phase1_gold_size: int = 0,
    raw_window_cache_size: int = 0,
    debug_jsonl_allowed: bool = False,
    broad_scope: bool = False,
) -> StorageBudgetReport:
    """Coarse pre-flight estimator. Never opens files."""

    normalized_storage_format = normalize_silver_storage_format(storage_format)
    storage_format_token = (
        "jsonl_gz"
        if normalized_storage_format == "jsonl-gz"
        else "jsonl_debug"
        if normalized_storage_format == "jsonl-debug"
        else "jsonl"
    )
    raw_size, silver_size = estimate_silver_size_for_paths(
        raw_paths, storage_format=normalized_storage_format
    )
    # Phase 2: T-1h..T+1h windows. Per candidate, conservatively assume a
    # raw_window snapshot of ~10 MB JSONL (snapshot+delta around the moment).
    per_window_bytes = 10 * 1024 * 1024
    phase2_window_size = candidate_window_count * per_window_bytes if candidate_window_count else 0

    total_estimate = silver_size + phase1_gold_size + phase2_window_size

    reasons: list[str] = []
    if storage_budget_limit_bytes > 0 and total_estimate > storage_budget_limit_bytes:
        if total_estimate > storage_budget_limit_bytes * 2:
            status = "STORAGE_BUDGET_EXCEEDED"
            reasons.append("STORAGE_BUDGET_EXCEEDED")
        else:
            status = "STORAGE_BUDGET_WARNING"
            reasons.append("STORAGE_BUDGET_NEAR_LIMIT")
    elif total_estimate > 0:
        status = "STORAGE_BUDGET_READY"
    else:
        status = "STORAGE_BUDGET_NOT_PROVEN"

    silver_bloat_ratio = (
        round(silver_size / raw_size, 6) if raw_size > 0 and silver_size > 0 else None
    )
    if normalized_storage_format == "jsonl-gz":
        silver_storage_status = "SILVER_STORAGE_READY_COMPRESSED"
    elif debug_jsonl_allowed:
        silver_storage_status = "SILVER_STORAGE_JSONL_DEBUG_ALLOWED"
    elif broad_scope:
        silver_storage_status = "SILVER_STORAGE_BLOAT_BLOCKER"
        reasons.append("SILVER_STORAGE_BLOAT_BLOCKER")
    else:
        silver_storage_status = "SILVER_STORAGE_BLOAT_WARNING"
    recommendation = ""
    if silver_bloat_ratio is not None and silver_bloat_ratio > 1.0:
        if normalized_storage_format != "jsonl-gz":
            silver_storage_status = (
                "SILVER_STORAGE_BLOAT_BLOCKER"
                if broad_scope and not debug_jsonl_allowed
                else "SILVER_STORAGE_BLOAT_WARNING"
            )
        reasons.append(silver_storage_status)
        recommendation = (
            "Silver estimate exceeds raw size. Prefer jsonl_gz or candidate-window "
            "replay extraction for broader runs."
        )
    if normalized_storage_format != "jsonl-gz" and silver_size > 5 * 1024 * 1024 * 1024:
        reasons.append("STORAGE_BUDGET_RECOMMEND_JSONL_GZ")
        if not recommendation:
            recommendation = "Switch silver storage to jsonl_gz for broader runs."
    blocker_severity = (
        "BLOCKER"
        if silver_storage_status == "SILVER_STORAGE_BLOAT_BLOCKER"
        or status == "STORAGE_BUDGET_EXCEEDED"
        else "WARNING"
        if silver_storage_status == "SILVER_STORAGE_BLOAT_WARNING"
        or status == "STORAGE_BUDGET_WARNING"
        else "READY"
    )

    report = StorageBudgetReport(
        run_id=run_id,
        output_root=str(output_root.resolve()),
        raw_size_bytes=raw_size,
        raw_size_estimate=raw_size,
        gold_size_bytes=phase1_gold_size,
        phase1_gold_size=phase1_gold_size,
        phase1_candidate_export_size=0,
        candidate_count=candidate_count,
        candidate_window_count=candidate_window_count,
        phase2_window_size_estimate=phase2_window_size,
        raw_window_cache_size=raw_window_cache_size,
        silver_size_bytes=silver_size,
        silver_size_estimate=silver_size,
        storage_format=normalized_storage_format,
        silver_storage_format=storage_format_token,
        silver_storage_status=silver_storage_status,
        silver_bloat_ratio=silver_bloat_ratio,
        storage_budget_status=status,
        storage_budget_limit_bytes=storage_budget_limit_bytes,
        storage_budget_reason_codes=tuple(dict.fromkeys(reasons)),
        recommendation=recommendation,
        blocker_severity=blocker_severity,
        created_at=datetime.now(tz=UTC),
    )
    return finalize_hashed_model(report)


def write_storage_budget_report(
    output_root: Path, report: StorageBudgetReport
) -> Path:
    """Persist the storage budget report next to the other manifests."""

    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "storage_budget_report.json"
    atomic_write_json(json_path, report.model_dump(mode="json"), indent=2)
    return json_path


__all__ = [
    "StorageBudgetReport",
    "build_storage_budget_report",
    "estimate_silver_size_for_paths",
    "write_storage_budget_report",
]
