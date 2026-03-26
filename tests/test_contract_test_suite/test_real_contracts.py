"""Tests Module 4 — Real contract verification on interface_contracts models.

This proves the contract_test_suite actually validates production modules,
not just toy examples. Tests the V5.3 domain types against their contracts.
"""

import pytest

from interface_contracts.market_event_contracts import TradeEvent
from interface_contracts.decision_contracts import SignalCandidate
from contract_test_suite.contract_test_runner import ContractSuite
from contract_test_suite.schema_assertions import (
    assert_field_present,
    assert_field_type,
    assert_invalid_rejected,
    assert_valid_instance,
)
from contract_test_suite.contract_reporter import build_suite_report


MODULE = "interface_contracts"
TS = 1700000000000


@pytest.mark.build1
class TestTradeEventContracts:
    """Contract tests for TradeEvent."""

    def test_trade_event_full_suite(self):
        suite = ContractSuite(MODULE)

        # Schema: required fields present
        for field in ("pair", "price", "quantity", "side", "timestamp_ms"):
            suite.add_test(lambda f=field: assert_field_present(TradeEvent, f, MODULE))

        VALID_TRADE = {
            "pair": "BTCUSDT", "price": 50000.0, "quantity": 1.0,
            "side": "buy", "trade_id": "t123", "timestamp_ms": TS,
        }

        # Valid instance
        suite.add_test(lambda: assert_valid_instance(
            TradeEvent, VALID_TRADE, MODULE, "trade_event_valid",
        ))

        # Negative: price <= 0
        suite.add_test(lambda: assert_invalid_rejected(TradeEvent, {
            **VALID_TRADE, "price": 0,
        }, MODULE, "trade_rejects_zero_price"))

        # Negative: quantity < 0
        suite.add_test(lambda: assert_invalid_rejected(TradeEvent, {
            **VALID_TRADE, "quantity": -1.0,
        }, MODULE, "trade_rejects_negative_qty"))

        report = suite.run()
        assert report.all_passed, (
            f"TradeEvent contract failures: "
            f"{[r.message for r in report.results if r.failed]}"
        )


@pytest.mark.build1
class TestSignalCandidateContracts:
    """Contract tests for SignalCandidate."""

    def test_signal_candidate_full_suite(self):
        suite = ContractSuite(MODULE)

        for field in ("pair", "engine_id", "side", "confidence", "timestamp_ms"):
            suite.add_test(lambda f=field: assert_field_present(SignalCandidate, f, MODULE))

        VALID_SIGNAL = {
            "pair": "BTCUSDT", "engine_id": "engine_a",
            "signal_type": "entry", "side": "buy",
            "confidence": 0.75, "regime": "trending_up",
            "entry_price": 50000.0, "stop_loss": 49000.0,
            "take_profit": 52000.0, "timestamp_ms": TS,
        }

        # Valid
        suite.add_test(lambda: assert_valid_instance(
            SignalCandidate, VALID_SIGNAL, MODULE, "signal_valid",
        ))

        # Negative: confidence > 1
        suite.add_test(lambda: assert_invalid_rejected(SignalCandidate, {
            **VALID_SIGNAL, "confidence": 1.5,
        }, MODULE, "signal_rejects_confidence_gt_1"))

        # Negative: confidence < 0
        suite.add_test(lambda: assert_invalid_rejected(SignalCandidate, {
            **VALID_SIGNAL, "confidence": -0.1,
        }, MODULE, "signal_rejects_confidence_lt_0"))

        report = suite.run()
        assert report.all_passed, (
            f"SignalCandidate contract failures: "
            f"{[r.message for r in report.results if r.failed]}"
        )


@pytest.mark.build1
class TestBuildFailOnBrokenContract:
    """6.9/6.14: build must fail if any critical contract is broken."""

    def test_suite_report_fails_on_critical(self):
        suite = ContractSuite(MODULE)
        # This will FAIL: TradeEvent does NOT have a field called "phantom"
        suite.add_test(lambda: assert_field_present(TradeEvent, "phantom", MODULE))
        mod_report = suite.run()

        report = build_suite_report([mod_report])
        assert not report.passed, "Build must FAIL when a critical contract is broken"

    def test_suite_report_passes_when_clean(self):
        suite = ContractSuite(MODULE)
        suite.add_test(lambda: assert_field_present(TradeEvent, "price", MODULE))
        mod_report = suite.run()

        report = build_suite_report([mod_report])
        assert report.passed
