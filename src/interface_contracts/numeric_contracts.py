"""
V5.3 - NUMERIC_CONTRACTS
========================
Shared numeric policy helpers for prod-safe execution values.

Scope:
- exact execution values such as price, quantity, fee, notional
- Decimal-based arithmetic only where execution exactness matters
- no replacement of float64 analytics/scoring layers
"""

from __future__ import annotations

import math
from decimal import Decimal, ROUND_CEILING, ROUND_DOWN, ROUND_HALF_EVEN, localcontext
from typing import Iterable, SupportsFloat


EXECUTION_DECIMAL_CONTEXT_PRECISION = 28
EXECUTION_DECIMAL_ROUNDING = ROUND_HALF_EVEN


def execution_decimal(value: Decimal | SupportsFloat | str, *, name: str = "value") -> Decimal:
    """Convert an execution value to a finite Decimal without float32-style drift."""

    if isinstance(value, bool):
        raise TypeError(f"{name} must not be bool")
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        decimal_value = Decimal(str(value))
    else:
        decimal_value = Decimal(str(value))
    if not decimal_value.is_finite():
        raise ValueError(f"{name} must be finite")
    return decimal_value


def decimal_to_canonical_str(value: Decimal | SupportsFloat | str) -> str:
    """Serialize Decimal values without scientific notation for audit-ready payloads."""

    decimal_value = execution_decimal(value)
    text = format(decimal_value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def multiply_exact(
    left: Decimal | SupportsFloat | str,
    right: Decimal | SupportsFloat | str,
) -> Decimal:
    """Exact Decimal multiplication for price * quantity style calculations."""

    with localcontext() as context:
        context.prec = EXECUTION_DECIMAL_CONTEXT_PRECISION
        context.rounding = EXECUTION_DECIMAL_ROUNDING
        return execution_decimal(left, name="left") * execution_decimal(right, name="right")


def divide_exact_or_zero(
    numerator: Decimal | SupportsFloat | str,
    denominator: Decimal | SupportsFloat | str,
) -> Decimal:
    """Exact Decimal division with explicit zero-denominator fallback."""

    denominator_decimal = execution_decimal(denominator, name="denominator")
    if denominator_decimal == 0:
        return Decimal("0")
    with localcontext() as context:
        context.prec = EXECUTION_DECIMAL_CONTEXT_PRECISION
        context.rounding = EXECUTION_DECIMAL_ROUNDING
        return execution_decimal(numerator, name="numerator") / denominator_decimal


def sum_exact(values: Iterable[Decimal | SupportsFloat | str]) -> Decimal:
    """Exact Decimal summation for execution values."""

    total = Decimal("0")
    with localcontext() as context:
        context.prec = EXECUTION_DECIMAL_CONTEXT_PRECISION
        context.rounding = EXECUTION_DECIMAL_ROUNDING
        for value in values:
            total += execution_decimal(value)
    return total


def quantize_down_to_step(
    value: Decimal | SupportsFloat | str,
    step: Decimal | SupportsFloat | str,
) -> Decimal:
    """Quantize a positive value downward to the nearest valid venue step."""

    step_decimal = execution_decimal(step, name="step")
    if step_decimal <= 0:
        raise ValueError("step must be > 0")
    value_decimal = execution_decimal(value, name="value")
    if value_decimal < 0:
        raise ValueError("value must be >= 0")
    with localcontext() as context:
        context.prec = EXECUTION_DECIMAL_CONTEXT_PRECISION
        context.rounding = EXECUTION_DECIMAL_ROUNDING
        units = (value_decimal / step_decimal).to_integral_value(rounding=ROUND_DOWN)
        return units * step_decimal


def quantize_up_to_step(
    value: Decimal | SupportsFloat | str,
    step: Decimal | SupportsFloat | str,
) -> Decimal:
    """Quantize a positive value upward to the nearest valid venue step."""

    step_decimal = execution_decimal(step, name="step")
    if step_decimal <= 0:
        raise ValueError("step must be > 0")
    value_decimal = execution_decimal(value, name="value")
    if value_decimal < 0:
        raise ValueError("value must be >= 0")
    with localcontext() as context:
        context.prec = EXECUTION_DECIMAL_CONTEXT_PRECISION
        context.rounding = EXECUTION_DECIMAL_ROUNDING
        units = (value_decimal / step_decimal).to_integral_value(rounding=ROUND_CEILING)
        return units * step_decimal


def decimal_to_float64(value: Decimal | SupportsFloat | str) -> float:
    """Bridge exact Decimal execution values back to Python float / binary64."""

    return float(execution_decimal(value))


__all__ = [
    "EXECUTION_DECIMAL_CONTEXT_PRECISION",
    "EXECUTION_DECIMAL_ROUNDING",
    "execution_decimal",
    "decimal_to_canonical_str",
    "multiply_exact",
    "divide_exact_or_zero",
    "sum_exact",
    "quantize_down_to_step",
    "quantize_up_to_step",
    "decimal_to_float64",
]
