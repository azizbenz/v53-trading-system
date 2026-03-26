"""
5.5.1 — Import Scanner: scan Python source files for import statements via AST.

Extracts all import targets from .py files in the src/ tree.
Handles: import X, from X import Y, TYPE_CHECKING blocks.
"""

from __future__ import annotations

import ast
from pathlib import Path

from pydantic import BaseModel, Field


class ImportRecord(BaseModel, frozen=True):
    """Single observed import."""

    source_module: str  # module that contains the import
    target_module: str  # top-level package being imported
    source_file: str    # relative file path
    line_number: int
    is_type_checking: bool = False  # inside TYPE_CHECKING block


class ScanResult(BaseModel, frozen=True):
    """Result of scanning the entire src tree."""

    imports: tuple[ImportRecord, ...]
    files_scanned: int
    errors: tuple[str, ...] = ()


def _resolve_module_name(file_path: Path, src_root: Path) -> str:
    """Convert a file path to its module package name.

    src/data_backbone/ingestion.py -> data_backbone
    src/interface_contracts/__init__.py -> interface_contracts
    """
    rel = file_path.relative_to(src_root)
    parts = rel.parts
    if len(parts) >= 1:
        return parts[0]
    return str(rel)


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
    """Detect all Python packages in src_root (dirs containing __init__.py).

    This catches packages that exist on disk but are NOT registered in the
    manifest — the exact phantom-module scenario that Build-1 must block.
    """
    packages: set[str] = set()
    if not src_root.is_dir():
        return frozenset()
    for child in src_root.iterdir():
        if child.is_dir() and (child / "__init__.py").exists():
            packages.add(child.name)
    return frozenset(packages)


def _extract_imports(
    tree: ast.Module,
    source_module: str,
    source_file: str,
    relevant_modules: frozenset[str],
) -> list[ImportRecord]:
    """Extract import records from an AST tree.

    Args:
        relevant_modules: Union of known_modules (manifest) and first-party
            packages detected on disk. An import is captured if its top-level
            package is in this set. Stdlib and third-party imports are excluded
            because they don't appear as directories under src/.
    """
    records: list[ImportRecord] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_pkg = alias.name.split(".")[0]
                if top_pkg in relevant_modules:
                    records.append(ImportRecord(
                        source_module=source_module,
                        target_module=top_pkg,
                        source_file=source_file,
                        line_number=node.lineno,
                        is_type_checking=_is_in_type_checking(node, tree),
                    ))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top_pkg = node.module.split(".")[0]
                if top_pkg in relevant_modules:
                    records.append(ImportRecord(
                        source_module=source_module,
                        target_module=top_pkg,
                        source_file=source_file,
                        line_number=node.lineno,
                        is_type_checking=_is_in_type_checking(node, tree),
                    ))

    return records


def scan_imports(src_root: Path, known_modules: frozenset[str]) -> ScanResult:
    """Scan all .py files under src_root for first-party imports.

    Captures imports of:
    - Modules registered in the manifest (known_modules)
    - Packages that exist as directories in src_root but are NOT registered
      (phantom/unregistered modules — these become missing_from_manifest violations)

    Stdlib and third-party imports are excluded: they don't exist as
    directories under src_root, so they are never in relevant_modules.

    Args:
        src_root: Path to the src/ directory.
        known_modules: Set of module names registered in manifest_registry.

    Returns:
        ScanResult with all observed first-party imports.
    """
    # Detect all first-party packages on disk (registered or not)
    first_party = _detect_first_party_packages(src_root)
    relevant_modules = known_modules | first_party

    all_imports: list[ImportRecord] = []
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
            files_scanned += 1
        except SyntaxError as e:
            errors.append(f"SyntaxError in {rel_path}: {e}")
        except OSError as e:
            errors.append(f"IOError reading {rel_path}: {e}")

    return ScanResult(
        imports=tuple(all_imports),
        files_scanned=files_scanned,
        errors=tuple(errors),
    )
