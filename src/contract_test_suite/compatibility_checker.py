"""
6.5.4 — Compatibility Checker: verify that contract changes don't break consumers.

Checks that a Pydantic model's schema hasn't lost required fields or changed
types in a way that would break existing downstream code.

Uses two snapshots (old schema, new schema) to detect breaking changes.
"""

from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel

from contract_test_suite.contract_models import (
    ContractCategory,
    ContractDefinition,
    ContractResult,
    ContractStatus,
)


class FieldSnapshot(BaseModel, frozen=True):
    """Frozen snapshot of a single field's schema."""

    name: str
    type_str: str
    required: bool  # True if no default value


class SchemaSnapshot(BaseModel, frozen=True):
    """Frozen snapshot of a model's field schema."""

    model_config = {"protected_namespaces": ()}
    model_name: str
    fields: tuple[FieldSnapshot, ...]


def snapshot_model(model_class: Type[BaseModel]) -> SchemaSnapshot:
    """Take a schema snapshot of a Pydantic model class."""
    fields: list[FieldSnapshot] = []
    for name, info in sorted(model_class.model_fields.items()):
        type_str = str(info.annotation) if info.annotation else "Any"
        is_required = info.is_required()
        fields.append(FieldSnapshot(name=name, type_str=type_str, required=is_required))
    return SchemaSnapshot(
        model_name=model_class.__name__,
        fields=tuple(fields),
    )


def check_compatibility(
    old_snapshot: SchemaSnapshot,
    new_snapshot: SchemaSnapshot,
    module_name: str,
) -> list[ContractResult]:
    """Compare old and new schema snapshots for breaking changes.

    Breaking changes:
    - Field removed
    - Field type changed
    - New required field added (no default — breaks existing constructors)
    - Existing optional field became required

    Non-breaking (allowed):
    - New field added with a default value
    - Field became optional (was required)
    """
    results: list[ContractResult] = []
    model = old_snapshot.model_name

    old_map: dict[str, FieldSnapshot] = {f.name: f for f in old_snapshot.fields}
    new_map: dict[str, FieldSnapshot] = {f.name: f for f in new_snapshot.fields}

    # 1. Removed fields
    for name, old_f in old_map.items():
        contract = ContractDefinition(
            module_name=module_name,
            contract_name=f"{model}.{name}_not_removed",
            category=ContractCategory.COMPATIBILITY,
            description=f"Field '{name}' must not be removed",
        )
        if name not in new_map:
            results.append(ContractResult(
                contract=contract,
                status=ContractStatus.FAIL,
                message=f"Field '{name}' was removed from {model}",
            ))
        else:
            results.append(ContractResult(contract=contract, status=ContractStatus.PASS))

    # 2. Type changes (on fields that still exist)
    for name, old_f in old_map.items():
        if name in new_map:
            new_f = new_map[name]
            contract = ContractDefinition(
                module_name=module_name,
                contract_name=f"{model}.{name}_type_stable",
                category=ContractCategory.COMPATIBILITY,
                description=f"Field '{name}' type must not change",
            )
            if old_f.type_str != new_f.type_str:
                results.append(ContractResult(
                    contract=contract,
                    status=ContractStatus.FAIL,
                    message=f"Type changed: {old_f.type_str} -> {new_f.type_str}",
                ))
            else:
                results.append(ContractResult(contract=contract, status=ContractStatus.PASS))

    # 3. New required fields added (BREAKING — callers don't provide them)
    for name, new_f in new_map.items():
        if name not in old_map:
            contract = ContractDefinition(
                module_name=module_name,
                contract_name=f"{model}.{name}_new_field_compat",
                category=ContractCategory.COMPATIBILITY,
                description=f"New field '{name}' must not be required",
            )
            if new_f.required:
                results.append(ContractResult(
                    contract=contract,
                    status=ContractStatus.FAIL,
                    message=f"New field '{name}' is required — breaks existing consumers",
                ))
            else:
                results.append(ContractResult(contract=contract, status=ContractStatus.PASS))

    # 4. Optional field became required (BREAKING)
    for name, old_f in old_map.items():
        if name in new_map:
            new_f = new_map[name]
            if not old_f.required and new_f.required:
                contract = ContractDefinition(
                    module_name=module_name,
                    contract_name=f"{model}.{name}_not_became_required",
                    category=ContractCategory.COMPATIBILITY,
                    description=f"Field '{name}' must not become required",
                )
                results.append(ContractResult(
                    contract=contract,
                    status=ContractStatus.FAIL,
                    message=f"Field '{name}' was optional, now required — breaks existing consumers",
                ))

    return results
