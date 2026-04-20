"""Bounded Binance REST quota tracking with header sync and 429 backoff.

This slice stays deliberately narrow:
- track the supported Binance Spot REST endpoints used by V5.3
- throttle preemptively before the official exchange quota is exhausted
- tighten local state from real `X-MBX-USED-WEIGHT-*` / `X-MBX-ORDER-COUNT-*`
  headers whenever Binance returns them
- keep 429 handling explicit without adding hidden retry loops
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping

from interface_contracts import BinanceApiRateLimitExceededError
from pydantic import BaseModel, Field, model_validator


class BinanceRequestQuotaCost(BaseModel, frozen=True):
    """Local quota-cost hint for one supported Binance REST request."""

    request_weight: int = Field(default=1, ge=0)
    order_count_10s: int = Field(default=0, ge=0)


class BinanceApiRateLimiterConfig(BaseModel, frozen=True):
    """Operational ceilings for the bounded Binance quota tracker.

    The official limits remain recorded for audit clarity. Preemptive limits are
    intentionally lower and used by the local tracker before the venue hard cap.
    """

    official_request_weight_limit_1m: int = Field(default=1200, gt=0)
    preemptive_request_weight_limit_1m: int = Field(default=800, gt=0)
    official_request_weight_warn_ratio: float = Field(default=0.80, gt=0.0, le=1.0)
    official_request_weight_block_ratio: float = Field(default=0.95, gt=0.0, le=1.0)
    official_request_weight_block_window_s: float = Field(default=60.0, gt=0.0)
    official_orders_limit_10s: int = Field(default=50, gt=0)
    preemptive_orders_limit_10s: int = Field(default=40, gt=0)
    http_429_backoff_base_s: float = Field(default=5.0, gt=0.0)
    http_429_backoff_max_s: float = Field(default=60.0, gt=0.0)

    @model_validator(mode="after")
    def validate_limits(self) -> "BinanceApiRateLimiterConfig":
        if self.preemptive_request_weight_limit_1m > self.official_request_weight_limit_1m:
            raise ValueError("preemptive_request_weight_limit_1m must stay <= official_request_weight_limit_1m")
        if self.official_request_weight_warn_ratio >= self.official_request_weight_block_ratio:
            raise ValueError("official_request_weight_warn_ratio must stay < official_request_weight_block_ratio")
        if self.preemptive_orders_limit_10s > self.official_orders_limit_10s:
            raise ValueError("preemptive_orders_limit_10s must stay <= official_orders_limit_10s")
        if self.http_429_backoff_base_s > self.http_429_backoff_max_s:
            raise ValueError("http_429_backoff_base_s must stay <= http_429_backoff_max_s")
        return self


class BinanceApiRateLimiterSnapshot(BaseModel, frozen=True):
    """Audit-friendly view of the local quota tracker state."""

    request_weight_tokens_remaining: float = Field(..., ge=0.0)
    order_tokens_remaining: float = Field(..., ge=0.0)
    throttle_until_ms: int = Field(default=0, ge=0)
    official_request_weight_used_1m: int = Field(default=0, ge=0)
    official_request_weight_quota_ratio: float = Field(default=0.0, ge=0.0)
    official_request_weight_warn_active: bool = Field(default=False)
    official_request_weight_block_until_ms: int = Field(default=0, ge=0)
    official_request_weight_block_active: bool = Field(default=False)
    consecutive_429s: int = Field(default=0, ge=0)


class _TokenBucket:
    def __init__(self, *, capacity: int, window_s: float, now_ms: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if not math.isfinite(window_s) or window_s <= 0:
            raise ValueError("window_s must be finite and > 0")
        self._capacity = float(capacity)
        self._tokens = float(capacity)
        self._refill_per_ms = float(capacity) / (window_s * 1000.0)
        self._last_refill_ms = now_ms

    def remaining(self, now_ms: int) -> float:
        self._refill(now_ms)
        return self._tokens

    def can_consume(self, amount: int, now_ms: int) -> bool:
        if amount < 0:
            raise ValueError("amount must be >= 0")
        return self.remaining(now_ms) + 1e-9 >= float(amount)

    def consume(self, amount: int, now_ms: int) -> None:
        if amount < 0:
            raise ValueError("amount must be >= 0")
        if amount == 0:
            self._refill(now_ms)
            return
        self._refill(now_ms)
        self._tokens = max(self._tokens - float(amount), 0.0)

    def tighten_remaining(self, max_remaining: int, now_ms: int) -> None:
        if max_remaining < 0:
            raise ValueError("max_remaining must be >= 0")
        self._refill(now_ms)
        self._tokens = min(self._tokens, float(max_remaining))

    def _refill(self, now_ms: int) -> None:
        if now_ms <= self._last_refill_ms:
            return
        elapsed_ms = now_ms - self._last_refill_ms
        replenished = elapsed_ms * self._refill_per_ms
        self._tokens = min(self._capacity, self._tokens + replenished)
        self._last_refill_ms = now_ms


class BinanceApiRateLimiter:
    """Token-bucket guard for the bounded Binance Spot REST client."""

    def __init__(
        self,
        *,
        config: BinanceApiRateLimiterConfig | None = None,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        self._config = config or BinanceApiRateLimiterConfig()
        self._clock_ms = clock_ms or _system_clock_ms
        now_ms = self._clock_ms()
        self._request_weight_bucket = _TokenBucket(
            capacity=self._config.preemptive_request_weight_limit_1m,
            window_s=60.0,
            now_ms=now_ms,
        )
        self._order_bucket = _TokenBucket(
            capacity=self._config.preemptive_orders_limit_10s,
            window_s=10.0,
            now_ms=now_ms,
        )
        self._throttle_until_ms = 0
        self._official_request_weight_block_until_ms = 0
        self._official_request_weight_used_1m = 0
        self._official_request_weight_quota_ratio = 0.0
        self._consecutive_429s = 0

    def reserve(
        self,
        *,
        cost: BinanceRequestQuotaCost,
        now_ms: int | None = None,
    ) -> None:
        now = self._resolve_now_ms(now_ms)
        if now < self._official_request_weight_block_until_ms:
            remaining_ms = self._official_request_weight_block_until_ms - now
            raise BinanceApiRateLimitExceededError(
                "Binance REST requests are throttled for another "
                f"{remaining_ms} ms after venue request-weight usage crossed the official block threshold"
            )
        if now < self._throttle_until_ms:
            remaining_ms = self._throttle_until_ms - now
            raise BinanceApiRateLimitExceededError(
                f"Binance REST requests are throttled for another {remaining_ms} ms after a prior 429"
            )
        if not self._request_weight_bucket.can_consume(cost.request_weight, now):
            remaining = self._request_weight_bucket.remaining(now)
            raise BinanceApiRateLimitExceededError(
                "Binance request-weight budget exhausted before official quota: "
                f"need={cost.request_weight} remaining={remaining:.3f} "
                f"limit={self._config.preemptive_request_weight_limit_1m}"
            )
        if not self._order_bucket.can_consume(cost.order_count_10s, now):
            remaining = self._order_bucket.remaining(now)
            raise BinanceApiRateLimitExceededError(
                "Binance order-count budget exhausted before official quota: "
                f"need={cost.order_count_10s} remaining={remaining:.3f} "
                f"limit={self._config.preemptive_orders_limit_10s}"
            )
        self._request_weight_bucket.consume(cost.request_weight, now)
        self._order_bucket.consume(cost.order_count_10s, now)

    def observe_response(
        self,
        *,
        headers: Mapping[str, str],
        status_code: int,
        now_ms: int | None = None,
    ) -> None:
        now = self._resolve_now_ms(now_ms)
        used_weight = _read_int_header(headers, "X-MBX-USED-WEIGHT-1M")
        if used_weight is not None:
            self._official_request_weight_used_1m = used_weight
            self._official_request_weight_quota_ratio = used_weight / float(
                self._config.official_request_weight_limit_1m
            )
            remaining_weight = max(self._config.preemptive_request_weight_limit_1m - used_weight, 0)
            self._request_weight_bucket.tighten_remaining(remaining_weight, now)
            if self._official_request_weight_quota_ratio >= self._config.official_request_weight_block_ratio:
                self._official_request_weight_block_until_ms = max(
                    self._official_request_weight_block_until_ms,
                    now + int(math.ceil(self._config.official_request_weight_block_window_s * 1000.0)),
                )
        used_orders = _read_int_header(headers, "X-MBX-ORDER-COUNT-10S")
        if used_orders is not None:
            remaining_orders = max(self._config.preemptive_orders_limit_10s - used_orders, 0)
            self._order_bucket.tighten_remaining(remaining_orders, now)

        if status_code == 429:
            self._apply_429_backoff(headers=headers, now_ms=now)
            self._request_weight_bucket.tighten_remaining(0, now)
            self._order_bucket.tighten_remaining(0, now)
            return

        self._consecutive_429s = 0

    def snapshot(self, *, now_ms: int | None = None) -> BinanceApiRateLimiterSnapshot:
        now = self._resolve_now_ms(now_ms)
        effective_throttle_until_ms = max(
            self._throttle_until_ms,
            self._official_request_weight_block_until_ms,
        )
        return BinanceApiRateLimiterSnapshot(
            request_weight_tokens_remaining=self._request_weight_bucket.remaining(now),
            order_tokens_remaining=self._order_bucket.remaining(now),
            throttle_until_ms=effective_throttle_until_ms,
            official_request_weight_used_1m=self._official_request_weight_used_1m,
            official_request_weight_quota_ratio=self._official_request_weight_quota_ratio,
            official_request_weight_warn_active=(
                self._official_request_weight_used_1m > 0
                and self._official_request_weight_quota_ratio >= self._config.official_request_weight_warn_ratio
            ),
            official_request_weight_block_until_ms=self._official_request_weight_block_until_ms,
            official_request_weight_block_active=now < self._official_request_weight_block_until_ms,
            consecutive_429s=self._consecutive_429s,
        )

    def _apply_429_backoff(self, *, headers: Mapping[str, str], now_ms: int) -> None:
        retry_after_s = _read_float_header(headers, "Retry-After")
        if retry_after_s is None or retry_after_s <= 0.0:
            retry_after_s = min(
                self._config.http_429_backoff_base_s * (2 ** self._consecutive_429s),
                self._config.http_429_backoff_max_s,
            )
        self._consecutive_429s += 1
        throttle_until_ms = now_ms + int(math.ceil(retry_after_s * 1000.0))
        self._throttle_until_ms = max(self._throttle_until_ms, throttle_until_ms)

    def _resolve_now_ms(self, now_ms: int | None) -> int:
        resolved = self._clock_ms() if now_ms is None else now_ms
        if resolved < 0:
            raise ValueError("now_ms must be >= 0")
        return resolved


def classify_binance_request_quota_cost(
    path: str,
    *,
    method: str = "GET",
    params: Mapping[str, str] | None = None,
) -> BinanceRequestQuotaCost:
    """Return a conservative local quota-cost hint for one supported endpoint.

    The real venue headers remain the source of truth after each response. These
    costs are only the bounded pre-request hints needed for proactive throttling.
    """

    normalized_method = method.upper()
    normalized_path = path.strip()
    request_params = dict(params or {})

    if normalized_method == "GET" and normalized_path == "/api/v3/time":
        return BinanceRequestQuotaCost(request_weight=1)
    if normalized_method == "GET" and normalized_path == "/api/v3/exchangeInfo":
        return BinanceRequestQuotaCost(
            request_weight=1 if request_params.get("symbol") else 20
        )
    if normalized_method == "GET" and normalized_path == "/api/v3/depth":
        limit = _coerce_positive_int(request_params.get("limit"), fallback=100)
        if limit <= 100:
            return BinanceRequestQuotaCost(request_weight=5)
        if limit <= 500:
            return BinanceRequestQuotaCost(request_weight=25)
        return BinanceRequestQuotaCost(request_weight=50)
    if normalized_method == "GET" and normalized_path == "/api/v3/account":
        return BinanceRequestQuotaCost(request_weight=20)
    if normalized_method == "GET" and normalized_path == "/api/v3/openOrders":
        return BinanceRequestQuotaCost(
            request_weight=6 if request_params.get("symbol") else 80
        )
    if normalized_path == "/api/v3/order" and normalized_method in {"POST", "DELETE"}:
        return BinanceRequestQuotaCost(request_weight=1, order_count_10s=1)
    if normalized_path.startswith("/sapi/"):
        return BinanceRequestQuotaCost(request_weight=10)
    return BinanceRequestQuotaCost(request_weight=1)


def _read_int_header(headers: Mapping[str, str], name: str) -> int | None:
    value = _read_header(headers, name)
    if value is None or value == "":
        return None
    try:
        return max(int(value), 0)
    except ValueError:
        return None


def _read_float_header(headers: Mapping[str, str], name: str) -> float | None:
    value = _read_header(headers, name)
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _read_header(headers: Mapping[str, str], name: str) -> str | None:
    if name in headers:
        return headers[name]
    lowered_name = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered_name:
            return value
    return None


def _coerce_positive_int(value: object, *, fallback: int) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def _system_clock_ms() -> int:
    return time.time_ns() // 1_000_000


__all__ = [
    "BinanceApiRateLimiter",
    "BinanceApiRateLimiterConfig",
    "BinanceApiRateLimiterSnapshot",
    "BinanceApiRateLimitExceededError",
    "BinanceRequestQuotaCost",
    "classify_binance_request_quota_cost",
]
