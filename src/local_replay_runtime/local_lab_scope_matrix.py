"""Typed multi-scope projection for Local IA Lab candidate vs baseline analysis."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from interface_contracts import ArtifactProofSummary
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


class LocalLabScopeKey(BaseModel, frozen=True):
    """Bounded pair/engine scope key for Local IA Lab review orchestration."""

    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    scope_slug: str = Field(..., min_length=1)


class LocalLabScopeAnalysisRow(BaseModel, frozen=True):
    """Audit-ready per-scope status emitted by the Local IA Lab analysis bundle."""

    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    scope_slug: str = Field(..., min_length=1)
    review_output_dir: str = Field(..., min_length=1)
    review_bundle_path: str = Field(..., min_length=1)
    trade_loss_attribution_path: str = Field(..., min_length=1)
    artifact_ablation_study_path: str = Field(..., min_length=1)
    artifact_proof_summary_path: str = Field(..., min_length=1)
    artifact_proof_assessment_path: str = Field(..., min_length=1)
    candidate_record_count: int = Field(default=0, ge=0)
    baseline_record_count: int = Field(default=0, ge=0)
    executed_records: int = Field(default=0, ge=0)
    losing_trade_count: int = Field(default=0, ge=0)
    artifact_ablation_ready: bool = False
    artifact_proof_ready: bool = False
    artifact_proof_validation_reasons: tuple[str, ...] = ()
    release_ready: bool = False
    release_blocking_reasons: tuple[str, ...] = ()
    release_scope_summary_path: str | None = None
    caution_flags: tuple[str, ...] = ()
    proof_summary: ArtifactProofSummary


class LocalLabScopeAnalysisMatrix(BaseModel, frozen=True):
    """Future-dashboard projection of all reviewed Local IA Lab scopes."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    baseline_export_dir: str | None = None
    scope_count: int = Field(default=0, ge=0)
    ready_scope_count: int = Field(default=0, ge=0)
    blocked_scope_count: int = Field(default=0, ge=0)
    release_ready_scope_count: int = Field(default=0, ge=0)
    release_blocked_scope_count: int = Field(default=0, ge=0)
    scopes: tuple[LocalLabScopeAnalysisRow, ...] = ()


def build_local_lab_scope_slug(pair: str, engine_id: str) -> str:
    """Build a deterministic filesystem-safe slug for a pair/engine scope."""

    def _normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")

    return f"{_normalize(pair)}__{_normalize(engine_id)}"


def discover_local_lab_scope_keys(
    records: tuple[DTRRecord, ...],
    *,
    pair: str | None = None,
    engine_id: str | None = None,
) -> tuple[LocalLabScopeKey, ...]:
    """Enumerate governed pair/engine scopes from exported DTR evidence."""

    scopes = {
        (record.pair, record.engine_id)
        for record in records
        if (pair is None or record.pair == pair)
        and (engine_id is None or record.engine_id == engine_id)
    }
    return tuple(
        LocalLabScopeKey(
            pair=scope_pair,
            engine_id=scope_engine_id,
            scope_slug=build_local_lab_scope_slug(scope_pair, scope_engine_id),
        )
        for scope_pair, scope_engine_id in sorted(scopes)
    )


def build_local_lab_scope_matrix(
    *,
    correlation_id: str,
    export_dir: str,
    baseline_export_dir: str | None,
    scopes: tuple[LocalLabScopeAnalysisRow, ...],
) -> LocalLabScopeAnalysisMatrix:
    """Build the bounded multi-scope Local IA Lab dashboard projection."""

    ready_scope_count = sum(1 for scope in scopes if scope.artifact_proof_ready)
    release_ready_scope_count = sum(1 for scope in scopes if scope.release_ready)
    return LocalLabScopeAnalysisMatrix(
        correlation_id=correlation_id,
        export_dir=export_dir,
        baseline_export_dir=baseline_export_dir,
        scope_count=len(scopes),
        ready_scope_count=ready_scope_count,
        blocked_scope_count=len(scopes) - ready_scope_count,
        release_ready_scope_count=release_ready_scope_count,
        release_blocked_scope_count=len(scopes) - release_ready_scope_count,
        scopes=scopes,
    )


__all__ = [
    "LocalLabScopeAnalysisMatrix",
    "LocalLabScopeAnalysisRow",
    "LocalLabScopeKey",
    "build_local_lab_scope_matrix",
    "build_local_lab_scope_slug",
    "discover_local_lab_scope_keys",
]
