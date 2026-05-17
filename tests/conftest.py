"""Fixtures partagees pour tous les tests V5.3."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from tests.support_paths import make_repo_scratch_dir, repo_build_path

NOW_MS = 1_700_000_000_000  # Timestamp de reference (Nov 2023)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TMP_ROOT = _REPO_ROOT / ".test_tmp"


def _prune_empty_parents(path: Path) -> None:
    current = path
    while current != _REPO_ROOT:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent

@pytest.fixture
def now_ms():
    return NOW_MS


@pytest.fixture
def valid_pairs():
    return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "LINKUSDT"]


@pytest.fixture
def repo_tmp_path() -> Iterator[Path]:
    """Return a repo-local scratch directory to avoid host temp permission issues."""
    case_root = make_repo_scratch_dir("repo_tmp_fixture", "case")

    try:
        yield case_root
    finally:
        shutil.rmtree(case_root, ignore_errors=True)
        _prune_empty_parents(case_root.parent)
