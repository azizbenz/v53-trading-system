"""CLI entrypoint for the first controlled Strategy Ladder run harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_replay_runtime.strategy_ladder_first_controlled_run import (
    run_strategy_ladder_first_controlled_run,
)
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderFirstControlledRunRequest,
)
from local_replay_runtime.strategy_ladder_expected_edge_feature_contracts import (
    DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
)


def _csv_tuple(raw_value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in (raw_value or "").split(",") if part.strip())


def _bucket_tuple(raw_value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in (raw_value or "").split(",") if part.strip())


def _raw_roots_tuple(raw_root_list: list[str], raw_roots: str) -> tuple[Path, ...]:
    values = [*raw_root_list, *_csv_tuple(raw_roots)]
    unique = tuple(dict.fromkeys(str(Path(item).resolve()) for item in values if item))
    return tuple(Path(item) for item in unique)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Patch 6 first controlled Strategy Ladder harness.")
    parser.add_argument("--run-id", default="", help="Deterministic run id.")
    parser.add_argument("--input-root", required=True, help="Operator work root for first-run reports and ladder artifacts.")
    parser.add_argument("--raw-root", dest="raw_root_list", action="append", default=[], help="Raw data root. May be repeated.")
    parser.add_argument("--raw-roots", default="", help="Comma-separated raw data roots.")
    parser.add_argument("--raw-source-manifest", default="", help="Optional raw source manifest path.")
    parser.add_argument(
        "--historical-metadata-root",
        default="",
        help="Optional local Bybit historical metadata cache root (symbol_metadata.csv/jsonl).",
    )
    parser.add_argument("--output-root", default="", help="Optional explicit output root. Defaults to --input-root.")
    parser.add_argument("--silver-root", default="", help="Optional explicit silver root. Defaults to <output-root>/silver.")
    parser.add_argument("--gold-root", default="", help="Optional explicit gold root. Defaults to <output-root>/gold.")
    parser.add_argument("--pairs", default="", help="Comma-separated pair filter.")
    parser.add_argument("--engines", default="engine_a,engine_b,engine_c,engine_d", help="Comma-separated engine filter.")
    parser.add_argument("--capital-buckets", default="400,500,1500,4000", help="Comma-separated capital buckets.")
    parser.add_argument("--timeframes", default="1m,5m", help="Comma-separated timeframe filter.")
    parser.add_argument(
        "--feature-names",
        default=",".join(DEFAULT_EXPECTED_EDGE_FEATURE_NAMES),
        help="Comma-separated governed expected-edge feature names to materialize in gold rows.",
    )
    parser.add_argument("--start", default="", help="Inclusive start boundary.")
    parser.add_argument("--end", default="", help="Inclusive end boundary.")
    parser.add_argument("--dry-run", action="store_true", help="Write status outputs only.")
    parser.add_argument("--fixture-mode", action="store_true", help="Use bounded fixture expectations.")
    parser.add_argument("--small-scope", action="store_true", help="Explicitly confirm bounded scope.")
    parser.add_argument("--no-full-scan", action="store_true", help="Prevent default broad scans.")
    parser.add_argument("--allow-broad-run", action="store_true", help="Explicitly allow broad historical scans.")
    parser.add_argument("--ml-mode", default="ML_MODE_OFF", help="ML mode for the controlled run.")
    parser.add_argument("--frozen-ml-artifact-path", default="", help="Frozen ML artifact path for ML_MODE_OVERLAY_FROZEN.")
    parser.add_argument("--frozen-ml-artifact-hash", default="", help="Frozen ML artifact hash for ML_MODE_OVERLAY_FROZEN.")
    parser.add_argument(
        "--engine-native-mode",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable the Strategy Ladder engine native bridge (default True; use --no-engine-native-mode for legacy proxy path).",
    )
    parser.add_argument(
        "--engine-native-sample-size",
        default=10,
        type=int,
        help="Max candidate sample size for the engine native bridge proof path.",
    )
    parser.add_argument(
        "--use-measured-economic-provenance",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Measure spread provenance from orderbook snapshots instead of hardcoded "
            "proxy constants. Default True (W1 patch 2026-05-30); use "
            "--no-use-measured-economic-provenance for legacy proxy behavior."
        ),
    )
    # Patch T13-CLI (2026-05-28) — opt-in A2 cache via env propagation. The
    # underlying `strategy_ladder_first_controlled_run` orchestrates A1+A2+B1
    # internally; we activate the cache by exporting V53_A2_CACHE_BASE before
    # invocation so the inner data_factory call uses the wrapper. Default
    # empty = legacy (no cache).
    parser.add_argument(
        "--cache-base",
        default="",
        help=(
            "Opt-in A2 content-addressable cache directory. When set, the "
            "inner data_factory call routes through the cached wrapper "
            "(hit → restore in seconds, miss → run + populate). Default "
            "empty = no cache (legacy behaviour)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    input_root = Path(args.input_root).resolve()
    output_root = Path(args.output_root).resolve() if args.output_root else input_root
    silver_root = Path(args.silver_root).resolve() if args.silver_root else (output_root / "silver")
    gold_root = Path(args.gold_root).resolve() if args.gold_root else (output_root / "gold")
    raw_roots = _raw_roots_tuple(args.raw_root_list, args.raw_roots)
    request = StrategyLadderFirstControlledRunRequest(
        run_id=args.run_id.strip() or f"strategy-ladder-first-run-{uuid4().hex[:12]}",
        input_root=input_root,
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
        output_root=output_root,
        silver_root=silver_root,
        gold_root=gold_root,
        pairs=_csv_tuple(args.pairs),
        engines=_csv_tuple(args.engines),
        capital_buckets=_bucket_tuple(args.capital_buckets),
        timeframes=_csv_tuple(args.timeframes),
        feature_names=_csv_tuple(args.feature_names) or DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
        start=args.start,
        end=args.end,
        dry_run=args.dry_run,
        fixture_mode=args.fixture_mode,
        small_scope=args.small_scope,
        no_full_scan=(True if not args.allow_broad_run else args.no_full_scan),
        allow_broad_run=args.allow_broad_run,
        ml_mode=args.ml_mode,
        frozen_ml_artifact_path=(
            Path(args.frozen_ml_artifact_path).resolve()
            if args.frozen_ml_artifact_path
            else None
        ),
        frozen_ml_artifact_hash=args.frozen_ml_artifact_hash or None,
        engine_native_mode=args.engine_native_mode,
        engine_native_sample_size=args.engine_native_sample_size,
        use_measured_economic_provenance=args.use_measured_economic_provenance,
    )
    # Patch T13-CLI (2026-05-28) — propagate the opt-in cache base to the
    # inner data_factory call via env. The wrapper module checks this env
    # at lookup time; absent or empty → legacy uncached behaviour.
    cache_base_arg = (args.cache_base or "").strip()
    if cache_base_arg:
        import os as _os

        _os.environ["V53_A2_CACHE_BASE"] = str(Path(cache_base_arg).resolve())
        _os.environ["V53_A2_CACHE"] = "1"
    result = run_strategy_ladder_first_controlled_run(request)
    print(
        json.dumps(
            {
                "run_id": result.manifest.run_id,
                "first_run_status": result.manifest.first_run_status,
                "data_factory_status": result.manifest.data_factory_status,
                "feature_store_status": result.manifest.feature_store_status,
                "raw_window_status": result.manifest.raw_window_status,
                "capital_profile_status": result.manifest.capital_profile_status,
                "artifact_inventory_path": str((output_root / "first_run_artifact_inventory.json").resolve()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
