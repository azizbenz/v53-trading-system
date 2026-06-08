"""Map step of the chunked (map-reduce) backtest orchestrator — Phase 3.

Splits a long [start, end] backtest into independent temporal chunks (1 day or
1 week) and runs the canonical A2 -> B1 -> B2 pipeline for each chunk by invoking
the existing, validated phase CLIs as subprocesses.

Why chunk: a monolithic 6-month run (a) loses manifest coherence, (b) blows RAM
in B2 (the parallel parent parses the whole range's silver at once -> measured
~24 GB / thrash on a 3-day range), and (c) leaves no per-stage evidence when it
is interrupted. Chunking by day shrinks each chunk's silver so the B2 parallel
path is RAM-safe (measured peak ~14 GB at 1 day vs ~24 GB at 3 days), and gives
one self-contained manifest + performance profile per chunk.

Resilience: each chunk writes its own ``chunk_manifest.json``. A blocked/failed
chunk is recorded and the run CONTINUES to the next chunk. Re-running is
idempotent: a chunk whose manifest is already ``CHUNK_COMPLETE`` is skipped
(``--resume``), so a run that dies at chunk 100/180 resumes at 100.

Aggregate the per-chunk results with ``reduce_backtest_chunks.py``.

V1 boundary note: each chunk is built fresh with the existing A2 1h context
lookback (``effective_context_start = requested_start - 1h``). Cross-chunk engine
warmup beyond that 1h is a documented v1 limitation, not a correctness claim.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
DATA_FACTORY_CLI = SCRIPTS / "run_strategy_ladder_data_factory.py"
LADDER_CLI = SCRIPTS / "run_backtest_strategy_ladder.py"

from local_replay_runtime.strategy_ladder_expected_edge_feature_contracts import (
    DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
    EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
)

# A2-materializable governed feature set (= DEFAULT u REPLAY_MICROSTRUCTURE u
# EXTENDED, mirrors strategy_ladder_data_factory._A2_MATERIALIZABLE_FEATURES).
# Used as the chunked-launcher --feature-names default so governed runs
# materialize the microstructure features (vpin / cumulative_ofi / queue_pressure
# / kyle_lambda / realized_vol_*) into A2 gold instead of silently degrading to
# the 3 legacy features when no --feature-names is supplied.
_A2_GOVERNED_FEATURE_NAMES: tuple[str, ...] = (
    *DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
    *REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    *EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
)


def _parse_date(value: str) -> date:
    return datetime.strptime(value.strip(), "%Y-%m-%d").date()


def _iter_chunks(start: date, end: date, granularity: str) -> list[tuple[date, date]]:
    """Inclusive [start, end] split into (chunk_start, chunk_end) pairs."""
    if end < start:
        raise ValueError(f"end {end} < start {start}")
    step_days = 1 if granularity == "1d" else 7
    chunks: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + timedelta(days=step_days - 1), end)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end + timedelta(days=1)
    return chunks


def _parse_cli_json(stdout: str) -> dict | None:
    """Extract the trailing ``json.dumps(..., indent=2)`` block a phase CLI prints.

    The CLIs emit one indented JSON object last on stdout (B2 also prints many
    ``execution_decision_no_trade_recorded`` lines to stderr — ignored here).
    """
    lines = stdout.splitlines()
    end = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].rstrip() == "}":
            end = i
            break
    if end is None:
        return None
    start = None
    for i in range(end, -1, -1):
        if lines[i].startswith("{"):
            start = i
            break
    if start is None:
        return None
    try:
        return json.loads("\n".join(lines[start : end + 1]))
    except json.JSONDecodeError:
        return None


def _run_phase(
    argv: list[str], *, env: dict[str, str] | None = None, log_path: Path
) -> tuple[int, dict | None, float]:
    """Run a phase CLI as a subprocess. Returns (exit_code, parsed_payload, wall_s).

    Full stdout+stderr is teed to ``log_path`` for audit even on failure.
    """
    started = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, *argv],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    wall = time.perf_counter() - started
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"$ {sys.executable} {' '.join(argv)}\n\n=== STDOUT ===\n{proc.stdout}\n"
        f"=== STDERR (tail) ===\n" + "\n".join(proc.stderr.splitlines()[-40:]),
        encoding="utf-8",
    )
    return proc.returncode, _parse_cli_json(proc.stdout), wall


def _read_b2_profile(chunk_dir: Path, b2_run_id: str) -> dict:
    prof = (
        chunk_dir
        / "phase_b2_detailed_replay"
        / "backtest_strategy_ladder"
        / b2_run_id
        / "replay_performance_profile.json"
    )
    if not prof.is_file():
        return {}
    try:
        j = json.loads(prof.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    engine_native = None
    for entry in j.get("phases", []):
        if entry.get("phase_name") == "engine_native_materialization":
            engine_native = entry.get("wall_time_s")
            break
    return {
        "total_wall_time_s": j.get("total_wall_time_s"),
        "engine_native_materialization_s": engine_native,
        "replay_workers_used": j.get("replay_workers_used"),
    }


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Chunked (map) backtest orchestrator — Phase 3.")
    p.add_argument("--run-id", default="", help="Run id; defaults to chunked-backtest-<start>-<end>.")
    p.add_argument("--start", required=True, help="Inclusive start date YYYY-MM-DD.")
    p.add_argument("--end", required=True, help="Inclusive end date YYYY-MM-DD.")
    p.add_argument("--chunk", default="1d", choices=("1d", "1w"), help="Chunk granularity.")
    p.add_argument("--output-root", required=True, help="Run root; chunks land under <root>/<run_id>/chunks/.")
    p.add_argument("--raw-root", dest="raw_root_list", action="append", default=[], help="Raw data root (repeatable).")
    p.add_argument("--historical-metadata-root", default="", help="Bybit historical metadata cache root.")
    p.add_argument("--pairs", default="BNBUSDT,BTCUSDT", help="Comma-separated pairs.")
    p.add_argument("--engines", default="engine_a,engine_b,engine_c,engine_d", help="Comma-separated engines.")
    p.add_argument("--timeframes", default="5m,15m", help="Comma-separated timeframes.")
    p.add_argument("--capital-buckets", default="400,500,1500,4000", help="Comma-separated capital buckets.")
    p.add_argument("--engine-native-sample-size", default=50, type=int, help="Per-day engine-native sample size.")
    p.add_argument("--candidate-discovery-mode", default="TEMPORAL_STRATIFIED", help="Candidate discovery mode.")
    p.add_argument("--candidate-sample-cap", default=50, type=int, help="Per-engine candidate cap.")
    p.add_argument("--b1-5-policy-mode", default="conservative_hard_only", help="B1.5 preselection policy.")
    p.add_argument("--storage-format", default="jsonl-gz", help="Silver storage format.")
    p.add_argument(
        "--feature-names",
        default=",".join(_A2_GOVERNED_FEATURE_NAMES),
        help=(
            "Comma-separated governed expected-edge feature names to materialize in A2 "
            "gold. Defaults to the microstructure-inclusive governed set so chunked runs "
            "do not silently degrade to the 3 legacy features. Pass a smaller set "
            "(e.g. 'close_return,high_low_range,volume') only for LIGHT smoke runs."
        ),
    )
    p.add_argument("--ml-mode", default="ML_MODE_OFF", help="ML mode.")
    p.add_argument("--max-workers", default="1", help="B2 engine-native workers (V53_MAX_WORKERS). RAM-safe at 1-day chunking.")
    p.add_argument("--resume", action="store_true", help="Skip chunks already CHUNK_COMPLETE.")
    p.add_argument("--dry-run", action="store_true", help="Print the chunk plan + per-phase commands without executing.")
    return p


def _write_chunk_index(
    run_root: Path,
    run_id: str,
    start: date,
    end: date,
    args: argparse.Namespace,
    chunks_total: int,
    chunk_index: list[dict],
) -> None:
    """Write/refresh chunk_index.json. Called after EACH chunk so the dashboard
    viewer shows live progress (grid grows as chunks complete), not only at the end."""
    index = {
        "schema_version": "v1",
        "run_id": run_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "granularity": args.chunk,
        "chunk_count": chunks_total,
        "chunks": chunk_index,
        "config": {
            "pairs": args.pairs,
            "engines": args.engines,
            "timeframes": args.timeframes,
            "max_workers": args.max_workers,
            "engine_native_sample_size": args.engine_native_sample_size,
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "chunk_index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    start, end = _parse_date(args.start), _parse_date(args.end)
    run_id = args.run_id.strip() or f"chunked-backtest-{start.isoformat()}-{end.isoformat()}"
    run_root = (Path(args.output_root).resolve() / run_id)
    chunks_root = run_root / "chunks"
    chunks_root.mkdir(parents=True, exist_ok=True)
    chunks = _iter_chunks(start, end, args.chunk)

    raw_root_args: list[str] = []
    for r in args.raw_root_list:
        raw_root_args += ["--raw-root", r]

    chunk_index: list[dict] = []
    print(f"[chunked] run_id={run_id} chunks={len(chunks)} granularity={args.chunk} root={run_root}")

    for c_start, c_end in chunks:
        label = c_start.isoformat() if c_start == c_end else f"{c_start.isoformat()}_{c_end.isoformat()}"
        chunk_dir = chunks_root / label
        manifest_path = chunk_dir / "chunk_manifest.json"
        s, e = c_start.isoformat(), c_end.isoformat()

        if args.resume and manifest_path.is_file():
            try:
                prev = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                prev = {}
            if prev.get("status") == "CHUNK_COMPLETE":
                print(f"[chunked] SKIP {label} (already CHUNK_COMPLETE)")
                chunk_index.append({"chunk_label": label, "status": "CHUNK_COMPLETE", "skipped": True})
                _write_chunk_index(run_root, run_id, start, end, args, len(chunks), chunk_index)
                continue

        a2_dir = chunk_dir / "phase_a2_data_factory"
        b1_dir = chunk_dir / "phase_b1_candidate_discovery"
        b2_dir = chunk_dir / "phase_b2_detailed_replay"
        b1_run_id, b2_run_id = f"{label}-bb", f"{label}-b2"

        a2_argv = [
            str(DATA_FACTORY_CLI), "--run-id", f"{label}-a2",
            "--output-root", str(a2_dir), *raw_root_args,
            "--pairs", args.pairs, "--timeframes", args.timeframes,
            "--start", s, "--end", e,
            "--feature-names", args.feature_names,
            "--storage-format", args.storage_format, "--use-measured-economic-provenance",
        ]
        if args.historical_metadata_root:
            a2_argv += ["--historical-metadata-root", args.historical_metadata_root]

        ce_path = b1_dir / "backtest_strategy_ladder" / b1_run_id / "fast_candidates" / "candidate_events.jsonl"
        common_ladder = [
            "--feature-store-root", str(a2_dir / "gold"),
            "--silver-index-path", str(a2_dir / "silver_index.json"),
            "--raw-source-manifest", str(a2_dir / "raw_source_manifest.json"),
            *raw_root_args,
            "--pairs", args.pairs, "--engines", args.engines, "--timeframes", args.timeframes,
            "--capital-buckets", args.capital_buckets,
            "--engine-native-sample-size", str(args.engine_native_sample_size),
            "--candidate-discovery-mode", args.candidate_discovery_mode,
            "--candidate-sample-cap", str(args.candidate_sample_cap),
            "--b1-5-policy-mode", args.b1_5_policy_mode, "--preselected-only",
            "--start", s, "--end", e, "--ml-mode", args.ml_mode,
        ]
        b1_argv = [str(LADDER_CLI), "--run-id", b1_run_id, "--fast-only",
                   "--input-root", str(b1_dir), "--output-root", str(b1_dir),
                   "--raw-window-mode", "REFS_ONLY", *common_ladder]
        b2_argv = [str(LADDER_CLI), "--run-id", b2_run_id, "--detailed-only",
                   "--candidate-events-path", str(ce_path),
                   "--input-root", str(b2_dir), "--output-root", str(b2_dir),
                   "--raw-window-mode", "MATERIALIZE", *common_ladder]

        if args.dry_run:
            print(f"\n[chunked] CHUNK {label} ({s}..{e}) -> {chunk_dir}")
            for name, av in (("A2", a2_argv), ("B1", b1_argv), ("B2", b2_argv)):
                print(f"  {name}: {sys.executable} {' '.join(av)}")
            chunk_index.append({"chunk_label": label, "status": "DRY_RUN", "start": s, "end": e})
            continue

        chunk_dir.mkdir(parents=True, exist_ok=True)
        logs = chunk_dir / "_phase_logs"
        phases: dict[str, dict] = {}
        status = "CHUNK_COMPLETE"
        t0 = time.perf_counter()

        # --- A2 ---
        rc, payload, wall = _run_phase(a2_argv, log_path=logs / "a2.log")
        phases["A2"] = {"exit": rc, "wall_s": round(wall, 2),
                        "data_factory_status": (payload or {}).get("data_factory_status")}
        if rc != 0 or (payload or {}).get("data_factory_status") != "DATA_FACTORY_READY":
            status = "CHUNK_FAILED_A2"

        # --- B1 ---
        if status == "CHUNK_COMPLETE":
            rc, payload, wall = _run_phase(b1_argv, log_path=logs / "b1.log")
            phases["B1"] = {"exit": rc, "wall_s": round(wall, 2),
                            "final_status": (payload or {}).get("final_status"),
                            "candidate_count": (payload or {}).get("candidate_count")}
            if rc != 0 or not ce_path.is_file():
                status = "CHUNK_FAILED_B1"

        # --- B2 (parallel; RAM-safe at chunk granularity) ---
        if status == "CHUNK_COMPLETE":
            env = dict(os.environ)
            env["V53_MAX_WORKERS"] = str(args.max_workers)
            rc, payload, wall = _run_phase(b2_argv, env=env, log_path=logs / "b2.log")
            prof = _read_b2_profile(chunk_dir, b2_run_id)
            b2_final = (payload or {}).get("final_status")
            phases["B2"] = {"exit": rc, "wall_s": round(wall, 2), "final_status": b2_final,
                            "detailed_replay_count": (payload or {}).get("detailed_replay_count"), **prof}
            if rc != 0:
                status = "CHUNK_FAILED_B2"
            elif b2_final and "BLOCKED_BY_BACKTEST_DATA" in str(b2_final):
                status = "CHUNK_BLOCKED_DATA"  # coverage gap etc. — recorded, not fatal to the run

        manifest = {
            "schema_version": "v1", "chunk_label": label, "start": s, "end": e,
            "status": status, "phases": phases,
            "total_wall_s": round(time.perf_counter() - t0, 2),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        chunk_dir.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        chunk_index.append({k: manifest[k] for k in ("chunk_label", "status", "total_wall_s")})
        _write_chunk_index(run_root, run_id, start, end, args, len(chunks), chunk_index)
        print(f"[chunked] {label}: {status} ({manifest['total_wall_s']}s)")

    _write_chunk_index(run_root, run_id, start, end, args, len(chunks), chunk_index)
    done = sum(1 for c in chunk_index if c.get("status") == "CHUNK_COMPLETE")
    print(f"\n[chunked] DONE {done}/{len(chunks)} complete. Index: {run_root / 'chunk_index.json'}")
    print(f"[chunked] Reduce: python scripts/reduce_backtest_chunks.py --run-root \"{run_root}\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
