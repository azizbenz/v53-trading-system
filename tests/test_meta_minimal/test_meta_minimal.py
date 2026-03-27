"""
Build-9 tests — meta_minimal (dtr_core + cra_monitor + break_even_dashboard + edge_tracker).
"""

from __future__ import annotations

import math

import pytest

# ── dtr_core imports ──
from meta_minimal.dtr_core.decision_state_encoder import (
    DecisionState,
    encode_state,
    state_severity,
)
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord, build_dtr
from meta_minimal.dtr_core.cause_chain_assembler import CauseChain, assemble_cause_chain
from meta_minimal.dtr_core.trace_persistence_layer import DTRStore
from meta_minimal.dtr_core.dtr_reporter import DTRSummary, build_dtr_summary

# ── cra_monitor imports ──
from meta_minimal.cra_monitor.reduction_trace_reader import ReductionTrace, read_reduction
from meta_minimal.cra_monitor.phantom_risk_estimator import PhantomRiskResult, estimate_phantom_risk
from meta_minimal.cra_monitor.sterilization_classifier import (
    SterilizationClass,
    classify_sterilization,
)
from meta_minimal.cra_monitor.cra_alert_builder import CRAAlert, CRAAlertLevel, build_alerts
from meta_minimal.cra_monitor.cra_reporter import CRAReport, build_cra_report

# ── break_even_dashboard imports ──
from meta_minimal.break_even_dashboard.expected_break_even_calculator import (
    compute_expected_break_even,
)
from meta_minimal.break_even_dashboard.realized_break_even_calculator import (
    compute_realized_break_even,
)
from meta_minimal.break_even_dashboard.cost_distribution_aggregator import aggregate_costs
from meta_minimal.break_even_dashboard.motor_pair_break_even_view import (
    build_break_even_view,
    build_views_by_engine_and_pair,
)
from meta_minimal.break_even_dashboard.break_even_reporter import build_break_even_report

# ── edge_tracker imports ──
from meta_minimal.edge_tracker_prudent_minimal.return_aggregator import aggregate_returns
from meta_minimal.edge_tracker_prudent_minimal.sample_size_tracker import (
    SampleAdequacy,
    assess_sample_size,
)
from meta_minimal.edge_tracker_prudent_minimal.uncertainty_estimator import estimate_uncertainty
from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import (
    EdgeStatus,
    classify_edge,
)
from meta_minimal.edge_tracker_prudent_minimal.edge_reporter import build_edge_report


# ═══════════════════════════════════════════════════════════════
# 1. dtr_core / decision_state_encoder
# ═══════════════════════════════════════════════════════════════

class TestDecisionStateEncoder:
    def test_executed_highest_priority(self):
        s = encode_state(hard_blocked=True, was_executed=True)
        assert s == DecisionState.EXECUTED

    def test_phantom(self):
        s = encode_state(selected=True, is_phantom=True)
        assert s == DecisionState.PHANTOM

    def test_reduced(self):
        s = encode_state(selected=True, was_reduced=True)
        assert s == DecisionState.REDUCED

    def test_selected(self):
        s = encode_state(selected=True)
        assert s == DecisionState.SELECTED

    def test_ranking_rejected(self):
        s = encode_state(ranking_rejected=True)
        assert s == DecisionState.REJECTED_RANKING

    def test_hard_blocked(self):
        s = encode_state(hard_blocked=True)
        assert s == DecisionState.HARD_BLOCKED

    def test_default_evaluated(self):
        s = encode_state()
        assert s == DecisionState.EVALUATED

    def test_severity_ordering(self):
        assert state_severity(DecisionState.EXECUTED) > state_severity(DecisionState.PHANTOM)
        assert state_severity(DecisionState.PHANTOM) > state_severity(DecisionState.SELECTED)


# ═══════════════════════════════════════════════════════════════
# 2. dtr_core / dtr_record_builder
# ═══════════════════════════════════════════════════════════════

class TestDTRRecordBuilder:
    def test_build_selected_dtr(self):
        dtr = build_dtr(
            dtr_id="dtr_001", pair="BTC/USDT", engine_id="engine_a",
            decision_state=DecisionState.SELECTED, raw_score=0.8,
            penalized_score=0.7, final_score=0.7, timestamp=1000.0,
        )
        assert dtr.pair == "BTC/USDT"
        assert dtr.decision_state == DecisionState.SELECTED
        assert dtr.schema_version == "1.0"

    def test_build_blocked_dtr(self):
        dtr = build_dtr(
            dtr_id="dtr_002", pair="ETH/USDT", engine_id="engine_b",
            decision_state=DecisionState.HARD_BLOCKED, hard_blocked=True,
            hard_block_reasons=("stale_data", "no_cluster"), timestamp=1000.0,
        )
        assert dtr.hard_blocked is True
        assert len(dtr.hard_block_reasons) == 2

    def test_build_phantom_dtr(self):
        dtr = build_dtr(
            dtr_id="dtr_003", pair="X/USDT", engine_id="engine_a",
            decision_state=DecisionState.PHANTOM,
            candidate_size=100.0, final_size=5.0, timestamp=1000.0,
        )
        assert dtr.decision_state == DecisionState.PHANTOM
        assert dtr.final_size == 5.0

    def test_timestamp_auto_filled(self):
        dtr = build_dtr(dtr_id="t", pair="X", engine_id="a", decision_state=DecisionState.EVALUATED)
        assert dtr.timestamp > 0.0


# ═══════════════════════════════════════════════════════════════
# 3. dtr_core / cause_chain_assembler
# ═══════════════════════════════════════════════════════════════

class TestCauseChainAssembler:
    def test_full_chain(self):
        cc = assemble_cause_chain(
            score_step="raw=0.8",
            penalty_steps=("stale:-0.1",),
            penalty_total=0.1,
            ranking_step="rank=3",
            allocation_step="size=50",
        )
        assert len(cc.steps) == 4
        assert cc.penalty_total == 0.1

    def test_blocker_chain(self):
        cc = assemble_cause_chain(blocker_steps=("no_cluster", "stale_data"))
        assert cc.blocker_count == 2
        assert cc.primary_reason == "blocked: no_cluster"

    def test_empty_chain(self):
        cc = assemble_cause_chain()
        assert len(cc.steps) == 0
        assert cc.primary_reason == ""

    def test_reduction_reason(self):
        cc = assemble_cause_chain(reduction_reason="gross_cap")
        assert cc.was_reduced is True
        assert cc.reduction_reason == "gross_cap"


# ═══════════════════════════════════════════════════════════════
# 4. dtr_core / trace_persistence_layer
# ═══════════════════════════════════════════════════════════════

class TestTracePersistenceLayer:
    def _dtr(self, dtr_id="d1", pair="BTC/USDT"):
        return build_dtr(dtr_id=dtr_id, pair=pair, engine_id="engine_a",
                         decision_state=DecisionState.SELECTED, timestamp=1000.0)

    def test_persist_and_retrieve(self):
        store = DTRStore()
        assert store.persist(self._dtr())
        assert store.size == 1

    def test_get_by_pair(self):
        store = DTRStore()
        store.persist(self._dtr("a", "BTC/USDT"))
        store.persist(self._dtr("b", "ETH/USDT"))
        assert len(store.get_by_pair("BTC/USDT")) == 1

    def test_get_by_engine(self):
        store = DTRStore()
        store.persist(self._dtr())
        assert len(store.get_by_engine("engine_a")) == 1

    def test_batch_persist(self):
        store = DTRStore()
        n = store.persist_batch((self._dtr("a"), self._dtr("b"), self._dtr("c")))
        assert n == 3
        assert store.size == 3

    def test_stats_no_drops(self):
        store = DTRStore()
        store.persist(self._dtr())
        stats = store.get_stats()
        assert stats.total_persisted == 1
        assert stats.loss_rate == 0.0


# ═══════════════════════════════════════════════════════════════
# 5. dtr_core / dtr_reporter
# ═══════════════════════════════════════════════════════════════

class TestDTRReporter:
    def test_summary_counts(self):
        records = (
            build_dtr("a", "BTC", "engine_a", DecisionState.SELECTED, timestamp=1.0),
            build_dtr("b", "ETH", "engine_b", DecisionState.HARD_BLOCKED, timestamp=2.0),
            build_dtr("c", "BTC", "engine_a", DecisionState.PHANTOM, timestamp=3.0),
        )
        s = build_dtr_summary(records, total_opportunities=5)
        assert s.total_records == 3
        assert s.by_state["selected"] == 1
        assert s.by_state["hard_blocked"] == 1
        assert s.by_state["phantom"] == 1
        assert s.by_engine["engine_a"] == 2
        assert s.by_pair["BTC"] == 2
        assert s.dtr_coverage == pytest.approx(0.6)

    def test_empty_summary(self):
        s = build_dtr_summary((), total_opportunities=0)
        assert s.total_records == 0
        assert s.dtr_coverage == 0.0


# ═══════════════════════════════════════════════════════════════
# 6. cra_monitor / reduction_trace_reader
# ═══════════════════════════════════════════════════════════════

class TestReductionTraceReader:
    def test_read_reduction(self):
        t = read_reduction("BTC", "engine_a", original_size=100.0, final_size=50.0)
        assert t.multiplier == pytest.approx(0.5)

    def test_zero_original_size(self):
        t = read_reduction("X", "a", original_size=0.0, final_size=0.0)
        assert t.multiplier == 0.0

    def test_no_reduction(self):
        t = read_reduction("X", "a", original_size=100.0, final_size=100.0)
        assert t.multiplier == pytest.approx(1.0)


# ═══════════════════════════════════════════════════════════════
# 7. cra_monitor / phantom_risk_estimator
# ═══════════════════════════════════════════════════════════════

class TestPhantomRiskEstimator:
    def _trace(self, final=50.0, ce=0.001, hours=2.0, cost=0.05):
        return ReductionTrace(
            pair="X", engine_id="a", original_size=100.0,
            final_size=final, multiplier=final / 100.0,
            ce_expected=ce, holding_hours=hours, expected_cost=cost,
        )

    def test_viable_trade_low_risk(self):
        r = estimate_phantom_risk(self._trace(final=100.0, ce=0.01, hours=2.0, cost=0.05))
        assert not r.is_high_risk
        assert r.net_expected > 0.0

    def test_tiny_trade_high_risk(self):
        r = estimate_phantom_risk(self._trace(final=1.0, ce=0.0001, hours=1.0, cost=0.05))
        assert r.is_high_risk
        assert r.phantom_risk_score > 0.5

    def test_high_cost_sterilizes(self):
        r = estimate_phantom_risk(self._trace(final=50.0, ce=0.0001, hours=1.0, cost=5.0))
        assert r.is_high_risk


# ═══════════════════════════════════════════════════════════════
# 8. cra_monitor / sterilization_classifier
# ═══════════════════════════════════════════════════════════════

class TestSterilizationClassifier:
    def _trace_and_risk(self, mult=1.0, net=1.0, risk_score=0.1):
        trace = ReductionTrace(
            pair="X", engine_id="a", original_size=100.0,
            final_size=100.0 * mult, multiplier=mult,
        )
        risk = PhantomRiskResult(
            pair="X", engine_id="a", expected_pnl=2.0,
            operational_cost=1.0, net_expected=net,
            phantom_risk_score=risk_score,
        )
        return trace, risk

    def test_healthy(self):
        t, r = self._trace_and_risk(mult=0.8, net=1.0, risk_score=0.1)
        c = classify_sterilization(t, r)
        assert c.classification == SterilizationClass.HEALTHY

    def test_reduced_viable(self):
        t, r = self._trace_and_risk(mult=0.3, net=1.0, risk_score=0.1)
        c = classify_sterilization(t, r)
        assert c.classification == SterilizationClass.REDUCED_VIABLE

    def test_phantom_probable(self):
        t, r = self._trace_and_risk(mult=0.2, net=0.3, risk_score=0.75)
        c = classify_sterilization(t, r)
        assert c.classification == SterilizationClass.PHANTOM_PROBABLE

    def test_phantom_confirmed(self):
        t, r = self._trace_and_risk(mult=0.05, net=-0.5, risk_score=0.95)
        c = classify_sterilization(t, r)
        assert c.classification == SterilizationClass.PHANTOM_CONFIRMED

    def test_negative_net_always_confirmed(self):
        t, r = self._trace_and_risk(mult=1.0, net=-0.1, risk_score=0.5)
        c = classify_sterilization(t, r)
        assert c.classification == SterilizationClass.PHANTOM_CONFIRMED


# ═══════════════════════════════════════════════════════════════
# 9. cra_monitor / cra_alert_builder
# ═══════════════════════════════════════════════════════════════

class TestCRAAlertBuilder:
    def _steril(self, engine, pair, cls):
        from meta_minimal.cra_monitor.sterilization_classifier import SterilizationResult
        return SterilizationResult(
            pair=pair, engine_id=engine, classification=cls,
            multiplier=0.5, phantom_risk_score=0.8,
            reason="test_reason",
        )

    def test_no_alert_all_healthy(self):
        results = tuple(
            self._steril("a", f"P{i}", SterilizationClass.HEALTHY) for i in range(10)
        )
        alerts = build_alerts(results)
        assert len(alerts) == 0

    def test_warning_alert(self):
        # 3 out of 10 = 30% > 20% warning threshold
        results = tuple(
            self._steril("a", "P1", SterilizationClass.HEALTHY) for _ in range(7)
        ) + tuple(
            self._steril("a", "P1", SterilizationClass.PHANTOM_CONFIRMED) for _ in range(3)
        )
        alerts = build_alerts(results)
        assert any(a.alert_level == CRAAlertLevel.WARNING for a in alerts)

    def test_critical_alert(self):
        # 5 out of 10 = 50% > 40% critical threshold
        results = tuple(
            self._steril("a", "P1", SterilizationClass.HEALTHY) for _ in range(5)
        ) + tuple(
            self._steril("a", "P1", SterilizationClass.PHANTOM_CONFIRMED) for _ in range(5)
        )
        alerts = build_alerts(results)
        assert any(a.alert_level == CRAAlertLevel.CRITICAL for a in alerts)


# ═══════════════════════════════════════════════════════════════
# 10. cra_monitor / cra_reporter
# ═══════════════════════════════════════════════════════════════

class TestCRAReporter:
    def test_report_counts(self):
        from meta_minimal.cra_monitor.sterilization_classifier import SterilizationResult
        results = (
            SterilizationResult(pair="A", engine_id="a", classification=SterilizationClass.HEALTHY, multiplier=1.0, phantom_risk_score=0.1),
            SterilizationResult(pair="B", engine_id="a", classification=SterilizationClass.PHANTOM_CONFIRMED, multiplier=0.1, phantom_risk_score=0.95),
            SterilizationResult(pair="C", engine_id="b", classification=SterilizationClass.REDUCED_VIABLE, multiplier=0.4, phantom_risk_score=0.3),
        )
        r = build_cra_report(results)
        assert r.total_trades == 3
        assert r.healthy_count == 1
        assert r.phantom_confirmed_count == 1
        assert r.reduced_viable_count == 1
        assert r.sterilization_rate == pytest.approx(1 / 3)

    def test_engine_rate(self):
        from meta_minimal.cra_monitor.sterilization_classifier import SterilizationResult
        results = (
            SterilizationResult(pair="A", engine_id="a", classification=SterilizationClass.PHANTOM_CONFIRMED, multiplier=0.1, phantom_risk_score=0.95),
            SterilizationResult(pair="B", engine_id="b", classification=SterilizationClass.HEALTHY, multiplier=1.0, phantom_risk_score=0.1),
        )
        r = build_cra_report(results)
        assert r.sterilization_rate_by_engine["a"] == 1.0
        assert r.sterilization_rate_by_engine["b"] == 0.0


# ═══════════════════════════════════════════════════════════════
# 11. break_even_dashboard / expected_break_even
# ═══════════════════════════════════════════════════════════════

class TestExpectedBreakEven:
    def test_simple_be(self):
        r = compute_expected_break_even(
            "BTC", "engine_a",
            expected_fee=0.001, expected_spread=0.0005,
            expected_slippage=0.0002, expected_adverse=0.0003,
        )
        assert r.simple_be == pytest.approx(0.002)

    def test_prudent_be_uses_p90(self):
        r = compute_expected_break_even(
            "BTC", "engine_a",
            expected_fee=0.001,
            spread_p90=0.002, slippage_p90=0.001, adverse_p90=0.001,
        )
        assert r.prudent_be == pytest.approx(0.005)
        assert r.prudent_be > r.simple_be


# ═══════════════════════════════════════════════════════════════
# 12. break_even_dashboard / realized_break_even
# ═══════════════════════════════════════════════════════════════

class TestRealizedBreakEven:
    def test_profitable_trade(self):
        r = compute_realized_break_even("BTC", "a", realized_cost=0.002, expected_cost=0.001, gross_return=0.005)
        assert r.was_profitable
        assert r.net_return == pytest.approx(0.003)
        assert r.cost_drift == pytest.approx(0.001)

    def test_unprofitable_trade(self):
        r = compute_realized_break_even("X", "a", realized_cost=0.005, expected_cost=0.002, gross_return=0.003)
        assert not r.was_profitable
        assert r.net_return == pytest.approx(-0.002)


# ═══════════════════════════════════════════════════════════════
# 13. break_even_dashboard / cost_distribution_aggregator
# ═══════════════════════════════════════════════════════════════

class TestCostDistributionAggregator:
    def test_basic_aggregation(self):
        costs = tuple(float(i) for i in range(1, 11))  # 1..10
        r = aggregate_costs("engine_a", costs)
        assert r.sample_size == 10
        assert r.mean_cost == pytest.approx(5.5)
        assert r.min_cost == 1.0
        assert r.max_cost == 10.0

    def test_p90_p95(self):
        costs = tuple(float(i) for i in range(1, 101))  # 1..100
        r = aggregate_costs("all", costs)
        assert r.p90_cost == pytest.approx(90.1, abs=0.5)
        assert r.p95_cost == pytest.approx(95.05, abs=0.5)

    def test_empty(self):
        r = aggregate_costs("x", ())
        assert r.sample_size == 0
        assert r.mean_cost == 0.0


# ═══════════════════════════════════════════════════════════════
# 14. break_even_dashboard / motor_pair_break_even_view
# ═══════════════════════════════════════════════════════════════

class TestBreakEvenView:
    def test_single_scope(self):
        records = (
            compute_realized_break_even("BTC", "a", 0.002, 0.001, 0.005),
            compute_realized_break_even("BTC", "a", 0.003, 0.001, 0.002),
        )
        v = build_break_even_view("engine_a", records)
        assert v.sample_size == 2
        assert v.profitable_rate == 0.5

    def test_views_by_engine_and_pair(self):
        records = (
            compute_realized_break_even("BTC", "a", 0.002, 0.001, 0.005),
            compute_realized_break_even("ETH", "b", 0.003, 0.002, 0.004),
        )
        views = build_views_by_engine_and_pair(records)
        # 2 engines + 2 pairs = 4 views
        assert len(views) == 4


# ═══════════════════════════════════════════════════════════════
# 15. break_even_dashboard / break_even_reporter
# ═══════════════════════════════════════════════════════════════

class TestBreakEvenReporter:
    def test_no_drift(self):
        from meta_minimal.break_even_dashboard.motor_pair_break_even_view import BreakEvenView
        views = (
            BreakEvenView(scope="a", sample_size=10, mean_realized_cost=0.002, mean_expected_cost=0.002, mean_cost_drift=0.0, profitable_rate=0.5),
        )
        r = build_break_even_report(views)
        assert not r.has_cost_drift_alert

    def test_drift_detected(self):
        from meta_minimal.break_even_dashboard.motor_pair_break_even_view import BreakEvenView
        views = (
            BreakEvenView(scope="engine_a", sample_size=10, mean_realized_cost=0.004, mean_expected_cost=0.002, mean_cost_drift=0.002, profitable_rate=0.3),
        )
        r = build_break_even_report(views)
        # drift = |0.002| / 0.002 = 1.0 > 0.20
        assert r.has_cost_drift_alert
        assert "engine_a" in r.cost_drift_alert_scopes


# ═══════════════════════════════════════════════════════════════
# 16. edge_tracker / return_aggregator
# ═══════════════════════════════════════════════════════════════

class TestReturnAggregator:
    def test_basic_aggregation(self):
        r = aggregate_returns("a", (0.01, 0.02, 0.03), (0.005, 0.005, 0.005))
        assert r.sample_size == 3
        assert r.mean_net == pytest.approx(0.015)
        assert r.mean_cost == pytest.approx(0.005)

    def test_mismatched_lengths(self):
        r = aggregate_returns("a", (0.01,), (0.005, 0.005))
        assert r.sample_size == 0

    def test_empty(self):
        r = aggregate_returns("a", (), ())
        assert r.sample_size == 0


# ═══════════════════════════════════════════════════════════════
# 17. edge_tracker / sample_size_tracker
# ═══════════════════════════════════════════════════════════════

class TestSampleSizeTracker:
    def test_insufficient(self):
        r = assess_sample_size("a", 5)
        assert r.adequacy == SampleAdequacy.INSUFFICIENT

    def test_marginal(self):
        r = assess_sample_size("a", 20)
        assert r.adequacy == SampleAdequacy.MARGINAL

    def test_adequate(self):
        r = assess_sample_size("a", 50)
        assert r.adequacy == SampleAdequacy.ADEQUATE

    def test_boundary_min(self):
        r = assess_sample_size("a", 10)
        assert r.adequacy == SampleAdequacy.MARGINAL

    def test_boundary_comfortable(self):
        r = assess_sample_size("a", 30)
        assert r.adequacy == SampleAdequacy.ADEQUATE


# ═══════════════════════════════════════════════════════════════
# 18. edge_tracker / uncertainty_estimator
# ═══════════════════════════════════════════════════════════════

class TestUncertaintyEstimator:
    def test_basic_uncertainty(self):
        returns = (0.01, 0.02, 0.03, 0.04, 0.05)
        r = estimate_uncertainty("a", returns)
        assert r.mean_return == pytest.approx(0.03)
        assert r.sample_size == 5
        assert r.std_dev > 0.0
        assert r.standard_error > 0.0
        assert r.confidence_lower < r.mean_return
        assert r.confidence_upper > r.mean_return

    def test_single_observation(self):
        r = estimate_uncertainty("a", (0.05,))
        assert r.mean_return == 0.05
        assert r.std_dev == 0.0

    def test_sharpe(self):
        returns = (0.10, 0.10, 0.10, 0.10)  # zero variance
        r = estimate_uncertainty("a", returns)
        # std = 0, sharpe = 0 (division guard)
        assert r.sharpe_per_trade == 0.0

    def test_negative_returns(self):
        returns = (-0.01, -0.02, -0.03)
        r = estimate_uncertainty("a", returns)
        assert r.mean_return < 0.0
        assert r.confidence_upper < 0.0  # all negative


# ═══════════════════════════════════════════════════════════════
# 19. edge_tracker / edge_status_classifier
# ═══════════════════════════════════════════════════════════════

class TestEdgeStatusClassifier:
    def test_insufficient_sample(self):
        u = estimate_uncertainty("a", (0.01, 0.02))
        s = assess_sample_size("a", 2)
        c = classify_edge(u, s)
        assert c.status == EdgeStatus.INSUFFICIENT

    def test_degraded_negative_edge(self):
        u = estimate_uncertainty("a", tuple(-0.01 for _ in range(30)))
        s = assess_sample_size("a", 30)
        c = classify_edge(u, s)
        assert c.status == EdgeStatus.DEGRADED

    def test_under_surveillance_ci_includes_zero(self):
        # High variance: CI crosses zero
        returns = tuple(0.01 * (1 if i % 2 == 0 else -1) for i in range(30))
        u = estimate_uncertainty("a", returns)
        s = assess_sample_size("a", 30)
        c = classify_edge(u, s)
        # Mean ~0, CI includes zero → under_surveillance or degraded
        assert c.status in (EdgeStatus.UNDER_SURVEILLANCE, EdgeStatus.DEGRADED)

    def test_credible_strong_edge(self):
        # Strong consistent positive returns
        returns = tuple(0.05 + 0.001 * i for i in range(50))
        u = estimate_uncertainty("a", returns)
        s = assess_sample_size("a", 50)
        c = classify_edge(u, s)
        assert c.status == EdgeStatus.CREDIBLE

    def test_marginal_sample_surveillance(self):
        # Positive returns but marginal sample
        returns = tuple(0.05 for _ in range(15))
        u = estimate_uncertainty("a", returns)
        s = assess_sample_size("a", 15)
        c = classify_edge(u, s)
        assert c.status == EdgeStatus.UNDER_SURVEILLANCE

    def test_classification_includes_sharpe(self):
        returns = tuple(0.05 for _ in range(50))
        u = estimate_uncertainty("a", returns)
        s = assess_sample_size("a", 50)
        c = classify_edge(u, s)
        assert c.sharpe_per_trade == 0.0  # zero variance


# ═══════════════════════════════════════════════════════════════
# 20. edge_tracker / edge_reporter
# ═══════════════════════════════════════════════════════════════

class TestEdgeReporter:
    def test_report_counts(self):
        from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import EdgeClassification
        classifications = (
            EdgeClassification(scope="a", status=EdgeStatus.CREDIBLE, mean_net_return=0.05, sample_size=50),
            EdgeClassification(scope="b", status=EdgeStatus.DEGRADED, mean_net_return=-0.01, sample_size=30),
            EdgeClassification(scope="c", status=EdgeStatus.INSUFFICIENT, sample_size=3),
        )
        r = build_edge_report(classifications)
        assert r.total_scopes == 3
        assert r.credible_count == 1
        assert r.degraded_count == 1
        assert r.insufficient_count == 1
        assert r.has_drift_warning
        assert "b" in r.drift_scopes

    def test_no_drift(self):
        from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import EdgeClassification
        r = build_edge_report((
            EdgeClassification(scope="a", status=EdgeStatus.CREDIBLE, mean_net_return=0.05, sample_size=50),
        ))
        assert not r.has_drift_warning
