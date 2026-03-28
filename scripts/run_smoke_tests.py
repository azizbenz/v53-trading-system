#!/usr/bin/env python3
"""Standalone launcher for the Build-1 smoke suite."""

from __future__ import annotations

import sys
from pathlib import Path


def _configure_stdio() -> None:
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")
    stderr = getattr(sys, "stderr", None)
    if stderr is not None and hasattr(stderr, "reconfigure"):
        stderr.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    _configure_stdio()
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root / "src"))

    try:
        from smoke_bootstrap_recovery import format_smoke_report, run_build1_smoke
    except ModuleNotFoundError as exc:
        print(f"Dependency missing: {exc.name}. Install project runtime dependencies first.")
        return 2

    report = run_build1_smoke()
    print(format_smoke_report(report))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
