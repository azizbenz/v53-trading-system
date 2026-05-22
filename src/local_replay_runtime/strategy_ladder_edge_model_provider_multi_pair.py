"""Multi-pair C1 expected-edge provider — C1-aware adapter wired on top of C1.3.D.

Patch P1 (2026-05-22) — wires the multi-pair LightGBM artifact produced by
C1.3.C orchestrator into the strategy-ladder runner's `expected_edge` rail.

Doctrine V5.3 :
- Coexists with the mono-pair provider (`strategy_ladder_edge_model_provider`).
- Mode is selected explicitly by the admin via a request field
  (`expected_edge_artifact_mode = MONO_PAIR_LEGACY | MULTI_PAIR_C1`). No
  auto-detection — the admin owns the decision.
- The wrapper `GovernedMultiPairExpectedEdgeModel` exposes the same
  `estimate_expected_edge_bps` signature as `GovernedExpectedEdgeModel` so the
  downstream runner consumes either via duck typing.
- Fail-closed semantics aligned with the mono-pair provider :
  pair unknown / features incomplete / non-finite prediction → `EdgeEstimate`
  with `edge_bps=0` and a `EDGE_MODEL_BLOCKED:<reason>` provenance.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from pydantic import BaseModel, Field, field_validator

from local_replay_runtime.strategy_ladder_multi_pair_expected_edge_training import (
    PAIR_ID_FEATURE_KEY,
    MultiPairExpectedEdgeInferenceArtifact,
    load_multi_pair_inference_artifact,
    predict_expected_edge_for_pair,
)


EXPECTED_EDGE_ARTIFACT_MODE_MONO_PAIR_LEGACY = "MONO_PAIR_LEGACY"
EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1 = "MULTI_PAIR_C1"
EXPECTED_EDGE_ARTIFACT_MODES = (
    EXPECTED_EDGE_ARTIFACT_MODE_MONO_PAIR_LEGACY,
    EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1,
)

MULTI_PAIR_C1_ARTIFACT_KIND = "MULTI_PAIR_C1_EXPECTED_EDGE"

_SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class StrategyLadderMultiPairC1Manifest(BaseModel, frozen=True):
    """Frozen JSON manifest describing a C1 multi-pair expected-edge artifact.

    The JSON shape is produced by the C1.3.C training orchestrator (or by an
    operator running the training script). Fields are validated to fail-close
    on malformed input before any LightGBM Booster load is attempted.
    """

    artifact_kind: str = Field(..., min_length=1)
    artifact_id: str = Field(..., min_length=1)
    artifact_hash: str = Field(..., min_length=64, max_length=64)
    feature_hash: str = Field(..., min_length=64, max_length=64)
    feature_names: tuple[str, ...] = Field(..., min_length=1)
    pair_id_encoding: dict[str, int] = Field(..., min_length=1)
    calibration_version: str = Field(..., min_length=1)
    timeframe: str = Field(..., min_length=1)
    model_path_ref: str = Field(..., min_length=1)
    label_source: str = Field(default="MULTI_PAIR_C1_LABEL_STORE_DATASET", min_length=1)
    label_fidelity: str = Field(default="EXPECTED_EDGE_GOVERNANCE_CANDIDATE", min_length=1)
    anti_leakage_status: str = Field(
        default="EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN", min_length=1
    )
    walkforward_status: str = Field(
        default="EXPECTED_EDGE_WALKFORWARD_NOT_DECLARED", min_length=1
    )
    horizon_minutes: int | None = Field(default=None, ge=1)
    purge_window_minutes: int | None = Field(default=None, ge=0)
    embargo_window_minutes: int | None = Field(default=None, ge=0)

    @field_validator("artifact_kind")
    @classmethod
    def _validate_artifact_kind(cls, value: str) -> str:
        if value != MULTI_PAIR_C1_ARTIFACT_KIND:
            raise ValueError(
                f"DOCTRINE_MULTI_PAIR_C1_MANIFEST_INVALID_KIND — expected "
                f"{MULTI_PAIR_C1_ARTIFACT_KIND!r}, got {value!r}"
            )
        return value

    @field_validator("artifact_hash", "feature_hash")
    @classmethod
    def _validate_sha256_hex(cls, value: str) -> str:
        if not _SHA256_HEX_PATTERN.match(value):
            raise ValueError(
                "DOCTRINE_MULTI_PAIR_C1_MANIFEST_HASH_FORMAT — must be 64 hex chars"
            )
        return value

    @field_validator("feature_names")
    @classmethod
    def _validate_feature_names_include_pair_id(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        if PAIR_ID_FEATURE_KEY not in value:
            raise ValueError(
                f"DOCTRINE_MULTI_PAIR_C1_MANIFEST_MISSING_PAIR_ID — feature_names "
                f"must include {PAIR_ID_FEATURE_KEY!r} (got {value})"
            )
        return value


@dataclass(frozen=True)
class GovernedMultiPairExpectedEdgeModel:
    """Frozen multi-pair ML artifact adapter for expected_edge_bps.

    Wraps a `MultiPairExpectedEdgeInferenceArtifact` (loaded via C1.3.D
    `load_multi_pair_inference_artifact`) and exposes the same scoring
    surface as `GovernedExpectedEdgeModel`. Auto-injects `pair_id` via
    `predict_expected_edge_for_pair` (C1.3.D).
    """

    artifact_path: Path
    artifact_hash: str
    feature_hash: str
    calibration_version: str
    timeframe: str
    inference_artifact: MultiPairExpectedEdgeInferenceArtifact

    @property
    def pair_universe(self) -> tuple[str, ...]:
        return tuple(sorted(self.inference_artifact.pair_id_encoding.keys()))

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(
            name
            for name in self.inference_artifact.feature_names
            if name != PAIR_ID_FEATURE_KEY
        )

    def estimate_expected_edge_bps(
        self,
        *,
        pair: str,
        timeframe: str | None = None,
        timestamp_ms: int,
        feature_values: Mapping[str, object] | None = None,
        route_features: Mapping[str, object] | None = None,
    ):
        from local_replay_runtime.strategy_ladder_edge_model_provider import (
            EdgeEstimate,
            _merge_numeric_features,
        )

        del timeframe
        del timestamp_ms

        if not pair or pair not in self.inference_artifact.pair_id_encoding:
            return EdgeEstimate(
                edge_bps=0.0,
                provenance="EDGE_MODEL_BLOCKED:PAIR_NOT_IN_C1_ENCODING",
                n_lookback_bars_used=0,
                median_abs_forward_return=0.0,
                detector_status="PAIR_NOT_IN_C1_ENCODING",
                warnings=(f"PAIR_NOT_IN_C1_ENCODING:{pair}",),
                artifact_hash=self.artifact_hash,
                feature_hash=self.feature_hash,
                model_status="GOVERNED_EDGE_MODEL_BLOCKED",
            )

        numeric_features = _merge_numeric_features(feature_values, route_features)
        required_features = tuple(
            name
            for name in self.inference_artifact.feature_names
            if name != PAIR_ID_FEATURE_KEY
        )
        missing = tuple(name for name in required_features if name not in numeric_features)
        if missing:
            return EdgeEstimate(
                edge_bps=0.0,
                provenance="EDGE_MODEL_BLOCKED:MISSING_FEATURES",
                n_lookback_bars_used=0,
                median_abs_forward_return=0.0,
                detector_status="MISSING_FEATURES",
                warnings=(f"MISSING_EDGE_MODEL_FEATURES:{','.join(missing)}",),
                artifact_hash=self.artifact_hash,
                feature_hash=self.feature_hash,
                model_status="GOVERNED_EDGE_MODEL_BLOCKED",
            )

        feature_dict = {name: float(numeric_features[name]) for name in required_features}
        try:
            prediction = predict_expected_edge_for_pair(
                artifact=self.inference_artifact,
                pair=pair,
                features=feature_dict,
            )
        except Exception as exc:  # noqa: BLE001 — fail closed on model runtime errors.
            return EdgeEstimate(
                edge_bps=0.0,
                provenance=f"EDGE_MODEL_BLOCKED:PREDICTION_FAILED_{type(exc).__name__}",
                n_lookback_bars_used=0,
                median_abs_forward_return=0.0,
                detector_status=f"PREDICTION_FAILED:{type(exc).__name__}",
                warnings=(f"EDGE_MODEL_PREDICTION_FAILED:{type(exc).__name__}",),
                artifact_hash=self.artifact_hash,
                feature_hash=self.feature_hash,
                model_status="GOVERNED_EDGE_MODEL_BLOCKED",
            )

        if not math.isfinite(prediction):
            return EdgeEstimate(
                edge_bps=0.0,
                provenance="EDGE_MODEL_BLOCKED:NON_FINITE_PREDICTION",
                n_lookback_bars_used=0,
                median_abs_forward_return=0.0,
                detector_status="NON_FINITE_PREDICTION",
                warnings=("EDGE_MODEL_NON_FINITE_PREDICTION",),
                artifact_hash=self.artifact_hash,
                feature_hash=self.feature_hash,
                model_status="GOVERNED_EDGE_MODEL_BLOCKED",
            )

        edge_bps = prediction * 10_000.0
        warnings: tuple[str, ...] = ()
        if edge_bps < 0.0:
            edge_bps = 0.0
            warnings = ("GOVERNED_EDGE_MODEL_NEGATIVE_PREDICTION_CLIPPED",)

        return EdgeEstimate(
            edge_bps=edge_bps,
            provenance="GOVERNED_ML_ARTIFACT_MULTI_PAIR_C1_BACKTEST_TRUTH",
            n_lookback_bars_used=0,
            median_abs_forward_return=0.0,
            detector_status="GOVERNED_EDGE_MODEL_READY",
            warnings=warnings,
            artifact_hash=self.artifact_hash,
            feature_hash=self.feature_hash,
            model_status="GOVERNED_EDGE_MODEL_READY",
        )


def load_multi_pair_c1_expected_edge_model(
    *,
    manifest_path: Path,
    raw_payload: str,
    expected_artifact_hash: str | None,
):
    """Parse a multi-pair C1 manifest JSON and load the LightGBM booster.

    Returns a `GovernedExpectedEdgeModelLoadResult` (imported lazily to avoid a
    circular import with the mono-pair provider). Fail-closed on : malformed
    manifest, hash mismatch, missing model file, lightgbm runtime missing.
    """
    from local_replay_runtime.strategy_ladder_edge_model_provider import (
        GovernedExpectedEdgeModelLoadResult,
    )

    training_artifact_ref = str(manifest_path.resolve())

    if MULTI_PAIR_C1_ARTIFACT_KIND not in raw_payload:
        return GovernedExpectedEdgeModelLoadResult(
            model=None,
            status="GOVERNED_EDGE_MODEL_MODE_MISMATCH:EXPECTED_MULTI_PAIR_C1",
            training_artifact_ref=training_artifact_ref,
            blocker_codes=("GOVERNED_EDGE_MODEL_MODE_MISMATCH:EXPECTED_MULTI_PAIR_C1",),
            warnings=("GOVERNED_EDGE_MODEL_MODE_MISMATCH:EXPECTED_MULTI_PAIR_C1",),
        )

    try:
        manifest = StrategyLadderMultiPairC1Manifest.model_validate_json(raw_payload)
    except Exception as exc:  # noqa: BLE001 — malformed manifest must fail closed.
        return GovernedExpectedEdgeModelLoadResult(
            model=None,
            status=f"GOVERNED_EDGE_MODEL_INVALID_ARTIFACT:{type(exc).__name__}",
            training_artifact_ref=training_artifact_ref,
            blocker_codes=("GOVERNED_EDGE_MODEL_INVALID_ARTIFACT",),
            warnings=(f"GOVERNED_EDGE_MODEL_INVALID_ARTIFACT:{type(exc).__name__}",),
        )

    if expected_artifact_hash and manifest.artifact_hash != expected_artifact_hash:
        return GovernedExpectedEdgeModelLoadResult(
            model=None,
            status="GOVERNED_EDGE_MODEL_HASH_MISMATCH",
            training_artifact_ref=training_artifact_ref,
            artifact_hash=manifest.artifact_hash,
            feature_hash=manifest.feature_hash,
            blocker_codes=("GOVERNED_EDGE_MODEL_HASH_MISMATCH",),
            warnings=("GOVERNED_EDGE_MODEL_HASH_MISMATCH",),
        )

    booster_path = Path(manifest.model_path_ref)
    if not booster_path.is_absolute():
        booster_path = manifest_path.parent / booster_path
    if not booster_path.is_file():
        return GovernedExpectedEdgeModelLoadResult(
            model=None,
            status="GOVERNED_EDGE_MODEL_BOOSTER_PATH_NOT_FOUND",
            training_artifact_ref=training_artifact_ref,
            artifact_hash=manifest.artifact_hash,
            feature_hash=manifest.feature_hash,
            blocker_codes=("GOVERNED_EDGE_MODEL_BOOSTER_PATH_NOT_FOUND",),
            warnings=(f"GOVERNED_EDGE_MODEL_BOOSTER_PATH_NOT_FOUND:{booster_path}",),
        )

    try:
        inference_artifact = load_multi_pair_inference_artifact(
            booster_path=booster_path,
            pair_id_encoding=dict(manifest.pair_id_encoding),
            feature_names=tuple(manifest.feature_names),
            feature_hash=manifest.feature_hash,
            manifest_path=manifest_path,
        )
    except Exception as exc:  # noqa: BLE001 — fail closed if runtime cannot score.
        return GovernedExpectedEdgeModelLoadResult(
            model=None,
            status=f"GOVERNED_EDGE_MODEL_LOAD_FAILED:{type(exc).__name__}",
            training_artifact_ref=training_artifact_ref,
            artifact_hash=manifest.artifact_hash,
            feature_hash=manifest.feature_hash,
            blocker_codes=("GOVERNED_EDGE_MODEL_LOAD_FAILED",),
            warnings=(f"GOVERNED_EDGE_MODEL_LOAD_FAILED:{type(exc).__name__}",),
        )

    model = GovernedMultiPairExpectedEdgeModel(
        artifact_path=manifest_path,
        artifact_hash=manifest.artifact_hash,
        feature_hash=manifest.feature_hash,
        calibration_version=manifest.calibration_version,
        timeframe=manifest.timeframe,
        inference_artifact=inference_artifact,
    )

    return GovernedExpectedEdgeModelLoadResult(
        model=model,
        status="EXPECTED_EDGE_GOVERNED_BACKTEST_LABELS_READY",
        training_artifact_ref=training_artifact_ref,
        artifact_hash=manifest.artifact_hash,
        feature_hash=manifest.feature_hash,
        label_source=manifest.label_source,
        label_fidelity=manifest.label_fidelity,
        anti_leakage_status=manifest.anti_leakage_status,
        walkforward_status=manifest.walkforward_status,
        horizon_minutes=manifest.horizon_minutes,
        purge_window_minutes=manifest.purge_window_minutes,
        embargo_window_minutes=manifest.embargo_window_minutes,
        blocker_codes=(
            "EXPECTED_EDGE_GOVERNED_SHADOW_REQUIRED",
            "EXPECTED_EDGE_NOT_PROMOTION_GRADE",
        ),
    )


__all__ = [
    "EXPECTED_EDGE_ARTIFACT_MODE_MONO_PAIR_LEGACY",
    "EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1",
    "EXPECTED_EDGE_ARTIFACT_MODES",
    "MULTI_PAIR_C1_ARTIFACT_KIND",
    "GovernedMultiPairExpectedEdgeModel",
    "StrategyLadderMultiPairC1Manifest",
    "load_multi_pair_c1_expected_edge_model",
]
