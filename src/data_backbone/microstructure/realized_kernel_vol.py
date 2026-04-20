"""
V5.3 - REALIZED KERNEL VOLATILITY
Canonical Parzen-kernel realized-vol estimator for microstructure-aware volatility.
"""

from __future__ import annotations

from hashlib import sha256
import json
from math import ceil, log, sqrt

from pydantic import BaseModel, ConfigDict, Field, field_validator


REALIZED_KERNEL_METHOD_VERSION = "realized_kernel_vol.parzen.v1"
REALIZED_KERNEL_METHOD_VERSION_HASH = sha256(
    REALIZED_KERNEL_METHOD_VERSION.encode("utf-8")
).hexdigest()
DEFAULT_RK_BANDWIDTH_C = 0.4
MAX_RK_BANDWIDTH_C = 1.0
DEFAULT_RK_BUCKET_SECONDS = 300.0
MAX_RK_BUCKET_SECONDS = 900.0


class RealizedKernelPricePoint(BaseModel):
    """Bucket-close price point used by the realized-kernel estimator."""

    timestamp_ns: int = Field(..., ge=1)
    price: float = Field(..., gt=0.0)

    model_config = ConfigDict(frozen=True, extra="forbid")


class RealizedKernelVolRecord(BaseModel):
    """Audit-ready realized-kernel output record."""

    value: float = Field(..., ge=0.0)
    kernel_variance: float = Field(..., ge=0.0)
    bandwidth: int = Field(..., ge=1)
    low_sample_confidence: bool = False
    insufficient_variation: bool = False
    n_events_received: int = Field(..., ge=2)
    window_used: tuple[int | None, float | None]
    n_events_used: int = Field(..., ge=2)
    method_version_hash: str = Field(..., min_length=8)
    pair: str = Field(..., min_length=1)
    computed_at_ns: int = Field(..., ge=1)
    input_data_hash: str = Field(..., min_length=8)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("pair")
    @classmethod
    def _normalize_pair(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("pair must not be blank")
        return normalized


def parzen_kernel_weight(x: float) -> float:
    """Flat-top Parzen kernel from BNHLS 2008 eq.(3.5)."""

    absolute = abs(x)
    if absolute <= 0.5:
        return 1.0 - (6.0 * absolute * absolute) + (6.0 * absolute * absolute * absolute)
    if absolute <= 1.0:
        return 2.0 * ((1.0 - absolute) ** 3)
    return 0.0


def resolve_realized_kernel_bandwidth(
    sample_size: int,
    *,
    bandwidth_c: float = DEFAULT_RK_BANDWIDTH_C,
) -> int:
    """Resolve H = ceil(c * n^(3/5)) under V5.3 caps."""

    if sample_size < 2:
        raise ValueError("sample_size must be >= 2")
    if not 0.0 < bandwidth_c <= MAX_RK_BANDWIDTH_C:
        raise ValueError(
            f"bandwidth_c must be in (0, {MAX_RK_BANDWIDTH_C}]"
        )
    upper_bound = max(1, sample_size - 1)
    resolved = ceil(bandwidth_c * (sample_size ** (3.0 / 5.0)))
    return min(max(1, resolved), upper_bound)


def _autocovariance(log_returns: list[float], lag: int) -> float:
    if lag == 0:
        return sum(value * value for value in log_returns)
    return sum(
        log_returns[index] * log_returns[index - lag]
        for index in range(lag, len(log_returns))
    )


def _hash_input(
    *,
    pair: str,
    bucket_seconds: float,
    bandwidth_c: float,
    points: list[RealizedKernelPricePoint],
) -> str:
    payload = {
        "pair": pair,
        "bucket_seconds": bucket_seconds,
        "bandwidth_c": bandwidth_c,
        "points": [
            {"timestamp_ns": point.timestamp_ns, "price": point.price}
            for point in points
        ],
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def compute_realized_kernel_vol(
    points: list[RealizedKernelPricePoint],
    *,
    pair: str,
    bucket_seconds: float = DEFAULT_RK_BUCKET_SECONDS,
    bandwidth_c: float = DEFAULT_RK_BANDWIDTH_C,
    computed_at_ns: int | None = None,
) -> RealizedKernelVolRecord:
    """Compute realized-kernel volatility on bucket-close prices."""

    if len(points) < 3:
        raise ValueError("at least 3 bucket-close prices are required")
    if not 0.0 < bucket_seconds <= MAX_RK_BUCKET_SECONDS:
        raise ValueError(
            f"bucket_seconds must be in (0, {MAX_RK_BUCKET_SECONDS}]"
        )
    for previous, current in zip(points, points[1:]):
        if current.timestamp_ns < previous.timestamp_ns:
            raise ValueError("points must be non-decreasing in timestamp_ns")
    eval_time_ns = points[-1].timestamp_ns if computed_at_ns is None else computed_at_ns
    if eval_time_ns < points[-1].timestamp_ns:
        raise ValueError("computed_at_ns must be >= latest point timestamp")

    log_returns = [
        log(current.price) - log(previous.price)
        for previous, current in zip(points, points[1:])
    ]
    bandwidth = resolve_realized_kernel_bandwidth(
        len(log_returns),
        bandwidth_c=bandwidth_c,
    )
    gamma_0 = _autocovariance(log_returns, 0)
    kernel_variance = gamma_0
    for lag in range(1, bandwidth + 1):
        gamma_h = _autocovariance(log_returns, lag)
        weight = parzen_kernel_weight((lag - 1) / bandwidth)
        kernel_variance += weight * (gamma_h + gamma_h)

    bounded_variance = max(kernel_variance, 0.0)
    observed_window_seconds = (points[-1].timestamp_ns - points[0].timestamp_ns) / 1_000_000_000.0
    return RealizedKernelVolRecord(
        value=sqrt(bounded_variance),
        kernel_variance=bounded_variance,
        bandwidth=bandwidth,
        low_sample_confidence=len(log_returns) < 10,
        insufficient_variation=bounded_variance <= 0.0,
        n_events_received=len(points),
        window_used=(len(points), observed_window_seconds),
        n_events_used=len(points),
        method_version_hash=REALIZED_KERNEL_METHOD_VERSION_HASH,
        pair=pair,
        computed_at_ns=eval_time_ns,
        input_data_hash=_hash_input(
            pair=pair,
            bucket_seconds=bucket_seconds,
            bandwidth_c=bandwidth_c,
            points=points,
        ),
    )


__all__ = [
    "DEFAULT_RK_BANDWIDTH_C",
    "DEFAULT_RK_BUCKET_SECONDS",
    "MAX_RK_BANDWIDTH_C",
    "MAX_RK_BUCKET_SECONDS",
    "REALIZED_KERNEL_METHOD_VERSION",
    "REALIZED_KERNEL_METHOD_VERSION_HASH",
    "RealizedKernelPricePoint",
    "RealizedKernelVolRecord",
    "compute_realized_kernel_vol",
    "parzen_kernel_weight",
    "resolve_realized_kernel_bandwidth",
]
