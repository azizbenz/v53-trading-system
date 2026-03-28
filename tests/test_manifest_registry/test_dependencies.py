"""Tests Module 2 — dependency_registry: dependances bien formees."""

import pytest

from manifest_registry.dependency_registry import (
    ALLOWED_DEPENDENCIES,
    get_allowed_dependencies,
    get_dependents,
    is_dependency_allowed,
    validate_all_modules_registered,
    validate_no_self_dependency,
    validate_no_unknown_targets,
)
from manifest_registry.module_inventory import get_module_names


@pytest.mark.build1
class TestDependenciesBienFormees:
    """4.14: dependances bien formees."""

    def test_every_module_has_dependency_entry(self):
        missing = validate_all_modules_registered()
        assert missing == [], f"Modules without dependency entries: {missing}"

    def test_no_unknown_dependency_targets(self):
        violations = validate_no_unknown_targets()
        assert violations == [], f"Unknown dependency targets: {violations}"

    def test_no_self_dependencies(self):
        self_deps = validate_no_self_dependency()
        assert self_deps == [], f"Self-dependent modules: {self_deps}"

    def test_interface_contracts_has_zero_deps(self):
        deps = get_allowed_dependencies("interface_contracts")
        assert deps == frozenset(), "interface_contracts must have ZERO dependencies"

    def test_manifest_registry_depends_only_on_contracts(self):
        deps = get_allowed_dependencies("manifest_registry")
        assert deps == frozenset({"interface_contracts"})

    def test_dag_validator_depends_on_contracts_and_manifest(self):
        deps = get_allowed_dependencies("dag_validator")
        assert "interface_contracts" in deps
        assert "manifest_registry" in deps


@pytest.mark.build1
class TestNoCycles:
    """Verify no circular dependency exists in the DAG."""

    def test_no_direct_cycles(self):
        """No module A -> B -> A."""
        for src, deps in ALLOWED_DEPENDENCIES.items():
            for dep in deps:
                reverse_deps = ALLOWED_DEPENDENCIES.get(dep, frozenset())
                assert src not in reverse_deps, (
                    f"Direct cycle: {src} <-> {dep}"
                )

    def test_topological_sort_possible(self):
        """If no cycles exist, topological sort must succeed."""
        remaining = dict(ALLOWED_DEPENDENCIES)
        resolved: set[str] = set()
        progress = True
        while remaining and progress:
            progress = False
            for mod, deps in list(remaining.items()):
                if deps.issubset(resolved):
                    resolved.add(mod)
                    del remaining[mod]
                    progress = True
        assert remaining == {}, f"Cycle detected involving: {list(remaining.keys())}"


@pytest.mark.build1
class TestDependencyQueries:
    """Test query helpers."""

    def test_is_dependency_allowed_true(self):
        assert is_dependency_allowed("manifest_registry", "interface_contracts")

    def test_is_dependency_allowed_false(self):
        assert not is_dependency_allowed("interface_contracts", "manifest_registry")

    def test_get_dependents(self):
        dependents = get_dependents("interface_contracts")
        assert "manifest_registry" in dependents
        assert "dag_validator" in dependents
        assert len(dependents) > 5  # many modules depend on contracts

    def test_unknown_module_raises(self):
        with pytest.raises(KeyError):
            get_allowed_dependencies("totally_fake_module")


@pytest.mark.build1
class TestDAGLayerHierarchy:
    """Verify that dependencies respect layer ordering (no upward arrows)."""

    LAYER_ORDER = {
        "interface_contracts": 0,
        "manifest_registry": 0,
        "dag_validator": 0,
        "contract_test_suite": 0,
        "smoke_bootstrap_recovery": 0,
        "data_backbone": 1,
        "execution_backbone": 2,
        "risk_backbone": 2,
        "scoring_backbone": 3,
        "engine_a": 4,
        "engine_b": 4,
        "engine_c": 4,
        "engine_d": 4,
        "complete_enablers": 3,
        "portfolio": 5,
        "meta": 6,
        "local_replay_runtime": 7,
        "monitoring": 7,
        "backtest_artifact_import": 8,
        "meta_learning": 8,
        "ui": 9,
        "protocols": 10,
    }

    def test_no_upward_dependency(self):
        """A module must not depend on a module at a higher layer."""
        for src, deps in ALLOWED_DEPENDENCIES.items():
            src_level = self.LAYER_ORDER.get(src, 99)
            for dep in deps:
                dep_level = self.LAYER_ORDER.get(dep, 99)
                assert dep_level <= src_level, (
                    f"Upward dep: {src}(L{src_level}) -> {dep}(L{dep_level})"
                )
