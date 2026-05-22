from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
import json
from pathlib import Path
from typing import Any

from engines.engine_a.engine_a_runner import EngineAInput, run_engine_a
from engines.engine_a.structure_detector_a import StructureInput, detect_structure
from engines.engine_b.cost_feasibility_b import CostInputB, check_cost_feasibility_b
from engines.engine_b.engine_b_runner import EngineBInput, run_engine_b
from engines.engine_b.excess_detector_b import ExcessInput, detect_excess
from engines.engine_c.engine_c_runner import EngineCInput, run_engine_c
from engines.engine_c.signal_math_c import (
    compute_breakout_score,
    compute_context_score as compute_context_score_c,
    compute_fake_breakout_risk,
)
from engines.engine_d.context_resolver_d import resolve_engine_d_context
from engines.engine_d.cost_feasibility_d import evaluate_cost_feasibility_d
from engines.engine_d.engine_d_models import EngineDInput
from engines.engine_d.engine_d_runner import run_engine_d
from engines.engine_d.signal_math_d import (
    compute_context_score as compute_context_score_d,
    compute_history_score,
    compute_marginal_value_score,
    compute_reformation_score,
)
from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from local_replay_runtime.engine_feature_contract_validator import (
    EngineFeatureExpectation,
    audit_engine_feature_contract,
)
from local_replay_runtime.strategy_ladder_candidate_discovery import (
    load_strategy_ladder_candidate_events,
)
from local_replay_runtime.strategy_ladder_candidate_trade_semantics_audit import (
    write_strategy_ladder_candidate_trade_semantics_audit,
)
from local_replay_runtime.strategy_ladder_complete_enabler_support import (
    apply_build14_shadow_context,
)
from local_replay_runtime.strategy_ladder_economic_provenance import (
    EconomicProvenance,
    expected_edge_backtest_truth_status,
)
from local_replay_runtime.strategy_ladder_engine_a_input_builder import (
    build_engine_a_input_from_window,
)
from local_replay_runtime.strategy_ladder_engine_b_input_builder import (
    build_engine_b_input_from_window,
)
from local_replay_runtime.strategy_ladder_engine_c_input_builder import (
    build_engine_c_input_from_window,
)
from local_replay_runtime.strategy_ladder_engine_d_input_builder import (
    build_engine_d_input_from_window,
)
from local_replay_runtime.strategy_ladder_engine_native_adapter import (
    build_engine_a_microstructure_inputs_from_window,
    build_engine_c_microstructure_inputs_from_window,
)
from local_replay_runtime.strategy_ladder_gate_waterfall_analysis import (
    write_strategy_ladder_gate_waterfall_reports,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderCandidateEvent,
    StrategyLadderRawWindowManifest,
    StrategyLadderReportSummary,
    StrategyLadderRunManifest,
)
from local_replay_runtime.strategy_ladder_raw_window_extractor import (
    load_strategy_ladder_raw_window_manifests,
)
from local_replay_runtime.strategy_ladder_replay_evidence import (
    build_measured_slippage_payload,
    build_measured_spread_payload,
)
from local_replay_runtime.strategy_ladder_runner import (
    _extract_engine_d_first_episode_context,
)
from sharia_compliance import ShariaTradeRequest, authorize_trade_type, load_sharia_policy


_SCHEMA_VERSION = "v53.engine_math_canary_audit.v1"
_CANARY_PROVENANCE = "GOVERNED_SYNTHETIC_CANARY"


def _enum_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def bps_to_decimal(value_bps: float) -> float:
    return float(value_bps) / 10_000.0


def decimal_to_bps(value_decimal: float) -> float:
    return float(value_decimal) * 10_000.0


def percent_to_decimal(percent_value: float) -> float:
    return float(percent_value) / 100.0


def build_expected_cost_decimal(
    *,
    spread_bps: float,
    slippage_bps: float,
    fee_bps: float,
    latency_penalty_bps: float,
) -> float:
    return bps_to_decimal(spread_bps + slippage_bps + fee_bps + latency_penalty_bps)


def _runner_expected_cost_decimal(provenance: EconomicProvenance) -> float:
    return (
        provenance.spread_bps
        + provenance.slippage_bps * 1.15
        + provenance.latency_penalty_bps
    ) / 10_000.0


def _planned_notional(payload: dict[str, object]) -> float:
    for key in ("planned_notional", "candidate_size", "final_size"):
        try:
            value = float(payload.get(key) or 0.0)
        except (TypeError, ValueError):
            continue
        if value > 0.0:
            return value
    return 0.0


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )


def _bar(
    *,
    scenario_id: str,
    pair: str,
    timeframe: str,
    ts_ms: int,
    o: float,
    h: float,
    l: float,
    c: float,
    v: float,
) -> dict[str, object]:
    return {
        "scenario_id": scenario_id,
        "timestamp_ms": ts_ms,
        "pair": pair,
        "timeframe": timeframe,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
    }


def _trade(
    *,
    scenario_id: str,
    pair: str,
    ts_ms: int,
    price: float,
    qty: float,
    side: str,
) -> dict[str, object]:
    return {
        "scenario_id": scenario_id,
        "timestamp_ms": ts_ms,
        "pair": pair,
        "trade_id": f"{scenario_id}:{ts_ms}",
        "price": str(price),
        "qty": str(qty),
        "side": side,
    }


def _book_snapshot(
    *,
    scenario_id: str,
    ts_ms: int,
    update_id: int,
    bids: list[list[object]],
    asks: list[list[object]],
) -> dict[str, object]:
    return {
        "scenario_id": scenario_id,
        "timestamp_ms": ts_ms,
        "update_id": update_id,
        "bids": bids,
        "asks": asks,
    }


def _book_delta(
    *,
    scenario_id: str,
    ts_ms: int,
    update_id: int,
    bids: list[list[object]] | None = None,
    asks: list[list[object]] | None = None,
) -> dict[str, object]:
    return {
        "scenario_id": scenario_id,
        "timestamp_ms": ts_ms,
        "update_id": update_id,
        "bids": bids or [],
        "asks": asks or [],
    }


@dataclass(frozen=True)
class EquationRegistryRow:
    equation_id: str
    engine_id: str
    module_path: str
    function_name: str
    formula_expected: str
    formula_implemented: str
    input_fields: tuple[str, ...]
    output_fields: tuple[str, ...]
    input_units: dict[str, str]
    output_units: dict[str, str]
    threshold_name: str
    threshold_value: float | str
    threshold_unit: str
    reason_code_fail: tuple[str, ...]
    reason_code_pass_or_marginal: tuple[str, ...]
    expected_provenance: str
    existing_tests: tuple[str, ...]
    missing_tests: tuple[str, ...]


@dataclass(frozen=True)
class ReconstructedNativeCase:
    engine_id: str
    candidate_id: str
    pair: str
    builder_status: str
    builder_provenance: str
    builder_warnings: tuple[str, ...]
    engine_input_payload: dict[str, object]
    output_payload: dict[str, object]
    decision: str
    reason_codes: tuple[str, ...]
    no_trade_reasons: tuple[str, ...]
    records_built: int


@dataclass(frozen=True)
class SyntheticScenarioResult:
    scenario_id: str
    engine_id: str
    expected_decision: str
    actual_decision: str
    expected_reason_codes: tuple[str, ...]
    actual_reason_codes: tuple[str, ...]
    expected_builder_status: str
    actual_builder_status: str
    expected_truth_status: str
    actual_expected_gain: float
    actual_expected_cost: float
    ok: bool


@dataclass(frozen=True)
class AuditCandidateContext:
    candidate: StrategyLadderCandidateEvent
    window: StrategyLadderRawWindowManifest
    payload: dict[str, object]
    economic_provenance: EconomicProvenance
    case: ReconstructedNativeCase


def _registry_rows() -> tuple[EquationRegistryRow, ...]:
    return (
        EquationRegistryRow(
            equation_id="A_DIRECTION_POLICY",
            engine_id="engine_a",
            module_path="src/engines/engine_a/engine_a_runner.py",
            function_name="run_engine_a",
            formula_expected="long-only gate: direction_score must be > 0 before any trade path",
            formula_implemented="if inputs.direction_score <= 0: NO_TRADE",
            input_fields=("direction_score",),
            output_fields=("decision", "reason_codes"),
            input_units={"direction_score": "signed_score_-1_to_1"},
            output_units={"decision": "enum", "reason_codes": "tuple[str]"},
            threshold_name="direction_score_non_long_gate",
            threshold_value=0.0,
            threshold_unit="signed_score_-1_to_1",
            reason_code_fail=("engine_internal.engine_a.direction.non_long", "engine_a.input.non_long_direction"),
            reason_code_pass_or_marginal=(),
            expected_provenance="engine_a_input_payload",
            existing_tests=("tests/test_engines/test_engine_a/test_engine_a.py::test_non_long_direction_branch",),
            missing_tests=("tests/engine_canary/test_engine_equations_canary.py::test_engine_a_negative_direction_never_becomes_long",),
        ),
        EquationRegistryRow(
            equation_id="A_STRUCTURE_SCORE",
            engine_id="engine_a",
            module_path="src/engines/engine_a/structure_detector_a.py",
            function_name="detect_structure",
            formula_expected="0.30*abs(direction)+0.25*continuation+0.20*quality+0.10*zone+0.15*stability",
            formula_implemented="ENGINE_A_STRUCTURE_WEIGHTS weighted sum with realized_kernel_vol_scale override for stability",
            input_fields=("direction_score", "continuation_score", "structure_quality", "zone_proximity", "trend_stability"),
            output_fields=("structure_score", "verdict"),
            input_units={
                "direction_score": "signed_score_-1_to_1",
                "continuation_score": "score_0_to_1",
                "structure_quality": "score_0_to_1",
                "zone_proximity": "score_0_to_1",
                "trend_stability": "score_0_to_1",
            },
            output_units={"structure_score": "score_0_to_1", "verdict": "enum"},
            threshold_name="favorable/marginal/min_direction",
            threshold_value="0.60/0.30/0.20",
            threshold_unit="score_0_to_1",
            reason_code_fail=(),
            reason_code_pass_or_marginal=(),
            expected_provenance="engine_a_input_payload",
            existing_tests=("tests/test_engines/test_engine_a/test_engine_a.py::test_structure_unfavorable_branch",),
            missing_tests=("tests/engine_canary/test_engine_equations_canary.py::test_engine_a_structure_detector_canary_cases",),
        ),
        EquationRegistryRow(
            equation_id="A_COST_BREAK_EVEN",
            engine_id="engine_a",
            module_path="src/engines/engine_a/cost_feasibility_a.py",
            function_name="check_cost_feasibility",
            formula_expected="break_even=(expected_cost+kyle_uplift)+delta_safe ; CE=(expected_gain-(expected_cost+kyle_uplift))/holding_period",
            formula_implemented="effective_expected_cost = expected_cost + kyle_lambda_cost_uplift ; expected_gain <= break_even blocks ; CE < ce_min marginal",
            input_fields=("expected_gain", "expected_cost", "kyle_lambda_cost_uplift", "candidate_size", "holding_period", "delta_safe", "ce_min"),
            output_fields=("expected_cost", "break_even", "ev_net", "ce_expected", "verdict"),
            input_units={
                "expected_gain": "decimal_return",
                "expected_cost": "decimal_return",
                "kyle_lambda_cost_uplift": "decimal_return",
                "candidate_size": "notional_quote",
                "holding_period": "hours",
                "delta_safe": "decimal_return",
                "ce_min": "decimal_return_per_hour",
            },
            output_units={
                "expected_cost": "decimal_return",
                "break_even": "decimal_return",
                "ev_net": "quote_notional_return",
                "ce_expected": "decimal_return_per_hour",
                "verdict": "enum",
            },
            threshold_name="delta_safe/ce_min",
            threshold_value="0.0005/0.0001",
            threshold_unit="decimal_return",
            reason_code_fail=("engine_a.cost.break_even_not_cleared", "engine_a.cost.ce_below_min"),
            reason_code_pass_or_marginal=(),
            expected_provenance="economic_provenance",
            existing_tests=("tests/test_engines/test_engine_a/test_engine_a.py::test_cost_marginal_branch",),
            missing_tests=("tests/engine_canary/test_engine_equations_canary.py::test_unit_conversions_and_expected_cost_sum",),
        ),
        EquationRegistryRow(
            equation_id="B_Z_SCORE_EXCESS",
            engine_id="engine_b",
            module_path="src/engines/engine_b/excess_detector_b.py",
            function_name="detect_excess",
            formula_expected="abs_z=abs(z_score); no_excess if abs_z<z_marginal; exploitable if abs_z>=z_star; invalid when z_score_valid is false",
            formula_implemented="abs_z gating with z_marginal=1.0 z_star=1.5 z_max=4.0; excess_score=z_quality+range_bonus-expansion_penalty",
            input_fields=("z_score", "z_score_valid", "structure_is_range", "recent_expansion"),
            output_fields=("abs_z", "excess_score", "verdict"),
            input_units={
                "z_score": "sigma_units",
                "z_score_valid": "bool",
                "structure_is_range": "score_0_to_1",
                "recent_expansion": "score_0_to_1",
            },
            output_units={"abs_z": "sigma_units", "excess_score": "score_0_to_1", "verdict": "enum"},
            threshold_name="z_marginal/z_star/z_max",
            threshold_value="1.0/1.5/4.0",
            threshold_unit="sigma_units",
            reason_code_fail=("engine_b.excess.no_excess", "engine_b.excess.invalid"),
            reason_code_pass_or_marginal=("b.toxic_flow_fade", "b.toxic_flow_fade_suppressed.correlation"),
            expected_provenance="engine_b_input_payload",
            existing_tests=("tests/test_engines/test_engine_b/test_engine_b.py::test_excess_detector",),
            missing_tests=("tests/engine_canary/test_engine_equations_canary.py::test_engine_b_excess_threshold_cases",),
        ),
        EquationRegistryRow(
            equation_id="B_DIRECTION_POLICY",
            engine_id="engine_b",
            module_path="src/engines/engine_b/engine_b_runner.py",
            function_name="run_engine_b",
            formula_expected="long-only mean reversion: z_score must be <= 0 for a long-compatible candidate",
            formula_implemented="if mean_result.z_score > 0: NO_TRADE non_long",
            input_fields=("current_price", "local_mean", "local_std"),
            output_fields=("decision", "reason_codes"),
            input_units={"current_price": "price_quote", "local_mean": "price_quote", "local_std": "price_quote"},
            output_units={"decision": "enum", "reason_codes": "tuple[str]"},
            threshold_name="z_score_sign",
            threshold_value=0.0,
            threshold_unit="sigma_units",
            reason_code_fail=("engine_internal.engine_b.direction.non_long", "engine_b.direction.non_long"),
            reason_code_pass_or_marginal=(),
            expected_provenance="engine_b_input_payload",
            existing_tests=("tests/test_engines/test_engine_b/test_engine_b.py::test_runner_rejects_positive_z_as_non_long",),
            missing_tests=("tests/engine_canary/test_engine_equations_canary.py::test_engine_b_negative_z_is_math_excess_but_positive_z_is_long_only_block",),
        ),
        EquationRegistryRow(
            equation_id="B_COST_BREAK_EVEN",
            engine_id="engine_b",
            module_path="src/engines/engine_b/cost_feasibility_b.py",
            function_name="check_cost_feasibility_b",
            formula_expected="break_even=expected_cost+delta_safe ; EV_net=x*(expected_gain-expected_cost) ; CE=(expected_gain-expected_cost)/holding_period",
            formula_implemented="expected_gain <= break_even infeasible ; ev_net <= 0 infeasible ; CE < ce_min marginal",
            input_fields=("expected_gain", "expected_cost", "candidate_size", "holding_period", "delta_safe", "ce_min"),
            output_fields=("break_even", "ev_net", "ce_expected", "verdict"),
            input_units={
                "expected_gain": "decimal_return",
                "expected_cost": "decimal_return",
                "candidate_size": "notional_quote",
                "holding_period": "hours",
                "delta_safe": "decimal_return",
                "ce_min": "decimal_return_per_hour",
            },
            output_units={"break_even": "decimal_return", "ev_net": "quote_notional_return", "ce_expected": "decimal_return_per_hour", "verdict": "enum"},
            threshold_name="delta_safe/ce_min",
            threshold_value="0.0008/0.0002",
            threshold_unit="decimal_return",
            reason_code_fail=("break_even_not_cleared", "ce_below_minimum"),
            reason_code_pass_or_marginal=(),
            expected_provenance="economic_provenance",
            existing_tests=("tests/test_engines/test_engine_b/test_engine_b.py::test_cost_equality_to_break_even_is_infeasible",),
            missing_tests=("tests/engine_canary/test_engine_equations_canary.py::test_engine_b_cost_threshold_cases",),
        ),
        EquationRegistryRow(
            equation_id="C_BREAKOUT_SCORE",
            engine_id="engine_c",
            module_path="src/engines/engine_c/signal_math_c.py",
            function_name="compute_breakout_score",
            formula_expected="0.35*breakout_strength+0.25*range_quality+0.20*compression_quality+0.20*volume_confirmation",
            formula_implemented="compute_breakout_score weighted sum clamped to [0,1]",
            input_fields=("breakout_strength", "range_quality", "compression_quality", "volume_confirmation"),
            output_fields=("breakout_score",),
            input_units={
                "breakout_strength": "score_0_to_1",
                "range_quality": "score_0_to_1",
                "compression_quality": "score_0_to_1",
                "volume_confirmation": "score_0_to_1",
            },
            output_units={"breakout_score": "score_0_to_1"},
            threshold_name="breakout_score_min",
            threshold_value=0.62,
            threshold_unit="score_0_to_1",
            reason_code_fail=("engine_c.breakout.unstructured",),
            reason_code_pass_or_marginal=(),
            expected_provenance="engine_c_input_payload",
            existing_tests=("tests/test_engines/test_engine_c/test_engine_c.py::test_breakout_unstructured_branch",),
            missing_tests=("tests/engine_canary/test_engine_equations_canary.py::test_engine_c_breakout_threshold_cases",),
        ),
        EquationRegistryRow(
            equation_id="C_FAKE_BREAKOUT_RISK",
            engine_id="engine_c",
            module_path="src/engines/engine_c/signal_math_c.py",
            function_name="compute_fake_breakout_risk",
            formula_expected="0.45*retrace_risk+0.30*rejection_wick_ratio+0.25*(1-volume_confirmation)",
            formula_implemented="compute_fake_breakout_risk weighted sum clamped to [0,1]",
            input_fields=("retrace_risk", "rejection_wick_ratio", "volume_confirmation"),
            output_fields=("fake_breakout_risk",),
            input_units={
                "retrace_risk": "score_0_to_1",
                "rejection_wick_ratio": "score_0_to_1",
                "volume_confirmation": "score_0_to_1",
            },
            output_units={"fake_breakout_risk": "score_0_to_1"},
            threshold_name="fake_breakout_risk_max",
            threshold_value=0.65,
            threshold_unit="score_0_to_1",
            reason_code_fail=("engine_c.fake_breakout.blocked",),
            reason_code_pass_or_marginal=(),
            expected_provenance="engine_c_input_payload",
            existing_tests=("tests/test_engines/test_engine_c/test_engine_c.py::test_fake_breakout_blocked_branch",),
            missing_tests=("tests/engine_canary/test_engine_threshold_boundaries.py::test_engine_c_threshold_boundaries_with_epsilon",),
        ),
        EquationRegistryRow(
            equation_id="D_HISTORY_SCORE",
            engine_id="engine_d",
            module_path="src/engines/engine_d/signal_math_d.py",
            function_name="compute_history_score",
            formula_expected="0.55*prior_trade_quality+0.25*pair_health+0.20*data_freshness",
            formula_implemented="compute_history_score weighted sum clamped to [0,1]",
            input_fields=("prior_trade_quality", "pair_health", "data_freshness"),
            output_fields=("history_score",),
            input_units={"prior_trade_quality": "score_0_to_1", "pair_health": "score_0_to_1", "data_freshness": "score_0_to_1"},
            output_units={"history_score": "score_0_to_1"},
            threshold_name="history_min",
            threshold_value=0.55,
            threshold_unit="score_0_to_1",
            reason_code_fail=("engine_internal.engine_d.history.weak", "engine_d.no_trade.history_weak"),
            reason_code_pass_or_marginal=(),
            expected_provenance="engine_d_input_payload",
            existing_tests=("tests/test_engines/test_engine_d/test_engine_d.py::test_history_weak_branch",),
            missing_tests=("tests/engine_canary/test_engine_equations_canary.py::test_engine_d_missing_history_and_threshold_cases",),
        ),
        EquationRegistryRow(
            equation_id="D_REFORMATION_SCORE",
            engine_id="engine_d",
            module_path="src/engines/engine_d/signal_math_d.py",
            function_name="compute_reformation_score",
            formula_expected="0.45*reformation_quality+0.30*pullback_quality+0.25*context_score",
            formula_implemented="compute_reformation_score weighted sum clamped to [0,1]",
            input_fields=("reformation_quality", "pullback_quality", "regime_favorability", "pair_health", "data_freshness", "flow_coherence"),
            output_fields=("context_score", "reformation_score"),
            input_units={
                "reformation_quality": "score_0_to_1",
                "pullback_quality": "score_0_to_1",
                "regime_favorability": "score_0_to_1",
                "pair_health": "score_0_to_1",
                "data_freshness": "score_0_to_1",
                "flow_coherence": "score_0_to_1",
            },
            output_units={"context_score": "score_0_to_1", "reformation_score": "score_0_to_1"},
            threshold_name="reformation_min",
            threshold_value=0.58,
            threshold_unit="score_0_to_1",
            reason_code_fail=("engine_internal.engine_d.reformation.weak", "engine_d.no_trade.reformation_weak"),
            reason_code_pass_or_marginal=(),
            expected_provenance="engine_d_input_payload",
            existing_tests=("tests/test_engines/test_engine_d/test_engine_d.py::test_reformation_weak_branch",),
            missing_tests=("tests/engine_canary/test_engine_threshold_boundaries.py::test_engine_d_threshold_boundaries_with_epsilon",),
        ),
        EquationRegistryRow(
            equation_id="D_CONCENTRATION_RISK",
            engine_id="engine_d",
            module_path="src/engines/engine_d/context_resolver_d.py",
            function_name="resolve_engine_d_context",
            formula_expected="0.60*(1-concentration_headroom)+0.40*reentry_lateness",
            formula_implemented="concentration_risk = clamp(0.60*(1-headroom)+0.40*lateness)",
            input_fields=("concentration_headroom", "reentry_lateness"),
            output_fields=("concentration_risk",),
            input_units={"concentration_headroom": "score_0_to_1", "reentry_lateness": "score_0_to_1"},
            output_units={"concentration_risk": "score_0_to_1"},
            threshold_name="concentration_max",
            threshold_value=0.64,
            threshold_unit="score_0_to_1",
            reason_code_fail=("engine_internal.engine_d.concentration.blocked", "engine_d.no_trade.concentration_blocked"),
            reason_code_pass_or_marginal=(),
            expected_provenance="engine_d_input_payload",
            existing_tests=("tests/test_engines/test_engine_d/test_engine_d.py::test_concentration_blocked_branch",),
            missing_tests=("tests/engine_canary/test_engine_equations_canary.py::test_engine_d_missing_history_and_threshold_cases",),
        ),
        EquationRegistryRow(
            equation_id="SHARED_EXPECTED_EDGE_TRUTH",
            engine_id="shared_b2",
            module_path="src/local_replay_runtime/strategy_ladder_economic_provenance.py",
            function_name="is_expected_edge_backtest_truth",
            formula_expected="only MEASURED_* or GOVERNED_* provenance is usable as B2 truth; proxy/default/to_calibrate blocked",
            formula_implemented="TO_CALIBRATE/DEFAULT/PROXY/UNKNOWN => false ; MEASURED_/GOVERNED_ => true",
            input_fields=("expected_edge_provenance",),
            output_fields=("expected_edge_truth_status",),
            input_units={"expected_edge_provenance": "string_label"},
            output_units={"expected_edge_truth_status": "string_label"},
            threshold_name="expected_edge_truth_gate",
            threshold_value="governed_or_measured_only",
            threshold_unit="label",
            reason_code_fail=("EXPECTED_EDGE_PROXY_BLOCKED", "EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH"),
            reason_code_pass_or_marginal=("EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",),
            expected_provenance="economic_provenance",
            existing_tests=("tests/test_local_replay_runtime/test_strategy_ladder_economic_provenance.py::test_expected_edge_backtest_truth_status",),
            missing_tests=("tests/engine_canary/test_engine_equations_canary.py::test_b2_proxy_expected_edge_never_becomes_truth",),
        ),
        EquationRegistryRow(
            equation_id="SHARED_SPREAD_AND_DEPTH",
            engine_id="shared_b2",
            module_path="src/local_replay_runtime/strategy_ladder_replay_evidence.py",
            function_name="build_measured_spread_payload/build_measured_slippage_payload",
            formula_expected="spread_bps=(ask-bid)/mid*10000 ; depth_topk_notional=sum(price*size) ; depth_fill_ratio=filled_notional/planned_notional",
            formula_implemented="spread from reconstructed book state; depth_top1/top5/top20 from top levels; walk_cost_bps from volume walk",
            input_fields=("best_bid", "best_ask", "levels", "planned_notional"),
            output_fields=("spread_bps", "depth_top1_notional", "depth_top5_notional", "depth_top20_notional", "depth_fill_ratio", "staleness_ms"),
            input_units={"best_bid": "price_quote", "best_ask": "price_quote", "levels": "price_qty_levels", "planned_notional": "notional_quote"},
            output_units={
                "spread_bps": "bps",
                "depth_top1_notional": "notional_quote",
                "depth_top5_notional": "notional_quote",
                "depth_top20_notional": "notional_quote",
                "depth_fill_ratio": "ratio_0_to_1",
                "staleness_ms": "milliseconds",
            },
            threshold_name="book_freshness_warn_ms",
            threshold_value=5000,
            threshold_unit="milliseconds",
            reason_code_fail=("SPREAD_MEASURED_STALE_AUDIT_ONLY", "SPREAD_BLOCKED_BY_MISSING_BOOK"),
            reason_code_pass_or_marginal=("SPREAD_MEASURED_FROM_BOOK", "SLIPPAGE_ESTIMATED_FROM_DEPTH20"),
            expected_provenance="replay_evidence",
            existing_tests=("tests/test_local_replay_runtime/test_strategy_ladder_replay_evidence.py::test_measured_spread",),
            missing_tests=("tests/engine_canary/test_engine_equations_canary.py::test_orderbook_depth_and_spread_canary",),
        ),
        EquationRegistryRow(
            equation_id="SHARED_SHARIA_SIDE_POLICY",
            engine_id="shared_policy",
            module_path="src/sharia_compliance/trade_type_guard.py",
            function_name="authorize_trade_type",
            formula_expected="short forbidden; non-spot forbidden; leverage forbidden; margin forbidden",
            formula_implemented="SHORT_FORBIDDEN / NON_SPOT_FORBIDDEN / LEVERAGE_FORBIDDEN / MARGIN_FORBIDDEN",
            input_fields=("side", "metadata.product_type", "metadata.leverage", "metadata.margin_required"),
            output_fields=("allowed", "reason_code"),
            input_units={"side": "label", "metadata.product_type": "label", "metadata.leverage": "multiple", "metadata.margin_required": "bool"},
            output_units={"allowed": "bool", "reason_code": "string_label"},
            threshold_name="sharia_spot_long_only",
            threshold_value="buy_or_inventory_reduce_only",
            threshold_unit="policy_label",
            reason_code_fail=("SHORT_FORBIDDEN", "NON_SPOT_FORBIDDEN", "LEVERAGE_FORBIDDEN", "MARGIN_FORBIDDEN"),
            reason_code_pass_or_marginal=(),
            expected_provenance="execution_policy",
            existing_tests=("tests/test_sharia_compliance/test_trade_type_guard.py",),
            missing_tests=("tests/engine_canary/test_engine_equations_canary.py::test_sharia_spot_long_only_canary",),
        ),
    )


def build_engine_equation_feature_registry() -> dict[str, object]:
    rows = _registry_rows()
    return {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "row_count": len(rows),
        "rows": [asdict(row) for row in rows],
    }


def _canary_provenance_guard(*, provenance: str, runtime_mode: str) -> None:
    if provenance == _CANARY_PROVENANCE and runtime_mode.upper() != "TEST":
        raise ValueError("GOVERNED_SYNTHETIC_CANARY is forbidden outside runtime_mode=TEST")


def _synthetic_provenance(
    *,
    expected_edge_bps: float,
    expected_edge_provenance: str,
    spread_bps: float,
    slippage_bps: float,
    latency_penalty_bps: float,
    fee_bps: float,
    runtime_mode: str,
) -> EconomicProvenance:
    _canary_provenance_guard(
        provenance=expected_edge_provenance,
        runtime_mode=runtime_mode,
    )
    return EconomicProvenance(
        expected_edge_bps=expected_edge_bps,
        expected_edge_provenance=expected_edge_provenance,
        spread_bps=spread_bps,
        spread_provenance="MEASURED_FROM_BOOK_RECONSTRUCTION",
        slippage_bps=slippage_bps,
        slippage_provenance="MEASURED_FROM_KYLE_LAMBDA",
        latency_penalty_bps=latency_penalty_bps,
        latency_provenance="STATIC_CONSERVATIVE_VENUE_MODEL",
        fee_bps=fee_bps,
        fee_provenance="MEASURED_FROM_VENUE_METADATA",
        measurement_warnings=(),
        expected_edge_model_status="GOVERNED_EDGE_MODEL_READY"
        if expected_edge_provenance == _CANARY_PROVENANCE
        else "EXPECTED_EDGE_PROXY_BLOCKED",
        expected_edge_model_artifact_hash="ENGINE_CANARY",
        expected_edge_model_feature_hash="ENGINE_CANARY",
    )


def reconstruct_native_candidate_case(
    *,
    candidate: StrategyLadderCandidateEvent,
    window: StrategyLadderRawWindowManifest,
    economic_provenance: EconomicProvenance,
) -> ReconstructedNativeCase:
    engine_id = str(candidate.engine_id or "").strip().lower()
    payload = dict(candidate.compatibility_payload or {})
    engine_input_overrides = (
        dict(payload.get("engine_input_overrides"))
        if isinstance(payload.get("engine_input_overrides"), dict)
        else {}
    )
    expected_gain = (
        economic_provenance.expected_edge_bps / 10_000.0
        if economic_provenance.expected_edge_provenance.startswith(("MEASURED_", "GOVERNED_"))
        and "TO_CALIBRATE" not in economic_provenance.expected_edge_provenance
        and "PROXY" not in economic_provenance.expected_edge_provenance
        and "DEFAULT" not in economic_provenance.expected_edge_provenance
        else 0.0
    )
    expected_cost = _runner_expected_cost_decimal(economic_provenance)
    candidate_size = _planned_notional(payload)

    builder_status = "UNSUPPORTED_ENGINE"
    builder_provenance = ""
    builder_warnings: tuple[str, ...] = ()
    engine_input_payload: dict[str, object] = {}
    output_payload: dict[str, object] = {}
    decision = "not_invoked"
    reason_codes: tuple[str, ...] = ()
    no_trade_reasons: tuple[str, ...] = ()
    records_built = 0

    if engine_id == "engine_a":
        bridge = build_engine_a_microstructure_inputs_from_window(
            candidate_id=candidate.candidate_id,
            pair=candidate.pair,
            window_start_ms=window.window_start_ms,
            window_end_ms=window.window_end_ms,
            raw_trade_path=window.raw_trade_path,
            raw_book_path=window.raw_book_path,
            raw_book_delta_path=window.raw_book_delta_path,
        )
        builder = build_engine_a_input_from_window(
            candidate_id=candidate.candidate_id,
            pair=candidate.pair,
            window_start_ms=window.window_start_ms,
            window_end_ms=window.window_end_ms,
            raw_ohlcv_path=window.raw_ohlcv_path,
            microstructure_updates=bridge.engine_a_microstructure_updates,
            expected_gain=expected_gain,
            expected_cost=expected_cost,
            candidate_size=candidate_size,
        )
        records_built = bridge.n_records_built
        builder_status = builder.builder_status
        builder_provenance = builder.engine_a_input_provenance
        builder_warnings = tuple(dict.fromkeys((*bridge.bridge_warnings, *builder.builder_warnings)))
        engine_input_payload = dict(builder.engine_a_input_payload)
        if engine_input_overrides:
            engine_input_payload.update(engine_input_overrides)
        if engine_input_payload:
            output = run_engine_a(EngineAInput.model_validate(engine_input_payload))
            output_payload = output.model_dump(mode="json")
            decision = _enum_value(output.decision)
            reason_codes = tuple(str(item) for item in output.reason_codes)
            no_trade_reasons = tuple(_enum_value(item) for item in output.no_trade_reasons)
    elif engine_id == "engine_b":
        builder = build_engine_b_input_from_window(
            candidate_id=candidate.candidate_id,
            pair=candidate.pair,
            window_start_ms=window.window_start_ms,
            window_end_ms=window.window_end_ms,
            raw_trade_path=window.raw_trade_path,
            expected_gain=expected_gain,
            expected_cost=expected_cost,
            candidate_size=candidate_size,
        )
        records_built = builder.bridge_result.n_records_built if builder.bridge_result is not None else 0
        builder_status = builder.builder_status
        builder_provenance = builder.engine_b_input_provenance
        builder_warnings = builder.builder_warnings
        engine_input_payload = dict(builder.engine_b_input_payload)
        if engine_input_overrides:
            engine_input_payload.update(engine_input_overrides)
        if engine_input_payload:
            output = run_engine_b(EngineBInput.model_validate(engine_input_payload))
            output_payload = output.model_dump(mode="json")
            decision = _enum_value(output.decision)
            reason_codes = tuple(str(item) for item in output.reason_codes)
            no_trade_reasons = tuple(_enum_value(item) for item in output.no_trade_reasons)
    elif engine_id == "engine_c":
        bridge = build_engine_c_microstructure_inputs_from_window(
            candidate_id=candidate.candidate_id,
            pair=candidate.pair,
            window_start_ms=window.window_start_ms,
            window_end_ms=window.window_end_ms,
            raw_trade_path=window.raw_trade_path,
            raw_book_path=window.raw_book_path,
            raw_book_delta_path=window.raw_book_delta_path,
        )
        builder = build_engine_c_input_from_window(
            candidate_id=candidate.candidate_id,
            pair=candidate.pair,
            window_start_ms=window.window_start_ms,
            window_end_ms=window.window_end_ms,
            raw_trade_path=window.raw_trade_path,
            raw_ohlcv_path=window.raw_ohlcv_path,
            microstructure_partial_payload=bridge.engine_c_partial_input_payload,
            expected_gain=expected_gain,
            expected_cost=expected_cost,
            candidate_size=candidate_size,
        )
        records_built = bridge.n_records_built
        builder_status = builder.builder_status
        builder_provenance = builder.engine_c_input_provenance
        builder_warnings = tuple(dict.fromkeys((*bridge.bridge_warnings, *builder.builder_warnings)))
        engine_input_payload = dict(builder.engine_c_input_payload)
        if engine_input_payload:
            adjusted = apply_build14_shadow_context(
                engine_id=engine_id,
                candidate_id=candidate.candidate_id,
                pair=candidate.pair,
                candidate_payload=payload,
                engine_input_payload=engine_input_payload,
            )
            engine_input_payload = dict(adjusted.adjusted_engine_input_payload)
            if engine_input_overrides:
                engine_input_payload.update(engine_input_overrides)
            output = run_engine_c(EngineCInput.model_validate(engine_input_payload))
            output_payload = output.model_dump(mode="json")
            decision = _enum_value(output.decision)
            reason_codes = tuple(str(item) for item in output.reason_codes)
            no_trade_reasons = tuple(_enum_value(item) for item in output.no_trade_reasons)
    elif engine_id == "engine_d":
        builder = build_engine_d_input_from_window(
            candidate_id=candidate.candidate_id,
            pair=candidate.pair,
            window_start_ms=window.window_start_ms,
            window_end_ms=window.window_end_ms,
            raw_trade_path=window.raw_trade_path,
            raw_ohlcv_path=window.raw_ohlcv_path,
            first_episode_context=_extract_engine_d_first_episode_context(payload),
            expected_gain=expected_gain,
            expected_cost=expected_cost,
            candidate_size=candidate_size,
        )
        records_built = builder.bridge_result.n_records_built if builder.bridge_result is not None else 0
        builder_status = builder.builder_status
        builder_provenance = builder.engine_d_input_provenance
        builder_warnings = builder.builder_warnings
        engine_input_payload = dict(builder.engine_d_input_payload)
        if engine_input_payload:
            adjusted = apply_build14_shadow_context(
                engine_id=engine_id,
                candidate_id=candidate.candidate_id,
                pair=candidate.pair,
                candidate_payload=payload,
                engine_input_payload=engine_input_payload,
            )
            engine_input_payload = dict(adjusted.adjusted_engine_input_payload)
            if engine_input_overrides:
                engine_input_payload.update(engine_input_overrides)
            output = run_engine_d(EngineDInput.model_validate(engine_input_payload))
            output_payload = output.model_dump(mode="json")
            decision = _enum_value(output.decision)
            reason_codes = tuple(str(item) for item in output.reason_codes)
            no_trade_reasons = tuple(_enum_value(item) for item in output.no_trade_reasons)

    return ReconstructedNativeCase(
        engine_id=engine_id,
        candidate_id=candidate.candidate_id,
        pair=candidate.pair,
        builder_status=builder_status,
        builder_provenance=builder_provenance,
        builder_warnings=builder_warnings,
        engine_input_payload=engine_input_payload,
        output_payload=output_payload,
        decision=decision,
        reason_codes=reason_codes,
        no_trade_reasons=no_trade_reasons,
        records_built=records_built,
    )


def _scenario_metadata_rows(asset_root: Path) -> list[dict[str, object]]:
    klines_path = str((asset_root / "klines.jsonl").resolve())
    trades_path = str((asset_root / "trades.jsonl").resolve())
    orderbook_snapshot_path = str((asset_root / "orderbook_snapshot.jsonl").resolve())
    orderbook_delta_path = str((asset_root / "orderbook_delta.jsonl").resolve())
    closed_episode_journal_path = str((asset_root / "closed_episode_journal.jsonl").resolve())
    return [
        {
            "scenario_id": "SCENARIO_A_LONG_PASS_NATIVE",
            "candidate_id": "a-long-pass",
            "engine_id": "engine_a",
            "pair": "BTCUSDT",
            "timeframe": "5m",
            "timestamp_ms": 1_700_100_000_000,
            "window_start_ms": 1_700_099_700_000,
            "window_end_ms": 1_700_100_000_000,
            "planned_notional": 1000.0,
            "raw_ohlcv_path": klines_path,
            "raw_trade_path": trades_path,
            "raw_book_path": orderbook_snapshot_path,
            "raw_book_delta_path": orderbook_delta_path,
        },
        {
            "scenario_id": "SCENARIO_A_NEGATIVE_DIRECTION_BLOCK",
            "candidate_id": "a-negative-direction",
            "engine_id": "engine_a",
            "pair": "BTCUSDT",
            "timeframe": "5m",
            "timestamp_ms": 1_700_110_000_000,
            "window_start_ms": 1_700_109_700_000,
            "window_end_ms": 1_700_110_000_000,
            "planned_notional": 1000.0,
            "raw_ohlcv_path": klines_path,
            "raw_trade_path": trades_path,
            "raw_book_path": orderbook_snapshot_path,
            "raw_book_delta_path": orderbook_delta_path,
        },
        {
            "scenario_id": "SCENARIO_B_EXCESS_PASS",
            "candidate_id": "b-excess-pass",
            "engine_id": "engine_b",
            "pair": "BTCUSDT",
            "timeframe": "1m",
            "timestamp_ms": 1_700_120_000_000,
            "window_start_ms": 1_700_119_940_000,
            "window_end_ms": 1_700_120_000_000,
            "planned_notional": 1000.0,
            "raw_ohlcv_path": klines_path,
            "raw_trade_path": trades_path,
            "raw_book_path": orderbook_snapshot_path,
            "raw_book_delta_path": orderbook_delta_path,
        },
        {
            "scenario_id": "SCENARIO_B_NO_EXCESS",
            "candidate_id": "b-no-excess",
            "engine_id": "engine_b",
            "pair": "BTCUSDT",
            "timeframe": "1m",
            "timestamp_ms": 1_700_130_000_000,
            "window_start_ms": 1_700_129_940_000,
            "window_end_ms": 1_700_130_000_000,
            "planned_notional": 1000.0,
            "raw_ohlcv_path": klines_path,
            "raw_trade_path": trades_path,
            "raw_book_path": orderbook_snapshot_path,
            "raw_book_delta_path": orderbook_delta_path,
        },
        {
            "scenario_id": "SCENARIO_B_COST_FAIL",
            "candidate_id": "b-cost-fail",
            "engine_id": "engine_b",
            "pair": "BTCUSDT",
            "timeframe": "1m",
            "timestamp_ms": 1_700_140_000_000,
            "window_start_ms": 1_700_139_940_000,
            "window_end_ms": 1_700_140_000_000,
            "planned_notional": 1000.0,
            "raw_ohlcv_path": klines_path,
            "raw_trade_path": trades_path,
            "raw_book_path": orderbook_snapshot_path,
            "raw_book_delta_path": orderbook_delta_path,
        },
        {
            "scenario_id": "SCENARIO_C_BREAKOUT_PASS",
            "candidate_id": "c-breakout-pass",
            "engine_id": "engine_c",
            "pair": "BTCUSDT",
            "timeframe": "5m",
            "timestamp_ms": 1_700_150_000_000,
            "window_start_ms": 1_700_149_700_000,
            "window_end_ms": 1_700_150_000_000,
            "planned_notional": 1200.0,
            "raw_ohlcv_path": klines_path,
            "raw_trade_path": trades_path,
            "raw_book_path": orderbook_snapshot_path,
            "raw_book_delta_path": orderbook_delta_path,
        },
        {
            "scenario_id": "SCENARIO_C_NO_BREAKOUT",
            "candidate_id": "c-no-breakout",
            "engine_id": "engine_c",
            "pair": "BTCUSDT",
            "timeframe": "5m",
            "timestamp_ms": 1_700_160_000_000,
            "window_start_ms": 1_700_159_700_000,
            "window_end_ms": 1_700_160_000_000,
            "planned_notional": 1200.0,
            "raw_ohlcv_path": klines_path,
            "raw_trade_path": trades_path,
            "raw_book_path": orderbook_snapshot_path,
            "raw_book_delta_path": orderbook_delta_path,
        },
        {
            "scenario_id": "SCENARIO_D_REENTRY_PASS",
            "candidate_id": "d-reentry-pass",
            "engine_id": "engine_d",
            "pair": "BTCUSDT",
            "timeframe": "5m",
            "timestamp_ms": 1_700_170_000_000,
            "window_start_ms": 1_700_169_700_000,
            "window_end_ms": 1_700_170_000_000,
            "planned_notional": 800.0,
            "closed_episode_journal_path": closed_episode_journal_path,
            "raw_ohlcv_path": klines_path,
            "raw_trade_path": trades_path,
            "raw_book_path": orderbook_snapshot_path,
            "raw_book_delta_path": orderbook_delta_path,
        },
        {
            "scenario_id": "SCENARIO_D_NO_HISTORY",
            "candidate_id": "d-no-history",
            "engine_id": "engine_d",
            "pair": "BTCUSDT",
            "timeframe": "5m",
            "timestamp_ms": 1_700_180_000_000,
            "window_start_ms": 1_700_179_700_000,
            "window_end_ms": 1_700_180_000_000,
            "planned_notional": 800.0,
            "closed_episode_journal_path": closed_episode_journal_path,
            "raw_ohlcv_path": klines_path,
            "raw_trade_path": trades_path,
            "raw_book_path": orderbook_snapshot_path,
            "raw_book_delta_path": orderbook_delta_path,
        },
    ]


def ensure_synthetic_strategy_ladder_canary_fixture(asset_root: Path | str) -> Path:
    root = Path(asset_root).resolve()
    root.mkdir(parents=True, exist_ok=True)

    klines: list[dict[str, object]] = []
    trades: list[dict[str, object]] = []
    snapshots: list[dict[str, object]] = []
    deltas: list[dict[str, object]] = []
    closed_episodes: list[dict[str, object]] = [
        {
            "episode_id": "episode-btc-01",
            "pair": "BTCUSDT",
            "engine_id": "engine_a",
            "direction": "buy",
            "entry_price": 99.5,
            "exit_price": 101.0,
            "close_reason": "time_stop",
            "closed_at_ms": 1_700_169_000_000,
            "prior_trade_quality": 0.82,
        }
    ]

    # Engine A favorable long
    for i in range(10):
        ts = 1_700_099_700_000 + i * 30_000
        base = 100.0 + i * 0.15
        klines.append(_bar(scenario_id="SCENARIO_A_LONG_PASS_NATIVE", pair="BTCUSDT", timeframe="5m", ts_ms=ts, o=base, h=base + 0.18, l=base - 0.04, c=base + 0.12, v=15.0))
    # Engine A negative direction
    for i in range(10):
        ts = 1_700_109_700_000 + i * 30_000
        base = 104.0 - i * 0.15
        klines.append(_bar(scenario_id="SCENARIO_A_NEGATIVE_DIRECTION_BLOCK", pair="BTCUSDT", timeframe="5m", ts_ms=ts, o=base, h=base + 0.05, l=base - 0.18, c=base - 0.12, v=15.0))
    # Engine B excess pass, negative z
    for price, ts in zip((100.0, 100.0, 100.0, 100.0, 98.4), range(1_700_119_940_000, 1_700_120_000_001, 15_000), strict=False):
        trades.append(_trade(scenario_id="SCENARIO_B_EXCESS_PASS", pair="BTCUSDT", ts_ms=ts, price=price, qty=0.5, side="sell"))
    # Engine B no excess
    for price, ts in zip((100.0, 100.0, 100.0, 100.0, 99.45), range(1_700_129_940_000, 1_700_130_000_001, 15_000), strict=False):
        trades.append(_trade(scenario_id="SCENARIO_B_NO_EXCESS", pair="BTCUSDT", ts_ms=ts, price=price, qty=0.5, side="sell"))
    # Engine B cost fail
    for price, ts in zip((100.0, 100.0, 100.0, 100.0, 98.4), range(1_700_139_940_000, 1_700_140_000_001, 15_000), strict=False):
        trades.append(_trade(scenario_id="SCENARIO_B_COST_FAIL", pair="BTCUSDT", ts_ms=ts, price=price, qty=0.5, side="sell"))
    # Engine C breakout pass
    for i in range(6):
        ts = 1_700_149_520_000 + i * 30_000
        klines.append(_bar(scenario_id="SCENARIO_C_BREAKOUT_PASS", pair="BTCUSDT", timeframe="5m", ts_ms=ts, o=100.0, h=100.2, l=99.8, c=100.0, v=10.0))
    for i in range(4):
        ts = 1_700_149_700_000 + i * 30_000
        base = 100.4 + i * 0.5
        klines.append(_bar(scenario_id="SCENARIO_C_BREAKOUT_PASS", pair="BTCUSDT", timeframe="5m", ts_ms=ts, o=base, h=base + 0.3, l=base - 0.05, c=base + 0.25, v=22.0))
    for i in range(12):
        ts = 1_700_149_700_000 + i * 20_000
        price = 100.2 + i * 0.12
        trades.append(_trade(scenario_id="SCENARIO_C_BREAKOUT_PASS", pair="BTCUSDT", ts_ms=ts, price=price, qty=0.6, side="buy"))
    # Engine C no breakout
    for i in range(10):
        ts = 1_700_159_700_000 + i * 30_000
        base = 101.0 + (0.02 if i % 2 == 0 else -0.02)
        klines.append(_bar(scenario_id="SCENARIO_C_NO_BREAKOUT", pair="BTCUSDT", timeframe="5m", ts_ms=ts, o=base, h=base + 0.05, l=base - 0.05, c=base + 0.01, v=8.0))
    for i in range(8):
        ts = 1_700_159_720_000 + i * 20_000
        trades.append(_trade(scenario_id="SCENARIO_C_NO_BREAKOUT", pair="BTCUSDT", ts_ms=ts, price=101.0, qty=0.4, side="buy"))
    # Engine D re-entry pass
    for i in range(10):
        ts = 1_700_169_700_000 + i * 30_000
        base = 101.0 + i * 0.08
        klines.append(_bar(scenario_id="SCENARIO_D_REENTRY_PASS", pair="BTCUSDT", timeframe="5m", ts_ms=ts, o=base, h=base + 0.12, l=base - 0.06, c=base + 0.07, v=14.0))
    for i in range(10):
        ts = 1_700_179_700_000 + i * 30_000
        base = 101.5 + (0.04 if i % 2 == 0 else -0.04)
        klines.append(_bar(scenario_id="SCENARIO_D_NO_HISTORY", pair="BTCUSDT", timeframe="5m", ts_ms=ts, o=base, h=base + 0.08, l=base - 0.08, c=base + 0.03, v=11.0))

    snapshots.extend(
        [
            _book_snapshot(
                scenario_id="SCENARIO_A_LONG_PASS_NATIVE",
                ts_ms=1_700_100_000_000,
                update_id=1,
                bids=[[100.00, 5.0], [99.95, 7.0], [99.90, 10.0]],
                asks=[[100.10, 5.0], [100.15, 7.0], [100.20, 10.0]],
            ),
            _book_snapshot(
                scenario_id="SCENARIO_A_NEGATIVE_DIRECTION_BLOCK",
                ts_ms=1_700_110_000_000,
                update_id=10,
                bids=[[100.00, 5.0], [99.95, 7.0], [99.90, 10.0]],
                asks=[[100.10, 5.0], [100.15, 7.0], [100.20, 10.0]],
            ),
            _book_snapshot(
                scenario_id="SCENARIO_C_BREAKOUT_PASS",
                ts_ms=1_700_150_000_000,
                update_id=20,
                bids=[[101.90, 4.0], [101.80, 6.0], [101.70, 8.0]],
                asks=[[102.00, 4.0], [102.10, 6.0], [102.20, 8.0]],
            ),
            _book_snapshot(
                scenario_id="SCENARIO_C_NO_BREAKOUT",
                ts_ms=1_700_160_000_000 - 70 * 60 * 1000,
                update_id=30,
                bids=[[101.00, 4.0], [100.95, 6.0], [100.90, 8.0]],
                asks=[[101.10, 4.0], [101.15, 6.0], [101.20, 8.0]],
            ),
            _book_snapshot(
                scenario_id="SCENARIO_D_REENTRY_PASS",
                ts_ms=1_700_170_000_000,
                update_id=40,
                bids=[[101.80, 4.0], [101.75, 6.0], [101.70, 8.0]],
                asks=[[101.90, 4.0], [101.95, 6.0], [102.00, 8.0]],
            ),
        ]
    )
    deltas.extend(
        [
            _book_delta(
                scenario_id="SCENARIO_A_LONG_PASS_NATIVE",
                ts_ms=1_700_099_995_000,
                update_id=2,
                bids=[[100.00, 5.0]],
                asks=[[100.10, 5.0]],
            ),
            _book_delta(
                scenario_id="SCENARIO_C_BREAKOUT_PASS",
                ts_ms=1_700_149_980_000,
                update_id=21,
                bids=[[101.92, 4.5]],
                asks=[[102.00, 4.0]],
            ),
            _book_delta(
                scenario_id="SCENARIO_C_BREAKOUT_PASS",
                ts_ms=1_700_149_990_000,
                update_id=22,
                bids=[[101.94, 4.5]],
                asks=[[102.01, 4.0]],
            ),
        ]
    )

    metadata_rows = _scenario_metadata_rows(root)
    expected_oracle = {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "scenarios": [
            {
                "scenario_id": "SCENARIO_A_LONG_PASS_NATIVE",
                "candidate_id": "a-long-pass",
                "engine_id": "engine_a",
                "expected_decision": "emit",
                "expected_reason_codes": (),
                "expected_builder_status": "ENGINE_A_INPUT_BUILDER_READY",
                "expected_edge_truth_status": "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",
                "expected_gain_decimal": 0.0032,
                "expected_cost_decimal": 0.00068,
            },
            {
                "scenario_id": "SCENARIO_A_NEGATIVE_DIRECTION_BLOCK",
                "candidate_id": "a-negative-direction",
                "engine_id": "engine_a",
                "expected_decision": "no_trade",
                "expected_reason_codes": ("engine_internal.engine_a.direction.non_long", "engine_a.input.non_long_direction"),
                "expected_builder_status": "ENGINE_A_INPUT_BUILDER_READY",
                "expected_edge_truth_status": "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",
                "expected_gain_decimal": 0.0032,
                "expected_cost_decimal": 0.00068,
            },
            {
                "scenario_id": "SCENARIO_B_EXCESS_PASS",
                "candidate_id": "b-excess-pass",
                "engine_id": "engine_b",
                "expected_decision": "emit",
                "expected_reason_codes": (),
                "expected_builder_status": "ENGINE_B_INPUT_BUILDER_READY",
                "expected_edge_truth_status": "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",
                "expected_gain_decimal": 0.0030,
                "expected_cost_decimal": 0.00068,
            },
            {
                "scenario_id": "SCENARIO_B_NO_EXCESS",
                "candidate_id": "b-no-excess",
                "engine_id": "engine_b",
                "expected_decision": "no_trade",
                "expected_reason_codes": ("engine_internal.engine_b.excess.no_excess", "engine_b.excess.no_excess"),
                "expected_builder_status": "ENGINE_B_INPUT_BUILDER_READY",
                "expected_edge_truth_status": "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",
                "expected_gain_decimal": 0.0030,
                "expected_cost_decimal": 0.00068,
            },
            {
                "scenario_id": "SCENARIO_B_COST_FAIL",
                "candidate_id": "b-cost-fail",
                "engine_id": "engine_b",
                "expected_decision": "no_trade",
                "expected_reason_codes": ("economics.engine_b.cost.infeasible", "break_even_not_cleared"),
                "expected_builder_status": "ENGINE_B_INPUT_BUILDER_READY",
                "expected_edge_truth_status": "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",
                "expected_gain_decimal": 0.0011,
                "expected_cost_decimal": 0.00068,
            },
            {
                "scenario_id": "SCENARIO_C_BREAKOUT_PASS",
                "candidate_id": "c-breakout-pass",
                "engine_id": "engine_c",
                "expected_decision": "emit",
                "expected_reason_codes": (),
                "expected_builder_status": "ENGINE_C_INPUT_BUILDER_READY",
                "expected_edge_truth_status": "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",
                "expected_gain_decimal": 0.012,
                "expected_cost_decimal": 0.0025,
            },
            {
                "scenario_id": "SCENARIO_C_NO_BREAKOUT",
                "candidate_id": "c-no-breakout",
                "engine_id": "engine_c",
                "expected_decision": "no_trade",
                "expected_reason_codes": ("engine_c.no_trade.non_long_breakout",),
                "expected_builder_status": "ENGINE_C_INPUT_BUILDER_NO_BREAKOUT",
                "expected_edge_truth_status": "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",
                "expected_gain_decimal": 0.0042,
                "expected_cost_decimal": 0.00068,
            },
            {
                "scenario_id": "SCENARIO_D_REENTRY_PASS",
                "candidate_id": "d-reentry-pass",
                "engine_id": "engine_d",
                "expected_decision": "emit",
                "expected_reason_codes": (),
                "expected_builder_status": "ENGINE_D_INPUT_BUILDER_READY_WITH_FIRST_EPISODE",
                "expected_edge_truth_status": "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",
                "expected_gain_decimal": 0.009,
                "expected_cost_decimal": 0.002,
            },
            {
                "scenario_id": "SCENARIO_D_NO_HISTORY",
                "candidate_id": "d-no-history",
                "engine_id": "engine_d",
                "expected_decision": "no_trade",
                "expected_reason_codes": ("engine_internal.engine_d.history.weak", "engine_d.no_trade.history_weak"),
                "expected_builder_status": "ENGINE_D_INPUT_BUILDER_READY_NO_FIRST_EPISODE",
                "expected_edge_truth_status": "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",
                "expected_gain_decimal": 0.0035,
                "expected_cost_decimal": 0.00068,
            },
        ],
    }

    _write_jsonl(root / "klines.jsonl", klines)
    _write_jsonl(root / "trades.jsonl", trades)
    _write_jsonl(root / "orderbook_snapshot.jsonl", snapshots)
    _write_jsonl(root / "orderbook_delta.jsonl", deltas)
    _write_jsonl(root / "metadata.jsonl", metadata_rows)
    _write_jsonl(root / "closed_episode_journal.jsonl", closed_episodes)
    atomic_write_json(root / "expected_oracle.json", expected_oracle, indent=2)
    return root


def _metadata_by_scenario(asset_root: Path) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    for line in (asset_root / "metadata.jsonl").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        row = json.loads(stripped)
        rows[str(row["scenario_id"])] = row
    return rows


def _candidate_from_metadata(row: dict[str, object]) -> StrategyLadderCandidateEvent:
    scenario_id = str(row["scenario_id"])
    payload: dict[str, object] = {
        "planned_notional": float(row["planned_notional"]),
        "book_depth_levels": 20,
        "book_depth_source_status": "BOOK_DEPTH20_AVAILABLE",
    }
    if scenario_id == "SCENARIO_B_EXCESS_PASS":
        payload["engine_input_overrides"] = {
            "current_price": 98.4,
            "local_mean": 100.0,
            "local_std": 1.0,
            "structure_is_range": 0.7,
            "regime_favorability": 0.7,
            "pair_health": 0.8,
            "data_freshness": 0.9,
            "flow_coherence": 0.8,
            "false_breakout_score": 0.0,
            "volume_anomaly": 0.1,
            "continuation_momentum": 0.1,
        }
    if scenario_id == "SCENARIO_B_NO_EXCESS":
        payload["engine_input_overrides"] = {
            "current_price": 99.45,
            "local_mean": 100.0,
            "local_std": 1.0,
            "structure_is_range": 0.7,
            "regime_favorability": 0.7,
            "pair_health": 0.8,
            "data_freshness": 0.9,
            "flow_coherence": 0.8,
            "volume_anomaly": 0.1,
            "continuation_momentum": 0.1,
        }
    if scenario_id == "SCENARIO_B_COST_FAIL":
        payload["engine_input_overrides"] = {
            "current_price": 98.4,
            "local_mean": 100.0,
            "local_std": 1.0,
            "structure_is_range": 0.7,
            "regime_favorability": 0.7,
            "pair_health": 0.8,
            "data_freshness": 0.9,
            "flow_coherence": 0.8,
            "volume_anomaly": 0.1,
            "continuation_momentum": 0.1,
        }
    if scenario_id == "SCENARIO_C_BREAKOUT_PASS":
        payload["engine_input_overrides"] = _engine_c_emit_payload()
    if scenario_id == "SCENARIO_D_REENTRY_PASS":
        payload["engine_input_overrides"] = _engine_d_emit_payload()
    if scenario_id == "SCENARIO_D_REENTRY_PASS":
        payload.update(
            {
                "origin_context_id": "ctx-btc-01",
                "origin_trade_id": "trade-btc-01",
                "link_type": "prior_trade",
                "first_episode_id": "episode-btc-01",
                "first_episode_engine_id": "engine_a",
                "first_episode_close_reason": "time_stop",
                "consecutive_stop_count": 0,
                "last_fresh_a_detection_at_ns": 1_700_169_900_000_000_000,
                "anti_revenge_state": "reset_required",
                "prior_trade_quality": 0.85,
                "duplication_overlap_with_engine_a": 0.10,
                "marginal_portfolio_gain": 4.0,
                "covered_share_by_engine_a": 0.12,
                "concentration_headroom": 0.78,
                "reentry_lateness": 0.18,
                "structure_reformed_detected": True,
                "reentry_anchor_price": 101.2,
            }
        )
    return StrategyLadderCandidateEvent(
        candidate_id=str(row["candidate_id"]),
        pair=str(row["pair"]),
        timeframe=str(row["timeframe"]),
        engine_id=str(row["engine_id"]),
        strategy_id=str(row["engine_id"]),
        timestamp_ms=int(row["timestamp_ms"]),
        compatibility_payload=payload,
        candidate_source="SYNTHETIC_ENGINE_CANARY",
        candidate_data_source_label="SYNTHETIC_ENGINE_CANARY",
    )


def _window_from_metadata(row: dict[str, object]) -> StrategyLadderRawWindowManifest:
    return StrategyLadderRawWindowManifest(
        candidate_id=str(row["candidate_id"]),
        pair=str(row["pair"]),
        engine_id=str(row["engine_id"]),
        timestamp_ms=int(row["timestamp_ms"]),
        window_start_ms=int(row["window_start_ms"]),
        window_end_ms=int(row["window_end_ms"]),
        raw_trade_path=str(row["raw_trade_path"]),
        raw_book_path=str(row["raw_book_path"]),
        raw_book_delta_path=str(row["raw_book_delta_path"]),
        raw_ohlcv_path=str(row["raw_ohlcv_path"]),
        book_depth_levels_available=20,
        book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
        window_extraction_status="RAW_WINDOW_READY",
        raw_sources_used=("trades", "orderbook", "klines"),
        source_coverage_status="RAW_WINDOW_SOURCE_READY",
    )


def run_synthetic_strategy_ladder_e2e(
    asset_root: Path | str,
    *,
    runtime_mode: str = "TEST",
) -> dict[str, object]:
    root = ensure_synthetic_strategy_ladder_canary_fixture(asset_root)
    oracle = _load_json(root / "expected_oracle.json")
    metadata = _metadata_by_scenario(root)
    results: list[SyntheticScenarioResult] = []

    for scenario in oracle["scenarios"]:
        scenario_id = str(scenario["scenario_id"])
        meta = metadata[scenario_id]
        candidate = _candidate_from_metadata(meta)
        window = _window_from_metadata(meta)
        provenance = _synthetic_provenance(
            expected_edge_bps=float(scenario["expected_gain_decimal"]) * 10_000.0,
            expected_edge_provenance=_CANARY_PROVENANCE,
            spread_bps=4.0,
            slippage_bps=2.0,
            latency_penalty_bps=0.5,
            fee_bps=10.0,
            runtime_mode=runtime_mode,
        )
        case = reconstruct_native_candidate_case(
            candidate=candidate,
            window=window,
            economic_provenance=provenance,
        )
        actual_expected_gain = float(case.engine_input_payload.get("expected_gain") or 0.0)
        actual_expected_cost = float(case.engine_input_payload.get("expected_cost") or 0.0)
        expected_gain = float(scenario["expected_gain_decimal"])
        expected_cost = float(scenario["expected_cost_decimal"])
        results.append(
            SyntheticScenarioResult(
                scenario_id=scenario_id,
                engine_id=str(scenario["engine_id"]),
                expected_decision=str(scenario["expected_decision"]),
                actual_decision=case.decision,
                expected_reason_codes=tuple(str(item) for item in scenario["expected_reason_codes"]),
                actual_reason_codes=case.reason_codes,
                expected_builder_status=str(scenario["expected_builder_status"]),
                actual_builder_status=case.builder_status,
                expected_truth_status=str(scenario["expected_edge_truth_status"]),
                actual_expected_gain=actual_expected_gain,
                actual_expected_cost=actual_expected_cost,
                ok=(
                    case.decision == str(scenario["expected_decision"])
                    and case.builder_status == str(scenario["expected_builder_status"])
                    and all(code in case.reason_codes for code in tuple(str(item) for item in scenario["expected_reason_codes"]))
                    and abs(actual_expected_gain - expected_gain) <= 1e-12
                    and abs(actual_expected_cost - expected_cost) <= 1e-12
                ),
            )
        )

    return {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "runtime_mode": runtime_mode,
        "diagnostic_only": True,
        "scenario_count": len(results),
        "all_ok": all(item.ok for item in results),
        "results": [asdict(item) for item in results],
    }


def _engine_c_emit_payload() -> dict[str, object]:
    return {
        "pair": "BTCUSDT",
        "breakout_strength": 0.88,
        "range_quality": 0.78,
        "compression_quality": 0.74,
        "volume_confirmation": 0.81,
        "followthrough_room": 0.76,
        "extension_pct": 0.24,
        "retrace_risk": 0.18,
        "rejection_wick_ratio": 0.12,
        "regime": "breakout",
        "regime_favorability": 0.80,
        "pair_health": 0.92,
        "data_freshness": 0.95,
        "flow_coherence": 0.79,
        "cumulative_ofi": 24.0,
        "queue_pressure": 0.36,
        "vpin": 0.22,
        "kyle_lambda": 0.0012,
        "continuation_ofi_min": 0.0,
        "continuation_queue_min": 0.0,
        "continuation_vpin_max": 0.35,
        "continuation_kyle_lambda_max": 0.01,
        "expected_gain": 0.012,
        "expected_cost": 0.0025,
        "candidate_size": 1000.0,
        "holding_period": 3.0,
        "entry_price": 105.0,
        "breakout_level": 101.0,
        "range_low": 97.5,
        "range_high": 101.0,
        "realized_vol_current": 2.0 / 105.0,
        "realized_vol_at_break": 2.0 / 105.0,
        "atr": 2.0,
        "engine_a_overlap_ratio": 0.28,
        "marginal_portfolio_gain": 9.2,
        "covered_share_by_engine_a": 0.22,
        "keff_contribution": 0.31,
        "scoring_version": "engine_c.v1",
    }


def _engine_d_emit_payload() -> dict[str, object]:
    return {
        "pair": "BTCUSDT",
        "origin_context_id": "ctx-btc-01",
        "origin_trade_id": "trade-btc-01",
        "link_type": "prior_trade",
        "first_episode_id": "episode-btc-01",
        "first_episode_engine_id": "engine_a",
        "first_episode_close_reason": "time_stop",
        "consecutive_stop_count": 0,
        "last_fresh_a_detection_at_ns": 1_700_000_100_000_000_000,
        "anti_revenge_state": "reset_required",
        "prior_trade_quality": 0.85,
        "reformation_quality": 0.77,
        "pullback_quality": 0.73,
        "continuation_room": 0.70,
        "concentration_headroom": 0.78,
        "marginal_edge": 0.72,
        "reentry_lateness": 0.18,
        "structure_reformed_detected": True,
        "regime": "trending_up",
        "regime_favorability": 0.78,
        "pair_health": 0.90,
        "data_freshness": 0.94,
        "flow_coherence": 0.81,
        "expected_gain": 0.009,
        "expected_cost": 0.0020,
        "candidate_size": 800.0,
        "holding_period": 2.0,
        "entry_price": 104.0,
        "reentry_anchor_price": 101.5,
        "realized_vol_current": 1.8 / 104.0,
        "realized_vol_post_close": 1.8 / 104.0,
        "atr": 1.8,
        "duplication_overlap_with_engine_a": 0.24,
        "marginal_portfolio_gain": 6.0,
        "covered_share_by_engine_a": 0.18,
        "scoring_version": "engine_d.v1",
    }


def _boundary_row(
    *,
    engine_id: str,
    threshold_name: str,
    threshold_value: float,
    threshold_unit: str,
    tested_input_values: list[float],
    derived_metric_name: str,
    derived_metric_values: list[float],
    compared_value_kind: str,
    comparison_expression: str,
    operator_used: str,
    actual_decisions: list[str],
    expected_decisions: list[str],
) -> dict[str, object]:
    return {
        "engine_id": engine_id,
        "threshold_name": threshold_name,
        "threshold_value": threshold_value,
        "threshold_unit": threshold_unit,
        "tested_input_values": tested_input_values,
        "derived_metric_name": derived_metric_name,
        "derived_metric_values": derived_metric_values,
        "tested_values": derived_metric_values,
        "compared_value_kind": compared_value_kind,
        "comparison_expression": comparison_expression,
        "output_decision": actual_decisions,
        "expected_decision": expected_decisions,
        "pass": actual_decisions == expected_decisions,
        "exact_operator_used": operator_used,
        "epsilon_behavior": {
            "below": {
                "input": tested_input_values[0],
                "derived": derived_metric_values[0],
            },
            "at": {
                "input": tested_input_values[1],
                "derived": derived_metric_values[1],
            },
            "above": {
                "input": tested_input_values[2],
                "derived": derived_metric_values[2],
            },
        },
    }


def build_engine_threshold_boundary_report() -> dict[str, object]:
    eps = 1e-9
    rows: list[dict[str, object]] = []

    def _add_row(
        *,
        engine_id: str,
        threshold_name: str,
        threshold_value: float,
        threshold_unit: str,
        tested_input_values: list[float],
        derived_metric_name: str,
        derived_metric_values: list[float],
        compared_value_kind: str,
        comparison_expression: str,
        operator_used: str,
        actual_decisions: list[str],
        expected_decisions: list[str],
    ) -> None:
        rows.append(
            _boundary_row(
                engine_id=engine_id,
                threshold_name=threshold_name,
                threshold_value=threshold_value,
                threshold_unit=threshold_unit,
                tested_input_values=tested_input_values,
                derived_metric_name=derived_metric_name,
                derived_metric_values=derived_metric_values,
                compared_value_kind=compared_value_kind,
                comparison_expression=comparison_expression,
                operator_used=operator_used,
                actual_decisions=actual_decisions,
                expected_decisions=expected_decisions,
            )
        )

    # Engine A min_direction
    a_values = [0.20 - eps, 0.20, 0.20 + eps]
    a_decisions: list[str] = []
    a_derived_direction: list[float] = []
    for value in a_values:
        result = detect_structure(
            StructureInput(
                pair="BTCUSDT",
                direction_score=value,
                continuation_score=0.80,
                structure_quality=0.80,
                zone_proximity=0.80,
                trend_stability=0.80,
            )
        )
        a_decisions.append(_enum_value(result.verdict))
        a_derived_direction.append(float(value))
    _add_row(
        engine_id="engine_a",
        threshold_name="min_direction",
        threshold_value=0.20,
        threshold_unit="signed_score_-1_to_1",
        tested_input_values=a_values,
        derived_metric_name="direction_score",
        derived_metric_values=a_derived_direction,
        compared_value_kind="INPUT_VALUE",
        comparison_expression="direction_score >= 0.20",
        operator_used="< blocks ; >= survives",
        actual_decisions=a_decisions,
        expected_decisions=["unfavorable", "favorable", "favorable"],
    )

    a_marginal_inputs = [0.9 - 4 * eps, 0.9, 0.9 + 4 * eps]
    a_marginal_decisions: list[str] = []
    a_marginal_scores: list[float] = []
    for continuation in a_marginal_inputs:
        result = detect_structure(
            StructureInput(
                pair="BTCUSDT",
                direction_score=0.25,
                continuation_score=continuation,
                structure_quality=0.0,
                zone_proximity=0.0,
                trend_stability=0.0,
            )
        )
        a_marginal_decisions.append(_enum_value(result.verdict))
        a_marginal_scores.append(float(result.structure_score))
    _add_row(
        engine_id="engine_a",
        threshold_name="marginal",
        threshold_value=0.30,
        threshold_unit="score_0_to_1",
        tested_input_values=a_marginal_inputs,
        derived_metric_name="structure_score",
        derived_metric_values=a_marginal_scores,
        compared_value_kind="DERIVED_SCORE",
        comparison_expression="structure_score >= 0.30",
        operator_used="score >= threshold",
        actual_decisions=a_marginal_decisions,
        expected_decisions=["unfavorable", "marginal", "marginal"],
    )

    a_favorable_inputs = [0.3 - 4 * eps, 0.3, 0.3 + 4 * eps]
    a_favorable_decisions: list[str] = []
    a_favorable_scores: list[float] = []
    for continuation in a_favorable_inputs:
        result = detect_structure(
            StructureInput(
                pair="BTCUSDT",
                direction_score=0.25,
                continuation_score=continuation,
                structure_quality=1.0,
                zone_proximity=1.0,
                trend_stability=1.0,
            )
        )
        a_favorable_decisions.append(_enum_value(result.verdict))
        a_favorable_scores.append(float(result.structure_score))
    _add_row(
        engine_id="engine_a",
        threshold_name="favorable",
        threshold_value=0.60,
        threshold_unit="score_0_to_1",
        tested_input_values=a_favorable_inputs,
        derived_metric_name="structure_score",
        derived_metric_values=a_favorable_scores,
        compared_value_kind="DERIVED_SCORE",
        comparison_expression="structure_score >= 0.60",
        operator_used="score >= threshold",
        actual_decisions=a_favorable_decisions,
        expected_decisions=["marginal", "favorable", "favorable"],
    )

    # Engine B z thresholds
    for threshold_name, threshold_value, expected_decisions in (
        ("z_marginal", 1.0, ["no_excess", "marginal", "marginal"]),
        ("z_star", 1.5, ["marginal", "exploitable", "exploitable"]),
    ):
        tested = [
            -(threshold_value - eps),
            -threshold_value,
            -(threshold_value + eps),
        ]
        actual: list[str] = []
        derived_abs_z: list[float] = []
        for value in tested:
            result = detect_excess(
                ExcessInput(
                    pair="BTCUSDT",
                    z_score=value,
                    z_score_valid=True,
                    structure_is_range=0.5,
                    recent_expansion=0.0,
                )
            )
            actual.append(_enum_value(result.verdict))
            derived_abs_z.append(float(result.abs_z))
        _add_row(
            engine_id="engine_b",
            threshold_name=threshold_name,
            threshold_value=threshold_value,
            threshold_unit="sigma_units",
            tested_input_values=tested,
            derived_metric_name="abs_z_score",
            derived_metric_values=derived_abs_z,
            compared_value_kind="DERIVED_SCORE",
            comparison_expression=f"abs(z_score) >= {threshold_value}",
            operator_used="< no_excess ; >= threshold survives",
            actual_decisions=actual,
            expected_decisions=expected_decisions,
        )

    for threshold_name, expected_gain_values, expected_decisions in (
        (
            "delta_safe",
            [0.0010115 - eps, 0.0010115, 0.0010115 + eps],
            ["infeasible", "infeasible", "feasible"],
        ),
    ):
        actual: list[str] = []
        derived_gain_minus_cost: list[float] = []
        for tested in expected_gain_values:
            result = check_cost_feasibility_b(
                CostInputB(
                    pair="BTCUSDT",
                    expected_gain=tested,
                    expected_cost=0.0002115,
                    candidate_size=100.0,
                    holding_period=2.0,
                    delta_safe=0.0008,
                    ce_min=0.0002,
                )
                )
            actual.append(_enum_value(result.verdict))
            derived_gain_minus_cost.append(float(tested - 0.0002115))
        _add_row(
            engine_id="engine_b",
            threshold_name=threshold_name,
            threshold_value=0.0008,
            threshold_unit="decimal_return",
            tested_input_values=expected_gain_values,
            derived_metric_name="expected_gain_minus_expected_cost",
            derived_metric_values=derived_gain_minus_cost,
            compared_value_kind="COST_DECIMAL",
            comparison_expression="(expected_gain - expected_cost) > delta_safe",
            operator_used="expected_gain <= break_even blocks ; CE < ce_min marginal",
            actual_decisions=actual,
            expected_decisions=expected_decisions,
        )

    ce_gain_tested = [0.0012115 - eps, 0.0012115, 0.0012115 + eps]
    ce_actual: list[str] = []
    ce_derived_values: list[float] = []
    for gain in ce_gain_tested:
        result = check_cost_feasibility_b(
            CostInputB(
                pair="BTCUSDT",
                expected_gain=gain,
                expected_cost=0.0002115,
                candidate_size=100.0,
                holding_period=5.0,
                delta_safe=0.0008,
                ce_min=0.0002,
            )
        )
        ce_actual.append(_enum_value(result.verdict))
        ce_derived_values.append(float((gain - 0.0002115) / 5.0))
    _add_row(
        engine_id="engine_b",
        threshold_name="ce_min",
        threshold_value=0.0002,
        threshold_unit="decimal_return_per_hour",
        tested_input_values=ce_gain_tested,
        derived_metric_name="ce_expected",
        derived_metric_values=ce_derived_values,
        compared_value_kind="COST_DECIMAL",
        comparison_expression="ce_expected >= ce_min once expected_gain > break_even",
        operator_used="CE < ce_min marginal ; CE >= ce_min feasible once break-even is cleared",
        actual_decisions=ce_actual,
        expected_decisions=["marginal", "feasible", "feasible"],
    )

    # Engine C thresholds
    c_payload = _engine_c_emit_payload()
    tested_breakout_strength = [0.55 - eps, 0.55, 0.55 + eps]
    c_strength_decisions: list[str] = []
    c_strength_values: list[float] = []
    for value in tested_breakout_strength:
        payload = dict(c_payload)
        payload["breakout_strength"] = value
        output = run_engine_c(EngineCInput.model_validate(payload))
        c_strength_decisions.append(_enum_value(output.decision))
        c_strength_values.append(float(value))
    _add_row(
        engine_id="engine_c",
        threshold_name="breakout_strength_min",
        threshold_value=0.55,
        threshold_unit="score_0_to_1",
        tested_input_values=tested_breakout_strength,
        derived_metric_name="breakout_strength",
        derived_metric_values=c_strength_values,
        compared_value_kind="INPUT_VALUE",
        comparison_expression="breakout_strength >= 0.55",
        operator_used="< blocks ; >= survives",
        actual_decisions=c_strength_decisions,
        expected_decisions=["no_trade", "emit", "emit"],
    )

    tested_range_quality = [0.50 - eps, 0.50, 0.50 + eps]
    c_range_decisions: list[str] = []
    c_range_values: list[float] = []
    for value in tested_range_quality:
        payload = dict(c_payload)
        payload["range_quality"] = value
        output = run_engine_c(EngineCInput.model_validate(payload))
        c_range_decisions.append(_enum_value(output.decision))
        c_range_values.append(float(value))
    _add_row(
        engine_id="engine_c",
        threshold_name="range_quality_min",
        threshold_value=0.50,
        threshold_unit="score_0_to_1",
        tested_input_values=tested_range_quality,
        derived_metric_name="range_quality",
        derived_metric_values=c_range_values,
        compared_value_kind="INPUT_VALUE",
        comparison_expression="range_quality >= 0.50",
        operator_used="< blocks ; >= survives",
        actual_decisions=c_range_decisions,
        expected_decisions=["no_trade", "emit", "emit"],
    )

    breakout_score_tested = [0.8428571420, 0.8428571430, 0.8428571440]
    c_score_decisions: list[str] = []
    c_score_values: list[float] = []
    for value in breakout_score_tested:
        payload = dict(c_payload)
        payload["breakout_strength"] = value
        payload["range_quality"] = 0.5
        payload["compression_quality"] = 0.5
        payload["volume_confirmation"] = 0.5
        inputs = EngineCInput.model_validate(payload)
        output = run_engine_c(inputs)
        c_score_decisions.append(_enum_value(output.decision))
        c_score_values.append(float(compute_breakout_score(inputs)))
    _add_row(
        engine_id="engine_c",
        threshold_name="breakout_score_min",
        threshold_value=0.62,
        threshold_unit="score_0_to_1",
        tested_input_values=breakout_score_tested,
        derived_metric_name="breakout_score",
        derived_metric_values=c_score_values,
        compared_value_kind="DERIVED_SCORE",
        comparison_expression="breakout_score >= 0.62",
        operator_used="< blocks ; >= survives",
        actual_decisions=c_score_decisions,
        expected_decisions=["no_trade", "emit", "emit"],
    )

    fake_risk_tested = [0.2222222220, 0.2222222230, 0.2222222240]
    c_fake_decisions: list[str] = []
    c_fake_values: list[float] = []
    for value in fake_risk_tested:
        payload = dict(c_payload)
        payload["retrace_risk"] = value
        payload["rejection_wick_ratio"] = 1.0
        payload["volume_confirmation"] = 0.0
        inputs = EngineCInput.model_validate(payload)
        output = run_engine_c(inputs)
        c_fake_decisions.append(_enum_value(output.decision))
        c_fake_values.append(float(compute_fake_breakout_risk(inputs)))
    _add_row(
        engine_id="engine_c",
        threshold_name="fake_breakout_risk_max",
        threshold_value=0.65,
        threshold_unit="score_0_to_1",
        tested_input_values=fake_risk_tested,
        derived_metric_name="fake_breakout_risk",
        derived_metric_values=c_fake_values,
        compared_value_kind="RISK_SCORE",
        comparison_expression="fake_breakout_risk < 0.65",
        operator_used=">= blocks ; < survives",
        actual_decisions=c_fake_decisions,
        expected_decisions=["emit", "no_trade", "no_trade"],
    )

    # Engine D thresholds
    d_payload = _engine_d_emit_payload()
    history_tested = [0.590909090, 0.590909091, 0.590909092]
    d_history_decisions: list[str] = []
    d_history_values: list[float] = []
    for value in history_tested:
        payload = dict(d_payload)
        payload["prior_trade_quality"] = value
        payload["pair_health"] = 0.5
        payload["data_freshness"] = 0.5
        inputs = EngineDInput.model_validate(payload)
        output = run_engine_d(inputs)
        d_history_decisions.append(_enum_value(output.decision))
        d_history_values.append(float(compute_history_score(inputs)))
    _add_row(
        engine_id="engine_d",
        threshold_name="history_min",
        threshold_value=0.55,
        threshold_unit="score_0_to_1",
        tested_input_values=history_tested,
        derived_metric_name="history_score",
        derived_metric_values=d_history_values,
        compared_value_kind="DERIVED_SCORE",
        comparison_expression="history_score >= 0.55",
        operator_used="< blocks ; >= survives",
        actual_decisions=d_history_decisions,
        expected_decisions=["no_trade", "emit", "emit"],
    )

    reform_tested = [0.566666666, 0.566666667, 0.566666668]
    d_reform_decisions: list[str] = []
    d_reform_values: list[float] = []
    for value in reform_tested:
        payload = dict(d_payload)
        payload["reformation_quality"] = value
        payload["pullback_quality"] = 0.5
        payload["regime_favorability"] = 0.7
        payload["pair_health"] = 0.7
        payload["data_freshness"] = 0.7
        payload["flow_coherence"] = 0.7
        inputs = EngineDInput.model_validate(payload)
        output = run_engine_d(inputs)
        d_reform_decisions.append(_enum_value(output.decision))
        context_score = compute_context_score_d(inputs)
        d_reform_values.append(float(compute_reformation_score(inputs, context_score=context_score)))
    _add_row(
        engine_id="engine_d",
        threshold_name="reformation_min",
        threshold_value=0.58,
        threshold_unit="score_0_to_1",
        tested_input_values=reform_tested,
        derived_metric_name="reformation_score",
        derived_metric_values=d_reform_values,
        compared_value_kind="DERIVED_SCORE",
        comparison_expression="reformation_score >= 0.58",
        operator_used="< blocks ; >= survives",
        actual_decisions=d_reform_decisions,
        expected_decisions=["no_trade", "emit", "emit"],
    )

    concentration_tested = [0.066666666 + eps, 0.066666666666, 0.066666666 - eps]
    d_concentration_decisions: list[str] = []
    d_concentration_values: list[float] = []
    for headroom in concentration_tested:
        payload = dict(d_payload)
        payload["concentration_headroom"] = headroom
        payload["reentry_lateness"] = 0.2
        inputs = EngineDInput.model_validate(payload)
        output = run_engine_d(inputs)
        d_concentration_decisions.append(_enum_value(output.decision))
        d_concentration_values.append(float(resolve_engine_d_context(inputs)["concentration_risk"]))
    _add_row(
        engine_id="engine_d",
        threshold_name="concentration_max",
        threshold_value=0.64,
        threshold_unit="score_0_to_1",
        tested_input_values=concentration_tested,
        derived_metric_name="concentration_risk",
        derived_metric_values=d_concentration_values,
        compared_value_kind="RISK_SCORE",
        comparison_expression="concentration_risk < 0.64",
        operator_used=">= blocks ; < survives",
        actual_decisions=d_concentration_decisions,
        expected_decisions=["emit", "no_trade", "no_trade"],
    )

    return {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
    }


def _workflow_run_dir(workflow_root: Path) -> Path:
    return (
        workflow_root
        / "phase_b2_detailed_replay"
        / "backtest_strategy_ladder"
        / workflow_root.name
    )


def _workflow_b1_candidate_events_path(workflow_root: Path) -> Path:
    return (
        workflow_root
        / "phase_b1_candidate_discovery"
        / "backtest_strategy_ladder"
        / workflow_root.name
        / "fast_candidates"
        / "candidate_events.jsonl"
    )


def _workflow_materialized_candidates_path(workflow_root: Path) -> Path:
    return _workflow_run_dir(workflow_root) / "fast_candidates" / "candidate_events.jsonl"


def _workflow_raw_window_map(
    workflow_root: Path,
) -> dict[str, StrategyLadderRawWindowManifest]:
    run_dir = _workflow_run_dir(workflow_root)
    manifests = load_strategy_ladder_raw_window_manifests(run_dir / "candidate_replay_windows")
    if not manifests:
        manifests = load_strategy_ladder_raw_window_manifests(run_dir / "raw_windows")
    return {manifest.candidate_id: manifest for manifest in manifests}


def _economic_provenance_from_payload(payload: dict[str, object]) -> EconomicProvenance:
    return EconomicProvenance(
        expected_edge_bps=float(payload.get("expected_edge_bps") or 0.0),
        expected_edge_provenance=str(payload.get("expected_edge_provenance") or ""),
        spread_bps=float(payload.get("spread_bps") or 0.0),
        spread_provenance=str(
            payload.get("spread_provenance")
            or payload.get("economic_provenance")
            or ""
        ),
        slippage_bps=float(payload.get("slippage_bps") or 0.0),
        slippage_provenance=str(
            payload.get("slippage_provenance")
            or payload.get("impact_source_status")
            or ""
        ),
        latency_penalty_bps=float(payload.get("latency_penalty_bps") or 0.0),
        latency_provenance="STATIC_CONSERVATIVE_VENUE_MODEL",
        fee_bps=float(payload.get("fee_bps") or 0.0),
        fee_provenance=str(payload.get("fee_source_status") or ""),
        measurement_warnings=tuple(str(item) for item in tuple(payload.get("economic_measurement_warnings") or ())),
        expected_edge_model_status=str(payload.get("expected_edge_model_status") or "EXPECTED_EDGE_MODEL_NOT_USED"),
        expected_edge_model_artifact_hash=payload.get("expected_edge_model_artifact_hash"),
        expected_edge_model_feature_hash=payload.get("expected_edge_model_feature_hash"),
    )


_FEATURE_METADATA_CONTROL_KEYS = frozenset(
    {
        "proxy_or_measured_override",
        "source_status",
        "truth_status",
        "block_reason",
        "unclassified_reason",
        "measured_required_failure_reason",
        "forced_invalid_reason",
    }
)


def _source_status_bucket(source_status: str) -> str:
    normalized = str(source_status or "").strip().upper()
    if not normalized:
        return "unknown"
    if normalized in {
        "SPREAD_MEASURED_FROM_BOOK",
        "SLIPPAGE_ESTIMATED_FROM_DEPTH20",
    }:
        return "measured"
    if "UNCLASSIFIED" in normalized or normalized.startswith("UNKNOWN"):
        return "unknown"
    if "STALE" in normalized:
        return "stale"
    if any(token in normalized for token in ("BLOCKED", "NOT_PROVEN", "MISSING")):
        return "blocked"
    if normalized in {"FULLY_MEASURED_COST", "PARTIALLY_MEASURED_COST"}:
        return "measured"
    if normalized.startswith(("MEASURED_", "GOVERNED_", "STATIC_CONSERVATIVE_")):
        return "measured"
    if any(token in normalized for token in ("PROXY", "DEFAULT", "TO_CALIBRATE", "FALLBACK")):
        return "proxy"
    return "unknown"


def _usage_from_cost_truth_status(cost_truth_status: str) -> str:
    if cost_truth_status == "FULLY_MEASURED_COST":
        return "measured"
    if cost_truth_status == "STALE_AUDIT_ONLY_COST":
        return "stale_audit_only"
    if cost_truth_status == "COST_MEASUREMENT_BLOCKED":
        return "blocked_missing_measurement"
    if cost_truth_status == "COST_PROVENANCE_UNCLASSIFIED":
        return "unclassified"
    if cost_truth_status == "PROXY_COST":
        return "proxy_audit_only"
    return "partially_measured_audit_only"


def _book_staleness_ms(
    *,
    candidate: StrategyLadderCandidateEvent,
    window: StrategyLadderRawWindowManifest | None,
) -> int | None:
    if window is None:
        return None
    return max(int(candidate.timestamp_ms or 0) - int(window.window_end_ms or 0), 0)


def _expected_gain_audit_fields(
    *,
    payload: dict[str, object],
    expected_gain_used_decimal: float,
    runtime_mode: str,
) -> dict[str, object]:
    source_status = str(payload.get("expected_edge_provenance") or "").strip()
    truth_status = str(payload.get("expected_edge_truth_status") or "").strip()
    if not truth_status:
        truth_status = expected_edge_backtest_truth_status(source_status)
    proxy_decimal = float(payload.get("expected_edge_bps") or 0.0) / 10_000.0
    runtime = runtime_mode.strip().upper()
    block_reason = ""
    if source_status == _CANARY_PROVENANCE and runtime != "TEST":
        truth_status = "EXPECTED_EDGE_PROXY_BLOCKED"
        block_reason = "EXPECTED_EDGE_SYNTHETIC_CANARY_FORBIDDEN_OUTSIDE_TEST"
    elif truth_status != "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH":
        block_reason = truth_status or "EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH"
    proxy_or_measured = (
        "measured"
        if truth_status == "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH"
        else "proxy"
    )
    return {
        "expected_gain_proxy_decimal": proxy_decimal,
        "expected_gain_used_decimal": float(expected_gain_used_decimal),
        "expected_gain_source_status": source_status,
        "expected_gain_truth_status": truth_status,
        "expected_gain_block_reason": block_reason,
        "proxy_or_measured_override": proxy_or_measured,
        "source_status": source_status,
        "truth_status": truth_status,
        "block_reason": (
            f"proxy_used_as_truth_in_b2:{block_reason}"
            if block_reason
            else ""
        ),
    }


def _expected_cost_audit_fields(
    *,
    payload: dict[str, object],
    expected_cost_used_decimal: float,
    book_staleness_ms: int | None,
) -> dict[str, object]:
    measured_spread_report = (
        dict(payload.get("measured_spread_report"))
        if isinstance(payload.get("measured_spread_report"), dict)
        else {}
    )
    measured_slippage_report = (
        dict(payload.get("measured_slippage_report"))
        if isinstance(payload.get("measured_slippage_report"), dict)
        else {}
    )
    spread_bps_measured = payload.get("spread_bps_measured")
    if spread_bps_measured is None:
        spread_bps_measured = measured_spread_report.get("spread_bps")
    slippage_bps_measured = payload.get("slippage_bps_measured")
    if slippage_bps_measured is None:
        slippage_bps_measured = measured_slippage_report.get("walk_cost_bps")
    spread_bps = float(
        spread_bps_measured
        if spread_bps_measured is not None
        else payload.get("spread_bps")
        or 0.0
    )
    slippage_bps = float(
        slippage_bps_measured
        if slippage_bps_measured is not None
        else payload.get("slippage_bps")
        or 0.0
    )
    latency_penalty_bps = float(payload.get("latency_penalty_bps") or 0.0)
    fee_bps = float(payload.get("fee_bps") or 0.0)
    spread_source_status = str(
        payload.get("spread_source_status")
        or measured_spread_report.get("status")
        or payload.get("spread_provenance")
        or ""
    ).strip()
    slippage_source_status = str(
        payload.get("slippage_source_status")
        or measured_slippage_report.get("status")
        or payload.get("slippage_provenance")
        or payload.get("impact_source_status")
        or ""
    ).strip()
    latency_source_status = str(
        payload.get("latency_source_status")
        or payload.get("latency_provenance")
        or "STATIC_CONSERVATIVE_VENUE_MODEL"
    ).strip()
    fee_source_status = str(payload.get("fee_source_status") or "").strip()
    impact_bps = float(slippage_bps * 0.15)
    impact_source_status = str(
        payload.get("impact_source_status")
        or (
            f"DERIVED_FROM_SLIPPAGE_X0.15:{slippage_source_status}"
            if slippage_source_status
            else "NOT_MODELED_IN_V53_COST_FORMULA"
        )
    ).strip()
    adverse_selection_bps = payload.get("adverse_selection_bps")
    adverse_selection_source_status = str(
        payload.get("adverse_selection_source_status")
        or "NOT_MODELED_IN_V53_COST_FORMULA"
    ).strip()
    book_depth_status = str(payload.get("book_depth_source_status") or "").strip()
    book_depth_staleness_status = str(
        payload.get("book_depth_staleness_status") or ""
    ).strip()
    orderbook_feature_status = str(payload.get("orderbook_feature_status") or "").strip()
    warnings = tuple(
        str(item)
        for item in tuple(payload.get("economic_measurement_warnings") or ())
        if str(item).strip()
    )
    measured_book_staleness_ms = payload.get("book_staleness_ms")
    if measured_book_staleness_ms is None:
        staleness_candidates = [
            value
            for value in (
                measured_spread_report.get("staleness_ms"),
                measured_slippage_report.get("staleness_ms"),
                book_staleness_ms,
            )
            if isinstance(value, (int, float))
        ]
        measured_book_staleness_ms = max(staleness_candidates) if staleness_candidates else None
    component_statuses = (
        spread_source_status,
        slippage_source_status,
        latency_source_status,
        fee_source_status,
    )
    buckets = [_source_status_bucket(status) for status in component_statuses]
    has_unknown = any(bucket == "unknown" for bucket in buckets)
    has_stale = any(bucket == "stale" for bucket in buckets) or "STALE" in book_depth_staleness_status.upper()
    has_blocked = any(bucket == "blocked" for bucket in buckets)
    has_proxy = any(bucket == "proxy" for bucket in buckets)
    all_measured = all(bucket == "measured" for bucket in buckets)
    all_proxy = all(bucket == "proxy" for bucket in buckets)
    partial_fill_status = str(
        payload.get("partial_fill_status")
        or measured_slippage_report.get("partial_fill_status")
        or "PARTIAL_FILL_STATUS_NOT_AVAILABLE"
    ).strip()

    explicit_cost_truth_status = str(payload.get("expected_cost_truth_status") or "").strip()
    if explicit_cost_truth_status:
        expected_cost_truth_status = explicit_cost_truth_status
    elif has_unknown:
        expected_cost_truth_status = "COST_PROVENANCE_UNCLASSIFIED"
    elif has_blocked:
        expected_cost_truth_status = "COST_MEASUREMENT_BLOCKED"
    elif has_stale:
        expected_cost_truth_status = "STALE_AUDIT_ONLY_COST"
    elif partial_fill_status not in {"", "FULL_DEPTH_FILL", "PARTIAL_FILL_STATUS_NOT_AVAILABLE"}:
        expected_cost_truth_status = "PARTIALLY_MEASURED_COST"
    elif all_measured:
        expected_cost_truth_status = "FULLY_MEASURED_COST"
    elif all_proxy:
        expected_cost_truth_status = "PROXY_COST"
    else:
        expected_cost_truth_status = "PARTIALLY_MEASURED_COST"

    if expected_cost_truth_status == "FULLY_MEASURED_COST":
        fill_realism_status = "FILL_REALISM_MEASURED"
    elif expected_cost_truth_status == "STALE_AUDIT_ONLY_COST":
        fill_realism_status = "FILL_REALISM_STALE_AUDIT_ONLY"
    elif expected_cost_truth_status == "COST_MEASUREMENT_BLOCKED":
        fill_realism_status = "FILL_REALISM_BLOCKED_BY_MISSING_MEASUREMENT"
    elif expected_cost_truth_status == "COST_PROVENANCE_UNCLASSIFIED":
        fill_realism_status = "FILL_REALISM_UNCLASSIFIED"
    elif has_proxy:
        fill_realism_status = "FILL_REALISM_PROXY_AUDIT_ONLY"
    else:
        fill_realism_status = "FILL_REALISM_PARTIALLY_MEASURED"
    explicit_fill_realism_status = str(payload.get("fill_realism_status") or "").strip()
    if explicit_fill_realism_status:
        fill_realism_status = explicit_fill_realism_status

    usage_break_even = str(payload.get("cost_source_used_for_break_even") or "").strip()
    usage_expected_ce_net = str(
        payload.get("cost_source_used_for_expected_ce_net") or ""
    ).strip()
    if not usage_break_even:
        usage_break_even = _usage_from_cost_truth_status(expected_cost_truth_status)
    if not usage_expected_ce_net:
        usage_expected_ce_net = usage_break_even

    proxy_or_measured = (
        "measured"
        if usage_break_even == "measured"
        or expected_cost_truth_status in {"FULLY_MEASURED_COST", "PARTIALLY_MEASURED_COST"}
        else "proxy"
        if expected_cost_truth_status == "PROXY_COST"
        else "stale_audit_only"
        if expected_cost_truth_status == "STALE_AUDIT_ONLY_COST"
        else "blocked"
        if expected_cost_truth_status == "COST_MEASUREMENT_BLOCKED"
        else "unclassified"
    )
    block_reason = str(payload.get("expected_cost_block_reason") or "").strip()
    if not block_reason and expected_cost_truth_status == "COST_MEASUREMENT_BLOCKED":
        block_reason = "B2_COST_MEASUREMENT_BLOCKED"
    elif not block_reason and expected_cost_truth_status == "STALE_AUDIT_ONLY_COST":
        block_reason = "B2_COST_STALE_AUDIT_ONLY"
    measured_required_failure_reason = (
        "expected_cost_provenance_unclassified"
        if expected_cost_truth_status == "COST_PROVENANCE_UNCLASSIFIED"
        else f"expected_cost_truth_not_ready:{expected_cost_truth_status}"
    )
    return {
        "expected_cost_used_decimal": float(expected_cost_used_decimal),
        "expected_cost_truth_status": expected_cost_truth_status,
        "fee_bps": fee_bps,
        "fee_source_status": fee_source_status,
        "spread_bps": spread_bps,
        "spread_bps_measured": (
            None if spread_bps_measured is None else float(spread_bps_measured)
        ),
        "spread_source_status": spread_source_status,
        "slippage_bps": slippage_bps,
        "slippage_bps_measured": (
            None if slippage_bps_measured is None else float(slippage_bps_measured)
        ),
        "slippage_source_status": slippage_source_status,
        "latency_penalty_bps": latency_penalty_bps,
        "latency_source_status": latency_source_status,
        "impact_bps": impact_bps,
        "impact_source_status": impact_source_status,
        "adverse_selection_bps": adverse_selection_bps,
        "adverse_selection_source_status": adverse_selection_source_status,
        "fill_realism_status": fill_realism_status,
        "book_staleness_ms": measured_book_staleness_ms,
        "book_depth_source_status": book_depth_status,
        "book_depth_staleness_status": book_depth_staleness_status,
        "orderbook_feature_status": orderbook_feature_status,
        "best_bid": measured_spread_report.get("best_bid") or payload.get("best_bid"),
        "best_ask": measured_spread_report.get("best_ask") or payload.get("best_ask"),
        "mid_price": measured_spread_report.get("mid_price") or payload.get("mid_price"),
        "depth_fill_ratio": (
            measured_slippage_report.get("depth_fill_ratio")
            if measured_slippage_report.get("depth_fill_ratio") is not None
            else payload.get("depth_fill_ratio")
        ),
        "partial_fill_status": partial_fill_status,
        "economic_measurement_warnings": warnings,
        "cost_source_used_for_break_even": usage_break_even,
        "cost_source_used_for_expected_ce_net": usage_expected_ce_net,
        "expected_cost_block_reason": block_reason,
        "proxy_or_measured_override": proxy_or_measured,
        "source_status": expected_cost_truth_status,
        "truth_status": expected_cost_truth_status,
        "forced_invalid_reason": (
            ""
            if expected_cost_truth_status == "FULLY_MEASURED_COST"
            or expected_cost_truth_status == "COST_PROVENANCE_UNCLASSIFIED"
            else f"expected_cost_truth_not_ready:{expected_cost_truth_status}"
        ),
        "unclassified_reason": "expected_cost_provenance_unclassified",
        "measured_required_failure_reason": measured_required_failure_reason,
    }


def _feature_metadata_map(
    *,
    case: ReconstructedNativeCase,
    candidate: StrategyLadderCandidateEvent,
    window: StrategyLadderRawWindowManifest | None,
    payload: dict[str, object],
) -> dict[str, dict[str, object]]:
    book_staleness_ms = _book_staleness_ms(candidate=candidate, window=window)
    expected_gain_fields = _expected_gain_audit_fields(
        payload=payload,
        expected_gain_used_decimal=float(case.engine_input_payload.get("expected_gain") or 0.0),
        runtime_mode="B2",
    )
    expected_cost_fields = _expected_cost_audit_fields(
        payload=payload,
        expected_cost_used_decimal=float(case.engine_input_payload.get("expected_cost") or 0.0),
        book_staleness_ms=book_staleness_ms,
    )
    return {
        "expected_gain": expected_gain_fields,
        "expected_cost": expected_cost_fields,
    }


def _feature_expectations(engine_id: str) -> tuple[EngineFeatureExpectation, ...]:
    if engine_id == "engine_a":
        return (
            EngineFeatureExpectation(engine_id, "direction_score", "signed_score_-1_to_1", "run_engine_a"),
            EngineFeatureExpectation(engine_id, "continuation_score", "score_0_to_1", "detect_structure"),
            EngineFeatureExpectation(engine_id, "structure_quality", "score_0_to_1", "detect_structure"),
            EngineFeatureExpectation(engine_id, "zone_proximity", "score_0_to_1", "detect_structure"),
            EngineFeatureExpectation(engine_id, "trend_stability", "score_0_to_1", "detect_structure"),
            EngineFeatureExpectation(engine_id, "expected_gain", "decimal_return", "check_cost_feasibility", proxy_forbidden_in_b2=True, sanity_min=0.0),
            EngineFeatureExpectation(engine_id, "expected_cost", "decimal_return", "check_cost_feasibility", measured_required=True, sanity_min=0.0),
        )
    if engine_id == "engine_b":
        return (
            EngineFeatureExpectation(engine_id, "current_price", "price_quote", "run_engine_b", measured_required=True, sanity_min=0.0),
            EngineFeatureExpectation(engine_id, "local_mean", "price_quote", "run_engine_b", measured_required=True, sanity_min=0.0),
            EngineFeatureExpectation(engine_id, "local_std", "price_quote", "run_engine_b", measured_required=True, sanity_min=0.0),
            EngineFeatureExpectation(engine_id, "expected_gain", "decimal_return", "check_cost_feasibility_b", proxy_forbidden_in_b2=True, sanity_min=0.0),
            EngineFeatureExpectation(engine_id, "expected_cost", "decimal_return", "check_cost_feasibility_b", measured_required=True, sanity_min=0.0),
        )
    if engine_id == "engine_c":
        return (
            EngineFeatureExpectation(engine_id, "breakout_strength", "score_0_to_1", "compute_breakout_score"),
            EngineFeatureExpectation(engine_id, "range_quality", "score_0_to_1", "compute_breakout_score"),
            EngineFeatureExpectation(engine_id, "compression_quality", "score_0_to_1", "compute_breakout_score"),
            EngineFeatureExpectation(engine_id, "volume_confirmation", "score_0_to_1", "compute_breakout_score"),
            EngineFeatureExpectation(engine_id, "followthrough_room", "score_0_to_1", "validate_continuation_c"),
            EngineFeatureExpectation(engine_id, "extension_pct", "score_0_to_1", "validate_continuation_c"),
            EngineFeatureExpectation(engine_id, "retrace_risk", "score_0_to_1", "compute_fake_breakout_risk"),
            EngineFeatureExpectation(engine_id, "cumulative_ofi", "signed_flow_units", "validate_continuation_c", required=False, measured_required=True),
            EngineFeatureExpectation(engine_id, "queue_pressure", "signed_score_-1_to_1", "validate_continuation_c", required=False, measured_required=True),
            EngineFeatureExpectation(engine_id, "vpin", "score_0_to_1", "validate_continuation_c", required=False, measured_required=True),
            EngineFeatureExpectation(engine_id, "kyle_lambda", "impact_units", "validate_continuation_c", required=False, measured_required=True),
            EngineFeatureExpectation(engine_id, "expected_gain", "decimal_return", "evaluate_cost_feasibility_c", proxy_forbidden_in_b2=True, sanity_min=0.0),
            EngineFeatureExpectation(engine_id, "expected_cost", "decimal_return", "evaluate_cost_feasibility_c", measured_required=True, sanity_min=0.0),
        )
    return (
        EngineFeatureExpectation(engine_id, "prior_trade_quality", "score_0_to_1", "compute_history_score"),
        EngineFeatureExpectation(engine_id, "reformation_quality", "score_0_to_1", "compute_reformation_score"),
        EngineFeatureExpectation(engine_id, "pullback_quality", "score_0_to_1", "compute_reformation_score"),
        EngineFeatureExpectation(engine_id, "continuation_room", "score_0_to_1", "compute_marginal_value_score"),
        EngineFeatureExpectation(engine_id, "concentration_headroom", "score_0_to_1", "resolve_engine_d_context"),
        EngineFeatureExpectation(engine_id, "marginal_edge", "score_0_to_1", "compute_marginal_value_score"),
        EngineFeatureExpectation(engine_id, "reentry_lateness", "score_0_to_1", "resolve_engine_d_context"),
        EngineFeatureExpectation(engine_id, "expected_gain", "decimal_return", "evaluate_cost_feasibility_d", proxy_forbidden_in_b2=True, sanity_min=0.0),
        EngineFeatureExpectation(engine_id, "expected_cost", "decimal_return", "evaluate_cost_feasibility_d", measured_required=True, sanity_min=0.0),
    )


def _feature_provenance_map(
    *,
    case: ReconstructedNativeCase,
    economic_provenance: EconomicProvenance,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in case.engine_input_payload:
        if key in {"expected_gain"}:
            out[key] = economic_provenance.expected_edge_provenance
        elif key in {"expected_cost"}:
            out[key] = economic_provenance.aggregated_provenance
        elif key in {"current_price", "local_mean", "local_std", "vpin", "cumulative_ofi", "queue_pressure", "kyle_lambda"}:
            out[key] = "MEASURED_FROM_REPLAY_WINDOW"
        else:
            out[key] = case.builder_provenance or "BUILDER_UNKNOWN"
    return out


def _feature_source_path_map(
    *,
    case: ReconstructedNativeCase,
    window: StrategyLadderRawWindowManifest,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in case.engine_input_payload:
        if key in {"current_price", "local_mean", "local_std", "vpin"}:
            out[key] = str(window.raw_trade_path or "")
        elif key in {"cumulative_ofi", "queue_pressure", "kyle_lambda"}:
            out[key] = str(window.raw_book_path or "")
        elif key in {"expected_gain", "expected_cost"}:
            out[key] = "economic_provenance"
        else:
            out[key] = str(window.raw_ohlcv_path or "")
    return out


def _feature_timestamp_map(
    *,
    case: ReconstructedNativeCase,
    window: StrategyLadderRawWindowManifest,
) -> dict[str, int | None]:
    return {key: int(window.window_end_ms) for key in case.engine_input_payload}


def _feature_staleness_map(
    *,
    case: ReconstructedNativeCase,
    candidate: StrategyLadderCandidateEvent,
    window: StrategyLadderRawWindowManifest,
) -> dict[str, int | None]:
    staleness = max(int(candidate.timestamp_ms) - int(window.window_end_ms), 0)
    return {key: staleness for key in case.engine_input_payload}


def _normalize_scope_bound_to_ms(
    value: str | int | float | None,
    *,
    end_of_day: bool,
) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = int(value)
        return numeric if numeric >= 1_000_000_000_000 else numeric * 1000
    raw = str(value).strip()
    if not raw:
        return None
    if raw.isdigit():
        numeric = int(raw)
        return numeric if numeric >= 1_000_000_000_000 else numeric * 1000
    normalized = raw.replace("Z", "+00:00")
    instant = datetime.fromisoformat(normalized)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        instant = instant.replace(
            hour=23 if end_of_day else 0,
            minute=59 if end_of_day else 0,
            second=59 if end_of_day else 0,
            microsecond=999_000 if end_of_day else 0,
        )
    return int(instant.timestamp() * 1000)


def _candidate_matches_scope(
    *,
    candidate: StrategyLadderCandidateEvent,
    pair_filter: str,
    start_ms: int | None,
    end_ms: int | None,
) -> bool:
    if str(candidate.pair or "").upper() != pair_filter.upper():
        return False
    timestamp_ms = int(candidate.timestamp_ms or 0)
    if start_ms is not None and timestamp_ms < start_ms:
        return False
    if end_ms is not None and timestamp_ms > end_ms:
        return False
    return True


def _load_scoped_candidate_contexts(
    *,
    workflow_root: Path | str,
    pair_filter: str,
    start_ms: int | None,
    end_ms: int | None,
) -> tuple[AuditCandidateContext, ...]:
    workflow = Path(workflow_root).resolve()
    materialized_candidates = load_strategy_ladder_candidate_events(
        _workflow_materialized_candidates_path(workflow)
    )
    raw_windows = _workflow_raw_window_map(workflow)
    contexts: list[AuditCandidateContext] = []
    for candidate in materialized_candidates:
        if not _candidate_matches_scope(
            candidate=candidate,
            pair_filter=pair_filter,
            start_ms=start_ms,
            end_ms=end_ms,
        ):
            continue
        window = raw_windows.get(candidate.candidate_id)
        if window is None:
            continue
        payload = dict(candidate.compatibility_payload or {})
        provenance = _economic_provenance_from_payload(payload)
        case = reconstruct_native_candidate_case(
            candidate=candidate,
            window=window,
            economic_provenance=provenance,
        )
        contexts.append(
            AuditCandidateContext(
                candidate=candidate,
                window=window,
                payload=payload,
                economic_provenance=provenance,
                case=case,
            )
        )
    return tuple(contexts)


def build_pre_engine_feature_contract_audit(
    *,
    workflow_root: Path | str,
    pair_filter: str = "BTCUSDT",
    start_ms: int | None = None,
    end_ms: int | None = None,
    contexts: tuple[AuditCandidateContext, ...] | None = None,
) -> dict[str, object]:
    workflow = Path(workflow_root).resolve()
    scoped_contexts = contexts or _load_scoped_candidate_contexts(
        workflow_root=workflow,
        pair_filter=pair_filter,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    rows: list[dict[str, object]] = []
    engine_summaries: dict[str, dict[str, object]] = defaultdict(
        lambda: {
            "candidate_count": 0,
            "invalid_feature_count": 0,
            "measured_count": 0,
            "proxy_count": 0,
            "stale_count": 0,
            "blocked_count": 0,
            "unclassified_count": 0,
            "missing_count": 0,
            "invalid_reason_counts": Counter(),
        }
    )

    for context in scoped_contexts:
        candidate = context.candidate
        window = context.window
        payload = context.payload
        provenance = context.economic_provenance
        case = context.case
        feature_metadata = _feature_metadata_map(
            case=case,
            candidate=candidate,
            window=window,
            payload=payload,
        )
        audit = audit_engine_feature_contract(
            engine_id=case.engine_id,
            candidate_id=case.candidate_id,
            payload=case.engine_input_payload,
            expectations=_feature_expectations(case.engine_id),
            provenance_by_feature=_feature_provenance_map(case=case, economic_provenance=provenance),
            source_path_by_feature=_feature_source_path_map(case=case, window=window),
            timestamp_ms_by_feature=_feature_timestamp_map(case=case, window=window),
            staleness_ms_by_feature=_feature_staleness_map(case=case, candidate=candidate, window=window),
            feature_metadata_by_feature=feature_metadata,
            runtime_mode="B2",
            builder_status=case.builder_status,
            builder_provenance=case.builder_provenance,
        )
        summary = engine_summaries[case.engine_id]
        summary["candidate_count"] += 1
        summary["invalid_feature_count"] += audit.invalid_count
        for row in audit.rows:
            row_dict = asdict(row)
            row_artifacts = feature_metadata.get(row.feature_name, {})
            for key, value in row_artifacts.items():
                if key not in _FEATURE_METADATA_CONTROL_KEYS:
                    row_dict[key] = value
            rows.append(row_dict)
            if row.proxy_or_measured == "measured":
                summary["measured_count"] += 1
            elif row.proxy_or_measured == "proxy":
                summary["proxy_count"] += 1
            elif row.proxy_or_measured == "stale_audit_only":
                summary["stale_count"] += 1
            elif row.proxy_or_measured == "blocked":
                summary["blocked_count"] += 1
            elif row.proxy_or_measured in {"unclassified", "unknown"}:
                summary["unclassified_count"] += 1
            if row.missing:
                summary["missing_count"] += 1
            if row.status != "valid":
                summary["invalid_reason_counts"][row.reason] += 1

    normalized_summaries: dict[str, dict[str, object]] = {}
    for engine_id, summary in engine_summaries.items():
        normalized = dict(summary)
        normalized["invalid_reason_counts"] = dict(summary["invalid_reason_counts"])
        normalized_summaries[engine_id] = normalized

    return {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "workflow_root": str(workflow),
        "pair_filter": pair_filter,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "row_count": len(rows),
        "engine_summaries": normalized_summaries,
        "rows": rows,
    }


def build_reason_code_consistency_report(
    *,
    workflow_root: Path | str,
    synthetic_report: dict[str, object],
    pair_filter: str = "BTCUSDT",
    start_ms: int | None = None,
    end_ms: int | None = None,
    contexts: tuple[AuditCandidateContext, ...] | None = None,
) -> dict[str, object]:
    workflow = Path(workflow_root).resolve()
    scoped_contexts = contexts or _load_scoped_candidate_contexts(
        workflow_root=workflow,
        pair_filter=pair_filter,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    real_rows: list[dict[str, object]] = []
    mismatch_count = 0
    for context in scoped_contexts:
        candidate = context.candidate
        payload = context.payload
        case = context.case
        recorded_reason_codes = tuple(str(item) for item in tuple(payload.get("engine_native_reason_codes") or ()))
        recorded_decision = str(payload.get("engine_native_decision") or "")
        recorded_builder_status = str(payload.get("engine_native_builder_status") or "")
        row = {
            "candidate_id": candidate.candidate_id,
            "engine_id": case.engine_id,
            "recorded_decision": recorded_decision,
            "reconstructed_decision": case.decision,
            "recorded_builder_status": recorded_builder_status,
            "reconstructed_builder_status": case.builder_status,
            "recorded_reason_codes": recorded_reason_codes,
            "reconstructed_reason_codes": case.reason_codes,
            "match": (
                recorded_decision == case.decision
                and recorded_builder_status == case.builder_status
                and recorded_reason_codes == case.reason_codes
            ),
        }
        if not row["match"]:
            mismatch_count += 1
        real_rows.append(row)

    synthetic_rows = list(synthetic_report.get("results") or ())
    return {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "workflow_root": str(workflow),
        "pair_filter": pair_filter,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "synthetic_all_ok": bool(synthetic_report.get("all_ok")),
        "synthetic_results": synthetic_rows,
        "real_rows": real_rows,
        "real_mismatch_count": mismatch_count,
    }


def build_cost_source_audit(
    *,
    workflow_root: Path | str,
    pair_filter: str = "BTCUSDT",
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> dict[str, object]:
    workflow = Path(workflow_root).resolve()
    materialized_candidates = load_strategy_ladder_candidate_events(_workflow_materialized_candidates_path(workflow))
    raw_windows = _workflow_raw_window_map(workflow)
    rows: list[dict[str, object]] = []
    for candidate in materialized_candidates:
        if not _candidate_matches_scope(
            candidate=candidate,
            pair_filter=pair_filter,
            start_ms=start_ms,
            end_ms=end_ms,
        ):
            continue
        payload = dict(candidate.compatibility_payload or {})
        window = raw_windows.get(candidate.candidate_id)
        expected_gain_truth_status = str(payload.get("expected_edge_truth_status") or "").strip()
        expected_gain_used_decimal = (
            float(payload.get("expected_edge_bps") or 0.0) / 10_000.0
            if expected_gain_truth_status == "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH"
            else 0.0
        )
        expected_gain_fields = _expected_gain_audit_fields(
            payload=payload,
            expected_gain_used_decimal=expected_gain_used_decimal,
            runtime_mode="B2",
        )
        expected_cost_fields = _expected_cost_audit_fields(
            payload=payload,
            expected_cost_used_decimal=float(payload.get("production_expected_cost") or 0.0),
            book_staleness_ms=_book_staleness_ms(candidate=candidate, window=window),
        )
        rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "engine_id": str(candidate.engine_id or ""),
                "expected_edge_truth_status": str(payload.get("expected_edge_truth_status") or ""),
                "expected_edge_provenance": str(payload.get("expected_edge_provenance") or ""),
                "economic_provenance": str(payload.get("economic_provenance") or ""),
                "production_expected_cost": float(payload.get("production_expected_cost") or 0.0),
                **{
                    key: value
                    for key, value in expected_gain_fields.items()
                    if key not in _FEATURE_METADATA_CONTROL_KEYS
                },
                **{
                    key: value
                    for key, value in expected_cost_fields.items()
                    if key not in _FEATURE_METADATA_CONTROL_KEYS
                },
            }
        )
    return {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "workflow_root": str(workflow),
        "pair_filter": pair_filter,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "rows": rows,
        "expected_edge_truth_status_counts": dict(Counter(row["expected_edge_truth_status"] for row in rows)),
        "economic_provenance_counts": dict(Counter(row["economic_provenance"] for row in rows)),
        "expected_cost_truth_status_counts": dict(
            Counter(row["expected_cost_truth_status"] for row in rows)
        ),
        "cost_source_used_for_break_even_counts": dict(
            Counter(row["cost_source_used_for_break_even"] for row in rows)
        ),
    }


def build_b1_b2_cost_source_contamination_audit(
    *,
    workflow_root: Path | str,
    pair_filter: str = "BTCUSDT",
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> dict[str, object]:
    workflow = Path(workflow_root).resolve()
    b1_candidates = load_strategy_ladder_candidate_events(_workflow_b1_candidate_events_path(workflow))
    b2_candidates = load_strategy_ladder_candidate_events(_workflow_materialized_candidates_path(workflow))
    raw_windows = _workflow_raw_window_map(workflow)
    b1_by_id = {
        candidate.candidate_id: candidate
        for candidate in b1_candidates
        if _candidate_matches_scope(
            candidate=candidate,
            pair_filter=pair_filter,
            start_ms=start_ms,
            end_ms=end_ms,
        )
    }
    b2_by_id = {
        candidate.candidate_id: candidate
        for candidate in b2_candidates
        if _candidate_matches_scope(
            candidate=candidate,
            pair_filter=pair_filter,
            start_ms=start_ms,
            end_ms=end_ms,
        )
    }
    ordered_ids = sorted(
        set(b1_by_id) | set(b2_by_id),
        key=lambda candidate_id: (
            int(
                (
                    (b2_by_id.get(candidate_id) or b1_by_id.get(candidate_id)).timestamp_ms
                )
                or 0
            ),
            candidate_id,
        ),
    )
    rows: list[dict[str, object]] = []
    for candidate_id in ordered_ids:
        b1_candidate = b1_by_id.get(candidate_id)
        b2_candidate = b2_by_id.get(candidate_id)
        b1_payload = dict((b1_candidate.compatibility_payload if b1_candidate is not None else {}) or {})
        b2_payload = dict((b2_candidate.compatibility_payload if b2_candidate is not None else {}) or {})
        engine_id = str(
            (
                b2_candidate.engine_id
                if b2_candidate is not None
                else b1_candidate.engine_id
                if b1_candidate is not None
                else ""
            )
            or ""
        )
        if b2_candidate is None:
            contamination_status = "B1_PROXY_USED_ONLY_FOR_DISCOVERY"
            b2_cost_fields = {
                "cost_source_used_for_break_even": "blocked_missing_measurement",
                "cost_source_used_for_expected_ce_net": "blocked_missing_measurement",
                "spread_source_status": "",
                "slippage_source_status": "",
            }
        else:
            window = raw_windows.get(candidate_id)
            b2_cost_fields = _expected_cost_audit_fields(
                payload=b2_payload,
                expected_cost_used_decimal=float(
                    b2_payload.get("production_expected_cost") or 0.0
                ),
                book_staleness_ms=_book_staleness_ms(candidate=b2_candidate, window=window),
            )
            b1_proxy_present = any(
                _source_status_bucket(status) == "proxy"
                for status in (
                    str(b1_payload.get("spread_provenance") or ""),
                    str(
                        b1_payload.get("slippage_provenance")
                        or b1_payload.get("impact_source_status")
                        or ""
                    ),
                )
            )
            same_spread = (
                b1_payload.get("spread_bps") == b2_payload.get("spread_bps")
                and str(b1_payload.get("spread_provenance") or "")
                == str(b2_payload.get("spread_provenance") or "")
            )
            same_slippage = (
                b1_payload.get("slippage_bps") == b2_payload.get("slippage_bps")
                and str(b1_payload.get("slippage_provenance") or b1_payload.get("impact_source_status") or "")
                == str(b2_payload.get("slippage_provenance") or b2_payload.get("impact_source_status") or "")
            )
            cost_usage = str(b2_cost_fields["cost_source_used_for_break_even"])
            b2_spread_bucket = _source_status_bucket(str(b2_cost_fields["spread_source_status"]))
            b2_slippage_bucket = _source_status_bucket(str(b2_cost_fields["slippage_source_status"]))
            if (
                cost_usage == "measured"
                and b2_spread_bucket == "measured"
                and b2_slippage_bucket == "measured"
            ):
                contamination_status = "NO_CONTAMINATION_MEASURED_B2_USED"
            elif cost_usage == "stale_audit_only":
                contamination_status = "B2_COST_STALE_AUDIT_ONLY"
            elif cost_usage == "blocked_missing_measurement":
                contamination_status = "B2_COST_BLOCKED_BY_MISSING_MEASUREMENT"
            elif (
                b1_proxy_present
                and (same_spread or same_slippage)
                and cost_usage in {"partially_measured_audit_only", "proxy_audit_only", "unclassified"}
            ):
                contamination_status = "B1_PROXY_COPIED_TO_B2_AUDIT_ONLY"
            elif (
                b1_proxy_present
                and (same_spread or same_slippage)
                and cost_usage == "measured"
            ):
                contamination_status = "B1_PROXY_CONTAMINATES_B2_COST"
            else:
                contamination_status = "NO_CONTAMINATION_MEASURED_B2_USED"

        rows.append(
            {
                "candidate_id": candidate_id,
                "engine_id": engine_id,
                "b1_spread_bps": (
                    float(b1_payload.get("spread_bps") or 0.0)
                    if b1_candidate is not None
                    else None
                ),
                "b1_spread_provenance": (
                    str(b1_payload.get("spread_provenance") or "")
                    if b1_candidate is not None
                    else ""
                ),
                "b2_measured_spread_bps": (
                    float(
                        b2_cost_fields.get("spread_bps_measured")
                        or b2_payload.get("spread_bps_measured")
                        or b2_payload.get("spread_bps")
                        or 0.0
                    )
                    if b2_candidate is not None
                    and _source_status_bucket(str(b2_cost_fields["spread_source_status"])) == "measured"
                    else None
                ),
                "b2_spread_source_status": str(b2_cost_fields["spread_source_status"]),
                "b1_slippage_bps": (
                    float(b1_payload.get("slippage_bps") or 0.0)
                    if b1_candidate is not None
                    else None
                ),
                "b1_slippage_provenance": (
                    str(
                        b1_payload.get("slippage_provenance")
                        or b1_payload.get("impact_source_status")
                        or ""
                    )
                    if b1_candidate is not None
                    else ""
                ),
                "b2_measured_slippage_bps": (
                    float(
                        b2_cost_fields.get("slippage_bps_measured")
                        or b2_payload.get("slippage_bps_measured")
                        or b2_payload.get("slippage_bps")
                        or 0.0
                    )
                    if b2_candidate is not None
                    and _source_status_bucket(str(b2_cost_fields["slippage_source_status"])) == "measured"
                    else None
                ),
                "b2_slippage_source_status": str(b2_cost_fields["slippage_source_status"]),
                "cost_source_used_for_break_even": str(
                    b2_cost_fields["cost_source_used_for_break_even"]
                ),
                "cost_source_used_for_expected_ce_net": str(
                    b2_cost_fields["cost_source_used_for_expected_ce_net"]
                ),
                "contamination_status": contamination_status,
            }
        )
    contamination_counts = dict(Counter(row["contamination_status"] for row in rows))
    p0_blocker_present = contamination_counts.get("B1_PROXY_CONTAMINATES_B2_COST", 0) > 0
    return {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "workflow_root": str(workflow),
        "pair_filter": pair_filter,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "rows": rows,
        "contamination_status_counts": contamination_counts,
        "p0_blocker_present": p0_blocker_present,
        "blocker_code": (
            "B1_COST_PROXY_CONTAMINATES_B2_TRUTH" if p0_blocker_present else ""
        ),
    }


def build_native_vs_proxy_blocker_report(
    *,
    workflow_root: Path | str,
    pair_filter: str = "BTCUSDT",
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> dict[str, object]:
    workflow = Path(workflow_root).resolve()
    materialized_candidates = load_strategy_ladder_candidate_events(_workflow_materialized_candidates_path(workflow))
    rows: list[dict[str, object]] = []
    for candidate in materialized_candidates:
        if not _candidate_matches_scope(
            candidate=candidate,
            pair_filter=pair_filter,
            start_ms=start_ms,
            end_ms=end_ms,
        ):
            continue
        payload = dict(candidate.compatibility_payload or {})
        native_reasons = tuple(str(item) for item in tuple(payload.get("engine_native_reason_codes") or ()))
        truth_status = str(payload.get("expected_edge_truth_status") or "")
        has_proxy_blocker = "PROXY_BLOCKED" in truth_status or any("PROXY_BLOCKED" in code for code in native_reasons)
        has_native_blocker = bool(native_reasons) and not all("PROXY_BLOCKED" in code for code in native_reasons)
        classification = (
            "MIXED_BLOCKERS"
            if has_proxy_blocker and has_native_blocker
            else "PROXY_BLOCKER"
            if has_proxy_blocker
            else "NATIVE_BLOCKER"
            if has_native_blocker
            else "NO_BLOCKER"
        )
        rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "engine_id": str(candidate.engine_id or ""),
                "expected_edge_truth_status": truth_status,
                "native_reason_codes": native_reasons,
                "classification": classification,
            }
        )
    return {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "workflow_root": str(workflow),
        "pair_filter": pair_filter,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "rows": rows,
        "classification_counts": dict(Counter(row["classification"] for row in rows)),
    }


def _distance_row_for_case(case: ReconstructedNativeCase) -> tuple[str, float, float, float] | None:
    if case.engine_id == "engine_a" and case.engine_input_payload:
        direction = float(case.engine_input_payload.get("direction_score") or 0.0)
        structure = detect_structure(StructureInput.model_validate({"pair": case.pair, **{k: case.engine_input_payload[k] for k in ("direction_score", "continuation_score", "structure_quality", "zone_proximity", "trend_stability") if k in case.engine_input_payload}}))
        if any("non_long" in code for code in case.reason_codes):
            return ("min_direction", direction, 0.0, direction - 0.0)
        if structure.structure_score < 0.30:
            return ("marginal", structure.structure_score, 0.30, structure.structure_score - 0.30)
        if structure.structure_score < 0.60:
            return ("favorable", structure.structure_score, 0.60, structure.structure_score - 0.60)
    if case.engine_id == "engine_b" and case.engine_input_payload:
        current = float(case.engine_input_payload.get("current_price") or 0.0)
        mean = float(case.engine_input_payload.get("local_mean") or 0.0)
        std = float(case.engine_input_payload.get("local_std") or 0.0)
        z = 0.0 if std <= 0 else (current - mean) / std
        if any("excess.no_excess" in code for code in case.reason_codes):
            return ("z_marginal", abs(z), 1.0, abs(z) - 1.0)
        if any("break_even_not_cleared" in code for code in case.reason_codes):
            break_even = float(case.output_payload.get("expected_cost") or 0.0) + 0.0008
            gain = float(case.engine_input_payload.get("expected_gain") or 0.0)
            return ("delta_safe", gain, break_even, gain - break_even)
    if case.engine_id == "engine_c" and case.engine_input_payload:
        breakout_score = compute_breakout_score(EngineCInput.model_validate(case.engine_input_payload))
        fake_risk = compute_fake_breakout_risk(EngineCInput.model_validate(case.engine_input_payload))
        if case.builder_status == "ENGINE_C_INPUT_BUILDER_NO_BREAKOUT":
            return ("no_breakout", 0.0, 1.0, -1.0)
        if any("breakout" in code and "unstructured" in code for code in case.reason_codes):
            return ("breakout_score_min", breakout_score, 0.62, breakout_score - 0.62)
        if any("fake_breakout" in code for code in case.reason_codes):
            return ("fake_breakout_risk_max", fake_risk, 0.65, 0.65 - fake_risk)
    if case.engine_id == "engine_d" and case.engine_input_payload:
        inputs = EngineDInput.model_validate(case.engine_input_payload)
        history = compute_history_score(inputs)
        context = compute_context_score_d(inputs)
        reformation = compute_reformation_score(inputs, context_score=context)
        concentration = float(resolve_engine_d_context(inputs)["concentration_risk"])
        if any("history_weak" in code for code in case.reason_codes):
            return ("history_min", history, 0.55, history - 0.55)
        if any("reformation_weak" in code for code in case.reason_codes):
            return ("reformation_min", reformation, 0.58, reformation - 0.58)
        if any("concentration" in code for code in case.reason_codes):
            return ("concentration_max", concentration, 0.64, 0.64 - concentration)
    return None


def build_engine_threshold_counterfactual_report(
    *,
    workflow_root: Path | str,
    pair_filter: str = "BTCUSDT",
    start_ms: int | None = None,
    end_ms: int | None = None,
    contexts: tuple[AuditCandidateContext, ...] | None = None,
) -> dict[str, object]:
    workflow = Path(workflow_root).resolve()
    scoped_contexts = contexts or _load_scoped_candidate_contexts(
        workflow_root=workflow,
        pair_filter=pair_filter,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    engine_rows: dict[str, list[dict[str, object]]] = defaultdict(list)
    summary_rows: list[dict[str, object]] = []

    for context in scoped_contexts:
        candidate = context.candidate
        case = context.case
        distance_row = _distance_row_for_case(case)
        if distance_row is None:
            continue
        threshold_name, measured_value, threshold, distance = distance_row
        engine_rows[case.engine_id].append(
            {
                "candidate_id": candidate.candidate_id,
                "threshold_name": threshold_name,
                "measured_value": measured_value,
                "threshold": threshold,
                "distance_to_threshold": distance,
            }
        )

    for engine_id, rows in engine_rows.items():
        near = sum(1 for row in rows if abs(float(row["distance_to_threshold"])) <= 0.02)
        far = sum(1 for row in rows if abs(float(row["distance_to_threshold"])) > 0.02)
        slight_pass = sum(1 for row in rows if float(row["distance_to_threshold"]) >= -0.02)
        strong_pass = sum(1 for row in rows if float(row["distance_to_threshold"]) >= -0.05)
        verdict = (
            "NEAR_MISS_CLUSTER"
            if near and near >= far
            else "FAR_FROM_THRESHOLD"
            if far
            else "MISSING_PREREQUISITE"
        )
        summary_rows.append(
            {
                "engine_id": engine_id,
                "candidates_blocked": len(rows),
                "near_miss_count": near,
                "far_fail_count": far,
                "counterfactual_pass_count_if_slight_move": slight_pass,
                "counterfactual_pass_count_if_strong_move": strong_pass,
                "verdict": verdict,
                "rows": rows,
            }
        )

    return {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "workflow_root": str(workflow),
        "pair_filter": pair_filter,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "engine_rows": summary_rows,
    }


def build_v53_engine_math_canary_final_verdict(
    *,
    synthetic_report: dict[str, object],
    threshold_report: dict[str, object],
    reason_code_report: dict[str, object],
    feature_contract_report: dict[str, object],
    cost_source_report: dict[str, object],
    contamination_report: dict[str, object],
    counterfactual_report: dict[str, object],
) -> dict[str, object]:
    synthetic_canary_status = (
        "PASS" if bool(synthetic_report.get("all_ok")) else "FAIL"
    )
    threshold_rows = list(threshold_report.get("rows") or ())
    boundary_fields_present = all(
        {
            "tested_input_values",
            "derived_metric_name",
            "derived_metric_values",
            "threshold_value",
            "threshold_unit",
            "compared_value_kind",
            "comparison_expression",
            "exact_operator_used",
            "expected_decision",
            "output_decision",
            "pass",
        }.issubset(row.keys())
        for row in threshold_rows
    )
    threshold_boundary_status = (
        "PASS"
        if threshold_rows and all(bool(row.get("pass")) for row in threshold_rows) and boundary_fields_present
        else "PASS_WITH_REPORTING_CLARITY_PATCH_REQUIRED"
        if threshold_rows and all(bool(row.get("pass")) for row in threshold_rows)
        else "FAIL"
    )
    reason_code_reconstruction_status = (
        "PASS" if int(reason_code_report.get("real_mismatch_count", 0)) == 0 else "FAIL"
    )
    feature_rows = list(feature_contract_report.get("rows") or ())
    invalid_rows = [row for row in feature_rows if row.get("status") != "valid"]
    feature_contract_status = (
        "PASS"
        if feature_rows and not invalid_rows
        else "PARTIAL"
        if feature_rows
        else "FAIL"
    )
    expected_gain_statuses = dict(
        Counter(
            str(row.get("expected_gain_truth_status") or "")
            for row in cost_source_report.get("rows", ())
            if row.get("expected_gain_truth_status") is not None
        )
    )
    if expected_gain_statuses == {"EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH": sum(expected_gain_statuses.values())}:
        expected_gain_truth_status = "GOVERNED_BACKTEST_TRUTH"
    elif expected_gain_statuses and set(expected_gain_statuses).issubset(
        {"EXPECTED_EDGE_PROXY_BLOCKED", "EXPECTED_EDGE_DEFAULT_BLOCKED", "EXPECTED_EDGE_MODEL_BLOCKED"}
    ):
        expected_gain_truth_status = "PROXY_BLOCKED"
    else:
        expected_gain_truth_status = "MIXED_OR_NOT_PROVEN"

    cost_truth_counts = dict(cost_source_report.get("expected_cost_truth_status_counts") or {})
    if not cost_truth_counts:
        expected_cost_truth_status = "NOT_PROVEN"
    elif len(cost_truth_counts) == 1:
        expected_cost_truth_status = next(iter(cost_truth_counts))
    else:
        expected_cost_truth_status = "MIXED"

    contamination_counts = dict(
        contamination_report.get("contamination_status_counts") or {}
    )
    if contamination_counts.get("B1_PROXY_CONTAMINATES_B2_COST", 0) > 0:
        b1_b2_cost_contamination_status = "P0_BLOCKER:B1_COST_PROXY_CONTAMINATES_B2_TRUTH"
    elif contamination_counts.get("B1_PROXY_COPIED_TO_B2_AUDIT_ONLY", 0) > 0:
        b1_b2_cost_contamination_status = "AUDIT_ONLY_PROXY_CARRYOVER"
    elif contamination_counts.get("B2_COST_BLOCKED_BY_MISSING_MEASUREMENT", 0) > 0:
        b1_b2_cost_contamination_status = "BLOCKED_BY_MISSING_MEASUREMENT"
    elif contamination_counts.get("B2_COST_STALE_AUDIT_ONLY", 0) > 0:
        b1_b2_cost_contamination_status = "STALE_AUDIT_ONLY"
    else:
        b1_b2_cost_contamination_status = "NO_CONTAMINATION_MEASURED_B2_USED"

    threshold_patch_justified = any(
        str(row.get("verdict") or "") == "NEAR_MISS_CLUSTER"
        for row in counterfactual_report.get("engine_rows", ())
    )
    profitability_backtest_ready = (
        feature_contract_status == "PASS"
        and expected_gain_truth_status == "GOVERNED_BACKTEST_TRUTH"
        and expected_cost_truth_status == "FULLY_MEASURED_COST"
        and b1_b2_cost_contamination_status == "NO_CONTAMINATION_MEASURED_B2_USED"
    )
    next_required_patch = (
        "MEASURED_SPREAD_AND_SLIPPAGE_PROVENANCE_GOVERNANCE"
        if expected_cost_truth_status != "FULLY_MEASURED_COST"
        else "GOVERN_EXPECTED_EDGE_BACKTEST_TRUTH"
        if expected_gain_truth_status != "GOVERNED_BACKTEST_TRUTH"
        else "NONE"
    )
    final_verdict = (
        "V53_ENGINE_MATH_CANARY_PASS_AND_FEATURE_COST_CONTRACT_READY_FOR_NEXT_MINI_RUN"
        if synthetic_canary_status == "PASS"
        and threshold_boundary_status == "PASS"
        and reason_code_reconstruction_status == "PASS"
        and feature_contract_status == "PASS"
        else "V53_ENGINE_MATH_CANARY_PASS_BUT_FEATURE_COST_CONTRACT_PARTIAL"
        if synthetic_canary_status == "PASS"
        and threshold_boundary_status in {"PASS", "PASS_WITH_REPORTING_CLARITY_PATCH_REQUIRED"}
        and reason_code_reconstruction_status == "PASS"
        else "V53_ENGINE_MATH_CANARY_FAIL"
    )
    return {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "final_verdict": final_verdict,
        "synthetic_canary_status": synthetic_canary_status,
        "threshold_boundary_status": threshold_boundary_status,
        "reason_code_reconstruction_status": reason_code_reconstruction_status,
        "feature_contract_status": feature_contract_status,
        "expected_gain_truth_status": expected_gain_truth_status,
        "expected_cost_truth_status": expected_cost_truth_status,
        "b1_b2_cost_contamination_status": b1_b2_cost_contamination_status,
        "threshold_patch_justified": threshold_patch_justified,
        "profitability_backtest_ready": profitability_backtest_ready,
        "next_required_patch": next_required_patch,
    }


def _render_registry_markdown(payload: dict[str, object]) -> str:
    lines = ["# ENGINE_EQUATION_FEATURE_REGISTRY", ""]
    for row in payload.get("rows", ()):
        lines.append(f"## {row['equation_id']}")
        lines.append(f"- engine_id: {row['engine_id']}")
        lines.append(f"- module: {row['module_path']}::{row['function_name']}")
        lines.append(f"- formula_expected: {row['formula_expected']}")
        lines.append(f"- formula_implemented: {row['formula_implemented']}")
        lines.append(f"- threshold: {row['threshold_name']} = {row['threshold_value']} {row['threshold_unit']}")
        lines.append(f"- fail_reason_codes: {', '.join(row['reason_code_fail']) or 'n/a'}")
        lines.append(f"- pass_or_marginal_reason_codes: {', '.join(row['reason_code_pass_or_marginal']) or 'n/a'}")
        lines.append(f"- expected_provenance: {row['expected_provenance']}")
        lines.append(f"- existing_tests: {', '.join(row['existing_tests']) or 'n/a'}")
        lines.append(f"- missing_tests: {', '.join(row['missing_tests']) or 'n/a'}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_boundary_markdown(payload: dict[str, object]) -> str:
    lines = ["# ENGINE_THRESHOLD_BOUNDARY_REPORT", ""]
    for row in payload.get("rows", ()):
        lines.append(f"## {row['engine_id']}::{row['threshold_name']}")
        lines.append(f"- threshold_value: {row['threshold_value']} {row['threshold_unit']}")
        lines.append(f"- compared_value_kind: {row['compared_value_kind']}")
        lines.append(f"- comparison_expression: {row['comparison_expression']}")
        lines.append(f"- exact_operator_used: {row['exact_operator_used']}")
        lines.append(f"- tested_input_values: {row['tested_input_values']}")
        lines.append(f"- derived_metric_name: {row['derived_metric_name']}")
        lines.append(f"- derived_metric_values: {row['derived_metric_values']}")
        lines.append(f"- output_decision: {row['output_decision']}")
        lines.append(f"- expected_decision: {row['expected_decision']}")
        lines.append(f"- pass: {row['pass']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_feature_contract_markdown(payload: dict[str, object]) -> str:
    lines = ["# ENGINE_FEATURE_CONTRACT_AUDIT", ""]
    for engine_id, summary in (payload.get("engine_summaries") or {}).items():
        lines.append(f"## {engine_id}")
        lines.append(f"- candidate_count: {summary.get('candidate_count', 0)}")
        lines.append(f"- invalid_feature_count: {summary.get('invalid_feature_count', 0)}")
        lines.append(f"- measured_count: {summary.get('measured_count', 0)}")
        lines.append(f"- proxy_count: {summary.get('proxy_count', 0)}")
        lines.append(f"- stale_count: {summary.get('stale_count', 0)}")
        lines.append(f"- blocked_count: {summary.get('blocked_count', 0)}")
        lines.append(f"- unclassified_count: {summary.get('unclassified_count', 0)}")
        lines.append(f"- missing_count: {summary.get('missing_count', 0)}")
        lines.append(f"- invalid_reason_counts: {summary.get('invalid_reason_counts', {})}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_counterfactual_markdown(payload: dict[str, object]) -> str:
    lines = ["# ENGINE_COUNTERFACTUAL_THRESHOLD_AUDIT", ""]
    for row in payload.get("engine_rows", ()):
        lines.append(f"## {row['engine_id']}")
        lines.append(f"- candidates_blocked: {row['candidates_blocked']}")
        lines.append(f"- near_miss_count: {row['near_miss_count']}")
        lines.append(f"- far_fail_count: {row['far_fail_count']}")
        lines.append(f"- counterfactual_pass_count_if_slight_move: {row['counterfactual_pass_count_if_slight_move']}")
        lines.append(f"- counterfactual_pass_count_if_strong_move: {row['counterfactual_pass_count_if_strong_move']}")
        lines.append(f"- verdict: {row['verdict']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_synthetic_plan_markdown(payload: dict[str, object]) -> str:
    lines = ["# ENGINE_CANARY_SYNTHETIC_TEST_PLAN", ""]
    lines.append(f"- runtime_mode: {payload.get('runtime_mode')}")
    lines.append(f"- all_ok: {payload.get('all_ok')}")
    lines.append("")
    for row in payload.get("results", ()):
        lines.append(f"## {row['scenario_id']}")
        lines.append(f"- engine_id: {row['engine_id']}")
        lines.append(f"- expected_decision: {row['expected_decision']}")
        lines.append(f"- actual_decision: {row['actual_decision']}")
        lines.append(f"- expected_builder_status: {row['expected_builder_status']}")
        lines.append(f"- actual_builder_status: {row['actual_builder_status']}")
        lines.append(f"- expected_reason_codes: {row['expected_reason_codes']}")
        lines.append(f"- actual_reason_codes: {row['actual_reason_codes']}")
        lines.append(f"- ok: {row['ok']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_final_verdict_markdown(payload: dict[str, object]) -> str:
    lines = ["# V53_ENGINE_MATH_CANARY_FINAL_VERDICT", ""]
    lines.append(f"- final_verdict: {payload.get('final_verdict')}")
    lines.append(f"- synthetic_canary_status: {payload.get('synthetic_canary_status')}")
    lines.append(f"- threshold_boundary_status: {payload.get('threshold_boundary_status')}")
    lines.append(f"- reason_code_reconstruction_status: {payload.get('reason_code_reconstruction_status')}")
    lines.append(f"- feature_contract_status: {payload.get('feature_contract_status')}")
    lines.append(f"- expected_gain_truth_status: {payload.get('expected_gain_truth_status')}")
    lines.append(f"- expected_cost_truth_status: {payload.get('expected_cost_truth_status')}")
    lines.append(f"- b1_b2_cost_contamination_status: {payload.get('b1_b2_cost_contamination_status')}")
    lines.append(f"- threshold_patch_justified: {payload.get('threshold_patch_justified')}")
    lines.append(f"- profitability_backtest_ready: {payload.get('profitability_backtest_ready')}")
    lines.append(f"- next_required_patch: {payload.get('next_required_patch')}")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_engine_math_canary_artifacts(
    *,
    repo_root: Path | str,
    workflow_root: Path | str,
    pair_filter: str = "BTCUSDT",
    start: str | int | float | None = None,
    end: str | int | float | None = None,
    write_workflow_side_effect_reports: bool = False,
) -> dict[str, object]:
    repo = Path(repo_root).resolve()
    workflow = Path(workflow_root).resolve()
    reports_dir = repo / "reports"
    docs_audit_dir = repo / "docs" / "audit"
    fixture_root = repo / "tests" / "fixtures" / "synthetic_strategy_ladder_canary"
    reports_dir.mkdir(parents=True, exist_ok=True)
    docs_audit_dir.mkdir(parents=True, exist_ok=True)
    start_ms = _normalize_scope_bound_to_ms(start, end_of_day=False)
    end_ms = _normalize_scope_bound_to_ms(end, end_of_day=True)

    registry = build_engine_equation_feature_registry()
    thresholds = build_engine_threshold_boundary_report()
    synthetic = run_synthetic_strategy_ladder_e2e(fixture_root, runtime_mode="TEST")
    scoped_contexts = _load_scoped_candidate_contexts(
        workflow_root=workflow,
        pair_filter=pair_filter,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    feature_contract = build_pre_engine_feature_contract_audit(
        workflow_root=workflow,
        pair_filter=pair_filter,
        start_ms=start_ms,
        end_ms=end_ms,
        contexts=scoped_contexts,
    )
    reason_codes = build_reason_code_consistency_report(
        workflow_root=workflow,
        synthetic_report=synthetic,
        pair_filter=pair_filter,
        start_ms=start_ms,
        end_ms=end_ms,
        contexts=scoped_contexts,
    )
    counterfactual = build_engine_threshold_counterfactual_report(
        workflow_root=workflow,
        pair_filter=pair_filter,
        start_ms=start_ms,
        end_ms=end_ms,
        contexts=scoped_contexts,
    )
    cost_sources = build_cost_source_audit(
        workflow_root=workflow,
        pair_filter=pair_filter,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    contamination = build_b1_b2_cost_source_contamination_audit(
        workflow_root=workflow,
        pair_filter=pair_filter,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    native_vs_proxy = build_native_vs_proxy_blocker_report(
        workflow_root=workflow,
        pair_filter=pair_filter,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    final_verdict = build_v53_engine_math_canary_final_verdict(
        synthetic_report=synthetic,
        threshold_report=thresholds,
        reason_code_report=reason_codes,
        feature_contract_report=feature_contract,
        cost_source_report=cost_sources,
        contamination_report=contamination,
        counterfactual_report=counterfactual,
    )

    if write_workflow_side_effect_reports:
        run_dir = _workflow_run_dir(workflow)
        summary = StrategyLadderReportSummary.model_validate_json(
            (run_dir / "reports" / "strategy_ladder_summary.json").read_text(encoding="utf-8-sig")
        )
        run_manifest = StrategyLadderRunManifest.model_validate_json(
            (run_dir / "run_manifest.json").read_text(encoding="utf-8-sig")
        )
        write_strategy_ladder_gate_waterfall_reports(run_dir=run_dir, summary=summary, run_manifest=run_manifest)
        write_strategy_ladder_candidate_trade_semantics_audit(run_dir=run_dir, summary=summary, run_manifest=run_manifest)

    atomic_write_json(reports_dir / "engine_equation_feature_registry.json", registry, indent=2)
    atomic_write_json(reports_dir / "engine_threshold_boundary_report.json", thresholds, indent=2)
    atomic_write_json(reports_dir / "pre_engine_feature_contract_audit.json", feature_contract, indent=2)
    atomic_write_json(reports_dir / "engine_threshold_counterfactual_report.json", counterfactual, indent=2)
    atomic_write_json(reports_dir / "reason_code_consistency_report.json", reason_codes, indent=2)
    atomic_write_json(reports_dir / "cost_source_audit.json", cost_sources, indent=2)
    atomic_write_json(reports_dir / "b1_b2_cost_source_contamination_audit.json", contamination, indent=2)
    atomic_write_json(reports_dir / "native_vs_proxy_blocker_report.json", native_vs_proxy, indent=2)
    atomic_write_json(reports_dir / "v53_engine_math_canary_final_verdict.json", final_verdict, indent=2)

    atomic_write_text(docs_audit_dir / "ENGINE_EQUATION_FEATURE_REGISTRY.md", _render_registry_markdown(registry))
    atomic_write_text(docs_audit_dir / "ENGINE_THRESHOLD_BOUNDARY_REPORT.md", _render_boundary_markdown(thresholds))
    atomic_write_text(docs_audit_dir / "ENGINE_FEATURE_CONTRACT_AUDIT.md", _render_feature_contract_markdown(feature_contract))
    atomic_write_text(docs_audit_dir / "ENGINE_COUNTERFACTUAL_THRESHOLD_AUDIT.md", _render_counterfactual_markdown(counterfactual))
    atomic_write_text(docs_audit_dir / "ENGINE_CANARY_SYNTHETIC_TEST_PLAN.md", _render_synthetic_plan_markdown(synthetic))
    atomic_write_text(docs_audit_dir / "V53_ENGINE_MATH_CANARY_FINAL_VERDICT.md", _render_final_verdict_markdown(final_verdict))

    return {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "reports_dir": str(reports_dir),
        "docs_audit_dir": str(docs_audit_dir),
        "pair_filter": pair_filter,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "synthetic_all_ok": bool(synthetic.get("all_ok")),
        "reason_code_real_mismatch_count": int(reason_codes.get("real_mismatch_count", 0)),
        "final_verdict": str(final_verdict.get("final_verdict") or ""),
    }


__all__ = [
    "_CANARY_PROVENANCE",
    "bps_to_decimal",
    "build_b1_b2_cost_source_contamination_audit",
    "build_cost_source_audit",
    "build_engine_equation_feature_registry",
    "build_engine_threshold_boundary_report",
    "build_expected_cost_decimal",
    "build_pre_engine_feature_contract_audit",
    "build_reason_code_consistency_report",
    "build_v53_engine_math_canary_final_verdict",
    "decimal_to_bps",
    "ensure_synthetic_strategy_ladder_canary_fixture",
    "generate_engine_math_canary_artifacts",
    "percent_to_decimal",
    "reconstruct_native_candidate_case",
    "run_synthetic_strategy_ladder_e2e",
]
