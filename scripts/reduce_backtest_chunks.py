"""Reduce step of the chunked (map-reduce) backtest — Phase 3.

Scans a chunked run produced by ``run_chunked_backtest.py`` and compiles a single
synthesis across all chunks:

  - Coverage   : how many chunks completed / blocked / failed / missing (+ reasons)
  - Performance: total + per-phase wall time, per-chunk distribution
  - Economic   : pooled candidate / replay / executed-trade counts; pooled
                 statistical-validation observation count (the deflated-Sharpe /
                 PSR / DSR must be computed on the POOLED trade set across the
                 whole horizon, never per-chunk — Harvey-Liu-Zhu)
  - Data quality: aggregated raw-window coverage gaps (BOOK_DEPTH_NOT_PROVEN etc.)

Writes ``global_synthesis.json`` + ``SYNTHESIS.md`` at the run root. Robust to
missing/partial chunks (a chunk with no manifest is reported MISSING, not fatal).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _b2_run_manifest(chunk_dir: Path, label: str) -> dict:
    return _load_json(
        chunk_dir / "phase_b2_detailed_replay" / "backtest_strategy_ladder"
        / f"{label}-b2" / "run_manifest.json"
    )


def _expected_chunk_labels(index: dict) -> list[str]:
    return [c.get("chunk_label") for c in index.get("chunks", []) if c.get("chunk_label")]


def _num(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def reduce_run(run_root: Path) -> dict:
    index = _load_json(run_root / "chunk_index.json")
    chunks_root = run_root / "chunks"
    labels = _expected_chunk_labels(index)
    if not labels and chunks_root.is_dir():
        labels = sorted(p.name for p in chunks_root.iterdir() if p.is_dir())

    coverage = {"complete": 0, "blocked": 0, "failed": 0, "missing": 0}
    non_complete: list[dict] = []
    perf = {"total_wall_s": 0.0, "a2_wall_s": 0.0, "b1_wall_s": 0.0, "b2_wall_s": 0.0,
            "engine_native_s": 0.0}
    econ = {"candidate_count": 0, "detailed_replay_count": 0, "executed_trade_count": 0,
            "statistical_validation_observation_count": 0}
    dq = {"raw_window_partial": 0, "book_depth_not_proven": 0, "depth20_missing": 0}
    per_chunk: list[dict] = []
    b2_status_counts: dict[str, int] = {}

    for label in labels:
        chunk_dir = chunks_root / label
        manifest = _load_json(chunk_dir / "chunk_manifest.json")
        if not manifest:
            coverage["missing"] += 1
            non_complete.append({"chunk_label": label, "status": "MISSING"})
            per_chunk.append({"chunk_label": label, "status": "MISSING"})
            continue

        status = manifest.get("status", "UNKNOWN")
        phases = manifest.get("phases", {})
        a2, b1, b2 = phases.get("A2", {}), phases.get("B1", {}), phases.get("B2", {})

        if status == "CHUNK_COMPLETE":
            coverage["complete"] += 1
        elif "BLOCKED" in status:
            coverage["blocked"] += 1
            non_complete.append({"chunk_label": label, "status": status,
                                 "b2_final_status": b2.get("final_status")})
        else:
            coverage["failed"] += 1
            non_complete.append({"chunk_label": label, "status": status})

        perf["total_wall_s"] += _num(manifest.get("total_wall_s"))
        perf["a2_wall_s"] += _num(a2.get("wall_s"))
        perf["b1_wall_s"] += _num(b1.get("wall_s"))
        perf["b2_wall_s"] += _num(b2.get("wall_s"))
        perf["engine_native_s"] += _num(b2.get("engine_native_materialization_s"))
        econ["candidate_count"] += int(_num(b1.get("candidate_count")))
        econ["detailed_replay_count"] += int(_num(b2.get("detailed_replay_count")))

        b2_final = b2.get("final_status")
        if b2_final:
            b2_status_counts[b2_final] = b2_status_counts.get(b2_final, 0) + 1

        # Deeper economic + data-quality fields from the B2 run manifest (best effort).
        rm = _b2_run_manifest(chunk_dir, label)
        econ["executed_trade_count"] += int(_num(rm.get("executed_trade_count")))
        econ["statistical_validation_observation_count"] += int(
            _num(rm.get("statistical_validation_observation_count"))
        )
        dq["raw_window_partial"] += int(_num(rm.get("raw_window_partial_count")))
        dq["book_depth_not_proven"] += int(_num(rm.get("depth20_missing")))
        dq["depth20_missing"] += int(_num(rm.get("depth20_missing")))

        per_chunk.append({
            "chunk_label": label, "status": status,
            "total_wall_s": round(_num(manifest.get("total_wall_s")), 1),
            "engine_native_s": round(_num(b2.get("engine_native_materialization_s")), 1),
            "replay_workers_used": b2.get("replay_workers_used"),
            "candidate_count": b1.get("candidate_count"),
            "b2_final_status": b2_final,
        })

    n = len(labels)
    wall_list = [c["total_wall_s"] for c in per_chunk if isinstance(c.get("total_wall_s"), (int, float))]
    synthesis = {
        "schema_version": "v1",
        "run_id": index.get("run_id"),
        "start": index.get("start"), "end": index.get("end"),
        "granularity": index.get("granularity"),
        "chunk_count": n,
        "coverage": coverage,
        "non_complete_chunks": non_complete,
        "performance": {
            **{k: round(v, 1) for k, v in perf.items()},
            "avg_chunk_wall_s": round(sum(wall_list) / len(wall_list), 1) if wall_list else 0.0,
            "max_chunk_wall_s": round(max(wall_list), 1) if wall_list else 0.0,
        },
        "economic": econ,
        "b2_final_status_counts": b2_status_counts,
        "data_quality": dq,
        "pooled_statistical_validation": (
            "PENDING_POOLED_TRADES" if econ["executed_trade_count"] == 0
            else "READY_FOR_POOLED_DSR_PSR"
        ),
        "per_chunk": per_chunk,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return synthesis


def _render_md(s: dict) -> str:
    cov = s["coverage"]
    perf = s["performance"]
    econ = s["economic"]
    lines = [
        f"# Backtest synthesis — {s.get('run_id')}",
        "",
        f"- Horizon: **{s.get('start')} → {s.get('end')}** ({s.get('granularity')} chunks, {s.get('chunk_count')} total)",
        f"- Generated: {s.get('generated_at')}",
        "",
        "## Coverage",
        f"- ✅ complete: **{cov['complete']}** / {s['chunk_count']}",
        f"- ⛔ blocked: {cov['blocked']}  ·  ❌ failed: {cov['failed']}  ·  ❔ missing: {cov['missing']}",
    ]
    if s["non_complete_chunks"]:
        lines.append("- Non-complete chunks:")
        for c in s["non_complete_chunks"][:50]:
            lines.append(f"  - `{c['chunk_label']}` — {c['status']}"
                         + (f" ({c.get('b2_final_status')})" if c.get("b2_final_status") else ""))
    lines += [
        "",
        "## Performance (summed across chunks)",
        f"- Total wall: **{perf['total_wall_s']:.0f} s** ({perf['total_wall_s']/3600:.2f} h)",
        f"- A2: {perf['a2_wall_s']:.0f} s · B1: {perf['b1_wall_s']:.0f} s · B2: {perf['b2_wall_s']:.0f} s "
        f"(engine_native {perf['engine_native_s']:.0f} s)",
        f"- Per-chunk: avg {perf['avg_chunk_wall_s']:.0f} s · max {perf['max_chunk_wall_s']:.0f} s",
        "",
        "## Economic (pooled)",
        f"- candidates: {econ['candidate_count']} · detailed replays: {econ['detailed_replay_count']}",
        f"- executed trades: **{econ['executed_trade_count']}** · stat-validation observations: "
        f"{econ['statistical_validation_observation_count']}",
        f"- B2 final-status counts: {s['b2_final_status_counts']}",
        f"- Pooled Sharpe deflation (PSR/DSR): **{s['pooled_statistical_validation']}** "
        "(compute on the pooled trade set across the full horizon, never per-chunk)",
        "",
        "## Data quality",
        f"- raw-window partial: {s['data_quality']['raw_window_partial']} · "
        f"depth20 missing: {s['data_quality']['depth20_missing']}",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Reduce a chunked backtest into a synthesis — Phase 3.")
    p.add_argument("--run-root", required=True, help="Run root (the <output-root>/<run_id> dir).")
    args = p.parse_args(argv)
    run_root = Path(args.run_root).resolve()
    synthesis = reduce_run(run_root)
    (run_root / "global_synthesis.json").write_text(json.dumps(synthesis, indent=2), encoding="utf-8")
    md = _render_md(synthesis)
    (run_root / "SYNTHESIS.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"[reduce] wrote {run_root / 'global_synthesis.json'} + SYNTHESIS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
