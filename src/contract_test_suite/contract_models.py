"""
6.5.0 — Contract Models: shared types for the contract test infrastructure.

A ContractDefinition declares what a module promises.
A ContractResult records whether a specific test passed or failed.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ContractStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


class ContractCategory(StrEnum):
    SCHEMA = "schema"          # field presence, type, bounds
    NEGATIVE = "negative"      # expected rejection of invalid input
    INVARIANT = "invariant"    # business logic invariant
    COMPATIBILITY = "compat"   # backward-compatibility check


class ContractDefinition(BaseModel, frozen=True):
    """Declaration of a single contract to verify.

    A contract belongs to a module, has a category, and a human description.
    """

    module_name: str = Field(..., min_length=1)
    contract_name: str = Field(..., min_length=1)
    category: ContractCategory
    description: str = Field(default="")
    critical: bool = Field(default=True)


class ContractResult(BaseModel, frozen=True):
    """Result of executing a single contract test."""

    contract: ContractDefinition
    status: ContractStatus
    message: str = Field(default="")
    duration_ms: float = Field(default=0.0, ge=0.0)

    @property
    def passed(self) -> bool:
        return self.status == ContractStatus.PASS

    @property
    def failed(self) -> bool:
        return self.status in (ContractStatus.FAIL, ContractStatus.ERROR)


class ModuleContractReport(BaseModel, frozen=True):
    """Aggregate results for a single module."""

    module_name: str
    results: tuple[ContractResult, ...]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.failed)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def has_critical_failure(self) -> bool:
        return any(r.failed and r.contract.critical for r in self.results)


class SuiteReport(BaseModel, frozen=True):
    """Top-level report for the entire contract test suite."""

    module_reports: tuple[ModuleContractReport, ...]
    passed: bool

    @property
    def total_contracts(self) -> int:
        return sum(m.total for m in self.module_reports)

    @property
    def total_passed(self) -> int:
        return sum(m.passed_count for m in self.module_reports)

    @property
    def total_failed(self) -> int:
        return sum(m.failed_count for m in self.module_reports)
