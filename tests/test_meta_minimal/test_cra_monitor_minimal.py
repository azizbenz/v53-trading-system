"""Build-9 tests for meta_minimal cra_monitor."""

from __future__ import annotations

import pytest

from meta_minimal.cra_monitor.cra_alert_builder import CRAAlertLevel, build_alerts
from meta_minimal.cra_monitor.cra_reporter import build_cra_report
from meta_minimal.cra_monitor.phantom_risk_estimator import (
    PhantomRiskResult,
    estimate_phantom_risk,
)
from meta_minimal.cra_monitor.reduction_trace_reader import ReductionTrace, read_reduction
from meta_minimal.cra_monitor.sterilization_classifier import (
    SterilizationClass,
    SterilizationResult,
    classify_sterilization,
)


class TestReductionTraceReader:
    def test_read_reduction(self) -> None:
        trace = read_reduction("BTC", "engine_a", original_size=100.0, final_size=50.0)
        assert trace.multiplier == pytest.approx(0.5)

    def test_zero_original_size(self) -> None:
        trace = read_reduction("X", "a", original_size=0.0, final_size=0.0)
        assert trace.multiplier == 0.0

    def test_no_reduction(self) -> None:
        trace = read_reduction("X", "a", original_size=100.0, final_size=100.0)
        assert trace.multiplier == pytest.approx(1.0)


class TestPhantomRiskEstimator:
    def _trace(
        self,
        final: float = 50.0,
        ce: float = 0.001,
        hours: float = 2.0,
        cost: float = 0.05,
    ) -> ReductionTrace:
        return ReductionTrace(
            pair="X",
            engine_id="a",
            original_size=100.0,
            final_size=final,
            multiplier=final / 100.0,
            ce_expected=ce,
            holding_hours=hours,
            expected_cost=cost,
        )

    def test_viable_trade_low_risk(self) -> None:
        risk = estimate_phantom_risk(
            self._trace(final=100.0, ce=0.01, hours=2.0, cost=0.05)
        )
        assert not risk.is_high_risk
        assert risk.net_expected > 0.0

    def test_tiny_trade_high_risk(self) -> None:
        risk = estimate_phantom_risk(
            self._trace(final=1.0, ce=0.0001, hours=1.0, cost=0.05)
        )
        assert risk.is_high_risk
        assert risk.phantom_risk_score > 0.5

    def test_high_cost_sterilizes(self) -> None:
        risk = estimate_phantom_risk(
            self._trace(final=50.0, ce=0.0001, hours=1.0, cost=5.0)
        )
        assert risk.is_high_risk


class TestSterilizationClassifier:
    def _trace_and_risk(
        self,
        mult: float = 1.0,
        net: float = 1.0,
        risk_score: float = 0.1,
    ) -> tuple[ReductionTrace, PhantomRiskResult]:
        trace = ReductionTrace(
            pair="X",
            engine_id="a",
            original_size=100.0,
            final_size=100.0 * mult,
            multiplier=mult,
        )
        risk = PhantomRiskResult(
            pair="X",
            engine_id="a",
            expected_pnl=2.0,
            operational_cost=1.0,
            net_expected=net,
            phantom_risk_score=risk_score,
        )
        return trace, risk

    def test_healthy(self) -> None:
        trace, risk = self._trace_and_risk(mult=0.8, net=1.0, risk_score=0.1)
        classification = classify_sterilization(trace, risk)
        assert classification.classification == SterilizationClass.HEALTHY

    def test_reduced_viable(self) -> None:
        trace, risk = self._trace_and_risk(mult=0.3, net=1.0, risk_score=0.1)
        classification = classify_sterilization(trace, risk)
        assert classification.classification == SterilizationClass.REDUCED_VIABLE

    def test_phantom_probable(self) -> None:
        trace, risk = self._trace_and_risk(mult=0.2, net=0.3, risk_score=0.75)
        classification = classify_sterilization(trace, risk)
        assert classification.classification == SterilizationClass.PHANTOM_PROBABLE

    def test_phantom_confirmed(self) -> None:
        trace, risk = self._trace_and_risk(mult=0.05, net=-0.5, risk_score=0.95)
        classification = classify_sterilization(trace, risk)
        assert classification.classification == SterilizationClass.PHANTOM_CONFIRMED

    def test_negative_net_always_confirmed(self) -> None:
        trace, risk = self._trace_and_risk(mult=1.0, net=-0.1, risk_score=0.5)
        classification = classify_sterilization(trace, risk)
        assert classification.classification == SterilizationClass.PHANTOM_CONFIRMED


class TestCRAAlertBuilder:
    def _steril(
        self,
        engine: str,
        pair: str,
        classification: SterilizationClass,
    ) -> SterilizationResult:
        return SterilizationResult(
            pair=pair,
            engine_id=engine,
            classification=classification,
            multiplier=0.5,
            phantom_risk_score=0.8,
            reason="test_reason",
        )

    def test_no_alert_all_healthy(self) -> None:
        results = tuple(
            self._steril("a", f"P{index}", SterilizationClass.HEALTHY)
            for index in range(10)
        )
        alerts = build_alerts(results)
        assert len(alerts) == 0

    def test_warning_alert(self) -> None:
        results = tuple(
            self._steril("a", "P1", SterilizationClass.HEALTHY) for _ in range(7)
        ) + tuple(
            self._steril("a", "P1", SterilizationClass.PHANTOM_CONFIRMED)
            for _ in range(3)
        )
        alerts = build_alerts(results)
        assert any(alert.alert_level == CRAAlertLevel.WARNING for alert in alerts)

    def test_critical_alert(self) -> None:
        results = tuple(
            self._steril("a", "P1", SterilizationClass.HEALTHY) for _ in range(5)
        ) + tuple(
            self._steril("a", "P1", SterilizationClass.PHANTOM_CONFIRMED)
            for _ in range(5)
        )
        alerts = build_alerts(results)
        assert any(alert.alert_level == CRAAlertLevel.CRITICAL for alert in alerts)


class TestCRAReporter:
    def test_report_counts(self) -> None:
        results = (
            SterilizationResult(
                pair="A",
                engine_id="a",
                classification=SterilizationClass.HEALTHY,
                multiplier=1.0,
                phantom_risk_score=0.1,
            ),
            SterilizationResult(
                pair="B",
                engine_id="a",
                classification=SterilizationClass.PHANTOM_CONFIRMED,
                multiplier=0.1,
                phantom_risk_score=0.95,
            ),
            SterilizationResult(
                pair="C",
                engine_id="b",
                classification=SterilizationClass.REDUCED_VIABLE,
                multiplier=0.4,
                phantom_risk_score=0.3,
            ),
        )
        report = build_cra_report(results)
        assert report.total_trades == 3
        assert report.healthy_count == 1
        assert report.phantom_confirmed_count == 1
        assert report.reduced_viable_count == 1
        assert report.sterilization_rate == pytest.approx(1 / 3)

    def test_engine_rate(self) -> None:
        results = (
            SterilizationResult(
                pair="A",
                engine_id="a",
                classification=SterilizationClass.PHANTOM_CONFIRMED,
                multiplier=0.1,
                phantom_risk_score=0.95,
            ),
            SterilizationResult(
                pair="B",
                engine_id="b",
                classification=SterilizationClass.HEALTHY,
                multiplier=1.0,
                phantom_risk_score=0.1,
            ),
        )
        report = build_cra_report(results)
        assert report.sterilization_rate_by_engine["a"] == 1.0
        assert report.sterilization_rate_by_engine["b"] == 0.0
