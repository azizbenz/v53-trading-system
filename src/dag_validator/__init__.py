"""
dag_validator — Module 3: Empêcher les dépendances interdites et les cycles.

Public API: validate_architecture() is the single entry point.
It scans imports, matches against manifest, detects cycles, validates layers,
and produces a unified report.

Dependencies: interface_contracts, manifest_registry, stdlib (ast, pathlib)
"""

from __future__ import annotations

from pathlib import Path

from dag_validator.cycle_detector import (
    CycleResult,
    detect_cycles_in_manifest,
    detect_cycles_in_observed,
)
from dag_validator.dependency_matcher import (
    MatchResult,
    Violation,
    match_dependencies,
)
from dag_validator.import_scanner import (
    ImportRecord,
    ScanResult,
    scan_imports,
)
from dag_validator.layer_validator import (
    LAYER_ORDER,
    LayerResult,
    LayerViolation,
    validate_layers,
)
from dag_validator.report_builder import (
    ReportEntry,
    Severity,
    ValidationReport,
    build_report,
    format_report,
)


def validate_architecture(
    src_root: Path | None = None,
) -> ValidationReport:
    """Run the full DAG validation pipeline.

    Steps:
    1. Load manifest data (modules, dependencies, layers)
    2. Scan imports from src/ tree
    3. Match imports against allowed dependencies
    4. Detect cycles in both manifest and observed graphs
    5. Validate layer hierarchy
    6. Build and return the unified report

    Args:
        src_root: Path to the src/ directory. Auto-detected if None.

    Returns:
        ValidationReport with pass/fail verdict and all findings.
    """
    from manifest_registry.dependency_registry import ALLOWED_DEPENDENCIES
    from manifest_registry.module_inventory import MODULES, get_module_names
    from manifest_registry.version_registry import MANIFEST_VERSION

    # Resolve src root
    if src_root is None:
        src_root = Path(__file__).resolve().parent.parent

    known_modules = get_module_names()

    # Step 1: Scan imports
    scan = scan_imports(src_root, known_modules)

    # Step 2: Match against manifest
    match = match_dependencies(scan, ALLOWED_DEPENDENCIES, known_modules)

    # Step 3: Detect cycles in manifest graph
    manifest_cycles = detect_cycles_in_manifest(ALLOWED_DEPENDENCIES)

    # Step 4: Detect cycles in observed import graph
    observed_cycles = detect_cycles_in_observed(scan)

    # Step 5: Merge cycle results
    all_cycles = manifest_cycles.cycles + observed_cycles.cycles
    # Deduplicate by frozenset
    seen: set[frozenset[str]] = set()
    unique_cycles: list[tuple[str, ...]] = []
    for c in all_cycles:
        key = frozenset(c)
        if key not in seen:
            seen.add(key)
            unique_cycles.append(c)
    merged_cycles = CycleResult(
        cycles=tuple(unique_cycles),
        has_cycles=len(unique_cycles) > 0,
    )

    # Step 6: Validate layer hierarchy
    module_layers = {m.module_name: m.module_layer for m in MODULES}
    layers = validate_layers(ALLOWED_DEPENDENCIES, module_layers)

    # Step 7: Build report
    return build_report(
        match_result=match,
        cycle_result=merged_cycles,
        layer_result=layers,
        manifest_version=MANIFEST_VERSION,
        files_scanned=scan.files_scanned,
        scan_errors=scan.errors,
    )


__all__ = [
    # Main entry point
    "validate_architecture",
    # Sub-components
    "CycleResult",
    "ImportRecord",
    "LayerResult",
    "LayerViolation",
    "LAYER_ORDER",
    "MatchResult",
    "ReportEntry",
    "ScanResult",
    "Severity",
    "ValidationReport",
    "Violation",
    # Sub-functions
    "build_report",
    "detect_cycles_in_manifest",
    "detect_cycles_in_observed",
    "format_report",
    "match_dependencies",
    "scan_imports",
    "validate_layers",
]
