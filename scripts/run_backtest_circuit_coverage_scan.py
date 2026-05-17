"""Slice 1 adapter — Run-Class Component Coverage scan over a phased K: workflow.

This wraps the existing `run_class_component_coverage` builder (which expects a
flat output_root) by staging the canonical artifacts from a phased workflow tree
(`phase_a2_data_factory/...`, `phase_b2_detailed_replay/.../backtest_strategy_ladder/<run_id>/`)
into a temporary flat layout, invoking the builder, then writing the resulting
`run_class_component_coverage.{json,md}` into the workflow's reports directory.

This is the Slice 1 minimal deliverable for the
RUN_BACKTEST_CIRCUIT_COVERAGE_SCAN action surfaced by the engine_no_trade_diagnosis.
Phases 1, 5, 6, 7, 8 of docs/V53_BACKTEST_CIRCUIT_COVERAGE_SCAN_PROMPT.md are out
of scope for Slice 1.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_replay_runtime.run_class_component_coverage import (  # noqa: E402
    build_run_class_component_coverage,
)


def _locate_artifacts(workflow_root: Path) -> dict[str, object]:
    """Find canonical artifacts inside a phased workflow tree."""
    a2 = workflow_root / "phase_a2_data_factory"
    b2 = workflow_root / "phase_b2_detailed_replay"
    b2_ladder = b2 / "backtest_strategy_ladder"
    run_dirs: list[Path] = []
    if b2_ladder.exists():
        run_dirs = sorted(
            (p for p in b2_ladder.iterdir() if p.is_dir()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    run_dir = run_dirs[0] if run_dirs else None
    return {
        "data_factory_manifest": a2 / "data_factory_manifest.json",
        "backtest_proof_matrix": a2 / "backtest_proof_matrix.json",
        "gold_feature_manifest": a2 / "gold_feature_manifest.json",
        "run_dir": run_dir,
        "run_id": run_dir.name if run_dir else "",
    }


def _stage_flat_layout(staging_root: Path, artifacts: dict[str, object]) -> None:
    """Copy the phased artifacts into the flat layout the builder expects."""
    staging_root.mkdir(parents=True, exist_ok=True)
    for key in ("data_factory_manifest", "backtest_proof_matrix", "gold_feature_manifest"):
        src = artifacts.get(key)
        if isinstance(src, Path) and src.is_file():
            shutil.copy2(src, staging_root / src.name)
    run_dir = artifacts.get("run_dir")
    run_id = str(artifacts.get("run_id") or "")
    if isinstance(run_dir, Path) and run_dir.is_dir() and run_id:
        staged_run = staging_root / "backtest_strategy_ladder" / run_id
        if staged_run.exists():
            shutil.rmtree(staged_run)
        shutil.copytree(run_dir, staged_run)


def _render_markdown(payload: dict[str, object], workflow_root: Path) -> str:
    run_id = str(payload.get("run_id") or "")
    run_class = str(payload.get("run_class") or "")
    run_class_id = str(payload.get("run_class_id") or "")
    ml_mode = str(payload.get("ml_mode") or "")
    counts = payload.get("component_status_counts") or {}
    components = payload.get("components") or ()

    lines: list[str] = []
    lines.append("# Run-Class Component Coverage (Slice 1)")
    lines.append("")
    lines.append(f"- workflow_root: `{workflow_root}`")
    lines.append(f"- run_id: `{run_id}`")
    lines.append(f"- run_class: `{run_class}`")
    lines.append(f"- run_class_id: `{run_class_id}`")
    lines.append(f"- ml_mode: `{ml_mode}`")
    lines.append(f"- generated_at: `{datetime.now(tz=UTC).isoformat(timespec='seconds')}`")
    lines.append("")

    lines.append("## Status counts")
    lines.append("")
    if isinstance(counts, dict) and counts:
        lines.append("| status | count |")
        lines.append("|---|---|")
        for status, count in sorted(counts.items(), key=lambda kv: (-int(kv[1]), kv[0])):
            lines.append(f"| `{status}` | {int(count)} |")
    else:
        lines.append("_(no components)_")
    lines.append("")

    lines.append("## Components by family")
    lines.append("")
    by_family: dict[str, list[dict[str, object]]] = {}
    for entry in components:
        if not isinstance(entry, dict):
            continue
        family = str(entry.get("component_family") or "unknown")
        by_family.setdefault(family, []).append(entry)
    for family in sorted(by_family):
        lines.append(f"### {family}")
        lines.append("")
        lines.append("| component_id | expected | invoked | status | proof_artifact | reason_codes |")
        lines.append("|---|---|---|---|---|---|")
        for entry in sorted(
            by_family[family], key=lambda e: str(e.get("component_id") or "")
        ):
            cid = str(entry.get("component_id") or "")
            expected = "yes" if entry.get("expected_for_run_class") else "no"
            invoked = "yes" if entry.get("invoked") else "no"
            status = str(entry.get("status") or "")
            proof = str(entry.get("proof_artifact") or "")
            reasons = entry.get("reason_codes") or ()
            if isinstance(reasons, (list, tuple)):
                reasons_str = ", ".join(str(r) for r in reasons) or "-"
            else:
                reasons_str = str(reasons)
            lines.append(
                f"| `{cid}` | {expected} | {invoked} | `{status}` | `{proof}` | {reasons_str} |"
            )
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append(
        "- Slice 1 output. Phases 1/5/6/7/8 of "
        "`docs/V53_BACKTEST_CIRCUIT_COVERAGE_SCAN_PROMPT.md` not yet implemented."
    )
    lines.append(
        "- Components list is hard-coded in "
        "`src/local_replay_runtime/run_class_component_coverage.py` "
        "(no static-scan discovery yet)."
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build run-class component coverage from a phased workflow output. "
            "Slice 1 wrapper for the existing run_class_component_coverage builder."
        )
    )
    parser.add_argument(
        "--workflow-root",
        required=True,
        type=Path,
        help="Path to a strategy_ladder_workflow-* directory (contains phase_a2_data_factory/, phase_b2_detailed_replay/).",
    )
    parser.add_argument(
        "--reports-dir",
        default=None,
        type=Path,
        help="Where to write the JSON + MD. Defaults to the B2 reports/ directory.",
    )
    parser.add_argument(
        "--staging-root",
        default=None,
        type=Path,
        help="Staging directory. Defaults to build/circuit_coverage_staging/<run_id>.",
    )
    parser.add_argument("--ml-mode", default="ML_MODE_OFF")
    parser.add_argument(
        "--print-summary",
        action="store_true",
        help="Print a short summary to stdout.",
    )
    args = parser.parse_args(argv)

    workflow_root = args.workflow_root.resolve()
    if not workflow_root.is_dir():
        print(f"ERROR: --workflow-root not a directory: {workflow_root}", file=sys.stderr)
        return 2

    artifacts = _locate_artifacts(workflow_root)
    run_dir = artifacts.get("run_dir")
    run_id = str(artifacts.get("run_id") or "")
    if not isinstance(run_dir, Path) or not run_id:
        print(
            "ERROR: no phase_b2_detailed_replay/backtest_strategy_ladder/<run_id> directory found.",
            file=sys.stderr,
        )
        return 3

    staging_root = (
        args.staging_root.resolve()
        if args.staging_root
        else REPO_ROOT / "build" / "circuit_coverage_staging" / run_id
    )
    _stage_flat_layout(staging_root, artifacts)

    matrix = build_run_class_component_coverage(
        output_root=staging_root,
        run_id=run_id,
        ml_mode=args.ml_mode,
    )

    reports_dir = (
        args.reports_dir.resolve() if args.reports_dir else run_dir / "reports"
    )
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload = matrix.model_dump(mode="json")
    json_path = reports_dir / "run_class_component_coverage.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path = reports_dir / "run_class_component_coverage.md"
    md_path.write_text(_render_markdown(payload, workflow_root), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    if args.print_summary:
        print(f"run_class: {matrix.run_class}")
        print(f"run_class_id: {matrix.run_class_id}")
        print(f"ml_mode: {matrix.ml_mode}")
        print("status_counts:")
        for status, count in sorted(
            (matrix.component_status_counts or {}).items(),
            key=lambda kv: (-int(kv[1]), kv[0]),
        ):
            print(f"  {status:55s} {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
