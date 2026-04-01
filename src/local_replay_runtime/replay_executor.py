"""Governed session executor for LOCAL_REPLAY artifact generation."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from local_replay_runtime.artifact_exporter import (
    ReplayArtifactExportRequest,
    ReplayArtifactExportResult,
    export_local_replay_artifact,
)
from local_replay_runtime.replay_dtr_exporter import export_replay_dtr_records
from local_replay_runtime.replay_metrics_collector import (
    ReplayMetricsSummary,
    build_replay_metrics_summary,
)
from local_replay_runtime.replay_run_manifest import ReplayRunManifest
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


class ReplayExecutionInput(BaseModel, frozen=True):
    """Typed local replay session inputs used to produce a governed artifact."""

    run_manifest: ReplayRunManifest
    total_opportunities: int = Field(..., ge=1)
    dtr_records: tuple[DTRRecord, ...] = ()
    feature_bridge_payload: dict
    parity_diagnostics_payload: dict
    review_notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_session(self) -> "ReplayExecutionInput":
        if self.run_manifest.record_count < len(self.dtr_records):
            raise ValueError(
                "ReplayExecutionInput run_manifest.record_count must cover exported DTR records"
            )
        return self


class ReplayExecutionResult(BaseModel, frozen=True):
    """Stable result of the governed local replay session executor."""

    export_result: ReplayArtifactExportResult
    metrics_summary: ReplayMetricsSummary


def _review_markdown(
    execution_input: ReplayExecutionInput,
    metrics_summary: ReplayMetricsSummary,
) -> str:
    notes = execution_input.review_notes or ("No additional review note.",)
    lines = [
        "# Governed Local Replay Review",
        "",
        "## Run",
        f"- run_id: {execution_input.run_manifest.run_id}",
        f"- strategy_id: {execution_input.run_manifest.strategy_id}",
        f"- strategy_version: {execution_input.run_manifest.strategy_version}",
        f"- lineage_version: {execution_input.run_manifest.lineage_version}",
        f"- profile_scope: {execution_input.run_manifest.profile_scope.value}",
        f"- runtime_mode: {execution_input.run_manifest.runtime_mode.value}",
        f"- performance_mode: {execution_input.run_manifest.performance_mode}",
        "",
        "## Coverage",
        f"- total_opportunities: {execution_input.total_opportunities}",
        f"- total_records: {metrics_summary.total_records}",
        f"- dtr_coverage: {metrics_summary.dtr_coverage:.3f}",
        "",
        "## Replay Metrics",
        f"- ce_net: {metrics_summary.ce_net:.6f}",
        f"- expected_cost_mean: {metrics_summary.expected_cost_mean:.6f}",
        f"- realized_cost_mean: {metrics_summary.realized_cost_mean:.6f}",
        f"- gross_return_total: {metrics_summary.gross_return_total:.6f}",
        f"- drawdown_proxy: {metrics_summary.drawdown_proxy:.6f}",
        "",
        "## Parity",
        f"- status: {execution_input.parity_diagnostics_payload.get('parity_status', 'unknown')}",
        f"- decision_match_rate: {execution_input.parity_diagnostics_payload.get('decision_match_rate', 'n/a')}",
        "",
        "## Notes",
        *[f"- {note}" for note in notes],
    ]
    return "\n".join(lines) + "\n"


def execute_local_replay_export(
    output_dir: Path,
    execution_input: ReplayExecutionInput,
) -> ReplayExecutionResult:
    """Build a governed LOCAL_REPLAY artifact directly from a typed replay session."""

    metrics_summary = build_replay_metrics_summary(
        execution_input.dtr_records,
        total_opportunities=execution_input.total_opportunities,
    )
    export_result = export_local_replay_artifact(
        output_dir,
        ReplayArtifactExportRequest(
            run_manifest=execution_input.run_manifest,
            review_export_markdown=_review_markdown(execution_input, metrics_summary),
            feature_bridge_payload=execution_input.feature_bridge_payload,
            parity_diagnostics_payload=execution_input.parity_diagnostics_payload,
            replay_metrics_payload=metrics_summary.model_dump(mode="json"),
            replay_dtr_records=export_replay_dtr_records(execution_input.dtr_records),
        ),
    )
    return ReplayExecutionResult(
        export_result=export_result,
        metrics_summary=metrics_summary,
    )


__all__ = [
    "ReplayExecutionInput",
    "ReplayExecutionResult",
    "execute_local_replay_export",
]
