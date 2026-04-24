from __future__ import annotations

from interface_contracts import (
    ML_BACKTEST_REALIZED_TARGET_POLICY,
    ML_BACKTEST_ROUTE_FEATURE_NAMES,
    ML_BACKTEST_TARGET_POLICY,
    MlBacktestOutcomeContext,
    MlBacktestRouteFeatures,
    MlBacktestTrainingSample,
)


def test_ml_backtest_route_features_expose_prefixed_feature_map() -> None:
    route = MlBacktestRouteFeatures(
        raw_score=0.4,
        penalized_score=0.3,
        final_score=0.2,
        expected_edge_bps=8.0,
        spread_bps=1.5,
        slippage_bps=0.8,
        latency_penalty_bps=0.2,
        fill_ratio=0.9,
        ranking_position=2,
        candidate_size=1.4,
        final_size=1.1,
    )

    feature_map = route.as_prefixed_feature_map()

    assert tuple(feature_map) == ML_BACKTEST_ROUTE_FEATURE_NAMES
    assert route.route_cost_bps_total == 2.5
    assert feature_map["route_final_size"] == 1.1


def test_ml_backtest_training_sample_exposes_target_fraction_and_features() -> None:
    sample = MlBacktestTrainingSample(
        dataset_id="dataset-1",
        opportunity_id="opp-1",
        timestamp_ms=1_700_000_000_000,
        pair="BTCUSDT",
        engine_id="engine_a",
        target_policy=ML_BACKTEST_TARGET_POLICY,
        recognized_feature_values={"sweep_score_1m": 0.7},
        route_features=MlBacktestRouteFeatures(final_score=0.2),
        outcome=MlBacktestOutcomeContext(
            gross_return_bps=12.0,
            projected_net_return_bps=9.5,
        ),
    )

    trainer_features = sample.trainer_feature_values()

    assert sample.target_return_fraction == 0.00095
    assert sample.feature_names == ("sweep_score_1m",)
    assert trainer_features["sweep_score_1m"] == 0.7
    assert trainer_features["route_final_score"] == 0.2


def test_ml_backtest_training_sample_prefers_realized_target_when_present() -> None:
    sample = MlBacktestTrainingSample(
        dataset_id="dataset-1",
        opportunity_id="opp-1",
        timestamp_ms=1_700_000_000_000,
        pair="BTCUSDT",
        engine_id="engine_a",
        target_policy=ML_BACKTEST_REALIZED_TARGET_POLICY,
        recognized_feature_values={"sweep_score_1m": 0.7},
        route_features=MlBacktestRouteFeatures(final_score=0.2),
        outcome=MlBacktestOutcomeContext(
            gross_return_bps=12.0,
            projected_net_return_bps=9.5,
            realized_net_return_bps=7.0,
            replay_dtr_id="dataset-1:opp-1",
        ),
    )

    assert sample.target_return_fraction == 0.0007
