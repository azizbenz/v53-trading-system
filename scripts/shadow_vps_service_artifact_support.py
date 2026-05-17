#!/usr/bin/env python3
"""Artifact comparison and verdict helpers for the Shadow VPS service."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from complete_enablers import (
    MlArtifactStatus,
    MlConfidenceEnabler,
    MlDirection,
    RegimeDetectorRuntime,
    load_regime_detector_runtime_artifact,
)
from complete_enablers.regime_detector_runtime_loader import (
    RegimeDetectorArtifactLoadStatus,
)
from data_backbone.microstructure import (
    DEFAULT_LOB_REGIME_TOP_N,
    DEFAULT_LOB_REGIME_WINDOW_SECONDS,
    LobRegimeFeatureSnapshot,
    lob_regime_feature_names,
)
from interface_contracts import DashboardArtifactTransferManifest
from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
    load_historical_replay_dataset,
    load_historical_snapshot_batch,
    route_snapshot_batch_to_dataset,
)
from monitoring.contracts_artifacts import (
    ArtifactShadowComparisonEvidence,
    ArtifactShadowVerdictBundle,
)
from sharia_compliance import ShariaRuntime, ShariaTradeRequest, load_sharia_policy
from shadow_vps_service_models import ShadowVpsServiceRuntimeContext

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SHARIA_POLICY_PATH = _REPO_ROOT / "config" / "sharia" / "policy_v1.yml"
_COMPARISON_DIRNAME = "artifact_comparisons"
_VERDICT_DIRNAME = "artifact_verdicts"
_SHARIA_SCOPE_MODE = "pair_perimeter_with_spot_long_assumptions"
_SHARIA_ASSUMPTION_FLAGS = (
    "assumed_product_type=SPOT",
    "assumed_leverage=1.0",
    "assumed_margin_required=false",
    "assumed_side=BUY",
    "short_predictions_treated_as_flat",
    "pair_screening_snapshot_missing",
)
_HISTORICAL_DATASET_FILENAMES = (
    "historical_dataset.json",
    "historical_dataset.jsonl",
    "historical_dataset.csv",
)
_HISTORICAL_SNAPSHOT_FILENAMES = (
    "historical_snapshot_batch.json",
    "historical_snapshot_batch.jsonl",
    "historical_snapshot_batch.csv",
    "snapshot_batch.json",
    "snapshot_batch.jsonl",
    "snapshot_batch.csv",
)


@dataclass(frozen=True)
class _ComparisonPersistenceResult:
    evidence: ArtifactShadowComparisonEvidence | None
    ref: str
    status: str


BuildComparisonEvidence = Callable[
    [HistoricalReplayDataset | None, DashboardArtifactTransferManifest, DashboardArtifactTransferManifest, datetime],
    ArtifactShadowComparisonEvidence,
]


def _bounded_unique(values: list[str], *, limit: int = 8) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))[:limit]


def _mean_or_zero(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / float(len(values))


def _artifact_manifest_refs(
    manifest: DashboardArtifactTransferManifest,
) -> tuple[str, ...]:
    refs = [manifest.source_ref, *manifest.payload_refs]
    return tuple(dict.fromkeys(ref for ref in refs if ref))


def _sidecar_path(
    service_dir: Path,
    *,
    dirname: str,
    session_date: str,
    filename: str,
) -> Path:
    output_dir = service_dir / dirname
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{session_date}.{filename}.json"


def _comparison_sidecar_path(
    service_dir: Path,
    *,
    session_date: str,
    artifact_family: str,
) -> Path:
    return _sidecar_path(
        service_dir,
        dirname=_COMPARISON_DIRNAME,
        session_date=session_date,
        filename=f"{artifact_family}.shadow_artifact_comparison",
    )


def _verdict_sidecar_path(
    service_dir: Path,
    *,
    session_date: str,
) -> Path:
    return _sidecar_path(
        service_dir,
        dirname=_VERDICT_DIRNAME,
        session_date=session_date,
        filename="shadow_challenger_verdict_bundle",
    )


def _load_dataset_from_feature_bridge(export_dir: Path) -> HistoricalReplayDataset | None:
    feature_bridge_path = export_dir / "feature_bridge.json"
    if not feature_bridge_path.is_file():
        return None
    try:
        feature_bridge = json.loads(feature_bridge_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(feature_bridge, dict):
        return None
    source_path_raw = str(feature_bridge.get("source_path", "")).strip()
    if not source_path_raw:
        return None
    source_path = Path(source_path_raw)
    if not source_path.is_file():
        return None
    source_kind = str(feature_bridge.get("source", "")).strip().lower()
    try:
        if source_kind == "historical_snapshot_batch":
            batch = load_historical_snapshot_batch(source_path)
            return route_snapshot_batch_to_dataset(
                batch,
                dataset_id=source_path.stem.replace(" ", "_"),
            )
        return load_historical_replay_dataset(source_path)
    except Exception:
        return None


def _load_shadow_comparison_dataset(export_dir: Path) -> HistoricalReplayDataset | None:
    for filename in _HISTORICAL_DATASET_FILENAMES:
        candidate = export_dir / filename
        if not candidate.is_file():
            continue
        try:
            return load_historical_replay_dataset(candidate)
        except Exception:
            continue
    for filename in _HISTORICAL_SNAPSHOT_FILENAMES:
        candidate = export_dir / filename
        if not candidate.is_file():
            continue
        try:
            batch = load_historical_snapshot_batch(candidate)
            return route_snapshot_batch_to_dataset(
                batch,
                dataset_id=candidate.stem.replace(" ", "_"),
            )
        except Exception:
            continue
    return _load_dataset_from_feature_bridge(export_dir)


def _build_sharia_runtime() -> ShariaRuntime:
    return ShariaRuntime(load_sharia_policy(_SHARIA_POLICY_PATH))


def _build_sharia_trade_request(
    row: HistoricalReplayOpportunity,
) -> ShariaTradeRequest:
    return ShariaTradeRequest(
        intent_id=row.opportunity_id,
        pair=row.pair,
        engine_id=row.engine_id,
        side="BUY",
        profile="COMPLETE",
        metadata={
            "product_type": "SPOT",
            "leverage": 1.0,
            "margin_required": False,
        },
    )


def _numeric_feature_values(row: HistoricalReplayOpportunity) -> dict[str, float]:
    projected: dict[str, float] = {}
    for key, raw_value in row.feature_values.items():
        if isinstance(raw_value, bool):
            projected[key] = 1.0 if raw_value else 0.0
        elif isinstance(raw_value, (int, float)):
            projected[key] = float(raw_value)
    return projected


def _finite_numeric_feature_values(
    row: HistoricalReplayOpportunity,
) -> dict[str, float]:
    return {
        key: value
        for key, value in _numeric_feature_values(row).items()
        if math.isfinite(value)
    }


def _normalized_shadow_decision_label(
    signal_direction: MlDirection,
) -> tuple[str, str | None]:
    if signal_direction == MlDirection.LONG:
        return "long", None
    if signal_direction == MlDirection.SHORT:
        return "flat", "ML_SHORT_TREATED_AS_FLAT_BY_HALAL_SCOPE"
    return "flat", None


def _row_expected_gain(row: HistoricalReplayOpportunity) -> float:
    return float(row.expected_edge_bps) / 10_000.0


def _row_expected_cost(row: HistoricalReplayOpportunity) -> float:
    return 0.0 if row.production_expected_cost is None else float(row.production_expected_cost)


def _row_expected_ce(row: HistoricalReplayOpportunity) -> float:
    return _row_expected_gain(row) - _row_expected_cost(row)


def _regime_snapshot_input_hash(
    row: HistoricalReplayOpportunity,
    *,
    feature_set_version: str,
    feature_values: dict[str, float],
) -> str:
    ordered_features = {
        name: feature_values[name]
        for name in lob_regime_feature_names(feature_set_version)
        if name in feature_values
    }
    payload = {
        "opportunity_id": row.opportunity_id,
        "pair": row.pair.strip().upper(),
        "timestamp_ms": row.timestamp_ms,
        "feature_set_version": feature_set_version,
        "feature_values": ordered_features,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _build_regime_snapshot_from_row(
    row: HistoricalReplayOpportunity,
    *,
    artifact_feature_set_version: str,
    required_feature_names: tuple[str, ...],
) -> tuple[LobRegimeFeatureSnapshot | None, tuple[str, ...]]:
    feature_values = _finite_numeric_feature_values(row)
    missing_required = tuple(
        feature_name
        for feature_name in required_feature_names
        if feature_name not in feature_values
    )
    if missing_required:
        return None, ("REGIME_DETECTOR_RUNTIME_FEATURES_MISSING",)

    snapshot_feature_names = lob_regime_feature_names(artifact_feature_set_version)
    snapshot_payload = {
        feature_name: feature_values.get(feature_name, 0.0)
        for feature_name in snapshot_feature_names
    }
    try:
        snapshot = LobRegimeFeatureSnapshot(
            pair=row.pair,
            computed_at_ns=max(int(row.timestamp_ms) * 1_000_000, 1),
            window_seconds=DEFAULT_LOB_REGIME_WINDOW_SECONDS,
            top_n=DEFAULT_LOB_REGIME_TOP_N,
            n_depth_events=1,
            n_trades=0,
            data_status="ready",
            insufficient_data=False,
            reason_codes=("REGIME_DETECTOR_REPLAY_SNAPSHOT_RECONSTRUCTED",),
            input_data_hash=_regime_snapshot_input_hash(
                row,
                feature_set_version=artifact_feature_set_version,
                feature_values=feature_values,
            ),
            **snapshot_payload,
        )
    except ValueError:
        return None, ("REGIME_DETECTOR_RUNTIME_INPUT_INVALID",)
    return snapshot, ()


def _regime_shadow_label(
    *,
    regime_transition_risk: float,
    regime_stability_score: float,
    market_toxicity_score: float,
    expected_duration_bucket: str,
) -> str:
    if market_toxicity_score >= 0.67:
        return "toxic"
    if regime_transition_risk >= 0.55:
        return "transition"
    if expected_duration_bucket in {"fragile", "short"}:
        return "fragile"
    if regime_stability_score >= 0.60:
        return "stable"
    return "mixed"


def _regime_strength_proxy(
    *,
    regime_transition_risk: float,
    market_toxicity_score: float,
) -> float:
    return 0.5 * float(regime_transition_risk) + 0.5 * float(market_toxicity_score)


def _build_ml_artifact_comparison_evidence(
    dataset: HistoricalReplayDataset | None,
    champion_manifest: DashboardArtifactTransferManifest,
    challenger_manifest: DashboardArtifactTransferManifest,
    as_of: datetime,
) -> ArtifactShadowComparisonEvidence:
    if dataset is None:
        return ArtifactShadowComparisonEvidence(
            artifact_family="ml",
            champion_artifact_id=champion_manifest.artifact_id or "none",
            challenger_artifact_id=challenger_manifest.artifact_id or "none",
            comparison_status="shadow_runtime_inputs_missing",
            sharia_scope_mode=_SHARIA_SCOPE_MODE,
            sharia_assumption_flags=_SHARIA_ASSUMPTION_FLAGS,
        )

    sharia_runtime = _build_sharia_runtime()
    enabler = MlConfidenceEnabler()
    champion_refs = _artifact_manifest_refs(champion_manifest)
    challenger_refs = _artifact_manifest_refs(challenger_manifest)

    halal_eligible_event_count = 0
    halal_excluded_event_count = 0
    halal_exclusion_reasons: list[str] = []
    decision_diffs = 0
    champion_no_trade_count = 0
    challenger_no_trade_count = 0
    forecast_strength_deltas: list[float] = []
    champion_expected_costs: list[float] = []
    challenger_expected_costs: list[float] = []
    champion_expected_ces: list[float] = []
    challenger_expected_ces: list[float] = []
    champion_expected_gains: list[float] = []
    challenger_expected_gains: list[float] = []
    reason_code_diffs: list[str] = []
    evaluable_event_count = 0

    for row in dataset.rows:
        sharia_decision = sharia_runtime.authorize_trade(_build_sharia_trade_request(row))
        if not sharia_decision.allowed:
            halal_excluded_event_count += 1
            halal_exclusion_reasons.append(sharia_decision.reason_code)
            continue
        halal_eligible_event_count += 1
        feature_values = _numeric_feature_values(row)
        if not feature_values:
            continue
        champion_signal = enabler.score_candidate_from_supplementary_refs(
            feature_values=feature_values,
            supplementary_refs=champion_refs,
            as_of=as_of,
        )
        challenger_signal = enabler.score_candidate_from_supplementary_refs(
            feature_values=feature_values,
            supplementary_refs=challenger_refs,
            as_of=as_of,
        )
        if (
            champion_signal.artifact_status != MlArtifactStatus.ACTIVE
            or challenger_signal.artifact_status != MlArtifactStatus.ACTIVE
        ):
            reason_code_diffs.extend(champion_signal.reason_codes)
            reason_code_diffs.extend(challenger_signal.reason_codes)
            continue
        evaluable_event_count += 1
        champion_label, champion_assumption = _normalized_shadow_decision_label(
            champion_signal.ml_direction
        )
        challenger_label, challenger_assumption = _normalized_shadow_decision_label(
            challenger_signal.ml_direction
        )
        if champion_assumption is not None:
            reason_code_diffs.append(f"champion:{champion_assumption}")
        if challenger_assumption is not None:
            reason_code_diffs.append(f"challenger:{challenger_assumption}")
        if champion_label != challenger_label:
            decision_diffs += 1
            reason_code_diffs.append(f"label_diff:{champion_label}->{challenger_label}")
        if champion_label == "flat":
            champion_no_trade_count += 1
        if challenger_label == "flat":
            challenger_no_trade_count += 1
        forecast_strength_deltas.append(
            float(challenger_signal.ml_confidence) - float(champion_signal.ml_confidence)
        )

        expected_gain = _row_expected_gain(row)
        expected_cost = _row_expected_cost(row)
        expected_ce = _row_expected_ce(row)
        if champion_label == "long":
            champion_expected_gains.append(expected_gain)
            champion_expected_costs.append(expected_cost)
            champion_expected_ces.append(expected_ce)
        if challenger_label == "long":
            challenger_expected_gains.append(expected_gain)
            challenger_expected_costs.append(expected_cost)
            challenger_expected_ces.append(expected_ce)

    comparison_status = (
        "shadow_ready"
        if evaluable_event_count > 0
        else (
            "sharia_scope_blocked"
            if halal_eligible_event_count == 0
            else "shadow_runtime_inputs_missing"
        )
    )
    return ArtifactShadowComparisonEvidence(
        artifact_family="ml",
        champion_artifact_id=champion_manifest.artifact_id or "none",
        challenger_artifact_id=challenger_manifest.artifact_id or "none",
        event_count=evaluable_event_count,
        decision_diff_rate=(
            float(decision_diffs) / float(evaluable_event_count)
            if evaluable_event_count > 0
            else 0.0
        ),
        no_trade_delta=(
            (float(challenger_no_trade_count) - float(champion_no_trade_count))
            / float(evaluable_event_count)
            if evaluable_event_count > 0
            else 0.0
        ),
        forecast_strength_delta_mean=_mean_or_zero(forecast_strength_deltas),
        expected_gain_delta_mean=(
            _mean_or_zero(challenger_expected_gains) - _mean_or_zero(champion_expected_gains)
        ),
        expected_cost_delta_mean=(
            _mean_or_zero(challenger_expected_costs) - _mean_or_zero(champion_expected_costs)
        ),
        expected_ce_delta_mean=(
            _mean_or_zero(challenger_expected_ces) - _mean_or_zero(champion_expected_ces)
        ),
        realized_slippage_delta_mean_bps=None,
        reason_code_diff_summary=_bounded_unique(reason_code_diffs),
        sharia_policy_version=sharia_runtime.policy_version,
        sharia_scope_mode=_SHARIA_SCOPE_MODE,
        halal_eligible_event_count=halal_eligible_event_count,
        halal_excluded_event_count=halal_excluded_event_count,
        halal_exclusion_reason_summary=_bounded_unique(halal_exclusion_reasons),
        sharia_assumption_flags=_SHARIA_ASSUMPTION_FLAGS,
        comparison_status=comparison_status,
    )


def _build_regime_artifact_comparison_evidence(
    dataset: HistoricalReplayDataset | None,
    champion_manifest: DashboardArtifactTransferManifest,
    challenger_manifest: DashboardArtifactTransferManifest,
    as_of: datetime,
) -> ArtifactShadowComparisonEvidence:
    if dataset is None:
        return ArtifactShadowComparisonEvidence(
            artifact_family="regime_detector",
            champion_artifact_id=champion_manifest.artifact_id or "none",
            challenger_artifact_id=challenger_manifest.artifact_id or "none",
            comparison_status="shadow_runtime_inputs_missing",
            sharia_scope_mode=_SHARIA_SCOPE_MODE,
            sharia_assumption_flags=_SHARIA_ASSUMPTION_FLAGS,
        )

    sharia_runtime = _build_sharia_runtime()
    regime_runtime = RegimeDetectorRuntime()
    champion_selection = load_regime_detector_runtime_artifact(
        _artifact_manifest_refs(champion_manifest),
        as_of=as_of,
    )
    challenger_selection = load_regime_detector_runtime_artifact(
        _artifact_manifest_refs(challenger_manifest),
        as_of=as_of,
    )
    champion_artifact = (
        champion_selection.artifact
        if champion_selection.status == RegimeDetectorArtifactLoadStatus.LOADED
        else None
    )
    challenger_artifact = (
        challenger_selection.artifact
        if challenger_selection.status == RegimeDetectorArtifactLoadStatus.LOADED
        else None
    )

    halal_eligible_event_count = 0
    halal_excluded_event_count = 0
    exclusion_reasons: list[str] = []
    decision_diffs = 0
    champion_no_trade_count = 0
    challenger_no_trade_count = 0
    forecast_strength_deltas: list[float] = []
    reason_code_diffs: list[str] = [
        *champion_selection.reasons,
        *challenger_selection.reasons,
    ]
    evaluable_event_count = 0

    for row in dataset.rows:
        sharia_decision = sharia_runtime.authorize_trade(_build_sharia_trade_request(row))
        if not sharia_decision.allowed:
            halal_excluded_event_count += 1
            exclusion_reasons.append(sharia_decision.reason_code)
            continue
        halal_eligible_event_count += 1
        if champion_artifact is None or challenger_artifact is None:
            continue

        champion_snapshot, champion_snapshot_reasons = _build_regime_snapshot_from_row(
            row,
            artifact_feature_set_version=champion_artifact.feature_set_version.value,
            required_feature_names=champion_artifact.feature_names,
        )
        challenger_snapshot, challenger_snapshot_reasons = _build_regime_snapshot_from_row(
            row,
            artifact_feature_set_version=challenger_artifact.feature_set_version.value,
            required_feature_names=challenger_artifact.feature_names,
        )
        if champion_snapshot is None or challenger_snapshot is None:
            reason_code_diffs.extend(champion_snapshot_reasons)
            reason_code_diffs.extend(challenger_snapshot_reasons)
            continue

        champion_signal = regime_runtime.evaluate(
            features=champion_snapshot,
            artifact=champion_artifact,
        )
        challenger_signal = regime_runtime.evaluate(
            features=challenger_snapshot,
            artifact=challenger_artifact,
        )
        if champion_signal.status.value != "active" or challenger_signal.status.value != "active":
            reason_code_diffs.extend(champion_signal.reason_codes)
            reason_code_diffs.extend(challenger_signal.reason_codes)
            continue

        evaluable_event_count += 1
        champion_label = _regime_shadow_label(
            regime_transition_risk=champion_signal.regime_transition_risk,
            regime_stability_score=champion_signal.regime_stability_score,
            market_toxicity_score=champion_signal.market_toxicity_score,
            expected_duration_bucket=champion_signal.expected_duration_bucket.value,
        )
        challenger_label = _regime_shadow_label(
            regime_transition_risk=challenger_signal.regime_transition_risk,
            regime_stability_score=challenger_signal.regime_stability_score,
            market_toxicity_score=challenger_signal.market_toxicity_score,
            expected_duration_bucket=challenger_signal.expected_duration_bucket.value,
        )
        if champion_label != challenger_label:
            decision_diffs += 1
            reason_code_diffs.append(f"regime_label_diff:{champion_label}->{challenger_label}")
        if champion_label == "neutral":
            champion_no_trade_count += 1
        if challenger_label == "neutral":
            challenger_no_trade_count += 1
        forecast_strength_deltas.append(
            _regime_strength_proxy(
                regime_transition_risk=challenger_signal.regime_transition_risk,
                market_toxicity_score=challenger_signal.market_toxicity_score,
            )
            - _regime_strength_proxy(
                regime_transition_risk=champion_signal.regime_transition_risk,
                market_toxicity_score=champion_signal.market_toxicity_score,
            )
        )

    comparison_status = (
        "shadow_ready"
        if evaluable_event_count > 0
        else (
            "sharia_scope_blocked"
            if halal_eligible_event_count == 0
            else "shadow_runtime_inputs_missing"
        )
    )
    return ArtifactShadowComparisonEvidence(
        artifact_family="regime_detector",
        champion_artifact_id=champion_manifest.artifact_id or "none",
        challenger_artifact_id=challenger_manifest.artifact_id or "none",
        event_count=evaluable_event_count,
        decision_diff_rate=(
            float(decision_diffs) / float(evaluable_event_count)
            if evaluable_event_count > 0
            else 0.0
        ),
        no_trade_delta=(
            (float(challenger_no_trade_count) - float(champion_no_trade_count))
            / float(evaluable_event_count)
            if evaluable_event_count > 0
            else 0.0
        ),
        forecast_strength_delta_mean=_mean_or_zero(forecast_strength_deltas),
        expected_gain_delta_mean=0.0,
        expected_cost_delta_mean=0.0,
        expected_ce_delta_mean=0.0,
        reason_code_diff_summary=_bounded_unique(reason_code_diffs),
        sharia_policy_version=sharia_runtime.policy_version,
        sharia_scope_mode=_SHARIA_SCOPE_MODE,
        halal_eligible_event_count=halal_eligible_event_count,
        halal_excluded_event_count=halal_excluded_event_count,
        halal_exclusion_reason_summary=_bounded_unique(exclusion_reasons),
        sharia_assumption_flags=_SHARIA_ASSUMPTION_FLAGS,
        comparison_status=comparison_status,
    )


def _write_shadow_artifact_comparison_evidence(
    *,
    sidecar_path: Path,
    evidence: ArtifactShadowComparisonEvidence,
) -> str:
    atomic_write_json(sidecar_path, evidence.model_dump(mode="json"), indent=2)
    return str(sidecar_path.resolve())


def _persist_family_comparison(
    *,
    service_dir: Path,
    session_date: str,
    artifact_family: str,
    dataset: HistoricalReplayDataset | None,
    champion_manifest: DashboardArtifactTransferManifest | None,
    challenger_manifest: DashboardArtifactTransferManifest | None,
    as_of: datetime,
    build_evidence: BuildComparisonEvidence,
) -> _ComparisonPersistenceResult:
    if champion_manifest is None or challenger_manifest is None or not session_date:
        return _ComparisonPersistenceResult(evidence=None, ref="", status="not_available")
    try:
        evidence = build_evidence(
            dataset,
            champion_manifest,
            challenger_manifest,
            as_of,
        )
        ref = _write_shadow_artifact_comparison_evidence(
            sidecar_path=_comparison_sidecar_path(
                service_dir,
                session_date=session_date,
                artifact_family=artifact_family,
            ),
            evidence=evidence,
        )
        return _ComparisonPersistenceResult(
            evidence=evidence,
            ref=ref,
            status=evidence.comparison_status,
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        return _ComparisonPersistenceResult(evidence=None, ref="", status="invalid_evidence")


def _status_reason(family: str, status: str) -> str:
    return f"{family}.{status}"


def _resolve_verdict(
    statuses: tuple[str, ...],
) -> tuple[str, str]:
    if not statuses:
        return "not_available", "keep_shadow"
    if any(status == "invalid_evidence" for status in statuses):
        return "invalid_evidence", "reject_or_retrain"
    if all(status == "shadow_ready" for status in statuses):
        return "shadow_validated", "review_for_micro_live_candidate"
    if all(status == "sharia_scope_blocked" for status in statuses):
        return "sharia_scope_blocked", "reject_or_retrain"
    if all(status == "shadow_runtime_inputs_missing" for status in statuses):
        return "shadow_runtime_inputs_missing", "keep_shadow"
    return "shadow_inconclusive", "keep_shadow"


def _build_shadow_challenger_verdict_bundle(
    *,
    session_date: str,
    ml_configured: bool,
    regime_configured: bool,
    ml_result: _ComparisonPersistenceResult,
    regime_result: _ComparisonPersistenceResult,
) -> ArtifactShadowVerdictBundle:
    family_results = {
        "ml": ml_result,
        "regime_detector": regime_result,
    }
    configured_families = tuple(
        family
        for family, configured in (
            ("ml", ml_configured),
            ("regime_detector", regime_configured),
        )
        if configured
    )
    statuses = tuple(family_results[family].status for family in configured_families)
    overall_verdict, operator_recommendation = _resolve_verdict(statuses)
    sharia_policy_version = next(
        (
            result.evidence.sharia_policy_version
            for result in family_results.values()
            if result.evidence is not None and result.evidence.sharia_policy_version
        ),
        "",
    )
    blocking_reasons = tuple(
        _status_reason(family, family_results[family].status)
        for family in configured_families
        if family_results[family].status in {
            "invalid_evidence",
            "shadow_runtime_inputs_missing",
            "sharia_scope_blocked",
        }
    )
    supporting_reasons = tuple(
        _status_reason(family, family_results[family].status)
        for family in configured_families
        if family_results[family].status == "shadow_ready"
    )
    return ArtifactShadowVerdictBundle(
        session_date=session_date,
        overall_verdict=overall_verdict,
        operator_recommendation=operator_recommendation,
        configured_family_count=len(configured_families),
        ready_family_count=sum(status == "shadow_ready" for status in statuses),
        invalid_family_count=sum(status == "invalid_evidence" for status in statuses),
        sharia_blocked_family_count=sum(
            status == "sharia_scope_blocked" for status in statuses
        ),
        runtime_inputs_missing_family_count=sum(
            status == "shadow_runtime_inputs_missing" for status in statuses
        ),
        ml_comparison_status=ml_result.status,
        regime_detector_comparison_status=regime_result.status,
        ml_comparison_ref=ml_result.ref,
        regime_detector_comparison_ref=regime_result.ref,
        sharia_policy_version=sharia_policy_version,
        blocking_reasons=blocking_reasons,
        supporting_reasons=supporting_reasons,
    )


def _write_shadow_verdict_bundle(
    *,
    sidecar_path: Path,
    verdict_bundle: ArtifactShadowVerdictBundle,
) -> str:
    atomic_write_json(sidecar_path, verdict_bundle.model_dump(mode="json"), indent=2)
    return str(sidecar_path.resolve())


def _persist_shadow_artifact_comparison_evidence(
    context: ShadowVpsServiceRuntimeContext,
    last_run: dict,
) -> None:
    state = context.store.state
    session_date = str(last_run.get("session_date", "")).strip()
    export_dir_ref = str(last_run.get("export_dir_ref", "")).strip()
    export_dir = Path(export_dir_ref) if export_dir_ref else None
    dataset = (
        _load_shadow_comparison_dataset(export_dir)
        if export_dir is not None and export_dir.is_dir()
        else None
    )
    as_of = datetime.now(tz=UTC)

    ml_result = _persist_family_comparison(
        service_dir=context.service_dir,
        session_date=session_date,
        artifact_family="ml",
        dataset=dataset,
        champion_manifest=state.active_ml_artifact,
        challenger_manifest=state.shadow_ml_challenger_artifact,
        as_of=as_of,
        build_evidence=_build_ml_artifact_comparison_evidence,
    )
    regime_result = _persist_family_comparison(
        service_dir=context.service_dir,
        session_date=session_date,
        artifact_family="regime_detector",
        dataset=dataset,
        champion_manifest=state.active_regime_detector_artifact,
        challenger_manifest=state.shadow_regime_detector_challenger_artifact,
        as_of=as_of,
        build_evidence=_build_regime_artifact_comparison_evidence,
    )

    updates: dict[str, object] = {
        "last_shadow_ml_artifact_comparison_ref": ml_result.ref,
        "last_shadow_ml_artifact_comparison_status": ml_result.status,
        "last_shadow_regime_detector_artifact_comparison_ref": regime_result.ref,
        "last_shadow_regime_detector_artifact_comparison_status": regime_result.status,
    }

    verdict_bundle_ref = ""
    verdict_bundle_status = "not_available"
    if session_date and (
        state.shadow_ml_challenger_artifact is not None
        or state.shadow_regime_detector_challenger_artifact is not None
    ):
        try:
            verdict_bundle = _build_shadow_challenger_verdict_bundle(
                session_date=session_date,
                ml_configured=state.shadow_ml_challenger_artifact is not None,
                regime_configured=state.shadow_regime_detector_challenger_artifact is not None,
                ml_result=ml_result,
                regime_result=regime_result,
            )
            verdict_bundle_ref = _write_shadow_verdict_bundle(
                sidecar_path=_verdict_sidecar_path(
                    context.service_dir,
                    session_date=session_date,
                ),
                verdict_bundle=verdict_bundle,
            )
            verdict_bundle_status = verdict_bundle.overall_verdict
        except (OSError, RuntimeError, TypeError, ValueError):
            verdict_bundle_ref = ""
            verdict_bundle_status = "invalid_evidence"
    updates["last_shadow_challenger_verdict_bundle_ref"] = verdict_bundle_ref
    updates["last_shadow_challenger_verdict_bundle_status"] = verdict_bundle_status
    context.store.update_state(**updates)


__all__ = ["_persist_shadow_artifact_comparison_evidence"]
