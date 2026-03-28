"""Repo-safe fixtures for DAG validator tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import shutil
from uuid import uuid4

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_TMP_ROOT = _REPO_ROOT / ".test_tmp" / "dag_validator"


def _prune_empty_parents(path: Path) -> None:
    current = path
    while current != _REPO_ROOT:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


@pytest.fixture
def isolated_tmp_path() -> Iterator[Path]:
    """Return a repo-local scratch directory for filesystem DAG tests."""
    _TMP_ROOT.mkdir(parents=True, exist_ok=True)
    case_root = _TMP_ROOT / f"case_{uuid4().hex}"
    case_root.mkdir()

    try:
        yield case_root
    finally:
        shutil.rmtree(case_root, ignore_errors=True)
        _prune_empty_parents(_TMP_ROOT)
