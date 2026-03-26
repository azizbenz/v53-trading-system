"""Tests for engines.engine_a — Build-6.

Covers all spec-mandated tests:
- Structure: signal in clean trend, no signal in dirty range, direction too weak
- Context: confirming, degraded, fatal
- Cost: feasible, marginal, infeasible, EV net check
- Conviction: high/medium/low/none, tier mapping, score decomposition, reproducibility
- Invalidation: price level, time expiry, always present
- Reporter: emit/no-trade tracking, emission rate, no-trade reasons
"""
import pytest

from engines.engine_a.structure_detector_a import (
    StructureVerdict,
    StructureInput,
    StructureResult,
    detect_structure,
)
from engines.engine_a.context_validator_a import (
    ContextVerdict,
    ContextInput,
    ContextResult,
    validate_context,
)
from engines.engine_a.cost_feasibility_a import (
    CostVerdict,
    CostInput,
    CostResult,
    check_cost_feasibility,
)
from engines.engine_a.conviction_builder_a import (
    ConvictionLevel,
    TierSuggestion,
    ConvictionInput,
    ConvictionResult,
    build_conviction,
)
from engines.engine_a.invalidation_mapper_a import (
    InvalidationType,
    InvalidationMap,
    build_invalidation,
)
from engines.engine_a.signal_reporter_a import (
    SignalDecision,
    NoTradeReason,
    SignalCandidateA,
    SignalReporterA,
)


# ── structure_detector_A ──


class TestStructureDetectorA:
    def test_signal_in_clean_trend(self):
        """Signal A emitted in clean trend context."""
        result = detect_structure(StructureInput(
            pair="BTCUSDT",
            direction_score=0.8,
            continuation_score=0.9,
            structure_quality=0.85,
            zone_proximity=0.5,
            trend_stability=0.8,
        ))
        assert result.verdict == StructureVerdict.FAVORABLE
        assert result.structure_score > 0.6

    def test_no_signal_in_dirty_range(self):
        """No signal A in dirty range."""
        result = detect_structure(StructureInput(
            pair="BTCUSDT",
            direction_score=0.05,
            continuation_score=0.1,
            structure_quality=0.1,
            zone_proximity=0.5,
            trend_stability=0.1,
        ))
        assert result.verdict == StructureVerdict.UNFAVORABLE

    def test_direction_too_weak(self):
        """Direction below minimum threshold → unfavorable."""
        result = detect_structure(StructureInput(
            pair="BTCUSDT",
            direction_score=0.1,
            continuation_score=0.9,
            structure_quality=0.9,
            zone_proximity=0.5,
            trend_stability=0.9,
        ))
        assert result.verdict == StructureVerdict.UNFAVORABLE
        assert "direction too weak" in result.reason

    def test_marginal_structure(self):
        result = detect_structure(StructureInput(
            pair="ETHUSDT",
            direction_score=0.4,
            continuation_score=0.4,
            structure_quality=0.3,
            zone_proximity=0.3,
            trend_stability=0.3,
        ))
        assert result.verdict == StructureVerdict.MARGINAL

    def test_negative_direction_uses_abs(self):
        """Negative direction (short) works via abs()."""
        result = detect_structure(StructureInput(
            pair="BTCUSDT",
            direction_score=-0.8,
            continuation_score=0.9,
            structure_quality=0.85,
            zone_proximity=0.5,
            trend_stability=0.8,
        ))
        assert result.verdict == StructureVerdict.FAVORABLE
        assert result.direction_strength == pytest.approx(0.8)

    def test_result_frozen(self):
        result = detect_structure(StructureInput(
            pair="BTC", direction_score=0.5, continuation_score=0.5,
            structure_quality=0.5, zone_proximity=0.5, trend_stability=0.5,
        ))
        with pytest.raises(Exception):
            result.verdict = "x"


# ── context_validator_A ──


class TestContextValidatorA:
    def test_confirming_context(self):
        result = validate_context(ContextInput(
            pair="BTCUSDT",
            regime_favorability=0.9,
            regime_confidence=0.8,
            pair_health=0.9,
            data_freshness=0.95,
            flow_coherence=0.8,
        ))
        assert result.verdict == ContextVerdict.CONFIRMING
        assert result.context_score > 0.65

    def test_degraded_context(self):
        result = validate_context(ContextInput(
            pair="BTCUSDT",
            regime_favorability=0.3,
            regime_confidence=0.3,
            pair_health=0.3,
            data_freshness=0.3,
            flow_coherence=0.3,
        ))
        assert result.verdict == ContextVerdict.DEGRADED

    def test_fatal_context(self):
        """Fatal context = all inputs near zero."""
        result = validate_context(ContextInput(
            pair="BTCUSDT",
            regime_favorability=0.05,
            regime_confidence=0.05,
            pair_health=0.05,
            data_freshness=0.05,
            flow_coherence=0.05,
        ))
        assert result.verdict == ContextVerdict.FATAL
        assert "fatal" in result.reason

    def test_neutral_context(self):
        result = validate_context(ContextInput(
            pair="ETHUSDT",
            regime_favorability=0.5,
            regime_confidence=0.5,
            pair_health=0.5,
            data_freshness=0.5,
            flow_coherence=0.5,
        ))
        assert result.verdict == ContextVerdict.NEUTRAL

    def test_result_frozen(self):
        result = validate_context(ContextInput(
            pair="BTC", regime_favorability=0.5, regime_confidence=0.5,
            pair_health=0.5, data_freshness=0.5, flow_coherence=0.5,
        ))
        with pytest.raises(Exception):
            result.context_score = 999.0


# ── cost_feasibility_A ──


class TestCostFeasibilityA:
    def test_feasible(self):
        result = check_cost_feasibility(CostInput(
            pair="BTCUSDT",
            expected_gain=0.005,
            expected_cost=0.001,
            candidate_size=1000.0,
        ))
        assert result.verdict == CostVerdict.FEASIBLE
        assert result.ev_net > 0

    def test_infeasible_cost_exceeds_gain(self):
        """No signal if cost impossible."""
        result = check_cost_feasibility(CostInput(
            pair="BTCUSDT",
            expected_gain=0.0003,
            expected_cost=0.001,
            candidate_size=1000.0,
        ))
        assert result.verdict == CostVerdict.INFEASIBLE
        assert "break-even" in result.reason

    def test_marginal_ce(self):
        """Gain > break-even but CE < CE_min → MARGINAL."""
        result = check_cost_feasibility(CostInput(
            pair="BTCUSDT",
            expected_gain=0.002,
            expected_cost=0.001,
            candidate_size=1000.0,
            holding_period=100.0,
            delta_safe=0.0005,
            ce_min=0.001,
        ))
        # gain 0.002 > break_even 0.0015 ✓, but CE = (0.002-0.001)/100 = 0.00001 < 0.001
        assert result.verdict == CostVerdict.MARGINAL
        assert "CE" in result.reason

    def test_ev_net_calculated(self):
        """EV_net = x · (E[g] - E[c])."""
        result = check_cost_feasibility(CostInput(
            pair="BTCUSDT",
            expected_gain=0.005,
            expected_cost=0.001,
            candidate_size=1000.0,
        ))
        assert result.ev_net == pytest.approx(1000.0 * (0.005 - 0.001))

    def test_ce_calculated(self):
        """CE = (E[g] - E[c]) / h."""
        result = check_cost_feasibility(CostInput(
            pair="BTCUSDT",
            expected_gain=0.005,
            expected_cost=0.001,
            candidate_size=1000.0,
            holding_period=2.0,
        ))
        assert result.ce_expected == pytest.approx((0.005 - 0.001) / 2.0)

    def test_result_frozen(self):
        result = check_cost_feasibility(CostInput(
            pair="BTC", expected_gain=0.01, expected_cost=0.001, candidate_size=100.0,
        ))
        with pytest.raises(Exception):
            result.verdict = "x"


# ── conviction_builder_A ──


class TestConvictionBuilderA:
    def test_high_conviction(self):
        result = build_conviction(ConvictionInput(
            pair="BTCUSDT", structure_score=0.9, context_score=0.8,
            flow_score=0.7, cost_preference_score=0.8,
        ))
        assert result.conviction == ConvictionLevel.HIGH
        assert result.tier_suggestion == TierSuggestion.TIER_3

    def test_medium_conviction(self):
        result = build_conviction(ConvictionInput(
            pair="BTCUSDT", structure_score=0.6, context_score=0.5,
            flow_score=0.3, cost_preference_score=0.4,
        ))
        assert result.conviction == ConvictionLevel.MEDIUM
        assert result.tier_suggestion == TierSuggestion.TIER_2

    def test_low_conviction(self):
        result = build_conviction(ConvictionInput(
            pair="BTCUSDT", structure_score=0.4, context_score=0.3,
            flow_score=0.1, cost_preference_score=0.1,
        ))
        assert result.conviction == ConvictionLevel.LOW
        assert result.tier_suggestion == TierSuggestion.TIER_1

    def test_no_conviction(self):
        result = build_conviction(ConvictionInput(
            pair="BTCUSDT", structure_score=0.1, context_score=0.1,
            flow_score=0.0, cost_preference_score=0.0,
        ))
        assert result.conviction == ConvictionLevel.NONE
        assert result.tier_suggestion == TierSuggestion.NO_TRADE

    def test_score_decomposition_visible(self):
        """Components of score visible in block_scores."""
        result = build_conviction(ConvictionInput(
            pair="BTCUSDT", structure_score=0.8, context_score=0.6,
            flow_score=0.5, cost_preference_score=0.7,
        ))
        assert "structure" in result.block_scores
        assert "context" in result.block_scores
        assert "flow" in result.block_scores
        assert "cost_preference" in result.block_scores

    def test_reproducibility(self):
        """Same inputs → same score."""
        kwargs = dict(pair="BTCUSDT", structure_score=0.7, context_score=0.6,
                      flow_score=0.5, cost_preference_score=0.4)
        r1 = build_conviction(ConvictionInput(**kwargs))
        r2 = build_conviction(ConvictionInput(**kwargs))
        assert r1.raw_score == r2.raw_score
        assert r1.conviction == r2.conviction

    def test_version_stored(self):
        result = build_conviction(ConvictionInput(
            pair="BTC", structure_score=0.5, context_score=0.5,
            scoring_version="v3.0",
        ))
        assert result.scoring_version == "v3.0"

    def test_result_frozen(self):
        result = build_conviction(ConvictionInput(
            pair="BTC", structure_score=0.5, context_score=0.5,
        ))
        with pytest.raises(Exception):
            result.raw_score = 999.0


# ── invalidation_mapper_A ──


class TestInvalidationMapperA:
    def test_invalidation_present(self):
        """Every signal must have invalidation."""
        result = build_invalidation(
            pair="BTCUSDT", direction_score=0.8,
            entry_price=50000.0, atr=500.0,
        )
        assert result.has_invalidation is True
        assert len(result.rules) >= 2

    def test_long_invalidation_below_entry(self):
        result = build_invalidation(
            pair="BTCUSDT", direction_score=0.8,
            entry_price=50000.0, atr=500.0,
        )
        price_rules = [r for r in result.rules if r.invalidation_type == InvalidationType.PRICE_LEVEL]
        assert len(price_rules) == 1
        assert price_rules[0].level is not None
        assert price_rules[0].level < 50000.0

    def test_short_invalidation_above_entry(self):
        result = build_invalidation(
            pair="BTCUSDT", direction_score=-0.8,
            entry_price=50000.0, atr=500.0,
        )
        price_rules = [r for r in result.rules if r.invalidation_type == InvalidationType.PRICE_LEVEL]
        assert price_rules[0].level is not None
        assert price_rules[0].level > 50000.0

    def test_time_expiry_present(self):
        result = build_invalidation("BTC", 0.8, 50000.0, 500.0, holding_hours=6.0)
        time_rules = [r for r in result.rules if r.invalidation_type == InvalidationType.TIME_EXPIRY]
        assert len(time_rules) == 1
        assert time_rules[0].horizon_hours == 6.0

    def test_holding_hours_stored(self):
        result = build_invalidation("BTC", 0.8, 50000.0, 500.0, holding_hours=8.0)
        assert result.expected_holding_hours == 8.0

    def test_structure_break_always_present(self):
        result = build_invalidation("BTC", 0.8, 50000.0, 500.0)
        types = {r.invalidation_type for r in result.rules}
        assert InvalidationType.STRUCTURE_BREAK in types

    def test_primary_invalidation_set(self):
        result = build_invalidation("BTC", 0.8, 50000.0, 500.0)
        assert result.primary_invalidation != ""

    def test_result_frozen(self):
        result = build_invalidation("BTC", 0.8, 50000.0, 500.0)
        with pytest.raises(Exception):
            result.pair = "ETH"


# ── signal_reporter_A ──


class TestSignalReporterA:
    def test_initial_state(self):
        reporter = SignalReporterA()
        stats = reporter.get_stats()
        assert stats.total_evaluated == 0
        assert stats.emission_rate == 0.0

    def test_record_emit(self):
        reporter = SignalReporterA()
        reporter.record_emit(raw_score=0.75)
        stats = reporter.get_stats()
        assert stats.total_emitted == 1
        assert stats.mean_raw_score == pytest.approx(0.75)

    def test_record_no_trade(self):
        reporter = SignalReporterA()
        reporter.record_no_trade((NoTradeReason.STRUCTURE_UNFAVORABLE,))
        stats = reporter.get_stats()
        assert stats.total_no_trade == 1
        assert stats.no_trade_by_reason[NoTradeReason.STRUCTURE_UNFAVORABLE] == 1

    def test_emission_rate(self):
        reporter = SignalReporterA()
        reporter.record_emit(0.8)
        reporter.record_no_trade((NoTradeReason.COST_INFEASIBLE,))
        reporter.record_no_trade((NoTradeReason.CONTEXT_FATAL,))
        stats = reporter.get_stats()
        assert stats.emission_rate == pytest.approx(1 / 3)

    def test_no_trade_reasons_tracked(self):
        """Explicit no-trade reasons per category."""
        reporter = SignalReporterA()
        reporter.record_no_trade((NoTradeReason.STRUCTURE_UNFAVORABLE,))
        reporter.record_no_trade((NoTradeReason.COST_INFEASIBLE,))
        reporter.record_no_trade((NoTradeReason.COST_INFEASIBLE,))
        stats = reporter.get_stats()
        assert stats.no_trade_by_reason[NoTradeReason.COST_INFEASIBLE] == 2
        assert stats.no_trade_by_reason[NoTradeReason.STRUCTURE_UNFAVORABLE] == 1

    def test_signal_candidate_frozen(self):
        signal = SignalCandidateA(
            pair="BTCUSDT", decision=SignalDecision.EMIT, raw_score=0.8,
        )
        with pytest.raises(Exception):
            signal.raw_score = 999.0

    def test_no_trade_signal_has_reasons(self):
        signal = SignalCandidateA(
            pair="BTCUSDT",
            decision=SignalDecision.NO_TRADE,
            no_trade_reasons=(NoTradeReason.CONTEXT_FATAL,),
        )
        assert len(signal.no_trade_reasons) > 0
        assert signal.decision == SignalDecision.NO_TRADE
