#!/usr/bin/env python3
"""Chain governed Local IA Lab post-trade review and EDGE calibration from one export_dir."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
import sys

from pydantic import BaseModel, Field


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from backtest_artifact_import.export_dir_bridge import discover_local_replay_export  # noqa: E402
from interface_contracts import ArtifactClass  # noqa: E402
from interface_contracts.atomic_io import atomic_write_json  # noqa: E402
from monitoring.local_lab_ingestion import (  # noqa: E402
    build_local_lab_monitoring_ingestion_summary,
)
from monitoring.observability_io import write_observability_text_payload  # noqa: E402
from local_replay_runtime import (  # noqa: E402
    LocalLabScopeAnalysisMatrix,
    LocalLabScopeAnalysisRow,
    WalkForwardHumanReview,
    build_local_lab_ablation_study,
    build_local_lab_artifact_proof_assessment,
    build_local_lab_artifact_release_candidate,
    build_local_lab_artifact_release_scope_summary,
    build_local_lab_recalibration_plan,
    build_local_lab_scope_matrix,
    build_pending_local_lab_ablation_study,
    build_walk_forward_review_template,
    build_local_lab_scope_slug,
    discover_local_lab_scope_keys,
    load_replay_dtr_records,
    summarize_walk_forward_review,
)
from local_replay_runtime.artifact_upload_bridge_candidate import (  # noqa: E402
    build_local_lab_release_gate_summary,
    build_local_lab_source_artifact_summary,
    build_local_lab_artifact_upload_dry_run_bridge,
)
from local_replay_runtime.local_lab_promotion_readiness import (  # noqa: E402
    build_local_lab_promotion_readiness_summary,
)
from local_replay_runtime.local_lab_monitoring_projection import (  # noqa: E402
    build_local_lab_monitoring_projection,
)
from local_replay_runtime.local_lab_observability import (  # noqa: E402
    build_local_lab_observability_export,
)
from local_replay_runtime.local_lab_monitoring_backend import (  # noqa: E402
    build_local_lab_monitoring_backend_payload,
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    discovery = discover_local_replay_export(Path(args.export_dir))
    candidate_records = load_replay_dtr_records(discovery.payload_bundle.replay_dtr_ref)

    baseline_discovery = None
    baseline_records: tuple = ()
    if args.baseline_export_dir:
        baseline_discovery = discover_local_replay_export(Path(args.baseline_export_dir))
        baseline_records = load_replay_dtr_records(baseline_discovery.payload_bundle.replay_dtr_ref)

    scope_keys = discover_local_lab_scope_keys(
        candidate_records,
        pair=args.pair,
        engine_id=args.engine_id,
    )
    multi_scope_mode = args.all_scopes and len(scope_keys) > 1

    output_root = Path(args.output_root)
    review_output_dir = output_root / "post_trade_review"
    edge_output_path = output_root / "edge_gate.yml"
    summary_path = output_root / "local_lab_analysis_summary.json"

    review_output_dir_value: str | None = None
    review_bundle_path_value: str | None = None
    review_projection_path_value: str | None = None
    trade_loss_attribution_path_value: str | None = None
    review_input_summary_path_value: str | None = None
    artifact_ablation_study_path_value: str | None = None
    artifact_proof_summary_path_value: str | None = None
    artifact_proof_assessment_path_value: str | None = None
    artifact_release_candidate_path_value: str | None = None
    local_lab_recalibration_plan_path_value: str | None = None
    artifact_import_dry_run_bridge_path_value: str | None = None
    artifact_source_summary_path_value: str | None = None
    artifact_release_gate_summary_path_value: str | None = None
    artifact_promotion_readiness_summary_path_value: str | None = None
    local_lab_monitoring_projection_path_value: str | None = None
    local_lab_observability_export_path_value: str | None = None
    local_lab_observability_text_path_value: str | None = None
    local_lab_monitoring_backend_payload_path_value: str | None = None
    local_lab_monitoring_ingestion_summary_path_value: str | None = None
    artifact_upload_request_path_value: str | None = None
    artifact_import_request_path_value: str | None = None
    artifact_import_decision_path_value: str | None = None
    artifact_upload_decision_path_value: str | None = None
    release_scope_summary_paths: tuple[str, ...] = ()

    artifact_ablation_study_path = output_root / "artifact_ablation_study.json"
    walk_forward_review_template_path = output_root / "walk_forward_review.template.json"
    walk_forward_review_output_path = output_root / "walk_forward_review.json"
    walk_forward_review_summary_path = output_root / "walk_forward_review.summary.json"
    artifact_proof_summary_path = output_root / "artifact_proof_summary.json"
    artifact_proof_assessment_path = output_root / "artifact_proof_assessment.json"
    artifact_release_candidate_path = output_root / "artifact_release_candidate.json"
    local_lab_recalibration_plan_path = output_root / "local_lab_recalibration_plan.json"
    artifact_import_dry_run_bridge_path = output_root / "artifact_import_dry_run_bridge.json"
    artifact_source_summary_path = output_root / "artifact_source_summary.json"
    artifact_release_gate_summary_path = output_root / "artifact_release_gate_summary.json"
    artifact_promotion_readiness_summary_path = output_root / "artifact_promotion_readiness_summary.json"
    local_lab_monitoring_projection_path = output_root / "local_lab_monitoring_projection.json"
    local_lab_observability_export_path = output_root / "local_lab_observability_export.json"
    local_lab_observability_text_path = output_root / "local_lab_observability.prom"
    local_lab_monitoring_backend_payload_path = (
        output_root / "local_lab_monitoring_backend_payload.json"
    )
    local_lab_monitoring_ingestion_summary_path = (
        output_root / "local_lab_monitoring_ingestion_summary.json"
    )
    artifact_upload_request_path = output_root / "artifact_upload_request.dry_run.json"
    artifact_import_request_path = output_root / "artifact_import_request.dry_run.json"
    artifact_import_decision_path = output_root / "artifact_import_decision.dry_run.json"
    artifact_upload_decision_path = output_root / "artifact_upload_decision.dry_run.json"
    scope_matrix_path = output_root / "local_lab_scope_matrix.json"
    edge_input_summary_path = edge_output_path.with_suffix(".input_summary.json")

    walk_forward_template = build_walk_forward_review_template(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        run_id=discovery.run_manifest.run_id,
    )
    atomic_write_json(
        walk_forward_review_template_path,
        walk_forward_template.model_dump(mode="json"),
        indent=2,
    )

    walk_forward_review_path: str | None = None
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
            walk_forward_review_output_path,
            walk_forward_review.model_dump(mode="json"),
            indent=2,
        )
        walk_forward_review_path = str(walk_forward_review_output_path)
    else:
        walk_forward_review = walk_forward_template

    walk_forward_review_summary = summarize_walk_forward_review(walk_forward_review)
    atomic_write_json(
        walk_forward_review_summary_path,
        walk_forward_review_summary.model_dump(mode="json"),
        indent=2,
    )

    review_ready = False
    trade_loss_attribution_ready = False
    artifact_ablation_ready = False
    artifact_proof_ready = False
    artifact_proof_validation_reasons: tuple[str, ...] = ()
    artifact_proof_summary_for_bridge = None
    recalibration_loss_reports: list[TradeLossAttributionReport] = []
    summary_selected_pair = args.pair
    summary_selected_engine_id = args.engine_id
    scope_count = 0
    scope_ready_count = 0
    scope_blocked_count = 0
    release_scope_ready_count = 0
    release_scope_blocked_count = 0
    scope_matrix_path_value: str | None = None
    scope_matrix: LocalLabScopeAnalysisMatrix | None = None

    if multi_scope_mode:
        scope_rows: list[LocalLabScopeAnalysisRow] = []
        for scope in scope_keys:
            scope_root = output_root / "scopes" / scope.scope_slug
            scope_review_output_dir = scope_root / "post_trade_review"
            scope_correlation_id = _scope_correlation_id(
                args.correlation_id,
                pair=scope.pair,
                engine_id=scope.engine_id,
            )
            scope_candidate_records = _filter_records(
                candidate_records,
                pair=scope.pair,
                engine_id=scope.engine_id,
            )
            scope_baseline_records = _filter_records(
                baseline_records,
                pair=scope.pair,
                engine_id=scope.engine_id,
            )
            scope_review_args = [
                "--export-dir",
                str(discovery.export_dir),
                "--correlation-id",
                scope_correlation_id,
                "--source-version",
                args.source_version,
                "--notes",
                args.notes,
                "--output-dir",
                str(scope_review_output_dir),
                "--near-miss-threshold",
                str(args.near_miss_threshold),
                "--pair",
                scope.pair,
                "--engine-id",
                scope.engine_id,
            ]
            if args.strategy_classification:
                scope_review_args.extend(["--strategy-classification", args.strategy_classification])
            if args.state_dir:
                scope_review_args.extend(["--state-dir", str(Path(args.state_dir) / scope.scope_slug)])
            scope_total_opportunities = (
                args.total_opportunities
                if args.total_opportunities is not None
                else len(scope_candidate_records)
            )
            scope_review_args.extend(["--total-opportunities", str(scope_total_opportunities)])

            review_exit_code = run_local_lab_post_trade_review_main(scope_review_args)
            if review_exit_code != 0:
                return review_exit_code

            scope_review_bundle_path = scope_review_output_dir / "meta_learning_review.bundle.json"
            scope_meta_runtime_path = scope_review_output_dir / "meta_runtime_result.json"
            scope_trade_loss_attribution_path = scope_review_output_dir / "trade_loss_attribution.json"
            scope_review_input_summary_path = scope_review_output_dir / "governed_input_summary.json"
            scope_artifact_ablation_study_path = scope_root / "artifact_ablation_study.json"
            scope_artifact_proof_summary_path = scope_root / "artifact_proof_summary.json"
            scope_artifact_proof_assessment_path = scope_root / "artifact_proof_assessment.json"

            scope_review_bundle = _load_json(scope_review_bundle_path)
            scope_meta_runtime_result = MetaRuntimeResult.model_validate(_load_json(scope_meta_runtime_path))
            scope_trade_loss_attribution = TradeLossAttributionReport.model_validate(
                _load_json(scope_trade_loss_attribution_path)
            )
            recalibration_loss_reports.append(scope_trade_loss_attribution)
            _load_json(scope_review_input_summary_path)

            if baseline_discovery is not None:
                scope_ablation_study = build_local_lab_ablation_study(
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
            else:
                scope_ablation_study = build_pending_local_lab_ablation_study(
                    correlation_id=scope_correlation_id,
                    candidate_export_dir=str(discovery.export_dir),
                    candidate_run_id=discovery.run_manifest.run_id,
                    candidate_dataset_manifest_id=discovery.run_manifest.dataset_manifest_id,
                    selected_pair=scope.pair,
                    selected_engine_id=scope.engine_id,
                )
            atomic_write_json(
                scope_artifact_ablation_study_path,
                scope_ablation_study.model_dump(mode="json"),
                indent=2,
            )

            scope_artifact_proof_assessment = build_local_lab_artifact_proof_assessment(
                correlation_id=scope_correlation_id,
                export_dir=str(discovery.export_dir),
                run_id=discovery.run_manifest.run_id,
                meta_result=scope_meta_runtime_result,
                trade_loss_attribution=scope_trade_loss_attribution,
                walk_forward_review=walk_forward_review_summary,
                ablation_study=scope_ablation_study,
            )
            atomic_write_json(
                scope_artifact_proof_summary_path,
                scope_artifact_proof_assessment.proof_summary.model_dump(mode="json"),
                indent=2,
            )
            atomic_write_json(
                scope_artifact_proof_assessment_path,
                scope_artifact_proof_assessment.model_dump(mode="json"),
                indent=2,
            )

            scope_rows.append(
                LocalLabScopeAnalysisRow(
                    pair=scope.pair,
                    engine_id=scope.engine_id,
                    scope_slug=scope.scope_slug,
                    review_output_dir=str(scope_review_output_dir),
                    review_bundle_path=str(scope_review_bundle_path),
                    trade_loss_attribution_path=str(scope_trade_loss_attribution_path),
                    artifact_ablation_study_path=str(scope_artifact_ablation_study_path),
                    artifact_proof_summary_path=str(scope_artifact_proof_summary_path),
                    artifact_proof_assessment_path=str(scope_artifact_proof_assessment_path),
                    candidate_record_count=len(scope_candidate_records),
                    baseline_record_count=len(scope_baseline_records),
                    executed_records=scope_trade_loss_attribution.executed_records,
                    losing_trade_count=scope_trade_loss_attribution.losing_trade_count,
                    artifact_ablation_ready=scope_ablation_study.study_ready,
                    artifact_proof_ready=scope_artifact_proof_assessment.ready_for_vps_import,
                    artifact_proof_validation_reasons=scope_artifact_proof_assessment.validation_reasons,
                    caution_flags=tuple(
                        dict.fromkeys(
                            list(scope_ablation_study.caution_flags)
                            + list(scope_artifact_proof_assessment.caution_flags)
                        )
                    ),
                    proof_summary=scope_artifact_proof_assessment.proof_summary,
                )
            )

        scope_matrix = build_local_lab_scope_matrix(
            correlation_id=args.correlation_id,
            export_dir=str(discovery.export_dir),
            baseline_export_dir=(
                None if baseline_discovery is None else str(baseline_discovery.export_dir)
            ),
            scopes=tuple(scope_rows),
        )
        atomic_write_json(scope_matrix_path, scope_matrix.model_dump(mode="json"), indent=2)
        scope_matrix_path_value = str(scope_matrix_path)
        scope_count = scope_matrix.scope_count
        scope_ready_count = scope_matrix.ready_scope_count
        scope_blocked_count = scope_matrix.blocked_scope_count
        review_ready = scope_matrix.scope_count > 0
        trade_loss_attribution_ready = scope_matrix.scope_count > 0
        artifact_ablation_ready = all(scope.artifact_ablation_ready for scope in scope_matrix.scopes)
        artifact_proof_ready = scope_matrix.scope_count > 0 and scope_matrix.blocked_scope_count == 0
        artifact_proof_validation_reasons = tuple(
            dict.fromkeys(
                reason
                for scope in scope_matrix.scopes
                for reason in scope.artifact_proof_validation_reasons
            )
        )
    else:
        review_args = [
            "--export-dir",
            str(discovery.export_dir),
            "--correlation-id",
            args.correlation_id,
            "--source-version",
            args.source_version,
            "--notes",
            args.notes,
            "--output-dir",
            str(review_output_dir),
            "--near-miss-threshold",
            str(args.near_miss_threshold),
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

        review_bundle_path = review_output_dir / "meta_learning_review.bundle.json"
        review_projection_path = review_output_dir / "meta_learning_projection.json"
        meta_runtime_path = review_output_dir / "meta_runtime_result.json"
        trade_loss_attribution_path = review_output_dir / "trade_loss_attribution.json"
        review_input_summary_path = review_output_dir / "governed_input_summary.json"

        review_input_summary = _load_json(review_input_summary_path)
        review_bundle = _load_json(review_bundle_path)
        trade_loss_attribution = TradeLossAttributionReport.model_validate(
            _load_json(trade_loss_attribution_path)
        )
        recalibration_loss_reports.append(trade_loss_attribution)
        meta_runtime_result = MetaRuntimeResult.model_validate(_load_json(meta_runtime_path))

        if baseline_discovery is not None:
            artifact_ablation_study = build_local_lab_ablation_study(
                correlation_id=args.correlation_id,
                candidate_export_dir=str(discovery.export_dir),
                baseline_export_dir=str(baseline_discovery.export_dir),
                candidate_run_id=discovery.run_manifest.run_id,
                baseline_run_id=baseline_discovery.run_manifest.run_id,
                candidate_dataset_manifest_id=discovery.run_manifest.dataset_manifest_id,
                baseline_dataset_manifest_id=baseline_discovery.run_manifest.dataset_manifest_id,
                candidate_records=candidate_records,
                baseline_records=baseline_records,
                selected_pair=review_input_summary.get("selected_pair"),
                selected_engine_id=review_input_summary.get("selected_engine_id"),
            )
        else:
            artifact_ablation_study = build_pending_local_lab_ablation_study(
                correlation_id=args.correlation_id,
                candidate_export_dir=str(discovery.export_dir),
                candidate_run_id=discovery.run_manifest.run_id,
                candidate_dataset_manifest_id=discovery.run_manifest.dataset_manifest_id,
                selected_pair=review_input_summary.get("selected_pair"),
                selected_engine_id=review_input_summary.get("selected_engine_id"),
            )
        atomic_write_json(
            artifact_ablation_study_path,
            artifact_ablation_study.model_dump(mode="json"),
            indent=2,
        )

        artifact_proof_assessment = build_local_lab_artifact_proof_assessment(
            correlation_id=args.correlation_id,
            export_dir=str(discovery.export_dir),
            run_id=discovery.run_manifest.run_id,
            meta_result=meta_runtime_result,
            trade_loss_attribution=trade_loss_attribution,
            walk_forward_review=walk_forward_review_summary,
            ablation_study=artifact_ablation_study,
        )
        atomic_write_json(
            artifact_proof_summary_path,
            artifact_proof_assessment.proof_summary.model_dump(mode="json"),
            indent=2,
        )
        atomic_write_json(
            artifact_proof_assessment_path,
            artifact_proof_assessment.model_dump(mode="json"),
            indent=2,
        )

        review_output_dir_value = str(review_output_dir)
        review_bundle_path_value = str(review_bundle_path)
        review_projection_path_value = str(review_projection_path)
        trade_loss_attribution_path_value = str(trade_loss_attribution_path)
        review_input_summary_path_value = str(review_input_summary_path)
        artifact_ablation_study_path_value = str(artifact_ablation_study_path)
        artifact_proof_summary_path_value = str(artifact_proof_summary_path)
        artifact_proof_assessment_path_value = str(artifact_proof_assessment_path)
        review_ready = bool(review_bundle.get("review_export", {}).get("markdown_body", "").strip())
        trade_loss_attribution_ready = trade_loss_attribution.attribution_ready
        artifact_ablation_ready = artifact_ablation_study.study_ready
        artifact_proof_ready = artifact_proof_assessment.ready_for_vps_import
        artifact_proof_validation_reasons = artifact_proof_assessment.validation_reasons
        artifact_proof_summary_for_bridge = artifact_proof_assessment.proof_summary
        summary_selected_pair = review_input_summary.get("selected_pair")
        summary_selected_engine_id = review_input_summary.get("selected_engine_id")

        if args.all_scopes:
            selected_pair = review_input_summary.get("selected_pair")
            selected_engine_id = review_input_summary.get("selected_engine_id")
            scope_rows = (
                LocalLabScopeAnalysisRow(
                    pair=selected_pair,
                    engine_id=selected_engine_id,
                    scope_slug=build_local_lab_scope_slug(selected_pair, selected_engine_id),
                    review_output_dir=str(review_output_dir),
                    review_bundle_path=str(review_bundle_path),
                    trade_loss_attribution_path=str(trade_loss_attribution_path),
                    artifact_ablation_study_path=str(artifact_ablation_study_path),
                    artifact_proof_summary_path=str(artifact_proof_summary_path),
                    artifact_proof_assessment_path=str(artifact_proof_assessment_path),
                    candidate_record_count=len(
                        _filter_records(
                            candidate_records,
                            pair=selected_pair,
                            engine_id=selected_engine_id,
                        )
                    ),
                    baseline_record_count=len(
                        _filter_records(
                            baseline_records,
                            pair=selected_pair,
                            engine_id=selected_engine_id,
                        )
                    ),
                    executed_records=trade_loss_attribution.executed_records,
                    losing_trade_count=trade_loss_attribution.losing_trade_count,
                    artifact_ablation_ready=artifact_ablation_study.study_ready,
                    artifact_proof_ready=artifact_proof_assessment.ready_for_vps_import,
                    artifact_proof_validation_reasons=artifact_proof_assessment.validation_reasons,
                    caution_flags=tuple(
                        dict.fromkeys(
                            list(artifact_ablation_study.caution_flags)
                            + list(artifact_proof_assessment.caution_flags)
                        )
                    ),
                    proof_summary=artifact_proof_assessment.proof_summary,
                ),
            )
            scope_matrix = build_local_lab_scope_matrix(
                correlation_id=args.correlation_id,
                export_dir=str(discovery.export_dir),
                baseline_export_dir=(
                    None if baseline_discovery is None else str(baseline_discovery.export_dir)
                ),
                scopes=scope_rows,
            )
            atomic_write_json(scope_matrix_path, scope_matrix.model_dump(mode="json"), indent=2)
            scope_matrix_path_value = str(scope_matrix_path)
            scope_count = scope_matrix.scope_count
            scope_ready_count = scope_matrix.ready_scope_count
            scope_blocked_count = scope_matrix.blocked_scope_count

    local_lab_recalibration_plan = build_local_lab_recalibration_plan(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        loss_reports=tuple(recalibration_loss_reports),
        scope_matrix=scope_matrix,
    )
    atomic_write_json(
        local_lab_recalibration_plan_path,
        local_lab_recalibration_plan.model_dump(mode="json"),
        indent=2,
    )
    local_lab_recalibration_plan_path_value = str(local_lab_recalibration_plan_path)
    edge_args = [
        "--export-dir",
        str(discovery.export_dir),
        "--output-path",
        str(edge_output_path),
        "--signed-by",
        args.signed_by,
        "--artifact-id",
        args.artifact_id,
        "--calibration-version",
        args.calibration_version,
        "--bootstrap-samples",
        str(args.bootstrap_samples),
        "--min-positive-trades",
        str(args.min_positive_trades),
        "--min-cost-observations",
        str(args.min_cost_observations),
        "--rng-seed",
        str(args.rng_seed),
        "--recalibration-plan-path",
        str(local_lab_recalibration_plan_path),
    ]
    edge_exit_code = run_edge_gate_calibration_main(edge_args)
    if edge_exit_code != 0:
        return edge_exit_code
    edge_input_summary = _load_json(edge_input_summary_path)

    artifact_release_candidate = build_local_lab_artifact_release_candidate(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        baseline_export_dir=None if baseline_discovery is None else str(baseline_discovery.export_dir),
        run_id=discovery.run_manifest.run_id,
        artifact_id=args.artifact_id,
        artifact_path=str(edge_output_path),
        artifact_input_summary_path=str(edge_input_summary_path),
        walk_forward_review_summary_path=str(walk_forward_review_summary_path),
        local_lab_recalibration_plan_path=local_lab_recalibration_plan_path_value,
        edge_calibration_ready=edge_input_summary.get("record_count", 0) > 0,
        recalibration_candidate_ready=local_lab_recalibration_plan.calibration_candidate_ready,
        recalibration_blocking_reasons=local_lab_recalibration_plan.blocking_reasons,
        artifact_proof_ready=artifact_proof_ready,
        artifact_proof_validation_reasons=artifact_proof_validation_reasons,
        artifact_proof_summary_path=artifact_proof_summary_path_value,
        artifact_proof_assessment_path=artifact_proof_assessment_path_value,
        scope_matrix_path=scope_matrix_path_value,
        scope_matrix=scope_matrix,
    )
    atomic_write_json(
        artifact_release_candidate_path,
        artifact_release_candidate.model_dump(mode="json"),
        indent=2,
    )
    artifact_release_candidate_path_value = str(artifact_release_candidate_path)
    source_artifact_summary = build_local_lab_source_artifact_summary(
        str(edge_output_path)
    )
    atomic_write_json(
        artifact_source_summary_path,
        source_artifact_summary.model_dump(mode="json"),
        indent=2,
    )
    artifact_source_summary_path_value = str(artifact_source_summary_path)
    release_gate_summary = build_local_lab_release_gate_summary(artifact_release_candidate)
    atomic_write_json(
        artifact_release_gate_summary_path,
        release_gate_summary.model_dump(mode="json"),
        indent=2,
    )
    artifact_release_gate_summary_path_value = str(artifact_release_gate_summary_path)

    artifact_upload_bridge_candidate, upload_build_context = build_local_lab_artifact_upload_dry_run_bridge(
        release_candidate=artifact_release_candidate,
        proof_summary=artifact_proof_summary_for_bridge,
        governance_reference_date=_parse_iso_date(args.bridge_governance_reference_date),
        training_end=_parse_iso_date(args.bridge_training_end),
        artifact_class=(
            None
            if args.bridge_artifact_class is None
            else ArtifactClass(args.bridge_artifact_class)
        ),
        artifact_scope=args.bridge_artifact_scope,
        lifecycle_ttl_days=args.bridge_lifecycle_ttl_days,
        rule_half_life_days=args.bridge_rule_half_life_days,
        drift_score_threshold=args.bridge_drift_score_threshold,
        uploaded_by=args.signed_by,
        source_artifact_summary_ref=artifact_source_summary_path_value,
        release_gate_summary_ref=artifact_release_gate_summary_path_value,
    )
    if upload_build_context is not None:
        atomic_write_json(
            artifact_upload_request_path,
            upload_build_context.upload_request.model_dump(mode="json"),
            indent=2,
        )
        atomic_write_json(
            artifact_import_request_path,
            upload_build_context.import_request.model_dump(mode="json"),
            indent=2,
        )
        if upload_build_context.import_decision is not None:
            atomic_write_json(
                artifact_import_decision_path,
                upload_build_context.import_decision.model_dump(mode="json"),
                indent=2,
            )
            artifact_import_decision_path_value = str(artifact_import_decision_path)
        if upload_build_context.upload_decision is not None:
            atomic_write_json(
                artifact_upload_decision_path,
                upload_build_context.upload_decision.model_dump(mode="json"),
                indent=2,
            )
            artifact_upload_decision_path_value = str(artifact_upload_decision_path)
        artifact_upload_request_path_value = str(artifact_upload_request_path)
        artifact_import_request_path_value = str(artifact_import_request_path)
        artifact_upload_bridge_candidate = artifact_upload_bridge_candidate.model_copy(
            update={
                "upload_request_path": artifact_upload_request_path_value,
                "import_request_path": artifact_import_request_path_value,
                "import_decision_path": artifact_import_decision_path_value,
                "upload_decision_path": artifact_upload_decision_path_value,
            }
        )
    atomic_write_json(
        artifact_import_dry_run_bridge_path,
        artifact_upload_bridge_candidate.model_dump(mode="json"),
        indent=2,
    )
    artifact_import_dry_run_bridge_path_value = str(artifact_import_dry_run_bridge_path)
    if artifact_release_candidate.release_scopes:
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
                shared_release_gate_summary_path=artifact_release_gate_summary_path_value,
                shared_source_artifact_summary_path=artifact_source_summary_path_value,
                shared_artifact_import_dry_run_bridge_path=artifact_import_dry_run_bridge_path_value,
            )
            atomic_write_json(
                scope_summary_path,
                scope_summary.model_dump(mode="json"),
                indent=2,
            )
            release_scope_summary_paths_list.append(str(scope_summary_path))
            updated_release_scopes.append(
                scope.model_copy(update={"release_scope_summary_path": str(scope_summary_path)})
            )
        artifact_release_candidate = artifact_release_candidate.model_copy(
            update={"release_scopes": tuple(updated_release_scopes)}
        )
        atomic_write_json(
            artifact_release_candidate_path,
            artifact_release_candidate.model_dump(mode="json"),
            indent=2,
        )
        release_scope_summary_paths = tuple(release_scope_summary_paths_list)
    if scope_matrix is not None and artifact_release_candidate.release_scopes:
        release_scope_by_slug = {
            scope.scope_slug: scope for scope in artifact_release_candidate.release_scopes
        }
        updated_scope_rows = []
        for row in scope_matrix.scopes:
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
        scope_matrix = build_local_lab_scope_matrix(
            correlation_id=scope_matrix.correlation_id,
            export_dir=scope_matrix.export_dir,
            baseline_export_dir=scope_matrix.baseline_export_dir,
            scopes=tuple(updated_scope_rows),
        )
        atomic_write_json(scope_matrix_path, scope_matrix.model_dump(mode="json"), indent=2)
        scope_matrix_path_value = str(scope_matrix_path)
        scope_count = scope_matrix.scope_count
        scope_ready_count = scope_matrix.ready_scope_count
        scope_blocked_count = scope_matrix.blocked_scope_count
        release_scope_ready_count = scope_matrix.release_ready_scope_count
        release_scope_blocked_count = scope_matrix.release_blocked_scope_count
    promotion_readiness_summary = build_local_lab_promotion_readiness_summary(
        release_candidate=artifact_release_candidate,
        dry_run_bridge=artifact_upload_bridge_candidate,
    )
    atomic_write_json(
        artifact_promotion_readiness_summary_path,
        promotion_readiness_summary.model_dump(mode="json"),
        indent=2,
    )
    artifact_promotion_readiness_summary_path_value = str(
        artifact_promotion_readiness_summary_path
    )
    local_lab_monitoring_projection = build_local_lab_monitoring_projection(
        correlation_id=args.correlation_id,
        run_id=discovery.run_manifest.run_id,
        export_dir=str(discovery.export_dir),
        dataset_manifest_id=discovery.run_manifest.dataset_manifest_id,
        artifact_id=args.artifact_id,
        selected_pair=summary_selected_pair,
        selected_engine_id=summary_selected_engine_id,
        review_ready=review_ready,
        trade_loss_attribution_ready=trade_loss_attribution_ready,
        walk_forward_review_ready=walk_forward_review_summary.walk_forward_pass,
        artifact_ablation_ready=artifact_ablation_ready,
        artifact_proof_ready=artifact_proof_ready,
        edge_calibration_ready=edge_input_summary.get("record_count", 0) > 0,
        scope_count=scope_count,
        scope_ready_count=scope_ready_count,
        scope_blocked_count=scope_blocked_count,
        release_scope_ready_count=release_scope_ready_count,
        release_scope_blocked_count=release_scope_blocked_count,
        release_candidate=artifact_release_candidate,
        dry_run_bridge=artifact_upload_bridge_candidate,
        promotion_readiness=promotion_readiness_summary,
        scope_matrix_path=scope_matrix_path_value,
        artifact_release_candidate_path=artifact_release_candidate_path_value,
        artifact_import_dry_run_bridge_path=artifact_import_dry_run_bridge_path_value,
        artifact_promotion_readiness_summary_path=artifact_promotion_readiness_summary_path_value,
    )
    atomic_write_json(
        local_lab_monitoring_projection_path,
        local_lab_monitoring_projection.model_dump(mode="json"),
        indent=2,
    )
    local_lab_monitoring_projection_path_value = str(local_lab_monitoring_projection_path)
    local_lab_observability_export = build_local_lab_observability_export(
        projection=local_lab_monitoring_projection,
        profile=discovery.run_manifest.profile_scope,
        runtime_mode=discovery.run_manifest.runtime_mode,
        timestamp_ms=discovery.run_manifest.end_timestamp_ms,
    )
    atomic_write_json(
        local_lab_observability_export_path,
        local_lab_observability_export.model_dump(mode="json"),
        indent=2,
    )
    local_lab_observability_export_path_value = str(local_lab_observability_export_path)
    write_observability_text_payload(
        local_lab_observability_export,
        local_lab_observability_text_path,
    )
    local_lab_observability_text_path_value = str(local_lab_observability_text_path)
    local_lab_monitoring_backend_payload = build_local_lab_monitoring_backend_payload(
        projection=local_lab_monitoring_projection,
        observability_export=local_lab_observability_export,
        observability_export_ref=local_lab_observability_export_path_value,
    )
    atomic_write_json(
        local_lab_monitoring_backend_payload_path,
        local_lab_monitoring_backend_payload.model_dump(mode="json"),
        indent=2,
    )
    local_lab_monitoring_backend_payload_path_value = str(local_lab_monitoring_backend_payload_path)
    local_lab_monitoring_ingestion_summary = build_local_lab_monitoring_ingestion_summary(
        backend_payload=local_lab_monitoring_backend_payload,
        observability_export=local_lab_observability_export,
        backend_payload_ref=local_lab_monitoring_backend_payload_path_value,
        observability_export_ref=local_lab_observability_export_path_value,
    )
    atomic_write_json(
        local_lab_monitoring_ingestion_summary_path,
        local_lab_monitoring_ingestion_summary.model_dump(mode="json"),
        indent=2,
    )
    local_lab_monitoring_ingestion_summary_path_value = str(
        local_lab_monitoring_ingestion_summary_path
    )

    summary = LocalLabAnalysisBundleSummary(
        correlation_id=args.correlation_id,
        export_dir=str(discovery.export_dir),
        run_id=discovery.run_manifest.run_id,
        artifact_hash=discovery.run_manifest.artifact_hash,
        dataset_manifest_id=discovery.run_manifest.dataset_manifest_id,
        profile_scope=discovery.run_manifest.profile_scope.value,
        runtime_mode=discovery.run_manifest.runtime_mode.value,
        strategy_id=discovery.run_manifest.strategy_id,
        strategy_version=discovery.run_manifest.strategy_version,
        lineage_version=discovery.run_manifest.lineage_version,
        tested_pairs=discovery.run_manifest.tested_pairs,
        engine_scope=discovery.run_manifest.engine_scope,
        selected_pair=summary_selected_pair,
        selected_engine_id=summary_selected_engine_id,
        scope_matrix_path=scope_matrix_path_value,
        scope_count=scope_count,
        scope_ready_count=scope_ready_count,
        scope_blocked_count=scope_blocked_count,
        release_scope_ready_count=release_scope_ready_count,
        release_scope_blocked_count=release_scope_blocked_count,
        artifact_ablation_study_path=artifact_ablation_study_path_value,
        review_output_dir=review_output_dir_value,
        review_bundle_path=review_bundle_path_value,
        review_projection_path=review_projection_path_value,
        trade_loss_attribution_path=trade_loss_attribution_path_value,
        review_input_summary_path=review_input_summary_path_value,
        walk_forward_review_template_path=str(walk_forward_review_template_path),
        walk_forward_review_path=walk_forward_review_path,
        walk_forward_review_summary_path=str(walk_forward_review_summary_path),
        artifact_proof_summary_path=artifact_proof_summary_path_value,
        artifact_proof_assessment_path=artifact_proof_assessment_path_value,
        artifact_release_candidate_path=artifact_release_candidate_path_value,
        local_lab_recalibration_plan_path=local_lab_recalibration_plan_path_value,
        artifact_import_dry_run_bridge_path=artifact_import_dry_run_bridge_path_value,
        artifact_source_summary_path=artifact_source_summary_path_value,
        artifact_release_gate_summary_path=artifact_release_gate_summary_path_value,
        artifact_promotion_readiness_summary_path=artifact_promotion_readiness_summary_path_value,
        local_lab_monitoring_projection_path=local_lab_monitoring_projection_path_value,
        local_lab_observability_export_path=local_lab_observability_export_path_value,
        local_lab_observability_text_path=local_lab_observability_text_path_value,
        local_lab_monitoring_backend_payload_path=local_lab_monitoring_backend_payload_path_value,
        local_lab_monitoring_ingestion_summary_path=local_lab_monitoring_ingestion_summary_path_value,
        artifact_upload_request_path=artifact_upload_request_path_value,
        artifact_import_request_path=artifact_import_request_path_value,
        artifact_import_decision_path=artifact_import_decision_path_value,
        artifact_upload_decision_path=artifact_upload_decision_path_value,
        edge_output_path=str(edge_output_path),
        edge_input_summary_path=str(edge_input_summary_path),
        review_ready=review_ready,
        trade_loss_attribution_ready=trade_loss_attribution_ready,
        walk_forward_review_ready=walk_forward_review_summary.walk_forward_pass,
        artifact_ablation_ready=artifact_ablation_ready,
        artifact_proof_ready=artifact_proof_ready,
        artifact_proof_validation_reasons=artifact_proof_validation_reasons,
        release_ready_for_shadow=artifact_release_candidate.ready_for_shadow_import,
        release_status=artifact_release_candidate.release_status,
        release_blocking_reasons=artifact_release_candidate.blocking_reasons,
        release_ready_scope_slugs=tuple(
            scope.scope_slug for scope in artifact_release_candidate.release_scopes if scope.release_ready
        ),
        release_blocked_scope_slugs=tuple(
            scope.scope_slug for scope in artifact_release_candidate.release_scopes if not scope.release_ready
        ),
        release_scope_summary_count=len(release_scope_summary_paths),
        release_scope_summary_paths=release_scope_summary_paths,
        promotion_readiness_status=promotion_readiness_summary.readiness_status,
        promotion_activation_stage=promotion_readiness_summary.activation_stage.value,
        promotion_normalized_state=promotion_readiness_summary.normalized_promotion_state.value,
        promotion_review_state=promotion_readiness_summary.review_state.value,
        monitoring_projection_status=local_lab_monitoring_projection.status,
        monitoring_projection_detail=local_lab_monitoring_projection.detail,
        local_lab_observability_sample_count=len(local_lab_observability_export.samples),
        local_lab_monitoring_backend_status=local_lab_monitoring_backend_payload.status,
        local_lab_monitoring_ingestion_ready=local_lab_monitoring_ingestion_summary.ingestion_ready,
        recalibration_candidate_ready=local_lab_recalibration_plan.calibration_candidate_ready,
        recalibration_blocking_reasons=local_lab_recalibration_plan.blocking_reasons,
        recalibration_action_count=local_lab_recalibration_plan.action_count,
        bridge_ready_for_shadow_dry_run=artifact_upload_bridge_candidate.ready_for_shadow_import_dry_run,
        bridge_status=artifact_upload_bridge_candidate.bridge_status,
        bridge_blocking_reasons=artifact_upload_bridge_candidate.blocking_reasons,
        bridge_release_gate_status=artifact_upload_bridge_candidate.release_gate_status,
        bridge_release_gate_reasons=artifact_upload_bridge_candidate.release_gate_reasons,
        bridge_semantic_status=artifact_upload_bridge_candidate.semantic_status,
        bridge_semantic_reasons=artifact_upload_bridge_candidate.semantic_reasons,
        bridge_transport_payload_ref_count=artifact_upload_bridge_candidate.transport_payload_ref_count,
        bridge_transport_supplementary_refs=artifact_upload_bridge_candidate.transport_supplementary_refs,
        edge_calibration_ready=edge_input_summary.get("record_count", 0) > 0,
    )
    atomic_write_json(summary_path, summary.model_dump(mode="json"), indent=2)

    print(f"Local IA Lab analysis summary JSON: {summary_path}")
    if review_output_dir_value is not None:
        print(f"Post-trade review dir: {review_output_dir_value}")
    if scope_matrix_path_value is not None:
        print(f"Local IA Lab scope matrix JSON: {scope_matrix_path_value}")
    if artifact_ablation_study_path_value is not None:
        print(f"Artifact ablation study JSON: {artifact_ablation_study_path_value}")
    if artifact_proof_summary_path_value is not None:
        print(f"Artifact proof summary JSON: {artifact_proof_summary_path_value}")
    if artifact_proof_assessment_path_value is not None:
        print(f"Artifact proof assessment JSON: {artifact_proof_assessment_path_value}")
    print(f"Artifact release candidate JSON: {artifact_release_candidate_path_value}")
    print(f"Local IA Lab recalibration plan JSON: {local_lab_recalibration_plan_path_value}")
    print(f"Artifact import dry-run bridge JSON: {artifact_import_dry_run_bridge_path_value}")
    print(f"Artifact promotion readiness summary JSON: {artifact_promotion_readiness_summary_path_value}")
    print(f"Local IA Lab monitoring projection JSON: {local_lab_monitoring_projection_path_value}")
    print(f"Local IA Lab observability export JSON: {local_lab_observability_export_path_value}")
    print(f"Local IA Lab observability text export: {local_lab_observability_text_path_value}")
    print(f"Local IA Lab monitoring backend payload JSON: {local_lab_monitoring_backend_payload_path_value}")
    print(f"Local IA Lab monitoring ingestion summary JSON: {local_lab_monitoring_ingestion_summary_path_value}")
    print(f"EDGE calibration artifact: {edge_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
