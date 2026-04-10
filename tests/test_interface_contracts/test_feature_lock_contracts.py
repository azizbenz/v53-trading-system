from __future__ import annotations

import pytest
from pydantic import ValidationError

from interface_contracts import (
    CANONICAL_FEATURE_SET_VERSION,
    CANONICAL_PHYSICS_FEATURE_DICTIONARY,
    CANONICAL_TRANSFORM_SET_VERSION,
    CANONICAL_TRANSFORM_WHITELIST,
    FeatureLineageLock,
    FeatureLineageRecord,
    PhysicsFeatureFamily,
    TransformWhitelistLock,
    TransformWhitelistId,
    validate_feature_lineage_lock,
    validate_transform_whitelist_lock,
)


def test_feature_lock_exports_minimal_canonical_dictionary_and_whitelist():
    assert CANONICAL_FEATURE_SET_VERSION == "1.0.0"
    assert CANONICAL_TRANSFORM_SET_VERSION == "1.0.0"
    assert "delta_proxy_soft_1m" in CANONICAL_PHYSICS_FEATURE_DICTIONARY
    assert "delta_confirmation" in CANONICAL_PHYSICS_FEATURE_DICTIONARY
    assert "micro_friction_score" in CANONICAL_PHYSICS_FEATURE_DICTIONARY
    assert TransformWhitelistId.CLIP01 in CANONICAL_TRANSFORM_WHITELIST
    assert TransformWhitelistId.DELTA_CONFIRMATION_V1 in CANONICAL_TRANSFORM_WHITELIST
    assert TransformWhitelistId.MICRO_FRICTION_SCORE_V1 in CANONICAL_TRANSFORM_WHITELIST


def test_feature_lineage_record_rejects_missing_lineage_inputs():
    with pytest.raises(ValidationError, match="requires source_inputs or upstream_feature_ids"):
        FeatureLineageRecord(
            feature_id="delta_proxy_soft_1m",
            family=PhysicsFeatureFamily.DELTA_PROXY,
            transform_ids=(TransformWhitelistId.DELTA_PROXY_SOFT,),
        )


def test_feature_lineage_record_rejects_family_drift_for_canonical_feature():
    with pytest.raises(
        ValidationError,
        match="family must match the canonical feature dictionary",
    ):
        FeatureLineageRecord(
            feature_id="sweep_score",
            family=PhysicsFeatureFamily.VOID_SCORE,
            source_inputs=("wick_ratio", "vol_burst", "reject_indicator"),
            transform_ids=(TransformWhitelistId.SWEEP_SCORE_V1,),
        )


def test_feature_lineage_lock_requires_consistent_versions():
    record = FeatureLineageRecord(
        feature_id="delta_proxy_soft_1m",
        family=PhysicsFeatureFamily.DELTA_PROXY,
        source_inputs=("open", "high", "low", "close", "volume"),
        transform_ids=(TransformWhitelistId.DELTA_PROXY_SOFT,),
        feature_set_version="2.0.0",
        transform_set_version=CANONICAL_TRANSFORM_SET_VERSION,
    )

    with pytest.raises(
        ValidationError,
        match="feature_set_version must match record feature_set_version",
    ):
        FeatureLineageLock(
            feature_set_version=CANONICAL_FEATURE_SET_VERSION,
            transform_set_version=CANONICAL_TRANSFORM_SET_VERSION,
            records=(record,),
        )


def test_validate_feature_lineage_lock_reports_missing_coverage():
    lineage_lock = FeatureLineageLock(
        records=(
            FeatureLineageRecord(
                feature_id="delta_proxy_soft_1m",
                family=PhysicsFeatureFamily.DELTA_PROXY,
                source_inputs=("open", "high", "low", "close", "volume"),
                transform_ids=(TransformWhitelistId.DELTA_PROXY_SOFT,),
            ),
        )
    )

    reasons = validate_feature_lineage_lock(
        ("delta_proxy_soft_1m", "sweep_score"),
        lineage_lock,
    )

    assert reasons == ("missing lineage for feature_id=sweep_score",)


def test_transform_whitelist_lock_requires_non_empty_unique_ids():
    with pytest.raises(ValidationError, match="requires at least one allowed_transform_id"):
        TransformWhitelistLock(allowed_transform_ids=())

    with pytest.raises(ValidationError, match="must stay unique"):
        TransformWhitelistLock(
            allowed_transform_ids=(
                TransformWhitelistId.CLIP01,
                TransformWhitelistId.CLIP01,
            )
        )


def test_validate_transform_whitelist_lock_reports_missing_coverage():
    whitelist_lock = TransformWhitelistLock(
        allowed_transform_ids=(TransformWhitelistId.CLIP01,)
    )

    reasons = validate_transform_whitelist_lock(
        (TransformWhitelistId.CLIP01, TransformWhitelistId.ZPLUS),
        whitelist_lock,
    )

    assert reasons == ("missing whitelist for transform_id=zplus",)
