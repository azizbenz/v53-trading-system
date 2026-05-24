from __future__ import annotations

from pathlib import Path

import pytest

from local_replay_runtime.strategy_ladder_expected_edge_training import (
    ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES,
    BUILD14_OBSERVED_EXPECTED_EDGE_FEATURE_NAMES,
    DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
    ENGINE_D_GOVERNANCE_EXPECTED_EDGE_FEATURE_NAMES,
    EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES,
    StrategyLadderExpectedEdgeTrainingRequest,
    _require_supported_legacy_features,
    normalize_supported_expected_edge_feature_names,
)


def _request(
    tmp_path: Path,
    *,
    feature_names: tuple[str, ...] = DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
    use_replay_source: bool = False,
) -> StrategyLadderExpectedEdgeTrainingRequest:
    kwargs = {
        "artifact_id": "fixture",
        "calibration_version": "v1",
        "output_dir": tmp_path,
        "pair": "BTCUSDT",
        "timeframe": "1m",
        "train_start": "2025-01-01",
        "train_end": "2025-01-31",
        "feature_names": feature_names,
    }
    if use_replay_source:
        kwargs["b2_run_root"] = tmp_path
    else:
        kwargs["kline_root"] = tmp_path
    return StrategyLadderExpectedEdgeTrainingRequest(**kwargs)


def test_supported_features_count_25() -> None:
    assert len(SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES) == 25


def test_validator_accepts_kyle_lambda(tmp_path: Path) -> None:
    request = _request(
        tmp_path,
        feature_names=(*DEFAULT_EXPECTED_EDGE_FEATURE_NAMES, "kyle_lambda"),
        use_replay_source=True,
    )
    assert request.feature_names[-1] == "kyle_lambda"


def test_validator_accepts_anti_revenge_one_hot_triplet(tmp_path: Path) -> None:
    request = _request(
        tmp_path,
        feature_names=(
            *DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
            *ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES,
        ),
        use_replay_source=True,
    )
    assert request.feature_names[-3:] == ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES


def test_validator_rejects_partial_anti_revenge_one_hot(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="anti_revenge_state one-hot requires the full governed triplet"):
        _request(
            tmp_path,
            feature_names=(*DEFAULT_EXPECTED_EDGE_FEATURE_NAMES, "anti_revenge_state__active"),
            use_replay_source=True,
        )


def test_validator_rejects_unknown_feature(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported Strategy Ladder expected-edge features"):
        _request(
            tmp_path,
            feature_names=(*DEFAULT_EXPECTED_EDGE_FEATURE_NAMES, "rsi_14"),
            use_replay_source=True,
        )


def test_validator_default_backward_compat(tmp_path: Path) -> None:
    request = _request(tmp_path)
    assert request.feature_names == DEFAULT_EXPECTED_EDGE_FEATURE_NAMES


def test_validator_dedup_preserves_order() -> None:
    normalized = normalize_supported_expected_edge_feature_names(
        ["vpin", "vpin", "kyle_lambda", "close_return"]
    )
    assert normalized == ("vpin", "kyle_lambda", "close_return")


def test_legacy_kline_only_lock_unchanged() -> None:
    with pytest.raises(ValueError, match="legacy kline training only supports gold-store kline features"):
        _require_supported_legacy_features(("close_return", "vpin"))


def test_latency_penalty_bps_now_validatable(tmp_path: Path) -> None:
    request = _request(
        tmp_path,
        feature_names=(*DEFAULT_EXPECTED_EDGE_FEATURE_NAMES, "latency_penalty_bps"),
        use_replay_source=True,
    )
    assert "latency_penalty_bps" in request.feature_names


def test_build14_observed_features_present_in_set() -> None:
    for feature_name in BUILD14_OBSERVED_EXPECTED_EDGE_FEATURE_NAMES:
        assert feature_name in SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES


def test_engine_d_governance_features_present() -> None:
    for feature_name in ENGINE_D_GOVERNANCE_EXPECTED_EDGE_FEATURE_NAMES:
        assert feature_name in SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES


def test_extended_microstructure_features_present() -> None:
    expected = {
        *REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
        *EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    }
    assert expected.issubset(set(SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES))
