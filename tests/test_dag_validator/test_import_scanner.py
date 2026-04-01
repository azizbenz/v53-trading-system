"""Tests Module 3 - import_scanner: AST-based import extraction."""

from pathlib import Path

import pytest

from dag_validator.import_scanner import (
    _resolve_module_name,
    scan_imports,
)


@pytest.mark.build1
class TestResolveModuleName:
    """Module name extraction from file path."""

    def test_simple_package(self, isolated_tmp_path: Path):
        src = isolated_tmp_path / "src"
        f = src / "data_backbone" / "ingestion.py"
        f.parent.mkdir(parents=True)
        assert _resolve_module_name(f, src) == "data_backbone"

    def test_nested_engine_package_maps_to_engine_name(self, isolated_tmp_path: Path):
        src = isolated_tmp_path / "src"
        f = src / "engines" / "engine_a" / "engine_a_runner.py"
        f.parent.mkdir(parents=True)
        assert _resolve_module_name(f, src) == "engine_a"

    def test_alias_package_maps_to_canonical_name(self, isolated_tmp_path: Path):
        src = isolated_tmp_path / "src"
        f = src / "portfolio_minimal" / "portfolio_orchestrator.py"
        f.parent.mkdir(parents=True)
        assert _resolve_module_name(f, src) == "portfolio"


@pytest.mark.build1
class TestScanImports:
    """Full import scanning from file system."""

    def _write_module(self, src: Path, module: str, code: str) -> None:
        pkg = src / module
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "__init__.py").write_text(code, encoding="utf-8")

    def test_scan_simple_import(self, isolated_tmp_path: Path):
        src = isolated_tmp_path / "src"
        self._write_module(src, "mod_a", "import mod_b\n")
        self._write_module(src, "mod_b", "")

        known = frozenset({"mod_a", "mod_b"})
        result = scan_imports(src, known)

        assert result.files_scanned == 2
        assert len(result.imports) == 1
        assert result.imports[0].source_module == "mod_a"
        assert result.imports[0].target_module == "mod_b"

    def test_detects_unregistered_first_party_package_even_without_imports(
        self,
        isolated_tmp_path: Path,
    ):
        src = isolated_tmp_path / "src"
        self._write_module(src, "ghost_module", "")

        result = scan_imports(src, frozenset())
        assert "ghost_module" in result.discovered_modules
        assert result.unknown_modules == ("ghost_module",)

    def test_detects_unregistered_first_party_package_import(self, isolated_tmp_path: Path):
        src = isolated_tmp_path / "src"
        self._write_module(src, "mod_a", "import phantom_module\n")
        self._write_module(src, "phantom_module", "")

        known = frozenset({"mod_a"})
        result = scan_imports(src, known)
        assert len(result.imports) == 1
        assert result.imports[0].source_module == "mod_a"
        assert result.imports[0].target_module == "phantom_module"
        assert result.unknown_modules == ("phantom_module",)

    def test_nested_engine_import_maps_to_canonical_engine_module(self, isolated_tmp_path: Path):
        src = isolated_tmp_path / "src"
        engine_a = src / "engines" / "engine_a"
        engine_a.mkdir(parents=True, exist_ok=True)
        (src / "engines" / "__init__.py").write_text("", encoding="utf-8")
        (engine_a / "__init__.py").write_text("", encoding="utf-8")
        (engine_a / "engine_a_runner.py").write_text(
            "from engines.engine_a.signal_reporter_a import SignalDecision\n",
            encoding="utf-8",
        )
        (engine_a / "signal_reporter_a.py").write_text("", encoding="utf-8")

        known = frozenset({"engine_a"})
        result = scan_imports(src, known)
        assert len(result.imports) == 1
        assert result.imports[0].source_module == "engine_a"
        assert result.imports[0].target_module == "engine_a"
        assert result.unknown_modules == ()

    def test_alias_package_maps_to_canonical_manifest_module(self, isolated_tmp_path: Path):
        src = isolated_tmp_path / "src"
        pkg = src / "portfolio_minimal"
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "portfolio_orchestrator.py").write_text(
            "from portfolio_minimal.allocation_router.base_size_builder import SizeProfile\n",
            encoding="utf-8",
        )
        sub = pkg / "allocation_router"
        sub.mkdir(parents=True, exist_ok=True)
        (sub / "__init__.py").write_text("", encoding="utf-8")
        (sub / "base_size_builder.py").write_text("", encoding="utf-8")

        known = frozenset({"portfolio"})
        result = scan_imports(src, known)
        assert len(result.imports) == 1
        assert result.imports[0].source_module == "portfolio"
        assert result.imports[0].target_module == "portfolio"
        assert result.unknown_modules == ()

    def test_ignores_stdlib_imports(self, isolated_tmp_path: Path):
        src = isolated_tmp_path / "src"
        self._write_module(src, "mod_a", "import os\nimport json\n")

        known = frozenset({"mod_a"})
        result = scan_imports(src, known)
        assert len(result.imports) == 0

    def test_type_checking_import_flagged(self, isolated_tmp_path: Path):
        src = isolated_tmp_path / "src"
        code = (
            "from __future__ import annotations\n"
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    import mod_b\n"
        )
        self._write_module(src, "mod_a", code)
        self._write_module(src, "mod_b", "")

        known = frozenset({"mod_a", "mod_b"})
        result = scan_imports(src, known)
        assert len(result.imports) == 1
        assert result.imports[0].is_type_checking is True

    def test_scan_handles_syntax_error(self, isolated_tmp_path: Path):
        src = isolated_tmp_path / "src"
        pkg = src / "bad_mod"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("def broken(:\n", encoding="utf-8")

        known = frozenset({"bad_mod"})
        result = scan_imports(src, known)
        assert len(result.errors) == 1
        assert "SyntaxError" in result.errors[0]

    def test_scan_empty_directory(self, isolated_tmp_path: Path):
        src = isolated_tmp_path / "src"
        src.mkdir()

        result = scan_imports(src, frozenset())
        assert result.files_scanned == 0
        assert len(result.imports) == 0
        assert result.discovered_modules == ()
        assert result.unknown_modules == ()

    def test_scan_records_dynamic_imports(self, isolated_tmp_path: Path):
        src = isolated_tmp_path / "src"
        pkg = src / "mod_a"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text(
            "import importlib\n"
            "importlib.import_module('x')\n"
            "__import__('y')\n",
            encoding="utf-8",
        )

        result = scan_imports(src, frozenset({"mod_a"}))

        assert len(result.dynamic_imports) == 2
        assert result.dynamic_imports[0].source_module == "mod_a"
        assert {record.call_text for record in result.dynamic_imports} == {
            "importlib.import_module",
            "__import__",
        }
