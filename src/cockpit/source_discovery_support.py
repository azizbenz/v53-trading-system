"""Read-only source discovery runner for the V5.3 cockpit audit."""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import re
from pathlib import Path
from typing import Iterable, Sequence

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None


_ROOT_VM_PATTERN = re.compile(r"vm(?:\.[A-Za-z_][A-Za-z0-9_]*)+")
_INCLUDE_PATTERN = re.compile(r"""{%\s*include\s+["']([^"']+)["']""")
_ARTIFACT_PATTERN = re.compile(
    r"""["']([^"'\n]+\.(?:jsonl?|ya?ml|log|prom|txt))["']""",
    re.IGNORECASE,
)
_FORMULA_HINT_PATTERN = re.compile(
    r"\b(threshold|limit|floor|cap|ratio|rate|drawdown|ce_net|exec_rate|sterilization|kill|lineage|warmup)\b",
    re.IGNORECASE,
)
_EXCLUDED_DIR_NAMES = {".git", ".pytest_cache", "__pycache__", "build"}
_EXCLUDED_PREFIXES = ("pytest-cache-files-",)
_CODE_EXTENSIONS = {".py", ".ps1"}
_RUNTIME_EXTENSIONS = {".json", ".jsonl", ".yaml", ".yml", ".log", ".prom", ".txt"}
_RUNTIME_NAME_HINTS = (
    "warmup",
    "shadow_vps_service",
    "feature_bridge",
    "replay",
    "grafana",
    "prometheus",
    "observability",
    "threshold",
    "model_risk",
    "refusal",
    "queue",
    "lineage",
    "live_complete",
    "capture",
    "snapshot",
    "user_data",
    "review",
    "verdict",
    "artifact",
    "consistency",
    "performance_mode",
    "session_config",
)
_SHARED_BADGES = {
    "runtime.alerts",
    "service.running",
    "pairs.active_pairs",
    "pairs.configured_pairs",
    "operational_proof.system_flow.operability_score",
    "operational_proof.freshness",
}
_PAGE_LABELS = {
    "overview": "Overview",
    "trading": "Trading",
    "shadow": "Shadow",
    "vps": "VPS",
    "lab": "IA Lab",
    "backtest": "Backtest",
    "backtest_chunked": "Backtest Chunked",
    "glossary": "Glossary",
    "logs": "Logs",
    "observability": "Observability",
}
_PAGE_ROUTE_HINTS = {
    "overview": "/",
    "trading": "/trading",
    "shadow": "/shadow",
    "vps": "/vps",
    "lab": "/lab",
    "backtest": "/backtest",
    "backtest_chunked": "/backtest/chunked",
    "glossary": "/glossary",
    "logs": "/logs",
    "observability": "/observability",
}
_PAGE_OWNERSHIP_HINTS = {
    "overview": ("system_flow", "freshness", "runtime.alerts"),
    "trading": ("feature_bridge", "engines", "replay", "sizing_chain", "decision_trace"),
    "shadow": ("warmup_explainer", "tail_risk", "refusal_journal", "pair_universe"),
    "vps": ("service_liveness", "queue_trace", "disk_growth", "data_quality"),
    "lab": ("lab_review", "lab_vps_transfer", "model_risk", "calibration", "multiple_testing"),
    "backtest": ("run_comparison", "replay", "decision_trace", "backtest_jobs"),
    "backtest_chunked": ("chunk_index", "global_synthesis", "chunk_manifest", "data_quality"),
    "glossary": ("canonical_glossary", "audit_dictionary", "operator_terms"),
    "logs": ("recent_logs", "log_query", "parse_error"),
    "observability": ("observability", "prometheus", "grafana", "bridge"),
}
_HIGH_SIGNAL_BACKLOG_DOMAINS = {
    "cockpit",
    "monitoring",
    "protocols",
    "local_replay_runtime",
    "backtest_artifact_import",
    "calibration_methods",
    "meta_learning",
    "meta_minimal",
    "engines",
    "execution_backbone",
    "interface_contracts",
    "scoring_backbone",
    "risk_backbone",
    "portfolio",
    "regime_classifier",
    "venue_adapters",
    "complete_enablers",
}


@dataclass(frozen=True)
class PageSurface:
    page_id: str
    label: str
    route_path: str
    template_path: str
    partials: tuple[str, ...]
    vm_paths: tuple[str, ...]
    vm_roots: tuple[str, ...]


@dataclass(frozen=True)
class FileLedgerEntry:
    file_path: str
    domain_area: str
    primary_responsibility: str
    dashboard_relevance: str
    owner_page_candidate: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    runtime_files_read: tuple[str, ...]
    formulas_or_derived_metrics: tuple[str, ...]
    thresholds_or_constants: tuple[str, ...]
    control_flags_or_gates: tuple[str, ...]
    duplication_notes: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class FormulaLedgerEntry:
    page_id: str
    metric_name: str
    source_classification: str
    source_file: str
    source_symbol: str
    notes: str


@dataclass(frozen=True)
class RuntimeFileEntry:
    file_path: str
    category: str
    exists: bool
    parse_status: str
    size_bytes: int
    age_seconds: float | None
    owner_page_candidate: str


@dataclass(frozen=True)
class DuplicationEntry:
    metric_path: str
    pages: tuple[str, ...]
    owner_page: str
    duplication_status: str
    notes: str


@dataclass(frozen=True)
class DiscoveryArtifacts:
    pages: tuple[PageSurface, ...]
    file_ledger: tuple[FileLedgerEntry, ...]
    formulas: tuple[FormulaLedgerEntry, ...]
    runtime_files: tuple[RuntimeFileEntry, ...]
    duplications: tuple[DuplicationEntry, ...]
    missing_backlog: tuple[dict[str, object], ...]


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the V5.3 cockpit source discovery audit.",
    )
    repo_root_default = Path(__file__).resolve().parents[2]
    parser.add_argument("--repo-root", type=Path, default=repo_root_default)
    parser.add_argument("--runtime-root", type=Path, default=repo_root_default / "build")
    parser.add_argument("--output-dir", type=Path, default=repo_root_default / "docs" / "cockpit")
    parser.add_argument(
        "--emit-json",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Emit machine-readable discovery artifacts under discovery_artifacts/.",
    )
    parser.add_argument(
        "--stdout-only",
        action="store_true",
        help="Print a compact summary instead of writing documentation files.",
    )
    return parser


def run_discovery(
    *,
    repo_root: Path,
    runtime_root: Path,
) -> DiscoveryArtifacts:
    repo_root = repo_root.resolve()
    view_model_fields = _discover_view_model_fields(repo_root)
    pages = discover_pages(repo_root)
    file_ledger = discover_file_ledger(
        repo_root=repo_root,
        pages=pages,
        dashboard_fields=view_model_fields["dashboard"],
        operational_fields=view_model_fields["operational"],
    )
    formulas = build_formula_ledger(file_ledger)
    runtime_files = discover_runtime_files(repo_root=repo_root, runtime_root=runtime_root)
    duplications = build_duplication_audit(pages)
    missing_backlog = build_missing_backlog(
        file_ledger=file_ledger,
        formulas=formulas,
        runtime_files=runtime_files,
    )
    return DiscoveryArtifacts(
        pages=pages,
        file_ledger=file_ledger,
        formulas=formulas,
        runtime_files=runtime_files,
        duplications=duplications,
        missing_backlog=missing_backlog,
    )


def write_discovery_outputs(
    *,
    artifacts: DiscoveryArtifacts,
    output_dir: Path,
    emit_json: bool,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "page_source": output_dir / "PAGE_SOURCE_DISCOVERY_MATRIX.md",
        "page_ownership": output_dir / "PAGE_METRIC_OWNERSHIP_MATRIX.md",
        "formula_source": output_dir / "PAGE_FORMULA_SOURCE_LEDGER.md",
        "missing_backlog": output_dir / "PAGE_MISSING_SOURCE_BACKLOG.md",
        "duplication": output_dir / "PAGE_DUPLICATION_AUDIT.md",
        "file_ledger": output_dir / "FILE_SOURCE_LEDGER.md",
    }
    paths["page_source"].write_text(render_page_source_matrix(artifacts.pages), encoding="utf-8")
    paths["page_ownership"].write_text(
        render_page_ownership_matrix(artifacts.pages),
        encoding="utf-8",
    )
    paths["formula_source"].write_text(
        render_formula_source_ledger(artifacts.formulas),
        encoding="utf-8",
    )
    paths["missing_backlog"].write_text(
        render_missing_backlog(artifacts.missing_backlog),
        encoding="utf-8",
    )
    paths["duplication"].write_text(
        render_duplication_audit(artifacts.duplications),
        encoding="utf-8",
    )
    paths["file_ledger"].write_text(
        render_file_source_ledger(artifacts.file_ledger),
        encoding="utf-8",
    )
    if emit_json:
        artifact_dir = output_dir / "discovery_artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "file_source_ledger.json").write_text(
            json.dumps([asdict(entry) for entry in artifacts.file_ledger], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (artifact_dir / "page_surfaces.json").write_text(
            json.dumps([asdict(entry) for entry in artifacts.pages], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (artifact_dir / "formula_source_ledger.json").write_text(
            json.dumps([asdict(entry) for entry in artifacts.formulas], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (artifact_dir / "runtime_files.json").write_text(
            json.dumps([asdict(entry) for entry in artifacts.runtime_files], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (artifact_dir / "duplication_audit.json").write_text(
            json.dumps([asdict(entry) for entry in artifacts.duplications], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (artifact_dir / "missing_backlog.json").write_text(
            json.dumps(list(artifacts.missing_backlog), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return paths


def discover_pages(repo_root: Path) -> tuple[PageSurface, ...]:
    templates_root = repo_root / "src" / "cockpit" / "templates"
    page_paths = [templates_root / "index.html"]
    page_paths.extend(sorted((templates_root / "pages").glob("*.html")))
    partial_cache: dict[Path, tuple[str, ...]] = {}
    surfaces: list[PageSurface] = []
    for path in page_paths:
        page_id = "overview" if path.name == "index.html" else path.stem
        partials = _resolve_partials(path, templates_root, partial_cache)
        vm_paths = _discover_template_vm_paths((path, *(templates_root / partial for partial in partials)))
        surfaces.append(
            PageSurface(
                page_id=page_id,
                label=_PAGE_LABELS.get(page_id, page_id.title()),
                route_path=_PAGE_ROUTE_HINTS.get(page_id, f"/{page_id}"),
                template_path=str(path.relative_to(repo_root).as_posix()),
                partials=partials,
                vm_paths=vm_paths,
                vm_roots=_extract_vm_roots(vm_paths),
            )
        )
    return tuple(surfaces)


def discover_file_ledger(
    *,
    repo_root: Path,
    pages: Sequence[PageSurface],
    dashboard_fields: set[str],
    operational_fields: set[str],
) -> tuple[FileLedgerEntry, ...]:
    page_vm_map = {page.page_id: set(page.vm_paths) for page in pages}
    ledger: list[FileLedgerEntry] = []
    for path in _iter_production_files(repo_root):
        relative = str(path.relative_to(repo_root).as_posix())
        if path.suffix == ".py":
            entry = _analyze_python_file(
                repo_root=repo_root,
                path=path,
                relative_path=relative,
                page_vm_map=page_vm_map,
                dashboard_fields=dashboard_fields,
                operational_fields=operational_fields,
            )
        else:
            entry = _analyze_text_script(
                repo_root=repo_root,
                path=path,
                relative_path=relative,
                page_vm_map=page_vm_map,
            )
        ledger.append(entry)
    return tuple(sorted(ledger, key=lambda item: item.file_path))


def build_formula_ledger(
    file_ledger: Sequence[FileLedgerEntry],
) -> tuple[FormulaLedgerEntry, ...]:
    rows: list[FormulaLedgerEntry] = []
    for entry in file_ledger:
        for formula in entry.formulas_or_derived_metrics:
            classification = "CODE_FORMULA_FOUND"
            metric_name = formula
            notes = entry.primary_responsibility
            if formula.startswith("REPORT_VALUE_FOUND:"):
                classification = "REPORT_VALUE_FOUND"
                metric_name = formula.split(":", 1)[1].strip()
            elif formula.startswith("DISPLAY_OPERATIONAL_DIAGNOSTIC:"):
                classification = "DISPLAY_OPERATIONAL_DIAGNOSTIC"
                metric_name = formula.split(":", 1)[1].strip()
            elif formula.startswith("FORMULA_SOURCE_MISSING:"):
                classification = "FORMULA_SOURCE_MISSING"
                metric_name = formula.split(":", 1)[1].strip()
            elif formula.startswith("NOT_YET_PERSISTED:"):
                classification = "NOT_YET_PERSISTED"
                metric_name = formula.split(":", 1)[1].strip()
            rows.append(
                FormulaLedgerEntry(
                    page_id=entry.owner_page_candidate or "unknown",
                    metric_name=metric_name,
                    source_classification=classification,
                    source_file=entry.file_path,
                    source_symbol=metric_name.split("=", 1)[0].strip(),
                    notes=notes,
                )
            )
        for threshold in entry.thresholds_or_constants:
            rows.append(
                FormulaLedgerEntry(
                    page_id=entry.owner_page_candidate or "unknown",
                    metric_name=threshold,
                    source_classification="CODE_FORMULA_FOUND",
                    source_file=entry.file_path,
                    source_symbol=threshold.split("=", 1)[0].strip(),
                    notes="threshold_or_constant",
                )
            )
    return tuple(sorted(rows, key=lambda row: (row.page_id, row.metric_name, row.source_file)))


def discover_runtime_files(
    *,
    repo_root: Path,
    runtime_root: Path,
) -> tuple[RuntimeFileEntry, ...]:
    roots = [runtime_root]
    config_root = repo_root / "config"
    if config_root.exists():
        roots.append(config_root)
    records: list[RuntimeFileEntry] = []
    now = datetime.now(tz=UTC)
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in _RUNTIME_EXTENSIONS:
                continue
            if not _is_relevant_runtime_artifact(path, root == config_root):
                continue
            stat = path.stat()
            parse_status = _parse_artifact_status(path)
            age_seconds = max((now - datetime.fromtimestamp(stat.st_mtime, tz=UTC)).total_seconds(), 0.0)
            records.append(
                RuntimeFileEntry(
                    file_path=str(path.relative_to(repo_root).as_posix()),
                    category=_runtime_category(path),
                    exists=True,
                    parse_status=parse_status,
                    size_bytes=int(stat.st_size),
                    age_seconds=age_seconds,
                    owner_page_candidate=_owner_from_runtime_path(path),
                )
            )
    return tuple(sorted(records, key=lambda item: item.file_path))


def build_duplication_audit(pages: Sequence[PageSurface]) -> tuple[DuplicationEntry, ...]:
    by_metric: dict[str, set[str]] = defaultdict(set)
    for page in pages:
        for path in page.vm_paths:
            by_metric[path].add(page.page_id)
    rows: list[DuplicationEntry] = []
    for metric_path, page_ids in sorted(by_metric.items()):
        if len(page_ids) <= 1:
            continue
        owner_page = _owner_from_metric_path(metric_path)
        duplication_status = "acceptable_badge" if metric_path in _SHARED_BADGES else "duplicate_non_owner"
        notes = "shared compact reminder" if duplication_status == "acceptable_badge" else "review page ownership"
        rows.append(
            DuplicationEntry(
                metric_path=metric_path,
                pages=tuple(sorted(page_ids)),
                owner_page=owner_page,
                duplication_status=duplication_status,
                notes=notes,
            )
        )
    return tuple(rows)


def build_missing_backlog(
    *,
    file_ledger: Sequence[FileLedgerEntry],
    formulas: Sequence[FormulaLedgerEntry],
    runtime_files: Sequence[RuntimeFileEntry],
) -> tuple[dict[str, object], ...]:
    backlog: list[dict[str, object]] = []
    for entry in file_ledger:
        if entry.status in {"coded_not_displayed", "orphan_candidate", "insufficient_evidence"} and _backlog_relevant(entry):
            backlog.append(
                {
                    "kind": entry.status,
                    "file_path": entry.file_path,
                    "owner_page_candidate": entry.owner_page_candidate,
                    "reason": entry.primary_responsibility,
                }
            )
    for entry in formulas:
        if entry.source_classification in {"FORMULA_SOURCE_MISSING", "NOT_YET_PERSISTED"}:
            backlog.append(
                {
                    "kind": entry.source_classification.lower(),
                    "metric_name": entry.metric_name,
                    "source_file": entry.source_file,
                    "owner_page_candidate": entry.page_id,
                }
            )
    for entry in runtime_files:
        if entry.owner_page_candidate == "unknown" and entry.parse_status != "ok":
            backlog.append(
                {
                    "kind": "runtime_owner_unknown",
                    "file_path": entry.file_path,
                    "parse_status": entry.parse_status,
                }
            )
    return tuple(backlog)


def render_page_source_matrix(pages: Sequence[PageSurface]) -> str:
    lines = ["# PAGE_SOURCE_DISCOVERY_MATRIX", ""]
    for page in pages:
        lines.extend(
            [
                f"## {page.label}",
                f"- Route: `{page.route_path}`",
                f"- Template: `{page.template_path}`",
                f"- Partials: `{', '.join(page.partials) if page.partials else 'none'}`",
                f"- VM roots: `{', '.join(page.vm_roots) if page.vm_roots else 'none'}`",
                f"- VM paths discovered: `{len(page.vm_paths)}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def render_page_ownership_matrix(pages: Sequence[PageSurface]) -> str:
    lines = [
        "# PAGE_METRIC_OWNERSHIP_MATRIX",
        "",
        "| Page | Route | Ownership hints | VM roots |",
        "|---|---|---|---|",
    ]
    for page in pages:
        hints = ", ".join(_PAGE_OWNERSHIP_HINTS.get(page.page_id, ()))
        roots = ", ".join(page.vm_roots)
        lines.append(f"| {page.label} | `{page.route_path}` | {hints} | {roots} |")
    lines.append("")
    return "\n".join(lines)


def render_formula_source_ledger(rows: Sequence[FormulaLedgerEntry]) -> str:
    lines = [
        "# PAGE_FORMULA_SOURCE_LEDGER",
        "",
        "| Owner page | Metric / formula | Classification | Source file | Symbol | Notes |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                (
                    row.page_id,
                    _escape_table(row.metric_name),
                    row.source_classification,
                    f"`{row.source_file}`",
                    _escape_table(row.source_symbol),
                    _escape_table(row.notes),
                )
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def render_missing_backlog(rows: Sequence[dict[str, object]]) -> str:
    lines = [
        "# PAGE_MISSING_SOURCE_BACKLOG",
        "",
        "| Kind | File / metric | Owner page | Reason |",
        "|---|---|---|---|",
    ]
    for row in rows:
        file_or_metric = row.get("file_path") or row.get("metric_name") or row.get("source_file") or ""
        owner = str(row.get("owner_page_candidate", "unknown"))
        reason = str(row.get("reason") or row.get("parse_status") or "")
        lines.append(
            f"| {row.get('kind', '')} | `{file_or_metric}` | {owner} | {_escape_table(reason)} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_duplication_audit(rows: Sequence[DuplicationEntry]) -> str:
    lines = [
        "# PAGE_DUPLICATION_AUDIT",
        "",
        "| Metric path | Pages | Owner page | Status | Notes |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row.metric_path}` | {', '.join(row.pages)} | {row.owner_page} | {row.duplication_status} | {_escape_table(row.notes)} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_file_source_ledger(rows: Sequence[FileLedgerEntry]) -> str:
    lines = ["# FILE_SOURCE_LEDGER", ""]
    grouped: dict[str, list[FileLedgerEntry]] = defaultdict(list)
    for row in rows:
        grouped[row.domain_area].append(row)
    for domain in sorted(grouped):
        lines.append(f"## {domain}")
        lines.append("")
        for row in grouped[domain]:
            lines.extend(
                [
                    f"### `{row.file_path}`",
                    f"- responsibility: {row.primary_responsibility}",
                    f"- dashboard_relevance: {row.dashboard_relevance}",
                    f"- owner_page_candidate: {row.owner_page_candidate or 'unknown'}",
                    f"- status: {row.status}",
                    f"- inputs: {', '.join(row.inputs) if row.inputs else 'none'}",
                    f"- outputs: {', '.join(row.outputs) if row.outputs else 'none'}",
                    f"- runtime_files_read: {', '.join(row.runtime_files_read) if row.runtime_files_read else 'none'}",
                    f"- formulas_or_derived_metrics: {', '.join(row.formulas_or_derived_metrics) if row.formulas_or_derived_metrics else 'none'}",
                    f"- thresholds_or_constants: {', '.join(row.thresholds_or_constants) if row.thresholds_or_constants else 'none'}",
                    f"- control_flags_or_gates: {', '.join(row.control_flags_or_gates) if row.control_flags_or_gates else 'none'}",
                    f"- duplication_notes: {', '.join(row.duplication_notes) if row.duplication_notes else 'none'}",
                    "",
                ]
            )
    return "\n".join(lines)


def summarize_artifacts(artifacts: DiscoveryArtifacts) -> str:
    return (
        f"pages={len(artifacts.pages)} "
        f"files={len(artifacts.file_ledger)} "
        f"formulas={len(artifacts.formulas)} "
        f"runtime_files={len(artifacts.runtime_files)} "
        f"duplications={len(artifacts.duplications)} "
        f"missing={len(artifacts.missing_backlog)}"
    )


def _resolve_partials(
    page_path: Path,
    templates_root: Path,
    partial_cache: dict[Path, tuple[str, ...]],
) -> tuple[str, ...]:
    if page_path in partial_cache:
        return partial_cache[page_path]
    partials: list[str] = []
    text = _read_text(page_path)
    for include in _INCLUDE_PATTERN.findall(text):
        include_path = templates_root / include
        relative = str(include_path.relative_to(templates_root).as_posix())
        partials.append(relative)
        partials.extend(_resolve_partials(include_path, templates_root, partial_cache))
    unique = tuple(dict.fromkeys(partials))
    partial_cache[page_path] = unique
    return unique


def _discover_template_vm_paths(paths: Iterable[Path]) -> tuple[str, ...]:
    found: dict[str, None] = {}
    for path in paths:
        for match in _ROOT_VM_PATTERN.findall(_read_text(path)):
            found[match.removeprefix("vm.")] = None
    return tuple(sorted(found))


def _extract_vm_roots(vm_paths: Sequence[str]) -> tuple[str, ...]:
    roots: dict[str, None] = {}
    for path in vm_paths:
        parts = path.split(".")
        if not parts:
            continue
        roots[parts[0]] = None
        if parts[0] == "operational_proof" and len(parts) > 1:
            roots[f"{parts[0]}.{parts[1]}"] = None
        if parts[0] == "runtime" and len(parts) > 1:
            roots[f"{parts[0]}.{parts[1]}"] = None
    return tuple(sorted(roots))


def _iter_production_files(repo_root: Path) -> Iterable[Path]:
    for base in (repo_root / "src", repo_root / "scripts"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in _CODE_EXTENSIONS:
                continue
            if any(part in _EXCLUDED_DIR_NAMES for part in path.parts):
                continue
            if any(part.startswith(prefix) for part in path.parts for prefix in _EXCLUDED_PREFIXES):
                continue
            yield path


def _analyze_python_file(
    *,
    repo_root: Path,
    path: Path,
    relative_path: str,
    page_vm_map: dict[str, set[str]],
    dashboard_fields: set[str],
    operational_fields: set[str],
) -> FileLedgerEntry:
    text = _read_text(path)
    tree = ast.parse(text)
    public_functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    public_classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    responsibility = _derive_python_responsibility(path, tree, public_functions)
    inputs = _discover_inputs(public_functions)
    outputs = _discover_outputs(public_functions, public_classes)
    runtime_files = _discover_runtime_file_literals(text, relative_path)
    formulas = _discover_formulas(path, text, tree)
    thresholds = _discover_thresholds(path, text, tree)
    control_flags = _discover_control_flags(text)
    owner_page = (
        _owner_from_script(relative_path, runtime_files)
        if relative_path.startswith("scripts/")
        else _owner_from_file(
            path=path,
            relative_path=relative_path,
            page_vm_map=page_vm_map,
            dashboard_fields=dashboard_fields,
            operational_fields=operational_fields,
        )
    )
    dashboard_relevance = _dashboard_relevance(relative_path, owner_page, runtime_files, formulas)
    duplication_notes = _duplication_notes(relative_path, owner_page, page_vm_map, dashboard_fields, operational_fields)
    status = _file_status(relative_path, owner_page, runtime_files, formulas, duplication_notes)
    return FileLedgerEntry(
        file_path=relative_path,
        domain_area=_domain_area(path, repo_root),
        primary_responsibility=responsibility,
        dashboard_relevance=dashboard_relevance,
        owner_page_candidate=owner_page,
        inputs=inputs,
        outputs=outputs,
        runtime_files_read=runtime_files,
        formulas_or_derived_metrics=formulas,
        thresholds_or_constants=thresholds,
        control_flags_or_gates=control_flags,
        duplication_notes=duplication_notes,
        status=status,
    )


def _analyze_text_script(
    *,
    repo_root: Path,
    path: Path,
    relative_path: str,
    page_vm_map: dict[str, set[str]],
) -> FileLedgerEntry:
    text = _read_text(path)
    runtime_files = _discover_runtime_file_literals(text, relative_path)
    control_flags = _discover_control_flags(text)
    thresholds = tuple(sorted(set(re.findall(r"\b[A-Z_]*(?:THRESHOLD|LIMIT|PORT|TIMEOUT|INTERVAL)[A-Z_0-9]*\b", text))))
    owner_page = _owner_from_script(relative_path, runtime_files)
    return FileLedgerEntry(
        file_path=relative_path,
        domain_area=_domain_area(path, repo_root),
        primary_responsibility=_first_non_empty_line(text) or "runtime script",
        dashboard_relevance=_dashboard_relevance(relative_path, owner_page, runtime_files, ()),
        owner_page_candidate=owner_page,
        inputs=(),
        outputs=(),
        runtime_files_read=runtime_files,
        formulas_or_derived_metrics=(),
        thresholds_or_constants=thresholds,
        control_flags_or_gates=control_flags,
        duplication_notes=(),
        status=_file_status(relative_path, owner_page, runtime_files, (), ()),
    )


def _discover_view_model_fields(repo_root: Path) -> dict[str, set[str]]:
    path = repo_root / "src" / "cockpit" / "state.py"
    tree = ast.parse(_read_text(path))
    dashboard: set[str] = set()
    operational: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        target = dashboard if node.name == "DashboardViewModel" else operational if node.name == "OperationalProofSnapshot" else None
        if target is None:
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                target.add(stmt.target.id)
    return {"dashboard": dashboard, "operational": operational}


def _derive_python_responsibility(
    path: Path,
    tree: ast.Module,
    public_functions: Sequence[ast.FunctionDef | ast.AsyncFunctionDef],
) -> str:
    doc = ast.get_docstring(tree)
    if doc:
        return doc.splitlines()[0].strip()
    if path.name.startswith("state_"):
        return f"cockpit state adapter for {path.stem.removeprefix('state_')}"
    if path.name.endswith("_support.py"):
        return f"support module for {path.stem.removesuffix('_support')}"
    if public_functions:
        return f"module exposing {public_functions[0].name}"
    return "production module"


def _discover_inputs(public_functions: Sequence[ast.FunctionDef | ast.AsyncFunctionDef]) -> tuple[str, ...]:
    names: dict[str, None] = {}
    for node in public_functions:
        if node.name.startswith("_"):
            continue
        for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
            if arg.arg != "self":
                names[arg.arg] = None
    return tuple(sorted(names))


def _discover_outputs(
    public_functions: Sequence[ast.FunctionDef | ast.AsyncFunctionDef],
    public_classes: Sequence[ast.ClassDef],
) -> tuple[str, ...]:
    outputs: dict[str, None] = {}
    for node in public_classes:
        if any(node.name.endswith(suffix) for suffix in ("Snapshot", "Summary", "ViewModel", "Projection", "Report", "State", "Bundle")):
            outputs[node.name] = None
    for node in public_functions:
        if node.name.startswith(("read_", "build_", "load_", "create_", "derive_", "compute_")):
            outputs[node.name] = None
    return tuple(sorted(outputs))


def _discover_runtime_file_literals(text: str, relative_path: str) -> tuple[str, ...]:
    found: dict[str, None] = {}
    for raw in _ARTIFACT_PATTERN.findall(text):
        cleaned = raw.replace("\\\\", "/")
        if cleaned.startswith("http"):
            continue
        found[cleaned] = None
    if relative_path.endswith("state.py"):
        found["build/build11_live_websocket_campaign/live_websocket_config.json"] = None
    return tuple(sorted(found))


def _discover_formulas(path: Path, text: str, tree: ast.Module) -> tuple[str, ...]:
    formulas: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = _assign_targets(node)
            expr = _assignment_expr(node)
            if not targets or expr is None:
                continue
            expr_text = _expr_source(text, expr)
            for target in targets:
                target_lower = target.lower()
                if (
                    _FORMULA_HINT_PATTERN.search(target_lower)
                    or "rate" in target_lower
                    or _FORMULA_HINT_PATTERN.search(expr_text)
                ):
                    formulas.append(f"{target} = {expr_text}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _FORMULA_HINT_PATTERN.search(node.name):
                for stmt in node.body:
                    if isinstance(stmt, ast.Return) and stmt.value is not None:
                        formulas.append(f"{node.name} = {_expr_source(text, stmt.value)}")
                        break
    if path.name.startswith("state_") and not formulas:
        suffix = path.stem.removeprefix("state_")
        if suffix in {"warmup_explainer", "service_liveness", "queue_trace", "decision_trace"}:
            formulas.append(f"DISPLAY_OPERATIONAL_DIAGNOSTIC: {suffix}")
        elif suffix in {"model_risk", "refusal_journal"}:
            formulas.append(f"NOT_YET_PERSISTED: {suffix}")
        elif _discover_runtime_file_literals(text, path.name):
            formulas.append(f"REPORT_VALUE_FOUND: {suffix}")
    return tuple(dict.fromkeys(formulas))


def _discover_thresholds(path: Path, text: str, tree: ast.Module) -> tuple[str, ...]:
    thresholds: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = _assign_targets(node)
            expr = _assignment_expr(node)
            if not targets or expr is None:
                continue
            if not isinstance(expr, ast.Constant) or not isinstance(expr.value, (int, float)):
                continue
            for target in targets:
                if re.search(r"(threshold|limit|floor|cap|timeout|interval|age|pct|ratio)", target, re.IGNORECASE):
                    thresholds.append(f"{target} = {expr.value}")
        if isinstance(node, ast.Compare):
            left = _expr_source(text, node.left)
            if _FORMULA_HINT_PATTERN.search(left):
                comparators = ", ".join(_expr_source(text, item) for item in node.comparators)
                thresholds.append(f"{left} compare {comparators}")
    if path.name == "thresholds.yml" and yaml is not None:
        thresholds.extend(_yaml_thresholds(path))
    return tuple(dict.fromkeys(thresholds))


def _discover_control_flags(text: str) -> tuple[str, ...]:
    flags = set(
        re.findall(
            r"\b(eligible_to_trade|runtime_mode|review_only|blocked|suspended|halt|kill|gate|queue|control_ready|passed|shadow_only)\b",
            text,
            re.IGNORECASE,
        )
    )
    return tuple(sorted(flag.lower() for flag in flags))


def _owner_from_file(
    *,
    path: Path,
    relative_path: str,
    page_vm_map: dict[str, set[str]],
    dashboard_fields: set[str],
    operational_fields: set[str],
) -> str:
    if "templates/index.html" in relative_path:
        return "overview"
    if relative_path == "src/cockpit/server.py":
        return "overview"
    if relative_path == "src/cockpit/state.py":
        return "overview"
    if relative_path == "src/cockpit/runtime_support.py":
        return "vps"
    if relative_path == "src/cockpit/source_discovery_support.py":
        return "overview"
    if "templates/pages/" in relative_path:
        return path.stem
    if "templates/partials/" in relative_path:
        partial_name = path.name
        candidates = [page_id for page_id, vm_paths in page_vm_map.items() if partial_name in _page_partial_names(page_id)]
        if candidates:
            return candidates[0]
    if path.name.startswith("state_"):
        suffix = path.stem.removeprefix("state_")
        root = suffix if suffix in dashboard_fields else f"operational_proof.{suffix}" if suffix in operational_fields else suffix
        consumers = _consuming_pages_for_root(root, page_vm_map)
        if consumers:
            return _pick_owner_for_pages(consumers, root)
        return _owner_from_metric_path(root)
    if path.name in {"runtime_support.py", "queue_support.py", "action_support.py"}:
        return "vps"
    if "monitoring" in relative_path:
        return "observability"
    if "engines" in relative_path or "scoring_backbone" in relative_path or "portfolio" in relative_path:
        return "trading"
    if any(part in relative_path for part in ("local_replay_runtime", "backtest_artifact_import", "calibration_methods")):
        return "backtest"
    if any(part in relative_path for part in ("meta_learning", "meta_minimal", "regime_classifier")):
        return "lab"
    if "protocols" in relative_path or "venue_adapters" in relative_path or "secrets_manager" in relative_path:
        return "shadow"
    return "unknown"


def _owner_from_script(relative_path: str, runtime_files: Sequence[str]) -> str:
    lower = relative_path.lower()
    if "cockpit" in lower:
        return "overview"
    if "local_solution" in lower:
        return "overview"
    if "grafana" in lower or "prometheus" in lower or "observability" in lower:
        return "observability"
    if "shadow_vps_service" in lower:
        return "vps"
    if "shadow" in lower or "live" in lower:
        return "shadow"
    if "backtest" in lower or "replay" in lower:
        return "backtest"
    if "lab" in lower or "calibration" in lower or "review" in lower:
        return "lab"
    if any("queue" in item for item in runtime_files):
        return "vps"
    return "unknown"


def _dashboard_relevance(
    relative_path: str,
    owner_page: str,
    runtime_files: Sequence[str],
    formulas: Sequence[str],
) -> str:
    if relative_path.startswith("src/cockpit/"):
        return "direct_surface_input"
    if owner_page != "unknown":
        return "indirect_dashboard_source"
    if runtime_files or formulas:
        return "runtime_only_source"
    return "no_direct_dashboard_evidence"


def _duplication_notes(
    relative_path: str,
    owner_page: str,
    page_vm_map: dict[str, set[str]],
    dashboard_fields: set[str],
    operational_fields: set[str],
) -> tuple[str, ...]:
    if not relative_path.startswith("src/cockpit/state_"):
        return ()
    suffix = Path(relative_path).stem.removeprefix("state_")
    root = suffix if suffix in dashboard_fields else f"operational_proof.{suffix}" if suffix in operational_fields else suffix
    consumers = _consuming_pages_for_root(root, page_vm_map)
    if len(consumers) <= 1:
        return ()
    if owner_page in consumers:
        duplicates = sorted(page for page in consumers if page != owner_page)
        if duplicates:
            return (f"also_consumed_by={','.join(duplicates)}",)
    return ()


def _file_status(
    relative_path: str,
    owner_page: str,
    runtime_files: Sequence[str],
    formulas: Sequence[str],
    duplication_notes: Sequence[str],
) -> str:
    if relative_path.startswith("src/cockpit/templates/"):
        return "displayed"
    if relative_path in {"src/cockpit/server.py", "src/cockpit/state.py"}:
        return "displayed"
    if relative_path.startswith("src/cockpit/state_") or relative_path.startswith("src/cockpit/runtime_support") or relative_path.startswith("src/cockpit/queue_support"):
        if duplication_notes:
            return "duplicate_non_owner"
        return "displayed" if owner_page != "unknown" else "coded_not_displayed"
    if owner_page != "unknown" and runtime_files:
        return "runtime_only"
    if owner_page != "unknown":
        return "coded_not_displayed"
    if formulas or runtime_files:
        return "orphan_candidate"
    return "insufficient_evidence"


def _domain_area(path: Path, repo_root: Path) -> str:
    relative = path.relative_to(repo_root)
    if relative.parts[0] == "src" and len(relative.parts) > 1:
        return relative.parts[1]
    return relative.parts[0]


def _backlog_relevant(entry: FileLedgerEntry) -> bool:
    if entry.status == "coded_not_displayed":
        return True
    if entry.owner_page_candidate != "unknown":
        return True
    if entry.domain_area in _HIGH_SIGNAL_BACKLOG_DOMAINS:
        return entry.dashboard_relevance != "no_direct_dashboard_evidence"
    if entry.file_path.startswith("scripts/"):
        return entry.dashboard_relevance in {"direct_surface_input", "indirect_dashboard_source", "runtime_only_source"}
    return False


def _owner_from_metric_path(metric_path: str) -> str:
    text = metric_path.lower()
    if any(token in text for token in ("queue_trace", "service_liveness", "disk_growth", "data_quality", "kill_proof")):
        return "vps"
    if any(token in text for token in ("warmup_explainer", "tail_risk", "refusal_journal", "pair_universe")):
        return "shadow"
    if any(token in text for token in ("feature_bridge", "engines", "replay", "sizing_chain", "economic_sterilization", "decision_trace")):
        return "trading"
    if any(token in text for token in ("lab_review", "lab_vps_transfer", "model_risk", "calibration", "multiple_testing")):
        return "lab"
    if any(token in text for token in ("observability", "grafana", "prometheus", "bridge")):
        return "observability"
    if any(token in text for token in ("backtest", "run_comparison")):
        return "backtest"
    if "log" in text:
        return "logs"
    return "overview"


def _consuming_pages_for_root(root: str, page_vm_map: dict[str, set[str]]) -> tuple[str, ...]:
    consumers = []
    for page_id, vm_paths in page_vm_map.items():
        if any(path == root or path.startswith(f"{root}.") for path in vm_paths):
            consumers.append(page_id)
    return tuple(sorted(consumers))


def _pick_owner_for_pages(pages: Sequence[str], root: str) -> str:
    root_owner = _owner_from_metric_path(root)
    if root_owner in pages:
        return root_owner
    return pages[0] if pages else "unknown"


def _runtime_category(path: Path) -> str:
    lower = path.name.lower()
    if "feature_bridge" in lower:
        return "feature_bridge"
    if "replay_metrics" in lower or "replay_dtr" in lower:
        return "backtest"
    if "warmup" in lower or "shadow_vps_service" in lower:
        return "shadow_runtime"
    if "grafana" in lower or "prometheus" in lower or "observability" in lower:
        return "observability"
    if "threshold" in lower:
        return "thresholds"
    return "runtime_artifact"


def _is_relevant_runtime_artifact(path: Path, is_config_root: bool) -> bool:
    if is_config_root:
        return path.suffix.lower() in {".yaml", ".yml", ".json"}
    lower = path.as_posix().lower()
    return any(hint in lower for hint in _RUNTIME_NAME_HINTS)


def _owner_from_runtime_path(path: Path) -> str:
    lower = path.as_posix().lower()
    if "grafana" in lower or "prometheus" in lower or "observability" in lower:
        return "observability"
    if "feature_bridge" in lower or "replay_metrics" in lower or "replay_dtr" in lower:
        return "trading" if "feature_bridge" in lower else "backtest"
    if "warmup" in lower or "shadow_vps_service" in lower:
        return "shadow"
    if "threshold" in lower:
        return "lab"
    if "log" in lower or "events" in lower:
        return "logs"
    return "unknown"


def _parse_artifact_status(path: Path) -> str:
    suffix = path.suffix.lower()
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return "unreadable"
    try:
        if suffix == ".json":
            json.loads(text)
        elif suffix == ".jsonl":
            for line in text.splitlines():
                if line.strip():
                    json.loads(line)
                    break
        elif suffix in {".yaml", ".yml"} and yaml is not None:
            yaml.safe_load(text)
    except Exception:
        return "parse_error"
    return "ok"


def _yaml_thresholds(path: Path) -> list[str]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # pragma: no cover - defensive
        return []
    thresholds: list[str] = []
    items = payload.get("thresholds")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and "threshold_id" in item and "value" in item:
                thresholds.append(f"{item['threshold_id']} = {item['value']}")
    return thresholds


def _assign_targets(node: ast.Assign | ast.AnnAssign) -> tuple[str, ...]:
    if isinstance(node, ast.Assign):
        return tuple(target.id for target in node.targets if isinstance(target, ast.Name))
    if isinstance(node.target, ast.Name):
        return (node.target.id,)
    return ()


def _assignment_expr(node: ast.Assign | ast.AnnAssign) -> ast.AST | None:
    return node.value


def _expr_source(text: str, node: ast.AST) -> str:
    return ast.get_source_segment(text, node) or ast.unparse(node)


def _page_partial_names(page_id: str) -> tuple[str, ...]:
    page = {
        "overview": ("partials/_system_flow.html", "partials/_source_freshness.html"),
        "trading": ("partials/_feature_bridge.html", "partials/_replay_metrics.html"),
        "shadow": ("partials/_warmup_explainer.html", "partials/_pair_universe_control.html"),
        "vps": ("partials/_service_liveness.html", "partials/_queue_trace.html", "partials/_disk_growth.html"),
        "lab": ("partials/_lab_review.html", "partials/_lab_vps_transfer.html"),
        "backtest": ("partials/_run_comparison.html", "partials/_decision_trace.html"),
        "logs": (),
        "observability": (),
    }
    return page.get(page_id, ())


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


__all__ = [
    "DiscoveryArtifacts",
    "FileLedgerEntry",
    "FormulaLedgerEntry",
    "PageSurface",
    "RuntimeFileEntry",
    "build_argument_parser",
    "build_duplication_audit",
    "build_formula_ledger",
    "build_missing_backlog",
    "discover_file_ledger",
    "discover_pages",
    "discover_runtime_files",
    "render_duplication_audit",
    "render_file_source_ledger",
    "render_formula_source_ledger",
    "render_missing_backlog",
    "render_page_ownership_matrix",
    "render_page_source_matrix",
    "run_discovery",
    "summarize_artifacts",
    "write_discovery_outputs",
]
