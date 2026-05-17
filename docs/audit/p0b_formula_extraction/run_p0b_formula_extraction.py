#!/usr/bin/env python3
"""P0-B full formula extraction audit for V5.3.

Audit-only generator:
- scans source/test/doc scopes
- extracts formula-like AST nodes
- classifies them into source-safe buckets
- maps tests/docs/consumers/artifacts/owner pages
- writes the P0-B audit package
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = REPO_ROOT / "docs" / "audit" / "p0b_formula_extraction"

REAL_CLASSES = {
    "REAL_QUANT_FORMULA",
    "MICROSTRUCTURE_ESTIMATOR",
    "STATISTICAL_ANCHOR",
    "EXECUTION_COST_FORMULA",
    "RISK_SIZING_FORMULA",
    "ML_LABEL_OR_FEATURE_TRANSFORM",
}

SOURCE_EXTENSIONS = {".py"}
DOC_EXTENSIONS = {".md", ".txt"}
DISPLAYABLE_CLASSES = REAL_CLASSES | {"OPERATIONAL_DIAGNOSTIC", "REPORT_VALUE"}

MATH_CALL_NAMES = {
    "abs",
    "all",
    "any",
    "cdf",
    "ceil",
    "corr",
    "cov",
    "erf",
    "exp",
    "floor",
    "inv_cdf",
    "log",
    "max",
    "mean",
    "median",
    "min",
    "pow",
    "prod",
    "quantile",
    "round",
    "sqrt",
    "std",
    "sum",
    "var",
    "variance",
    "zip",
}

THRESHOLD_KEYWORDS = (
    "acceptance",
    "alpha",
    "bandwidth",
    "block",
    "bootstrap_samples",
    "bucket",
    "cap",
    "ceiling",
    "confidence",
    "cutoff",
    "default",
    "embargo",
    "floor",
    "gate",
    "horizon",
    "lag",
    "level",
    "limit",
    "lookback",
    "max",
    "min",
    "n_",
    "period",
    "probability",
    "purge",
    "quantile",
    "ratio",
    "seed",
    "sigma",
    "threshold",
    "timeout",
    "trial_count",
    "window",
)

STATUS_KEYWORDS = (
    "allowed",
    "applied",
    "blocked",
    "complete",
    "confident",
    "covered",
    "enabled",
    "flag",
    "halted",
    "healthy",
    "insufficient",
    "live",
    "loaded",
    "low_sample",
    "missing",
    "partial",
    "passes",
    "persisted",
    "present",
    "proven",
    "ready",
    "rejects",
    "review",
    "selected",
    "stale",
    "status",
    "suspended",
    "valid",
    "warning",
)

TEXT_LIST_HINTS = (
    "lines",
    "message",
    "messages",
    "notes",
    "reasons",
    "refs",
    "report",
    "summary",
    "warnings",
)

FALSE_GREEN_METRIC_HINTS = (
    "ce_net",
    "exec_rate",
    "expected_cost",
    "realized_cost",
    "gross_return",
    "drawdown",
    "psr",
    "dsr",
)

OWNER_PAGE_MAP = {
    "backtest": "Backtest",
    "lab": "IA Lab",
    "observability": "Observability",
    "overview": "Overview",
    "shadow": "Shadow",
    "trading": "Trading",
    "vps": "VPS",
}

FILE_CLASS_OVERRIDES = {
    "src/data_backbone/microstructure/kyle_lambda.py": (
        "Kyle lambda / price impact",
        "rolling_ols",
        "MICROSTRUCTURE_ESTIMATOR",
    ),
    "src/data_backbone/microstructure/order_flow_imbalance.py": (
        "Order Flow Imbalance (Cont-Kukanov)",
        "event_sum",
        "MICROSTRUCTURE_ESTIMATOR",
    ),
    "src/data_backbone/microstructure/vpin.py": (
        "VPIN",
        "equal_volume_bvc",
        "MICROSTRUCTURE_ESTIMATOR",
    ),
    "src/data_backbone/microstructure/pin.py": (
        "PIN",
        "poisson_mixture",
        "MICROSTRUCTURE_ESTIMATOR",
    ),
    "src/data_backbone/microstructure/amihud_illiquidity.py": (
        "Amihud illiquidity",
        "impact_ratio",
        "MICROSTRUCTURE_ESTIMATOR",
    ),
    "src/data_backbone/microstructure/roll_spread.py": (
        "Roll spread",
        "serial_covariance",
        "MICROSTRUCTURE_ESTIMATOR",
    ),
    "src/data_backbone/microstructure/corwin_schultz_spread.py": (
        "Corwin-Schultz spread",
        "high_low_estimator",
        "MICROSTRUCTURE_ESTIMATOR",
    ),
    "src/data_backbone/microstructure/realized_kernel_vol.py": (
        "Realized kernel volatility",
        "parzen_kernel",
        "MICROSTRUCTURE_ESTIMATOR",
    ),
    "src/data_backbone/microstructure/realized_effective_spread.py": (
        "Realized / effective spread",
        "spread_estimator",
        "MICROSTRUCTURE_ESTIMATOR",
    ),
    "src/data_backbone/microstructure/spread_dynamics.py": (
        "Spread dynamics",
        "spread_time_series",
        "MICROSTRUCTURE_ESTIMATOR",
    ),
    "src/data_backbone/microstructure/queue_pressure.py": (
        "Queue pressure / order-book imbalance",
        "book_pressure_ratio",
        "MICROSTRUCTURE_ESTIMATOR",
    ),
    "src/data_backbone/microstructure/hawkes_intensity.py": (
        "Hawkes intensity",
        "hawkes_decay",
        "MICROSTRUCTURE_ESTIMATOR",
    ),
    "src/data_backbone/microstructure/lob_regime_features.py": (
        "LOB regime features",
        "feature_transform",
        "ML_LABEL_OR_FEATURE_TRANSFORM",
    ),
    "src/data_backbone/microstructure/walls_and_spoofing.py": (
        "Walls / spoofing features",
        "feature_transform",
        "MICROSTRUCTURE_ESTIMATOR",
    ),
    "src/calibration_methods/psr.py": (
        "Probabilistic Sharpe Ratio",
        "closed_form_statistic",
        "STATISTICAL_ANCHOR",
    ),
    "src/calibration_methods/dsr.py": (
        "Deflated Sharpe Ratio",
        "closed_form_statistic",
        "STATISTICAL_ANCHOR",
    ),
    "src/calibration_methods/multiple_testing_guard.py": (
        "Harvey-Liu-Zhu multiple-testing guard",
        "hlz_deflation",
        "STATISTICAL_ANCHOR",
    ),
    "src/calibration_methods/hansen_spa.py": (
        "Hansen SPA",
        "stationary_bootstrap_test",
        "STATISTICAL_ANCHOR",
    ),
    "src/calibration_methods/pot_gpd.py": (
        "POT-GPD",
        "evt_tail_fit",
        "STATISTICAL_ANCHOR",
    ),
    "src/calibration_methods/energy_distance.py": (
        "Energy distance",
        "distribution_distance",
        "STATISTICAL_ANCHOR",
    ),
    "src/calibration_methods/ks_test.py": (
        "KS two-sample",
        "nonparametric_test",
        "STATISTICAL_ANCHOR",
    ),
    "src/calibration_methods/mann_kendall.py": (
        "Mann-Kendall trend",
        "rank_test",
        "STATISTICAL_ANCHOR",
    ),
    "src/calibration_methods/stationarity.py": (
        "ADF / KPSS stationarity",
        "dual_stationarity",
        "STATISTICAL_ANCHOR",
    ),
    "src/calibration_methods/bootstrap.py": (
        "Stationary bootstrap",
        "stationary_bootstrap",
        "STATISTICAL_ANCHOR",
    ),
    "src/calibration_methods/walkforward.py": (
        "Purged walk-forward",
        "walk_forward_validation",
        "STATISTICAL_ANCHOR",
    ),
    "src/local_replay_runtime/replay_metrics_collector.py": (
        "Replay profitability aggregates",
        "replay_aggregate",
        "REAL_QUANT_FORMULA",
    ),
    "src/local_replay_runtime/shadow_execution_simulator.py": (
        "Shadow / replay parity metrics",
        "parity_metric",
        "REAL_QUANT_FORMULA",
    ),
    "src/local_replay_runtime/artifact_ablation_study.py": (
        "Ablation / block-rate metrics",
        "ablation_metric",
        "REAL_QUANT_FORMULA",
    ),
}

RUNTIME_ARTIFACT_OVERRIDES = {
    "scripts/run_shadow_vps_service.py": {
        "read": [
            "dashboard_command_queue/*",
            "live_websocket_config.json",
            "auto_exports/*/replay_run_manifest.json",
            "auto_exports/*/feature_bridge.json",
            "auto_exports/*/parity_diagnostics.json",
            "auto_exports/*/replay_metrics.json",
            "service/runtime_evidence_bundle.json",
        ],
        "write": [
            "shadow_vps_service.pid",
            "shadow_vps_service.state.json",
            "shadow_vps_service.events.jsonl",
            "shadow_vps_service_monitoring_backend_payload.json",
            "shadow_vps_service_observability_export.json",
            "shadow_vps_service_recent_events.json",
            "shadow_vps_service_scrape_manifest.json",
            "shadow_vps_service_prometheus_file_sd.json",
            "shadow_vps_service_execution_telemetry.json",
            "shadow_vps_service_execution_telemetry.archive.json",
            "shadow_vps_service.campaign_summary.json",
        ],
    },
    "src/local_replay_runtime/artifact_exporter.py": {
        "write": [
            "replay_run_manifest.json",
            "review_export.md",
            "feature_bridge.json",
            "parity_diagnostics.json",
            "replay_metrics.json",
            "replay_dtr.jsonl",
        ]
    },
    "src/local_replay_runtime/replay_orchestrator_io.py": {
        "read": [
            "replay_chunk_session.json",
            "replay_run_manifest.json",
            "replay_session_config.json",
        ],
        "write": ["replay_run_manifest.json"],
    },
    "src/local_replay_runtime/replay_orchestrator_execution.py": {
        "read": [
            "performance_mode_guard.json",
            "replay_chunk_session.json",
            "replay_session_config.json",
            "replay_session_state.json",
            "run_consistency_guard.json",
        ]
    },
    "src/local_replay_runtime/replay_orchestrator_resume.py": {
        "read": [
            "replay_run_manifest.json",
            "feature_bridge.json",
            "parity_diagnostics.json",
            "replay_metrics.json",
            "replay_dtr.jsonl",
            "performance_mode_guard.json",
            "replay_chunk_session.json",
            "replay_session_config.json",
            "replay_session_state.json",
            "run_consistency_guard.json",
        ]
    },
    "src/local_replay_runtime/replay_state_store.py": {
        "read": ["replay_session_state.json"]
    },
    "src/local_replay_runtime/runtime_evidence.py": {
        "read": ["local_replay_runtime_evidence.json"]
    },
    "src/local_replay_runtime/local_lab_replay_workflow_loader.py": {
        "read": [
            "local_lab_replay_workflow_manifest.json",
            "local_lab_replay_candidate_queue.json",
            "local_lab_replay_ticket_index.json",
            "local_lab_replay_dispatch_plan.json",
        ]
    },
    "src/local_replay_runtime/local_lab_execution_telemetry_artifact.py": {
        "read": ["replay_run_manifest.json"]
    },
    "src/local_replay_runtime/edge_gate_calibration.py": {
        "read": ["config/calibration/v1/edge_gate.yml"]
    },
    "src/backtest_artifact_import/export_dir_bridge.py": {
        "read": [
            "replay_run_manifest.json",
            "review_export.md",
            "feature_bridge.json",
            "parity_diagnostics.json",
            "replay_metrics.json",
            "replay_dtr.json",
            "replay_dtr.jsonl",
        ]
    },
    "src/backtest_artifact_import/ml_model_transport.py": {
        "read": ["ml_model_artifact.json", "ml_model_artifact.summary.json"]
    },
    "src/backtest_artifact_import/regime_detector_transport.py": {
        "read": [
            "regime_detector_artifact.json",
            "regime_detector_artifact.summary.json",
        ]
    },
    "src/execution_backbone/emergency_circuit_breaker.py": {
        "read": ["kill_switch_state.json"],
        "write": ["kill_switch_state.json"],
    },
    "src/engines/engine_d/engine_state_snapshot_d.py": {
        "read": [
            "engine_d_state_snapshots.jsonl",
            "engine_d_state_snapshot_manifest.json",
        ],
        "write": [
            "engine_d_state_snapshots.jsonl",
            "engine_d_state_snapshot_manifest.json",
        ],
    },
    "src/secrets_manager/loader.py": {"read": ["{source}.sealed.json"]},
    "src/secrets_manager/sealer.py": {"write": ["{source}.sealed.json"]},
    "src/venue_adapters/binance_spot/credential_loader.py": {
        "read": [".sealed.json"]
    },
}

DOC_HINTS = {
    "Kyle lambda / price impact": ("kyle_lambda", "kyle lambda"),
    "Order Flow Imbalance (Cont-Kukanov)": ("order_flow_imbalance", "ofi"),
    "VPIN": ("vpin",),
    "PIN": (" pin ", "pin.py"),
    "Amihud illiquidity": ("amihud",),
    "Roll spread": ("roll spread", "roll_spread"),
    "Corwin-Schultz spread": ("corwin", "schultz"),
    "Realized kernel volatility": ("realized kernel", "realized_kernel"),
    "Realized / effective spread": ("effective spread", "realized_effective_spread"),
    "Spread dynamics": ("spread_dynamics", "spread dynamics"),
    "Queue pressure / order-book imbalance": ("queue_pressure", "book imbalance"),
    "Hawkes intensity": ("hawkes",),
    "LOB regime features": ("lob regime", "lob_regime_features"),
    "Walls / spoofing features": ("spoof", "walls_and_spoofing"),
    "Probabilistic Sharpe Ratio": ("psr", "probabilistic sharpe"),
    "Deflated Sharpe Ratio": ("dsr", "deflated sharpe"),
    "Harvey-Liu-Zhu multiple-testing guard": ("hlz", "harvey", "liu", "zhu"),
    "Hansen SPA": ("hansen spa", "spa"),
    "POT-GPD": ("pot_gpd", "gpd", "evt"),
    "Energy distance": ("energy distance",),
    "KS two-sample": ("ks_test", "kolmogorov"),
    "Mann-Kendall trend": ("mann_kendall",),
    "ADF / KPSS stationarity": ("adf", "kpss", "stationarity"),
    "Stationary bootstrap": ("stationary bootstrap", "bootstrap"),
    "Purged walk-forward": ("walkforward", "walk-forward", "purge", "embargo"),
    "Replay profitability aggregates": (
        "replay_metrics",
        "ce_net",
        "gross_return",
        "expected_cost",
        "realized_cost",
    ),
    "Shadow / replay parity metrics": ("decision_match_rate", "score_match_rate"),
    "Ablation / block-rate metrics": ("block_rate", "ablation"),
}


@dataclass
class FormulaCandidate:
    source_file: str
    function_or_class: str
    target_name: str
    node_kind: str
    line_start: int
    line_end: int
    code_excerpt: str
    plain_text_formula: str
    expr_names: tuple[str, ...]
    numeric_literals: tuple[str, ...]
    context_args: tuple[str, ...]
    class_name: str | None


@dataclass
class FormulaRow:
    formula_id: str
    formula_name: str
    primary_class: str
    secondary_flags: list[str]
    source_file: str
    function_or_class: str
    line_start: int
    line_end: int
    code_excerpt: str
    plain_text_formula: str
    mathematical_family: str
    inputs: list[str]
    outputs: list[str]
    units: str
    window_definition: str
    estimator_type: str
    threshold_or_constant_values: list[str]
    source_doc_refs: list[str]
    tests_covering: list[str]
    consumers: list[str]
    runtime_artifacts_read: list[str]
    runtime_artifacts_written: list[str]
    dashboard_owner_page: str
    display_allowed: str
    display_warning_label: str
    risk_level: str
    audit_verdict: str
    notes: str


class CandidateVisitor(ast.NodeVisitor):
    def __init__(self, source_file: str, source_text: str) -> None:
        self.source_file = source_file
        self.lines = source_text.splitlines()
        self.candidates: list[FormulaCandidate] = []
        self._stack: list[tuple[str, tuple[str, ...], str | None]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._stack.append((node.name, (), node.name))
        self.generic_visit(node)
        self._stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        args = tuple(arg.arg for arg in node.args.args)
        current_class = self._stack[-1][2] if self._stack else None
        self._stack.append((node.name, args, current_class))
        self.generic_visit(node)
        self._stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        args = tuple(arg.arg for arg in node.args.args)
        current_class = self._stack[-1][2] if self._stack else None
        self._stack.append((node.name, args, current_class))
        self.generic_visit(node)
        self._stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        target_name = ", ".join(_target_names(node.targets))
        self._append_candidate(
            target_name=target_name or "<assign>",
            node_kind="assign",
            expr_node=node.value,
            holder_node=node,
        )
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is None:
            return
        self._append_candidate(
            target_name=_target_name(node.target) or "<annassign>",
            node_kind="annassign",
            expr_node=node.value,
            holder_node=node,
        )
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        op_name = type(node.op).__name__.lower()
        try:
            formula = f"{ast.unparse(node.target)} {op_name}= {ast.unparse(node.value)}"
        except Exception:
            formula = op_name
        self._append_candidate(
            target_name=_target_name(node.target) or "<augassign>",
            node_kind="augassign",
            expr_node=node.value,
            holder_node=node,
            formula_override=formula,
        )
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        if node.value is None:
            return
        self._append_candidate(
            target_name="return",
            node_kind="return",
            expr_node=node.value,
            holder_node=node,
        )
        self.generic_visit(node)

    def _append_candidate(
        self,
        *,
        target_name: str,
        node_kind: str,
        expr_node: ast.AST,
        holder_node: ast.AST,
        formula_override: str | None = None,
    ) -> None:
        if not _is_relevant_candidate(expr_node, target_name=target_name):
            return
        function_or_class = ".".join(item[0] for item in self._stack) or "<module>"
        context_args = self._stack[-1][1] if self._stack else ()
        class_name = self._stack[-1][2] if self._stack else None
        line_start = getattr(holder_node, "lineno", getattr(expr_node, "lineno", 1))
        line_end = getattr(
            holder_node, "end_lineno", getattr(expr_node, "end_lineno", line_start)
        )
        code_excerpt = _code_excerpt(self.lines, line_start, line_end)
        plain_text_formula = formula_override or _safe_unparse(expr_node)
        expr_names = tuple(sorted(_expression_names(expr_node)))
        numeric_literals = tuple(sorted(_numeric_literals(expr_node)))
        self.candidates.append(
            FormulaCandidate(
                source_file=self.source_file,
                function_or_class=function_or_class,
                target_name=target_name,
                node_kind=node_kind,
                line_start=line_start,
                line_end=line_end,
                code_excerpt=code_excerpt,
                plain_text_formula=plain_text_formula,
                expr_names=expr_names,
                numeric_literals=numeric_literals,
                context_args=context_args,
                class_name=class_name,
            )
        )


def _target_names(targets: Iterable[ast.AST]) -> list[str]:
    names: list[str] = []
    for target in targets:
        name = _target_name(target)
        if name:
            names.append(name)
    return names


def _target_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Tuple):
        return ", ".join(_target_name(item) for item in node.elts if _target_name(item))
    return ""


def _safe_unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return type(node).__name__


def _code_excerpt(lines: list[str], line_start: int, line_end: int) -> str:
    start = max(line_start - 1, 0)
    end = min(line_end, len(lines))
    excerpt = "\n".join(lines[start:end]).strip()
    return excerpt[:500]


def _expression_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for item in ast.walk(node):
        if isinstance(item, ast.Name):
            names.add(item.id)
        elif isinstance(item, ast.Attribute):
            names.add(item.attr)
    return names


def _numeric_literals(node: ast.AST) -> set[str]:
    values: set[str] = set()
    for item in ast.walk(node):
        if isinstance(item, ast.Constant) and isinstance(item.value, (int, float)):
            values.add(repr(item.value))
    return values


def _is_math_call(node: ast.Call) -> bool:
    func_name = _safe_unparse(node.func).split(".")[-1]
    return func_name in MATH_CALL_NAMES


def _contains_bool_constant(node: ast.AST) -> bool:
    return any(
        isinstance(item, ast.Constant) and isinstance(item.value, bool)
        for item in ast.walk(node)
    )


def _is_text_only(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(_is_text_only(item) for item in node.elts)
    if isinstance(node, ast.Dict):
        keys = [key for key in node.keys if key is not None]
        return all(_is_text_only(key) for key in keys) and all(
            _is_text_only(value) for value in node.values
        )
    return False


def _is_constant_numeric(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return _is_constant_numeric(node.operand)
    return False


def _has_math_expression(node: ast.AST | None) -> bool:
    if node is None:
        return False
    for item in ast.walk(node):
        if isinstance(
            item,
            (
                ast.BinOp,
                ast.UnaryOp,
                ast.Compare,
                ast.BoolOp,
                ast.IfExp,
                ast.GeneratorExp,
                ast.ListComp,
                ast.DictComp,
                ast.SetComp,
            ),
        ):
            return True
        if isinstance(item, ast.Call) and _is_math_call(item):
            return True
    return False


def _looks_like_field_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and _safe_unparse(node.func).split(".")[-1] == "Field"


def _field_default_value(node: ast.Call) -> str | None:
    for keyword in node.keywords:
        if keyword.arg == "default":
            return _safe_unparse(keyword.value)
    if node.args:
        return _safe_unparse(node.args[0])
    return None


def _is_status_name(name: str) -> bool:
    lowered = name.lower()
    return lowered.startswith(("is_", "has_", "can_", "should_", "passes_")) or any(
        keyword in lowered for keyword in STATUS_KEYWORDS
    )


def _is_threshold_name(name: str) -> bool:
    lowered = name.lower()
    return lowered.isupper() or any(keyword in lowered for keyword in THRESHOLD_KEYWORDS)


def _is_text_name(name: str) -> bool:
    lowered = name.lower()
    return any(keyword in lowered for keyword in TEXT_LIST_HINTS)


def _is_relevant_candidate(node: ast.AST, *, target_name: str) -> bool:
    if _looks_like_field_call(node):
        return True
    if _is_text_only(node) or _contains_bool_constant(node):
        return True
    if _is_constant_numeric(node) and (_is_threshold_name(target_name) or target_name != "return"):
        return True
    if _has_math_expression(node):
        return True
    return False


def collect_source_files(repo_root: Path) -> list[Path]:
    files: set[Path] = set()
    include_dirs = [
        "src/calibration_methods",
        "src/calibration_loader",
        "src/local_replay_runtime",
        "src/engines",
        "src/execution_backbone",
        "src/venue_adapters",
        "src/risk_backbone",
        "src/scoring_backbone",
        "src/portfolio",
        "src/portfolio_minimal",
        "src/sharia_compliance",
        "src/meta_learning",
        "src/meta_minimal",
        "src/monitoring",
    ]
    for rel_dir in include_dirs:
        root_dir = repo_root / rel_dir
        if root_dir.is_dir():
            files.update(path for path in root_dir.rglob("*.py"))

    explicit_patterns = [
        "src/interface_contracts/*ml*.py",
        "src/interface_contracts/*regime*.py",
        "src/data_backbone/microstructure/*.py",
        "src/data_backbone/market_physics_math.py",
        "src/data_backbone/*freshness*.py",
        "src/data_backbone/*consistency*.py",
        "src/data_backbone/*pair_health*.py",
        "src/complete_enablers/*order*.py",
        "src/complete_enablers/*lob*.py",
        "src/complete_enablers/*toxicity*.py",
        "src/complete_enablers/*fragility*.py",
        "src/complete_enablers/*entry*.py",
        "src/complete_enablers/*exit*.py",
        "src/cockpit/state*.py",
    ]
    for pattern in explicit_patterns:
        files.update(repo_root.glob(pattern))

    return sorted(file for file in files if file.suffix in SOURCE_EXTENSIONS)


def collect_doc_files(repo_root: Path) -> list[Path]:
    docs: set[Path] = set()
    for rel_dir in [
        "docs/backtest",
        "docs/chatgpt",
        "docs/production_deployment_plan/update_audit",
        "docs/audit/chatgpt_upload",
        "docs/audit/p0a_orphan_resolution",
    ]:
        root_dir = repo_root / rel_dir
        if root_dir.is_dir():
            for path in root_dir.rglob("*"):
                if path.suffix.lower() in DOC_EXTENSIONS:
                    docs.add(path)
    return sorted(docs)


def collect_test_files(repo_root: Path) -> list[Path]:
    test_root = repo_root / "tests"
    if not test_root.is_dir():
        return []
    return sorted(path for path in test_root.rglob("*.py"))


def build_import_graph(
    source_files: list[Path], test_files: list[Path], repo_root: Path
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    all_python = {path: path for path in source_files + test_files}
    aliases: defaultdict[str, set[str]] = defaultdict(set)
    for path in all_python:
        rel = path.relative_to(repo_root).as_posix()
        if rel.startswith("src/"):
            parts = rel[4:].split("/")
            if parts[-1] == "__init__.py":
                mod = ".".join(parts[:-1])
            else:
                mod = ".".join(parts)[:-3]
            aliases[mod].add(rel)
            aliases["src." + mod].add(rel)
        elif rel.startswith("tests/"):
            mod = rel[:-3].replace("/", ".")
            aliases[mod].add(rel)
        elif rel.startswith("scripts/"):
            mod = rel[:-3].replace("/", ".")
            aliases[mod].add(rel)

    def resolve_module(name: str | None) -> str | None:
        if not name:
            return None
        if name in aliases:
            return sorted(aliases[name])[0]
        parts = name.split(".")
        for index in range(len(parts), 0, -1):
            prefix = ".".join(parts[:index])
            if prefix in aliases:
                return sorted(aliases[prefix])[0]
        return None

    imports: defaultdict[str, set[str]] = defaultdict(set)
    imported_by: defaultdict[str, set[str]] = defaultdict(set)
    for path in all_python:
        rel = path.relative_to(repo_root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(text)
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = resolve_module(alias.name)
                    if target:
                        imports[rel].add(target)
                        imported_by[target].add(rel)
            elif isinstance(node, ast.ImportFrom):
                target = resolve_module(node.module or "")
                if target:
                    imports[rel].add(target)
                    imported_by[target].add(rel)
    return imports, imported_by


def classify_owner_page(rel_path: str) -> str:
    lowered = rel_path.lower()
    if rel_path.startswith("src/cockpit/"):
        if "lab" in lowered:
            return "IA Lab"
        if any(token in lowered for token in ("service", "queue", "liveness", "disk", "vps")):
            return "VPS"
        if any(token in lowered for token in ("warmup", "shadow", "verdict")):
            return "Shadow"
        if any(token in lowered for token in ("feature_bridge", "engine", "replay_metrics", "sizing", "economic")):
            return "Trading"
        if "observability" in lowered:
            return "Observability"
        return "Overview"
    if rel_path.startswith("src/monitoring/"):
        return "Observability"
    if rel_path.startswith("src/calibration_methods/"):
        if any(token in lowered for token in ("ml_", "regime_detector")):
            return "IA Lab"
        return "Backtest"
    if rel_path.startswith("src/local_replay_runtime/"):
        if any(token in lowered for token in ("local_lab_", "ml_", "regime_detector")):
            return "IA Lab"
        if "live_complete_operator_audit_report" in lowered:
            return "VPS"
        return "Backtest"
    if rel_path.startswith("src/backtest_artifact_import/"):
        if any(token in lowered for token in ("upload", "transport", "ml_model", "regime_detector")):
            return "IA Lab"
        if "monitoring_projection" in lowered:
            return "Observability"
        return "Backtest"
    if rel_path.startswith("src/engines/"):
        return "Trading"
    if rel_path.startswith("src/execution_backbone/"):
        if any(token in lowered for token in ("fill_", "reconciliation", "runtime", "breaker", "rate_limiter")):
            return "VPS"
        return "Trading"
    if rel_path.startswith("src/venue_adapters/") or rel_path.startswith("src/secrets_manager/"):
        return "VPS"
    if rel_path.startswith("src/data_backbone/microstructure/") or rel_path.endswith(
        "market_physics_math.py"
    ):
        return "Trading"
    if rel_path.startswith("src/risk_backbone/"):
        return "VPS" if "runtime" in lowered else "Trading"
    if rel_path.startswith("src/scoring_backbone/"):
        return "Trading"
    if rel_path.startswith("src/portfolio_minimal/") or rel_path.startswith("src/sharia_compliance/"):
        return "Trading"
    if rel_path.startswith("src/meta_learning/") or rel_path.startswith("src/meta_minimal/"):
        return "IA Lab"
    if rel_path.startswith("src/complete_enablers/"):
        if any(token in lowered for token in ("ml_", "promotion", "regime_detector")):
            return "IA Lab"
        return "Trading"
    return "Overview"


def family_from_file(rel_path: str) -> tuple[str, str, str | None]:
    if rel_path in FILE_CLASS_OVERRIDES:
        family, estimator, primary = FILE_CLASS_OVERRIDES[rel_path]
        return family, estimator, primary

    lowered = rel_path.lower()
    name = Path(rel_path).stem.lower()
    if rel_path.startswith("src/data_backbone/microstructure/"):
        return name.replace("_", " "), "microstructure_estimator", "MICROSTRUCTURE_ESTIMATOR"
    if rel_path.startswith("src/calibration_methods/"):
        if any(token in lowered for token in ("ml_", "regime_detector")):
            return name.replace("_", " "), "ml_transform", "ML_LABEL_OR_FEATURE_TRANSFORM"
        return name.replace("_", " "), "statistical_anchor", "STATISTICAL_ANCHOR"
    if rel_path.startswith("src/execution_backbone/") or rel_path.startswith("src/venue_adapters/"):
        return name.replace("_", " "), "execution_formula", "EXECUTION_COST_FORMULA"
    if rel_path.startswith("src/risk_backbone/") or rel_path.startswith("src/scoring_backbone/"):
        return name.replace("_", " "), "risk_or_score_formula", "RISK_SIZING_FORMULA"
    if rel_path.startswith("src/portfolio_minimal/") or rel_path.startswith("src/sharia_compliance/"):
        return name.replace("_", " "), "portfolio_gate_formula", "RISK_SIZING_FORMULA"
    if rel_path.startswith("src/meta_learning/") or rel_path.startswith("src/meta_minimal/"):
        return name.replace("_", " "), "ml_transform", "ML_LABEL_OR_FEATURE_TRANSFORM"
    if rel_path.startswith("src/local_replay_runtime/"):
        if any(token in lowered for token in ("local_lab_", "ml_", "regime_detector")):
            return name.replace("_", " "), "ml_transform", "ML_LABEL_OR_FEATURE_TRANSFORM"
        return name.replace("_", " "), "replay_metric", "REAL_QUANT_FORMULA"
    if rel_path.startswith("src/cockpit/") or rel_path.startswith("src/monitoring/"):
        return name.replace("_", " "), "operational_diagnostic", "OPERATIONAL_DIAGNOSTIC"
    if rel_path.startswith("src/complete_enablers/"):
        if any(token in lowered for token in ("toxicity", "fragility", "lob", "order_book", "entry", "exit")):
            return name.replace("_", " "), "microstructure_estimator", "MICROSTRUCTURE_ESTIMATOR"
        if any(token in lowered for token in ("ml_", "regime_detector")):
            return name.replace("_", " "), "ml_transform", "ML_LABEL_OR_FEATURE_TRANSFORM"
        return name.replace("_", " "), "real_quant_formula", "REAL_QUANT_FORMULA"
    return name.replace("_", " "), "formula", None


def classify_candidate(
    candidate: FormulaCandidate,
    *,
    owner_page: str,
    file_ledger_status: str,
) -> tuple[str, str, str]:
    rel_path = candidate.source_file
    target_name = candidate.target_name
    expression = candidate.plain_text_formula
    parsed_expression = _parse_expr(expression) if expression else None
    family, estimator, suggested = family_from_file(rel_path)
    lowered_target = target_name.lower()
    lowered_expr = expression.lower()

    if candidate.node_kind in {"assign", "annassign"} and _is_text_name(target_name) and (
        "[" in expression or "'" in expression or '"' in expression
    ):
        return "TEXT_OR_LIST", family, estimator
    if _looks_like_field_call(parsed_expression) if parsed_expression is not None else False:
        return "PYDANTIC_FIELD", family, estimator
    if "field(" in lowered_expr and candidate.class_name:
        return "PYDANTIC_FIELD", family, estimator
    if _is_status_name(target_name) or any(
        token in lowered_expr for token in (" is ", " not ", ">= ", "<= ", " == ", " != ")
    ) and any(keyword in lowered_target for keyword in STATUS_KEYWORDS):
        return "STATUS_FLAG", family, estimator
    if _is_text_only(parsed_expression) if parsed_expression is not None else False:
        return "TEXT_OR_LIST", family, estimator
    if _is_threshold_name(target_name) and candidate.numeric_literals:
        return "THRESHOLD_CONSTANT", family, estimator
    if suggested == "OPERATIONAL_DIAGNOSTIC":
        if any(metric in lowered_target for metric in FALSE_GREEN_METRIC_HINTS) and any(
            op in lowered_expr for op in ("/", "+", "-", "*", "sum(", "mean(", "round(")
        ):
            return "REAL_QUANT_FORMULA", family, estimator
        return "OPERATIONAL_DIAGNOSTIC", family, estimator
    if suggested == "MICROSTRUCTURE_ESTIMATOR":
        return "MICROSTRUCTURE_ESTIMATOR", family, estimator
    if suggested == "STATISTICAL_ANCHOR":
        return "STATISTICAL_ANCHOR", family, estimator
    if suggested == "EXECUTION_COST_FORMULA":
        return "EXECUTION_COST_FORMULA", family, estimator
    if suggested == "RISK_SIZING_FORMULA":
        return "RISK_SIZING_FORMULA", family, estimator
    if suggested == "ML_LABEL_OR_FEATURE_TRANSFORM":
        return "ML_LABEL_OR_FEATURE_TRANSFORM", family, estimator

    if rel_path.startswith("src/cockpit/") or rel_path.startswith("src/monitoring/"):
        return "REPORT_VALUE" if "payload" in lowered_expr or ".get(" in lowered_expr else "OPERATIONAL_DIAGNOSTIC", family, estimator
    if not _has_math_expression(parsed_expression) if expression else True:
        if candidate.numeric_literals and target_name:
            return "THRESHOLD_CONSTANT", family, estimator
        return "FALSE_POSITIVE", family, estimator
    return "REAL_QUANT_FORMULA", family, estimator


def _parse_expr(expression: str) -> ast.AST | None:
    try:
        return ast.parse(expression, mode="eval").body
    except Exception:
        return None


def build_test_index(test_files: list[Path], repo_root: Path) -> dict[str, dict[str, object]]:
    index: dict[str, dict[str, object]] = {}
    for path in test_files:
        rel = path.relative_to(repo_root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        test_names: list[str] = []
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    test_names.append(node.name)
        except Exception:
            pass
        index[rel] = {
            "text": text.lower(),
            "test_names": tuple(sorted(test_names)),
            "has_fixture": "@pytest.fixture" in text or "fixture(" in text,
        }
    return index


def build_doc_index(doc_files: list[Path], repo_root: Path) -> dict[str, str]:
    return {
        path.relative_to(repo_root).as_posix(): path.read_text(
            encoding="utf-8", errors="ignore"
        ).lower()
        for path in doc_files
    }


def detect_runtime_artifacts(rel_path: str, ledger_row: dict[str, object]) -> tuple[list[str], list[str]]:
    reads = set(ledger_row.get("runtime_files_read", []) or [])
    writes = set()
    overrides = RUNTIME_ARTIFACT_OVERRIDES.get(rel_path, {})
    reads.update(overrides.get("read", []))
    writes.update(overrides.get("write", []))
    clean_reads = sorted(item for item in reads if " " not in item)
    clean_writes = sorted(item for item in writes if " " not in item)
    return clean_reads, clean_writes


def source_doc_refs_for_row(
    row: FormulaRow,
    *,
    doc_index: dict[str, str],
    source_text: str,
) -> list[str]:
    refs: list[str] = []
    for line in source_text.splitlines():
        if "doi" in line.lower() or line.strip().startswith("Reference:"):
            refs.append(f"{row.source_file}::docstring::{line.strip()}")
            if len(refs) >= 2:
                break

    keywords = list(DOC_HINTS.get(row.mathematical_family, ()))
    keywords.extend(
        keyword
        for keyword in (
            Path(row.source_file).stem.lower(),
            row.function_or_class.split(".")[-1].lower(),
            row.formula_name.lower(),
        )
        if keyword
    )
    seen: set[str] = set()
    for doc_rel, doc_text in doc_index.items():
        hits = 0
        for keyword in keywords:
            needle = keyword.strip().lower()
            if needle and needle in doc_text:
                hits += 1
        if hits:
            seen.add(doc_rel)
        if len(seen) >= 5:
            break
    refs.extend(sorted(seen))
    return refs[:5]


def tests_for_row(
    row: FormulaRow,
    *,
    test_index: dict[str, dict[str, object]],
) -> list[str]:
    source_stem = Path(row.source_file).stem.lower()
    symbol = row.function_or_class.split(".")[-1].lower()
    extra = row.formula_name.lower()
    matches: list[str] = []
    for test_rel, payload in test_index.items():
        text = payload["text"]
        file_match = source_stem in test_rel.lower()
        symbol_match = symbol and symbol in text
        name_match = extra and extra in text and extra not in {"return", "<module>"}
        if file_match or symbol_match or name_match:
            matches.append(test_rel)
    return sorted(matches)[:8]


def consumer_refs_for_row(
    row: FormulaRow,
    *,
    imported_by: dict[str, set[str]],
) -> list[str]:
    consumers = sorted(
        path
        for path in imported_by.get(row.source_file, set())
        if not path.startswith("tests/")
    )
    return consumers[:8]


def infer_units(row: FormulaRow) -> str:
    text = f"{row.formula_name} {row.plain_text_formula}".lower()
    if "timestamp_ns" in text or text.endswith("_ns"):
        return "nanoseconds"
    if "seconds" in text or "_s" in text:
        return "seconds"
    if "bps" in text:
        return "bps"
    if "price" in text:
        return "price"
    if any(token in text for token in ("volume", "size", "qty")):
        return "quantity"
    if any(token in text for token in ("sharpe", "psr", "dsr", "vpin", "pin", "ratio", "probability", "coverage")):
        return "ratio"
    if "return" in text or "ce_net" in text:
        return "return units"
    if "lambda" in text:
        return "price change per signed volume"
    if "vol" in text or "variance" in text:
        return "volatility / variance"
    return "unknown"


def infer_window_definition(row: FormulaRow) -> str:
    window_tokens = [
        token
        for token in (*row.inputs, row.plain_text_formula)
        if any(
            hint in token.lower()
            for hint in ("window", "bucket", "bandwidth", "lag", "fold", "period", "lookback", "horizon", "sample")
        )
    ]
    if not window_tokens:
        return "n/a"
    return ", ".join(dict.fromkeys(window_tokens))


def infer_threshold_values(candidate: FormulaCandidate) -> list[str]:
    return list(candidate.numeric_literals)[:8]


def secondary_flags_for_row(
    row: FormulaRow,
    *,
    file_status: str,
    source_text: str,
) -> list[str]:
    flags: list[str] = []
    formula_lower = row.plain_text_formula.lower()
    name_lower = row.formula_name.lower()
    measured_context = any(
        token in row.source_file.lower()
        for token in (
            "metrics_collector",
            "artifact_exporter",
            "collector",
            "reporter",
            "projection",
            "summary",
            "bundle",
            "monitoring_payload",
            "parity",
            "telemetry",
            "aggregator",
        )
    ) or bool(row.runtime_artifacts_written)
    if "field(" in formula_lower or row.primary_class == "PYDANTIC_FIELD":
        flags.append("PLACEHOLDER_DEFAULT" if "default=0.0" in formula_lower else "HARD_CODED_THRESHOLD")
    if any(formula_lower.strip() == literal for literal in ("0.0", "0", "false", "true")) or (
        any(hint in name_lower for hint in FALSE_GREEN_METRIC_HINTS) and formula_lower.strip() in {"0.0", "0"}
    ):
        flags.append("PLACEHOLDER_DEFAULT")
    if row.primary_class in REAL_CLASSES and measured_context and "PLACEHOLDER_DEFAULT" not in flags:
        flags.append("REAL_MEASURED_VALUE")
    if row.primary_class == "REPORT_VALUE":
        flags.append("REPORT_LOADED_VALUE")
    if file_status in {"coded_not_displayed", "runtime_only", "orphan_candidate"}:
        flags.append("CODED_NOT_DISPLAYED")
    if row.tests_covering:
        flags.append("TEST_COVERED")
    else:
        flags.append("TEST_MISSING")
    if row.source_doc_refs:
        flags.append("DOC_SOURCE_FOUND")
    else:
        flags.append("DOC_SOURCE_MISSING")
    if row.consumers:
        flags.append("CONSUMER_PROVEN")
    else:
        flags.append("NO_CONSUMER_PROVEN")
    if row.units == "unknown" and row.primary_class in REAL_CLASSES | {"EXECUTION_COST_FORMULA", "RISK_SIZING_FORMULA"}:
        flags.append("UNIT_MISSING")
    if row.window_definition == "n/a" and row.primary_class in {
        "MICROSTRUCTURE_ESTIMATOR",
        "STATISTICAL_ANCHOR",
        "EXECUTION_COST_FORMULA",
        "ML_LABEL_OR_FEATURE_TRANSFORM",
    }:
        flags.append("WINDOW_MISSING")
    if row.primary_class == "THRESHOLD_CONSTANT":
        flags.append("HARD_CODED_THRESHOLD")
        if "config/" not in row.plain_text_formula.lower() and "loader" not in row.source_file:
            flags.append("THRESHOLD_UNCALIBRATED")
    if any(hint in name_lower for hint in FALSE_GREEN_METRIC_HINTS) and "PLACEHOLDER_DEFAULT" in flags:
        flags.append("DASHBOARD_FALSE_GREEN_RISK")
    if row.primary_class == "ML_LABEL_OR_FEATURE_TRANSFORM":
        lowered = source_text.lower()
        has_split_guard = any(token in lowered for token in ("purge", "embargo", "train", "validation", "test split", "walkforward"))
        has_target = any(token in lowered for token in ("target", "label", "future", "next_", "horizon"))
        if not has_split_guard:
            flags.append("LEAKAGE_PROOF_MISSING")
        if has_target and not has_split_guard:
            flags.append("LOOKAHEAD_RISK")
    if row.source_file.endswith("multiple_testing_guard.py") or row.source_file.endswith("stationarity.py"):
        flags.append("HUMAN_DECISION_REQUIRED")
    if row.source_file.endswith("pot_gpd.py") and not row.source_doc_refs:
        flags.append("MATH_ANCHOR_BLOCKED")
    return sorted(dict.fromkeys(flag for flag in flags if flag))


def display_policy(row: FormulaRow) -> tuple[str, str]:
    if row.primary_class in REAL_CLASSES:
        label = "source_label_only"
        if "PLACEHOLDER_DEFAULT" in row.secondary_flags:
            label = "placeholder_not_measured"
        return "source_label_only", label
    if row.primary_class == "REPORT_VALUE":
        label = "report_loaded_value"
        if "DASHBOARD_FALSE_GREEN_RISK" in row.secondary_flags:
            label = "false_green_risk"
        return "report_value_only", label
    if row.primary_class == "OPERATIONAL_DIAGNOSTIC":
        return "yes", "operational_diagnostic"
    return "no", "not_displayable"


def risk_level(row: FormulaRow) -> str:
    if row.primary_class in {
        "MICROSTRUCTURE_ESTIMATOR",
        "STATISTICAL_ANCHOR",
        "EXECUTION_COST_FORMULA",
        "RISK_SIZING_FORMULA",
    }:
        return "P0"
    if row.primary_class in {"REAL_QUANT_FORMULA", "ML_LABEL_OR_FEATURE_TRANSFORM", "OPERATIONAL_DIAGNOSTIC"}:
        return "P1"
    return "P2"


def audit_verdict(row: FormulaRow) -> str:
    flags = set(row.secondary_flags)
    if "LOOKAHEAD_RISK" in flags or "LEAKAGE_PROOF_MISSING" in flags:
        return "LEAKAGE_RISK_UNPROVEN"
    if "PLACEHOLDER_DEFAULT" in flags:
        return "PLACEHOLDER_NOT_MEASURED"
    if "NO_CONSUMER_PROVEN" in flags:
        return "MISSING_CONSUMER_PROOF"
    if "TEST_MISSING" in flags:
        return "MISSING_TESTS"
    if "DOC_SOURCE_MISSING" in flags:
        return "MISSING_DOC_SOURCE"
    if "HUMAN_DECISION_REQUIRED" in flags:
        return "NEEDS_HUMAN_AUDIT"
    return "OK_SOURCE_MAPPED"


def formula_id(row: FormulaRow) -> str:
    symbol = row.function_or_class.replace(".", "::")
    name = re.sub(r"[^A-Za-z0-9_]+", "_", row.formula_name)
    return f"{row.source_file}:{symbol}:{name}:{row.line_start}"


def build_rows(repo_root: Path) -> tuple[list[FormulaRow], dict[str, str]]:
    file_ledger = {}
    ledger_path = repo_root / "docs" / "cockpit" / "discovery_artifacts" / "file_source_ledger.json"
    if ledger_path.is_file():
        raw = json.loads(ledger_path.read_text(encoding="utf-8"))
        file_ledger = {row["file_path"]: row for row in raw}

    source_files = collect_source_files(repo_root)
    test_files = collect_test_files(repo_root)
    doc_files = collect_doc_files(repo_root)
    doc_index = build_doc_index(doc_files, repo_root)
    test_index = build_test_index(test_files, repo_root)
    imports, imported_by = build_import_graph(source_files, test_files, repo_root)

    rows: list[FormulaRow] = []
    source_cache: dict[str, str] = {}
    for path in source_files:
        rel = path.relative_to(repo_root).as_posix()
        source_text = path.read_text(encoding="utf-8", errors="ignore")
        source_cache[rel] = source_text
        visitor = CandidateVisitor(rel, source_text)
        try:
            visitor.visit(ast.parse(source_text))
        except Exception:
            continue
        owner_page = classify_owner_page(rel)
        ledger_row = file_ledger.get(rel, {})
        file_status = str(ledger_row.get("status", "unknown"))
        runtime_reads, runtime_writes = detect_runtime_artifacts(rel, ledger_row)

        for candidate in visitor.candidates:
            primary_class, family, estimator = classify_candidate(
                candidate,
                owner_page=owner_page,
                file_ledger_status=file_status,
            )
            if primary_class == "FALSE_POSITIVE" and not candidate.numeric_literals:
                continue
            formula_name = (
                candidate.target_name
                if candidate.target_name != "return"
                else candidate.function_or_class.split(".")[-1]
            )
            tests_covering = tests_for_row(
                FormulaRow(
                    formula_id="",
                    formula_name=formula_name,
                    primary_class=primary_class,
                    secondary_flags=[],
                    source_file=rel,
                    function_or_class=candidate.function_or_class,
                    line_start=candidate.line_start,
                    line_end=candidate.line_end,
                    code_excerpt=candidate.code_excerpt,
                    plain_text_formula=candidate.plain_text_formula,
                    mathematical_family=family,
                    inputs=[],
                    outputs=[],
                    units="",
                    window_definition="",
                    estimator_type=estimator,
                    threshold_or_constant_values=[],
                    source_doc_refs=[],
                    tests_covering=[],
                    consumers=[],
                    runtime_artifacts_read=[],
                    runtime_artifacts_written=[],
                    dashboard_owner_page=owner_page,
                    display_allowed="",
                    display_warning_label="",
                    risk_level="",
                    audit_verdict="",
                    notes="",
                ),
                test_index=test_index,
            )
            consumers = consumer_refs_for_row(
                FormulaRow(
                    formula_id="",
                    formula_name=formula_name,
                    primary_class=primary_class,
                    secondary_flags=[],
                    source_file=rel,
                    function_or_class=candidate.function_or_class,
                    line_start=candidate.line_start,
                    line_end=candidate.line_end,
                    code_excerpt=candidate.code_excerpt,
                    plain_text_formula=candidate.plain_text_formula,
                    mathematical_family=family,
                    inputs=[],
                    outputs=[],
                    units="",
                    window_definition="",
                    estimator_type=estimator,
                    threshold_or_constant_values=[],
                    source_doc_refs=[],
                    tests_covering=[],
                    consumers=[],
                    runtime_artifacts_read=[],
                    runtime_artifacts_written=[],
                    dashboard_owner_page=owner_page,
                    display_allowed="",
                    display_warning_label="",
                    risk_level="",
                    audit_verdict="",
                    notes="",
                ),
                imported_by=imported_by,
            )

            outputs = [formula_name]
            inputs = sorted(
                name
                for name in candidate.expr_names
                if name != formula_name and name not in {"True", "False", "None"}
            )[:12]
            row = FormulaRow(
                formula_id="",
                formula_name=formula_name,
                primary_class=primary_class,
                secondary_flags=[],
                source_file=rel,
                function_or_class=candidate.function_or_class,
                line_start=candidate.line_start,
                line_end=candidate.line_end,
                code_excerpt=candidate.code_excerpt,
                plain_text_formula=candidate.plain_text_formula,
                mathematical_family=family,
                inputs=inputs or list(candidate.context_args),
                outputs=outputs,
                units="",
                window_definition="",
                estimator_type=estimator,
                threshold_or_constant_values=infer_threshold_values(candidate),
                source_doc_refs=[],
                tests_covering=tests_covering,
                consumers=consumers,
                runtime_artifacts_read=runtime_reads,
                runtime_artifacts_written=runtime_writes,
                dashboard_owner_page=owner_page,
                display_allowed="",
                display_warning_label="",
                risk_level="",
                audit_verdict="",
                notes="",
            )
            row.units = infer_units(row)
            row.window_definition = infer_window_definition(row)
            row.source_doc_refs = source_doc_refs_for_row(
                row,
                doc_index=doc_index,
                source_text=source_text,
            )
            row.secondary_flags = secondary_flags_for_row(
                row,
                file_status=file_status,
                source_text=source_text,
            )
            row.display_allowed, row.display_warning_label = display_policy(row)
            row.risk_level = risk_level(row)
            row.audit_verdict = audit_verdict(row)
            row.notes = build_notes(row)
            row.formula_id = formula_id(row)
            rows.append(row)

    rows.sort(key=lambda item: (item.source_file, item.line_start, item.formula_name))
    return rows, source_cache


def build_notes(row: FormulaRow) -> str:
    note_bits = [
        f"class={row.primary_class}",
        f"owner={row.dashboard_owner_page}",
        f"estimator={row.estimator_type}",
    ]
    if row.tests_covering:
        note_bits.append(f"tests={len(row.tests_covering)}")
    if row.consumers:
        note_bits.append(f"consumers={len(row.consumers)}")
    if row.runtime_artifacts_read or row.runtime_artifacts_written:
        note_bits.append("artifact_linked")
    return "; ".join(note_bits)


def write_csv(rows: list[FormulaRow], output_path: Path) -> None:
    fieldnames = list(asdict(rows[0]).keys()) if rows else [
        "formula_id",
        "formula_name",
        "primary_class",
        "secondary_flags",
        "source_file",
        "function_or_class",
        "line_start",
        "line_end",
        "code_excerpt",
        "plain_text_formula",
        "mathematical_family",
        "inputs",
        "outputs",
        "units",
        "window_definition",
        "estimator_type",
        "threshold_or_constant_values",
        "source_doc_refs",
        "tests_covering",
        "consumers",
        "runtime_artifacts_read",
        "runtime_artifacts_written",
        "dashboard_owner_page",
        "display_allowed",
        "display_warning_label",
        "risk_level",
        "audit_verdict",
        "notes",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            payload = asdict(row)
            for key, value in payload.items():
                if isinstance(value, list):
                    payload[key] = " | ".join(str(item) for item in value)
            writer.writerow(payload)


def write_json(rows: list[FormulaRow], output_path: Path) -> None:
    output_path.write_text(
        json.dumps([asdict(row) for row in rows], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_master_md(rows: list[FormulaRow], output_path: Path) -> None:
    lines = [
        "# P0-B Formula Master Ledger\n",
        f"Total rows: {len(rows)}\n\n",
        "| Formula ID | Formula Name | Class | Flags | Source | Symbol | Start | End | Code Excerpt | Plain Formula | Family | Inputs | Outputs | Units | Window | Estimator | Thresholds | Source Docs | Tests | Consumers | Runtime Read | Runtime Write | Owner Page | Display Allowed | Display Warning | Risk | Verdict | Notes |\n",
        "|---|---|---|---|---|---|---:|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n",
    ]
    for row in rows:
        flags = ", ".join(row.secondary_flags)
        lines.append(
            f"| `{_md(row.formula_id)}` | `{_md(row.formula_name)}` | {row.primary_class} | {_md(flags)} | "
            f"`{_md(row.source_file)}` | `{_md(row.function_or_class)}` | {row.line_start} | {row.line_end} | "
            f"{_md(row.code_excerpt)} | {_md(row.plain_text_formula)} | {_md(row.mathematical_family)} | "
            f"{_md(', '.join(row.inputs))} | {_md(', '.join(row.outputs))} | {_md(row.units)} | "
            f"{_md(row.window_definition)} | {_md(row.estimator_type)} | {_md(', '.join(row.threshold_or_constant_values))} | "
            f"{_md(', '.join(row.source_doc_refs))} | {_md(', '.join(row.tests_covering))} | {_md(', '.join(row.consumers))} | "
            f"{_md(', '.join(row.runtime_artifacts_read))} | {_md(', '.join(row.runtime_artifacts_written))} | "
            f"{row.dashboard_owner_page} | {_md(row.display_allowed)} | {_md(row.display_warning_label)} | "
            f"{row.risk_level} | {row.audit_verdict} | {_md(row.notes)} |\n"
        )
    output_path.write_text("".join(lines), encoding="utf-8")


def _md(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", "<br>")


def write_filtered_bank(
    rows: list[FormulaRow],
    *,
    allowed_classes: set[str],
    title: str,
    output_path: Path,
) -> None:
    filtered = [row for row in rows if row.primary_class in allowed_classes]
    counts = Counter(row.mathematical_family for row in filtered)
    lines = [
        f"# {title}\n",
        f"Rows: {len(filtered)}\n\n",
        "## Family Counts\n",
    ]
    for family, count in counts.most_common():
        lines.append(f"- `{family}`: {count}\n")
    lines.append(
        "\n| Formula | Class | Source | Symbol | Tests | Consumers | Warnings |\n|---|---|---|---|---|---|---|\n"
    )
    for row in filtered:
        warnings = ", ".join(
            flag
            for flag in row.secondary_flags
            if flag
            in {
                "TEST_MISSING",
                "DOC_SOURCE_MISSING",
                "NO_CONSUMER_PROVEN",
                "LOOKAHEAD_RISK",
                "LEAKAGE_PROOF_MISSING",
                "PLACEHOLDER_DEFAULT",
            }
        )
        lines.append(
            f"| `{_md(row.formula_name)}` | {row.primary_class} | `{_md(row.source_file)}` | "
            f"`{_md(row.function_or_class)}` | {_md(', '.join(row.tests_covering) or 'none')} | "
            f"{_md(', '.join(row.consumers) or 'none')} | {_md(warnings or 'none')} |\n"
        )
    output_path.write_text("".join(lines), encoding="utf-8")


def write_family_bank(rows: list[FormulaRow], *, title: str, families: list[str], output_path: Path) -> None:
    family_rows = [row for row in rows if row.mathematical_family in families]
    lines = [f"# {title}\n"]
    for family in families:
        subset = [row for row in family_rows if row.mathematical_family == family]
        lines.append(f"\n## {family}\n")
        if not subset:
            lines.append("No extracted rows.\n")
            continue
        lines.append(
            "| Formula | Class | Source | Symbol | Plain Formula | Tests | Docs | Consumers |\n|---|---|---|---|---|---|---|---|\n"
        )
        for row in subset:
            lines.append(
                f"| `{_md(row.formula_name)}` | {row.primary_class} | `{_md(row.source_file)}` | "
                f"`{_md(row.function_or_class)}` | {_md(row.plain_text_formula)} | "
                f"{_md(', '.join(row.tests_covering) or 'none')} | {_md(', '.join(row.source_doc_refs) or 'none')} | "
                f"{_md(', '.join(row.consumers) or 'none')} |\n"
            )
    output_path.write_text("".join(lines), encoding="utf-8")


def write_engine_consumer_map(rows: list[FormulaRow], output_path: Path) -> None:
    engine_names = ["engine_a", "engine_b", "engine_c", "engine_d"]
    lines = ["# P0-B Engine Formula Consumer Map\n"]
    for engine in engine_names:
        direct = [row for row in rows if f"src/engines/{engine}/" in row.source_file]
        consumed = [
            row
            for row in rows
            if engine not in row.source_file
            and any(engine in consumer for consumer in row.consumers)
        ]
        lines.append(f"\n## {engine}\n")
        lines.append(f"- Direct formulas implemented: {len(direct)}\n")
        lines.append(
            f"- Upstream formulas consumed: {len(consumed)}\n"
        )
        direct_classes = Counter(row.primary_class for row in direct)
        consumed_classes = Counter(row.primary_class for row in consumed)
        lines.append(f"- Direct class mix: {dict(direct_classes)}\n")
        lines.append(f"- Upstream class mix: {dict(consumed_classes)}\n")
        micro = sorted({row.mathematical_family for row in consumed if row.primary_class == "MICROSTRUCTURE_ESTIMATOR"})
        cost = sorted({row.mathematical_family for row in consumed if row.primary_class == "EXECUTION_COST_FORMULA"})
        risk = sorted({row.mathematical_family for row in consumed if row.primary_class == "RISK_SIZING_FORMULA"})
        forecast_refusal_coordination = sorted(
            {
                row.formula_name
                for row in consumed
                if any(
                    token in f"{row.source_file} {row.function_or_class} {row.formula_name}".lower()
                    for token in ("forecast", "refusal", "coordination")
                )
            }
        )
        lines.append(f"- Microstructure features consumed: {', '.join(micro) or 'none proven'}\n")
        lines.append(f"- Cost/risk formulas consumed: {', '.join(cost + risk) or 'none proven'}\n")
        lines.append(
            f"- Forecast/refusal/coordination formulas consumed: {', '.join(forecast_refusal_coordination) or 'none proven'}\n"
        )
        missing = [row.formula_id for row in direct if "NO_CONSUMER_PROVEN" in row.secondary_flags]
        lines.append(f"- Missing consumer proof inside engine surface: {len(missing)}\n")
        lines.append(
            "- Not allowed inside engine by architecture: cockpit diagnostics, monitoring health logic, secrets management, venue IO, and standalone calibration anchors without source-mapped upstream evidence.\n"
        )
    output_path.write_text("".join(lines), encoding="utf-8")


def write_test_coverage_map(rows: list[FormulaRow], test_index: dict[str, dict[str, object]], output_path: Path) -> None:
    lines = [
        "# P0-B Formula Test Coverage Map\n",
        "| Formula ID | Test Files | Positive Tests | Negative Tests | Edge-case Tests | Deterministic/Hash Tests | Fixture Tests | Missing |\n",
        "|---|---|---|---|---|---|---|---|\n",
    ]
    for row in rows:
        positive: list[str] = []
        negative: list[str] = []
        edge: list[str] = []
        deterministic: list[str] = []
        fixture = False
        for test_rel in row.tests_covering:
            payload = test_index.get(test_rel, {})
            for test_name in payload.get("test_names", ()):
                lowered = str(test_name).lower()
                if any(token in lowered for token in ("error", "invalid", "raise", "fail")):
                    negative.append(f"{test_rel}::{test_name}")
                elif any(token in lowered for token in ("edge", "boundary", "zero", "empty", "single", "stale")):
                    edge.append(f"{test_rel}::{test_name}")
                elif any(token in lowered for token in ("seed", "hash", "repro", "deterministic")):
                    deterministic.append(f"{test_rel}::{test_name}")
                else:
                    positive.append(f"{test_rel}::{test_name}")
            fixture = fixture or bool(payload.get("has_fixture"))
        lines.append(
            f"| `{_md(row.formula_id)}` | {_md(', '.join(row.tests_covering) or 'none')} | "
            f"{_md(', '.join(positive) or 'none')} | {_md(', '.join(negative) or 'none')} | "
            f"{_md(', '.join(edge) or 'none')} | {_md(', '.join(deterministic) or 'none')} | "
            f"{'yes' if fixture else 'no'} | {'yes' if 'TEST_MISSING' in row.secondary_flags else 'no'} |\n"
        )
    output_path.write_text("".join(lines), encoding="utf-8")


def write_doc_source_map(rows: list[FormulaRow], output_path: Path) -> None:
    lines = [
        "# P0-B Formula Doc Source Map\n",
        "| Formula ID | Family | Source Docs / Specs | Paper / Reference Found | Doctrine Status | Missing Docs | Human Decision Required |\n",
        "|---|---|---|---|---|---|---|\n",
    ]
    for row in rows:
        doctrine = "documented" if row.source_doc_refs else "missing"
        human = "yes" if "HUMAN_DECISION_REQUIRED" in row.secondary_flags else "no"
        reference_found = "yes" if any(
            token in f"{row.formula_name} {row.code_excerpt}".lower()
            for token in (
                "harvey",
                "liu",
                "zhu",
                "hansen",
                "kolmogorov",
                "kpss",
                "dickey",
                "kyle",
                "cont",
                "kukanov",
                "easley",
                "lopez",
                "ohara",
                "amihud",
                "roll",
                "corwin",
                "schultz",
                "hawkes",
            )
        ) else "no"
        lines.append(
            f"| `{_md(row.formula_id)}` | {_md(row.mathematical_family)} | {_md(', '.join(row.source_doc_refs) or 'none')} | "
            f"{reference_found} | {doctrine} | {'yes' if 'DOC_SOURCE_MISSING' in row.secondary_flags else 'no'} | {human} |\n"
        )
    output_path.write_text("".join(lines), encoding="utf-8")


def write_gaps(rows: list[FormulaRow], output_path: Path) -> None:
    sections = {
        "Missing source docs": [row for row in rows if "DOC_SOURCE_MISSING" in row.secondary_flags],
        "Missing tests": [row for row in rows if "TEST_MISSING" in row.secondary_flags],
        "Missing consumer proof": [row for row in rows if "NO_CONSUMER_PROVEN" in row.secondary_flags],
        "Leakage / lookahead risk": [row for row in rows if {"LOOKAHEAD_RISK", "LEAKAGE_PROOF_MISSING"} & set(row.secondary_flags)],
        "False positives / placeholders": [row for row in rows if row.primary_class in {"FALSE_POSITIVE", "PYDANTIC_FIELD"} or "PLACEHOLDER_DEFAULT" in row.secondary_flags],
        "Human decision required": [row for row in rows if "HUMAN_DECISION_REQUIRED" in row.secondary_flags],
    }
    lines = ["# P0-B Formula Extraction Gaps\n"]
    for title, subset in sections.items():
        lines.append(f"\n## {title}\n")
        if not subset:
            lines.append("None.\n")
            continue
        for row in subset[:120]:
            lines.append(
                f"- `{row.formula_id}` [{row.primary_class}] `{row.source_file}` :: {row.function_or_class} -> {row.audit_verdict}\n"
            )
    output_path.write_text("".join(lines), encoding="utf-8")


def write_display_policy(output_path: Path) -> None:
    output_path.write_text(
        "\n".join(
            [
                "# P0-B Dashboard Formula Display Policy",
                "",
                "- Dashboard may display report-loaded values and source labels.",
                "- Dashboard may not recompute quant/statistical/microstructure formulas locally.",
                "- `display_allowed=source_label_only` means the cockpit can show provenance, owner page, tests, docs, and warnings, but not claim local recomputation.",
                "- `display_allowed=report_value_only` means the cockpit can display persisted/measured values with explicit source status.",
                "- `PLACEHOLDER_DEFAULT` must never appear near a green verdict as a measured value.",
                "- `NOT_YET_PERSISTED` or missing runtime evidence must remain explicit.",
                "- Formula owner page must stay visible:",
                "  - Trading for engines/microstructure/score-cost synthesis",
                "  - Backtest for replay/calibration/profitability provenance",
                "  - VPS for service/queue/kill/disk/runtime diagnostics",
                "  - Shadow for readiness/verdict",
                "  - IA Lab for ML/regime/artifact provenance",
                "  - Observability for scrape/bridge/Prometheus/Grafana health",
            ]
        ),
        encoding="utf-8",
    )


def write_top_50(rows: list[FormulaRow], output_path: Path) -> None:
    def score(row: FormulaRow) -> int:
        value = 0
        if row.primary_class in {"EXECUTION_COST_FORMULA", "RISK_SIZING_FORMULA", "MICROSTRUCTURE_ESTIMATOR"}:
            value += 6
        if row.primary_class == "STATISTICAL_ANCHOR":
            value += 5
        if row.primary_class == "REAL_QUANT_FORMULA":
            value += 4
        if row.primary_class == "ML_LABEL_OR_FEATURE_TRANSFORM":
            value += 5
        if row.dashboard_owner_page in {"Trading", "Backtest", "VPS"}:
            value += 3
        for flag in row.secondary_flags:
            if flag in {"TEST_MISSING", "DOC_SOURCE_MISSING", "NO_CONSUMER_PROVEN"}:
                value += 3
            if flag in {"LOOKAHEAD_RISK", "LEAKAGE_PROOF_MISSING", "DASHBOARD_FALSE_GREEN_RISK"}:
                value += 5
            if flag == "HUMAN_DECISION_REQUIRED":
                value += 4
        return value

    ranked = sorted(rows, key=lambda row: (-score(row), row.source_file, row.line_start))[:50]
    lines = [
        "# P0-B Top 50 Formula Audit Queue\n",
        "| Rank | Formula ID | Class | Owner | Risk | Flags | Why it is high priority |\n",
        "|---:|---|---|---|---|---|---|\n",
    ]
    for index, row in enumerate(ranked, start=1):
        why = []
        if row.primary_class in {"EXECUTION_COST_FORMULA", "RISK_SIZING_FORMULA", "MICROSTRUCTURE_ESTIMATOR"}:
            why.append("can influence trade side/size/order/fill")
        if row.dashboard_owner_page == "Backtest":
            why.append("can influence replay profitability or promotion evidence")
        if "DASHBOARD_FALSE_GREEN_RISK" in row.secondary_flags:
            why.append("can create false green cockpit")
        if "TEST_MISSING" in row.secondary_flags:
            why.append("missing tests")
        if "DOC_SOURCE_MISSING" in row.secondary_flags:
            why.append("missing docs")
        if "NO_CONSUMER_PROVEN" in row.secondary_flags:
            why.append("no consumer proof")
        if "LOOKAHEAD_RISK" in row.secondary_flags or "LEAKAGE_PROOF_MISSING" in row.secondary_flags:
            why.append("anti-leakage proof missing")
        lines.append(
            f"| {index} | `{_md(row.formula_id)}` | {row.primary_class} | {row.dashboard_owner_page} | {row.risk_level} | "
            f"{_md(', '.join(row.secondary_flags))} | {_md('; '.join(why) or 'owner-critical formula')} |\n"
        )
    output_path.write_text("".join(lines), encoding="utf-8")


def summarize(rows: list[FormulaRow]) -> dict[str, object]:
    return {
        "files_scanned": len({row.source_file for row in rows}),
        "formula_rows": len(rows),
        "class_counts": Counter(row.primary_class for row in rows),
        "family_counts": Counter(row.mathematical_family for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rows, _ = build_rows(repo_root)
    if not rows:
        raise SystemExit("No formula rows extracted")

    test_files = collect_test_files(repo_root)
    test_index = build_test_index(test_files, repo_root)

    write_csv(rows, output_dir / "P0B_FORMULA_MASTER_LEDGER.csv")
    write_json(rows, output_dir / "P0B_FORMULA_MASTER_LEDGER.json")
    write_master_md(rows, output_dir / "P0B_FORMULA_MASTER_LEDGER.md")
    write_filtered_bank(
        rows,
        allowed_classes=REAL_CLASSES,
        title="P0-B Real Quant Formulas Only",
        output_path=output_dir / "P0B_REAL_QUANT_FORMULAS_ONLY.md",
    )
    write_family_bank(
        rows,
        title="P0-B Microstructure Formula Bank",
        families=[
            "Kyle lambda / price impact",
            "Order Flow Imbalance (Cont-Kukanov)",
            "VPIN",
            "PIN",
            "Amihud illiquidity",
            "Roll spread",
            "Corwin-Schultz spread",
            "Realized kernel volatility",
            "Realized / effective spread",
            "Spread dynamics",
            "Queue pressure / order-book imbalance",
            "Walls / spoofing features",
            "LOB regime features",
            "Hawkes intensity",
        ],
        output_path=output_dir / "P0B_MICROSTRUCTURE_FORMULA_BANK.md",
    )
    write_family_bank(
        rows,
        title="P0-B Statistical Anchor Bank",
        families=[
            "Probabilistic Sharpe Ratio",
            "Deflated Sharpe Ratio",
            "Harvey-Liu-Zhu multiple-testing guard",
            "Hansen SPA",
            "POT-GPD",
            "Energy distance",
            "KS two-sample",
            "Mann-Kendall trend",
            "ADF / KPSS stationarity",
            "Stationary bootstrap",
            "Purged walk-forward",
        ],
        output_path=output_dir / "P0B_STATISTICAL_ANCHOR_BANK.md",
    )
    write_family_bank(
        rows,
        title="P0-B Replay / Profitability Formula Bank",
        families=[
            "Replay profitability aggregates",
            "Shadow / replay parity metrics",
            "Ablation / block-rate metrics",
        ],
        output_path=output_dir / "P0B_REPLAY_PROFITABILITY_FORMULA_BANK.md",
    )
    write_filtered_bank(
        rows,
        allowed_classes={"EXECUTION_COST_FORMULA"},
        title="P0-B Execution Cost Formula Bank",
        output_path=output_dir / "P0B_EXECUTION_COST_FORMULA_BANK.md",
    )
    write_engine_consumer_map(rows, output_dir / "P0B_ENGINE_FORMULA_CONSUMER_MAP.md")
    write_test_coverage_map(
        rows,
        test_index=test_index,
        output_path=output_dir / "P0B_FORMULA_TEST_COVERAGE_MAP.md",
    )
    write_doc_source_map(rows, output_dir / "P0B_FORMULA_DOC_SOURCE_MAP.md")
    write_gaps(rows, output_dir / "P0B_FORMULA_EXTRACTION_GAPS.md")
    write_display_policy(output_dir / "P0B_DASHBOARD_FORMULA_DISPLAY_POLICY.md")
    write_top_50(rows, output_dir / "P0B_TOP_50_FORMULA_AUDIT_QUEUE.md")

    summary = summarize(rows)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=lambda value: dict(value)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
