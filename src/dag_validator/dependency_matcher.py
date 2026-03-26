"""
5.5.2 — Dependency Matcher: compare observed imports vs manifest-authorized dependencies.

Takes scan results and the allowed-dependency whitelist, produces violations.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from dag_validator.import_scanner import ImportRecord, ScanResult


class Violation(BaseModel, frozen=True):
    """A single dependency violation."""

    source_module: str
    target_module: str
    source_file: str
    line_number: int
    violation_type: str  # "unauthorized_import" | "missing_from_manifest"
    message: str


class MatchResult(BaseModel, frozen=True):
    """Result of matching imports against allowed dependencies."""

    violations: tuple[Violation, ...]
    authorized_count: int
    total_imports: int

    @property
    def is_clean(self) -> bool:
        return len(self.violations) == 0


def match_dependencies(
    scan: ScanResult,
    allowed_dependencies: dict[str, frozenset[str]],
    known_modules: frozenset[str],
) -> MatchResult:
    """Compare observed imports against the manifest whitelist.

    Checks:
    1. Every internal import must be in the allowed_dependencies whitelist.
    2. Every imported module must exist in the manifest (no phantom modules).
    3. Self-imports are always allowed (module importing from itself).

    Args:
        scan: Result from import_scanner.
        allowed_dependencies: From manifest_registry.dependency_registry.
        known_modules: Set of all registered module names.

    Returns:
        MatchResult with violations and stats.
    """
    violations: list[Violation] = []
    authorized_count = 0

    for imp in scan.imports:
        # Self-import is always allowed
        if imp.source_module == imp.target_module:
            authorized_count += 1
            continue

        # Target must exist in manifest
        if imp.target_module not in known_modules:
            violations.append(Violation(
                source_module=imp.source_module,
                target_module=imp.target_module,
                source_file=imp.source_file,
                line_number=imp.line_number,
                violation_type="missing_from_manifest",
                message=(
                    f"{imp.source_module} imports '{imp.target_module}' "
                    f"which is not registered in the manifest"
                ),
            ))
            continue

        # Check against whitelist
        allowed = allowed_dependencies.get(imp.source_module, frozenset())
        if imp.target_module in allowed:
            authorized_count += 1
        else:
            violations.append(Violation(
                source_module=imp.source_module,
                target_module=imp.target_module,
                source_file=imp.source_file,
                line_number=imp.line_number,
                violation_type="unauthorized_import",
                message=(
                    f"{imp.source_module} imports '{imp.target_module}' "
                    f"which is not in its allowed dependencies"
                ),
            ))

    return MatchResult(
        violations=tuple(violations),
        authorized_count=authorized_count,
        total_imports=len(scan.imports),
    )
