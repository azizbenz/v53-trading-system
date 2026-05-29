"""Compact tabular mirrors for large replay artifacts.

JSONL remains the audit/source-of-truth format for the current V5.3 workflow.
This module writes optional table mirrors for faster scans and smaller storage
without changing trading decisions or existing consumers.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel

from interface_contracts.atomic_io import atomic_write_json


TABULAR_MIRROR_SCHEMA_VERSION = "v53.tabular_artifact_mirror.v1"


def _now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def _file_size(path: Path | None) -> int | None:
    if path is None or not path.is_file():
        return None
    try:
        return int(path.stat().st_size)
    except OSError:
        return None


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)
    return str(value)


def _row_to_mapping(row: Any) -> dict[str, Any]:
    if isinstance(row, BaseModel):
        payload = row.model_dump(mode="json")
    elif isinstance(row, dict):
        payload = dict(row)
    else:
        payload = dict(getattr(row, "__dict__", {}) or {})
    return {str(key): _normalize_scalar(value) for key, value in payload.items()}


def _normalize_rows(rows: Iterable[Any]) -> tuple[dict[str, Any], ...]:
    return tuple(_row_to_mapping(row) for row in rows)


def _column_names(rows: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    columns: set[str] = set()
    for row in rows:
        columns.update(row)
    return tuple(sorted(columns))


def _column_values(rows: tuple[dict[str, Any], ...], column: str) -> list[Any]:
    values = [row.get(column) for row in rows]
    non_null = [value for value in values if value is not None]
    if not non_null:
        return values
    if all(isinstance(value, bool) for value in non_null):
        return values
    if all(isinstance(value, int) and not isinstance(value, bool) for value in non_null):
        return values
    if all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in non_null
    ):
        return [None if value is None else float(value) for value in values]
    return [None if value is None else str(value) for value in values]


def _write_columnar_json(path: Path, rows: tuple[dict[str, Any], ...]) -> Path:
    columns = _column_names(rows)
    payload = {
        "schema_version": TABULAR_MIRROR_SCHEMA_VERSION,
        "storage_format": "columnar_json",
        "columns": list(columns),
        "rows": [[row.get(column) for column in columns] for row in rows],
    }
    atomic_write_json(path, payload)
    return path


def _write_parquet(path: Path, rows: tuple[dict[str, Any], ...]) -> tuple[Path, str]:
    import pyarrow as pa  # type: ignore[import-not-found]
    import pyarrow.parquet as pq  # type: ignore[import-not-found]

    path.parent.mkdir(parents=True, exist_ok=True)
    columns = _column_names(rows)
    arrays = [
        pa.array(_column_values(rows, column))
        for column in columns
    ]
    table = pa.Table.from_arrays(arrays, names=list(columns))
    tmp = path.parent / f"{path.name}.tmp_{os.getpid()}_{id(rows)}"
    compression = "zstd"
    try:
        pq.write_table(table, tmp, compression=compression)
    except Exception:
        compression = "snappy"
        pq.write_table(table, tmp, compression=compression)
    os.replace(tmp, path)
    return path, compression


def _pyarrow_available() -> bool:
    try:
        import pyarrow  # noqa: F401
    except Exception:
        return False
    return True


def write_tabular_mirror(
    *,
    rows: Iterable[Any],
    artifact_name: str,
    output_dir: Path,
    source_path: Path | None = None,
    preferred_format: str = "parquet",
) -> dict[str, Any]:
    """Write a compact mirror and return its manifest payload.

    The writer is fail-closed at the artifact level: if Parquet cannot be used,
    it writes a deterministic columnar JSON fallback and records the reason in
    the manifest. Existing JSONL artifacts are never removed or modified.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_rows = _normalize_rows(rows)
    columns = _column_names(normalized_rows)
    source_bytes = _file_size(source_path)
    manifest_path = output_dir / f"{artifact_name}.tabular_manifest.json"
    pyarrow_available = _pyarrow_available()
    storage_format = "columnar_json"
    compression = "none"
    artifact_path = output_dir / f"{artifact_name}.columns.json"
    status = "TABULAR_MIRROR_COLUMNAR_JSON_READY"
    fallback_reason = ""

    if preferred_format.strip().lower() == "parquet" and pyarrow_available:
        try:
            artifact_path, compression = _write_parquet(
                output_dir / f"{artifact_name}.parquet",
                normalized_rows,
            )
            storage_format = "parquet"
            status = "TABULAR_MIRROR_PARQUET_READY"
        except Exception as exc:  # pragma: no cover - defensive fallback
            fallback_reason = f"PARQUET_WRITE_FAILED:{type(exc).__name__}"
            artifact_path = _write_columnar_json(
                output_dir / f"{artifact_name}.columns.json",
                normalized_rows,
            )
    else:
        fallback_reason = (
            "PYARROW_NOT_AVAILABLE"
            if preferred_format.strip().lower() == "parquet"
            else "PARQUET_NOT_REQUESTED"
        )
        artifact_path = _write_columnar_json(artifact_path, normalized_rows)

    mirror_bytes = _file_size(artifact_path)
    manifest = {
        "schema_version": TABULAR_MIRROR_SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "artifact_name": artifact_name,
        "source_path": None if source_path is None else str(source_path.resolve()),
        "mirror_path": str(artifact_path.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "status": status,
        "storage_format": storage_format,
        "compression": compression,
        "pyarrow_available": pyarrow_available,
        "fallback_reason": fallback_reason,
        "row_count": len(normalized_rows),
        "column_count": len(columns),
        "columns": list(columns),
        "source_bytes": source_bytes,
        "mirror_bytes": mirror_bytes,
        "source_to_mirror_size_ratio": (
            None
            if source_bytes is None or mirror_bytes in (None, 0)
            else source_bytes / mirror_bytes
        ),
        "audit_jsonl_preserved": source_path is None or source_path.is_file(),
    }
    atomic_write_json(manifest_path, manifest, indent=2)
    return manifest


def tabular_manifest_path_for_source(source_path: Path) -> Path:
    return source_path.with_name(f"{source_path.stem}.tabular_manifest.json")


def _manifest_matches_source(manifest: dict[str, Any], source_path: Path) -> bool:
    raw_source = manifest.get("source_path")
    if raw_source is None:
        return False
    try:
        return Path(str(raw_source)).resolve() == source_path.resolve()
    except OSError:
        return False


def _read_parquet_rows(path: Path) -> tuple[dict[str, Any], ...]:
    import pyarrow.parquet as pq  # type: ignore[import-not-found]

    table = pq.read_table(path)
    return tuple(dict(row) for row in table.to_pylist())


def read_tabular_mirror_rows_if_ready(source_path: Path) -> tuple[dict[str, Any], ...] | None:
    """Read a source's Parquet mirror only when the manifest proves it is ready."""

    manifest_path = tabular_manifest_path_for_source(source_path)
    if not manifest_path.is_file() or not source_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, TypeError, ValueError):
        return None
    if not isinstance(manifest, dict):
        return None
    if manifest.get("status") != "TABULAR_MIRROR_PARQUET_READY":
        return None
    if manifest.get("storage_format") != "parquet":
        return None
    if not bool(manifest.get("audit_jsonl_preserved")):
        return None
    if not _manifest_matches_source(manifest, source_path):
        return None
    mirror_path = Path(str(manifest.get("mirror_path") or ""))
    if not mirror_path.is_file() or not _pyarrow_available():
        return None
    try:
        return _read_parquet_rows(mirror_path)
    except Exception:
        return None


__all__ = [
    "TABULAR_MIRROR_SCHEMA_VERSION",
    "read_tabular_mirror_rows_if_ready",
    "tabular_manifest_path_for_source",
    "write_tabular_mirror",
]
