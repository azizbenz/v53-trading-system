from __future__ import annotations

from cockpit.state_decision_trace import read_decision_trace

from ._operational_helpers import build_paths, cleanup_scratch, scratch_dir, seed_phase25_files


def test_decision_trace_parses_latest_jsonl() -> None:
    scratch = scratch_dir("decision_trace_ok")
    try:
        paths = build_paths(scratch)
        seed_phase25_files(paths)
        snapshot = read_decision_trace(paths.auto_exports_root)
        assert snapshot.source_status == "ok"
        assert len(snapshot.entries) == 2
        assert snapshot.entries[-1].selected is True
        assert snapshot.entries[-1].expected_ce == 0.0016
    finally:
        cleanup_scratch(scratch)


def test_decision_trace_handles_missing_and_corrupt_rows() -> None:
    scratch = scratch_dir("decision_trace_missing")
    try:
        paths = build_paths(scratch)
        snapshot = read_decision_trace(paths.auto_exports_root)
        assert snapshot.source_status == "not_yet_persisted"

        seed_phase25_files(paths)
        dtr_path = paths.auto_exports_root / "2026-04-27" / "replay_dtr.jsonl"
        dtr_path.write_text('{"ok":1}\n{bad}\n', encoding="utf-8")
        snapshot = read_decision_trace(paths.auto_exports_root)
        assert snapshot.skipped_corrupt_row_count == 1
    finally:
        cleanup_scratch(scratch)
