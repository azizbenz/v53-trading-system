"""Shadow-only logging for Build-3 hybrid routing."""

from __future__ import annotations

from dataclasses import dataclass

from execution_backbone.execution_routing_features import ExecutionRoutingFeatureSnapshot

from .hybrid_router_metrics import HybridRouterMetricsSink
from .hybrid_router_types import HybridRoutingDecision


@dataclass(frozen=True)
class ShadowRoutingRecord:
    snapshot: ExecutionRoutingFeatureSnapshot
    predicted_decision: HybridRoutingDecision
    runtime_actual_decision: str


class ShadowRoutingLogger:
    """In-memory shadow logger for predicted-vs-legacy routing comparisons."""

    def __init__(self, metrics_sink: HybridRouterMetricsSink | None = None) -> None:
        self._metrics_sink = metrics_sink
        self._records: list[ShadowRoutingRecord] = []

    def record(
        self,
        *,
        snapshot: ExecutionRoutingFeatureSnapshot,
        predicted_decision: HybridRoutingDecision,
        runtime_actual_decision: str,
    ) -> None:
        self._records.append(
            ShadowRoutingRecord(
                snapshot=snapshot,
                predicted_decision=predicted_decision,
                runtime_actual_decision=runtime_actual_decision,
            )
        )
        if self._metrics_sink is not None:
            self._metrics_sink.record_shadow_observation()

    def records(self) -> tuple[ShadowRoutingRecord, ...]:
        return tuple(self._records)


__all__ = [
    "ShadowRoutingLogger",
    "ShadowRoutingRecord",
]
