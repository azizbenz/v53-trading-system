"""Tests for the minimal Build-14 enabler scaffold."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import complete_enablers
from complete_enablers import (
    Build14EnablerContract,
    Build14InfluenceAction,
    Build14HardState,
    Build14InfluenceReport,
    Build14InfluenceSignal,
    Build14Severity,
    Build14InfluenceMode,
    Build14ObservationInput,
    Build14SignalFamily,
    build_competition_monitor_snapshot,
    build_execution_fragility_score,
    build_false_breakout_snapshot,
    build_hurst_regime_snapshot,
    build_lob_deep_filter_vwa_snapshot,
    build_market_toxicity_snapshot,
    build_order_book_imbalance_snapshot,
    evaluate_build14_limited_influence,
    evaluate_build14_shadow_activation,
)


def test_complete_enablers_exports_expected_symbols():
    assert {
        "Build14EnablerContract",
        "Build14ObservationInput",
        "Build14InfluenceMode",
        "Build14InfluenceAction",
        "Build14HardState",
        "Build14InfluenceSignal",
        "Build14Severity",
        "Build14SignalFamily",
        "build_competition_monitor_snapshot",
        "build_market_toxicity_snapshot",
        "build_execution_fragility_score",
        "build_false_breakout_snapshot",
        "build_hurst_regime_snapshot",
        "build_lob_deep_filter_vwa_snapshot",
        "build_order_book_imbalance_snapshot",
        "evaluate_build14_shadow_activation",
        "evaluate_build14_limited_influence",
    }.issubset(set(complete_enablers.__all__))


def test_build14_contract_defaults_to_shadow_enabled():
    contract = Build14EnablerContract(
        correlation_id="corr-1",
        signal_family=Build14SignalFamily.AI_EDGE,
        summary="Build-14 AI edge enrichment is active in Shadow and still governed",
    )

    assert contract.hard_state == Build14HardState.SHADOW_ENABLED
    assert contract.live_promotion_eligible is False
    assert contract.influence_mode == Build14InfluenceMode.SHADOW_ENABLED
    assert contract.max_influence_weight == 1.0


def test_build14_limited_influence_requires_positive_weight():
    with pytest.raises(ValidationError):
        Build14EnablerContract(
            correlation_id="corr-2",
            signal_family=Build14SignalFamily.MICROSTRUCTURE,
            summary="Enable a bounded read-only projection",
            influence_mode=Build14InfluenceMode.LIMITED_INFLUENCE,
            max_influence_weight=0.0,
        )


def test_build14_cannot_bypass_risk_or_trade_autonomously():
    with pytest.raises(ValidationError):
        Build14EnablerContract(
            correlation_id="corr-3",
            signal_family=Build14SignalFamily.REGIME,
            summary="Attempt a forbidden bypass",
            can_bypass_risk=True,
        )


def test_market_toxicity_snapshot_is_traceable_and_shadow_enabled():
    snapshot = build_market_toxicity_snapshot(
        Build14ObservationInput(
            correlation_id="corr-14",
            dtr_coverage=0.75,
            cra_sterilization_rate=0.35,
            cra_alert_count=2,
            break_even_drift_alert=True,
            edge_degraded_count=1,
            queue_backlog=95,
            stale_pair_count=1,
            dtr_loss_count=1,
            log_loss_count=0,
            ce_net=0.0003,
        )
    )

    assert snapshot.signal_family == Build14SignalFamily.MICROSTRUCTURE
    assert snapshot.hard_state == Build14HardState.SHADOW_ENABLED
    assert snapshot.influence_mode == Build14InfluenceMode.SHADOW_ENABLED
    assert snapshot.max_influence_weight == 1.0
    assert snapshot.observed_value > 0.0
    assert snapshot.structured_log_key == "build14.shadow_enabled.market_toxicity"


def test_execution_fragility_score_uses_existing_build9_and_build10_facts_only():
    snapshot = build_execution_fragility_score(
        Build14ObservationInput(
            correlation_id="corr-14b",
            dtr_coverage=0.95,
            cra_sterilization_rate=0.05,
            cra_alert_count=0,
            break_even_drift_alert=True,
            edge_degraded_count=2,
            queue_backlog=20,
            stale_pair_count=0,
            dtr_loss_count=1,
            log_loss_count=1,
            ce_net=-0.0002,
        )
    )

    assert snapshot.signal_family == Build14SignalFamily.AI_EDGE
    assert snapshot.status in {Build14Severity.ELEVATED, Build14Severity.CRITICAL}
    assert snapshot.can_trade_autonomously is False
    assert "edge_degraded" in snapshot.detail


def test_false_breakout_snapshot_is_traceable_and_shadow_enabled():
    snapshot = build_false_breakout_snapshot(
        Build14ObservationInput(
            correlation_id="corr-14fb",
            dtr_coverage=0.88,
            cra_sterilization_rate=0.25,
            cra_alert_count=1,
            break_even_drift_alert=True,
            edge_degraded_count=1,
            queue_backlog=15,
            stale_pair_count=0,
            dtr_loss_count=0,
            log_loss_count=0,
            ce_net=0.0001,
            breakout_failure_rate=0.80,
            volume_support_ratio=0.20,
        )
    )

    assert snapshot.signal_family == Build14SignalFamily.MICROSTRUCTURE
    assert snapshot.hard_state == Build14HardState.SHADOW_ENABLED
    assert snapshot.status in {Build14Severity.ELEVATED, Build14Severity.CRITICAL}
    assert snapshot.structured_log_key == "build14.shadow_enabled.false_breakout_model"
    assert "breakout_failure_rate=0.80" in snapshot.detail


def test_lob_deep_filter_vwa_snapshot_is_traceable_and_shadow_enabled():
    snapshot = build_lob_deep_filter_vwa_snapshot(
        Build14ObservationInput(
            correlation_id="corr-14lob",
            dtr_coverage=0.92,
            cra_sterilization_rate=0.12,
            cra_alert_count=0,
            break_even_drift_alert=False,
            edge_degraded_count=0,
            queue_backlog=18,
            stale_pair_count=1,
            dtr_loss_count=0,
            log_loss_count=0,
            ce_net=0.0003,
            vwa_absorption_ratio=0.25,
            ghost_liquidity_ratio=0.80,
        )
    )

    assert snapshot.signal_family == Build14SignalFamily.MICROSTRUCTURE
    assert snapshot.hard_state == Build14HardState.SHADOW_ENABLED
    assert snapshot.status in {Build14Severity.ELEVATED, Build14Severity.CRITICAL}
    assert snapshot.structured_log_key == "build14.shadow_enabled.lob_deep_filter_vwa"
    assert "vwa_absorption_ratio=0.25" in snapshot.detail


def test_order_book_imbalance_snapshot_is_traceable_and_shadow_enabled():
    snapshot = build_order_book_imbalance_snapshot(
        Build14ObservationInput(
            correlation_id="corr-14obi",
            dtr_coverage=0.91,
            cra_sterilization_rate=0.18,
            cra_alert_count=1,
            break_even_drift_alert=False,
            edge_degraded_count=1,
            queue_backlog=10,
            stale_pair_count=1,
            dtr_loss_count=0,
            log_loss_count=0,
            ce_net=-0.0001,
            adverse_obi_pressure=0.85,
        )
    )

    assert snapshot.signal_family == Build14SignalFamily.MICROSTRUCTURE
    assert snapshot.hard_state == Build14HardState.SHADOW_ENABLED
    assert snapshot.status in {Build14Severity.ELEVATED, Build14Severity.CRITICAL}
    assert snapshot.structured_log_key == "build14.shadow_enabled.order_book_imbalance"
    assert "adverse_obi_pressure=0.85" in snapshot.detail


def test_hurst_regime_snapshot_is_traceable_and_shadow_enabled():
    snapshot = build_hurst_regime_snapshot(
        Build14ObservationInput(
            correlation_id="corr-14hurst",
            dtr_coverage=0.91,
            cra_sterilization_rate=0.10,
            cra_alert_count=0,
            break_even_drift_alert=True,
            edge_degraded_count=1,
            queue_backlog=8,
            stale_pair_count=0,
            dtr_loss_count=0,
            log_loss_count=0,
            ce_net=0.0002,
            hurst_exponent=0.88,
        )
    )

    assert snapshot.signal_family == Build14SignalFamily.REGIME
    assert snapshot.hard_state == Build14HardState.SHADOW_ENABLED
    assert snapshot.status in {Build14Severity.ELEVATED, Build14Severity.CRITICAL}
    assert snapshot.structured_log_key == "build14.shadow_enabled.hurst_regime_classifier"
    assert "hurst_exponent=0.88" in snapshot.detail


def test_competition_monitor_snapshot_is_traceable_and_shadow_enabled():
    snapshot = build_competition_monitor_snapshot(
        Build14ObservationInput(
            correlation_id="corr-14comp",
            dtr_coverage=0.93,
            cra_sterilization_rate=0.08,
            cra_alert_count=0,
            break_even_drift_alert=False,
            edge_degraded_count=0,
            queue_backlog=5,
            stale_pair_count=1,
            dtr_loss_count=0,
            log_loss_count=0,
            ce_net=-0.0001,
            competition_density=0.90,
        )
    )

    assert snapshot.signal_family == Build14SignalFamily.RISK
    assert snapshot.hard_state == Build14HardState.SHADOW_ENABLED
    assert snapshot.status in {Build14Severity.ELEVATED, Build14Severity.CRITICAL}
    assert snapshot.structured_log_key == "build14.shadow_enabled.competition_monitor"
    assert "competition_density=0.90" in snapshot.detail


def test_build14_limited_influence_stays_read_only_when_signals_are_nominal():
    report = evaluate_build14_limited_influence(
        Build14ObservationInput(
            correlation_id="corr-14c",
            dtr_coverage=0.97,
            cra_sterilization_rate=0.05,
            cra_alert_count=0,
            break_even_drift_alert=False,
            edge_degraded_count=0,
            queue_backlog=5,
            stale_pair_count=0,
            dtr_loss_count=0,
            log_loss_count=0,
            ce_net=0.002,
        )
    )

    assert report.signal.influence_mode == Build14InfluenceMode.READ_ONLY
    assert report.signal.action == Build14InfluenceAction.OBSERVE
    assert report.signal.recommended_budget_factor == 1.0
    assert report.signal.requires_manual_review is False


def test_build14_shadow_activation_is_fully_active_in_shadow_but_not_live_promoted():
    report = evaluate_build14_shadow_activation(
        Build14ObservationInput(
            correlation_id="corr-14shadow",
            dtr_coverage=0.75,
            cra_sterilization_rate=0.45,
            cra_alert_count=2,
            break_even_drift_alert=True,
            edge_degraded_count=1,
            queue_backlog=55,
            stale_pair_count=0,
            dtr_loss_count=0,
            log_loss_count=0,
            ce_net=0.0012,
        )
    )

    assert report.hard_state == Build14HardState.SHADOW_ENABLED
    assert report.live_promotion_eligible is False
    assert report.signal.influence_mode == Build14InfluenceMode.SHADOW_ENABLED
    assert report.signal.action == Build14InfluenceAction.SHADOW_APPLY
    assert report.signal.candidate_effect == "shadow_enabled"
    assert report.signal.requires_manual_review is False
    reader_names = {snapshot.reader_name for snapshot in report.snapshots}
    assert {
        "competition_monitor",
        "false_breakout_model",
        "hurst_regime_classifier",
        "lob_deep_filter_vwa",
        "order_book_imbalance",
    } <= reader_names


def test_build14_limited_influence_can_downgrade_confidence_without_becoming_autonomous():
    report = evaluate_build14_limited_influence(
        Build14ObservationInput(
            correlation_id="corr-14d",
            dtr_coverage=0.75,
            cra_sterilization_rate=0.45,
            cra_alert_count=2,
            break_even_drift_alert=True,
            edge_degraded_count=1,
            queue_backlog=55,
            stale_pair_count=0,
            dtr_loss_count=0,
            log_loss_count=0,
            ce_net=0.0012,
        )
    )

    assert report.signal.influence_mode == Build14InfluenceMode.LIMITED_INFLUENCE
    assert report.signal.action == Build14InfluenceAction.DOWNGRADE_CONFIDENCE
    assert 0.0 < report.signal.confidence_penalty_weight <= 0.25
    assert 0.0 < report.signal.recommended_budget_factor < 1.0
    assert report.signal.can_trade_autonomously is False


def test_build14_limited_influence_uses_false_breakout_reader_when_breakout_support_collapses():
    report = evaluate_build14_limited_influence(
        Build14ObservationInput(
            correlation_id="corr-14fb-live",
            dtr_coverage=0.86,
            cra_sterilization_rate=0.18,
            cra_alert_count=1,
            break_even_drift_alert=True,
            edge_degraded_count=1,
            queue_backlog=12,
            stale_pair_count=0,
            dtr_loss_count=0,
            log_loss_count=0,
            ce_net=0.0002,
            breakout_failure_rate=0.90,
            volume_support_ratio=0.10,
        )
    )

    assert any(snapshot.reader_name == "false_breakout_model" for snapshot in report.snapshots)
    assert any(reason_code.startswith("false_breakout_model_") for reason_code in report.signal.reason_codes)
    assert report.signal.influence_mode == Build14InfluenceMode.LIMITED_INFLUENCE


def test_build14_limited_influence_uses_lob_and_obi_reason_codes_when_microstructure_deteriorates():
    report = evaluate_build14_limited_influence(
        Build14ObservationInput(
            correlation_id="corr-14lob-obi",
            dtr_coverage=0.90,
            cra_sterilization_rate=0.15,
            cra_alert_count=1,
            break_even_drift_alert=False,
            edge_degraded_count=0,
            queue_backlog=22,
            stale_pair_count=1,
            dtr_loss_count=0,
            log_loss_count=0,
            ce_net=0.0002,
            vwa_absorption_ratio=0.20,
            ghost_liquidity_ratio=0.90,
            adverse_obi_pressure=0.80,
        )
    )

    assert any(snapshot.reader_name == "lob_deep_filter_vwa" for snapshot in report.snapshots)
    assert any(snapshot.reader_name == "order_book_imbalance" for snapshot in report.snapshots)
    assert any(reason_code.startswith("lob_deep_filter_vwa_") for reason_code in report.signal.reason_codes)
    assert any(reason_code.startswith("order_book_imbalance_") for reason_code in report.signal.reason_codes)
    assert report.signal.influence_mode == Build14InfluenceMode.LIMITED_INFLUENCE


def test_build14_limited_influence_uses_hurst_and_competition_reason_codes_when_regime_and_crowding_deteriorate():
    report = evaluate_build14_limited_influence(
        Build14ObservationInput(
            correlation_id="corr-14hurst-comp",
            dtr_coverage=0.92,
            cra_sterilization_rate=0.10,
            cra_alert_count=0,
            break_even_drift_alert=True,
            edge_degraded_count=1,
            queue_backlog=6,
            stale_pair_count=1,
            dtr_loss_count=0,
            log_loss_count=0,
            ce_net=-0.0002,
            hurst_exponent=0.92,
            competition_density=0.88,
        )
    )

    assert any(snapshot.reader_name == "hurst_regime_classifier" for snapshot in report.snapshots)
    assert any(snapshot.reader_name == "competition_monitor" for snapshot in report.snapshots)
    assert any(reason_code.startswith("hurst_regime_classifier_") for reason_code in report.signal.reason_codes)
    assert any(reason_code.startswith("competition_monitor_") for reason_code in report.signal.reason_codes)
    assert report.signal.influence_mode == Build14InfluenceMode.LIMITED_INFLUENCE


def test_build14_limited_influence_can_escalate_to_review_only_for_critical_reader():
    report = evaluate_build14_limited_influence(
        Build14ObservationInput(
            correlation_id="corr-14e",
            dtr_coverage=0.72,
            cra_sterilization_rate=0.20,
            cra_alert_count=1,
            break_even_drift_alert=True,
            edge_degraded_count=2,
            queue_backlog=10,
            stale_pair_count=0,
            dtr_loss_count=1,
            log_loss_count=0,
            ce_net=-0.0004,
        )
    )

    assert report.signal.influence_mode == Build14InfluenceMode.LIMITED_INFLUENCE
    assert report.signal.action == Build14InfluenceAction.REVIEW_ONLY
    assert report.signal.requires_manual_review is True
    assert report.signal.recommended_budget_factor == 0.0


def test_build14_influence_signal_rejects_any_attempt_to_bypass_guardrails():
    with pytest.raises(ValidationError):
        Build14InfluenceSignal(
            correlation_id="corr-14f",
            influence_mode=Build14InfluenceMode.LIMITED_INFLUENCE,
            action=Build14InfluenceAction.DOWNGRADE_CONFIDENCE,
            severity=Build14Severity.ELEVATED,
            families=(Build14SignalFamily.MICROSTRUCTURE,),
            summary="Forbidden override attempt",
            reason_codes=("toxicity_elevated",),
            confidence_penalty_weight=0.10,
            recommended_budget_factor=0.85,
            can_bypass_risk=True,
        )


def test_build14_report_requires_matching_signal_correlation_id():
    with pytest.raises(ValidationError):
        Build14InfluenceReport(
            correlation_id="corr-14g",
            signal=Build14InfluenceSignal(
                correlation_id="corr-14h",
                influence_mode=Build14InfluenceMode.LIMITED_INFLUENCE,
                action=Build14InfluenceAction.DOWNGRADE_CONFIDENCE,
                severity=Build14Severity.ELEVATED,
                families=(Build14SignalFamily.MICROSTRUCTURE,),
                summary="Correlation mismatch must be rejected",
                reason_codes=("market_toxicity_snapshot_elevated",),
                confidence_penalty_weight=0.10,
                recommended_budget_factor=0.85,
                requires_manual_review=False,
                candidate_effect="confidence_downgrade",
            ),
        )
