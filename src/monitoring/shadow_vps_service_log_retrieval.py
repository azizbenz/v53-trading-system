"""Bounded retrieval helpers over durable Shadow VPS service JSONL events."""

from __future__ import annotations

from collections import deque
from pathlib import Path

from interface_contracts import ProfileId, RuntimeMode
from interface_contracts.shadow_vps_service_contracts import ShadowVpsServiceEvent
from monitoring.contracts import (
    ProjectionStatus,
    ShadowVpsServiceLogEventProjection,
    ShadowVpsServiceLogQuery,
    ShadowVpsServiceLogQueryResult,
)


def _project_event(event: ShadowVpsServiceEvent) -> ShadowVpsServiceLogEventProjection:
    return ShadowVpsServiceLogEventProjection(
        event_type=event.event_type,
        timestamp_ms=max(0, int(event.timestamp * 1000.0)),
        message=event.message,
        session_date=event.session_date,
        export_dir_ref=event.export_dir_ref,
        accepted=event.accepted,
        consecutive_days=event.consecutive_days,
        remaining_days=event.remaining_days,
        live_capture_summary_ref=event.live_capture_summary_ref,
        emitted_message_count=event.emitted_message_count,
        accepted_message_count=event.accepted_message_count,
        ignored_message_count=event.ignored_message_count,
        rejected_message_count=event.rejected_message_count,
        pair_scope=event.pair_scope,
        event_types=event.event_types,
        reason_codes=event.reason_codes,
        error=event.error,
    )


def _event_matches_query(
    event: ShadowVpsServiceLogEventProjection,
    query: ShadowVpsServiceLogQuery,
) -> bool:
    if query.event_types and event.event_type not in set(query.event_types):
        return False
    if query.session_date and event.session_date != query.session_date:
        return False
    if query.since_timestamp_ms is not None and event.timestamp_ms < query.since_timestamp_ms:
        return False
    if query.error_only and not event.error:
        return False
    if query.contains_text:
        needle = query.contains_text.casefold()
        haystacks = (
            event.message.casefold(),
            event.error.casefold(),
            event.event_type.casefold(),
            event.session_date.casefold(),
            " ".join(reason.casefold() for reason in event.reason_codes),
        )
        if not any(needle in haystack for haystack in haystacks):
            return False
    return True


def _read_tail_lines(path: Path, max_lines: int) -> tuple[list[str], bool]:
    if max_lines <= 0 or not path.is_file():
        return [], False
    with path.open("rb") as handle:
        handle.seek(0, 2)
        position = handle.tell()
        if position <= 0:
            return [], False
        buffer = b""
        chunk_size = 4096
        while position > 0 and buffer.count(b"\n") <= max_lines:
            read_size = min(chunk_size, position)
            position -= read_size
            handle.seek(position)
            buffer = handle.read(read_size) + buffer
        truncated = position > 0
    lines = [line.decode("utf-8", errors="replace") for line in buffer.splitlines()]
    truncated = truncated or len(lines) > max_lines
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    return [line for line in lines if line.strip()], truncated


def _build_status(
    *,
    file_missing: bool,
    parse_error_count: int,
    latest_error: str,
) -> ProjectionStatus:
    if file_missing:
        return "warning"
    if latest_error:
        return "warning"
    if parse_error_count > 0:
        return "warning"
    return "info"


def query_shadow_vps_service_events(
    events_path: str | Path,
    *,
    query: ShadowVpsServiceLogQuery | None = None,
    timestamp_ms: int,
) -> ShadowVpsServiceLogQueryResult:
    """Run a bounded full-scan query over the durable Shadow VPS event log."""

    query = query or ShadowVpsServiceLogQuery()
    resolved_events_path = Path(events_path)
    if not resolved_events_path.is_file():
        detail = f"Shadow VPS service events file is missing: {resolved_events_path}"
        return ShadowVpsServiceLogQueryResult(
            timestamp_ms=timestamp_ms,
            correlation_id="shadow-vps-service-log-query",
            profile=ProfileId.COMPLETE,
            runtime_mode=RuntimeMode.SHADOW,
            status="warning",
            detail=detail,
            scan_mode="full_scan",
            scan_complete=False,
            events_path=str(resolved_events_path),
            query=query,
        )

    matched_events: deque[ShadowVpsServiceLogEventProjection] = deque(maxlen=query.max_events)
    scanned_line_count = 0
    parsed_event_count = 0
    parse_error_count = 0
    matched_event_count = 0
    latest_event_type = ""
    latest_session_date = ""
    latest_error = ""
    with resolved_events_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            scanned_line_count += 1
            try:
                event = ShadowVpsServiceEvent.model_validate_json(raw_line)
            except ValueError:
                parse_error_count += 1
                continue
            parsed_event_count += 1
            projected = _project_event(event)
            if not _event_matches_query(projected, query):
                continue
            matched_event_count += 1
            latest_event_type = projected.event_type
            latest_session_date = projected.session_date
            if projected.error:
                latest_error = projected.error
            matched_events.append(projected)

    events = list(matched_events)
    if query.newest_first:
        events.reverse()
    truncated = matched_event_count > len(events)
    detail = (
        f"scan=full_scan / matched={matched_event_count} / returned={len(events)} / "
        f"parse_errors={parse_error_count}"
    )
    return ShadowVpsServiceLogQueryResult(
        timestamp_ms=timestamp_ms,
        correlation_id="shadow-vps-service-log-query",
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.SHADOW,
        status=_build_status(
            file_missing=False,
            parse_error_count=parse_error_count,
            latest_error=latest_error,
        ),
        detail=detail,
        scan_mode="full_scan",
        scan_complete=True,
        events_path=str(resolved_events_path.resolve()),
        query=query,
        scanned_line_count=scanned_line_count,
        parsed_event_count=parsed_event_count,
        parse_error_count=parse_error_count,
        matched_event_count=matched_event_count,
        returned_event_count=len(events),
        truncated=truncated,
        latest_event_type=latest_event_type,
        latest_session_date=latest_session_date,
        latest_error=latest_error,
        events=tuple(events),
    )


def build_shadow_vps_service_recent_events_summary(
    events_path: str | Path,
    *,
    max_events: int = 20,
    timestamp_ms: int,
) -> ShadowVpsServiceLogQueryResult:
    """Read only the recent tail of the Shadow VPS event log for cheap service summaries."""

    query = ShadowVpsServiceLogQuery(max_events=max_events, newest_first=True)
    resolved_events_path = Path(events_path)
    if not resolved_events_path.is_file():
        detail = f"Shadow VPS service events file is missing: {resolved_events_path}"
        return ShadowVpsServiceLogQueryResult(
            timestamp_ms=timestamp_ms,
            correlation_id="shadow-vps-service-log-tail",
            profile=ProfileId.COMPLETE,
            runtime_mode=RuntimeMode.SHADOW,
            status="warning",
            detail=detail,
            scan_mode="tail_recent",
            scan_complete=False,
            events_path=str(resolved_events_path),
            query=query,
        )

    raw_lines, truncated_to_tail = _read_tail_lines(resolved_events_path, max_events)
    events: list[ShadowVpsServiceLogEventProjection] = []
    parse_error_count = 0
    latest_error = ""
    latest_event_type = ""
    latest_session_date = ""
    for raw_line in raw_lines:
        try:
            event = ShadowVpsServiceEvent.model_validate_json(raw_line)
        except ValueError:
            parse_error_count += 1
            continue
        projected = _project_event(event)
        events.append(projected)
        latest_event_type = projected.event_type
        latest_session_date = projected.session_date
        if projected.error:
            latest_error = projected.error
    events.reverse()
    detail = (
        f"scan=tail_recent / returned={len(events)} / "
        f"tail_truncated={truncated_to_tail} / parse_errors={parse_error_count}"
    )
    return ShadowVpsServiceLogQueryResult(
        timestamp_ms=timestamp_ms,
        correlation_id="shadow-vps-service-log-tail",
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.SHADOW,
        status=_build_status(
            file_missing=False,
            parse_error_count=parse_error_count,
            latest_error=latest_error,
        ),
        detail=detail,
        scan_mode="tail_recent",
        scan_complete=not truncated_to_tail,
        events_path=str(resolved_events_path.resolve()),
        query=query,
        scanned_line_count=len(raw_lines),
        parsed_event_count=len(events),
        parse_error_count=parse_error_count,
        matched_event_count=len(events),
        returned_event_count=len(events),
        truncated=truncated_to_tail,
        latest_event_type=latest_event_type,
        latest_session_date=latest_session_date,
        latest_error=latest_error,
        events=tuple(events),
    )


__all__ = [
    "build_shadow_vps_service_recent_events_summary",
    "query_shadow_vps_service_events",
]
