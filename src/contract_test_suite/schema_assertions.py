"""
6.5.2 — Schema Assertions: verify field presence, absence, types, bounds, units.

Provides reusable assertion helpers that contract tests call to validate
that a Pydantic model conforms to its declared schema contract.
"""

from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel, ValidationError

from contract_test_suite.contract_models import (
    ContractCategory,
    ContractDefinition,
    ContractResult,
    ContractStatus,
)


def assert_field_present(
    model_class: Type[BaseModel],
    field_name: str,
    module_name: str,
) -> ContractResult:
    """Assert that a model class declares a given field."""
    contract = ContractDefinition(
        module_name=module_name,
        contract_name=f"{model_class.__name__}.{field_name}_present",
        category=ContractCategory.SCHEMA,
        description=f"Field '{field_name}' must exist on {model_class.__name__}",
    )
    if field_name in model_class.model_fields:
        return ContractResult(contract=contract, status=ContractStatus.PASS)
    return ContractResult(
        contract=contract,
        status=ContractStatus.FAIL,
        message=f"Field '{field_name}' not found on {model_class.__name__}",
    )


def assert_field_absent(
    model_class: Type[BaseModel],
    field_name: str,
    module_name: str,
) -> ContractResult:
    """Assert that a model class does NOT declare a given field."""
    contract = ContractDefinition(
        module_name=module_name,
        contract_name=f"{model_class.__name__}.{field_name}_absent",
        category=ContractCategory.SCHEMA,
        description=f"Field '{field_name}' must not exist on {model_class.__name__}",
    )
    if field_name not in model_class.model_fields:
        return ContractResult(contract=contract, status=ContractStatus.PASS)
    return ContractResult(
        contract=contract,
        status=ContractStatus.FAIL,
        message=f"Field '{field_name}' unexpectedly found on {model_class.__name__}",
    )


def assert_field_type(
    model_class: Type[BaseModel],
    field_name: str,
    expected_type: Type,
    module_name: str,
) -> ContractResult:
    """Assert that a field's annotation matches the expected type."""
    contract = ContractDefinition(
        module_name=module_name,
        contract_name=f"{model_class.__name__}.{field_name}_type",
        category=ContractCategory.SCHEMA,
        description=f"Field '{field_name}' must be of type {expected_type.__name__}",
    )
    field_info = model_class.model_fields.get(field_name)
    if field_info is None:
        return ContractResult(
            contract=contract,
            status=ContractStatus.FAIL,
            message=f"Field '{field_name}' does not exist",
        )
    annotation = field_info.annotation
    if annotation is expected_type or (
        hasattr(annotation, "__origin__") and annotation is expected_type
    ):
        return ContractResult(contract=contract, status=ContractStatus.PASS)
    # Check if it's a subclass
    try:
        if issubclass(annotation, expected_type):  # type: ignore[arg-type]
            return ContractResult(contract=contract, status=ContractStatus.PASS)
    except TypeError:
        pass
    return ContractResult(
        contract=contract,
        status=ContractStatus.FAIL,
        message=f"Field '{field_name}' has type {annotation}, expected {expected_type}",
    )


def assert_valid_instance(
    model_class: Type[BaseModel],
    data: dict[str, Any],
    module_name: str,
    contract_name: str = "",
) -> ContractResult:
    """Assert that data can construct a valid model instance."""
    cname = contract_name or f"{model_class.__name__}_valid_construction"
    contract = ContractDefinition(
        module_name=module_name,
        contract_name=cname,
        category=ContractCategory.SCHEMA,
        description=f"Data must produce a valid {model_class.__name__}",
    )
    try:
        model_class(**data)
        return ContractResult(contract=contract, status=ContractStatus.PASS)
    except (ValidationError, TypeError, ValueError) as e:
        return ContractResult(
            contract=contract,
            status=ContractStatus.FAIL,
            message=str(e)[:300],
        )


def assert_invalid_rejected(
    model_class: Type[BaseModel],
    data: dict[str, Any],
    module_name: str,
    contract_name: str = "",
    reason: str = "",
) -> ContractResult:
    """Assert that invalid data is REJECTED by the model (negative test).

    This is a schema-level negative assertion: the model must raise
    ValidationError when given invalid data.
    """
    cname = contract_name or f"{model_class.__name__}_rejects_invalid"
    contract = ContractDefinition(
        module_name=module_name,
        contract_name=cname,
        category=ContractCategory.NEGATIVE,
        description=reason or f"Invalid data must be rejected by {model_class.__name__}",
    )
    try:
        model_class(**data)
        return ContractResult(
            contract=contract,
            status=ContractStatus.FAIL,
            message=f"{model_class.__name__} accepted invalid data: {data}",
        )
    except (ValidationError, TypeError, ValueError):
        return ContractResult(contract=contract, status=ContractStatus.PASS)


def assert_bounds(
    model_class: Type[BaseModel],
    field_name: str,
    valid_value: Any,
    invalid_low: Any | None,
    invalid_high: Any | None,
    base_data: dict[str, Any],
    module_name: str,
) -> list[ContractResult]:
    """Assert that a field enforces its bounds.

    Returns up to 3 results: valid value accepted, too-low rejected, too-high rejected.
    """
    results: list[ContractResult] = []

    # Valid value must be accepted
    data_ok = {**base_data, field_name: valid_value}
    results.append(assert_valid_instance(
        model_class, data_ok, module_name,
        contract_name=f"{model_class.__name__}.{field_name}_valid_bound",
    ))

    # Too-low must be rejected
    if invalid_low is not None:
        data_low = {**base_data, field_name: invalid_low}
        results.append(assert_invalid_rejected(
            model_class, data_low, module_name,
            contract_name=f"{model_class.__name__}.{field_name}_rejects_low",
            reason=f"{field_name}={invalid_low} must be rejected (too low)",
        ))

    # Too-high must be rejected
    if invalid_high is not None:
        data_high = {**base_data, field_name: invalid_high}
        results.append(assert_invalid_rejected(
            model_class, data_high, module_name,
            contract_name=f"{model_class.__name__}.{field_name}_rejects_high",
            reason=f"{field_name}={invalid_high} must be rejected (too high)",
        ))

    return results
