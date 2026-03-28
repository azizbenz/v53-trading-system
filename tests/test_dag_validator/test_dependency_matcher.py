"""Tests Module 3 - dependency_matcher: authorized, forbidden, and missing modules."""

import pytest

from dag_validator.dependency_matcher import match_dependencies
from dag_validator.import_scanner import ImportRecord, ScanResult


def _make_scan(
    *imports: tuple[str, str],
    unknown_modules: tuple[str, ...] = (),
) -> ScanResult:
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
    return ScanResult(
        imports=records,
        files_scanned=len(imports),
        unknown_modules=unknown_modules,
    )


@pytest.mark.build1
class TestImportAutorise:
    """Authorized imports should pass without violations."""

    def test_authorized_import_passes(self):
        scan = _make_scan(("manifest_registry", "interface_contracts"))
        allowed = {"manifest_registry": frozenset({"interface_contracts"})}
        known = frozenset({"manifest_registry", "interface_contracts"})

        result = match_dependencies(scan, allowed, known)
        assert result.is_clean
        assert result.authorized_count == 1
        assert result.total_imports == 1

    def test_self_import_allowed_for_known_module(self):
        scan = _make_scan(("interface_contracts", "interface_contracts"))
        allowed = {"interface_contracts": frozenset()}
        known = frozenset({"interface_contracts"})

        result = match_dependencies(scan, allowed, known)
        assert result.is_clean
        assert result.authorized_count == 1


@pytest.mark.build1
class TestImportInterdit:
    """Forbidden imports must raise unauthorized_import violations."""

    def test_unauthorized_import_detected(self):
        scan = _make_scan(("interface_contracts", "data_backbone"))
        allowed = {"interface_contracts": frozenset()}
        known = frozenset({"interface_contracts", "data_backbone"})

        result = match_dependencies(scan, allowed, known)
        assert not result.is_clean
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == "unauthorized_import"

    def test_upward_dependency_detected(self):
        scan = _make_scan(("data_backbone", "engine_a"))
        allowed = {"data_backbone": frozenset({"interface_contracts"})}
        known = frozenset({"data_backbone", "engine_a", "interface_contracts"})

        result = match_dependencies(scan, allowed, known)
        assert not result.is_clean
        assert result.violations[0].violation_type == "unauthorized_import"


@pytest.mark.build1
class TestImportManquant:
    """Imports or packages missing from the manifest must fail."""

    def test_missing_target_from_manifest_detected(self):
        scan = _make_scan(("data_backbone", "phantom_module"))
        allowed = {"data_backbone": frozenset({"interface_contracts"})}
        known = frozenset({"data_backbone", "interface_contracts"})

        result = match_dependencies(scan, allowed, known)
        assert not result.is_clean
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == "missing_from_manifest"
        assert "phantom_module" in result.violations[0].message

    def test_unknown_first_party_package_without_imports_detected(self):
        scan = _make_scan(unknown_modules=("ghost_module",))
        result = match_dependencies(scan, {}, frozenset())
        assert not result.is_clean
        assert len(result.violations) == 1
        assert result.violations[0].target_module == "ghost_module"
        assert result.violations[0].violation_type == "missing_from_manifest"

    def test_unknown_source_module_detected(self):
        scan = _make_scan(("ghost_module", "interface_contracts"))
        allowed = {}
        known = frozenset({"interface_contracts"})

        result = match_dependencies(scan, allowed, known)
        assert not result.is_clean
        assert len(result.violations) == 1
        assert result.violations[0].source_module == "ghost_module"
        assert result.violations[0].violation_type == "missing_from_manifest"


@pytest.mark.build1
class TestMixedViolations:
    """Mix of authorized, unauthorized, and phantom imports."""

    def test_mixed_scenario(self):
        scan = _make_scan(
            ("dag_validator", "interface_contracts"),
            ("dag_validator", "manifest_registry"),
            ("dag_validator", "engine_a"),
            ("dag_validator", "phantom"),
        )
        allowed = {
            "dag_validator": frozenset({"interface_contracts", "manifest_registry"}),
        }
        known = frozenset({
            "dag_validator",
            "interface_contracts",
            "manifest_registry",
            "engine_a",
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
