from __future__ import annotations

import math

import pytest

from data_backbone import (
    DELTA_CONFIRMATION_V1_PROFILE_ID,
    DeltaProxyVariant,
    EXECUTION_SURVIVABILITY_SCORE_V1_WEIGHTS,
    FRAGILITY_SCORE_V1_WEIGHTS,
    MARKET_PHYSICS_CALIBRATION_PROFILE_ID,
    MARKET_PHYSICS_CALIBRATION_STATUS,
    MICRO_FRICTION_SCORE_V1_WEIGHTS,
    PhysicsFeatureFamily,
    PHYSICS_FEATURE_ALIASES,
    SWEEP_SCORE_V1_WEIGHTS,
    TOXICITY_SCORE_V1_WEIGHTS,
    TO_CALIBRATE,
    as_float64,
    capratio,
    clip01,
    delta_confirmation_v1,
    delta_proxy_sign,
    delta_proxy_soft,
    execution_survivability_score_v1,
    fragility_score_v1,
    micro_friction_score_v1,
    participation_ratio,
    resolve_delta_confirmation,
    require_finite_float64,
    round_float64,
    sweep_score_v1,
    toxicity_score_v1,
    void_score_discrete,
    zplus,
)


def test_physics_feature_dictionary_includes_void_and_false_breakout():
    assert PhysicsFeatureFamily.VOID_SCORE.value == "void_score"
    assert PhysicsFeatureFamily.FALSE_BREAKOUT_SCORE.value == "false_breakout_score"
    assert PHYSICS_FEATURE_ALIASES["OFI"] == PhysicsFeatureFamily.ORDER_FLOW_IMBALANCE


def test_market_physics_calibration_profile_is_explicitly_marked_to_calibrate():
    assert MARKET_PHYSICS_CALIBRATION_PROFILE_ID == "market_physics.to_calibrate.v1"
    assert MARKET_PHYSICS_CALIBRATION_STATUS == TO_CALIBRATE
    assert SWEEP_SCORE_V1_WEIGHTS["wick_ratio_capratio"] == pytest.approx(0.45)
    assert FRAGILITY_SCORE_V1_WEIGHTS["base_fragility"] == pytest.approx(0.70)
    assert TOXICITY_SCORE_V1_WEIGHTS["base_toxicity"] == pytest.approx(0.60)
    assert EXECUTION_SURVIVABILITY_SCORE_V1_WEIGHTS["fragility_score"] == pytest.approx(0.45)
    assert MICRO_FRICTION_SCORE_V1_WEIGHTS["spread_regime_penalty"] == pytest.approx(0.40)


def test_delta_proxy_variants_are_named_explicitly():
    assert DeltaProxyVariant.SOFT.value == "delta_proxy_soft"
    assert DeltaProxyVariant.SIGN.value == "delta_proxy_sign"
    assert DELTA_CONFIRMATION_V1_PROFILE_ID == "delta_confirmation.to_calibrate.v1"


def test_as_float64_returns_python_float():
    value = as_float64(1)

    assert isinstance(value, float)
    assert value == 1.0


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_require_finite_float64_rejects_non_finite_values(value: float):
    with pytest.raises(ValueError):
        require_finite_float64(value)


def test_round_float64_uses_shared_audit_rounding_policy():
    assert round_float64(0.123456789, 6) == 0.123457


@pytest.mark.parametrize(
    ("value", "expected"),
    [(-1.0, 0.0), (0.25, 0.25), (2.0, 1.0)],
)
def test_clip01(value: float, expected: float):
    assert clip01(value) == expected


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_clip01_rejects_non_finite_values(value: float):
    with pytest.raises(ValueError):
        clip01(value)


def test_zplus_requires_positive_cap():
    with pytest.raises(ValueError):
        zplus(1.0, 0.0)


def test_zplus_and_capratio_follow_p2_normalization():
    assert zplus(1.5, 3.0) == 0.5
    assert capratio(1.5, 3.0) == 0.5


def test_delta_proxy_soft_uses_soft_bar_formula():
    result = delta_proxy_soft(100.0, 105.0, 95.0, 104.0, 10.0)

    assert math.isclose(result, 4.0, rel_tol=0.0, abs_tol=1e-12)


def test_delta_proxy_sign_uses_directional_fallback():
    assert delta_proxy_sign(100.0, 101.0, 10.0) == 10.0
    assert delta_proxy_sign(100.0, 99.0, 10.0) == -10.0
    assert delta_proxy_sign(100.0, 100.0, 10.0) == 0.0


def test_delta_confirmation_v1_normalizes_signed_proxy_to_unit_interval():
    assert delta_confirmation_v1(10.0, 10.0) == pytest.approx(1.0)
    assert delta_confirmation_v1(-10.0, 10.0) == pytest.approx(0.0)
    assert delta_confirmation_v1(0.0, 10.0) == pytest.approx(0.5)


def test_resolve_delta_confirmation_prefers_explicit_value_then_soft_then_sign():
    assert resolve_delta_confirmation(delta_confirmation=0.8) == pytest.approx(0.8)
    assert resolve_delta_confirmation(
        delta_proxy_soft_value=4.0,
        reference_volume=10.0,
    ) == pytest.approx(0.7)
    assert resolve_delta_confirmation(
        delta_proxy_sign_value=-10.0,
        reference_volume=10.0,
    ) == pytest.approx(0.0)


def test_resolve_delta_confirmation_rejects_proxy_without_reference_volume():
    with pytest.raises(ValueError, match="reference_volume"):
        resolve_delta_confirmation(delta_proxy_soft_value=4.0)


def test_participation_ratio_uses_helper_feature_formula():
    result = participation_ratio(50.0, 200.0)

    assert math.isclose(result, 0.25, rel_tol=0.0, abs_tol=1e-12)


def test_void_score_discrete_uses_corridor_baseline():
    result = void_score_discrete((1.0, 2.0, 1.0), mean_window_volume=5.0)

    assert math.isclose(result, 11.0 / 15.0, rel_tol=0.0, abs_tol=1e-12)


def test_void_score_discrete_rejects_empty_region():
    with pytest.raises(ValueError):
        void_score_discrete((), mean_window_volume=5.0)


def test_sweep_score_v1_uses_canonical_p2_weights():
    result = sweep_score_v1(wick_ratio=3.0, vol_burst=1.5, reject_indicator=1.0)

    assert math.isclose(result, 0.825, rel_tol=0.0, abs_tol=1e-12)


def test_fragility_toxicity_survivability_and_micro_friction_are_bounded():
    fragility = fragility_score_v1(1.0, spread_regime_penalty=1.0)
    toxicity = toxicity_score_v1(
        1.0,
        fragility_score=fragility,
        spread_regime_penalty=1.0,
    )
    survivability = execution_survivability_score_v1(
        fragility_score=fragility,
        toxicity_score=toxicity,
        spread_regime_penalty=1.0,
    )
    micro_friction = micro_friction_score_v1(
        spread_regime_penalty=1.0,
        fragility_score=fragility,
        toxicity_score=toxicity,
    )

    assert math.isclose(fragility, 0.9, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(toxicity, 0.88, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(survivability, 0.137, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(micro_friction, 0.845, rel_tol=0.0, abs_tol=1e-12)


def test_execution_survivability_drops_when_penalties_rise():
    benign = execution_survivability_score_v1(
        fragility_score=0.0,
        toxicity_score=0.0,
        spread_regime_penalty=0.0,
    )
    stressed = execution_survivability_score_v1(
        fragility_score=0.8,
        toxicity_score=0.9,
        spread_regime_penalty=0.7,
    )

    assert benign == pytest.approx(1.0)
    assert stressed < benign
