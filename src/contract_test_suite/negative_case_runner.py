"""
6.5.3 — Negative Case Runner: execute expected-failure test cases.

A NegativeCase declares that given certain invalid inputs, the system
must reject them (raise ValidationError, return error, etc.).
This ensures we test more than happy paths — spec 6.15 drift prevention.
"""

from __future__ import annotations

from typing import Callable

from pydantic import BaseModel, ValidationError

from contract_test_suite.contract_models import (
    ContractCategory,
    ContractDefinition,
    ContractResult,
    ContractStatus,
)


class NegativeCase(BaseModel, frozen=True):
    """Declaration of a single negative test case."""

    module_name: str
    case_name: str
    description: str = ""
    critical: bool = True


def run_negative_pydantic(
    case: NegativeCase,
    model_class: type[BaseModel],
    invalid_data: dict[str, object],
) -> ContractResult:
    """Run a negative case against a Pydantic model.

    Expects that model_class(**invalid_data) raises ValidationError.
    """
    contract = ContractDefinition(
        module_name=case.module_name,
        contract_name=case.case_name,
        category=ContractCategory.NEGATIVE,
        description=case.description,
        critical=case.critical,
    )
    try:
        model_class(**invalid_data)
        return ContractResult(
            contract=contract,
            status=ContractStatus.FAIL,
            message=f"{model_class.__name__} accepted invalid data (should have rejected)",
        )
    except (ValidationError, TypeError, ValueError):
        return ContractResult(contract=contract, status=ContractStatus.PASS)


def run_negative_callable(
    case: NegativeCase,
    func: Callable[..., object],
    args: tuple[object, ...] = (),
    kwargs: dict[str, object] | None = None,
    expected_exception: type[Exception] = Exception,
) -> ContractResult:
    """Run a negative case against a callable.

    Expects that func(*args, **kwargs) raises expected_exception.
    """
    contract = ContractDefinition(
        module_name=case.module_name,
        contract_name=case.case_name,
        category=ContractCategory.NEGATIVE,
        description=case.description,
        critical=case.critical,
    )
    try:
        func(*args, **(kwargs or {}))
        return ContractResult(
            contract=contract,
            status=ContractStatus.FAIL,
            message=f"{func.__name__} did not raise {expected_exception.__name__}",
        )
    except expected_exception:
        return ContractResult(contract=contract, status=ContractStatus.PASS)
    except Exception as e:
        return ContractResult(
            contract=contract,
            status=ContractStatus.FAIL,
            message=f"Raised {type(e).__name__} instead of {expected_exception.__name__}: {e}",
        )
