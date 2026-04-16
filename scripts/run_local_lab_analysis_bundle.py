#!/usr/bin/env python3
"""Chain governed Local IA Lab post-trade review and EDGE calibration from one export_dir."""

from __future__ import annotations

import argparse
from dataclasses import field
import json
from datetime import date
from pathlib import Path
import sys

from pydantic import BaseModel, Field, ValidationError


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from backtest_artifact_import.export_dir_bridge import discover_local_replay_export  # noqa: E402
from backtest_artifact_import.local_lab_upload_bridge_candidate import (  # noqa: E402
    build_local_lab_artifact_upload_dry_run_bridge,
    build_local_lab_release_gate_summary,
    build_local_lab_source_artifact_summary,
)
from interface_contracts import ArtifactClass  # noqa: E402
from interface_contracts.atomic_io import atomic_write_json  # noqa: E402
from monitoring.local_lab_ingestion import (  # noqa: E402
    build_local_lab_monitoring_ingestion_summary,
)
from monitoring.local_lab_monitoring_bundle_manifest import (  # noqa: E402
    build_local_lab_monitoring_bundle_manifest,
)
from monitoring.local_lab_monitoring_projection import (  # noqa: E402
    build_local_lab_monitoring_projection,
)
from monitoring.local_lab_observability import (  # noqa: E402
    build_local_lab_observability_export,
)
from monitoring.local_lab_monitoring_backend import (  # noqa: E402
    build_local_lab_monitoring_backend_payload,
)
from monitoring.observability_io import write_observability_text_payload  # noqa: E402
from local_replay_runtime import (  # noqa: E402
    EdgeGateCalibrationConfig,
    EdgeGateCalibrationReport,
    build_local_lab_loss_surrogate_report,
    build_local_lab_calibration_methods_review,
    build_local_lab_calibration_normalized_report,
    build_local_lab_execution_review,
    build_local_lab_execution_runtime_projection,
    build_local_lab_multiple_testing_review,
    build_local_lab_tail_risk_review,
    build_local_lab_replay_candidate_queue,
    build_local_lab_replay_dispatch_plan,
    build_local_lab_replay_ticket_index,
    build_local_lab_replay_workflow_manifest,
    LocalLabScopeAnalysisMatrix,
    LocalLabScopeAnalysisRow,
    WalkForwardHumanReview,
    build_local_lab_ablation_study,
    build_local_lab_artifact_proof_assessment,
    build_local_lab_artifact_release_candidate,
    build_local_lab_artifact_release_scope_summary,
    build_local_lab_recalibration_plan,
    build_local_lab_research_priority_report,
    build_local_lab_scope_matrix,
    build_pending_local_lab_ablation_study,
    build_walk_forward_review_template,
    build_local_lab_scope_slug,
    discover_local_lab_scope_keys,
    load_replay_dtr_records,
    summarize_walk_forward_review,
    LocalLabExecutionTelemetry,
)
from local_replay_runtime.local_lab_execution_telemetry_artifact import (  # noqa: E402
    load_local_lab_execution_telemetry_artifact,
)
from local_replay_runtime.local_lab_promotion_readiness import (  # noqa: E402
    build_local_lab_promotion_readiness_summary,
)
from meta_learning.contracts import TradeLossAttributionReport  # noqa: E402
from meta_minimal.meta_runtime import MetaRuntimeResult  # noqa: E402
from scripts.run_edge_gate_calibration import main as run_edge_gate_calibration_main  # noqa: E402
from scripts.run_local_lab_post_trade_review import main as run_local_lab_post_trade_review_main  # noqa: E402


class LocalLabAnalysisBundleSummary(BaseModel, frozen=True):
    """Future-facing summary of the chained Local IA Lab analysis bundle."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    artifact_hash: str = Field(..., min_length=1)
    dataset_manifest_id: str = Field(..., min_length=1)
    profile_scope: str = Field(..., min_length=1)
    runtime_mode: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    strategy_version: str = Field(..., min_length=1)
    lineage_version: str = Field(..., min_length=1)
    tested_pairs: tuple[str, ...] = ()
    engine_scope: tuple[str, ...] = ()
    selected_pair: str | None = None
    selected_engine_id: str | None = None
    scope_matrix_path: str | None = None
    scope_count: int = Field(default=0, ge=0)
    scope_ready_count: int = Field(default=0, ge=0)
    scope_blocked_count: int = Field(default=0, ge=0)
    release_scope_ready_count: int = Field(default=0, ge=0)
    release_scope_blocked_count: int = Field(default=0, ge=0)
    artifact_ablation_study_path: str | None = None
    review_output_dir: str | None = None
    review_bundle_path: str | None = None
    review_projection_path: str | None = None
    trade_loss_attribution_path: str | None = None
    review_input_summary_path: str | None = None
    walk_forward_review_template_path: str = Field(..., min_length=1)
    walk_forward_review_path: str | None = None
    walk_forward_review_summary_path: str = Field(..., min_length=1)
    artifact_proof_summary_path: str | None = None
    artifact_proof_assessment_path: str | None = None
    artifact_release_candidate_path: str | None = None
    local_lab_recalibration_plan_path: str | None = None
    artifact_import_dry_run_bridge_path: str | None = None
    artifact_source_summary_path: str | None = None
    artifact_release_gate_summary_path: str | None = None
    artifact_promotion_readiness_summary_path: str | None = None
    local_lab_monitoring_projection_path: str | None = None
    local_lab_observability_export_path: str | None = None
    local_lab_observability_text_path: str | None = None
    local_lab_monitoring_backend_payload_path: str | None = None
    local_lab_monitoring_ingestion_summary_path: str | None = None
    local_lab_monitoring_bundle_manifest_path: str | None = None
    local_lab_loss_surrogate_path: str | None = None
    local_lab_calibration_methods_review_path: str | None = None
    local_lab_execution_review_path: str | None = None
    local_lab_execution_runtime_projection_path: str | None = None
    local_lab_multiple_testing_review_path: str | None = None
    local_lab_tail_risk_review_path: str | None = None
    local_lab_calibration_normalized_report_path: str | None = None
    local_lab_research_priority_path: str | None = None
    local_lab_replay_candidate_queue_path: str | None = None
    local_lab_replay_ticket_index_path: str | None = None
    local_lab_replay_dispatch_plan_path: str | None = None
    local_lab_replay_workflow_manifest_path: str | None = None
    artifact_upload_request_path: str | None = None
    artifact_import_request_path: str | None = None
    artifact_import_decision_path: str | None = None
    artifact_upload_decision_path: str | None = None
    edge_output_path: str = Field(..., min_length=1)
    edge_input_summary_path: str = Field(..., min_length=1)
    review_ready: bool = False
    trade_loss_attribution_ready: bool = False
    walk_forward_review_ready: bool = False
    artifact_ablation_ready: bool = False
    artifact_proof_ready: bool = False
    artifact_proof_validation_reasons: tuple[str, ...] = ()
    release_ready_for_shadow: bool = False
    release_status: str = Field(default="local_only", min_length=1)
    release_blocking_reasons: tuple[str, ...] = ()
    release_ready_scope_slugs: tuple[str, ...] = ()
    release_blocked_scope_slugs: tuple[str, ...] = ()
    release_scope_summary_count: int = Field(default=0, ge=0)
    release_scope_summary_paths: tuple[str, ...] = ()
    promotion_readiness_status: str = Field(default="not_evaluated", min_length=1)
    promotion_activation_stage: str = Field(default="replay_only", min_length=1)
    promotion_normalized_state: str = Field(default="replay_only", min_length=1)
    promotion_review_state: str = Field(default="needs_revision", min_length=1)
    monitoring_projection_status: str = Field(default="planned", min_length=1)
    monitoring_projection_detail: str = ""
    local_lab_observability_sample_count: int = Field(default=0, ge=0)
    local_lab_monitoring_backend_status: str = Field(default="planned", min_length=1)
    local_lab_monitoring_ingestion_ready: bool = False
    loss_surrogate_status: str = Field(default="not_evaluated", min_length=1)
    loss_surrogate_ready: bool = False
    loss_surrogate_scope_count: int = Field(default=0, ge=0)
    loss_surrogate_top_scope_slug: str = ""
    loss_surrogate_top_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    calibration_methods_review_status: str = Field(default="not_evaluated", min_length=1)
    calibration_methods_review_ready: bool = False
    calibration_methods_dsr_pass: bool | None = None
    calibration_methods_walk_forward_plan_ready: bool = False
    calibration_methods_stationarity_status: str = Field(default="not_evaluated", min_length=1)
    calibration_methods_stationarity_pass: bool | None = None
    execution_review_status: str = Field(default="not_evaluated", min_length=1)
    execution_review_ready: bool = False
    execution_ready_threshold_count: int = Field(default=0, ge=0)
    execution_partial_threshold_count: int = Field(default=0, ge=0)
    execution_blocked_threshold_count: int = Field(default=0, ge=0)
    execution_runtime_projection_status: str = Field(default="not_evaluated", min_length=1)
    execution_runtime_projection_ready: bool = False
    execution_runtime_projection_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_ready_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_partial_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_blocked_consumer_count: int = Field(default=0, ge=0)
    multiple_testing_review_status: str = Field(default="not_evaluated", min_length=1)
    multiple_testing_review_ready: bool = False
    multiple_testing_correction_required: bool = False
    multiple_testing_correction: str = Field(default="not_evaluated", min_length=1)
    multiple_testing_family_count: int = Field(default=0, ge=0)
    calibration_normalized_report_status: str = Field(default="not_evaluated", min_length=1)
    calibration_normalized_report_ready: bool = False
    calibration_normalized_threshold_count: int = Field(default=0, ge=0)
    tail_risk_review_status: str = Field(default="not_evaluated", min_length=1)
    tail_risk_review_ready: bool = False
    tail_risk_ready_breaker_count: int = Field(default=0, ge=0)
    tail_risk_partial_breaker_count: int = Field(default=0, ge=0)
    tail_risk_blocked_breaker_count: int = Field(default=0, ge=0)
    research_priority_status: str = Field(default="not_evaluated", min_length=1)
    research_priority_scope_count: int = Field(default=0, ge=0)
    research_priority_top_scope_slug: str = ""
    research_priority_top_score: float = Field(default=0.0, ge=0.0, le=1.0)
    replay_candidate_queue_status: str = Field(default="not_evaluated", min_length=1)
    replay_candidate_count: int = Field(default=0, ge=0)
    replay_candidate_ready_count: int = Field(default=0, ge=0)
    replay_candidate_top_scope_slug: str = ""
    replay_ticket_index_status: str = Field(default="not_evaluated", min_length=1)
    replay_ticket_count: int = Field(default=0, ge=0)
    replay_ticket_ready_count: int = Field(default=0, ge=0)
    replay_ticket_top_scope_slug: str = ""
    replay_dispatch_plan_status: str = Field(default="not_evaluated", min_length=1)
    replay_dispatch_ready_count: int = Field(default=0, ge=0)
    replay_dispatch_blocked_count: int = Field(default=0, ge=0)
    replay_dispatch_top_ticket_id: str = ""
    recalibration_candidate_ready: bool = False
    recalibration_blocking_reasons: tuple[str, ...] = ()
    recalibration_action_count: int = Field(default=0, ge=0)
    bridge_ready_for_shadow_dry_run: bool = False
    bridge_status: str = Field(default="not_built", min_length=1)
    bridge_blocking_reasons: tuple[str, ...] = ()
    bridge_release_gate_status: str = Field(default="not_evaluated", min_length=1)
    bridge_release_gate_reasons: tuple[str, ...] = ()
    bridge_semantic_status: str = Field(default="not_evaluated", min_length=1)
    bridge_semantic_reasons: tuple[str, ...] = ()
    bridge_transport_payload_ref_count: int = Field(default=0, ge=0)
    bridge_transport_supplementary_refs: tuple[str, ...] = ()
    edge_calibration_ready: bool = False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run governed Local IA Lab post-trade review and EDGE calibration from one export_dir.",
    )
    parser.add_argument("--export-dir", required=True, help="Path to governed LOCAL_REPLAY export directory")
    parser.add_argument("--correlation-id", required=True, help="Governed review correlation id")
    parser.add_argument("--signed-by", required=True, help="Human attestation identity for EDGE calibration")
    parser.add_argument(
        "--baseline-export-dir",
        help="Optional governed baseline export directory used for ablation proof against the candidate export_dir",
    )
    parser.add_argument("--pair", help="Optional pair selector for the post-trade review")
    parser.add_argument("--engine-id", help="Optional engine selector for the post-trade review")
    parser.add_argument(
        "--strategy-classification",
        help="Optional strategy classification forwarded to the post-trade review",
    )
    parser.add_argument(
        "--source-version",
        default="local_lab_analysis_bundle.v1",
        help="Governed source_version recorded on the review input",
    )
    parser.add_argument("--notes", default="", help="Optional governed notes for the post-trade review")
    parser.add_argument(
        "--output-root",
        default="build/local_lab_analysis_bundle",
        help="Root directory for the chained Local IA Lab outputs",
    )
    parser.add_argument("--state-dir", help="Optional append-only state dir for meta_learning persistence")
    parser.add_argument(
        "--execution-telemetry-path",
        help=(
            "Optional Local IA Lab execution telemetry JSON carrying THR-X01/THR-X02 "
            "observation series. When omitted, the execution review remains explicit "
            "'missing_telemetry'."
        ),
    )
    parser.add_argument(
        "--walk-forward-review-path",
        help=(
            "Optional path to a human-reviewed walk-forward anti-leakage checklist JSON. "
            "When omitted, the bundle emits a pending template instead."
        ),
    )
    parser.add_argument(
        "--all-scopes",
        action="store_true",
        help=(
            "Emit a governed pair x engine scope matrix from the export_dir. "
            "When multiple scopes exist, per-scope review/proof sidecars are written under output-root/scopes/."
        ),
    )
    parser.add_argument("--near-miss-threshold", type=float, default=0.70)
    parser.add_argument("--total-opportunities", type=int, help="Optional override for DTR coverage reconstruction")
    parser.add_argument("--artifact-id", default="edge_gate_thresholds")
    parser.add_argument("--calibration-version", default="v1")
    parser.add_argument("--bootstrap-samples", type=int, default=2_000)
    parser.add_argument("--min-positive-trades", type=int, default=200)
    parser.add_argument("--min-cost-observations", type=int, default=500)
    parser.add_argument("--rng-seed", type=int, default=53)
    parser.add_argument(
        "--bridge-governance-reference-date",
        help="Explicit governance reference date for the future governed upload/import dry-run (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--bridge-training-end",
        help="Explicit training_end date for the future governed upload/import dry-run (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--bridge-artifact-class",
        choices=tuple(member.value for member in ArtifactClass),
        help="Explicit artifact class for the future governed upload/import dry-run.",
    )
    parser.add_argument(
        "--bridge-artifact-scope",
        help="Explicit artifact scope for the future governed upload/import dry-run.",
    )
    parser.add_argument(
        "--bridge-lifecycle-ttl-days",
        type=int,
        help="Explicit TTL max days for the future governed upload/import dry-run.",
    )
    parser.add_argument(
        "--bridge-rule-half-life-days",
        type=int,
        help="Explicit rule half-life days for the future governed upload/import dry-run.",
    )
    parser.add_argument(
        "--bridge-drift-score-threshold",
        type=float,
        help="Explicit drift score threshold for the future governed upload/import dry-run.",
    )
    return parser


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_iso_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def _load_execution_telemetry(
    telemetry_path: Path,
    *,
    correlation_id: str,
) -> LocalLabExecutionTelemetry:
    payload = telemetry_path.read_text(encoding="utf-8")
    try:
        return LocalLabExecutionTelemetry.model_validate_json(payload)
    except ValidationError:
        artifact = load_local_lab_execution_telemetry_artifact(telemetry_path)
        return artifact.bind_to_review(correlation_id=correlation_id)


def _filter_records(
    records: tuple,
    *,
    pair: str | None,
    engine_id: str | None,
) -> tuple:
    filtered = records
    if pair is not None:
        filtered = tuple(record for record in filtered if record.pair == pair)
    if engine_id is not None:
        filtered = tuple(record for record in filtered if record.engine_id == engine_id)
    return filtered


def _scope_correlation_id(base_correlation_id: str, *, pair: str, engine_id: str) -> str:
    return f"{base_correlation_id}:{build_local_lab_scope_slug(pair, engine_id)}"


def _write_cli_output(lines: tuple[str, ...]) -> None:
    sys.stdout.write("\n".join(lines))
    sys.stdout.write("\n")


def _emit_local_lab_analysis_bundle_output(
    *,
    summary_path: Path,
    review_output_dir_value: str | None,
    scope_matrix_path_value: str | None,
    artifact_ablation_study_path_value: str | None,
    artifact_proof_summary_path_value: str | None,
    artifact_proof_assessment_path_value: str | None,
    artifact_release_candidate_path_value: str | None,
    local_lab_recalibration_plan_path_value: str | None,
    artifact_import_dry_run_bridge_path_value: str | None,
    artifact_promotion_readiness_summary_path_value: str | None,
    local_lab_monitoring_projection_path_value: str | None,
    local_lab_observability_export_path_value: str | None,
    local_lab_observability_text_path_value: str | None,
    local_lab_monitoring_backend_payload_path_value: str | None,
    local_lab_monitoring_ingestion_summary_path_value: str | None,
    local_lab_monitoring_bundle_manifest_path_value: str | None,
    local_lab_loss_surrogate_path_value: str | None,
    local_lab_execution_review_path_value: str | None,
    local_lab_execution_runtime_projection_path_value: str | None,
    local_lab_multiple_testing_review_path_value: str | None,
    local_lab_calibration_normalized_report_path_value: str | None,
    local_lab_tail_risk_review_path_value: str | None,
    local_lab_research_priority_path_value: str | None,
    local_lab_replay_candidate_queue_path_value: str | None,
    local_lab_replay_ticket_index_path_value: str | None,
    local_lab_replay_dispatch_plan_path_value: str | None,
    local_lab_replay_workflow_manifest_path_value: str | None,
    edge_output_path: Path,
) -> None:
    output_lines = [f"Local IA Lab analysis summary JSON: {summary_path}"]
    optional_lines = (
        ("Post-trade review dir", review_output_dir_value),
        ("Local IA Lab scope matrix JSON", scope_matrix_path_value),
        ("Artifact ablation study JSON", artifact_ablation_study_path_value),
        ("Artifact proof summary JSON", artifact_proof_summary_path_value),
        ("Artifact proof assessment JSON", artifact_proof_assessment_path_value),
        ("Artifact release candidate JSON", artifact_release_candidate_path_value),
        ("Local IA Lab recalibration plan JSON", local_lab_recalibration_plan_path_value),
        ("Artifact import dry-run bridge JSON", artifact_import_dry_run_bridge_path_value),
        (
            "Artifact promotion readiness summary JSON",
            artifact_promotion_readiness_summary_path_value,
        ),
        ("Local IA Lab monitoring projection JSON", local_lab_monitoring_projection_path_value),
        ("Local IA Lab observability export JSON", local_lab_observability_export_path_value),
        ("Local IA Lab observability text export", local_lab_observability_text_path_value),
        (
            "Local IA Lab monitoring backend payload JSON",
            local_lab_monitoring_backend_payload_path_value,
        ),
        (
            "Local IA Lab monitoring ingestion summary JSON",
            local_lab_monitoring_ingestion_summary_path_value,
        ),
        (
            "Local IA Lab monitoring bundle manifest JSON",
            local_lab_monitoring_bundle_manifest_path_value,
        ),
        ("Local IA Lab loss surrogate JSON", local_lab_loss_surrogate_path_value),
        ("Local IA Lab execution review JSON", local_lab_execution_review_path_value),
        (
            "Local IA Lab execution runtime projection JSON",
            local_lab_execution_runtime_projection_path_value,
        ),
        (
            "Local IA Lab multiple-testing review JSON",
            local_lab_multiple_testing_review_path_value,
        ),
        (
            "Local IA Lab calibration normalized report JSON",
            local_lab_calibration_normalized_report_path_value,
        ),
        ("Local IA Lab tail risk review JSON", local_lab_tail_risk_review_path_value),
        ("Local IA Lab research priority JSON", local_lab_research_priority_path_value),
        ("Local IA Lab replay candidate queue JSON", local_lab_replay_candidate_queue_path_value),
        ("Local IA Lab replay ticket index JSON", local_lab_replay_ticket_index_path_value),
        ("Local IA Lab replay dispatch plan JSON", local_lab_replay_dispatch_plan_path_value),
        (
            "Local IA Lab replay workflow manifest JSON",
            local_lab_replay_workflow_manifest_path_value,
        ),
        ("EDGE calibration artifact", str(edge_output_path)),
    )
    output_lines.extend(
        f"{label}: {value}"
        for label, value in optional_lines
        if value is not None
    )
    _write_cli_output(tuple(output_lines))


def _build_analysis_paths(output_root: Path) -> dict[str, Path]:
    edge_output_path = output_root / "edge_gate.yml"
    return {
        "output_root": output_root,
        "review_output_dir": output_root / "post_trade_review",
        "edge_output_path": edge_output_path,
        "summary_path": output_root / "local_lab_analysis_summary.json",
        "artifact_ablation_study_path": output_root / "artifact_ablation_study.json",
        "walk_forward_review_template_path": output_root / "walk_forward_review.template.json",
        "walk_forward_review_output_path": output_root / "walk_forward_review.json",
        "walk_forward_review_summary_path": output_root / "walk_forward_review.summary.json",
        "artifact_proof_summary_path": output_root / "artifact_proof_summary.json",
        "artifact_proof_assessment_path": output_root / "artifact_proof_assessment.json",
        "artifact_release_candidate_path": output_root / "artifact_release_candidate.json",
        "local_lab_recalibration_plan_path": output_root / "local_lab_recalibration_plan.json",
        "artifact_import_dry_run_bridge_path": output_root / "artifact_import_dry_run_bridge.json",
        "artifact_source_summary_path": output_root / "artifact_source_summary.json",
        "artifact_release_gate_summary_path": output_root / "artifact_release_gate_summary.json",
        "artifact_promotion_readiness_summary_path": (
            output_root / "artifact_promotion_readiness_summary.json"
        ),
        "local_lab_monitoring_projection_path": output_root / "local_lab_monitoring_projection.json",
        "local_lab_observability_export_path": output_root / "local_lab_observability_export.json",
        "local_lab_observability_text_path": output_root / "local_lab_observability.prom",
        "local_lab_monitoring_backend_payload_path": (
            output_root / "local_lab_monitoring_backend_payload.json"
        ),
        "local_lab_monitoring_ingestion_summary_path": (
            output_root / "local_lab_monitoring_ingestion_summary.json"
        ),
        "local_lab_monitoring_bundle_manifest_path": (
            output_root / "local_lab_monitoring_bundle_manifest.json"
        ),
        "local_lab_loss_surrogate_path": output_root / "local_lab_loss_surrogate_report.json",
        "local_lab_calibration_methods_review_path": (
            output_root / "local_lab_calibration_methods_review.json"
        ),
        "local_lab_execution_review_path": output_root / "local_lab_execution_review.json",
        "local_lab_execution_runtime_projection_path": (
            output_root / "local_lab_execution_runtime_projection.json"
        ),
        "local_lab_multiple_testing_review_path": (
            output_root / "local_lab_multiple_testing_review.json"
        ),
        "local_lab_tail_risk_review_path": output_root / "local_lab_tail_risk_review.json",
        "local_lab_calibration_normalized_report_path": (
            output_root / "local_lab_calibration_normalized_report.json"
        ),
        "local_lab_research_priority_path": output_root / "local_lab_research_priority.json",
        "local_lab_replay_candidate_queue_path": (
            output_root / "local_lab_replay_candidate_queue.json"
        ),
        "local_lab_replay_ticket_index_path": output_root / "local_lab_replay_ticket_index.json",
        "local_lab_replay_dispatch_plan_path": output_root / "local_lab_replay_dispatch_plan.json",
        "local_lab_replay_workflow_manifest_path": (
            output_root / "local_lab_replay_workflow_manifest.json"
        ),
        "artifact_upload_request_path": output_root / "artifact_upload_request.dry_run.json",
        "artifact_import_request_path": output_root / "artifact_import_request.dry_run.json",
        "artifact_import_decision_path": output_root / "artifact_import_decision.dry_run.json",
        "artifact_upload_decision_path": output_root / "artifact_upload_decision.dry_run.json",
        "scope_matrix_path": output_root / "local_lab_scope_matrix.json",
        "edge_input_summary_path": edge_output_path.with_suffix(".input_summary.json"),
        "edge_report_path": edge_output_path.with_suffix(".report.json"),
    }


def _initialize_analysis_state(args: argparse.Namespace) -> dict[str, object]:
    discovery = discover_local_replay_export(Path(args.export_dir))
    candidate_records = load_replay_dtr_records(discovery.payload_bundle.replay_dtr_ref)
    baseline_discovery = None
    baseline_records: tuple[object, ...] = ()
    if args.baseline_export_dir:
        baseline_discovery = discover_local_replay_export(Path(args.baseline_export_dir))
        baseline_records = load_replay_dtr_records(baseline_discovery.payload_bundle.replay_dtr_ref)
    execution_telemetry = None
    if args.execution_telemetry_path:
        execution_telemetry = _load_execution_telemetry(
            Path(args.execution_telemetry_path),
            correlation_id=args.correlation_id,
        )
    scope_keys = discover_local_lab_scope_keys(
        candidate_records,
        pair=args.pair,
        engine_id=args.engine_id,
    )
    paths = _build_analysis_paths(Path(args.output_root))
    state = {
        "discovery": discovery,
        "candidate_records": candidate_records,
        "baseline_discovery": baseline_discovery,
        "baseline_records": baseline_records,
        "execution_telemetry": execution_telemetry,
        "scope_keys": scope_keys,
        "multi_scope_mode": args.all_scopes and len(scope_keys) > 1,
        "paths": paths,
    }
    state.update(_initialize_analysis_path_values(paths))
    state.update(_initialize_analysis_status_values(args))
    return state


def _initialize_analysis_path_values(paths: dict[str, Path]) -> dict[str, object]:
    return {
        "review_output_dir_value": None,
        "review_bundle_path_value": None,
        "review_projection_path_value": None,
        "trade_loss_attribution_path_value": None,
        "review_input_summary_path_value": None,
        "artifact_ablation_study_path_value": None,
        "artifact_proof_summary_path_value": None,
        "artifact_proof_assessment_path_value": None,
        "artifact_release_candidate_path_value": None,
        "local_lab_recalibration_plan_path_value": None,
        "artifact_import_dry_run_bridge_path_value": None,
        "artifact_source_summary_path_value": None,
        "artifact_release_gate_summary_path_value": None,
        "artifact_promotion_readiness_summary_path_value": None,
        "local_lab_monitoring_projection_path_value": None,
        "local_lab_observability_export_path_value": None,
        "local_lab_observability_text_path_value": None,
        "local_lab_monitoring_backend_payload_path_value": None,
        "local_lab_monitoring_ingestion_summary_path_value": None,
        "local_lab_monitoring_bundle_manifest_path_value": str(
            paths["local_lab_monitoring_bundle_manifest_path"]
        ),
        "local_lab_loss_surrogate_path_value": None,
        "local_lab_calibration_methods_review_path_value": None,
        "local_lab_execution_review_path_value": None,
        "local_lab_execution_runtime_projection_path_value": None,
        "local_lab_multiple_testing_review_path_value": None,
        "local_lab_tail_risk_review_path_value": None,
        "local_lab_calibration_normalized_report_path_value": None,
        "local_lab_research_priority_path_value": None,
        "local_lab_replay_candidate_queue_path_value": None,
        "local_lab_replay_ticket_index_path_value": None,
        "local_lab_replay_dispatch_plan_path_value": None,
        "local_lab_replay_workflow_manifest_path_value": None,
        "artifact_upload_request_path_value": None,
        "artifact_import_request_path_value": None,
        "artifact_import_decision_path_value": None,
        "artifact_upload_decision_path_value": None,
        "release_scope_summary_paths": (),
        "local_lab_monitoring_bundle_manifest_path_value": str(
            paths["local_lab_monitoring_bundle_manifest_path"]
        ),
    }


def _initialize_analysis_status_values(args: argparse.Namespace) -> dict[str, object]:
    return {
        "walk_forward_review_path": None,
        "review_ready": False,
        "trade_loss_attribution_ready": False,
        "artifact_ablation_ready": False,
        "artifact_proof_ready": False,
        "artifact_proof_validation_reasons": (),
        "artifact_proof_summary_for_bridge": None,
        "recalibration_loss_reports": [],
        "calibration_methods_review_status": "not_evaluated",
        "calibration_methods_review_ready": False,
        "calibration_methods_dsr_pass": None,
        "calibration_methods_walk_forward_plan_ready": False,
        "calibration_methods_stationarity_status": "not_evaluated",
        "calibration_methods_stationarity_pass": None,
        "execution_review_status": "not_evaluated",
        "execution_review_ready": False,
        "execution_ready_threshold_count": 0,
        "execution_partial_threshold_count": 0,
        "execution_blocked_threshold_count": 0,
        "execution_runtime_projection_status": "not_evaluated",
        "execution_runtime_projection_ready": False,
        "execution_runtime_projection_consumer_count": 0,
        "execution_runtime_projection_ready_consumer_count": 0,
        "execution_runtime_projection_partial_consumer_count": 0,
        "execution_runtime_projection_blocked_consumer_count": 0,
        "multiple_testing_review_status": "not_evaluated",
        "multiple_testing_review_ready": False,
        "multiple_testing_correction_required": False,
        "multiple_testing_correction": "not_evaluated",
        "multiple_testing_family_count": 0,
        "calibration_normalized_report_status": "not_evaluated",
        "calibration_normalized_report_ready": False,
        "calibration_normalized_threshold_count": 0,
        "tail_risk_review_status": "not_evaluated",
        "tail_risk_review_ready": False,
        "tail_risk_ready_breaker_count": 0,
        "tail_risk_partial_breaker_count": 0,
        "tail_risk_blocked_breaker_count": 0,
        "summary_selected_pair": args.pair,
        "summary_selected_engine_id": args.engine_id,
        "scope_count": 0,
        "scope_ready_count": 0,
        "scope_blocked_count": 0,
        "release_scope_ready_count": 0,
        "release_scope_blocked_count": 0,
        "scope_matrix_path_value": None,
        "scope_matrix": None,
        "top_level_calibration_methods_review": None,
        "meta_runtime_result": None,
        "trade_loss_attribution": None,
        "artifact_ablation_study": None,
        "review_input_summary": {},
    }


def _prepare_walk_forward_review(
    args: argparse.Namespace,
    state: dict[str, object],
) -> tuple[WalkForwardHumanReview, object]:
    paths = state["paths"]
    discovery = state["discovery"]
    walk_forward_template = build_walk_forward_review_template(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        run_id=discovery.run_manifest.run_id,
    )
    atomic_write_json(
        paths["walk_forward_review_template_path"],
        walk_forward_template.model_dump(mode="json"),
        indent=2,
    )
    if args.walk_forward_review_path:
        walk_forward_review = WalkForwardHumanReview.model_validate_json(
            Path(args.walk_forward_review_path).read_text(encoding="utf-8")
        )
        if walk_forward_review.correlation_id != args.correlation_id:
            raise ValueError("walk-forward review correlation_id must match the analysis bundle correlation_id")
        if Path(walk_forward_review.export_dir).resolve() != discovery.export_dir.resolve():
            raise ValueError("walk-forward review export_dir must match the governed export_dir under analysis")
        if walk_forward_review.run_id != discovery.run_manifest.run_id:
            raise ValueError("walk-forward review run_id must match the governed replay run_id")
        atomic_write_json(
            paths["walk_forward_review_output_path"],
            walk_forward_review.model_dump(mode="json"),
            indent=2,
        )
        state["walk_forward_review_path"] = str(paths["walk_forward_review_output_path"])
    else:
        walk_forward_review = walk_forward_template
    walk_forward_review_summary = summarize_walk_forward_review(walk_forward_review)
    atomic_write_json(
        paths["walk_forward_review_summary_path"],
        walk_forward_review_summary.model_dump(mode="json"),
        indent=2,
    )
    return walk_forward_review, walk_forward_review_summary


def _run_multi_scope_review_phase(
    args: argparse.Namespace,
    state: dict[str, object],
    walk_forward_review_summary: object,
) -> int:
    discovery = state["discovery"]
    baseline_discovery = state["baseline_discovery"]
    candidate_records = state["candidate_records"]
    baseline_records = state["baseline_records"]
    paths = state["paths"]
    scope_rows: list[LocalLabScopeAnalysisRow] = []
    for scope in state["scope_keys"]:
        review_exit_code, scope_row, scope_trade_loss_attribution = _build_multi_scope_analysis_row(
            args=args,
            discovery=discovery,
            baseline_discovery=baseline_discovery,
            candidate_records=candidate_records,
            baseline_records=baseline_records,
            walk_forward_review_summary=walk_forward_review_summary,
            scope=scope,
        )
        if review_exit_code != 0:
            return review_exit_code
        if scope_trade_loss_attribution is not None:
            state["recalibration_loss_reports"].append(scope_trade_loss_attribution)
        if scope_row is not None:
            scope_rows.append(scope_row)
    scope_matrix = build_local_lab_scope_matrix(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        baseline_export_dir=None if baseline_discovery is None else str(baseline_discovery.export_dir),
        scopes=tuple(scope_rows),
    )
    atomic_write_json(paths["scope_matrix_path"], scope_matrix.model_dump(mode="json"), indent=2)
    state["scope_matrix"] = scope_matrix
    state["scope_matrix_path_value"] = str(paths["scope_matrix_path"])
    state["scope_count"] = scope_matrix.scope_count
    state["scope_ready_count"] = scope_matrix.ready_scope_count
    state["scope_blocked_count"] = scope_matrix.blocked_scope_count
    state["review_ready"] = scope_matrix.scope_count > 0
    state["trade_loss_attribution_ready"] = scope_matrix.scope_count > 0
    state["artifact_ablation_ready"] = all(scope.artifact_ablation_ready for scope in scope_matrix.scopes)
    state["artifact_proof_ready"] = scope_matrix.scope_count > 0 and scope_matrix.blocked_scope_count == 0
    state["artifact_proof_validation_reasons"] = tuple(
        dict.fromkeys(
            reason
            for scope in scope_matrix.scopes
            for reason in scope.artifact_proof_validation_reasons
        )
    )
    return 0


def _build_multi_scope_analysis_row(
    *,
    args: argparse.Namespace,
    discovery: object,
    baseline_discovery: object | None,
    candidate_records: tuple[object, ...],
    baseline_records: tuple[object, ...],
    walk_forward_review_summary: object,
    scope: object,
) -> tuple[int, LocalLabScopeAnalysisRow | None, TradeLossAttributionReport | None]:
    scope_root = Path(args.output_root) / "scopes" / scope.scope_slug
    scope_review_output_dir = scope_root / "post_trade_review"
    scope_correlation_id = _scope_correlation_id(
        args.correlation_id,
        pair=scope.pair,
        engine_id=scope.engine_id,
    )
    scope_candidate_records = _filter_records(candidate_records, pair=scope.pair, engine_id=scope.engine_id)
    scope_baseline_records = _filter_records(baseline_records, pair=scope.pair, engine_id=scope.engine_id)
    scope_review_args = [
        "--export-dir", str(discovery.export_dir),
        "--correlation-id", scope_correlation_id,
        "--source-version", args.source_version,
        "--notes", args.notes,
        "--output-dir", str(scope_review_output_dir),
        "--near-miss-threshold", str(args.near_miss_threshold),
        "--pair", scope.pair,
        "--engine-id", scope.engine_id,
        "--total-opportunities", str(args.total_opportunities if args.total_opportunities is not None else len(scope_candidate_records)),
    ]
    if args.strategy_classification:
        scope_review_args.extend(["--strategy-classification", args.strategy_classification])
    if args.state_dir:
        scope_review_args.extend(["--state-dir", str(Path(args.state_dir) / scope.scope_slug)])
    review_exit_code = run_local_lab_post_trade_review_main(scope_review_args)
    if review_exit_code != 0:
        return review_exit_code, None, None
    scope_bundle_path = scope_review_output_dir / "meta_learning_review.bundle.json"
    scope_trade_path = scope_review_output_dir / "trade_loss_attribution.json"
    scope_meta_path = scope_review_output_dir / "meta_runtime_result.json"
    scope_ablation_path = scope_root / "artifact_ablation_study.json"
    scope_proof_summary_path = scope_root / "artifact_proof_summary.json"
    scope_proof_assessment_path = scope_root / "artifact_proof_assessment.json"
    scope_calibration_path = scope_root / "local_lab_calibration_methods_review.json"
    scope_meta_runtime_result = MetaRuntimeResult.model_validate(_load_json(scope_meta_path))
    scope_trade_loss_attribution = TradeLossAttributionReport.model_validate(_load_json(scope_trade_path))
    scope_calibration_methods_review = build_local_lab_calibration_methods_review(
        correlation_id=scope_correlation_id,
        export_dir=str(discovery.export_dir),
        run_id=discovery.run_manifest.run_id,
        records=scope_candidate_records,
    )
    atomic_write_json(scope_calibration_path, scope_calibration_methods_review.model_dump(mode="json"), indent=2)
    scope_ablation_study = _build_scope_ablation_study(
        baseline_discovery=baseline_discovery,
        discovery=discovery,
        candidate_records=candidate_records,
        baseline_records=baseline_records,
        scope=scope,
        scope_correlation_id=scope_correlation_id,
    )
    atomic_write_json(scope_ablation_path, scope_ablation_study.model_dump(mode="json"), indent=2)
    scope_proof_assessment = build_local_lab_artifact_proof_assessment(
        correlation_id=scope_correlation_id,
        export_dir=str(discovery.export_dir),
        run_id=discovery.run_manifest.run_id,
        meta_result=scope_meta_runtime_result,
        trade_loss_attribution=scope_trade_loss_attribution,
        walk_forward_review=walk_forward_review_summary,
        ablation_study=scope_ablation_study,
        calibration_methods_review=scope_calibration_methods_review,
    )
    atomic_write_json(scope_proof_summary_path, scope_proof_assessment.proof_summary.model_dump(mode="json"), indent=2)
    atomic_write_json(scope_proof_assessment_path, scope_proof_assessment.model_dump(mode="json"), indent=2)
    return 0, LocalLabScopeAnalysisRow(
        pair=scope.pair,
        engine_id=scope.engine_id,
        scope_slug=scope.scope_slug,
        review_output_dir=str(scope_review_output_dir),
        review_bundle_path=str(scope_bundle_path),
        trade_loss_attribution_path=str(scope_trade_path),
        artifact_ablation_study_path=str(scope_ablation_path),
        artifact_proof_summary_path=str(scope_proof_summary_path),
        artifact_proof_assessment_path=str(scope_proof_assessment_path),
        calibration_methods_review_path=str(scope_calibration_path),
        candidate_record_count=len(scope_candidate_records),
        baseline_record_count=len(scope_baseline_records),
        executed_records=scope_trade_loss_attribution.executed_records,
        losing_trade_count=scope_trade_loss_attribution.losing_trade_count,
        artifact_ablation_ready=scope_ablation_study.study_ready,
        artifact_proof_ready=scope_proof_assessment.ready_for_vps_import,
        artifact_proof_validation_reasons=scope_proof_assessment.validation_reasons,
        calibration_methods_review_status=scope_calibration_methods_review.review_status.value,
        calibration_methods_review_ready=scope_calibration_methods_review.review_ready,
        caution_flags=tuple(dict.fromkeys(list(scope_ablation_study.caution_flags) + list(scope_proof_assessment.caution_flags))),
        proof_summary=scope_proof_assessment.proof_summary,
    ), scope_trade_loss_attribution


def _build_scope_ablation_study(
    *,
    baseline_discovery: object | None,
    discovery: object,
    candidate_records: tuple[object, ...],
    baseline_records: tuple[object, ...],
    scope: object,
    scope_correlation_id: str,
) -> object:
    if baseline_discovery is not None:
        return build_local_lab_ablation_study(
            correlation_id=scope_correlation_id,
            candidate_export_dir=str(discovery.export_dir),
            baseline_export_dir=str(baseline_discovery.export_dir),
            candidate_run_id=discovery.run_manifest.run_id,
            baseline_run_id=baseline_discovery.run_manifest.run_id,
            candidate_dataset_manifest_id=discovery.run_manifest.dataset_manifest_id,
            baseline_dataset_manifest_id=baseline_discovery.run_manifest.dataset_manifest_id,
            candidate_records=candidate_records,
            baseline_records=baseline_records,
            selected_pair=scope.pair,
            selected_engine_id=scope.engine_id,
        )
    return build_pending_local_lab_ablation_study(
        correlation_id=scope_correlation_id,
        candidate_export_dir=str(discovery.export_dir),
        candidate_run_id=discovery.run_manifest.run_id,
        candidate_dataset_manifest_id=discovery.run_manifest.dataset_manifest_id,
        selected_pair=scope.pair,
        selected_engine_id=scope.engine_id,
    )


def _run_single_scope_review_phase(
    args: argparse.Namespace,
    state: dict[str, object],
) -> int:
    discovery = state["discovery"]
    baseline_discovery = state["baseline_discovery"]
    candidate_records = state["candidate_records"]
    baseline_records = state["baseline_records"]
    paths = state["paths"]
    review_args = [
        "--export-dir", str(discovery.export_dir),
        "--correlation-id", args.correlation_id,
        "--source-version", args.source_version,
        "--notes", args.notes,
        "--output-dir", str(paths["review_output_dir"]),
        "--near-miss-threshold", str(args.near_miss_threshold),
    ]
    if args.pair:
        review_args.extend(["--pair", args.pair])
    if args.engine_id:
        review_args.extend(["--engine-id", args.engine_id])
    if args.strategy_classification:
        review_args.extend(["--strategy-classification", args.strategy_classification])
    if args.state_dir:
        review_args.extend(["--state-dir", args.state_dir])
    if args.total_opportunities is not None:
        review_args.extend(["--total-opportunities", str(args.total_opportunities)])
    review_exit_code = run_local_lab_post_trade_review_main(review_args)
    if review_exit_code != 0:
        return review_exit_code
    review_bundle_path = paths["review_output_dir"] / "meta_learning_review.bundle.json"
    review_projection_path = paths["review_output_dir"] / "meta_learning_projection.json"
    meta_runtime_path = paths["review_output_dir"] / "meta_runtime_result.json"
    trade_loss_path = paths["review_output_dir"] / "trade_loss_attribution.json"
    review_input_summary_path = paths["review_output_dir"] / "governed_input_summary.json"
    state["review_input_summary"] = _load_json(review_input_summary_path)
    state["trade_loss_attribution"] = TradeLossAttributionReport.model_validate(_load_json(trade_loss_path))
    state["meta_runtime_result"] = MetaRuntimeResult.model_validate(_load_json(meta_runtime_path))
    state["recalibration_loss_reports"].append(state["trade_loss_attribution"])
    state["top_level_calibration_methods_review"] = build_local_lab_calibration_methods_review(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        run_id=discovery.run_manifest.run_id,
        records=candidate_records,
    )
    atomic_write_json(
        paths["local_lab_calibration_methods_review_path"],
        state["top_level_calibration_methods_review"].model_dump(mode="json"),
        indent=2,
    )
    if baseline_discovery is not None:
        state["artifact_ablation_study"] = build_local_lab_ablation_study(
            correlation_id=args.correlation_id,
            candidate_export_dir=str(discovery.export_dir),
            baseline_export_dir=str(baseline_discovery.export_dir),
            candidate_run_id=discovery.run_manifest.run_id,
            baseline_run_id=baseline_discovery.run_manifest.run_id,
            candidate_dataset_manifest_id=discovery.run_manifest.dataset_manifest_id,
            baseline_dataset_manifest_id=baseline_discovery.run_manifest.dataset_manifest_id,
            candidate_records=candidate_records,
            baseline_records=baseline_records,
            selected_pair=state["review_input_summary"].get("selected_pair"),
            selected_engine_id=state["review_input_summary"].get("selected_engine_id"),
        )
    else:
        state["artifact_ablation_study"] = build_pending_local_lab_ablation_study(
            correlation_id=args.correlation_id,
            candidate_export_dir=str(discovery.export_dir),
            candidate_run_id=discovery.run_manifest.run_id,
            candidate_dataset_manifest_id=discovery.run_manifest.dataset_manifest_id,
            selected_pair=state["review_input_summary"].get("selected_pair"),
            selected_engine_id=state["review_input_summary"].get("selected_engine_id"),
        )
    atomic_write_json(paths["artifact_ablation_study_path"], state["artifact_ablation_study"].model_dump(mode="json"), indent=2)
    state["review_output_dir_value"] = str(paths["review_output_dir"])
    state["review_bundle_path_value"] = str(review_bundle_path)
    state["review_projection_path_value"] = str(review_projection_path)
    state["trade_loss_attribution_path_value"] = str(trade_loss_path)
    state["review_input_summary_path_value"] = str(review_input_summary_path)
    state["artifact_ablation_study_path_value"] = str(paths["artifact_ablation_study_path"])
    state["local_lab_calibration_methods_review_path_value"] = str(paths["local_lab_calibration_methods_review_path"])
    state["review_ready"] = True
    state["trade_loss_attribution_ready"] = True
    state["artifact_ablation_ready"] = state["artifact_ablation_study"].study_ready
    state["summary_selected_pair"] = state["review_input_summary"].get("selected_pair")
    state["summary_selected_engine_id"] = state["review_input_summary"].get("selected_engine_id")
    return 0


def _run_review_phase(
    args: argparse.Namespace,
    state: dict[str, object],
    walk_forward_review_summary: object,
) -> int:
    if state["multi_scope_mode"]:
        return _run_multi_scope_review_phase(args, state, walk_forward_review_summary)
    return _run_single_scope_review_phase(args, state)


def _update_calibration_review_state(
    state: dict[str, object],
    calibration_review: object,
) -> None:
    state["calibration_methods_review_status"] = calibration_review.review_status.value
    state["calibration_methods_review_ready"] = calibration_review.review_ready
    state["calibration_methods_dsr_pass"] = calibration_review.dsr_pass
    state["calibration_methods_walk_forward_plan_ready"] = (
        calibration_review.walk_forward_plan_ready
    )
    state["calibration_methods_stationarity_status"] = calibration_review.stationarity_status
    state["calibration_methods_stationarity_pass"] = calibration_review.stationarity_pass


def _run_secondary_review_phase(
    args: argparse.Namespace,
    state: dict[str, object],
) -> None:
    discovery = state["discovery"]
    candidate_records = state["candidate_records"]
    paths = state["paths"]
    local_lab_loss_surrogate = build_local_lab_loss_surrogate_report(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        records=candidate_records,
        scope_matrix=state["scope_matrix"],
        selected_pair=state["summary_selected_pair"],
        selected_engine_id=state["summary_selected_engine_id"],
    )
    atomic_write_json(
        paths["local_lab_loss_surrogate_path"],
        local_lab_loss_surrogate.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_loss_surrogate"] = local_lab_loss_surrogate
    state["local_lab_loss_surrogate_path_value"] = str(paths["local_lab_loss_surrogate_path"])
    if state["multi_scope_mode"]:
        aggregate_review = build_local_lab_calibration_methods_review(
            correlation_id=args.correlation_id,
            export_dir=str(discovery.export_dir),
            run_id=discovery.run_manifest.run_id,
            records=candidate_records,
        )
        atomic_write_json(
            paths["local_lab_calibration_methods_review_path"],
            aggregate_review.model_dump(mode="json"),
            indent=2,
        )
        state["top_level_calibration_methods_review"] = aggregate_review
        state["local_lab_calibration_methods_review_path_value"] = str(
            paths["local_lab_calibration_methods_review_path"]
        )
        _update_calibration_review_state(state, aggregate_review)
    elif state["top_level_calibration_methods_review"] is not None:
        _update_calibration_review_state(state, state["top_level_calibration_methods_review"])
    local_lab_execution_review = build_local_lab_execution_review(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        run_id=discovery.run_manifest.run_id,
        telemetry=state["execution_telemetry"],
    )
    atomic_write_json(
        paths["local_lab_execution_review_path"],
        local_lab_execution_review.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_execution_review"] = local_lab_execution_review
    state["local_lab_execution_review_path_value"] = str(paths["local_lab_execution_review_path"])
    state["execution_review_status"] = local_lab_execution_review.review_status.value
    state["execution_review_ready"] = local_lab_execution_review.review_ready
    state["execution_ready_threshold_count"] = local_lab_execution_review.ready_threshold_count
    state["execution_partial_threshold_count"] = local_lab_execution_review.partial_threshold_count
    state["execution_blocked_threshold_count"] = local_lab_execution_review.blocked_threshold_count
    local_lab_execution_runtime_projection = build_local_lab_execution_runtime_projection(
        local_lab_execution_review
    )
    atomic_write_json(
        paths["local_lab_execution_runtime_projection_path"],
        local_lab_execution_runtime_projection.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_execution_runtime_projection"] = local_lab_execution_runtime_projection
    state["local_lab_execution_runtime_projection_path_value"] = str(
        paths["local_lab_execution_runtime_projection_path"]
    )
    state["execution_runtime_projection_status"] = (
        local_lab_execution_runtime_projection.projection_status.value
    )
    state["execution_runtime_projection_ready"] = local_lab_execution_runtime_projection.projection_ready
    state["execution_runtime_projection_consumer_count"] = (
        local_lab_execution_runtime_projection.consumer_count
    )
    state["execution_runtime_projection_ready_consumer_count"] = (
        local_lab_execution_runtime_projection.ready_consumer_count
    )
    state["execution_runtime_projection_partial_consumer_count"] = (
        local_lab_execution_runtime_projection.partial_consumer_count
    )
    state["execution_runtime_projection_blocked_consumer_count"] = (
        local_lab_execution_runtime_projection.blocked_consumer_count
    )
    local_lab_tail_risk_review = build_local_lab_tail_risk_review(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        run_id=discovery.run_manifest.run_id,
        records=candidate_records,
    )
    atomic_write_json(
        paths["local_lab_tail_risk_review_path"],
        local_lab_tail_risk_review.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_tail_risk_review"] = local_lab_tail_risk_review
    state["local_lab_tail_risk_review_path_value"] = str(paths["local_lab_tail_risk_review_path"])
    state["tail_risk_review_status"] = local_lab_tail_risk_review.review_status.value
    state["tail_risk_review_ready"] = local_lab_tail_risk_review.review_ready
    state["tail_risk_ready_breaker_count"] = local_lab_tail_risk_review.ready_breaker_count
    state["tail_risk_partial_breaker_count"] = local_lab_tail_risk_review.partial_breaker_count
    state["tail_risk_blocked_breaker_count"] = local_lab_tail_risk_review.blocked_breaker_count


def _run_edge_calibration_phase(
    args: argparse.Namespace,
    state: dict[str, object],
) -> int:
    discovery = state["discovery"]
    paths = state["paths"]
    local_lab_recalibration_plan = build_local_lab_recalibration_plan(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        loss_reports=tuple(state["recalibration_loss_reports"]),
        scope_matrix=state["scope_matrix"],
        loss_surrogate_report=state["local_lab_loss_surrogate"],
    )
    atomic_write_json(
        paths["local_lab_recalibration_plan_path"],
        local_lab_recalibration_plan.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_recalibration_plan"] = local_lab_recalibration_plan
    state["local_lab_recalibration_plan_path_value"] = str(paths["local_lab_recalibration_plan_path"])
    edge_args = [
        "--export-dir", str(discovery.export_dir),
        "--output-path", str(paths["edge_output_path"]),
        "--signed-by", args.signed_by,
        "--artifact-id", args.artifact_id,
        "--calibration-version", args.calibration_version,
        "--bootstrap-samples", str(args.bootstrap_samples),
        "--min-positive-trades", str(args.min_positive_trades),
        "--min-cost-observations", str(args.min_cost_observations),
        "--rng-seed", str(args.rng_seed),
        "--recalibration-plan-path", str(paths["local_lab_recalibration_plan_path"]),
    ]
    edge_exit_code = run_edge_gate_calibration_main(edge_args)
    if edge_exit_code != 0:
        return edge_exit_code
    edge_input_summary = _load_json(paths["edge_input_summary_path"])
    edge_report = EdgeGateCalibrationReport.model_validate_json(
        paths["edge_report_path"].read_text(encoding="utf-8")
    )
    edge_config = EdgeGateCalibrationConfig(
        artifact_id=args.artifact_id,
        calibration_version=args.calibration_version,
        bootstrap_samples=args.bootstrap_samples,
        min_positive_trades=args.min_positive_trades,
        min_cost_observations=args.min_cost_observations,
        rng_seed=args.rng_seed,
    )
    state["edge_input_summary"] = edge_input_summary
    state["edge_report"] = edge_report
    state["edge_config"] = edge_config
    local_lab_multiple_testing_review = build_local_lab_multiple_testing_review(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        run_id=discovery.run_manifest.run_id,
        edge_report=edge_report,
        tail_risk_review=state["local_lab_tail_risk_review"],
    )
    atomic_write_json(
        paths["local_lab_multiple_testing_review_path"],
        local_lab_multiple_testing_review.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_multiple_testing_review"] = local_lab_multiple_testing_review
    state["local_lab_multiple_testing_review_path_value"] = str(
        paths["local_lab_multiple_testing_review_path"]
    )
    state["multiple_testing_review_status"] = local_lab_multiple_testing_review.review_status.value
    state["multiple_testing_review_ready"] = local_lab_multiple_testing_review.review_ready
    state["multiple_testing_correction_required"] = local_lab_multiple_testing_review.correction_required
    state["multiple_testing_correction"] = local_lab_multiple_testing_review.multi_test_correction
    state["multiple_testing_family_count"] = local_lab_multiple_testing_review.family_count
    return 0


def _run_artifact_proof_phase(
    args: argparse.Namespace,
    state: dict[str, object],
    walk_forward_review_summary: object,
) -> None:
    discovery = state["discovery"]
    paths = state["paths"]
    if (
        state["meta_runtime_result"] is not None
        and state["trade_loss_attribution"] is not None
        and state["artifact_ablation_study"] is not None
        and state["top_level_calibration_methods_review"] is not None
    ):
        artifact_proof_assessment = build_local_lab_artifact_proof_assessment(
            correlation_id=args.correlation_id,
            export_dir=str(discovery.export_dir),
            run_id=discovery.run_manifest.run_id,
            meta_result=state["meta_runtime_result"],
            trade_loss_attribution=state["trade_loss_attribution"],
            walk_forward_review=walk_forward_review_summary,
            ablation_study=state["artifact_ablation_study"],
            calibration_methods_review=state["top_level_calibration_methods_review"],
            execution_runtime_projection=state["local_lab_execution_runtime_projection"],
            multiple_testing_review=state["local_lab_multiple_testing_review"],
        )
        atomic_write_json(
            paths["artifact_proof_summary_path"],
            artifact_proof_assessment.proof_summary.model_dump(mode="json"),
            indent=2,
        )
        atomic_write_json(
            paths["artifact_proof_assessment_path"],
            artifact_proof_assessment.model_dump(mode="json"),
            indent=2,
        )
        state["artifact_proof_summary_path_value"] = str(paths["artifact_proof_summary_path"])
        state["artifact_proof_assessment_path_value"] = str(paths["artifact_proof_assessment_path"])
        state["artifact_ablation_ready"] = state["artifact_ablation_study"].study_ready
        state["artifact_proof_ready"] = artifact_proof_assessment.ready_for_vps_import
        state["artifact_proof_validation_reasons"] = artifact_proof_assessment.validation_reasons
        state["artifact_proof_summary_for_bridge"] = artifact_proof_assessment.proof_summary
    if state["top_level_calibration_methods_review"] is None:
        return
    normalized_report = build_local_lab_calibration_normalized_report(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        run_id=discovery.run_manifest.run_id,
        records=state["candidate_records"],
        edge_report=state["edge_report"],
        edge_config=state["edge_config"],
        calibration_methods_review=state["top_level_calibration_methods_review"],
        multiple_testing_review=state["local_lab_multiple_testing_review"],
        tail_risk_review=state["local_lab_tail_risk_review"],
    )
    atomic_write_json(
        paths["local_lab_calibration_normalized_report_path"],
        normalized_report.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_calibration_normalized_report_path_value"] = str(
        paths["local_lab_calibration_normalized_report_path"]
    )
    state["calibration_normalized_report_status"] = normalized_report.review_status
    state["calibration_normalized_report_ready"] = normalized_report.review_ready
    state["calibration_normalized_threshold_count"] = normalized_report.threshold_count


def _run_edge_and_proof_phase(
    args: argparse.Namespace,
    state: dict[str, object],
    walk_forward_review_summary: object,
) -> int:
    edge_exit_code = _run_edge_calibration_phase(args, state)
    if edge_exit_code != 0:
        return edge_exit_code
    _run_artifact_proof_phase(args, state, walk_forward_review_summary)
    return 0


def _write_upload_bridge_support_files(
    *,
    bridge_candidate: object,
    upload_build_context: object | None,
    paths: dict[str, Path],
    state: dict[str, object],
) -> object:
    if upload_build_context is None:
        return bridge_candidate
    atomic_write_json(
        paths["artifact_upload_request_path"],
        upload_build_context.upload_request.model_dump(mode="json"),
        indent=2,
    )
    atomic_write_json(
        paths["artifact_import_request_path"],
        upload_build_context.import_request.model_dump(mode="json"),
        indent=2,
    )
    if upload_build_context.import_decision is not None:
        atomic_write_json(
            paths["artifact_import_decision_path"],
            upload_build_context.import_decision.model_dump(mode="json"),
            indent=2,
        )
        state["artifact_import_decision_path_value"] = str(paths["artifact_import_decision_path"])
    if upload_build_context.upload_decision is not None:
        atomic_write_json(
            paths["artifact_upload_decision_path"],
            upload_build_context.upload_decision.model_dump(mode="json"),
            indent=2,
        )
        state["artifact_upload_decision_path_value"] = str(paths["artifact_upload_decision_path"])
    state["artifact_upload_request_path_value"] = str(paths["artifact_upload_request_path"])
    state["artifact_import_request_path_value"] = str(paths["artifact_import_request_path"])
    return bridge_candidate.model_copy(
        update={
            "upload_request_path": state["artifact_upload_request_path_value"],
            "import_request_path": state["artifact_import_request_path_value"],
            "import_decision_path": state["artifact_import_decision_path_value"],
            "upload_decision_path": state["artifact_upload_decision_path_value"],
        }
    )


def _update_release_scope_summaries(state: dict[str, object]) -> None:
    artifact_release_candidate = state["artifact_release_candidate"]
    if not artifact_release_candidate.release_scopes:
        return
    output_root = state["paths"]["output_root"]
    updated_release_scopes = []
    release_scope_summary_paths_list: list[str] = []
    for scope in artifact_release_candidate.release_scopes:
        if scope.artifact_proof_summary_path:
            scope_root = Path(scope.artifact_proof_summary_path).parent
        elif scope.review_bundle_path:
            scope_root = Path(scope.review_bundle_path).parent.parent
        else:
            scope_root = output_root / "scopes" / scope.scope_slug
        scope_root.mkdir(parents=True, exist_ok=True)
        scope_summary_path = scope_root / "artifact_release_scope_summary.json"
        scope_summary = build_local_lab_artifact_release_scope_summary(
            release_candidate=artifact_release_candidate,
            scope=scope,
            shared_release_gate_summary_path=state["artifact_release_gate_summary_path_value"],
            shared_source_artifact_summary_path=state["artifact_source_summary_path_value"],
            shared_artifact_import_dry_run_bridge_path=state["artifact_import_dry_run_bridge_path_value"],
        )
        atomic_write_json(scope_summary_path, scope_summary.model_dump(mode="json"), indent=2)
        release_scope_summary_paths_list.append(str(scope_summary_path))
        updated_release_scopes.append(
            scope.model_copy(update={"release_scope_summary_path": str(scope_summary_path)})
        )
    state["artifact_release_candidate"] = artifact_release_candidate.model_copy(
        update={"release_scopes": tuple(updated_release_scopes)}
    )
    atomic_write_json(
        state["paths"]["artifact_release_candidate_path"],
        state["artifact_release_candidate"].model_dump(mode="json"),
        indent=2,
    )
    state["release_scope_summary_paths"] = tuple(release_scope_summary_paths_list)
    if state["scope_matrix"] is None:
        return
    release_scope_by_slug = {
        scope.scope_slug: scope for scope in state["artifact_release_candidate"].release_scopes
    }
    updated_scope_rows = []
    for row in state["scope_matrix"].scopes:
        release_scope = release_scope_by_slug.get(row.scope_slug)
        if release_scope is None:
            updated_scope_rows.append(row)
            continue
        updated_scope_rows.append(
            row.model_copy(
                update={
                    "release_ready": release_scope.release_ready,
                    "release_blocking_reasons": release_scope.blocking_reasons,
                    "release_scope_summary_path": release_scope.release_scope_summary_path,
                }
            )
        )
    state["scope_matrix"] = build_local_lab_scope_matrix(
        correlation_id=state["scope_matrix"].correlation_id,
        export_dir=state["scope_matrix"].export_dir,
        baseline_export_dir=state["scope_matrix"].baseline_export_dir,
        scopes=tuple(updated_scope_rows),
    )
    atomic_write_json(
        state["paths"]["scope_matrix_path"],
        state["scope_matrix"].model_dump(mode="json"),
        indent=2,
    )
    state["scope_matrix_path_value"] = str(state["paths"]["scope_matrix_path"])
    state["scope_count"] = state["scope_matrix"].scope_count
    state["scope_ready_count"] = state["scope_matrix"].ready_scope_count
    state["scope_blocked_count"] = state["scope_matrix"].blocked_scope_count
    state["release_scope_ready_count"] = state["scope_matrix"].release_ready_scope_count
    state["release_scope_blocked_count"] = state["scope_matrix"].release_blocked_scope_count


def _run_release_candidate_phase(
    args: argparse.Namespace,
    state: dict[str, object],
) -> None:
    discovery = state["discovery"]
    baseline_discovery = state["baseline_discovery"]
    paths = state["paths"]
    artifact_release_candidate = build_local_lab_artifact_release_candidate(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        baseline_export_dir=None if baseline_discovery is None else str(baseline_discovery.export_dir),
        run_id=discovery.run_manifest.run_id,
        artifact_id=args.artifact_id,
        artifact_path=str(paths["edge_output_path"]),
        artifact_input_summary_path=str(paths["edge_input_summary_path"]),
        walk_forward_review_summary_path=str(paths["walk_forward_review_summary_path"]),
        local_lab_recalibration_plan_path=state["local_lab_recalibration_plan_path_value"],
        edge_calibration_ready=state["edge_input_summary"].get("record_count", 0) > 0,
        recalibration_candidate_ready=state["local_lab_recalibration_plan"].calibration_candidate_ready,
        recalibration_blocking_reasons=state["local_lab_recalibration_plan"].blocking_reasons,
        artifact_proof_ready=state["artifact_proof_ready"],
        artifact_proof_validation_reasons=state["artifact_proof_validation_reasons"],
        local_lab_calibration_methods_review_path=state["local_lab_calibration_methods_review_path_value"],
        calibration_methods_review_status=state["calibration_methods_review_status"],
        calibration_methods_review_ready=state["calibration_methods_review_ready"],
        calibration_methods_dsr_pass=state["calibration_methods_dsr_pass"],
        calibration_methods_walk_forward_plan_ready=state["calibration_methods_walk_forward_plan_ready"],
        local_lab_execution_runtime_projection_path=state["local_lab_execution_runtime_projection_path_value"],
        execution_runtime_projection_status=state["execution_runtime_projection_status"],
        execution_runtime_projection_ready=state["execution_runtime_projection_ready"],
        execution_runtime_projection_consumer_count=state["execution_runtime_projection_consumer_count"],
        execution_runtime_projection_ready_consumer_count=state["execution_runtime_projection_ready_consumer_count"],
        execution_runtime_projection_partial_consumer_count=state["execution_runtime_projection_partial_consumer_count"],
        execution_runtime_projection_blocked_consumer_count=state["execution_runtime_projection_blocked_consumer_count"],
        execution_runtime_projection_blocking_reasons=state["local_lab_execution_runtime_projection"].blocking_reasons,
        artifact_proof_summary_path=state["artifact_proof_summary_path_value"],
        artifact_proof_assessment_path=state["artifact_proof_assessment_path_value"],
        scope_matrix_path=state["scope_matrix_path_value"],
        scope_matrix=state["scope_matrix"],
    )
    atomic_write_json(
        paths["artifact_release_candidate_path"],
        artifact_release_candidate.model_dump(mode="json"),
        indent=2,
    )
    state["artifact_release_candidate"] = artifact_release_candidate
    state["artifact_release_candidate_path_value"] = str(paths["artifact_release_candidate_path"])
    source_artifact_summary = build_local_lab_source_artifact_summary(str(paths["edge_output_path"]))
    atomic_write_json(
        paths["artifact_source_summary_path"],
        source_artifact_summary.model_dump(mode="json"),
        indent=2,
    )
    state["artifact_source_summary_path_value"] = str(paths["artifact_source_summary_path"])
    release_gate_summary = build_local_lab_release_gate_summary(artifact_release_candidate)
    atomic_write_json(
        paths["artifact_release_gate_summary_path"],
        release_gate_summary.model_dump(mode="json"),
        indent=2,
    )
    state["artifact_release_gate_summary_path_value"] = str(paths["artifact_release_gate_summary_path"])
    bridge_candidate, upload_build_context = build_local_lab_artifact_upload_dry_run_bridge(
        release_candidate=artifact_release_candidate,
        proof_summary=state["artifact_proof_summary_for_bridge"],
        governance_reference_date=_parse_iso_date(args.bridge_governance_reference_date),
        training_end=_parse_iso_date(args.bridge_training_end),
        artifact_class=None if args.bridge_artifact_class is None else ArtifactClass(args.bridge_artifact_class),
        artifact_scope=args.bridge_artifact_scope,
        lifecycle_ttl_days=args.bridge_lifecycle_ttl_days,
        rule_half_life_days=args.bridge_rule_half_life_days,
        drift_score_threshold=args.bridge_drift_score_threshold,
        uploaded_by=args.signed_by,
        source_artifact_summary_ref=state["artifact_source_summary_path_value"],
        release_gate_summary_ref=state["artifact_release_gate_summary_path_value"],
    )
    state["artifact_upload_bridge_candidate"] = _write_upload_bridge_support_files(
        bridge_candidate=bridge_candidate,
        upload_build_context=upload_build_context,
        paths=paths,
        state=state,
    )
    atomic_write_json(
        paths["artifact_import_dry_run_bridge_path"],
        state["artifact_upload_bridge_candidate"].model_dump(mode="json"),
        indent=2,
    )
    state["artifact_import_dry_run_bridge_path_value"] = str(paths["artifact_import_dry_run_bridge_path"])
    _update_release_scope_summaries(state)


def _run_promotion_and_replay_phase(
    args: argparse.Namespace,
    state: dict[str, object],
) -> None:
    discovery = state["discovery"]
    paths = state["paths"]
    promotion_readiness_summary = build_local_lab_promotion_readiness_summary(
        release_candidate=state["artifact_release_candidate"],
        dry_run_bridge=state["artifact_upload_bridge_candidate"],
    )
    atomic_write_json(
        paths["artifact_promotion_readiness_summary_path"],
        promotion_readiness_summary.model_dump(mode="json"),
        indent=2,
    )
    state["promotion_readiness_summary"] = promotion_readiness_summary
    state["artifact_promotion_readiness_summary_path_value"] = str(
        paths["artifact_promotion_readiness_summary_path"]
    )
    local_lab_research_priority = build_local_lab_research_priority_report(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        loss_reports=tuple(state["recalibration_loss_reports"]),
        scope_matrix=state["scope_matrix"],
        selected_pair=state["summary_selected_pair"],
        selected_engine_id=state["summary_selected_engine_id"],
        artifact_proof_ready=state["artifact_proof_ready"],
        artifact_proof_validation_reasons=state["artifact_proof_validation_reasons"],
        release_ready_for_shadow=state["artifact_release_candidate"].ready_for_shadow_import,
        release_blocking_reasons=state["artifact_release_candidate"].blocking_reasons,
        loss_surrogate_report=state["local_lab_loss_surrogate"],
    )
    atomic_write_json(
        paths["local_lab_research_priority_path"],
        local_lab_research_priority.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_research_priority"] = local_lab_research_priority
    state["local_lab_research_priority_path_value"] = str(paths["local_lab_research_priority_path"])
    local_lab_replay_candidate_queue = build_local_lab_replay_candidate_queue(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        research_priority_report=local_lab_research_priority,
        recalibration_plan=state["local_lab_recalibration_plan"],
    )
    atomic_write_json(
        paths["local_lab_replay_candidate_queue_path"],
        local_lab_replay_candidate_queue.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_replay_candidate_queue"] = local_lab_replay_candidate_queue
    state["local_lab_replay_candidate_queue_path_value"] = str(paths["local_lab_replay_candidate_queue_path"])
    local_lab_replay_ticket_index = build_local_lab_replay_ticket_index(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        profile=discovery.run_manifest.profile_scope,
        lineage_version=discovery.run_manifest.lineage_version,
        replay_candidate_queue=local_lab_replay_candidate_queue,
        strategy_classification=args.strategy_classification,
    )
    atomic_write_json(
        paths["local_lab_replay_ticket_index_path"],
        local_lab_replay_ticket_index.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_replay_ticket_index"] = local_lab_replay_ticket_index
    state["local_lab_replay_ticket_index_path_value"] = str(paths["local_lab_replay_ticket_index_path"])
    local_lab_replay_dispatch_plan = build_local_lab_replay_dispatch_plan(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        replay_ticket_index=local_lab_replay_ticket_index,
    )
    atomic_write_json(
        paths["local_lab_replay_dispatch_plan_path"],
        local_lab_replay_dispatch_plan.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_replay_dispatch_plan"] = local_lab_replay_dispatch_plan
    state["local_lab_replay_dispatch_plan_path_value"] = str(paths["local_lab_replay_dispatch_plan_path"])
    workflow_manifest = build_local_lab_replay_workflow_manifest(
        replay_candidate_queue=local_lab_replay_candidate_queue,
        replay_candidate_queue_path=state["local_lab_replay_candidate_queue_path_value"],
        replay_ticket_index=local_lab_replay_ticket_index,
        replay_ticket_index_path=state["local_lab_replay_ticket_index_path_value"],
        replay_dispatch_plan=local_lab_replay_dispatch_plan,
        replay_dispatch_plan_path=state["local_lab_replay_dispatch_plan_path_value"],
    )
    atomic_write_json(
        paths["local_lab_replay_workflow_manifest_path"],
        workflow_manifest.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_replay_workflow_manifest"] = workflow_manifest
    state["local_lab_replay_workflow_manifest_path_value"] = str(
        paths["local_lab_replay_workflow_manifest_path"]
    )


def _build_monitoring_projection_artifact(
    args: argparse.Namespace,
    state: dict[str, object],
    walk_forward_review_summary: object,
) -> None:
    discovery = state["discovery"]
    paths = state["paths"]
    projection = build_local_lab_monitoring_projection(
        correlation_id=args.correlation_id,
        run_id=discovery.run_manifest.run_id,
        export_dir=str(discovery.export_dir),
        dataset_manifest_id=discovery.run_manifest.dataset_manifest_id,
        artifact_id=args.artifact_id,
        selected_pair=state["summary_selected_pair"],
        selected_engine_id=state["summary_selected_engine_id"],
        review_ready=state["review_ready"],
        trade_loss_attribution_ready=state["trade_loss_attribution_ready"],
        walk_forward_review_ready=walk_forward_review_summary.walk_forward_pass,
        artifact_ablation_ready=state["artifact_ablation_ready"],
        artifact_proof_ready=state["artifact_proof_ready"],
        edge_calibration_ready=state["edge_input_summary"].get("record_count", 0) > 0,
        scope_count=state["scope_count"],
        scope_ready_count=state["scope_ready_count"],
        scope_blocked_count=state["scope_blocked_count"],
        release_scope_ready_count=state["release_scope_ready_count"],
        release_scope_blocked_count=state["release_scope_blocked_count"],
        release_ready_for_shadow=state["artifact_release_candidate"].ready_for_shadow_import,
        release_status=state["artifact_release_candidate"].release_status,
        release_blocking_reasons=state["artifact_release_candidate"].blocking_reasons,
        artifact_proof_validation_reasons=state["artifact_release_candidate"].artifact_proof_validation_reasons,
        recalibration_blocking_reasons=state["artifact_release_candidate"].recalibration_blocking_reasons,
        bridge_status=state["artifact_upload_bridge_candidate"].bridge_status,
        ready_for_shadow_import_dry_run=state["artifact_upload_bridge_candidate"].ready_for_shadow_import_dry_run,
        bridge_blocking_reasons=state["artifact_upload_bridge_candidate"].blocking_reasons,
        release_gate_status=state["artifact_upload_bridge_candidate"].release_gate_status,
        release_gate_reasons=state["artifact_upload_bridge_candidate"].release_gate_reasons,
        semantic_status=state["artifact_upload_bridge_candidate"].semantic_status,
        promotion_readiness_status=state["promotion_readiness_summary"].readiness_status,
        activation_stage=state["promotion_readiness_summary"].activation_stage.value,
        normalized_promotion_state=state["promotion_readiness_summary"].normalized_promotion_state.value,
        review_state=state["promotion_readiness_summary"].review_state.value,
        loss_surrogate_status=state["local_lab_loss_surrogate"].status,
        loss_surrogate_ready=state["local_lab_loss_surrogate"].ready,
        loss_surrogate_scope_count=state["local_lab_loss_surrogate"].scope_count,
        loss_surrogate_top_scope_slug=state["local_lab_loss_surrogate"].highest_risk_scope_slug,
        loss_surrogate_top_probability=state["local_lab_loss_surrogate"].highest_risk_probability,
        calibration_methods_review_status=state["calibration_methods_review_status"],
        calibration_methods_review_ready=state["calibration_methods_review_ready"],
        calibration_methods_dsr_pass=state["calibration_methods_dsr_pass"],
        calibration_methods_walk_forward_plan_ready=state["calibration_methods_walk_forward_plan_ready"],
        calibration_methods_stationarity_status=state["calibration_methods_stationarity_status"],
        calibration_methods_stationarity_pass=state["calibration_methods_stationarity_pass"],
        execution_review_status=state["execution_review_status"],
        execution_review_ready=state["execution_review_ready"],
        execution_ready_threshold_count=state["execution_ready_threshold_count"],
        execution_partial_threshold_count=state["execution_partial_threshold_count"],
        execution_blocked_threshold_count=state["execution_blocked_threshold_count"],
        multiple_testing_review_status=state["multiple_testing_review_status"],
        multiple_testing_review_ready=state["multiple_testing_review_ready"],
        multiple_testing_correction_required=state["multiple_testing_correction_required"],
        multiple_testing_correction=state["multiple_testing_correction"],
        multiple_testing_family_count=state["multiple_testing_family_count"],
        tail_risk_review_status=state["tail_risk_review_status"],
        tail_risk_review_ready=state["tail_risk_review_ready"],
        tail_risk_ready_breaker_count=state["tail_risk_ready_breaker_count"],
        tail_risk_partial_breaker_count=state["tail_risk_partial_breaker_count"],
        tail_risk_blocked_breaker_count=state["tail_risk_blocked_breaker_count"],
        research_priority_status=state["local_lab_research_priority"].status,
        research_priority_scope_count=state["local_lab_research_priority"].priority_scope_count,
        research_priority_top_scope_slug=state["local_lab_research_priority"].highest_priority_scope_slug,
        research_priority_top_score=state["local_lab_research_priority"].highest_priority_score,
        replay_candidate_queue_status=state["local_lab_replay_candidate_queue"].status,
        replay_candidate_count=state["local_lab_replay_candidate_queue"].candidate_count,
        replay_candidate_ready_count=state["local_lab_replay_candidate_queue"].ready_candidate_count,
        replay_candidate_top_scope_slug=state["local_lab_replay_candidate_queue"].top_scope_slug,
        replay_ticket_index_status=state["local_lab_replay_ticket_index"].status,
        replay_ticket_count=state["local_lab_replay_ticket_index"].ticket_count,
        replay_ticket_ready_count=state["local_lab_replay_ticket_index"].ready_ticket_count,
        replay_ticket_top_scope_slug=state["local_lab_replay_ticket_index"].top_scope_slug,
        replay_dispatch_plan_status=state["local_lab_replay_dispatch_plan"].status,
        replay_dispatch_ready_count=state["local_lab_replay_dispatch_plan"].ready_dispatch_count,
        replay_dispatch_blocked_count=state["local_lab_replay_dispatch_plan"].blocked_dispatch_count,
        replay_dispatch_top_ticket_id=state["local_lab_replay_dispatch_plan"].top_ticket_id,
        scope_matrix_path=state["scope_matrix_path_value"],
        artifact_release_candidate_path=state["artifact_release_candidate_path_value"],
        artifact_import_dry_run_bridge_path=state["artifact_import_dry_run_bridge_path_value"],
        artifact_promotion_readiness_summary_path=state["artifact_promotion_readiness_summary_path_value"],
        local_lab_loss_surrogate_path=state["local_lab_loss_surrogate_path_value"],
        local_lab_calibration_methods_review_path=state["local_lab_calibration_methods_review_path_value"],
        local_lab_execution_review_path=state["local_lab_execution_review_path_value"],
        local_lab_execution_runtime_projection_path=state["local_lab_execution_runtime_projection_path_value"],
        local_lab_multiple_testing_review_path=state["local_lab_multiple_testing_review_path_value"],
        local_lab_tail_risk_review_path=state["local_lab_tail_risk_review_path_value"],
        calibration_normalized_report_status=state["calibration_normalized_report_status"],
        calibration_normalized_report_ready=state["calibration_normalized_report_ready"],
        calibration_normalized_threshold_count=state["calibration_normalized_threshold_count"],
        local_lab_calibration_normalized_report_path=state["local_lab_calibration_normalized_report_path_value"],
        local_lab_research_priority_path=state["local_lab_research_priority_path_value"],
        local_lab_replay_candidate_queue_path=state["local_lab_replay_candidate_queue_path_value"],
        local_lab_replay_ticket_index_path=state["local_lab_replay_ticket_index_path_value"],
        local_lab_replay_dispatch_plan_path=state["local_lab_replay_dispatch_plan_path_value"],
        local_lab_replay_workflow_manifest_path=state["local_lab_replay_workflow_manifest_path_value"],
        local_lab_monitoring_bundle_manifest_path=state["local_lab_monitoring_bundle_manifest_path_value"],
    )
    atomic_write_json(
        paths["local_lab_monitoring_projection_path"],
        projection.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_monitoring_projection"] = projection
    state["local_lab_monitoring_projection_path_value"] = str(paths["local_lab_monitoring_projection_path"])


def _write_monitoring_bundle_artifacts(state: dict[str, object]) -> None:
    discovery = state["discovery"]
    paths = state["paths"]
    observability_export = build_local_lab_observability_export(
        projection=state["local_lab_monitoring_projection"],
        profile=discovery.run_manifest.profile_scope,
        runtime_mode=discovery.run_manifest.runtime_mode,
        timestamp_ms=discovery.run_manifest.end_timestamp_ms,
    )
    atomic_write_json(
        paths["local_lab_observability_export_path"],
        observability_export.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_observability_export"] = observability_export
    state["local_lab_observability_export_path_value"] = str(paths["local_lab_observability_export_path"])
    write_observability_text_payload(observability_export, paths["local_lab_observability_text_path"])
    state["local_lab_observability_text_path_value"] = str(paths["local_lab_observability_text_path"])
    backend_payload = build_local_lab_monitoring_backend_payload(
        projection=state["local_lab_monitoring_projection"],
        observability_export=observability_export,
        observability_export_ref=state["local_lab_observability_export_path_value"],
    )
    atomic_write_json(
        paths["local_lab_monitoring_backend_payload_path"],
        backend_payload.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_monitoring_backend_payload"] = backend_payload
    state["local_lab_monitoring_backend_payload_path_value"] = str(paths["local_lab_monitoring_backend_payload_path"])
    ingestion_summary = build_local_lab_monitoring_ingestion_summary(
        backend_payload=backend_payload,
        observability_export=observability_export,
        backend_payload_ref=state["local_lab_monitoring_backend_payload_path_value"],
        observability_export_ref=state["local_lab_observability_export_path_value"],
        monitoring_bundle_manifest_ref=str(paths["local_lab_monitoring_bundle_manifest_path"]),
    )
    atomic_write_json(
        paths["local_lab_monitoring_ingestion_summary_path"],
        ingestion_summary.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_monitoring_ingestion_summary"] = ingestion_summary
    state["local_lab_monitoring_ingestion_summary_path_value"] = str(paths["local_lab_monitoring_ingestion_summary_path"])
    bundle_manifest = build_local_lab_monitoring_bundle_manifest(
        backend_payload=backend_payload,
        backend_payload_path=state["local_lab_monitoring_backend_payload_path_value"],
        observability_export=observability_export,
        observability_export_path=state["local_lab_observability_export_path_value"],
        ingestion_summary=ingestion_summary,
        ingestion_summary_path=state["local_lab_monitoring_ingestion_summary_path_value"],
        replay_workflow_manifest_path=state["local_lab_replay_workflow_manifest_path_value"] or "",
        replay_workflow_manifest_status=state["local_lab_replay_workflow_manifest"].replay_dispatch_plan_status,
    )
    atomic_write_json(
        paths["local_lab_monitoring_bundle_manifest_path"],
        bundle_manifest.model_dump(mode="json"),
        indent=2,
    )
    state["local_lab_monitoring_bundle_manifest"] = bundle_manifest
    state["local_lab_monitoring_bundle_manifest_path_value"] = str(paths["local_lab_monitoring_bundle_manifest_path"])


def _run_monitoring_phase(
    args: argparse.Namespace,
    state: dict[str, object],
    walk_forward_review_summary: object,
) -> None:
    _build_monitoring_projection_artifact(args, state, walk_forward_review_summary)
    _write_monitoring_bundle_artifacts(state)


def _build_analysis_summary_core_kwargs(
    args: argparse.Namespace,
    state: dict[str, object],
    walk_forward_review_summary: object,
) -> dict[str, object]:
    discovery = state["discovery"]
    return {
        "correlation_id": args.correlation_id,
        "export_dir": str(discovery.export_dir),
        "run_id": discovery.run_manifest.run_id,
        "artifact_hash": discovery.run_manifest.artifact_hash,
        "dataset_manifest_id": discovery.run_manifest.dataset_manifest_id,
        "profile_scope": discovery.run_manifest.profile_scope.value,
        "runtime_mode": discovery.run_manifest.runtime_mode.value,
        "strategy_id": discovery.run_manifest.strategy_id,
        "strategy_version": discovery.run_manifest.strategy_version,
        "lineage_version": discovery.run_manifest.lineage_version,
        "tested_pairs": discovery.run_manifest.tested_pairs,
        "engine_scope": discovery.run_manifest.engine_scope,
        "selected_pair": state["summary_selected_pair"],
        "selected_engine_id": state["summary_selected_engine_id"],
        "scope_matrix_path": state["scope_matrix_path_value"],
        "scope_count": state["scope_count"],
        "scope_ready_count": state["scope_ready_count"],
        "scope_blocked_count": state["scope_blocked_count"],
        "release_scope_ready_count": state["release_scope_ready_count"],
        "release_scope_blocked_count": state["release_scope_blocked_count"],
        "edge_output_path": str(state["paths"]["edge_output_path"]),
        "edge_input_summary_path": str(state["paths"]["edge_input_summary_path"]),
        "review_ready": state["review_ready"],
        "trade_loss_attribution_ready": state["trade_loss_attribution_ready"],
        "walk_forward_review_ready": walk_forward_review_summary.walk_forward_pass,
        "artifact_ablation_ready": state["artifact_ablation_ready"],
        "artifact_proof_ready": state["artifact_proof_ready"],
        "artifact_proof_validation_reasons": state["artifact_proof_validation_reasons"],
        "edge_calibration_ready": state["edge_input_summary"].get("record_count", 0) > 0,
    }


def _build_analysis_summary_path_kwargs(state: dict[str, object]) -> dict[str, object]:
    return {
        "artifact_ablation_study_path": state["artifact_ablation_study_path_value"],
        "review_output_dir": state["review_output_dir_value"],
        "review_bundle_path": state["review_bundle_path_value"],
        "review_projection_path": state["review_projection_path_value"],
        "trade_loss_attribution_path": state["trade_loss_attribution_path_value"],
        "review_input_summary_path": state["review_input_summary_path_value"],
        "walk_forward_review_template_path": str(state["paths"]["walk_forward_review_template_path"]),
        "walk_forward_review_path": state["walk_forward_review_path"],
        "walk_forward_review_summary_path": str(state["paths"]["walk_forward_review_summary_path"]),
        "artifact_proof_summary_path": state["artifact_proof_summary_path_value"],
        "artifact_proof_assessment_path": state["artifact_proof_assessment_path_value"],
        "artifact_release_candidate_path": state["artifact_release_candidate_path_value"],
        "local_lab_recalibration_plan_path": state["local_lab_recalibration_plan_path_value"],
        "artifact_import_dry_run_bridge_path": state["artifact_import_dry_run_bridge_path_value"],
        "artifact_source_summary_path": state["artifact_source_summary_path_value"],
        "artifact_release_gate_summary_path": state["artifact_release_gate_summary_path_value"],
        "artifact_promotion_readiness_summary_path": state["artifact_promotion_readiness_summary_path_value"],
        "local_lab_monitoring_projection_path": state["local_lab_monitoring_projection_path_value"],
        "local_lab_observability_export_path": state["local_lab_observability_export_path_value"],
        "local_lab_observability_text_path": state["local_lab_observability_text_path_value"],
        "local_lab_monitoring_backend_payload_path": state["local_lab_monitoring_backend_payload_path_value"],
        "local_lab_monitoring_ingestion_summary_path": state["local_lab_monitoring_ingestion_summary_path_value"],
        "local_lab_monitoring_bundle_manifest_path": state["local_lab_monitoring_bundle_manifest_path_value"],
        "local_lab_loss_surrogate_path": state["local_lab_loss_surrogate_path_value"],
        "local_lab_calibration_methods_review_path": state["local_lab_calibration_methods_review_path_value"],
        "local_lab_execution_review_path": state["local_lab_execution_review_path_value"],
        "local_lab_execution_runtime_projection_path": state["local_lab_execution_runtime_projection_path_value"],
        "local_lab_multiple_testing_review_path": state["local_lab_multiple_testing_review_path_value"],
        "local_lab_tail_risk_review_path": state["local_lab_tail_risk_review_path_value"],
        "local_lab_calibration_normalized_report_path": state["local_lab_calibration_normalized_report_path_value"],
        "local_lab_research_priority_path": state["local_lab_research_priority_path_value"],
        "local_lab_replay_candidate_queue_path": state["local_lab_replay_candidate_queue_path_value"],
        "local_lab_replay_ticket_index_path": state["local_lab_replay_ticket_index_path_value"],
        "local_lab_replay_dispatch_plan_path": state["local_lab_replay_dispatch_plan_path_value"],
        "local_lab_replay_workflow_manifest_path": state["local_lab_replay_workflow_manifest_path_value"],
        "artifact_upload_request_path": state["artifact_upload_request_path_value"],
        "artifact_import_request_path": state["artifact_import_request_path_value"],
        "artifact_import_decision_path": state["artifact_import_decision_path_value"],
        "artifact_upload_decision_path": state["artifact_upload_decision_path_value"],
    }


def _build_analysis_summary_status_kwargs(state: dict[str, object]) -> dict[str, object]:
    return {
        "loss_surrogate_status": state["local_lab_loss_surrogate"].status,
        "loss_surrogate_ready": state["local_lab_loss_surrogate"].ready,
        "loss_surrogate_scope_count": state["local_lab_loss_surrogate"].scope_count,
        "loss_surrogate_top_scope_slug": state["local_lab_loss_surrogate"].highest_risk_scope_slug,
        "loss_surrogate_top_probability": state["local_lab_loss_surrogate"].highest_risk_probability,
        "calibration_methods_review_status": state["calibration_methods_review_status"],
        "calibration_methods_review_ready": state["calibration_methods_review_ready"],
        "calibration_methods_dsr_pass": state["calibration_methods_dsr_pass"],
        "calibration_methods_walk_forward_plan_ready": state["calibration_methods_walk_forward_plan_ready"],
        "calibration_methods_stationarity_status": state["calibration_methods_stationarity_status"],
        "calibration_methods_stationarity_pass": state["calibration_methods_stationarity_pass"],
        "execution_review_status": state["execution_review_status"],
        "execution_review_ready": state["execution_review_ready"],
        "execution_ready_threshold_count": state["execution_ready_threshold_count"],
        "execution_partial_threshold_count": state["execution_partial_threshold_count"],
        "execution_blocked_threshold_count": state["execution_blocked_threshold_count"],
        "execution_runtime_projection_status": state["execution_runtime_projection_status"],
        "execution_runtime_projection_ready": state["execution_runtime_projection_ready"],
        "execution_runtime_projection_consumer_count": state["execution_runtime_projection_consumer_count"],
        "execution_runtime_projection_ready_consumer_count": state["execution_runtime_projection_ready_consumer_count"],
        "execution_runtime_projection_partial_consumer_count": state["execution_runtime_projection_partial_consumer_count"],
        "execution_runtime_projection_blocked_consumer_count": state["execution_runtime_projection_blocked_consumer_count"],
        "multiple_testing_review_status": state["multiple_testing_review_status"],
        "multiple_testing_review_ready": state["multiple_testing_review_ready"],
        "multiple_testing_correction_required": state["multiple_testing_correction_required"],
        "multiple_testing_correction": state["multiple_testing_correction"],
        "multiple_testing_family_count": state["multiple_testing_family_count"],
        "calibration_normalized_report_status": state["calibration_normalized_report_status"],
        "calibration_normalized_report_ready": state["calibration_normalized_report_ready"],
        "calibration_normalized_threshold_count": state["calibration_normalized_threshold_count"],
        "tail_risk_review_status": state["tail_risk_review_status"],
        "tail_risk_review_ready": state["tail_risk_review_ready"],
        "tail_risk_ready_breaker_count": state["tail_risk_ready_breaker_count"],
        "tail_risk_partial_breaker_count": state["tail_risk_partial_breaker_count"],
        "tail_risk_blocked_breaker_count": state["tail_risk_blocked_breaker_count"],
    }


def _build_analysis_summary_release_kwargs(state: dict[str, object]) -> dict[str, object]:
    return {
        "release_ready_for_shadow": state["artifact_release_candidate"].ready_for_shadow_import,
        "release_status": state["artifact_release_candidate"].release_status,
        "release_blocking_reasons": state["artifact_release_candidate"].blocking_reasons,
        "release_ready_scope_slugs": tuple(
            scope.scope_slug
            for scope in state["artifact_release_candidate"].release_scopes
            if scope.release_ready
        ),
        "release_blocked_scope_slugs": tuple(
            scope.scope_slug
            for scope in state["artifact_release_candidate"].release_scopes
            if not scope.release_ready
        ),
        "release_scope_summary_count": len(state["release_scope_summary_paths"]),
        "release_scope_summary_paths": state["release_scope_summary_paths"],
        "promotion_readiness_status": state["promotion_readiness_summary"].readiness_status,
        "promotion_activation_stage": state["promotion_readiness_summary"].activation_stage.value,
        "promotion_normalized_state": state["promotion_readiness_summary"].normalized_promotion_state.value,
        "promotion_review_state": state["promotion_readiness_summary"].review_state.value,
        "recalibration_candidate_ready": state["local_lab_recalibration_plan"].calibration_candidate_ready,
        "recalibration_blocking_reasons": state["local_lab_recalibration_plan"].blocking_reasons,
        "recalibration_action_count": state["local_lab_recalibration_plan"].action_count,
        "bridge_ready_for_shadow_dry_run": state["artifact_upload_bridge_candidate"].ready_for_shadow_import_dry_run,
        "bridge_status": state["artifact_upload_bridge_candidate"].bridge_status,
        "bridge_blocking_reasons": state["artifact_upload_bridge_candidate"].blocking_reasons,
        "bridge_release_gate_status": state["artifact_upload_bridge_candidate"].release_gate_status,
        "bridge_release_gate_reasons": state["artifact_upload_bridge_candidate"].release_gate_reasons,
        "bridge_semantic_status": state["artifact_upload_bridge_candidate"].semantic_status,
        "bridge_semantic_reasons": state["artifact_upload_bridge_candidate"].semantic_reasons,
        "bridge_transport_payload_ref_count": state["artifact_upload_bridge_candidate"].transport_payload_ref_count,
        "bridge_transport_supplementary_refs": state["artifact_upload_bridge_candidate"].transport_supplementary_refs,
    }


def _build_analysis_summary_monitoring_kwargs(state: dict[str, object]) -> dict[str, object]:
    return {
        "monitoring_projection_status": state["local_lab_monitoring_projection"].status,
        "monitoring_projection_detail": state["local_lab_monitoring_projection"].detail,
        "local_lab_observability_sample_count": len(state["local_lab_observability_export"].samples),
        "local_lab_monitoring_backend_status": state["local_lab_monitoring_backend_payload"].status,
        "local_lab_monitoring_ingestion_ready": state["local_lab_monitoring_ingestion_summary"].ingestion_ready,
        "research_priority_status": state["local_lab_research_priority"].status,
        "research_priority_scope_count": state["local_lab_research_priority"].priority_scope_count,
        "research_priority_top_scope_slug": state["local_lab_research_priority"].highest_priority_scope_slug,
        "research_priority_top_score": state["local_lab_research_priority"].highest_priority_score,
        "replay_candidate_queue_status": state["local_lab_replay_candidate_queue"].status,
        "replay_candidate_count": state["local_lab_replay_candidate_queue"].candidate_count,
        "replay_candidate_ready_count": state["local_lab_replay_candidate_queue"].ready_candidate_count,
        "replay_candidate_top_scope_slug": state["local_lab_replay_candidate_queue"].top_scope_slug,
        "replay_ticket_index_status": state["local_lab_replay_ticket_index"].status,
        "replay_ticket_count": state["local_lab_replay_ticket_index"].ticket_count,
        "replay_ticket_ready_count": state["local_lab_replay_ticket_index"].ready_ticket_count,
        "replay_ticket_top_scope_slug": state["local_lab_replay_ticket_index"].top_scope_slug,
        "replay_dispatch_plan_status": state["local_lab_replay_dispatch_plan"].status,
        "replay_dispatch_ready_count": state["local_lab_replay_dispatch_plan"].ready_dispatch_count,
        "replay_dispatch_blocked_count": state["local_lab_replay_dispatch_plan"].blocked_dispatch_count,
        "replay_dispatch_top_ticket_id": state["local_lab_replay_dispatch_plan"].top_ticket_id,
    }


def _write_analysis_summary(
    args: argparse.Namespace,
    state: dict[str, object],
    walk_forward_review_summary: object,
) -> None:
    summary = LocalLabAnalysisBundleSummary(
        **_build_analysis_summary_core_kwargs(args, state, walk_forward_review_summary),
        **_build_analysis_summary_path_kwargs(state),
        **_build_analysis_summary_status_kwargs(state),
        **_build_analysis_summary_release_kwargs(state),
        **_build_analysis_summary_monitoring_kwargs(state),
    )
    atomic_write_json(state["paths"]["summary_path"], summary.model_dump(mode="json"), indent=2)
    _emit_local_lab_analysis_bundle_output(
        summary_path=state["paths"]["summary_path"],
        review_output_dir_value=state["review_output_dir_value"],
        scope_matrix_path_value=state["scope_matrix_path_value"],
        artifact_ablation_study_path_value=state["artifact_ablation_study_path_value"],
        artifact_proof_summary_path_value=state["artifact_proof_summary_path_value"],
        artifact_proof_assessment_path_value=state["artifact_proof_assessment_path_value"],
        artifact_release_candidate_path_value=state["artifact_release_candidate_path_value"],
        local_lab_recalibration_plan_path_value=state["local_lab_recalibration_plan_path_value"],
        artifact_import_dry_run_bridge_path_value=state["artifact_import_dry_run_bridge_path_value"],
        artifact_promotion_readiness_summary_path_value=state["artifact_promotion_readiness_summary_path_value"],
        local_lab_monitoring_projection_path_value=state["local_lab_monitoring_projection_path_value"],
        local_lab_observability_export_path_value=state["local_lab_observability_export_path_value"],
        local_lab_observability_text_path_value=state["local_lab_observability_text_path_value"],
        local_lab_monitoring_backend_payload_path_value=state["local_lab_monitoring_backend_payload_path_value"],
        local_lab_monitoring_ingestion_summary_path_value=state["local_lab_monitoring_ingestion_summary_path_value"],
        local_lab_monitoring_bundle_manifest_path_value=state["local_lab_monitoring_bundle_manifest_path_value"],
        local_lab_loss_surrogate_path_value=state["local_lab_loss_surrogate_path_value"],
        local_lab_execution_review_path_value=state["local_lab_execution_review_path_value"],
        local_lab_execution_runtime_projection_path_value=state["local_lab_execution_runtime_projection_path_value"],
        local_lab_multiple_testing_review_path_value=state["local_lab_multiple_testing_review_path_value"],
        local_lab_calibration_normalized_report_path_value=state["local_lab_calibration_normalized_report_path_value"],
        local_lab_tail_risk_review_path_value=state["local_lab_tail_risk_review_path_value"],
        local_lab_research_priority_path_value=state["local_lab_research_priority_path_value"],
        local_lab_replay_candidate_queue_path_value=state["local_lab_replay_candidate_queue_path_value"],
        local_lab_replay_ticket_index_path_value=state["local_lab_replay_ticket_index_path_value"],
        local_lab_replay_dispatch_plan_path_value=state["local_lab_replay_dispatch_plan_path_value"],
        local_lab_replay_workflow_manifest_path_value=state["local_lab_replay_workflow_manifest_path_value"],
        edge_output_path=state["paths"]["edge_output_path"],
    )




def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    state = _initialize_analysis_state(args)
    _, walk_forward_review_summary = _prepare_walk_forward_review(args, state)
    review_exit_code = _run_review_phase(args, state, walk_forward_review_summary)
    if review_exit_code != 0:
        return review_exit_code
    _run_secondary_review_phase(args, state)
    edge_exit_code = _run_edge_and_proof_phase(args, state, walk_forward_review_summary)
    if edge_exit_code != 0:
        return edge_exit_code
    _run_release_candidate_phase(args, state)
    _run_promotion_and_replay_phase(args, state)
    _run_monitoring_phase(args, state, walk_forward_review_summary)
    _write_analysis_summary(args, state, walk_forward_review_summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
