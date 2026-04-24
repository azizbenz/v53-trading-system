from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from backtest_artifact_import import package_ml_model_artifact_for_transport
from complete_enablers import MlArtifactStatus, MlConfidenceEnabler
from interface_contracts import MlModelArtifact, MlModelWindow, PromotionState, Side
from tests.support_paths import make_repo_scratch_dir


def _artifact(*, prediction: float, stale_after: datetime | None = None) -> MlModelArtifact:
    created_at = datetime(2026, 4, 22, 12, 0, tzinfo=UTC)
    return MlModelArtifact.create(
        feature_names=("feature_a", "feature_b"),
        feature_hash="3" * 64,
        pair_universe=("BTCUSDT",),
        train_window=MlModelWindow(
            start_at=datetime(2025, 9, 24, tzinfo=UTC),
            end_at=datetime(2026, 3, 22, tzinfo=UTC),
        ),
        validation_window=MlModelWindow(
            start_at=datetime(2026, 3, 23, tzinfo=UTC),
            end_at=datetime(2026, 4, 21, tzinfo=UTC),
        ),
        oos_sharpe=1.0,
        backtest_sharpe=1.2,
        ks_test_features_pvalue=0.4,
        shadow_diff_pct=0.02,
        promotion_state=PromotionState.REPLAY_ONLY,
        training_seed=8,
        created_at=created_at,
        calibration_version="cal.v1",
        dataset_hash="4" * 64,
        model_bytes_b64=base64.b64encode(
            json.dumps({"prediction": prediction}).encode("utf-8")
        ).decode("ascii"),
        stale_after=stale_after,
    )


def _fake_lightgbm_module() -> SimpleNamespace:
    class FakeBooster:
        def __init__(self, *, model_str: str | None = None, model_file: str | None = None) -> None:
            assert model_file is None
            payload = json.loads(model_str or "{}")
            self._prediction = float(payload.get("prediction", 0.5))

        def predict(self, rows: list[list[float]]) -> list[float]:
            assert rows
            return [self._prediction]

    return SimpleNamespace(Booster=FakeBooster)


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir(
        "complete_enablers_ml_confidence_enabler_tests",
        label,
    )


def _packaged_artifact_refs(
    *,
    label: str,
    prediction: float,
    stale_after: datetime | None = None,
) -> tuple[Path, Path, tuple[str, str]]:
    export_dir = _scratch_dir(f"{label}_export")
    source_dir = _scratch_dir(f"{label}_source")
    source_path = source_dir / "ml_model_artifact.json"
    artifact = _artifact(prediction=prediction, stale_after=stale_after)
    source_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    transport_package = package_ml_model_artifact_for_transport(
        export_dir,
        source_artifact_ref=str(source_path),
    )
    return (
        export_dir,
        source_dir,
        (
            transport_package.transport_artifact_ref,
            transport_package.summary_ref,
        ),
    )


def test_ml_confidence_is_clipped_to_unit_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "complete_enablers.ml_confidence_enabler._load_lightgbm_module",
        lambda: _fake_lightgbm_module(),
    )
    enabler = MlConfidenceEnabler()
    artifact = _artifact(prediction=1.7)

    signal = enabler.score_candidate(
        feature_values={"feature_a": 0.1, "feature_b": 0.2},
        artifact=artifact,
    )

    assert signal.ml_confidence == pytest.approx(1.0)
    assert signal.artifact_status == MlArtifactStatus.ACTIVE


def test_ml_confidence_missing_artifact_degrades_gracefully() -> None:
    enabler = MlConfidenceEnabler()

    result = enabler.apply_to_engine_score(
        base_score=11.0,
        engine_side=Side.BUY,
        artifact=None,
        feature_values={"feature_a": 0.1, "feature_b": 0.2},
    )

    assert result.signal.artifact_status == MlArtifactStatus.MISSING
    assert result.signal.ml_confidence == pytest.approx(0.5)
    assert result.fusion.fused_score == pytest.approx(11.0)
    assert result.fusion.applied is False


def test_ml_confidence_stale_artifact_degrades_gracefully() -> None:
    artifact = _artifact(
        prediction=0.8,
        stale_after=datetime(2026, 4, 22, 12, 0, tzinfo=UTC),
    )
    enabler = MlConfidenceEnabler()

    result = enabler.apply_to_engine_score(
        base_score=8.0,
        engine_side=Side.BUY,
        artifact=artifact,
        feature_values={"feature_a": 0.1, "feature_b": 0.2},
        as_of=datetime(2026, 4, 22, 12, 1, tzinfo=UTC),
    )

    assert result.signal.artifact_status == MlArtifactStatus.STALE
    assert result.fusion.fused_score == pytest.approx(8.0)
    assert result.fusion.applied is False


def test_ml_direction_never_overrides_engine_side(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "complete_enablers.ml_confidence_enabler._load_lightgbm_module",
        lambda: _fake_lightgbm_module(),
    )
    enabler = MlConfidenceEnabler(default_alpha=0.3)
    artifact = _artifact(prediction=0.95)

    result = enabler.apply_to_engine_score(
        base_score=6.0,
        engine_side=Side.SELL,
        artifact=artifact,
        feature_values={"feature_a": 0.1, "feature_b": 0.2},
    )

    assert result.signal.ml_direction.value == "long"
    assert result.engine_side == Side.SELL


def test_ml_confidence_loads_from_supplementary_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "complete_enablers.ml_confidence_enabler._load_lightgbm_module",
        lambda: _fake_lightgbm_module(),
    )
    export_dir, source_dir, supplementary_refs = _packaged_artifact_refs(
        label="supplementary_active",
        prediction=0.8,
    )
    enabler = MlConfidenceEnabler()

    try:
        signal = enabler.score_candidate_from_supplementary_refs(
            feature_values={"feature_a": 0.1, "feature_b": 0.2},
            supplementary_refs=supplementary_refs,
        )

        assert signal.artifact_status == MlArtifactStatus.ACTIVE
        assert signal.ml_confidence == pytest.approx(0.8)
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_dir, ignore_errors=True)


def test_ml_confidence_stale_supplementary_artifact_degrades_gracefully() -> None:
    export_dir, source_dir, supplementary_refs = _packaged_artifact_refs(
        label="supplementary_stale",
        prediction=0.8,
        stale_after=datetime(2026, 4, 22, 12, 0, tzinfo=UTC),
    )
    enabler = MlConfidenceEnabler()

    try:
        signal = enabler.score_candidate_from_supplementary_refs(
            feature_values={"feature_a": 0.1, "feature_b": 0.2},
            supplementary_refs=supplementary_refs,
            as_of=datetime(2026, 4, 22, 12, 1, tzinfo=UTC),
        )

        assert signal.artifact_status == MlArtifactStatus.STALE
        assert signal.ml_confidence == pytest.approx(0.5)
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_dir, ignore_errors=True)
