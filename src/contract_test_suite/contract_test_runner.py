"""
6.5.1 — Contract Test Runner: execute contract suites per module.

Orchestrates schema_assertions, negative_case_runner, and any custom
invariant checks registered for each module. Produces ModuleContractReport.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Type

from pydantic import BaseModel

from contract_test_suite.contract_models import (
    ContractCategory,
    ContractDefinition,
    ContractResult,
    ContractStatus,
    ModuleContractReport,
)


# Type alias for a contract test function: () -> ContractResult
ContractTestFn = Callable[[], ContractResult]


class ContractSuite:
    """A collection of contract tests for a single module.

    Usage:
        suite = ContractSuite("interface_contracts")
        suite.add_test(lambda: assert_field_present(TradeEvent, "price", "interface_contracts"))
        suite.add_test(my_invariant_check)
        report = suite.run()
    """

    def __init__(self, module_name: str) -> None:
        self.module_name = module_name
        self._tests: list[ContractTestFn] = []

    def add_test(self, test_fn: ContractTestFn) -> None:
        """Register a contract test function."""
        self._tests.append(test_fn)

    def add_tests(self, test_fns: list[ContractTestFn]) -> None:
        """Register multiple contract test functions."""
        self._tests.extend(test_fns)

    @property
    def test_count(self) -> int:
        return len(self._tests)

    def run(self) -> ModuleContractReport:
        """Execute all registered tests and return the module report.

        Spec 6.13: logs module, contract, status, duration, failure reason.
        """
        results: list[ContractResult] = []

        for test_fn in self._tests:
            start = time.perf_counter()
            try:
                result = test_fn()
                elapsed_ms = (time.perf_counter() - start) * 1000
                # Inject duration
                result = ContractResult(
                    contract=result.contract,
                    status=result.status,
                    message=result.message,
                    duration_ms=round(elapsed_ms, 3),
                )
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000
                # Test itself errored — create an ERROR result
                result = ContractResult(
                    contract=ContractDefinition(
                        module_name=self.module_name,
                        contract_name=getattr(test_fn, "__name__", "unknown"),
                        category=ContractCategory.INVARIANT,
                        description="Contract test raised an unexpected exception",
                    ),
                    status=ContractStatus.ERROR,
                    message=f"{type(e).__name__}: {e}"[:300],
                    duration_ms=round(elapsed_ms, 3),
                )
            results.append(result)

        return ModuleContractReport(
            module_name=self.module_name,
            results=tuple(results),
        )


def run_suites(suites: list[ContractSuite]) -> list[ModuleContractReport]:
    """Run multiple contract suites and return their reports."""
    return [suite.run() for suite in suites]
