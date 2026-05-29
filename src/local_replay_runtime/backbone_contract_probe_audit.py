"""Read-only contract probe before wiring B2 surfaces to canonical backbones.

This module inspects source code and dashboard templates. It does not import or
execute trading runtimes, does not change engines, and does not mutate replay
artifacts. The output is a pre-wiring checklist: which backbone APIs exist,
which inputs/outputs are visible, which dashboard fields are missing, and
whether a B2 surface is safe to wire without a pre-patch.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text


BACKBONE_CONTRACT_PROBE_DIRNAME = "backbone_contract_probe"
BACKBONE_CONTRACT_PROBE_FINAL_FILENAME = "backbone_contract_probe_final_report.json"
BACKBONE_CONTRACT_PROBE_MATRIX_FILENAME = "backbone_contract_probe_surface_matrix.json"


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="ignore")
    except OSError:
        return ""


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _iter_python_files(root: Path) -> tuple[Path, ...]:
    if not root.is_dir():
        return ()
    return tuple(
        sorted(
            path
            for path in root.rglob("*.py")
            if path.is_file() and "__pycache__" not in path.parts
        )
    )


def _annotation_name(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _literal_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _literal_name(node.func)
    return ""


def _fields_from_class(node: ast.ClassDef) -> tuple[dict[str, str], ...]:
    fields: list[dict[str, str]] = []
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            fields.append(
                {
                    "name": item.target.id,
                    "annotation": _annotation_name(item.annotation),
                    "default_kind": _literal_name(item.value) if item.value is not None else "",
                }
            )
    return tuple(fields)


def _args_from_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[dict[str, str], ...]:
    args: list[dict[str, str]] = []
    all_args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    for arg in all_args:
        if arg.arg in {"self", "cls"}:
            continue
        args.append({"name": arg.arg, "annotation": _annotation_name(arg.annotation)})
    if node.args.vararg is not None:
        args.append({"name": f"*{node.args.vararg.arg}", "annotation": _annotation_name(node.args.vararg.annotation)})
    if node.args.kwarg is not None:
        args.append({"name": f"**{node.args.kwarg.arg}", "annotation": _annotation_name(node.args.kwarg.annotation)})
    return tuple(args)


def _scan_module(repo_root: Path, module: str) -> dict[str, Any]:
    module_root = repo_root / "src" / module
    functions: list[dict[str, Any]] = []
    classes: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []
    for path in _iter_python_files(module_root):
        rel = _relative(path, repo_root)
        text = _read_text(path)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom):
                    source = node.module or ""
                    names = tuple(alias.name for alias in node.names)
                else:
                    source = ""
                    names = tuple(alias.name for alias in node.names)
                imports.append({"path": rel, "line": node.lineno, "source": source, "names": names})
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(
                    {
                        "name": node.name,
                        "path": rel,
                        "line": node.lineno,
                        "args": _args_from_function(node),
                        "returns": _annotation_name(node.returns),
                    }
                )
            elif isinstance(node, ast.ClassDef):
                bases = tuple(_annotation_name(base) for base in node.bases)
                classes.append(
                    {
                        "name": node.name,
                        "path": rel,
                        "line": node.lineno,
                        "bases": bases,
                        "fields": _fields_from_class(node),
                    }
                )
    return {"functions": functions, "classes": classes, "imports": imports}


def _find_items(items: list[dict[str, Any]], names: tuple[str, ...]) -> list[dict[str, Any]]:
    wanted = set(names)
    return [item for item in items if str(item.get("name")) in wanted]


def _field_names(classes: list[dict[str, Any]], class_names: tuple[str, ...]) -> set[str]:
    result: set[str] = set()
    for cls in classes:
        if cls.get("name") in class_names:
            result.update(str(field.get("name")) for field in cls.get("fields", ()))
    return result


def _arg_names(functions: list[dict[str, Any]], function_names: tuple[str, ...]) -> set[str]:
    result: set[str] = set()
    for fn in functions:
        if fn.get("name") in function_names:
            result.update(str(arg.get("name")).lstrip("*") for arg in fn.get("args", ()))
    return result


def _source_mentions(repo_root: Path, roots: tuple[str, ...], tokens: tuple[str, ...]) -> dict[str, list[str]]:
    mentions: dict[str, list[str]] = {token: [] for token in tokens}
    for root in roots:
        base = repo_root / root
        files = _iter_python_files(base) if base.suffix != ".html" else ()
        if base.is_dir() and root.endswith("templates"):
            files = tuple(sorted(path for path in base.rglob("*.html") if path.is_file()))
        for path in files:
            text = _read_text(path)
            for token in tokens:
                if token in text:
                    mentions[token].append(_relative(path, repo_root))
    return mentions


SURFACE_PROBES: tuple[dict[str, Any], ...] = (
    {
        "backbone": "execution",
        "module": "execution_backbone",
        "surface": "spread_measurement",
        "entrypoints": ("evaluate_execution_spread_guard",),
        "input_classes": ("ExecutionSpreadGuardModel",),
        "output_classes": ("ExecutionSpreadGuardDecision",),
        "required_inputs": ("current_spread_bps", "max_spread_bps"),
        "required_outputs": ("blocked", "reason_code", "current_spread_bps", "max_spread_bps"),
        "dashboard_fields": ("spread", "spread_bps", "measured_spread_report"),
        "replay_truth_requirements": ("decision_timestamp_ms", "book_snapshot_ref", "bid", "ask"),
    },
    {
        "backbone": "execution",
        "module": "execution_backbone",
        "surface": "slippage_measurement",
        "entrypoints": ("predict_execution_slippage",),
        "input_classes": ("ExecutionSlippageModel",),
        "output_classes": ("ExecutionSlippageEstimate",),
        "required_inputs": ("model", "size_value", "depth20_walk_ref", "planned_notional"),
        "required_outputs": ("predicted_slippage_bps", "cost_addition", "source_threshold_id", "slippage_source_status"),
        "dashboard_fields": ("slippage", "slippage_bps", "measured_slippage_report"),
        "replay_truth_requirements": ("depth20_walk_ref", "book_snapshot_ref", "fill_price"),
    },
    {
        "backbone": "execution",
        "module": "execution_backbone",
        "surface": "fee_measurement",
        "entrypoints": ("compute_fee", "estimate_fee"),
        "input_classes": ("FeeBreakdown",),
        "output_classes": ("FeeBreakdown",),
        "required_inputs": ("order_id", "pair", "price", "quantity", "fee_amount", "fee_asset"),
        "required_outputs": ("fee_amount", "fee_rate", "fee_asset", "gross_value"),
        "dashboard_fields": ("fee", "fee_bps", "fee_source_status"),
        "replay_truth_requirements": ("venue_fee_schedule_ref", "maker"),
    },
    {
        "backbone": "execution",
        "module": "execution_backbone",
        "surface": "adverse_selection",
        "entrypoints": ("compute_adverse_selection", "resolve_adverse_selection_delay_s"),
        "input_classes": ("AdverseSelectionMeasurement", "AdverseSelectionDelayPolicy"),
        "output_classes": ("AdverseSelectionMeasurement",),
        "required_inputs": ("order_id", "pair", "side", "exec_price", "mid_after", "delay_s"),
        "required_outputs": ("adverse_selection", "mid_after", "delay_s"),
        "dashboard_fields": ("adverse_selection", "adverse_selection_status"),
        "replay_truth_requirements": ("post_fill_mid_ref", "post_window_ref"),
    },
    {
        "backbone": "scoring",
        "module": "scoring_backbone",
        "surface": "break_even",
        "entrypoints": ("evaluate_break_even_filter",),
        "input_classes": ("BreakEvenFilterConfig",),
        "output_classes": ("BreakEvenFilterDecision",),
        "required_inputs": ("expected_gain", "expected_cost", "candidate_size", "delta_safe", "cost_model_completeness_status"),
        "required_outputs": ("allowed", "reason_code", "expected_break_even", "ev_net", "cost_gate_status"),
        "dashboard_fields": ("break_even", "expected_cost", "ev_net"),
        "replay_truth_requirements": ("cost_model_completeness_status", "expected_gain_truth_status"),
    },
    {
        "backbone": "risk",
        "module": "risk_backbone",
        "surface": "risk_filtering",
        "entrypoints": ("RiskRuntime", "evaluate_candidate"),
        "input_classes": ("RiskCandidate", "RiskLimits", "PortfolioRiskSnapshot"),
        "output_classes": ("RiskEvaluation", "RiskExplainability"),
        "required_inputs": ("pair", "engine_id", "size", "planned_loss", "spread_bps", "fill_realism_status", "realized_slippage_status"),
        "required_outputs": ("accepted", "reasons", "dominant_reason_code", "explainability", "drawdown_result"),
        "dashboard_fields": ("drawdown", "loss_budget", "risk_readiness", "exposure"),
        "replay_truth_requirements": ("portfolio_snapshot_ref", "equity_curve_ref", "position_state_ref"),
    },
    {
        "backbone": "portfolio",
        "module": "portfolio_minimal",
        "surface": "capital_bucket_sizing",
        "entrypoints": ("run_portfolio_pipeline",),
        "input_classes": ("OrchestratorConfig", "OpportunityCandidate", "PortfolioSnapshot"),
        "output_classes": ("OrchestratorResult", "AllocationReport", "PortfolioArbitrationRecord"),
        "required_inputs": ("candidates", "config", "candidate_size", "expected_cost", "ev_net"),
        "required_outputs": ("report", "arbitration_records", "final_size", "capital_remaining"),
        "dashboard_fields": ("capital_bucket", "bucket", "selected_bucket_record_count", "executed_bucket_record_count"),
        "replay_truth_requirements": ("capital_profile_ref", "portfolio_snapshot_ref"),
    },
    {
        "backbone": "regime",
        "module": "regime_classifier",
        "surface": "regime_classification",
        "entrypoints": ("classify_regime_lite",),
        "input_classes": ("RegimeLiteInput", "RegimeLiteThresholds", "RegimeLiteMemory"),
        "output_classes": ("RegimeLiteAssessment",),
        "required_inputs": ("as_of_ts", "btc_realized_vol_24h", "btc_drop_1h", "intraday_drawdown"),
        "required_outputs": ("state", "entries_blocked", "reason_codes", "state_entered_ts"),
        "dashboard_fields": ("regime", "regime_id", "entries_blocked"),
        "replay_truth_requirements": ("decision_timestamp_ms", "regime_feature_window_ref"),
    },
    {
        "backbone": "protocols",
        "module": "protocols",
        "surface": "replay_governance_projection",
        "entrypoints": ("project_replay_governance",),
        "input_classes": ("ReplayGovernanceProjection",),
        "output_classes": ("ReplayGovernanceProjection",),
        "required_inputs": ("overall_backtest_proof_status", "promotion_artifact_status", "expected_edge_truth_status", "execution_label_source"),
        "required_outputs": ("readiness_status", "shadow_runtime_compatibility_status", "blocking_reasons", "micro_live_gate", "live_gate"),
        "dashboard_fields": ("readiness_status", "blocking_reasons", "micro_live_gate", "live_gate"),
        "replay_truth_requirements": ("promotion_artifact_status", "execution_fidelity_gap_codes"),
    },
)


def _probe_surface(repo_root: Path, probe: dict[str, Any], scanned: dict[str, dict[str, Any]]) -> dict[str, Any]:
    module = str(probe["module"])
    scan = scanned[module]
    functions = scan["functions"]
    classes = scan["classes"]
    function_names = tuple(str(item) for item in probe["entrypoints"])
    input_classes = tuple(str(item) for item in probe["input_classes"])
    output_classes = tuple(str(item) for item in probe["output_classes"])
    entrypoint_rows = [
        *_find_items(functions, function_names),
        *_find_items(classes, function_names),
    ]
    available_inputs = _arg_names(functions, function_names) | _field_names(classes, input_classes)
    available_outputs = _field_names(classes, output_classes)
    required_inputs = set(str(item) for item in probe["required_inputs"])
    required_outputs = set(str(item) for item in probe["required_outputs"])
    missing_inputs = tuple(sorted(required_inputs - available_inputs))
    missing_outputs = tuple(sorted(required_outputs - available_outputs))
    dashboard_fields = tuple(str(item) for item in probe["dashboard_fields"])
    dashboard_mentions = _source_mentions(
        repo_root,
        ("src/cockpit",),
        dashboard_fields,
    )
    dashboard_missing = tuple(
        field for field, paths in dashboard_mentions.items() if not paths
    )
    source_text = "\n".join(
        _read_text(repo_root / row["path"]) for row in entrypoint_rows if row.get("path")
    )
    transport_terms = tuple(
        term
        for term in ("websocket", "telegram", "live_order", "exchange_http", "send_order")
        if term in source_text.lower()
    )
    pre_patch: list[str] = []
    if not entrypoint_rows:
        pre_patch.append("ADD_REPLAY_SAFE_ENTRYPOINT")
    if missing_inputs:
        pre_patch.append("DEFINE_OR_MAP_MISSING_INPUTS")
    if missing_outputs:
        pre_patch.append("DEFINE_OR_MAP_MISSING_OUTPUTS")
    if dashboard_missing:
        pre_patch.append("ADD_DASHBOARD_REPORT_FIELDS")
    if transport_terms:
        pre_patch.append("SPLIT_TRANSPORT_FROM_REPLAY_SAFE_CONTRACT")
    if "depth20_walk_ref" in missing_inputs and probe["surface"] == "slippage_measurement":
        pre_patch.append("ADD_DEPTH20_MEASURED_SLIPPAGE_CONTRACT")
    if probe["surface"] == "adverse_selection" and "post_fill_mid_ref" in probe["replay_truth_requirements"]:
        pre_patch.append("WIRE_POST_FILL_MID_WINDOW")
    safe = bool(entrypoint_rows) and not missing_inputs and not missing_outputs and not transport_terms
    if dashboard_missing:
        safe = False
    return {
        "backbone": probe["backbone"],
        "module": module,
        "surface": probe["surface"],
        "entrypoints_found": entrypoint_rows,
        "input_contract": sorted(available_inputs),
        "output_contract": sorted(available_outputs),
        "required_inputs": tuple(sorted(required_inputs)),
        "required_outputs": tuple(sorted(required_outputs)),
        "missing_inputs": missing_inputs,
        "missing_outputs": missing_outputs,
        "dashboard_fields_required": dashboard_fields,
        "dashboard_fields_available": {
            field: tuple(sorted(set(paths))) for field, paths in dashboard_mentions.items() if paths
        },
        "dashboard_fields_missing": dashboard_missing,
        "replay_truth_requirements": probe["replay_truth_requirements"],
        "transport_coupling_terms": transport_terms,
        "safe_to_wire_b2": safe,
        "status": "BACKBONE_CONTRACT_READY" if safe else "BACKBONE_CONTRACT_INCOMPLETE",
        "required_pre_patch": tuple(dict.fromkeys(pre_patch)),
    }


def _render_markdown(final: dict[str, Any]) -> str:
    lines = [
        "# Backbone Contract Probe Audit",
        "",
        f"Generated at: `{final['generated_at']}`",
        f"Overall status: `{final['overall_status']}`",
        "",
        "This audit is read-only. It probes code contracts before moving B2 surfaces to canonical backbones.",
        "",
        "## Surface Readiness",
        "",
    ]
    for row in final["surfaces"]:
        lines.extend(
            [
                f"### {row['module']} / {row['surface']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Safe to wire B2: `{row['safe_to_wire_b2']}`",
                f"- Missing inputs: `{row['missing_inputs']}`",
                f"- Missing outputs: `{row['missing_outputs']}`",
                f"- Dashboard missing: `{row['dashboard_fields_missing']}`",
                f"- Required pre-patch: `{row['required_pre_patch']}`",
                "",
            ]
        )
    return "\n".join(lines)


def write_backbone_contract_probe_audit(
    *,
    repo_root: str | Path | None = None,
    output_dir: str | Path | None = None,
    docs_dir: str | Path | None = None,
) -> dict[str, str]:
    """Write read-only backbone contract probe reports."""

    resolved_repo_root = Path(repo_root).resolve() if repo_root is not None else Path.cwd().resolve()
    resolved_output_dir = (
        Path(output_dir).resolve()
        if output_dir is not None
        else resolved_repo_root / "reports" / BACKBONE_CONTRACT_PROBE_DIRNAME
    )
    resolved_docs_dir = (
        Path(docs_dir).resolve()
        if docs_dir is not None
        else resolved_repo_root / "docs" / "audit"
    )
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    resolved_docs_dir.mkdir(parents=True, exist_ok=True)

    modules = sorted({str(probe["module"]) for probe in SURFACE_PROBES})
    scanned = {module: _scan_module(resolved_repo_root, module) for module in modules}
    surfaces = [_probe_surface(resolved_repo_root, probe, scanned) for probe in SURFACE_PROBES]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for surface in surfaces:
        grouped[str(surface["backbone"])].append(surface)
    ready_count = sum(1 for surface in surfaces if surface["safe_to_wire_b2"])
    overall = (
        "BACKBONE_CONTRACT_PROBE_READY"
        if ready_count == len(surfaces)
        else "BACKBONE_CONTRACT_PROBE_PARTIAL"
        if ready_count
        else "BACKBONE_CONTRACT_PROBE_BLOCKED"
    )
    final = {
        "schema_version": "v53.backbone_contract_probe_audit.v1",
        "generated_at": _now_iso(),
        "audit_mode": "READ_ONLY_PRE_WIRING",
        "trading_logic_modified": False,
        "thresholds_modified": False,
        "overall_status": overall,
        "surface_count": len(surfaces),
        "safe_to_wire_count": ready_count,
        "surfaces": surfaces,
        "next_methodology": [
            "Patch one surface at a time only after safe_to_wire_b2=true or required_pre_patch is completed.",
            "After each surface patch, run B2 mini and compare reason codes/counts before moving the next surface.",
            "Never use LOCAL_REPLAY_FALLBACK_USED silently; every fallback must be reported.",
        ],
    }
    matrix = {
        "schema_version": "v53.backbone_contract_probe_surface_matrix.v1",
        "generated_at": final["generated_at"],
        "rows": surfaces,
    }
    written: dict[str, str] = {}
    final_path = resolved_output_dir / BACKBONE_CONTRACT_PROBE_FINAL_FILENAME
    matrix_path = resolved_output_dir / BACKBONE_CONTRACT_PROBE_MATRIX_FILENAME
    atomic_write_json(final_path, final, indent=2)
    atomic_write_json(matrix_path, matrix, indent=2)
    written[BACKBONE_CONTRACT_PROBE_FINAL_FILENAME] = str(final_path)
    written[BACKBONE_CONTRACT_PROBE_MATRIX_FILENAME] = str(matrix_path)
    for backbone, rows in sorted(grouped.items()):
        path = resolved_output_dir / f"backbone_contract_probe_{backbone}.json"
        payload = {
            "schema_version": f"v53.backbone_contract_probe_{backbone}.v1",
            "generated_at": final["generated_at"],
            "backbone": backbone,
            "surface_count": len(rows),
            "safe_to_wire_count": sum(1 for row in rows if row["safe_to_wire_b2"]),
            "rows": rows,
        }
        atomic_write_json(path, payload, indent=2)
        written[path.name] = str(path)
    md_path = resolved_docs_dir / "BACKBONE_CONTRACT_PROBE_AUDIT.md"
    atomic_write_text(md_path, _render_markdown(final), encoding="utf-8")
    written["BACKBONE_CONTRACT_PROBE_AUDIT.md"] = str(md_path)
    return written


__all__ = [
    "BACKBONE_CONTRACT_PROBE_FINAL_FILENAME",
    "BACKBONE_CONTRACT_PROBE_MATRIX_FILENAME",
    "write_backbone_contract_probe_audit",
]
