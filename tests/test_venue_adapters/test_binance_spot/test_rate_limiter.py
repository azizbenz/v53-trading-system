from __future__ import annotations

from venue_adapters.binance_spot.rate_limiter import (
    BinanceApiRateLimiter,
    BinanceApiRateLimiterConfig,
    BinanceApiRateLimitExceededError,
    BinanceRequestQuotaCost,
    classify_binance_request_quota_cost,
)


def test_classify_exchange_info_with_symbol_uses_light_cost() -> None:
    cost = classify_binance_request_quota_cost(
        "/api/v3/exchangeInfo",
        params={"symbol": "BTCUSDT"},
    )
    assert cost.request_weight == 1
    assert cost.order_count_10s == 0


def test_classify_depth_limit_1000_uses_conservative_heavy_cost() -> None:
    cost = classify_binance_request_quota_cost(
        "/api/v3/depth",
        params={"symbol": "BTCUSDT", "limit": "1000"},
    )
    assert cost.request_weight == 50


def test_classify_open_orders_without_symbol_uses_account_wide_cost() -> None:
    cost = classify_binance_request_quota_cost("/api/v3/openOrders")
    assert cost.request_weight == 80


def test_reserve_allows_request_within_budget() -> None:
    limiter = BinanceApiRateLimiter(
        config=BinanceApiRateLimiterConfig(
            preemptive_request_weight_limit_1m=10,
            preemptive_orders_limit_10s=4,
        ),
        clock_ms=lambda: 0,
    )
    limiter.reserve(cost=BinanceRequestQuotaCost(request_weight=3), now_ms=0)
    snapshot = limiter.snapshot(now_ms=0)
    assert snapshot.request_weight_tokens_remaining == 7.0
    assert snapshot.order_tokens_remaining == 4.0


def test_reserve_blocks_when_request_weight_budget_is_exhausted() -> None:
    limiter = BinanceApiRateLimiter(
        config=BinanceApiRateLimiterConfig(
            preemptive_request_weight_limit_1m=5,
            preemptive_orders_limit_10s=4,
        ),
        clock_ms=lambda: 0,
    )
    limiter.reserve(cost=BinanceRequestQuotaCost(request_weight=5), now_ms=0)
    try:
        limiter.reserve(cost=BinanceRequestQuotaCost(request_weight=1), now_ms=0)
    except BinanceApiRateLimitExceededError as exc:
        assert "request-weight budget exhausted" in str(exc)
    else:
        raise AssertionError("Expected request-weight exhaustion to block")


def test_reserve_blocks_when_order_budget_is_exhausted() -> None:
    limiter = BinanceApiRateLimiter(
        config=BinanceApiRateLimiterConfig(
            preemptive_request_weight_limit_1m=20,
            preemptive_orders_limit_10s=2,
        ),
        clock_ms=lambda: 0,
    )
    limiter.reserve(cost=BinanceRequestQuotaCost(request_weight=1, order_count_10s=2), now_ms=0)
    try:
        limiter.reserve(cost=BinanceRequestQuotaCost(request_weight=1, order_count_10s=1), now_ms=0)
    except BinanceApiRateLimitExceededError as exc:
        assert "order-count budget exhausted" in str(exc)
    else:
        raise AssertionError("Expected order-count exhaustion to block")


def test_response_headers_tighten_request_budget() -> None:
    limiter = BinanceApiRateLimiter(
        config=BinanceApiRateLimiterConfig(
            preemptive_request_weight_limit_1m=10,
            preemptive_orders_limit_10s=4,
        ),
        clock_ms=lambda: 0,
    )
    limiter.observe_response(
        headers={"X-MBX-USED-WEIGHT-1M": "8"},
        status_code=200,
        now_ms=0,
    )
    snapshot = limiter.snapshot(now_ms=0)
    assert snapshot.request_weight_tokens_remaining == 2.0


def test_response_headers_flag_warning_at_80_percent_of_official_quota() -> None:
    limiter = BinanceApiRateLimiter(
        config=BinanceApiRateLimiterConfig(
            official_request_weight_limit_1m=100,
            preemptive_request_weight_limit_1m=100,
            preemptive_orders_limit_10s=4,
        ),
        clock_ms=lambda: 0,
    )
    limiter.observe_response(
        headers={"X-MBX-USED-WEIGHT-1M": "80"},
        status_code=200,
        now_ms=0,
    )
    snapshot = limiter.snapshot(now_ms=0)
    assert snapshot.official_request_weight_used_1m == 80
    assert snapshot.official_request_weight_quota_ratio == 0.8
    assert snapshot.official_request_weight_warn_active is True
    assert snapshot.official_request_weight_block_active is False


def test_response_headers_block_for_60s_at_95_percent_of_official_quota() -> None:
    limiter = BinanceApiRateLimiter(
        config=BinanceApiRateLimiterConfig(
            official_request_weight_limit_1m=100,
            preemptive_request_weight_limit_1m=100,
            preemptive_orders_limit_10s=4,
        ),
        clock_ms=lambda: 0,
    )
    limiter.observe_response(
        headers={"X-MBX-USED-WEIGHT-1M": "95"},
        status_code=200,
        now_ms=0,
    )
    snapshot = limiter.snapshot(now_ms=0)
    assert snapshot.official_request_weight_quota_ratio == 0.95
    assert snapshot.official_request_weight_warn_active is True
    assert snapshot.official_request_weight_block_until_ms == 60_000
    assert snapshot.official_request_weight_block_active is True
    assert snapshot.throttle_until_ms == 60_000

    try:
        limiter.reserve(cost=BinanceRequestQuotaCost(request_weight=1), now_ms=59_999)
    except BinanceApiRateLimitExceededError as exc:
        assert "official block threshold" in str(exc)
    else:
        raise AssertionError("Expected official request-weight block window to stop reserve()")

    limiter.reserve(cost=BinanceRequestQuotaCost(request_weight=1), now_ms=60_000)


def test_response_headers_tighten_order_budget() -> None:
    limiter = BinanceApiRateLimiter(
        config=BinanceApiRateLimiterConfig(
            preemptive_request_weight_limit_1m=10,
            preemptive_orders_limit_10s=4,
        ),
        clock_ms=lambda: 0,
    )
    limiter.observe_response(
        headers={"X-MBX-ORDER-COUNT-10S": "3"},
        status_code=200,
        now_ms=0,
    )
    snapshot = limiter.snapshot(now_ms=0)
    assert snapshot.order_tokens_remaining == 1.0


def test_retry_after_header_applies_throttle_window() -> None:
    limiter = BinanceApiRateLimiter(clock_ms=lambda: 0)
    limiter.observe_response(
        headers={"Retry-After": "3"},
        status_code=429,
        now_ms=0,
    )
    try:
        limiter.reserve(cost=BinanceRequestQuotaCost(request_weight=1), now_ms=2_000)
    except BinanceApiRateLimitExceededError as exc:
        assert "throttled" in str(exc)
    else:
        raise AssertionError("Expected active 429 throttle window to block")

    limiter.reserve(cost=BinanceRequestQuotaCost(request_weight=1), now_ms=3_000)


def test_exponential_429_backoff_grows_without_retry_after() -> None:
    limiter = BinanceApiRateLimiter(clock_ms=lambda: 0)
    limiter.observe_response(headers={}, status_code=429, now_ms=0)
    assert limiter.snapshot(now_ms=0).throttle_until_ms == 5_000

    limiter.observe_response(headers={}, status_code=429, now_ms=5_000)
    assert limiter.snapshot(now_ms=5_000).throttle_until_ms == 15_000


def test_non_429_response_resets_backoff_counter() -> None:
    limiter = BinanceApiRateLimiter(clock_ms=lambda: 0)
    limiter.observe_response(headers={}, status_code=429, now_ms=0)
    limiter.observe_response(headers={}, status_code=200, now_ms=5_000)
    limiter.observe_response(headers={}, status_code=429, now_ms=5_000)
    assert limiter.snapshot(now_ms=5_000).throttle_until_ms == 10_000
