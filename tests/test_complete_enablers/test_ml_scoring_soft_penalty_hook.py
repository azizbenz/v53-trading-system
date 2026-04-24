from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from backtest_artifact_import import package_ml_model_artifact_for_transport
from complete_enablers import MlScoringSoftPenaltyHook, MlScoringSoftPenaltyHookConfig
from interface_contracts import MlModelArtifact, MlModelWindow, PromotionState
from scoring_backbone import ScoringSoftPenaltyLayerInput
from tests.support_paths import make_repo_scratch_dir


def _artifact(
    *,
    prediction: float,
    feature_names: tuple[str, ...] = ("momentum", "flow"),
    stale_after: datetime | None = None,
) -> MlModelArtifact:
    created_at = datetime(2026, 4, 22, 12, 0, tzinfo=UTC)
    return MlModelArtifact.create(
        feature_names=feature_names,
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
        "complete_enablers_ml_scoring_soft_penalty_hook_tests",
        label,
    )


def _packaged_artifact_refs(
    *,
    label: str,
    prediction: float,
    feature_names: tuple[str, ...] = ("momentum", "flow"),
    stale_after: datetime | None = None,
) -> tuple[Path, Path, tuple[str, str]]:
    export_dir = _scratch_dir(f"{label}_export")
    source_dir = _scratch_dir(f"{label}_source")
    source_path = source_dir / "ml_model_artifact.json"
    artifact = _artifact(
        prediction=prediction,
        feature_names=feature_names,
        stale_after=stale_after,
    )
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


def _hook_input(*, supplementary_refs: tuple[str, ...], feature_values: dict[str, float]) -> ScoringSoftPenaltyLayerInput:
    return ScoringSoftPenaltyLayerInput(
        context_id="engine_a:BTCUSDT:5.0",
        pair="BTCUSDT",
        engine_id="engine_a",
        scoring_version="5.0",
        feature_values=feature_values,
        supplementary_refs=supplementary_refs,
        expected_cost=0.2,
        expected_ce=0.1,
        corr_penalty=0.05,
        risk_penalty=0.03,
        fragility_score=0.2,
        toxicity_score=0.1,
        execution_survivability_score=0.9,
        micro_friction_score=0.1,
        pressure_state="nominal",
    )


def test_ml_scoring_soft_penalty_hook_applies_exact_multiplier_delta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "complete_enablers.ml_confidence_enabler._load_lightgbm_module",
        lambda: _fake_lightgbm_module(),
    )
    export_dir, source_dir, supplementary_refs = _packaged_artifact_refs(
        label="active",
        prediction=0.9,
    )
    hook = MlScoringSoftPenaltyHook(
        config=MlScoringSoftPenaltyHookConfig(alpha=0.3),
    )

    try:
        outcome = hook(
            _hook_input(
                supplementary_refs=supplementary_refs,
                feature_values={"momentum": 1.0, "flow": 0.5},
            )
        )

        assert outcome.raw_score_multiplier_delta == pytest.approx(0.12)
        assert outcome.raw_score_add == pytest.approx(0.0)
        assert outcome.raw_score_cap is None
        assert outcome.reason_codes[-1] == "ML_SCORE_MODULATION_ACTIVE"
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_dir, ignore_errors=True)


def test_ml_scoring_soft_penalty_hook_degrades_to_neutral_without_artifact() -> None:
    hook = MlScoringSoftPenaltyHook()

    outcome = hook(
        _hook_input(
            supplementary_refs=(),
            feature_values={"momentum": 1.0, "flow": 0.5},
        )
    )

    assert outcome.raw_score_multiplier_delta == pytest.approx(0.0)
    assert outcome.raw_score_add == pytest.approx(0.0)
    assert outcome.raw_score_cap is None
    assert outcome.reason_codes[0] == "ML_RUNTIME_ARTIFACT_MISSING_SUPPLEMENTARY_REFS"


def test_ml_scoring_soft_penalty_hook_degrades_to_neutral_on_feature_schema_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "complete_enablers.ml_confidence_enabler._load_lightgbm_module",
        lambda: _fake_lightgbm_module(),
    )
    export_dir, source_dir, supplementary_refs = _packaged_artifact_refs(
        label="schema_mismatch",
        prediction=0.8,
        feature_names=("route_raw_score", "momentum"),
    )
    hook = MlScoringSoftPenaltyHook()

    try:
        outcome = hook(
            _hook_input(
                supplementary_refs=supplementary_refs,
                feature_values={"momentum": 1.0, "flow": 0.5},
            )
        )

        assert outcome.raw_score_multiplier_delta == pytest.approx(0.0)
        assert outcome.raw_score_add == pytest.approx(0.0)
        assert outcome.raw_score_cap is None
        assert outcome.reason_codes[0].startswith("ML_ARTIFACT_INVALID:")
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)
        shutil.rmtree(source_dir, ignore_errors=True)
