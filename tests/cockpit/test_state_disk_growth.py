from __future__ import annotations

from collections import namedtuple

from cockpit.state_disk_growth import read_disk_growth

from ._operational_helpers import build_paths, cleanup_scratch, scratch_dir


def test_disk_growth_reports_warning_and_sizes(monkeypatch) -> None:
    scratch = scratch_dir("disk_growth_warning")
    try:
        paths = build_paths(scratch)
        (paths.service_dir / "shadow_vps_service.events.jsonl").write_text("x" * 1024, encoding="utf-8")
        export_dir = paths.auto_exports_root / "2026-04-27"
        export_dir.mkdir(parents=True, exist_ok=True)
        (export_dir / "replay_metrics.json").write_text("{}", encoding="utf-8")
        usage = namedtuple("usage", "total used free")
        monkeypatch.setattr("cockpit.state_disk_growth.shutil.disk_usage", lambda _: usage(100, 80, 20))
        snapshot = read_disk_growth(paths)
        assert snapshot.status == "warning"
        assert snapshot.logs_size_mb > 0
    finally:
        cleanup_scratch(scratch)


def test_disk_growth_reports_critical_threshold(monkeypatch) -> None:
    scratch = scratch_dir("disk_growth_critical")
    try:
        paths = build_paths(scratch)
        usage = namedtuple("usage", "total used free")
        monkeypatch.setattr("cockpit.state_disk_growth.shutil.disk_usage", lambda _: usage(100, 90, 10))
        snapshot = read_disk_growth(paths)
        assert snapshot.status == "critical"
    finally:
        cleanup_scratch(scratch)
