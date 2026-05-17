"""Tests Module 2 — module_inventory: module list unique, couche, owner."""

import pytest

from interface_contracts.domain_types import ModuleLayer, ModuleStatus
from manifest_registry.module_inventory import (
    MODULES,
    ModuleEntry,
    Owner,
    Priority,
    ProfileScope,
    get_all_modules,
    get_module,
    get_module_names,
    get_modules_by_build,
    get_modules_by_layer,
    get_modules_by_status,
    validate_no_duplicates,
)


@pytest.mark.build1
class TestModuleListUnique:
    """4.9: aucun module fantome, aucun doublon."""

    def test_no_duplicate_module_names(self):
        names = [m.module_name for m in MODULES]
        assert len(names) == len(set(names)), f"Duplicate module names: {names}"

    def test_validate_no_duplicates_helper(self):
        assert validate_no_duplicates() is True

    def test_all_modules_have_names(self):
        for m in MODULES:
            assert len(m.module_name) > 0

    def test_get_module_names_returns_frozenset(self):
        names = get_module_names()
        assert isinstance(names, frozenset)
        assert len(names) == len(MODULES)

    def test_module_count_is_reasonable(self):
        assert len(MODULES) >= 15, "Expected at least 15 modules in V5.3"


@pytest.mark.build1
class TestModuleLayerObligatoire:
    """4.9: chaque module a une couche."""

    def test_all_modules_have_layer(self):
        for m in MODULES:
            assert isinstance(m.module_layer, ModuleLayer), (
                f"{m.module_name} has invalid layer"
            )

    def test_get_modules_by_layer(self):
        contracts = get_modules_by_layer(ModuleLayer.CONTRACTS)
        assert len(contracts) >= 3  # at least interface_contracts, manifest, dag
        for m in contracts:
            assert m.module_layer == ModuleLayer.CONTRACTS


@pytest.mark.build1
class TestOwnerObligatoire:
    """4.9: chaque module a un owner."""

    def test_all_modules_have_owner(self):
        for m in MODULES:
            assert isinstance(m.owner, Owner), f"{m.module_name} has invalid owner"


@pytest.mark.build1
class TestStatusObligatoire:
    """4.9: chaque module a un statut."""

    def test_all_modules_have_status(self):
        for m in MODULES:
            assert isinstance(m.status, ModuleStatus), (
                f"{m.module_name} has invalid status"
            )

    def test_active_modules_exist(self):
        active = get_modules_by_status(ModuleStatus.ACTIVE)
        assert len(active) >= 1

    def test_no_forbidden_modules_in_initial_build(self):
        forbidden = get_modules_by_status(ModuleStatus.FORBIDDEN)
        assert len(forbidden) == 0, "No modules should be forbidden initially"


@pytest.mark.build1
class TestPriorityObligatoire:
    """4.9: chaque module a une priorite."""

    def test_all_modules_have_priority(self):
        for m in MODULES:
            assert isinstance(m.priority, Priority), (
                f"{m.module_name} has invalid priority"
            )

    def test_build1_modules_are_p0(self):
        build1 = get_modules_by_build(1)
        for m in build1:
            assert m.priority == Priority.P0, (
                f"{m.module_name} in Build-1 should be P0"
            )


@pytest.mark.build1
class TestBuildStageObligatoire:
    """Chaque module a un build_stage valide."""

    def test_all_modules_have_build_stage(self):
        for m in MODULES:
            assert 0 <= m.build_stage <= 17, (
                f"{m.module_name} has invalid build_stage={m.build_stage}"
            )

    def test_get_modules_by_build(self):
        build1 = get_modules_by_build(1)
        assert len(build1) == 6
        for m in build1:
            assert m.build_stage == 1


@pytest.mark.build1
class TestLookupHelpers:
    """Test lookup functions."""

    def test_get_module_found(self):
        m = get_module("interface_contracts")
        assert m is not None
        assert m.module_name == "interface_contracts"

    def test_get_module_not_found(self):
        assert get_module("nonexistent_module") is None

    def test_get_all_modules(self):
        all_mods = get_all_modules()
        assert all_mods == MODULES

    def test_module_entry_is_frozen(self):
        m = get_module("interface_contracts")
        assert m is not None
        with pytest.raises(Exception):
            m.module_name = "hacked"  # type: ignore[misc]


@pytest.mark.build1
class TestExpectedModules:
    """Verify key modules exist in inventory."""

    @pytest.mark.parametrize("name", [
        "interface_contracts",
        "manifest_registry",
        "dag_validator",
        "contract_test_suite",
        "smoke_bootstrap_recovery",
        "calibration_loader",
        "data_backbone",
        "regime_classifier",
        "secrets_manager",
        "alerting",
        "sharia_compliance",
        "execution_backbone",
        "risk_backbone",
        "scoring_backbone",
        "engine_a",
        "engine_b",
        "portfolio",
        "meta",
        "calibration_methods",
        "local_replay_runtime",
        "backtest_artifact_import",
        "meta_learning",
        "monitoring",
        "ui",
        "venue_adapters",
        "protocols",
        "complete_enablers",
        "engine_c",
        "engine_d",
        "cockpit",
    ])
    def test_module_exists(self, name: str):
        m = get_module(name)
        assert m is not None, f"Module '{name}' missing from inventory"
