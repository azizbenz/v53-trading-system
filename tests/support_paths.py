"""Shared repo-local path helpers for test scratch state."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4


_REPO_ROOT = Path(__file__).resolve().parents[1]
_TMP_ROOT = _REPO_ROOT / ".test_tmp" / "shared"
_SCRATCH_ROOT = _TMP_ROOT / "scratch"
_BUILD_ROOT = _TMP_ROOT / "build"


def make_repo_scratch_dir(namespace: str, label: str | None = None) -> Path:
    _SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    namespace_root = _SCRATCH_ROOT / namespace
    namespace_root.mkdir(parents=True, exist_ok=True)
    stem = uuid4().hex if label is None else f"{label}_{uuid4().hex}"
    case_root = namespace_root / stem
    case_root.mkdir()
    return case_root


def repo_build_path(*parts: str | Path) -> Path:
    raw_path = Path(*parts)
    normalized_parts = raw_path.parts
    if normalized_parts and normalized_parts[0] == "build":
        normalized_parts = normalized_parts[1:]
    _BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    return _BUILD_ROOT.joinpath(*normalized_parts)
