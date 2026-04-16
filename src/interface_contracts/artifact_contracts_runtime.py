"""Runtime constants and helpers for governed artifact contracts."""

from __future__ import annotations

from datetime import date

from .artifact_contracts_models import (
    ArtifactConflictPolicy,
    ArtifactDriftStatus,
    ArtifactHealthState,
    ArtifactLifecyclePolicy,
    ArtifactProofFloorPolicy,
    ArtifactProofSummary,
    ArtifactRuntimeErrorPolicy,
    ArtifactRuntimeGovernanceEvaluation,
    ArtifactTtlStatus,
    CompiledArtifactRegistryPolicy,
    HookId,
)


HOOK_MODULE_BY_ID: dict[HookId, str] = {
    HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION: "engine_a_hooks.py",
    HookId.ENGINE_B_SWEEP_VALIDATION: "engine_b_hooks.py",
    HookId.ENGINE_C_VOID_VALIDATION: "engine_c_hooks.py",
    HookId.ENGINE_D_REENTRY_VALIDATION: "engine_d_hooks.py",
    HookId.RISK_MICRO_FRICTION_PRECHECK: "risk_hooks.py",
    HookId.SCORING_SOFT_PENALTY_LAYER: "scoring_hooks.py",
    HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT: "portfolio_hooks.py",
    HookId.EXECUTION_NO_TRADE_FILTER: "execution_hooks.py",
}

RUNTIME_OPEN_HOOK_IDS: tuple[HookId, ...] = (
    HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
    HookId.ENGINE_B_SWEEP_VALIDATION,
    HookId.ENGINE_C_VOID_VALIDATION,
    HookId.ENGINE_D_REENTRY_VALIDATION,
    HookId.RISK_MICRO_FRICTION_PRECHECK,
    HookId.SCORING_SOFT_PENALTY_LAYER,
    HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT,
    HookId.EXECUTION_NO_TRADE_FILTER,
)

NON_ACTIVE_ARTIFACT_HEALTH_STATES: frozenset[ArtifactHealthState] = frozenset(
    {ArtifactHealthState.DORMANT, ArtifactHealthState.EXPIRED}
)

CANONICAL_ARTIFACT_CONFLICT_POLICY = ArtifactConflictPolicy()
CANONICAL_COMPILED_ARTIFACT_REGISTRY_POLICY = CompiledArtifactRegistryPolicy()
CANONICAL_ARTIFACT_PROOF_FLOOR_POLICY = ArtifactProofFloorPolicy()
CANONICAL_ARTIFACT_RUNTIME_ERROR_POLICY = ArtifactRuntimeErrorPolicy()


def is_runtime_open_hook_id(hook_id: HookId) -> bool:
    """Return whether a canonical hook id is open on the active runtime rail."""

    return hook_id in RUNTIME_OPEN_HOOK_IDS


def validate_artifact_proof_summary(
    proof_summary: ArtifactProofSummary,
    *,
    policy: ArtifactProofFloorPolicy = CANONICAL_ARTIFACT_PROOF_FLOOR_POLICY,
) -> tuple[str, ...]:
    """Validate proof summary against bounded canonical quantitative floors."""

    reasons: list[str] = []

    if policy.require_anti_cowardice_pass and not proof_summary.anti_cowardice_pass:
        reasons.append("PROOF_ANTI_COWARDICE_REQUIRED")
    if policy.require_friction_regret_pass and not proof_summary.friction_regret_pass:
        reasons.append("PROOF_FRICTION_REGRET_REQUIRED")
    if policy.require_walk_forward_pass and not proof_summary.walk_forward_pass:
        reasons.append("PROOF_WALK_FORWARD_REQUIRED")
    if (
        policy.require_regime_segmentation_pass
        and not proof_summary.regime_segmentation_pass
    ):
        reasons.append("PROOF_REGIME_SEGMENTATION_REQUIRED")
    if (
        policy.require_operational_burden_pass
        and not proof_summary.operational_burden_pass
    ):
        reasons.append("PROOF_OPERATIONAL_BURDEN_REQUIRED")
    if (
        policy.require_capital_efficiency_when_present
        and proof_summary.capital_efficiency_pass is False
    ):
        reasons.append("PROOF_CAPITAL_EFFICIENCY_REQUIRED")
    if proof_summary.ablation_delta_net_pnl < policy.min_ablation_delta_net_pnl:
        reasons.append("PROOF_ABLATION_DELTA_NET_PNL_TOO_LOW")
    if proof_summary.ablation_delta_ce is None:
        reasons.append("PROOF_ABLATION_DELTA_CE_REQUIRED")
    elif proof_summary.ablation_delta_ce < policy.min_ablation_delta_ce:
        reasons.append("PROOF_ABLATION_DELTA_CE_TOO_LOW")
    if proof_summary.friction_regret_value < 0.0:
        reasons.append("PROOF_FRICTION_REGRET_NEGATIVE")
    elif proof_summary.friction_regret_value > policy.max_friction_regret_value:
        reasons.append("PROOF_FRICTION_REGRET_TOO_HIGH")
    if proof_summary.block_rate_delta < 0.0:
        reasons.append("PROOF_BLOCK_RATE_DELTA_NEGATIVE")
    elif proof_summary.block_rate_delta > policy.max_block_rate_delta:
        reasons.append("PROOF_BLOCK_RATE_DELTA_TOO_HIGH")

    return tuple(reasons)


def evaluate_artifact_runtime_governance(
    *,
    training_end: date | None,
    lifecycle_policy: ArtifactLifecyclePolicy | None,
    governance_reference_date: date | None,
    drift_score_threshold: float | None,
    observed_drift_score: float | None,
) -> ArtifactRuntimeGovernanceEvaluation:
    """Evaluate bounded TTL/drift governance without claiming active monitoring."""

    ttl_reasons: list[str] = []
    drift_reasons: list[str] = []
    ttl_status = ArtifactTtlStatus.ACTIVE
    drift_status = ArtifactDriftStatus.NOT_OBSERVED
    derived_health_state = ArtifactHealthState.ACTIVE

    if training_end is None or lifecycle_policy is None:
        ttl_status = ArtifactTtlStatus.MISSING_POLICY
        ttl_reasons.append("ARTIFACT_LIFECYCLE_POLICY_REQUIRED")
    elif governance_reference_date is None:
        ttl_status = ArtifactTtlStatus.MISSING_REFERENCE_DATE
        ttl_reasons.append("ARTIFACT_GOVERNANCE_REFERENCE_DATE_REQUIRED")
    else:
        days_since_training_end = (governance_reference_date - training_end).days
        if days_since_training_end > lifecycle_policy.ttl_max_days:
            ttl_status = ArtifactTtlStatus.EXPIRED
            ttl_reasons.append("ARTIFACT_TTL_EXPIRED")
            derived_health_state = ArtifactHealthState.EXPIRED

    if drift_score_threshold is None:
        drift_status = ArtifactDriftStatus.MISSING_THRESHOLD
        drift_reasons.append("ARTIFACT_DRIFT_THRESHOLD_REQUIRED")
        if derived_health_state == ArtifactHealthState.ACTIVE:
            derived_health_state = ArtifactHealthState.REVIEW_REQUIRED
    elif observed_drift_score is None:
        drift_status = ArtifactDriftStatus.NOT_OBSERVED
    elif observed_drift_score > drift_score_threshold:
        drift_status = ArtifactDriftStatus.EXCEEDED
        drift_reasons.append("ARTIFACT_DRIFT_THRESHOLD_EXCEEDED")
        if derived_health_state != ArtifactHealthState.EXPIRED:
            derived_health_state = ArtifactHealthState.REVIEW_REQUIRED
    else:
        drift_status = ArtifactDriftStatus.WITHIN_THRESHOLD

    return ArtifactRuntimeGovernanceEvaluation(
        ttl_status=ttl_status,
        ttl_reasons=tuple(ttl_reasons),
        drift_status=drift_status,
        drift_reasons=tuple(drift_reasons),
        derived_health_state=derived_health_state,
    )


__all__ = [
    "CANONICAL_ARTIFACT_CONFLICT_POLICY",
    "CANONICAL_ARTIFACT_PROOF_FLOOR_POLICY",
    "CANONICAL_ARTIFACT_RUNTIME_ERROR_POLICY",
    "CANONICAL_COMPILED_ARTIFACT_REGISTRY_POLICY",
    "HOOK_MODULE_BY_ID",
    "NON_ACTIVE_ARTIFACT_HEALTH_STATES",
    "RUNTIME_OPEN_HOOK_IDS",
    "evaluate_artifact_runtime_governance",
    "is_runtime_open_hook_id",
    "validate_artifact_proof_summary",
]
