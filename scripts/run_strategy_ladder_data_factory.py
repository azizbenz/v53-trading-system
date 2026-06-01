"""CLI entrypoint for Patch 6 Strategy Ladder Data Factory."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from data_backbone.feature_timeframes import DEFAULT_GOLD_TIMEFRAMES
from local_replay_runtime.strategy_ladder_expected_edge_feature_contracts import (
    DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
)
from local_replay_runtime.strategy_ladder_data_factory import run_strategy_ladder_data_factory
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderDataFactoryRequest,
)


_COCKPIT_JOB_TERMINAL_SENTINEL_ENV = "COCKPIT_JOB_TERMINAL_SENTINEL_PATH"


def _csv_tuple(raw_value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in (raw_value or "").split(",") if part.strip())


def _raw_roots_tuple(raw_root_list: list[str], raw_roots: str) -> tuple[Path, ...]:
    values = [*raw_root_list, *_csv_tuple(raw_roots)]
    unique = tuple(dict.fromkeys(str(Path(item).resolve()) for item in values if item))
    return tuple(Path(item) for item in unique)


def _write_terminal_sentinel(payload: dict[str, object]) -> None:
    raw_path = os.environ.get(_COCKPIT_JOB_TERMINAL_SENTINEL_ENV, "").strip()
    if not raw_path:
        return
    path = Path(raw_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "written_at": payload.get("written_at"),
                "run_id": payload.get("run_id"),
                "report_root": payload.get("report_root"),
                "data_factory_status": payload.get("data_factory_status"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Patch 6 Strategy Ladder Data Factory.")
    parser.add_argument("--run-id", default="", help="Deterministic run id.")
    parser.add_argument("--raw-root", dest="raw_root_list", action="append", default=[], help="Raw data root. May be repeated.")
    parser.add_argument("--raw-roots", default="", help="Comma-separated raw data roots.")
    parser.add_argument("--raw-source-manifest", default="", help="Optional raw source manifest path.")
    parser.add_argument(
        "--historical-metadata-root",
        default="",
        help="Optional local Bybit historical metadata cache root (symbol_metadata.csv/jsonl).",
    )
    parser.add_argument(
        "--output-root",
        default="",
        help=(
            "Optional explicit output root. When supplied, reports go directly under this "
            "directory and --silver-root / --gold-root default to <output-root>/silver and "
            "<output-root>/gold if not specified."
        ),
    )
    parser.add_argument(
        "--silver-root",
        default="",
        help="Silver normalization output root. Defaults to <output-root>/silver when --output-root is supplied.",
    )
    parser.add_argument(
        "--gold-root",
        default="",
        help="Gold feature store output root. Defaults to <output-root>/gold when --output-root is supplied.",
    )
    parser.add_argument("--pairs", default="", help="Comma-separated requested pairs.")
    parser.add_argument("--start", default="", help="Inclusive start boundary.")
    parser.add_argument("--end", default="", help="Inclusive end boundary.")
    parser.add_argument("--data-types", default="trades,klines,orderbook,metadata", help="Comma-separated data types.")
    parser.add_argument(
        "--feature-names",
        default=",".join(DEFAULT_EXPECTED_EDGE_FEATURE_NAMES),
        help="Comma-separated governed expected-edge feature names to materialize in gold rows.",
    )
    parser.add_argument(
        "--timeframes",
        default=",".join(DEFAULT_GOLD_TIMEFRAMES),
        help=(
            "Comma-separated gold feature timeframes. Defaults to the canonical "
            "registry ({0}). Pass a strict subset to prune explicitly; pruned "
            "timeframes appear in the manifest with TIMEFRAME_PRUNED_NOT_REQUESTED."
        ).format(",".join(DEFAULT_GOLD_TIMEFRAMES)),
    )
    parser.add_argument("--compression", default="zstd", help="Preferred compression target.")
    parser.add_argument("--resume", action="store_true", help="Resume Data Factory output if possible.")
    parser.add_argument("--dry-run", action="store_true", help="Write reports only.")
    parser.add_argument("--small-scope", action="store_true", help="Allow debug-sized materialization scope.")
    # Patch 6 batch 1 — silver storage governance.
    parser.add_argument(
        "--storage-format",
        choices=("jsonl", "jsonl-gz", "jsonl_debug", "jsonl-debug"),
        default="jsonl",
        help="Silver storage format. ``jsonl-gz`` is ~7-10x smaller and recommended for production.",
    )
    parser.add_argument(
        "--allow-broad-run",
        action="store_true",
        help="Explicitly allow non-dry-run scans without --start/--end (default: blocked).",
    )
    parser.add_argument(
        "--debug-storage-override",
        action="store_true",
        help="Allow debug JSONL mode outside small-scope when the operator explicitly overrides storage bloat safeguards.",
    )
    parser.add_argument(
        "--storage-budget-limit-bytes",
        type=int,
        default=53_687_091_200,
        help="Hard limit for combined silver+gold output size. Default: 50 GB.",
    )
    # Patch A2-OPT-3 (2026-05-26) — expose the measured economic provenance flag
    # so spread/slippage become MEASURED_FROM_BOOK_SNAPSHOT / MEASURED_FROM_KYLE_LAMBDA
    # instead of DEFAULT_BY_BOOK_STATUS / DEFAULT_TO_CALIBRATE. Upgrades B_ML
    # verdict from RESEARCH_ONLY_COST_PARTIAL → EXECUTION_AWARE_PARTIAL / COST_AWARE
    # when sufficient book/trade data exists at decision timestamps.
    parser.add_argument(
        "--use-measured-economic-provenance",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Compute spread/slippage from actual book snapshots and Kyle lambda from trades, "
            "instead of hardcoded proxy constants. Default True (W1 patch 2026-05-30); "
            "use --no-use-measured-economic-provenance for legacy proxy behavior."
        ),
    )
    # Patch T13-CLI (2026-05-28) — opt-in content-addressable cache for A2.
    # When `--cache-base PATH` is supplied the script routes through the
    # cached wrapper: cache hit → restore silver/gold/reports + return
    # deserialized result in seconds, cache miss → run A2 normally and
    # populate the cache at the end. Without the flag the script behaves
    # exactly as before (no cache lookup or write). Cache base must be a
    # writable directory; we deliberately do NOT default it so the operator
    # picks an explicit cache location per crypto set / per ML scope.
    parser.add_argument(
        "--cache-base",
        default="",
        help=(
            "Opt-in A2 content-addressable cache directory. When set, the "
            "script routes through `run_strategy_ladder_data_factory_cached`. "
            "Hit/miss decided by a deterministic hash of raw_roots fingerprint "
            "+ pairs + timeframes + feature_names + window + storage_format. "
            "Default empty = no cache (legacy behaviour)."
        ),
    )
    # Patch GOLD-CANCEL (2026-06-01) — cooperative cancel sidecar. The cockpit
    # passes the running job's cancel_request.json path; the gold build polls it
    # at entry/row boundaries and exits within seconds instead of waiting for the
    # cockpit's external SIGTERM poll (observed 54-min lag on run b3ffd14a).
    parser.add_argument(
        "--cancel-file",
        default="",
        help=(
            "Operator cancel sidecar path (e.g. the job's cancel_request.json). "
            "When this file appears mid-run, the A2 gold build stops promptly."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    # Patch GOLD-CANCEL (2026-06-01) — register the operator cancel sidecar so
    # the gold build can stop promptly mid-run.
    from local_replay_runtime.strategy_ladder_data_factory import (
        GoldBuildCancelledError,
        set_gold_cancel_file,
    )
    _cancel_file_arg = (args.cancel_file or "").strip()
    set_gold_cancel_file(Path(_cancel_file_arg).resolve() if _cancel_file_arg else None)
    explicit_output_root = (args.output_root or "").strip()
    explicit_silver = (args.silver_root or "").strip()
    explicit_gold = (args.gold_root or "").strip()
    if not explicit_output_root and not explicit_silver:
        parser.error("--silver-root is required when --output-root is not supplied")
    if not explicit_output_root and not explicit_gold:
        parser.error("--gold-root is required when --output-root is not supplied")
    if explicit_output_root:
        output_root = Path(explicit_output_root).resolve()
        silver_root = (
            Path(explicit_silver).resolve()
            if explicit_silver
            else (output_root / "silver").resolve()
        )
        gold_root = (
            Path(explicit_gold).resolve()
            if explicit_gold
            else (output_root / "gold").resolve()
        )
        report_root = output_root
    else:
        silver_root = Path(explicit_silver).resolve()
        gold_root = Path(explicit_gold).resolve()
        report_root = silver_root.parent.resolve()
    raw_roots = _raw_roots_tuple(args.raw_root_list, args.raw_roots)
    request = StrategyLadderDataFactoryRequest(
        run_id=args.run_id.strip() or f"strategy-ladder-data-factory-{uuid4().hex[:12]}",
        input_root=report_root,
        raw_roots=raw_roots,
        raw_source_manifest_path=(
            Path(args.raw_source_manifest).resolve()
            if args.raw_source_manifest
            else None
        ),
        historical_metadata_root=(
            Path(args.historical_metadata_root).resolve()
            if args.historical_metadata_root
            else None
        ),
        silver_root=silver_root,
        gold_root=gold_root,
        pairs=_csv_tuple(args.pairs),
        feature_names=_csv_tuple(args.feature_names) or DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
        timeframes=_csv_tuple(args.timeframes) or DEFAULT_GOLD_TIMEFRAMES,
        start=args.start,
        end=args.end,
        data_types=_csv_tuple(args.data_types),
        compression=args.compression,
        resume=args.resume,
        dry_run=args.dry_run,
        storage_format=args.storage_format,
        allow_broad_run=args.allow_broad_run,
        small_scope=args.small_scope,
        debug_storage_override=args.debug_storage_override,
        storage_budget_limit_bytes=args.storage_budget_limit_bytes,
        use_measured_economic_provenance=args.use_measured_economic_provenance,
    )
    # Patch T13-CLI (2026-05-28) — opt-in cache wrapper. The wrapper is a
    # drop-in replacement; the result is byte-identical to the un-cached
    # path. We pick the wrapper *only* when `--cache-base` was supplied.
    cache_base_arg = (args.cache_base or "").strip()
    try:
        if cache_base_arg:
            from local_replay_runtime.a2_cache_runner import (
                run_strategy_ladder_data_factory_cached,
            )
            cache_base_path = Path(cache_base_arg).resolve()
            result = run_strategy_ladder_data_factory_cached(
                request,
                cache_base=cache_base_path,
                cache_enabled=True,
            )
        else:
            result = run_strategy_ladder_data_factory(request)
    except GoldBuildCancelledError as exc:
        # Patch GOLD-CANCEL (2026-06-01) — cooperative cancel: exit promptly with
        # a clear status. The cockpit derives the cancelled job status from the
        # cancel_request.json sidecar + the process exit.
        print(
            json.dumps(
                {"data_factory_status": "CANCELLED_BY_OPERATOR", "detail": str(exc)},
                indent=2,
            )
        )
        sys.stdout.flush()
        return 130
    payload = {
        "run_id": result.manifest.run_id,
        "report_root": str(report_root),
        "data_factory_status": result.manifest.data_factory_status,
        "raw_source_status": result.manifest.raw_source_status,
        "pair_universe_status": result.manifest.pair_universe_status,
        "silver_index_status": result.manifest.silver_index_status,
        "gold_feature_store_status": result.manifest.gold_feature_store_status,
        "files_processed": result.manifest.files_processed,
        "rows_processed": result.manifest.rows_processed,
        "written_at": (
            result.manifest.updated_at.isoformat()
            if result.manifest.updated_at is not None
            else ""
        ),
    }
    print(json.dumps(payload, indent=2))
    sys.stdout.flush()
    _write_terminal_sentinel(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
