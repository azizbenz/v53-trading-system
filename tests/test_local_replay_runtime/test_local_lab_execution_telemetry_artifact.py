from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

import pytest

from local_replay_runtime.local_lab_execution_telemetry_artifact import (
    LocalLabExecutionTelemetryArchive,
    build_execution_telemetry_session_from_sources,
    derive_candidate_sizes_from_snapshot_batch,
    derive_candidate_sizes_from_stream,
    derive_final_sizes_from_snapshot_batch,
    derive_final_sizes_from_stream,
    derive_slippage_bps_from_snapshot_batch,
    derive_slippage_bps_from_stream,
    derive_spread_bps_from_snapshot_batch,
    derive_spread_bps_from_stream,
    derive_websocket_interarrival_s_from_snapshot_batch,
    derive_websocket_interarrival_s_from_stream,
    materialize_local_lab_execution_telemetry_artifact,
    upsert_local_lab_execution_telemetry_archive,
)
from tests.support_paths import repo_build_path


def _scratch_dir() -> Path:
    return repo_build_path("pytest-local-lab-execution-telemetry", uuid4().hex)


def _write_stream(path: Path) -> None:
    path.write_text(
        "\n".join(
            (
                json.dumps(
                    {
                        "endpoint": "wss://shadow.injected",
                        "pair": "BTCUSDT",
                        "stream_type": "snapshot",
                        "payload": {
                            "snapshot_type": "ticker",
                            "last_price": 43250.0,
                            "bid": 43249.5,
                            "ask": 43250.5,
                            "volume_24h": 125000.0,
                        },
                        "recv_time": 1_700_000_000.0,
                        "source": "binance",
                        "route_hint": {
                            "route_id": "btc-live-1",
                            "engine_id": "engine_a",
                            "slippage_bps": 2.5,
                            "candidate_size": 10.0,
                            "final_size": 9.0,
                        },
                    }
                ),
                json.dumps(
                    {
                        "endpoint": "wss://shadow.injected",
                        "pair": "BTCUSDT",
                        "stream_type": "snapshot",
                        "payload": {
                            "snapshot_type": "ticker",
                            "last_price": 43255.0,
                            "bid": 43254.5,
                            "ask": 43255.5,
                            "volume_24h": 125100.0,
                        },
                        "recv_time": 1_700_000_060.0,
                        "source": "binance",
                        "route_hint": {
                            "route_id": "btc-live-2",
                            "engine_id": "engine_a",
                            "slippage_bps": 3.0,
                            "candidate_size": 12.0,
                            "final_size": 11.0,
                        },
                    }
                ),
            )
        ),
        encoding="utf-8",
    )


def _write_snapshot_batch(path: Path) -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "event_type": "snapshot",
                    "event": {
                        "timestamp_ms": 1_700_000_120_000,
                        "pair": "BTCUSDT",
                        "last_price": 43250.0,
                        "bid": 43249.5,
                        "ask": 43250.5,
                        "volume_24h": 125000.0,
                    },
                    "route_hint": {
                        "route_id": "btc-live",
                        "engine_id": "engine_a",
                        "slippage_bps": 1.5,
                        "candidate_size": 8.0,
                        "final_size": 7.5,
                    },
                },
                {
                    "event_type": "snapshot",
                    "event": {
                        "timestamp_ms": 1_700_000_180_000,
                        "pair": "BTCUSDT",
                        "last_price": 43255.0,
                        "bid": 43254.5,
                        "ask": 43255.5,
                        "volume_24h": 125100.0,
                    },
                    "route_hint": {
                        "route_id": "btc-live-2",
                        "engine_id": "engine_a",
                        "slippage_bps": 2.0,
                        "candidate_size": 9.0,
                        "final_size": 8.5,
                    },
                },
            ],
            indent=2,
        ),
        encoding="utf-8",
    )


def test_execution_telemetry_derives_gaps_from_stream_and_snapshot_batch():
    scratch = _scratch_dir()
    scratch.mkdir(parents=True, exist_ok=False)
    try:
        stream_path = scratch / "websocket_stream.jsonl"
        snapshot_batch_path = scratch / "live_websocket_snapshot_batch.json"
        _write_stream(stream_path)
        _write_snapshot_batch(snapshot_batch_path)

        assert derive_websocket_interarrival_s_from_stream(stream_path) == (60.0,)
        assert derive_websocket_interarrival_s_from_snapshot_batch(snapshot_batch_path) == (
            60.0,
        )
        assert derive_spread_bps_from_stream(stream_path) == pytest.approx(
            (0.23121257142140914, 0.23118584720404193),
            rel=1e-4,
        )
        assert derive_spread_bps_from_snapshot_batch(snapshot_batch_path) == pytest.approx(
            (0.23121257142140914, 0.23118584720404193),
            rel=1e-4,
        )
        assert derive_slippage_bps_from_stream(stream_path) == (2.5, 3.0)
        assert derive_slippage_bps_from_snapshot_batch(snapshot_batch_path) == (1.5, 2.0)
        assert derive_candidate_sizes_from_stream(stream_path) == (10.0, 12.0)
        assert derive_candidate_sizes_from_snapshot_batch(snapshot_batch_path) == (8.0, 9.0)
        assert derive_final_sizes_from_stream(stream_path) == (9.0, 11.0)
        assert derive_final_sizes_from_snapshot_batch(snapshot_batch_path) == (7.5, 8.5)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_execution_telemetry_archive_materializes_service_owned_artifact():
    scratch = _scratch_dir()
    scratch.mkdir(parents=True, exist_ok=False)
    try:
        stream_path = scratch / "websocket_stream.jsonl"
        snapshot_batch_path = scratch / "live_websocket_snapshot_batch.json"
        time_sync_path = scratch / "time_sync_offsets.json"
        _write_stream(stream_path)
        _write_snapshot_batch(snapshot_batch_path)
        time_sync_path.write_text(
            json.dumps(
                {
                    "time_sync_offsets_ms": [25.0, 30.0, 40.0],
                    "rest_call_count": 3,
                    "probe_duration_s": 1.5,
                    "rest_quota_max_calls_per_minute": 120,
                    "observed_calls_per_minute": 120.0,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        archive = LocalLabExecutionTelemetryArchive()
        session_day_1 = build_execution_telemetry_session_from_sources(
            session_date="2026-04-01",
            websocket_stream_path=stream_path,
            time_sync_offsets_path=time_sync_path,
        )
        archive = upsert_local_lab_execution_telemetry_archive(
            archive,
            export_dir="E:/lab/export_a",
            run_id="run-a",
            session=session_day_1,
        )
        session_day_2 = build_execution_telemetry_session_from_sources(
            session_date="2026-04-02",
            snapshot_batch_path=snapshot_batch_path,
        )
        archive = upsert_local_lab_execution_telemetry_archive(
            archive,
            export_dir="E:/lab/export_b",
            run_id="run-b",
            session=session_day_2,
        )

        artifact = materialize_local_lab_execution_telemetry_artifact(archive)
        bound = artifact.bind_to_review(correlation_id="corr-lab")

        assert artifact.export_dir == "E:/lab/export_b"
        assert artifact.run_id == "run-b"
        assert artifact.source_session_dates == ("2026-04-01", "2026-04-02")
        assert artifact.time_sync_observation_days == 1.0
        assert artifact.quota_observation_days == 1.0
        assert artifact.quota_call_counts == (3,)
        assert artifact.quota_probe_durations_s == (1.5,)
        assert artifact.quota_limit_calls_per_minute_values == (120,)
        assert artifact.quota_calls_per_minute_observed == (120.0,)
        assert artifact.websocket_observation_days == 2.0
        assert artifact.websocket_interarrival_s == (60.0, 60.0)
        assert artifact.spread_observation_days == 2.0
        assert len(artifact.spread_bps) == 4
        assert artifact.slippage_observation_days == 2.0
        assert artifact.slippage_bps == (2.5, 3.0, 1.5, 2.0)
        assert artifact.candidate_size_observation_days == 2.0
        assert artifact.candidate_sizes == (10.0, 12.0, 8.0, 9.0)
        assert artifact.final_size_observation_days == 2.0
        assert artifact.final_sizes == (9.0, 11.0, 7.5, 8.5)
        assert artifact.time_sync_source_refs == (str(time_sync_path.resolve()),)
        assert artifact.quota_source_refs == (str(time_sync_path.resolve()),)
        assert len(artifact.websocket_source_refs) == 2
        assert len(artifact.spread_source_refs) == 2
        assert len(artifact.slippage_source_refs) == 2
        assert len(artifact.candidate_size_source_refs) == 2
        assert len(artifact.final_size_source_refs) == 2
        assert artifact.coverage_caution_flags == ("THR-X02_ACCEPTED_EVENTS_ONLY",)
        assert bound.correlation_id == "corr-lab"
        assert bound.quota_call_counts == (3,)
        assert bound.quota_probe_durations_s == (1.5,)
        assert bound.quota_limit_calls_per_minute_values == (120,)
        assert bound.quota_calls_per_minute_observed == (120.0,)
        assert bound.candidate_sizes == (10.0, 12.0, 8.0, 9.0)
        assert bound.final_sizes == (9.0, 11.0, 7.5, 8.5)
        assert bound.coverage_caution_flags == ("THR-X02_ACCEPTED_EVENTS_ONLY",)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_execution_telemetry_archive_preserves_prior_time_sync_on_same_session_update():
    scratch = _scratch_dir()
    scratch.mkdir(parents=True, exist_ok=False)
    try:
        stream_path = scratch / "websocket_stream.jsonl"
        time_sync_path = scratch / "time_sync_offsets.json"
        _write_stream(stream_path)
        time_sync_path.write_text(
            json.dumps(
                {
                    "time_sync_offsets_ms": [20.0, 21.0, 22.0],
                    "rest_call_count": 3,
                    "probe_duration_s": 1.5,
                    "observed_calls_per_minute": 120.0,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        archive = LocalLabExecutionTelemetryArchive()
        initial_session = build_execution_telemetry_session_from_sources(
            session_date="2026-04-01",
            time_sync_offsets_path=time_sync_path,
        )
        archive = upsert_local_lab_execution_telemetry_archive(
            archive,
            export_dir="E:/lab/export_a",
            run_id="run-a",
            session=initial_session,
        )

        updated_session = build_execution_telemetry_session_from_sources(
            session_date="2026-04-01",
            websocket_stream_path=stream_path,
        )
        archive = upsert_local_lab_execution_telemetry_archive(
            archive,
            export_dir="E:/lab/export_b",
            run_id="run-b",
            session=updated_session,
        )
        artifact = materialize_local_lab_execution_telemetry_artifact(archive)

        assert artifact.time_sync_offsets_ms == (20.0, 21.0, 22.0)
        assert artifact.quota_call_counts == (3,)
        assert artifact.quota_probe_durations_s == (1.5,)
        assert artifact.quota_calls_per_minute_observed == (120.0,)
        assert artifact.websocket_interarrival_s == (60.0,)
        assert artifact.time_sync_observation_days == 1.0
        assert artifact.quota_observation_days == 1.0
        assert artifact.websocket_observation_days == 1.0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
