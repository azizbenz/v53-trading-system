"""Phase 2.5 adapter - bounded disk and log growth visibility."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import shutil
from typing import TYPE_CHECKING

from pydantic import BaseModel

from cockpit.state_freshness import OperationalSourceSnapshot, source_stamp

if TYPE_CHECKING:
    from cockpit.state import CockpitPaths


class DiskGrowthSnapshot(OperationalSourceSnapshot):
    disk_used_percent: float = 0.0
    logs_size_mb: float = 0.0
    artifacts_size_mb: float = 0.0
    auto_exports_size_mb: float = 0.0
    oldest_log_date: str | None = None
    retention_policy_present: bool = False
    cleanup_needed: bool = False
    status: str = "unknown"


def read_disk_growth(paths: CockpitPaths) -> DiskGrowthSnapshot:
    """Summarize disk and log growth without mutating anything."""

    stamp = source_stamp(path=paths.service_dir, stale_after_seconds=None)
    service_dir = paths.service_dir
    disk = shutil.disk_usage(service_dir)
    disk_used_percent = 0.0
    if disk.total > 0:
        disk_used_percent = ((disk.total - disk.free) / disk.total) * 100.0
    log_files = [path for path in service_dir.rglob("*") if path.is_file() and _is_log_like(path)]
    logs_size_mb = _size_mb(log_files)
    artifacts_size_mb = _size_mb(
        [path for path in service_dir.rglob("*") if path.is_file() and not _is_log_like(path)]
    )
    auto_exports_size_mb = _size_mb(
        [path for path in paths.auto_exports_root.rglob("*") if path.is_file()]
    )
    oldest_log_date = None
    if log_files:
        oldest = min(log_files, key=lambda path: path.stat().st_mtime)
        oldest_log_date = datetime.fromtimestamp(oldest.stat().st_mtime, tz=UTC).isoformat()
    retention_policy_present = _retention_policy_present()
    if disk_used_percent > 85.0:
        status = "critical"
    elif disk_used_percent >= 75.0:
        status = "warning"
    else:
        status = "ok"
    return DiskGrowthSnapshot(
        source_status=stamp["source_status"],
        source_file=str(paths.service_dir),
        last_modified_at=stamp["last_modified_at"],
        age_seconds=stamp["age_seconds"],
        reason_codes=stamp["reason_codes"],
        disk_used_percent=disk_used_percent,
        logs_size_mb=logs_size_mb,
        artifacts_size_mb=artifacts_size_mb,
        auto_exports_size_mb=auto_exports_size_mb,
        oldest_log_date=oldest_log_date,
        retention_policy_present=retention_policy_present,
        cleanup_needed=disk_used_percent >= 75.0,
        status=status,
    )


def _is_log_like(path: Path) -> bool:
    suffix = path.suffix.lower()
    return suffix in {".log", ".jsonl"} or path.name.endswith(".events.jsonl")


def _size_mb(files: list[Path]) -> float:
    size_bytes = 0
    for path in files:
        try:
            size_bytes += path.stat().st_size
        except OSError:
            continue
    return size_bytes / (1024.0 * 1024.0)


def _retention_policy_present() -> bool:
    config_path = Path(__file__).resolve().parents[1] / "monitoring" / "logging_config.py"
    if not config_path.is_file():
        return False
    try:
        return "RotatingFileHandler" in config_path.read_text(encoding="utf-8")
    except OSError:
        return False


__all__ = ["DiskGrowthSnapshot", "read_disk_growth"]
