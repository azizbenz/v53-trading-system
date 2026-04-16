#!/usr/bin/env python3
"""Standalone launcher for the DAG validator."""

from __future__ import annotations

import sys
from pathlib import Path


def _emit_stdout(message: str) -> None:
    """Emit a launcher message to stdout without using print()."""
    sys.stdout.write(f"{message}\n")


def _emit_stderr(message: str) -> None:
    """Emit a launcher message to stderr without using print()."""
    sys.stderr.write(f"{message}\n")


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root / "src"))

    try:
        from dag_validator import format_report, validate_architecture
    except ModuleNotFoundError as exc:
        _emit_stderr(
            f"Dependency missing: {exc.name}. Install project runtime dependencies first."
        )
        return 2

    report = validate_architecture(src_root=repo_root / "src")
    _emit_stdout(format_report(report))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
