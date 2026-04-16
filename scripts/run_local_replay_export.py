#!/usr/bin/env python3
"""Generate a governed LOCAL_REPLAY export artifact directory."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from interface_contracts import ProfileId, StrategyClassification  # noqa: E402
from local_replay_runtime import (  # noqa: E402
    EdgeGateCalibrationConfig,
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
    HistoricalSnapshotBatch,
    ReplayInputKind,
    build_edge_gate_calibration_artifact,
    calibrate_edge_gate_thresholds,
    load_replay_dtr_records,
    load_historical_replay_dataset,
    load_historical_snapshot_batch,
    orchestrate_local_replay_export,
    ReplayOrchestratorRequest,
    route_snapshot_batch_to_dataset,
    write_edge_gate_calibration_artifact,
)


def _configure_stdio() -> None:
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")
    stderr = getattr(sys, "stderr", None)
    if stderr is not None and hasattr(stderr, "reconfigure"):
        stderr.reconfigure(encoding="utf-8", errors="replace")


def _timestamp_id() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")


def _build_demo_dataset(
    *,
    run_id: str,
    dataset_id: str,
) -> HistoricalReplayDataset:
    return HistoricalReplayDataset.from_records(
        dataset_id=dataset_id,
        source_path=f"inmemory://{run_id}",
        source="demo_local_dataset",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id=f"{run_id}:opportunity:1",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                close_price=43_250.0,
                raw_score=0.91,
                penalized_score=0.88,
                final_score=0.86,
                expected_edge_bps=17.0,
                spread_bps=3.0,
                slippage_bps=4.0,
                latency_penalty_bps=1.0,
                fill_ratio=1.0,
                target_decision_state="executed",
                production_decision_state="executed",
                production_final_score=0.86,
                production_expected_cost=0.00086,
                candidate_size=1.0,
                final_size=1.0,
                tier="core",
                gross_return_bps=21.0,
                feature_values={
                    "mid_return_1m": 0.0042,
                    "imbalance": 0.11,
                    "spread_bps": 3.0,
                },
            ),
            HistoricalReplayOpportunity(
                opportunity_id=f"{run_id}:opportunity:2",
                timestamp_ms=1_700_000_060_000,
                pair="ETHUSDT",
                engine_id="engine_b",
                close_price=2_280.0,
                raw_score=0.81,
                penalized_score=0.79,
                final_score=0.76,
                expected_edge_bps=7.0,
                spread_bps=5.0,
                slippage_bps=3.0,
                latency_penalty_bps=1.0,
                fill_ratio=0.0,
                target_decision_state="rejected_ranking",
                production_decision_state="rejected_ranking",
                production_final_score=0.76,
                production_expected_cost=0.00094,
                ranking_position=3,
                gross_return_bps=-4.0,
                primary_reason="rank_cutoff",
                feature_values={
                    "mid_return_1m": 0.0021,
                    "imbalance": -0.06,
                    "spread_bps": 5.0,
                },
            ),
            HistoricalReplayOpportunity(
                opportunity_id=f"{run_id}:opportunity:3",
                timestamp_ms=1_700_000_120_000,
                pair="SOLUSDT",
                engine_id="engine_a",
                close_price=142.0,
                raw_score=0.43,
                penalized_score=0.18,
                final_score=0.12,
                expected_edge_bps=2.0,
                spread_bps=9.0,
                slippage_bps=4.0,
                latency_penalty_bps=2.0,
                fill_ratio=0.0,
                target_decision_state="hard_blocked",
                production_decision_state="hard_blocked",
                production_final_score=0.12,
                production_expected_cost=0.00156,
                hard_block_reasons=("ce_negative",),
                primary_reason="ce_negative",
                feature_values={
                    "mid_return_1m": -0.0015,
                    "imbalance": -0.22,
                    "spread_bps": 9.0,
                },
            ),
        ),
    )


def _load_input_dataset(
    *,
    parser: argparse.ArgumentParser,
    run_id: str,
    dataset_path: Path | None,
    snapshot_path: Path | None,
) -> tuple[HistoricalReplayDataset, ReplayInputKind]:
    if dataset_path is not None and snapshot_path is not None:
        parser.error("Use either --dataset-path or --snapshot-path, not both.")
    if snapshot_path is not None:
        snapshot_batch: HistoricalSnapshotBatch = load_historical_snapshot_batch(snapshot_path)
        return (
            route_snapshot_batch_to_dataset(
                snapshot_batch,
                dataset_id=snapshot_path.resolve().stem.replace(" ", "_"),
            ),
            "historical_snapshot_batch",
        )
    if dataset_path is not None:
        return load_historical_replay_dataset(dataset_path), "historical_dataset"
    return (
        _build_demo_dataset(
            run_id=run_id,
            dataset_id=f"dataset-{run_id}",
        ),
        "demo_dataset",
    )


def _parse_chunk_indices(raw_value: str) -> tuple[int, ...]:
    values: set[int] = set()
    for part in raw_value.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            start_str, end_str = token.split("-", 1)
            start = int(start_str.strip())
            end = int(end_str.strip())
            if end < start:
                raise ValueError("chunk range end must stay >= start")
            values.update(range(start, end + 1))
            continue
        values.add(int(token))
    if not values:
        raise ValueError("chunk indices selection cannot be empty")
    return tuple(sorted(values))


def _option_was_provided(argv: list[str], option: str) -> bool:
    return any(token == option or token.startswith(f"{option}=") for token in argv)


def _load_existing_resume_metadata(output_dir: Path) -> tuple[dict[str, object], dict[str, object]] | None:
    session_config_path = output_dir / "replay_session_config.json"
    run_manifest_path = output_dir / "replay_run_manifest.json"
    if not session_config_path.exists() or not run_manifest_path.exists():
        return None
    session_config = json.loads(session_config_path.read_text(encoding="utf-8"))
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    return session_config, run_manifest


def _emit_edge_calibration(
    *,
    replay_dtr_path: Path,
    output_path: Path,
    signed_by: str,
    calibration_version: str,
    bootstrap_samples: int,
    min_positive_trades: int,
    min_cost_observations: int,
    rng_seed: int,
) -> Path:
    records = load_replay_dtr_records(replay_dtr_path)
    config = EdgeGateCalibrationConfig(
        calibration_version=calibration_version,
        bootstrap_samples=bootstrap_samples,
        min_positive_trades=min_positive_trades,
        min_cost_observations=min_cost_observations,
        rng_seed=rng_seed,
    )
    report = calibrate_edge_gate_thresholds(records, config=config)
    artifact = build_edge_gate_calibration_artifact(
        report,
        signed_by=signed_by,
        config=config,
    )
    return write_edge_gate_calibration_artifact(artifact, output_path)


def _hydrate_resume_defaults(
    args: argparse.Namespace,
    *,
    raw_argv: list[str],
) -> argparse.Namespace:
    if not args.resume:
        return args
    metadata = _load_existing_resume_metadata(args.output_dir)
    if metadata is None:
        return args
    session_config, run_manifest = metadata

    if not _option_was_provided(raw_argv, "--run-id"):
        args.run_id = str(session_config["run_id"])
    if not _option_was_provided(raw_argv, "--strategy-id"):
        args.strategy_id = str(session_config["strategy_id"])
    if not _option_was_provided(raw_argv, "--strategy-version"):
        args.strategy_version = str(session_config["strategy_version"])
    if not _option_was_provided(raw_argv, "--strategy-classification"):
        args.strategy_classification = str(run_manifest["strategy_classification"])
    if not _option_was_provided(raw_argv, "--lineage-version"):
        args.lineage_version = str(session_config["lineage_version"])
    if not _option_was_provided(raw_argv, "--performance-mode"):
        args.performance_mode = str(session_config["performance_mode"])
    if not _option_was_provided(raw_argv, "--profile-scope"):
        args.profile_scope = str(session_config["profile_scope"])
    if not _option_was_provided(raw_argv, "--chunk-count"):
        args.chunk_count = int(session_config["chunk_count"])
    if not _option_was_provided(raw_argv, "--chunk-index"):
        args.chunk_index = int(session_config["chunk_index"])
    return args


def _emit_output_lines(lines: tuple[str, ...]) -> None:
    if not lines:
        return
    sys.stdout.write("\n".join(lines) + "\n")


def _add_replay_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "build" / "local_replay_export",
        help="Directory where the governed export artifact will be written.",
    )
    parser.add_argument(
        "--run-id",
        default=f"run-local-replay-export-{_timestamp_id()}",
        help="Stable run identifier recorded in the replay_run_manifest.",
    )
    parser.add_argument(
        "--dataset-path",
        type=Path,
        default=None,
        help=(
            "Optional path to a historical dataset (.json, .jsonl, .csv). "
            "When omitted, the launcher uses a governed demo dataset."
        ),
    )
    parser.add_argument(
        "--snapshot-path",
        type=Path,
        default=None,
        help=(
            "Optional path to a raw historical snapshot batch (.json, .jsonl, .csv). "
            "The launcher will route it into normalized replay opportunities."
        ),
    )
    parser.add_argument(
        "--strategy-id",
        default="strategy-a-demo",
        help="Strategy identifier recorded in the replay_run_manifest.",
    )
    parser.add_argument(
        "--strategy-classification",
        choices=tuple(item.value for item in StrategyClassification),
        default=StrategyClassification.A_VARIANT.value,
        help="Canonical strategy classification recorded in the replay_run_manifest.",
    )
    parser.add_argument(
        "--strategy-version",
        default="a.v1.0",
        help="Strategy version recorded in the replay_run_manifest.",
    )
    parser.add_argument(
        "--lineage-version",
        default="a.v1.0.r1",
        help="Lineage version recorded in the replay_run_manifest.",
    )
    parser.add_argument(
        "--performance-mode",
        choices=("shadow_fidelity_mode", "research_fast_mode"),
        default="research_fast_mode",
        help="Performance mode recorded in the replay_run_manifest.",
    )
    parser.add_argument(
        "--profile-scope",
        choices=tuple(profile.value for profile in ProfileId),
        default=ProfileId.COMPLETE.value,
        help=(
            "Profile scope recorded in the replay_run_manifest. "
            "Default stays COMPLETE to align the governed IA Lab -> VPS import chain."
        ),
    )
    parser.add_argument(
        "--chunk-count",
        type=int,
        default=1,
        help="Optional temporal chunk count recorded in replay_session_config.",
    )
    parser.add_argument(
        "--chunk-index",
        type=int,
        default=1,
        help="Optional 1-based chunk index recorded in replay_session_config.",
    )
    parser.add_argument(
        "--chunk-indices",
        default="",
        help='Optional explicit chunk selection for --run-all-chunks, for example "1,3,5-7".',
    )
    parser.add_argument(
        "--window-start-ms",
        type=int,
        default=None,
        help="Optional inclusive replay window start timestamp in milliseconds.",
    )
    parser.add_argument(
        "--window-end-ms",
        type=int,
        default=None,
        help="Optional inclusive replay window end timestamp in milliseconds.",
    )
    parser.add_argument(
        "--rewind-requested",
        action="store_true",
        help="Record that this replay session was launched with rewind semantics.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a previously completed LOCAL_REPLAY export from persisted session state.",
    )
    parser.add_argument(
        "--run-all-chunks",
        action="store_true",
        help=(
            "Run every chunk of the governed LOCAL_REPLAY session, aggregate the chunk outputs, "
            "and write a canonical root export consumable by run_local_replay_shadow.py."
        ),
    )


def _add_edge_calibration_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--emit-edge-calibration",
        action="store_true",
        help="Also emit a signed THR-E01/THR-E02 artifact from replay_dtr evidence.",
    )
    parser.add_argument(
        "--edge-calibration-output-path",
        type=Path,
        default=None,
        help=(
            "Optional YAML path for the EDGE calibration artifact. "
            "Defaults to <output-dir>/calibration/edge_gate.yml when --emit-edge-calibration is used."
        ),
    )
    parser.add_argument(
        "--edge-calibration-signed-by",
        default="",
        help="Human attestation identity used when --emit-edge-calibration is enabled.",
    )
    parser.add_argument("--edge-calibration-version", default="v1")
    parser.add_argument("--edge-bootstrap-samples", type=int, default=2_000)
    parser.add_argument("--edge-min-positive-trades", type=int, default=200)
    parser.add_argument("--edge-min-cost-observations", type=int, default=500)
    parser.add_argument("--edge-rng-seed", type=int, default=53)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a governed LOCAL_REPLAY export artifact directory.",
    )
    _add_replay_arguments(parser)
    _add_edge_calibration_arguments(parser)
    return parser


def _parse_main_args(
    argv: list[str] | None,
) -> tuple[argparse.ArgumentParser, argparse.Namespace, tuple[int, ...]]:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args = parser.parse_args(raw_argv)
    args = _hydrate_resume_defaults(args, raw_argv=raw_argv)
    if args.emit_edge_calibration and not args.edge_calibration_signed_by.strip():
        parser.error(
            "--edge-calibration-signed-by is required when --emit-edge-calibration is enabled"
        )
    try:
        selected_chunk_indices = (
            _parse_chunk_indices(args.chunk_indices)
            if args.chunk_indices.strip()
            else ()
        )
    except ValueError as exc:
        parser.error(str(exc))
    return parser, args, selected_chunk_indices


def _load_requested_dataset(
    *,
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> tuple[HistoricalReplayDataset | None, ReplayInputKind | None]:
    if (
        args.run_all_chunks
        or not args.resume
        or args.dataset_path is not None
        or args.snapshot_path is not None
    ):
        return _load_input_dataset(
            parser=parser,
            run_id=args.run_id,
            dataset_path=args.dataset_path,
            snapshot_path=args.snapshot_path,
        )
    return None, None


def _build_replay_request(
    *,
    args: argparse.Namespace,
    dataset: HistoricalReplayDataset | None,
    input_kind: ReplayInputKind | None,
    selected_chunk_indices: tuple[int, ...],
) -> ReplayOrchestratorRequest:
    return ReplayOrchestratorRequest(
        output_dir=args.output_dir,
        run_id=args.run_id,
        strategy_id=args.strategy_id,
        strategy_version=args.strategy_version,
        strategy_classification=StrategyClassification(args.strategy_classification),
        lineage_version=args.lineage_version,
        performance_mode=args.performance_mode,
        profile_scope=ProfileId(args.profile_scope),
        input_kind=input_kind,
        dataset=dataset,
        chunk_count=args.chunk_count,
        chunk_index=args.chunk_index,
        selected_chunk_indices=selected_chunk_indices,
        window_start_ms=args.window_start_ms,
        window_end_ms=args.window_end_ms,
        rewind_requested=args.rewind_requested,
        resume=args.resume,
        run_all_chunks=args.run_all_chunks,
    )


def _resume_status_lines(result: object) -> tuple[str, ...]:
    if not getattr(result, "resumed", False):
        return ()
    completed_chunk_indices = tuple(getattr(result, "completed_chunk_indices", ()) or ())
    resumed_chunk_indices = tuple(getattr(result, "resumed_chunk_indices", ()) or ())
    if completed_chunk_indices and resumed_chunk_indices:
        if resumed_chunk_indices == completed_chunk_indices:
            return ("Replay orchestrator resumed a fully completed multi-chunk export.",)
        resumed_chunks = ", ".join(str(index) for index in resumed_chunk_indices)
        return (
            "Replay orchestrator resumed completed chunks "
            f"{resumed_chunks} and rebuilt the missing chunks.",
        )
    return ("Replay orchestrator resumed a previously completed export.",)


def _export_output_lines(
    result: object,
    *,
    args: argparse.Namespace,
) -> tuple[str, ...]:
    export_result = result.export_result.export_result
    lines = list(_resume_status_lines(result))
    lines.extend(
        (
            f"Replay session config JSON: {result.session_config_path}",
            f"Replay session state JSON: {result.session_state_path}",
            f"Performance mode guard JSON: {result.performance_mode_guard_path}",
            f"Run consistency guard JSON: {result.run_consistency_guard_path}",
            f"Run manifest JSON: {export_result.run_manifest_path}",
            f"Review export Markdown: {export_result.review_export_path}",
            f"Feature bridge JSON: {export_result.feature_bridge_path}",
            f"Parity diagnostics JSON: {export_result.parity_diagnostics_path}",
            f"Replay metrics JSON: {export_result.replay_metrics_path}",
            f"Replay DTR JSONL: {export_result.replay_dtr_path}",
        )
    )
    if args.emit_edge_calibration:
        output_path = args.edge_calibration_output_path or (
            args.output_dir / "calibration" / "edge_gate.yml"
        )
        written_calibration_path = _emit_edge_calibration(
            replay_dtr_path=export_result.replay_dtr_path,
            output_path=output_path,
            signed_by=args.edge_calibration_signed_by.strip(),
            calibration_version=args.edge_calibration_version,
            bootstrap_samples=args.edge_bootstrap_samples,
            min_positive_trades=args.edge_min_positive_trades,
            min_cost_observations=args.edge_min_cost_observations,
            rng_seed=args.edge_rng_seed,
        )
        lines.append(f"EDGE calibration YAML: {written_calibration_path}")
    if result.chunk_session_path is not None:
        lines.append(f"Replay chunk session JSON: {result.chunk_session_path}")
    lines.append("Use this directory as --export-dir for run_local_replay_shadow.py.")
    return tuple(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the governed LOCAL_REPLAY export generator."""

    _configure_stdio()
    parser, args, selected_chunk_indices = _parse_main_args(argv)
    dataset, input_kind = _load_requested_dataset(parser=parser, args=args)

    result = orchestrate_local_replay_export(
        _build_replay_request(
            args=args,
            dataset=dataset,
            input_kind=input_kind,
            selected_chunk_indices=selected_chunk_indices,
        )
    )
    _emit_output_lines(_export_output_lines(result, args=args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
