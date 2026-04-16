"""Support helpers for Local IA Lab execution telemetry archive materialization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from local_replay_runtime.local_lab_execution_telemetry_artifact import (
        LocalLabExecutionTelemetryArchive,
        LocalLabExecutionTelemetryArtifact,
        LocalLabExecutionTelemetrySession,
    )

TNumber = TypeVar("TNumber", int, float)


@dataclass(frozen=True)
class _TelemetrySessionBuckets:
    """Grouped telemetry sessions per observable family."""

    time_sync: tuple[LocalLabExecutionTelemetrySession, ...]
    quota: tuple[LocalLabExecutionTelemetrySession, ...]
    websocket: tuple[LocalLabExecutionTelemetrySession, ...]
    spread: tuple[LocalLabExecutionTelemetrySession, ...]
    slippage: tuple[LocalLabExecutionTelemetrySession, ...]
    candidate_size: tuple[LocalLabExecutionTelemetrySession, ...]
    final_size: tuple[LocalLabExecutionTelemetrySession, ...]


def _prefer_nonempty_tuple(
    new_value: tuple[TNumber, ...],
    existing_value: tuple[TNumber, ...],
) -> tuple[TNumber, ...]:
    return new_value if new_value else existing_value


def _prefer_nonempty_text(new_value: str, existing_value: str) -> str:
    return new_value if new_value else existing_value


def _prefer_positive_int(new_value: int, existing_value: int) -> int:
    return new_value if new_value > 0 else existing_value


def _prefer_optional_value(
    new_value: TNumber | None,
    existing_value: TNumber | None,
) -> TNumber | None:
    return new_value if new_value is not None else existing_value


def _merge_caution_flags(
    existing_session: LocalLabExecutionTelemetrySession,
    session: LocalLabExecutionTelemetrySession,
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            existing_session.coverage_caution_flags + session.coverage_caution_flags
        )
    )


def _merge_session(
    existing_session: LocalLabExecutionTelemetrySession,
    session: LocalLabExecutionTelemetrySession,
) -> LocalLabExecutionTelemetrySession:
    from local_replay_runtime.local_lab_execution_telemetry_artifact import (
        LocalLabExecutionTelemetrySession,
    )

    return LocalLabExecutionTelemetrySession(
        session_date=session.session_date,
        time_sync_offsets_ms=_prefer_nonempty_tuple(
            session.time_sync_offsets_ms,
            existing_session.time_sync_offsets_ms,
        ),
        time_sync_source_ref=_prefer_nonempty_text(
            session.time_sync_source_ref,
            existing_session.time_sync_source_ref,
        ),
        quota_call_count=_prefer_positive_int(
            session.quota_call_count,
            existing_session.quota_call_count,
        ),
        quota_probe_duration_s=_prefer_optional_value(
            session.quota_probe_duration_s,
            existing_session.quota_probe_duration_s,
        ),
        quota_limit_calls_per_minute=_prefer_optional_value(
            session.quota_limit_calls_per_minute,
            existing_session.quota_limit_calls_per_minute,
        ),
        quota_calls_per_minute_observed=_prefer_optional_value(
            session.quota_calls_per_minute_observed,
            existing_session.quota_calls_per_minute_observed,
        ),
        quota_source_ref=_prefer_nonempty_text(
            session.quota_source_ref,
            existing_session.quota_source_ref,
        ),
        websocket_interarrival_s=_prefer_nonempty_tuple(
            session.websocket_interarrival_s,
            existing_session.websocket_interarrival_s,
        ),
        websocket_source_ref=_prefer_nonempty_text(
            session.websocket_source_ref,
            existing_session.websocket_source_ref,
        ),
        websocket_source_kind=_prefer_nonempty_text(
            session.websocket_source_kind,
            existing_session.websocket_source_kind,
        ),
        spread_bps=_prefer_nonempty_tuple(session.spread_bps, existing_session.spread_bps),
        spread_source_ref=_prefer_nonempty_text(
            session.spread_source_ref,
            existing_session.spread_source_ref,
        ),
        slippage_bps=_prefer_nonempty_tuple(
            session.slippage_bps,
            existing_session.slippage_bps,
        ),
        slippage_source_ref=_prefer_nonempty_text(
            session.slippage_source_ref,
            existing_session.slippage_source_ref,
        ),
        candidate_sizes=_prefer_nonempty_tuple(
            session.candidate_sizes,
            existing_session.candidate_sizes,
        ),
        candidate_size_source_ref=_prefer_nonempty_text(
            session.candidate_size_source_ref,
            existing_session.candidate_size_source_ref,
        ),
        final_sizes=_prefer_nonempty_tuple(
            session.final_sizes,
            existing_session.final_sizes,
        ),
        final_size_source_ref=_prefer_nonempty_text(
            session.final_size_source_ref,
            existing_session.final_size_source_ref,
        ),
        coverage_caution_flags=_merge_caution_flags(existing_session, session),
    )


def upsert_local_lab_execution_telemetry_archive(
    archive: LocalLabExecutionTelemetryArchive,
    *,
    export_dir: str,
    run_id: str,
    session: LocalLabExecutionTelemetrySession,
) -> LocalLabExecutionTelemetryArchive:
    from local_replay_runtime.local_lab_execution_telemetry_artifact import (
        LocalLabExecutionTelemetryArchive,
    )

    sessions_by_date = {item.session_date: item for item in archive.sessions}
    existing_session = sessions_by_date.get(session.session_date)
    sessions_by_date[session.session_date] = (
        _merge_session(existing_session, session)
        if existing_session is not None
        else session
    )
    ordered_sessions = tuple(
        sessions_by_date[session_date]
        for session_date in sorted(sessions_by_date)
    )
    return LocalLabExecutionTelemetryArchive(
        latest_export_dir=export_dir,
        latest_run_id=run_id,
        sessions=ordered_sessions,
    )


def _bucket_sessions(
    archive: LocalLabExecutionTelemetryArchive,
) -> _TelemetrySessionBuckets:
    return _TelemetrySessionBuckets(
        time_sync=tuple(
            session for session in archive.sessions if session.time_sync_offsets_ms
        ),
        quota=tuple(
            session
            for session in archive.sessions
            if session.quota_call_count > 0
            or session.quota_limit_calls_per_minute is not None
            or session.quota_calls_per_minute_observed is not None
        ),
        websocket=tuple(
            session for session in archive.sessions if session.websocket_interarrival_s
        ),
        spread=tuple(session for session in archive.sessions if session.spread_bps),
        slippage=tuple(session for session in archive.sessions if session.slippage_bps),
        candidate_size=tuple(
            session for session in archive.sessions if session.candidate_sizes
        ),
        final_size=tuple(session for session in archive.sessions if session.final_sizes),
    )


def _session_dates(
    sessions: tuple[LocalLabExecutionTelemetrySession, ...],
) -> tuple[str, ...]:
    return tuple(session.session_date for session in sessions)


def _observation_days(
    sessions: tuple[LocalLabExecutionTelemetrySession, ...],
) -> float | None:
    return float(len(sessions)) if sessions else None


def _unique_source_refs(
    sessions: tuple[LocalLabExecutionTelemetrySession, ...],
    attribute_name: str,
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            getattr(session, attribute_name)
            for session in sessions
            if getattr(session, attribute_name)
        )
    )


def _flatten_float_series(
    sessions: tuple[LocalLabExecutionTelemetrySession, ...],
    attribute_name: str,
) -> tuple[float, ...]:
    return tuple(
        float(value)
        for session in sessions
        for value in getattr(session, attribute_name)
    )


def _flatten_positive_ints(
    sessions: tuple[LocalLabExecutionTelemetrySession, ...],
    attribute_name: str,
) -> tuple[int, ...]:
    return tuple(
        int(value)
        for session in sessions
        if (value := getattr(session, attribute_name)) > 0
    )


def _flatten_optional_ints(
    sessions: tuple[LocalLabExecutionTelemetrySession, ...],
    attribute_name: str,
) -> tuple[int, ...]:
    return tuple(
        int(value)
        for session in sessions
        if (value := getattr(session, attribute_name)) is not None
    )


def _flatten_optional_floats(
    sessions: tuple[LocalLabExecutionTelemetrySession, ...],
    attribute_name: str,
) -> tuple[float, ...]:
    return tuple(
        float(value)
        for session in sessions
        if (value := getattr(session, attribute_name)) is not None
    )


def _build_time_sync_payload(
    buckets: _TelemetrySessionBuckets,
) -> dict[str, object]:
    return {
        "time_sync_offsets_ms": _flatten_float_series(
            buckets.time_sync,
            "time_sync_offsets_ms",
        ),
        "time_sync_observation_days": _observation_days(buckets.time_sync),
        "time_sync_session_dates": _session_dates(buckets.time_sync),
        "time_sync_source_refs": _unique_source_refs(
            buckets.time_sync,
            "time_sync_source_ref",
        ),
    }


def _build_quota_payload(buckets: _TelemetrySessionBuckets) -> dict[str, object]:
    return {
        "quota_call_counts": _flatten_positive_ints(
            buckets.quota,
            "quota_call_count",
        ),
        "quota_probe_durations_s": _flatten_optional_floats(
            buckets.quota,
            "quota_probe_duration_s",
        ),
        "quota_limit_calls_per_minute_values": _flatten_optional_ints(
            buckets.quota,
            "quota_limit_calls_per_minute",
        ),
        "quota_calls_per_minute_observed": _flatten_optional_floats(
            buckets.quota,
            "quota_calls_per_minute_observed",
        ),
        "quota_observation_days": _observation_days(buckets.quota),
        "quota_session_dates": _session_dates(buckets.quota),
        "quota_source_refs": _unique_source_refs(
            buckets.quota,
            "quota_source_ref",
        ),
    }


def _build_websocket_payload(
    buckets: _TelemetrySessionBuckets,
) -> dict[str, object]:
    return {
        "websocket_interarrival_s": _flatten_float_series(
            buckets.websocket,
            "websocket_interarrival_s",
        ),
        "websocket_observation_days": _observation_days(buckets.websocket),
        "websocket_session_dates": _session_dates(buckets.websocket),
        "websocket_source_refs": _unique_source_refs(
            buckets.websocket,
            "websocket_source_ref",
        ),
    }


def _build_metric_payload(
    sessions: tuple[LocalLabExecutionTelemetrySession, ...],
    *,
    metric_field: str,
    observation_field: str,
    session_dates_field: str,
    source_refs_field: str,
    source_ref_attribute: str,
) -> dict[str, object]:
    return {
        metric_field: _flatten_float_series(sessions, metric_field),
        observation_field: _observation_days(sessions),
        session_dates_field: _session_dates(sessions),
        source_refs_field: _unique_source_refs(sessions, source_ref_attribute),
    }


def _collect_caution_flags(
    archive: LocalLabExecutionTelemetryArchive,
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            flag
            for session in archive.sessions
            for flag in session.coverage_caution_flags
        )
    )


def materialize_local_lab_execution_telemetry_artifact(
    archive: LocalLabExecutionTelemetryArchive,
) -> "LocalLabExecutionTelemetryArtifact":
    from local_replay_runtime.local_lab_execution_telemetry_artifact import (
        LocalLabExecutionTelemetryArtifact,
    )

    buckets = _bucket_sessions(archive)
    payload = {
        "export_dir": archive.latest_export_dir,
        "run_id": archive.latest_run_id,
        "source_session_dates": _session_dates(archive.sessions),
        "coverage_caution_flags": _collect_caution_flags(archive),
    }
    payload.update(_build_time_sync_payload(buckets))
    payload.update(_build_quota_payload(buckets))
    payload.update(_build_websocket_payload(buckets))
    payload.update(
        _build_metric_payload(
            buckets.spread,
            metric_field="spread_bps",
            observation_field="spread_observation_days",
            session_dates_field="spread_session_dates",
            source_refs_field="spread_source_refs",
            source_ref_attribute="spread_source_ref",
        )
    )
    payload.update(
        _build_metric_payload(
            buckets.slippage,
            metric_field="slippage_bps",
            observation_field="slippage_observation_days",
            session_dates_field="slippage_session_dates",
            source_refs_field="slippage_source_refs",
            source_ref_attribute="slippage_source_ref",
        )
    )
    payload.update(
        _build_metric_payload(
            buckets.candidate_size,
            metric_field="candidate_sizes",
            observation_field="candidate_size_observation_days",
            session_dates_field="candidate_size_session_dates",
            source_refs_field="candidate_size_source_refs",
            source_ref_attribute="candidate_size_source_ref",
        )
    )
    payload.update(
        _build_metric_payload(
            buckets.final_size,
            metric_field="final_sizes",
            observation_field="final_size_observation_days",
            session_dates_field="final_size_session_dates",
            source_refs_field="final_size_source_refs",
            source_ref_attribute="final_size_source_ref",
        )
    )
    return LocalLabExecutionTelemetryArtifact(**payload)
