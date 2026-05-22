"""Tests C1.3.D + Phase 4 (2026-05-21) — inference helper + end-to-end integration.

C1.3.D : predict_expected_edge_for_pair + batch + load_multi_pair_inference_artifact
Phase 4 : intégration full chain C1.3.A → 3.B → 3.C → 3.D avec fake LightGBM.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pytest

from local_replay_runtime.pair_capability_discovery import (
    discover_pair_capabilities,
    filter_pairs_for_training,
)
from local_replay_runtime.strategy_ladder_multi_pair_expected_edge_training import (
    PAIR_ID_FEATURE_KEY,
    MultiPairExpectedEdgeInferenceArtifact,
    StrategyLadderMultiPairExpectedEdgeTrainingRequest,
    _assign_pair_ids_deterministic,
    _compute_inverse_frequency_weights,
    _build_multi_pair_pair_assignment,
    build_multi_pair_ml_trainer_request,
    build_multi_pair_training_rows,
    predict_expected_edge_batch,
    predict_expected_edge_for_pair,
)


# ---------------------------------------------------------------------------
# Fake booster — avoids dependency on lightgbm install for unit tests
# ---------------------------------------------------------------------------


@dataclass
class _FakeBooster:
    """Fake LightGBM Booster mimicking .predict(matrix) → list[float]."""

    expected_feature_count: int
    response: float = 7.5  # default expected_edge_bps prediction
    last_predict_input: list[list[float]] | None = None

    def predict(self, matrix: list[list[float]]) -> list[float]:
        """Mimic lightgbm.Booster.predict signature."""
        self.last_predict_input = list(matrix)
        # Validate input shape matches expected_feature_count
        for row in matrix:
            if len(row) != self.expected_feature_count:
                raise ValueError(
                    f"_FakeBooster expects {self.expected_feature_count} features per row, "
                    f"got {len(row)}"
                )
        return [self.response] * len(matrix)


def _make_artifact(
    *,
    feature_names: tuple[str, ...] = (
        "close_return", "high_low_range", "volume", PAIR_ID_FEATURE_KEY,
    ),
    pair_id_encoding: dict[str, int] | None = None,
    response: float = 7.5,
) -> MultiPairExpectedEdgeInferenceArtifact:
    """Build a fake inference artifact for unit testing."""
    if pair_id_encoding is None:
        pair_id_encoding = {"ALPHA": 0, "BETA": 1, "GAMMA": 2}
    return MultiPairExpectedEdgeInferenceArtifact(
        booster=_FakeBooster(
            expected_feature_count=len(feature_names),
            response=response,
        ),
        pair_id_encoding=pair_id_encoding,
        feature_names=feature_names,
    )


# ---------------------------------------------------------------------------
# C1.3.D tests : predict_expected_edge_for_pair
# ---------------------------------------------------------------------------


def test_predict_returns_booster_output_for_known_pair_2026_05_21() -> None:
    """Patch C1.3.D — predict returns booster.predict() result for known pair."""
    artifact = _make_artifact(response=12.5)
    edge = predict_expected_edge_for_pair(
        artifact=artifact,
        pair="ALPHA",
        features={"close_return": 0.001, "high_low_range": 0.002, "volume": 100.0},
    )
    assert edge == 12.5
    # Verify pair_id was injected as float(0) (ALPHA→0)
    feature_vector = artifact.booster.last_predict_input[0]
    pair_id_index = artifact.feature_names.index(PAIR_ID_FEATURE_KEY)
    assert feature_vector[pair_id_index] == 0.0


def test_predict_injects_correct_pair_id_for_each_pair_2026_05_21() -> None:
    """Patch C1.3.D — pair_id injection uses encoding (BETA→1, GAMMA→2)."""
    artifact = _make_artifact()
    features = {"close_return": 0.0, "high_low_range": 0.0, "volume": 0.0}
    for pair, expected_id in [("ALPHA", 0), ("BETA", 1), ("GAMMA", 2)]:
        predict_expected_edge_for_pair(
            artifact=artifact, pair=pair, features=features,
        )
        feature_vector = artifact.booster.last_predict_input[0]
        pair_id_index = artifact.feature_names.index(PAIR_ID_FEATURE_KEY)
        assert feature_vector[pair_id_index] == float(expected_id), (
            f"pair={pair} should encode to {expected_id}, got {feature_vector[pair_id_index]}"
        )


def test_predict_rejects_unknown_pair_with_actionable_message_2026_05_21() -> None:
    """Patch C1.3.D — pair unknown → fail-close with hint."""
    artifact = _make_artifact()
    with pytest.raises(ValueError) as exc_info:
        predict_expected_edge_for_pair(
            artifact=artifact,
            pair="UNKNOWN_PAIR_2027",
            features={"close_return": 0.0, "high_low_range": 0.0, "volume": 0.0},
        )
    err = str(exc_info.value)
    assert "DOCTRINE_MULTI_PAIR_INFERENCE_PAIR_UNKNOWN" in err
    assert "UNKNOWN_PAIR_2027" in err
    assert "Known pairs" in err  # actionable hint listing known pairs
    assert "mono-pair" in err  # alternative suggestion


def test_predict_rejects_missing_features_with_clear_list_2026_05_21() -> None:
    """Patch C1.3.D — missing feature keys → ValueError listing missing."""
    artifact = _make_artifact()
    with pytest.raises(ValueError) as exc_info:
        predict_expected_edge_for_pair(
            artifact=artifact,
            pair="ALPHA",
            features={"close_return": 0.0},  # missing high_low_range + volume
        )
    err = str(exc_info.value)
    assert "FEATURES_INCOMPLETE" in err
    assert "high_low_range" in err
    assert "volume" in err


def test_predict_overrides_user_provided_pair_id_2026_05_21() -> None:
    """Patch C1.3.D — user-provided pair_id is OVERRIDDEN by encoding (protection)."""
    artifact = _make_artifact()
    # User accidentally provides pair_id=999 but pair="BETA" should use encoding=1
    predict_expected_edge_for_pair(
        artifact=artifact,
        pair="BETA",
        features={
            "close_return": 0.0, "high_low_range": 0.0, "volume": 0.0,
            PAIR_ID_FEATURE_KEY: 999.0,  # incoherent — should be overridden
        },
    )
    feature_vector = artifact.booster.last_predict_input[0]
    pair_id_index = artifact.feature_names.index(PAIR_ID_FEATURE_KEY)
    # Encoding wins : BETA→1, not 999
    assert feature_vector[pair_id_index] == 1.0


def test_predict_respects_feature_name_ordering_2026_05_21() -> None:
    """Patch C1.3.D — feature vector built in artifact.feature_names order."""
    artifact = _make_artifact(
        feature_names=("volume", "close_return", PAIR_ID_FEATURE_KEY, "high_low_range"),
    )
    predict_expected_edge_for_pair(
        artifact=artifact,
        pair="ALPHA",
        features={
            "close_return": 1.0, "high_low_range": 2.0, "volume": 3.0,
        },
    )
    fv = artifact.booster.last_predict_input[0]
    # Order : volume, close_return, pair_id (ALPHA=0), high_low_range
    assert fv == [3.0, 1.0, 0.0, 2.0]


# ---------------------------------------------------------------------------
# C1.3.D tests : predict_expected_edge_batch
# ---------------------------------------------------------------------------


def test_predict_batch_returns_predictions_in_order_2026_05_21() -> None:
    """Patch C1.3.D — batch predict returns predictions in input order."""
    artifact = _make_artifact(response=8.0)
    batch = (
        ("ALPHA", {"close_return": 0.0, "high_low_range": 0.0, "volume": 0.0}),
        ("BETA", {"close_return": 0.0, "high_low_range": 0.0, "volume": 0.0}),
        ("GAMMA", {"close_return": 0.0, "high_low_range": 0.0, "volume": 0.0}),
    )
    predictions = predict_expected_edge_batch(
        artifact=artifact,
        pair_feature_batch=batch,
    )
    assert predictions == (8.0, 8.0, 8.0)
    # Verify pair_ids injected correctly per row
    matrix = artifact.booster.last_predict_input
    assert len(matrix) == 3
    pair_id_index = artifact.feature_names.index(PAIR_ID_FEATURE_KEY)
    assert matrix[0][pair_id_index] == 0.0  # ALPHA
    assert matrix[1][pair_id_index] == 1.0  # BETA
    assert matrix[2][pair_id_index] == 2.0  # GAMMA


def test_predict_batch_empty_returns_empty_tuple_2026_05_21() -> None:
    """Patch C1.3.D — batch empty → empty tuple, no booster call."""
    artifact = _make_artifact()
    predictions = predict_expected_edge_batch(
        artifact=artifact, pair_feature_batch=(),
    )
    assert predictions == ()
    assert artifact.booster.last_predict_input is None


def test_predict_batch_fails_on_first_unknown_pair_2026_05_21() -> None:
    """Patch C1.3.D — batch fails atomically si one pair unknown."""
    artifact = _make_artifact()
    with pytest.raises(ValueError, match="PAIR_UNKNOWN"):
        predict_expected_edge_batch(
            artifact=artifact,
            pair_feature_batch=(
                ("ALPHA", {"close_return": 0.0, "high_low_range": 0.0, "volume": 0.0}),
                ("UNKNOWN_2027", {"close_return": 0.0, "high_low_range": 0.0, "volume": 0.0}),
            ),
        )


# ---------------------------------------------------------------------------
# Phase 4 — End-to-end integration tests (C1.3.A → C1.3.B → C1.3.C → C1.3.D)
# ---------------------------------------------------------------------------


def _setup_pair_dirs(
    *,
    klines_root: Path,
    trades_root: Path,
    orderbook_root: Path,
    pairs_with_full_data: Iterable[str] = (),
    pairs_with_legacy_data: Iterable[str] = (),
) -> None:
    """Create empty pair dirs to simulate filesystem presence."""
    klines_root.mkdir(parents=True, exist_ok=True)
    trades_root.mkdir(parents=True, exist_ok=True)
    orderbook_root.mkdir(parents=True, exist_ok=True)
    for pair in pairs_with_full_data:
        (klines_root / pair).mkdir(exist_ok=True)
        (trades_root / pair).mkdir(exist_ok=True)
        (orderbook_root / pair).mkdir(exist_ok=True)
    for pair in pairs_with_legacy_data:
        (klines_root / pair).mkdir(exist_ok=True)
        (trades_root / pair).mkdir(exist_ok=True)
        # No orderbook for legacy pairs


def test_phase4_full_chain_admin_chooses_3_pairs_2026_05_21(tmp_path: Path) -> None:
    """Phase 4 — admin chooses 3 arbitrary pair names, full chain validates + filters."""
    klines = tmp_path / "klines"
    trades = tmp_path / "trades"
    orderbook = tmp_path / "orderbook"
    _setup_pair_dirs(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        pairs_with_full_data=("ARBITRARY_A", "ARBITRARY_B", "ARBITRARY_C"),
    )
    # Step 1 — discovery (C1.3.A)
    caps = discover_pair_capabilities(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        metadata_pairs=("ARBITRARY_A", "ARBITRARY_B", "ARBITRARY_C"),
    )
    # Step 2 — filter (C1.3.A)
    accepted, rejected = filter_pairs_for_training(
        requested_pairs=("ARBITRARY_A", "ARBITRARY_B", "ARBITRARY_C"),
        capabilities=caps,
        require_microstructure=True,
    )
    assert accepted == ("ARBITRARY_A", "ARBITRARY_B", "ARBITRARY_C")
    assert rejected == ()
    # Step 3 — build request (C1.3.C)
    request = StrategyLadderMultiPairExpectedEdgeTrainingRequest(
        artifact_id="phase4_test",
        calibration_version="v1",
        pairs=accepted,
        timeframe="15m",
        output_dir=tmp_path,
        train_start="2025-01-01",
        train_end="2025-06-30",
    )
    assert request.pairs == ("ARBITRARY_A", "ARBITRARY_B", "ARBITRARY_C")


def test_phase4_full_chain_legacy_pair_rejected_for_microstructure_2026_05_21(
    tmp_path: Path,
) -> None:
    """Phase 4 — admin choses pair without orderbook → filter rejects when microstructure required."""
    klines = tmp_path / "klines"
    trades = tmp_path / "trades"
    orderbook = tmp_path / "orderbook"
    _setup_pair_dirs(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        pairs_with_full_data=("FULL_PAIR",),
        pairs_with_legacy_data=("LEGACY_PAIR",),
    )
    caps = discover_pair_capabilities(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        metadata_pairs=("FULL_PAIR", "LEGACY_PAIR"),
    )
    accepted, rejected = filter_pairs_for_training(
        requested_pairs=("FULL_PAIR", "LEGACY_PAIR"),
        capabilities=caps,
        require_microstructure=True,
    )
    assert accepted == ("FULL_PAIR",)
    assert rejected == ("LEGACY_PAIR",)


def test_phase4_full_chain_assignment_to_inference_2026_05_21(tmp_path: Path) -> None:
    """Phase 4 — assignment used in C1.3.C also used in C1.3.D for inference consistency."""
    pairs = ("PAIR_X", "PAIR_Y", "PAIR_Z")
    assignment = _build_multi_pair_pair_assignment(
        pairs=pairs,
        rows_per_pair={p: () for p in pairs},  # empty rows OK for this test
        apply_inverse_frequency=False,
    )
    # Use same encoding in inference artifact
    artifact = _make_artifact(
        pair_id_encoding=assignment.pair_to_id,
        feature_names=("close_return", "high_low_range", "volume", PAIR_ID_FEATURE_KEY),
    )
    # Predict for PAIR_Y → pair_id should match assignment
    predict_expected_edge_for_pair(
        artifact=artifact,
        pair="PAIR_Y",
        features={"close_return": 0.0, "high_low_range": 0.0, "volume": 0.0},
    )
    pair_id_index = artifact.feature_names.index(PAIR_ID_FEATURE_KEY)
    actual_pair_id = artifact.booster.last_predict_input[0][pair_id_index]
    expected_pair_id = float(assignment.pair_to_id["PAIR_Y"])
    assert actual_pair_id == expected_pair_id, (
        f"Inference pair_id ({actual_pair_id}) must match training assignment "
        f"pair_id ({expected_pair_id}) for consistency"
    )
