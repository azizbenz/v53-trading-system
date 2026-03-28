"""Tests for the minimal Build-14 enabler scaffold."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import complete_enablers
from complete_enablers import (
    Build14EnablerContract,
    Build14InfluenceMode,
    Build14SignalFamily,
)


def test_complete_enablers_exports_expected_symbols():
    assert {
        "Build14EnablerContract",
        "Build14InfluenceMode",
        "Build14SignalFamily",
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
