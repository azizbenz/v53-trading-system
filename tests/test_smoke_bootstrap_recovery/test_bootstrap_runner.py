"""Tests Module 5 — bootstrap_runner: bootstrap OK / FAIL for modules."""

import pytest
from typing import Any

from smoke_bootstrap_recovery.bootstrap_runner import (
    Bootstrappable,
    bootstrap_full,
    bootstrap_module_import,
    bootstrap_with_config,
    run_bootstrap_for_modules,
)
from smoke_bootstrap_recovery.smoke_models import SmokeStatus


# ─── FIXTURES ────────────────────────────────────────────────────────


class GoodModule:
    """A module that bootstraps successfully."""

    def __init__(self) -> None:
        self.started = False

    def bootstrap(self, config: dict[str, Any]) -> None:
        self.started = True

    def shutdown(self) -> None:
        self.started = False


class BadModule:
    """A module that fails to bootstrap."""

    def bootstrap(self, config: dict[str, Any]) -> None:
        raise RuntimeError("Missing required resource")

    def shutdown(self) -> None:
        pass


class ConfigDependentModule:
    """A module that needs specific config keys."""

    def bootstrap(self, config: dict[str, Any]) -> None:
        if "api_key" not in config:
            raise ValueError("Config missing 'api_key'")
        self.started = True

    def shutdown(self) -> None:
        pass


# ─── IMPORT-ONLY TESTS (bootstrap_module_import) ────────────────────


@pytest.mark.build1
class TestBootstrapImportOK:
    """7.14: basic import passes for real modules."""

    def test_real_module_imports_ok(self):
        result = bootstrap_module_import("interface_contracts")
        assert result.passed
        assert result.status == SmokeStatus.PASS
        assert result.duration_ms >= 0

    def test_nonexistent_module_fails(self):
        result = bootstrap_module_import("totally_nonexistent_module_xyz")
        assert not result.passed
        assert "Import failed" in result.message
        assert "ModuleNotFoundError" in result.message


# ─── FULL BOOTSTRAP TESTS (import + __all__ verification) ───────────


@pytest.mark.build1
class TestBootstrapFull:
    """7.15: import OK != bootstrap OK. Full bootstrap verifies API."""

    def test_full_bootstrap_real_module(self):
        result = bootstrap_full("interface_contracts")
        assert result.passed
        assert "API verified" in result.message

    def test_full_bootstrap_all_build1_modules(self):
        from smoke_bootstrap_recovery import BUILD1_MODULES

        for mod in BUILD1_MODULES:
            result = bootstrap_full(mod)
            assert result.passed, f"{mod} full bootstrap failed: {result.message}"

    def test_full_bootstrap_nonexistent_fails(self):
        result = bootstrap_full("totally_fake_xyz")
        assert not result.passed

    def test_import_only_is_not_full_bootstrap(self):
        """Import-only gives a different message than full bootstrap.
        This proves they are distinct operations."""
        import_result = bootstrap_module_import("interface_contracts")
        full_result = bootstrap_full("interface_contracts")
        assert "imported successfully" in import_result.message
        assert "API verified" in full_result.message
        assert import_result.message != full_result.message


# ─── BOOTSTRAP WITH CONFIG ──────────────────────────────────────────


@pytest.mark.build1
class TestBootstrapWithConfig:
    """7.14: bootstrap OK/FAIL with config."""

    def test_good_module_passes(self):
        mod = GoodModule()
        result = bootstrap_with_config("test_good", mod, {})
        assert result.passed
        assert mod.started

    def test_bad_module_fails(self):
        mod = BadModule()
        result = bootstrap_with_config("test_bad", mod, {})
        assert not result.passed
        assert "RuntimeError" in result.message

    def test_config_dependent_with_config_passes(self):
        mod = ConfigDependentModule()
        result = bootstrap_with_config("test_cfg", mod, {"api_key": "abc"})
        assert result.passed

    def test_config_dependent_without_config_fails(self):
        mod = ConfigDependentModule()
        result = bootstrap_with_config("test_cfg", mod, {})
        assert not result.passed
        assert "api_key" in result.message


# ─── BATCH BOOTSTRAP ────────────────────────────────────────────────


@pytest.mark.build1
class TestRunBootstrapForModules:
    """Batch bootstrap uses full bootstrap (not import-only)."""

    def test_all_build1_modules_bootstrap(self):
        from smoke_bootstrap_recovery import BUILD1_MODULES

        results = run_bootstrap_for_modules(BUILD1_MODULES)
        assert len(results) == 5
        for r in results:
            assert r.passed, f"{r.module_name} failed bootstrap: {r.message}"
            # Verify it used full bootstrap, not import-only
            assert "API verified" in r.message

    def test_returns_tuple(self):
        results = run_bootstrap_for_modules(("interface_contracts",))
        assert isinstance(results, tuple)
        assert len(results) == 1
