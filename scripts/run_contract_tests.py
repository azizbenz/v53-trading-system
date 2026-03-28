#!/usr/bin/env python3
"""Standalone launcher for Build-1 contract-oriented tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_interface_contracts/",
        "tests/test_contract_test_suite/",
        "-v",
        "--tb=short",
    ]
    result = subprocess.run(command, cwd=repo_root)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
