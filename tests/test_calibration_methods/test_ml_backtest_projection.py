from __future__ import annotations

from calibration_methods import (
    project_ml_training_row_from_ml_backtest_sample,
    project_ml_training_rows_from_backtest_dataset,
)
from interface_contracts import MlBacktestOutcomeContext, MlBacktestRouteFeatures, MlBacktestTrainingDataset, MlBacktestTrainingSample
from local_replay_runtime.ml_backtest_projection import build_ml_backtest_training_dataset
from meta_minimal.dtr_core.decision_state_encoder import DecisionState


def _ml_backtest_dataset() -> MlBacktestTrainingDataset:
    return MlBacktestTrainingDataset(
        dataset_id="dataset-ml-1",
        source_path="history.json",
        source="local_dataset",
        samples=(
            MlBacktestTrainingSample(
                dataset_id="dataset-ml-1",
                opportunity_id="opp-1",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                regime="trend",
                tier="core",
                recognized_feature_values={
                    "sweep_score_1m": 0.8,
                    "flow_coherence_1m": 0.4,
                },
                route_features=MlBacktestRouteFeatures(
                    raw_score=0.7,
                    penalized_score=0.6,
                    final_score=0.55,
                    expected_edge_bps=18.0,
                    spread_bps=1.0,
                    slippage_bps=0.5,
                    latency_penalty_bps=0.25,
                    fill_ratio=0.9,
                    ranking_position=1,
                    candidate_size=1.2,
                    final_size=1.0,
                ),
                outcome=MlBacktestOutcomeContext(
                    gross_return_bps=14.0,
                    projected_net_return_bps=12.25,
                    target_decision_state=DecisionState.EXECUTED.value,
                    primary_reason="ok",
                ),
            ),
        ),
        pair_scope=("BTCUSDT",),
        engine_scope=("engine_a",),
        recognized_feature_keys=("flow_coherence_1m", "sweep_score_1m"),
    )


def test_project_ml_training_row_from_ml_backtest_sample_builds_trainer_ready_row() -> None:
    row = project_ml_training_row_from_ml_backtest_sample(_ml_backtest_dataset().samples[0])

    assert row.pair == "BTCUSDT"
    assert row.features["sweep_score_1m"] == 0.8
    assert row.features["route_expected_edge_bps"] == 18.0
    assert row.target == 0.001225


def test_project_ml_training_rows_from_backtest_dataset_builds_trainer_ready_rows() -> None:
    rows = project_ml_training_rows_from_backtest_dataset(
        _ml_backtest_dataset(),
    )

    assert len(rows) == 1
    assert rows[0].pair == "BTCUSDT"
    assert rows[0].features["sweep_score_1m"] == 0.8
    assert rows[0].features["route_expected_edge_bps"] == 18.0
    assert rows[0].target == 0.001225
