"""Tests for the minimal Build-14 enabler scaffold."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import complete_enablers
from complete_enablers import (
    Build14EnablerContract,
    Build14InfluenceMode,
    Build14ObservationInput,
    Build14SignalFamily,
    build_execution_fragility_score,
    build_market_toxicity_snapshot,
)


def test_complete_enablers_exports_expected_symbols():
    assert {
        "Build14EnablerContract",
        "Build14ObservationInput",
        "Build14InfluenceMode",
        "Build14SignalFamily",
        "build_market_toxicity_snapshot",
        "build_execution_fragility_score",
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
    assert snapshot.status in {"elevated", "critical"}
    assert snapshot.can_trade_autonomously is False
    assert "edge_degraded" in snapshot.detail
