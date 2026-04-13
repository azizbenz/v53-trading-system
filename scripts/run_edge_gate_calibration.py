#!/usr/bin/env python3
"""Build a Local IA Lab EDGE calibration artifact from governed replay DTR exports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from backtest_artifact_import.export_dir_bridge import discover_local_replay_export  # noqa: E402
from interface_contracts.atomic_io import atomic_write_json  # noqa: E402
from local_replay_runtime import (  # noqa: E402
    EdgeGateCalibrationConfig,
    LocalLabRecalibrationPlan,
    build_edge_gate_calibration_artifact,
    calibrate_edge_gate_thresholds,
    load_replay_dtr_records,
    write_edge_gate_calibration_artifact,
)


class EdgeCalibrationInputSummary(BaseModel, frozen=True):
    """Future-facing audit summary for Local IA Lab EDGE calibration inputs."""

    source_kind: str = Field(..., min_length=1)
    replay_dtr_ref: str = Field(..., min_length=1)
    export_dir: str | None = None
    run_id: str | None = None
    artifact_hash: str | None = None
    dataset_manifest_id: str | None = None
    profile_scope: str | None = None
    runtime_mode: str | None = None
    strategy_id: str | None = None
    strategy_version: str | None = None
    lineage_version: str | None = None
    tested_pairs: tuple[str, ...] = ()
    engine_scope: tuple[str, ...] = ()
    feature_set_version: str | None = None
    transform_set_version: str | None = None
    replay_metrics_ref: str | None = None
    replay_diagnostics_ref: str | None = None
    recalibration_plan_ref: str | None = None
    recalibration_candidate_ready: bool = False
    recalibration_blocking_reasons: tuple[str, ...] = ()
    recalibration_recommended_threshold_ids: tuple[str, ...] = ()
    record_count: int = Field(..., ge=0)
    calibration_version: str = Field(..., min_length=1)
    artifact_id: str = Field(..., min_length=1)


def _configure_stdio() -> None:
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")
    stderr = getattr(sys, "stderr", None)
    if stderr is not None and hasattr(stderr, "reconfigure"):
        stderr.reconfigure(encoding="utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate THR-E01/THR-E02 from governed replay DTR evidence.",
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--replay-dtr-path",
        type=Path,
        help="Path to governed replay_dtr.json or replay_dtr.jsonl.",
    )
    source_group.add_argument(
        "--export-dir",
        type=Path,
        help="Path to a governed LOCAL_REPLAY export directory containing replay sidecars.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=REPO_ROOT / "build" / "calibration" / "edge_gate.yml",
        help="YAML path where the signed EDGE calibration artifact will be written.",
    )
    parser.add_argument(
        "--signed-by",
        required=True,
        help="Human attestation identity recorded in the artifact signature.",
    )
    parser.add_argument("--artifact-id", default="edge_gate_thresholds")
    parser.add_argument("--calibration-version", default="v1")
    parser.add_argument("--bootstrap-samples", type=int, default=2_000)
    parser.add_argument("--min-positive-trades", type=int, default=200)
    parser.add_argument("--min-cost-observations", type=int, default=500)
    parser.add_argument("--rng-seed", type=int, default=53)
    parser.add_argument(
        "--recalibration-plan-path",
        type=Path,
        help="Optional Local IA Lab recalibration plan JSON used to document why this EDGE artifact is being refreshed.",
    )
    return parser


def _resolve_calibration_source(
    args: argparse.Namespace,
) -> tuple[tuple, EdgeCalibrationInputSummary]:
    if args.export_dir is not None:
        discovery = discover_local_replay_export(args.export_dir)
        records = load_replay_dtr_records(discovery.payload_bundle.replay_dtr_ref)
        return (
            records,
            EdgeCalibrationInputSummary(
                source_kind="export_dir",
                replay_dtr_ref=discovery.payload_bundle.replay_dtr_ref,
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
                feature_set_version=discovery.run_manifest.feature_set_version,
                transform_set_version=discovery.run_manifest.transform_set_version,
                replay_metrics_ref=discovery.payload_bundle.replay_metrics_ref,
                replay_diagnostics_ref=discovery.payload_bundle.parity_diagnostics_ref,
                record_count=len(records),
                calibration_version=args.calibration_version,
                artifact_id=args.artifact_id,
            ),
        )

    replay_dtr_ref = str(args.replay_dtr_path.resolve())
    records = load_replay_dtr_records(args.replay_dtr_path)
    return (
        records,
        EdgeCalibrationInputSummary(
            source_kind="replay_dtr",
            replay_dtr_ref=replay_dtr_ref,
            record_count=len(records),
            calibration_version=args.calibration_version,
            artifact_id=args.artifact_id,
        ),
    )


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    records, input_summary = _resolve_calibration_source(args)
    if args.recalibration_plan_path is not None:
        recalibration_plan = LocalLabRecalibrationPlan.model_validate_json(
            args.recalibration_plan_path.read_text(encoding="utf-8")
        )
        input_summary = input_summary.model_copy(
            update={
                "recalibration_plan_ref": str(args.recalibration_plan_path.resolve()),
                "recalibration_candidate_ready": recalibration_plan.calibration_candidate_ready,
                "recalibration_blocking_reasons": recalibration_plan.blocking_reasons,
                "recalibration_recommended_threshold_ids": recalibration_plan.recommended_threshold_ids,
            }
        )
    config = EdgeGateCalibrationConfig(
        artifact_id=args.artifact_id,
        calibration_version=args.calibration_version,
        bootstrap_samples=args.bootstrap_samples,
        min_positive_trades=args.min_positive_trades,
        min_cost_observations=args.min_cost_observations,
        rng_seed=args.rng_seed,
    )
    report = calibrate_edge_gate_thresholds(records, config=config)
    artifact = build_edge_gate_calibration_artifact(
        report,
        signed_by=args.signed_by,
        config=config,
    )
    output_path = write_edge_gate_calibration_artifact(artifact, args.output_path)
    report_path = output_path.with_suffix(".report.json")
    atomic_write_json(report_path, report.model_dump(mode="json"), indent=2)
    input_summary_path = output_path.with_suffix(".input_summary.json")
    atomic_write_json(input_summary_path, input_summary.model_dump(mode="json"), indent=2)

    e01 = report.get_threshold(config.edge_multiplier_threshold_id)
    e02 = report.get_threshold(config.min_absolute_edge_threshold_id)
    print(f"EDGE calibration artifact written: {output_path}")
    print(f"EDGE calibration report JSON: {report_path}")
    print(f"Governed input summary JSON: {input_summary_path}")
    print(
        "THR-E01="
        f"{e01.published_value:.6f} multiplier "
        f"(IC95 {e01.ic95_lower:.6f}..{e01.ic95_upper:.6f})"
    )
    print(
        "THR-E02="
        f"{e02.published_value:.6f} bps "
        f"(IC95 {e02.ic95_lower:.6f}..{e02.ic95_upper:.6f})"
    )
    print(
        "sample="
        f"executed:{report.executed_record_count} "
        f"positive:{report.positive_trade_count} "
        f"cost:{report.cost_observation_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
