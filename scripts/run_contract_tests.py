#!/usr/bin/env python3
"""Lanceur standalone des contract tests."""
import subprocess, sys
result = subprocess.run(["python", "-m", "pytest", "tests/test_interface_contracts/", "-v"], cwd=".")
sys.exit(result.returncode)
