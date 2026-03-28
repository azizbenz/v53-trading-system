"""Governed contracts for the minimal real Build-11 Shadow runtime."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from interface_contracts import ProfileId, PromotionState, ReviewState, RuntimeMode
from protocols.enums import (
    ShadowComparisonStatus,
    ShadowDivergenceSeverity,
    ShadowRunState,
    ShadowVerdict,
)


_ACCEPTED_IMPORT_STATUSES = frozenset({"accepted"})


class ShadowTruthSet(BaseModel, frozen=True):
    """Baseline truth set used by Shadow for candidate comparison."""

    truth_ref: str = Field(..., min_length=1)
    dtr_coverage: float = Field(..., ge=0.0, le=1.0)
    cra_sterilization_rate: float = Field(..., ge=0.0, le=1.0)
    break_even_drift_scope_count: int = Field(..., ge=0)
    edge_degraded_count: int = Field(..., ge=0)
    ce_net: float = 0.0
    active_alert_count: int = Field(..., ge=0)
    queue_backlog: int = Field(..., ge=0)


class ShadowValidationSet(BaseModel, frozen=True):
    """Candidate validation set measured in Shadow conditions."""

    validation_ref: str = Field(..., min_length=1)
    dtr_coverage: float = Field(..., ge=0.0, le=1.0)
    cra_sterilization_rate: float = Field(..., ge=0.0, le=1.0)
    break_even_drift_scope_count: int = Field(..., ge=0)
    edge_degraded_count: int = Field(..., ge=0)
    ce_net: float = 0.0
    active_alert_count: int = Field(..., ge=0)
    queue_backlog: int = Field(..., ge=0)
    accepted_import: bool = False
    import_validation_status: str = Field(..., min_length=1)
    import_artifact_id: str = ""
    import_lineage_version: str = ""
    import_rejection_reasons: tuple[str, ...] = ()
    build9x_diagnostics_count: int = Field(default=0, ge=0)
    open_hypotheses: int = Field(default=0, ge=0)
    replay_candidate_count: int = Field(default=0, ge=0)
    review_export_ready: bool = False

    @model_validator(mode="after")
    def validate_import_consistency(self) -> "ShadowValidationSet":
        normalized_status = self.import_validation_status.strip().casefold()

        if self.accepted_import:
            if normalized_status not in _ACCEPTED_IMPORT_STATUSES:
                raise ValueError(
                    "accepted_import=True requires an acceptance import_validation_status"
                )
            if self.import_rejection_reasons:
                raise ValueError(
                    "accepted_import=True requires empty import_rejection_reasons"
                )

        if normalized_status in _ACCEPTED_IMPORT_STATUSES and not self.accepted_import:
            raise ValueError(
                "accepted import_validation_status requires accepted_import=True"
            )

        return self


class ShadowInput(BaseModel, frozen=True):
    """Single governed input entering the Build-11 Shadow runtime."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId = ProfileId.LIGHT
    runtime_mode: RuntimeMode = RuntimeMode.SHADOW
    truth_set: ShadowTruthSet
    validation_set: ShadowValidationSet
    max_allowed_dtr_coverage_drop: float = Field(default=0.05, ge=0.0, le=1.0)
    max_allowed_cra_increase: float = Field(default=0.10, ge=0.0, le=1.0)
    max_allowed_break_even_drift_scope_increase: int = Field(default=0, ge=0)
    max_allowed_edge_degraded_delta: int = Field(default=0, ge=0)
    max_allowed_ce_net_drop: float = Field(default=0.0005, ge=0.0)
    max_allowed_alert_count_increase: int = Field(default=1, ge=0)
    max_allowed_queue_backlog_increase: int = Field(default=25, ge=0)
    backtest_profile: str | None = None
    creates_profile_fork: bool = False
    automatic_promotion_requested: bool = False

    @model_validator(mode="after")
    def validate_governance(self) -> "ShadowInput":
        if self.profile != ProfileId.LIGHT:
            raise ValueError("Build-11 Shadow opens in LIGHT profile only")
        if self.runtime_mode != RuntimeMode.SHADOW:
            raise ValueError("Build-11 Shadow requires runtime_mode=SHADOW")
        if self.backtest_profile is not None:
            raise ValueError("BACKTEST_PROFILE is forbidden in the unified V5.3")
        if self.creates_profile_fork:
            raise ValueError("Local/VPS profile forks are forbidden")
        if self.automatic_promotion_requested:
            raise ValueError("Shadow must not request automatic promotion")
        return self


class ShadowComparison(BaseModel, frozen=True):
    """Single baseline-vs-candidate Shadow comparison."""

    comparison_id: str = Field(..., min_length=1)
    metric_name: str = Field(..., min_length=1)
    baseline_value: float
    candidate_value: float
    delta: float = Field(..., ge=0.0)
    threshold: float = Field(..., ge=0.0)
    status: ShadowComparisonStatus
    severity: ShadowDivergenceSeverity
    blocking: bool = False
    summary: str = Field(..., min_length=1)


class ShadowDecision(BaseModel, frozen=True):
    """Governed Shadow verdict for a candidate."""

    accepted: bool
    verdict: ShadowVerdict
    normalized_promotion_state: PromotionState
    review_state: ReviewState
    blocking_reasons: tuple[str, ...] = ()
    manual_review_required: bool = True


class ShadowRunSummary(BaseModel, frozen=True):
    """Deterministic output of the minimal Build-11 Shadow runtime."""

    run_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    run_state: ShadowRunState
    truth_set_ref: str = Field(..., min_length=1)
    validation_set_ref: str = Field(..., min_length=1)
    comparisons: tuple[ShadowComparison, ...] = ()
    decision: ShadowDecision
    import_artifact_id: str = ""
    import_lineage_version: str = ""
    build9x_diagnostics_count: int = Field(default=0, ge=0)
    open_hypotheses: int = Field(default=0, ge=0)
    replay_candidate_count: int = Field(default=0, ge=0)
    review_export_ready: bool = False

    @property
    def blocking_comparison_count(self) -> int:
        return sum(1 for comparison in self.comparisons if comparison.blocking)

    @property
    def divergent_comparison_count(self) -> int:
        return sum(
            1
            for comparison in self.comparisons
            if comparison.status == ShadowComparisonStatus.DIVERGENT
        )


__all__ = [
    "ShadowTruthSet",
    "ShadowValidationSet",
    "ShadowInput",
    "ShadowComparison",
    "ShadowDecision",
    "ShadowRunSummary",
]
