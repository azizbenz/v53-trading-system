"""Governed contracts for the minimal real Build-11/12 runtimes."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from interface_contracts import LIGHT_PAIRS, ProfileId, PromotionState, ReviewState, RuntimeMode
from protocols.enums import (
    MicroLiveRunState,
    MicroLiveVerdict,
    ShadowComparisonStatus,
    ShadowDivergenceSeverity,
    ShadowRunState,
    ShadowVerdict,
)


_ACCEPTED_IMPORT_STATUSES = frozenset({"accepted"})
_ACCEPTED_ONBOARDING_REVIEW_STATES = frozenset(
    {ReviewState.PENDING, ReviewState.APPROVED}
)
_MICRO_LIVE_ALLOWED_ENGINES = frozenset({"engine_a", "engine_b"})


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


class MicroLiveInput(BaseModel, frozen=True):
    """Single governed input entering the minimal Build-12 Micro-live gate."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId = ProfileId.LIGHT
    runtime_mode: RuntimeMode = RuntimeMode.MICRO_LIVE
    shadow_run_id: str = Field(..., min_length=1)
    shadow_truth_set_ref: str = Field(..., min_length=1)
    shadow_validation_set_ref: str = Field(..., min_length=1)
    shadow_verdict: ShadowVerdict
    shadow_run_state: ShadowRunState
    shadow_blocking_reasons: tuple[str, ...] = ()
    shadow_import_artifact_id: str = Field(..., min_length=1)
    shadow_import_lineage_version: str = Field(..., min_length=1)
    import_artifact_id: str = Field(..., min_length=1)
    import_lineage_version: str = Field(..., min_length=1)
    import_validation_status: str = Field(..., min_length=1)
    import_rejection_reasons: tuple[str, ...] = ()
    onboarding_accepted: bool = False
    onboarding_review_state: ReviewState = ReviewState.PENDING
    onboarding_reasons: tuple[str, ...] = ()
    review_export_ready: bool = False
    observability_ready: bool = False
    halt_ready: bool = False
    active_engines: tuple[str, ...] = ()
    probe_pairs: tuple[str, ...] = ()
    requested_total_notional_usdt: float = Field(..., gt=0.0)
    requested_pair_notional_usdt: float = Field(..., gt=0.0)
    max_total_notional_usdt: float = Field(..., gt=0.0)
    max_pair_notional_usdt: float = Field(..., gt=0.0)
    order_probe_limit: int = Field(default=3, ge=1, le=10)
    backtest_profile: str | None = None
    creates_profile_fork: bool = False
    automatic_live_promotion_requested: bool = False

    @model_validator(mode="after")
    def validate_governance(self) -> "MicroLiveInput":
        if self.profile != ProfileId.LIGHT:
            raise ValueError("Build-12 Micro-live opens in LIGHT profile only")
        if self.runtime_mode != RuntimeMode.MICRO_LIVE:
            raise ValueError("Build-12 Micro-live requires runtime_mode=MICRO_LIVE")
        if self.backtest_profile is not None:
            raise ValueError("BACKTEST_PROFILE is forbidden in the unified V5.3")
        if self.creates_profile_fork:
            raise ValueError("Local/VPS profile forks are forbidden")
        if self.automatic_live_promotion_requested:
            raise ValueError("Micro-live must not request automatic promotion to LIVE")

        normalized_status = self.import_validation_status.strip().casefold()
        if normalized_status not in _ACCEPTED_IMPORT_STATUSES:
            raise ValueError(
                "Build-12 Micro-live requires an accepted import_validation_status"
            )
        if self.import_rejection_reasons:
            raise ValueError(
                "Build-12 Micro-live requires empty import_rejection_reasons"
            )
        if self.shadow_import_artifact_id == "none":
            raise ValueError(
                "Build-12 Micro-live requires a concrete shadow_import_artifact_id"
            )
        if self.shadow_import_lineage_version == "n/a":
            raise ValueError(
                "Build-12 Micro-live requires a concrete shadow_import_lineage_version"
            )
        if self.import_artifact_id == "none":
            raise ValueError("Build-12 Micro-live requires a concrete import_artifact_id")
        if self.import_lineage_version == "n/a":
            raise ValueError("Build-12 Micro-live requires a concrete lineage_version")
        if self.shadow_import_artifact_id != self.import_artifact_id:
            raise ValueError(
                "Build-12 Micro-live requires matching Shadow/import artifact_id"
            )
        if self.shadow_import_lineage_version != self.import_lineage_version:
            raise ValueError(
                "Build-12 Micro-live requires matching Shadow/import lineage_version"
            )

        if self.onboarding_accepted:
            if self.onboarding_review_state not in _ACCEPTED_ONBOARDING_REVIEW_STATES:
                raise ValueError(
                    "onboarding_accepted=True requires a pending or approved onboarding_review_state"
                )
            if self.onboarding_reasons:
                raise ValueError(
                    "onboarding_accepted=True requires empty onboarding_reasons"
                )

        if not self.active_engines:
            raise ValueError("Build-12 Micro-live requires at least one Light engine")
        unknown_engines = set(self.active_engines) - _MICRO_LIVE_ALLOWED_ENGINES
        if unknown_engines:
            raise ValueError(
                "Build-12 Micro-live allows only engine_a and engine_b"
            )

        if not self.probe_pairs:
            raise ValueError("Build-12 Micro-live requires at least one probe pair")
        if len(self.probe_pairs) > len(LIGHT_PAIRS):
            raise ValueError("Build-12 Micro-live must stay within the Light pair scope")
        invalid_pairs = tuple(pair for pair in self.probe_pairs if pair not in LIGHT_PAIRS)
        if invalid_pairs:
            raise ValueError(
                "Build-12 Micro-live probe_pairs must stay within the Light pair scope"
            )

        if self.max_pair_notional_usdt > self.max_total_notional_usdt:
            raise ValueError("Micro-live max_pair_notional_usdt must stay within total budget")
        if self.requested_pair_notional_usdt > self.requested_total_notional_usdt:
            raise ValueError(
                "Micro-live requested_pair_notional_usdt must stay within total request"
            )
        if self.requested_total_notional_usdt > self.max_total_notional_usdt:
            raise ValueError("Micro-live requested_total_notional_usdt exceeds max budget")
        if self.requested_pair_notional_usdt > self.max_pair_notional_usdt:
            raise ValueError("Micro-live requested_pair_notional_usdt exceeds max pair budget")

        return self


class MicroLiveDecision(BaseModel, frozen=True):
    """Governed Build-12 verdict for a micro-live candidate."""

    allowed_to_probe: bool
    verdict: MicroLiveVerdict
    normalized_promotion_state: PromotionState
    review_state: ReviewState
    approved_total_notional_usdt: float = Field(default=0.0, ge=0.0)
    approved_pair_notional_usdt: float = Field(default=0.0, ge=0.0)
    blocking_reasons: tuple[str, ...] = ()
    manual_review_required: bool = True

    @model_validator(mode="after")
    def validate_decision(self) -> "MicroLiveDecision":
        if self.allowed_to_probe and self.verdict != MicroLiveVerdict.ALLOWED_TO_PROBE:
            raise ValueError(
                "allowed_to_probe=True requires verdict=ALLOWED_TO_PROBE"
            )
        if not self.allowed_to_probe and self.verdict == MicroLiveVerdict.ALLOWED_TO_PROBE:
            raise ValueError(
                "verdict=ALLOWED_TO_PROBE requires allowed_to_probe=True"
            )
        return self


class MicroLiveExecutionPlan(BaseModel, frozen=True):
    """Minimal micro-live plan produced by the governed Build-12 gate."""

    plan_id: str = Field(..., min_length=1)
    import_artifact_id: str = Field(..., min_length=1)
    import_lineage_version: str = Field(..., min_length=1)
    planned_engines: tuple[str, ...] = ()
    planned_pairs: tuple[str, ...] = ()
    requested_total_notional_usdt: float = Field(..., ge=0.0)
    approved_total_notional_usdt: float = Field(..., ge=0.0)
    approved_pair_notional_usdt: float = Field(..., ge=0.0)
    order_probe_limit: int = Field(..., ge=0)
    dry_run_only: bool = False
    halt_guard_required: bool = True

    @model_validator(mode="after")
    def validate_budgets(self) -> "MicroLiveExecutionPlan":
        if self.approved_total_notional_usdt > self.requested_total_notional_usdt:
            raise ValueError("Approved total notional must stay within the requested budget")
        if self.approved_pair_notional_usdt > self.approved_total_notional_usdt:
            raise ValueError("Approved pair notional must stay within the approved total budget")
        return self


class MicroLiveRunSummary(BaseModel, frozen=True):
    """Deterministic output of the minimal Build-12 Micro-live gate."""

    run_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    run_state: MicroLiveRunState
    shadow_run_id: str = Field(..., min_length=1)
    shadow_verdict: ShadowVerdict
    decision: MicroLiveDecision
    execution_plan: MicroLiveExecutionPlan
    import_artifact_id: str = Field(..., min_length=1)
    import_lineage_version: str = Field(..., min_length=1)
    observability_ready: bool = False
    halt_ready: bool = False
    onboarding_ready: bool = False

    @property
    def blocking_reason_count(self) -> int:
        return len(self.decision.blocking_reasons)

    @property
    def planned_pair_count(self) -> int:
        return len(self.execution_plan.planned_pairs)

    @property
    def planned_engine_count(self) -> int:
        return len(self.execution_plan.planned_engines)


__all__ = [
    "ShadowTruthSet",
    "ShadowValidationSet",
    "ShadowInput",
    "ShadowComparison",
    "ShadowDecision",
    "ShadowRunSummary",
    "MicroLiveInput",
    "MicroLiveDecision",
    "MicroLiveExecutionPlan",
    "MicroLiveRunSummary",
]
