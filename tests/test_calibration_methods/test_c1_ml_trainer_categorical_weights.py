"""Tests C1.3.B (2026-05-21) — MlTrainerRequest categorical_feature_names + sample_weights.

Vérifie l'extension de l'API ml_trainer pour multi-pair training :
1. Backward compat : sans nouveaux params, comportement inchangé
2. Validator categorical_feature_names rejette features inconnues
3. Validator sample_weights vérifie longueur match rows
4. Defaults empty tuple = mono-pair pur (aucune categorical, aucune weight)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from calibration_methods.ml_trainer import (
    MlTrainerRequest,
    MlTrainingRow,
)


def _make_rows(
    n: int,
    *,
    pair: str = "BTCUSDT",
    extra_features: dict[str, float] | None = None,
) -> tuple[MlTrainingRow, ...]:
    """Build n training rows starting at 2025-01-01."""
    base = datetime(2025, 1, 1, tzinfo=UTC)
    features = {"close_return": 0.001, "high_low_range": 0.002, "volume": 100.0}
    if extra_features:
        features.update(extra_features)
    return tuple(
        MlTrainingRow(
            timestamp=base + timedelta(minutes=i),
            pair=pair,
            features=dict(features),
            target=0.0005 * i,
        )
        for i in range(n)
    )


def test_ml_trainer_request_backward_compat_no_new_params_2026_05_21() -> None:
    """Patch C1.3.B — sans nouveaux params, MlTrainerRequest fonctionne comme avant."""
    request = MlTrainerRequest(
        artifact_id="test_backward_compat",
        calibration_version="v1",
        rows=_make_rows(50),
        training_seed=42,
    )
    # Defaults empty
    assert request.categorical_feature_names == ()
    assert request.sample_weights == ()


def test_ml_trainer_request_accepts_categorical_feature_names_2026_05_21() -> None:
    """Patch C1.3.B — categorical_feature_names accepted si feature présente dans rows."""
    rows = _make_rows(50, extra_features={"pair_id": 0.0})
    request = MlTrainerRequest(
        artifact_id="test_categorical",
        calibration_version="v1",
        rows=rows,
        training_seed=42,
        categorical_feature_names=("pair_id",),
    )
    assert request.categorical_feature_names == ("pair_id",)


def test_ml_trainer_request_rejects_unknown_categorical_feature_2026_05_21() -> None:
    """Patch C1.3.B — categorical_feature_names doit exister dans row.features."""
    rows = _make_rows(50)  # no pair_id
    with pytest.raises(ValueError, match="not found in row features"):
        MlTrainerRequest(
            artifact_id="test_unknown_categorical",
            calibration_version="v1",
            rows=rows,
            training_seed=42,
            categorical_feature_names=("pair_id_not_present",),
        )


def test_ml_trainer_request_accepts_sample_weights_matching_rows_2026_05_21() -> None:
    """Patch C1.3.B — sample_weights length match rows OK."""
    rows = _make_rows(50)
    weights = tuple(1.0 + 0.01 * i for i in range(50))
    request = MlTrainerRequest(
        artifact_id="test_weights",
        calibration_version="v1",
        rows=rows,
        training_seed=42,
        sample_weights=weights,
    )
    assert len(request.sample_weights) == 50
    assert request.sample_weights[0] == 1.0


def test_ml_trainer_request_rejects_sample_weights_wrong_length_2026_05_21() -> None:
    """Patch C1.3.B — sample_weights length mismatch → ValueError clair."""
    rows = _make_rows(50)
    weights = tuple(1.0 for _ in range(30))  # wrong length
    with pytest.raises(ValueError, match="sample_weights length"):
        MlTrainerRequest(
            artifact_id="test_weights_wrong",
            calibration_version="v1",
            rows=rows,
            training_seed=42,
            sample_weights=weights,
        )


def test_ml_trainer_request_empty_sample_weights_ok_2026_05_21() -> None:
    """Patch C1.3.B — sample_weights=() (default) = uniform weights, aucune erreur."""
    rows = _make_rows(50)
    request = MlTrainerRequest(
        artifact_id="test_empty_weights",
        calibration_version="v1",
        rows=rows,
        training_seed=42,
        sample_weights=(),  # explicit empty
    )
    assert request.sample_weights == ()


def test_ml_trainer_request_multi_pair_setup_2026_05_21() -> None:
    """Patch C1.3.B — setup multi-pair complet : pair_id + sample_weights par pair."""
    # 30 BTCUSDT + 20 ETHUSDT rows
    btc_rows = _make_rows(30, pair="BTCUSDT", extra_features={"pair_id": 0.0})
    eth_rows = _make_rows(20, pair="ETHUSDT", extra_features={"pair_id": 1.0})
    all_rows = btc_rows + eth_rows
    # Inverse frequency weighting : BTC 1/30, ETH 1/20 (normalized)
    btc_weight = 1.0 / 30.0
    eth_weight = 1.0 / 20.0
    weights = tuple([btc_weight] * 30 + [eth_weight] * 20)
    request = MlTrainerRequest(
        artifact_id="test_multi_pair_complete",
        calibration_version="v1",
        rows=all_rows,
        training_seed=42,
        categorical_feature_names=("pair_id",),
        sample_weights=weights,
    )
    assert request.categorical_feature_names == ("pair_id",)
    assert len(request.sample_weights) == 50
    # BTC rows should have btc_weight, ETH rows eth_weight
    assert request.sample_weights[0] == pytest.approx(btc_weight)
    assert request.sample_weights[35] == pytest.approx(eth_weight)
