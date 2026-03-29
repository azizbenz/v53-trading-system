"""Tests for the minimal Build-14 enabler scaffold."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import complete_enablers
from complete_enablers import (
    Build14EnablerContract,
    Build14InfluenceAction,
    Build14InfluenceSignal,
    Build14Severity,
    Build14InfluenceMode,
    Build14ObservationInput,
    Build14SignalFamily,
    build_execution_fragility_score,
    build_market_toxicity_snapshot,
    evaluate_build14_limited_influence,
)


def test_complete_enablers_exports_expected_symbols():
    assert {
        "Build14EnablerContract",
        "Build14ObservationInput",
        "Build14InfluenceMode",
        "Build14InfluenceAction",
        "Build14InfluenceSignal",
        "Build14Severity",
        "Build14SignalFamily",
        "build_market_toxicity_snapshot",
        "build_execution_fragility_score",
        "evaluate_build14_limited_influence",
    }.issubset(set(complete_enablers.__all__))


def test_build14_contract_defaults_to_read_only():
    contract = Build14EnablerContract(
        correlation_id="corr-1",
        signal_family=Build14SignalFamily.AI_EDGE,
        summary="Observe AI edge enrichments without affecting decisions",
    )

    assert contract.influence_mode == Build14InfluenceMode.READ_ONLY
    assert contract.max_influence_weight == 0.0


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


def test_market_toxicity_snapshot_is_traceable_and_read_only():
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
    assert snapshot.influence_mode == Build14InfluenceMode.READ_ONLY
    assert snapshot.max_influence_weight == 0.0
    assert snapshot.observed_value > 0.0
    assert snapshot.structured_log_key == "build14.read_only.market_toxicity"


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
