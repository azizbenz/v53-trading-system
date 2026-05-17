from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from data_backbone.microstructure import (
    FEATURE_REGISTRY,
    MicrostructurePromotionState,
    get_feature_registry,
    get_feature_spec,
    is_valid_feature_promotion_transition,
    list_feature_specs,
    promote_feature_spec,
    quarantine_feature_spec,
    reject_feature_spec,
    restore_quarantined_feature_spec,
)


def test_feature_registry_contains_all_doc23_canonical_features() -> None:
    expected_ids = {
        "ofi.cont_kukanov",
        "vpin.easley_lopez_ohara",
        "kyle_lambda.kyle",
        "amihud_illiquidity.amihud",
        "roll_spread.roll",
        "corwin_schultz_spread.corwin_schultz",
        "realized_kernel_vol.barndorff_nielsen",
        "hawkes_intensity.bacry_mastromatteo_muzy",
        "pin.easley_kiefer_ohara_paperman",
        "queue_pressure.book_imbalance",
        "realized_effective_spread.live",
        "wall_strength_bid",
        "wall_strength_ask",
        "wall_persistence_bid",
        "wall_persistence_ask",
        "wall_persistence_conditional_bid",
        "wall_persistence_conditional_ask",
        "wall_pullaway_bid",
        "wall_pullaway_ask",
        "near_touch_cancel_ratio_bid",
        "near_touch_cancel_ratio_ask",
        "executed_vs_displayed_bid",
        "executed_vs_displayed_ask",
        "book_shape_skew",
        "microprice_pressure",
        "real_wall_score_bid",
        "real_wall_score_ask",
        "spoof_suspicion_score_bid",
        "spoof_suspicion_score_ask",
        "deceptive_liquidity_score",
        "observation_coverage_ratio",
    }

    assert set(FEATURE_REGISTRY) == expected_ids
    assert {spec.feature_id for spec in list_feature_specs()} == expected_ids


def test_feature_registry_specs_are_integral_and_audit_ready() -> None:
    registry = get_feature_registry()

    for feature_id, spec in registry.items():
        assert spec.feature_id == feature_id
        assert spec.reference_paper
        assert spec.method_version  # non-empty
        assert "." in spec.method_version  # namespaced format e.g. 'ofi.cont_kukanov.v1'
        assert (
            spec.default_window_events is not None
            or spec.default_window_seconds is not None
        )
        assert spec.calibration_seam_path.startswith("src/calibration_methods/")
        assert spec.calibration_seam_path.endswith(".py")
        assert spec.consumed_by
        assert spec.consumer_statuses
        assert all(consumer.strip() for consumer in spec.consumed_by)
        assert spec.method_version_hash == sha256(spec.method_version.encode("utf-8")).hexdigest()


def test_feature_registry_surfaces_wave4_semantic_statuses() -> None:
    ofi = get_feature_spec("ofi.cont_kukanov")
    kyle = get_feature_spec("kyle_lambda.kyle")
    amihud = get_feature_spec("amihud_illiquidity.amihud")
    roll = get_feature_spec("roll_spread.roll")
    corwin = get_feature_spec("corwin_schultz_spread.corwin_schultz")
    pin = get_feature_spec("pin.easley_kiefer_ohara_paperman")
    hawkes = get_feature_spec("hawkes_intensity.bacry_mastromatteo_muzy")
    wall = get_feature_spec("real_wall_score_bid")

    assert ofi.unit_status == "RAW_SIGNED_SIZE_IMBALANCE"
    assert ofi.cross_pair_comparable is False
    assert ofi.normalization_status == "ENGINE_LOCAL_THRESHOLDS"
    assert ofi.normalized_seam_available is True
    assert ofi.runtime_lifecycle_status == "ACTIVE_ENGINE_INPUT"

    assert kyle.unit_status == "UNNORMALIZED_LOCAL_OLS_SLOPE"
    assert kyle.cross_pair_comparable is False
    assert kyle.normalized_seam_available is True
    assert kyle.runtime_lifecycle_status == "ACTIVE_ENGINE_INPUT"

    assert amihud.runtime_lifecycle_status == "RESEARCH_ONLY"
    assert amihud.registry_intent_status == "PAIR_LIQUIDITY_REPORT"
    assert roll.runtime_lifecycle_status == "FALLBACK_ONLY"
    assert roll.registry_intent_status == "MISSING_L2_SPREAD_FALLBACK"
    assert corwin.runtime_lifecycle_status == "RESEARCH_ONLY"
    assert corwin.registry_intent_status == "OHLC_FALLBACK"

    assert "FUTURE_RESERVED" in pin.consumer_statuses
    assert "NOT_RUNTIME_CONSUMED" in pin.consumer_statuses
    assert pin.runtime_lifecycle_status == "FUTURE_RESERVED"
    assert pin.registry_intent_status == "OFFLINE_PARAMETER_SEAM"
    assert "RESEARCH_ONLY" in hawkes.consumer_statuses
    assert "NOT_RUNTIME_CONSUMED" in hawkes.consumer_statuses
    assert hawkes.runtime_lifecycle_status == "FUTURE_RESERVED"

    assert wall.calibration_status == "CALIBRATION_REQUIRED_FOR_STRONG_PRODUCTION_CLAIM"
    assert wall.runtime_lifecycle_status == "ACTIVE_RUNTIME"


def test_feature_registry_consumers_resolve_to_real_source_surfaces() -> None:
    repo_src = Path("src")
    registry = get_feature_registry()

    missing: list[str] = []
    for feature_id, spec in registry.items():
        for consumer in spec.consumed_by:
            consumer_path = repo_src.joinpath(*consumer.split("."))
            if consumer_path.with_suffix(".py").exists():
                continue
            if consumer_path.joinpath("__init__.py").exists():
                continue
            missing.append(f"{feature_id}:{consumer}")

    assert missing == []


def test_feature_registry_promotion_transitions_are_sequential_only() -> None:
    assert is_valid_feature_promotion_transition(
        MicrostructurePromotionState.DISCOVERED,
        MicrostructurePromotionState.VALIDATED,
    )
    assert not is_valid_feature_promotion_transition(
        MicrostructurePromotionState.DISCOVERED,
        MicrostructurePromotionState.CANDIDATE_VPS,
    )
    assert not is_valid_feature_promotion_transition(
        MicrostructurePromotionState.SHADOW_VPS,
        MicrostructurePromotionState.VALIDATED,
    )

    promoted = promote_feature_spec(
        get_feature_spec("ofi.cont_kukanov"),
        MicrostructurePromotionState.VALIDATED,
    )
    assert promoted.promotion_state == MicrostructurePromotionState.VALIDATED

    with pytest.raises(ValueError, match="invalid promotion transition"):
        promote_feature_spec(
            get_feature_spec("ofi.cont_kukanov"),
            MicrostructurePromotionState.SHADOW_VPS,
        )


def test_get_feature_spec_rejects_unknown_feature_id() -> None:
    with pytest.raises(KeyError, match="unknown microstructure feature_id"):
        get_feature_spec("unknown.feature")


def test_quarantine_requires_non_blank_reason() -> None:
    spec = get_feature_spec("ofi.cont_kukanov")

    with pytest.raises(ValueError, match="lifecycle_reason"):
        quarantine_feature_spec(spec, reason="   ")


def test_reject_requires_non_blank_reason() -> None:
    spec = get_feature_spec("vpin.easley_lopez_ohara")

    with pytest.raises(ValueError, match="lifecycle_reason"):
        reject_feature_spec(spec, reason="  ")


def test_quarantine_and_restore_round_trip_preserves_last_active_state() -> None:
    promoted = promote_feature_spec(
        get_feature_spec("kyle_lambda.kyle"),
        MicrostructurePromotionState.VALIDATED,
    )

    quarantined = quarantine_feature_spec(promoted, reason="shadow drift")
    restored = restore_quarantined_feature_spec(quarantined)

    assert quarantined.promotion_state == MicrostructurePromotionState.QUARANTINED
    assert quarantined.quarantined_from == MicrostructurePromotionState.VALIDATED
    assert restored.promotion_state == MicrostructurePromotionState.VALIDATED
    assert restored.quarantined_from is None
    assert restored.lifecycle_reason is None
