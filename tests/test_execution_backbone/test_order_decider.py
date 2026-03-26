"""Tests for execution_backbone.order_decider — Build-3."""
import pytest

from execution_backbone.order_decider.intent_builder import (
    ExecutionIntent,
    NoTradeDecision,
    NoTradeReason,
    OrderType,
    build_intent,
)
from execution_backbone.order_decider.order_type_selector import (
    select_order_type,
)
from execution_backbone.order_decider.execution_guard import (
    BlockReason,
    GuardVerdict,
    check_execution_guards,
)
from execution_backbone.order_decider.timeout_policy_selector import (
    CancelPolicy,
    select_timeout_policy,
)
from execution_backbone.order_decider.decision_reporter import (
    DecisionReporter,
)


pytestmark = pytest.mark.build3


# --- Intent Builder ---

class TestIntentBuilder:
    def test_build_market_intent(self):
        intent = build_intent(
            intent_id="i1", pair="BTCUSDT", engine_id="A", side="buy",
            order_type=OrderType.MARKET, quantity=0.1,
            expected_cost=0.001, expected_gain=0.005, score=0.8,
            justification="strong signal",
        )
        assert intent.order_type == OrderType.MARKET
        assert intent.pair == "BTCUSDT"
        assert intent.expected_gain > intent.expected_cost

    def test_intent_frozen(self):
        intent = build_intent(
            "i1", "BTC", "A", "buy", OrderType.MARKET, 1.0, 0.001, 0.01, 0.9, "test",
        )
        with pytest.raises(Exception):
            intent.quantity = 999  # frozen

    def test_no_trade_decision(self):
        d = NoTradeDecision(
            pair="BTC", engine_id="A",
            reason=NoTradeReason.COST_EXCEEDS_GAIN,
            expected_cost=0.01, expected_gain=0.005,
        )
        assert d.reason == NoTradeReason.COST_EXCEEDS_GAIN


# --- Order Type Selector ---

class TestOrderTypeSelector:
    def test_market_when_profitable_tight_spread(self):
        result = select_order_type(
            expected_gain=0.005, expected_cost=0.001,
            safety_margin=0.001, spread_bps=2.0,
        )
        assert result.order_type == OrderType.MARKET
        assert result.net_expected > 0

    def test_no_trade_when_cost_exceeds_gain(self):
        result = select_order_type(
            expected_gain=0.001, expected_cost=0.005, safety_margin=0.001,
        )
        assert result.order_type == OrderType.NO_TRADE
        assert result.net_expected <= 0

    def test_limit_when_spread_wide(self):
        result = select_order_type(
            expected_gain=0.01, expected_cost=0.001, safety_margin=0.001,
            spread_bps=7.0, use_limit_threshold_bps=5.0,
        )
        assert result.order_type == OrderType.LIMIT

    def test_no_trade_when_spread_too_wide(self):
        result = select_order_type(
            expected_gain=0.01, expected_cost=0.001,
            spread_bps=15.0, max_spread_for_market=10.0,
        )
        assert result.order_type == OrderType.NO_TRADE

    def test_exact_breakeven_is_no_trade(self):
        result = select_order_type(
            expected_gain=0.002, expected_cost=0.001, safety_margin=0.001,
        )
        assert result.order_type == OrderType.NO_TRADE  # net = 0


# --- Execution Guard ---

class TestExecutionGuard:
    def test_all_clear(self):
        result = check_execution_guards()
        assert result.verdict == GuardVerdict.PASS
        assert len(result.blocks) == 0

    def test_pair_suspended_blocks(self):
        result = check_execution_guards(pair_suspended=True)
        assert result.verdict == GuardVerdict.BLOCK
        assert BlockReason.PAIR_SUSPENDED in result.blocks

    def test_low_health_blocks(self):
        result = check_execution_guards(pair_health_score=0.1, pair_health_min=0.3)
        assert result.verdict == GuardVerdict.BLOCK
        assert BlockReason.PAIR_HEALTH_LOW in result.blocks

    def test_multiple_blocks(self):
        result = check_execution_guards(
            pair_suspended=True, risk_budget_available=False, data_stale=True,
        )
        assert result.verdict == GuardVerdict.BLOCK
        assert len(result.blocks) == 3

    def test_cost_too_high_blocks(self):
        result = check_execution_guards(expected_cost=0.05, max_acceptable_cost=0.01)
        assert BlockReason.COST_TOO_HIGH in result.blocks


# --- Timeout Policy ---

class TestTimeoutPolicy:
    def test_market_default(self):
        p = select_timeout_policy(OrderType.MARKET)
        assert p.timeout_s == 5.0
        assert p.cancel_policy == CancelPolicy.CANCEL_ON_TIMEOUT

    def test_limit_default(self):
        p = select_timeout_policy(OrderType.LIMIT)
        assert p.timeout_s == 30.0

    def test_no_trade(self):
        p = select_timeout_policy(OrderType.NO_TRADE)
        assert p.timeout_s == 0.0

    def test_custom_timeout(self):
        p = select_timeout_policy(OrderType.LIMIT, custom_timeout_s=120.0)
        assert p.timeout_s == 120.0


# --- Decision Reporter ---

class TestDecisionReporter:
    def test_trade_and_no_trade(self):
        reporter = DecisionReporter()
        intent = build_intent(
            "i1", "BTC", "A", "buy", OrderType.MARKET, 1.0,
            0.001, 0.01, 0.9, "strong signal",
        )
        reporter.record_trade(intent, timestamp=100.0)

        no_trade = NoTradeDecision(
            pair="ETH", engine_id="B",
            reason=NoTradeReason.COST_EXCEEDS_GAIN,
        )
        reporter.record_no_trade(no_trade, timestamp=101.0)

        stats = reporter.get_stats()
        assert stats.total_decisions == 2
        assert stats.trades == 1
        assert stats.no_trades == 1
        assert stats.trade_rate == 0.5

    def test_filter_by_pair(self):
        reporter = DecisionReporter()
        intent = build_intent(
            "i1", "BTC", "A", "buy", OrderType.MARKET, 1.0,
            0.001, 0.01, 0.9, "test",
        )
        reporter.record_trade(intent)
        events = reporter.get_events(pair="BTC")
        assert len(events) == 1
        assert len(reporter.get_events(pair="ETH")) == 0
