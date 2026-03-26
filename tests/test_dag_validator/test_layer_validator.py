"""Tests Module 3 — layer_validator: enforce layer hierarchy."""

import pytest

from interface_contracts.domain_types import ModuleLayer
from dag_validator.layer_validator import (
    LAYER_ORDER,
    LayerResult,
    LayerViolation,
    validate_layers,
)


@pytest.mark.build1
class TestLayerHierarchyClean:
    """No violations when dependencies respect layer order."""

    def test_lower_depends_on_lower_ok(self):
        allowed = {"data_backbone": frozenset({"interface_contracts"})}
        layers = {
            "data_backbone": ModuleLayer.DATA,
            "interface_contracts": ModuleLayer.CONTRACTS,
        }
        result = validate_layers(allowed, layers)
        assert result.is_clean

    def test_same_layer_ok(self):
        allowed = {"execution_backbone": frozenset({"risk_backbone"})}
        layers = {
            "execution_backbone": ModuleLayer.EXECUTION,
            "risk_backbone": ModuleLayer.RISK,
        }
        result = validate_layers(allowed, layers)
        assert result.is_clean  # EXECUTION and RISK are same level

    def test_real_manifest_is_clean(self):
        """The actual V5.3 manifest must have zero layer violations."""
        from manifest_registry.dependency_registry import ALLOWED_DEPENDENCIES
        from manifest_registry.module_inventory import MODULES

        module_layers = {m.module_name: m.module_layer for m in MODULES}
        result = validate_layers(ALLOWED_DEPENDENCIES, module_layers)
        assert result.is_clean, (
            f"Layer violations: {[v.message for v in result.violations]}"
        )


@pytest.mark.build1
class TestLayerHierarchyViolation:
    """Detect when dependencies point upward."""

    def test_upward_dependency_detected(self):
        allowed = {"interface_contracts": frozenset({"engine_a"})}
        layers = {
            "interface_contracts": ModuleLayer.CONTRACTS,
            "engine_a": ModuleLayer.ENGINE,
        }
        result = validate_layers(allowed, layers)
        assert not result.is_clean
        assert len(result.violations) == 1
        v = result.violations[0]
        assert v.source_module == "interface_contracts"
        assert v.target_module == "engine_a"
        assert v.source_level < v.target_level

    def test_contracts_to_protocol_violation(self):
        allowed = {"interface_contracts": frozenset({"protocols"})}
        layers = {
            "interface_contracts": ModuleLayer.CONTRACTS,
            "protocols": ModuleLayer.PROTOCOL,
        }
        result = validate_layers(allowed, layers)
        assert not result.is_clean

    def test_data_to_meta_violation(self):
        allowed = {"data_backbone": frozenset({"meta"})}
        layers = {
            "data_backbone": ModuleLayer.DATA,
            "meta": ModuleLayer.META,
        }
        result = validate_layers(allowed, layers)
        assert not result.is_clean

    def test_multiple_violations(self):
        allowed = {
            "interface_contracts": frozenset({"engine_a", "portfolio"}),
        }
        layers = {
            "interface_contracts": ModuleLayer.CONTRACTS,
            "engine_a": ModuleLayer.ENGINE,
            "portfolio": ModuleLayer.PORTFOLIO,
        }
        result = validate_layers(allowed, layers)
        assert len(result.violations) == 2


@pytest.mark.build1
class TestLayerOrder:
    """Verify the layer ordering constants are correct."""

    def test_contracts_is_lowest(self):
        assert LAYER_ORDER[ModuleLayer.CONTRACTS] == 0

    def test_protocol_is_highest(self):
        assert LAYER_ORDER[ModuleLayer.PROTOCOL] == max(LAYER_ORDER.values())

    def test_execution_equals_risk(self):
        assert LAYER_ORDER[ModuleLayer.EXECUTION] == LAYER_ORDER[ModuleLayer.RISK]

    def test_all_layers_have_order(self):
        for layer in ModuleLayer:
            assert layer in LAYER_ORDER, f"{layer} missing from LAYER_ORDER"

    def test_engine_above_scoring(self):
        assert LAYER_ORDER[ModuleLayer.ENGINE] > LAYER_ORDER[ModuleLayer.SCORING]

    def test_portfolio_above_engine(self):
        assert LAYER_ORDER[ModuleLayer.PORTFOLIO] > LAYER_ORDER[ModuleLayer.ENGINE]
