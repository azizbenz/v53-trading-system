#!/usr/bin/env python3
"""Compute a governed Shadow gate report from Build-11 artifacts and explicit evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parent
SRC_ROOT = REPO_ROOT / "src"
for candidate in (SCRIPT_ROOT, SRC_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from shadow_gate_check_support import (  # noqa: E402
    GATE_SPECS,
    HARD_VETO_KEYS,
    build_shadow_gate_report,
)


DEFAULT_SESSION_DIR = REPO_ROOT / "build" / "build11_live_websocket_campaign" / "shadow_session"
DEFAULT_OUTPUT_NAME = "shadow_gate_report.json"


def _configure_stdio() -> None:
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")
    stderr = getattr(sys, "stderr", None)
    if stderr is not None and hasattr(stderr, "reconfigure"):
        stderr.reconfigure(encoding="utf-8", errors="replace")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute a governed Shadow gate report.")
    parser.add_argument("--gate-id", required=True, choices=tuple(GATE_SPECS))
    parser.add_argument("--engine-id", required=True)
    parser.add_argument("--shadow-session-dir", type=Path, default=DEFAULT_SESSION_DIR)
    parser.add_argument("--shadow-report-path", type=Path, default=None)
    parser.add_argument("--shadow-session-summary-path", type=Path, default=None)
    parser.add_argument("--shadow-summary-path", type=Path, default=None)
    parser.add_argument("--inputs-json", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--code-commit", default="unknown")
    return parser


def _read_json_mapping(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _resolve_artifact_paths(
    session_dir: Path,
    shadow_report_path: Path | None,
    shadow_session_summary_path: Path | None,
    shadow_summary_path: Path | None,
) -> tuple[Path, Path, Path]:
    return (
        shadow_report_path or session_dir / "local_replay_shadow.shadow_report.json",
        shadow_session_summary_path or session_dir / "local_replay_shadow.shadow_session_summary.json",
        shadow_summary_path or session_dir / "local_replay_shadow.shadow_summary.json",
    )


def run_shadow_gate_check(
    *,
    gate_id: str,
    engine_id: str,
    shadow_session_dir: Path,
    shadow_report_path: Path | None = None,
    shadow_session_summary_path: Path | None = None,
    shadow_summary_path: Path | None = None,
    inputs_json: Path | None = None,
    output_path: Path | None = None,
    code_commit: str = "unknown",
) -> int:
    resolved_shadow_report_path, resolved_session_summary_path, resolved_shadow_summary_path = _resolve_artifact_paths(
        shadow_session_dir,
        shadow_report_path,
        shadow_session_summary_path,
        shadow_summary_path,
    )
    shadow_report = _read_json_mapping(resolved_shadow_report_path)
    shadow_session_summary = _read_json_mapping(resolved_session_summary_path)
    shadow_summary = _read_json_mapping(resolved_shadow_summary_path)
    evidence = _read_json_mapping(inputs_json) if inputs_json is not None else {}
    resolved_output_path = output_path if output_path is not None else shadow_session_dir / DEFAULT_OUTPUT_NAME
    report = build_shadow_gate_report(
        gate_id=gate_id,
        engine_id=engine_id,
        shadow_report=shadow_report,
        shadow_session_summary=shadow_session_summary,
        shadow_summary=shadow_summary,
        evidence=evidence,
        source_paths=tuple(
            path
            for path in (
                resolved_shadow_report_path,
                resolved_session_summary_path,
                resolved_shadow_summary_path,
                inputs_json,
            )
            if path is not None
        ),
        code_commit=code_commit,
    )
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    sys.stdout.write(f"Shadow gate report JSON: {resolved_output_path}\n")
    sys.stdout.write(f"Recommendation: {report['overall_machine_recommendation']}\n")
    return 0 if report["overall_machine_recommendation"] == "PASS_RECOMMENDED" else 2


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    args = _build_parser().parse_args(argv)
    return run_shadow_gate_check(
        gate_id=args.gate_id,
        engine_id=args.engine_id,
        shadow_session_dir=args.shadow_session_dir,
        shadow_report_path=args.shadow_report_path,
        shadow_session_summary_path=args.shadow_session_summary_path,
        shadow_summary_path=args.shadow_summary_path,
        inputs_json=args.inputs_json,
        output_path=args.output,
        code_commit=args.code_commit,
    )


__all__ = ["HARD_VETO_KEYS", "build_shadow_gate_report", "main", "run_shadow_gate_check"]


if __name__ == "__main__":
    raise SystemExit(main())
