"""Tests Module 3 — dependency_matcher: import autorisé, interdit, manquant du manifest."""

import pytest

from dag_validator.dependency_matcher import MatchResult, Violation, match_dependencies
from dag_validator.import_scanner import ImportRecord, ScanResult


def _make_scan(*imports: tuple[str, str]) -> ScanResult:
    """Helper: create a ScanResult from (source, target) pairs."""
    records = tuple(
        ImportRecord(
            source_module=src,
            target_module=tgt,
            source_file=f"{src}/__init__.py",
            line_number=1,
        )
        for src, tgt in imports
    )
    return ScanResult(imports=records, files_scanned=len(imports))


@pytest.mark.build1
class TestImportAutorise:
    """5.14: import autorisé — no violation raised."""

    def test_authorized_import_passes(self):
        scan = _make_scan(("manifest_registry", "interface_contracts"))
        allowed = {"manifest_registry": frozenset({"interface_contracts"})}
        known = frozenset({"manifest_registry", "interface_contracts"})

        result = match_dependencies(scan, allowed, known)
        assert result.is_clean
        assert result.authorized_count == 1
        assert result.total_imports == 1

    def test_self_import_always_allowed(self):
        scan = _make_scan(("interface_contracts", "interface_contracts"))
        allowed = {"interface_contracts": frozenset()}
        known = frozenset({"interface_contracts"})

        result = match_dependencies(scan, allowed, known)
        assert result.is_clean
        assert result.authorized_count == 1

    def test_multiple_authorized_imports(self):
        scan = _make_scan(
            ("dag_validator", "interface_contracts"),
            ("dag_validator", "manifest_registry"),
        )
        allowed = {
            "dag_validator": frozenset({"interface_contracts", "manifest_registry"}),
        }
        known = frozenset({"dag_validator", "interface_contracts", "manifest_registry"})

        result = match_dependencies(scan, allowed, known)
        assert result.is_clean
        assert result.authorized_count == 2


@pytest.mark.build1
class TestImportInterdit:
    """5.14: import interdit — unauthorized_import violation."""

    def test_unauthorized_import_detected(self):
        scan = _make_scan(("interface_contracts", "data_backbone"))
        allowed = {"interface_contracts": frozenset()}
        known = frozenset({"interface_contracts", "data_backbone"})

        result = match_dependencies(scan, allowed, known)
        assert not result.is_clean
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == "unauthorized_import"

    def test_upward_dependency_detected(self):
        """A lower module importing a higher module."""
        scan = _make_scan(("data_backbone", "engine_a"))
        allowed = {"data_backbone": frozenset({"interface_contracts"})}
        known = frozenset({"data_backbone", "engine_a", "interface_contracts"})

        result = match_dependencies(scan, allowed, known)
        assert not result.is_clean
        assert result.violations[0].violation_type == "unauthorized_import"

    def test_violation_has_source_info(self):
        scan = _make_scan(("scoring_backbone", "meta"))
        allowed = {"scoring_backbone": frozenset({"interface_contracts"})}
        known = frozenset({"scoring_backbone", "meta", "interface_contracts"})

        result = match_dependencies(scan, allowed, known)
        v = result.violations[0]
        assert v.source_module == "scoring_backbone"
        assert v.target_module == "meta"
        assert v.source_file == "scoring_backbone/__init__.py"


@pytest.mark.build1
class TestImportManquant:
    """5.14: import d'un module manquant du manifest."""

    def test_missing_from_manifest_detected(self):
        scan = _make_scan(("data_backbone", "phantom_module"))
        allowed = {"data_backbone": frozenset({"interface_contracts"})}
        known = frozenset({"data_backbone", "interface_contracts"})

        result = match_dependencies(scan, allowed, known)
        assert not result.is_clean
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == "missing_from_manifest"
        assert "phantom_module" in result.violations[0].message

    def test_multiple_phantom_imports(self):
        scan = _make_scan(
            ("data_backbone", "ghost_a"),
            ("data_backbone", "ghost_b"),
        )
        allowed = {"data_backbone": frozenset()}
        known = frozenset({"data_backbone"})

        result = match_dependencies(scan, allowed, known)
        assert len(result.violations) == 2
        types = {v.violation_type for v in result.violations}
        assert types == {"missing_from_manifest"}


@pytest.mark.build1
class TestMixedViolations:
    """Mix of authorized, unauthorized, and phantom imports."""

    def test_mixed_scenario(self):
        scan = _make_scan(
            ("dag_validator", "interface_contracts"),  # OK
            ("dag_validator", "manifest_registry"),    # OK
            ("dag_validator", "engine_a"),             # FORBIDDEN
            ("dag_validator", "phantom"),              # PHANTOM
        )
        allowed = {
            "dag_validator": frozenset({"interface_contracts", "manifest_registry"}),
        }
        known = frozenset({
            "dag_validator", "interface_contracts", "manifest_registry", "engine_a",
        })

        result = match_dependencies(scan, allowed, known)
        assert not result.is_clean
        assert result.authorized_count == 2
        assert len(result.violations) == 2
        types = {v.violation_type for v in result.violations}
        assert "unauthorized_import" in types
        assert "missing_from_manifest" in types

    def test_empty_scan_is_clean(self):
        scan = ScanResult(imports=(), files_scanned=0)
        result = match_dependencies(scan, {}, frozenset())
        assert result.is_clean
        assert result.total_imports == 0
