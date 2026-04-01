"""Tests for execution_backbone.execution_cost_meter — Build-3."""
import pytest

from execution_backbone.execution_cost_meter.fee_meter import (
    compute_fee,
    estimate_fee,
)
from execution_backbone.execution_cost_meter.elw_meter import (
    compute_elw,
    compute_implicit_round_trip,
)
from execution_backbone.execution_cost_meter.adverse_selection_meter import (
    compute_adverse_selection,
)
from execution_backbone.execution_cost_meter.partial_fill_cost_meter import (
    compute_partial_fill_cost,
)
from execution_backbone.execution_cost_meter.cost_aggregator import (
    CostAggregator,
    compute_trade_cost,
)


pytestmark = pytest.mark.build3


# --- Fee Meter ---

class TestFeeMeter:
    def test_compute_fee(self):
        f = compute_fee("o1", "BTC", price=50000.0, quantity=1.0, fee_amount=50.0)
        assert f.gross_value == 50000.0
        assert f.fee_rate == pytest.approx(0.001)

    def test_maker_flag(self):
        f = compute_fee("o1", "BTC", 50000.0, 1.0, 25.0, maker=True)
        assert f.maker is True

    def test_estimate_fee(self):
        est = estimate_fee(50000.0, 1.0, fee_rate=0.001)
        assert est == pytest.approx(50.0)


# --- ELW Meter ---

class TestELWMeter:
    def test_compute_elw(self):
        m = compute_elw("o1", "BTC", exec_price=50010.0, mid_price=50000.0, side="buy")
        assert m.elw == pytest.approx(0.0002)  # 10/50000

    def test_elw_zero_when_exact(self):
        m = compute_elw("o1", "BTC", exec_price=50000.0, mid_price=50000.0, side="buy")
        assert m.elw == 0.0

    def test_implicit_round_trip(self):
        rt = compute_implicit_round_trip("BTC", elw_entry=0.0002, elw_exit=0.0003)
        assert rt.implicit_round_trip == pytest.approx(0.0005)

    def test_implicit_entry_only(self):
        rt = compute_implicit_round_trip("BTC", elw_entry=0.0002)
        assert rt.implicit_round_trip == pytest.approx(0.0002)


# --- Adverse Selection ---

class TestAdverseSelection:
    def test_buy_mid_drops_negative_as(self):
        # Buy at 50000, mid drops to 49900 → adverse (bought, price fell)
        # AS = +1 * (49900 - 50000) / 50000 = -0.002
        m = compute_adverse_selection("o1", "BTC", "buy", 50000.0, 49900.0, 5.0)
        assert m.adverse_selection < 0
        assert m.adverse_selection == pytest.approx(-0.002)

    def test_buy_mid_rises_positive_as(self):
        # Buy at 50000, mid rises to 50100 → favorable (bought, price rose)
        # AS = +1 * (50100 - 50000) / 50000 = +0.002
        m = compute_adverse_selection("o1", "BTC", "buy", 50000.0, 50100.0, 5.0)
        assert m.adverse_selection > 0
        assert m.adverse_selection == pytest.approx(0.002)

    def test_sell_mid_rises_negative_as(self):
        # Sell at 50000, mid rises to 50100 → adverse (sold, price rose)
        # AS = -1 * (50100 - 50000) / 50000 = -0.002
        m = compute_adverse_selection("o1", "BTC", "sell", 50000.0, 50100.0, 5.0)
        assert m.adverse_selection < 0
        assert m.adverse_selection == pytest.approx(-0.002)

    def test_sell_mid_drops_positive_as(self):
        # Sell at 50000, mid drops to 49900 → favorable (sold, price fell)
        # AS = -1 * (49900 - 50000) / 50000 = +0.002
        m = compute_adverse_selection("o1", "BTC", "sell", 50000.0, 49900.0, 5.0)
        assert m.adverse_selection > 0
        assert m.adverse_selection == pytest.approx(0.002)

    def test_zero_exec_price(self):
        m = compute_adverse_selection("o1", "BTC", "buy", 0.0, 100.0, 5.0)
        assert m.adverse_selection == 0.0


# --- Partial Fill Cost ---

class TestPartialFillCost:
    def test_single_fill_no_variance(self):
        r = compute_partial_fill_cost(
            "o1", "BTC", 1.0, (50000.0,), (1.0,),
        )
        assert r.fill_count == 1
        assert r.price_variance == 0.0
        assert r.fill_ratio == 1.0

    def test_fragmented_fills(self):
        r = compute_partial_fill_cost(
            "o1", "BTC", 1.0,
            (50000.0, 50100.0), (0.5, 0.5),
        )
        assert r.fill_count == 2
        assert r.price_variance > 0  # different prices
        assert r.fill_ratio == 1.0

    def test_partial_fill_with_residual(self):
        r = compute_partial_fill_cost(
            "o1", "BTC", 1.0, (50000.0,), (0.3,), current_mid=50050.0,
        )
        assert r.fill_ratio == pytest.approx(0.3)
        assert r.unfilled_cost > 0  # 0.7 * |50050 - 50000|

    def test_empty_fills(self):
        r = compute_partial_fill_cost("o1", "BTC", 1.0, (), ())
        assert r.fill_count == 0
        assert r.fill_ratio == 0.0


# --- Cost Aggregator ---

class TestCostAggregator:
    def test_trade_cost_formula(self):
        c = compute_trade_cost(
            "o1", "BTC", "A",
            explicit_fee=0.001, implicit_cost=0.0002,
            adverse_selection=0.0001, partial_fill_cost=0.00005,
            expected_cost=0.001,
        )
        assert c.total_cost == pytest.approx(0.00135)
        assert c.cost_surprise == pytest.approx(0.00035)

    def test_aggregator(self):
        agg = CostAggregator()
        agg.record(compute_trade_cost("o1", "BTC", "A", 0.001, 0.0002))
        agg.record(compute_trade_cost("o2", "BTC", "A", 0.001, 0.0003))
        agg.record(compute_trade_cost("o3", "ETH", "B", 0.002, 0.0001))

        stats = agg.get_aggregate()
        assert stats.count == 3
        assert "A" in stats.by_engine
        assert "BTC" in stats.by_pair

    def test_break_even(self):
        agg = CostAggregator()
        agg.record(compute_trade_cost("o1", "BTC", "A", 0.001, 0.0002))
        agg.record(compute_trade_cost("o2", "BTC", "A", 0.001, 0.0004))
        be = agg.get_break_even("A", "BTC")
        assert be == pytest.approx((0.0012 + 0.0014) / 2)

    def test_market_impact_is_included_in_total_cost(self):
        c = compute_trade_cost(
            "o1", "BTC", "A",
            explicit_fee=0.001,
            implicit_cost=0.0002,
            adverse_selection=0.0001,
            partial_fill_cost=0.00005,
            market_impact=0.0003,
            expected_cost=0.001,
        )
        assert c.market_impact == pytest.approx(0.0003)
        assert c.total_cost == pytest.approx(0.00165)
