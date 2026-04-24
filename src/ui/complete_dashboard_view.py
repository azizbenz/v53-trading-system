"""Build-17 Complete dashboard view over normalized monitoring truth."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import (
    DashboardArtifactTransferManifest,
    DashboardCommandQueueSnapshot,
    LiveCompleteAllowedAction,
    LiveCompleteForbiddenAction,
    VpsRecoveryReadinessReport,
    VpsWarmupRunSummary,
)
from monitoring.contracts import TechnicalDashboardPayload
from ui.complete_dashboard_control_plane import build_complete_control_plane_section
from ui.contracts import DashboardCard, DashboardSection


class CompletePairMetadata(BaseModel, frozen=True):
    """Supplemental Build-17 metadata for a Complete pair row."""

    pair: str = Field(..., min_length=1)
    pair_class: str = "n/a"
    cluster: str = "n/a"
    beta_pair: float = 0.0
    active_engines: tuple[str, ...] = ()


class CompleteEngineMetadata(BaseModel, frozen=True):
    """Supplemental Build-17 metadata for a Complete engine row."""

    engine_id: str = Field(..., min_length=1)
    dominant_cluster: str = "n/a"
    active_pairs: tuple[str, ...] = ()
    cost_p90_bps: float = 0.0
    sterilization_note: str = "n/a"
    marginal_cost_note: str = "n/a"
    marginal_value_note: str = "n/a"


class CompleteDashboardSupplement(BaseModel, frozen=True):
    """Build-17-specific enrichments not yet carried by the Build-10 payload."""

    deployment_state: str = "live_complete"
    capital_total_usdt: float = Field(default=0.0, ge=0.0)
    capital_free_usdt: float = Field(default=0.0, ge=0.0)
    pnl_real_usdt: float = 0.0
    drawdown_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    k_eff: float = Field(default=1.0, ge=0.0)
    variance_estimate: float = Field(default=0.0, ge=0.0)
    cluster_pressure_summary: str = "not available"
    top_risk_contributors: tuple[str, ...] = ()
    engine_risk_contributors: tuple[str, ...] = ()
    pair_risk_contributors: tuple[str, ...] = ()
    cost_drift_vs_light_bps: float = 0.0
    pair_health_transition_summary: str = "not available"
    io_status: str = "not available"
    end_to_end_latency_ms: int = Field(default=0, ge=0)
    hard_block_rate_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    ranking_rejection_rate_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    phantom_trade_count: int = Field(default=0, ge=0)
    break_even_summary: tuple[str, ...] = ()
    edge_drift_summary: tuple[str, ...] = ()
    covariance_summary: str = "not available"
    top_correlations: tuple[str, ...] = ()
    covariance_drift_summary: str = "not available"
    redundancy_summary: str = "not available"
    c_marginal_contribution: str = "not available"
    d_marginal_contribution: str = "not available"
    event_log_refs: tuple[str, ...] = ()
    complete_gates: tuple[str, ...] = ()
    selected_pairs: tuple[str, ...] = ()
    available_pairs: tuple[str, ...] = ()
    pair_selection_source: str = "canonical_complete_universe"
    allowed_actions: tuple[LiveCompleteAllowedAction, ...] = (
        LiveCompleteAllowedAction.SUSPEND_PAIR,
        LiveCompleteAllowedAction.REQUEST_PAIR_RESUME,
        LiveCompleteAllowedAction.SUSPEND_ENGINE,
        LiveCompleteAllowedAction.REQUEST_ENGINE_RESUME,
        LiveCompleteAllowedAction.SET_HALTED,
        LiveCompleteAllowedAction.ROLLBACK_TO_LIGHT,
        LiveCompleteAllowedAction.REQUEST_UPLOAD_ML_ARTIFACT,
        LiveCompleteAllowedAction.REQUEST_UPLOAD_REGIME_DETECTOR_ARTIFACT,
        LiveCompleteAllowedAction.REQUEST_EXPORT_ACTIVE_ML_ARTIFACT,
        LiveCompleteAllowedAction.REQUEST_EXPORT_ACTIVE_REGIME_DETECTOR_ARTIFACT,
        LiveCompleteAllowedAction.REQUEST_EXPORT_REGIME_DETECTOR_SHADOW_AUDIT_BUNDLE,
        LiveCompleteAllowedAction.REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE,
        LiveCompleteAllowedAction.REQUEST_ACTIVATE_BINANCE_CREDENTIALS_PROFILE,
        LiveCompleteAllowedAction.REQUEST_EXPORT_BINANCE_CREDENTIAL_INVENTORY,
        LiveCompleteAllowedAction.REQUEST_DEACTIVATE_BINANCE_CREDENTIALS_PROFILE,
        LiveCompleteAllowedAction.VIEW_COMPLETE_GATES,
    )
    forbidden_actions: tuple[LiveCompleteForbiddenAction, ...] = (
        LiveCompleteForbiddenAction.PROFILE_CUSTOM,
        LiveCompleteForbiddenAction.ACTIVATE_UNVALIDATED_ENGINE,
        LiveCompleteForbiddenAction.MODIFY_RISK_CAPS,
        LiveCompleteForbiddenAction.INJECT_UNVERSIONED_CONFIG,
        LiveCompleteForbiddenAction.BYPASS_HARD_BLOCKER,
    )
    command_queue_snapshot: DashboardCommandQueueSnapshot | None = None
    active_ml_artifact: DashboardArtifactTransferManifest | None = None
    active_regime_detector_artifact: DashboardArtifactTransferManifest | None = None
    recovery_readiness_report: VpsRecoveryReadinessReport | None = None
    warmup_run_summary: VpsWarmupRunSummary | None = None
    active_binance_profile_id: str = ""
    active_binance_environment: str = ""
    binance_credential_validation_status: str = "unknown"
    credential_inventory_count: int = Field(default=0, ge=0)
    operator_report_status: str = "not_available"
    operator_report_ref: str = ""
    pair_metadata: tuple[CompletePairMetadata, ...] = ()
    engine_metadata: tuple[CompleteEngineMetadata, ...] = ()


def build_complete_dashboard_sections(
    payload: TechnicalDashboardPayload,
    supplement: CompleteDashboardSupplement,
) -> tuple[DashboardSection, ...]:
    """Project Build-17 Complete supervision into dashboard sections."""

    pair_meta_by_symbol = {item.pair: item for item in supplement.pair_metadata}
    engine_meta_by_id = {item.engine_id: item for item in supplement.engine_metadata}

    return (
        _build_overview_section(payload, supplement),
        _build_profile_state_section(payload, supplement),
        DashboardSection(title="Pairs (12 Pairs)", cards=_pair_cards(payload, pair_meta_by_symbol)),
        DashboardSection(title="Engines (A/B/C/D)", cards=_engine_cards(payload, engine_meta_by_id)),
        _build_risk_section(payload, supplement),
        _build_execution_section(payload, supplement, engine_meta_by_id),
        _build_infra_section(payload, supplement),
        _build_meta_section(payload, supplement),
        _build_covariance_section(supplement),
        _build_diversity_section(payload, supplement),
        build_complete_control_plane_section(supplement),
        _build_logs_section(payload, supplement),
        _build_admin_section(supplement),
    )


def _build_overview_section(
    payload: TechnicalDashboardPayload,
    supplement: CompleteDashboardSupplement,
) -> DashboardSection:
    active_pairs = sum(1 for pair in payload.pairs if pair.is_active)
    engines_visible = len(payload.engines)
    alert_status = "critical" if payload.alerts.active_alert_count else "healthy"
    return DashboardSection(
        title="Overview Portefeuille Complete",
        cards=(
            DashboardCard(
                key="overview_profile_state",
                label="Profile / State",
                value=f"{payload.profile.value} / {supplement.deployment_state}",
                status=payload.system.headline_status,
                detail=f"runtime={payload.runtime_mode.value}",
            ),
            DashboardCard(
                key="overview_surface",
                label="Pairs / Engines",
                value=f"{active_pairs}/{len(payload.pairs)} pairs / {engines_visible} engines",
                status="healthy" if active_pairs else "warning",
                detail=(
                    f"engines={', '.join(engine.engine_id for engine in payload.engines) or 'none'} / "
                    f"selected={_join(supplement.selected_pairs or tuple(pair.pair for pair in payload.pairs), empty='none')}"
                ),
            ),
            DashboardCard(
                key="overview_capital",
                label="Capital",
                value=(
                    f"total={supplement.capital_total_usdt:.0f} / "
                    f"engaged={payload.portfolio.capital_deployed_usdt:.0f} / "
                    f"free={supplement.capital_free_usdt:.0f}"
                ),
                status="info",
            ),
            DashboardCard(
                key="overview_performance",
                label="PnL / CE / DD",
                value=(
                    f"pnl={supplement.pnl_real_usdt:.2f} / "
                    f"ce={payload.portfolio.ce_net:.6f} / "
                    f"dd={supplement.drawdown_pct:.1f}%"
                ),
                status="healthy" if payload.portfolio.ce_net >= 0 else "warning",
            ),
            DashboardCard(
                key="overview_beta_cluster",
                label="Beta / Cluster",
                value=(
                    f"beta={payload.portfolio.beta_utilization:.2f} / "
                    f"cluster={payload.portfolio.dominant_cluster or 'n/a'}"
                ),
                status="warning" if payload.portfolio.beta_utilization >= 0.8 else "healthy",
            ),
            DashboardCard(
                key="overview_keff_alerts",
                label="Keff / Alerts",
                value=f"Keff={supplement.k_eff:.2f} / alerts={payload.alerts.active_alert_count}",
                status=alert_status,
                detail="Complete remains governed; no autonomous promotion implied",
            ),
        ),
    )


def _build_profile_state_section(
    payload: TechnicalDashboardPayload,
    supplement: CompleteDashboardSupplement,
) -> DashboardSection:
    gate_status = "healthy" if supplement.complete_gates else "warning"
    return DashboardSection(
        title="Profiles & Deployment State",
        cards=(
            DashboardCard(
                key="profile_runtime",
                label="Profile Runtime",
                value=f"profile={payload.profile.value} / runtime={payload.runtime_mode.value}",
                status="info",
                detail=f"deployment={supplement.deployment_state}",
            ),
            DashboardCard(
                key="deployment_headline",
                label="Headline",
                value=payload.system.headline_status,
                status=payload.system.headline_status,
                detail=f"{payload.alerts.active_alert_count} active alert(s)",
            ),
            DashboardCard(
                key="gates_complete",
                label="Complete Gates",
                value=str(len(supplement.complete_gates)),
                status=gate_status,
                detail=_join(supplement.complete_gates, empty="No gate evidence attached"),
            ),
            DashboardCard(
                key="pair_selection_scope",
                label="Pair Scope",
                value=(
                    f"{len(supplement.selected_pairs or tuple(pair.pair for pair in payload.pairs))}/"
                    f"{len(supplement.available_pairs or tuple(pair.pair for pair in payload.pairs))} selected"
                ),
                status="info",
                detail=(
                    f"source={supplement.pair_selection_source} / "
                    f"selected={_join(supplement.selected_pairs or tuple(pair.pair for pair in payload.pairs), empty='none')}"
                ),
            ),
            DashboardCard(
                key="rollback_halt",
                label="Rollback / Halt",
                value="available",
                status="warning" if payload.alerts.kill_switch_active else "info",
                detail="Rollback to Light and HALTED remain governed-only actions",
            ),
        ),
    )


def _pair_cards(
    payload: TechnicalDashboardPayload,
    pair_meta_by_symbol: dict[str, CompletePairMetadata],
) -> tuple[DashboardCard, ...]:
    cards: list[DashboardCard] = []
    for pair in payload.pairs:
        metadata = pair_meta_by_symbol.get(pair.pair)
        beta_pair = metadata.beta_pair if metadata else 0.0
        status = "healthy"
        if pair.health.value in {"stale", "offline", "suspended"} or not pair.is_active:
            status = "warning" if pair.health.value != "offline" else "critical"
        cards.append(
            DashboardCard(
                key=f"complete_pair_{pair.pair.lower()}",
                label=pair.pair,
                value=f"{'active' if pair.is_active else 'suspended'} / {pair.health.value}",
                status=status,
                detail=(
                    f"class={metadata.pair_class if metadata else 'n/a'} / "
                    f"cluster={metadata.cluster if metadata else 'n/a'} / "
                    f"beta={beta_pair:.2f} / "
                    f"engines={_join(metadata.active_engines if metadata else (), empty='n/a')} / "
                    f"cost={pair.average_cost_bps:.2f}/{pair.cost_p90_bps:.2f} / "
                    f"ce={pair.ce_expected:.6f} / freq={pair.useful_frequency:.2f}"
                    + (f" / reason={pair.suspension_reason}" if pair.suspension_reason else "")
                ),
            )
        )
    return tuple(cards) or (
        DashboardCard(
            key="complete_pairs_empty",
            label="Pairs",
            value="not available",
            status="planned",
            detail="No Complete pair projection provided",
        ),
    )


def _engine_cards(
    payload: TechnicalDashboardPayload,
    engine_meta_by_id: dict[str, CompleteEngineMetadata],
) -> tuple[DashboardCard, ...]:
    cards: list[DashboardCard] = []
    for engine in payload.engines:
        metadata = engine_meta_by_id.get(engine.engine_id)
        cost_p90_bps = metadata.cost_p90_bps if metadata else 0.0
        active_state = "suspended" if engine.suspension_reason else "active"
        status = "warning" if engine.stale or engine.suspension_reason or engine.net_edge_bps < 0 else "healthy"
        cards.append(
            DashboardCard(
                key=f"complete_engine_{engine.engine_id.lower()}",
                label=engine.engine_id,
                value=f"{active_state} / edge={engine.net_edge_bps:.2f}bps",
                status=status,
                detail=(
                    f"freq={engine.useful_frequency:.2f} / cost={engine.expected_cost_bps:.2f} / "
                    f"p90={cost_p90_bps:.2f} / "
                    f"ce={engine.ce_expected:.6f} / sharpe={engine.sharpe_per_trade:.2f} / "
                    f"dd={engine.drawdown_pct:.1f}% / "
                    f"cluster={metadata.dominant_cluster if metadata else 'n/a'} / "
                    f"pairs={_join(metadata.active_pairs if metadata else (), empty='n/a')}"
                    + (f" / steril={metadata.sterilization_note}" if metadata else "")
                    + (f" / reason={engine.suspension_reason}" if engine.suspension_reason else "")
                ),
            )
        )
    return tuple(cards) or (
        DashboardCard(
            key="complete_engines_empty",
            label="Engines",
            value="not available",
            status="planned",
            detail="No Complete engine projection provided",
        ),
    )


def _build_risk_section(
    payload: TechnicalDashboardPayload,
    supplement: CompleteDashboardSupplement,
) -> DashboardSection:
    return DashboardSection(
        title="Risk & Exposure Enriched",
        cards=(
            DashboardCard(
                key="complete_risk_exposure",
                label="Gross / Loss Budget",
                value=(
                    f"gross={payload.portfolio.gross_capacity_used_pct:.1f}% / "
                    f"loss={payload.portfolio.loss_capacity_used_pct:.1f}%"
                ),
                status="warning" if payload.portfolio.loss_capacity_used_pct >= 25.0 else "healthy",
                detail=f"capital={payload.portfolio.capital_deployed_usdt:.2f}",
            ),
            DashboardCard(
                key="complete_risk_cluster",
                label="Beta / Cluster Pressure",
                value=f"beta={payload.portfolio.beta_utilization:.2f}",
                status="warning" if payload.portfolio.beta_utilization >= 0.8 else "healthy",
                detail=supplement.cluster_pressure_summary,
            ),
            DashboardCard(
                key="complete_risk_variance",
                label="Variance / Keff",
                value=f"var={supplement.variance_estimate:.4f} / Keff={supplement.k_eff:.2f}",
                status="warning" if supplement.k_eff < 2.0 else "healthy",
                detail=_join(supplement.top_risk_contributors, empty="No top contributor projected"),
            ),
            DashboardCard(
                key="complete_risk_contributors",
                label="RC Pair / Engine",
                value=f"breaches={len(payload.portfolio.breaches)}",
                status="warning" if payload.portfolio.breaches else "healthy",
                detail=(
                    f"pairs={_join(supplement.pair_risk_contributors, empty='n/a')} / "
                    f"engines={_join(supplement.engine_risk_contributors, empty='n/a')} / "
                    f"breaches={_join(payload.portfolio.breaches, empty='none')}"
                ),
            ),
        ),
    )


def _build_execution_section(
    payload: TechnicalDashboardPayload,
    supplement: CompleteDashboardSupplement,
    engine_meta_by_id: dict[str, CompleteEngineMetadata],
) -> DashboardSection:
    engine_cost_summary = tuple(
        f"{engine.engine_id}:{engine.expected_cost_bps:.2f}/{engine_meta_by_id.get(engine.engine_id, CompleteEngineMetadata(engine_id=engine.engine_id)).cost_p90_bps:.2f}"
        for engine in payload.engines
    )
    avg_pair_cost = (
        sum(pair.average_cost_bps for pair in payload.pairs) / len(payload.pairs)
        if payload.pairs
        else 0.0
    )
    return DashboardSection(
        title="Costs & Execution Enriched",
        cards=(
            DashboardCard(
                key="complete_cost_engine",
                label="Cost by Engine",
                value=_join(engine_cost_summary, empty="n/a"),
                status="warning" if any(engine.net_edge_bps < 0 for engine in payload.engines) else "healthy",
                detail="avg/p90 bps by engine",
            ),
            DashboardCard(
                key="complete_cost_pair",
                label="Cost by Pair",
                value=f"avg={avg_pair_cost:.2f} / elw={payload.infra.elw_bps:.2f}",
                status="warning" if payload.infra.elw_bps > 1.0 else "healthy",
                detail="Pair-level cost surface remains visible in Complete",
            ),
            DashboardCard(
                key="complete_cost_drift",
                label="Cost Drift vs Light",
                value=f"{supplement.cost_drift_vs_light_bps:.2f} bps",
                status="warning" if supplement.cost_drift_vs_light_bps > 0.0 else "healthy",
                detail=(
                    f"partial={payload.infra.partial_fill_count} / "
                    f"reco={payload.infra.reconciliation_alert_count}"
                ),
            ),
            DashboardCard(
                key="complete_cost_cd",
                label="C vs A / D vs Idle",
                value="governed comparison",
                status="info",
                detail=(
                    f"C={engine_meta_by_id.get('engine_c', CompleteEngineMetadata(engine_id='engine_c')).marginal_cost_note} / "
                    f"D={engine_meta_by_id.get('engine_d', CompleteEngineMetadata(engine_id='engine_d')).marginal_cost_note}"
                ),
            ),
        ),
    )


def _build_infra_section(
    payload: TechnicalDashboardPayload,
    supplement: CompleteDashboardSupplement,
) -> DashboardSection:
    return DashboardSection(
        title="Data & Infra",
        cards=(
            DashboardCard(
                key="complete_infra_queue",
                label="Queue / Backlog",
                value=(
                    f"backlog={payload.infra.queue_backlog} / "
                    f"hwm={payload.infra.backlog_high_water_mark} / "
                    f"drop={payload.infra.drop_rate_pct:.1f}%"
                ),
                status="warning" if payload.infra.queue_backlog or payload.infra.drop_rate_pct > 0 else "healthy",
            ),
            DashboardCard(
                key="complete_infra_stale",
                label="Stale / Transitions",
                value=f"stale={len(payload.infra.stale_pairs)} / spikes={payload.infra.stale_spike_count}",
                status="warning" if payload.infra.stale_pairs or payload.infra.stale_spike_count > 0 else "healthy",
                detail=supplement.pair_health_transition_summary,
            ),
            DashboardCard(
                key="complete_infra_losses",
                label="Loss / Latency",
                value=(
                    f"dtr={payload.infra.dtr_loss_count} / "
                    f"log={payload.infra.log_loss_count} / "
                    f"e2e={supplement.end_to_end_latency_ms}ms"
                ),
                status="critical" if payload.infra.dtr_loss_count or payload.infra.log_loss_count else "healthy",
                detail=f"reconnect={payload.infra.reconnect_count}",
            ),
            DashboardCard(
                key="complete_infra_runtime",
                label="CPU / RAM / I/O",
                value=f"cpu={payload.infra.cpu_pct:.1f}% / ram={payload.infra.ram_pct:.1f}%",
                status="warning" if payload.infra.cpu_pct >= 70.0 or payload.infra.ram_pct >= 70.0 else "healthy",
                detail=supplement.io_status,
            ),
        ),
    )


def _build_meta_section(
    payload: TechnicalDashboardPayload,
    supplement: CompleteDashboardSupplement,
) -> DashboardSection:
    return DashboardSection(
        title="Meta / DTR / CRA / Edge",
        cards=(
            DashboardCard(
                key="complete_meta_dtr",
                label="DTR / Blocks / Ranking",
                value=(
                    f"dtr={payload.build9_meta.dtr_coverage:.2%} / "
                    f"hard={supplement.hard_block_rate_pct:.1f}% / "
                    f"rank={supplement.ranking_rejection_rate_pct:.1f}%"
                ),
                status="warning" if payload.build9_meta.dtr_coverage < 0.8 else "healthy",
            ),
            DashboardCard(
                key="complete_meta_cra",
                label="CRA / Phantom",
                value=(
                    f"cra={payload.build9_meta.cra_alert_count} / "
                    f"steril={payload.build9_meta.cra_sterilization_rate:.2%} / "
                    f"phantom={supplement.phantom_trade_count}"
                ),
                status="warning" if payload.build9_meta.cra_alert_count or payload.build9_meta.cra_sterilization_rate >= 0.2 else "healthy",
            ),
            DashboardCard(
                key="complete_meta_break_even",
                label="Break-even",
                value=payload.build9_meta.break_even_state,
                status=payload.build9_meta.break_even_status,
                detail=_join(supplement.break_even_summary, empty="No pair/engine break-even summary"),
            ),
            DashboardCard(
                key="complete_meta_edge",
                label="Prudent Edge",
                value=(
                    f"C={payload.build9_meta.edge_credible_count} / "
                    f"D={payload.build9_meta.edge_degraded_count} / "
                    f"S={payload.build9_meta.edge_surveillance_count}"
                ),
                status=payload.build9_meta.edge_status,
                detail=_join(supplement.edge_drift_summary, empty="No edge drift summary"),
            ),
        ),
    )


def _build_covariance_section(supplement: CompleteDashboardSupplement) -> DashboardSection:
    return DashboardSection(
        title="Covariance & Risk Contributions",
        cards=(
            DashboardCard(
                key="complete_covariance_matrix",
                label="Covariance Matrix",
                value=supplement.covariance_summary,
                status="info" if supplement.covariance_summary != "not available" else "planned",
            ),
            DashboardCard(
                key="complete_covariance_top",
                label="Top Correlations",
                value=str(len(supplement.top_correlations)),
                status="warning" if supplement.top_correlations else "planned",
                detail=_join(supplement.top_correlations, empty="No correlation set projected"),
            ),
            DashboardCard(
                key="complete_covariance_rc_pairs",
                label="Risk Contributors",
                value=str(len(supplement.top_risk_contributors)),
                status="warning" if supplement.top_risk_contributors else "planned",
                detail=(
                    f"top={_join(supplement.top_risk_contributors, empty='n/a')} / "
                    f"pairs={_join(supplement.pair_risk_contributors, empty='n/a')} / "
                    f"engines={_join(supplement.engine_risk_contributors, empty='n/a')}"
                ),
            ),
            DashboardCard(
                key="complete_covariance_drift",
                label="Covariance Drift",
                value=supplement.covariance_drift_summary,
                status="warning" if supplement.covariance_drift_summary != "not available" else "planned",
            ),
        ),
    )


def _build_diversity_section(
    payload: TechnicalDashboardPayload,
    supplement: CompleteDashboardSupplement,
) -> DashboardSection:
    return DashboardSection(
        title="Effective Edge Diversity",
        cards=(
            DashboardCard(
                key="complete_diversity_engines",
                label="Engine Correlations",
                value=str(len(payload.engines)),
                status="info",
                detail=_join(tuple(engine.engine_id for engine in payload.engines), empty="No engine projected"),
            ),
            DashboardCard(
                key="complete_diversity_redundancy",
                label="Redundancy / Keff",
                value=f"Keff={supplement.k_eff:.2f}",
                status="warning" if supplement.k_eff < 2.0 else "healthy",
                detail=supplement.redundancy_summary,
            ),
            DashboardCard(
                key="complete_diversity_c",
                label="Contribution C",
                value=supplement.c_marginal_contribution,
                status="info" if supplement.c_marginal_contribution != "not available" else "planned",
            ),
            DashboardCard(
                key="complete_diversity_d",
                label="Contribution D",
                value=supplement.d_marginal_contribution,
                status="info" if supplement.d_marginal_contribution != "not available" else "planned",
            ),
        ),
    )


def _build_logs_section(
    payload: TechnicalDashboardPayload,
    supplement: CompleteDashboardSupplement,
) -> DashboardSection:
    return DashboardSection(
        title="Logs & Events",
        cards=(
            DashboardCard(
                key="complete_logs_categories",
                label="Categories",
                value="infra,data,risk,execution,portfolio,engine,pair,operator,alerts",
                status="info",
                detail=f"correlation_id={payload.correlation_id}",
            ),
            DashboardCard(
                key="complete_logs_refs",
                label="Event Links",
                value=str(len(supplement.event_log_refs)),
                status="warning" if supplement.event_log_refs else "planned",
                detail=_join(supplement.event_log_refs, empty="No event reference projected"),
            ),
            DashboardCard(
                key="complete_logs_alerts",
                label="Alert Traceability",
                value=str(payload.alerts.active_alert_count),
                status="critical" if payload.alerts.active_alert_count else "healthy",
                detail=_join(payload.alerts.alert_ids, empty="No active alert"),
            ),
        ),
    )


def _build_admin_section(supplement: CompleteDashboardSupplement) -> DashboardSection:
    return DashboardSection(
        title="Controlled Complete Administration",
        cards=(
            DashboardCard(
                key="complete_admin_allowed",
                label="Allowed Actions",
                value=str(len(supplement.allowed_actions)),
                status="healthy",
                detail=_join(supplement.allowed_actions, empty="No allowed action declared"),
            ),
            DashboardCard(
                key="complete_admin_forbidden",
                label="Forbidden Actions",
                value=str(len(supplement.forbidden_actions)),
                status="critical",
                detail=_join(supplement.forbidden_actions, empty="No forbidden action declared"),
            ),
            DashboardCard(
                key="complete_admin_gates",
                label="Gates / Rollback",
                value=str(len(supplement.complete_gates)),
                status="warning" if supplement.complete_gates else "planned",
                detail="Every sensitive action remains journalized and gate-bound",
            ),
        ),
    )


def _join(values: tuple[str, ...], *, empty: str) -> str:
    return ", ".join(values) if values else empty


__all__ = [
    "CompletePairMetadata",
    "CompleteEngineMetadata",
    "CompleteDashboardSupplement",
    "build_complete_dashboard_sections",
]
