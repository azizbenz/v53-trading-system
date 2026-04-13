"""Bounded disk usage sampling for VPS observability."""

from __future__ import annotations

import shutil
from pathlib import Path

from monitoring.contracts import DiskUsageSample


def sample_disk_usage(path: Path) -> DiskUsageSample:
    """Sample disk usage for the volume hosting the given path."""

    resolved = Path(path).resolve()
    usage = shutil.disk_usage(resolved)
    total_bytes = max(1, usage.total)
    used_bytes = max(0, usage.used)
    free_bytes = max(0, usage.free)
    return DiskUsageSample(
        path=str(resolved),
        total_gb=total_bytes / (1024.0 * 1024.0 * 1024.0),
        free_gb=free_bytes / (1024.0 * 1024.0 * 1024.0),
        used_pct=min(100.0, max(0.0, used_bytes / total_bytes * 100.0)),
        sampling_mode="shutil_disk_usage",
    )


__all__ = ["sample_disk_usage"]
