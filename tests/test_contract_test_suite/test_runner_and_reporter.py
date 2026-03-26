"""Tests Module 4 — contract_test_runner + contract_reporter: execution and report generation."""

import pytest

from pydantic import BaseModel, Field

from contract_test_suite.contract_models import (
    ContractCategory,
    ContractDefinition,
    ContractResult,
    ContractStatus,
    ModuleContractReport,
)
from contract_test_suite.contract_test_runner import ContractSuite, run_suites
from contract_test_suite.contract_reporter import build_suite_report, format_suite_report
from contract_test_suite.schema_assertions import assert_field_present, assert_valid_instance


class DemoModel(BaseModel, frozen=True):
    name: str
    price: float = Field(..., gt=0)


MODULE = "demo_module"


@pytest.mark.build1
class TestContractSuiteRunner:
    """6.5.1: execute contract test suites."""

    def test_empty_suite_all_passed(self):
        suite = ContractSuite("empty_mod")
        report = suite.run()
        assert report.all_passed
        assert report.total == 0

    def test_suite_with_passing_tests(self):
        suite = ContractSuite(MODULE)
        suite.add_test(lambda: assert_field_present(DemoModel, "name", MODULE))
        suite.add_test(lambda: assert_field_present(DemoModel, "price", MODULE))
        report = suite.run()
        assert report.all_passed
        assert report.total == 2
        assert report.passed_count == 2

    def test_suite_with_failing_test(self):
        suite = ContractSuite(MODULE)
        suite.add_test(lambda: assert_field_present(DemoModel, "name", MODULE))
        suite.add_test(lambda: assert_field_present(DemoModel, "nonexistent", MODULE))
        report = suite.run()
        assert not report.all_passed
        assert report.failed_count == 1

    def test_suite_captures_duration(self):
        suite = ContractSuite(MODULE)
        suite.add_test(lambda: assert_field_present(DemoModel, "name", MODULE))
        report = suite.run()
        assert report.results[0].duration_ms >= 0.0

    def test_suite_handles_exception_in_test(self):
        def bad_test() -> ContractResult:
            raise RuntimeError("boom")

        suite = ContractSuite(MODULE)
        suite.add_test(bad_test)
        report = suite.run()
        assert report.failed_count == 1
        assert report.results[0].status == ContractStatus.ERROR
        assert "boom" in report.results[0].message

    def test_run_multiple_suites(self):
        suite1 = ContractSuite("mod_a")
        suite1.add_test(lambda: assert_field_present(DemoModel, "name", "mod_a"))

        suite2 = ContractSuite("mod_b")
        suite2.add_test(lambda: assert_field_present(DemoModel, "price", "mod_b"))

        reports = run_suites([suite1, suite2])
        assert len(reports) == 2
        assert all(r.all_passed for r in reports)


@pytest.mark.build1
class TestCriticalFailure:
    """6.9: broken contract must fail the build."""

    def test_critical_failure_detected(self):
        failing = ContractResult(
            contract=ContractDefinition(
                module_name=MODULE,
                contract_name="critical_test",
                category=ContractCategory.SCHEMA,
                critical=True,
            ),
            status=ContractStatus.FAIL,
            message="broke",
        )
        report = ModuleContractReport(module_name=MODULE, results=(failing,))
        assert report.has_critical_failure

    def test_non_critical_failure_not_blocking(self):
        failing = ContractResult(
            contract=ContractDefinition(
                module_name=MODULE,
                contract_name="minor_test",
                category=ContractCategory.SCHEMA,
                critical=False,
            ),
            status=ContractStatus.FAIL,
            message="minor issue",
        )
        report = ModuleContractReport(module_name=MODULE, results=(failing,))
        assert not report.has_critical_failure
        assert report.failed_count == 1


@pytest.mark.build1
class TestReportGeneration:
    """6.14: report generation (verify output format is correct)."""

    def test_suite_report_pass(self):
        suite = ContractSuite(MODULE)
        suite.add_test(lambda: assert_field_present(DemoModel, "name", MODULE))
        mod_report = suite.run()

        report = build_suite_report([mod_report])
        assert report.passed
        assert report.total_contracts == 1
        assert report.total_passed == 1

    def test_suite_report_fail_on_critical(self):
        suite = ContractSuite(MODULE)
        suite.add_test(lambda: assert_field_present(DemoModel, "ghost_field", MODULE))
        mod_report = suite.run()

        report = build_suite_report([mod_report])
        assert not report.passed
        assert report.total_failed == 1

    def test_format_report_contains_verdict(self):
        suite = ContractSuite(MODULE)
        suite.add_test(lambda: assert_field_present(DemoModel, "name", MODULE))
        mod_report = suite.run()
        report = build_suite_report([mod_report])

        text = format_suite_report(report)
        assert "PASS" in text
        assert MODULE in text

    def test_format_report_shows_failure_reason(self):
        suite = ContractSuite(MODULE)
        suite.add_test(lambda: assert_field_present(DemoModel, "ghost", MODULE))
        mod_report = suite.run()
        report = build_suite_report([mod_report])

        text = format_suite_report(report)
        assert "FAIL" in text
        assert "Reason:" in text

    def test_format_report_shows_duration(self):
        suite = ContractSuite(MODULE)
        suite.add_test(lambda: assert_field_present(DemoModel, "name", MODULE))
        mod_report = suite.run()
        report = build_suite_report([mod_report])

        text = format_suite_report(report)
        assert "ms)" in text

    def test_format_report_shows_error_as_error(self):
        """ERROR status must be displayed as [ERROR], not [FAIL]."""
        error_result = ContractResult(
            contract=ContractDefinition(
                module_name=MODULE,
                contract_name="errored_test",
                category=ContractCategory.SCHEMA,
                critical=True,
            ),
            status=ContractStatus.ERROR,
            message="unexpected crash",
        )
        mod_report = ModuleContractReport(module_name=MODULE, results=(error_result,))
        report = build_suite_report([mod_report])
        text = format_suite_report(report)
        assert "[ERROR]" in text
        assert "unexpected crash" in text

    def test_format_report_shows_skip_as_skip(self):
        """SKIP status must be displayed as [SKIP], not [FAIL]."""
        skip_result = ContractResult(
            contract=ContractDefinition(
                module_name=MODULE,
                contract_name="skipped_test",
                category=ContractCategory.SCHEMA,
                critical=False,
            ),
            status=ContractStatus.SKIP,
            message="not applicable yet",
        )
        mod_report = ModuleContractReport(module_name=MODULE, results=(skip_result,))
        report = build_suite_report([mod_report])
        text = format_suite_report(report)
        assert "[SKIP]" in text
