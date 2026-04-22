"""Minimal monitor for execution-cost bias drift."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostDriftMonitorConfig:
    bias_alert_threshold: float = 0.20
    min_events: int = 10

    def __post_init__(self) -> None:
        if self.bias_alert_threshold < 0.0:
            raise ValueError("bias_alert_threshold must be >= 0")
        if self.bias_alert_threshold > 0.50:
            raise ValueError("THR-D01 hard cap = 50%")
        if self.min_events <= 0:
            raise ValueError("min_events must be > 0")


@dataclass(frozen=True)
class CostDriftSample:
    expected_cost: float
    realised_cost: float

    def __post_init__(self) -> None:
        if self.expected_cost <= 0.0:
            raise ValueError("expected_cost must be > 0")
        if self.realised_cost < 0.0:
            raise ValueError("realised_cost must be >= 0")


@dataclass(frozen=True)
class CostDriftResult:
    alert: bool
    bias_pct: float
    sample_count: int
    reason: str


class CostDriftMonitor:
    def __init__(self, config: CostDriftMonitorConfig) -> None:
        self._config = config
        self._samples: list[CostDriftSample] = []

    def record(self, sample: CostDriftSample) -> None:
        self._samples.append(sample)

    def evaluate(self) -> CostDriftResult:
        sample_count = len(self._samples)
        if sample_count < self._config.min_events:
            return CostDriftResult(
                alert=False,
                bias_pct=0.0,
                sample_count=sample_count,
                reason="insufficient_data",
            )

        mean_expected = sum(sample.expected_cost for sample in self._samples) / sample_count
        mean_realised = sum(sample.realised_cost for sample in self._samples) / sample_count
        bias_pct = (mean_realised - mean_expected) / mean_expected
        alert = bias_pct > self._config.bias_alert_threshold
        return CostDriftResult(
            alert=alert,
            bias_pct=bias_pct,
            sample_count=sample_count,
            reason="alert_bias_exceeded" if alert else "pass",
        )

    def reset(self) -> None:
        self._samples.clear()
