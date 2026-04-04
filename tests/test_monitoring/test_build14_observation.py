"""Tests for governed Build-14 observation derivation helpers."""

from __future__ import annotations

from interface_contracts import PairHealthLevel, ProfileId, RuntimeMode
from meta import (
    build_break_even_report,
    build_cra_report,
    build_dtr_summary,
    build_edge_report,
)
from meta_minimal.break_even_dashboard.motor_pair_break_even_view import BreakEvenView
from meta_minimal.cra_monitor.cra_alert_builder import CRAAlert, CRAAlertLevel
from meta_minimal.cra_monitor.sterilization_classifier import (
    SterilizationClass,
    SterilizationResult,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import (
    EdgeClassification,
    EdgeStatus,
)
from monitoring import (
    build_technical_dashboard_payload,
    collect_engine_metrics,
    collect_infra_metrics,
    collect_meta_metrics,
    collect_monitoring_snapshot,
    collect_pair_metrics,
    collect_portfolio_metrics,
    derive_build14_observation_from_payload,
    derive_build14_observation_from_snapshot,
)


def _snapshot(
    *,
    correlation_id: str,
    queue_backlog: int,
    stale_pairs: tuple[str, ...],
    dtr_loss_count: int,
    log_loss_count: int,
    ce_net: float,
    cra_sterilization_rate: float,
) :
    dtr_summary = build_dtr_summary(
        (
            build_dtr(
                dtr_id="dtr-build14-observation-1",
                pair="BTCUSDT",
                engine_id="engine_a",
                decision_state=DecisionState.SELECTED,
                timestamp=1_700_000_000.0,
            ),
        ),
        total_opportunities=2,
    )
    cra_report = build_cra_report(
        (
            SterilizationResult(
                pair="BTCUSDT",
                engine_id="engine_a",
                classification=SterilizationClass.PHANTOM_PROBABLE,
                multiplier=0.5,
                phantom_risk_score=0.8,
            ),
        ),
        alerts=(
            CRAAlert(
                scope="engine_a",
                sterilization_rate=cra_sterilization_rate,
                total_trades=1,
                sterilized_count=1,
                alert_level=CRAAlertLevel.WARNING,
                dominant_cause="spread_drift",
            ),
        ),
    )
    break_even_report = build_break_even_report(
        (
            BreakEvenView(
                scope="engine_b",
                sample_size=10,
                mean_realized_cost=0.0015,
                mean_expected_cost=0.0010,
                mean_cost_drift=0.0005,
                profitable_rate=0.4,
            ),
        )
    )
    edge_report = build_edge_report(
        (
            EdgeClassification(
                scope="engine_a",
                status=EdgeStatus.CREDIBLE,
                mean_net_return=0.002,
                standard_error=0.0003,
                sample_size=20,
                sharpe_per_trade=0.3,
                mean_cost_p90=0.001,
                ce_observed=0.0005,
                cluster_utilization=0.2,
            ),
            EdgeClassification(
                scope="engine_b",
                status=EdgeStatus.DEGRADED,
                mean_net_return=-0.001,
                standard_error=0.0004,
                sample_size=20,
                sharpe_per_trade=-0.1,
                mean_cost_p90=0.002,
                ce_observed=0.0,
                cluster_utilization=0.4,
            ),
        )
    )
    return collect_monitoring_snapshot(
        correlation_id=correlation_id,
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=2,
            gross_capacity_used_pct=35.0,
            loss_capacity_used_pct=8.0,
            beta_utilization=0.3,
            capital_deployed_usdt=1_200.0,
            ce_net=ce_net,
        ),
        infra=collect_infra_metrics(
            queue_backlog=queue_backlog,
            stale_pairs=stale_pairs,
            dtr_loss_count=dtr_loss_count,
            log_loss_count=log_loss_count,
        ),
        meta=collect_meta_metrics(
            dtr_summary,
            cra_report,
            break_even_report,
            edge_report,
            future_learning_diagnostics=1,
            future_learning_hypotheses=1,
        ),
        engines=(
            collect_engine_metrics(
                engine_id="engine_a",
                emitted_signals=2,
                net_edge_bps=12.0,
                expected_cost_bps=4.0,
                ce_expected=0.0007,
            ),
            collect_engine_metrics(
                engine_id="engine_b",
                emitted_signals=1,
                net_edge_bps=4.0,
                expected_cost_bps=3.0,
                ce_expected=0.0002,
                stale=True,
            ),
        ),
        pairs=(
            collect_pair_metrics(
                pair="BTCUSDT",
                health=PairHealthLevel.HEALTHY,
                freshness_ms=900,
                backlog_depth=queue_backlog,
            ),
            collect_pair_metrics(
                pair="ETHUSDT",
                health=(
                    PairHealthLevel.STALE if stale_pairs else PairHealthLevel.HEALTHY
                ),
                freshness_ms=9_000 if stale_pairs else 1_100,
                backlog_depth=queue_backlog,
            ),
        ),
    )


def test_build14_observation_derivation_reacts_to_monitoring_stress():
    healthy = derive_build14_observation_from_snapshot(
        _snapshot(
            correlation_id="corr-build14-healthy",
            queue_backlog=4,
            stale_pairs=(),
            dtr_loss_count=0,
            log_loss_count=0,
            ce_net=0.0012,
            cra_sterilization_rate=0.05,
        )
    )
    stressed = derive_build14_observation_from_snapshot(
        _snapshot(
            correlation_id="corr-build14-stressed",
            queue_backlog=88,
            stale_pairs=("ETHUSDT",),
            dtr_loss_count=1,
            log_loss_count=1,
            ce_net=-0.0002,
            cra_sterilization_rate=0.42,
        )
    )

    assert stressed.breakout_failure_rate > healthy.breakout_failure_rate
    assert stressed.ghost_liquidity_ratio > healthy.ghost_liquidity_ratio
    assert stressed.competition_density > healthy.competition_density
    assert stressed.volume_support_ratio < healthy.volume_support_ratio
    assert stressed.vwa_absorption_ratio < healthy.vwa_absorption_ratio


def test_build14_observation_derivation_matches_between_snapshot_and_payload():
    snapshot = _snapshot(
        correlation_id="corr-build14-payload",
        queue_backlog=72,
        stale_pairs=("ETHUSDT",),
        dtr_loss_count=1,
        log_loss_count=0,
        ce_net=0.0011,
        cra_sterilization_rate=0.5,
    )
    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("monitoring", "ui", "complete_enablers"),
        active_engines=("engine_a", "engine_b"),
    )

    from_snapshot = derive_build14_observation_from_snapshot(snapshot)
    from_payload = derive_build14_observation_from_payload(payload)

    assert from_payload == from_snapshot
