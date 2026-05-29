"""Backfill the A2 content-addressable cache from a completed run.

Use this after a successful A2 phase to make the silver/gold output reusable
by future runs with identical inputs. The cache key is rebuilt from the run's
`a2_gold_progress_report.json` (typed `request` block) and the operator-supplied
`--raw-root` paths.

Typical use:

    python scripts/backfill_a2_cache.py \\
        --run-dir "L:\\output backtest\\runs\\strategy_ladder_workflow-bc242fb957301811\\phase_a2_data_factory" \\
        --raw-root "L:\\ordrebookpart1" \\
        --raw-root "L:\\trades" \\
        --raw-root "L:\\klines" \\
        --cache-base "L:\\cache\\a2"

The script is read-only on the source run directory: it only copies silver/gold
into the cache root. Failure modes are explicit:

  * missing progress report → exit code 2
  * missing silver/gold subdirs → exit code 3
  * non-existent raw roots → exit code 4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _add_src_to_path() -> None:
    """Allow running this script before the package is installed."""

    script_dir = Path(__file__).resolve().parent
    src_dir = script_dir.parent / "src"
    if src_dir.is_dir() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


_add_src_to_path()


from local_replay_runtime.a2_cache import (  # noqa: E402
    build_a2_cache_key,
    compute_input_hash,
    populate_a2_cache,
)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        required=True,
        help="phase_a2_data_factory directory of the completed run.",
    )
    parser.add_argument(
        "--raw-root",
        dest="raw_root_list",
        action="append",
        default=[],
        help="Raw data root path. May be repeated.",
    )
    parser.add_argument(
        "--historical-metadata-root",
        default="",
        help="Optional historical metadata cache root.",
    )
    parser.add_argument(
        "--cache-base",
        default="L:/cache/a2",
        help="Cache base directory. Defaults to L:/cache/a2.",
    )
    parser.add_argument(
        "--engines",
        default="engine_a,engine_b,engine_c,engine_d",
        help="Comma-separated engines used by the run (default: a/b/c/d).",
    )
    parser.add_argument(
        "--data-types",
        default="trades,klines,orderbook,metadata",
        help="Comma-separated data types (default: trades/klines/orderbook/metadata).",
    )
    parser.add_argument(
        "--compression",
        default="zstd",
        help="Compression used (default: zstd).",
    )
    parser.add_argument(
        "--use-measured-economic-provenance",
        action="store_true",
        help="Set if the run used measured economic provenance (default: false).",
    )
    parser.add_argument(
        "--max-gold-feature-rows",
        type=int,
        default=0,
        help="`max_gold_feature_rows` from the request (default: 0).",
    )
    parser.add_argument(
        "--source-run-id",
        default="",
        help="Source workflow run id. Inferred from --run-dir if not provided.",
    )
    return parser.parse_args(argv)


def _infer_run_id(run_dir: Path) -> str:
    # `<L:/.../runs/strategy_ladder_workflow-XXX>/phase_a2_data_factory`
    if run_dir.name == "phase_a2_data_factory":
        return run_dir.parent.name
    return run_dir.name


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        print(f"[ERROR] run_dir does not exist: {run_dir}", file=sys.stderr)
        return 2
    progress_path = run_dir / "a2_gold_progress_report.json"
    if not progress_path.is_file():
        print(
            f"[ERROR] a2_gold_progress_report.json is missing under {run_dir}",
            file=sys.stderr,
        )
        return 2
    try:
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"[ERROR] could not read progress report: {exc}", file=sys.stderr)
        return 2

    silver_root = run_dir / "silver"
    gold_root = run_dir / "gold"
    if not silver_root.is_dir():
        print(f"[ERROR] silver subdir missing: {silver_root}", file=sys.stderr)
        return 3
    if not gold_root.is_dir():
        print(f"[ERROR] gold subdir missing: {gold_root}", file=sys.stderr)
        return 3

    raw_roots = tuple(Path(p) for p in args.raw_root_list if p)
    missing_raw = [str(p) for p in raw_roots if not p.exists()]
    if missing_raw:
        print(
            "[ERROR] raw roots do not exist: " + ", ".join(missing_raw),
            file=sys.stderr,
        )
        return 4

    historical_metadata_root: Path | None = (
        Path(args.historical_metadata_root).resolve()
        if args.historical_metadata_root
        else None
    )

    request = progress.get("request") or {}
    pairs = tuple(request.get("pairs") or progress.get("pairs") or ())
    timeframes = tuple(request.get("timeframes") or ())
    feature_names = tuple(request.get("feature_names") or ())
    window = progress.get("window") or {}
    start = str(window.get("requested_start") or "")
    end = str(window.get("requested_end") or "")

    engines = tuple(p.strip() for p in args.engines.split(",") if p.strip())
    data_types = tuple(p.strip().lower() for p in args.data_types.split(",") if p.strip())

    key = build_a2_cache_key(
        raw_roots=raw_roots,
        historical_metadata_root=historical_metadata_root,
        pairs=pairs,
        engines=engines,
        timeframes=timeframes,
        feature_names=feature_names,
        start=start,
        end=end,
        data_types=data_types,
        compression=args.compression,
        storage_format=str(
            progress.get("silver_storage_mode_effective")
            or progress.get("silver_storage_mode_requested")
            or "jsonl-gz"
        ),
        max_gold_feature_rows=int(args.max_gold_feature_rows),
        use_measured_economic_provenance=bool(args.use_measured_economic_provenance),
    )
    input_hash = compute_input_hash(key)
    source_run_id = args.source_run_id or _infer_run_id(run_dir)

    counters = progress.get("counters") or {}
    counters_snapshot = {
        k: int(v) for k, v in counters.items() if isinstance(v, (int, float))
    }

    print(f"[INFO] input_hash={input_hash}")
    print(f"[INFO] cache_root={Path(args.cache_base).resolve() / input_hash}")
    print(f"[INFO] source_run_id={source_run_id}")
    print(f"[INFO] pairs={pairs} window={start}->{end}")
    print(f"[INFO] feature_names={len(feature_names)} timeframes={timeframes}")

    entry = populate_a2_cache(
        cache_base=Path(args.cache_base).resolve(),
        key=key,
        source_run_id=source_run_id,
        source_silver_root=silver_root,
        source_gold_root=gold_root,
        source_progress_report_path=progress_path,
        counters_snapshot=counters_snapshot,
        gold_feature_row_count=int(counters.get("gold_feature_row_count") or 0),
        silver_entry_count=int(counters.get("silver_entry_count") or 0),
        # Patch 2026-05-28 — propagate prod-safety + anti-leakage verdict so
        # the cache entry honestly carries the source run's status. The
        # reports live alongside the progress report under the same dir.
        source_report_dir=run_dir,
    )
    print(f"[OK] entry stored at {entry.cache_root}")
    print(f"[OK] gold_feature_row_count={entry.gold_feature_row_count}")
    print(f"[OK] silver_entry_count={entry.silver_entry_count}")
    print(f"[OK] prod_safety_status={entry.prod_safety_status}")
    print(f"[OK] prod_safe={entry.prod_safe}")
    if entry.prod_safety_blocker_codes:
        print(
            f"[OK] prod_safety_blocker_codes={list(entry.prod_safety_blocker_codes)}"
        )
    print(f"[OK] anti_leakage_status={entry.anti_leakage_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
