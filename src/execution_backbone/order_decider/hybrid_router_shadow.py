"""Shadow-only logging for Build-3 hybrid routing V2."""

from __future__ import annotations

from dataclasses import dataclass

from execution_backbone.execution_routing_features import ExecutionRoutingFeatureSnapshot

from .hybrid_router_metrics import HybridRouterMetricsSink
from .hybrid_router_types import (
    HybridRoutingDecision,
    RoutingTraceFull,
    build_full_routing_trace,
)


@dataclass(frozen=True)
class ShadowDecisionRecord:
    snapshot: ExecutionRoutingFeatureSnapshot
    predicted_decision: HybridRoutingDecision
    runtime_actual_action: str
    decision_diff: str
    decision_diff_reason_hint: tuple[str, ...]
    realized_fill_ratio: float | None
    realized_time_to_fill_s: float | None
    realized_slippage_bps: float | None
    realized_alpha_decay_bps: float | None


class ShadowRoutingLogger:
    """In-memory shadow logger for predicted-vs-legacy routing comparisons."""

    def __init__(self, metrics_sink: HybridRouterMetricsSink | None = None) -> None:
        self._metrics_sink = metrics_sink
        self._records: dict[str, ShadowDecisionRecord] = {}
        self._record_sequence = 0

    def record(
        self,
        *,
        snapshot: ExecutionRoutingFeatureSnapshot,
        predicted_decision: HybridRoutingDecision,
        runtime_actual_action: str,
        calibration_version: str = "",
    ) -> ShadowDecisionRecord:
        self._record_sequence += 1
        record_id = f"shadow-{self._record_sequence}"
        decision_diff = _decision_diff(
            predicted_action=predicted_decision.action.value,
            runtime_actual_action=runtime_actual_action,
        )
        record = ShadowDecisionRecord(
            snapshot=snapshot,
            predicted_decision=predicted_decision,
            runtime_actual_action=runtime_actual_action,
            decision_diff=decision_diff,
            decision_diff_reason_hint=(
                ()
                if decision_diff == "match"
                else tuple(predicted_decision.reason_codes)
            ),
            realized_fill_ratio=None,
            realized_time_to_fill_s=None,
            realized_slippage_bps=None,
            realized_alpha_decay_bps=None,
        )
        object.__setattr__(record, "_record_id", record_id)
        self._records[record_id] = record
        if self._metrics_sink is not None:
            full_trace = build_full_routing_trace(
                predicted_decision,
                calibration_version=calibration_version,
                shadow_only=True,
            )
            self._metrics_sink.record_shadow_observation(
                full_trace=full_trace,
                decision_diff=decision_diff,
            )
        return record

    def attach_outcome(
        self,
        record_id: str,
        *,
        fill_ratio: float | None,
        time_to_fill_s: float | None,
        slippage_bps: float | None,
        alpha_decay_bps: float | None,
    ) -> None:
        record = self._records.get(record_id)
        if record is None:
            return
        updated_record = ShadowDecisionRecord(
            snapshot=record.snapshot,
            predicted_decision=record.predicted_decision,
            runtime_actual_action=record.runtime_actual_action,
            decision_diff=record.decision_diff,
            decision_diff_reason_hint=record.decision_diff_reason_hint,
            realized_fill_ratio=fill_ratio,
            realized_time_to_fill_s=time_to_fill_s,
            realized_slippage_bps=slippage_bps,
            realized_alpha_decay_bps=alpha_decay_bps,
        )
        object.__setattr__(updated_record, "_record_id", record_id)
        self._records[record_id] = updated_record

    def resolve_record_id(self, record: ShadowDecisionRecord) -> str:
        raw_value = getattr(record, "_record_id", "")
        return str(raw_value)

    def records(self) -> tuple[ShadowDecisionRecord, ...]:
        return tuple(self._records.values())

    def record_by_id(self, record_id: str) -> ShadowDecisionRecord | None:
        return self._records.get(record_id)


def _decision_diff(*, predicted_action: str, runtime_actual_action: str) -> str:
    if predicted_action == runtime_actual_action:
        return "match"
    return f"predicted_{predicted_action}_actual_{runtime_actual_action}"


__all__ = [
    "ShadowDecisionRecord",
    "ShadowRoutingLogger",
]
