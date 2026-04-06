"""Tests for engines.engine_a — Build-6.

Covers all spec-mandated tests:
- Structure: signal in clean trend, no signal in dirty range, direction too weak, zone_proximity used
- Context: confirming, degraded, fatal
- Cost: feasible, marginal, infeasible, EV net check
- Conviction: high/medium/low/none, tier mapping, score decomposition, reproducibility
- Invalidation: price level, time expiry, always present, short direction documented
- Reporter: emit/no-trade tracking, emission rate, no-trade reasons, typed enums
- E2E: full pipeline emit, full pipeline no-trade
"""
import pytest

from engines.engine_a.structure_detector_a import (
    StructureVerdict,
    StructureInput,
    detect_structure,
)
from engines.engine_a.context_validator_a import (
    ContextVerdict,
    ContextInput,
    validate_context,
)
from engines.engine_a.cost_feasibility_a import (
    CostVerdict,
    CostInput,
    check_cost_feasibility,
)
from engines.engine_a.conviction_builder_a import (
    ConvictionLevel,
    TierSuggestion,
    ConvictionInput,
    build_conviction,
)
from engines.engine_a.invalidation_mapper_a import (
    InvalidationType,
    build_invalidation,
)
from engines.engine_a.signal_reporter_a import (
    SignalDecision,
    NoTradeReason,
    SignalCandidateA,
    SignalReporterA,
)
from engines.engine_a.engine_a_runner import (
    EngineADecision,
    EngineAInput,
    EngineAOutput,
    EngineALogEntry,
    run_engine_a,
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
            zone_proximity=0.7,
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
            zone_proximity=0.1,
            trend_stability=0.1,
        ))
        assert result.verdict == StructureVerdict.UNFAVORABLE

    def test_direction_too_weak(self):
        """Direction below minimum threshold -> unfavorable."""
        result = detect_structure(StructureInput(
            pair="BTCUSDT",
            direction_score=0.1,
            continuation_score=0.9,
            structure_quality=0.9,
            zone_proximity=0.9,
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

    def test_negative_direction_abs_in_score(self):
        """Structure detector still uses abs() internally for score calc.
        But the runner rejects direction_score <= 0 before reaching here (long-only).
        This test validates the math layer only."""
        result = detect_structure(StructureInput(
            pair="BTCUSDT",
            direction_score=-0.8,
            continuation_score=0.9,
            structure_quality=0.85,
            zone_proximity=0.7,
            trend_stability=0.8,
        ))
        assert result.direction_strength == pytest.approx(0.8)

    def test_zone_proximity_affects_score(self):
        """zone_proximity is used in the score formula (P1 fix #5)."""
        base = dict(pair="BTCUSDT", direction_score=0.6, continuation_score=0.5,
                    structure_quality=0.5, trend_stability=0.5)
        low_zone = detect_structure(StructureInput(**base, zone_proximity=0.0))
        high_zone = detect_structure(StructureInput(**base, zone_proximity=1.0))
        assert high_zone.structure_score > low_zone.structure_score

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
        """Gain > break-even but CE < CE_min -> MARGINAL."""
        result = check_cost_feasibility(CostInput(
            pair="BTCUSDT",
            expected_gain=0.002,
            expected_cost=0.001,
            candidate_size=1000.0,
            holding_period=100.0,
            delta_safe=0.0005,
            ce_min=0.001,
        ))
        assert result.verdict == CostVerdict.MARGINAL
        assert "CE" in result.reason

    def test_ev_net_calculated(self):
        """EV_net = x * (E[g] - E[c])."""
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
        """Same inputs -> same score."""
        kwargs = dict(pair="BTCUSDT", structure_score=0.7, context_score=0.6,
                      flow_score=0.5, cost_preference_score=0.4)
        r1 = build_conviction(ConvictionInput(**kwargs))
        r2 = build_conviction(ConvictionInput(**kwargs))
        assert r1.raw_score == r2.raw_score
        assert r1.conviction == r2.conviction

    def test_market_physics_confirmation_and_penalties_shift_score(self):
        base = build_conviction(ConvictionInput(
            pair="BTCUSDT",
            structure_score=0.7,
            context_score=0.6,
            flow_score=0.5,
            cost_preference_score=0.5,
        ))
        enriched = build_conviction(ConvictionInput(
            pair="BTCUSDT",
            structure_score=0.7,
            context_score=0.6,
            flow_score=0.5,
            cost_preference_score=0.5,
            delta_confirmation=1.0,
            competition_density=0.0,
        ))
        penalized = build_conviction(ConvictionInput(
            pair="BTCUSDT",
            structure_score=0.7,
            context_score=0.6,
            flow_score=0.5,
            cost_preference_score=0.5,
            execution_fragility=1.0,
            market_toxicity=1.0,
            spread_regime_penalty=1.0,
        ))
        assert enriched.raw_score > base.raw_score
        assert penalized.raw_score < base.raw_score
        assert enriched.block_scores["delta_confirmation"] == pytest.approx(1.0)
        assert penalized.block_scores["execution_fragility"] == pytest.approx(1.0)
        assert "fragility_score" in penalized.block_scores
        assert "toxicity_score" in penalized.block_scores
        assert "execution_survivability_score" in penalized.block_scores
        assert "micro_friction_score" in penalized.block_scores

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

    def test_short_branch_defensive_only(self):
        """Short branch exists defensively but is unreachable in normal flow.
        Runner rejects direction_score <= 0 before invalidation mapping.
        This tests the math layer directly for coverage."""
        result = build_invalidation(
            pair="BTCUSDT", direction_score=-0.8,
            entry_price=50000.0, atr=500.0,
        )
        price_rules = [r for r in result.rules if r.invalidation_type == InvalidationType.PRICE_LEVEL]
        assert price_rules[0].level is not None
        # Defensive: short maps above entry
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

    def test_signal_candidate_typed_enums(self):
        """P1 fix #6: conviction/tier use enums, not raw strings."""
        signal = SignalCandidateA(
            pair="BTCUSDT",
            decision=SignalDecision.EMIT,
            raw_score=0.8,
            conviction=ConvictionLevel.HIGH,
            tier_suggestion=TierSuggestion.TIER_3,
        )
        assert signal.conviction == ConvictionLevel.HIGH
        assert signal.tier_suggestion == TierSuggestion.TIER_3

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


# ── engine_a_runner (E2E orchestration) ──


def _make_good_inputs(**overrides) -> EngineAInput:
    """Helper: inputs that produce a full EMIT through the pipeline."""
    defaults = dict(
        pair="BTCUSDT",
        direction_score=0.8,
        continuation_score=0.9,
        structure_quality=0.85,
        zone_proximity=0.7,
        trend_stability=0.8,
        regime="trending_up",
        regime_favorability=0.9,
        regime_confidence=0.8,
        pair_health=0.9,
        data_freshness=0.95,
        flow_coherence=0.8,
        flow_score=0.4,
        cost_preference_score=0.5,
        expected_gain=0.005,
        expected_cost=0.001,
        candidate_size=1000.0,
        holding_period=4.0,
        entry_price=50000.0,
        atr=500.0,
        scoring_version="v1.0",
    )
    defaults.update(overrides)
    return EngineAInput(**defaults)


class TestEngineARunner:
    def test_e2e_emit_full_pipeline(self):
        """E2E: favorable structure + confirming context + feasible cost + conviction => EMIT."""
        output = run_engine_a(_make_good_inputs())

        assert output.decision == EngineADecision.EMIT
        assert output.pair == "BTCUSDT"
        assert output.engine_id == "engine_a"
        assert output.raw_score > 0
        assert len(output.block_scores) > 0
        assert output.conviction != ConvictionLevel.NONE
        assert output.tier_suggestion != TierSuggestion.NO_TRADE
        assert output.expected_cost > 0
        assert output.ce_expected > 0
        assert output.ev_net > 0
        assert output.invalidation is not None
        assert output.invalidation.has_invalidation is True
        assert output.holding_hours > 0
        assert output.scoring_version == "v1.0"
        assert output.no_trade_reasons == ()
        assert output.structure_verdict == StructureVerdict.FAVORABLE
        assert output.context_verdict == ContextVerdict.CONFIRMING
        assert output.cost_verdict == CostVerdict.FEASIBLE

    def test_e2e_long_only_rejects_negative_direction(self):
        """Long-only: direction_score < 0 => immediate NO_TRADE."""
        output = run_engine_a(_make_good_inputs(direction_score=-0.8))
        assert output.decision == EngineADecision.NO_TRADE
        assert NoTradeReason.NON_LONG_DIRECTION in output.no_trade_reasons

    def test_e2e_long_only_rejects_zero_direction(self):
        """Long-only: direction_score == 0 => NO_TRADE."""
        output = run_engine_a(_make_good_inputs(direction_score=0.0))
        assert output.decision == EngineADecision.NO_TRADE
        assert NoTradeReason.NON_LONG_DIRECTION in output.no_trade_reasons

    def test_e2e_long_only_log_present(self):
        """Long-only rejection produces structured log."""
        output = run_engine_a(_make_good_inputs(direction_score=-0.5))
        events = {log.event for log in output.log_entries}
        assert "engine_a_no_trade" in events

    def test_e2e_no_trade_structure_unfavorable(self):
        """E2E no-trade: dirty structure => NO_TRADE with explicit reason."""
        output = run_engine_a(_make_good_inputs(
            direction_score=0.05,
            continuation_score=0.1,
            structure_quality=0.1,
            zone_proximity=0.1,
            trend_stability=0.1,
        ))
        assert output.decision == EngineADecision.NO_TRADE
        assert NoTradeReason.STRUCTURE_UNFAVORABLE in output.no_trade_reasons

    def test_e2e_no_trade_context_fatal(self):
        """E2E no-trade: fatal context => NO_TRADE."""
        output = run_engine_a(_make_good_inputs(
            regime_favorability=0.02,
            regime_confidence=0.02,
            pair_health=0.02,
            data_freshness=0.02,
            flow_coherence=0.02,
        ))
        assert output.decision == EngineADecision.NO_TRADE
        assert NoTradeReason.CONTEXT_FATAL in output.no_trade_reasons

    def test_e2e_no_trade_cost_infeasible(self):
        """E2E no-trade: cost kills edge => NO_TRADE."""
        output = run_engine_a(_make_good_inputs(
            expected_gain=0.0001,
            expected_cost=0.005,
        ))
        assert output.decision == EngineADecision.NO_TRADE
        assert NoTradeReason.COST_INFEASIBLE in output.no_trade_reasons

    def test_e2e_structured_logs_present(self):
        """Spec section 19: structured logs must be present in output."""
        output = run_engine_a(_make_good_inputs())
        assert len(output.log_entries) > 0
        events = {log.event for log in output.log_entries}
        assert "engine_a_structure_evaluated" in events
        assert "engine_a_context_evaluated" in events
        assert "engine_a_cost_checked" in events
        assert "engine_a_conviction_built" in events
        assert "engine_a_invalidation_built" in events
        assert "engine_a_signal_emitted" in events

    def test_e2e_flow_and_cost_preference_are_used_in_runtime_path(self):
        """Build-6 guardrail: runtime path must not drop flow/cost-preference inputs."""
        base = _make_good_inputs(flow_score=0.0, cost_preference_score=0.0)
        enriched = _make_good_inputs(flow_score=0.8, cost_preference_score=0.9)

        base_output = run_engine_a(base)
        enriched_output = run_engine_a(enriched)

        assert base_output.decision == EngineADecision.EMIT
        assert enriched_output.decision == EngineADecision.EMIT
        assert enriched_output.raw_score > base_output.raw_score
        assert enriched_output.block_scores["flow"] == pytest.approx(0.8)
        assert enriched_output.block_scores["cost_preference"] == pytest.approx(0.9)

    def test_e2e_market_physics_inputs_shift_conviction_path(self):
        base_output = run_engine_a(_make_good_inputs())
        enriched_output = run_engine_a(_make_good_inputs(
            delta_confirmation=1.0,
            competition_density=0.0,
        ))
        penalized_output = run_engine_a(_make_good_inputs(
            execution_fragility=1.0,
            market_toxicity=1.0,
            spread_regime_penalty=1.0,
        ))

        assert enriched_output.decision == EngineADecision.EMIT
        assert penalized_output.decision == EngineADecision.EMIT
        assert enriched_output.raw_score > base_output.raw_score
        assert penalized_output.raw_score < base_output.raw_score
        assert enriched_output.block_scores["delta_confirmation"] == pytest.approx(1.0)
        assert penalized_output.block_scores["market_toxicity"] == pytest.approx(1.0)
        assert "execution_survivability_score" in penalized_output.block_scores
        assert penalized_output.block_scores["micro_friction_score"] > 0.0

    def test_e2e_no_trade_logs_present(self):
        """No-trade path also produces structured logs."""
        output = run_engine_a(_make_good_inputs(
            direction_score=0.05,
            continuation_score=0.1,
            structure_quality=0.1,
            zone_proximity=0.1,
            trend_stability=0.1,
        ))
        events = {log.event for log in output.log_entries}
        assert "engine_a_structure_evaluated" in events
        assert "engine_a_no_trade" in events

    def test_e2e_emit_log_has_full_fields(self):
        """The final emit log has all required audit fields (spec section 19)."""
        output = run_engine_a(_make_good_inputs())
        emit_logs = [l for l in output.log_entries if l.event == "engine_a_signal_emitted"]
        assert len(emit_logs) == 1
        log = emit_logs[0]
        assert log.pair == "BTCUSDT"
        assert log.regime == "trending_up"
        assert log.raw_score > 0
        assert log.expected_cost > 0
        assert log.ce_expected > 0
        assert log.ev_net > 0
        assert log.conviction != ""
        assert log.tier != ""
        assert log.invalidation != ""
        assert log.holding_hours > 0
        assert log.penalized_score == pytest.approx(log.raw_score)
        assert log.scoring_version == "v1.0"

    def test_e2e_output_frozen(self):
        """EngineAOutput is immutable."""
        output = run_engine_a(_make_good_inputs())
        with pytest.raises(Exception):
            output.decision = "x"

    def test_e2e_log_entry_frozen(self):
        """EngineALogEntry is immutable."""
        log = EngineALogEntry(event="test", pair="BTC")
        with pytest.raises(Exception):
            log.event = "x"
