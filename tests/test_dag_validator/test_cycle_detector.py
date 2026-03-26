"""Tests Module 3 — cycle_detector: cycle simple, cycle indirect, pas de cycle."""

import pytest

from dag_validator.cycle_detector import (
    CycleResult,
    _find_cycles_dfs,
    detect_cycles_in_manifest,
    detect_cycles_in_observed,
)
from dag_validator.import_scanner import ImportRecord, ScanResult


@pytest.mark.build1
class TestCycleSimple:
    """5.14: cycle simple A -> B -> A."""

    def test_direct_cycle_detected(self):
        graph = {"A": {"B"}, "B": {"A"}}
        cycles = _find_cycles_dfs(graph)
        assert len(cycles) >= 1
        # The cycle must contain both A and B
        flat = {node for c in cycles for node in c}
        assert "A" in flat
        assert "B" in flat

    def test_self_cycle_detected(self):
        graph = {"A": {"A"}}
        cycles = _find_cycles_dfs(graph)
        assert len(cycles) >= 1

    def test_no_cycle_clean_dag(self):
        graph = {"A": {"B"}, "B": {"C"}, "C": set()}
        cycles = _find_cycles_dfs(graph)
        assert len(cycles) == 0


@pytest.mark.build1
class TestCycleIndirect:
    """5.14: cycle indirect A -> B -> C -> A."""

    def test_indirect_cycle_3_nodes(self):
        graph = {"A": {"B"}, "B": {"C"}, "C": {"A"}}
        cycles = _find_cycles_dfs(graph)
        assert len(cycles) >= 1
        flat = {node for c in cycles for node in c}
        assert flat == {"A", "B", "C"}

    def test_indirect_cycle_4_nodes(self):
        graph = {"A": {"B"}, "B": {"C"}, "C": {"D"}, "D": {"A"}}
        cycles = _find_cycles_dfs(graph)
        assert len(cycles) >= 1

    def test_multiple_independent_cycles(self):
        graph = {
            "A": {"B"}, "B": {"A"},
            "C": {"D"}, "D": {"C"},
            "E": set(),
        }
        cycles = _find_cycles_dfs(graph)
        assert len(cycles) >= 2


@pytest.mark.build1
class TestCycleInManifest:
    """Detect cycles in the manifest whitelist graph."""

    def test_manifest_has_no_cycles(self):
        """The real V5.3 manifest must be cycle-free."""
        from manifest_registry.dependency_registry import ALLOWED_DEPENDENCIES

        result = detect_cycles_in_manifest(ALLOWED_DEPENDENCIES)
        assert not result.has_cycles, f"Cycles found: {result.cycles}"
        assert result.cycle_count == 0

    def test_synthetic_manifest_with_cycle(self):
        fake_deps = {
            "mod_a": frozenset({"mod_b"}),
            "mod_b": frozenset({"mod_c"}),
            "mod_c": frozenset({"mod_a"}),
        }
        result = detect_cycles_in_manifest(fake_deps)
        assert result.has_cycles
        assert result.cycle_count >= 1


@pytest.mark.build1
class TestCycleInObserved:
    """Detect cycles in observed import graph."""

    def test_no_cycle_in_clean_scan(self):
        scan = ScanResult(
            imports=(
                ImportRecord(
                    source_module="A", target_module="B",
                    source_file="A/__init__.py", line_number=1,
                ),
            ),
            files_scanned=1,
        )
        result = detect_cycles_in_observed(scan)
        assert not result.has_cycles

    def test_cycle_in_observed_scan(self):
        scan = ScanResult(
            imports=(
                ImportRecord(
                    source_module="A", target_module="B",
                    source_file="A/__init__.py", line_number=1,
                ),
                ImportRecord(
                    source_module="B", target_module="A",
                    source_file="B/__init__.py", line_number=1,
                ),
            ),
            files_scanned=2,
        )
        result = detect_cycles_in_observed(scan)
        assert result.has_cycles
        assert result.cycle_count >= 1

    def test_self_import_ignored(self):
        """Self-imports (A imports A) should not create cycles."""
        scan = ScanResult(
            imports=(
                ImportRecord(
                    source_module="A", target_module="A",
                    source_file="A/sub.py", line_number=1,
                ),
            ),
            files_scanned=1,
        )
        result = detect_cycles_in_observed(scan)
        assert not result.has_cycles
