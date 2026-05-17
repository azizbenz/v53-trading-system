"""Shared repo-local path helpers for test scratch state."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4


_REPO_ROOT = Path(__file__).resolve().parents[1]
_TMP_ROOT = _REPO_ROOT / ".test_tmp"
_SHARED_ROOT = "s"
_ALT_ROOT = "a"
_FALLBACK_PREFIX = "f"
_MAX_COMPONENT_LENGTH = 40


def _short_component(value: str) -> str:
    normalized = value.strip().replace(":", "_")
    if not normalized:
        return "tmp"
    if len(normalized) <= _MAX_COMPONENT_LENGTH:
        return normalized
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]
    candidate = Path(normalized)
    suffix = candidate.suffix
    stem = candidate.stem if suffix else normalized
    prefix = stem[:20].rstrip("._-") or "tmp"
    return f"{prefix}_{digest}{suffix}"


def _normalize_parts(*parts: str | Path) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw_part in parts:
        for item in Path(raw_part).parts:
            if item in {"", "."}:
                continue
            if item == "build" and not normalized:
                continue
            normalized.append(_short_component(str(item)))
    return tuple(normalized)


def _preferred_root(*parts: str) -> Path:
    return _TMP_ROOT.joinpath(*parts)


def _writable_root(kind: str) -> Path:
    candidates = (
        _preferred_root(_SHARED_ROOT, _short_component(kind)),
        _preferred_root(_ALT_ROOT, _short_component(kind)),
        _preferred_root(f"{_FALLBACK_PREFIX}{uuid4().hex[:6]}", _short_component(kind)),
    )
    last_error: Exception | None = None
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    raise PermissionError(f"Unable to create writable test root for {kind}")


def make_repo_scratch_dir(namespace: str, label: str | None = None) -> Path:
    stem = uuid4().hex if label is None else f"{label}_{uuid4().hex[:8]}"
    namespace_name = _short_component(namespace)
    stem_name = _short_component(stem)
    last_error: Exception | None = None
    for base_name in (_SHARED_ROOT, _ALT_ROOT, f"{_FALLBACK_PREFIX}{uuid4().hex[:6]}"):
        candidate_root = _preferred_root(base_name, "scratch")
        candidate_namespace = candidate_root / namespace_name
        case_root = candidate_namespace / stem_name
        try:
            candidate_namespace.mkdir(parents=True, exist_ok=True)
            case_root.mkdir()
            return case_root
        except OSError as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    raise PermissionError(f"Unable to create scratch dir for namespace {namespace}")


def repo_build_path(*parts: str | Path) -> Path:
    normalized_parts = _normalize_parts(*parts)
    last_error: Exception | None = None
    for base_name in (_SHARED_ROOT, _ALT_ROOT):
        candidate_root = _preferred_root(base_name, "build")
        candidate = candidate_root.joinpath(*normalized_parts)
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError as exc:
            last_error = exc
            continue
    fallback_root = _preferred_root(f"{_FALLBACK_PREFIX}{uuid4().hex[:6]}", "build")
    candidate = fallback_root.joinpath(*normalized_parts)
    candidate.parent.mkdir(parents=True, exist_ok=True)
    if last_error is not None:
        return candidate
    return candidate
