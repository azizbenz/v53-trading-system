"""
7.5.1 — Bootstrap Runner: launch minimal startup sequences per module.

Tests that a module can:
- Be imported without error
- Initialize its core objects with valid config
- Fail explicitly if preconditions are not met

No heavy business logic. No external services. Pure, fast, deterministic.
"""

from __future__ import annotations

import importlib
import time
from typing import Any, Protocol

from smoke_bootstrap_recovery.smoke_models import BootstrapResult, SmokeStatus


class Bootstrappable(Protocol):
    """Protocol that stateful modules should implement for smoke testing."""

    def bootstrap(self, config: dict[str, Any]) -> None:
        """Initialize the module with the given config. Raise on failure."""
        ...

    def shutdown(self) -> None:
        """Clean shutdown. Raise on failure."""
        ...


def bootstrap_module_import(module_name: str) -> BootstrapResult:
    """Test that a module can be imported without error.

    This is the most basic bootstrap: if import fails, the module is broken.
    """
    start = time.perf_counter()
    try:
        importlib.import_module(module_name)
        elapsed = (time.perf_counter() - start) * 1000
        return BootstrapResult(
            module_name=module_name,
            status=SmokeStatus.PASS,
            message=f"Module '{module_name}' imported successfully",
            duration_ms=elapsed,
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return BootstrapResult(
            module_name=module_name,
            status=SmokeStatus.FAIL,
            message=f"Import failed: {type(exc).__name__}: {exc}",
            duration_ms=elapsed,
        )


def bootstrap_with_config(
    module_name: str,
    factory: Bootstrappable,
    config: dict[str, Any],
) -> BootstrapResult:
    """Test that a module can bootstrap with a given config.

    Calls factory.bootstrap(config) and checks for explicit errors.
    Spec 7.9: no partially initialized state considered OK.
    """
    start = time.perf_counter()
    try:
        factory.bootstrap(config)
        elapsed = (time.perf_counter() - start) * 1000
        return BootstrapResult(
            module_name=module_name,
            status=SmokeStatus.PASS,
            message="Bootstrap completed successfully",
            duration_ms=elapsed,
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return BootstrapResult(
            module_name=module_name,
            status=SmokeStatus.FAIL,
            message=f"Bootstrap failed: {type(exc).__name__}: {exc}",
            duration_ms=elapsed,
        )


def bootstrap_full(module_name: str) -> BootstrapResult:
    """Full bootstrap: import + verify public API is accessible.

    Spec 7.15: import OK != bootstrap OK. A module must expose its
    declared API (has __all__) and not raise at attribute access.
    """
    start = time.perf_counter()
    try:
        mod = importlib.import_module(module_name)
        elapsed_import = time.perf_counter()

        # Phase 2: verify __all__ exists and is non-empty for real modules
        if not hasattr(mod, "__all__"):
            elapsed = (time.perf_counter() - start) * 1000
            return BootstrapResult(
                module_name=module_name,
                status=SmokeStatus.FAIL,
                message=f"Module '{module_name}' has no __all__: public API undefined",
                duration_ms=elapsed,
            )

        # Phase 3: verify every name in __all__ is actually accessible
        missing_exports: list[str] = []
        for name in mod.__all__:
            if not hasattr(mod, name):
                missing_exports.append(name)

        if missing_exports:
            elapsed = (time.perf_counter() - start) * 1000
            return BootstrapResult(
                module_name=module_name,
                status=SmokeStatus.FAIL,
                message=f"Module '{module_name}' __all__ declares missing attrs: {missing_exports}",
                duration_ms=elapsed,
            )

        elapsed = (time.perf_counter() - start) * 1000
        return BootstrapResult(
            module_name=module_name,
            status=SmokeStatus.PASS,
            message=f"Full bootstrap OK: import + API verified ({len(mod.__all__)} exports)",
            duration_ms=elapsed,
        )

    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return BootstrapResult(
            module_name=module_name,
            status=SmokeStatus.FAIL,
            message=f"Bootstrap failed: {type(exc).__name__}: {exc}",
            duration_ms=elapsed,
        )


def run_bootstrap_for_modules(module_names: tuple[str, ...]) -> tuple[BootstrapResult, ...]:
    """Run full bootstrap (import + API verification) for a list of modules."""
    return tuple(bootstrap_full(name) for name in module_names)
