from __future__ import annotations

import json
from pathlib import Path

import pytest

from calibration_methods import MlTrainerDataError, MlTrainerRequest, MlTrainerResult
from local_replay_runtime.strategy_ladder_b2_label_store_builder import (
    LABEL_STORE_DATASET_FILENAME,
    StrategyLadderB2LabelStoreQualityReport,
    StrategyLadderB2LabelStoreRow,
    StrategyLadderB2LabelStoreSummary,
)
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    StrategyLadderExpectedEdgeTrainingRequest,
    build_fixture_expected_edge_artifact,
    build_strategy_ladder_expected_edge_training_rows,
    train_strategy_ladder_expected_edge_artifact,
)
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    path = make_repo_scratch_dir("strategy_ladder_expected_edge_training_tests", label)
    return path


def _write_kline_csv(
    root: Path,
    *,
    pair: str = "BTCUSDT",
    timeframe: str = "1m",
    day: str = "2025-01-01",
    flat_layout: bool = False,
) -> Path:
    timeframe_code = timeframe[:-1] if timeframe.endswith("m") else timeframe
    if flat_layout:
        path = root / pair / timeframe_code / f"{pair}_{timeframe_code}_{day}.csv"
    else:
        path = root / pair / timeframe_code / "2025" / f"{pair}_{timeframe_code}_{day}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    start_ms = 1_735_689_600_000
    step_ms = int(timeframe_code) * 60_000
    rows = ["startTime,open,high,low,close,volume,turnover"]
    for index in range(12):
        open_price = 100.0 + index
        high_price = open_price + 1.0
        low_price = open_price - 1.0
        close_price = open_price + 0.5
        volume = 10.0 + index
        rows.append(
            ",".join(
                (
                    str(start_ms + index * step_ms),
                    str(open_price),
                    str(high_price),
                    str(low_price),
                    str(close_price),
                    str(volume),
                    str(volume * close_price),
                )
            )
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_expected_edge_training_rows_use_gold_store_features() -> None:
    scratch = _scratch_dir("rows")
    _write_kline_csv(scratch)

    rows = build_strategy_ladder_expected_edge_training_rows(
        StrategyLadderExpectedEdgeTrainingRequest(
            artifact_id="edge-fixture",
            calibration_version="test.v1",
            kline_root=scratch,
            output_dir=scratch / "out",
            train_start="2025-01-01",
            train_end="2025-01-01",
            sample_stride_minutes=1,
            target_horizon_minutes=1,
        )
    )

    assert len(rows) == 11
    assert rows[0].features["close_return"] == pytest.approx(0.005)
    assert rows[0].features["high_low_range"] == pytest.approx(0.02)
    assert rows[0].features["volume"] == 10.0
    assert rows[0].target == pytest.approx(abs(101.5 - 100.5) / 100.5)


def test_expected_edge_training_rows_support_flat_multitimeframe_layout() -> None:
    scratch = _scratch_dir("rows_flat_5m")
    _write_kline_csv(scratch, timeframe="5m", flat_layout=True)

    rows = build_strategy_ladder_expected_edge_training_rows(
        StrategyLadderExpectedEdgeTrainingRequest(
            artifact_id="edge-fixture-5m",
            calibration_version="test.v1",
            kline_root=scratch,
            output_dir=scratch / "out",
            timeframe="5m",
            train_start="2025-01-01",
            train_end="2025-01-01",
            sample_stride_minutes=5,
            target_horizon_minutes=5,
        )
    )

    assert len(rows) == 11
    assert rows[0].features["close_return"] == pytest.approx(0.005)
    assert rows[0].features["high_low_range"] == pytest.approx(0.02)
    assert rows[0].target == pytest.approx(abs(101.5 - 100.5) / 100.5)


def test_expected_edge_training_request_blocks_microstructure_features_without_replay_source() -> None:
    scratch = _scratch_dir("micro_without_replay")
    _write_kline_csv(scratch)

    with pytest.raises(
        ValueError,
        match="microstructure expected-edge features require b2_run_root or label_store_dataset_path",
    ):
        StrategyLadderExpectedEdgeTrainingRequest(
            artifact_id="edge-fixture",
            calibration_version="test.v1",
            kline_root=scratch,
            output_dir=scratch / "out",
            train_start="2025-01-01",
            train_end="2025-01-01",
            sample_stride_minutes=1,
            target_horizon_minutes=1,
            feature_names=("close_return", "spread_bps"),
        )


def test_train_expected_edge_artifact_writes_report_and_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("train")
    _write_kline_csv(scratch)
    output_dir = scratch / "artifacts"

    def _fake_train(request: MlTrainerRequest) -> MlTrainerResult:
        assert len(request.rows) == 11
        assert request.max_optuna_trials == 0
        artifact = build_fixture_expected_edge_artifact(
            feature_names=tuple(request.rows[0].features)
        )
        return MlTrainerResult(
            artifact=artifact,
            train_row_count=6,
            validation_row_count=5,
            bagging_folds_used=5,
            optuna_trials_used=0,
            best_params={"learning_rate": 0.05},
        )

    monkeypatch.setattr(
        "local_replay_runtime.strategy_ladder_expected_edge_training.train_lightgbm_ml_artifact",
        _fake_train,
    )

    report = train_strategy_ladder_expected_edge_artifact(
        StrategyLadderExpectedEdgeTrainingRequest(
            artifact_id="edge-fixture",
            calibration_version="test.v1",
            kline_root=scratch,
            output_dir=output_dir,
            train_start="2025-01-01",
            train_end="2025-01-01",
            sample_stride_minutes=1,
            target_horizon_minutes=1,
            min_training_rows=10,
        )
    )

    assert report.ready is True
    assert report.status == "STRATEGY_LADDER_EXPECTED_EDGE_ARTIFACT_READY"
    assert report.training_row_count == 11
    assert report.artifact_path is not None
    assert Path(report.artifact_path).is_file()
    assert report.training_report_path is not None
    saved_report = json.loads(Path(report.training_report_path).read_text(encoding="utf-8"))
    assert saved_report["artifact_hash"] == report.artifact_hash


def test_train_expected_edge_artifact_consumes_replay_grounded_label_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("replay_grounded_label_store")
    label_store_dir = scratch / "label-store"
    label_store_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = label_store_dir / LABEL_STORE_DATASET_FILENAME
    rows = []
    for index in range(12):
        rows.append(
            StrategyLadderB2LabelStoreRow(
                candidate_id=f"cand-{index}",
                engine_id="engine_a",
                pair="BTCUSDT",
                timeframe="1m",
                capital_bucket=400,
                decision_timestamp_ms=1_735_689_600_000 + index * 86_400_000,
                feature_timestamp_ms=1_735_689_540_000 + index * 86_400_000,
                raw_window_ref="fixture://raw-window",
                replay_ref="fixture://replay",
                replay_record_id=f"dtr-{index}",
                feature_vector_ref="fixture://features",
                spread_bps=4.0,
                fee_bps=1.0,
                slippage_bps=1.5,
                adverse_selection_bps=0.1,
                expected_ce_net=0.0005,
                executed_only_net_return=0.0007,
                break_even_bps=6.0,
                mfe_bps=10.0,
                mae_bps=-3.0,
                holding_time_ms=60_000,
                label_net_positive=True,
                label_break_even_cleared=True,
                label_survived_mae=True,
                evidence_class="REPLAY_EXECUTED_ONLY_NET_RETURN",
                label_quality_status="LABEL_QUALITY_PROMOTION_GRADE_CANDIDATE",
                replay_grounded_status="REPLAY_GROUNDED_PROMOTION_GRADE_CANDIDATE",
                replay_quality_status="REPLAY_READY",
                execution_fidelity_status="EXECUTION_FIDELITY_READY",
                entry_reference_status="ENTRY_REFERENCE_EXECUTED_FILL_MEASURED",
                mfe_mae_status="MFE_MAE_AVAILABLE",
                proxy_execution_label_flag=False,
                replay_grounded_label_flag=True,
                feature_values={
                    "close_return": 0.01,
                    "high_low_range": 0.02,
                    "volume": 10.0 + index,
                    "spread_bps": 4.0,
                    "slippage_bps": 1.5,
                    "book_depth_levels": 20.0,
                    "break_even_bps": 6.0,
                    "fragility_score": 0.25,
                    "false_breakout_context": 0.15,
                },
                feature_hash="a" * 64,
            )
        )
    dataset_path.write_text(
        "\n".join(row.model_dump_json() for row in rows) + "\n",
        encoding="utf-8",
    )
    (label_store_dir / "label_store_summary.json").write_text(
        StrategyLadderB2LabelStoreSummary(
            status="LABEL_STORE_READY",
            promotion_state="LABEL_STORE_PROMOTION_GRADE_CANDIDATE",
            label_source_type="B2_REPLAY_EXECUTED_ONLY_NET_RETURN",
            run_root=str(scratch.resolve()),
            dataset_ref=str(dataset_path.resolve()),
            quality_report_ref=str((label_store_dir / "label_store_quality_report.json").resolve()),
            row_count=12,
            replay_grounded_label_count=12,
            proxy_execution_label_count=0,
            executed_trade_label_count=12,
            net_positive_rate=1.0,
            break_even_clearance_rate=1.0,
            replay_backed_label_coverage=1.0,
            mfe_available_count=12,
            mae_available_count=12,
            mfe_availability_rate=1.0,
            mae_availability_rate=1.0,
            dataset_hash="d" * 64,
            feature_hash="e" * 64,
            label_hash="f" * 64,
            pair_scope=("BTCUSDT",),
            engine_scope=("engine_a",),
            timeframe_scope=("1m",),
            capital_bucket_scope=(400,),
            replay_provenance_refs=("fixture://replay",),
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    (label_store_dir / "label_store_quality_report.json").write_text(
        StrategyLadderB2LabelStoreQualityReport(
            status="LABEL_STORE_READY",
            promotion_state="LABEL_STORE_PROMOTION_GRADE_CANDIDATE",
            label_source_type="B2_REPLAY_EXECUTED_ONLY_NET_RETURN",
            run_root=str(scratch.resolve()),
            dataset_ref=str(dataset_path.resolve()),
            dataset_hash="d" * 64,
            feature_hash="e" * 64,
            label_hash="f" * 64,
            row_count=12,
            replay_grounded_label_count=12,
            proxy_execution_label_count=0,
            replay_backed_label_coverage=1.0,
            net_positive_rate=1.0,
            break_even_clearance_rate=1.0,
            mfe_mae_availability="MFE_MAE_AVAILABLE",
            execution_fidelity_status_counts={"EXECUTION_FIDELITY_READY": 12},
            evidence_class_counts={"REPLAY_EXECUTED_ONLY_NET_RETURN": 12},
            replay_provenance_refs=("fixture://replay",),
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    output_dir = scratch / "artifacts"

    def _fake_train(request: MlTrainerRequest) -> MlTrainerResult:
        assert len(request.rows) == 12
        assert request.rows[0].target == pytest.approx(0.0007)
        assert request.rows[0].features["close_return"] == pytest.approx(0.01)
        assert request.rows[0].features["spread_bps"] == pytest.approx(4.0)
        assert request.rows[0].features["book_depth_levels"] == pytest.approx(20.0)
        artifact = build_fixture_expected_edge_artifact(
            feature_names=tuple(request.rows[0].features),
            label_source="B2_REPLAY_EXECUTED_ONLY_NET_RETURN",
            label_fidelity="LABEL_STORE_PROMOTION_GRADE_CANDIDATE",
        )
        return MlTrainerResult(
            artifact=artifact,
            train_row_count=6,
            validation_row_count=6,
            bagging_folds_used=5,
            optuna_trials_used=0,
            best_params={"learning_rate": 0.05},
        )

    monkeypatch.setattr(
        "local_replay_runtime.strategy_ladder_expected_edge_training.train_lightgbm_ml_artifact",
        _fake_train,
    )

    report = train_strategy_ladder_expected_edge_artifact(
        StrategyLadderExpectedEdgeTrainingRequest(
            artifact_id="edge-replay-grounded",
            calibration_version="test.v2",
            kline_root=None,
            label_store_dataset_path=dataset_path,
            output_dir=output_dir,
            pair="BTCUSDT",
            timeframe="1m",
            train_start="2025-01-01",
            train_end="2025-01-12",
            sample_stride_minutes=1,
            target_horizon_minutes=1,
            min_training_rows=10,
            feature_names=(
                "close_return",
                "spread_bps",
                "book_depth_levels",
                "break_even_bps",
                "fragility_score",
                "false_breakout_context",
            ),
        )
    )

    assert report.ready is True
    assert report.label_source_type == "B2_REPLAY_EXECUTED_ONLY_NET_RETURN"
    assert report.replay_grounded_label_count == 12
    assert report.proxy_execution_label_count == 0
    assert report.label_store_dataset_path == str(dataset_path.resolve())
    assert report.feature_names == (
        "close_return",
        "spread_bps",
        "book_depth_levels",
        "break_even_bps",
        "fragility_score",
        "false_breakout_context",
    )


def test_train_expected_edge_artifact_surfaces_ml_trainer_failure_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("replay_grounded_label_store_failure_detail")
    label_store_dir = scratch / "label-store"
    label_store_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = label_store_dir / LABEL_STORE_DATASET_FILENAME
    rows = []
    for index in range(12):
        rows.append(
            StrategyLadderB2LabelStoreRow(
                candidate_id=f"cand-{index}",
                engine_id="engine_a",
                pair="BTCUSDT",
                timeframe="1m",
                capital_bucket=400,
                decision_timestamp_ms=1_735_689_600_000 + index * 86_400_000,
                feature_timestamp_ms=1_735_689_540_000 + index * 86_400_000,
                raw_window_ref="fixture://raw-window",
                replay_ref="fixture://replay",
                replay_record_id=f"dtr-{index}",
                feature_vector_ref="fixture://features",
                spread_bps=4.0,
                fee_bps=1.0,
                slippage_bps=1.5,
                adverse_selection_bps=0.1,
                expected_ce_net=0.0005,
                executed_only_net_return=0.0007,
                break_even_bps=6.0,
                mfe_bps=10.0,
                mae_bps=-3.0,
                holding_time_ms=60_000,
                label_net_positive=True,
                label_break_even_cleared=True,
                label_survived_mae=True,
                evidence_class="REPLAY_EXECUTED_ONLY_NET_RETURN",
                label_quality_status="LABEL_QUALITY_PROMOTION_GRADE_CANDIDATE",
                replay_grounded_status="REPLAY_GROUNDED_PROMOTION_GRADE_CANDIDATE",
                replay_quality_status="REPLAY_READY",
                execution_fidelity_status="EXECUTION_FIDELITY_READY",
                entry_reference_status="ENTRY_REFERENCE_EXECUTED_FILL_MEASURED",
                mfe_mae_status="MFE_MAE_AVAILABLE",
                proxy_execution_label_flag=False,
                replay_grounded_label_flag=True,
                feature_values={
                    "close_return": 0.01,
                    "high_low_range": 0.02,
                    "volume": 10.0 + index,
                    "spread_bps": 4.0,
                    "slippage_bps": 1.5,
                    "book_depth_levels": 20.0,
                    "break_even_bps": 6.0,
                    "fragility_score": 0.25,
                    "false_breakout_context": 0.15,
                },
                feature_hash="a" * 64,
            )
        )
    dataset_path.write_text(
        "\n".join(row.model_dump_json() for row in rows) + "\n",
        encoding="utf-8",
    )
    (label_store_dir / "label_store_summary.json").write_text(
        StrategyLadderB2LabelStoreSummary(
            status="LABEL_STORE_READY",
            promotion_state="LABEL_STORE_PROMOTION_GRADE_CANDIDATE",
            label_source_type="B2_REPLAY_EXECUTED_ONLY_NET_RETURN",
            run_root=str(scratch.resolve()),
            dataset_ref=str(dataset_path.resolve()),
            quality_report_ref=str((label_store_dir / "label_store_quality_report.json").resolve()),
            row_count=12,
            replay_grounded_label_count=12,
            proxy_execution_label_count=0,
            executed_trade_label_count=12,
            net_positive_rate=1.0,
            break_even_clearance_rate=1.0,
            replay_backed_label_coverage=1.0,
            mfe_available_count=12,
            mae_available_count=12,
            mfe_availability_rate=1.0,
            mae_availability_rate=1.0,
            dataset_hash="d" * 64,
            feature_hash="e" * 64,
            label_hash="f" * 64,
            pair_scope=("BTCUSDT",),
            engine_scope=("engine_a",),
            timeframe_scope=("1m",),
            capital_bucket_scope=(400,),
            replay_provenance_refs=("fixture://replay",),
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    (label_store_dir / "label_store_quality_report.json").write_text(
        StrategyLadderB2LabelStoreQualityReport(
            status="LABEL_STORE_READY",
            promotion_state="LABEL_STORE_PROMOTION_GRADE_CANDIDATE",
            label_source_type="B2_REPLAY_EXECUTED_ONLY_NET_RETURN",
            run_root=str(scratch.resolve()),
            dataset_ref=str(dataset_path.resolve()),
            dataset_hash="d" * 64,
            feature_hash="e" * 64,
            label_hash="f" * 64,
            row_count=12,
            replay_grounded_label_count=12,
            proxy_execution_label_count=0,
            replay_backed_label_coverage=1.0,
            net_positive_rate=1.0,
            break_even_clearance_rate=1.0,
            mfe_mae_availability="MFE_MAE_AVAILABLE",
            execution_fidelity_status_counts={"EXECUTION_FIDELITY_READY": 12},
            evidence_class_counts={"REPLAY_EXECUTED_ONLY_NET_RETURN": 12},
            replay_provenance_refs=("fixture://replay",),
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )

    def _fail_train(_request: MlTrainerRequest) -> MlTrainerResult:
        raise MlTrainerDataError("MlTrainerRequest produced an empty 180d train window")

    monkeypatch.setattr(
        "local_replay_runtime.strategy_ladder_expected_edge_training.train_lightgbm_ml_artifact",
        _fail_train,
    )

    report = train_strategy_ladder_expected_edge_artifact(
        StrategyLadderExpectedEdgeTrainingRequest(
            artifact_id="edge-replay-grounded-failure-detail",
            calibration_version="test.v2",
            kline_root=None,
            label_store_dataset_path=dataset_path,
            output_dir=scratch / "artifacts",
            pair="BTCUSDT",
            timeframe="1m",
            train_start="2025-01-01",
            train_end="2025-01-12",
            sample_stride_minutes=1,
            target_horizon_minutes=1,
            min_training_rows=10,
            feature_names=(
                "close_return",
                "spread_bps",
                "book_depth_levels",
                "break_even_bps",
                "fragility_score",
                "false_breakout_context",
            ),
        )
    )

    assert report.ready is False
    assert report.blocking_reasons == (
        "ML_TRAINER_FAILED:MLTRAINERREQUEST_PRODUCED_AN_EMPTY_180D_TRAIN_WINDOW",
    )


def test_train_expected_edge_artifact_reports_no_executed_label_store_blocker() -> None:
    scratch = _scratch_dir("blocked_no_executed_labels")
    label_store_dir = scratch / "label-store"
    label_store_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = label_store_dir / LABEL_STORE_DATASET_FILENAME
    dataset_path.write_text("", encoding="utf-8")
    (label_store_dir / "label_store_summary.json").write_text(
        StrategyLadderB2LabelStoreSummary(
            status="LABEL_STORE_BLOCKED_BY_NO_EXECUTED_TRADES",
            promotion_state="LABEL_STORE_RESEARCH_ONLY",
            label_source_type="B2_REPLAY_EXPECTED_CE_NET_PROXY",
            run_root=str(scratch.resolve()),
            dataset_ref=str(dataset_path.resolve()),
            quality_report_ref=str((label_store_dir / "label_store_quality_report.json").resolve()),
            row_count=0,
            replay_grounded_label_count=0,
            proxy_execution_label_count=0,
            executed_trade_label_count=0,
            net_positive_rate=None,
            break_even_clearance_rate=None,
            replay_backed_label_coverage=0.0,
            mfe_available_count=0,
            mae_available_count=0,
            mfe_availability_rate=0.0,
            mae_availability_rate=0.0,
            dataset_hash="d" * 64,
            feature_hash="e" * 64,
            label_hash="f" * 64,
            pair_scope=("BTCUSDT",),
            engine_scope=("engine_a",),
            timeframe_scope=("1m",),
            capital_bucket_scope=(400,),
            replay_provenance_refs=("fixture://replay",),
            blocking_reasons=("NO_EXECUTED_REPLAY_LABELS",),
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    (label_store_dir / "label_store_quality_report.json").write_text(
        StrategyLadderB2LabelStoreQualityReport(
            status="LABEL_STORE_BLOCKED_BY_NO_EXECUTED_TRADES",
            promotion_state="LABEL_STORE_RESEARCH_ONLY",
            label_source_type="B2_REPLAY_EXPECTED_CE_NET_PROXY",
            run_root=str(scratch.resolve()),
            dataset_ref=str(dataset_path.resolve()),
            dataset_hash="d" * 64,
            feature_hash="e" * 64,
            label_hash="f" * 64,
            row_count=0,
            replay_grounded_label_count=0,
            proxy_execution_label_count=0,
            replay_backed_label_coverage=0.0,
            net_positive_rate=None,
            break_even_clearance_rate=None,
            mfe_mae_availability="MFE_MAE_NOT_AVAILABLE",
            execution_fidelity_status_counts={},
            evidence_class_counts={},
            replay_provenance_refs=("fixture://replay",),
            blocking_reasons=("NO_EXECUTED_REPLAY_LABELS",),
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )

    report = train_strategy_ladder_expected_edge_artifact(
        StrategyLadderExpectedEdgeTrainingRequest(
            artifact_id="edge-blocked",
            calibration_version="test.v3",
            kline_root=None,
            label_store_dataset_path=dataset_path,
            output_dir=scratch / "artifacts",
            pair="BTCUSDT",
            timeframe="1m",
            train_start="2025-01-01",
            train_end="2025-01-12",
            sample_stride_minutes=1,
            target_horizon_minutes=1,
            min_training_rows=10,
            feature_names=("close_return",),
        )
    )

    assert report.ready is False
    assert report.status == "STRATEGY_LADDER_EXPECTED_EDGE_TRAINING_BLOCKED"
    assert report.blocking_reasons == (
        "TRAINING_DATASET_LOAD_FAILED:LABEL_STORE_BLOCKED_BY_NO_EXECUTED_TRADES",
    )
