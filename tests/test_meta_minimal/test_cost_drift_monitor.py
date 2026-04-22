from __future__ import annotations

import pytest

from meta_minimal.cost_drift_monitor import (
    CostDriftMonitor,
    CostDriftMonitorConfig,
    CostDriftSample,
)


def _samples(*, count: int, expected: float, realised: float) -> list[CostDriftSample]:
    return [
        CostDriftSample(expected_cost=expected, realised_cost=realised)
        for _ in range(count)
    ]


def test_cost_drift_monitor_alerts_when_bias_exceeds_threshold() -> None:
    monitor = CostDriftMonitor(CostDriftMonitorConfig())
    for sample in _samples(count=30, expected=1.0, realised=1.3):
        monitor.record(sample)

    result = monitor.evaluate()

    assert result.alert is True
    assert result.reason == "alert_bias_exceeded"
    assert result.sample_count == 30
    assert result.bias_pct == pytest.approx(0.30)


def test_cost_drift_monitor_passes_when_bias_stays_below_threshold() -> None:
    monitor = CostDriftMonitor(CostDriftMonitorConfig())
    for sample in _samples(count=30, expected=1.0, realised=1.15):
        monitor.record(sample)

    result = monitor.evaluate()

    assert result.alert is False
    assert result.reason == "pass"
    assert result.bias_pct == pytest.approx(0.15)


def test_cost_drift_monitor_reports_insufficient_data_below_min_events() -> None:
    monitor = CostDriftMonitor(CostDriftMonitorConfig(min_events=10))
    for sample in _samples(count=9, expected=1.0, realised=1.3):
        monitor.record(sample)

    result = monitor.evaluate()

    assert result.alert is False
    assert result.reason == "insufficient_data"
    assert result.sample_count == 9
    assert result.bias_pct == 0.0


def test_cost_drift_monitor_rejects_threshold_above_hard_cap() -> None:
    with pytest.raises(ValueError, match="THR-D01 hard cap"):
        CostDriftMonitorConfig(bias_alert_threshold=0.60)


def test_cost_drift_monitor_rejects_non_positive_expected_cost() -> None:
    with pytest.raises(ValueError, match="expected_cost"):
        CostDriftSample(expected_cost=0.0, realised_cost=0.1)


def test_cost_drift_monitor_reset_clears_recorded_samples() -> None:
    monitor = CostDriftMonitor(CostDriftMonitorConfig())
    for sample in _samples(count=10, expected=1.0, realised=1.3):
        monitor.record(sample)

    monitor.reset()
    result = monitor.evaluate()

    assert result.sample_count == 0
    assert result.reason == "insufficient_data"
