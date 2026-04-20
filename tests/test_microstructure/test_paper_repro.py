"""Paper reproduction tests for canonical microstructure calculators.

Each test verifies a mathematical property published in the original paper.
These tests wire directly to the real calculators in
`src/data_backbone/microstructure/` — they are NOT stub-based.

References
----------
BNHLS-2008 : Barndorff-Nielsen, Hansen, Lunde, Shephard (2008)
             "Designing Realized Kernels to Measure the Ex-Post Variation
              of Equity Prices in the Presence of Noise"
             Econometrica, 76(6). DOI: 10.3982/ECTA6495
             Key equations: (3.1) kernel estimator, (3.5) Parzen kernel, (3.7) bandwidth.

CKS-2014   : Cont, Kukanov, Stoikov (2014)
             "The Price Impact of Order Book Events"
             Journal of Financial Econometrics, 12(1). DOI: 10.1016/j.finmar.2013.06.001
             Key equations: (1) OFI event contribution, (3) cumulative OFI.

KYLE-1985  : Kyle (1985)
             "Continuous Auctions and Insider Trading"
             Econometrica, 53(6). DOI: 10.2307/1913210
             Key equation: (1) linear price-impact model ΔP = λ · SignedVolume + ε.

ELO-2012   : Easley, López de Prado, O'Hara (2012)
             "Flow Toxicity and Liquidity in a High-Frequency World"
             Review of Financial Studies, 25(5). DOI: 10.1093/rfs/hhs053
             Key equations: (2) equal-volume bucketing, (3) BVC classification, (4) VPIN.
"""

from __future__ import annotations

import math

import pytest

from data_backbone.microstructure.realized_kernel_vol import (
    parzen_kernel_weight,
    resolve_realized_kernel_bandwidth,
)
from data_backbone.microstructure.order_flow_imbalance import (
    OrderBookTopLevelPoint,
    compute_order_flow_imbalance,
)
from data_backbone.microstructure.kyle_lambda import (
    KyleTradePoint,
    compute_kyle_lambda,
)
from data_backbone.microstructure.vpin import (
    VpinTradePoint,
    compute_vpin,
)


# ---------------------------------------------------------------------------
# Test 1 — Parzen kernel shape properties (BNHLS-2008 eq. 3.5)
# ---------------------------------------------------------------------------

class TestParzenKernel:
    """Reproduce Barndorff-Nielsen et al. 2008 Parzen kernel (eq. 3.5).

    k(x) = 1 − 6x² + 6|x|³     if |x| ≤ 0.5
    k(x) = 2(1 − |x|)³          if 0.5 < |x| ≤ 1
    k(x) = 0                     otherwise
    """

    def test_parzen_kernel_at_zero_is_one(self) -> None:
        """k(0) = 1 — centre du kernel. BNHLS-2008 eq.(3.5), x=0."""
        assert parzen_kernel_weight(0.0) == 1.0

    def test_parzen_kernel_at_boundary_is_zero(self) -> None:
        """k(±1) = 0 — bords du kernel. BNHLS-2008 eq.(3.5), x=±1."""
        assert parzen_kernel_weight(1.0) == 0.0
        assert parzen_kernel_weight(-1.0) == 0.0

    def test_parzen_kernel_outside_support_is_zero(self) -> None:
        """k(x) = 0 pour |x| > 1. BNHLS-2008 eq.(3.5)."""
        assert parzen_kernel_weight(1.5) == 0.0
        assert parzen_kernel_weight(-2.0) == 0.0
        assert parzen_kernel_weight(100.0) == 0.0

    def test_parzen_kernel_symmetry(self) -> None:
        """k(x) = k(−x) pour tout x. BNHLS-2008 eq.(3.5) — kernel pair."""
        for x in [0.1, 0.25, 0.499, 0.5, 0.501, 0.75, 0.99]:
            assert parzen_kernel_weight(x) == pytest.approx(
                parzen_kernel_weight(-x), abs=1e-12
            ), f"symmetry failed at x={x}"

    def test_parzen_kernel_nonnegative(self) -> None:
        """k(x) ≥ 0 pour tout x ∈ [−1, 1]. BNHLS-2008 eq.(3.5)."""
        for i in range(-100, 101):
            x = i / 100.0
            assert parzen_kernel_weight(x) >= 0.0, f"negative at x={x}"

    def test_parzen_kernel_transition_at_half(self) -> None:
        """Continuité en x=0.5 : les deux branches coïncident. BNHLS-2008 eq.(3.5)."""
        # Branch 1 at x=0.5: 1 - 6*(0.25) + 6*(0.125) = 1 - 1.5 + 0.75 = 0.25
        branch1 = 1.0 - 6.0 * 0.25 + 6.0 * 0.125
        # Branch 2 at x=0.5: 2*(1 - 0.5)^3 = 2*0.125 = 0.25
        branch2 = 2.0 * (0.5 ** 3)
        assert branch1 == pytest.approx(branch2, abs=1e-12)
        assert parzen_kernel_weight(0.5) == pytest.approx(0.25, abs=1e-12)

    def test_bandwidth_rule(self) -> None:
        """H = ⌈c · n^(3/5)⌉ avec c=0.4, n=1000 → H=26. BNHLS-2008 Theorem 2."""
        # 1000^0.6 = 63.096, 0.4 × 63.096 = 25.238, ceil = 26
        H = resolve_realized_kernel_bandwidth(1000, bandwidth_c=0.4)
        assert H == 26


# ---------------------------------------------------------------------------
# Test 2 — OFI direction (CKS-2014 eq. 1 + Proposition 1)
# ---------------------------------------------------------------------------

def _book(ts: int, bp: float, bs: float, ap: float, as_: float) -> OrderBookTopLevelPoint:
    return OrderBookTopLevelPoint(
        timestamp_ns=ts,
        bid_price=bp,
        bid_size=bs,
        ask_price=ap,
        ask_size=as_,
    )


class TestOrderFlowImbalance:
    """Reproduce Cont-Kukanov-Stoikov 2014 OFI direction predictions (eq.1, §3 Prop.1).

    Δe_i = ΔQ^b_i · 𝟙(P^b_i ≥ P^b_{i-1}) − ΔQ^a_i · 𝟙(P^a_i ≤ P^a_{i-1})
    OFI = Σ Δe_i  (buy pressure > 0, sell pressure < 0)
    """

    def test_ofi_positive_when_bid_grows_ask_stable(self) -> None:
        """Bid queue grows → OFI > 0 (buy pressure). CKS-2014 eq.(1)."""
        points = [
            _book(1_000_000_000, 100.0, 1000.0, 100.1, 500.0),  # t=1
            _book(2_000_000_000, 100.0, 1100.0, 100.1, 500.0),  # t=2, bid+100
        ]
        result = compute_order_flow_imbalance(points, pair="BTCUSDT")
        assert result.value > 0.0, f"expected OFI > 0, got {result.value}"

    def test_ofi_negative_when_ask_grows_bid_stable(self) -> None:
        """Ask queue grows → OFI < 0 (sell pressure). CKS-2014 eq.(1)."""
        points = [
            _book(1_000_000_000, 100.0, 1000.0, 100.1, 500.0),  # t=1
            _book(2_000_000_000, 100.0, 1000.0, 100.1, 620.0),  # t=2, ask+120
        ]
        result = compute_order_flow_imbalance(points, pair="BTCUSDT")
        assert result.value < 0.0, f"expected OFI < 0, got {result.value}"

    def test_ofi_positive_when_bid_price_ticks_up(self) -> None:
        """Bid price ticks up (aggressive buyer) → OFI > 0. CKS-2014 eq.(1)."""
        points = [
            _book(1_000_000_000, 99.9, 1000.0, 100.0, 500.0),  # t=1
            _book(2_000_000_000, 100.0, 1000.0, 100.1, 500.0),  # t=2, bid ticked up
        ]
        result = compute_order_flow_imbalance(points, pair="BTCUSDT")
        assert result.value > 0.0, f"expected OFI > 0, got {result.value}"

    def test_ofi_buy_pressure_larger_than_sell_pressure(self) -> None:
        """Strong buy vs weak sell → net OFI > 0. CKS-2014 §3 Proposition 1."""
        # Large bid growth, small ask growth → net positive
        points = [
            _book(1_000_000_000, 100.0, 500.0,  100.1, 500.0),
            _book(2_000_000_000, 100.0, 1000.0, 100.1, 520.0),  # bid+500, ask+20
        ]
        result = compute_order_flow_imbalance(points, pair="BTCUSDT")
        assert result.value > 0.0


# ---------------------------------------------------------------------------
# Test 3 — Kyle lambda positive with buy-side informed flow (KYLE-1985 eq.1)
# ---------------------------------------------------------------------------

class TestKyleLambda:
    """Reproduce Kyle 1985 eq.(1): ΔP = λ · SignedVolume + ε, λ > 0.

    An informed buyer drives price up → signed volume positive →
    price change positive → OLS estimate λ̂ > 0.
    """

    def _make_informed_buy_trades(
        self,
        n: int = 60,
        price_start: float = 100.0,
        price_step: float = 0.01,
        volume_base: float = 100.0,
        volume_step: float = 5.0,
        start_ns: int = 1_000_000_000,
        step_ns: int = 60_000_000_000,  # 1 min in ns
    ) -> list[KyleTradePoint]:
        """Synthetic buy-side informed-trader flow: price drifts up monotonically.

        Volume varies linearly with `i` to give the rolling-OLS estimator
        non-zero variance in SignedVolume (Kyle 1985 eq.1 requires Var(y) > 0).
        """
        return [
            KyleTradePoint(
                timestamp_ns=start_ns + i * step_ns,
                price=price_start + i * price_step,
                volume=volume_base + i * volume_step,
                mid_price=price_start + (i - 0.5) * price_step if i > 0 else None,
            )
            for i in range(n)
        ]

    def test_lambda_positive_for_buy_flow(self) -> None:
        """Informed buyer → price drifts up → λ > 0. KYLE-1985 eq.(1)."""
        trades = self._make_informed_buy_trades(n=60)
        record = compute_kyle_lambda(
            trades,
            pair="BTCUSDT",
            window_seconds=3600.0,
            bucket_seconds=60.0,
        )
        assert not record.is_stale, f"unexpected stale: {record.stale_reason}"
        assert record.value > 0.0, (
            f"Kyle λ should be > 0 for informed buy flow, got {record.value}"
        )

    def test_lambda_bounded_and_finite(self) -> None:
        """λ is finite and non-negative. KYLE-1985 eq.(1) invariant."""
        trades = self._make_informed_buy_trades(n=60)
        record = compute_kyle_lambda(
            trades,
            pair="BTCUSDT",
            window_seconds=3600.0,
            bucket_seconds=60.0,
        )
        assert math.isfinite(record.value), f"λ is not finite: {record.value}"
        assert record.value >= 0.0

    def test_lambda_increases_with_stronger_price_impact(self) -> None:
        """Steeper price drift → larger λ̂. KYLE-1985: λ = market illiquidity.

        Two scenarios: slow drift (liquid) vs fast drift (illiquid).
        """
        trades_liquid = self._make_informed_buy_trades(n=60, price_step=0.001)
        trades_illiquid = self._make_informed_buy_trades(n=60, price_step=0.05)

        liq = compute_kyle_lambda(trades_liquid, pair="BTCUSDT",
                                   window_seconds=3600.0, bucket_seconds=60.0)
        illiq = compute_kyle_lambda(trades_illiquid, pair="BTCUSDT",
                                     window_seconds=3600.0, bucket_seconds=60.0)

        if liq.is_stale or illiq.is_stale:
            pytest.skip("stale result — insufficient variation for comparison")

        assert illiq.value >= liq.value, (
            f"illiquid λ={illiq.value:.6f} should be ≥ liquid λ={liq.value:.6f}"
        )


# ---------------------------------------------------------------------------
# Test 4 — VPIN boundary cases (ELO-2012 eq. 2-4)
# ---------------------------------------------------------------------------

class TestVpin:
    """Reproduce Easley-López de Prado-O'Hara 2012 VPIN boundary properties.

    VPIN = (1/n) · Σ |V^S_τ − V^B_τ| / V_bucket

    VPIN ∈ [0, 1] always (eq. 4).
    Perfectly balanced flow → VPIN → 0.
    Strongly directional flow → VPIN → 1.
    """

    def _make_trades(
        self,
        prices: list[float],
        volume: float = 10.0,
        start_ns: int = 1_000_000_000,
        step_ns: int = 1_000_000_000,
    ) -> list[VpinTradePoint]:
        return [
            VpinTradePoint(
                timestamp_ns=start_ns + i * step_ns,
                price=p,
                volume=volume,
            )
            for i, p in enumerate(prices)
        ]

    def test_vpin_bounded_zero_one(self) -> None:
        """VPIN ∈ [0, 1] always. ELO-2012 eq.(4), field ge=0.0, le=1.0."""
        # Monotonically rising prices (buy pressure)
        prices = [100.0 + i * 0.01 for i in range(200)]
        trades = self._make_trades(prices)
        result = compute_vpin(
            trades,
            pair="BTCUSDT",
            buckets_per_day=10,
            window_buckets=5,
            allow_derived_daily_volume=True,
        )
        assert 0.0 <= result.value <= 1.0, f"VPIN out of [0,1]: {result.value}"

    def test_vpin_higher_for_directional_flow(self) -> None:
        """Strongly trending prices → higher VPIN than mean-reverting prices.

        ELO-2012 §3: VPIN captures order-flow toxicity (unilateral informed flow).
        """
        # Trending: monotonic price increase (informed buyers pushing price up)
        trending_prices = [100.0 + i * 0.1 for i in range(200)]

        # Mean-reverting: price oscillates ±0.1 around 100
        import random
        rng = random.Random(42)
        reverting_prices = []
        p = 100.0
        for _ in range(200):
            p += rng.choice([-0.1, 0.1])
            p = max(95.0, min(105.0, p))
            reverting_prices.append(p)

        trending_trades = self._make_trades(trending_prices)
        reverting_trades = self._make_trades(reverting_prices)

        vpin_trend = compute_vpin(
            trending_trades, pair="BTCUSDT",
            buckets_per_day=10, window_buckets=5,
            allow_derived_daily_volume=True,
        )
        vpin_revert = compute_vpin(
            reverting_trades, pair="BTCUSDT",
            buckets_per_day=10, window_buckets=5,
            allow_derived_daily_volume=True,
        )

        assert vpin_trend.value >= vpin_revert.value, (
            f"trending VPIN={vpin_trend.value:.4f} should be ≥ "
            f"reverting VPIN={vpin_revert.value:.4f}"
        )

    def test_vpin_with_explicit_daily_volume(self) -> None:
        """VPIN with explicit daily_volume matches expected bucket size. ELO-2012 eq.(2).

        bucket_volume = daily_volume / buckets_per_day
        """
        prices = [100.0 + i * 0.01 for i in range(100)]
        trades = self._make_trades(prices, volume=10.0)
        total_volume = 100 * 10.0  # 1000 units

        result = compute_vpin(
            trades, pair="BTCUSDT",
            buckets_per_day=10, window_buckets=5,
            daily_volume=total_volume,
        )
        assert 0.0 <= result.value <= 1.0
        assert result.method_version_hash  # audit-ready: hash must be present

    def test_vpin_result_is_auditable(self) -> None:
        """VPIN record carries method_version_hash for audit trail. V5.3 doctrine."""
        prices = [100.0 + i * 0.005 for i in range(120)]
        trades = self._make_trades(prices)
        result = compute_vpin(
            trades, pair="ETHUSDT",
            buckets_per_day=10, window_buckets=5,
            allow_derived_daily_volume=True,
        )
        assert result.method_version_hash, "method_version_hash must be non-empty"
        assert result.pair == "ETHUSDT"
        assert math.isfinite(result.value)
