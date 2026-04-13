#!/usr/bin/env python3
"""Run executable engineering guardrails and optionally refresh the baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _configure_stdio() -> None:
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")
    stderr = getattr(sys, "stderr", None)
    if stderr is not None and hasattr(stderr, "reconfigure"):
        stderr.reconfigure(encoding="utf-8", errors="replace")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repo-wide engineering guardrails derived from CODEX_PROMPT.md.",
    )
    parser.add_argument(
        "--policy-path",
        type=Path,
        default=Path("config/engineering_guardrails_policy.json"),
        help="JSON policy describing scan roots and thresholds.",
    )
    parser.add_argument(
        "--baseline-path",
        type=Path,
        default=Path("config/engineering_guardrails_baseline.json"),
        help="JSON baseline containing accepted legacy fingerprints.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/engineering_guardrails"),
        help="Directory where the report JSON and summary text are written.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Refresh the baseline to match the current full violation set.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root / "src"))
    args = _parse_args(argv)

    from smoke_bootstrap_recovery.engineering_guardrails import (
        format_engineering_guardrails_summary,
        load_engineering_guardrails_baseline,
        load_engineering_guardrails_policy,
        run_engineering_guardrails,
        write_engineering_guardrails_baseline,
    )

    policy_path = (repo_root / args.policy_path).resolve()
    baseline_path = (repo_root / args.baseline_path).resolve()
    output_dir = (repo_root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    policy = load_engineering_guardrails_policy(policy_path)
    accepted_fingerprints = (
        frozenset()
        if args.write_baseline or not baseline_path.exists()
        else load_engineering_guardrails_baseline(baseline_path)
    )
    report = run_engineering_guardrails(
        repo_root=repo_root,
        policy=policy,
        policy_path=policy_path,
        baseline_path=baseline_path,
        accepted_fingerprints=accepted_fingerprints,
    )

    report_path = output_dir / "engineering_guardrails.report.json"
    summary_path = output_dir / "engineering_guardrails.summary.txt"
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    summary_text = format_engineering_guardrails_summary(report)
    summary_path.write_text(summary_text + "\n", encoding="utf-8")

    if args.write_baseline:
        write_engineering_guardrails_baseline(
            baseline_path,
            policy_path=policy_path,
            report=report,
        )

    sys.stdout.write(f"Engineering guardrails report JSON: {report_path}\n")
    sys.stdout.write(f"Engineering guardrails summary TXT: {summary_path}\n")
    if args.write_baseline:
        sys.stdout.write(f"Engineering guardrails baseline JSON: {baseline_path}\n")
    sys.stdout.write(summary_text + "\n")
    return 0 if report.passed or args.write_baseline else 1


if __name__ == "__main__":
    raise SystemExit(main())
