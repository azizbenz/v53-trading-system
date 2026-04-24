"""
5.5.2 - Dependency Matcher: compare observed imports vs manifest-authorized dependencies.

Takes scan results and the allowed-dependency whitelist, produces violations.
"""

from __future__ import annotations

from pydantic import BaseModel

from dag_validator.import_scanner import DynamicImportRecord, ScanResult


_DECLARED_DYNAMIC_IMPORTS = frozenset({
    ("calibration_methods/ml_trainer.py", "importlib.import_module"),
    ("calibration_methods/regime_detector_trainer.py", "importlib.import_module"),
    ("complete_enablers/ml_confidence_enabler.py", "importlib.import_module"),
    ("complete_enablers/regime_detector_runtime.py", "importlib.import_module"),
    ("meta_learning/monitoring_projection.py", "importlib.import_module"),
    ("meta_learning/replay_bundle_builder.py", "importlib.import_module"),
    ("monitoring/monitoring_runtime.py", "importlib.import_module"),
    ("smoke_bootstrap_recovery/__init__.py", "importlib.import_module"),
    ("smoke_bootstrap_recovery/bootstrap_runner.py", "importlib.import_module"),
    ("smoke_bootstrap_recovery/shadow_readiness.py", "importlib.import_module"),
    ("smoke_bootstrap_recovery/state_sanity_checker.py", "__import__"),
})


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
    declared_dynamic_imports: tuple[DynamicImportRecord, ...] = ()
    undeclared_dynamic_imports: tuple[DynamicImportRecord, ...] = ()

    @property
    def is_clean(self) -> bool:
        return len(self.violations) == 0 and len(self.undeclared_dynamic_imports) == 0


def _missing_module_violation(module_name: str) -> Violation:
    """Create a deterministic violation for an unregistered first-party module."""
    return Violation(
        source_module=module_name,
        target_module=module_name,
        source_file=f"{module_name}/__init__.py",
        line_number=1,
        violation_type="missing_from_manifest",
        message=f"First-party module '{module_name}' exists on disk but is not registered in the manifest",
    )


def _is_declared_dynamic_import(record: DynamicImportRecord) -> bool:
    normalized_source = record.source_file.replace("\\", "/")
    return (normalized_source, record.call_text) in _DECLARED_DYNAMIC_IMPORTS


def match_dependencies(
    scan: ScanResult,
    allowed_dependencies: dict[str, frozenset[str]],
    known_modules: frozenset[str],
) -> MatchResult:
    """Compare observed imports against the manifest whitelist."""
    violations: list[Violation] = []
    authorized_count = 0
    reported_missing: set[str] = set()

    for module_name in scan.unknown_modules:
        violations.append(_missing_module_violation(module_name))
        reported_missing.add(module_name)

    for imp in scan.imports:
        if imp.source_module not in known_modules:
            if imp.source_module not in reported_missing:
                violations.append(_missing_module_violation(imp.source_module))
                reported_missing.add(imp.source_module)
            continue

        if imp.target_module not in known_modules:
            if imp.target_module not in reported_missing:
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
                reported_missing.add(imp.target_module)
            continue

        if imp.source_module == imp.target_module:
            authorized_count += 1
            continue

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

    declared_dynamic_imports = tuple(
        record for record in scan.dynamic_imports if _is_declared_dynamic_import(record)
    )
    undeclared_dynamic_imports = tuple(
        record for record in scan.dynamic_imports if not _is_declared_dynamic_import(record)
    )

    return MatchResult(
        violations=tuple(violations),
        authorized_count=authorized_count,
        total_imports=len(scan.imports),
        declared_dynamic_imports=declared_dynamic_imports,
        undeclared_dynamic_imports=undeclared_dynamic_imports,
    )
