from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from monitoring.shadow_vps_service_log_retrieval import (
    build_shadow_vps_service_recent_events_summary,
    query_shadow_vps_service_events,
)
from monitoring.contracts import ShadowVpsServiceLogQuery
from protocols.shadow_vps_service import ShadowVpsServiceEvent


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("shadow_vps_service_log_retrieval_tests", label)


def _write_events(events_path: Path, events: list[str]) -> None:
    events_path.write_text("\n".join(events) + "\n", encoding="utf-8")


def test_query_shadow_vps_service_events_filters_and_truncates() -> None:
    scratch_dir = _scratch_dir("full_scan")
    try:
        events_path = scratch_dir / "shadow_vps_service.events.jsonl"
        _write_events(
            events_path,
            [
                ShadowVpsServiceEvent(
                    event_type="service_started",
                    timestamp=10.0,
                    message="service started",
                    session_date="2026-04-01",
                ).model_dump_json(),
                ShadowVpsServiceEvent(
                    event_type="shadow_day_completed",
                    timestamp=20.0,
                    message="day 1 completed",
                    session_date="2026-04-01",
                ).model_dump_json(),
                ShadowVpsServiceEvent(
                    event_type="shadow_day_completed",
                    timestamp=40.0,
                    message="day 2 completed",
                    session_date="2026-04-02",
                ).model_dump_json(),
            ],
        )

        result = query_shadow_vps_service_events(
            events_path,
            query=ShadowVpsServiceLogQuery(
                max_events=1,
                event_types=("shadow_day_completed",),
                newest_first=True,
            ),
            timestamp_ms=1_800_000_000_000,
        )

        assert result.scan_mode == "full_scan"
        assert result.status == "info"
        assert result.scan_complete is True
        assert result.matched_event_count == 2
        assert result.returned_event_count == 1
        assert result.truncated is True
        assert result.latest_session_date == "2026-04-02"
        assert result.events[0].message == "day 2 completed"
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


def test_query_shadow_vps_service_events_reports_parse_errors_and_error_filter() -> None:
    scratch_dir = _scratch_dir("error_filter")
    try:
        events_path = scratch_dir / "shadow_vps_service.events.jsonl"
        _write_events(
            events_path,
            [
                ShadowVpsServiceEvent(
                    event_type="service_started",
                    timestamp=10.0,
                    message="service started",
                    session_date="2026-04-01",
                ).model_dump_json(),
                "{not-json",
                ShadowVpsServiceEvent(
                    event_type="shadow_day_failed",
                    timestamp=50.0,
                    message="shadow failed",
                    session_date="2026-04-02",
                    reason_codes=("shadow.recovery.blocked",),
                    error="network timeout",
                ).model_dump_json(),
            ],
        )

        result = query_shadow_vps_service_events(
            events_path,
            query=ShadowVpsServiceLogQuery(
                max_events=5,
                error_only=True,
                contains_text="failed",
            ),
            timestamp_ms=1_800_000_000_000,
        )

        assert result.status == "warning"
        assert result.parse_error_count == 1
        assert result.matched_event_count == 1
        assert result.returned_event_count == 1
        assert result.latest_event_type == "shadow_day_failed"
        assert result.latest_error == "network timeout"
        assert result.events[0].error == "network timeout"
        assert result.events[0].reason_codes == ("shadow.recovery.blocked",)
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


def test_build_shadow_vps_service_recent_events_summary_reads_bounded_tail() -> None:
    scratch_dir = _scratch_dir("tail_recent")
    try:
        events_path = scratch_dir / "shadow_vps_service.events.jsonl"
        _write_events(
            events_path,
            [
                ShadowVpsServiceEvent(
                    event_type="service_started",
                    timestamp=10.0,
                    message="service started",
                    session_date="2026-04-01",
                ).model_dump_json(),
                ShadowVpsServiceEvent(
                    event_type="shadow_day_completed",
                    timestamp=20.0,
                    message="day 1 completed",
                    session_date="2026-04-01",
                ).model_dump_json(),
                ShadowVpsServiceEvent(
                    event_type="shadow_day_failed",
                    timestamp=30.0,
                    message="day 2 failed",
                    session_date="2026-04-02",
                    error="gateway timeout",
                ).model_dump_json(),
            ],
        )

        result = build_shadow_vps_service_recent_events_summary(
            events_path,
            max_events=2,
            timestamp_ms=1_800_000_000_000,
        )

        assert result.scan_mode == "tail_recent"
        assert result.scan_complete is False
        assert result.truncated is True
        assert result.returned_event_count == 2
        assert result.events[0].event_type == "shadow_day_failed"
        assert result.events[1].event_type == "shadow_day_completed"
        assert result.latest_error == "gateway timeout"
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


def test_query_shadow_vps_service_events_matches_reason_codes() -> None:
    scratch_dir = _scratch_dir("reason_codes")
    try:
        events_path = scratch_dir / "shadow_vps_service.events.jsonl"
        _write_events(
            events_path,
            [
                ShadowVpsServiceEvent(
                    event_type="recovery_gate_blocked",
                    timestamp=60.0,
                    message="cycle blocked",
                    reason_codes=("shadow.warmup.blocked",),
                ).model_dump_json(),
            ],
        )

        result = query_shadow_vps_service_events(
            events_path,
            query=ShadowVpsServiceLogQuery(
                max_events=5,
                contains_text="shadow.warmup.blocked",
            ),
            timestamp_ms=1_800_000_000_000,
        )

        assert result.matched_event_count == 1
        assert result.events[0].reason_codes == ("shadow.warmup.blocked",)
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)
