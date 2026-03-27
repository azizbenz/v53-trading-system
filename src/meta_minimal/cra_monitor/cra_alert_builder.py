"""
Build-9 / cra_monitor / cra_alert_builder
Produce CRA alerts by engine / pair / period.

SterilRate = sum(Steril_i) / sum(A_i)
SterilRate_k = sum(Steril_i in k) / sum(A_i in k)
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from meta_minimal.cra_monitor.sterilization_classifier import (
    SterilizationClass,
    SterilizationResult,
)


class CRAAlertLevel(StrEnum):
    NONE = "none"
    WARNING = "warning"
    CRITICAL = "critical"


class CRAAlert(BaseModel, frozen=True):
    """One CRA alert."""

    scope: str  # e.g. "engine_a", "BTC/USDT", "engine_a:BTC/USDT"
    sterilization_rate: float
    total_trades: int
    sterilized_count: int
    alert_level: CRAAlertLevel
    dominant_cause: str = ""


# Alert thresholds
_WARNING_RATE = 0.20
_CRITICAL_RATE = 0.40


def build_alerts(
    results: tuple[SterilizationResult, ...],
    warning_rate: float = _WARNING_RATE,
    critical_rate: float = _CRITICAL_RATE,
) -> tuple[CRAAlert, ...]:
    """Build CRA alerts aggregated by engine and by pair.

    Sterilized = PHANTOM_PROBABLE or PHANTOM_CONFIRMED.
    """
    _STERILIZED = {SterilizationClass.PHANTOM_PROBABLE, SterilizationClass.PHANTOM_CONFIRMED}

    # Group by engine and by pair
    by_engine: dict[str, list[SterilizationResult]] = {}
    by_pair: dict[str, list[SterilizationResult]] = {}

    for r in results:
        by_engine.setdefault(r.engine_id, []).append(r)
        by_pair.setdefault(r.pair, []).append(r)

    alerts: list[CRAAlert] = []

    for scope, group in [*by_engine.items(), *by_pair.items()]:
        total = len(group)
        sterilized = [r for r in group if r.classification in _STERILIZED]
        rate = len(sterilized) / total if total > 0 else 0.0

        if rate >= critical_rate:
            level = CRAAlertLevel.CRITICAL
        elif rate >= warning_rate:
            level = CRAAlertLevel.WARNING
        else:
            level = CRAAlertLevel.NONE

        # Dominant cause: most common reason among sterilized
        cause_counts: dict[str, int] = {}
        for s in sterilized:
            if s.reason:
                cause_counts[s.reason] = cause_counts.get(s.reason, 0) + 1
        dominant = max(cause_counts, key=cause_counts.get, default="") if cause_counts else ""

        if level != CRAAlertLevel.NONE:
            alerts.append(CRAAlert(
                scope=scope,
                sterilization_rate=rate,
                total_trades=total,
                sterilized_count=len(sterilized),
                alert_level=level,
                dominant_cause=dominant,
            ))

    return tuple(alerts)
