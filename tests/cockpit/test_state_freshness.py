from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os

from cockpit.state_freshness import read_source_freshness

from ._operational_helpers import (
    build_paths,
    cleanup_scratch,
    scratch_dir,
    seed_phase25_files,
)


def test_source_freshness_reports_ok_stale_missing_and_parse_error() -> None:
    scratch = scratch_dir("state_freshness")
    try:
        paths = build_paths(scratch)
        seed_phase25_files(paths)
        old_mtime = (datetime.now(tz=UTC) - timedelta(hours=2)).timestamp()
        os.utime(paths.warmup_summary, (old_mtime, old_mtime))
        (paths.auto_exports_root / "2026-04-27" / "feature_bridge.json").write_text(
            "{bad json",
            encoding="utf-8",
        )
        lab_bundle = paths.build_root / "local_lab_analysis_real" / "post_trade_review" / "meta_learning_review.bundle.json"
        lab_bundle.unlink()

        snapshot = read_source_freshness(paths)
        statuses = {entry.source_name: entry.status for entry in snapshot.sources}

        assert statuses["service_state"] == "ok"
        assert statuses["warmup_summary"] == "stale"
        assert statuses["lab_review_bundle"] == "missing"
        assert statuses["feature_bridge"] == "parse_error"
    finally:
        cleanup_scratch(scratch)
