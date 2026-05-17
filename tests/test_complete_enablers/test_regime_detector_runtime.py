from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from backtest_artifact_import import package_regime_detector_artifact_for_transport
from complete_enablers import (
    DIRECTIONAL_RUNTIME_KEYS_FORBIDDEN,
    RegimeDetectorRuntime,
    RegimeDetectorSignalStatus,
    RUNTIME_REGIME_OUTPUT_MODE,
    RUNTIME_REGIME_OUTPUTS,
    load_regime_detector_runtime_artifact,
)
from complete_enablers.regime_detector_runtime_loader import RegimeDetectorArtifactLoadStatus
from data_backbone.microstructure import (
    LobAggTrade,
    LobBookLevel,
    LobDepth20Snapshot,
    build_lob_regime_feature_snapshot,
)
from interface_contracts import (
    PromotionState,
    RegimeDetectorArtifact,
    RegimeDetectorFeatureSetVersion,
    RegimeDetectorWindow,
)
from local_replay_runtime.regime_detector_dataset_builder import DATASET_BUILDER_LABEL_SCOPE
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir(
        "complete_enablers_regime_detector_runtime_tests",
        label,
    )


def _levels(best_price: float, best_size: float) -> tuple[LobBookLevel, ...]:
    return (
        LobBookLevel(price=best_price, size=best_size),
        LobBookLevel(price=best_price - 0.1, size=10.0),
    )


def _ask_levels(best_price: float, best_size: float) -> tuple[LobBookLevel, ...]:
    return (
        LobBookLevel(price=best_price, size=best_size),
        LobBookLevel(price=best_price + 0.1, size=10.0),
    )


def _features() -> object:
    depth = (
        LobDepth20Snapshot(
            pair="BTCUSDT",
            timestamp_ns=1_000_000_000,
            bids=_levels(100.0, 100.0),
            asks=_ask_levels(100.1, 20.0),
        ),
        LobDepth20Snapshot(
            pair="BTCUSDT",
            timestamp_ns=2_000_000_000,
            bids=_levels(100.0, 95.0),
            asks=_ask_levels(100.1, 25.0),
        ),
    )
    trades = (
        LobAggTrade(
            timestamp_ns=1_500_000_000,
            price=100.0,
            quantity=10.0,
            aggressor_side="sell",
        ),
    )
    return build_lob_regime_feature_snapshot(
        depth,
        trades,
        pair="BTCUSDT",
        computed_at_ns=2_000_000_000,
        touch_eps_bps=10.0,
    )


def _artifact_path(
    *,
    label: str,
    prediction: object,
    feature_names: tuple[str, ...] = (
        "real_wall_score_bid",
        "deceptive_liquidity_score",
        "microprice_pressure",
        "observation_coverage_ratio",
    ),
    pair_universe: tuple[str, ...] = ("BTCUSDT",),
    stale_after: datetime | None = None,
) -> Path:
    scratch = _scratch_dir(label)
    path = scratch / "source_regime_detector_artifact.json"
    created_at = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    artifact = RegimeDetectorArtifact.create(
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        feature_names=feature_names,
        feature_hash="a" * 64,
        pair_universe=pair_universe,
        train_window=RegimeDetectorWindow(
            start_at=datetime(2026, 1, 1, tzinfo=UTC),
            end_at=datetime(2026, 3, 31, tzinfo=UTC),
        ),
        validation_window=RegimeDetectorWindow(
            start_at=datetime(2026, 4, 1, tzinfo=UTC),
            end_at=datetime(2026, 4, 22, tzinfo=UTC),
        ),
        regime_labels=("calm", "transition", "toxic"),
        oos_metrics={"transition_auc": 0.71},
        shadow_metrics={"shadow_diff_pct": 0.02},
        promotion_state=PromotionState.REPLAY_ONLY,
        training_seed=17,
        created_at=created_at,
        calibration_version="lob-regime.v1",
        dataset_hash="b" * 64,
        model_bytes_b64=base64.b64encode(
            json.dumps({"prediction": prediction}).encode("utf-8")
        ).decode("ascii"),
        stale_after=stale_after,
    )
    path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return path


def _fake_lightgbm_module() -> SimpleNamespace:
    class FakeBooster:
        def __init__(self, *, model_str: str | None = None, model_file: str | None = None) -> None:
            assert model_file is None
            payload = json.loads(model_str or "{}")
            self._prediction = payload.get("prediction", 0.0)

        def predict(self, rows: list[list[float]]) -> list[object]:
            assert rows
            return [self._prediction]

    return SimpleNamespace(Booster=FakeBooster)


def test_regime_detector_runtime_loads_artifact_and_emits_shadow_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "complete_enablers.regime_detector_runtime._load_lightgbm_module",
        lambda: _fake_lightgbm_module(),
    )
    source_path = _artifact_path(label="active_source", prediction=[0.82, 0.21, 0.74, 0.0])
    export_dir = _scratch_dir("active_export")

    try:
        package = package_regime_detector_artifact_for_transport(
            export_dir,
            source_artifact_ref=str(source_path),
        )
        signal = RegimeDetectorRuntime().evaluate_from_supplementary_refs(
            features=_features(),
            supplementary_refs=(package.transport_artifact_ref, package.summary_ref),
        )

        assert signal.status == RegimeDetectorSignalStatus.ACTIVE
        assert signal.shadow_only is True
        assert signal.regime_transition_risk == pytest.approx(0.82)
        assert signal.market_toxicity_score == pytest.approx(0.74)
        assert signal.feature_hash == "a" * 64
        assert not hasattr(signal, "side")
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_path.parent, ignore_errors=True)


def test_regime_detector_runtime_degrades_to_neutral_without_artifact() -> None:
    signal = RegimeDetectorRuntime().evaluate_from_supplementary_refs(
        features=_features(),
        supplementary_refs=(),
    )

    assert signal.status == RegimeDetectorSignalStatus.NEUTRAL
    assert signal.regime_transition_risk == pytest.approx(0.0)
    assert signal.regime_stability_score == pytest.approx(1.0)


def test_regime_detector_runtime_rejects_directional_supplementary_refs() -> None:
    scratch = _scratch_dir("directional_regime_ref")
    forbidden_ref = scratch / "directional_regime_ref.json"
    forbidden_ref.write_text(
        json.dumps({"direction_up_300s_fee_safe": True}, indent=2),
        encoding="utf-8",
    )

    try:
        signal = RegimeDetectorRuntime().evaluate_from_supplementary_refs(
            features=_features(),
            supplementary_refs=(str(forbidden_ref),),
        )

        assert signal.status == RegimeDetectorSignalStatus.INVALID_ARTIFACT
        assert signal.reason_codes[0] == "REGIME_DIRECTIONAL_REF_FORBIDDEN"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_regime_runtime_outputs_are_non_directional_and_dataset_labels_are_local_lab_only() -> None:
    assert RUNTIME_REGIME_OUTPUT_MODE == "NON_DIRECTIONAL_ONLY"
    assert set(RUNTIME_REGIME_OUTPUTS) == {
        "regime_transition_risk",
        "regime_stability_score",
        "market_toxicity_score",
        "expected_duration_bucket",
    }
    assert "direction_up_300s_fee_safe" in DIRECTIONAL_RUNTIME_KEYS_FORBIDDEN
    assert "buy_probability" in DIRECTIONAL_RUNTIME_KEYS_FORBIDDEN
    assert DATASET_BUILDER_LABEL_SCOPE == "LOCAL_LAB_TRAINING_ONLY"


def test_regime_detector_runtime_degrades_on_feature_schema_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "complete_enablers.regime_detector_runtime._load_lightgbm_module",
        lambda: _fake_lightgbm_module(),
    )
    source_path = _artifact_path(
        label="schema_source",
        prediction=[0.8, 0.2, 0.7, 0.0],
        feature_names=("not_available_live",),
    )
    export_dir = _scratch_dir("schema_export")

    try:
        package = package_regime_detector_artifact_for_transport(
            export_dir,
            source_artifact_ref=str(source_path),
        )
        signal = RegimeDetectorRuntime().evaluate_from_supplementary_refs(
            features=_features(),
            supplementary_refs=(package.transport_artifact_ref, package.summary_ref),
        )

        assert signal.status == RegimeDetectorSignalStatus.FEATURE_SCHEMA_MISMATCH
        assert signal.regime_transition_risk == pytest.approx(0.0)
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_path.parent, ignore_errors=True)


def test_regime_detector_runtime_loader_rejects_stale_artifact() -> None:
    source_path = _artifact_path(
        label="stale_source",
        prediction=[0.8, 0.2, 0.7, 0.0],
        stale_after=datetime(2026, 4, 23, 12, 5, tzinfo=UTC),
    )
    export_dir = _scratch_dir("stale_export")

    try:
        package = package_regime_detector_artifact_for_transport(
            export_dir,
            source_artifact_ref=str(source_path),
        )
        selection = load_regime_detector_runtime_artifact(
            (package.transport_artifact_ref, package.summary_ref),
            as_of=datetime(2026, 4, 23, 12, 6, tzinfo=UTC),
        )

        assert selection.status == RegimeDetectorArtifactLoadStatus.STALE
        assert selection.artifact_ready is False
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_path.parent, ignore_errors=True)


def test_regime_detector_runtime_loader_rejects_feature_set_version_mismatch() -> None:
    source_path = _artifact_path(
        label="feature_set_mismatch_source",
        prediction=[0.8, 0.2, 0.7, 0.0],
    )
    export_dir = _scratch_dir("feature_set_mismatch_export")

    try:
        package = package_regime_detector_artifact_for_transport(
            export_dir,
            source_artifact_ref=str(source_path),
        )
        summary_path = Path(package.summary_ref)
        summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
        summary_payload["feature_set_version"] = "lob_regime_feature_set.v1"
        summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

        selection = load_regime_detector_runtime_artifact(
            (package.transport_artifact_ref, package.summary_ref),
        )

        assert selection.status == RegimeDetectorArtifactLoadStatus.FEATURE_SET_VERSION_MISMATCH
        assert selection.artifact_ready is False
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_path.parent, ignore_errors=True)


def test_regime_detector_runtime_loader_rejects_feature_hash_mismatch() -> None:
    source_path = _artifact_path(
        label="feature_hash_mismatch_source",
        prediction=[0.8, 0.2, 0.7, 0.0],
    )
    export_dir = _scratch_dir("feature_hash_mismatch_export")

    try:
        package = package_regime_detector_artifact_for_transport(
            export_dir,
            source_artifact_ref=str(source_path),
        )
        summary_path = Path(package.summary_ref)
        summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
        summary_payload["feature_hash"] = "f" * 64
        summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

        selection = load_regime_detector_runtime_artifact(
            (package.transport_artifact_ref, package.summary_ref),
        )

        assert selection.status == RegimeDetectorArtifactLoadStatus.FEATURE_HASH_MISMATCH
        assert selection.artifact_ready is False
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_path.parent, ignore_errors=True)
