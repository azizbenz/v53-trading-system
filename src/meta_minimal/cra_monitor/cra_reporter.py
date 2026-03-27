"""
Build-9 / cra_monitor / cra_reporter
Expose CRA results to monitoring and UI.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from meta_minimal.cra_monitor.sterilization_classifier import (
    SterilizationClass,
    SterilizationResult,
)
from meta_minimal.cra_monitor.cra_alert_builder import CRAAlert


class CRAReport(BaseModel, frozen=True):
    """CRA monitoring report."""

    total_trades: int = 0
    healthy_count: int = 0
    reduced_viable_count: int = 0
    phantom_probable_count: int = 0
    phantom_confirmed_count: int = 0
    sterilization_rate: float = 0.0
    sterilization_rate_by_engine: dict[str, float] = Field(default_factory=dict)
    sterilization_rate_by_pair: dict[str, float] = Field(default_factory=dict)
    alerts: tuple[CRAAlert, ...] = ()


def build_cra_report(
    results: tuple[SterilizationResult, ...],
    alerts: tuple[CRAAlert, ...] = (),
) -> CRAReport:
    """Build a CRA report from classification results."""
    _STERILIZED = {SterilizationClass.PHANTOM_PROBABLE, SterilizationClass.PHANTOM_CONFIRMED}

    counts = {cls: 0 for cls in SterilizationClass}
    by_engine: dict[str, tuple[int, int]] = {}  # engine -> (total, sterilized)
    by_pair: dict[str, tuple[int, int]] = {}

    for r in results:
        counts[r.classification] += 1
        is_steril = 1 if r.classification in _STERILIZED else 0

        et, es = by_engine.get(r.engine_id, (0, 0))
        by_engine[r.engine_id] = (et + 1, es + is_steril)

        pt, ps = by_pair.get(r.pair, (0, 0))
        by_pair[r.pair] = (pt + 1, ps + is_steril)

    total = len(results)
    steril_total = counts[SterilizationClass.PHANTOM_PROBABLE] + counts[SterilizationClass.PHANTOM_CONFIRMED]
    rate = steril_total / total if total > 0 else 0.0

    rate_by_engine = {k: s / t if t > 0 else 0.0 for k, (t, s) in by_engine.items()}
    rate_by_pair = {k: s / t if t > 0 else 0.0 for k, (t, s) in by_pair.items()}

    return CRAReport(
        total_trades=total,
        healthy_count=counts[SterilizationClass.HEALTHY],
        reduced_viable_count=counts[SterilizationClass.REDUCED_VIABLE],
        phantom_probable_count=counts[SterilizationClass.PHANTOM_PROBABLE],
        phantom_confirmed_count=counts[SterilizationClass.PHANTOM_CONFIRMED],
        sterilization_rate=rate,
        sterilization_rate_by_engine=rate_by_engine,
        sterilization_rate_by_pair=rate_by_pair,
        alerts=alerts,
    )
