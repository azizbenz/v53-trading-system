from __future__ import annotations

from decimal import Decimal

import pytest

from interface_contracts import (
    decimal_to_canonical_str,
    decimal_to_float64_abs_loss,
    decimal_to_float64,
    divide_exact_or_zero,
    execution_decimal,
    multiply_exact,
    sum_exact,
)


def test_execution_decimal_uses_string_based_decimal_for_floats():
    value = execution_decimal(0.1)

    assert value == Decimal("0.1")


def test_decimal_to_canonical_str_avoids_scientific_notation():
    assert decimal_to_canonical_str(Decimal("50000.1000")) == "50000.1"
    assert decimal_to_canonical_str(Decimal("0.0200")) == "0.02"


def test_exact_multiply_and_sum_keep_execution_values_stable():
    assert multiply_exact(50000.1, 0.2) == Decimal("10000.02")
    assert sum_exact((0.1, 0.2, 0.3)) == Decimal("0.6")


def test_divide_exact_or_zero_raises_for_zero_denominator():
    with pytest.raises(ZeroDivisionError):
        divide_exact_or_zero("1", "0")


def test_decimal_to_float64_bridges_exact_values_back_to_runtime():
    assert decimal_to_float64(Decimal("50.125")) == pytest.approx(50.125)


def test_decimal_to_float64_abs_loss_exposes_bridge_precision_gap():
    loss = decimal_to_float64_abs_loss(Decimal("0.1"))
    assert loss > Decimal("0")


def test_decimal_to_float64_rejects_loss_above_allowed_bound():
    with pytest.raises(ValueError, match="above allowed"):
        decimal_to_float64(Decimal("0.1"), max_abs_loss=Decimal("1e-20"), name="price")
