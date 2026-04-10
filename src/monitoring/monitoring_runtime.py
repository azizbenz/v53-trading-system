"""Build-10 runtime orchestration across snapshot, alerting, dashboard, and UI."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts import (
    OperatorSafingAction,
    OperatorSafingRequest,
    PairHealthLevel,
    ProfileId,
    RuntimeMode,
)
from interface_contracts.atomic_io import atomic_write_json
from monitoring.alert_manager import AlertLifecycleTracker, build_monitoring_alerts
from monitoring.contracts import (
    AlertHistoryEntry,
    Build14Projection,
    Build9XProjection,
    EngineMetrics,
    ExecutionNoTradeBridgeProjection,
    HealthDashboardPayload,
    InfraMetrics,
    LiveProjection,
    LiveLightProjection,
    MetaMetrics,
    MicroLiveProjection,
    MonitoringSnapshot,
    ObservabilityExport,
    PairMetrics,
    PortfolioMetrics,
    ReplayImportProjection,
    RuntimeHookBridgeProjection,
    ShadowProjection,
    TechnicalDashboardPayload,
)
from monitoring.health_dashboard_backend import build_health_dashboard_payload
from monitoring.metrics_collector import collect_monitoring_snapshot
from monitoring.observability import build_observability_export
from monitoring.technical_dashboard_backend import build_technical_dashboard_payload


def _ui_module():
    return importlib.import_module("ui")


class MonitoringRuntimeConfig(BaseModel, frozen=True):
    """Runtime persistence options for Build-10 guardrail state."""

    state_dir: Path | None = None
    persist_runtime_state: bool = False
    state_filename: str = "monitoring_runtime_state.json"
    alert_history_limit: int = Field(default=20, ge=1)


class MonitoringRuntimeState(BaseModel):
    """Persisted session guardrail state for Build-10 monitoring."""

    backlog_high_water_mark: int = Field(default=0, ge=0)
    stale_spike_count: int = Field(default=0, ge=0)
    last_stale_pair_count: int = Field(default=0, ge=0)
    alert_history: tuple[AlertHistoryEntry, ...] = ()


class MonitoringRuntimeResult(BaseModel, frozen=True):
    """Audit-ready Build-10 runtime result."""

    snapshot: MonitoringSnapshot
    health_payload: HealthDashboardPayload
    locked_operator_view: BaseModel
    technical_payload: TechnicalDashboardPayload
    technical_view: BaseModel
    observability_export: ObservabilityExport
    state_path: str = ""

    @property
    def light_view(self) -> BaseModel:
        return self.locked_operator_view


class MonitoringRuntime:
    """Stateful Build-10 runtime chaining snapshot -> alerts -> dashboard -> UI."""

    def __init__(
        self,
        *,
        locked_operator_ui_runtime: object | None = None,
        light_ui_runtime: object | None = None,
        config: MonitoringRuntimeConfig | None = None,
    ) -> None:
        if locked_operator_ui_runtime is not None and light_ui_runtime is not None:
            raise ValueError(
                "Use either locked_operator_ui_runtime or legacy light_ui_runtime, not both"
            )
        self._config = config or MonitoringRuntimeConfig()
        self._state_path = (
            self._config.state_dir / self._config.state_filename
            if self._config.state_dir is not None
            else None
        )
        state = self._load_or_create()
        self._backlog_high_water_mark = state.backlog_high_water_mark
        self._stale_spike_count = state.stale_spike_count
        self._last_stale_pair_count = state.last_stale_pair_count
        self._alert_lifecycle_tracker = AlertLifecycleTracker(
            history_limit=self._config.alert_history_limit,
            history=state.alert_history,
        )
        runtime_surface = locked_operator_ui_runtime or light_ui_runtime
        self._locked_operator_ui_runtime = (
            runtime_surface or _ui_module().LockedOperatorUiRuntime()
        )

    def evaluate(
        self,
        *,
        correlation_id: str,
        profile: ProfileId,
        runtime_mode: RuntimeMode,
        timestamp_ms: int,
        portfolio: PortfolioMetrics,
        infra: InfraMetrics,
        meta: MetaMetrics,
        engines: tuple[EngineMetrics, ...] = (),
        pairs: tuple[PairMetrics, ...] = (),
        active_modules: tuple[str, ...] = (),
        active_engines: tuple[str, ...] = (),
        build9x_projection: Build9XProjection | None = None,
        shadow_projection: ShadowProjection | None = None,
        micro_live_projection: MicroLiveProjection | None = None,
        live_projection: LiveProjection | None = None,
        live_light_projection: LiveLightProjection | None = None,
        build14_projection: Build14Projection | None = None,
        execution_no_trade_bridge_projection: ExecutionNoTradeBridgeProjection | None = None,
        runtime_hook_bridge_projections: tuple[RuntimeHookBridgeProjection, ...] | None = None,
        replay_projection: ReplayImportProjection | None = None,
    ) -> MonitoringRuntimeResult:
        """Evaluate the full Build-10 runtime path on real runtime inputs."""

        if live_projection is not None and live_light_projection is not None:
            raise ValueError(
                "Use either live_projection or legacy live_light_projection, not both"
            )
        resolved_live_projection = live_projection or live_light_projection

        resolved_infra = self._resolve_infra(infra=infra, pairs=pairs)
        snapshot = collect_monitoring_snapshot(
            correlation_id=correlation_id,
            profile=profile,
            runtime_mode=runtime_mode,
            timestamp_ms=timestamp_ms,
            portfolio=portfolio,
            infra=resolved_infra,
            meta=meta,
            engines=engines,
            pairs=pairs,
        )
        alerts = build_monitoring_alerts(snapshot)
        resolved_snapshot = snapshot.model_copy(update={"alerts": alerts})
        alert_history = self._alert_lifecycle_tracker.update(
            alerts=alerts,
            timestamp_ms=timestamp_ms,
        )
        preliminary_health_payload = build_health_dashboard_payload(
            resolved_snapshot,
            alert_history=alert_history,
            shadow_status=(
                shadow_projection.status if shadow_projection is not None else None
            ),
            micro_live_status=(
                micro_live_projection.status if micro_live_projection is not None else None
            ),
            live_light_status=(
                resolved_live_projection.status if resolved_live_projection is not None else None
            ),
        )
        locked_operator_runtime_result = self._locked_operator_ui_runtime.build_view(
            preliminary_health_payload,
            alerts=resolved_snapshot.alerts,
        )
        operator_runtime = self._locked_operator_ui_runtime.get_operator_projection()
        health_payload = build_health_dashboard_payload(
            resolved_snapshot,
            alert_history=alert_history,
            operator_runtime=operator_runtime,
            shadow_status=(
                shadow_projection.status if shadow_projection is not None else None
            ),
            micro_live_status=(
                micro_live_projection.status if micro_live_projection is not None else None
            ),
            live_light_status=(
                resolved_live_projection.status if resolved_live_projection is not None else None
            ),
        )
        technical_payload = build_technical_dashboard_payload(
            resolved_snapshot,
            active_modules=active_modules,
            active_engines=active_engines,
            build9x_projection=build9x_projection,
            shadow_projection=shadow_projection,
            micro_live_projection=micro_live_projection,
            live_projection=resolved_live_projection,
            build14_projection=build14_projection,
            execution_no_trade_bridge_projection=execution_no_trade_bridge_projection,
            runtime_hook_bridge_projections=runtime_hook_bridge_projections,
            replay_projection=replay_projection,
            operator_runtime=operator_runtime,
        )
        self._persist(alert_history=alert_history)
        return MonitoringRuntimeResult(
            snapshot=resolved_snapshot,
            health_payload=health_payload,
            locked_operator_view=locked_operator_runtime_result.view,
            technical_payload=technical_payload,
            technical_view=_ui_module().build_technical_dashboard_view(technical_payload),
            observability_export=build_observability_export(technical_payload),
            state_path=str(self._state_path) if self._state_path is not None else "",
        )

    def build_latest_operator_safing_request(self) -> OperatorSafingRequest | None:
        """Translate the latest accepted UI safing action into a typed protocol request."""

        operator_runtime = self._locked_operator_ui_runtime.get_operator_projection()
        if not operator_runtime.latest_safing_action:
            return None

        safing_event = next(
            (
                event
                for event in reversed(operator_runtime.recent_event_log)
                if event.accepted
                and event.action == operator_runtime.latest_safing_action
            ),
            None,
        )
        if safing_event is None:
            return None

        return OperatorSafingRequest(
            timestamp_ms=safing_event.timestamp_ms,
            request_id=(
                f"{safing_event.correlation_id}:"
                f"{operator_runtime.latest_safing_action}:"
                f"{safing_event.timestamp_ms}"
            ),
            action=OperatorSafingAction(operator_runtime.latest_safing_action),
            source_runtime_mode=RuntimeMode(operator_runtime.latest_safing_source_runtime_mode),
            target_runtime_mode=(
                RuntimeMode(operator_runtime.latest_safing_target_runtime_mode)
                if operator_runtime.latest_safing_target_runtime_mode
                else None
            ),
            requested_by="operator",
            ui_channel="local_operator_ui",
            reason=operator_runtime.latest_safing_reason or safing_event.operator_reason,
        )

    def _resolve_infra(
        self,
        *,
        infra: InfraMetrics,
        pairs: tuple[PairMetrics, ...],
    ) -> InfraMetrics:
        stale_pair_count = len(infra.stale_pairs) or sum(
            1
            for pair in pairs
            if pair.health
            in {
                PairHealthLevel.STALE,
                PairHealthLevel.OFFLINE,
                PairHealthLevel.SUSPENDED,
            }
        )
        if stale_pair_count > self._last_stale_pair_count and stale_pair_count > 0:
            self._stale_spike_count += 1
        self._last_stale_pair_count = stale_pair_count
        self._backlog_high_water_mark = max(
            self._backlog_high_water_mark,
            infra.backlog_high_water_mark,
            infra.queue_backlog,
        )

        persisted_metrics = tuple(dict.fromkeys(infra.persisted_metric_names))
        volatile_metrics = (
            infra.volatile_metric_names
            or tuple(
                metric_name
                for metric_name in (
                    "queue_backlog",
                    "backlog_high_water_mark",
                    "drop_rate_pct",
                    "stale_spike_count",
                    "recovery_retry_count",
                    "kill_switch_active",
                )
                if metric_name not in set(persisted_metrics)
            )
        )

        return infra.model_copy(
            update={
                "backlog_high_water_mark": max(infra.backlog_high_water_mark, self._backlog_high_water_mark),
                "stale_spike_count": max(infra.stale_spike_count, self._stale_spike_count),
                "volatile_metric_names": volatile_metrics,
                "persisted_metric_names": persisted_metrics,
            }
        )

    def _load_or_create(self) -> MonitoringRuntimeState:
        if self._state_path is not None and self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                return MonitoringRuntimeState(**data)
            except (json.JSONDecodeError, OSError, ValueError):
                pass
        return MonitoringRuntimeState()

    def _persist(self, *, alert_history: tuple[AlertHistoryEntry, ...]) -> None:
        if not self._config.persist_runtime_state or self._state_path is None:
            return
        if self._config.state_dir is not None:
            self._config.state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(
            self._state_path,
            MonitoringRuntimeState(
                backlog_high_water_mark=self._backlog_high_water_mark,
                stale_spike_count=self._stale_spike_count,
                last_stale_pair_count=self._last_stale_pair_count,
                alert_history=alert_history,
            ).model_dump(mode="json"),
        )


__all__ = [
    "MonitoringRuntime",
    "MonitoringRuntimeConfig",
    "MonitoringRuntimeResult",
    "MonitoringRuntimeState",
]
