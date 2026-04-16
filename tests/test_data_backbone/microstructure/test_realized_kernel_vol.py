from __future__ import annotations

from math import ceil, isclose, sqrt
import random

import pytest

from data_backbone.microstructure.realized_kernel_vol import (
    DEFAULT_RK_BANDWIDTH_C,
    MAX_RK_BANDWIDTH_C,
    MAX_RK_BUCKET_SECONDS,
    REALIZED_KERNEL_METHOD_VERSION_HASH,
    RealizedKernelPricePoint,
    compute_realized_kernel_vol,
    parzen_kernel_weight,
    resolve_realized_kernel_bandwidth,
)


def test_realized_kernel_parzen_shape_properties() -> None:
    assert parzen_kernel_weight(0.0) == pytest.approx(1.0)
    assert parzen_kernel_weight(0.5) == pytest.approx(0.25)
    assert parzen_kernel_weight(0.75) == pytest.approx(0.03125)
    assert parzen_kernel_weight(1.0) == pytest.approx(0.0)
    assert parzen_kernel_weight(1.1) == pytest.approx(0.0)


def test_resolve_realized_kernel_bandwidth_matches_doc_rule() -> None:
    sample_size = 100
    expected = ceil(DEFAULT_RK_BANDWIDTH_C * (sample_size ** (3.0 / 5.0)))
    assert resolve_realized_kernel_bandwidth(sample_size) == expected


def test_compute_realized_kernel_vol_matches_small_manual_case() -> None:
    points = [
        RealizedKernelPricePoint(timestamp_ns=1_000_000_000, price=100.0),
        RealizedKernelPricePoint(timestamp_ns=2_000_000_000, price=101.0),
        RealizedKernelPricePoint(timestamp_ns=3_000_000_000, price=102.0),
        RealizedKernelPricePoint(timestamp_ns=4_000_000_000, price=101.5),
    ]

    result = compute_realized_kernel_vol(points, pair="btcusdt")

    returns = [
        0.009950330853168092,
        0.00985229644301164,
        -0.004914014802429163,
    ]
    gamma_0 = sum(value * value for value in returns)
    gamma_1 = (
        returns[1] * returns[0]
        + returns[2] * returns[1]
    )
    expected_variance = gamma_0 + 2.0 * gamma_1

    assert result.bandwidth == 1
    assert result.kernel_variance == pytest.approx(expected_variance)
    assert result.value == pytest.approx(sqrt(expected_variance))
    assert result.pair == "BTCUSDT"
    assert result.window_used == pytest.approx((4, 3.0))
    assert result.n_events_used == 4
    assert result.method_version_hash == REALIZED_KERNEL_METHOD_VERSION_HASH


def test_compute_realized_kernel_vol_is_non_negative_on_fixed_seed_simulation() -> None:
    random_generator = random.Random(42)
    price = 100.0
    points = []
    timestamp_ns = 1_000_000_000
    for _ in range(64):
        price *= 1.0 + random_generator.uniform(-0.0025, 0.0025)
        points.append(
            RealizedKernelPricePoint(timestamp_ns=timestamp_ns, price=price)
        )
        timestamp_ns += 300_000_000_000

    result = compute_realized_kernel_vol(points, pair="ETHUSDT")

    assert result.value >= 0.0
    assert result.kernel_variance >= 0.0
    assert result.bandwidth >= 1
    assert result.input_data_hash


def test_compute_realized_kernel_vol_rejects_thresholds_outside_doc_caps() -> None:
    points = [
        RealizedKernelPricePoint(timestamp_ns=1_000_000_000, price=100.0),
        RealizedKernelPricePoint(timestamp_ns=2_000_000_000, price=100.5),
        RealizedKernelPricePoint(timestamp_ns=3_000_000_000, price=101.0),
    ]

    with pytest.raises(ValueError, match="bandwidth_c"):
        compute_realized_kernel_vol(
            points,
            pair="BTCUSDT",
            bandwidth_c=MAX_RK_BANDWIDTH_C + 0.1,
        )

    with pytest.raises(ValueError, match="bucket_seconds"):
        compute_realized_kernel_vol(
            points,
            pair="BTCUSDT",
            bucket_seconds=MAX_RK_BUCKET_SECONDS + 1.0,
        )
