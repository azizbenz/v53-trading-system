from __future__ import annotations

from datetime import datetime, timedelta, timezone
import gzip
from pathlib import Path
import shutil
from uuid import uuid4

from monitoring.log_rotation import rotate_log_file


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("pytest-log-rotation", label)


def test_rotate_log_file_is_noop_below_threshold():
    root = _scratch_dir("below_threshold")
    try:
        log_path = root / "shadow_vps_service.events.jsonl"
        log_path.write_text("short-line\n", encoding="utf-8")

        result = rotate_log_file(
            log_path,
            max_bytes=1024,
            now=datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc),
        )

        assert result.rotated is False
        assert result.compressed_archive_path == ""
        assert result.retained_archive_count == 0
        assert log_path.read_text(encoding="utf-8") == "short-line\n"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_rotate_log_file_compresses_and_truncates_current_log():
    root = _scratch_dir("rotate")
    try:
        log_path = root / "shadow_vps_service.events.jsonl"
        original_text = ("critical-event\n" * 32)
        log_path.write_text(original_text, encoding="utf-8")

        result = rotate_log_file(
            log_path,
            max_bytes=32,
            now=datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc),
        )

        assert result.rotated is True
        archive_path = Path(result.compressed_archive_path)
        assert archive_path.exists()
        assert result.compressed_bytes > 0
        assert log_path.read_bytes() == b""
        with gzip.open(archive_path, "rt", encoding="utf-8") as handle:
            assert handle.read() == original_text
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_rotate_log_file_prunes_old_archives_by_retention():
    root = _scratch_dir("retention")
    try:
        log_path = root / "shadow_vps_service.events.jsonl"
        log_path.write_text("fresh\n", encoding="utf-8")
        old_archive = root / "shadow_vps_service.events.jsonl.20260101T000000Z.gz"
        new_archive = root / "shadow_vps_service.events.jsonl.20260410T000000Z.gz"
        with gzip.open(old_archive, "wt", encoding="utf-8") as handle:
            handle.write("old")
        with gzip.open(new_archive, "wt", encoding="utf-8") as handle:
            handle.write("new")

        old_time = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp()
        new_time = datetime(2026, 4, 10, 0, 0, tzinfo=timezone.utc).timestamp()
        old_archive.touch()
        new_archive.touch()
        old_archive.stat()
        new_archive.stat()
        import os

        os.utime(old_archive, (old_time, old_time))
        os.utime(new_archive, (new_time, new_time))

        result = rotate_log_file(
            log_path,
            max_bytes=1024,
            retention_days=30,
            now=datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc),
        )

        assert result.rotated is False
        assert str(old_archive.resolve()) in result.deleted_archives
        assert old_archive.exists() is False
        assert new_archive.exists() is True
        assert result.retained_archive_count == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)
