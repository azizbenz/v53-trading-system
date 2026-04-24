"""Typed contracts for VPS->IA Lab shadow audit bundles of RegimeDetectorML."""

from __future__ import annotations

import math
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from interface_contracts.regime_detector_artifact import (
    RegimeDetectorFeatureSetVersion,
    RegimeDurationBucket,
)


_HEX64_LEN = 64


def _is_valid_hex64(value: str) -> bool:
    if len(value) != _HEX64_LEN:
        return False
    return all(character in "0123456789abcdef" for character in value)


class RegimeDetectorShadowAuditSchemaMatchStatus(StrEnum):
    """Closed schema-match vocabulary for VPS shadow audit bundles."""

    MATCHED = "matched"
    MISMATCHED = "mismatched"
    INCONCLUSIVE = "inconclusive"


class RegimeDetectorShadowAuditMetricSummary(BaseModel):
    """Deterministic bounded summary of one shadow metric across a window."""

    count: int = Field(default=0, ge=0)
    min_value: float = Field(default=0.0, ge=0.0, le=1.0)
    max_value: float = Field(default=0.0, ge=0.0, le=1.0)
    mean_value: float = Field(default=0.0, ge=0.0, le=1.0)
    last_value: float = Field(default=0.0, ge=0.0, le=1.0)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_bounds(self) -> "RegimeDetectorShadowAuditMetricSummary":
        if self.count == 0:
            if any(
                value != 0.0
                for value in (
                    self.min_value,
                    self.max_value,
                    self.mean_value,
                    self.last_value,
                )
            ):
                raise ValueError("empty metric summaries must stay at zero")
            return self
        if self.min_value > self.max_value:
            raise ValueError("metric summary min_value must be <= max_value")
        if not self.min_value <= self.mean_value <= self.max_value:
            raise ValueError("metric summary mean_value must stay within [min,max]")
        if not self.min_value <= self.last_value <= self.max_value:
            raise ValueError("metric summary last_value must stay within [min,max]")
        return self


class RegimeDetectorShadowAuditReasonCodeCount(BaseModel):
    """Stable reason-code count emitted by the RegimeDetector shadow audit bundle."""

    reason_code: str = Field(..., min_length=1)
    count: int = Field(..., ge=1)

    model_config = ConfigDict(frozen=True, extra="forbid")


class RegimeDetectorShadowAuditStatusCount(BaseModel):
    """Stable status count emitted by the RegimeDetector shadow audit bundle."""

    status: str = Field(..., min_length=1)
    count: int = Field(..., ge=1)

    model_config = ConfigDict(frozen=True, extra="forbid")


class RegimeDetectorShadowAuditDurationCounts(BaseModel):
    """Bucketed duration counts for active shadow predictions."""

    fragile: int = Field(default=0, ge=0)
    short: int = Field(default=0, ge=0)
    medium: int = Field(default=0, ge=0)
    persistent: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_total(self) -> "RegimeDetectorShadowAuditDurationCounts":
        resolved_total = self.fragile + self.short + self.medium + self.persistent
        if self.total != resolved_total:
            raise ValueError("duration counts total mismatch")
        return self


class RegimeDetectorShadowAuditSample(BaseModel):
    """One bounded VPS shadow observation used to build a durable audit bundle."""

    artifact_status: str = Field(..., min_length=1)
    signal_status: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    computed_at_ns: int = Field(..., ge=1)
    artifact_hash: str = ""
    feature_hash: str = ""
    regime_transition_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    regime_stability_score: float = Field(default=1.0, ge=0.0, le=1.0)
    market_toxicity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    expected_duration_bucket: RegimeDurationBucket = RegimeDurationBucket.PERSISTENT
    observation_coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    reason_codes: tuple[str, ...] = ()

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("artifact_hash", "feature_hash")
    @classmethod
    def validate_optional_hash(cls, value: str) -> str:
        if value and not _is_valid_hex64(value):
            raise ValueError("optional hashes must be empty or 64-char lowercase hex")
        return value

    @field_validator("reason_codes")
    @classmethod
    def validate_reason_codes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value if item.strip())
        if len(normalized) != len(set(normalized)):
            raise ValueError("reason_codes must stay unique per sample")
        return normalized


class RegimeDetectorShadowAuditBundle(BaseModel):
    """Durable VPS->IA Lab evidence bundle for RegimeDetectorML shadow behavior."""

    artifact_hash: str = ""
    feature_hash_at_runtime: str = ""
    feature_set_version: RegimeDetectorFeatureSetVersion = (
        RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1
    )
    feature_profile: str = Field(..., min_length=1)
    pair: str = ""
    window_start_ns: int = Field(default=0, ge=0)
    window_end_ns: int = Field(default=0, ge=0)
    sample_count: int = Field(default=0, ge=0)
    prediction_count: int = Field(default=0, ge=0)
    insufficient_data_count: int = Field(default=0, ge=0)
    runtime_stale_count: int = Field(default=0, ge=0)
    schema_match_status: RegimeDetectorShadowAuditSchemaMatchStatus = (
        RegimeDetectorShadowAuditSchemaMatchStatus.INCONCLUSIVE
    )
    transition_risk_summary: RegimeDetectorShadowAuditMetricSummary = Field(
        default_factory=RegimeDetectorShadowAuditMetricSummary
    )
    stability_score_summary: RegimeDetectorShadowAuditMetricSummary = Field(
        default_factory=RegimeDetectorShadowAuditMetricSummary
    )
    toxicity_score_summary: RegimeDetectorShadowAuditMetricSummary = Field(
        default_factory=RegimeDetectorShadowAuditMetricSummary
    )
    observation_coverage_ratio_summary: RegimeDetectorShadowAuditMetricSummary = Field(
        default_factory=RegimeDetectorShadowAuditMetricSummary
    )
    duration_bucket_counts: RegimeDetectorShadowAuditDurationCounts = Field(
        default_factory=RegimeDetectorShadowAuditDurationCounts
    )
    artifact_status_counts: tuple[RegimeDetectorShadowAuditStatusCount, ...] = ()
    signal_status_counts: tuple[RegimeDetectorShadowAuditStatusCount, ...] = ()
    reason_code_counts: tuple[RegimeDetectorShadowAuditReasonCodeCount, ...] = ()
    shadow_metrics: dict[str, float | int | str | bool] = Field(default_factory=dict)
    blocking_reasons: tuple[str, ...] = ()

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("artifact_hash", "feature_hash_at_runtime")
    @classmethod
    def validate_bundle_hash(cls, value: str) -> str:
        if value and not _is_valid_hex64(value):
            raise ValueError("bundle hashes must be empty or 64-char lowercase hex")
        return value

    @field_validator("shadow_metrics")
    @classmethod
    def validate_shadow_metrics(
        cls,
        value: dict[str, float | int | str | bool],
    ) -> dict[str, float | int | str | bool]:
        for key, item in value.items():
            if not key.strip():
                raise ValueError("shadow metric names must not be blank")
            if isinstance(item, float) and not math.isfinite(item):
                raise ValueError("shadow metric values must be finite")
        return dict(value)

    @field_validator("artifact_status_counts", "signal_status_counts")
    @classmethod
    def validate_status_counts(
        cls,
        value: tuple[RegimeDetectorShadowAuditStatusCount, ...],
    ) -> tuple[RegimeDetectorShadowAuditStatusCount, ...]:
        statuses = tuple(entry.status for entry in value)
        if len(statuses) != len(set(statuses)):
            raise ValueError("status counts must stay unique by status")
        return value

    @field_validator("reason_code_counts")
    @classmethod
    def validate_reason_code_counts(
        cls,
        value: tuple[RegimeDetectorShadowAuditReasonCodeCount, ...],
    ) -> tuple[RegimeDetectorShadowAuditReasonCodeCount, ...]:
        reason_codes = tuple(entry.reason_code for entry in value)
        if len(reason_codes) != len(set(reason_codes)):
            raise ValueError("reason code counts must stay unique by reason_code")
        return value

    @model_validator(mode="after")
    def validate_window_and_counts(self) -> "RegimeDetectorShadowAuditBundle":
        if self.window_end_ns and self.window_end_ns < self.window_start_ns:
            raise ValueError("shadow audit bundle window_end_ns must be >= window_start_ns")
        if self.sample_count < self.prediction_count:
            raise ValueError("sample_count must stay >= prediction_count")
        if self.sample_count < self.insufficient_data_count:
            raise ValueError("sample_count must stay >= insufficient_data_count")
        if self.sample_count < self.runtime_stale_count:
            raise ValueError("sample_count must stay >= runtime_stale_count")
        if self.duration_bucket_counts.total != self.prediction_count:
            raise ValueError("duration bucket total must match prediction_count")
        return self


class RegimeDetectorShadowAuditFindingSeverity(StrEnum):
    """Bounded severity levels for IA-Lab-side shadow audit findings."""

    INFO = "info"
    CAUTION = "caution"
    BLOCKING = "blocking"


class RegimeDetectorShadowAuditFindingCode(StrEnum):
    """Stable finding codes emitted by IA-Lab root-cause diagnosis."""

    AUDIT_BUNDLE_EMPTY = "audit_bundle_empty"
    ARTIFACT_HASH_MISMATCH = "artifact_hash_mismatch"
    FEATURE_HASH_MISMATCH = "feature_hash_mismatch"
    FEATURE_PROFILE_MISMATCH = "feature_profile_mismatch"
    FEATURE_SET_VERSION_MISMATCH = "feature_set_version_mismatch"
    ARTIFACT_SCHEMA_MISMATCH = "artifact_schema_mismatch"
    PAIR_NOT_IN_UNIVERSE = "pair_not_in_universe"
    SHADOW_DRIFT_HIGH = "shadow_drift_high"
    RUNTIME_STALE_PRESENT = "runtime_stale_present"
    COVERAGE_TOO_LOW = "coverage_too_low"
    INSUFFICIENT_DATA_DOMINANT = "insufficient_data_dominant"
    NO_ACTIVE_PREDICTIONS = "no_active_predictions"


class RegimeDetectorShadowAuditFinding(BaseModel):
    """One deterministic IA-Lab root-cause finding for a shadow audit bundle."""

    code: RegimeDetectorShadowAuditFindingCode
    severity: RegimeDetectorShadowAuditFindingSeverity
    detail: str = Field(..., min_length=1)

    model_config = ConfigDict(frozen=True, extra="forbid")


class RegimeDetectorShadowAuditDiagnosisStatus(StrEnum):
    """Overall IA-Lab diagnosis status for a shadow audit bundle."""

    HEALTHY = "healthy"
    CAUTION = "caution"
    BLOCKED = "blocked"


class RegimeDetectorShadowAuditDiagnosis(BaseModel):
    """IA-Lab diagnosis of a bounded VPS RegimeDetector shadow audit bundle."""

    status: RegimeDetectorShadowAuditDiagnosisStatus
    diagnosis_ready: bool = False
    artifact_hash: str = ""
    feature_set_version: RegimeDetectorFeatureSetVersion = (
        RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1
    )
    feature_profile: str = Field(..., min_length=1)
    pair: str = ""
    sample_count: int = Field(default=0, ge=0)
    prediction_count: int = Field(default=0, ge=0)
    insufficient_data_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    runtime_stale_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    observation_coverage_mean: float | None = Field(default=None, ge=0.0, le=1.0)
    shadow_diff_pct: float | None = Field(default=None, ge=0.0)
    finding_count: int = Field(default=0, ge=0)
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()
    findings: tuple[RegimeDetectorShadowAuditFinding, ...] = ()

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_finding_count(self) -> "RegimeDetectorShadowAuditDiagnosis":
        if self.finding_count != len(self.findings):
            raise ValueError("diagnosis finding_count must match findings length")
        return self


__all__ = [
    "RegimeDetectorShadowAuditSchemaMatchStatus",
    "RegimeDetectorShadowAuditMetricSummary",
    "RegimeDetectorShadowAuditReasonCodeCount",
    "RegimeDetectorShadowAuditStatusCount",
    "RegimeDetectorShadowAuditDurationCounts",
    "RegimeDetectorShadowAuditSample",
    "RegimeDetectorShadowAuditBundle",
    "RegimeDetectorShadowAuditFindingSeverity",
    "RegimeDetectorShadowAuditFindingCode",
    "RegimeDetectorShadowAuditFinding",
    "RegimeDetectorShadowAuditDiagnosisStatus",
    "RegimeDetectorShadowAuditDiagnosis",
]
