from __future__ import annotations

import shutil

from monitoring.disk_monitor import sample_disk_usage


def test_sample_disk_usage_projects_gb_and_used_pct(monkeypatch):
    monkeypatch.setattr(
        "monitoring.disk_monitor.shutil.disk_usage",
        lambda path: shutil._ntuple_diskusage(
            total=100 * 1024 * 1024 * 1024,
            used=70 * 1024 * 1024 * 1024,
            free=30 * 1024 * 1024 * 1024,
        ),
    )

    sample = sample_disk_usage("E:/shadow/service")

    assert sample.path
    assert sample.total_gb == 100.0
    assert sample.free_gb == 30.0
    assert sample.used_pct == 70.0
    assert sample.sampling_mode == "shutil_disk_usage"
