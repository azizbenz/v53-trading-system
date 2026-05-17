from __future__ import annotations

import json
from pathlib import Path

from local_replay_runtime.ml_governance_sidecars import (
    ML_ANTI_LEAKAGE_PROOF_FILENAME,
    ML_LIVE_DRIFT_SNAPSHOT_FILENAME,
)
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    StrategyLadderExpectedEdgeTrainingReport,
    StrategyLadderExpectedEdgeTrainingRequest,
    build_fixture_expected_edge_artifact,
)
from local_replay_runtime.strategy_ladder_ml_lab_handoff import (
    STRATEGY_LADDER_ML_BACKTEST_INPUT_FILENAME,
    StrategyLadderMlLabHandoffRequest,
    run_strategy_ladder_ml_lab_handoff,
)
from local_replay_runtime.strategy_ladder_rolling_ml_window_planner import (
    ROLLING_ML_WINDOW_PLAN_JSON_FILENAME,
    ROLLING_ML_WINDOW_PLAN_MARKDOWN_FILENAME,
)
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir("strategy_ladder_ml_lab_handoff_tests", label)


def _fake_training_report(
    request: StrategyLadderExpectedEdgeTrainingRequest,
) -> StrategyLadderExpectedEdgeTrainingReport:
    artifact = build_fixture_expected_edge_artifact(feature_names=request.feature_names)
    artifact_path = request.output_dir / f"{request.artifact_id}.json"
    report_path = request.output_dir / f"{request.artifact_id}.training_report.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return StrategyLadderExpectedEdgeTrainingReport(
        artifact_id=request.artifact_id,
        status="STRATEGY_LADDER_EXPECTED_EDGE_ARTIFACT_READY",
        ready=True,
        pair=request.pair,
        timeframe=request.timeframe,
        kline_root=str(request.kline_root),
        output_dir=str(request.output_dir),
        artifact_path=str(artifact_path),
        training_report_path=str(report_path),
        artifact_hash=artifact.artifact_hash,
        feature_hash=artifact.feature_hash,
        dataset_hash=artifact.dataset_hash,
        feature_names=artifact.feature_names,
        train_start=request.train_start,
        train_end=request.train_end,
        target_horizon_minutes=request.target_horizon_minutes,
        sample_stride_minutes=request.sample_stride_minutes,
        kline_file_count=210,
        training_row_count=210,
        trainer_train_row_count=180,
        trainer_validation_row_count=30,
        artifact_stale_after=artifact.stale_after,
        calibration_version=request.calibration_version,
        training_seed=request.training_seed,
    )


def test_ml_lab_handoff_packages_artifact_and_emits_backtest_input(
    monkeypatch,
) -> None:
    scratch = _scratch_dir("ready")
    monkeypatch.setattr(
        "local_replay_runtime.strategy_ladder_ml_lab_handoff.train_strategy_ladder_expected_edge_artifact",
        _fake_training_report,
    )

    report = run_strategy_ladder_ml_lab_handoff(
        StrategyLadderMlLabHandoffRequest(
            artifact_id="edge-handoff",
            calibration_version="test.v1",
            kline_root=scratch / "klines",
            export_dir=scratch / "export",
            train_start="2025-01-01",
            train_end="2025-04-30",
            requested_backtest_start="2025-05-01",
            requested_backtest_days=30,
        )
    )

    assert report.ready is True
    assert report.status == "STRATEGY_LADDER_ML_LAB_HANDOFF_READY"
    assert report.transport_artifact_ref is not None
    assert Path(report.transport_artifact_ref).is_file()
    assert report.backtest_input_ref is not None
    assert report.anti_leakage_proof_ref is not None
    assert Path(report.anti_leakage_proof_ref).is_file()
    assert report.live_drift_snapshot_ref is not None
    assert Path(report.live_drift_snapshot_ref).is_file()
    payload = json.loads(Path(report.backtest_input_ref).read_text(encoding="utf-8"))
    assert payload["ml_mode"] == "ML_MODE_OVERLAY_FROZEN"
    assert payload["frozen_ml_artifact_hash"] == report.artifact_hash
    assert payload["requested_backtest_end"] == "2025-05-30"
    assert payload["max_valid_backtest_end"] == "2025-05-30"
    assert payload["rolling_ml_window_plan_status"] == "ROLLING_PLAN_READY"
    assert payload["rolling_ml_required_artifact_count"] == 1
    assert "--rolling-ml-window-plan-path" in payload["backtest_cli_args"]
    assert "--ml-artifact-freshness-days" in payload["backtest_cli_args"]
    assert Path(scratch / "export" / STRATEGY_LADDER_ML_BACKTEST_INPUT_FILENAME).is_file()
    assert Path(scratch / "export" / ML_ANTI_LEAKAGE_PROOF_FILENAME).is_file()
    assert Path(scratch / "export" / ML_LIVE_DRIFT_SNAPSHOT_FILENAME).is_file()
    assert Path(scratch / "export" / ROLLING_ML_WINDOW_PLAN_JSON_FILENAME).is_file()
    assert Path(scratch / "export" / ROLLING_ML_WINDOW_PLAN_MARKDOWN_FILENAME).is_file()


def test_ml_lab_handoff_blocks_single_artifact_for_130_day_backtest(
    monkeypatch,
) -> None:
    scratch = _scratch_dir("blocked_stale")
    monkeypatch.setattr(
        "local_replay_runtime.strategy_ladder_ml_lab_handoff.train_strategy_ladder_expected_edge_artifact",
        _fake_training_report,
    )

    report = run_strategy_ladder_ml_lab_handoff(
        StrategyLadderMlLabHandoffRequest(
            artifact_id="edge-handoff",
            calibration_version="test.v1",
            kline_root=scratch / "klines",
            export_dir=scratch / "export",
            train_start="2025-01-01",
            train_end="2025-04-30",
            requested_backtest_start="2025-05-01",
            requested_backtest_days=130,
        )
    )

    assert report.ready is False
    assert report.status == "STRATEGY_LADDER_ML_LAB_HANDOFF_BLOCKED"
    assert "BACKTEST_WINDOW_EXCEEDS_ARTIFACT_STALE_AFTER" in report.blocking_reasons
    assert "ROLLING_PLAN_REQUIRES_5_ARTIFACTS" in report.blocking_reasons
    assert report.requested_backtest_end == "2025-09-07"
    assert report.max_valid_backtest_end == "2025-05-30"
    assert report.rolling_ml_window_plan_status == "ROLLING_PLAN_REQUIRES_5_ARTIFACTS"
    assert report.rolling_ml_required_artifact_count == 5
    assert report.rolling_ml_window_plan_ref is not None
    assert Path(report.rolling_ml_window_plan_ref).is_file()
    assert report.backtest_input_ref is None


def test_ml_lab_handoff_propagates_training_blocker(monkeypatch) -> None:
    scratch = _scratch_dir("blocked_training")

    def _blocked_training(
        request: StrategyLadderExpectedEdgeTrainingRequest,
    ) -> StrategyLadderExpectedEdgeTrainingReport:
        return StrategyLadderExpectedEdgeTrainingReport(
            artifact_id=request.artifact_id,
            status="STRATEGY_LADDER_EXPECTED_EDGE_TRAINING_BLOCKED",
            ready=False,
            pair=request.pair,
            timeframe=request.timeframe,
            kline_root=str(request.kline_root),
            output_dir=str(request.output_dir),
            train_start=request.train_start,
            train_end=request.train_end,
            target_horizon_minutes=request.target_horizon_minutes,
            sample_stride_minutes=request.sample_stride_minutes,
            calibration_version=request.calibration_version,
            training_seed=request.training_seed,
            blocking_reasons=("INSUFFICIENT_EXPECTED_EDGE_TRAINING_ROWS",),
        )

    monkeypatch.setattr(
        "local_replay_runtime.strategy_ladder_ml_lab_handoff.train_strategy_ladder_expected_edge_artifact",
        _blocked_training,
    )

    report = run_strategy_ladder_ml_lab_handoff(
        StrategyLadderMlLabHandoffRequest(
            artifact_id="edge-handoff",
            calibration_version="test.v1",
            kline_root=scratch / "klines",
            export_dir=scratch / "export",
            train_start="2025-01-01",
            train_end="2025-04-30",
        )
    )

    assert report.ready is False
    assert "INSUFFICIENT_EXPECTED_EDGE_TRAINING_ROWS" in report.blocking_reasons
    assert report.backtest_cli_args == ()
