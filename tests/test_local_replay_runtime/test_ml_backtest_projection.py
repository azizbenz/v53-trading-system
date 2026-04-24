from __future__ import annotations

from local_replay_runtime.historical_data_gateway import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
)
from local_replay_runtime.ml_backtest_projection import (
    build_ml_backtest_training_dataset,
    build_ml_backtest_training_dataset_from_replay_and_dtr,
    project_historical_replay_opportunity_to_ml_sample,
    project_historical_replay_opportunity_to_ml_sample_with_replay_dtr,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


def _dataset() -> HistoricalReplayDataset:
    return HistoricalReplayDataset.from_records(
        dataset_id="dataset-ml-1",
        source_path="history.json",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="opp-1",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                regime="trend",
                raw_score=0.7,
                penalized_score=0.6,
                final_score=0.55,
                expected_edge_bps=18.0,
                spread_bps=1.0,
                slippage_bps=0.5,
                latency_penalty_bps=0.25,
                fill_ratio=0.9,
                target_decision_state=DecisionState.EXECUTED,
                ranking_position=1,
                candidate_size=1.2,
                final_size=1.0,
                tier="core",
                gross_return_bps=14.0,
                primary_reason="ok",
                feature_values={
                    "sweep_score_1m": 0.8,
                    "flow_coherence_1m": 0.4,
                    "label_text": "ignored",
                },
                shared_core_match=True,
            ),
        ),
        source="local_dataset",
    )


def test_project_historical_replay_opportunity_to_ml_sample_extracts_expected_information() -> None:
    dataset = _dataset()
    sample = project_historical_replay_opportunity_to_ml_sample(
        dataset.rows[0],
        dataset_id=dataset.dataset_id,
        allowed_feature_keys=("sweep_score_1m", "flow_coherence_1m"),
    )

    assert sample.dataset_id == "dataset-ml-1"
    assert sample.recognized_feature_values == {
        "flow_coherence_1m": 0.4,
        "sweep_score_1m": 0.8,
    }
    assert sample.route_features.route_cost_bps_total == 1.75
    assert sample.outcome.projected_net_return_bps == 12.25
    assert sample.outcome.target_decision_state == "executed"


def test_build_ml_backtest_training_dataset_summarizes_scope_and_feature_keys() -> None:
    ml_dataset = build_ml_backtest_training_dataset(
        _dataset(),
        allowed_feature_keys=("sweep_score_1m", "flow_coherence_1m"),
    )

    assert ml_dataset.sample_count == 1
    assert ml_dataset.recognized_feature_keys == ("flow_coherence_1m", "sweep_score_1m")
    assert ml_dataset.pair_scope == ("BTCUSDT",)
    assert ml_dataset.engine_scope == ("engine_a",)


def test_project_historical_replay_opportunity_to_ml_sample_with_replay_dtr_prefers_realized_target() -> None:
    dataset = _dataset()
    dtr_record = build_dtr(
        dtr_id="dataset-ml-1:opp-1",
        pair="BTCUSDT",
        engine_id="engine_a",
        decision_state=DecisionState.EXECUTED,
        gross_return=0.0014,
        realized_cost=0.0005,
        expected_cost=0.0004,
        ce_expected=0.0007,
        timestamp=1_700_000_000.0,
    )

    sample = project_historical_replay_opportunity_to_ml_sample_with_replay_dtr(
        dataset.rows[0],
        dataset_id=dataset.dataset_id,
        dtr_record=dtr_record,
        allowed_feature_keys=("sweep_score_1m", "flow_coherence_1m"),
    )

    assert sample.target_policy == "net_return_bps_after_replay_realized_cost.v1"
    assert sample.outcome.replay_dtr_id == "dataset-ml-1:opp-1"
    assert sample.outcome.realized_net_return_bps == 9.0
    assert sample.target_return_fraction == 0.0009


def test_build_ml_backtest_training_dataset_from_replay_and_dtr_uses_aligned_samples_only() -> None:
    dataset = _dataset()
    dtr_records = (
        build_dtr(
            dtr_id="dataset-ml-1:opp-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            gross_return=0.0014,
            realized_cost=0.0005,
            expected_cost=0.0004,
            ce_expected=0.0007,
            timestamp=1_700_000_000.0,
        ),
    )

    ml_dataset = build_ml_backtest_training_dataset_from_replay_and_dtr(
        dataset,
        dtr_records,
        allowed_feature_keys=("sweep_score_1m", "flow_coherence_1m"),
    )

    assert ml_dataset.target_policy == "net_return_bps_after_replay_realized_cost.v1"
    assert ml_dataset.source == "local_dataset+replay_dtr"
    assert ml_dataset.sample_count == 1
