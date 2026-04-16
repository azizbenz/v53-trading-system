"""Service-owned execution telemetry archive for Local IA Lab THR-X01 to THR-X05."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from data_backbone.websocket_gateway.injected_stream_loader import (
    load_injected_websocket_frames,
)
from local_replay_runtime.historical_snapshot_loader import load_historical_snapshot_batch
from local_replay_runtime.historical_snapshot_loader import HistoricalMarketEventEnvelope
from local_replay_runtime.local_lab_execution_telemetry_archive_support import (
    materialize_local_lab_execution_telemetry_artifact as _materialize_local_lab_execution_telemetry_artifact,
)
from local_replay_runtime.local_lab_execution_telemetry_archive_support import (
    upsert_local_lab_execution_telemetry_archive as _upsert_local_lab_execution_telemetry_archive,
)
from local_replay_runtime.local_lab_execution_review import LocalLabExecutionTelemetry
from local_replay_runtime.replay_run_manifest import ReplayRunManifest


class LocalLabExecutionTelemetrySession(BaseModel, frozen=True):
    """One dated service-owned execution telemetry contribution."""

    session_date: str = Field(..., min_length=10)
    time_sync_offsets_ms: tuple[float, ...] = ()
    time_sync_source_ref: str = ""
    quota_call_count: int = Field(default=0, ge=0)
    quota_probe_duration_s: float | None = Field(default=None, ge=0.0)
    quota_limit_calls_per_minute: int | None = Field(default=None, ge=1)
    quota_calls_per_minute_observed: float | None = Field(default=None, ge=0.0)
    quota_source_ref: str = ""
    websocket_interarrival_s: tuple[float, ...] = ()
    websocket_source_ref: str = ""
    websocket_source_kind: str = ""
    spread_bps: tuple[float, ...] = ()
    spread_source_ref: str = ""
    slippage_bps: tuple[float, ...] = ()
    slippage_source_ref: str = ""
    candidate_sizes: tuple[float, ...] = ()
    candidate_size_source_ref: str = ""
    final_sizes: tuple[float, ...] = ()
    final_size_source_ref: str = ""
    coverage_caution_flags: tuple[str, ...] = ()


class LocalLabExecutionTelemetryArchive(BaseModel, frozen=True):
    """Persistent archive of per-session execution telemetry."""

    latest_export_dir: str = ""
    latest_run_id: str = ""
    sessions: tuple[LocalLabExecutionTelemetrySession, ...] = ()


class LocalLabExecutionTelemetryArtifact(BaseModel, frozen=True):
    """Service-owned telemetry artifact bindable to a Lab review correlation."""

    export_dir: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    source_session_dates: tuple[str, ...] = ()
    time_sync_offsets_ms: tuple[float, ...] = ()
    time_sync_observation_days: float | None = Field(default=None, ge=0.0)
    time_sync_session_dates: tuple[str, ...] = ()
    time_sync_source_refs: tuple[str, ...] = ()
    quota_call_counts: tuple[int, ...] = ()
    quota_probe_durations_s: tuple[float, ...] = ()
    quota_limit_calls_per_minute_values: tuple[int, ...] = ()
    quota_calls_per_minute_observed: tuple[float, ...] = ()
    quota_observation_days: float | None = Field(default=None, ge=0.0)
    quota_session_dates: tuple[str, ...] = ()
    quota_source_refs: tuple[str, ...] = ()
    websocket_interarrival_s: tuple[float, ...] = ()
    websocket_observation_days: float | None = Field(default=None, ge=0.0)
    websocket_session_dates: tuple[str, ...] = ()
    websocket_source_refs: tuple[str, ...] = ()
    spread_bps: tuple[float, ...] = ()
    spread_observation_days: float | None = Field(default=None, ge=0.0)
    spread_session_dates: tuple[str, ...] = ()
    spread_source_refs: tuple[str, ...] = ()
    slippage_bps: tuple[float, ...] = ()
    slippage_observation_days: float | None = Field(default=None, ge=0.0)
    slippage_session_dates: tuple[str, ...] = ()
    slippage_source_refs: tuple[str, ...] = ()
    candidate_sizes: tuple[float, ...] = ()
    candidate_size_observation_days: float | None = Field(default=None, ge=0.0)
    candidate_size_session_dates: tuple[str, ...] = ()
    candidate_size_source_refs: tuple[str, ...] = ()
    final_sizes: tuple[float, ...] = ()
    final_size_observation_days: float | None = Field(default=None, ge=0.0)
    final_size_session_dates: tuple[str, ...] = ()
    final_size_source_refs: tuple[str, ...] = ()
    coverage_caution_flags: tuple[str, ...] = ()

    def bind_to_review(self, *, correlation_id: str) -> LocalLabExecutionTelemetry:
        return LocalLabExecutionTelemetry(
            correlation_id=correlation_id,
            export_dir=self.export_dir,
            run_id=self.run_id,
            source_session_dates=self.source_session_dates,
            time_sync_offsets_ms=self.time_sync_offsets_ms,
            time_sync_observation_days=self.time_sync_observation_days,
            time_sync_session_dates=self.time_sync_session_dates,
            time_sync_source_refs=self.time_sync_source_refs,
            quota_call_counts=self.quota_call_counts,
            quota_probe_durations_s=self.quota_probe_durations_s,
            quota_limit_calls_per_minute_values=self.quota_limit_calls_per_minute_values,
            quota_calls_per_minute_observed=self.quota_calls_per_minute_observed,
            quota_observation_days=self.quota_observation_days,
            quota_session_dates=self.quota_session_dates,
            quota_source_refs=self.quota_source_refs,
            websocket_interarrival_s=self.websocket_interarrival_s,
            websocket_observation_days=self.websocket_observation_days,
            websocket_session_dates=self.websocket_session_dates,
            websocket_source_refs=self.websocket_source_refs,
            spread_bps=self.spread_bps,
            spread_observation_days=self.spread_observation_days,
            spread_session_dates=self.spread_session_dates,
            spread_source_refs=self.spread_source_refs,
            slippage_bps=self.slippage_bps,
            slippage_observation_days=self.slippage_observation_days,
            slippage_session_dates=self.slippage_session_dates,
            slippage_source_refs=self.slippage_source_refs,
            candidate_sizes=self.candidate_sizes,
            candidate_size_observation_days=self.candidate_size_observation_days,
            candidate_size_session_dates=self.candidate_size_session_dates,
            candidate_size_source_refs=self.candidate_size_source_refs,
            final_sizes=self.final_sizes,
            final_size_observation_days=self.final_size_observation_days,
            final_size_session_dates=self.final_size_session_dates,
            final_size_source_refs=self.final_size_source_refs,
            coverage_caution_flags=self.coverage_caution_flags,
        )


def _load_local_replay_run_manifest(export_dir: Path) -> ReplayRunManifest:
    run_manifest_path = export_dir / "replay_run_manifest.json"
    if not run_manifest_path.is_file():
        raise FileNotFoundError(
            f"Missing governed export replay_run_manifest.json in {export_dir}"
        )
    return ReplayRunManifest.model_validate_json(
        run_manifest_path.read_text(encoding="utf-8")
    )


def load_local_lab_execution_telemetry_archive(
    archive_path: Path,
) -> LocalLabExecutionTelemetryArchive:
    if not archive_path.is_file():
        return LocalLabExecutionTelemetryArchive()
    return LocalLabExecutionTelemetryArchive.model_validate_json(
        archive_path.read_text(encoding="utf-8")
    )


def load_local_lab_execution_telemetry_artifact(
    artifact_path: Path,
) -> LocalLabExecutionTelemetryArtifact:
    return LocalLabExecutionTelemetryArtifact.model_validate_json(
        artifact_path.read_text(encoding="utf-8")
    )


def load_time_sync_probe_payload(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return {"time_sync_offsets_ms": payload}
    if isinstance(payload, dict):
        return dict(payload)
    raise ValueError("Time-sync offsets payload must be a list or mapping")


def load_time_sync_offsets_ms(path: Path) -> tuple[float, ...]:
    payload = load_time_sync_probe_payload(path)
    candidates = payload.get("time_sync_offsets_ms", payload.get("offsets_ms", ()))
    if not isinstance(candidates, list | tuple):
        raise ValueError("Time-sync offsets series must be a list/tuple")
    return tuple(float(value) for value in candidates)


def build_execution_telemetry_session_from_sources(
    *,
    session_date: str,
    websocket_stream_path: Path | None = None,
    snapshot_batch_path: Path | None = None,
    time_sync_offsets_path: Path | None = None,
) -> LocalLabExecutionTelemetrySession:
    if websocket_stream_path is not None and snapshot_batch_path is not None:
        raise ValueError(
            "Execution telemetry session accepts at most one websocket source"
        )

    time_sync_offsets_ms: tuple[float, ...] = ()
    time_sync_source_ref = ""
    quota_call_count = 0
    quota_probe_duration_s: float | None = None
    quota_limit_calls_per_minute: int | None = None
    quota_calls_per_minute_observed: float | None = None
    quota_source_ref = ""
    if time_sync_offsets_path is not None and time_sync_offsets_path.is_file():
        time_sync_payload = load_time_sync_probe_payload(time_sync_offsets_path)
        candidates = time_sync_payload.get(
            "time_sync_offsets_ms",
            time_sync_payload.get("offsets_ms", ()),
        )
        if not isinstance(candidates, list | tuple):
            raise ValueError("Time-sync offsets series must be a list/tuple")
        time_sync_offsets_ms = tuple(float(value) for value in candidates)
        time_sync_source_ref = str(time_sync_offsets_path.resolve())
        quota_call_count = int(
            time_sync_payload.get("rest_call_count", len(time_sync_offsets_ms))
        )
        probe_duration_value = time_sync_payload.get("probe_duration_s")
        if probe_duration_value is not None:
            quota_probe_duration_s = float(probe_duration_value)
        quota_limit_value = time_sync_payload.get("rest_quota_max_calls_per_minute")
        if quota_limit_value is not None:
            quota_limit_calls_per_minute = int(quota_limit_value)
        observed_rate_value = time_sync_payload.get("observed_calls_per_minute")
        if observed_rate_value is not None:
            quota_calls_per_minute_observed = float(observed_rate_value)
        quota_source_ref = time_sync_source_ref

    websocket_interarrival_s: tuple[float, ...] = ()
    websocket_source_ref = ""
    websocket_source_kind = ""
    spread_bps: tuple[float, ...] = ()
    spread_source_ref = ""
    slippage_bps: tuple[float, ...] = ()
    slippage_source_ref = ""
    candidate_sizes: tuple[float, ...] = ()
    candidate_size_source_ref = ""
    final_sizes: tuple[float, ...] = ()
    final_size_source_ref = ""
    coverage_caution_flags: tuple[str, ...] = ()
    if websocket_stream_path is not None and websocket_stream_path.is_file():
        websocket_interarrival_s = derive_websocket_interarrival_s_from_stream(
            websocket_stream_path
        )
        spread_bps = derive_spread_bps_from_stream(websocket_stream_path)
        slippage_bps = derive_slippage_bps_from_stream(websocket_stream_path)
        candidate_sizes = derive_candidate_sizes_from_stream(websocket_stream_path)
        final_sizes = derive_final_sizes_from_stream(websocket_stream_path)
        websocket_source_ref = str(websocket_stream_path.resolve())
        websocket_source_kind = "injected_websocket_stream"
        spread_source_ref = websocket_source_ref
        slippage_source_ref = websocket_source_ref
        candidate_size_source_ref = websocket_source_ref
        final_size_source_ref = websocket_source_ref
    elif snapshot_batch_path is not None and snapshot_batch_path.is_file():
        websocket_interarrival_s = derive_websocket_interarrival_s_from_snapshot_batch(
            snapshot_batch_path
        )
        spread_bps = derive_spread_bps_from_snapshot_batch(snapshot_batch_path)
        slippage_bps = derive_slippage_bps_from_snapshot_batch(snapshot_batch_path)
        candidate_sizes = derive_candidate_sizes_from_snapshot_batch(snapshot_batch_path)
        final_sizes = derive_final_sizes_from_snapshot_batch(snapshot_batch_path)
        websocket_source_ref = str(snapshot_batch_path.resolve())
        websocket_source_kind = "snapshot_batch_accepted_events"
        spread_source_ref = websocket_source_ref
        slippage_source_ref = websocket_source_ref
        candidate_size_source_ref = websocket_source_ref
        final_size_source_ref = websocket_source_ref
        coverage_caution_flags = ("THR-X02_ACCEPTED_EVENTS_ONLY",)

    return LocalLabExecutionTelemetrySession(
        session_date=session_date,
        time_sync_offsets_ms=time_sync_offsets_ms,
        time_sync_source_ref=time_sync_source_ref,
        quota_call_count=quota_call_count,
        quota_probe_duration_s=quota_probe_duration_s,
        quota_limit_calls_per_minute=quota_limit_calls_per_minute,
        quota_calls_per_minute_observed=quota_calls_per_minute_observed,
        quota_source_ref=quota_source_ref,
        websocket_interarrival_s=websocket_interarrival_s,
        websocket_source_ref=websocket_source_ref,
        websocket_source_kind=websocket_source_kind,
        spread_bps=spread_bps,
        spread_source_ref=spread_source_ref,
        slippage_bps=slippage_bps,
        slippage_source_ref=slippage_source_ref,
        candidate_sizes=candidate_sizes,
        candidate_size_source_ref=candidate_size_source_ref,
        final_sizes=final_sizes,
        final_size_source_ref=final_size_source_ref,
        coverage_caution_flags=coverage_caution_flags,
    )


def upsert_local_lab_execution_telemetry_archive(
    archive: LocalLabExecutionTelemetryArchive,
    *,
    export_dir: str,
    run_id: str,
    session: LocalLabExecutionTelemetrySession,
) -> LocalLabExecutionTelemetryArchive:
    return _upsert_local_lab_execution_telemetry_archive(
        archive,
        export_dir=export_dir,
        run_id=run_id,
        session=session,
    )


def materialize_local_lab_execution_telemetry_artifact(
    archive: LocalLabExecutionTelemetryArchive,
) -> LocalLabExecutionTelemetryArtifact:
    return _materialize_local_lab_execution_telemetry_artifact(archive)


def build_local_lab_execution_telemetry_artifact_for_export(
    *,
    export_dir: Path,
    session_date: str,
    websocket_stream_path: Path | None = None,
    snapshot_batch_path: Path | None = None,
    time_sync_offsets_path: Path | None = None,
    existing_archive: LocalLabExecutionTelemetryArchive | None = None,
) -> tuple[LocalLabExecutionTelemetryArchive, LocalLabExecutionTelemetryArtifact]:
    resolved_export_dir = export_dir.resolve()
    run_manifest = _load_local_replay_run_manifest(resolved_export_dir)
    archive = existing_archive or LocalLabExecutionTelemetryArchive()
    session = build_execution_telemetry_session_from_sources(
        session_date=session_date,
        websocket_stream_path=websocket_stream_path,
        snapshot_batch_path=snapshot_batch_path,
        time_sync_offsets_path=time_sync_offsets_path,
    )
    updated_archive = upsert_local_lab_execution_telemetry_archive(
        archive,
        export_dir=str(resolved_export_dir),
        run_id=run_manifest.run_id,
        session=session,
    )
    return updated_archive, materialize_local_lab_execution_telemetry_artifact(
        updated_archive
    )


def derive_websocket_interarrival_s_from_stream(stream_path: Path) -> tuple[float, ...]:
    frames = load_injected_websocket_frames(stream_path)
    return _derive_interarrival_from_timestamps_by_group(
        (
            (frame.endpoint, frame.recv_time)
            for frame in frames
        )
    )


def derive_websocket_interarrival_s_from_snapshot_batch(
    snapshot_batch_path: Path,
) -> tuple[float, ...]:
    batch = load_historical_snapshot_batch(
        snapshot_batch_path,
        source="shadow_vps_execution_telemetry",
    )
    ordered_timestamps_s = sorted(
        envelope.timestamp_ms / 1000.0 for envelope in batch.events
    )
    return tuple(
        max(0.0, current - previous)
        for previous, current in zip(ordered_timestamps_s, ordered_timestamps_s[1:])
    )


def derive_spread_bps_from_stream(stream_path: Path) -> tuple[float, ...]:
    frames = load_injected_websocket_frames(stream_path)
    values: list[float] = []
    for frame in frames:
        derived = _extract_spread_bps(
            payload=dict(frame.payload),
            route_hint_payload=dict(frame.route_hint),
        )
        if derived is not None:
            values.append(derived)
    return tuple(values)


def derive_spread_bps_from_snapshot_batch(snapshot_batch_path: Path) -> tuple[float, ...]:
    batch = load_historical_snapshot_batch(
        snapshot_batch_path,
        source="shadow_vps_execution_telemetry",
    )
    values: list[float] = []
    for envelope in batch.events:
        derived = _extract_event_spread_bps(envelope)
        if derived is not None:
            values.append(derived)
    return tuple(values)


def derive_slippage_bps_from_stream(stream_path: Path) -> tuple[float, ...]:
    frames = load_injected_websocket_frames(stream_path)
    values: list[float] = []
    for frame in frames:
        derived = _extract_route_hint_slippage_bps(dict(frame.route_hint))
        if derived is not None:
            values.append(derived)
    return tuple(values)


def derive_slippage_bps_from_snapshot_batch(
    snapshot_batch_path: Path,
) -> tuple[float, ...]:
    batch = load_historical_snapshot_batch(
        snapshot_batch_path,
        source="shadow_vps_execution_telemetry",
    )
    values: list[float] = []
    for envelope in batch.events:
        if envelope.route_hint.slippage_bps is not None:
            values.append(float(envelope.route_hint.slippage_bps))
    return tuple(values)


def derive_candidate_sizes_from_stream(stream_path: Path) -> tuple[float, ...]:
    frames = load_injected_websocket_frames(stream_path)
    values: list[float] = []
    for frame in frames:
        derived = _extract_route_hint_scalar(dict(frame.route_hint), field_name="candidate_size")
        if derived is not None:
            values.append(derived)
    return tuple(values)


def derive_candidate_sizes_from_snapshot_batch(
    snapshot_batch_path: Path,
) -> tuple[float, ...]:
    batch = load_historical_snapshot_batch(
        snapshot_batch_path,
        source="shadow_vps_execution_telemetry",
    )
    values: list[float] = []
    for envelope in batch.events:
        derived = _extract_envelope_route_hint_scalar(envelope, field_name="candidate_size")
        if derived is not None:
            values.append(derived)
    return tuple(values)


def derive_final_sizes_from_stream(stream_path: Path) -> tuple[float, ...]:
    frames = load_injected_websocket_frames(stream_path)
    values: list[float] = []
    for frame in frames:
        derived = _extract_route_hint_scalar(dict(frame.route_hint), field_name="final_size")
        if derived is not None:
            values.append(derived)
    return tuple(values)


def derive_final_sizes_from_snapshot_batch(
    snapshot_batch_path: Path,
) -> tuple[float, ...]:
    batch = load_historical_snapshot_batch(
        snapshot_batch_path,
        source="shadow_vps_execution_telemetry",
    )
    values: list[float] = []
    for envelope in batch.events:
        derived = _extract_envelope_route_hint_scalar(envelope, field_name="final_size")
        if derived is not None:
            values.append(derived)
    return tuple(values)


def _derive_interarrival_from_timestamps_by_group(
    keyed_timestamps: tuple[tuple[str, float], ...] | list[tuple[str, float]] | object,
) -> tuple[float, ...]:
    grouped: dict[str, list[float]] = {}
    for key, timestamp_s in keyed_timestamps:
        grouped.setdefault(key, []).append(float(timestamp_s))
    gaps: list[float] = []
    for timestamps in grouped.values():
        ordered = sorted(timestamps)
        gaps.extend(
            max(0.0, current - previous)
            for previous, current in zip(ordered, ordered[1:])
        )
    return tuple(gaps)


def _extract_spread_bps(
    *,
    payload: dict[str, object],
    route_hint_payload: dict[str, object],
) -> float | None:
    spread_from_feature = _extract_route_hint_feature_float(
        route_hint_payload,
        feature_key="spread_bps",
    )
    if spread_from_feature is not None:
        return spread_from_feature
    try:
        bid = float(payload["bid"])
        ask = float(payload["ask"])
    except (KeyError, TypeError, ValueError):
        bid = ask = 0.0
    if bid > 0.0 and ask >= bid:
        mid = (bid + ask) / 2.0
        if mid > 0.0:
            return ((ask - bid) / mid) * 10_000.0
    bids = payload.get("bids")
    asks = payload.get("asks")
    if isinstance(bids, list) and isinstance(asks, list) and bids and asks:
        try:
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
        except (TypeError, ValueError, IndexError):
            return None
        if best_bid > 0.0 and best_ask >= best_bid:
            mid = (best_bid + best_ask) / 2.0
            if mid > 0.0:
                return ((best_ask - best_bid) / mid) * 10_000.0
    return None


def _extract_event_spread_bps(
    envelope: HistoricalMarketEventEnvelope,
) -> float | None:
    event = envelope.event
    if hasattr(event, "spread_bps"):
        try:
            value = float(event.spread_bps)
        except (TypeError, ValueError):
            value = None
        else:
            if value >= 0.0:
                return value
    feature_value = envelope.route_hint.feature_values.get("spread_bps")
    try:
        return float(feature_value) if feature_value is not None else None
    except (TypeError, ValueError):
        return None


def _extract_route_hint_slippage_bps(
    route_hint_payload: dict[str, object],
) -> float | None:
    raw = route_hint_payload.get("slippage_bps")
    if raw is None and isinstance(route_hint_payload.get("feature_values"), dict):
        raw = route_hint_payload["feature_values"].get("slippage_bps")
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _extract_route_hint_scalar(
    route_hint_payload: dict[str, object],
    *,
    field_name: str,
) -> float | None:
    raw = route_hint_payload.get(field_name)
    try:
        value = float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None
    if value is None or value < 0.0:
        return None
    return value


def _extract_envelope_route_hint_scalar(
    envelope: HistoricalMarketEventEnvelope,
    *,
    field_name: str,
) -> float | None:
    raw = getattr(envelope.route_hint, field_name, None)
    try:
        value = float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None
    if value is None or value < 0.0:
        return None
    return value


def _extract_route_hint_feature_float(
    route_hint_payload: dict[str, object],
    *,
    feature_key: str,
) -> float | None:
    feature_values = route_hint_payload.get("feature_values")
    if not isinstance(feature_values, dict):
        return None
    raw = feature_values.get(feature_key)
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


__all__ = [
    "LocalLabExecutionTelemetryArchive",
    "LocalLabExecutionTelemetryArtifact",
    "LocalLabExecutionTelemetrySession",
    "build_execution_telemetry_session_from_sources",
    "build_local_lab_execution_telemetry_artifact_for_export",
    "derive_candidate_sizes_from_snapshot_batch",
    "derive_candidate_sizes_from_stream",
    "derive_final_sizes_from_snapshot_batch",
    "derive_final_sizes_from_stream",
    "derive_websocket_interarrival_s_from_snapshot_batch",
    "derive_websocket_interarrival_s_from_stream",
    "derive_slippage_bps_from_snapshot_batch",
    "derive_slippage_bps_from_stream",
    "derive_spread_bps_from_snapshot_batch",
    "derive_spread_bps_from_stream",
    "load_local_lab_execution_telemetry_archive",
    "load_local_lab_execution_telemetry_artifact",
    "load_time_sync_offsets_ms",
    "materialize_local_lab_execution_telemetry_artifact",
    "upsert_local_lab_execution_telemetry_archive",
]
