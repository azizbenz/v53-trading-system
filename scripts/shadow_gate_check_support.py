"""Support primitives for the governed Shadow gate report launcher."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path

from calibration_methods import (
    compute_deflated_sharpe_ratio,
    compute_energy_distance_test,
    compute_hansen_spa_test,
    compute_ks_2sample,
    compute_mann_kendall_test,
    compute_probabilistic_sharpe_ratio,
)


HARD_VETO_KEYS = (
    "HV-1_haram",
    "HV-2_forbidden_features",
    "HV-3_breaker_breached",
    "HV-4_reconciliation_unresolved",
    "HV-5_unsigned_calibration",
    "HV-6_auto_recalibration",
    "HV-7_secret_manipulation",
    "HV-8_orphan_orders",
    "HV-9_sample_too_small",
    "HV-10_disk_full",
)
HALAL_CHECK_KEYS = ("HC-1", "HC-2", "HC-3", "HC-4", "HC-5", "HC-6")


@dataclass(frozen=True)
class GateSpec:
    palier: str
    min_days: int
    min_trades: int
    psr_floor: float
    dsr_floor: float | None
    ks_floor: float
    energy_floor: float
    drawdown_multiplier: float
    drawdown_absolute_floor: float
    calmar_floor: float
    sortino_floor: float
    profit_factor_floor: float
    mann_kendall_floor: float
    rolling_min_passes: int
    rolling_sharpe_floor: float
    rolling_requires_strictly_greater: bool
    hansen_ceiling: float | None
    requires_full_halal: bool
    requires_oos_reservation: bool


GATE_SPECS: dict[str, GateSpec] = {
    "G2.1": GateSpec(
        palier="shadow_1_to_2_months",
        min_days=20,
        min_trades=50,
        psr_floor=0.60,
        dsr_floor=None,
        ks_floor=0.01,
        energy_floor=0.01,
        drawdown_multiplier=1.5,
        drawdown_absolute_floor=-0.03,
        calmar_floor=0.5,
        sortino_floor=0.5,
        profit_factor_floor=1.05,
        mann_kendall_floor=0.05,
        rolling_min_passes=2,
        rolling_sharpe_floor=0.0,
        rolling_requires_strictly_greater=True,
        hansen_ceiling=None,
        requires_full_halal=False,
        requires_oos_reservation=False,
    ),
    "G2.2": GateSpec(
        palier="shadow_2_to_3_months",
        min_days=40,
        min_trades=150,
        psr_floor=0.85,
        dsr_floor=0.85,
        ks_floor=0.05,
        energy_floor=0.05,
        drawdown_multiplier=1.3,
        drawdown_absolute_floor=-0.05,
        calmar_floor=1.0,
        sortino_floor=1.0,
        profit_factor_floor=1.15,
        mann_kendall_floor=0.10,
        rolling_min_passes=3,
        rolling_sharpe_floor=0.0,
        rolling_requires_strictly_greater=True,
        hansen_ceiling=0.10,
        requires_full_halal=False,
        requires_oos_reservation=False,
    ),
    "G2.3": GateSpec(
        palier="shadow_3_to_micro_live",
        min_days=60,
        min_trades=300,
        psr_floor=0.95,
        dsr_floor=0.95,
        ks_floor=0.10,
        energy_floor=0.10,
        drawdown_multiplier=1.2,
        drawdown_absolute_floor=-0.07,
        calmar_floor=2.0,
        sortino_floor=1.5,
        profit_factor_floor=1.30,
        mann_kendall_floor=0.20,
        rolling_min_passes=3,
        rolling_sharpe_floor=0.5,
        rolling_requires_strictly_greater=False,
        hansen_ceiling=0.05,
        requires_full_halal=True,
        requires_oos_reservation=True,
    ),
}


def _dedupe(items: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _date_to_utc(date_value: object) -> str | None:
    if not isinstance(date_value, str) or not date_value:
        return None
    return f"{date_value}T00:00:00Z"


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _coerce_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    if isinstance(value, str):
        try:
            numeric = float(value)
        except ValueError:
            return None
        return numeric if math.isfinite(numeric) else None
    return None


def _coerce_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"pass", "passed", "true", "ok"}:
            return True
        if lowered in {"fail", "failed", "false", "ko"}:
            return False
    return None


def _coerce_series(value: object, engine_id: str) -> tuple[float, ...] | None:
    mapping = _as_mapping(value)
    if mapping is not None:
        if engine_id in mapping:
            return _coerce_series(mapping[engine_id], engine_id)
        for nested_key in (
            "returns",
            "values",
            "series",
            "data",
            "trade_returns_by_engine",
            "daily_returns_by_engine",
            "backtest_trade_returns_by_engine",
            "backtest_daily_returns_by_engine",
        ):
            if nested_key in mapping:
                return _coerce_series(mapping[nested_key], engine_id)
        return None
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        numeric_values = tuple(float(item) for item in value)
        return numeric_values if all(math.isfinite(item) for item in numeric_values) else None
    return None


def extract_series(
    evidence: Mapping[str, object],
    engine_id: str,
    *candidate_keys: str,
) -> tuple[float, ...] | None:
    for key in candidate_keys:
        if key in evidence:
            series = _coerce_series(evidence[key], engine_id)
            if series is not None:
                return series
    return None


def extract_scalar(
    evidence: Mapping[str, object],
    engine_id: str,
    *candidate_keys: str,
) -> float | None:
    for key in candidate_keys:
        raw = evidence.get(key)
        mapping = _as_mapping(raw)
        if mapping is not None and engine_id in mapping:
            numeric = _coerce_float(mapping[engine_id])
            if numeric is not None:
                return numeric
        numeric = _coerce_float(raw)
        if numeric is not None:
            return numeric
    return None


def _extract_loss_differentials(
    evidence: Mapping[str, object],
) -> dict[str, tuple[float, ...]] | None:
    raw = evidence.get("loss_differentials_by_candidate") or evidence.get("candidate_loss_differentials")
    mapping = _as_mapping(raw)
    if mapping is None:
        return None
    resolved: dict[str, tuple[float, ...]] = {}
    for candidate_id, values in mapping.items():
        series = _coerce_series(values, str(candidate_id))
        if series is None:
            return None
        resolved[str(candidate_id)] = series
    return resolved or None


def _metric(
    *,
    required: bool,
    threshold: object,
    value: object = None,
    passed: bool | None = None,
    status: str,
    reason: str | None = None,
    **extras: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "required": required,
        "threshold": threshold,
        "value": value,
        "pass": passed,
        "status": status,
    }
    if reason is not None:
        payload["reason"] = reason
    payload.update(extras)
    return payload


def _is_blocking_metric(metric: Mapping[str, object]) -> bool:
    return bool(metric.get("required")) and metric.get("pass") is False


def _sample_std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean_value = sum(values) / len(values)
    variance = sum((item - mean_value) ** 2 for item in values) / (len(values) - 1)
    return math.sqrt(max(variance, 0.0))


def _annualized_sharpe(values: Sequence[float]) -> float:
    std = _sample_std(values)
    if std <= 0.0:
        return 0.0
    return (sum(values) / len(values)) / std * math.sqrt(252.0)


def _rolling_window_sharpes(daily_returns: Sequence[float]) -> list[float]:
    if len(daily_returns) < 6:
        raise ValueError("rolling sharpe requires at least six daily observations")
    windows: list[list[float]] = [[], [], []]
    for index, value in enumerate(daily_returns):
        windows[min(index * 3 // len(daily_returns), 2)].append(value)
    return [_annualized_sharpe(window) for window in windows]


def _max_drawdown(returns: Sequence[float]) -> float:
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for item in returns:
        equity *= 1.0 + item
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, (equity / peak) - 1.0)
    return max_drawdown


def _annualized_return(daily_returns: Sequence[float]) -> float:
    if not daily_returns:
        return 0.0
    equity = 1.0
    for item in daily_returns:
        equity *= 1.0 + item
    return equity ** (252.0 / len(daily_returns)) - 1.0


def _sortino_ratio(daily_returns: Sequence[float]) -> float:
    if not daily_returns:
        return 0.0
    downside = [min(item, 0.0) for item in daily_returns]
    downside_variance = sum(item * item for item in downside) / len(daily_returns)
    downside_std = math.sqrt(max(downside_variance, 0.0))
    if downside_std <= 0.0:
        return 1_000_000.0 if sum(daily_returns) > 0.0 else 0.0
    return (sum(daily_returns) / len(daily_returns)) / downside_std * math.sqrt(252.0)


def _profit_factor(returns: Sequence[float]) -> float:
    gross_profit = sum(item for item in returns if item > 0.0)
    gross_loss = abs(sum(item for item in returns if item < 0.0))
    if gross_loss <= 0.0:
        return 1_000_000.0 if gross_profit > 0.0 else 0.0
    return gross_profit / gross_loss


def _build_data_window(
    evidence: Mapping[str, object],
    shadow_session_summary: Mapping[str, object],
) -> dict[str, str | None]:
    bundle_window = _as_mapping(evidence.get("data_window"))
    if bundle_window is not None:
        return {
            "start": bundle_window.get("start") if isinstance(bundle_window.get("start"), str) else None,
            "end": bundle_window.get("end") if isinstance(bundle_window.get("end"), str) else None,
        }
    session_dates = shadow_session_summary.get("session_dates")
    if isinstance(session_dates, Sequence) and not isinstance(session_dates, str) and session_dates:
        return {"start": _date_to_utc(session_dates[0]), "end": _date_to_utc(session_dates[-1])}
    base_session_date = shadow_session_summary.get("base_session_date")
    return {"start": _date_to_utc(base_session_date), "end": _date_to_utc(base_session_date)}


def build_reproducibility(source_paths: Sequence[Path], code_commit: str) -> dict[str, object]:
    digest = hashlib.sha256()
    for path in sorted(source_paths, key=lambda item: str(item)):
        digest.update(str(path).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return {
        "computed_with_method_version": "shadow_gate_math_v1",
        "code_commit": code_commit,
        "data_hash_sha256": digest.hexdigest(),
    }


def _evaluate_sample(
    *,
    spec: GateSpec,
    shadow_report: Mapping[str, object],
    shadow_session_summary: Mapping[str, object],
    shadow_daily_returns: Sequence[float] | None,
) -> tuple[dict[str, object], list[str]]:
    n_days = int(
        shadow_session_summary.get("consecutive_days")
        or shadow_report.get("consecutive_days")
        or (len(shadow_daily_returns) if shadow_daily_returns else 0)
    )
    sample = {
        "n_days": n_days,
        "n_trades": None,
        "n_min_required": spec.min_trades,
        "n_days_satisfied": n_days >= spec.min_days,
        "n_trades_satisfied": False,
    }
    blocking_reasons: list[str] = []
    if not sample["n_days_satisfied"]:
        blocking_reasons.append(f"{spec.palier} requires at least {spec.min_days} shadow days")
    return sample, blocking_reasons


def _evaluate_trade_stats(
    *,
    spec: GateSpec,
    engine_id: str,
    active_engines: Sequence[str],
    evidence: Mapping[str, object],
    missing_inputs: list[str],
) -> tuple[tuple[float, ...] | None, tuple[float, ...] | None, dict[str, dict[str, object]]]:
    stat_tests: dict[str, dict[str, object]] = {}
    shadow_trade_returns = extract_series(evidence, engine_id, "shadow_trade_returns", "trade_returns", "shadow_returns")
    backtest_trade_returns = extract_series(evidence, engine_id, "backtest_trade_returns", "reference_trade_returns", "backtest_returns")

    if shadow_trade_returns is None:
        missing_inputs.append("shadow_trade_returns")
        stat_tests["PSR"] = _metric(required=True, threshold=spec.psr_floor, passed=False, status="missing_input", reason="shadow_trade_returns missing")
    else:
        psr_result = compute_probabilistic_sharpe_ratio(shadow_trade_returns, benchmark_sharpe=0.0, acceptance_floor=spec.psr_floor)
        stat_tests["PSR"] = _metric(required=True, threshold=spec.psr_floor, value=psr_result.psr, passed=psr_result.passes_floor, status="ready", sample_sharpe=psr_result.sample_sharpe, observation_count=psr_result.observation_count)

    if spec.dsr_floor is None:
        stat_tests["DSR"] = _metric(required=False, threshold=None, passed=None, status="not_required")
    elif shadow_trade_returns is None:
        stat_tests["DSR"] = _metric(required=True, threshold=spec.dsr_floor, passed=False, status="missing_input", reason="shadow_trade_returns missing")
    else:
        trial_count = max(len(active_engines), 1)
        dsr_result = compute_deflated_sharpe_ratio(shadow_trade_returns, trial_count=trial_count, acceptance_floor=spec.dsr_floor)
        stat_tests["DSR"] = _metric(required=True, threshold=spec.dsr_floor, value=dsr_result.dsr, passed=dsr_result.passes_floor, status="ready", trial_count=trial_count, benchmark_sharpe=dsr_result.benchmark_sharpe)

    if shadow_trade_returns is None or backtest_trade_returns is None:
        if shadow_trade_returns is None:
            missing_inputs.append("shadow_trade_returns")
        if backtest_trade_returns is None:
            missing_inputs.append("backtest_trade_returns")
        stat_tests["KS_pvalue_vs_backtest"] = _metric(required=True, threshold=spec.ks_floor, passed=False, status="missing_input", reason="shadow_trade_returns/backtest_trade_returns missing")
        stat_tests["Energy_pvalue_vs_backtest"] = _metric(required=True, threshold=spec.energy_floor, passed=False, status="missing_input", reason="shadow_trade_returns/backtest_trade_returns missing")
    else:
        ks_result = compute_ks_2sample(shadow_trade_returns, backtest_trade_returns, acceptance_floor=spec.ks_floor)
        energy_result = compute_energy_distance_test(shadow_trade_returns, backtest_trade_returns, acceptance_floor=spec.energy_floor)
        stat_tests["KS_pvalue_vs_backtest"] = _metric(required=True, threshold=spec.ks_floor, value=ks_result.p_value, passed=ks_result.passes_floor, status="ready", ks_statistic=ks_result.ks_statistic)
        stat_tests["Energy_pvalue_vs_backtest"] = _metric(required=True, threshold=spec.energy_floor, value=energy_result.p_value, passed=energy_result.passes_floor, status="ready", energy_statistic=energy_result.energy_statistic, permutations=energy_result.n_permutations)

    if shadow_trade_returns is None:
        stat_tests["profit_factor"] = _metric(required=True, threshold=spec.profit_factor_floor, passed=False, status="missing_input", reason="shadow_trade_returns missing")
    else:
        profit_factor = _profit_factor(shadow_trade_returns)
        stat_tests["profit_factor"] = _metric(required=True, threshold=spec.profit_factor_floor, value=profit_factor, passed=profit_factor >= spec.profit_factor_floor, status="ready")

    return shadow_trade_returns, backtest_trade_returns, stat_tests


def _evaluate_daily_stats(
    *,
    spec: GateSpec,
    engine_id: str,
    evidence: Mapping[str, object],
    missing_inputs: list[str],
) -> tuple[tuple[float, ...] | None, dict[str, dict[str, object]]]:
    stat_tests: dict[str, dict[str, object]] = {}
    shadow_daily_returns = extract_series(evidence, engine_id, "shadow_daily_returns", "daily_returns")
    drawdown_calibration = extract_scalar(evidence, engine_id, "drawdown_calibration", "drawdown_calibration_by_engine")

    if shadow_daily_returns is None:
        missing_inputs.append("shadow_daily_returns")
        for name, threshold in (
            ("drawdown_max_live", f"<= {spec.drawdown_multiplier} * DD_calib and >= {spec.drawdown_absolute_floor}"),
            ("calmar", spec.calmar_floor),
            ("sortino", spec.sortino_floor),
            ("mann_kendall_pvalue", spec.mann_kendall_floor),
            ("rolling_3_windows_sharpe_positive", f"{spec.rolling_min_passes}/3 windows >= {spec.rolling_sharpe_floor}"),
        ):
            stat_tests[name] = _metric(required=True, threshold=threshold, passed=False, status="missing_input", reason="shadow_daily_returns missing")
        return None, stat_tests

    max_drawdown = _max_drawdown(shadow_daily_returns)
    if drawdown_calibration is None:
        missing_inputs.append("drawdown_calibration")
        stat_tests["drawdown_max_live"] = _metric(required=True, threshold=f"<= {spec.drawdown_multiplier} * DD_calib and >= {spec.drawdown_absolute_floor}", value=max_drawdown, passed=False, status="missing_input", reason="drawdown_calibration missing")
    else:
        relative_cap = spec.drawdown_multiplier * abs(drawdown_calibration)
        drawdown_pass = abs(max_drawdown) <= relative_cap and max_drawdown >= spec.drawdown_absolute_floor
        stat_tests["drawdown_max_live"] = _metric(required=True, threshold=f"<= {relative_cap:.6f} abs-dd and >= {spec.drawdown_absolute_floor}", value=max_drawdown, passed=drawdown_pass, status="ready", threshold_relative=f"<= {spec.drawdown_multiplier} * DD_calib", threshold_absolute=spec.drawdown_absolute_floor, drawdown_calibration=drawdown_calibration)

    annualized_return = _annualized_return(shadow_daily_returns)
    calmar = annualized_return / abs(max_drawdown) if abs(max_drawdown) > 1e-12 else (1_000_000.0 if annualized_return > 0.0 else 0.0)
    sortino = _sortino_ratio(shadow_daily_returns)
    mann_kendall = compute_mann_kendall_test(shadow_daily_returns, acceptance_floor=spec.mann_kendall_floor)
    rolling_sharpes = _rolling_window_sharpes(shadow_daily_returns)
    rolling_passes = sum((item > spec.rolling_sharpe_floor if spec.rolling_requires_strictly_greater else item >= spec.rolling_sharpe_floor) for item in rolling_sharpes)

    stat_tests["calmar"] = _metric(required=True, threshold=spec.calmar_floor, value=calmar, passed=calmar >= spec.calmar_floor, status="ready", annualized_return=annualized_return)
    stat_tests["sortino"] = _metric(required=True, threshold=spec.sortino_floor, value=sortino, passed=sortino >= spec.sortino_floor, status="ready")
    stat_tests["mann_kendall_pvalue"] = _metric(required=True, threshold=spec.mann_kendall_floor, value=mann_kendall.p_value, passed=mann_kendall.passes_floor, status="ready", trend_direction=mann_kendall.trend_direction, kendall_tau=mann_kendall.kendall_tau)
    stat_tests["rolling_3_windows_sharpe_positive"] = _metric(required=True, threshold=f"{spec.rolling_min_passes}/3 windows >= {spec.rolling_sharpe_floor}", value=rolling_sharpes, passed=rolling_passes >= spec.rolling_min_passes, status="ready", passing_windows=rolling_passes)
    return shadow_daily_returns, stat_tests


def _evaluate_hansen_stat(
    *,
    spec: GateSpec,
    engine_id: str,
    active_engines: Sequence[str],
    evidence: Mapping[str, object],
    missing_inputs: list[str],
) -> dict[str, object]:
    if spec.hansen_ceiling is None:
        return _metric(required=False, threshold=None, passed=None, status="not_required")
    if len(active_engines) <= 1:
        return _metric(required=False, threshold=spec.hansen_ceiling, passed=None, status="not_applicable", reason="single-engine shadow scope")
    loss_differentials = _extract_loss_differentials(evidence)
    if loss_differentials is None:
        missing_inputs.append("loss_differentials_by_candidate")
        return _metric(required=True, threshold=spec.hansen_ceiling, passed=False, status="missing_input", reason="loss_differentials_by_candidate missing")
    hansen = compute_hansen_spa_test(loss_differentials, acceptance_ceiling=spec.hansen_ceiling)
    hansen_pass = hansen.passes_floor and hansen.selected_candidate_id == engine_id
    reason = None if hansen.selected_candidate_id == engine_id else f"selected_candidate_id={hansen.selected_candidate_id}"
    return _metric(required=True, threshold=spec.hansen_ceiling, value=hansen.p_value, passed=hansen_pass, status="ready", selected_candidate_id=hansen.selected_candidate_id, bootstrap_samples=hansen.bootstrap_samples, reason=reason)


def _evaluate_hard_vetos(
    *,
    sample: Mapping[str, object],
    evidence: Mapping[str, object],
    missing_inputs: list[str],
) -> dict[str, dict[str, object]]:
    hard_veto_inputs = _as_mapping(evidence.get("hard_vetos")) or {}
    hard_vetos: dict[str, dict[str, object]] = {}
    for veto_key in HARD_VETO_KEYS:
        if veto_key == "HV-9_sample_too_small":
            passes_sample = bool(sample["n_days_satisfied"]) and bool(sample["n_trades_satisfied"])
            hard_vetos[veto_key] = _metric(required=True, threshold="sample minimum satisfied", value=0 if passes_sample else 1, passed=passes_sample, status="ready", violations=0 if passes_sample else 1)
            continue
        raw_value = hard_veto_inputs.get(veto_key)
        if raw_value is None:
            missing_inputs.append(f"hard_vetos.{veto_key}")
            hard_vetos[veto_key] = _metric(required=True, threshold="0 violations", passed=False, status="missing_input", reason=f"{veto_key} evidence missing")
            continue
        mapping = _as_mapping(raw_value)
        numeric = _coerce_float(mapping.get("violations") if mapping is not None and "violations" in mapping else raw_value)
        boolean = _coerce_bool(mapping.get("pass") if mapping is not None and "pass" in mapping else raw_value)
        violations = int(numeric) if numeric is not None else (0 if boolean is True else 1)
        hard_vetos[veto_key] = _metric(required=True, threshold="0 violations", value=violations, passed=violations == 0, status="ready", violations=violations)
    return hard_vetos


def _evaluate_halal_checks(
    *,
    spec: GateSpec,
    evidence: Mapping[str, object],
    missing_inputs: list[str],
) -> dict[str, dict[str, object]]:
    halal_inputs = _as_mapping(evidence.get("halal_checks")) or {}
    halal_checks: dict[str, dict[str, object]] = {}
    for halal_key in HALAL_CHECK_KEYS:
        if not spec.requires_full_halal:
            halal_checks[halal_key] = _metric(required=False, threshold="pass", passed=None, status="not_required")
            continue
        boolean = _coerce_bool(halal_inputs.get(halal_key))
        if boolean is None:
            missing_inputs.append(f"halal_checks.{halal_key}")
            halal_checks[halal_key] = _metric(required=True, threshold="pass", passed=False, status="missing_input", reason=f"{halal_key} evidence missing")
            continue
        halal_checks[halal_key] = _metric(required=True, threshold="pass", value="pass" if boolean else "fail", passed=boolean, status="ready")
    return halal_checks


def _evaluate_gate_specific_checks(
    *,
    spec: GateSpec,
    evidence: Mapping[str, object],
    missing_inputs: list[str],
) -> dict[str, dict[str, object]]:
    oos_reservation_used = _coerce_bool(evidence.get("oos_reservation_used"))
    gate_specific_checks = {
        "oos_reservation_used": _metric(required=False, threshold="true", passed=None, status="not_required"),
    }
    if not spec.requires_oos_reservation:
        return gate_specific_checks
    if oos_reservation_used is None:
        missing_inputs.append("oos_reservation_used")
        gate_specific_checks["oos_reservation_used"] = _metric(required=True, threshold="true", passed=False, status="missing_input", reason="oos_reservation_used missing")
        return gate_specific_checks
    gate_specific_checks["oos_reservation_used"] = _metric(required=True, threshold="true", value=oos_reservation_used, passed=oos_reservation_used, status="ready")
    return gate_specific_checks


def _append_metric_failures(
    target: list[str],
    metrics: Mapping[str, Mapping[str, object]],
) -> None:
    for name, metric_payload in metrics.items():
        if _is_blocking_metric(metric_payload):
            target.append(f"{name} failed: {metric_payload.get('reason', 'threshold not satisfied')}")


def build_shadow_gate_report(
    *,
    gate_id: str,
    engine_id: str,
    shadow_report: Mapping[str, object],
    shadow_session_summary: Mapping[str, object],
    shadow_summary: Mapping[str, object],
    evidence: Mapping[str, object],
    source_paths: Sequence[Path],
    code_commit: str,
) -> dict[str, object]:
    spec = GATE_SPECS[gate_id]
    active_engines = tuple(str(item) for item in shadow_summary.get("active_engines", ()) if isinstance(item, str))
    missing_inputs: list[str] = []
    sample, blocking_reasons = _evaluate_sample(spec=spec, shadow_report=shadow_report, shadow_session_summary=shadow_session_summary, shadow_daily_returns=extract_series(evidence, engine_id, "shadow_daily_returns", "daily_returns"))
    shadow_trade_returns, _, trade_stats = _evaluate_trade_stats(spec=spec, engine_id=engine_id, active_engines=active_engines, evidence=evidence, missing_inputs=missing_inputs)
    shadow_daily_returns, daily_stats = _evaluate_daily_stats(spec=spec, engine_id=engine_id, evidence=evidence, missing_inputs=missing_inputs)
    sample["n_trades"] = len(shadow_trade_returns) if shadow_trade_returns is not None else None
    sample["n_trades_satisfied"] = sample["n_trades"] is not None and sample["n_trades"] >= spec.min_trades
    if not sample["n_trades_satisfied"]:
        blocking_reasons.append(f"{gate_id} requires at least {spec.min_trades} executed shadow trades")

    stat_tests = {**trade_stats, **daily_stats, "hansen_spa_pvalue": _evaluate_hansen_stat(spec=spec, engine_id=engine_id, active_engines=active_engines, evidence=evidence, missing_inputs=missing_inputs)}
    hard_vetos = _evaluate_hard_vetos(sample=sample, evidence=evidence, missing_inputs=missing_inputs)
    halal_checks = _evaluate_halal_checks(spec=spec, evidence=evidence, missing_inputs=missing_inputs)
    gate_specific_checks = _evaluate_gate_specific_checks(spec=spec, evidence=evidence, missing_inputs=missing_inputs)
    _append_metric_failures(blocking_reasons, stat_tests)
    _append_metric_failures(blocking_reasons, hard_vetos)
    _append_metric_failures(blocking_reasons, halal_checks)
    _append_metric_failures(blocking_reasons, gate_specific_checks)

    decision = _as_mapping(shadow_summary.get("decision"))
    engine_present = engine_id in active_engines or not active_engines
    if not engine_present:
        blocking_reasons.append(f"engine {engine_id} is absent from shadow_summary.active_engines")
    overall_pass = not blocking_reasons
    return {
        "gate_id": gate_id,
        "palier": spec.palier,
        "engine": engine_id,
        "evaluated_at": _iso_now(),
        "data_window": _build_data_window(evidence, shadow_session_summary),
        "sample": sample,
        "stat_tests": stat_tests,
        "hard_vetos": hard_vetos,
        "halal_checks": halal_checks,
        "gate_specific_checks": gate_specific_checks,
        "source_artifacts": {
            "shadow_report_ready": bool(shadow_report.get("shadow_report_ready", False)),
            "promotion_gate_passed": bool(shadow_session_summary.get("promotion_gate_passed", False)),
            "shadow_summary_verdict": decision.get("verdict") if decision is not None else None,
            "shadow_summary_blocking_reasons": decision.get("blocking_reasons") if decision is not None else (),
            "active_engines": active_engines,
            "engine_present_in_summary": engine_present,
            "build14_status": shadow_summary.get("build14_status"),
        },
        "overall_machine_recommendation": "PASS_RECOMMENDED" if overall_pass else "FAIL",
        "human_decision_required": True,
        "human_signature": None,
        "calibration_in_use": evidence.get("calibration_in_use") if isinstance(evidence.get("calibration_in_use"), str) else "unknown",
        "missing_inputs": _dedupe(missing_inputs),
        "blocking_reasons": _dedupe(blocking_reasons),
        "reproducibility": build_reproducibility(source_paths, code_commit),
    }


__all__ = [
    "GATE_SPECS",
    "HALAL_CHECK_KEYS",
    "HARD_VETO_KEYS",
    "build_reproducibility",
    "build_shadow_gate_report",
]
