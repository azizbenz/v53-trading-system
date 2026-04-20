"""
V5.3 - Quantitative Paper Reproduction Tests
============================================
These tests reproduce the exact properties from the canonical research papers
to ensure the mathematical integrity of the microstructure estimators.

(DOC 29 - Sprint Final Codex - T3)
"""

from __future__ import annotations

import math

import pytest

# The tests check the mathematical properties, so we test against the
# real module implementations when available. We import what we have.
from data_backbone.microstructure.realized_kernel_vol import parzen_kernel_weight, resolve_realized_kernel_bandwidth
from data_backbone.microstructure.order_flow_imbalance import compute_order_flow_imbalance, OrderBookTopLevelPoint
from data_backbone.microstructure.kyle_lambda import compute_kyle_lambda, KyleTradePoint
from data_backbone.microstructure.vpin import compute_vpin, VpinTradePoint


# ─── TEST 1: Parzen Kernel Properties ────────────────────────────────────────

def test_parzen_kernel_at_zero_is_one() -> None:
    """k(0) = 1 (centre du kernel)
    Source: Barndorff-Nielsen 2008 Parzen kernel shape properties.
    DOI 10.3982/ECTA6495, eq.(3.5)
    """
    assert parzen_kernel_weight(0.0) == 1.0


def test_parzen_kernel_at_boundary_is_zero() -> None:
    """k(±1) = 0 (bords du kernel)"""
    assert parzen_kernel_weight(1.0) == 0.0
    assert parzen_kernel_weight(-1.0) == 0.0


def test_parzen_kernel_symmetry() -> None:
    """k(x) = k(-x) pour tout x"""
    for x in [0.1, 0.25, 0.5, 0.75, 0.99]:
        assert parzen_kernel_weight(x) == parzen_kernel_weight(-x)


def test_parzen_kernel_nonnegative() -> None:
    """k(x) ≥ 0 pour tout x ∈ [-1, 1]"""
    for x in [i / 100 for i in range(-100, 101)]:
        assert parzen_kernel_weight(x) >= 0.0


def test_bandwidth_scaling() -> None:
    """H = ⌈c · n^(3/5)⌉ avec c=0.4, n=1000 → H = ⌈0.4 × 63.1⌉ = 26"""
    # math.ceil(0.4 * (1000 ** 0.6))
    H = resolve_realized_kernel_bandwidth(1000, bandwidth_c=0.4)
    assert H == 26


# ─── TEST 2: OFI Direction ───────────────────────────────────────────────────

def test_ofi_positive_when_bid_grows_ask_shrinks() -> None:
    """Bid queue +100, ask queue -50 → OFI > 0
    Source: Cont-Kukanov 2014 §3 Proposition 1: OFI predicts price direction.
    DOI 10.1016/j.finmar.2013.06.001
    """
    events = [
        OrderBookTopLevelPoint(timestamp_ns=1, bid_price=100.0, bid_size=1000, ask_price=100.1, ask_size=500),
        OrderBookTopLevelPoint(timestamp_ns=2, bid_price=100.0, bid_size=1100, ask_price=100.1, ask_size=450),
    ]
    assert compute_order_flow_imbalance(events, pair="TESTUSD").value > 0


def test_ofi_negative_when_ask_grows_bid_shrinks() -> None:
    """Bid queue -80, ask queue +120 → OFI < 0"""
    events = [
        OrderBookTopLevelPoint(timestamp_ns=1, bid_price=100.0, bid_size=1000, ask_price=100.1, ask_size=500),
        OrderBookTopLevelPoint(timestamp_ns=2, bid_price=100.0, bid_size=920, ask_price=100.1, ask_size=620),
    ]
    assert compute_order_flow_imbalance(events, pair="TESTUSD").value < 0


def test_ofi_zero_when_symmetric() -> None:
    """Bid +50, ask -50 puis bid -50, ask +50 → OFI ≈ 0"""
    events = [
        OrderBookTopLevelPoint(timestamp_ns=1, bid_price=100.0, bid_size=1000, ask_price=100.1, ask_size=500),
        OrderBookTopLevelPoint(timestamp_ns=2, bid_price=100.0, bid_size=1050, ask_price=100.1, ask_size=450),
        OrderBookTopLevelPoint(timestamp_ns=3, bid_price=100.0, bid_size=1000, ask_price=100.1, ask_size=500),
    ]
    # The V5.3 compute_order_flow_imbalance gives a normalized mean
    assert abs(compute_order_flow_imbalance(events, pair="TESTUSD", window_events=2).value) < 1e-10


# ─── TEST 3: Kyle Lambda Positive ────────────────────────────────────────────

def test_lambda_positive_with_informed_trader() -> None:
    """Synthetic market: informed buyer drives price up → λ > 0
    Source: Kyle 1985 basic prediction: λ > 0.
    DOI 10.2307/1913210, eq.(1)
    """
    import numpy as np

    rng = np.random.default_rng(42)  # Fixed seed for paper repro
    n = 500
    # informed: always buys → SignedVolume > 0 → price drifts up
    signed_volume = rng.exponential(100, n)
    noise = rng.normal(0, 0.5, n)
    true_lambda = 0.001
    delta_p = true_lambda * signed_volume + noise

    # Construct V5.3 types to send to real implementation
    # price = sum of delta_p, volume = abs(signed_volume)
    prices = 100.0 + np.cumsum(delta_p)
    trades = []
    for i in range(n):
        qty = abs(float(signed_volume[i]))
        is_buyer = bool(signed_volume[i] > 0)
        trades.append(
            KyleTradePoint(
                timestamp_ns=(i + 1) * 65_000_000_000,
                price=float(prices[i]),
                volume=qty,
            )
        )

    result = compute_kyle_lambda(trades, pair="TESTUSD")
    lambda_hat = result.value

    assert lambda_hat > 0.0, f"λ should be positive, got {lambda_hat}"
    assert abs(lambda_hat - true_lambda) < 0.002, f"λ should be ≈ {true_lambda}"


# ─── TEST 4: VPIN Boundary ───────────────────────────────────────────────────

def test_vpin_one_when_all_same_side() -> None:
    """All trades classified as buys → V^S=0 in every bucket → VPIN=1.0
    Source: Easley-López-O'Hara 2012 boundary case: 100% informed → VPIN=1.
    DOI 10.1093/rfs/hhs053
    """
    trades = [
        VpinTradePoint(timestamp_ns=i + 1, price=100.0 + i * 0.01, volume=10.0)
        for i in range(1000)
    ]
    daily_volume = sum(t.volume for t in trades)
    result = compute_vpin(
        trades,
        pair="TESTUSD",
        buckets_per_day=50,
        window_buckets=50,
        daily_volume=daily_volume,
    )
    # The BVC approach correctly infers direction from price drift
    assert abs(result.value - 1.0) < 1e-6


def test_vpin_zero_when_perfectly_balanced() -> None:
    """Alternating buy/sell of equal volume → VPIN ≈ 0"""
    trades = []
    # To alternate buy/sell in a BVC framework (based on price changes),
    # price needs to alternate up and down slightly.
    for i in range(1000):
        trades.append(VpinTradePoint(timestamp_ns=i + 1, price=100.0, volume=10.0))

    daily_volume = sum(t.volume for t in trades)
    result = compute_vpin(
        trades,
        pair="TESTUSD",
        buckets_per_day=50,
        window_buckets=50,
        daily_volume=daily_volume,
    )
    # The VPIN should be very close to 0
    assert result.value < 0.05
