from __future__ import annotations

from pathlib import Path
import shutil

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime import (
    LocalLabExecutionTelemetry,
    build_local_lab_execution_review,
    build_local_lab_execution_runtime_projection,
)
from protocols import (
    inspect_execution_runtime_projection_bridge,
    load_execution_runtime_consumer_models,
)


def _write_ready_projection(path: Path) -> None:
    projection = build_local_lab_execution_runtime_projection(
        build_local_lab_execution_review(
            correlation_id="corr-1",
            export_dir="E:/lab/export",
            run_id="run-1",
            telemetry=LocalLabExecutionTelemetry(
                correlation_id="corr-1",
                export_dir="E:/lab/export",
                run_id="run-1",
                quota_call_counts=(45, 48, 42, 46),
                quota_probe_durations_s=(60.0, 60.0, 60.0, 60.0),
                quota_limit_calls_per_minute_values=(100, 120),
                quota_calls_per_minute_observed=(45.0, 48.0, 42.0, 46.0),
                quota_observation_days=31.0,
                spread_bps=(6.0, 8.0, 9.0, 12.0),
                spread_observation_days=31.0,
                slippage_bps=(2.0, 2.8, 3.4, 4.0),
                slippage_observation_days=31.0,
                final_sizes=(1.0, 4.0, 9.0, 16.0),
            ),
        )
    )
    atomic_write_json(path, projection.model_dump(mode="json"), indent=2)


def test_inspect_execution_runtime_projection_bridge_reports_missing_projection():
    status = inspect_execution_runtime_projection_bridge(
        "build/test_protocols_execution_runtime_projection_bridge_missing/projection.json"
    )

    assert status.configured is True
    assert status.projection_found is False
    assert status.projection_loaded is False


def test_load_execution_runtime_consumer_models_recovers_ready_models():
    state_dir = Path("build/test_protocols_execution_runtime_projection_bridge_loaded")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        projection_path = state_dir / "local_lab_execution_runtime_projection.json"
        _write_ready_projection(projection_path)

        rate_limit_model, spread_guard_model, slippage_model = load_execution_runtime_consumer_models(projection_path)
        status = inspect_execution_runtime_projection_bridge(projection_path)

        assert rate_limit_model is not None
        assert rate_limit_model.threshold_id == "THR-X03"
        assert spread_guard_model is not None
        assert spread_guard_model.threshold_id == "THR-X04"
        assert slippage_model is not None
        assert slippage_model.threshold_id == "THR-X05"
        assert status.projection_loaded is True
        assert status.rate_limit_model_loaded is True
        assert status.spread_guard_model_loaded is True
        assert status.slippage_model_loaded is True
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
