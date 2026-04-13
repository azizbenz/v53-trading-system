"""Tests for the bounded Build-4 information-stress monitor."""

import pytest

from risk_backbone import (
    InfoStressLevel,
    InfoStressMonitor,
    InfoStressThresholds,
    build_info_stress_entry_gate,
)
from risk_backbone.risk_runtime import RiskInfoStressPrecheckInput


pytestmark = pytest.mark.build4


def test_info_stress_monitor_detects_extreme_and_keeps_cooldown():
    monitor = InfoStressMonitor(
        thresholds=InfoStressThresholds(cooldown_s=60),
    )

    first = monitor.assess(
        pair="BTCUSDT",
        now=100.0,
        spread_bps=10.0,
        reference_spread_bps=1.0,
        depth_ratio=0.05,
        order_cancellation_rate=0.85,
        taker_imbalance=0.95,
        micro_vol_divergence=4.0,
    )

    assert first.level == InfoStressLevel.EXTREME
    assert first.entries_blocked is True
    assert first.entries_blocked_until_ts == 160
    assert first.alert_count == 5

    second = monitor.assess(
        pair="BTCUSDT",
        now=120.0,
        spread_bps=1.1,
        reference_spread_bps=1.0,
        depth_ratio=0.45,
        order_cancellation_rate=0.20,
        taker_imbalance=0.10,
        micro_vol_divergence=0.8,
    )

    assert second.level == InfoStressLevel.ELEVATED
    assert second.entries_blocked is True
    assert second.entries_blocked_until_ts == 160
    assert "INFO_STRESS_COOLDOWN_ACTIVE" in second.reason_codes


def test_info_stress_monitor_keeps_sideways_pair_normal():
    monitor = InfoStressMonitor()

    assessment = monitor.assess(
        pair="ETHUSDT",
        now=200.0,
        spread_bps=1.2,
        reference_spread_bps=1.0,
        depth_ratio=0.50,
        order_cancellation_rate=0.25,
        taker_imbalance=0.20,
        micro_vol_divergence=0.9,
    )

    assert assessment.level == InfoStressLevel.NORMAL
    assert assessment.entries_blocked is False
    assert assessment.reason_codes == ()


def test_info_stress_entry_gate_blocks_extreme_signal():
    hook = build_info_stress_entry_gate(
        InfoStressMonitor(thresholds=InfoStressThresholds(cooldown_s=30))
    )

    outcome = hook(
        RiskInfoStressPrecheckInput(
            context_id="BTCUSDT:engine_a:100.0",
            pair="BTCUSDT",
            engine_id="engine_a",
            size=1.0,
            planned_loss=0.1,
            now_ts=100.0,
            spread_bps=10.0,
            reference_spread_bps=1.0,
            depth_ratio=0.05,
            order_cancellation_rate=0.85,
            taker_imbalance=0.95,
            micro_vol_divergence=4.0,
        )
    )

    assert outcome.accepted is False
    assert outcome.stress_level == InfoStressLevel.EXTREME.value
    assert outcome.entries_blocked is True
    assert outcome.entries_blocked_until_ts == 130
    assert "INFO_STRESS_SPREAD_EXPLOSION" in outcome.reason_codes
