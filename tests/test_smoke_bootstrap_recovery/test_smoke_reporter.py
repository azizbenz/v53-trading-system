"""Tests Module 5 — smoke_reporter + integration: report, verdicts, recovery required."""

import pytest

from smoke_bootstrap_recovery.smoke_models import (
    BootstrapResult,
    ConfigCheckResult,
    ModuleSmokeReport,
    RecoveryResult,
    SmokeReport,
    SmokeStatus,
    StateSanityResult,
)
from smoke_bootstrap_recovery.smoke_reporter import (
    build_smoke_report,
    format_smoke_report,
)


def _pass_bootstrap(name: str) -> BootstrapResult:
    return BootstrapResult(module_name=name, status=SmokeStatus.PASS, message="Full bootstrap OK")


def _fail_bootstrap(name: str) -> BootstrapResult:
    return BootstrapResult(module_name=name, status=SmokeStatus.FAIL, message="Import failed")


def _pass_config(name: str) -> ConfigCheckResult:
    return ConfigCheckResult(module_name=name, status=SmokeStatus.PASS)


def _fail_config(name: str) -> ConfigCheckResult:
    return ConfigCheckResult(
        module_name=name, status=SmokeStatus.FAIL,
        missing_keys=("api_key",), message="Missing api_key",
    )


def _pass_recovery(name: str) -> RecoveryResult:
    return RecoveryResult(
        module_name=name, status=SmokeStatus.PASS,
        pre_state_valid=True, post_state_valid=True,
    )


def _pass_sanity(name: str) -> StateSanityResult:
    return StateSanityResult(
        module_name=name, status=SmokeStatus.PASS, checks_passed=1,
    )


# ─── VERDICT LOGIC ──────────────────────────────────────────────────


@pytest.mark.build1
class TestBuildSmokeReport:
    """build_smoke_report aggregation."""

    def test_all_pass(self):
        reports = (
            ModuleSmokeReport(module_name="a", bootstrap=_pass_bootstrap("a"), recovery=_pass_recovery("a")),
            ModuleSmokeReport(module_name="b", bootstrap=_pass_bootstrap("b"), recovery=_pass_recovery("b")),
        )
        report = build_smoke_report(reports)
        assert report.passed
        assert report.modules_passed == 2

    def test_one_fail_causes_global_fail(self):
        reports = (
            ModuleSmokeReport(module_name="a", bootstrap=_pass_bootstrap("a")),
            ModuleSmokeReport(module_name="b", bootstrap=_fail_bootstrap("b")),
        )
        report = build_smoke_report(reports)
        assert not report.passed

    def test_empty_reports_fails(self):
        report = build_smoke_report(())
        assert not report.passed


# ─── REQUIRES_RECOVERY ENFORCEMENT ──────────────────────────────────


@pytest.mark.build1
class TestRequiresRecovery:
    """A module that requires recovery MUST NOT pass without it."""

    def test_requires_recovery_absent_is_fail(self):
        """CRITICAL: recovery=None + requires_recovery=True => FAIL."""
        mr = ModuleSmokeReport(
            module_name="test_mod",
            bootstrap=_pass_bootstrap("test_mod"),
            recovery=None,
            requires_recovery=True,
        )
        assert not mr.all_passed
        assert mr.has_failure

    def test_requires_recovery_present_and_passing(self):
        mr = ModuleSmokeReport(
            module_name="test_mod",
            bootstrap=_pass_bootstrap("test_mod"),
            recovery=_pass_recovery("test_mod"),
            requires_recovery=True,
        )
        assert mr.all_passed

    def test_requires_sanity_absent_is_fail(self):
        mr = ModuleSmokeReport(
            module_name="test_mod",
            bootstrap=_pass_bootstrap("test_mod"),
            state_sanity=None,
            requires_sanity=True,
        )
        assert not mr.all_passed
        assert mr.has_failure

    def test_not_requires_recovery_absent_is_ok(self):
        """If recovery is NOT required, absent is fine."""
        mr = ModuleSmokeReport(
            module_name="test_mod",
            bootstrap=_pass_bootstrap("test_mod"),
            requires_recovery=False,
        )
        assert mr.all_passed


# ─── FORMAT REPORT ──────────────────────────────────────────────────


@pytest.mark.build1
class TestFormatSmokeReport:
    """7.14: readable report generation."""

    def test_format_contains_verdict_pass(self):
        reports = (
            ModuleSmokeReport(module_name="a", bootstrap=_pass_bootstrap("a")),
        )
        report = build_smoke_report(reports)
        text = format_smoke_report(report)
        assert "PASS" in text
        assert "VERDICT" in text

    def test_format_contains_verdict_fail(self):
        reports = (
            ModuleSmokeReport(module_name="a", bootstrap=_fail_bootstrap("a")),
        )
        report = build_smoke_report(reports)
        text = format_smoke_report(report)
        assert "FAIL" in text

    def test_format_shows_module_names(self):
        reports = (
            ModuleSmokeReport(module_name="interface_contracts", bootstrap=_pass_bootstrap("interface_contracts")),
            ModuleSmokeReport(module_name="manifest_registry", bootstrap=_pass_bootstrap("manifest_registry")),
        )
        report = build_smoke_report(reports)
        text = format_smoke_report(report)
        assert "interface_contracts" in text
        assert "manifest_registry" in text

    def test_format_shows_config_details(self):
        reports = (
            ModuleSmokeReport(
                module_name="a",
                bootstrap=_pass_bootstrap("a"),
                config_check=_fail_config("a"),
            ),
        )
        report = build_smoke_report(reports)
        text = format_smoke_report(report)
        assert "Config" in text
        assert "api_key" in text

    def test_format_shows_recovery_details(self):
        recovery = RecoveryResult(
            module_name="a",
            status=SmokeStatus.PASS,
            pre_state_valid=True,
            post_state_valid=True,
            duration_ms=12.5,
        )
        reports = (
            ModuleSmokeReport(module_name="a", bootstrap=_pass_bootstrap("a"), recovery=recovery),
        )
        report = build_smoke_report(reports)
        text = format_smoke_report(report)
        assert "Recovery" in text
        assert "Pre-state: OK" in text

    def test_format_shows_anomalies(self):
        sanity = StateSanityResult(
            module_name="a", status=SmokeStatus.FAIL,
            checks_passed=1, checks_failed=1,
            anomalies=("check_x: something broke",),
        )
        reports = (
            ModuleSmokeReport(module_name="a", bootstrap=_pass_bootstrap("a"), state_sanity=sanity),
        )
        report = build_smoke_report(reports)
        text = format_smoke_report(report)
        assert "something broke" in text


# ─── FULL BUILD-1 INTEGRATION ───────────────────────────────────────


@pytest.mark.build1
class TestFullBuild1Smoke:
    """Integration: run_build1_smoke on the real codebase."""

    def test_build1_smoke_passes(self):
        from smoke_bootstrap_recovery import run_build1_smoke, format_smoke_report

        report = run_build1_smoke()
        if not report.passed:
            pytest.fail(f"Build-1 smoke failed:\n{format_smoke_report(report)}")

    def test_build1_smoke_returns_report_type(self):
        from smoke_bootstrap_recovery import run_build1_smoke

        report = run_build1_smoke()
        assert isinstance(report, SmokeReport)
        assert report.total_modules == 5

    def test_build1_smoke_has_recovery_for_all_modules(self):
        """CRITICAL: run_build1_smoke() must execute recovery for every module."""
        from smoke_bootstrap_recovery import run_build1_smoke

        report = run_build1_smoke()
        for mr in report.module_reports:
            assert mr.recovery is not None, (
                f"{mr.module_name} has recovery=None — recovery was not executed"
            )
            assert mr.requires_recovery is True, (
                f"{mr.module_name} must require recovery"
            )

    def test_build1_smoke_has_sanity_for_all_modules(self):
        """Every module must have per-module sanity checks."""
        from smoke_bootstrap_recovery import run_build1_smoke

        report = run_build1_smoke()
        for mr in report.module_reports:
            assert mr.state_sanity is not None, (
                f"{mr.module_name} has state_sanity=None"
            )

    def test_build1_smoke_uses_full_bootstrap_not_import_only(self):
        """CRITICAL: import OK != bootstrap OK."""
        from smoke_bootstrap_recovery import run_build1_smoke

        report = run_build1_smoke()
        for mr in report.module_reports:
            assert mr.bootstrap is not None
            assert "API verified" in mr.bootstrap.message, (
                f"{mr.module_name}: bootstrap used import-only, not full bootstrap"
            )
