"""Multi-pair expected-edge training orchestrator.

Patch C1.3.C (2026-05-21) — coexiste avec la doctrine MP3 mono-pair atomic.
Cette API permet à un admin de choisir N pairs à entraîner ensemble dans un
SEUL artifact LightGBM par timeframe, avec :
- `pair_id` comme feature categorical native LightGBM
- Sample weights inverse-frequency par pair pour balance imbalance
- Discovery filesystem-driven via `pair_capability_discovery`
- ZERO hardcoded pair name dans la logique

Doctrine V5.3 :
- MP3 mono-pair atomic reste intact (`StrategyLadderExpectedEdgeTrainingRequest`)
- C1 multi-pair coexiste comme nouvelle API (`StrategyLadderMultiPairExpectedEdgeTrainingRequest`)
- Admin choisit runtime quelle subset de pairs entraîner (1 à N)
- Capability check : microstructure features exigent orderbook (rejet LEGACY-only pairs)

Example d'usage admin :
    >>> request = StrategyLadderMultiPairExpectedEdgeTrainingRequest(
    ...     artifact_id="multipair_v1",
    ...     calibration_version="v1",
    ...     pairs=("PAIR_A", "PAIR_B", "PAIR_C"),  # admin choice runtime
    ...     timeframe="15m",
    ...     label_store_dataset_paths={"PAIR_A": ..., "PAIR_B": ..., "PAIR_C": ...},
    ...     output_dir=Path("/artifacts/"),
    ...     train_start="2025-01-01",
    ...     train_end="2025-06-30",
    ...     feature_names=("close_return", "high_low_range", "volume", "pair_id"),
    ... )
    >>> result = train_multi_pair_expected_edge_artifact(request)
    >>> # → artifacts/expected_edge_multipair_15m.lgb (1 artifact for all N pairs)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, Field, field_validator, model_validator

from calibration_methods import MlTrainerRequest, MlTrainingRow

# Patch C1.3.C — réutilise les helpers existants depuis MP3 module
# (load_label_store_rows, _label_store_paths_from_dataset, dataset_hash, etc.)


# Patch C1.3.C — feature key pour pair encoding categorical.
# Nom standardisé pour cohérence inter-modules (label_store, runner, inference).
PAIR_ID_FEATURE_KEY = "pair_id"


class StrategyLadderMultiPairExpectedEdgeTrainingRequest(BaseModel, frozen=True):
    """Multi-pair expected-edge training request.

    Patch C1.3.C (2026-05-21) — coexiste avec MP3 mono-pair atomic.
    Admin fournit runtime un tuple `pairs` (1 à N), discovery filesystem
    confirme capabilities, training produit 1 artifact par timeframe.

    Pair name format : ZERO hardcode dans le validator. Admin peut fournir
    n'importe quel nom (MMXX, BTCUSDT, FUTURE_PAIR_42). Le validator vérifie :
    - Non-empty, déduplication
    - Caractères raisonnables (str non-blank)
    - Cohérence avec label_store_dataset_paths keys
    """

    artifact_id: str = Field(..., min_length=1)
    calibration_version: str = Field(..., min_length=1)
    # Patch C1.3.C — pairs runtime, ZERO hardcode (admin choisit à l'instance)
    pairs: tuple[str, ...] = Field(..., min_length=1)
    timeframe: str = Field(default="15m", min_length=1)
    # Map pair → label_store_dataset_path (un par pair, build via N B2 runs ou shared run)
    label_store_dataset_paths: dict[str, Path] = Field(default_factory=dict)
    output_dir: Path
    train_start: str = Field(..., min_length=1)
    train_end: str = Field(..., min_length=1)
    sample_stride_minutes: int = Field(default=60, ge=1)
    target_horizon_minutes: int = Field(default=1, ge=1)
    training_seed: int = 5307
    max_optuna_trials: int = Field(default=0, ge=0)
    min_training_rows: int = Field(default=210, ge=10)
    feature_names: tuple[str, ...] = ("close_return", "high_low_range", "volume", PAIR_ID_FEATURE_KEY)
    # Patch C1.3.C — balance imbalance par pair via inverse-frequency weighting.
    # Default True : applique sample_weights = 1/n_pair_samples (normalisé).
    apply_inverse_frequency_pair_weighting: bool = True
    # Patch C1.3.C — pair_id encoding (par défaut categorical native LightGBM).
    # Si False : pair_id encodé comme float ordinal sans categorical hint
    # (les arbres apprendront tout de même les splits par pair).
    use_categorical_pair_id: bool = True

    @field_validator("pairs")
    @classmethod
    def _validate_pairs_non_empty_deduplicated(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Patch C1.3.C — pairs validation runtime, ZERO whitelist."""
        normalized = tuple(dict.fromkeys(p.strip() for p in value if p.strip()))
        if not normalized:
            raise ValueError(
                "DOCTRINE_MULTI_PAIR_TRAINING_EMPTY — pairs tuple must contain "
                "at least one non-blank pair name"
            )
        return normalized

    @field_validator("feature_names")
    @classmethod
    def _validate_feature_names_include_pair_id(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        """Patch C1.3.C — pair_id MUST be in feature_names for multi-pair training.

        Si admin oublie pair_id, le modèle ne pourra pas distinguer les pairs.
        On force présence + warning explicit.
        """
        normalized = tuple(dict.fromkeys(name.strip() for name in value if name.strip()))
        if not normalized:
            raise ValueError("feature_names must not be empty")
        if PAIR_ID_FEATURE_KEY not in normalized:
            raise ValueError(
                f"DOCTRINE_MULTI_PAIR_TRAINING_MISSING_PAIR_ID — feature_names must "
                f"include {PAIR_ID_FEATURE_KEY!r} for multi-pair model to distinguish "
                f"pairs. Got: {normalized}. Add {PAIR_ID_FEATURE_KEY!r} OR use mono-pair "
                f"training (StrategyLadderExpectedEdgeTrainingRequest)."
            )
        return normalized

    @model_validator(mode="after")
    def _validate_label_store_paths_match_pairs(
        self,
    ) -> "StrategyLadderMultiPairExpectedEdgeTrainingRequest":
        """Patch C1.3.C — label_store_dataset_paths keys must include all pairs."""
        if self.label_store_dataset_paths:
            missing = tuple(p for p in self.pairs if p not in self.label_store_dataset_paths)
            if missing:
                raise ValueError(
                    f"DOCTRINE_MULTI_PAIR_TRAINING_LABEL_STORE_MISSING — pairs {missing} "
                    f"have no label_store_dataset_path. Provide one per pair OR run B2 "
                    f"first to build label_store per pair."
                )
        return self


class StrategyLadderMultiPairExpectedEdgeTrainingReport(BaseModel, frozen=True):
    """Audit-ready report for multi-pair expected-edge training.

    Patch C1.3.C — exposes per-pair stats for transparency (sample count, weight,
    inclusion status). Doctrine V5.3 audit-ready : tout doit être traçable.
    """

    artifact_id: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)
    ready: bool = False
    pair_scope: tuple[str, ...] = ()
    accepted_pairs: tuple[str, ...] = ()
    rejected_pairs: tuple[str, ...] = ()
    rejection_reasons: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    timeframe: str = Field(..., min_length=1)
    artifact_path: str | None = None
    artifact_hash: str | None = None
    feature_hash: str | None = None
    dataset_hash: str | None = None
    feature_names: tuple[str, ...] = ()
    pair_sample_distribution: dict[str, int] = Field(default_factory=dict)
    pair_sample_weights: dict[str, float] = Field(default_factory=dict)
    pair_id_encoding: dict[str, int] = Field(default_factory=dict)
    used_categorical_pair_id: bool = True
    used_inverse_frequency_weighting: bool = True
    total_training_rows: int = Field(default=0, ge=0)
    train_start: str = Field(..., min_length=1)
    train_end: str = Field(..., min_length=1)
    blocking_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class _PairAssignment:
    """Internal helper : pair → int_id encoding + sample stats."""

    pair_to_id: dict[str, int]
    pair_to_sample_count: dict[str, int]
    pair_to_weight: dict[str, float]


def _assign_pair_ids_deterministic(pairs: Iterable[str]) -> dict[str, int]:
    """Patch C1.3.C — assign int id per pair using SORTED order for determinism.

    Ne PAS utiliser hash() ou random — sorted alphabetical garantit
    reproductibilité across runs et machines.

    Filtres : strings vides ET whitespace-only sont ignorés.
    """
    sorted_pairs = sorted(set(p for p in pairs if p and p.strip()))
    return {pair: idx for idx, pair in enumerate(sorted_pairs)}


def _compute_inverse_frequency_weights(
    pair_to_sample_count: dict[str, int],
) -> dict[str, float]:
    """Patch C1.3.C — compute per-pair weight as 1/n_samples normalized.

    Normalize so mean weight = 1.0 across all samples (preserves total mass).
    Imbalance correction : pair with fewer samples gets higher per-sample weight.
    """
    if not pair_to_sample_count:
        return {}
    total_samples = sum(pair_to_sample_count.values())
    n_pairs = len(pair_to_sample_count)
    if total_samples == 0 or n_pairs == 0:
        return {pair: 1.0 for pair in pair_to_sample_count}
    # Each pair contributes total_samples/n_pairs effective samples after weighting.
    target_per_pair = total_samples / n_pairs
    return {
        pair: target_per_pair / count if count > 0 else 1.0
        for pair, count in pair_to_sample_count.items()
    }


def _build_multi_pair_pair_assignment(
    *,
    pairs: tuple[str, ...],
    rows_per_pair: dict[str, tuple[MlTrainingRow, ...]],
    apply_inverse_frequency: bool,
) -> _PairAssignment:
    """Patch C1.3.C — build pair_id encoding + per-pair weights.

    Returns PairAssignment with (pair_to_id, pair_to_sample_count, pair_to_weight).
    """
    pair_to_id = _assign_pair_ids_deterministic(pairs)
    pair_to_sample_count = {
        pair: len(rows_per_pair.get(pair, ()))
        for pair in pairs
    }
    if apply_inverse_frequency:
        pair_to_weight = _compute_inverse_frequency_weights(pair_to_sample_count)
    else:
        pair_to_weight = {pair: 1.0 for pair in pairs}
    return _PairAssignment(
        pair_to_id=pair_to_id,
        pair_to_sample_count=pair_to_sample_count,
        pair_to_weight=pair_to_weight,
    )


def _augment_row_with_pair_id(
    row: MlTrainingRow,
    pair_id: int,
) -> MlTrainingRow:
    """Patch C1.3.C — return a new MlTrainingRow with pair_id added to features.

    MlTrainingRow is frozen (Pydantic) so we build a new one. The pair_id is
    added as a float since features dict accepts float; LightGBM will treat
    it as categorical IF categorical_feature_names=("pair_id",) is passed.
    """
    augmented_features = {**row.features, PAIR_ID_FEATURE_KEY: float(pair_id)}
    return MlTrainingRow(
        timestamp=row.timestamp,
        pair=row.pair,
        features=augmented_features,
        target=row.target,
    )


def build_multi_pair_training_rows(
    *,
    rows_per_pair: dict[str, tuple[MlTrainingRow, ...]],
    pair_assignment: _PairAssignment,
) -> tuple[tuple[MlTrainingRow, ...], tuple[float, ...]]:
    """Patch C1.3.C — concatenate rows from all pairs with pair_id encoding.

    Returns (concatenated_rows, sample_weights_aligned_with_rows).

    Order : sorted by (pair_id, timestamp) for determinism. Sample weights
    are aligned with rows by index : weights[i] applies to rows[i].
    """
    concatenated: list[MlTrainingRow] = []
    weights: list[float] = []
    # Iterate in pair_id order for determinism
    sorted_pairs = sorted(rows_per_pair.keys(), key=lambda p: pair_assignment.pair_to_id.get(p, 0))
    for pair in sorted_pairs:
        pair_id = pair_assignment.pair_to_id[pair]
        weight = pair_assignment.pair_to_weight.get(pair, 1.0)
        # Sort rows within pair by timestamp for determinism
        sorted_rows = sorted(rows_per_pair[pair], key=lambda r: r.timestamp)
        for row in sorted_rows:
            augmented = _augment_row_with_pair_id(row, pair_id)
            concatenated.append(augmented)
            weights.append(weight)
    return tuple(concatenated), tuple(weights)


def build_multi_pair_ml_trainer_request(
    *,
    artifact_id: str,
    calibration_version: str,
    rows: tuple[MlTrainingRow, ...],
    sample_weights: tuple[float, ...],
    training_seed: int,
    max_optuna_trials: int,
    use_categorical_pair_id: bool,
    shap_summary_ref: str | None = None,
) -> MlTrainerRequest:
    """Patch C1.3.C — construct MlTrainerRequest wired with C1.3.B extensions.

    Pair_id is passed as categorical_feature when use_categorical_pair_id=True
    (default). Sample weights are passed when non-uniform.
    """
    categorical_feature_names: tuple[str, ...] = (
        (PAIR_ID_FEATURE_KEY,) if use_categorical_pair_id else ()
    )
    # Only pass non-uniform weights to preserve byte-equal output for mono-pair regression
    has_variable_weights = any(
        not math.isclose(w, sample_weights[0], rel_tol=1e-9) for w in sample_weights
    ) if sample_weights else False
    weights_to_pass = sample_weights if has_variable_weights else ()
    return MlTrainerRequest(
        artifact_id=artifact_id,
        calibration_version=calibration_version,
        rows=rows,
        training_seed=training_seed,
        max_optuna_trials=max_optuna_trials,
        categorical_feature_names=categorical_feature_names,
        sample_weights=weights_to_pass,
        shap_summary_ref=shap_summary_ref,
    )


# ---------------------------------------------------------------------------
# C1.3.D — Inference helper accepting pair_id (2026-05-21)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MultiPairExpectedEdgeInferenceArtifact:
    """Loaded multi-pair expected-edge artifact ready for inference.

    Patch C1.3.D (2026-05-21) — combines LightGBM Booster + pair_id encoding
    + feature ordering for deterministic inference. Encoding comes from the
    training manifest (built in C1.3.C orchestrator).
    """

    booster: object  # lightgbm.Booster, lazy-typed to avoid hard dep
    pair_id_encoding: dict[str, int]
    feature_names: tuple[str, ...]
    feature_hash: str = ""
    artifact_path: str = ""
    manifest_path: str = ""


def load_multi_pair_inference_artifact(
    *,
    booster_path: Path,
    pair_id_encoding: dict[str, int],
    feature_names: tuple[str, ...],
    feature_hash: str = "",
    manifest_path: Path | None = None,
) -> MultiPairExpectedEdgeInferenceArtifact:
    """Load LightGBM Booster + bind C1.3.C training metadata for inference.

    Patch C1.3.D — the booster is loaded lazily (lightgbm imported on demand)
    to keep test environments without lightgbm functional. The pair_id_encoding
    + feature_names MUST match those used during C1.3.C training (saved in
    training report manifest).
    """
    import importlib

    lightgbm_module = importlib.import_module("lightgbm")
    booster = lightgbm_module.Booster(model_file=str(booster_path))
    if PAIR_ID_FEATURE_KEY not in feature_names:
        raise ValueError(
            f"DOCTRINE_MULTI_PAIR_INFERENCE_MISSING_PAIR_ID — feature_names must "
            f"include {PAIR_ID_FEATURE_KEY!r} (got {feature_names})"
        )
    if not pair_id_encoding:
        raise ValueError(
            "DOCTRINE_MULTI_PAIR_INFERENCE_EMPTY_ENCODING — pair_id_encoding "
            "must be non-empty (admin trained on at least one pair)"
        )
    return MultiPairExpectedEdgeInferenceArtifact(
        booster=booster,
        pair_id_encoding=dict(pair_id_encoding),
        feature_names=tuple(feature_names),
        feature_hash=feature_hash,
        artifact_path=str(booster_path.resolve()),
        manifest_path=str(manifest_path.resolve()) if manifest_path is not None else "",
    )


def predict_expected_edge_for_pair(
    *,
    artifact: MultiPairExpectedEdgeInferenceArtifact,
    pair: str,
    features: dict[str, float],
) -> float:
    """Predict expected_edge_bps for a specific pair using multi-pair model.

    Patch C1.3.D (2026-05-21) — fail-closed semantics : pair not in encoding
    → ValueError with actionable message. Missing pair_id in features dict is
    auto-augmented from encoding. Output is the booster's prediction in the
    same units as training target (expected_edge_bps).

    Args:
        artifact: loaded multi-pair inference artifact (from load_multi_pair_inference_artifact)
        pair: pair name (must be in artifact.pair_id_encoding)
        features: feature dict aligned with artifact.feature_names (excluding pair_id)

    Returns:
        Predicted expected_edge_bps (float)

    Raises:
        ValueError: pair unknown OR features incomplete
    """
    if pair not in artifact.pair_id_encoding:
        raise ValueError(
            f"DOCTRINE_MULTI_PAIR_INFERENCE_PAIR_UNKNOWN — pair {pair!r} not in "
            f"trained encoding. Known pairs: {sorted(artifact.pair_id_encoding)}. "
            f"Either retrain with this pair OR use a separate mono-pair model "
            f"(StrategyLadderExpectedEdgeTrainingRequest)."
        )
    pair_id = artifact.pair_id_encoding[pair]
    # Patch C1.3.D — auto-inject pair_id (override any user-provided value to
    # protect against incoherent inputs).
    augmented = {**features, PAIR_ID_FEATURE_KEY: float(pair_id)}
    # Build feature vector in artifact.feature_names order (deterministic).
    missing = tuple(
        name for name in artifact.feature_names
        if name not in augmented
    )
    if missing:
        raise ValueError(
            f"DOCTRINE_MULTI_PAIR_INFERENCE_FEATURES_INCOMPLETE — features dict "
            f"missing required keys: {missing}. Required (in order): "
            f"{artifact.feature_names}."
        )
    feature_vector = [float(augmented[name]) for name in artifact.feature_names]
    prediction = artifact.booster.predict([feature_vector])
    return float(prediction[0])


def predict_expected_edge_batch(
    *,
    artifact: MultiPairExpectedEdgeInferenceArtifact,
    pair_feature_batch: tuple[tuple[str, dict[str, float]], ...],
) -> tuple[float, ...]:
    """Patch C1.3.D — batch prediction for performance.

    Predicts expected_edge_bps for a batch of (pair, features) tuples.
    More efficient than calling predict_expected_edge_for_pair in a loop
    when many predictions are needed (e.g., scoring many candidates at once).
    """
    if not pair_feature_batch:
        return ()
    matrix: list[list[float]] = []
    for pair, features in pair_feature_batch:
        if pair not in artifact.pair_id_encoding:
            raise ValueError(
                f"DOCTRINE_MULTI_PAIR_INFERENCE_PAIR_UNKNOWN — pair {pair!r} not in "
                f"trained encoding. Known pairs: {sorted(artifact.pair_id_encoding)}."
            )
        pair_id = artifact.pair_id_encoding[pair]
        augmented = {**features, PAIR_ID_FEATURE_KEY: float(pair_id)}
        missing = tuple(
            name for name in artifact.feature_names
            if name not in augmented
        )
        if missing:
            raise ValueError(
                f"DOCTRINE_MULTI_PAIR_INFERENCE_FEATURES_INCOMPLETE — features dict "
                f"for pair {pair!r} missing required keys: {missing}."
            )
        feature_vector = [float(augmented[name]) for name in artifact.feature_names]
        matrix.append(feature_vector)
    predictions = artifact.booster.predict(matrix)
    return tuple(float(p) for p in predictions)


__all__ = [
    "PAIR_ID_FEATURE_KEY",
    "MultiPairExpectedEdgeInferenceArtifact",
    "StrategyLadderMultiPairExpectedEdgeTrainingRequest",
    "StrategyLadderMultiPairExpectedEdgeTrainingReport",
    "build_multi_pair_ml_trainer_request",
    "build_multi_pair_training_rows",
    "load_multi_pair_inference_artifact",
    "predict_expected_edge_batch",
    "predict_expected_edge_for_pair",
]
