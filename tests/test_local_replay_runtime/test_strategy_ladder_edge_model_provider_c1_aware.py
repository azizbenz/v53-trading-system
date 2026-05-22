"""Tests Patch P1 (2026-05-22) — edge model provider C1-aware (mode mono|multi explicite)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from local_replay_runtime.strategy_ladder_edge_model_provider import (
    EXPECTED_EDGE_ARTIFACT_MODE_MONO_PAIR_LEGACY,
    EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1,
    EdgeEstimate,
    GovernedExpectedEdgeModel,
    GovernedMultiPairExpectedEdgeModel,
    load_governed_expected_edge_model_artifact,
)
from local_replay_runtime.strategy_ladder_edge_model_provider_multi_pair import (
    MULTI_PAIR_C1_ARTIFACT_KIND,
)

lgb = pytest.importorskip("lightgbm")


_VALID_SHA256_A = "a" * 64
_VALID_SHA256_B = "b" * 64
_VALID_SHA256_C = "c" * 64


def _build_minimal_multipair_booster(tmp_path: Path) -> Path:
    """Train a 10-round LightGBM booster on synthetic (close_return, range, pair_id)."""
    rng = np.random.default_rng(seed=42)
    n = 256
    X = rng.standard_normal((n, 3))
    y = X[:, 0] * 0.001 + 0.0005
    train_set = lgb.Dataset(
        X,
        label=y,
        feature_name=["close_return", "high_low_range", "pair_id"],
    )
    params = {"objective": "regression", "verbosity": -1, "num_leaves": 7, "seed": 5307}
    booster = lgb.train(params, train_set, num_boost_round=10)
    booster_path = tmp_path / "multipair_minimal.lgb"
    booster.save_model(str(booster_path))
    return booster_path


def _build_multipair_c1_manifest_payload(*, booster_filename: str) -> dict:
    return {
        "artifact_kind": MULTI_PAIR_C1_ARTIFACT_KIND,
        "artifact_id": "multipair_v1_15m",
        "artifact_hash": _VALID_SHA256_A,
        "feature_hash": _VALID_SHA256_B,
        "feature_names": ["close_return", "high_low_range", "pair_id"],
        "pair_id_encoding": {"BTCUSDT": 0, "ETHUSDT": 1},
        "calibration_version": "v1",
        "timeframe": "15m",
        "model_path_ref": booster_filename,
        "label_source": "MULTI_PAIR_C1_LABEL_STORE_DATASET",
        "label_fidelity": "EXPECTED_EDGE_GOVERNANCE_CANDIDATE",
        "anti_leakage_status": "EXPECTED_EDGE_ANTI_LEAKAGE_PROVEN",
        "walkforward_status": "EXPECTED_EDGE_WALKFORWARD_DECLARED",
        "horizon_minutes": 1,
        "purge_window_minutes": 0,
        "embargo_window_minutes": 0,
    }


def _write_multipair_c1_manifest(tmp_path: Path) -> tuple[Path, dict]:
    booster_path = _build_minimal_multipair_booster(tmp_path)
    payload = _build_multipair_c1_manifest_payload(booster_filename=booster_path.name)
    manifest_path = tmp_path / "expected_edge_multipair_15m.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    return manifest_path, payload


def _write_legacy_mlmodelartifact_manifest(tmp_path: Path) -> Path:
    """Build a payload that looks like a legacy MlModelArtifact (no C1 kind)."""
    payload = {
        "artifact_id": "legacy_v1",
        "feature_names": ["edge_score"],
        "feature_hash": _VALID_SHA256_C,
        "pair_universe": ["BTCUSDT"],
        "artifact_hash": _VALID_SHA256_A,
    }
    manifest_path = tmp_path / "legacy_artifact.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    return manifest_path


def test_mono_pair_legacy_mode_default_preserves_existing_path(tmp_path: Path) -> None:
    """Mode default (MONO_PAIR_LEGACY) ne casse pas le code-path existant.

    Le JSON legacy n'est pas un MlModelArtifact valide complet, donc on attend
    un blocker GOVERNED_EDGE_MODEL_INVALID_ARTIFACT (pas un mode_mismatch).
    """
    manifest_path = _write_legacy_mlmodelartifact_manifest(tmp_path)

    result = load_governed_expected_edge_model_artifact(
        manifest_path,
        expected_artifact_hash=None,
    )
    assert result.model is None
    assert "MODE_MISMATCH" not in result.status, (
        f"default mode must not trigger mode_mismatch, got status={result.status}"
    )
    assert result.status.startswith("GOVERNED_EDGE_MODEL_INVALID_ARTIFACT"), (
        f"expected INVALID_ARTIFACT for incomplete legacy json, got {result.status}"
    )


def test_multi_pair_c1_mode_loads_and_predicts(tmp_path: Path) -> None:
    """Mode MULTI_PAIR_C1 charge le manifest C1 et prédit pour une paire connue."""
    manifest_path, payload = _write_multipair_c1_manifest(tmp_path)

    result = load_governed_expected_edge_model_artifact(
        manifest_path,
        expected_artifact_hash=payload["artifact_hash"],
        expected_edge_artifact_mode=EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1,
    )

    assert result.status == "EXPECTED_EDGE_GOVERNED_BACKTEST_LABELS_READY", (
        f"expected ready, got {result.status}, blockers={result.blocker_codes}"
    )
    assert isinstance(result.model, GovernedMultiPairExpectedEdgeModel)
    assert "BTCUSDT" in result.model.pair_universe
    assert "ETHUSDT" in result.model.pair_universe
    assert "pair_id" not in result.model.feature_names

    estimate = result.model.estimate_expected_edge_bps(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_700_000_000_000,
        feature_values={"close_return": 0.001, "high_low_range": 0.002},
        route_features=None,
    )
    assert isinstance(estimate, EdgeEstimate)
    assert estimate.detector_status == "GOVERNED_EDGE_MODEL_READY"
    assert estimate.provenance == "GOVERNED_ML_ARTIFACT_MULTI_PAIR_C1_BACKTEST_TRUTH"
    assert estimate.edge_bps >= 0.0  # clipped at 0 if negative


def test_multi_pair_c1_mode_unknown_pair_fails_close(tmp_path: Path) -> None:
    """Pair pas dans pair_id_encoding → EdgeEstimate blocked (pas d'exception)."""
    manifest_path, payload = _write_multipair_c1_manifest(tmp_path)
    result = load_governed_expected_edge_model_artifact(
        manifest_path,
        expected_artifact_hash=payload["artifact_hash"],
        expected_edge_artifact_mode=EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1,
    )
    assert result.model is not None

    estimate = result.model.estimate_expected_edge_bps(
        pair="SOLUSDT",  # not in {BTCUSDT, ETHUSDT}
        timeframe="15m",
        timestamp_ms=1_700_000_000_000,
        feature_values={"close_return": 0.001, "high_low_range": 0.002},
        route_features=None,
    )
    assert estimate.edge_bps == 0.0
    assert estimate.provenance == "EDGE_MODEL_BLOCKED:PAIR_NOT_IN_C1_ENCODING"
    assert estimate.detector_status == "PAIR_NOT_IN_C1_ENCODING"
    assert estimate.model_status == "GOVERNED_EDGE_MODEL_BLOCKED"
    assert any("SOLUSDT" in w for w in estimate.warnings)


def test_multi_pair_c1_mode_missing_features_fails_close(tmp_path: Path) -> None:
    """Features required absentes → EdgeEstimate blocked avec liste explicite."""
    manifest_path, payload = _write_multipair_c1_manifest(tmp_path)
    result = load_governed_expected_edge_model_artifact(
        manifest_path,
        expected_artifact_hash=payload["artifact_hash"],
        expected_edge_artifact_mode=EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1,
    )
    assert result.model is not None

    estimate = result.model.estimate_expected_edge_bps(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_700_000_000_000,
        feature_values={"close_return": 0.001},  # high_low_range missing
        route_features=None,
    )
    assert estimate.edge_bps == 0.0
    assert estimate.provenance == "EDGE_MODEL_BLOCKED:MISSING_FEATURES"
    assert estimate.detector_status == "MISSING_FEATURES"
    assert any("high_low_range" in w for w in estimate.warnings)


def test_mode_mismatch_multi_expected_received_legacy(tmp_path: Path) -> None:
    """Mode MULTI mais JSON n'a pas l'artifact_kind C1 → mode_mismatch explicite."""
    manifest_path = _write_legacy_mlmodelartifact_manifest(tmp_path)

    result = load_governed_expected_edge_model_artifact(
        manifest_path,
        expected_artifact_hash=None,
        expected_edge_artifact_mode=EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1,
    )
    assert result.model is None
    assert result.status == "GOVERNED_EDGE_MODEL_MODE_MISMATCH:EXPECTED_MULTI_PAIR_C1"
    assert "GOVERNED_EDGE_MODEL_MODE_MISMATCH:EXPECTED_MULTI_PAIR_C1" in result.blocker_codes


def test_mode_mismatch_legacy_expected_received_multi(tmp_path: Path) -> None:
    """Mode LEGACY mais JSON est un manifest C1 → mode_mismatch explicite."""
    manifest_path, _payload = _write_multipair_c1_manifest(tmp_path)

    result = load_governed_expected_edge_model_artifact(
        manifest_path,
        expected_artifact_hash=None,
        expected_edge_artifact_mode=EXPECTED_EDGE_ARTIFACT_MODE_MONO_PAIR_LEGACY,
    )
    assert result.model is None
    assert (
        result.status
        == "GOVERNED_EDGE_MODEL_MODE_MISMATCH:RECEIVED_MULTI_PAIR_C1_EXPECTED_LEGACY"
    )
    assert (
        "GOVERNED_EDGE_MODEL_MODE_MISMATCH:RECEIVED_MULTI_PAIR_C1_EXPECTED_LEGACY"
        in result.blocker_codes
    )


def test_unknown_mode_fails_close() -> None:
    """Mode inconnu (typo) → fail-close avant tout disk access."""
    result = load_governed_expected_edge_model_artifact(
        Path("/does/not/matter.json"),
        expected_artifact_hash=None,
        expected_edge_artifact_mode="MONO_PAIR_LEGACEY",  # typo
    )
    assert result.model is None
    assert result.status == "GOVERNED_EDGE_MODEL_MODE_UNKNOWN"
    assert any("MODE_UNKNOWN" in code for code in result.blocker_codes)
