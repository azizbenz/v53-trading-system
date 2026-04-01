"""
5.5.1 - Import Scanner: scan Python source files for import statements via AST.

Extracts first-party import targets from the src/ tree and normalizes physical
package layout to canonical module names declared in the manifest.
"""

from __future__ import annotations

import ast
from pathlib import Path

from pydantic import BaseModel


_PACKAGE_ALIASES: dict[str, str] = {
    "portfolio_minimal": "portfolio",
    "meta_minimal": "meta",
}

_ENGINE_PARENT = "engines"
_ENGINE_MODULES = frozenset({"engine_a", "engine_b", "engine_c", "engine_d"})


class ImportRecord(BaseModel, frozen=True):
    """Single observed import."""

    source_module: str
    target_module: str
    source_file: str
    line_number: int
    is_type_checking: bool = False


class DynamicImportRecord(BaseModel, frozen=True):
    """GEM-03: detected dynamic import via importlib."""

    source_module: str = ""
    source_file: str
    line_number: int
    call_text: str


class ScanResult(BaseModel, frozen=True):
    """Result of scanning the entire src tree."""

    imports: tuple[ImportRecord, ...]
    files_scanned: int
    errors: tuple[str, ...] = ()
    discovered_modules: tuple[str, ...] = ()
    unknown_modules: tuple[str, ...] = ()
    dynamic_imports: tuple[DynamicImportRecord, ...] = ()


def _canonicalize_package_parts(parts: tuple[str, ...]) -> str:
    """Map a filesystem or import path to a canonical manifest module name."""
    if not parts:
        return ""

    top = parts[0]
    if top == _ENGINE_PARENT and len(parts) >= 2 and parts[1] in _ENGINE_MODULES:
        return parts[1]

    return _PACKAGE_ALIASES.get(top, top)


def _resolve_module_name(file_path: Path, src_root: Path) -> str:
    """Convert a file path to its canonical module name."""
    rel = file_path.relative_to(src_root)
    return _canonicalize_package_parts(rel.parts)


def _resolve_import_target(import_name: str) -> str:
    """Map an import string to its canonical manifest module name."""
    return _canonicalize_package_parts(tuple(import_name.split(".")))


def _is_in_type_checking(node: ast.AST, tree: ast.Module) -> bool:
    """Check if an import node is inside an `if TYPE_CHECKING:` block."""
    for top_node in ast.walk(tree):
        if isinstance(top_node, ast.If):
            test = top_node.test
            if (
                isinstance(test, ast.Name) and test.id == "TYPE_CHECKING"
                or isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
            ):
                for child in ast.walk(top_node):
                    if child is node:
                        return True
    return False


def _detect_first_party_packages(src_root: Path) -> frozenset[str]:
    """Detect canonical first-party module names present on disk."""
    packages: set[str] = set()
    if not src_root.is_dir():
        return frozenset()

    for child in src_root.iterdir():
        if not child.is_dir() or not (child / "__init__.py").exists():
            continue

        if child.name == _ENGINE_PARENT:
            for engine_dir in child.iterdir():
                if engine_dir.is_dir() and (engine_dir / "__init__.py").exists():
                    packages.add(_canonicalize_package_parts((child.name, engine_dir.name)))
            continue

        packages.add(_canonicalize_package_parts((child.name,)))

    return frozenset(packages)


def _extract_imports(
    tree: ast.Module,
    source_module: str,
    source_file: str,
    relevant_modules: frozenset[str],
) -> list[ImportRecord]:
    """Extract canonicalized first-party import records from an AST tree."""
    records: list[ImportRecord] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target_module = _resolve_import_target(alias.name)
                if target_module in relevant_modules:
                    records.append(ImportRecord(
                        source_module=source_module,
                        target_module=target_module,
                        source_file=source_file,
                        line_number=node.lineno,
                        is_type_checking=_is_in_type_checking(node, tree),
                    ))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                target_module = _resolve_import_target(node.module)
                if target_module in relevant_modules:
                    records.append(ImportRecord(
                        source_module=source_module,
                        target_module=target_module,
                        source_file=source_file,
                        line_number=node.lineno,
                        is_type_checking=_is_in_type_checking(node, tree),
                    ))

    return records


def _detect_dynamic_imports(
    tree: ast.Module,
    source_file: str,
    source_module: str = "",
) -> list[DynamicImportRecord]:
    """GEM-03: detect importlib.import_module() and __import__() calls via AST."""
    records: list[DynamicImportRecord] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # importlib.import_module(...)
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "import_module"
            and isinstance(func.value, ast.Name)
            and func.value.id == "importlib"
        ):
            records.append(DynamicImportRecord(
                source_module=source_module,
                source_file=source_file,
                line_number=node.lineno,
                call_text="importlib.import_module",
            ))
        # __import__(...)
        elif isinstance(func, ast.Name) and func.id == "__import__":
            records.append(DynamicImportRecord(
                source_module=source_module,
                source_file=source_file,
                line_number=node.lineno,
                call_text="__import__",
            ))
    return records


def scan_imports(src_root: Path, known_modules: frozenset[str]) -> ScanResult:
    """Scan all .py files under src_root for canonicalized first-party imports."""
    first_party = _detect_first_party_packages(src_root)
    relevant_modules = known_modules | first_party

    all_imports: list[ImportRecord] = []
    all_dynamic: list[DynamicImportRecord] = []
    errors: list[str] = []
    files_scanned = 0

    py_files = sorted(src_root.rglob("*.py"))

    for py_file in py_files:
        source_module = _resolve_module_name(py_file, src_root)
        rel_path = str(py_file.relative_to(src_root))

        try:
            source_code = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source_code, filename=str(py_file))
            imports = _extract_imports(tree, source_module, rel_path, relevant_modules)
            all_imports.extend(imports)
            # GEM-03: detect dynamic imports (importlib / __import__)
            dynamic = _detect_dynamic_imports(tree, rel_path, source_module=source_module)
            all_dynamic.extend(dynamic)
            files_scanned += 1
        except SyntaxError as e:
            errors.append(f"SyntaxError in {rel_path}: {e}")
        except OSError as e:
            errors.append(f"IOError reading {rel_path}: {e}")

    unknown_modules = tuple(sorted(first_party - known_modules))

    return ScanResult(
        imports=tuple(all_imports),
        files_scanned=files_scanned,
        errors=tuple(errors),
        discovered_modules=tuple(sorted(first_party)),
        unknown_modules=unknown_modules,
        dynamic_imports=tuple(all_dynamic),
    )
