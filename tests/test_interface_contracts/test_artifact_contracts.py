from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from interface_contracts import (
    ActionUnit,
    ArtifactActionKind,
    ArtifactClass,
    ArtifactCompatibilityEntry,
    ArtifactCompatibilityStatus,
    ArtifactConflictResolutionMode,
    ArtifactConflictPolicy,
    ArtifactExportBundle,
    ArtifactLifecyclePolicy,
    ArtifactPolicyErrorCode,
    ArtifactProofFloorPolicy,
    ArtifactProofSummary,
    ArtifactSignatureEnvelope,
    ArtifactDriftStatus,
    ArtifactRuntimeGovernanceEvaluation,
    ArtifactTrustKeyStatus,
    ArtifactTrustStoreEntry,
    ArtifactTtlStatus,
    CANONICAL_ARTIFACT_CONFLICT_POLICY,
    CANONICAL_COMPILED_ARTIFACT_REGISTRY_POLICY,
    CANONICAL_ARTIFACT_PROOF_FLOOR_POLICY,
    CompiledRegistryAtomicityMode,
    CompiledRegistryConcurrencyModel,
    DistilledRule,
    DistilledRuleAction,
    DistilledRuleCondition,
    DistilledRuleLogicalOp,
    DistilledRuleOperator,
    FeatureLineageLock,
    FeatureLineageRecord,
    HookId,
    HOOK_MODULE_BY_ID,
    PhysicsFeatureFamily,
    TransformWhitelistLock,
    TransformWhitelistId,
    evaluate_artifact_runtime_governance,
    validate_artifact_proof_summary,
)


def test_hook_module_mapping_is_complete_for_canonical_hooks():
    assert HOOK_MODULE_BY_ID[HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION] == "engine_a_hooks.py"
    assert HOOK_MODULE_BY_ID[HookId.EXECUTION_NO_TRADE_FILTER] == "execution_hooks.py"


def test_artifact_policy_error_codes_cover_schema_transform_and_signature_failures():
    assert ArtifactPolicyErrorCode.ARTIFACT_SCHEMA_UNKNOWN.value == "ARTIFACT_SCHEMA_UNKNOWN"
    assert ArtifactPolicyErrorCode.TRANSFORM_SET_UNKNOWN.value == "TRANSFORM_SET_UNKNOWN"
    assert ArtifactPolicyErrorCode.KEY_REVOKED.value == "KEY_REVOKED"


def test_artifact_compatibility_entry_accepts_supported_window():
    entry = ArtifactCompatibilityEntry(
        artifact_schema_version="1.0.0",
        feature_set_version="1.2.0",
        transform_set_version="1.1.0",
        status=ArtifactCompatibilityStatus.SUPPORTED,
        activated_on=date(2026, 4, 5),
    )

    assert entry.status == ArtifactCompatibilityStatus.SUPPORTED


def test_artifact_compatibility_entry_rejects_inverted_window():
    with pytest.raises(ValidationError):
        ArtifactCompatibilityEntry(
            artifact_schema_version="1.0.0",
            feature_set_version="1.2.0",
            transform_set_version="1.1.0",
            status=ArtifactCompatibilityStatus.DEPRECATED,
            activated_on=date(2026, 4, 5),
            support_end_on=date(2026, 4, 4),
        )


def test_artifact_signature_envelope_requires_three_traceable_fields():
    envelope = ArtifactSignatureEnvelope(
        key_id="lab_ed25519_2026_q2_k1",
        public_key_author_sig="sig",
        payload_hash_sha256="hash",
    )

    assert envelope.key_id == "lab_ed25519_2026_q2_k1"


def test_artifact_trust_store_entry_enforces_revoked_window_rules():
    with pytest.raises(ValidationError):
        ArtifactTrustStoreEntry(
            key_id="lab_ed25519_2026_q2_k1",
            public_key="pub",
            status=ArtifactTrustKeyStatus.REVOKED,
            activated_on=date(2026, 4, 5),
        )

    with pytest.raises(ValidationError):
        ArtifactTrustStoreEntry(
            key_id="lab_ed25519_2026_q2_k1",
            public_key="pub",
            status=ArtifactTrustKeyStatus.ACTIVE,
            activated_on=date(2026, 4, 5),
            revoked_on=date(2026, 4, 6),
        )


def test_artifact_trust_store_entry_accepts_revoked_key_with_date():
    entry = ArtifactTrustStoreEntry(
        key_id="lab_ed25519_2026_q2_k1",
        public_key="pub",
        status=ArtifactTrustKeyStatus.REVOKED,
        activated_on=date(2026, 4, 5),
        revoked_on=date(2026, 4, 6),
        operator_note="suspected compromise",
    )

    assert entry.status == ArtifactTrustKeyStatus.REVOKED


def test_action_unit_vocabulary_remains_bounded():
    assert ActionUnit.RAW_SCORE_MULTIPLIER.value == "raw_score_multiplier"


def test_canonical_artifact_conflict_policy_is_explicit_and_no_trade_first():
    assert (
        CANONICAL_ARTIFACT_CONFLICT_POLICY.resolution_mode
        == ArtifactConflictResolutionMode.NO_TRADE_THEN_STRICTEST
    )
    assert (
        CANONICAL_ARTIFACT_CONFLICT_POLICY.hard_veto_action
        == ArtifactActionKind.NO_TRADE
    )


def test_artifact_conflict_policy_rejects_non_no_trade_hard_veto():
    with pytest.raises(ValidationError):
        ArtifactConflictPolicy(hard_veto_action=ArtifactActionKind.SOFT_BOOST)


def test_canonical_compiled_registry_policy_is_atomic_snapshot_based():
    assert (
        CANONICAL_COMPILED_ARTIFACT_REGISTRY_POLICY.atomicity_mode
        == CompiledRegistryAtomicityMode.ATOMIC_SNAPSHOT_SWAP
    )
    assert (
        CANONICAL_COMPILED_ARTIFACT_REGISTRY_POLICY.concurrency_model
        == CompiledRegistryConcurrencyModel.SINGLE_WRITER_MULTI_READER
    )
    assert CANONICAL_COMPILED_ARTIFACT_REGISTRY_POLICY.rollback_to_last_known_good is True


def test_distilled_rule_condition_supports_single_threshold_and_range_shapes():
    scalar = DistilledRuleCondition(
        condition_id="SWEEP_GT",
        feature_id="sweep_score_1m",
        operator=DistilledRuleOperator.GT,
        threshold=0.82,
    )
    ranged = DistilledRuleCondition(
        condition_id="TOX_RANGE",
        feature_id="toxicity_score_1m",
        operator=DistilledRuleOperator.IN_RANGE,
        lower_threshold=0.2,
        upper_threshold=0.6,
    )

    assert scalar.threshold == 0.82
    assert ranged.lower_threshold == 0.2


def test_distilled_rule_action_rejects_invalid_no_trade_shape():
    with pytest.raises(ValidationError):
        DistilledRuleAction(
            action=ArtifactActionKind.NO_TRADE,
            action_value=0.1,
            reason_code="BLOCK",
        )


def test_distilled_rule_supports_single_condition_with_default_and():
    rule = DistilledRule(
        rule_id="rule_1",
        conditions=(
            DistilledRuleCondition(
                condition_id="SWEEP_GT",
                feature_id="sweep_score_1m",
                operator=DistilledRuleOperator.GT,
                threshold=0.82,
            ),
        ),
        action=DistilledRuleAction(
            action=ArtifactActionKind.SOFT_BOOST,
            action_value=0.15,
            action_unit=ActionUnit.RAW_SCORE_MULTIPLIER,
            max_raw_score_cap=2.5,
            reason_code="PHYSICS_B_SWEEP_FADE_BOOST",
        ),
        support_count=18,
        fragility_score=0.2,
    )

    assert rule.logical_op == DistilledRuleLogicalOp.AND
    assert rule.support_count == 18


def test_canonical_artifact_proof_floor_policy_is_bounded_and_explicit():
    assert isinstance(CANONICAL_ARTIFACT_PROOF_FLOOR_POLICY, ArtifactProofFloorPolicy)
    assert CANONICAL_ARTIFACT_PROOF_FLOOR_POLICY.min_ablation_delta_net_pnl == 0.01
    assert CANONICAL_ARTIFACT_PROOF_FLOOR_POLICY.max_friction_regret_value == 0.05


def test_validate_artifact_proof_summary_accepts_canonical_good_proof():
    proof = ArtifactProofSummary(
        anti_cowardice_pass=True,
        friction_regret_pass=True,
        walk_forward_pass=True,
        regime_segmentation_pass=True,
        operational_burden_pass=True,
        capital_efficiency_pass=True,
        ablation_delta_net_pnl=0.12,
        ablation_delta_ce=0.03,
        friction_regret_value=0.01,
        block_rate_delta=0.02,
    )

    assert validate_artifact_proof_summary(proof) == ()


def test_validate_artifact_proof_summary_rejects_weak_proof():
    proof = ArtifactProofSummary(
        anti_cowardice_pass=False,
        friction_regret_pass=True,
        walk_forward_pass=True,
        regime_segmentation_pass=True,
        operational_burden_pass=True,
        capital_efficiency_pass=False,
        ablation_delta_net_pnl=0.0,
        ablation_delta_ce=None,
        friction_regret_value=0.08,
        block_rate_delta=0.12,
    )

    assert validate_artifact_proof_summary(proof) == (
        "PROOF_ANTI_COWARDICE_REQUIRED",
        "PROOF_CAPITAL_EFFICIENCY_REQUIRED",
        "PROOF_ABLATION_DELTA_NET_PNL_TOO_LOW",
        "PROOF_ABLATION_DELTA_CE_REQUIRED",
        "PROOF_FRICTION_REGRET_TOO_HIGH",
        "PROOF_BLOCK_RATE_DELTA_TOO_HIGH",
    )


def test_evaluate_artifact_runtime_governance_accepts_active_ttl_and_unobserved_drift():
    evaluation = evaluate_artifact_runtime_governance(
        training_end=date(2026, 4, 1),
        lifecycle_policy=ArtifactLifecyclePolicy(ttl_max_days=30, rule_half_life_days=7),
        governance_reference_date=date(2026, 4, 6),
        drift_score_threshold=0.85,
        observed_drift_score=None,
    )

    assert isinstance(evaluation, ArtifactRuntimeGovernanceEvaluation)
    assert evaluation.ttl_status == ArtifactTtlStatus.ACTIVE
    assert evaluation.ttl_reasons == ()
    assert evaluation.drift_status == ArtifactDriftStatus.NOT_OBSERVED
    assert evaluation.drift_reasons == ()


def test_evaluate_artifact_runtime_governance_rejects_expired_ttl_and_excessive_drift():
    evaluation = evaluate_artifact_runtime_governance(
        training_end=date(2026, 1, 1),
        lifecycle_policy=ArtifactLifecyclePolicy(ttl_max_days=30, rule_half_life_days=7),
        governance_reference_date=date(2026, 4, 6),
        drift_score_threshold=0.85,
        observed_drift_score=0.90,
    )

    assert evaluation.ttl_status == ArtifactTtlStatus.EXPIRED
    assert evaluation.ttl_reasons == ("ARTIFACT_TTL_EXPIRED",)
    assert evaluation.drift_status == ArtifactDriftStatus.EXCEEDED
    assert evaluation.drift_reasons == ("ARTIFACT_DRIFT_THRESHOLD_EXCEEDED",)


def test_artifact_export_bundle_aligns_rule_ast_shape_with_proof_and_lifecycle():
    bundle = ArtifactExportBundle(
        artifact_id="ART_B_SWEEP_FADE_V1",
        artifact_version="1.0.0",
        artifact_class=ArtifactClass.DAMAGE_REDUCER,
        artifact_scope="engine_b:sweep_fade",
        allowed_hook_ids=(HookId.ENGINE_B_SWEEP_VALIDATION,),
        allowed_action_kinds=(ArtifactActionKind.SOFT_BOOST,),
        allowed_action_units=(ActionUnit.RAW_SCORE_MULTIPLIER,),
        distilled_logic_format="rule_ast_json",
        rules=(
            DistilledRule(
                rule_id="rule_1",
                logical_op=DistilledRuleLogicalOp.AND,
                conditions=(
                    DistilledRuleCondition(
                        condition_id="SWEEP_GT",
                        feature_id="sweep_score_1m",
                        operator=DistilledRuleOperator.GT,
                        threshold=0.82,
                    ),
                ),
                action=DistilledRuleAction(
                    action=ArtifactActionKind.SOFT_BOOST,
                    action_value=0.15,
                    action_unit=ActionUnit.RAW_SCORE_MULTIPLIER,
                    max_raw_score_cap=2.5,
                    reason_code="PHYSICS_B_SWEEP_FADE_BOOST",
                ),
                support_count=12,
                fragility_score=0.15,
            ),
        ),
        payload_hash_sha256="hash",
        public_key_author_sig="sig",
        dataset_id="dataset-1",
        feature_set_version="1.0.0",
        transform_set_version="1.0.0",
        feature_lineage_lock=FeatureLineageLock(
            records=(
                FeatureLineageRecord(
                    feature_id="sweep_score_1m",
                    family=PhysicsFeatureFamily.SWEEP_SCORE,
                    source_inputs=("wick_ratio", "vol_burst", "reject_indicator"),
                    transform_ids=(TransformWhitelistId.SWEEP_SCORE_V1,),
                ),
                FeatureLineageRecord(
                    feature_id="sweep_score",
                    family=PhysicsFeatureFamily.SWEEP_SCORE,
                    upstream_feature_ids=("sweep_score_1m",),
                    transform_ids=(TransformWhitelistId.CLIP01,),
                ),
                FeatureLineageRecord(
                    feature_id="spread_regime",
                    family=PhysicsFeatureFamily.SPREAD_REGIME,
                    source_inputs=("bid", "ask", "mid"),
                    transform_ids=(TransformWhitelistId.ZPLUS,),
                ),
            )
        ),
        transform_whitelist_lock=TransformWhitelistLock(
            allowed_transform_ids=(
                TransformWhitelistId.SWEEP_SCORE_V1,
                TransformWhitelistId.CLIP01,
                TransformWhitelistId.ZPLUS,
            )
        ),
        training_start=date(2025, 1, 1),
        training_end=date(2025, 12, 31),
        lifecycle_policy=ArtifactLifecyclePolicy(ttl_max_days=30, rule_half_life_days=7),
        regime_features_used=("spread_regime", "sweep_score"),
        covariance_shrinkage_matrix_ref="matrix_ref_or_embedded_blob",
        drift_score_threshold=0.85,
        proof_summary=ArtifactProofSummary(
            anti_cowardice_pass=True,
            friction_regret_pass=True,
            walk_forward_pass=True,
            regime_segmentation_pass=True,
            operational_burden_pass=True,
            capital_efficiency_pass=True,
            ablation_delta_net_pnl=0.12,
            ablation_delta_ce=0.03,
            friction_regret_value=0.01,
            block_rate_delta=0.02,
        ),
    )

    assert bundle.distilled_logic_format.value == "rule_ast_json"
    assert bundle.lifecycle_policy.ttl_max_days == 30


def test_artifact_export_bundle_rejects_missing_feature_lineage_coverage():
    with pytest.raises(ValidationError, match="feature_lineage_lock is incomplete"):
        ArtifactExportBundle(
            artifact_id="ART_B_SWEEP_FADE_V1",
            artifact_version="1.0.0",
            artifact_class=ArtifactClass.DAMAGE_REDUCER,
            artifact_scope="engine_b:sweep_fade",
            allowed_hook_ids=(HookId.ENGINE_B_SWEEP_VALIDATION,),
            allowed_action_kinds=(ArtifactActionKind.SOFT_BOOST,),
            allowed_action_units=(ActionUnit.RAW_SCORE_MULTIPLIER,),
            distilled_logic_format="rule_ast_json",
            rules=(
                DistilledRule(
                    rule_id="rule_1",
                    conditions=(
                        DistilledRuleCondition(
                            condition_id="SWEEP_GT",
                            feature_id="sweep_score_1m",
                            operator=DistilledRuleOperator.GT,
                            threshold=0.82,
                        ),
                    ),
                    action=DistilledRuleAction(
                        action=ArtifactActionKind.SOFT_BOOST,
                        action_value=0.15,
                        action_unit=ActionUnit.RAW_SCORE_MULTIPLIER,
                        reason_code="PHYSICS_B_SWEEP_FADE_BOOST",
                    ),
                    support_count=12,
                    fragility_score=0.15,
                ),
            ),
            payload_hash_sha256="hash",
            public_key_author_sig="sig",
            dataset_id="dataset-1",
            feature_set_version="1.0.0",
            transform_set_version="1.0.0",
            feature_lineage_lock=FeatureLineageLock(records=()),
            transform_whitelist_lock=TransformWhitelistLock(
                allowed_transform_ids=(TransformWhitelistId.SWEEP_SCORE_V1,)
            ),
            training_start=date(2025, 1, 1),
            training_end=date(2025, 12, 31),
            lifecycle_policy=ArtifactLifecyclePolicy(ttl_max_days=30, rule_half_life_days=7),
            covariance_shrinkage_matrix_ref="matrix_ref_or_embedded_blob",
            drift_score_threshold=0.85,
            proof_summary=ArtifactProofSummary(
                anti_cowardice_pass=True,
                friction_regret_pass=True,
                walk_forward_pass=True,
                regime_segmentation_pass=True,
                operational_burden_pass=True,
                ablation_delta_net_pnl=0.12,
                friction_regret_value=0.01,
                block_rate_delta=0.02,
            ),
        )


def test_artifact_export_bundle_rejects_incomplete_transform_whitelist_coverage():
    with pytest.raises(ValidationError, match="transform_whitelist_lock is incomplete"):
        ArtifactExportBundle(
            artifact_id="ART_B_SWEEP_FADE_V1",
            artifact_version="1.0.0",
            artifact_class=ArtifactClass.DAMAGE_REDUCER,
            artifact_scope="engine_b:sweep_fade",
            allowed_hook_ids=(HookId.ENGINE_B_SWEEP_VALIDATION,),
            allowed_action_kinds=(ArtifactActionKind.SOFT_BOOST,),
            allowed_action_units=(ActionUnit.RAW_SCORE_MULTIPLIER,),
            distilled_logic_format="rule_ast_json",
            rules=(
                DistilledRule(
                    rule_id="rule_1",
                    conditions=(
                        DistilledRuleCondition(
                            condition_id="SWEEP_GT",
                            feature_id="sweep_score_1m",
                            operator=DistilledRuleOperator.GT,
                            threshold=0.82,
                        ),
                    ),
                    action=DistilledRuleAction(
                        action=ArtifactActionKind.SOFT_BOOST,
                        action_value=0.15,
                        action_unit=ActionUnit.RAW_SCORE_MULTIPLIER,
                        reason_code="PHYSICS_B_SWEEP_FADE_BOOST",
                    ),
                    support_count=12,
                    fragility_score=0.15,
                ),
            ),
            payload_hash_sha256="hash",
            public_key_author_sig="sig",
            dataset_id="dataset-1",
            feature_set_version="1.0.0",
            transform_set_version="1.0.0",
            feature_lineage_lock=FeatureLineageLock(
                records=(
                    FeatureLineageRecord(
                        feature_id="sweep_score_1m",
                        family=PhysicsFeatureFamily.SWEEP_SCORE,
                        source_inputs=("wick_ratio", "vol_burst", "reject_indicator"),
                        transform_ids=(TransformWhitelistId.SWEEP_SCORE_V1,),
                    ),
                )
            ),
            transform_whitelist_lock=TransformWhitelistLock(
                allowed_transform_ids=(TransformWhitelistId.CLIP01,)
            ),
            training_start=date(2025, 1, 1),
            training_end=date(2025, 12, 31),
            lifecycle_policy=ArtifactLifecyclePolicy(ttl_max_days=30, rule_half_life_days=7),
            covariance_shrinkage_matrix_ref="matrix_ref_or_embedded_blob",
            drift_score_threshold=0.85,
            proof_summary=ArtifactProofSummary(
                anti_cowardice_pass=True,
                friction_regret_pass=True,
                walk_forward_pass=True,
                regime_segmentation_pass=True,
                operational_burden_pass=True,
                ablation_delta_net_pnl=0.12,
                friction_regret_value=0.01,
                block_rate_delta=0.02,
            ),
        )
