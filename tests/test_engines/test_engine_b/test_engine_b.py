"""Tests for engines.engine_b — Build-7 — Mean Reversion Intraday."""
import pytest
from pydantic import ValidationError
from data_backbone.market_physics_math import ENGINE_CONVICTION_PHYSICS_PENALTY_WEIGHTS
from engines.engine_a.conviction_builder_a import ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS

from engines.engine_b.local_mean_estimator_b import (
    ENGINE_B_LOCAL_MEAN_CALIBRATION_STATUS,
    ENGINE_B_LOCAL_MEAN_PROFILE_ID,
    LocalMeanInput,
    LocalMeanResult,
    estimate_local_mean,
)
from engines.engine_b.excess_detector_b import (
    ENGINE_B_EXCESS_CALIBRATION_STATUS,
    ENGINE_B_EXCESS_PROFILE_ID,
    ENGINE_B_EXCESS_ADJUSTMENTS_TO_CALIBRATE,
    ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE,
    ExcessInput,
    ExcessVerdict,
    ExcessResult,
    detect_excess,
)
from engines.engine_b.anti_breakout_filter_b import (
    ENGINE_B_BREAKOUT_FILTER_CALIBRATION_STATUS,
    ENGINE_B_BREAKOUT_FILTER_PROFILE_ID,
    ENGINE_B_BREAKOUT_FILTER_THRESHOLDS_TO_CALIBRATE,
    ENGINE_B_BREAKOUT_FILTER_WEIGHTS_TO_CALIBRATE,
    BreakoutInput,
    BreakoutVerdict,
    BreakoutResult,
    evaluate_breakout_risk,
)
from engines.engine_b.cost_feasibility_b import (
    ENGINE_B_COST_CALIBRATION_STATUS,
    ENGINE_B_COST_DEFAULTS,
    ENGINE_B_COST_PROFILE_ID,
    ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE,
    CostInputB,
    CostReasonCodeB,
    CostVerdictB,
    CostResultB,
    check_cost_feasibility_b,
)
from engines.engine_b.conviction_builder_b import (
    ConvictionInputB,
    ConvictionLevelB,
    TierSuggestionB,
    ConvictionResultB,
    ENGINE_B_CONVICTION_INPUT_DEFAULTS,
    ENGINE_B_CONVICTION_NORMALIZATION,
    ENGINE_B_CONVICTION_PROFILE_ID,
    ENGINE_B_CONVICTION_CALIBRATION_STATUS,
    ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS,
    MARKET_PHYSICS_CALIBRATION_PROFILE_ID,
    MARKET_PHYSICS_CALIBRATION_STATUS,
    build_conviction_b,
)
from engines.engine_b.invalidation_mapper_b import (
    ENGINE_B_INVALIDATION_CALIBRATION_STATUS,
    ENGINE_B_INVALIDATION_DEFAULTS,
    ENGINE_B_INVALIDATION_PROFILE_ID,
    ENGINE_B_INVALIDATION_THRESHOLDS_TO_CALIBRATE,
    InvalidationMapB,
    build_invalidation_b,
)
from engines.engine_b.signal_reporter_b import (
    ENGINE_B_SIGNAL_REPORTER_STATUS,
    ENGINE_B_SIGNAL_REPORTER_STATUS_DETAIL,
    SignalDecisionB,
    NoTradeReasonB,
    SignalReporterB,
    SignalStatsB,
)
from engines.engine_b.engine_b_runner import (
    ENGINE_B_RUNNER_CONTEXT_COMPONENT_COUNT,
    ENGINE_B_RUNNER_COST_RATIO_EPSILON,
    ENGINE_B_RUNNER_INPUT_DEFAULTS,
    ENGINE_B_RUNNER_WARNING_PENALTY_WEIGHT,
    EngineBInput,
    EngineBOutput,
    EngineBDecision,
    run_engine_b,
)


# ── local_mean_estimator_b ──


class TestLocalMeanEstimator:
    def test_basic_z_score(self):
        result = estimate_local_mean(LocalMeanInput(
            pair="BTCUSDT", current_price=99.0, local_mean=100.0, local_std=1.0,
        ))
        assert result.z_score == pytest.approx(-1.0)
        assert result.deviation == pytest.approx(-1.0)
        assert result.valid is True

    def test_positive_z_score(self):
        result = estimate_local_mean(LocalMeanInput(
            pair="BTCUSDT", current_price=102.0, local_mean=100.0, local_std=1.0,
        ))
        assert result.z_score == pytest.approx(2.0)

    def test_zero_std_invalid(self):
        result = estimate_local_mean(LocalMeanInput(
            pair="BTCUSDT", current_price=100.0, local_mean=100.0, local_std=0.0,
        ))
        assert result.valid is False
        assert result.z_score == 0.0

    def test_abs_z_property(self):
        result = estimate_local_mean(LocalMeanInput(
            pair="BTCUSDT", current_price=98.0, local_mean=100.0, local_std=1.0,
        ))
        assert result.abs_z == pytest.approx(2.0)

    def test_result_frozen(self):
        result = estimate_local_mean(LocalMeanInput(
            pair="BTCUSDT", current_price=99.0, local_mean=100.0, local_std=1.0,
        ))
        with pytest.raises(Exception):
            result.z_score = 999.0

    def test_local_mean_profile_is_explicitly_marked_to_calibrate(self):
        result = estimate_local_mean(LocalMeanInput(
            pair="BTCUSDT", current_price=99.0, local_mean=100.0, local_std=1.0,
        ))
        assert result.calibration_profile_id == ENGINE_B_LOCAL_MEAN_PROFILE_ID
        assert result.calibration_status == ENGINE_B_LOCAL_MEAN_CALIBRATION_STATUS

    def test_local_mean_input_contract_explicit(self) -> None:
        with pytest.raises(ValidationError):
            LocalMeanInput(pair="BTCUSDT", current_price=0.0, local_mean=100.0, local_std=1.0)
        with pytest.raises(ValidationError):
            LocalMeanInput(pair="BTCUSDT", current_price=100.0, local_mean=0.0, local_std=1.0)
        with pytest.raises(ValidationError):
            LocalMeanInput(pair="BTCUSDT", current_price=100.0, local_mean=100.0, local_std=-1.0)


# ── excess_detector_b ──


class TestExcessDetector:
    def test_exploitable_excess(self):
        """z=-2.0 is beyond z*=1.5 => EXPLOITABLE."""
        result = detect_excess(ExcessInput(
            pair="BTCUSDT", z_score=-2.0, structure_is_range=0.7,
        ))
        assert result.verdict == ExcessVerdict.EXPLOITABLE
        assert result.abs_z == pytest.approx(2.0)
        assert result.excess_score > 0.0

    def test_marginal_excess(self):
        """z=-1.2 is between z_marginal=1.0 and z*=1.5 => MARGINAL."""
        result = detect_excess(ExcessInput(
            pair="BTCUSDT", z_score=-1.2,
        ))
        assert result.verdict == ExcessVerdict.MARGINAL

    def test_no_excess_too_small(self):
        """z=-0.5 below threshold => NO_EXCESS."""
        result = detect_excess(ExcessInput(
            pair="BTCUSDT", z_score=-0.5,
        ))
        assert result.verdict == ExcessVerdict.NO_EXCESS

    def test_no_excess_too_large(self):
        """z=-5.0 beyond z_max=4.0 => likely breakout, NO_EXCESS."""
        result = detect_excess(ExcessInput(
            pair="BTCUSDT", z_score=-5.0,
        ))
        assert result.verdict == ExcessVerdict.NO_EXCESS
        assert "breakout" in result.reason

    def test_invalid_z(self):
        result = detect_excess(ExcessInput(
            pair="BTCUSDT", z_score=0.0, z_score_valid=False,
        ))
        assert result.verdict == ExcessVerdict.INVALID

    def test_range_bonus(self):
        """Higher structure_is_range should increase excess_score."""
        base = detect_excess(ExcessInput(pair="BTCUSDT", z_score=-2.0, structure_is_range=0.0))
        bonus = detect_excess(ExcessInput(pair="BTCUSDT", z_score=-2.0, structure_is_range=1.0))
        assert bonus.excess_score > base.excess_score

    def test_expansion_penalty(self):
        """Higher recent_expansion should decrease excess_score."""
        base = detect_excess(ExcessInput(pair="BTCUSDT", z_score=-2.0, recent_expansion=0.0))
        penalized = detect_excess(ExcessInput(pair="BTCUSDT", z_score=-2.0, recent_expansion=1.0))
        assert penalized.excess_score < base.excess_score

    def test_excess_profile_is_explicitly_marked_to_calibrate(self):
        result = detect_excess(ExcessInput(pair="BTCUSDT", z_score=-2.0))
        assert result.calibration_profile_id == ENGINE_B_EXCESS_PROFILE_ID
        assert result.calibration_status == ENGINE_B_EXCESS_CALIBRATION_STATUS
        assert ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.z_marginal < ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.z_star
        assert ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.z_star < ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.z_max
        assert ENGINE_B_EXCESS_ADJUSTMENTS_TO_CALIBRATE.range_bonus == pytest.approx(0.15)
        assert ENGINE_B_EXCESS_ADJUSTMENTS_TO_CALIBRATE.expansion_penalty == pytest.approx(0.20)

    def test_toxic_flow_fade_reason_code_activates_on_high_vpin(self) -> None:
        result = detect_excess(ExcessInput(
            pair="BTCUSDT",
            z_score=-1.2,
            vpin_current=0.40,
        ))
        assert result.verdict == ExcessVerdict.MARGINAL
        assert result.active_reason_codes == ("b.toxic_flow_fade",)
        assert result.suppressed_reason_codes == ()

    def test_toxic_flow_fade_suppressed_when_correlation_too_high(self) -> None:
        result = detect_excess(ExcessInput(
            pair="BTCUSDT",
            z_score=-1.2,
            vpin_current=0.40,
            toxic_flow_correlation=0.85,
        ))
        assert result.active_reason_codes == ()
        assert result.suppressed_reason_codes == ("b.toxic_flow_fade_suppressed.correlation",)

    def test_excess_input_rejects_out_of_range_fields(self) -> None:
        with pytest.raises(ValidationError):
            ExcessInput(pair="BTCUSDT", z_score=-2.0, structure_is_range=1.1)
        with pytest.raises(ValidationError):
            ExcessInput(pair="BTCUSDT", z_score=-2.0, recent_expansion=-0.1)


# ── anti_breakout_filter_b ──


class TestAntiBreakoutFilter:
    def test_clear(self):
        result = evaluate_breakout_risk(BreakoutInput(
            pair="BTCUSDT",
            regime_trend_strength=0.1, volume_anomaly=0.1,
            structural_break=0.0, continuation_momentum=0.1,
        ))
        assert result.verdict == BreakoutVerdict.CLEAR

    def test_warning(self):
        result = evaluate_breakout_risk(BreakoutInput(
            pair="BTCUSDT",
            regime_trend_strength=0.5, volume_anomaly=0.3,
            structural_break=0.3, continuation_momentum=0.3,
        ))
        assert result.verdict == BreakoutVerdict.WARNING

    def test_blocked(self):
        """Strong trend + volume + structural break => BLOCKED."""
        result = evaluate_breakout_risk(BreakoutInput(
            pair="BTCUSDT",
            regime_trend_strength=0.9, volume_anomaly=0.8,
            structural_break=0.7, continuation_momentum=0.8,
        ))
        assert result.verdict == BreakoutVerdict.BLOCKED
        assert "hostile continuation" in result.reason

    def test_result_frozen(self):
        result = evaluate_breakout_risk(BreakoutInput(pair="BTCUSDT"))
        with pytest.raises(Exception):
            result.breakout_score = 999.0

    def test_zero_inputs_clear(self):
        result = evaluate_breakout_risk(BreakoutInput(pair="BTCUSDT"))
        assert result.verdict == BreakoutVerdict.CLEAR
        assert result.breakout_score == pytest.approx(0.0)

    def test_microstructure_confirmation_increases_breakout_risk(self):
        base = evaluate_breakout_risk(BreakoutInput(
            pair="BTCUSDT",
            regime_trend_strength=0.3,
            volume_anomaly=0.2,
            structural_break=0.2,
            continuation_momentum=0.2,
            microstructure_breakout_confirmation=0.0,
        ))
        confirmed = evaluate_breakout_risk(BreakoutInput(
            pair="BTCUSDT",
            regime_trend_strength=0.3,
            volume_anomaly=0.2,
            structural_break=0.2,
            continuation_momentum=0.2,
            microstructure_breakout_confirmation=1.0,
        ))
        assert confirmed.breakout_score > base.breakout_score

    def test_breakout_profile_is_explicitly_marked_to_calibrate(self):
        result = evaluate_breakout_risk(BreakoutInput(pair="BTCUSDT"))
        assert result.calibration_profile_id == ENGINE_B_BREAKOUT_FILTER_PROFILE_ID
        assert result.calibration_status == ENGINE_B_BREAKOUT_FILTER_CALIBRATION_STATUS
        assert ENGINE_B_BREAKOUT_FILTER_THRESHOLDS_TO_CALIBRATE.warning < ENGINE_B_BREAKOUT_FILTER_THRESHOLDS_TO_CALIBRATE.blocked
        assert ENGINE_B_BREAKOUT_FILTER_WEIGHTS_TO_CALIBRATE.regime_trend_strength == pytest.approx(0.30)
        assert ENGINE_B_BREAKOUT_FILTER_WEIGHTS_TO_CALIBRATE.microstructure_breakout_confirmation == pytest.approx(0.15)

    def test_breakout_input_rejects_out_of_range_fields(self) -> None:
        with pytest.raises(ValidationError):
            BreakoutInput(pair="BTCUSDT", regime_trend_strength=1.1)
        with pytest.raises(ValidationError):
            BreakoutInput(pair="BTCUSDT", continuation_momentum=-0.1)


# ── cost_feasibility_b ──


class TestCostFeasibilityB:
    def test_feasible(self):
        result = check_cost_feasibility_b(CostInputB(
            pair="BTCUSDT", expected_gain=0.003, expected_cost=0.001,
            candidate_size=100.0, holding_period=2.0,
        ))
        assert result.verdict == CostVerdictB.FEASIBLE
        assert result.ev_net == pytest.approx(0.2)

    def test_infeasible_gain_below_breakeven(self):
        result = check_cost_feasibility_b(CostInputB(
            pair="BTCUSDT", expected_gain=0.001, expected_cost=0.0008,
            candidate_size=100.0,
        ))
        assert result.verdict == CostVerdictB.INFEASIBLE

    def test_marginal_low_ce(self):
        result = check_cost_feasibility_b(CostInputB(
            pair="BTCUSDT", expected_gain=0.002, expected_cost=0.001,
            candidate_size=100.0, holding_period=100.0, ce_min=0.001,
        ))
        assert result.verdict == CostVerdictB.MARGINAL

    def test_stricter_delta_safe_than_a(self):
        """B's default delta_safe=0.0008 vs A's 0.0005."""
        result = check_cost_feasibility_b(CostInputB(
            pair="BTCUSDT", expected_gain=0.0014, expected_cost=0.0006,
            candidate_size=100.0,
        ))
        # gain=0.0014, break_even = 0.0006 + 0.0008 = 0.0014
        # gain <= break_even => INFEASIBLE
        assert result.verdict == CostVerdictB.INFEASIBLE

    def test_ce_calculation(self):
        result = check_cost_feasibility_b(CostInputB(
            pair="BTCUSDT", expected_gain=0.004, expected_cost=0.001,
            candidate_size=100.0, holding_period=2.0,
        ))
        # edge = 0.003, CE = 0.003/2.0 = 0.0015
        assert result.ce_expected == pytest.approx(0.0015)

    def test_cost_profile_is_explicitly_marked_to_calibrate(self):
        result = check_cost_feasibility_b(CostInputB(
            pair="BTCUSDT", expected_gain=0.003, expected_cost=0.001,
            candidate_size=100.0, holding_period=2.0,
        ))
        assert result.calibration_profile_id == ENGINE_B_COST_PROFILE_ID
        assert result.calibration_status == ENGINE_B_COST_CALIBRATION_STATUS
        assert CostInputB.model_fields["delta_safe"].default == ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE.delta_safe
        assert CostInputB.model_fields["ce_min"].default == ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE.ce_min

    def test_candidate_size_zero_is_not_emittable(self) -> None:
        result = check_cost_feasibility_b(CostInputB(
            pair="BTCUSDT",
            expected_gain=0.003,
            expected_cost=0.001,
            candidate_size=0.0,
            holding_period=2.0,
        ))
        assert result.verdict == CostVerdictB.INFEASIBLE
        assert result.is_emittable is False
        assert result.reason_codes == (CostReasonCodeB.INVALID_CANDIDATE_SIZE,)

    def test_negative_candidate_size_rejected(self) -> None:
        with pytest.raises(ValidationError, match="candidate_size"):
            CostInputB(
                pair="BTCUSDT",
                expected_gain=0.003,
                expected_cost=0.001,
                candidate_size=-1.0,
                holding_period=2.0,
            )

    def test_zero_holding_period_rejected_or_not_feasible(self) -> None:
        result = check_cost_feasibility_b(CostInputB(
            pair="BTCUSDT",
            expected_gain=0.003,
            expected_cost=0.001,
            candidate_size=100.0,
            holding_period=0.0,
        ))
        assert result.verdict == CostVerdictB.INFEASIBLE
        assert result.is_emittable is False
        assert result.reason_codes == (CostReasonCodeB.INVALID_HOLDING_PERIOD,)

    def test_expected_gain_equal_boundary_not_feasible_if_strict(self) -> None:
        result = check_cost_feasibility_b(CostInputB(
            pair="BTCUSDT",
            expected_gain=0.0018,
            expected_cost=0.001,
            candidate_size=100.0,
            holding_period=2.0,
            delta_safe=0.0008,
        ))
        assert result.verdict == CostVerdictB.INFEASIBLE
        assert result.reason_codes == (CostReasonCodeB.BREAK_EVEN_NOT_CLEARED,)

    def test_reason_code_present_when_cost_infeasible(self) -> None:
        result = check_cost_feasibility_b(CostInputB(
            pair="BTCUSDT",
            expected_gain=0.001,
            expected_cost=0.001,
            candidate_size=100.0,
            holding_period=2.0,
        ))
        assert result.verdict == CostVerdictB.INFEASIBLE
        assert result.reason_codes


# ── conviction_builder_b ──


class TestConvictionBuilderB:
    def test_medium_conviction(self):
        result = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT", excess_score=0.8, structure_score=0.7,
            context_score=0.6, cost_preference_score=0.5,
        ))
        assert result.conviction == ConvictionLevelB.MEDIUM
        assert result.tier_suggestion == TierSuggestionB.TIER_2
        assert result.is_emittable is True

    def test_low_conviction(self):
        result = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT", excess_score=0.5, structure_score=0.3,
            context_score=0.3, cost_preference_score=0.2,
        ))
        assert result.conviction == ConvictionLevelB.LOW
        assert result.tier_suggestion == TierSuggestionB.NO_TRADE
        assert result.is_emittable is False

    def test_none_conviction(self):
        result = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT", excess_score=0.1, structure_score=0.1,
            context_score=0.1, cost_preference_score=0.1,
        ))
        assert result.conviction == ConvictionLevelB.NONE
        assert result.tier_suggestion == TierSuggestionB.NO_TRADE
        assert result.is_emittable is False

    def test_no_tier_3(self):
        """Engine B never gets Tier 3 — max is Tier 2."""
        result = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT", excess_score=1.0, structure_score=1.0,
            context_score=1.0, cost_preference_score=1.0,
        ))
        assert result.tier_suggestion == TierSuggestionB.TIER_2
        assert result.conviction == ConvictionLevelB.MEDIUM

    def test_block_scores_populated(self):
        result = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT", excess_score=0.5, structure_score=0.4,
            context_score=0.3, cost_preference_score=0.2,
        ))
        assert "excess" in result.block_scores
        assert "structure" in result.block_scores
        assert "context" in result.block_scores
        assert "cost_preference" in result.block_scores

    def test_calibration_profiles_are_propagated(self):
        result = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT", excess_score=0.5, structure_score=0.4,
            context_score=0.3, cost_preference_score=0.2,
        ))
        assert result.calibration_profile_id == ENGINE_B_CONVICTION_PROFILE_ID
        assert result.calibration_status == ENGINE_B_CONVICTION_CALIBRATION_STATUS
        assert result.physics_calibration_profile_id == MARKET_PHYSICS_CALIBRATION_PROFILE_ID
        assert result.physics_calibration_status == MARKET_PHYSICS_CALIBRATION_STATUS

    def test_conviction_defaults_are_explicitly_governed(self):
        assert ConvictionInputB.model_fields["sweep_score"].default == ENGINE_B_CONVICTION_INPUT_DEFAULTS["sweep_score"]
        assert ConvictionInputB.model_fields["poc_reversion_score"].default == ENGINE_B_CONVICTION_INPUT_DEFAULTS["poc_reversion_score"]
        assert ConvictionInputB.model_fields["false_breakout_score"].default == ENGINE_B_CONVICTION_INPUT_DEFAULTS["false_breakout_score"]
        assert ENGINE_B_CONVICTION_NORMALIZATION["neutral_midpoint"] == 0.5

    def test_false_breakout_default_is_neutral_not_optimistic(self):
        implicit = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT", excess_score=0.7, structure_score=0.6,
            context_score=0.5, cost_preference_score=0.5,
        ))
        explicit = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT", excess_score=0.7, structure_score=0.6,
            context_score=0.5, cost_preference_score=0.5,
            false_breakout_score=0.5,
        ))

        assert implicit.block_scores["false_breakout_score"] == pytest.approx(0.5)
        assert implicit.raw_score == pytest.approx(explicit.raw_score)

    def test_physics_penalty_weights_match_shared_governance_and_engine_a(self):
        for key, value in ENGINE_CONVICTION_PHYSICS_PENALTY_WEIGHTS.items():
            assert ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS[key] == pytest.approx(value)
            assert ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS[key] == pytest.approx(value)

    def test_raw_score_formula(self):
        """raw = legacy core score plus governed default physics adjustments."""
        result = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT", excess_score=0.8, structure_score=0.6,
            context_score=0.4, cost_preference_score=0.2,
        ))
        expected = (
            0.35 * 0.8
            + 0.25 * 0.6
            + 0.20 * 0.4
            + 0.20 * 0.2
            - 0.10 * 0.5
        )
        assert result.raw_score == pytest.approx(expected)

    def test_market_physics_inputs_shift_b_score(self):
        base = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT",
            excess_score=0.7,
            structure_score=0.6,
            context_score=0.5,
            cost_preference_score=0.5,
        ))
        enriched = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT",
            excess_score=0.7,
            structure_score=0.6,
            context_score=0.5,
            cost_preference_score=0.5,
            sweep_score=1.0,
            absorption_score=1.0,
            poc_reversion_score=1.0,
        ))
        penalized = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT",
            excess_score=0.7,
            structure_score=0.6,
            context_score=0.5,
            cost_preference_score=0.5,
            false_breakout_score=1.0,
            execution_fragility=1.0,
            market_toxicity=1.0,
            spread_regime_penalty=1.0,
        ))
        assert enriched.raw_score > base.raw_score
        assert penalized.raw_score < base.raw_score
        assert enriched.block_scores["sweep_score"] == pytest.approx(1.0)
        assert penalized.block_scores["false_breakout_score"] == pytest.approx(1.0)
        assert "fragility_score" in penalized.block_scores
        assert "toxicity_score" in penalized.block_scores
        assert "execution_survivability_score" in penalized.block_scores
        assert "micro_friction_score" in penalized.block_scores

    def test_low_boundary_exact_is_not_emittable(self) -> None:
        result = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT",
            excess_score=1.0,
            structure_score=0.0,
            context_score=0.0,
            cost_preference_score=0.0,
        ))
        assert result.raw_score == pytest.approx(0.30)
        assert result.conviction == ConvictionLevelB.LOW
        assert result.tier_suggestion == TierSuggestionB.NO_TRADE
        assert result.is_emittable is False

    def test_medium_boundary_exact_is_emittable(self) -> None:
        result = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT",
            excess_score=1.0,
            structure_score=1.0,
            context_score=0.0,
            cost_preference_score=0.0000001,
        ))
        assert result.raw_score > 0.55
        assert result.conviction == ConvictionLevelB.MEDIUM
        assert result.tier_suggestion == TierSuggestionB.TIER_2
        assert result.is_emittable is True


# ── invalidation_mapper_b ──


class TestInvalidationMapperB:
    def test_basic_invalidation(self):
        inv = build_invalidation_b(
            pair="BTCUSDT", entry_price=98.0, local_mean=100.0, local_std=1.0,
        )
        assert inv.direction == "long"
        assert inv.target_price == pytest.approx(100.0)
        assert inv.stop_price == pytest.approx(98.0 - 1.5 * 1.0)  # 96.5
        assert inv.max_holding_hours == pytest.approx(8.0)

    def test_custom_holding_hours(self):
        inv = build_invalidation_b(
            pair="ETHUSDT", entry_price=1900.0, local_mean=2000.0,
            local_std=50.0, holding_hours=4.0,
        )
        assert inv.max_holding_hours == pytest.approx(4.0)

    def test_zero_std_fallback(self):
        """If local_std=0, stop defaults to entry * 0.98."""
        inv = build_invalidation_b(
            pair="BTCUSDT", entry_price=100.0, local_mean=102.0, local_std=0.0,
        )
        assert inv.stop_price == pytest.approx(98.0)

    def test_result_frozen(self):
        inv = build_invalidation_b(
            pair="BTCUSDT", entry_price=100.0, local_mean=102.0, local_std=1.0,
        )
        with pytest.raises(Exception):
            inv.direction = "short"

    def test_always_long(self):
        """Engine B is long-only for spot-halal profile."""
        inv = build_invalidation_b(
            pair="BTCUSDT", entry_price=100.0, local_mean=102.0, local_std=1.0,
        )
        assert inv.direction == "long"

    def test_invalidation_profile_is_explicitly_marked_to_calibrate(self):
        inv = build_invalidation_b(
            pair="BTCUSDT", entry_price=98.0, local_mean=100.0, local_std=1.0,
        )
        assert inv.calibration_profile_id == ENGINE_B_INVALIDATION_PROFILE_ID
        assert inv.calibration_status == ENGINE_B_INVALIDATION_CALIBRATION_STATUS
        assert inv.max_holding_hours == pytest.approx(
            ENGINE_B_INVALIDATION_THRESHOLDS_TO_CALIBRATE.max_holding_hours
        )
        assert ENGINE_B_INVALIDATION_THRESHOLDS_TO_CALIBRATE.fallback_stop_ratio == pytest.approx(0.98)
        assert ENGINE_B_INVALIDATION_THRESHOLDS_TO_CALIBRATE.stop_multiplier == pytest.approx(1.5)

    def test_entry_price_invalid_rejected(self) -> None:
        with pytest.raises(ValueError, match="entry_price"):
            build_invalidation_b(
                pair="BTCUSDT",
                entry_price=0.0,
                local_mean=100.0,
                local_std=1.0,
            )

    def test_local_mean_invalid_rejected(self) -> None:
        with pytest.raises(ValueError, match="local_mean"):
            build_invalidation_b(
                pair="BTCUSDT",
                entry_price=98.0,
                local_mean=0.0,
                local_std=1.0,
            )

    def test_negative_local_std_rejected(self) -> None:
        with pytest.raises(ValueError, match="local_std"):
            build_invalidation_b(
                pair="BTCUSDT",
                entry_price=98.0,
                local_mean=100.0,
                local_std=-1.0,
            )

    def test_holding_hours_invalid_rejected(self) -> None:
        with pytest.raises(ValueError, match="holding_hours"):
            build_invalidation_b(
                pair="BTCUSDT",
                entry_price=98.0,
                local_mean=100.0,
                local_std=1.0,
                holding_hours=0.0,
            )

    def test_stop_fallback_sets_reason_when_non_positive(self) -> None:
        inv = build_invalidation_b(
            pair="BTCUSDT",
            entry_price=1.0,
            local_mean=1.2,
            local_std=10.0,
        )
        assert inv.stop_price == pytest.approx(0.98)
        assert inv.reason == "engine_b.invalidation.fallback_stop.non_positive"

    def test_target_at_or_below_entry_rejected_with_stable_code(self) -> None:
        with pytest.raises(ValueError, match="INVALID_TARGET_LE_ENTRY"):
            build_invalidation_b(
                pair="BTCUSDT",
                entry_price=100.0,
                local_mean=100.0,
                local_std=1.0,
            )

    def test_stop_at_or_above_entry_rejected_with_stable_code(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(ENGINE_B_INVALIDATION_DEFAULTS, "stop_multiplier", -1.0)
        with pytest.raises(ValueError, match="INVALID_STOP_GE_ENTRY"):
            build_invalidation_b(
                pair="BTCUSDT",
                entry_price=100.0,
                local_mean=120.0,
                local_std=1.0,
            )


# ── signal_reporter_b ──


class TestSignalReporterB:
    def test_signal_reporter_status_is_explicit(self) -> None:
        assert ENGINE_B_SIGNAL_REPORTER_STATUS == "secondary_helper_non_canonical_flow"
        assert "NoTradeReasonB is canonical" in ENGINE_B_SIGNAL_REPORTER_STATUS_DETAIL
        assert "secondary audit helpers" in ENGINE_B_SIGNAL_REPORTER_STATUS_DETAIL

    def test_initial_state(self):
        reporter = SignalReporterB()
        stats = reporter.get_stats()
        assert stats.total_evaluated == 0
        assert stats.total_emitted == 0

    def test_record_emit(self):
        reporter = SignalReporterB()
        reporter.record_emit(raw_score=0.65, z_score=-2.1)
        stats = reporter.get_stats()
        assert stats.total_emitted == 1
        assert stats.mean_z_score == pytest.approx(-2.1)

    def test_record_no_trade(self):
        reporter = SignalReporterB()
        reporter.record_no_trade(("no_excess", "cost_infeasible"))
        stats = reporter.get_stats()
        assert stats.total_no_trade == 1
        assert stats.no_trade_by_reason["no_excess"] == 1

    def test_emission_rate(self):
        reporter = SignalReporterB()
        reporter.record_emit(0.6, z_score=-1.5)
        reporter.record_no_trade(("no_excess",))
        stats = reporter.get_stats()
        assert stats.emission_rate == pytest.approx(0.5)


# ── engine_b_runner E2E ──


def _emit_inputs(**overrides) -> EngineBInput:
    """Standard favorable B inputs — price below mean, good excess, low breakout."""
    defaults = dict(
        pair="BTCUSDT",
        current_price=97.0,
        local_mean=100.0,
        local_std=1.5,  # z = (97-100)/1.5 = -2.0
        structure_is_range=0.7,
        recent_expansion=0.1,
        regime="range",
        regime_trend_strength=0.1,
        volume_anomaly=0.1,
        structural_break=0.0,
        continuation_momentum=0.1,
        microstructure_breakout_confirmation=0.0,
        regime_favorability=0.7,
        pair_health=0.8,
        data_freshness=0.9,
        flow_coherence=0.8,
        expected_gain=0.003,
        expected_cost=0.001,
        candidate_size=100.0,
        holding_period=2.0,
        scoring_version="B_v1",
    )
    defaults.update(overrides)
    return EngineBInput(**defaults)


def test_engine_b_runner_defaults_are_explicitly_governed():
    assert EngineBInput.model_fields["structure_is_range"].default == ENGINE_B_RUNNER_INPUT_DEFAULTS["structure_is_range"]
    assert EngineBInput.model_fields["sweep_score"].default == ENGINE_B_RUNNER_INPUT_DEFAULTS["sweep_score"]
    assert EngineBInput.model_fields["false_breakout_score"].default == ENGINE_B_RUNNER_INPUT_DEFAULTS["false_breakout_score"]
    assert EngineBInput.model_fields["holding_period"].default == ENGINE_B_RUNNER_INPUT_DEFAULTS["holding_period"]
    assert EngineBInput.model_fields["delta_safe"].default == ENGINE_B_RUNNER_INPUT_DEFAULTS["delta_safe"]
    assert EngineBInput.model_fields["ce_min"].default == ENGINE_B_RUNNER_INPUT_DEFAULTS["ce_min"]
    assert EngineBInput.model_fields["holding_period"].default == ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE.holding_period
    assert EngineBInput.model_fields["delta_safe"].default == ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE.delta_safe
    assert EngineBInput.model_fields["ce_min"].default == ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE.ce_min


def test_engine_b_runner_false_breakout_default_is_neutral():
    implicit = run_engine_b(_emit_inputs())
    explicit = run_engine_b(_emit_inputs(false_breakout_score=0.5))

    assert implicit.block_scores["false_breakout_score"] == pytest.approx(0.5)
    assert implicit.raw_score == pytest.approx(explicit.raw_score)


def test_engine_b_runner_conventions_are_explicitly_governed():
    assert ENGINE_B_RUNNER_CONTEXT_COMPONENT_COUNT == 4.0
    assert ENGINE_B_RUNNER_COST_RATIO_EPSILON == 1e-9
    assert ENGINE_B_RUNNER_WARNING_PENALTY_WEIGHT == 0.30


class TestEngineBRunner:
    def test_emit_favorable(self):
        """Full pipeline with favorable inputs => EMIT."""
        output = run_engine_b(_emit_inputs())
        assert output.decision == EngineBDecision.EMIT
        assert output.conviction == ConvictionLevelB.MEDIUM
        assert output.tier_suggestion == TierSuggestionB.TIER_2
        assert output.z_score < 0
        assert output.invalidation is not None
        assert output.invalidation.direction == "long"
        assert len(output.log_entries) >= 5

    def test_no_trade_long_only(self):
        """Price above mean (z > 0) => NO_TRADE (long-only)."""
        output = run_engine_b(_emit_inputs(current_price=103.0))
        assert output.decision == EngineBDecision.NO_TRADE
        assert NoTradeReasonB.NON_LONG_DIRECTION in output.no_trade_reasons

    def test_no_trade_no_excess(self):
        """Small deviation => NO_TRADE (no excess)."""
        output = run_engine_b(_emit_inputs(current_price=99.5))
        # z = (99.5 - 100) / 1.5 = -0.33 < z_marginal
        assert output.decision == EngineBDecision.NO_TRADE
        assert NoTradeReasonB.NO_EXCESS in output.no_trade_reasons
        assert output.reason_codes == (
            "engine_internal.engine_b.excess.no_excess",
            "engine_b.excess.no_excess",
        )
        assert output.log_entries[-1].reasons == output.reason_codes

    def test_no_trade_breakout_blocked(self):
        """Strong trend against reversion => BLOCKED."""
        output = run_engine_b(_emit_inputs(
            regime_trend_strength=0.9, volume_anomaly=0.8,
            structural_break=0.7, continuation_momentum=0.8,
        ))
        assert output.decision == EngineBDecision.NO_TRADE
        assert NoTradeReasonB.BREAKOUT_BLOCKED in output.no_trade_reasons
        assert output.reason_codes == (
            "engine_internal.engine_b.breakout.blocked",
            "engine_b.breakout.blocked",
        )
        assert output.log_entries[-1].reasons == output.reason_codes

    def test_no_trade_cost_infeasible(self):
        """Cost kills the edge => NO_TRADE."""
        output = run_engine_b(_emit_inputs(expected_gain=0.001, expected_cost=0.0008))
        assert output.decision == EngineBDecision.NO_TRADE
        assert NoTradeReasonB.COST_INFEASIBLE in output.no_trade_reasons

    def test_no_trade_invalid_dispersion(self):
        """Zero dispersion => INVALID_DISPERSION."""
        output = run_engine_b(_emit_inputs(local_std=0.0))
        assert output.decision == EngineBDecision.NO_TRADE
        assert NoTradeReasonB.INVALID_DISPERSION in output.no_trade_reasons
        assert output.reason_codes == (
            "hard_block.engine_b.local_mean.invalid_dispersion",
            "engine_b.local_mean.invalid_dispersion",
        )

    def test_scoring_version_propagated(self):
        output = run_engine_b(_emit_inputs(scoring_version="B_v2"))
        assert output.scoring_version == "B_v2"

    def test_structured_logs_present(self):
        output = run_engine_b(_emit_inputs())
        events = [log.event for log in output.log_entries]
        assert "engine_b_mean_estimated" in events
        assert "engine_b_excess_evaluated" in events
        assert "engine_b_breakout_evaluated" in events
        assert "engine_b_cost_checked" in events
        assert "engine_b_conviction_built" in events
        assert "engine_b_signal_emitted" in events

    def test_output_frozen(self):
        output = run_engine_b(_emit_inputs())
        with pytest.raises(Exception):
            output.decision = EngineBDecision.NO_TRADE

    def test_z_score_in_output(self):
        """Spec requires z-score in output for audit."""
        output = run_engine_b(_emit_inputs())
        assert output.z_score == pytest.approx(-2.0)

    def test_no_trade_reasons_explicit(self):
        """Every NO_TRADE must have at least one explicit reason."""
        output = run_engine_b(_emit_inputs(current_price=103.0))
        assert len(output.no_trade_reasons) > 0
        assert output.reason_codes == (
            "engine_internal.engine_b.direction.non_long",
            "engine_b.direction.non_long",
        )

    def test_breakout_warning_still_emits(self):
        """WARNING doesn't block, only BLOCKED does."""
        output = run_engine_b(_emit_inputs(
            regime_trend_strength=0.5, volume_anomaly=0.3,
            structural_break=0.2, continuation_momentum=0.2,
        ))
        # breakout_score ~ 0.34, below BLOCKED threshold
        assert output.decision == EngineBDecision.EMIT

    def test_breakout_warning_penalizes_score(self):
        """WARNING must produce penalized_score < raw_score."""
        output = run_engine_b(_emit_inputs(
            regime_trend_strength=0.5, volume_anomaly=0.4,
            structural_break=0.3, continuation_momentum=0.3,
        ))
        # breakout_score = 0.30*0.5 + 0.25*0.4 + 0.25*0.3 + 0.20*0.3 = 0.385
        # This is WARNING range (>=0.35, <0.65)
        assert output.decision == EngineBDecision.EMIT
        assert output.breakout_verdict == BreakoutVerdict.WARNING
        assert output.penalized_score < output.raw_score
        # Penalty = 0.30 * breakout_score
        expected_penalty = 0.30 * output.breakout_score
        assert output.penalized_score == pytest.approx(output.raw_score - expected_penalty)

    def test_breakout_warning_logged(self):
        """WARNING penalty must appear in structured logs."""
        output = run_engine_b(_emit_inputs(
            regime_trend_strength=0.5, volume_anomaly=0.4,
            structural_break=0.3, continuation_momentum=0.3,
        ))
        events = [log.event for log in output.log_entries]
        assert "engine_b_breakout_penalty" in events

    def test_no_warning_no_penalty(self):
        """CLEAR breakout => penalized_score == raw_score."""
        output = run_engine_b(_emit_inputs())
        assert output.breakout_verdict == BreakoutVerdict.CLEAR
        assert output.penalized_score == pytest.approx(output.raw_score)

    def test_excess_score_in_output(self):
        output = run_engine_b(_emit_inputs())
        assert output.excess_score > 0.0
        assert output.excess_verdict == ExcessVerdict.EXPLOITABLE
        assert "scoring.engine_b.conviction.medium" in output.reason_codes
        assert "engine_b.conviction.medium" in output.reason_codes
        assert "engine_internal.engine_b.excess.exploitable" in output.reason_codes
        assert "engine_b.excess.exploitable" in output.reason_codes
        assert "economics.engine_b.cost.feasible" in output.reason_codes

    def test_flow_coherence_feeds_runtime_conviction_path(self):
        weak_flow = run_engine_b(_emit_inputs(flow_coherence=0.0))
        strong_flow = run_engine_b(_emit_inputs(flow_coherence=1.0))
        assert weak_flow.decision == EngineBDecision.NO_TRADE
        assert weak_flow.no_trade_reasons == (NoTradeReasonB.CONVICTION_LOW,)
        assert weak_flow.reason_codes == (
            "scoring.engine_b.conviction.low",
            "engine_b.conviction.low",
        )
        assert strong_flow.decision == EngineBDecision.EMIT
        assert strong_flow.raw_score > weak_flow.raw_score
        assert strong_flow.block_scores["context"] > weak_flow.block_scores["context"]

    def test_microstructure_confirmation_can_upgrade_warning_to_blocked(self):
        warning = run_engine_b(_emit_inputs(
            regime_trend_strength=0.7,
            volume_anomaly=0.5,
            structural_break=0.5,
            continuation_momentum=0.4,
            microstructure_breakout_confirmation=0.0,
        ))
        blocked = run_engine_b(_emit_inputs(
            regime_trend_strength=0.7,
            volume_anomaly=0.5,
            structural_break=0.5,
            continuation_momentum=0.4,
            microstructure_breakout_confirmation=1.0,
        ))
        assert warning.breakout_verdict == BreakoutVerdict.WARNING
        assert blocked.decision == EngineBDecision.NO_TRADE
        assert blocked.breakout_verdict == BreakoutVerdict.BLOCKED

    def test_market_physics_inputs_shift_runtime_conviction_path(self):
        base_output = run_engine_b(_emit_inputs())
        enriched_output = run_engine_b(_emit_inputs(
            sweep_score=1.0,
            absorption_score=1.0,
            poc_reversion_score=1.0,
        ))
        penalized_output = run_engine_b(_emit_inputs(
            false_breakout_score=1.0,
            execution_fragility=1.0,
            market_toxicity=1.0,
            spread_regime_penalty=1.0,
        ))

        assert enriched_output.decision == EngineBDecision.EMIT
        assert penalized_output.decision == EngineBDecision.NO_TRADE
        assert enriched_output.raw_score > base_output.raw_score
        assert penalized_output.raw_score < base_output.raw_score
        assert penalized_output.conviction == ConvictionLevelB.NONE
        assert enriched_output.block_scores["sweep_score"] == pytest.approx(1.0)
        assert penalized_output.block_scores["market_toxicity"] == pytest.approx(1.0)
        assert "execution_survivability_score" in penalized_output.block_scores
        assert penalized_output.block_scores["micro_friction_score"] > 0.0

    def test_toxic_flow_fade_reason_codes_propagate_on_emit(self) -> None:
        output = run_engine_b(_emit_inputs(
            vpin_current=0.40,
        ))
        assert output.decision == EngineBDecision.EMIT
        assert "scoring.engine_b.conviction.medium" in output.reason_codes
        assert "engine_b.conviction.medium" in output.reason_codes
        assert "engine_internal.engine_b.excess.exploitable" in output.reason_codes
        assert "engine_b.excess.exploitable" in output.reason_codes
        assert "b.toxic_flow_fade" in output.reason_codes

    def test_toxic_flow_fade_is_suppressed_when_correlation_exceeds_threshold(self) -> None:
        output = run_engine_b(_emit_inputs(
            vpin_current=0.40,
            toxic_flow_correlation=0.85,
        ))
        assert output.decision == EngineBDecision.EMIT
        assert "scoring.engine_b.conviction.medium" in output.reason_codes
        assert "engine_b.conviction.medium" in output.reason_codes
        assert "engine_internal.engine_b.excess.exploitable" in output.reason_codes
        assert "engine_b.excess.exploitable" in output.reason_codes
        assert "b.toxic_flow_fade_suppressed.correlation" in output.reason_codes
        excess_logs = [entry for entry in output.log_entries if entry.event == "engine_b_excess_evaluated"]
        assert len(excess_logs) == 1
        assert "b.toxic_flow_fade_suppressed.correlation" in excess_logs[0].reasons

    def test_emit_reason_codes_are_not_excess_only(self) -> None:
        output = run_engine_b(_emit_inputs(
            regime_trend_strength=0.5,
            volume_anomaly=0.4,
            structural_break=0.3,
            continuation_momentum=0.3,
        ))
        assert output.decision == EngineBDecision.EMIT
        assert "engine_b.conviction.medium" in output.reason_codes
        assert "engine_b.excess.exploitable" in output.reason_codes
        assert "engine_b.breakout.warning" in output.reason_codes

    def test_candidate_size_zero_rejected_before_emit(self) -> None:
        output = run_engine_b(_emit_inputs(candidate_size=0.0))
        assert output.decision == EngineBDecision.NO_TRADE
        assert output.no_trade_reasons == (NoTradeReasonB.INVALID_INPUT,)
        assert output.reason_codes == (
            "hard_block.engine_b.input.invalid_input",
            "engine_b.input.candidate_size_non_positive",
        )
        assert output.log_entries[-1].event == "engine_b_no_trade"

    def test_holding_period_zero_rejected_before_emit(self) -> None:
        output = run_engine_b(_emit_inputs(holding_period=0.0))
        assert output.decision == EngineBDecision.NO_TRADE
        assert output.no_trade_reasons == (NoTradeReasonB.INVALID_INPUT,)
        assert output.reason_codes == (
            "hard_block.engine_b.input.invalid_input",
            "engine_b.input.holding_period_non_positive",
        )
        assert output.log_entries[-1].event == "engine_b_no_trade"

    def test_current_price_zero_rejected_before_emit(self) -> None:
        output = run_engine_b(_emit_inputs(current_price=0.0))
        assert output.decision == EngineBDecision.NO_TRADE
        assert output.no_trade_reasons == (NoTradeReasonB.INVALID_INPUT,)
        assert output.reason_codes == (
            "hard_block.engine_b.input.invalid_input",
            "engine_b.input.current_price_non_positive",
        )
        assert output.log_entries[-1].event == "engine_b_no_trade"

    def test_cost_marginal_cannot_emit(self) -> None:
        output = run_engine_b(_emit_inputs(
            expected_gain=0.002,
            expected_cost=0.001,
            holding_period=100.0,
            ce_min=0.001,
        ))
        assert output.decision == EngineBDecision.NO_TRADE
        assert output.no_trade_reasons == (NoTradeReasonB.COST_MARGINAL,)
        assert output.cost_verdict == CostVerdictB.MARGINAL
        assert output.reason_codes == (
            "economics.engine_b.cost.marginal",
            "ce_below_minimum",
        )
        assert output.log_entries[-1].reasons == output.reason_codes
        assert output.log_entries[-1].event == "engine_b_no_trade"

    def test_low_conviction_cannot_emit(self) -> None:
        output = run_engine_b(_emit_inputs(flow_coherence=0.0))
        assert output.decision == EngineBDecision.NO_TRADE
        assert output.no_trade_reasons == (NoTradeReasonB.CONVICTION_LOW,)
        assert output.reason_codes == (
            "scoring.engine_b.conviction.low",
            "engine_b.conviction.low",
        )
        assert output.log_entries[-1].event == "engine_b_no_trade"

    def test_invalid_invalidation_inputs_rejected_before_emit(self) -> None:
        output = run_engine_b(_emit_inputs(local_mean=0.0))
        assert output.decision == EngineBDecision.NO_TRADE
        assert output.no_trade_reasons == (NoTradeReasonB.INVALID_INPUT,)
        assert output.reason_codes == (
            "hard_block.engine_b.input.invalid_input",
            "engine_b.input.local_mean_non_positive",
        )
        assert output.log_entries[-1].event == "engine_b_no_trade"

    def test_engine_b_input_rejects_out_of_range_normalized_fields(self) -> None:
        with pytest.raises(ValidationError):
            _emit_inputs(structure_is_range=1.1)

    def test_engine_b_input_accepts_boundary_zero(self) -> None:
        output = run_engine_b(_emit_inputs(
            structure_is_range=0.0,
            recent_expansion=0.0,
            regime_trend_strength=0.0,
            volume_anomaly=0.0,
            structural_break=0.0,
            continuation_momentum=0.0,
            microstructure_breakout_confirmation=0.0,
            sweep_score=0.0,
            absorption_score=0.0,
            poc_reversion_score=0.0,
            false_breakout_score=0.0,
            execution_fragility=0.0,
            market_toxicity=0.0,
            spread_regime_penalty=0.0,
            regime_favorability=0.0,
            pair_health=0.0,
            data_freshness=0.0,
            flow_coherence=0.0,
        ))
        assert output.decision == EngineBDecision.NO_TRADE

    def test_engine_b_input_accepts_boundary_one(self) -> None:
        output = run_engine_b(_emit_inputs(
            structure_is_range=1.0,
            recent_expansion=1.0,
            regime_trend_strength=1.0,
            volume_anomaly=1.0,
            structural_break=1.0,
            continuation_momentum=1.0,
            microstructure_breakout_confirmation=1.0,
            sweep_score=1.0,
            absorption_score=1.0,
            poc_reversion_score=1.0,
            false_breakout_score=1.0,
            execution_fragility=1.0,
            market_toxicity=1.0,
            spread_regime_penalty=1.0,
            regime_favorability=1.0,
            pair_health=1.0,
            data_freshness=1.0,
            flow_coherence=1.0,
        ))
        assert output.decision in (EngineBDecision.EMIT, EngineBDecision.NO_TRADE)
