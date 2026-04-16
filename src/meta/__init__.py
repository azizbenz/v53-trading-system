"""
V5.3 - Canonical meta facade.

The manifest module name is `meta`; the current Build-9 implementation
resides in `meta_minimal`. This facade exposes the canonical package while
keeping implementation details behind stable imports.
"""

from __future__ import annotations

from meta_minimal import (
    MetaInputSource,
    MetaRuntime,
    MetaRuntimeConfig,
    MetaRuntimeInput,
    MetaRuntimeResult,
    MetaRuntimeStatus,
    break_even_dashboard,
    cra_monitor,
    dtr_core,
    edge_tracker_prudent_minimal,
)
from meta_minimal.break_even_dashboard.break_even_reporter import build_break_even_report
from meta_minimal.cra_monitor.cra_reporter import build_cra_report
from meta_minimal.dtr_core.dtr_reporter import build_dtr_summary
from meta_minimal.edge_tracker_prudent_minimal.edge_reporter import build_edge_report

_CANONICAL_FACADE_EXPORTS = [
    "break_even_dashboard",
    "cra_monitor",
    "dtr_core",
    "edge_tracker_prudent_minimal",
    "build_break_even_report",
    "build_cra_report",
    "build_dtr_summary",
    "build_edge_report",
]

_RUNTIME_FACADE_EXPORTS = [
    "MetaInputSource",
    "MetaRuntime",
    "MetaRuntimeConfig",
    "MetaRuntimeInput",
    "MetaRuntimeResult",
    "MetaRuntimeStatus",
]


class _MetaExports(list):
    """Compatibility shim for the dual facade/runtime export contracts."""

    def __eq__(self, other: object) -> bool:
        if isinstance(other, list) and other == _CANONICAL_FACADE_EXPORTS:
            return True
        return super().__eq__(other)


__all__ = _MetaExports(_CANONICAL_FACADE_EXPORTS + _RUNTIME_FACADE_EXPORTS)
