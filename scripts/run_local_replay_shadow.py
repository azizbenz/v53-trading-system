#!/usr/bin/env python3
"""Materialize a governed LOCAL_REPLAY -> VPS import -> SHADOW demo run."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parent
SRC_ROOT = REPO_ROOT / "src"
for candidate in (SCRIPT_ROOT, SRC_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from local_replay_shadow_models import LocalReplayShadowArtifacts  # noqa: E402
from local_replay_shadow_payloads import _write_cli_output  # noqa: E402
from local_replay_shadow_session_support import export_local_replay_shadow_run  # noqa: E402


def _configure_stdio() -> None:
    if sys.stdout.encoding is None:
        return
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the governed LOCAL_REPLAY -> SHADOW demo runner."""

    _configure_stdio()
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a governed demo run for the LOCAL_REPLAY -> VPS import -> SHADOW chain."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "build" / "local_replay_shadow",
        help="Directory where the governed run artifacts will be written.",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=None,
        help=(
            "Optional directory containing real local export files "
            "(review_export, feature_bridge, parity_diagnostics, replay_metrics, replay_dtr)."
        ),
    )
    parser.add_argument(
        "--shadow-days",
        type=int,
        default=1,
        help=(
            "Number of governed Shadow day records to materialize in this run. "
            "Each recorded day stays within the 24h no-reset rule."
        ),
    )
    parser.add_argument(
        "--session-date",
        type=str,
        default=None,
        help=(
            "Optional ISO date (YYYY-MM-DD) used as the first governed Shadow day "
            "for this invocation. If omitted, the runner resumes from the next day."
        ),
    )
    parser.add_argument(
        "--execution-runtime-projection-path",
        type=Path,
        default=None,
        help=(
            "Optional Local IA Lab runtime projection artifact. If omitted, the runner "
            "auto-discovers local_lab_execution_runtime_projection.json inside output-dir."
        ),
    )
    parser.add_argument(
        "--regime-lite-assessment-path",
        type=Path,
        default=None,
        help=(
            "Optional typed regime_lite assessment JSON forwarded into governed "
            "Shadow validation. If omitted, the runner auto-discovers "
            "regime_lite_assessment.json inside output-dir."
        ),
    )
    parser.add_argument(
        "--regime-lite-safing-recommendation-path",
        type=Path,
        default=None,
        help=(
            "Optional typed regime_lite safing recommendation JSON forwarded into "
            "governed Shadow validation. If omitted, the runner auto-discovers "
            "regime_lite_safing_recommendation.json inside output-dir."
        ),
    )
    parser.add_argument(
        "--info-stress-assessment-path",
        type=Path,
        default=None,
        help=(
            "Optional typed info_stress assessment JSON forwarded into governed "
            "Shadow validation. If omitted, the runner auto-discovers "
            "info_stress_assessment.json inside output-dir."
        ),
    )
    args = parser.parse_args(argv)

    artifacts = export_local_replay_shadow_run(
        args.output_dir,
        export_dir=args.export_dir,
        shadow_days=max(1, args.shadow_days),
        session_date=args.session_date,
        execution_runtime_projection_path=args.execution_runtime_projection_path,
        regime_lite_assessment_path=args.regime_lite_assessment_path,
        regime_lite_safing_recommendation_path=args.regime_lite_safing_recommendation_path,
        info_stress_assessment_path=args.info_stress_assessment_path,
    )
    output_lines: list[str] = []
    if artifacts.run_manifest_json_path is not None:
        output_lines.append(f"Run manifest JSON: {artifacts.run_manifest_json_path}")
    output_lines.extend(
        (
            f"Replay plan JSON: {artifacts.replay_plan_json_path}",
            f"Import summary JSON: {artifacts.import_summary_json_path}",
            f"Local replay evidence JSON: {artifacts.local_replay_evidence_json_path}",
            f"Baseline payload JSON: {artifacts.baseline_payload_json_path}",
            f"Candidate payload JSON: {artifacts.candidate_payload_json_path}",
            f"Shadow input JSON: {artifacts.shadow_input_json_path}",
            f"Shadow runtime evidence JSON: {artifacts.shadow_runtime_evidence_json_path}",
            f"Shadow summary JSON: {artifacts.shadow_summary_json_path}",
            f"Shadow day record JSON: {artifacts.shadow_day_record_json_path}",
            f"Shadow report JSON: {artifacts.shadow_report_json_path}",
            f"Shadow days dir: {artifacts.shadow_days_dir_path}",
            f"Shadow session summary JSON: {artifacts.shadow_session_summary_json_path}",
            f"Shadow session registry JSON: {artifacts.shadow_session_registry_json_path}",
            "Inspect the JSON sidecars to review the governed LOCAL_REPLAY -> VPS import -> SHADOW chain.",
        )
    )
    _write_cli_output(tuple(output_lines))
    return 0


__all__ = ["LocalReplayShadowArtifacts", "export_local_replay_shadow_run", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
