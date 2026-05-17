"""Phase 2.5 adapter - thin-sample economic sterilization monitor."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from cockpit.state_freshness import OperationalSourceSnapshot, source_stamp
from cockpit.state_replay_metrics import ReplayMetricsSnapshot


class EconomicSterilizationSnapshot(OperationalSourceSnapshot):
    opportunities_seen: int = 0
    selected_count: int = 0
    hard_blocked_count: int = 0
    cost_blocked_count: int | None = None
    cost_blocked_count_status: str = "SOURCE_UNAVAILABLE"
    min_notional_blocked_count: int | None = None
    min_notional_blocked_count_status: str = "SOURCE_UNAVAILABLE"
    slippage_blocked_count: int | None = None
    slippage_blocked_count_status: str = "SOURCE_UNAVAILABLE"
    exec_rate: float = 0.0
    ce_net: float = 0.0
    executed_only_net_return: float | None = None
    executed_only_net_return_status: str = "EXECUTED_NET_RETURN_NOT_PROVEN"
    missing_realized_cost_count: int = 0
    economic_sterilization_ratio: float = 0.0
    sterilization_severity: str = "unknown"
    ce_net_label: str = "Expected CE net"
    exec_rate_label: str = "Exec rate (executed / total records)"
    promotion_economics_status: str = "PROMOTION_ECONOMICS_NOT_READY"
    cost_model_completeness_status: str = "UNKNOWN"
    book_depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    impact_depth_readiness_status: str = "BOOK_DEPTH_NOT_PROVEN"
    shadow_extension_required: bool = True
    shadow_extension_reason: str | None = "NO_PROMOTION_GRADE_REPLAY_IMPACT_PROOF"
    minimum_shadow_days_required: int | None = None
    shadow_extension_status: str = "MICRO_LIVE_BLOCKED_BY_DEPTH"
    fill_realism_status: str = "FILL_REALISM_NOT_PROVEN"
    fill_source_status: str = "FILL_SOURCE_NOT_PROVEN"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
    capital_profile_artifact_status: str = "CAPITAL_BUCKET_NOT_PROVEN"
    capital_profile_count: int = 0
    scoring_cost_completeness_status: str = "UNKNOWN"
    risk_input_completeness_status: str = "UNKNOWN"
    small_capital_viability_status: str = "BLOCKED_BY_BACKTEST"
    min_notional_viability_status: str = "BLOCKED_BY_BACKTEST"
    capital_fragmentation_status: str = "NOT_PROVEN"
    sizing_doctrine_status: str = "FIXED_FRACTION_VOL_TARGET_CAPS"
    kelly_status: str = "NOT_IMPLEMENTED_BY_DESIGN_FOR_NOW"
    portfolio_multi_asset_status: str = "BASELINE_CAPS_ONLY"
    covariance_model_status: str = "NOT_IMPLEMENTED"
    true_drawdown_status: str = "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    drawdown_proxy_promotion_grade: bool = False
    economics_display_state: str = "unknown"
    status: str = "unknown"


def read_economic_sterilization(
    replay: ReplayMetricsSnapshot,
) -> EconomicSterilizationSnapshot:
    """Expose blocked-vs-selected ratios without pretending thin samples are conclusive."""

    source_path = Path(replay.source_path) if replay.source_path else None
    stamp = source_stamp(path=source_path, stale_after_seconds=300.0)
    opportunities = replay.total_opportunities or replay.total_records
    blocked_or_rejected = max(opportunities - replay.selected_count, 0)
    ratio = blocked_or_rejected / max(opportunities, 1)
    display_state = replay.economics_display_state
    if ratio >= 0.80:
        sterilization_severity = "critical"
    elif ratio >= 0.50:
        sterilization_severity = "watch"
    else:
        sterilization_severity = "ok"
    if display_state == "placeholder":
        status = "placeholder"
    elif display_state == "stale":
        status = "stale"
    elif display_state == "partial_replay":
        status = "partial"
    elif opportunities < 30:
        status = "insufficient_sample"
    else:
        status = sterilization_severity
    reason_codes = list(stamp["reason_codes"])
    reason_codes.append("economic_breakdown_partial")
    reason_codes.extend(replay.economics_reason_codes)
    if opportunities < 30:
        reason_codes.append("SAMPLE_TOO_SMALL")
    return EconomicSterilizationSnapshot(
        source_status=stamp["source_status"],
        source_file=str(stamp["source_file"]) if stamp["source_file"] else replay.source_path or None,
        last_modified_at=stamp["last_modified_at"],
        age_seconds=stamp["age_seconds"],
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        opportunities_seen=opportunities,
        selected_count=replay.selected_count,
        hard_blocked_count=replay.hard_blocked_count,
        cost_blocked_count=None,
        cost_blocked_count_status="SOURCE_UNAVAILABLE",
        min_notional_blocked_count=None,
        min_notional_blocked_count_status="SOURCE_UNAVAILABLE",
        slippage_blocked_count=None,
        slippage_blocked_count_status="SOURCE_UNAVAILABLE",
        exec_rate=replay.exec_rate,
        ce_net=replay.ce_net,
        executed_only_net_return=replay.executed_only_net_return,
        executed_only_net_return_status=replay.executed_only_net_return_status,
        missing_realized_cost_count=replay.missing_realized_cost_count,
        economic_sterilization_ratio=ratio,
        sterilization_severity=sterilization_severity,
        ce_net_label=replay.expected_ce_label,
        exec_rate_label=replay.exec_rate_label,
        promotion_economics_status=replay.promotion_economics_status,
        cost_model_completeness_status=replay.cost_model_completeness_status,
        book_depth_source_status=replay.book_depth_source_status,
        impact_depth_readiness_status=replay.impact_depth_readiness_status,
        shadow_extension_required=replay.shadow_extension_required,
        shadow_extension_reason=replay.shadow_extension_reason,
        minimum_shadow_days_required=replay.minimum_shadow_days_required,
        shadow_extension_status=replay.shadow_extension_status,
        fill_realism_status=replay.fill_realism_status,
        fill_source_status=replay.fill_source_status,
        cost_parity_status=replay.cost_parity_status,
        capital_profile_artifact_status=replay.capital_profile_artifact_status,
        capital_profile_count=len(replay.capital_bucket_profiles),
        scoring_cost_completeness_status=replay.cost_model_completeness_status,
        risk_input_completeness_status="UNKNOWN",
        small_capital_viability_status=replay.small_capital_viability_status,
        min_notional_viability_status=replay.min_notional_viability_status,
        capital_fragmentation_status=replay.capital_fragmentation_status,
        sizing_doctrine_status=replay.sizing_doctrine,
        kelly_status=replay.kelly_status,
        portfolio_multi_asset_status=replay.multi_asset_risk_control_status,
        covariance_model_status=replay.covariance_model_status,
        true_drawdown_status=replay.true_net_equity_drawdown_status,
        drawdown_proxy_promotion_grade=replay.drawdown_proxy_promotion_grade,
        economics_display_state=display_state,
        status=status,
    )


__all__ = ["EconomicSterilizationSnapshot", "read_economic_sterilization"]
