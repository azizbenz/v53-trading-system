"""Typed models and enums for governed artifact contracts."""

from __future__ import annotations

from datetime import date
from enum import Enum, unique

from pydantic import BaseModel, Field, model_validator

from .feature_lock_contracts import (
    FeatureLineageLock,
    TransformWhitelistLock,
    validate_feature_lineage_lock,
    validate_transform_whitelist_lock,
)


@unique
class ArtifactActivationStage(str, Enum):
    """Functional runtime activation stage declared by an artifact."""

    REPLAY_ONLY = "replay_only"
    SHADOW_READY = "shadow_ready"
    LIMITED_INFLUENCE = "limited_influence"
    MICRO_LIVE_CANDIDATE = "micro_live_candidate"
    LIVE_APPROVED = "live_approved"


@unique
class ArtifactHealthState(str, Enum):
    """Health/drift state of an artifact independently from activation stage."""

    ACTIVE = "active"
    DECAYING = "decaying"
    REVIEW_REQUIRED = "review_required"
    DORMANT = "dormant"
    EXPIRED = "expired"


@unique
class ArtifactLogicFormat(str, Enum):
    """Declared distilled artifact payload format."""

    THRESHOLD_JSON = "threshold_json"
    LOOKUP_JSON = "lookup_json"
    RULE_AST_JSON = "rule_ast_json"


@unique
class HookId(str, Enum):
    """Canonical runtime hooks authorized by the corpus."""

    ENGINE_A_PRE_ENTRY_CONFIRMATION = "engine_a_pre_entry_confirmation"
    ENGINE_B_SWEEP_VALIDATION = "engine_b_sweep_validation"
    ENGINE_C_VOID_VALIDATION = "engine_c_void_validation"
    ENGINE_D_REENTRY_VALIDATION = "engine_d_reentry_validation"
    RISK_MICRO_FRICTION_PRECHECK = "risk_micro_friction_precheck"
    SCORING_SOFT_PENALTY_LAYER = "scoring_soft_penalty_layer"
    PORTFOLIO_RELATIVE_RANK_ADJUSTMENT = "portfolio_relative_rank_adjustment"
    EXECUTION_NO_TRADE_FILTER = "execution_no_trade_filter"


@unique
class ArtifactActionKind(str, Enum):
    """Minimal canonical influence forms for governed runtime artifacts."""

    SOFT_BOOST = "soft_boost"
    SOFT_REDUCE = "soft_reduce"
    NO_TRADE = "no_trade"
    SIZE_REDUCE = "size_reduce"
    RANK_ADJUST = "rank_adjust"


@unique
class ActionUnit(str, Enum):
    """Allowed action units for bounded artifact influence."""

    RAW_SCORE_MULTIPLIER = "raw_score_multiplier"
    RAW_SCORE_ADD = "raw_score_add"
    CONVICTION_ADD = "conviction_add"
    SIZE_FACTOR = "size_factor"
    RANK_DELTA = "rank_delta"


@unique
class ArtifactConflictResolutionMode(str, Enum):
    """Canonical VPS-side policy for conflicts between multiple active artifacts."""

    NO_TRADE_THEN_STRICTEST = "no_trade_then_strictest"


@unique
class ScoreConflictAggregationMode(str, Enum):
    """Canonical composition rule for score-affecting artifact actions."""

    BOUNDED_SUM_WITH_GLOBAL_CAP = "bounded_sum_with_global_cap"


@unique
class SizeReduceConflictMode(str, Enum):
    """Canonical composition rule for multiple size-reduction actions."""

    MIN_FACTOR_WINS = "min_factor_wins"


@unique
class RankAdjustConflictMode(str, Enum):
    """Canonical composition rule for rank adjustments."""

    BOUNDED_SUM = "bounded_sum"


@unique
class CompiledRegistryAtomicityMode(str, Enum):
    """Canonical publication mode for the compiled artifact registry."""

    ATOMIC_SNAPSHOT_SWAP = "atomic_snapshot_swap"


@unique
class CompiledRegistryConcurrencyModel(str, Enum):
    """Canonical concurrency model for registry reads/writes."""

    SINGLE_WRITER_MULTI_READER = "single_writer_multi_reader"


@unique
class ArtifactRuntimeFailureMode(str, Enum):
    """Canonical runtime handling mode for bounded artifact influence failures."""

    FAIL_OPEN_BASELINE_SKIP_ARTIFACT = "fail_open_baseline_skip_artifact"


@unique
class ArtifactRuntimeFailureStage(str, Enum):
    """Where a bounded artifact runtime rail failed."""

    PLAN_SELECTION = "plan_selection"
    PAYLOAD_LOAD = "payload_load"
    HOOK_EXECUTION = "hook_execution"


@unique
class DistilledRuleLogicalOp(str, Enum):
    """Logical operator joining multiple rule conditions."""

    AND = "AND"
    OR = "OR"


@unique
class DistilledRuleOperator(str, Enum):
    """Closed comparison vocabulary for RULE_AST_JSON conditions."""

    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="
    IN_RANGE = "IN_RANGE"


@unique
class ArtifactClass(str, Enum):
    """Canonical high-level artifact classes exported by the Lab."""

    EDGE_ADDER = "EDGE_ADDER"
    DAMAGE_REDUCER = "DAMAGE_REDUCER"
    EXEC_SURVIVABILITY_FILTER = "EXEC_SURVIVABILITY_FILTER"
    CAPITAL_EFFICIENCY_ENHANCER = "CAPITAL_EFFICIENCY_ENHANCER"


@unique
class ArtifactCompatibilityStatus(str, Enum):
    """Compatibility status published by the VPS compatibility registry."""

    SUPPORTED = "supported"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"


@unique
class ArtifactTrustKeyStatus(str, Enum):
    """Trust-store status of a public signing key."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"


@unique
class ArtifactPolicyErrorCode(str, Enum):
    """Normalized policy-layer rejection/error codes for governed artifacts."""

    ARTIFACT_SCHEMA_UNKNOWN = "ARTIFACT_SCHEMA_UNKNOWN"
    ARTIFACT_SCHEMA_MAJOR_INCOMPATIBLE = "ARTIFACT_SCHEMA_MAJOR_INCOMPATIBLE"
    ARTIFACT_SCHEMA_MINOR_UNSUPPORTED = "ARTIFACT_SCHEMA_MINOR_UNSUPPORTED"
    FEATURE_SET_UNKNOWN = "FEATURE_SET_UNKNOWN"
    FEATURE_SET_INCOMPATIBLE = "FEATURE_SET_INCOMPATIBLE"
    TRANSFORM_SET_UNKNOWN = "TRANSFORM_SET_UNKNOWN"
    TRANSFORM_SET_INCOMPATIBLE = "TRANSFORM_SET_INCOMPATIBLE"
    ARTIFACT_REQUIRES_MIGRATION = "ARTIFACT_REQUIRES_MIGRATION"
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    KEY_ID_UNKNOWN = "KEY_ID_UNKNOWN"
    KEY_REVOKED = "KEY_REVOKED"
    PAYLOAD_HASH_MISMATCH = "PAYLOAD_HASH_MISMATCH"
    TRUST_STORE_UNAVAILABLE = "TRUST_STORE_UNAVAILABLE"


class ArtifactCompatibilityEntry(BaseModel, frozen=True):
    """Minimal VPS compatibility registry entry for governed artifact intake."""

    artifact_schema_version: str = Field(..., min_length=1)
    feature_set_version: str = Field(..., min_length=1)
    transform_set_version: str = Field(..., min_length=1)
    status: ArtifactCompatibilityStatus
    activated_on: date
    support_end_on: date | None = None
    migration_note: str = ""

    @model_validator(mode="after")
    def validate_window(self) -> "ArtifactCompatibilityEntry":
        if self.support_end_on is not None and self.support_end_on < self.activated_on:
            raise ValueError("ArtifactCompatibilityEntry support_end_on must be >= activated_on")
        return self


class ArtifactSignatureEnvelope(BaseModel, frozen=True):
    """Minimal signature envelope carried by a governed artifact bundle."""

    key_id: str = Field(..., min_length=1)
    public_key_author_sig: str = Field(..., min_length=1)
    payload_hash_sha256: str = Field(..., min_length=1)


class ArtifactTrustStoreEntry(BaseModel, frozen=True):
    """Minimal trusted public-key registry entry used by VPS/control-plane checks."""

    key_id: str = Field(..., min_length=1)
    public_key: str = Field(..., min_length=1)
    status: ArtifactTrustKeyStatus
    activated_on: date
    revoked_on: date | None = None
    operator_note: str = ""

    @model_validator(mode="after")
    def validate_status_window(self) -> "ArtifactTrustStoreEntry":
        if self.revoked_on is not None and self.revoked_on < self.activated_on:
            raise ValueError("ArtifactTrustStoreEntry revoked_on must be >= activated_on")
        if self.status == ArtifactTrustKeyStatus.REVOKED and self.revoked_on is None:
            raise ValueError("ArtifactTrustStoreEntry REVOKED keys require revoked_on")
        if self.status != ArtifactTrustKeyStatus.REVOKED and self.revoked_on is not None:
            raise ValueError("ArtifactTrustStoreEntry revoked_on is only valid for REVOKED keys")
        return self


class ArtifactConflictPolicy(BaseModel, frozen=True):
    """Canonical VPS-side policy for resolving multiple active artifact actions."""

    resolution_mode: ArtifactConflictResolutionMode = (
        ArtifactConflictResolutionMode.NO_TRADE_THEN_STRICTEST
    )
    hard_veto_action: ArtifactActionKind = ArtifactActionKind.NO_TRADE
    score_aggregation_mode: ScoreConflictAggregationMode = (
        ScoreConflictAggregationMode.BOUNDED_SUM_WITH_GLOBAL_CAP
    )
    size_reduce_mode: SizeReduceConflictMode = SizeReduceConflictMode.MIN_FACTOR_WINS
    rank_adjust_mode: RankAdjustConflictMode = RankAdjustConflictMode.BOUNDED_SUM
    aggregate_raw_score_cap_scope: str = "per_hook_total"
    additive_soft_boosts_allowed: bool = True
    additive_soft_reduces_allowed: bool = True

    @model_validator(mode="after")
    def validate_hard_veto(self) -> "ArtifactConflictPolicy":
        if self.hard_veto_action != ArtifactActionKind.NO_TRADE:
            raise ValueError("ArtifactConflictPolicy hard_veto_action must be NO_TRADE")
        return self


class CompiledArtifactRegistryPolicy(BaseModel, frozen=True):
    """Canonical atomicity/concurrency policy for compiled artifact publication."""

    atomicity_mode: CompiledRegistryAtomicityMode = (
        CompiledRegistryAtomicityMode.ATOMIC_SNAPSHOT_SWAP
    )
    concurrency_model: CompiledRegistryConcurrencyModel = (
        CompiledRegistryConcurrencyModel.SINGLE_WRITER_MULTI_READER
    )
    publish_requires_atomic_replace: bool = True
    publish_requires_fsync: bool = True
    rollback_to_last_known_good: bool = True
    in_flight_reads_use_snapshot: bool = True


class DistilledRuleCondition(BaseModel, frozen=True):
    """Typed RULE_AST_JSON condition contract aligned with the blueprint."""

    condition_id: str = Field(..., min_length=1)
    feature_id: str = Field(..., min_length=1)
    operator: DistilledRuleOperator
    threshold: float | None = None
    lower_threshold: float | None = None
    upper_threshold: float | None = None

    @model_validator(mode="after")
    def validate_threshold_shape(self) -> "DistilledRuleCondition":
        if self.operator == DistilledRuleOperator.IN_RANGE:
            if self.threshold is not None:
                raise ValueError("IN_RANGE conditions must not declare threshold")
            if self.lower_threshold is None or self.upper_threshold is None:
                raise ValueError(
                    "IN_RANGE conditions require lower_threshold and upper_threshold"
                )
            if self.lower_threshold > self.upper_threshold:
                raise ValueError(
                    "IN_RANGE conditions require lower_threshold <= upper_threshold"
                )
            return self
        if self.threshold is None:
            raise ValueError("Scalar rule conditions require threshold")
        if self.lower_threshold is not None or self.upper_threshold is not None:
            raise ValueError(
                "Scalar rule conditions must not declare lower/upper thresholds"
            )
        return self


class DistilledRuleAction(BaseModel, frozen=True):
    """Typed RULE_AST_JSON action contract using the closed runtime vocabulary."""

    action: ArtifactActionKind
    action_value: float = 0.0
    action_unit: ActionUnit | None = None
    max_raw_score_cap: float | None = None
    min_floor: float | None = None
    reason_code: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_action_shape(self) -> "DistilledRuleAction":
        if self.action == ArtifactActionKind.NO_TRADE:
            if self.action_unit is not None:
                raise ValueError("NO_TRADE actions must not declare action_unit")
            if self.action_value != 0.0:
                raise ValueError("NO_TRADE actions must keep action_value=0.0")
            return self
        if self.action == ArtifactActionKind.SIZE_REDUCE:
            if self.action_unit != ActionUnit.SIZE_FACTOR:
                raise ValueError("SIZE_REDUCE actions require action_unit=SIZE_FACTOR")
            return self
        if self.action == ArtifactActionKind.RANK_ADJUST:
            if self.action_unit != ActionUnit.RANK_DELTA:
                raise ValueError("RANK_ADJUST actions require action_unit=RANK_DELTA")
            return self
        if self.action_unit not in {
            ActionUnit.RAW_SCORE_MULTIPLIER,
            ActionUnit.RAW_SCORE_ADD,
            ActionUnit.CONVICTION_ADD,
        }:
            raise ValueError(
                "SOFT_BOOST/SOFT_REDUCE actions require score-oriented action units"
            )
        return self


class DistilledRule(BaseModel, frozen=True):
    """Typed RULE_AST_JSON rule node."""

    rule_id: str = Field(..., min_length=1)
    logical_op: DistilledRuleLogicalOp = DistilledRuleLogicalOp.AND
    conditions: tuple[DistilledRuleCondition, ...]
    action: DistilledRuleAction
    support_count: int = Field(..., ge=1)
    fragility_score: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_conditions(self) -> "DistilledRule":
        if not self.conditions:
            raise ValueError("DistilledRule requires at least one condition")
        return self


class ArtifactProofSummary(BaseModel, frozen=True):
    """Typed proof/protocol summary carried by an exported governed artifact."""

    anti_cowardice_pass: bool
    friction_regret_pass: bool
    walk_forward_pass: bool
    regime_segmentation_pass: bool
    operational_burden_pass: bool
    capital_efficiency_pass: bool | None = None
    ablation_delta_net_pnl: float
    ablation_delta_ce: float | None = None
    friction_regret_value: float
    block_rate_delta: float


class ArtifactProofFloorPolicy(BaseModel, frozen=True):
    """Canonical quantitative floors for governed artifact proof summaries."""

    require_anti_cowardice_pass: bool = True
    require_friction_regret_pass: bool = True
    require_walk_forward_pass: bool = True
    require_regime_segmentation_pass: bool = True
    require_operational_burden_pass: bool = True
    require_capital_efficiency_when_present: bool = True
    min_ablation_delta_net_pnl: float = 0.01
    min_ablation_delta_ce: float = 0.0
    max_friction_regret_value: float = 0.05
    max_block_rate_delta: float = 0.10


class ArtifactRuntimeErrorPolicy(BaseModel, frozen=True):
    """Bounded runtime error policy for artifact influence on the open VPS rail."""

    selection_failure_mode: ArtifactRuntimeFailureMode = (
        ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
    )
    payload_load_failure_mode: ArtifactRuntimeFailureMode = (
        ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
    )
    hook_execution_failure_mode: ArtifactRuntimeFailureMode = (
        ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
    )


class ArtifactLifecyclePolicy(BaseModel, frozen=True):
    """Typed lifecycle policy attached to an exported artifact bundle."""

    ttl_max_days: int = Field(..., ge=1)
    rule_half_life_days: int = Field(..., ge=1)


@unique
class ArtifactTtlStatus(str, Enum):
    """Bounded lifecycle TTL status for governed artifact evaluation."""

    MISSING_POLICY = "missing_policy"
    MISSING_REFERENCE_DATE = "missing_reference_date"
    ACTIVE = "active"
    EXPIRED = "expired"


@unique
class ArtifactDriftStatus(str, Enum):
    """Bounded drift-policy status for governed artifact evaluation."""

    MISSING_THRESHOLD = "missing_threshold"
    NOT_OBSERVED = "not_observed"
    WITHIN_THRESHOLD = "within_threshold"
    EXCEEDED = "exceeded"


class ArtifactRuntimeGovernanceEvaluation(BaseModel, frozen=True):
    """Typed runtime governance evaluation for TTL and drift policy."""

    ttl_status: ArtifactTtlStatus
    ttl_reasons: tuple[str, ...] = ()
    drift_status: ArtifactDriftStatus
    drift_reasons: tuple[str, ...] = ()
    derived_health_state: ArtifactHealthState = ArtifactHealthState.ACTIVE


class ArtifactExportBundle(BaseModel, frozen=True):
    """Typed governed artifact export bundle aligned with the blueprint/canon."""

    artifact_id: str = Field(..., min_length=1)
    artifact_version: str = Field(..., min_length=1)
    artifact_class: ArtifactClass
    artifact_scope: str = Field(..., min_length=1)
    allowed_hook_ids: tuple[HookId, ...] = ()
    allowed_action_kinds: tuple[ArtifactActionKind, ...] = ()
    allowed_action_units: tuple[ActionUnit, ...] = ()
    distilled_logic_format: ArtifactLogicFormat
    rules: tuple[DistilledRule, ...] = ()
    payload_hash_sha256: str = Field(..., min_length=1)
    public_key_author_sig: str = Field(..., min_length=1)
    dataset_id: str = Field(..., min_length=1)
    feature_set_version: str = Field(..., min_length=1)
    transform_set_version: str = Field(..., min_length=1)
    feature_lineage_lock: FeatureLineageLock
    transform_whitelist_lock: TransformWhitelistLock
    training_start: date
    training_end: date
    lifecycle_policy: ArtifactLifecyclePolicy
    regime_features_used: tuple[str, ...] = ()
    covariance_shrinkage_matrix_ref: str = Field(..., min_length=1)
    drift_score_threshold: float
    proof_summary: ArtifactProofSummary

    @model_validator(mode="after")
    def validate_bundle(self) -> "ArtifactExportBundle":
        if self.training_end < self.training_start:
            raise ValueError("ArtifactExportBundle training_end must be >= training_start")
        if len(set(self.allowed_hook_ids)) != len(self.allowed_hook_ids):
            raise ValueError("ArtifactExportBundle allowed_hook_ids must be unique")
        if len(set(self.allowed_action_kinds)) != len(self.allowed_action_kinds):
            raise ValueError("ArtifactExportBundle allowed_action_kinds must be unique")
        if len(set(self.allowed_action_units)) != len(self.allowed_action_units):
            raise ValueError("ArtifactExportBundle allowed_action_units must be unique")
        if self.distilled_logic_format == ArtifactLogicFormat.RULE_AST_JSON and not self.rules:
            raise ValueError("RULE_AST_JSON bundles require at least one rule")
        if self.feature_lineage_lock.feature_set_version != self.feature_set_version:
            raise ValueError(
                "ArtifactExportBundle feature_lineage_lock.feature_set_version must match feature_set_version"
            )
        if self.feature_lineage_lock.transform_set_version != self.transform_set_version:
            raise ValueError(
                "ArtifactExportBundle feature_lineage_lock.transform_set_version must match transform_set_version"
            )
        if (
            self.transform_whitelist_lock.transform_set_version
            != self.transform_set_version
        ):
            raise ValueError(
                "ArtifactExportBundle transform_whitelist_lock.transform_set_version must match transform_set_version"
            )
        expected_feature_ids = tuple(
            dict.fromkeys(
                (
                    *(condition.feature_id for rule in self.rules for condition in rule.conditions),
                    *self.regime_features_used,
                )
            )
        )
        lineage_reasons = validate_feature_lineage_lock(
            expected_feature_ids,
            self.feature_lineage_lock,
        )
        if lineage_reasons:
            raise ValueError(
                "ArtifactExportBundle feature_lineage_lock is incomplete: "
                + "; ".join(lineage_reasons)
            )
        expected_transform_ids = tuple(
            dict.fromkeys(
                transform_id
                for record in self.feature_lineage_lock.records
                for transform_id in record.transform_ids
            )
        )
        whitelist_reasons = validate_transform_whitelist_lock(
            expected_transform_ids,
            self.transform_whitelist_lock,
        )
        if whitelist_reasons:
            raise ValueError(
                "ArtifactExportBundle transform_whitelist_lock is incomplete: "
                + "; ".join(whitelist_reasons)
            )
        return self


__all__ = [
    "ActionUnit",
    "ArtifactActivationStage",
    "ArtifactActionKind",
    "ArtifactClass",
    "ArtifactCompatibilityEntry",
    "ArtifactCompatibilityStatus",
    "ArtifactConflictPolicy",
    "ArtifactConflictResolutionMode",
    "ArtifactDriftStatus",
    "ArtifactExportBundle",
    "ArtifactHealthState",
    "ArtifactLifecyclePolicy",
    "ArtifactLogicFormat",
    "ArtifactPolicyErrorCode",
    "ArtifactProofFloorPolicy",
    "ArtifactProofSummary",
    "ArtifactRuntimeErrorPolicy",
    "ArtifactRuntimeFailureMode",
    "ArtifactRuntimeFailureStage",
    "ArtifactRuntimeGovernanceEvaluation",
    "ArtifactSignatureEnvelope",
    "ArtifactTrustKeyStatus",
    "ArtifactTrustStoreEntry",
    "ArtifactTtlStatus",
    "CompiledArtifactRegistryPolicy",
    "CompiledRegistryAtomicityMode",
    "CompiledRegistryConcurrencyModel",
    "DistilledRule",
    "DistilledRuleAction",
    "DistilledRuleCondition",
    "DistilledRuleLogicalOp",
    "DistilledRuleOperator",
    "HookId",
    "RankAdjustConflictMode",
    "ScoreConflictAggregationMode",
    "SizeReduceConflictMode",
]
