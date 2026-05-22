"""Edge model provider — predicteur ex-ante simple (MVP 2026-05-07).

Le caller dit "j'ai besoin de l'edge attendu pour ce setup au timestamp t" — le
service va chercher la donnee historique disponible et estime un edge ex-ante.

Architecture MVP :
  - Lookback rolling : N bars OHLCV jusqu'a t (causal, pas de look-ahead)
  - Forward return distribution conditionnelle : sur le lookback, on calcule
    la mediane des |close[i+1] − close[i]| / close[i] (5min forward return abs)
  - Output : edge_bps = |median_forward_return| × 10000 clampé bornes pair

Provenance : `PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE`

LIMITATION (TO_CALIBRATE) :
  - Pas de conditionnement par regime (trend / range)
  - Pas de conditionnement par direction signal (long / short)
  - Pas de feature engineering (volume, vol, OFI direction)
  - C'est un predictor naif pour MVP demonstrator. Un vrai edge model exige
    LightGBM (`calibration_methods/ml_trainer.py` existe deja) + walk-forward
    validation + conditioning par feature.

Architecture future :
  - Tier 1 : edge depuis LightGBM model loaded depuis CalibrationLoader
  - Tier 2 : edge depuis forward return median (ce module)
  - Tier 3 : DEFAULT_TO_CALIBRATE 5.0 bps
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping

from interface_contracts import MlAntiLeakageProofArtifact, MlModelArtifact
from local_replay_runtime.strategy_ladder_edge_model_provider_multi_pair import (
    EXPECTED_EDGE_ARTIFACT_MODE_MONO_PAIR_LEGACY,
    EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1,
    EXPECTED_EDGE_ARTIFACT_MODES,
    MULTI_PAIR_C1_ARTIFACT_KIND,
    GovernedMultiPairExpectedEdgeModel,
    StrategyLadderMultiPairC1Manifest,
    load_multi_pair_c1_expected_edge_model,
)
from local_replay_runtime.strategy_ladder_multiframe_ml_bundle import (
    StrategyLadderMlMultiTimeframeBundle,
)


_EXPECTED_EDGE_LABEL_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_EXPECTED_EDGE_ANTI_LEAKAGE_FILENAME = "ml_anti_leakage_proof_artifact.json"


@dataclass(frozen=True)
class EdgeEstimate:
    """Estimation audit-ready d'edge ex-ante au timestamp t."""

    edge_bps: float
    provenance: str
    n_lookback_bars_used: int
    median_abs_forward_return: float
    # `detector_status` indique seulement si le statisticien local a reussi
    # a calculer une valeur depuis les bars disponibles. La verite backtest /
    # replay ne doit jamais etre deduite de ce champ seul ; elle vient de
    # `provenance` et des rails de gouvernance (`MEASURED_*` / `GOVERNED_*`).
    detector_status: str  # "MEASURED" | "INSUFFICIENT_BARS" | "DEGENERATE_PRICES"
    warnings: tuple[str, ...] = ()
    artifact_hash: str | None = None
    feature_hash: str | None = None
    model_status: str = "EXPECTED_EDGE_MODEL_NOT_USED"


@dataclass(frozen=True)
class GovernedExpectedEdgeModelLoadResult:
    """Result of loading a frozen ML artifact for the expected-edge rail."""

    model: "GovernedExpectedEdgeModel | None"
    status: str
    training_artifact_ref: str | None = None
    artifact_hash: str | None = None
    feature_hash: str | None = None
    label_source: str = "EXPECTED_EDGE_LABEL_SOURCE_NOT_PROVEN"
    label_fidelity: str = "EXPECTED_EDGE_PROXY_DISCOVERY_ONLY"
    anti_leakage_status: str = "EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN"
    walkforward_status: str = "EXPECTED_EDGE_WALKFORWARD_NOT_DECLARED"
    horizon_minutes: int | None = None
    purge_window_minutes: int | None = None
    embargo_window_minutes: int | None = None
    blocker_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _hash_json_payload(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _feature_hash(feature_names: tuple[str, ...]) -> str:
    return _hash_json_payload(list(feature_names))


def _coerce_feature_float(value: object) -> float | None:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        result = float(value)
        return result if math.isfinite(result) else None
    return None


def _coerce_positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return None
    return numeric if numeric > 0 else None


def _read_expected_edge_training_metrics(
    artifact: MlModelArtifact,
) -> dict[str, object]:
    metrics = artifact.training_metrics
    return dict(metrics) if isinstance(metrics, dict) else {}


def _expected_edge_label_hash(artifact: MlModelArtifact) -> str | None:
    metrics = _read_expected_edge_training_metrics(artifact)
    value = str(metrics.get("strategy_ladder_label_hash") or "").strip().lower()
    return value if _EXPECTED_EDGE_LABEL_HASH_PATTERN.fullmatch(value) else None


def _expected_edge_label_source(artifact: MlModelArtifact) -> str:
    metrics = _read_expected_edge_training_metrics(artifact)
    return str(
        metrics.get("strategy_ladder_label_source")
        or metrics.get("strategy_ladder_target_policy")
        or "EXPECTED_EDGE_LABEL_SOURCE_NOT_PROVEN"
    )


def _expected_edge_label_fidelity_declared(artifact: MlModelArtifact) -> str:
    metrics = _read_expected_edge_training_metrics(artifact)
    return str(metrics.get("strategy_ladder_label_fidelity") or "").strip()


def _expected_edge_horizon_minutes(artifact: MlModelArtifact) -> int | None:
    metrics = _read_expected_edge_training_metrics(artifact)
    return _coerce_positive_int(metrics.get("strategy_ladder_target_horizon_minutes"))


def _expected_edge_purge_window_minutes(artifact: MlModelArtifact) -> int | None:
    metrics = _read_expected_edge_training_metrics(artifact)
    return _coerce_positive_int(metrics.get("strategy_ladder_purge_window_minutes"))


def _expected_edge_embargo_window_minutes(artifact: MlModelArtifact) -> int | None:
    metrics = _read_expected_edge_training_metrics(artifact)
    return _coerce_positive_int(metrics.get("strategy_ladder_embargo_window_minutes"))


def _expected_edge_walkforward_status(artifact: MlModelArtifact) -> str:
    metrics = _read_expected_edge_training_metrics(artifact)
    status = str(metrics.get("strategy_ladder_walkforward_status") or "").strip()
    split_declared = metrics.get("strategy_ladder_split_declared") is True
    if status:
        return status
    return (
        "EXPECTED_EDGE_WALKFORWARD_DECLARED"
        if split_declared
        else "EXPECTED_EDGE_WALKFORWARD_NOT_DECLARED"
    )


def _load_expected_edge_anti_leakage_proof(
    artifact_path: Path,
) -> MlAntiLeakageProofArtifact | None:
    proof_path = artifact_path.parent / _EXPECTED_EDGE_ANTI_LEAKAGE_FILENAME
    if not proof_path.is_file():
        return None
    return MlAntiLeakageProofArtifact.model_validate_json(
        proof_path.read_text(encoding="utf-8-sig")
    )


def _merge_numeric_features(
    feature_values: Mapping[str, object] | None,
    route_features: Mapping[str, object] | None,
) -> dict[str, float]:
    merged: dict[str, float] = {}
    for source in (feature_values or {}, route_features or {}):
        for key, raw_value in source.items():
            name = str(key).strip()
            if not name:
                continue
            value = _coerce_feature_float(raw_value)
            if value is not None:
                merged[name] = value
    return merged


@dataclass(frozen=True)
class GovernedExpectedEdgeModel:
    """Frozen ML artifact adapter for expected_edge_bps.

    The artifact is non-sovereign: it only emits an expected edge magnitude.
    Engine direction, sizing, cost gates and promotion gates remain unchanged.
    """

    artifact_path: Path
    artifact_hash: str
    feature_names: tuple[str, ...]
    feature_hash: str
    pair_universe: tuple[str, ...]
    calibration_version: str
    booster: object

    def estimate_expected_edge_bps(
        self,
        *,
        pair: str,
        timeframe: str | None = None,
        timestamp_ms: int,
        feature_values: Mapping[str, object] | None = None,
        route_features: Mapping[str, object] | None = None,
    ) -> EdgeEstimate:
        del timeframe
        del timestamp_ms  # timestamp is carried by the caller and kept for audit symmetry.
        if pair and self.pair_universe and pair not in self.pair_universe:
            return EdgeEstimate(
                edge_bps=0.0,
                provenance="EDGE_MODEL_BLOCKED:PAIR_NOT_IN_ARTIFACT_UNIVERSE",
                n_lookback_bars_used=0,
                median_abs_forward_return=0.0,
                detector_status="PAIR_NOT_IN_ARTIFACT_UNIVERSE",
                warnings=(f"PAIR_NOT_IN_ARTIFACT_UNIVERSE:{pair}",),
                artifact_hash=self.artifact_hash,
                feature_hash=self.feature_hash,
                model_status="GOVERNED_EDGE_MODEL_BLOCKED",
            )

        numeric_features = _merge_numeric_features(feature_values, route_features)
        missing = tuple(name for name in self.feature_names if name not in numeric_features)
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

        row = [[numeric_features[name] for name in self.feature_names]]
        try:
            predictions = self.booster.predict(row)  # type: ignore[attr-defined]
            prediction = float(list(predictions)[0])
        except Exception as exc:  # noqa: BLE001 - fail closed on model runtime errors.
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
            provenance="GOVERNED_ML_ARTIFACT_BACKTEST_TRUTH",
            n_lookback_bars_used=0,
            median_abs_forward_return=0.0,
            detector_status="GOVERNED_EDGE_MODEL_READY",
            warnings=warnings,
            artifact_hash=self.artifact_hash,
            feature_hash=self.feature_hash,
            model_status="GOVERNED_EDGE_MODEL_READY",
        )


@dataclass(frozen=True)
class GovernedExpectedEdgeMultiTimeframeModel:
    """Bundle router that selects the governed edge model by candidate timeframe."""

    artifact_path: Path
    artifact_hash: str
    feature_hash: str
    timeframe_scope: tuple[str, ...]
    models_by_timeframe: dict[str, GovernedExpectedEdgeModel]

    def estimate_expected_edge_bps(
        self,
        *,
        pair: str,
        timeframe: str | None = None,
        timestamp_ms: int,
        feature_values: Mapping[str, object] | None = None,
        route_features: Mapping[str, object] | None = None,
    ) -> EdgeEstimate:
        resolved_timeframe = str(timeframe or "").strip()
        if not resolved_timeframe:
            return EdgeEstimate(
                edge_bps=0.0,
                provenance="EDGE_MODEL_BLOCKED:TIMEFRAME_NOT_PROVIDED",
                n_lookback_bars_used=0,
                median_abs_forward_return=0.0,
                detector_status="TIMEFRAME_NOT_PROVIDED",
                warnings=("EDGE_MODEL_TIMEFRAME_NOT_PROVIDED",),
                artifact_hash=self.artifact_hash,
                feature_hash=self.feature_hash,
                model_status="GOVERNED_EDGE_MODEL_BLOCKED",
            )
        if resolved_timeframe not in self.models_by_timeframe:
            return EdgeEstimate(
                edge_bps=0.0,
                provenance="EDGE_MODEL_BLOCKED:TIMEFRAME_NOT_IN_BUNDLE",
                n_lookback_bars_used=0,
                median_abs_forward_return=0.0,
                detector_status="TIMEFRAME_NOT_IN_BUNDLE",
                warnings=(f"EDGE_MODEL_TIMEFRAME_NOT_IN_BUNDLE:{resolved_timeframe}",),
                artifact_hash=self.artifact_hash,
                feature_hash=self.feature_hash,
                model_status="GOVERNED_EDGE_MODEL_BLOCKED",
            )
        estimate = self.models_by_timeframe[resolved_timeframe].estimate_expected_edge_bps(
            pair=pair,
            timeframe=resolved_timeframe,
            timestamp_ms=timestamp_ms,
            feature_values=feature_values,
            route_features=route_features,
        )
        return EdgeEstimate(
            edge_bps=estimate.edge_bps,
            provenance=estimate.provenance,
            n_lookback_bars_used=estimate.n_lookback_bars_used,
            median_abs_forward_return=estimate.median_abs_forward_return,
            detector_status=estimate.detector_status,
            warnings=estimate.warnings,
            artifact_hash=self.artifact_hash,
            feature_hash=self.feature_hash,
            model_status=estimate.model_status,
        )


def _load_lightgbm_booster(artifact: MlModelArtifact, artifact_path: Path) -> object:
    try:
        lightgbm = __import__("lightgbm")
    except ImportError as exc:
        raise RuntimeError("LIGHTGBM_RUNTIME_MISSING") from exc
    if artifact.model_bytes_b64:
        model_str = base64.b64decode(artifact.model_bytes_b64.encode("ascii")).decode("utf-8")
        return lightgbm.Booster(model_str=model_str)
    if artifact.model_path_ref:
        model_path = Path(artifact.model_path_ref)
        if not model_path.is_absolute():
            model_path = artifact_path.parent / model_path
        return lightgbm.Booster(model_file=str(model_path))
    raise RuntimeError("MODEL_PAYLOAD_MISSING")


def _read_unique_value(
    values: list[object],
    *,
    missing_default: object,
) -> object:
    unique = tuple(dict.fromkeys(values))
    if not unique:
        return missing_default
    return unique[0] if len(unique) == 1 else missing_default


def load_governed_expected_edge_model_artifact(
    artifact_path: Path | str | None,
    *,
    expected_artifact_hash: str | None,
    now: datetime | None = None,
    expected_edge_artifact_mode: str = EXPECTED_EDGE_ARTIFACT_MODE_MONO_PAIR_LEGACY,
) -> GovernedExpectedEdgeModelLoadResult:
    """Load and validate a frozen MlModelArtifact for governed edge scoring.

    `expected_edge_artifact_mode` (Patch P1, 2026-05-22) selects between :
      - `MONO_PAIR_LEGACY` (default, backward-compat) — parses MlModelArtifact
        or StrategyLadderMlMultiTimeframeBundle.
      - `MULTI_PAIR_C1` — parses StrategyLadderMultiPairC1Manifest (produced by
        the C1.3.C orchestrator) and wraps the LightGBM Booster via
        GovernedMultiPairExpectedEdgeModel.
    """

    if expected_edge_artifact_mode not in EXPECTED_EDGE_ARTIFACT_MODES:
        return GovernedExpectedEdgeModelLoadResult(
            model=None,
            status="GOVERNED_EDGE_MODEL_MODE_UNKNOWN",
            blocker_codes=(
                f"GOVERNED_EDGE_MODEL_MODE_UNKNOWN:{expected_edge_artifact_mode}",
            ),
            warnings=(f"GOVERNED_EDGE_MODEL_MODE_UNKNOWN:{expected_edge_artifact_mode}",),
        )

    if artifact_path is None:
        return GovernedExpectedEdgeModelLoadResult(
            model=None,
            status="EXPECTED_EDGE_PROXY_DISCOVERY_ONLY",
            label_fidelity="EXPECTED_EDGE_PROXY_DISCOVERY_ONLY",
            anti_leakage_status="EXPECTED_EDGE_ANTI_LEAKAGE_MISSING",
            blocker_codes=(
                "GOVERNED_EDGE_MODEL_PATH_MISSING",
                "EXPECTED_EDGE_PROXY_BLOCKED",
            ),
            warnings=("GOVERNED_EDGE_MODEL_PATH_MISSING",),
        )
    path = Path(artifact_path)
    training_artifact_ref = str(path.resolve())
    if not path.is_file():
        return GovernedExpectedEdgeModelLoadResult(
            model=None,
            status="EXPECTED_EDGE_PROXY_DISCOVERY_ONLY",
            training_artifact_ref=training_artifact_ref,
            label_fidelity="EXPECTED_EDGE_PROXY_DISCOVERY_ONLY",
            anti_leakage_status="EXPECTED_EDGE_ANTI_LEAKAGE_MISSING",
            blocker_codes=(
                "GOVERNED_EDGE_MODEL_PATH_NOT_FOUND",
                "EXPECTED_EDGE_PROXY_BLOCKED",
            ),
            warnings=(f"GOVERNED_EDGE_MODEL_PATH_NOT_FOUND:{path}",),
        )
    raw_payload = path.read_text(encoding="utf-8-sig")

    if expected_edge_artifact_mode == EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1:
        return load_multi_pair_c1_expected_edge_model(
            manifest_path=path,
            raw_payload=raw_payload,
            expected_artifact_hash=expected_artifact_hash,
        )

    if MULTI_PAIR_C1_ARTIFACT_KIND in raw_payload:
        return GovernedExpectedEdgeModelLoadResult(
            model=None,
            status="GOVERNED_EDGE_MODEL_MODE_MISMATCH:RECEIVED_MULTI_PAIR_C1_EXPECTED_LEGACY",
            training_artifact_ref=training_artifact_ref,
            blocker_codes=(
                "GOVERNED_EDGE_MODEL_MODE_MISMATCH:RECEIVED_MULTI_PAIR_C1_EXPECTED_LEGACY",
            ),
            warnings=(
                "GOVERNED_EDGE_MODEL_MODE_MISMATCH:RECEIVED_MULTI_PAIR_C1_EXPECTED_LEGACY",
            ),
        )

    artifact: MlModelArtifact | None = None
    multiframe_bundle: StrategyLadderMlMultiTimeframeBundle | None = None
    try:
        artifact = MlModelArtifact.model_validate_json(raw_payload)
    except Exception:
        try:
            multiframe_bundle = StrategyLadderMlMultiTimeframeBundle.model_validate_json(raw_payload)
        except Exception as exc:  # noqa: BLE001 - invalid artifact must fail closed.
            return GovernedExpectedEdgeModelLoadResult(
                model=None,
                status=f"GOVERNED_EDGE_MODEL_INVALID_ARTIFACT:{type(exc).__name__}",
                training_artifact_ref=training_artifact_ref,
                blocker_codes=("GOVERNED_EDGE_MODEL_INVALID_ARTIFACT",),
                warnings=(f"GOVERNED_EDGE_MODEL_INVALID_ARTIFACT:{type(exc).__name__}",),
            )

    if multiframe_bundle is not None:
        if expected_artifact_hash and multiframe_bundle.artifact_hash != expected_artifact_hash:
            return GovernedExpectedEdgeModelLoadResult(
                model=None,
                status="GOVERNED_EDGE_MODEL_HASH_MISMATCH",
                training_artifact_ref=training_artifact_ref,
                artifact_hash=multiframe_bundle.artifact_hash,
                feature_hash=multiframe_bundle.feature_hash,
                blocker_codes=("GOVERNED_EDGE_MODEL_HASH_MISMATCH",),
                warnings=("GOVERNED_EDGE_MODEL_HASH_MISMATCH",),
            )
        reference_now = now or datetime.now(tz=UTC)
        if reference_now.tzinfo is None:
            reference_now = reference_now.replace(tzinfo=UTC)
        slice_results: list[tuple[str, GovernedExpectedEdgeModelLoadResult]] = []
        models_by_timeframe: dict[str, GovernedExpectedEdgeModel] = {}
        for item in multiframe_bundle.slices:
            slice_result = load_governed_expected_edge_model_artifact(
                item.artifact_ref,
                expected_artifact_hash=item.artifact_hash,
                now=reference_now,
            )
            slice_results.append((item.timeframe, slice_result))
            if (
                slice_result.status != "EXPECTED_EDGE_GOVERNED_BACKTEST_LABELS_READY"
                or slice_result.model is None
                or not isinstance(slice_result.model, GovernedExpectedEdgeModel)
            ):
                blockers = tuple(
                    dict.fromkeys(
                        (
                            *(f"TIMEFRAME_{item.timeframe}:{code}" for code in slice_result.blocker_codes),
                            f"TIMEFRAME_{item.timeframe}:EDGE_MODEL_SLICE_NOT_READY",
                        )
                    )
                )
                warnings = tuple(
                    dict.fromkeys(
                        (
                            *(f"TIMEFRAME_{item.timeframe}:{code}" for code in slice_result.warnings),
                            f"EDGE_MODEL_SLICE_NOT_READY:{item.timeframe}",
                        )
                    )
                )
                return GovernedExpectedEdgeModelLoadResult(
                    model=None,
                    status="GOVERNED_EDGE_MODEL_BLOCKED:TIMEFRAME_SLICE_NOT_READY",
                    training_artifact_ref=training_artifact_ref,
                    artifact_hash=multiframe_bundle.artifact_hash,
                    feature_hash=multiframe_bundle.feature_hash,
                    blocker_codes=blockers,
                    warnings=warnings,
                )
            models_by_timeframe[item.timeframe] = slice_result.model
        label_source = str(
            _read_unique_value(
                [result.label_source for _timeframe, result in slice_results],
                missing_default="EXPECTED_EDGE_LABEL_SOURCE_MULTIFRAME_MIXED",
            )
        )
        label_fidelity = str(
            _read_unique_value(
                [result.label_fidelity for _timeframe, result in slice_results],
                missing_default="EXPECTED_EDGE_GOVERNANCE_CANDIDATE",
            )
        )
        anti_leakage_status = str(
            _read_unique_value(
                [result.anti_leakage_status for _timeframe, result in slice_results],
                missing_default="EXPECTED_EDGE_ANTI_LEAKAGE_BLOCKED",
            )
        )
        walkforward_status = str(
            _read_unique_value(
                [result.walkforward_status for _timeframe, result in slice_results],
                missing_default="EXPECTED_EDGE_WALKFORWARD_NOT_DECLARED",
            )
        )
        horizon_minutes = _read_unique_value(
            [result.horizon_minutes for _timeframe, result in slice_results],
            missing_default=None,
        )
        purge_window_minutes = _read_unique_value(
            [result.purge_window_minutes for _timeframe, result in slice_results],
            missing_default=None,
        )
        embargo_window_minutes = _read_unique_value(
            [result.embargo_window_minutes for _timeframe, result in slice_results],
            missing_default=None,
        )
        if (
            label_source == "EXPECTED_EDGE_LABEL_SOURCE_MULTIFRAME_MIXED"
            or anti_leakage_status != "EXPECTED_EDGE_ANTI_LEAKAGE_PROVEN"
            or walkforward_status != "EXPECTED_EDGE_WALKFORWARD_DECLARED"
            or horizon_minutes is None
            or purge_window_minutes is None
            or embargo_window_minutes is None
        ):
            return GovernedExpectedEdgeModelLoadResult(
                model=None,
                status="GOVERNED_EDGE_MODEL_BLOCKED:TIMEFRAME_SCOPE_NOT_GOVERNED",
                training_artifact_ref=training_artifact_ref,
                artifact_hash=multiframe_bundle.artifact_hash,
                feature_hash=multiframe_bundle.feature_hash,
                label_source=label_source,
                label_fidelity=label_fidelity,
                anti_leakage_status=anti_leakage_status,
                walkforward_status=walkforward_status,
                horizon_minutes=None if horizon_minutes is None else int(horizon_minutes),
                purge_window_minutes=None if purge_window_minutes is None else int(purge_window_minutes),
                embargo_window_minutes=None if embargo_window_minutes is None else int(embargo_window_minutes),
                blocker_codes=("GOVERNED_EDGE_MODEL_MULTIFRAME_GOVERNANCE_BLOCKED",),
                warnings=("GOVERNED_EDGE_MODEL_MULTIFRAME_GOVERNANCE_BLOCKED",),
            )
        return GovernedExpectedEdgeModelLoadResult(
            model=GovernedExpectedEdgeMultiTimeframeModel(
                artifact_path=path,
                artifact_hash=multiframe_bundle.artifact_hash,
                feature_hash=multiframe_bundle.feature_hash,
                timeframe_scope=multiframe_bundle.timeframe_scope,
                models_by_timeframe=models_by_timeframe,
            ),
            status="EXPECTED_EDGE_GOVERNED_BACKTEST_LABELS_READY",
            training_artifact_ref=training_artifact_ref,
            artifact_hash=multiframe_bundle.artifact_hash,
            feature_hash=multiframe_bundle.feature_hash,
            label_source=label_source,
            label_fidelity=label_fidelity,
            anti_leakage_status=anti_leakage_status,
            walkforward_status=walkforward_status,
            horizon_minutes=int(horizon_minutes),
            purge_window_minutes=int(purge_window_minutes),
            embargo_window_minutes=int(embargo_window_minutes),
            blocker_codes=(
                "EXPECTED_EDGE_GOVERNED_SHADOW_REQUIRED",
                "EXPECTED_EDGE_NOT_PROMOTION_GRADE",
            ),
        )

    assert artifact is not None

    label_source = _expected_edge_label_source(artifact)
    label_fidelity_declared = _expected_edge_label_fidelity_declared(artifact)
    label_hash = _expected_edge_label_hash(artifact)
    horizon_minutes = _expected_edge_horizon_minutes(artifact)
    purge_window_minutes = _expected_edge_purge_window_minutes(artifact)
    embargo_window_minutes = _expected_edge_embargo_window_minutes(artifact)
    walkforward_status = _expected_edge_walkforward_status(artifact)

    if expected_artifact_hash and artifact.artifact_hash != expected_artifact_hash:
        return GovernedExpectedEdgeModelLoadResult(
            model=None,
            status="GOVERNED_EDGE_MODEL_HASH_MISMATCH",
            training_artifact_ref=training_artifact_ref,
            artifact_hash=artifact.artifact_hash,
            feature_hash=artifact.feature_hash,
            label_source=label_source,
            label_fidelity="EXPECTED_EDGE_GOVERNANCE_CANDIDATE",
            anti_leakage_status="EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN",
            walkforward_status=walkforward_status,
            horizon_minutes=horizon_minutes,
            purge_window_minutes=purge_window_minutes,
            embargo_window_minutes=embargo_window_minutes,
            blocker_codes=("GOVERNED_EDGE_MODEL_HASH_MISMATCH",),
            warnings=("GOVERNED_EDGE_MODEL_HASH_MISMATCH",),
        )
    computed_feature_hash = _feature_hash(artifact.feature_names)
    if artifact.feature_hash != computed_feature_hash:
        return GovernedExpectedEdgeModelLoadResult(
            model=None,
            status="GOVERNED_EDGE_MODEL_FEATURE_HASH_MISMATCH",
            training_artifact_ref=training_artifact_ref,
            artifact_hash=artifact.artifact_hash,
            feature_hash=artifact.feature_hash,
            label_source=label_source,
            label_fidelity="EXPECTED_EDGE_GOVERNANCE_CANDIDATE",
            anti_leakage_status="EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN",
            walkforward_status=walkforward_status,
            horizon_minutes=horizon_minutes,
            purge_window_minutes=purge_window_minutes,
            embargo_window_minutes=embargo_window_minutes,
            blocker_codes=("GOVERNED_EDGE_MODEL_FEATURE_HASH_MISMATCH",),
            warnings=("GOVERNED_EDGE_MODEL_FEATURE_HASH_MISMATCH",),
        )
    governance_blockers: list[str] = []
    if label_hash is None:
        governance_blockers.append("EXPECTED_EDGE_LABEL_HASH_MISSING_OR_INVALID")
    if horizon_minutes is None:
        governance_blockers.append("EXPECTED_EDGE_HORIZON_NOT_DECLARED")
    if purge_window_minutes is None:
        governance_blockers.append("EXPECTED_EDGE_PURGE_WINDOW_NOT_DECLARED")
    if embargo_window_minutes is None:
        governance_blockers.append("EXPECTED_EDGE_EMBARGO_WINDOW_NOT_DECLARED")
    if walkforward_status != "EXPECTED_EDGE_WALKFORWARD_DECLARED":
        governance_blockers.append("EXPECTED_EDGE_WALKFORWARD_NOT_DECLARED")
    if label_fidelity_declared not in {
        "LABEL_STORE_PROMOTION_GRADE_CANDIDATE",
        "EXPECTED_EDGE_GOVERNED_BACKTEST_LABELS_READY",
    }:
        governance_blockers.append("EXPECTED_EDGE_LABEL_FIDELITY_NOT_PROMOTION_GRADE")
    if artifact.train_window.end_at > artifact.validation_window.start_at:
        governance_blockers.append("EXPECTED_EDGE_TRAIN_VALIDATION_WINDOW_OVERLAP")
    reference_now = now or datetime.now(tz=UTC)
    if reference_now.tzinfo is None:
        reference_now = reference_now.replace(tzinfo=UTC)
    stale_after = artifact.stale_after
    if stale_after is not None and stale_after.tzinfo is None:
        stale_after = stale_after.replace(tzinfo=UTC)
    if stale_after is not None and stale_after < reference_now:
        return GovernedExpectedEdgeModelLoadResult(
            model=None,
            status="GOVERNED_EDGE_MODEL_STALE",
            training_artifact_ref=training_artifact_ref,
            artifact_hash=artifact.artifact_hash,
            feature_hash=artifact.feature_hash,
            label_source=label_source,
            label_fidelity="EXPECTED_EDGE_GOVERNANCE_CANDIDATE",
            anti_leakage_status="EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN",
            walkforward_status=walkforward_status,
            horizon_minutes=horizon_minutes,
            purge_window_minutes=purge_window_minutes,
            embargo_window_minutes=embargo_window_minutes,
            blocker_codes=("GOVERNED_EDGE_MODEL_STALE",),
            warnings=("GOVERNED_EDGE_MODEL_STALE",),
        )
    anti_leakage_status = "EXPECTED_EDGE_ANTI_LEAKAGE_MISSING"
    try:
        anti_leakage_proof = _load_expected_edge_anti_leakage_proof(path)
    except Exception as exc:  # noqa: BLE001 - fail closed on malformed proof sidecars.
        anti_leakage_proof = None
        anti_leakage_status = f"EXPECTED_EDGE_ANTI_LEAKAGE_INVALID:{type(exc).__name__}"
        governance_blockers.append("EXPECTED_EDGE_ANTI_LEAKAGE_PROOF_INVALID")
    else:
        if anti_leakage_proof is None:
            governance_blockers.append("EXPECTED_EDGE_ANTI_LEAKAGE_PROOF_MISSING")
        else:
            proof_blockers: list[str] = []
            if anti_leakage_proof.target_artifact_hash != artifact.artifact_hash:
                proof_blockers.append("EXPECTED_EDGE_ANTI_LEAKAGE_TARGET_HASH_MISMATCH")
            if anti_leakage_proof.feature_hash != artifact.feature_hash:
                proof_blockers.append("EXPECTED_EDGE_ANTI_LEAKAGE_FEATURE_HASH_MISMATCH")
            if anti_leakage_proof.dataset_hash != artifact.dataset_hash:
                proof_blockers.append("EXPECTED_EDGE_ANTI_LEAKAGE_DATASET_HASH_MISMATCH")
            if not anti_leakage_proof.promotion_ready_proof:
                proof_blockers.append("EXPECTED_EDGE_ANTI_LEAKAGE_PROOF_NOT_READY")
            if proof_blockers:
                governance_blockers.extend(proof_blockers)
                anti_leakage_status = "EXPECTED_EDGE_ANTI_LEAKAGE_BLOCKED"
            else:
                anti_leakage_status = "EXPECTED_EDGE_ANTI_LEAKAGE_PROVEN"
    if governance_blockers:
        return GovernedExpectedEdgeModelLoadResult(
            model=None,
            status="EXPECTED_EDGE_GOVERNANCE_CANDIDATE",
            training_artifact_ref=training_artifact_ref,
            artifact_hash=artifact.artifact_hash,
            feature_hash=artifact.feature_hash,
            label_source=label_source,
            label_fidelity="EXPECTED_EDGE_GOVERNANCE_CANDIDATE",
            anti_leakage_status=anti_leakage_status,
            walkforward_status=walkforward_status,
            horizon_minutes=horizon_minutes,
            purge_window_minutes=purge_window_minutes,
            embargo_window_minutes=embargo_window_minutes,
            blocker_codes=tuple(
                dict.fromkeys(
                    (
                        *governance_blockers,
                        "EXPECTED_EDGE_PROXY_BLOCKED",
                        "EXPECTED_EDGE_NOT_PROMOTION_GRADE",
                    )
                )
            ),
            warnings=tuple(
                dict.fromkeys(
                    (
                        *tuple(f"EXPECTED_EDGE_GOVERNANCE_BLOCKED:{code}" for code in governance_blockers),
                        "EXPECTED_EDGE_PROXY_BLOCKED",
                    )
                )
            ),
        )
    try:
        booster = _load_lightgbm_booster(artifact, path)
    except Exception as exc:  # noqa: BLE001 - fail closed if runtime cannot score.
        return GovernedExpectedEdgeModelLoadResult(
            model=None,
            status=f"GOVERNED_EDGE_MODEL_LOAD_FAILED:{type(exc).__name__}",
            training_artifact_ref=training_artifact_ref,
            artifact_hash=artifact.artifact_hash,
            feature_hash=artifact.feature_hash,
            label_source=label_source,
            label_fidelity="EXPECTED_EDGE_GOVERNED_BACKTEST_LABELS_READY",
            anti_leakage_status=anti_leakage_status,
            walkforward_status=walkforward_status,
            horizon_minutes=horizon_minutes,
            purge_window_minutes=purge_window_minutes,
            embargo_window_minutes=embargo_window_minutes,
            blocker_codes=("GOVERNED_EDGE_MODEL_LOAD_FAILED",),
            warnings=(f"GOVERNED_EDGE_MODEL_LOAD_FAILED:{type(exc).__name__}",),
        )

    model = GovernedExpectedEdgeModel(
        artifact_path=path,
        artifact_hash=artifact.artifact_hash,
        feature_names=artifact.feature_names,
        feature_hash=artifact.feature_hash,
        pair_universe=artifact.pair_universe,
        calibration_version=artifact.calibration_version,
        booster=booster,
    )
    return GovernedExpectedEdgeModelLoadResult(
        model=model,
        status="EXPECTED_EDGE_GOVERNED_BACKTEST_LABELS_READY",
        training_artifact_ref=training_artifact_ref,
        artifact_hash=artifact.artifact_hash,
        feature_hash=artifact.feature_hash,
        label_source=label_source,
        label_fidelity="EXPECTED_EDGE_GOVERNED_BACKTEST_LABELS_READY",
        anti_leakage_status=anti_leakage_status,
        walkforward_status=walkforward_status,
        horizon_minutes=horizon_minutes,
        purge_window_minutes=purge_window_minutes,
        embargo_window_minutes=embargo_window_minutes,
        blocker_codes=(
            "EXPECTED_EDGE_GOVERNED_SHADOW_REQUIRED",
            "EXPECTED_EDGE_NOT_PROMOTION_GRADE",
        ),
    )


def estimate_forward_return_edge_bps(
    *,
    raw_ohlcv_path: Path | str | None,
    timestamp_ms: int,
    lookback_ms: int = 60 * 60 * 1000,  # 1h par defaut
    min_bars: int = 5,
) -> EdgeEstimate:
    """Mesure ex-ante l'edge attendu via la distribution des forward returns
    sur le lookback rolling causal.

    Strategie :
      1. Charge les bars OHLCV dans [timestamp_ms - lookback_ms, timestamp_ms]
      2. Calcule pour chaque bar i : forward_return_i = (close[i+1] - close[i]) / close[i]
      3. Edge = mediane(|forward_return_i|) × 10000

    Causal : on n'utilise QUE les bars <= timestamp_ms. Le forward_return_i
    pour le dernier bar n'est pas calculable (pas de bar suivant), donc on
    l'ignore. C'est la mediane des deltas observes DANS le lookback.
    """
    warnings: list[str] = []
    if raw_ohlcv_path is None:
        return EdgeEstimate(
            edge_bps=0.0,
            provenance="DEFAULT_TO_CALIBRATE",
            n_lookback_bars_used=0,
            median_abs_forward_return=0.0,
            detector_status="OHLCV_PATH_MISSING",
            warnings=("OHLCV_PATH_MISSING",),
        )
    ohlcv_path = Path(raw_ohlcv_path)
    if not ohlcv_path.exists():
        return EdgeEstimate(
            edge_bps=0.0,
            provenance="DEFAULT_TO_CALIBRATE",
            n_lookback_bars_used=0,
            median_abs_forward_return=0.0,
            detector_status=f"OHLCV_PATH_NOT_FOUND:{ohlcv_path}",
            warnings=(f"OHLCV_PATH_NOT_FOUND",),
        )

    bars: list[tuple[int, float]] = []
    extended_start = timestamp_ms - lookback_ms
    try:
        with ohlcv_path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                    ts = int(row.get("timestamp_ms") or 0)
                    close = float(row.get("close") or 0.0)
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
                if close <= 0.0:
                    continue
                # Causal : seulement les bars <= timestamp_ms
                if extended_start <= ts <= timestamp_ms:
                    bars.append((ts, close))
    except OSError as exc:
        return EdgeEstimate(
            edge_bps=0.0,
            provenance="DEFAULT_TO_CALIBRATE",
            n_lookback_bars_used=0,
            median_abs_forward_return=0.0,
            detector_status=f"OHLCV_LOAD_FAILED:{type(exc).__name__}",
            warnings=(f"OHLCV_LOAD_FAILED",),
        )

    if len(bars) < min_bars:
        return EdgeEstimate(
            edge_bps=0.0,
            provenance="DEFAULT_TO_CALIBRATE",
            n_lookback_bars_used=len(bars),
            median_abs_forward_return=0.0,
            detector_status=f"INSUFFICIENT_BARS:{len(bars)}<{min_bars}",
            warnings=(f"INSUFFICIENT_BARS:{len(bars)}<{min_bars}",),
        )

    bars.sort(key=lambda b: b[0])
    closes = [c for _, c in bars]

    # Forward returns : (close[i+1] - close[i]) / close[i]
    forward_returns: list[float] = []
    for i in range(len(closes) - 1):
        if closes[i] <= 0.0:
            continue
        fr = (closes[i + 1] - closes[i]) / closes[i]
        if math.isfinite(fr):
            forward_returns.append(fr)

    if len(forward_returns) < 2:
        return EdgeEstimate(
            edge_bps=0.0,
            provenance="DEFAULT_TO_CALIBRATE",
            n_lookback_bars_used=len(bars),
            median_abs_forward_return=0.0,
            detector_status="DEGENERATE_PRICES",
            warnings=("DEGENERATE_PRICES",),
        )

    abs_forward_returns = sorted(abs(fr) for fr in forward_returns)
    n = len(abs_forward_returns)
    if n % 2 == 1:
        median_abs = abs_forward_returns[n // 2]
    else:
        median_abs = 0.5 * (abs_forward_returns[n // 2 - 1] + abs_forward_returns[n // 2])

    edge_bps = median_abs * 10_000.0

    return EdgeEstimate(
        edge_bps=edge_bps,
        provenance="PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE",
        n_lookback_bars_used=len(bars),
        median_abs_forward_return=median_abs,
        # Successful local computation from OHLCV bars. This remains a proxy
        # calibration source, not governed backtest truth.
        detector_status="MEASURED",
        warnings=tuple(warnings),
    )


__all__ = [
    "EXPECTED_EDGE_ARTIFACT_MODE_MONO_PAIR_LEGACY",
    "EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1",
    "EXPECTED_EDGE_ARTIFACT_MODES",
    "MULTI_PAIR_C1_ARTIFACT_KIND",
    "EdgeEstimate",
    "GovernedExpectedEdgeModel",
    "GovernedExpectedEdgeMultiTimeframeModel",
    "GovernedExpectedEdgeModelLoadResult",
    "GovernedMultiPairExpectedEdgeModel",
    "StrategyLadderMultiPairC1Manifest",
    "estimate_forward_return_edge_bps",
    "load_governed_expected_edge_model_artifact",
    "load_multi_pair_c1_expected_edge_model",
]
