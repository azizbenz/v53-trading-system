from __future__ import annotations

import pytest

from data_backbone.microstructure import (
    FEATURE_REGISTRY,
    MicrostructurePromotionState,
    get_feature_registry,
    get_feature_spec,
    is_valid_feature_promotion_transition,
    list_feature_specs,
    promote_feature_spec,
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
    }

    assert set(FEATURE_REGISTRY) == expected_ids
    assert {spec.feature_id for spec in list_feature_specs()} == expected_ids


def test_feature_registry_specs_are_integral_and_audit_ready() -> None:
    registry = get_feature_registry()

    for feature_id, spec in registry.items():
        assert spec.feature_id == feature_id
        assert spec.reference_paper
        assert spec.method_version == "1.0.0"
        assert (
            spec.default_window_events is not None
            or spec.default_window_seconds is not None
        )
        assert spec.calibration_seam_path.startswith("src/calibration_methods/")
        assert spec.calibration_seam_path.endswith(".py")
        assert spec.consumed_by
        assert all(consumer.strip() for consumer in spec.consumed_by)


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
