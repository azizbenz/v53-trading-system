#!/usr/bin/env python3
"""Generate a governed LOCAL_REPLAY export artifact directory."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from interface_contracts import StrategyClassification  # noqa: E402
from local_replay_runtime import (  # noqa: E402
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
    HistoricalSnapshotBatch,
    ReplayInputKind,
    load_historical_replay_dataset,
    load_historical_snapshot_batch,
    orchestrate_local_replay_export,
    ReplayOrchestratorRequest,
    route_snapshot_batch_to_dataset,
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


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the governed LOCAL_REPLAY export generator."""

    _configure_stdio()
    parser = argparse.ArgumentParser(
        description="Generate a governed LOCAL_REPLAY export artifact directory.",
    )
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
        help=(
            "Optional explicit chunk selection for --run-all-chunks, for example "
            "\"1,3,5-7\"."
        ),
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
    args = parser.parse_args(argv)
    try:
        selected_chunk_indices = (
            _parse_chunk_indices(args.chunk_indices)
            if args.chunk_indices.strip()
            else ()
        )
    except ValueError as exc:
        parser.error(str(exc))

    dataset: HistoricalReplayDataset | None = None
    input_kind: ReplayInputKind | None = None
    if (
        args.run_all_chunks
        or not args.resume
        or args.dataset_path is not None
        or args.snapshot_path is not None
    ):
        dataset, input_kind = _load_input_dataset(
            parser=parser,
            run_id=args.run_id,
            dataset_path=args.dataset_path,
            snapshot_path=args.snapshot_path,
        )
    result = orchestrate_local_replay_export(
        ReplayOrchestratorRequest(
            output_dir=args.output_dir,
            run_id=args.run_id,
            strategy_id=args.strategy_id,
            strategy_version=args.strategy_version,
            strategy_classification=StrategyClassification(args.strategy_classification),
            lineage_version=args.lineage_version,
            performance_mode=args.performance_mode,
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
    )
    if result.resumed:
        if result.completed_chunk_indices and result.resumed_chunk_indices:
            if result.resumed_chunk_indices == result.completed_chunk_indices:
                print("Replay orchestrator resumed a fully completed multi-chunk export.")
            else:
                resumed_chunks = ", ".join(str(index) for index in result.resumed_chunk_indices)
                print(
                    "Replay orchestrator resumed completed chunks "
                    f"{resumed_chunks} and rebuilt the missing chunks."
                )
        else:
            print("Replay orchestrator resumed a previously completed export.")
    export_result = result.export_result.export_result
    print(f"Replay session config JSON: {result.session_config_path}")
    print(f"Replay session state JSON: {result.session_state_path}")
    print(f"Performance mode guard JSON: {result.performance_mode_guard_path}")
    print(f"Run consistency guard JSON: {result.run_consistency_guard_path}")
    print(f"Run manifest JSON: {export_result.run_manifest_path}")
    print(f"Review export Markdown: {export_result.review_export_path}")
    print(f"Feature bridge JSON: {export_result.feature_bridge_path}")
    print(f"Parity diagnostics JSON: {export_result.parity_diagnostics_path}")
    print(f"Replay metrics JSON: {export_result.replay_metrics_path}")
    print(f"Replay DTR JSONL: {export_result.replay_dtr_path}")
    if result.chunk_session_path is not None:
        print(f"Replay chunk session JSON: {result.chunk_session_path}")
    print("Use this directory as --export-dir for run_local_replay_shadow.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
