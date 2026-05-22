"""Tests F16-B (2026-05-21) — persistence VPIN/OFI/queue_pressure.

Vérifie que :
1. StrategyLadderB2LabelStoreRow v2 expose vpin/cumulative_ofi/queue_pressure
2. Backward-compat : load d'un label store v1 sans ces champs → None defaults
3. `_extract_bridge_microstructure_scalars` extrait correctement depuis un
   bridge result (ou None pour les records absents)
4. Le builder lit ces 3 features depuis compatibility_payload
5. La liste REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES contient les 3
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from local_replay_runtime.strategy_ladder_b2_label_store_builder import (
    StrategyLadderB2LabelStoreRow,
    _EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS,
    _numeric_feature_values,
)
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES,
)
from local_replay_runtime.strategy_ladder_runner import (
    _extract_bridge_microstructure_scalars,
)


def test_label_store_row_v2_exposes_vpin_ofi_queue_pressure_2026_05_21() -> None:
    """Patch F16-B Phase 3a — schema v2 ajoute 3 champs microstructure nullables."""
    row = StrategyLadderB2LabelStoreRow(
        candidate_id="c1",
        engine_id="engine_c",
        pair="BTCUSDT",
        timeframe="15m",
        capital_bucket=400,
        decision_timestamp_ms=1,
        feature_timestamp_ms=1,
        replay_record_id="r1",
        evidence_class="SCRATCH_ONLY",
        label_quality_status="LABEL_QUALITY_NOT_PROVEN",
        replay_grounded_status="REPLAY_GROUNDED_NOT_PROVEN",
        replay_quality_status="REPLAY_QUALITY_NOT_PROVEN",
        execution_fidelity_status="EXECUTION_FIDELITY_NOT_PROVEN",
        entry_reference_status="ENTRY_REFERENCE_NOT_AVAILABLE",
        mfe_mae_status="MFE_MAE_NOT_AVAILABLE",
        vpin=0.42,
        cumulative_ofi=0.11,
        queue_pressure=-0.15,
    )
    assert row.schema_version == "strategy_ladder.b2_label_store_row.v2"
    assert row.vpin == 0.42
    assert row.cumulative_ofi == 0.11
    assert row.queue_pressure == -0.15

    # JSON roundtrip
    loaded = StrategyLadderB2LabelStoreRow.model_validate_json(row.model_dump_json())
    assert loaded.vpin == 0.42
    assert loaded.cumulative_ofi == 0.11
    assert loaded.queue_pressure == -0.15


def test_label_store_row_backward_compat_v1_without_vpin_2026_05_21() -> None:
    """Patch F16-B Phase 3a — anciens label stores v1 chargent avec None defaults."""
    # Simule un label store v1 sérialisé avec tous les champs required v1 mais
    # SANS les 3 nouveaux champs F16-B (vpin/cumulative_ofi/queue_pressure).
    legacy_json = (
        '{"candidate_id":"c2","engine_id":"engine_a","pair":"BTCUSDT",'
        '"timeframe":"1m","capital_bucket":400,"decision_timestamp_ms":1,'
        '"feature_timestamp_ms":1,"replay_record_id":"r2",'
        '"evidence_class":"SCRATCH_ONLY",'
        '"label_quality_status":"LABEL_QUALITY_NOT_PROVEN",'
        '"replay_grounded_status":"REPLAY_GROUNDED_NOT_PROVEN",'
        '"replay_quality_status":"REPLAY_QUALITY_NOT_PROVEN",'
        '"execution_fidelity_status":"EXECUTION_FIDELITY_NOT_PROVEN",'
        '"entry_reference_status":"ENTRY_REFERENCE_NOT_AVAILABLE",'
        '"mfe_mae_status":"MFE_MAE_NOT_AVAILABLE"}'
    )
    row = StrategyLadderB2LabelStoreRow.model_validate_json(legacy_json)
    assert row.vpin is None
    assert row.cumulative_ofi is None
    assert row.queue_pressure is None


def test_extract_bridge_microstructure_scalars_handles_none_2026_05_21() -> None:
    """Patch F16-B Phase 3b — None bridge → all None scalars."""
    scalars = _extract_bridge_microstructure_scalars(None)
    assert scalars == {
        "vpin": None,
        "cumulative_ofi": None,
        "queue_pressure": None,
    }


def test_extract_bridge_microstructure_scalars_extracts_values_2026_05_21() -> None:
    """Patch F16-B Phase 3b — bridge avec records → scalaires extraits."""
    bridge = SimpleNamespace(
        vpin_record=SimpleNamespace(value=0.42),
        ofi_record=SimpleNamespace(value=0.11),
        queue_pressure_record=SimpleNamespace(value=-0.15),
    )
    scalars = _extract_bridge_microstructure_scalars(bridge)
    assert scalars == {
        "vpin": 0.42,
        "cumulative_ofi": 0.11,
        "queue_pressure": -0.15,
    }


def test_extract_bridge_microstructure_scalars_partial_records_2026_05_21() -> None:
    """Patch F16-B Phase 3b — records partiels (e.g. OFI insufficient) → None pour absents."""
    bridge = SimpleNamespace(
        vpin_record=SimpleNamespace(value=0.42),
        ofi_record=None,  # ex: OFI_INSUFFICIENT_BOOK_STATES
        queue_pressure_record=SimpleNamespace(value=-0.15),
    )
    scalars = _extract_bridge_microstructure_scalars(bridge)
    assert scalars["vpin"] == 0.42
    assert scalars["cumulative_ofi"] is None
    assert scalars["queue_pressure"] == -0.15


def test_extract_bridge_microstructure_scalars_robust_to_bad_values_2026_05_21() -> None:
    """Patch F16-B Phase 3b — robustesse: TypeError / AttributeError swallowed → None."""
    bridge = SimpleNamespace(
        vpin_record=SimpleNamespace(value="not_a_number"),
        ofi_record=SimpleNamespace(value=0.0),
        queue_pressure_record=SimpleNamespace(),  # no value attr
    )
    scalars = _extract_bridge_microstructure_scalars(bridge)
    assert scalars["vpin"] is None
    assert scalars["cumulative_ofi"] == 0.0
    assert scalars["queue_pressure"] is None


def test_numeric_feature_values_augments_vpin_ofi_queue_from_payload_2026_05_21() -> None:
    """Patch F16-B Phase 3c — _numeric_feature_values pioche vpin/ofi/queue depuis payload."""
    payload = {
        "feature_values": {"close_return": 0.001, "high_low_range": 0.0025, "volume": 12.3},
        "spread_bps": 1.5,
        "vpin": 0.38,
        "cumulative_ofi": 0.22,
        "queue_pressure": 0.0,
    }
    features = _numeric_feature_values(payload)
    assert features["close_return"] == 0.001
    assert features["high_low_range"] == 0.0025
    assert features["volume"] == 12.3
    assert features["spread_bps"] == 1.5
    assert features["vpin"] == 0.38
    assert features["cumulative_ofi"] == 0.22
    assert features["queue_pressure"] == 0.0


def test_numeric_feature_values_missing_vpin_returns_no_key_2026_05_21() -> None:
    """Patch F16-B Phase 3c — si payload n'a pas vpin/ofi/queue, dict ne contient pas la clé."""
    payload = {
        "feature_values": {"close_return": 0.001},
    }
    features = _numeric_feature_values(payload)
    assert "vpin" not in features
    assert "cumulative_ofi" not in features
    assert "queue_pressure" not in features
    assert features["close_return"] == 0.001


def test_expected_edge_augmented_feature_keys_contains_microstructure_2026_05_21() -> None:
    """Patch F16-B Phase 3c — la liste d'augmentation contient les 3 microstructure V5.3."""
    assert "vpin" in _EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS
    assert "cumulative_ofi" in _EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS
    assert "queue_pressure" in _EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS


def test_replay_microstructure_feature_names_contains_vpin_ofi_queue_2026_05_21() -> None:
    """Patch F16-B Phase 3c — REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES augmenté."""
    assert "vpin" in REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES
    assert "cumulative_ofi" in REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES
    assert "queue_pressure" in REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES
    # SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES inclut LEGACY + MICROSTRUCTURE
    assert "vpin" in SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES
    assert "cumulative_ofi" in SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES
    assert "queue_pressure" in SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES


def test_request_validator_accepts_vpin_ofi_queue_with_b2_source_2026_05_21(
    tmp_path,
) -> None:
    """Patch F16-B Phase 3c — request validator accepte enriched features avec b2_run_root."""
    from local_replay_runtime.strategy_ladder_expected_edge_training import (
        StrategyLadderExpectedEdgeTrainingRequest,
    )

    b2_root = tmp_path / "b2"
    b2_root.mkdir()

    request = StrategyLadderExpectedEdgeTrainingRequest(
        artifact_id="test_enriched",
        calibration_version="v1",
        b2_run_root=b2_root,
        output_dir=tmp_path / "out",
        pair="BTCUSDT",
        timeframe="15m",
        train_start="2025-01-01",
        train_end="2025-01-31",
        feature_names=(
            "close_return",
            "high_low_range",
            "volume",
            "vpin",
            "cumulative_ofi",
            "queue_pressure",
            "spread_bps",
        ),
    )
    assert "vpin" in request.feature_names
    assert "cumulative_ofi" in request.feature_names
    assert "queue_pressure" in request.feature_names


def test_request_validator_rejects_vpin_without_replay_source_2026_05_21(
    tmp_path,
) -> None:
    """Patch F16-B Phase 3c — VPIN/OFI/queue exigent b2_run_root ou label_store_dataset_path."""
    from local_replay_runtime.strategy_ladder_expected_edge_training import (
        StrategyLadderExpectedEdgeTrainingRequest,
    )

    kline_root = tmp_path / "klines"
    kline_root.mkdir()

    with pytest.raises(ValueError, match="microstructure"):
        StrategyLadderExpectedEdgeTrainingRequest(
            artifact_id="test_kline_no_micro",
            calibration_version="v1",
            kline_root=kline_root,  # no b2_run_root, no label_store
            output_dir=tmp_path / "out",
            pair="BTCUSDT",
            timeframe="15m",
            train_start="2025-01-01",
            train_end="2025-01-31",
            feature_names=("close_return", "vpin"),  # vpin sans replay source → reject
        )
