"""Fixtures partagees pour tous les tests V5.3."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest

NOW_MS = 1_700_000_000_000  # Timestamp de reference (Nov 2023)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TMP_ROOT = _REPO_ROOT / ".test_tmp" / "shared"


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
    _TMP_ROOT.mkdir(parents=True, exist_ok=True)
    case_root = _TMP_ROOT / f"case_{uuid4().hex}"
    case_root.mkdir()

    try:
        yield case_root
    finally:
        shutil.rmtree(case_root, ignore_errors=True)
        _prune_empty_parents(_TMP_ROOT)
