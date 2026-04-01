"""Tests for engines.engine_b — Build-7 — Mean Reversion Intraday."""
import pytest

from engines.engine_b.local_mean_estimator_b import (
    LocalMeanInput,
    LocalMeanResult,
    estimate_local_mean,
)
from engines.engine_b.excess_detector_b import (
    ExcessInput,
    ExcessVerdict,
    ExcessResult,
    detect_excess,
)
from engines.engine_b.anti_breakout_filter_b import (
    BreakoutInput,
    BreakoutVerdict,
    BreakoutResult,
    evaluate_breakout_risk,
)
from engines.engine_b.cost_feasibility_b import (
    CostInputB,
    CostVerdictB,
    CostResultB,
    check_cost_feasibility_b,
)
from engines.engine_b.conviction_builder_b import (
    ConvictionInputB,
    ConvictionLevelB,
    TierSuggestionB,
    ConvictionResultB,
    build_conviction_b,
)
from engines.engine_b.invalidation_mapper_b import (
    InvalidationMapB,
    build_invalidation_b,
)
from engines.engine_b.signal_reporter_b import (
    SignalDecisionB,
    NoTradeReasonB,
    SignalReporterB,
    SignalStatsB,
)
from engines.engine_b.engine_b_runner import (
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


# ── conviction_builder_b ──


class TestConvictionBuilderB:
    def test_medium_conviction(self):
        result = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT", excess_score=0.8, structure_score=0.7,
            context_score=0.6, cost_preference_score=0.5,
        ))
        assert result.conviction == ConvictionLevelB.MEDIUM
        assert result.tier_suggestion == TierSuggestionB.TIER_2

    def test_low_conviction(self):
        result = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT", excess_score=0.5, structure_score=0.3,
            context_score=0.3, cost_preference_score=0.2,
        ))
        assert result.conviction == ConvictionLevelB.LOW
        assert result.tier_suggestion == TierSuggestionB.TIER_1

    def test_none_conviction(self):
        result = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT", excess_score=0.1, structure_score=0.1,
            context_score=0.1, cost_preference_score=0.1,
        ))
        assert result.conviction == ConvictionLevelB.NONE
        assert result.tier_suggestion == TierSuggestionB.NO_TRADE

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

    def test_raw_score_formula(self):
        """raw = 0.35·excess + 0.25·structure + 0.20·context + 0.20·cost_pref."""
        result = build_conviction_b(ConvictionInputB(
            pair="BTCUSDT", excess_score=0.8, structure_score=0.6,
            context_score=0.4, cost_preference_score=0.2,
        ))
        expected = 0.35 * 0.8 + 0.25 * 0.6 + 0.20 * 0.4 + 0.20 * 0.2
        assert result.raw_score == pytest.approx(expected)


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


# ── signal_reporter_b ──


class TestSignalReporterB:
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


class TestEngineBRunner:
    def test_emit_favorable(self):
        """Full pipeline with favorable inputs => EMIT."""
        output = run_engine_b(_emit_inputs())
        assert output.decision == EngineBDecision.EMIT
        assert output.conviction in (ConvictionLevelB.MEDIUM, ConvictionLevelB.LOW)
        assert output.tier_suggestion in (TierSuggestionB.TIER_2, TierSuggestionB.TIER_1)
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

    def test_no_trade_breakout_blocked(self):
        """Strong trend against reversion => BLOCKED."""
        output = run_engine_b(_emit_inputs(
            regime_trend_strength=0.9, volume_anomaly=0.8,
            structural_break=0.7, continuation_momentum=0.8,
        ))
        assert output.decision == EngineBDecision.NO_TRADE
        assert NoTradeReasonB.BREAKOUT_BLOCKED in output.no_trade_reasons

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

    def test_flow_coherence_feeds_runtime_conviction_path(self):
        weak_flow = run_engine_b(_emit_inputs(flow_coherence=0.0))
        strong_flow = run_engine_b(_emit_inputs(flow_coherence=1.0))
        assert weak_flow.decision == EngineBDecision.EMIT
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
