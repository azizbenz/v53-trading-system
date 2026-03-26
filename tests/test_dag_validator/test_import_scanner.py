"""Tests Module 3 — import_scanner: AST-based import extraction."""

import pytest
import tempfile
from pathlib import Path

from dag_validator.import_scanner import (
    ImportRecord,
    ScanResult,
    scan_imports,
    _resolve_module_name,
    _extract_imports,
)


@pytest.mark.build1
class TestResolveModuleName:
    """Module name extraction from file path."""

    def test_simple_package(self, tmp_path: Path):
        src = tmp_path / "src"
        f = src / "data_backbone" / "ingestion.py"
        f.parent.mkdir(parents=True)
        assert _resolve_module_name(f, src) == "data_backbone"

    def test_init_file(self, tmp_path: Path):
        src = tmp_path / "src"
        f = src / "interface_contracts" / "__init__.py"
        f.parent.mkdir(parents=True)
        assert _resolve_module_name(f, src) == "interface_contracts"


@pytest.mark.build1
class TestScanImports:
    """Full import scanning from file system."""

    def _write_module(self, src: Path, module: str, code: str) -> None:
        pkg = src / module
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "__init__.py").write_text(code, encoding="utf-8")

    def test_scan_simple_import(self, tmp_path: Path):
        src = tmp_path / "src"
        self._write_module(src, "mod_a", "import mod_b\n")
        self._write_module(src, "mod_b", "")

        known = frozenset({"mod_a", "mod_b"})
        result = scan_imports(src, known)

        assert result.files_scanned == 2
        assert len(result.imports) == 1
        assert result.imports[0].source_module == "mod_a"
        assert result.imports[0].target_module == "mod_b"

    def test_scan_from_import(self, tmp_path: Path):
        src = tmp_path / "src"
        self._write_module(src, "mod_a", "from mod_b import something\n")
        self._write_module(src, "mod_b", "")

        known = frozenset({"mod_a", "mod_b"})
        result = scan_imports(src, known)
        assert len(result.imports) == 1
        assert result.imports[0].target_module == "mod_b"

    def test_ignores_stdlib_imports(self, tmp_path: Path):
        src = tmp_path / "src"
        self._write_module(src, "mod_a", "import os\nimport json\n")

        known = frozenset({"mod_a"})
        result = scan_imports(src, known)
        assert len(result.imports) == 0  # os/json not in known

    def test_ignores_nonexistent_external_modules(self, tmp_path: Path):
        """Import of a package that doesn't exist on disk → ignored (not first-party)."""
        src = tmp_path / "src"
        self._write_module(src, "mod_a", "import unknown_pkg\n")

        known = frozenset({"mod_a"})
        result = scan_imports(src, known)
        assert len(result.imports) == 0

    def test_detects_unregistered_first_party_package(self, tmp_path: Path):
        """A package exists in src/ but is NOT in known_modules → captured.

        This is the phantom-module scenario: the scanner must not silently
        drop it, so dependency_matcher can flag it as missing_from_manifest.
        """
        src = tmp_path / "src"
        self._write_module(src, "mod_a", "import phantom_module\n")
        self._write_module(src, "phantom_module", "")  # exists on disk

        known = frozenset({"mod_a"})  # phantom_module NOT registered
        result = scan_imports(src, known)
        assert len(result.imports) == 1
        assert result.imports[0].source_module == "mod_a"
        assert result.imports[0].target_module == "phantom_module"

    def test_type_checking_import_flagged(self, tmp_path: Path):
        src = tmp_path / "src"
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

    def test_scan_handles_syntax_error(self, tmp_path: Path):
        src = tmp_path / "src"
        pkg = src / "bad_mod"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("def broken(:\n", encoding="utf-8")

        known = frozenset({"bad_mod"})
        result = scan_imports(src, known)
        assert len(result.errors) == 1
        assert "SyntaxError" in result.errors[0]

    def test_scan_empty_directory(self, tmp_path: Path):
        src = tmp_path / "src"
        src.mkdir()

        result = scan_imports(src, frozenset())
        assert result.files_scanned == 0
        assert len(result.imports) == 0

    def test_dotted_import_extracts_top_package(self, tmp_path: Path):
        src = tmp_path / "src"
        self._write_module(src, "mod_a", "from mod_b.sub.deep import X\n")
        self._write_module(src, "mod_b", "")

        known = frozenset({"mod_a", "mod_b"})
        result = scan_imports(src, known)
        assert len(result.imports) == 1
        assert result.imports[0].target_module == "mod_b"
