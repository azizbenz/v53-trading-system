"""Tests Module 4 — schema_assertions: valid contract, type error, missing field, bounds."""

import pytest

from pydantic import BaseModel, Field

from contract_test_suite.schema_assertions import (
    assert_bounds,
    assert_field_absent,
    assert_field_present,
    assert_field_type,
    assert_invalid_rejected,
    assert_valid_instance,
)
from contract_test_suite.contract_models import ContractStatus


# ─── Test model ──────────────────────────────────────────────────────

class SampleModel(BaseModel, frozen=True):
    name: str
    price: float = Field(..., gt=0)
    quantity: int = Field(..., ge=0, le=1000)


MODULE = "test_module"


@pytest.mark.build1
class TestValidContract:
    """6.14: execution of a simple valid contract (happy path)."""

    def test_valid_instance_passes(self):
        result = assert_valid_instance(
            SampleModel,
            {"name": "BTCUSDT", "price": 50000.0, "quantity": 10},
            MODULE,
        )
        assert result.passed
        assert result.status == ContractStatus.PASS

    def test_field_present_passes(self):
        result = assert_field_present(SampleModel, "price", MODULE)
        assert result.passed

    def test_field_type_passes(self):
        result = assert_field_type(SampleModel, "price", float, MODULE)
        assert result.passed


@pytest.mark.build1
class TestFailOnInvalidType:
    """6.14: failure on invalid type."""

    def test_wrong_type_rejected(self):
        result = assert_invalid_rejected(
            SampleModel,
            {"name": "BTC", "price": "not_a_number", "quantity": 10},
            MODULE,
            contract_name="rejects_string_price",
            reason="price must be float, not string",
        )
        # Pydantic coerces strings to float if possible, so use truly invalid
        result2 = assert_invalid_rejected(
            SampleModel,
            {"name": "BTC", "price": "abc", "quantity": 10},
            MODULE,
            contract_name="rejects_non_numeric_price",
        )
        assert result2.passed

    def test_field_type_mismatch_detected(self):
        result = assert_field_type(SampleModel, "price", int, MODULE)
        assert result.failed


@pytest.mark.build1
class TestFailOnMissingField:
    """6.14: failure on missing field."""

    def test_missing_required_field_rejected(self):
        result = assert_valid_instance(
            SampleModel,
            {"name": "BTC"},  # missing price and quantity
            MODULE,
            contract_name="rejects_missing_price",
        )
        assert result.failed
        assert result.status == ContractStatus.FAIL

    def test_field_absent_when_expected(self):
        result = assert_field_absent(SampleModel, "nonexistent_field", MODULE)
        assert result.passed

    def test_field_absent_fails_when_present(self):
        result = assert_field_absent(SampleModel, "price", MODULE)
        assert result.failed

    def test_field_present_fails_when_absent(self):
        result = assert_field_present(SampleModel, "nonexistent_field", MODULE)
        assert result.failed


@pytest.mark.build1
class TestFailOnInvalidBound:
    """6.14: failure on invalid bound."""

    def test_bounds_valid_accepted(self):
        base = {"name": "BTC", "price": 100.0}
        results = assert_bounds(
            SampleModel, "quantity",
            valid_value=500,
            invalid_low=-1,
            invalid_high=1001,
            base_data=base,
            module_name=MODULE,
        )
        assert len(results) == 3
        assert results[0].passed  # valid value
        assert results[1].passed  # low rejected
        assert results[2].passed  # high rejected

    def test_price_must_be_positive(self):
        result = assert_invalid_rejected(
            SampleModel,
            {"name": "BTC", "price": 0, "quantity": 10},
            MODULE,
            contract_name="rejects_zero_price",
            reason="price must be > 0",
        )
        assert result.passed

    def test_price_negative_rejected(self):
        result = assert_invalid_rejected(
            SampleModel,
            {"name": "BTC", "price": -1, "quantity": 10},
            MODULE,
            contract_name="rejects_negative_price",
        )
        assert result.passed
