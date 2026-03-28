"""
4.5.2 — Dependency Registry: whitelist of allowed dependencies per module.

Every import between V5.3 modules MUST be declared here.
An import not in this registry is a violation detected by dag_validator.
"""

from __future__ import annotations

from manifest_registry.module_inventory import get_module_names


# ─── ALLOWED DEPENDENCIES (DAG) ──────────────────────────────────────
# Key = module name, Value = frozenset of modules it is allowed to import.
# interface_contracts is the root: no internal dependencies.
# No arrow ever points upward in the DAG.

ALLOWED_DEPENDENCIES: dict[str, frozenset[str]] = {
    # Build-1: Dependency Architecture
    "interface_contracts": frozenset(),
    "manifest_registry": frozenset({"interface_contracts"}),
    "dag_validator": frozenset({"interface_contracts", "manifest_registry"}),
    "contract_test_suite": frozenset({"interface_contracts", "manifest_registry"}),
    "smoke_bootstrap_recovery": frozenset({
        "interface_contracts",
        "manifest_registry",
        "dag_validator",
        "contract_test_suite",
    }),
    # Build-2: Data Backbone
    "data_backbone": frozenset({"interface_contracts", "manifest_registry"}),
    # Build-3: Execution Backbone
    "execution_backbone": frozenset({"interface_contracts", "data_backbone"}),
    # Build-4: Risk Backbone
    "risk_backbone": frozenset({"interface_contracts", "data_backbone"}),
    # Build-5: Scoring Backbone
    "scoring_backbone": frozenset({"interface_contracts", "risk_backbone"}),
    # Build-6: Engine A
    "engine_a": frozenset({
        "interface_contracts",
        "scoring_backbone",
        "data_backbone",
        "risk_backbone",
    }),
    # Build-7: Engine B
    "engine_b": frozenset({
        "interface_contracts",
        "scoring_backbone",
        "data_backbone",
        "risk_backbone",
    }),
    # Build-8: Portfolio
    "portfolio": frozenset({
        "interface_contracts",
        "scoring_backbone",
        "risk_backbone",
        "engine_a",
        "engine_b",
    }),
    # Build-9: Meta
    "meta": frozenset({
        "interface_contracts",
        "portfolio",
        "engine_a",
        "engine_b",
    }),
    # Stage-10 scaffolding: LOCAL_REPLAY / artifact import / Build-9X
    "local_replay_runtime": frozenset({
        "interface_contracts",
        "manifest_registry",
    }),
    "backtest_artifact_import": frozenset({
        "interface_contracts",
        "local_replay_runtime",
    }),
    "meta_learning": frozenset({
        "interface_contracts",
        "meta",
    }),
    # Build-10: Monitoring + UI
    "monitoring": frozenset({
        "interface_contracts",
        "data_backbone",
        "execution_backbone",
        "risk_backbone",
        "scoring_backbone",
        "portfolio",
        "meta",
    }),
    "ui": frozenset({
        "interface_contracts",
        "monitoring",
        "meta_learning",
    }),
    # Build-11/12/13: Protocols
    "protocols": frozenset({
        "interface_contracts",
        "data_backbone",
        "execution_backbone",
        "risk_backbone",
        "scoring_backbone",
        "portfolio",
        "meta",
        "monitoring",
        "ui",
    }),
    # Build-14: Complete Enablers
    "complete_enablers": frozenset({
        "interface_contracts",
        "data_backbone",
        "risk_backbone",
        "scoring_backbone",
    }),
    # Build-15: Engine C
    "engine_c": frozenset({
        "interface_contracts",
        "scoring_backbone",
        "data_backbone",
        "risk_backbone",
        "complete_enablers",
    }),
    # Build-16: Engine D
    "engine_d": frozenset({
        "interface_contracts",
        "scoring_backbone",
        "data_backbone",
        "risk_backbone",
        "complete_enablers",
    }),
}


# ─── VALIDATION HELPERS ──────────────────────────────────────────────


def get_allowed_dependencies(module_name: str) -> frozenset[str]:
    """Return the set of modules that `module_name` is allowed to import."""
    if module_name not in ALLOWED_DEPENDENCIES:
        raise KeyError(f"Module '{module_name}' not found in dependency registry")
    return ALLOWED_DEPENDENCIES[module_name]


def is_dependency_allowed(source: str, target: str) -> bool:
    """Check if `source` is allowed to import `target`."""
    allowed = ALLOWED_DEPENDENCIES.get(source)
    if allowed is None:
        return False
    return target in allowed


def get_dependents(module_name: str) -> frozenset[str]:
    """Return all modules that depend on `module_name`."""
    return frozenset(
        src for src, deps in ALLOWED_DEPENDENCIES.items() if module_name in deps
    )


def validate_all_modules_registered() -> list[str]:
    """Check that every module in inventory has a dependency entry. Returns missing names."""
    known = get_module_names()
    registered = frozenset(ALLOWED_DEPENDENCIES.keys())
    return sorted(known - registered)


def validate_no_unknown_targets() -> list[tuple[str, str]]:
    """Check that every dependency target is a known module. Returns (source, unknown_target) pairs."""
    known = get_module_names()
    violations: list[tuple[str, str]] = []
    for src, deps in ALLOWED_DEPENDENCIES.items():
        for dep in deps:
            if dep not in known:
                violations.append((src, dep))
    return violations


def validate_no_self_dependency() -> list[str]:
    """Check that no module depends on itself."""
    return [src for src, deps in ALLOWED_DEPENDENCIES.items() if src in deps]
