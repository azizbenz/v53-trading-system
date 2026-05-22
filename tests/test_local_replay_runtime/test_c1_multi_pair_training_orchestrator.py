"""Tests C1.3.C (2026-05-21) — multi-pair training orchestrator.

Vérifie :
1. Request validator : pairs non-empty + dedupliqué + pair_id in feature_names
2. Pair_id assignment déterministe (sorted alphabetical, ZERO hardcode)
3. Inverse-frequency weighting balance correct (BTC 10x ETH → BTC weight ÷10)
4. build_multi_pair_training_rows concat + weight alignment correct
5. build_multi_pair_ml_trainer_request wires categorical + weights vers C1.3.B
6. ZERO hardcoded pair name (parametrized avec noms arbitraires)
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from calibration_methods import MlTrainingRow
from local_replay_runtime.strategy_ladder_multi_pair_expected_edge_training import (
    PAIR_ID_FEATURE_KEY,
    StrategyLadderMultiPairExpectedEdgeTrainingRequest,
    _assign_pair_ids_deterministic,
    _compute_inverse_frequency_weights,
    build_multi_pair_ml_trainer_request,
    build_multi_pair_training_rows,
    _build_multi_pair_pair_assignment,
)


def _make_rows(n: int, pair: str) -> tuple[MlTrainingRow, ...]:
    """Generic rows builder, ZERO hardcoded pair."""
    base = datetime(2025, 1, 1, tzinfo=UTC)
    return tuple(
        MlTrainingRow(
            timestamp=base + timedelta(minutes=i),
            pair=pair,
            features={"close_return": 0.001 * i, "high_low_range": 0.002, "volume": 100.0},
            target=0.0005 * i,
        )
        for i in range(n)
    )


def test_request_validator_accepts_arbitrary_pair_names_2026_05_21(tmp_path: Path) -> None:
    """Patch C1.3.C — accepte n'importe quels noms (MMXX, XYZ123, FUTURE_42)."""
    request = StrategyLadderMultiPairExpectedEdgeTrainingRequest(
        artifact_id="test_arbitrary",
        calibration_version="v1",
        pairs=("MMXX", "XYZ123", "FUTURE_PAIR_42"),
        timeframe="15m",
        output_dir=tmp_path,
        train_start="2025-01-01",
        train_end="2025-06-30",
    )
    assert request.pairs == ("MMXX", "XYZ123", "FUTURE_PAIR_42")


def test_request_validator_rejects_empty_pairs_2026_05_21(tmp_path: Path) -> None:
    """Patch C1.3.C — pairs vide rejected."""
    with pytest.raises(ValueError, match="MULTI_PAIR_TRAINING_EMPTY"):
        StrategyLadderMultiPairExpectedEdgeTrainingRequest(
            artifact_id="test_empty",
            calibration_version="v1",
            pairs=("",),  # blank only
            timeframe="15m",
            output_dir=tmp_path,
            train_start="2025-01-01",
            train_end="2025-06-30",
        )


def test_request_validator_deduplicates_pairs_2026_05_21(tmp_path: Path) -> None:
    """Patch C1.3.C — doublons dans pairs → déduplication."""
    request = StrategyLadderMultiPairExpectedEdgeTrainingRequest(
        artifact_id="test_dedup",
        calibration_version="v1",
        pairs=("ALPHA", "BETA", "ALPHA"),  # ALPHA twice
        timeframe="15m",
        output_dir=tmp_path,
        train_start="2025-01-01",
        train_end="2025-06-30",
    )
    assert request.pairs == ("ALPHA", "BETA")


def test_request_validator_requires_pair_id_in_features_2026_05_21(tmp_path: Path) -> None:
    """Patch C1.3.C — pair_id MUST be in feature_names sinon model ne distingue pas pairs."""
    with pytest.raises(ValueError, match="MISSING_PAIR_ID"):
        StrategyLadderMultiPairExpectedEdgeTrainingRequest(
            artifact_id="test_no_pair_id",
            calibration_version="v1",
            pairs=("ALPHA", "BETA"),
            timeframe="15m",
            output_dir=tmp_path,
            train_start="2025-01-01",
            train_end="2025-06-30",
            feature_names=("close_return", "high_low_range", "volume"),  # no pair_id
        )


def test_request_validator_rejects_label_store_missing_pair_2026_05_21(tmp_path: Path) -> None:
    """Patch C1.3.C — label_store_dataset_paths must include all pairs si fourni."""
    with pytest.raises(ValueError, match="LABEL_STORE_MISSING"):
        StrategyLadderMultiPairExpectedEdgeTrainingRequest(
            artifact_id="test_label_store_missing",
            calibration_version="v1",
            pairs=("ALPHA", "BETA"),
            timeframe="15m",
            output_dir=tmp_path,
            train_start="2025-01-01",
            train_end="2025-06-30",
            label_store_dataset_paths={"ALPHA": tmp_path / "alpha.jsonl"},  # missing BETA
        )


def test_assign_pair_ids_deterministic_sorted_2026_05_21() -> None:
    """Patch C1.3.C — assignment is sorted alphabetical, NOT hash-based."""
    result1 = _assign_pair_ids_deterministic(("BETA", "ALPHA", "GAMMA"))
    result2 = _assign_pair_ids_deterministic(("GAMMA", "ALPHA", "BETA"))
    assert result1 == result2 == {"ALPHA": 0, "BETA": 1, "GAMMA": 2}


def test_assign_pair_ids_handles_blanks_2026_05_21() -> None:
    """Patch C1.3.C — blank/empty pairs sont filtrés."""
    result = _assign_pair_ids_deterministic(("ALPHA", "", "BETA", "  "))
    assert result == {"ALPHA": 0, "BETA": 1}


def test_inverse_frequency_weights_balance_imbalance_2026_05_21() -> None:
    """Patch C1.3.C — pair avec 10x samples a 1/10 weight (balance imbalance)."""
    # BTC 100 samples, ETH 10 samples → BTC weight ÷10 d'ETH
    counts = {"BTC": 100, "ETH": 10}
    weights = _compute_inverse_frequency_weights(counts)
    # target_per_pair = 110 / 2 = 55
    # BTC weight = 55 / 100 = 0.55
    # ETH weight = 55 / 10 = 5.5
    assert weights["BTC"] == pytest.approx(0.55)
    assert weights["ETH"] == pytest.approx(5.5)
    # BTC contribution after weighting : 100 × 0.55 = 55
    # ETH contribution after weighting : 10 × 5.5 = 55
    # → balanced!
    assert pytest.approx(weights["BTC"] * counts["BTC"]) == weights["ETH"] * counts["ETH"]


def test_inverse_frequency_weights_uniform_when_balanced_2026_05_21() -> None:
    """Patch C1.3.C — pairs déjà balancés → weights uniformes."""
    counts = {"ALPHA": 50, "BETA": 50}
    weights = _compute_inverse_frequency_weights(counts)
    assert weights["ALPHA"] == pytest.approx(1.0)
    assert weights["BETA"] == pytest.approx(1.0)


def test_build_multi_pair_training_rows_concat_with_pair_id_2026_05_21() -> None:
    """Patch C1.3.C — rows concat + pair_id added + weights aligned."""
    rows_per_pair = {
        "ALPHA": _make_rows(30, "ALPHA"),
        "BETA": _make_rows(20, "BETA"),
    }
    assignment = _build_multi_pair_pair_assignment(
        pairs=("ALPHA", "BETA"),
        rows_per_pair=rows_per_pair,
        apply_inverse_frequency=True,
    )
    rows, weights = build_multi_pair_training_rows(
        rows_per_pair=rows_per_pair,
        pair_assignment=assignment,
    )
    assert len(rows) == 50  # 30 + 20
    assert len(weights) == 50  # aligned
    # ALPHA rows have pair_id=0 (sorted alpha first)
    alpha_rows = [r for r in rows if r.pair == "ALPHA"]
    assert all(r.features[PAIR_ID_FEATURE_KEY] == 0.0 for r in alpha_rows)
    # BETA rows have pair_id=1
    beta_rows = [r for r in rows if r.pair == "BETA"]
    assert all(r.features[PAIR_ID_FEATURE_KEY] == 1.0 for r in beta_rows)
    # ALPHA weight < BETA weight (ALPHA has more samples → less weight per sample)
    alpha_weight = assignment.pair_to_weight["ALPHA"]
    beta_weight = assignment.pair_to_weight["BETA"]
    assert alpha_weight < beta_weight


def test_build_multi_pair_ml_trainer_request_wires_categorical_2026_05_21() -> None:
    """Patch C1.3.C → C1.3.B — categorical_feature_names=("pair_id",) propagé."""
    rows = _make_rows(50, "ALPHA")
    # Augment with pair_id manually
    augmented_rows = tuple(
        MlTrainingRow(
            timestamp=r.timestamp,
            pair=r.pair,
            features={**r.features, PAIR_ID_FEATURE_KEY: 0.0},
            target=r.target,
        )
        for r in rows
    )
    weights = tuple(1.0 for _ in range(50))
    trainer_request = build_multi_pair_ml_trainer_request(
        artifact_id="test_wire",
        calibration_version="v1",
        rows=augmented_rows,
        sample_weights=weights,
        training_seed=42,
        max_optuna_trials=0,
        use_categorical_pair_id=True,
    )
    assert trainer_request.categorical_feature_names == (PAIR_ID_FEATURE_KEY,)
    # Uniform weights → sample_weights empty (preserves byte-equal mono-pair regression)
    assert trainer_request.sample_weights == ()


def test_build_multi_pair_ml_trainer_request_passes_variable_weights_2026_05_21() -> None:
    """Patch C1.3.C → C1.3.B — weights non-uniformes propagés à MlTrainerRequest."""
    rows = _make_rows(50, "ALPHA")
    augmented_rows = tuple(
        MlTrainingRow(
            timestamp=r.timestamp,
            pair=r.pair,
            features={**r.features, PAIR_ID_FEATURE_KEY: 0.0},
            target=r.target,
        )
        for r in rows
    )
    # Variable weights (first 30 weight 1.0, last 20 weight 2.0)
    weights = tuple([1.0] * 30 + [2.0] * 20)
    trainer_request = build_multi_pair_ml_trainer_request(
        artifact_id="test_variable_weights",
        calibration_version="v1",
        rows=augmented_rows,
        sample_weights=weights,
        training_seed=42,
        max_optuna_trials=0,
        use_categorical_pair_id=True,
    )
    assert trainer_request.sample_weights == weights


def test_build_multi_pair_ml_trainer_request_categorical_off_2026_05_21() -> None:
    """Patch C1.3.C — use_categorical_pair_id=False → categorical_feature_names empty."""
    rows = _make_rows(50, "ALPHA")
    augmented = tuple(
        MlTrainingRow(
            timestamp=r.timestamp, pair=r.pair,
            features={**r.features, PAIR_ID_FEATURE_KEY: 0.0}, target=r.target,
        )
        for r in rows
    )
    trainer_request = build_multi_pair_ml_trainer_request(
        artifact_id="test_categorical_off",
        calibration_version="v1",
        rows=augmented,
        sample_weights=tuple(1.0 for _ in range(50)),
        training_seed=42,
        max_optuna_trials=0,
        use_categorical_pair_id=False,
    )
    assert trainer_request.categorical_feature_names == ()


def test_multi_pair_training_rows_deterministic_ordering_2026_05_21() -> None:
    """Patch C1.3.C — output rows order is deterministic across runs (sorted)."""
    rows_per_pair = {
        "ZETA": _make_rows(5, "ZETA"),
        "ALPHA": _make_rows(5, "ALPHA"),
        "MIDDLE": _make_rows(5, "MIDDLE"),
    }
    assignment = _build_multi_pair_pair_assignment(
        pairs=("ZETA", "ALPHA", "MIDDLE"),
        rows_per_pair=rows_per_pair,
        apply_inverse_frequency=False,
    )
    rows1, _ = build_multi_pair_training_rows(
        rows_per_pair=rows_per_pair, pair_assignment=assignment,
    )
    rows2, _ = build_multi_pair_training_rows(
        rows_per_pair=rows_per_pair, pair_assignment=assignment,
    )
    # Same rows, same order
    assert [(r.pair, r.timestamp) for r in rows1] == [(r.pair, r.timestamp) for r in rows2]
    # ALPHA rows first (pair_id=0), then MIDDLE (1), then ZETA (2)
    first_pair = rows1[0].pair
    last_pair = rows1[-1].pair
    assert first_pair == "ALPHA"
    assert last_pair == "ZETA"
