"""Bounded gzip log rotation with retention for operated monitoring rails."""

from __future__ import annotations

import gzip
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel, Field


class LogRotationResult(BaseModel, frozen=True):
    log_path: str
    rotated: bool = False
    compressed_archive_path: str = ""
    compressed_bytes: int = Field(default=0, ge=0)
    deleted_archives: tuple[str, ...] = ()
    retained_archive_count: int = Field(default=0, ge=0)


def rotate_log_file(
    log_path: Path | str,
    *,
    max_bytes: int,
    retention_days: int = 90,
    now: datetime | None = None,
) -> LogRotationResult:
    """Rotate one log file into a timestamped gzip archive and prune old archives."""

    if max_bytes <= 0:
        raise ValueError("max_bytes must be > 0")
    if retention_days < 0:
        raise ValueError("retention_days must be >= 0")

    resolved = Path(log_path).resolve()
    current_now = now or datetime.now(timezone.utc)
    if current_now.tzinfo is None:
        current_now = current_now.replace(tzinfo=timezone.utc)
    else:
        current_now = current_now.astimezone(timezone.utc)

    rotated = False
    compressed_archive_path = ""
    compressed_bytes = 0
    if resolved.exists() and resolved.is_file() and resolved.stat().st_size >= max_bytes:
        archive_path = _resolve_archive_path(resolved, current_now)
        with resolved.open("rb") as source, gzip.open(archive_path, "wb") as target:
            shutil.copyfileobj(source, target)
        compressed_archive_path = str(archive_path)
        compressed_bytes = archive_path.stat().st_size
        resolved.write_bytes(b"")
        rotated = True

    deleted_archives = _prune_archives(
        resolved,
        retention_days=retention_days,
        now=current_now,
    )
    retained_archive_count = len(_list_archives(resolved))
    return LogRotationResult(
        log_path=str(resolved),
        rotated=rotated,
        compressed_archive_path=compressed_archive_path,
        compressed_bytes=compressed_bytes,
        deleted_archives=deleted_archives,
        retained_archive_count=retained_archive_count,
    )


def _resolve_archive_path(log_path: Path, now: datetime) -> Path:
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    candidate = log_path.with_name(f"{log_path.name}.{stamp}.gz")
    nonce = 1
    while candidate.exists():
        candidate = log_path.with_name(f"{log_path.name}.{stamp}.{nonce}.gz")
        nonce += 1
    return candidate


def _list_archives(log_path: Path) -> tuple[Path, ...]:
    return tuple(sorted(log_path.parent.glob(f"{log_path.name}.*.gz")))


def _prune_archives(
    log_path: Path,
    *,
    retention_days: int,
    now: datetime,
) -> tuple[str, ...]:
    cutoff = now - timedelta(days=retention_days)
    deleted: list[str] = []
    for archive in _list_archives(log_path):
        modified_at = datetime.fromtimestamp(archive.stat().st_mtime, tz=timezone.utc)
        if modified_at <= cutoff:
            archive.unlink(missing_ok=True)
            deleted.append(str(archive))
    return tuple(deleted)


__all__ = ["LogRotationResult", "rotate_log_file"]
