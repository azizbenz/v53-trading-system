"""Tests Module 3 — report_builder + full pipeline: build fail on critical violation."""

import pytest

from dag_validator.cycle_detector import CycleResult
from dag_validator.dependency_matcher import MatchResult, Violation
from dag_validator.import_scanner import ImportRecord, ScanResult
from dag_validator.layer_validator import LayerResult, LayerViolation
from dag_validator.report_builder import (
    ReportEntry,
    Severity,
    ValidationReport,
    build_report,
    format_report,
)
from interface_contracts.domain_types import ModuleLayer


# ─── HELPERS ─────────────────────────────────────────────────────────

def _clean_match() -> MatchResult:
    return MatchResult(violations=(), authorized_count=5, total_imports=5)

def _clean_cycles() -> CycleResult:
    return CycleResult(cycles=(), has_cycles=False)

def _clean_layers() -> LayerResult:
    return LayerResult(violations=())


# ─── REPORT BUILDER ─────────────────────────────────────────────────


@pytest.mark.build1
class TestReportClean:
    """A clean codebase produces a PASS report."""

    def test_all_clean_passes(self):
        report = build_report(
            _clean_match(), _clean_cycles(), _clean_layers(),
            manifest_version="1.1.0", files_scanned=10,
        )
        assert report.passed is True
        assert report.error_count == 0
        assert report.cycle_count == 0
        assert report.violation_count == 0

    def test_clean_report_has_manifest_version(self):
        report = build_report(
            _clean_match(), _clean_cycles(), _clean_layers(),
            manifest_version="1.1.0",
        )
        assert report.manifest_version == "1.1.0"


@pytest.mark.build1
class TestReportBuildFailOnCritical:
    """5.14: build fail sur violation critique."""

    def test_cycle_causes_fail(self):
        cycles = CycleResult(cycles=(("A", "B"),), has_cycles=True)
        report = build_report(
            _clean_match(), cycles, _clean_layers(),
            manifest_version="1.1.0",
        )
        assert report.passed is False
        assert report.error_count >= 1
        assert any(e.category == "cycle" for e in report.entries)

    def test_unauthorized_import_causes_fail(self):
        match = MatchResult(
            violations=(
                Violation(
                    source_module="A", target_module="B",
                    source_file="A/__init__.py", line_number=1,
                    violation_type="unauthorized_import",
                    message="A imports B: not allowed",
                ),
            ),
            authorized_count=0,
            total_imports=1,
        )
        report = build_report(
            match, _clean_cycles(), _clean_layers(),
            manifest_version="1.1.0",
        )
        assert report.passed is False
        assert report.violation_count == 1

    def test_missing_from_manifest_causes_fail(self):
        match = MatchResult(
            violations=(
                Violation(
                    source_module="A", target_module="ghost",
                    source_file="A/__init__.py", line_number=1,
                    violation_type="missing_from_manifest",
                    message="ghost not in manifest",
                ),
            ),
            authorized_count=0,
            total_imports=1,
        )
        report = build_report(
            match, _clean_cycles(), _clean_layers(),
            manifest_version="1.1.0",
        )
        assert report.passed is False

    def test_layer_violation_causes_fail(self):
        layers = LayerResult(
            violations=(
                LayerViolation(
                    source_module="interface_contracts",
                    source_layer=ModuleLayer.CONTRACTS,
                    source_level=0,
                    target_module="engine_a",
                    target_layer=ModuleLayer.ENGINE,
                    target_level=4,
                    message="upward dep",
                ),
            ),
        )
        report = build_report(
            _clean_match(), _clean_cycles(), layers,
            manifest_version="1.1.0",
        )
        assert report.passed is False
        assert report.layer_violation_count == 1

    def test_scan_errors_are_warnings_not_fail(self):
        report = build_report(
            _clean_match(), _clean_cycles(), _clean_layers(),
            manifest_version="1.1.0",
            scan_errors=("SyntaxError in bad.py",),
        )
        assert report.passed is True  # warnings don't fail
        assert report.warning_count == 1

    def test_multiple_critical_issues_all_reported(self):
        cycles = CycleResult(cycles=(("X", "Y"),), has_cycles=True)
        match = MatchResult(
            violations=(
                Violation(
                    source_module="A", target_module="B",
                    source_file="A/__init__.py", line_number=1,
                    violation_type="unauthorized_import",
                    message="forbidden",
                ),
            ),
            authorized_count=0,
            total_imports=1,
        )
        layers = LayerResult(
            violations=(
                LayerViolation(
                    source_module="C", source_layer=ModuleLayer.CONTRACTS,
                    source_level=0, target_module="D",
                    target_layer=ModuleLayer.ENGINE, target_level=4,
                    message="upward",
                ),
            ),
        )
        report = build_report(match, cycles, layers, manifest_version="1.1.0")
        assert report.passed is False
        assert report.error_count == 3


@pytest.mark.build1
class TestFormatReport:
    """Human-readable report formatting."""

    def test_format_contains_verdict_pass(self):
        report = build_report(
            _clean_match(), _clean_cycles(), _clean_layers(),
            manifest_version="1.1.0",
        )
        text = format_report(report)
        assert "PASS" in text
        assert "FAIL" not in text

    def test_format_contains_verdict_fail(self):
        cycles = CycleResult(cycles=(("A", "B"),), has_cycles=True)
        report = build_report(
            _clean_match(), cycles, _clean_layers(),
            manifest_version="1.1.0",
        )
        text = format_report(report)
        assert "FAIL" in text

    def test_format_contains_version(self):
        report = build_report(
            _clean_match(), _clean_cycles(), _clean_layers(),
            manifest_version="1.1.0",
        )
        text = format_report(report)
        assert "1.1.0" in text

    def test_format_shows_error_entries(self):
        cycles = CycleResult(cycles=(("A", "B"),), has_cycles=True)
        report = build_report(
            _clean_match(), cycles, _clean_layers(),
            manifest_version="1.1.0",
        )
        text = format_report(report)
        assert "[ERROR]" in text
        assert "cycle" in text.lower()


@pytest.mark.build1
class TestFullPipeline:
    """Integration: validate_architecture on the real V5.3 codebase."""

    def test_v53_codebase_passes_validation(self):
        """The actual V5.3 src/ must pass DAG validation."""
        from dag_validator import validate_architecture
        from pathlib import Path

        src_root = Path(__file__).resolve().parent.parent.parent / "src"
        report = validate_architecture(src_root=src_root)

        if not report.passed:
            text = format_report(report)
            pytest.fail(f"V5.3 codebase failed DAG validation:\n{text}")

    def test_pipeline_returns_report_type(self):
        from dag_validator import validate_architecture
        from pathlib import Path

        src_root = Path(__file__).resolve().parent.parent.parent / "src"
        report = validate_architecture(src_root=src_root)
        assert isinstance(report, ValidationReport)
        assert isinstance(report.manifest_version, str)
        assert report.files_scanned > 0

    def test_phantom_module_detected_end_to_end(self, tmp_path):
        """CRITICAL: a package in src/ not in manifest must cause FAIL.

        Creates a temporary src/ with:
        - registered_mod (in known_modules) importing phantom_mod
        - phantom_mod (exists on disk, NOT in manifest)

        The full pipeline must produce FAIL with missing_from_manifest.
        """
        from dag_validator.import_scanner import scan_imports
        from dag_validator.dependency_matcher import match_dependencies
        from dag_validator.cycle_detector import detect_cycles_in_manifest
        from dag_validator.layer_validator import validate_layers
        from dag_validator.report_builder import build_report, format_report
        from interface_contracts.domain_types import ModuleLayer

        src = tmp_path / "src"

        # registered_mod: imports phantom_mod
        pkg_a = src / "registered_mod"
        pkg_a.mkdir(parents=True)
        (pkg_a / "__init__.py").write_text(
            "import phantom_mod\n", encoding="utf-8"
        )

        # phantom_mod: exists on disk but NOT in manifest
        pkg_b = src / "phantom_mod"
        pkg_b.mkdir(parents=True)
        (pkg_b / "__init__.py").write_text("", encoding="utf-8")

        # Simulate a minimal manifest
        known_modules = frozenset({"registered_mod"})
        allowed_deps = {"registered_mod": frozenset()}
        module_layers = {"registered_mod": ModuleLayer.DATA}

        # Run pipeline
        scan = scan_imports(src, known_modules)
        assert len(scan.imports) >= 1, "Scanner must capture phantom_mod import"

        phantom_imports = [
            i for i in scan.imports
            if i.target_module == "phantom_mod"
        ]
        assert len(phantom_imports) == 1, "phantom_mod import must be captured"

        match = match_dependencies(scan, allowed_deps, known_modules)
        assert not match.is_clean, "Matcher must flag phantom_mod"
        assert any(
            v.violation_type == "missing_from_manifest"
            and v.target_module == "phantom_mod"
            for v in match.violations
        ), "Violation type must be missing_from_manifest"

        cycles = detect_cycles_in_manifest(allowed_deps)
        layers = validate_layers(allowed_deps, module_layers)
        report = build_report(
            match, cycles, layers,
            manifest_version="test",
            files_scanned=scan.files_scanned,
        )

        assert report.passed is False, (
            f"Pipeline must FAIL on phantom module:\n{format_report(report)}"
        )
