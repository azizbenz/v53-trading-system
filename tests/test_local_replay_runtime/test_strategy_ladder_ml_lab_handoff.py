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
    REPORTS_DIRNAME,
    STRATEGY_LADDER_ML_BACKTEST_INPUT_FILENAME,
    STRATEGY_LADDER_ML_MULTIFRAME_ARTIFACT_FILENAME,
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
    assert report.feature_grounding_contract_report_ref is not None
    assert Path(report.feature_grounding_contract_report_ref).is_file()
    assert report.training_source_contract_report_ref is not None
    assert Path(report.training_source_contract_report_ref).is_file()
    assert report.ml_overlay_authority_contract_report_ref is not None
    assert Path(report.ml_overlay_authority_contract_report_ref).is_file()
    assert report.ml_train_eval_overlap_report_ref is not None
    assert Path(report.ml_train_eval_overlap_report_ref).is_file()
    assert report.ml_feature_input_label_leakage_report_ref is not None
    assert Path(report.ml_feature_input_label_leakage_report_ref).is_file()
    payload = json.loads(Path(report.backtest_input_ref).read_text(encoding="utf-8"))
    assert payload["ml_mode"] == "ML_MODE_OVERLAY_FROZEN"
    assert payload["frozen_ml_artifact_hash"] == report.artifact_hash
    assert Path(payload["feature_grounding_contract_report_ref"]).is_file()
    assert Path(payload["training_source_contract_report_ref"]).is_file()
    assert Path(payload["ml_overlay_authority_contract_report_ref"]).is_file()
    assert payload["requested_backtest_end"] == "2025-05-30"
    assert payload["max_valid_backtest_end"] == "2025-05-30"
    assert payload["rolling_ml_window_plan_status"] == "ROLLING_PLAN_READY"
    assert payload["rolling_ml_required_artifact_count"] == 1
    assert "--rolling-ml-window-plan-path" in payload["backtest_cli_args"]
    assert "--ml-artifact-freshness-days" in payload["backtest_cli_args"]
    assert Path(scratch / "export" / STRATEGY_LADDER_ML_BACKTEST_INPUT_FILENAME).is_file()
    assert Path(scratch / "export" / ML_ANTI_LEAKAGE_PROOF_FILENAME).is_file()
    assert Path(scratch / "export" / ML_LIVE_DRIFT_SNAPSHOT_FILENAME).is_file()
    assert Path(scratch / "export" / REPORTS_DIRNAME / "feature_grounding_contract_report.json").is_file()
    assert Path(scratch / "export" / REPORTS_DIRNAME / "training_source_contract_report.json").is_file()
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
    assert len(report.timeframe_training_reports) == 1
    assert report.timeframe_training_reports[0].ready is False


def test_ml_lab_handoff_request_accepts_supported_microstructure_features_with_b2_root() -> None:
    scratch = _scratch_dir("micro_features")

    request = StrategyLadderMlLabHandoffRequest(
        artifact_id="edge-handoff",
        calibration_version="test.v1",
        kline_root=scratch / "klines",
        b2_run_root=scratch / "b2-run",
        export_dir=scratch / "export",
        train_start="2025-01-01",
        train_end="2025-04-30",
        feature_names=("close_return", "spread_bps", "book_depth_levels"),
    )

    assert request.feature_names == ("close_return", "spread_bps", "book_depth_levels")


def test_ml_lab_handoff_request_accepts_supported_microstructure_features_with_label_store_dataset_path() -> None:
    scratch = _scratch_dir("micro_features_label_store")
    dataset_path = scratch / "phase_b_ml_training_label_factory" / "labels" / "b_ml_label_store.jsonl"
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_path.write_text("", encoding="utf-8")

    request = StrategyLadderMlLabHandoffRequest(
        artifact_id="edge-handoff",
        calibration_version="test.v1",
        kline_root=scratch / "klines",
        label_store_dataset_path=dataset_path,
        export_dir=scratch / "export",
        train_start="2025-01-01",
        train_end="2025-04-30",
        feature_names=("close_return", "spread_bps", "book_depth_levels"),
    )

    assert request.label_store_dataset_path == dataset_path
    assert request.feature_names == ("close_return", "spread_bps", "book_depth_levels")


def test_ml_lab_handoff_prefers_explicit_label_store_dataset_path_over_b2_run_root(
    monkeypatch,
) -> None:
    scratch = _scratch_dir("prefer_label_store")
    dataset_path = scratch / "phase_b_ml_training_label_factory" / "labels" / "b_ml_label_store.jsonl"
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_path.write_text("", encoding="utf-8")
    captured: dict[str, object] = {}

    def _capturing_training_report(
        request: StrategyLadderExpectedEdgeTrainingRequest,
    ) -> StrategyLadderExpectedEdgeTrainingReport:
        captured["b2_run_root"] = request.b2_run_root
        captured["label_store_dataset_path"] = request.label_store_dataset_path
        return _fake_training_report(request)

    monkeypatch.setattr(
        "local_replay_runtime.strategy_ladder_ml_lab_handoff.train_strategy_ladder_expected_edge_artifact",
        _capturing_training_report,
    )

    report = run_strategy_ladder_ml_lab_handoff(
        StrategyLadderMlLabHandoffRequest(
            artifact_id="edge-handoff",
            calibration_version="test.v1",
            kline_root=scratch / "klines",
            b2_run_root=scratch / "b2-run",
            label_store_dataset_path=dataset_path,
            export_dir=scratch / "export",
            train_start="2025-01-01",
            train_end="2025-04-30",
            requested_backtest_start="2025-05-01",
            requested_backtest_days=15,
            feature_names=("close_return", "high_low_range", "volume"),
        )
    )

    assert report.ready is True
    assert captured["b2_run_root"] is None
    assert captured["label_store_dataset_path"] == dataset_path


def test_ml_lab_handoff_packages_multiframe_bundle_and_emits_bundle_input(
    monkeypatch,
) -> None:
    scratch = _scratch_dir("multiframe_ready")

    def _fake_training_report_by_timeframe(
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
            dataset_hash=f"{request.timeframe[0]}" * 64,
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

    monkeypatch.setattr(
        "local_replay_runtime.strategy_ladder_ml_lab_handoff.train_strategy_ladder_expected_edge_artifact",
        _fake_training_report_by_timeframe,
    )

    report = run_strategy_ladder_ml_lab_handoff(
        StrategyLadderMlLabHandoffRequest(
            artifact_id="edge-handoff-mtf",
            calibration_version="test.v1",
            kline_root=scratch / "klines",
            export_dir=scratch / "export",
            timeframe="1m,5m",
            train_start="2025-01-01",
            train_end="2025-04-30",
            requested_backtest_start="2025-05-01",
            requested_backtest_days=15,
        )
    )

    assert report.ready is True
    assert report.status == "STRATEGY_LADDER_ML_LAB_HANDOFF_READY"
    assert report.timeframe_scope == ("1m", "5m")
    assert len(report.timeframe_training_reports) == 2
    assert all(item.ready is True for item in report.timeframe_training_reports)
    assert report.transport_artifact_ref is not None
    assert Path(report.transport_artifact_ref).name == STRATEGY_LADDER_ML_MULTIFRAME_ARTIFACT_FILENAME
    bundle_payload = json.loads(Path(report.transport_artifact_ref).read_text(encoding="utf-8"))
    assert bundle_payload["timeframe_scope"] == ["1m", "5m"]
    assert len(bundle_payload["slices"]) == 2
    backtest_input = json.loads(Path(report.backtest_input_ref).read_text(encoding="utf-8"))
    assert backtest_input["timeframe_scope"] == ["1m", "5m"]
    assert backtest_input["frozen_ml_artifact_hash"] == report.artifact_hash
    assert Path(scratch / "export" / STRATEGY_LADDER_ML_BACKTEST_INPUT_FILENAME).is_file()


def test_ml_lab_handoff_aggregates_multiframe_training_blockers(monkeypatch) -> None:
    scratch = _scratch_dir("multiframe_blocked")

    def _fake_training_report_by_timeframe(
        request: StrategyLadderExpectedEdgeTrainingRequest,
    ) -> StrategyLadderExpectedEdgeTrainingReport:
        if request.timeframe == "1m":
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
                blocking_reasons=("TRAINING_DATASET_LOAD_FAILED:LABEL_STORE_BLOCKED_BY_NO_EXECUTED_TRADES",),
            )
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
        _fake_training_report_by_timeframe,
    )

    report = run_strategy_ladder_ml_lab_handoff(
        StrategyLadderMlLabHandoffRequest(
            artifact_id="edge-handoff-mtf-blocked",
            calibration_version="test.v1",
            kline_root=scratch / "klines",
            export_dir=scratch / "export",
            timeframe="1m,5m",
            train_start="2025-01-01",
            train_end="2025-04-30",
        )
    )

    assert report.ready is False
    assert report.status == "STRATEGY_LADDER_ML_LAB_HANDOFF_BLOCKED"
    assert len(report.timeframe_training_reports) == 2
    assert "TIMEFRAME_1m:TRAINING_DATASET_LOAD_FAILED:LABEL_STORE_BLOCKED_BY_NO_EXECUTED_TRADES" in report.blocking_reasons
    assert "TIMEFRAME_5m:INSUFFICIENT_EXPECTED_EDGE_TRAINING_ROWS" in report.blocking_reasons
