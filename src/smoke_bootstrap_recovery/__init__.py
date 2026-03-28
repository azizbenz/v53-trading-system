"""
smoke_bootstrap_recovery — Module 5: Bootstrap, config, recovery, state sanity.

Last module of Build-1. Validates that the dependency architecture
can start cleanly, restart without corruption, and fail explicitly.

Dependencies: interface_contracts, manifest_registry, contract_test_suite, dag_validator
"""

from __future__ import annotations

from typing import Any

from smoke_bootstrap_recovery.smoke_models import (
    BootstrapResult,
    ConfigCheckResult,
    ModuleSmokeReport,
    RecoveryResult,
    SmokeReport,
    SmokeStatus,
    StateSanityResult,
)
from smoke_bootstrap_recovery.bootstrap_runner import (
    bootstrap_full,
    bootstrap_module_import,
    bootstrap_with_config,
    run_bootstrap_for_modules,
)
from smoke_bootstrap_recovery.config_validator import (
    BUILD1_SCHEMAS,
    ConfigSchema,
    validate_build1_configs,
    validate_config,
)
from smoke_bootstrap_recovery.recovery_runner import run_recovery_cycle
from smoke_bootstrap_recovery.state_sanity_checker import (
    check_dag_clean,
    check_manifest_consistency,
    check_module_importable,
    run_sanity_checks,
)
from smoke_bootstrap_recovery.smoke_reporter import (
    build_smoke_report,
    format_smoke_report,
)
from smoke_bootstrap_recovery.shadow_readiness import (
    ShadowReadinessReport,
    evaluate_shadow_readiness,
)


# ─── BUILD-1 MODULES ────────────────────────────────────────────────

BUILD1_MODULES: tuple[str, ...] = (
    "interface_contracts",
    "manifest_registry",
    "dag_validator",
    "contract_test_suite",
    "smoke_bootstrap_recovery",
)


class _Build1ModuleAdapter:
    """Adapter making a stateless Build-1 module look like Bootstrappable.

    Build-1 modules are stateless (no mutable state), so bootstrap = re-import
    with full API verification, and shutdown = no-op. This satisfies the spec
    requirement that recovery is actually *executed*, not skipped.
    """

    def __init__(self, module_name: str) -> None:
        self.module_name = module_name
        self._module: Any = None

    def bootstrap(self, config: dict[str, Any]) -> None:
        import importlib
        import sys

        # Force re-import to test a real re-initialization path
        if self.module_name in sys.modules:
            self._module = importlib.reload(sys.modules[self.module_name])
        else:
            self._module = importlib.import_module(self.module_name)

        # Verify public API is accessible (import != bootstrap)
        if not hasattr(self._module, "__all__"):
            raise RuntimeError(f"{self.module_name} has no __all__")
        for name in self._module.__all__:
            if not hasattr(self._module, name):
                raise RuntimeError(f"{self.module_name}.__all__ declares missing: {name}")

    def shutdown(self) -> None:
        self._module = None


def run_build1_smoke() -> SmokeReport:
    """Run the full Build-1 smoke test suite.

    For each Build-1 module:
    1. Full bootstrap (import + API verification — NOT import-only)
    2. Config validation
    3. Recovery cycle (bootstrap → shutdown → re-bootstrap → verify)
    4. Per-module sanity checks

    Spec 7.9: no partial init considered OK.
    Spec 7.15: import OK != bootstrap OK.
    """
    from typing import Any

    # Config checks
    config_checks = validate_build1_configs()
    config_map = {c.module_name: c for c in config_checks}

    module_reports: list[ModuleSmokeReport] = []

    for mod_name in BUILD1_MODULES:
        # 1. Full bootstrap (import + __all__ verification)
        boot = bootstrap_full(mod_name)

        # 2. Recovery cycle via adapter
        adapter = _Build1ModuleAdapter(mod_name)
        recovery = run_recovery_cycle(mod_name, adapter, {})

        # 3. Per-module sanity checks
        sanity_checks: dict[str, Any] = {
            f"importable_{mod_name}": check_module_importable(mod_name),
        }
        # Add global checks to manifest_registry module
        if mod_name == "manifest_registry":
            sanity_checks["manifest_consistency"] = check_manifest_consistency()
        # Add DAG check to dag_validator module
        if mod_name == "dag_validator":
            sanity_checks["dag_clean"] = check_dag_clean()

        sanity = run_sanity_checks(mod_name, sanity_checks)

        module_reports.append(ModuleSmokeReport(
            module_name=mod_name,
            bootstrap=boot,
            config_check=config_map.get(mod_name),
            recovery=recovery,
            state_sanity=sanity,
            requires_recovery=True,
            requires_sanity=True,
        ))

    return build_smoke_report(tuple(module_reports))


__all__ = [
    # Models
    "BootstrapResult",
    "ConfigCheckResult",
    "ModuleSmokeReport",
    "RecoveryResult",
    "SmokeReport",
    "SmokeStatus",
    "StateSanityResult",
    # Bootstrap
    "bootstrap_full",
    "bootstrap_module_import",
    "bootstrap_with_config",
    "run_bootstrap_for_modules",
    # Config
    "BUILD1_SCHEMAS",
    "ConfigSchema",
    "validate_build1_configs",
    "validate_config",
    # Recovery
    "run_recovery_cycle",
    # Sanity
    "check_dag_clean",
    "check_manifest_consistency",
    "check_module_importable",
    "run_sanity_checks",
    # Reporter
    "build_smoke_report",
    "format_smoke_report",
    # Shadow readiness preflight
    "ShadowReadinessReport",
    "evaluate_shadow_readiness",
    # Main entry
    "BUILD1_MODULES",
    "run_build1_smoke",
]
