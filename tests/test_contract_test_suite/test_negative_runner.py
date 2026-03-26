"""Tests Module 4 — negative_case_runner: expected failures properly detected."""

import pytest

from pydantic import BaseModel, Field

from contract_test_suite.negative_case_runner import (
    NegativeCase,
    run_negative_callable,
    run_negative_pydantic,
)
from contract_test_suite.contract_models import ContractStatus


class StrictModel(BaseModel, frozen=True):
    value: int = Field(..., ge=0, le=100)


@pytest.mark.build1
class TestNegativePydantic:
    """Negative cases against Pydantic models."""

    def test_invalid_data_correctly_rejected(self):
        case = NegativeCase(
            module_name="test",
            case_name="rejects_negative_value",
            description="value < 0 must be rejected",
        )
        result = run_negative_pydantic(case, StrictModel, {"value": -1})
        assert result.passed

    def test_valid_data_causes_failure(self):
        """If valid data is passed to a negative test, it should FAIL."""
        case = NegativeCase(
            module_name="test",
            case_name="should_reject_but_doesnt",
        )
        result = run_negative_pydantic(case, StrictModel, {"value": 50})
        assert result.failed
        assert "accepted invalid data" in result.message

    def test_out_of_bounds_high_rejected(self):
        case = NegativeCase(
            module_name="test",
            case_name="rejects_101",
        )
        result = run_negative_pydantic(case, StrictModel, {"value": 101})
        assert result.passed


@pytest.mark.build1
class TestNegativeCallable:
    """Negative cases against callable functions."""

    def test_raising_function_passes(self):
        def always_fails() -> None:
            raise ValueError("expected")

        case = NegativeCase(
            module_name="test",
            case_name="must_raise_value_error",
        )
        result = run_negative_callable(
            case, always_fails, expected_exception=ValueError,
        )
        assert result.passed

    def test_non_raising_function_fails(self):
        def never_fails() -> int:
            return 42

        case = NegativeCase(
            module_name="test",
            case_name="should_raise_but_doesnt",
        )
        result = run_negative_callable(
            case, never_fails, expected_exception=ValueError,
        )
        assert result.failed

    def test_wrong_exception_type_fails(self):
        def raises_type_error() -> None:
            raise TypeError("wrong kind")

        case = NegativeCase(
            module_name="test",
            case_name="expects_value_error_not_type_error",
        )
        result = run_negative_callable(
            case, raises_type_error, expected_exception=ValueError,
        )
        assert result.failed
        assert "TypeError" in result.message
