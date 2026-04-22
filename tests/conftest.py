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
_SCRATCH_ROOT = _TMP_ROOT / "scratch"


def _prune_empty_parents(path: Path) -> None:
    current = path
    while current != _REPO_ROOT:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def make_repo_scratch_dir(namespace: str, label: str | None = None) -> Path:
    """Return a repo-local scratch directory that avoids locked build roots on Windows."""

    _SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    namespace_root = _SCRATCH_ROOT / namespace
    namespace_root.mkdir(parents=True, exist_ok=True)
    stem = uuid4().hex if label is None else f"{label}_{uuid4().hex}"
    case_root = namespace_root / stem
    case_root.mkdir()
    return case_root


def repo_build_path(*parts: str | Path) -> Path:
    """Map repo-local build paths onto the writable shared test root."""

    raw_path = Path(*parts)
    normalized_parts = raw_path.parts
    if normalized_parts and normalized_parts[0] == "build":
        normalized_parts = normalized_parts[1:]
    build_root = _TMP_ROOT / "build"
    build_root.mkdir(parents=True, exist_ok=True)
    return build_root.joinpath(*normalized_parts)


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
