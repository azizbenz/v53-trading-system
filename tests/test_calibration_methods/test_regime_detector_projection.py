from __future__ import annotations

import pytest

from calibration_methods import (
    project_regime_detector_training_row,
    project_regime_detector_training_rows,
    resolve_regime_detector_feature_set,
)
from interface_contracts import (
    RegimeDetectorDatasetSample,
    RegimeDetectorFeatureSetVersion,
    RegimeDetectorTrainingDataset,
    RegimeDurationBucket,
    RegimeToxicityBucket,
)


def _sample() -> RegimeDetectorDatasetSample:
    return RegimeDetectorDatasetSample(
        pair="BTCUSDT",
        anchor_timestamp_ns=1_700_000_000,
        feature_values={
            "spread_bps": 1.2,
            "order_book_imbalance": 0.3,
            "liquidity_thinning_score": 0.15,
            "ofi_short_window": 0.21,
            "aggressive_trade_imbalance": 0.08,
            "short_window_volatility": 4.5,
            "real_wall_score_bid": 0.72,
            "real_wall_score_ask": 0.22,
            "spoof_like_suspicion_bid": 0.18,
            "spoof_like_suspicion_ask": 0.07,
            "deceptive_liquidity_score": 0.18,
            "book_shape_skew": 0.11,
            "microprice_pressure": 0.33,
            "executed_vs_displayed_bid": 0.4,
            "executed_vs_displayed_ask": 0.2,
            "wall_pullaway_bid": 0.1,
            "wall_pullaway_ask": 0.05,
            "observation_coverage_ratio": 0.8,
        },
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        transition_next_window=1,
        duration_bucket=RegimeDurationBucket.SHORT,
        toxicity_bucket=RegimeToxicityBucket.ELEVATED,
        future_steps_observed=2,
        input_data_hash="a" * 64,
        feature_hash="b" * 64,
        label_config_hash="c" * 64,
        reason_codes=("REGIME_LABEL_TRANSITION",),
    )


def test_project_regime_detector_training_row_preserves_labels() -> None:
    row = project_regime_detector_training_row(_sample())

    assert row.pair == "BTCUSDT"
    assert row.transition_next_window == 1
    assert row.duration_bucket == RegimeDurationBucket.SHORT
    assert row.toxicity_bucket == "elevated"
    assert row.feature_set_version == RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2
    assert row.features["real_wall_score_bid"] == pytest.approx(0.72)


def test_project_regime_detector_training_rows_supports_feature_subset() -> None:
    sample = _sample()
    dataset = RegimeDetectorTrainingDataset(
        dataset_id="regime-dataset-1",
        source_path="build/tests/regime_dataset.json",
        source="historical_snapshot_batch",
        feature_set_version=sample.feature_set_version,
        label_config_hash=sample.label_config_hash,
        samples=(sample,),
        pair_scope=("BTCUSDT",),
        feature_names=sample.feature_names,
    )

    rows = project_regime_detector_training_rows(
        dataset,
        selected_feature_names=("deceptive_liquidity_score",),
    )

    assert len(rows) == 1
    assert tuple(rows[0].features) == ("deceptive_liquidity_score",)
    assert rows[0].features["deceptive_liquidity_score"] == pytest.approx(0.18)


def test_project_regime_detector_training_row_rejects_missing_feature() -> None:
    with pytest.raises(ValueError, match="missing regime training feature"):
        project_regime_detector_training_row(
            _sample(),
            selected_feature_names=("not_present",),
        )


def test_project_regime_detector_training_rows_supports_feature_profile() -> None:
    sample = _sample()
    dataset = RegimeDetectorTrainingDataset(
        dataset_id="regime-dataset-1",
        source_path="build/tests/regime_dataset.json",
        source="historical_snapshot_batch",
        feature_set_version=sample.feature_set_version,
        label_config_hash=sample.label_config_hash,
        samples=(sample,),
        pair_scope=("BTCUSDT",),
        feature_names=sample.feature_names,
    )

    rows = project_regime_detector_training_rows(
        dataset,
        feature_profile="core_v1",
    )

    expected = tuple(
        feature
        for feature in resolve_regime_detector_feature_set("core_v1")
        if feature in sample.feature_values
    )
    assert tuple(rows[0].features) == expected


def test_project_regime_detector_training_row_rejects_ambiguous_feature_selection() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        project_regime_detector_training_row(
            _sample(),
            selected_feature_names=("real_wall_score_bid",),
            feature_profile="core_v1",
        )
