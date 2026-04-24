"""Shadow monitoring projection for artifact-only LOB RegimeDetectorML signals."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, Field

from monitoring.contracts import ProjectionStatus


class RegimeDetectorShadowProjection(BaseModel, frozen=True):
    """Dashboard-safe shadow view of the RegimeDetector artifact and signal."""

    status: ProjectionStatus
    correlation_id: str = Field(..., min_length=1)
    artifact_status: str = Field(..., min_length=1)
    signal_status: str = Field(..., min_length=1)
    pair: str = ""
    artifact_hash: str = ""
    feature_hash: str = ""
    regime_transition_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    regime_stability_score: float = Field(default=0.5, ge=0.0, le=1.0)
    market_toxicity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    expected_duration_bucket: str = "fragile"
    shadow_only: bool = True
    detail: str = Field(..., min_length=1)
    reason_codes: tuple[str, ...] = ()


def _signal_value(
    signal_payload: Mapping[str, object], key: str, default: object
) -> object:
    value = signal_payload.get(key, default)
    if hasattr(value, "value"):
        return value.value
    return value


def _projection_status(*, artifact_status: str, signal_status: str) -> ProjectionStatus:
    normalized_artifact = artifact_status.lower()
    normalized_signal = signal_status.lower()
    if normalized_artifact == "loaded" and normalized_signal == "active":
        return "healthy"
    if normalized_signal in {"neutral", "insufficient_data"}:
        return "info"
    if normalized_artifact in {"missing_supplementary_refs", "summary_not_found"}:
        return "info"
    return "warning"


def _projection_detail(*, artifact_status: str, signal_status: str) -> str:
    if artifact_status.lower() == "loaded" and signal_status.lower() == "active":
        return "RegimeDetectorML shadow inference is active and observable."
    if signal_status.lower() == "neutral":
        return "RegimeDetectorML shadow inference is neutral; trading is unchanged."
    if signal_status.lower() == "insufficient_data":
        return "RegimeDetectorML shadow inference lacks enough live LOB data."
    return f"RegimeDetectorML shadow inference is not active ({artifact_status}/{signal_status})."


def build_regime_detector_shadow_projection(
    *,
    correlation_id: str,
    artifact_status: str,
    signal_payload: Mapping[str, object],
) -> RegimeDetectorShadowProjection:
    """Build a monitoring-only projection from a serialized shadow signal."""

    signal_status = str(_signal_value(signal_payload, "status", "neutral"))
    return RegimeDetectorShadowProjection(
        status=_projection_status(artifact_status=artifact_status, signal_status=signal_status),
        correlation_id=correlation_id,
        artifact_status=artifact_status,
        signal_status=signal_status,
        pair=str(_signal_value(signal_payload, "pair", "")),
        artifact_hash=str(_signal_value(signal_payload, "artifact_hash", "")),
        feature_hash=str(_signal_value(signal_payload, "feature_hash", "")),
        regime_transition_risk=float(
            _signal_value(signal_payload, "regime_transition_risk", 0.0)
        ),
        regime_stability_score=float(
            _signal_value(signal_payload, "regime_stability_score", 0.5)
        ),
        market_toxicity_score=float(_signal_value(signal_payload, "market_toxicity_score", 0.0)),
        expected_duration_bucket=str(
            _signal_value(signal_payload, "expected_duration_bucket", "fragile")
        ),
        detail=_projection_detail(artifact_status=artifact_status, signal_status=signal_status),
        reason_codes=tuple(str(item) for item in signal_payload.get("reason_codes", ())),
    )


__all__ = [
    "RegimeDetectorShadowProjection",
    "build_regime_detector_shadow_projection",
]
