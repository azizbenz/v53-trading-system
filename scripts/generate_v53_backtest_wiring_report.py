from __future__ import annotations

import ast
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
REPORT_PATH = REPO_ROOT / "docs" / "v53_backtest_wiring_audit_2026-05-09.md"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dag_validator.import_scanner import scan_imports
from manifest_registry.dependency_registry import ALLOWED_DEPENDENCIES
from manifest_registry.module_inventory import MODULES, get_module_names


ROOT_MODULES = {
    "local_replay_runtime",
    "backtest_artifact_import",
    "calibration_methods",
    "meta_learning",
    "cockpit",
}
FOUNDATION_MODULES = {
    "interface_contracts",
    "manifest_registry",
    "dag_validator",
    "contract_test_suite",
    "smoke_bootstrap_recovery",
    "calibration_loader",
}
RUNTIME_OFF_RAIL_MODULES = {
    "complete_enablers",
    "protocols",
    "venue_adapters",
    "alerting",
    "secrets_manager",
    "ui",
}
MISSION2_TARGET_BY_MODULE = {
    "local_replay_runtime": "ia_lab+backtest",
    "backtest_artifact_import": "ia_lab+backtest",
    "cockpit": "ia_lab+backtest",
    "monitoring": "ia_lab+backtest",
    "calibration_methods": "ia_lab",
    "meta_learning": "ia_lab",
    "complete_enablers": "ia_lab+backtest",
    "data_backbone": "backtest",
    "regime_classifier": "backtest",
    "sharia_compliance": "backtest",
    "execution_backbone": "backtest",
    "risk_backbone": "backtest",
    "scoring_backbone": "backtest",
    "engine_a": "backtest",
    "engine_b": "backtest",
    "engine_c": "backtest",
    "engine_d": "backtest",
    "portfolio": "backtest",
    "meta": "backtest",
    "interface_contracts": "reste",
    "manifest_registry": "reste",
    "dag_validator": "reste",
    "contract_test_suite": "reste",
    "smoke_bootstrap_recovery": "reste",
    "calibration_loader": "reste",
    "protocols": "reste",
    "venue_adapters": "reste",
    "alerting": "reste",
    "secrets_manager": "reste",
    "ui": "reste",
}


@dataclass(frozen=True)
class FileInfo:
    path: Path
    relative_path: str
    import_name: str
    canonical_module: str
    docstring: str
    class_names: tuple[str, ...]
    function_names: tuple[str, ...]
    direct_dep_files: tuple[str, ...]
    direct_dep_modules: tuple[str, ...]
    reverse_dep_files: tuple[str, ...]
    reverse_dep_modules: tuple[str, ...]


def _canonical_module_for_path(path: Path) -> str:
    parts = path.relative_to(SRC_ROOT).parts
    if not parts:
        return ""
    if parts == ("__init__.py",):
        return "src_root"
    if parts[0] == "engines" and len(parts) == 2 and parts[1] == "__init__.py":
        return "engines_pkg"
    if parts[0] == "engines" and len(parts) > 1:
        return parts[1]
    if parts[0] == "portfolio_minimal":
        return "portfolio"
    if parts[0] == "meta_minimal":
        return "meta"
    return parts[0]


def _import_name_for_path(path: Path) -> str:
    rel = path.relative_to(SRC_ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _build_import_maps(py_files: Iterable[Path]) -> tuple[dict[str, Path], dict[Path, str]]:
    import_to_path: dict[str, Path] = {}
    path_to_import: dict[Path, str] = {}
    for path in py_files:
        import_name = _import_name_for_path(path)
        path_to_import[path] = import_name
        if import_name:
            import_to_path[import_name] = path
    return import_to_path, path_to_import


def _resolve_relative_module(current_import: str, module: str | None, level: int) -> str:
    current_parts = current_import.split(".")
    package_parts = current_parts[:-1]
    if level > 0:
        package_parts = package_parts[: max(len(package_parts) - (level - 1), 0)]
    if module:
        return ".".join((*package_parts, *module.split(".")))
    return ".".join(package_parts)


def _candidate_import_targets(base_module: str, imported_name: str | None) -> tuple[str, ...]:
    candidates: list[str] = []
    if base_module:
        candidates.append(base_module)
    if base_module and imported_name:
        candidates.append(f"{base_module}.{imported_name}")
    if imported_name:
        candidates.append(imported_name)
    return tuple(dict.fromkeys(item for item in candidates if item))


def _resolve_dep_paths(
    path: Path,
    import_name: str,
    import_to_path: dict[str, Path],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    dep_files: set[str] = set()
    dep_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = alias.name
                target_path = import_to_path.get(target)
                if target_path is not None and target_path != path:
                    dep_files.add(target_path.relative_to(SRC_ROOT).as_posix())
                    dep_modules.add(_canonical_module_for_path(target_path))
        elif isinstance(node, ast.ImportFrom):
            base_module = _resolve_relative_module(import_name, node.module, node.level)
            for alias in node.names:
                if alias.name == "*":
                    candidates = _candidate_import_targets(base_module, None)
                else:
                    candidates = _candidate_import_targets(base_module, alias.name)
                for candidate in candidates:
                    target_path = import_to_path.get(candidate)
                    if target_path is not None and target_path != path:
                        dep_files.add(target_path.relative_to(SRC_ROOT).as_posix())
                        dep_modules.add(_canonical_module_for_path(target_path))
                        break
    return tuple(sorted(dep_files)), tuple(sorted(dep_modules))


def _extract_docstring(path: Path) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except Exception:
        return "", (), ()
    doc = ast.get_docstring(tree) or ""
    classes = tuple(
        node.name for node in tree.body if isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef, ast.FunctionDef))
    )
    class_names = tuple(name for name in classes if name[:1].isupper())
    function_names = tuple(name for name in classes if name[:1].islower())
    return doc.strip(), class_names, function_names


def _short_role(file_info: FileInfo) -> str:
    if file_info.docstring:
        first_line = file_info.docstring.splitlines()[0].strip().strip(".")
        return first_line[:120]
    name = Path(file_info.relative_path).name
    if "contract" in name:
        return "typed contracts/models"
    if "runtime" in name:
        return "runtime flow"
    if "bridge" in name:
        return "integration bridge"
    if "loader" in name:
        return "loader"
    if "validator" in name:
        return "validator"
    if "report" in name:
        return "report builder"
    if "monitor" in name:
        return "monitoring support"
    return "module support"


def _surface_names(names: tuple[str, ...], suffixes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(name for name in names if name.endswith(suffixes))


def _format_surface(values: tuple[str, ...], fallback: str) -> str:
    if not values:
        return fallback
    display = ", ".join(values[:3])
    if len(values) > 3:
        display += f" (+{len(values) - 3})"
    return display


def _independence_label(file_info: FileInfo) -> str:
    dep_count = len(file_info.direct_dep_files)
    rev_count = len(file_info.reverse_dep_files)
    if dep_count == 0 and rev_count == 0:
        return "isolated"
    if dep_count == 0 and rev_count > 0:
        return "provider"
    if dep_count > 0 and rev_count == 0:
        return "leaf"
    if dep_count >= 5 or rev_count >= 5:
        return "hub"
    return "relay"


def _module_closure(edges: dict[str, set[str]], roots: set[str]) -> set[str]:
    seen = set(roots)
    queue = deque(roots)
    while queue:
        source = queue.popleft()
        for target in edges.get(source, set()):
            if target not in seen:
                seen.add(target)
                queue.append(target)
    return seen


def _rail_status(module_name: str, closure: set[str]) -> str:
    if module_name in ROOT_MODULES:
        return "cabled_direct"
    if module_name in closure:
        return "cabled_transitive"
    if module_name in RUNTIME_OFF_RAIL_MODULES:
        return "not_cabled_runtime"
    if module_name in FOUNDATION_MODULES:
        return "foundation_only"
    return "not_cabled"


def _rail_tag(module_name: str, closure: set[str]) -> str:
    if module_name in ROOT_MODULES:
        return "ia_lab+backtest_root"
    if module_name in closure:
        return "shared_core_on_rail"
    if module_name in RUNTIME_OFF_RAIL_MODULES:
        return "runtime_off_rail"
    if module_name in FOUNDATION_MODULES:
        return "foundation"
    return "outside_scope"


def _mission2_target(module_name: str) -> str:
    return MISSION2_TARGET_BY_MODULE.get(module_name, "reste")


def _collect_file_infos() -> tuple[list[FileInfo], dict[str, set[str]], list[tuple[str, str, str, int]]]:
    py_files = sorted(
        path
        for path in SRC_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts and "pytest-cache-files" not in path.parts
    )
    import_to_path, path_to_import = _build_import_maps(py_files)

    dep_by_file: dict[str, set[str]] = defaultdict(set)
    dep_modules_by_file: dict[str, set[str]] = defaultdict(set)
    rev_by_file: dict[str, set[str]] = defaultdict(set)
    rev_modules_by_file: dict[str, set[str]] = defaultdict(set)

    for path in py_files:
        import_name = path_to_import[path]
        dep_files, dep_modules = _resolve_dep_paths(path, import_name, import_to_path)
        rel = path.relative_to(SRC_ROOT).as_posix()
        dep_by_file[rel].update(dep_files)
        dep_modules_by_file[rel].update(dep_modules)
        for dep_file in dep_files:
            rev_by_file[dep_file].add(rel)
        for dep_module in dep_modules:
            rev_modules_by_file[dep_module].add(_canonical_module_for_path(path))

    scan_result = scan_imports(SRC_ROOT, get_module_names())
    module_edges: dict[str, set[str]] = defaultdict(set)
    violations: list[tuple[str, str, str, int]] = []
    seen_violations: set[tuple[str, str]] = set()
    for record in scan_result.imports:
        if record.source_module == record.target_module:
            continue
        module_edges[record.source_module].add(record.target_module)
        if record.target_module not in ALLOWED_DEPENDENCIES.get(record.source_module, frozenset()):
            key = (record.source_module, record.target_module)
            if key not in seen_violations:
                seen_violations.add(key)
                violations.append(
                    (
                        record.source_module,
                        record.target_module,
                        record.source_file.replace("\\", "/"),
                        record.line_number,
                    )
                )

    file_infos: list[FileInfo] = []
    for path in py_files:
        rel = path.relative_to(SRC_ROOT).as_posix()
        import_name = path_to_import[path]
        doc, class_names, function_names = _extract_docstring(path)
        file_infos.append(
            FileInfo(
                path=path,
                relative_path=rel,
                import_name=import_name,
                canonical_module=_canonical_module_for_path(path),
                docstring=doc,
                class_names=class_names,
                function_names=function_names,
                direct_dep_files=tuple(sorted(dep_by_file.get(rel, set()))),
                direct_dep_modules=tuple(sorted(dep_modules_by_file.get(rel, set()))),
                reverse_dep_files=tuple(sorted(rev_by_file.get(rel, set()))),
                reverse_dep_modules=tuple(sorted(rev_modules_by_file.get(rel, set()))),
            )
        )
    return file_infos, module_edges, violations


def _write_report() -> None:
    file_infos, module_edges, violations = _collect_file_infos()
    closure = _module_closure(module_edges, ROOT_MODULES)
    files_by_module = Counter(info.canonical_module for info in file_infos)
    cabled_files_by_module = Counter(
        info.canonical_module for info in file_infos if info.canonical_module in closure
    )
    root_files = sum(1 for info in file_infos if info.canonical_module in ROOT_MODULES)
    closure_files = sum(1 for info in file_infos if info.canonical_module in closure)
    neither_modules = sorted(set(get_module_names()) - closure)

    lines: list[str] = []
    lines.append("# V5.3 Backtest Wiring Audit")
    lines.append("")
    lines.append("Generated on 2026-05-09 from the current `src/` tree.")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(
        f"- Files scanned: **{len(file_infos)}** Python files under `src/`."
    )
    lines.append(
        f"- Direct IA Lab/backtest root modules: **{', '.join(sorted(ROOT_MODULES))}**."
    )
    lines.append(
        f"- Files on the effective IA Lab/backtest rail: **{closure_files}/{len(file_infos)}**."
    )
    lines.append(
        f"- Files inside direct root modules: **{root_files}/{len(file_infos)}**."
    )
    lines.append(
        "- Shared-core coverage already present on the rail: "
        "`data_backbone`, `regime_classifier`, `execution_backbone`, `risk_backbone`, "
        "`scoring_backbone`, `engine_a`, `engine_b`, `engine_c`, `engine_d`, `portfolio`, `meta`."
    )
    lines.append(
        "- Runtime layers still off the effective rail: "
        + ", ".join(f"`{name}`" for name in neither_modules)
        + "."
    )
    lines.append(
        "- Main architectural gap: replay/backtest uses a dedicated `shadow_execution_simulator` path, not the canonical governed runtime/protocol rail."
    )
    lines.append("")
    lines.append("## Module Rail Coverage")
    lines.append("")
    lines.append("| Module | Build | Layer | Files | On Rail | Rail Status | Mission-2 Target | Notes |")
    lines.append("|---|---:|---|---:|---|---|---|---|")
    for entry in sorted(MODULES, key=lambda item: (item.build_stage, item.module_name)):
        module_name = entry.module_name
        on_rail = "yes" if module_name in closure else "no"
        notes = entry.description.replace("|", "/")
        lines.append(
            f"| `{module_name}` | {entry.build_stage} | `{entry.module_layer}` | "
            f"{files_by_module.get(module_name, 0)} | {on_rail} | `{_rail_status(module_name, closure)}` | "
            f"`{_mission2_target(module_name)}` | {notes} |"
        )
    lines.append("")
    lines.append("## P0/P1 Findings")
    lines.append("")
    lines.append("### P0")
    lines.append("")
    lines.append("1. `local_replay_runtime` is the backtest root, but its detailed replay uses `local_replay_runtime/shadow_execution_simulator.py` instead of the canonical `execution_backbone` runtime path.")
    lines.append("2. `complete_enablers` is absent from the effective backtest rail. Engine C/D replay therefore misses the governed enrichment layer that should influence realism for advanced engines.")
    lines.append("")
    lines.append("### P1")
    lines.append("")
    lines.append(f"1. The declared DAG and the real code diverge in **{len(violations)}** module-level edges.")
    lines.append("2. `local_replay_runtime -> backtest_artifact_import` creates a reverse dependency across two stage-10 modules, which makes the handoff rail less clean than the documented architecture.")
    lines.append("3. `cockpit` imports `local_replay_runtime` directly although the manifest restricts it to read-only projections over `monitoring`/`data_backbone`.")
    lines.append("")
    lines.append("## DAG Drift")
    lines.append("")
    lines.append("| Source Module | Target Module | First File | Line |")
    lines.append("|---|---|---|---:|")
    for source, target, rel_path, line_no in violations:
        lines.append(f"| `{source}` | `{target}` | `{rel_path}` | {line_no} |")
    lines.append("")
    lines.append("## Mission 2 - Triage Table")
    lines.append("")
    lines.append("| Target | Modules / Files To Prioritize | Why |")
    lines.append("|---|---|---|")
    lines.append(
        "| `ia_lab` | `calibration_methods/*`, `meta_learning/*` | calibration, hypothesis, training, review, replay governance stay lab-first. |"
    )
    lines.append(
        "| `backtest` | `data_backbone/*`, `execution_backbone/*`, `risk_backbone/*`, `scoring_backbone/*`, `engines/engine_[a-d]/*`, `portfolio_minimal/*`, `meta_minimal/*`, `regime_classifier/*`, `sharia_compliance/*` | these are the shared-core decision layers that must drive realistic replay. |"
    )
    lines.append(
        "| `ia_lab+backtest` | `local_replay_runtime/*`, `backtest_artifact_import/*`, `cockpit/*`, `monitoring/local_lab_*`, `monitoring/local_lab_*projection*`, `complete_enablers/*` | these files own the lab/backtest rail, operator launch surface, artifact handoff, and advanced realism extensions. |"
    )
    lines.append(
        "| `reste` | `interface_contracts/*`, `manifest_registry/*`, `dag_validator/*`, `contract_test_suite/*`, `smoke_bootstrap_recovery/*`, `protocols/*`, `venue_adapters/*`, `alerting/*`, `secrets_manager/*`, `ui/*` | foundation/live-only surfaces; keep them aligned, but do not wire everything blindly into replay. |"
    )
    lines.append("")
    lines.append("## Wiring Plan")
    lines.append("")
    lines.append("1. **Stabilize architecture truth**: update `manifest_registry/dependency_registry.py` so the documented DAG matches the current Strategy Ladder backtest rail, or refactor the code to respect the declared DAG. Without this, every next wiring step keeps two architectures alive.")
    lines.append("2. **Replace proxy replay seams with canonical seams**: progressively move `local_replay_runtime/strategy_ladder_detailed_replay.py` and `replay_orchestrator_execution.py` from `shadow_execution_simulator` toward canonical `execution_backbone` components for cost, fills, spread, slippage, and route realism.")
    lines.append("3. **Wire `complete_enablers` into engine C/D replay**: import the governed enabler layer through canonical engine input composition, not through static manifests or coverage-only references.")
    lines.append("4. **Expose shared-core runtime snapshots**: ensure backtest artifacts record which exact risk/scoring/execution/enabler versions were used so parity with Shadow can be audited.")
    lines.append("5. **Keep the handoff one-way**: move ML/artifact packaging responsibilities out of `local_replay_runtime` where possible so `backtest_artifact_import` stays a downstream bridge instead of forming a cycle.")
    lines.append("6. **Converge replay and Shadow gates**: reuse `protocols` gate/projection logic selectively for proof and promotion checks, but avoid importing live transport concerns into replay.")
    lines.append("7. **Add regression coverage**: DAG check, backtest proof matrix checks, and a replay-vs-shadow parity suite should be mandatory before declaring the rail fully wired.")
    lines.append("")
    lines.append("## Appendix A - File Inventory")
    lines.append("")
    lines.append(
        "The table below is file-level. `Inputs` and `Outputs` are inferred from class/function surfaces and docstrings, so they are useful for triage, not a formal API contract."
    )
    lines.append("")
    lines.append("| File | Module | Role | Inputs | Outputs | Direct File Deps | Reverse File Deps | Independence | Rail Tag | Status | Mission-2 Target |")
    lines.append("|---|---|---|---|---|---:|---:|---|---|---|---|")

    for info in sorted(file_infos, key=lambda item: (item.canonical_module, item.relative_path)):
        input_names = _surface_names(info.class_names, ("Request", "Input", "Config", "Manifest", "Preview", "State"))
        output_names = _surface_names(info.class_names, ("Result", "Report", "Artifact", "Summary", "Record", "Payload"))
        if not input_names:
            input_names = tuple(name for name in info.function_names if name.startswith(("load_", "build_", "run_", "parse_")))
        if not output_names:
            output_names = tuple(name for name in info.function_names if name.startswith(("build_", "write_", "export_", "render_")))
        lines.append(
            f"| `{info.relative_path}` | `{info.canonical_module}` | {_short_role(info).replace('|', '/')} | "
            f"{_format_surface(input_names, '-').replace('|', '/')} | "
            f"{_format_surface(output_names, '-').replace('|', '/')} | "
            f"{len(info.direct_dep_files)} | {len(info.reverse_dep_files)} | "
            f"`{_independence_label(info)}` | `{_rail_tag(info.canonical_module, closure)}` | "
            f"`{_rail_status(info.canonical_module, closure)}` | `{_mission2_target(info.canonical_module)}` |"
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    _write_report()
