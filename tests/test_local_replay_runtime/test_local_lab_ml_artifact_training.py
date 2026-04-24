from __future__ import annotations

from datetime import UTC, datetime

import pytest

from calibration_methods import MlTrainerDependencyError, MlTrainerRequest, MlTrainerResult
from interface_contracts import MlModelArtifact, MlModelWindow, PromotionState
from local_replay_runtime import build_local_lab_ml_artifact_training_report
from local_replay_runtime.historical_data_gateway import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


def _dataset() -> HistoricalReplayDataset:
    records = []
    for index in range(12):
        records.append(
            HistoricalReplayOpportunity(
                opportunity_id=f"opp-{index}",
                timestamp_ms=1_700_000_000_000 + (index * 86_400_000),
                pair="BTCUSDT",
                engine_id="engine_a",
                regime="trend",
                raw_score=0.4 + (index / 100.0),
                penalized_score=0.35 + (index / 100.0),
                final_score=0.3 + (index / 100.0),
                expected_edge_bps=10.0 + index,
                spread_bps=1.0,
                slippage_bps=0.4,
                latency_penalty_bps=0.1,
                fill_ratio=0.9,
                target_decision_state=DecisionState.EXECUTED,
                ranking_position=1 + (index % 3),
                candidate_size=1.0,
                final_size=0.9,
                tier="core",
                gross_return_bps=8.0 + index,
                primary_reason="ok",
                feature_values={
                    "sweep_score_1m": 0.5 + (index / 100.0),
                    "flow_coherence_1m": 0.2 + (index / 200.0),
                },
                shared_core_match=True,
            )
        )
    return HistoricalReplayDataset.from_records(
        dataset_id="dataset-ml-train",
        source_path="history.json",
        records=tuple(records),
        source="local_dataset",
    )


def _dtr_records() -> tuple:
    records = []
    for index in range(12):
        records.append(
            build_dtr(
                dtr_id=f"dataset-ml-train:opp-{index}",
                pair="BTCUSDT",
                engine_id="engine_a",
                decision_state=DecisionState.EXECUTED,
                gross_return=0.0015 + (index / 100000.0),
                realized_cost=0.0004,
                expected_cost=0.0003,
                ce_expected=0.0007,
                raw_score=0.4 + (index / 100.0),
                penalized_score=0.35 + (index / 100.0),
                final_score=0.3 + (index / 100.0),
                candidate_size=1.0,
                final_size=0.9,
                ranking_position=1 + (index % 3),
                runtime_mode="local_replay",
                input_source="local_replay",
                timestamp=1_700_000_000.0 + (index * 86_400.0),
            )
        )
    return tuple(records)


def _fake_train(request: MlTrainerRequest) -> MlTrainerResult:
    ordered = tuple(sorted(request.rows, key=lambda row: row.timestamp))
    artifact = MlModelArtifact.create(
        feature_names=tuple(sorted(ordered[0].features)),
        feature_hash="a" * 64,
        pair_universe=tuple(sorted({row.pair for row in ordered})),
        train_window=MlModelWindow(
            start_at=ordered[0].timestamp,
            end_at=ordered[-2].timestamp,
        ),
        validation_window=MlModelWindow(
            start_at=ordered[-2].timestamp,
            end_at=ordered[-1].timestamp,
        ),
        oos_sharpe=1.1,
        backtest_sharpe=1.3,
        ks_test_features_pvalue=0.41,
        shadow_diff_pct=0.02,
        promotion_state=PromotionState.REPLAY_ONLY,
        training_seed=request.training_seed,
        created_at=ordered[-1].timestamp,
        calibration_version=request.calibration_version,
        dataset_hash="b" * 64,
        model_bytes_b64="eyJwcmVkaWN0aW9uIjowLjd9",
    )
    return MlTrainerResult(
        artifact=artifact,
        train_row_count=len(request.rows) - 2,
        validation_row_count=2,
        bagging_folds_used=request.bagging_folds,
        optuna_trials_used=min(request.max_optuna_trials, 100),
        best_params={"learning_rate": 0.05, "num_leaves": 31},
    )


def test_build_local_lab_ml_artifact_training_report_uses_realized_target_when_dtr_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "local_replay_runtime.local_lab_ml_artifact_training.train_lightgbm_ml_artifact",
        _fake_train,
    )

    report = build_local_lab_ml_artifact_training_report(
        correlation_id="corr-ml",
        export_dir="E:/lab/export_dir",
        dataset=_dataset(),
        dtr_records=_dtr_records(),
        artifact_id="ml-artifact-1",
        calibration_version="cal.v1",
        training_seed=17,
    )

    assert report.status == "trained"
    assert report.ready is True
    assert report.target_policy == "net_return_bps_after_replay_realized_cost.v1"
    assert report.route_target_fallback_used is False
    assert report.aligned_dtr_count == 12
    assert report.training_row_count == 12
    assert report.artifact is not None
    assert report.artifact_hash == report.artifact.artifact_hash


def test_build_local_lab_ml_artifact_training_report_falls_back_to_route_target_without_dtr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "local_replay_runtime.local_lab_ml_artifact_training.train_lightgbm_ml_artifact",
        _fake_train,
    )

    report = build_local_lab_ml_artifact_training_report(
        correlation_id="corr-ml",
        export_dir="E:/lab/export_dir",
        dataset=_dataset(),
        artifact_id="ml-artifact-1",
        calibration_version="cal.v1",
        training_seed=17,
    )

    assert report.status == "trained"
    assert report.ready is True
    assert report.target_policy == "net_return_bps_after_route_cost_bps.v1"
    assert report.route_target_fallback_used is True


def test_build_local_lab_ml_artifact_training_report_fails_closed_on_missing_dtr_alignment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "local_replay_runtime.local_lab_ml_artifact_training.train_lightgbm_ml_artifact",
        _fake_train,
    )
    wrong_dtrs = (
        build_dtr(
            dtr_id="other-dataset:opp-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            gross_return=0.001,
            realized_cost=0.0003,
            timestamp=1_700_000_000.0,
        ),
    )

    report = build_local_lab_ml_artifact_training_report(
        correlation_id="corr-ml",
        export_dir="E:/lab/export_dir",
        dataset=_dataset(),
        dtr_records=wrong_dtrs,
        artifact_id="ml-artifact-1",
        calibration_version="cal.v1",
        training_seed=17,
    )

    assert report.status == "missing_replay_dtr_alignment"
    assert report.ready is False
    assert report.blocking_reasons


def test_build_local_lab_ml_artifact_training_report_exposes_dependency_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_dependency(_: MlTrainerRequest) -> MlTrainerResult:
        raise MlTrainerDependencyError("lightgbm missing")

    monkeypatch.setattr(
        "local_replay_runtime.local_lab_ml_artifact_training.train_lightgbm_ml_artifact",
        _raise_dependency,
    )

    report = build_local_lab_ml_artifact_training_report(
        correlation_id="corr-ml",
        export_dir="E:/lab/export_dir",
        dataset=_dataset(),
        artifact_id="ml-artifact-1",
        calibration_version="cal.v1",
        training_seed=17,
    )

    assert report.status == "trainer_dependency_missing"
    assert report.ready is False
