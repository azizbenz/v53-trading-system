"""Bounded artifact visibility contracts shared by Build-10 and Build-17 surfaces."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ArtifactRuntimeVisibilityProjection(BaseModel, frozen=True):
    """Bounded artifact identity and forecast/feature visibility for live surfaces."""

    slot: Literal["active", "shadow_challenger"]
    artifact_kind: str = Field(..., min_length=1)
    artifact_id: str = "none"
    artifact_hash: str = ""
    lineage_version: str = "n/a"
    feature_set_version: str = ""
    feature_hash: str = ""
    dataset_hash: str = ""
    calibration_version: str = ""
    promotion_state: str = ""
    review_state: str = ""
    validation_status: str = ""
    pair_universe_count: int = Field(default=0, ge=0)
    feature_count: int = Field(default=0, ge=0)
    forecast_target_class: str = "not_available"
    forecast_horizon_class: str = "not_available"
    bet_structure: str = "not_available"
    conditioning_state_summary: str = ""
    top_feature_names_ref: str = ""
    summary_ref: str = ""
    shadow_only: bool = False
    influence_detail: str = ""


class ArtifactThresholdConsumerProjection(BaseModel, frozen=True):
    """Bounded runtime threshold-consumer visibility surfaced to dashboards."""

    threshold_id: str = Field(..., min_length=1)
    threshold_family: str = Field(..., min_length=1)
    consumer_id: str = Field(..., min_length=1)
    consumer_interface: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)
    unit: str = ""
    current_value: float | None = None
    target_runtime_mode: str = Field(default="shadow", min_length=1)
    threshold_review_status: str = Field(..., min_length=1)
    threshold_fit_ready: bool = False
    hard_cap_binding: bool | None = None
    source_ref: str = ""
    detail: str = ""


class ArtifactComparisonProjection(BaseModel, frozen=True):
    """Bounded champion-vs-challenger shadow comparison surface."""

    champion_artifact_id: str = "none"
    challenger_artifact_id: str = "none"
    event_count: int = Field(default=0, ge=0)
    decision_diff_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    no_trade_delta: float = 0.0
    forecast_strength_delta_mean: float = 0.0
    expected_gain_delta_mean: float = 0.0
    expected_cost_delta_mean: float = 0.0
    expected_ce_delta_mean: float = 0.0
    realized_slippage_delta_mean_bps: float | None = None
    reason_code_diff_summary: tuple[str, ...] = ()
    sharia_policy_version: str = ""
    sharia_scope_mode: str = ""
    halal_eligible_event_count: int = Field(default=0, ge=0)
    halal_excluded_event_count: int = Field(default=0, ge=0)
    halal_exclusion_reason_summary: tuple[str, ...] = ()
    sharia_assumption_flags: tuple[str, ...] = ()
    comparison_status: str = "not_available"
    evidence_ref: str = ""
    shadow_only: bool = True


class ArtifactVerdictBundleProjection(BaseModel, frozen=True):
    """Bounded daily verdict across challenger evidence families."""

    session_date: str = ""
    overall_verdict: str = "not_available"
    operator_recommendation: str = "keep_shadow"
    configured_family_count: int = Field(default=0, ge=0)
    ready_family_count: int = Field(default=0, ge=0)
    invalid_family_count: int = Field(default=0, ge=0)
    sharia_blocked_family_count: int = Field(default=0, ge=0)
    runtime_inputs_missing_family_count: int = Field(default=0, ge=0)
    ml_comparison_status: str = "not_available"
    regime_detector_comparison_status: str = "not_available"
    ml_comparison_ref: str = ""
    regime_detector_comparison_ref: str = ""
    sharia_policy_version: str = ""
    blocking_reasons: tuple[str, ...] = ()
    supporting_reasons: tuple[str, ...] = ()
    evidence_ref: str = ""


class ArtifactShadowComparisonEvidence(BaseModel, frozen=True):
    """Durable bounded champion-vs-challenger evidence written by the Shadow VPS service."""

    artifact_family: Literal["ml", "regime_detector"]
    champion_artifact_id: str = Field(..., min_length=1)
    challenger_artifact_id: str = Field(..., min_length=1)
    event_count: int = Field(default=0, ge=0)
    decision_diff_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    no_trade_delta: float = 0.0
    forecast_strength_delta_mean: float = 0.0
    expected_gain_delta_mean: float = 0.0
    expected_cost_delta_mean: float = 0.0
    expected_ce_delta_mean: float = 0.0
    realized_slippage_delta_mean_bps: float | None = None
    reason_code_diff_summary: tuple[str, ...] = ()
    sharia_policy_version: str = ""
    sharia_scope_mode: str = ""
    halal_eligible_event_count: int = Field(default=0, ge=0)
    halal_excluded_event_count: int = Field(default=0, ge=0)
    halal_exclusion_reason_summary: tuple[str, ...] = ()
    sharia_assumption_flags: tuple[str, ...] = ()
    comparison_status: str = Field(default="shadow_ready", min_length=1)


class ArtifactShadowVerdictBundle(BaseModel, frozen=True):
    """Durable daily verdict written from bounded challenger evidence."""

    session_date: str = Field(..., min_length=10)
    overall_verdict: str = Field(default="not_available", min_length=1)
    operator_recommendation: str = Field(default="keep_shadow", min_length=1)
    configured_family_count: int = Field(default=0, ge=0)
    ready_family_count: int = Field(default=0, ge=0)
    invalid_family_count: int = Field(default=0, ge=0)
    sharia_blocked_family_count: int = Field(default=0, ge=0)
    runtime_inputs_missing_family_count: int = Field(default=0, ge=0)
    ml_comparison_status: str = Field(default="not_available", min_length=1)
    regime_detector_comparison_status: str = Field(default="not_available", min_length=1)
    ml_comparison_ref: str = ""
    regime_detector_comparison_ref: str = ""
    sharia_policy_version: str = ""
    blocking_reasons: tuple[str, ...] = ()
    supporting_reasons: tuple[str, ...] = ()


__all__ = [
    "ArtifactShadowComparisonEvidence",
    "ArtifactShadowVerdictBundle",
    "ArtifactRuntimeVisibilityProjection",
    "ArtifactThresholdConsumerProjection",
    "ArtifactComparisonProjection",
    "ArtifactVerdictBundleProjection",
]
