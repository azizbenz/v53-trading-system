"""Reporting-only Backtest Decision Report builder for Strategy Ladder runs."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.strategy_ladder_models import deterministic_payload_hash


CAPABILITY_AUDIT_FILENAME = "backtest_decision_capability_audit.json"
DECISION_REPORT_FILENAME = "backtest_decision_report.json"
TIMEFRAME_RANKING_FILENAME = "timeframe_ranking_report.json"
FEATURE_RANKING_FILENAME = "feature_ranking_report.json"
ML_VS_NO_ML_DELTA_FILENAME = "ml_vs_no_ml_delta_report.json"
ENGINE_BY_REGIME_FILENAME = "engine_by_regime_report.json"
PAIR_RANKING_FILENAME = "pair_ranking_report.json"
CAPITAL_BUCKET_RANKING_FILENAME = "capital_bucket_ranking_report.json"
COST_FILL_REALISM_FILENAME = "cost_fill_realism_report.json"
THRESHOLD_NEAR_MISS_FILENAME = "threshold_near_miss_report.json"
FINAL_VERDICT_FILENAME = "backtest_decision_report_final_verdict.json"

_SELECTED_STATES = {"selected", "executed", "reduced", "phantom"}
_PROXY_TOKENS = ("PROXY", "DEFAULT_BY_BOOK_STATUS", "DEFAULT_TO_CALIBRATE")
_READY_STATUSES = {"READY", "PROVEN", "MEASURED", "SHADOW_MEASURED"}


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return default


def _read_jsonl(path: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    rows.append(payload)
                    if limit is not None and len(rows) >= limit:
                        break
    except OSError:
        return rows
    return rows


def _json_files(root: Path) -> tuple[Path, ...]:
    if not root.is_dir():
        return ()
    return tuple(sorted(path for path in root.rglob("*.json") if path.is_file()))


def _existing_paths(*paths: Path) -> list[str]:
    return [str(path.resolve()) for path in paths if path.is_file()]


def _reports_dir(run_dir: Path) -> Path:
    return run_dir / "reports"


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    if isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            return None
        return number if math.isfinite(number) else None
    return None


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


def _as_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value if str(item))
    return ()


def _status_counts(rows: list[dict[str, Any]], key: str = "status") -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        status = str(row.get(key) or "")
        if status:
            counter[status] += 1
    return dict(sorted(counter.items()))


def _has_proxy_token(*values: Any) -> bool:
    joined = " ".join(
        str(item)
        for value in values
        for item in (
            value
            if isinstance(value, (list, tuple, set))
            else (value,)
        )
    ).upper()
    return any(token in joined for token in _PROXY_TOKENS)


def _candidate_index(candidate_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("candidate_id") or ""): row
        for row in candidate_rows
        if str(row.get("candidate_id") or "")
    }


def _load_bucket_rows(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in _json_files(run_dir / "detailed_replay" / "by_bucket"):
        payload = _read_json(path, {})
        if isinstance(payload, dict):
            row = dict(payload)
            row["_artifact_path"] = str(path.resolve())
            rows.append(row)
    return rows


def _metric_from_report_rows(
    rows: list[dict[str, Any]],
    *,
    candidate_id: str,
    capital_bucket: int,
    field_names: tuple[str, ...],
) -> float | None:
    for row in rows:
        if str(row.get("candidate_id") or "") != candidate_id:
            continue
        if _as_int(row.get("capital_bucket")) != capital_bucket:
            continue
        for field_name in field_names:
            value = _as_float(row.get(field_name))
            if value is not None:
                return value
    return None


def _unique_state_counts(bucket_rows: list[dict[str, Any]]) -> dict[str, int]:
    by_state: dict[str, set[str]] = defaultdict(set)
    for row in bucket_rows:
        candidate_id = str(row.get("candidate_id") or "")
        state = str(row.get("execution_state") or "").lower()
        if candidate_id and state:
            by_state[state].add(candidate_id)
    return {state: len(ids) for state, ids in by_state.items()}


def _summary_counts(
    summary: dict[str, Any],
    bucket_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
) -> dict[str, int]:
    state_counts = _unique_state_counts(bucket_rows)
    selected_ids = {
        str(row.get("candidate_id") or "")
        for row in bucket_rows
        if str(row.get("execution_state") or "").lower() in _SELECTED_STATES
    }
    return {
        "candidate_count": _as_int(summary.get("candidate_count")) or len(candidate_rows),
        "selected_count": len({item for item in selected_ids if item}),
        "executed_count": state_counts.get("executed", 0),
        "hard_blocked_count": state_counts.get("hard_blocked", 0),
    }


def _rank_status(executed_count: int, has_rows: bool) -> str:
    if not has_rows:
        return "missing"
    if executed_count <= 0:
        return "insufficient_executions"
    return "ranked"


def _ranked_rows(
    rows: list[dict[str, Any]],
    *,
    score_key: str,
) -> list[dict[str, Any]]:
    ranked_candidates = [
        row for row in rows if _as_float(row.get(score_key)) is not None
    ]
    ranked_candidates.sort(
        key=lambda row: (
            _as_float(row.get(score_key)) or float("-inf"),
            _as_int(row.get("executed_count")),
        ),
        reverse=True,
    )
    rank_by_key = {id(row): index + 1 for index, row in enumerate(ranked_candidates)}
    result: list[dict[str, Any]] = []
    for row in rows:
        output = dict(row)
        output["rank"] = rank_by_key.get(id(row))
        result.append(output)
    return result


def _write_payload(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    final_payload = dict(payload)
    final_payload.setdefault("generated_at", _utc_now_iso())
    final_payload["artifact_hash"] = deterministic_payload_hash(final_payload)
    atomic_write_json(path, final_payload, indent=2)
    return final_payload


def _build_timeframe_ranking(
    *,
    run_dir: Path,
    candidate_rows: list[dict[str, Any]],
    bucket_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    matrix_rows = _read_json(_reports_dir(run_dir) / "timeframe_matrix.json", [])
    if not isinstance(matrix_rows, list):
        matrix_rows = []
    candidate_by_id = _candidate_index(candidate_rows)
    state_counts: dict[str, Counter[str]] = defaultdict(Counter)
    hard_counts: Counter[str] = Counter()
    selected_counts: Counter[str] = Counter()
    for row in bucket_rows:
        candidate = candidate_by_id.get(str(row.get("candidate_id") or ""), {})
        timeframe = str(candidate.get("timeframe") or "unknown")
        state = str(row.get("execution_state") or "").lower()
        state_counts[timeframe][state] += 1
        if state in _SELECTED_STATES:
            selected_counts[timeframe] += 1
        if state == "hard_blocked":
            hard_counts[timeframe] += 1
    rows: list[dict[str, Any]] = []
    for item in matrix_rows:
        if not isinstance(item, dict):
            continue
        timeframe = str(item.get("timeframe") or "unknown")
        executed_count = _as_int(item.get("executed_count"))
        rows.append(
            {
                "timeframe": timeframe,
                "candidate_count": _as_int(item.get("candidate_count")),
                "selected_count": selected_counts.get(timeframe, 0),
                "executed_count": executed_count,
                "hard_blocked_count": hard_counts.get(timeframe, 0),
                "net_edge_bps": _as_float(item.get("net_pnl_bps")),
                "cost_bps": _as_float(item.get("avg_realized_cost_fraction")),
                "mfe_bps": None,
                "mae_bps": None,
                "drawdown_bps": _as_float(item.get("max_drawdown_bps")),
                "psr": None,
                "dsr": None,
                "recommendation": _rank_status(executed_count, True),
            }
        )
    ranked = _ranked_rows(rows, score_key="net_edge_bps")
    top = next((row for row in ranked if row.get("rank") == 1 and row["executed_count"] > 0), None)
    status = "TIMEFRAME_RANKING_MISSING" if not rows else "TIMEFRAME_RANKING_PARTIAL"
    return {
        "schema_version": "v53.timeframe_ranking_report.v1",
        "status": status,
        "run_id": str(_read_json(run_dir / "run_manifest.json", {}).get("run_id") or ""),
        "ranking_status": "ranked" if top else _rank_status(0, bool(rows)),
        "top_timeframe": None if top is None else top.get("timeframe"),
        "rows": ranked,
        "missing_fields": ["psr", "dsr", "mfe_bps", "mae_bps"],
    }


def _feature_names_from_artifacts(run_dir: Path) -> tuple[str, ...]:
    names: list[str] = []
    label_rows = _read_jsonl(
        run_dir / "ml_label_store" / "strategy_ladder_replay_label_store.jsonl",
        limit=25,
    )
    for row in label_rows:
        feature_values = row.get("feature_values")
        if isinstance(feature_values, dict):
            names.extend(str(name) for name in feature_values if str(name))
    for path in (
        run_dir / "reports" / "strategy_ladder_ml_lab_handoff_report.json",
        run_dir / "strategy_ladder_ml_lab_handoff_report.json",
        run_dir / "reports" / "training_report.json",
    ):
        payload = _read_json(path, {})
        if isinstance(payload, dict):
            names.extend(_as_tuple(payload.get("feature_names")))
    return tuple(dict.fromkeys(names))


def _build_feature_ranking(run_dir: Path) -> dict[str, Any]:
    feature_names = _feature_names_from_artifacts(run_dir)
    ablation_paths = tuple(
        path
        for path in _json_files(run_dir)
        if path.name.startswith("feature_ablation_")
    )
    ablation_by_feature: dict[str, dict[str, Any]] = {}
    for path in ablation_paths:
        payload = _read_json(path, {})
        if isinstance(payload, dict) and payload.get("feature_name"):
            ablation_by_feature[str(payload["feature_name"])] = payload
    rows: list[dict[str, Any]] = []
    for name in feature_names:
        ablation = ablation_by_feature.get(name, {})
        rows.append(
            {
                "feature_name": name,
                "rank": None,
                "importance": None,
                "ablation_delta_psr": _as_float(ablation.get("delta_psr")),
                "ablation_delta_sharpe": _as_float(ablation.get("delta_sharpe")),
                "ablation_delta_break_even_bps": _as_float(
                    ablation.get("delta_break_even_bps")
                ),
                "stability_status": "UNAVAILABLE",
                "grounding_status": "FEATURE_GROUNDING_PRESENT"
                if feature_names
                else "FEATURE_GROUNDING_NOT_PROVEN",
                "utility_status": (
                    str(ablation.get("verdict"))
                    if ablation
                    else "UNPROVEN_WITHOUT_ABLATION_OR_OOS_STABILITY"
                ),
                "evidence_ref": str(Path(ablation.get("evidence_artifact_ref", "")).resolve())
                if ablation.get("evidence_artifact_ref")
                else "",
            }
        )
    status = (
        "FEATURE_RANKING_MISSING"
        if not feature_names
        else "FEATURE_RANKING_PARTIAL"
        if not ablation_paths
        else "FEATURE_RANKING_PARTIAL"
    )
    return {
        "schema_version": "v53.feature_ranking_report.v1",
        "status": status,
        "feature_count": len(feature_names),
        "ablation_report_count": len(ablation_paths),
        "rows": rows,
        "missing_fields": ["feature_importance", "oos_ablation", "period_stability", "regime_stability"]
        if not ablation_paths
        else ["feature_importance", "period_stability", "regime_stability"],
    }


def _build_ml_vs_no_ml_delta(
    *,
    run_dir: Path,
    baseline_run_dir: Path | None,
    comparison_run_dir: Path | None,
) -> dict[str, Any]:
    current_summary = _read_json(_reports_dir(run_dir) / "strategy_ladder_summary.json", {})
    if baseline_run_dir is None or comparison_run_dir is None:
        return {
            "schema_version": "v53.ml_vs_no_ml_delta_report.v1",
            "status": "ML_VS_NO_ML_REPORT_UNAVAILABLE",
            "reason": "aligned_baseline_and_overlay_run_dirs_not_provided",
            "current_mode": str(current_summary.get("ml_mode_status") or "ML_MODE_OFF")
            if isinstance(current_summary, dict)
            else "ML_MODE_OFF",
            "deltas": {},
        }
    baseline = _read_json(_reports_dir(baseline_run_dir) / "strategy_ladder_summary.json", {})
    comparison = _read_json(
        _reports_dir(comparison_run_dir) / "strategy_ladder_summary.json",
        {},
    )
    if not isinstance(baseline, dict) or not isinstance(comparison, dict):
        return {
            "schema_version": "v53.ml_vs_no_ml_delta_report.v1",
            "status": "ML_VS_NO_ML_REPORT_UNAVAILABLE",
            "reason": "baseline_or_comparison_summary_missing",
            "deltas": {},
        }
    fields = (
        "candidate_count",
        "selected_count",
        "executed_trade_count",
        "expected_edge_governed_count",
        "expected_edge_proxy_count",
    )
    deltas = {
        field: _as_int(comparison.get(field)) - _as_int(baseline.get(field))
        for field in fields
    }
    return {
        "schema_version": "v53.ml_vs_no_ml_delta_report.v1",
        "status": "ML_VS_NO_ML_REPORT_READY",
        "baseline_run_dir": str(baseline_run_dir.resolve()),
        "comparison_run_dir": str(comparison_run_dir.resolve()),
        "deltas": deltas,
    }


def _regime_for_candidate(candidate: dict[str, Any]) -> str:
    regime = str(candidate.get("regime") or "").strip()
    if regime:
        return regime
    payload = candidate.get("compatibility_payload")
    if isinstance(payload, dict):
        for key in ("regime", "market_regime", "trend_regime", "liquidity_regime"):
            value = str(payload.get(key) or "").strip()
            if value:
                return value
    return ""


def _build_engine_by_regime(
    candidate_rows: list[dict[str, Any]],
    bucket_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_by_id = _candidate_index(candidate_rows)
    rows_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in bucket_rows:
        candidate = candidate_by_id.get(str(row.get("candidate_id") or ""), {})
        regime = _regime_for_candidate(candidate)
        if not regime:
            continue
        rows_by_key[(str(row.get("engine_id") or "unknown"), regime)].append(row)
    rows: list[dict[str, Any]] = []
    for (engine_id, regime), scoped in sorted(rows_by_key.items()):
        executed_returns = [
            value
            for value in (_as_float(row.get("executed_only_net_return")) for row in scoped)
            if value is not None
        ]
        rows.append(
            {
                "engine_id": engine_id,
                "market_regime": regime,
                "candidate_count": len({str(row.get("candidate_id") or "") for row in scoped}),
                "selected_count": sum(
                    1
                    for row in scoped
                    if str(row.get("execution_state") or "").lower() in _SELECTED_STATES
                ),
                "executed_count": sum(
                    1 for row in scoped if str(row.get("execution_state") or "").lower() == "executed"
                ),
                "net_edge_bps": round(sum(executed_returns) * 10_000.0, 6)
                if executed_returns
                else None,
                "drawdown_bps": None,
                "cost_bps": None,
                "hard_blocked_count": sum(
                    1
                    for row in scoped
                    if str(row.get("execution_state") or "").lower() == "hard_blocked"
                ),
            }
        )
    return {
        "schema_version": "v53.engine_by_regime_report.v1",
        "status": "ENGINE_BY_REGIME_MISSING" if not rows else "ENGINE_BY_REGIME_PARTIAL",
        "rows": rows,
        "missing_fields": []
        if rows
        else ["market_regime", "trend_regime", "volatility_regime", "liquidity_regime"],
    }


def _build_pair_ranking(
    *,
    run_dir: Path,
    bucket_rows: list[dict[str, Any]],
    spread_rows: list[dict[str, Any]],
    slippage_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    matrix_rows = _read_json(_reports_dir(run_dir) / "pair_matrix.json", [])
    if not isinstance(matrix_rows, list):
        matrix_rows = []
    rows: list[dict[str, Any]] = []
    for item in matrix_rows:
        if not isinstance(item, dict):
            continue
        pair = str(item.get("pair") or "unknown")
        scoped = [row for row in bucket_rows if str(row.get("pair") or "") == pair]
        spreads: list[float] = []
        slippages: list[float] = []
        for row in scoped:
            candidate_id = str(row.get("candidate_id") or "")
            bucket = _as_int(row.get("capital_bucket"))
            spread = _metric_from_report_rows(
                spread_rows,
                candidate_id=candidate_id,
                capital_bucket=bucket,
                field_names=("spread_bps", "spread_cost_bps"),
            )
            slippage = _metric_from_report_rows(
                slippage_rows,
                candidate_id=candidate_id,
                capital_bucket=bucket,
                field_names=("walk_cost_bps", "slippage_bps", "measured_slippage_bps"),
            )
            if spread is not None:
                spreads.append(spread)
            if slippage is not None:
                slippages.append(slippage)
        executed_count = _as_int(item.get("executed_count"))
        rows.append(
            {
                "pair": pair,
                "spread_mean_bps": round(mean(spreads), 6) if spreads else None,
                "slippage_mean_bps": round(mean(slippages), 6) if slippages else None,
                "candidate_count": _as_int(item.get("candidate_count")),
                "selected_count": _as_int(item.get("selected_count")),
                "executed_count": executed_count,
                "net_edge": _as_float(item.get("executed_only_net_return")),
                "cost_infeasible_count": sum(
                    1 for row in scoped if "COST" in " ".join(_as_tuple(row.get("reason_codes")))
                ),
                "fill_realism_status": str(item.get("fill_realism_status") or "FILL_REALISM_NOT_PROVEN"),
                "final_recommendation": _rank_status(executed_count, True),
            }
        )
    ranked = _ranked_rows(rows, score_key="net_edge")
    top = next((row for row in ranked if row.get("rank") == 1 and row["executed_count"] > 0), None)
    return {
        "schema_version": "v53.pair_ranking_report.v1",
        "status": "PAIR_RANKING_MISSING" if not rows else "PAIR_RANKING_PARTIAL",
        "top_pair": None if top is None else top.get("pair"),
        "rows": ranked,
    }


def _build_capital_bucket_ranking(
    *,
    run_dir: Path,
    slippage_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    matrix_rows = _read_json(_reports_dir(run_dir) / "capital_bucket_matrix.json", [])
    if not isinstance(matrix_rows, list):
        matrix_rows = []
    rows: list[dict[str, Any]] = []
    for item in matrix_rows:
        if not isinstance(item, dict):
            continue
        bucket = _as_int(item.get("capital_bucket"))
        bucket_slippages = [
            value
            for value in (
                _as_float(row.get("walk_cost_bps"))
                or _as_float(row.get("slippage_bps"))
                for row in slippage_rows
                if _as_int(row.get("capital_bucket")) == bucket
            )
            if value is not None
        ]
        record_count = _as_int(item.get("record_count"))
        executed_count = _as_int(item.get("executed_count"))
        reduced_count = _as_int(item.get("reduced_count"))
        rows.append(
            {
                "capital_bucket": bucket,
                "fill_ratio": round((executed_count + reduced_count) / record_count, 6)
                if record_count
                else None,
                "slippage_bps": round(mean(bucket_slippages), 6)
                if bucket_slippages
                else None,
                "cost_bps": None,
                "net_edge": _as_float(item.get("executed_only_net_return")),
                "break_even_gap_bps": None,
                "selected_count": _as_int(item.get("selected_count")),
                "executed_count": executed_count,
                "capital_recommendation": _rank_status(executed_count, True),
            }
        )
    ranked = _ranked_rows(rows, score_key="net_edge")
    top = next((row for row in ranked if row.get("rank") == 1 and row["executed_count"] > 0), None)
    return {
        "schema_version": "v53.capital_bucket_ranking_report.v1",
        "status": "CAPITAL_BUCKET_RANKING_MISSING"
        if not rows
        else "CAPITAL_BUCKET_RANKING_PARTIAL",
        "top_capital_bucket": None if top is None else top.get("capital_bucket"),
        "rows": ranked,
        "missing_fields": ["cost_bps", "break_even_gap_bps"],
    }


def _build_cost_fill_realism(
    *,
    run_dir: Path,
    summary: dict[str, Any],
    spread_rows: list[dict[str, Any]],
    slippage_rows: list[dict[str, Any]],
    fill_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    execution_summary = _read_json(_reports_dir(run_dir) / "execution_realism_summary.json", {})
    gap_codes = _as_tuple(summary.get("execution_fidelity_gap_codes"))
    source_values = (
        summary.get("fee_model_source"),
        summary.get("spread_model_source"),
        summary.get("slippage_model_source"),
        summary.get("partial_fill_model_source"),
        summary.get("adverse_selection_source"),
        gap_codes,
    )
    proxy_present = _has_proxy_token(*source_values)
    required_files = {
        "measured_spread_report": str((_reports_dir(run_dir) / "measured_spread_report.json").resolve())
        if (_reports_dir(run_dir) / "measured_spread_report.json").is_file()
        else "",
        "measured_slippage_report": str((_reports_dir(run_dir) / "measured_slippage_report.json").resolve())
        if (_reports_dir(run_dir) / "measured_slippage_report.json").is_file()
        else "",
        "fill_realism_report": str((_reports_dir(run_dir) / "fill_realism_report.json").resolve())
        if (_reports_dir(run_dir) / "fill_realism_report.json").is_file()
        else "",
        "execution_realism_summary": str((_reports_dir(run_dir) / "execution_realism_summary.json").resolve())
        if (_reports_dir(run_dir) / "execution_realism_summary.json").is_file()
        else "",
    }
    ready = (
        all(required_files.values())
        and not proxy_present
        and not gap_codes
        and str(summary.get("adverse_selection_source") or "").upper() != "REPLAY_PROXY"
    )
    return {
        "schema_version": "v53.cost_fill_realism_report.v1",
        "status": "COST_FILL_REALISM_READY" if ready else "COST_FILL_REALISM_PARTIAL",
        "profitability_ready": ready,
        "proxy_contamination_present": proxy_present,
        "execution_fidelity_gap_codes": gap_codes,
        "source_status": {
            "fee_model_source": summary.get("fee_model_source"),
            "spread_model_source": summary.get("spread_model_source"),
            "slippage_model_source": summary.get("slippage_model_source"),
            "partial_fill_model_source": summary.get("partial_fill_model_source"),
            "adverse_selection_source": summary.get("adverse_selection_source"),
        },
        "report_refs": required_files,
        "spread_status_counts": _status_counts(spread_rows),
        "slippage_status_counts": _status_counts(slippage_rows),
        "fill_realism_status_counts": _status_counts(fill_rows),
        "execution_realism_summary": execution_summary if isinstance(execution_summary, dict) else {},
        "missing_reports": [key for key, value in required_files.items() if not value],
    }


def _build_threshold_near_miss(run_dir: Path) -> dict[str, Any]:
    threshold_payload = _read_json(_reports_dir(run_dir) / "candidate_threshold_audit.json", {})
    waterfall_payload = _read_json(_reports_dir(run_dir) / "gate_waterfall_analysis.json", {})
    matrix_payload = _read_json(_reports_dir(run_dir) / "gate_counterfactual_matrix.json", {})
    threshold_rows = (
        threshold_payload.get("rows")
        if isinstance(threshold_payload, dict)
        else []
    )
    if not isinstance(threshold_rows, list):
        threshold_rows = []
    counterfactual_rows = (
        matrix_payload.get("rows") if isinstance(matrix_payload, dict) else []
    )
    if not isinstance(counterfactual_rows, list):
        counterfactual_rows = []
    near_miss_count = sum(
        1
        for row in threshold_rows
        if isinstance(row, dict)
        and str(row.get("threshold_alignment_status") or "") == "THRESHOLD_TOO_LOOSE_FOR_B2"
    )
    best = (
        waterfall_payload.get("best_counterfactual_scenario")
        if isinstance(waterfall_payload, dict)
        else {}
    )
    if not isinstance(best, dict):
        best = {}
    return {
        "schema_version": "v53.threshold_near_miss_report.v1",
        "status": "THRESHOLD_NEAR_MISS_MISSING"
        if not threshold_rows and not counterfactual_rows
        else "THRESHOLD_NEAR_MISS_PARTIAL",
        "near_miss_count": near_miss_count,
        "far_fail_count": None,
        "counterfactual_pass_count": _as_int(best.get("counterfactual_survival_count")),
        "best_counterfactual_scenario": best.get("scenario_id") or "",
        "threshold_patch_justified": False,
        "rows": threshold_rows,
        "missing_fields": ["threshold_distance", "far_fail_count"],
    }


def _build_capability_audit(
    *,
    run_dir: Path,
    timeframe_report: dict[str, Any],
    feature_report: dict[str, Any],
    ml_delta_report: dict[str, Any],
    engine_regime_report: dict[str, Any],
    pair_report: dict[str, Any],
    capital_report: dict[str, Any],
    cost_report: dict[str, Any],
    threshold_report: dict[str, Any],
) -> dict[str, Any]:
    reports = _reports_dir(run_dir)
    capability_inputs = {
        "timeframe_ranking": (
            timeframe_report,
            _existing_paths(reports / "timeframe_matrix.json"),
            ["psr", "dsr", "mfe_bps", "mae_bps"],
        ),
        "feature_ranking": (
            feature_report,
            _existing_paths(
                run_dir / "ml_label_store" / "strategy_ladder_replay_label_store.jsonl",
                run_dir / "ml_label_store" / "f16_feature_coverage_report.json",
                reports / "feature_grounding_contract_report.json",
                reports / "feature_ablation_report.json",
                reports / "strategy_ladder_ml_lab_handoff_report.json",
            ),
            list(feature_report.get("missing_fields") or []),
        ),
        "ml_vs_no_ml": (
            ml_delta_report,
            [],
            ["aligned_baseline_run", "aligned_overlay_run"]
            if str(ml_delta_report.get("status") or "").endswith("UNAVAILABLE")
            else [],
        ),
        "engine_by_regime": (
            engine_regime_report,
            _existing_paths(reports / "engine_matrix.json"),
            list(engine_regime_report.get("missing_fields") or []),
        ),
        "pair_ranking": (
            pair_report,
            _existing_paths(reports / "pair_matrix.json"),
            [],
        ),
        "capital_bucket_ranking": (
            capital_report,
            _existing_paths(reports / "capital_bucket_matrix.json"),
            list(capital_report.get("missing_fields") or []),
        ),
        "cost_fill_realism": (
            cost_report,
            _existing_paths(
                reports / "measured_spread_report.json",
                reports / "measured_slippage_report.json",
                reports / "fill_realism_report.json",
                reports / "execution_realism_summary.json",
            ),
            list(cost_report.get("missing_reports") or []),
        ),
        "threshold_near_miss": (
            threshold_report,
            _existing_paths(
                reports / "candidate_threshold_audit.json",
                reports / "gate_counterfactual_matrix.json",
            ),
            list(threshold_report.get("missing_fields") or []),
        ),
    }
    capabilities: dict[str, dict[str, Any]] = {}
    for name, (payload, existing_files, missing_fields) in capability_inputs.items():
        raw_status = str(payload.get("status") or "").upper()
        if "READY" in raw_status and not missing_fields:
            status = "READY"
        elif "MISSING" in raw_status or (not existing_files and name != "ml_vs_no_ml"):
            status = "MISSING"
        else:
            status = "PARTIAL"
        capabilities[name] = {
            "status": status,
            "existing_files": existing_files,
            "missing_fields": missing_fields,
            "patch_needed": status != "READY",
        }
    statuses = {item["status"] for item in capabilities.values()}
    overall = (
        "BACKTEST_DECISION_REPORT_READY"
        if statuses == {"READY"}
        else "BACKTEST_DECISION_REPORT_MISSING"
        if statuses == {"MISSING"}
        else "BACKTEST_DECISION_REPORT_PARTIAL"
    )
    return {
        "schema_version": "v53.backtest_decision_capability_audit.v1",
        "workflow_root": str(run_dir.parent.parent.resolve())
        if run_dir.parent.name == "backtest_strategy_ladder"
        else str(run_dir.resolve()),
        "run_dir": str(run_dir.resolve()),
        "capabilities": capabilities,
        "overall_status": overall,
        "profitability_backtest_ready": False,
    }


def _profitability_claim_allowed(
    *,
    counts: dict[str, int],
    summary: dict[str, Any],
    profitability_verdict: dict[str, Any],
    cost_report: dict[str, Any],
) -> bool:
    if counts["executed_count"] <= 0:
        return False
    if not bool(profitability_verdict.get("profitability_claim_allowed")):
        return False
    if cost_report.get("status") != "COST_FILL_REALISM_READY":
        return False
    if _has_proxy_token(
        summary.get("blocker_codes"),
        summary.get("execution_fidelity_gap_codes"),
        summary.get("expected_edge_label_fidelity"),
        summary.get("expected_edge_truth_status"),
    ):
        return False
    if _as_int(summary.get("expected_edge_proxy_count")) > 0:
        return False
    return True


def _recommendation(
    *,
    profitability_allowed: bool,
    cost_report: dict[str, Any],
    summary: dict[str, Any],
    counts: dict[str, int],
) -> dict[str, Any]:
    blockers = list(_as_tuple(summary.get("blocker_codes")))
    if counts["executed_count"] <= 0 and "NO_EXECUTED_TRADES" not in blockers:
        blockers.insert(0, "NO_EXECUTED_TRADES")
    if cost_report.get("status") != "COST_FILL_REALISM_READY":
        blockers.append("COST_FILL_REALISM_NOT_READY")
    blockers = list(dict.fromkeys(blockers))
    return {
        "live_ready": bool(profitability_allowed),
        "shadow_ready": bool(profitability_allowed and not blockers),
        "research_only": not profitability_allowed,
        "next_required_patch": blockers[0] if blockers else "",
        "blockers": blockers,
    }


def write_backtest_decision_reports(
    run_dir: str | Path,
    *,
    baseline_run_dir: str | Path | None = None,
    comparison_run_dir: str | Path | None = None,
) -> dict[str, str]:
    """Read existing B2 artifacts and write decision-report artifacts only."""

    resolved_run_dir = Path(run_dir)
    reports = _reports_dir(resolved_run_dir)
    reports.mkdir(parents=True, exist_ok=True)

    summary = _read_json(reports / "strategy_ladder_summary.json", {})
    if not isinstance(summary, dict):
        summary = {}
    run_manifest = _read_json(resolved_run_dir / "run_manifest.json", {})
    if not isinstance(run_manifest, dict):
        run_manifest = {}
    profitability_verdict = _read_json(reports / "profitability_truth_verdict.json", {})
    if not isinstance(profitability_verdict, dict):
        profitability_verdict = {}

    candidate_rows = _read_jsonl(
        resolved_run_dir / "fast_candidates" / "candidate_events.jsonl"
    )
    bucket_rows = _load_bucket_rows(resolved_run_dir)
    counts = _summary_counts(summary, bucket_rows, candidate_rows)

    spread_payload = _read_json(reports / "measured_spread_report.json", {})
    slippage_payload = _read_json(reports / "measured_slippage_report.json", {})
    fill_payload = _read_json(reports / "fill_realism_report.json", {})
    spread_rows = list(spread_payload.get("rows") or []) if isinstance(spread_payload, dict) else []
    slippage_rows = (
        list(slippage_payload.get("rows") or []) if isinstance(slippage_payload, dict) else []
    )
    fill_rows = list(fill_payload.get("rows") or []) if isinstance(fill_payload, dict) else []

    timeframe_report = _build_timeframe_ranking(
        run_dir=resolved_run_dir,
        candidate_rows=candidate_rows,
        bucket_rows=bucket_rows,
    )
    feature_report = _build_feature_ranking(resolved_run_dir)
    ml_delta_report = _build_ml_vs_no_ml_delta(
        run_dir=resolved_run_dir,
        baseline_run_dir=Path(baseline_run_dir) if baseline_run_dir is not None else None,
        comparison_run_dir=Path(comparison_run_dir) if comparison_run_dir is not None else None,
    )
    engine_regime_report = _build_engine_by_regime(candidate_rows, bucket_rows)
    pair_report = _build_pair_ranking(
        run_dir=resolved_run_dir,
        bucket_rows=bucket_rows,
        spread_rows=spread_rows,
        slippage_rows=slippage_rows,
    )
    capital_report = _build_capital_bucket_ranking(
        run_dir=resolved_run_dir,
        slippage_rows=slippage_rows,
    )
    cost_report = _build_cost_fill_realism(
        run_dir=resolved_run_dir,
        summary=summary,
        spread_rows=spread_rows,
        slippage_rows=slippage_rows,
        fill_rows=fill_rows,
    )
    threshold_report = _build_threshold_near_miss(resolved_run_dir)
    capability_audit = _build_capability_audit(
        run_dir=resolved_run_dir,
        timeframe_report=timeframe_report,
        feature_report=feature_report,
        ml_delta_report=ml_delta_report,
        engine_regime_report=engine_regime_report,
        pair_report=pair_report,
        capital_report=capital_report,
        cost_report=cost_report,
        threshold_report=threshold_report,
    )
    profitability_allowed = _profitability_claim_allowed(
        counts=counts,
        summary=summary,
        profitability_verdict=profitability_verdict,
        cost_report=cost_report,
    )
    recommendation = _recommendation(
        profitability_allowed=profitability_allowed,
        cost_report=cost_report,
        summary=summary,
        counts=counts,
    )

    decision_report = {
        "schema_version": "v53.backtest_decision_report.v1",
        "run_id": str(summary.get("run_id") or run_manifest.get("run_id") or ""),
        "mode": str(summary.get("ml_mode_status") or run_manifest.get("ml_mode_status") or "ML_MODE_OFF"),
        "artifact_hash": summary.get("expected_edge_model_artifact_hash") or "",
        "train_window": {
            "status": str(summary.get("expected_edge_walkforward_status") or ""),
            "training_artifact_ref": str(summary.get("expected_edge_training_artifact_ref") or ""),
        },
        "validation_window": {"status": "UNAVAILABLE"},
        "backtest_window": {
            "start": str(run_manifest.get("start") or ""),
            "end": str(run_manifest.get("end") or ""),
        },
        "anti_leakage_status": str(summary.get("expected_edge_anti_leakage_status") or ""),
        "summary": {
            **counts,
            "profitability_claim_allowed": profitability_allowed,
        },
        "timeframe_ranking": timeframe_report.get("rows", []),
        "feature_ranking": feature_report.get("rows", []),
        "engine_by_regime": engine_regime_report.get("rows", []),
        "pair_ranking": pair_report.get("rows", []),
        "capital_bucket_ranking": capital_report.get("rows", []),
        "ml_vs_no_ml_delta": ml_delta_report,
        "cost_fill_realism": cost_report,
        "threshold_near_miss": threshold_report,
        "report_status": capability_audit["overall_status"],
        "profitability_backtest_ready": profitability_allowed,
        "recommendation": recommendation,
    }
    final_verdict = {
        "schema_version": "v53.backtest_decision_report_final_verdict.v1",
        "run_id": decision_report["run_id"],
        "verdict": capability_audit["overall_status"],
        "profitability_backtest_ready": profitability_allowed,
        "profitability_claim_allowed": profitability_allowed,
        "next_required_patch": recommendation["next_required_patch"],
        "research_only": recommendation["research_only"],
        "live_ready": recommendation["live_ready"],
        "shadow_ready": recommendation["shadow_ready"],
    }

    payloads = {
        TIMEFRAME_RANKING_FILENAME: timeframe_report,
        FEATURE_RANKING_FILENAME: feature_report,
        ML_VS_NO_ML_DELTA_FILENAME: ml_delta_report,
        ENGINE_BY_REGIME_FILENAME: engine_regime_report,
        PAIR_RANKING_FILENAME: pair_report,
        CAPITAL_BUCKET_RANKING_FILENAME: capital_report,
        COST_FILL_REALISM_FILENAME: cost_report,
        THRESHOLD_NEAR_MISS_FILENAME: threshold_report,
        CAPABILITY_AUDIT_FILENAME: capability_audit,
        DECISION_REPORT_FILENAME: decision_report,
        FINAL_VERDICT_FILENAME: final_verdict,
    }
    refs: dict[str, str] = {}
    for filename, payload in payloads.items():
        refs[filename] = str((reports / filename).resolve())
        _write_payload(reports / filename, payload)
    return refs


__all__ = [
    "CAPABILITY_AUDIT_FILENAME",
    "DECISION_REPORT_FILENAME",
    "FINAL_VERDICT_FILENAME",
    "write_backtest_decision_reports",
]
