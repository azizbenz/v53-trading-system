"""
contract_test_suite — Module 4: Tests de contrat par module.

Guarantees that each module respects its contracts in reality, not just on paper.
A broken contract MUST fail the build — spec 6.9.

Dependencies: interface_contracts, manifest_registry
"""

from contract_test_suite.contract_models import (
    ContractCategory,
    ContractDefinition,
    ContractResult,
    ContractStatus,
    ModuleContractReport,
    SuiteReport,
)
from contract_test_suite.contract_test_runner import (
    ContractSuite,
    ContractTestFn,
    run_suites,
)
from contract_test_suite.schema_assertions import (
    assert_bounds,
    assert_field_absent,
    assert_field_present,
    assert_field_type,
    assert_invalid_rejected,
    assert_valid_instance,
)
from contract_test_suite.negative_case_runner import (
    NegativeCase,
    run_negative_callable,
    run_negative_pydantic,
)
from contract_test_suite.compatibility_checker import (
    FieldSnapshot,
    SchemaSnapshot,
    check_compatibility,
    snapshot_model,
)
from contract_test_suite.contract_reporter import (
    build_suite_report,
    format_suite_report,
)

__all__ = [
    # Models
    "ContractCategory",
    "ContractDefinition",
    "ContractResult",
    "ContractStatus",
    "ModuleContractReport",
    "SuiteReport",
    # Runner
    "ContractSuite",
    "ContractTestFn",
    "run_suites",
    # Schema assertions
    "assert_bounds",
    "assert_field_absent",
    "assert_field_present",
    "assert_field_type",
    "assert_invalid_rejected",
    "assert_valid_instance",
    # Negative cases
    "NegativeCase",
    "run_negative_callable",
    "run_negative_pydantic",
    # Compatibility
    "FieldSnapshot",
    "SchemaSnapshot",
    "check_compatibility",
    "snapshot_model",
    # Reporter
    "build_suite_report",
    "format_suite_report",
]
