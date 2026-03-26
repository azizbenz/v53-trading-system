"""
5.5.4 — Layer Validator: enforce that dependencies respect the layer hierarchy.

A module must never depend on a module at a HIGHER architectural layer.
Layer order (lowest to highest):
  CONTRACTS < DATA < EXECUTION = RISK < SCORING < ENGINE < PORTFOLIO < META < MONITORING < UI < PROTOCOL
"""

from __future__ import annotations

from interface_contracts.domain_types import ModuleLayer
from pydantic import BaseModel


# ─── LAYER ORDERING ──────────────────────────────────────────────────
# Lower number = lower layer. A module can only depend on same or lower.

LAYER_ORDER: dict[ModuleLayer, int] = {
    ModuleLayer.CONTRACTS: 0,
    ModuleLayer.DATA: 1,
    ModuleLayer.EXECUTION: 2,
    ModuleLayer.RISK: 2,
    ModuleLayer.SCORING: 3,
    ModuleLayer.ENGINE: 4,
    ModuleLayer.PORTFOLIO: 5,
    ModuleLayer.META: 6,
    ModuleLayer.MONITORING: 7,
    ModuleLayer.UI: 8,
    ModuleLayer.PROTOCOL: 9,
}


class LayerViolation(BaseModel, frozen=True):
    """A dependency that violates the layer hierarchy."""

    source_module: str
    source_layer: ModuleLayer
    source_level: int
    target_module: str
    target_layer: ModuleLayer
    target_level: int
    message: str


class LayerResult(BaseModel, frozen=True):
    """Result of layer hierarchy validation."""

    violations: tuple[LayerViolation, ...]

    @property
    def is_clean(self) -> bool:
        return len(self.violations) == 0


def validate_layers(
    allowed_dependencies: dict[str, frozenset[str]],
    module_layers: dict[str, ModuleLayer],
) -> LayerResult:
    """Validate that no dependency arrow points upward in the layer hierarchy.

    Args:
        allowed_dependencies: The manifest whitelist (module -> set of deps).
        module_layers: Mapping of module name -> ModuleLayer.

    Returns:
        LayerResult with any violations found.
    """
    violations: list[LayerViolation] = []

    for src, deps in sorted(allowed_dependencies.items()):
        src_layer = module_layers.get(src)
        if src_layer is None:
            continue
        src_level = LAYER_ORDER.get(src_layer, 99)

        for dep in sorted(deps):
            dep_layer = module_layers.get(dep)
            if dep_layer is None:
                continue
            dep_level = LAYER_ORDER.get(dep_layer, 99)

            if dep_level > src_level:
                violations.append(LayerViolation(
                    source_module=src,
                    source_layer=src_layer,
                    source_level=src_level,
                    target_module=dep,
                    target_layer=dep_layer,
                    target_level=dep_level,
                    message=(
                        f"{src} (layer {src_layer.value}, L{src_level}) "
                        f"depends on {dep} (layer {dep_layer.value}, L{dep_level}): "
                        f"upward dependency forbidden"
                    ),
                ))

    return LayerResult(violations=tuple(violations))
