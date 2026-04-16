"""Minimal structured observability export for Build-10 supervision."""

from __future__ import annotations

from monitoring.contracts import ObservabilityExport, TechnicalDashboardPayload
from monitoring.observability_support import build_observability_export_support


def build_observability_export(payload: TechnicalDashboardPayload) -> ObservabilityExport:
    """Emit a grouped, stable metrics surface from the Build-10 technical payload."""

    return build_observability_export_support(payload)


__all__ = [
    "build_observability_export",
]
