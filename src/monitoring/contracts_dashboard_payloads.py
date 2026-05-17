"""Payload contracts split from contracts_dashboard to keep modules bounded."""

from __future__ import annotations

from interface_contracts import ProfileId, RuntimeMode, TimestampedModel

from .contracts_artifacts import (
    ArtifactComparisonProjection,
    ArtifactRuntimeVisibilityProjection,
    ArtifactThresholdConsumerProjection,
    ArtifactVerdictBundleProjection,
)
from .contracts_core import (
    InfraMetrics,
    PairMetrics,
    PortfolioMetrics,
    SystemProjection,
)
from .contracts_dashboard import (
    AccountUserDataProjection,
    AlertProjection,
    Build14Projection,
    Build9MetaProjection,
    Build9XProjection,
    EngineJudgmentProjection,
    EngineMetrics,
    ExecutionNoTradeBridgeProjection,
    ExecutionRuntimeProjectionBridgeProjection,
    LiveLightProjection,
    MicroLiveProjection,
    ReplayImportProjection,
    RuntimeHookBridgeProjection,
    ShadowProjection,
)
from .hybrid_router_metrics import HybridRouterMetricsProjection


class TechnicalDashboardPayload(TimestampedModel):
    """Normalized Build-10 technical supervision payload."""

    correlation_id: str
    profile: ProfileId
    runtime_mode: RuntimeMode
    system: SystemProjection
    portfolio: PortfolioMetrics
    engines: tuple[EngineMetrics, ...] = ()
    pairs: tuple[PairMetrics, ...] = ()
    infra: InfraMetrics = InfraMetrics()
    build9_meta: Build9MetaProjection
    build9x: Build9XProjection
    engine_judgment: EngineJudgmentProjection = EngineJudgmentProjection()
    shadow: ShadowProjection = ShadowProjection()
    micro_live: MicroLiveProjection = MicroLiveProjection()
    live_light: LiveLightProjection = LiveLightProjection()
    build14: Build14Projection = Build14Projection()
    account_user_data: AccountUserDataProjection = AccountUserDataProjection()
    execution_no_trade_bridge: ExecutionNoTradeBridgeProjection = (
        ExecutionNoTradeBridgeProjection()
    )
    execution_runtime_projection_bridge: ExecutionRuntimeProjectionBridgeProjection = (
        ExecutionRuntimeProjectionBridgeProjection()
    )
    hybrid_router: HybridRouterMetricsProjection = HybridRouterMetricsProjection()
    artifact_runtime_visibility: tuple[ArtifactRuntimeVisibilityProjection, ...] = ()
    artifact_threshold_consumers: tuple[ArtifactThresholdConsumerProjection, ...] = ()
    artifact_comparisons: tuple[ArtifactComparisonProjection, ...] = ()
    artifact_verdict_bundle: ArtifactVerdictBundleProjection | None = None
    shadow_last_completed_session_date: str = ""
    runtime_hook_bridges: tuple[RuntimeHookBridgeProjection, ...] = ()
    replay_import: ReplayImportProjection
    alerts: AlertProjection
    future_panels: tuple[str, ...] = (
        "technical_supervision",
        "build9x_diagnostics",
        "shadow_supervision",
        "micro_live_supervision",
        "live_light_supervision",
        "build14_supervision",
        "artifact_import",
        "observability_export",
    )

    @property
    def live(self) -> LiveLightProjection:
        return self.live_light


__all__ = ["TechnicalDashboardPayload"]
