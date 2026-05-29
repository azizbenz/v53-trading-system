"""Monitor an in-flight A2 run.

Reads `a2_gold_progress_report.json` from a `phase_a2_data_factory` directory
every `--poll-interval` seconds and prints a compact dashboard line:

  [HH:MM:SS] stage=GOLD_FEATURE_BUILD_RUNNING gold_rows=1057
  Δrows=+0 (stuck?) K=303GB silver=12345 files

`Δrows=+0` over several polls is a heuristic for a stuck run. The K: free
space is shown so the operator catches a disk-saturation crash early (the
exact failure mode of `7ef24299c45dc46d`).

Exit codes:
  0  user-interrupted (Ctrl+C) or one-shot poll completed
  2  --run-dir missing
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        required=True,
        help="phase_a2_data_factory directory of the in-flight run.",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="Seconds between polls (default 60). Pass 0 for a single snapshot.",
    )
    parser.add_argument(
        "--stuck-after",
        type=int,
        default=5,
        help=(
            "Number of consecutive polls with 0 delta before flagging "
            "'STUCK?' on the line (default 5)."
        ),
    )
    return parser.parse_args(argv)


def _read_progress(run_dir: Path) -> dict | None:
    path = run_dir / "a2_gold_progress_report.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _free_gb(path: Path) -> float:
    try:
        return shutil.disk_usage(path).free / (1024**3)
    except OSError:
        return -1.0


def _count_silver_files(run_dir: Path) -> int:
    silver = run_dir / "silver"
    if not silver.is_dir():
        return 0
    return sum(1 for _ in silver.rglob("*.jsonl.gz"))


def _short_stage(stage: str) -> str:
    if not stage:
        return "?"
    return stage.replace("_COMPLETE", "").replace("_RUNNING", "*")


def _format_counters(counters: dict | None) -> tuple[int, int, int, int]:
    if not isinstance(counters, dict):
        return 0, 0, 0, 0
    return (
        int(counters.get("rows_processed", 0) or 0),
        int(counters.get("silver_entry_count", 0) or 0),
        int(counters.get("gold_feature_row_count", 0) or 0),
        int(counters.get("files_processed", 0) or 0),
    )


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        print(f"[ERROR] run_dir does not exist: {run_dir}", file=sys.stderr)
        return 2

    last_rows = 0
    stuck_count = 0
    try:
        while True:
            payload = _read_progress(run_dir)
            now = datetime.now(timezone.utc).astimezone().strftime("%H:%M:%S")
            if payload is None:
                print(f"[{now}] progress_report missing — waiting", flush=True)
            else:
                status = str(payload.get("status") or "?")
                stage = _short_stage(str(payload.get("current_stage") or ""))
                stage_detail = str(payload.get("stage_detail") or "")
                rows, silver_n, gold_n, files_n = _format_counters(
                    payload.get("counters")
                )
                delta = rows - last_rows
                last_rows = rows
                if delta == 0:
                    stuck_count += 1
                else:
                    stuck_count = 0
                stuck_flag = (
                    f"STUCK?({stuck_count})" if stuck_count >= args.stuck_after else ""
                )
                silver_files = _count_silver_files(run_dir)
                k_free = _free_gb(Path("K:/"))
                l_free = _free_gb(Path("L:/"))
                detail = f" [{stage_detail}]" if stage_detail else ""
                print(
                    f"[{now}] {status} {stage}{detail} "
                    f"rows={rows:,} Δ+{delta:,} silver={silver_n} files={files_n} gold={gold_n} "
                    f"silver_files_disk={silver_files} K={k_free:.1f}GB L={l_free:.1f}GB "
                    f"{stuck_flag}",
                    flush=True,
                )
                if status in {"A2_COMPLETE", "A2_FAILED"}:
                    print(f"[{now}] terminal status reached — exiting monitor")
                    return 0
            if args.poll_interval <= 0:
                return 0
            time.sleep(args.poll_interval)
    except KeyboardInterrupt:
        print("\n[interrupted by user]")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
