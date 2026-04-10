"""Normalized Build-10 technical dashboard payload builder."""

from __future__ import annotations

from monitoring.alert_manager import build_monitoring_alerts
from monitoring.contracts import (
    AccountUserDataProjection,
    AlertProjection,
    Build14Projection,
    Build9MetaProjection,
    Build9XProjection,
    EngineJudgmentProjection,
    ExecutionNoTradeBridgeProjection,
    LiveProjection,
    LiveLightProjection,
    MicroLiveProjection,
    MonitoringSnapshot,
    OperatorRuntimeProjection,
    RuntimeHookBridgeProjection,
    ReplayImportProjection,
    ShadowProjection,
    SystemProjection,
    TechnicalDashboardPayload,
)
from monitoring.health_dashboard_backend import build_health_dashboard_payload
from interface_contracts import HookId, RUNTIME_OPEN_HOOK_IDS


def _resolve_snapshot(snapshot: MonitoringSnapshot) -> MonitoringSnapshot:
    if snapshot.alerts:
        return snapshot
    return snapshot.model_copy(update={"alerts": build_monitoring_alerts(snapshot)})


def _default_build9x_projection(*, active_modules: tuple[str, ...]) -> Build9XProjection:
    module_active = "meta_learning" in active_modules
    return Build9XProjection(
        status="info" if module_active else "planned",
        diagnostics_count=0,
        diagnostics_summary="No diagnostic report",
        open_hypotheses=0,
        total_hypotheses=0,
        near_miss_count=0,
        replay_candidate_count=0,
        memory_record_count=0,
        latest_memory_summary="No memory records",
        enrichment_hypothesis_count=0,
        latest_enrichment_target="",
        latest_enrichment_signal_family="",
        expected_replay_evidence_count=0,
        expected_shadow_evidence_count=0,
        enrichment_summary="No enrichment hypothesis mapped",
        review_export_ready=False,
        review_export_ref="",
        learning_queue_depth=0,
        learning_queue_oldest_age_ms=0,
        learning_worker_cpu_pct=0.0,
        learning_worker_rss_mb=0.0,
        learning_write_latency_ms=0.0,
        learning_export_failures_total=0,
        learning_log_loss_total=0,
        learning_unprocessed_items_count=0,
        learning_backlog_state="normal",
        learning_capture_mode="full_capture",
        learning_observability_reduced=False,
        learning_backpressure_active=False,
        review_blocked_due_to_incomplete_data=False,
        promotion_blocked_due_to_incomplete_data=False,
        learning_capacity_summary="queue=0 / backlog=normal / mode=full_capture",
    )


def _default_replay_projection(*, active_modules: tuple[str, ...]) -> ReplayImportProjection:
    modules_active = {
        "local_replay_runtime",
        "backtest_artifact_import",
    } & set(active_modules)
    return ReplayImportProjection(
        status="info" if modules_active else "planned",
        artifact_id="none",
        artifact_kind="No replay bundle exported",
        lineage_version="n/a",
        activation_stage="",
        health_state="",
        lifecycle_state="Awaiting LOCAL_REPLAY artifact",
        validation_status="not_run",
        review_state="No import review executed",
        compatibility_status="not_evaluated",
        signature_check_status="not_provided",
        conflict_resolution_mode="",
        conflict_hard_veto_action="",
        conflict_score_aggregation_mode="",
        conflict_size_reduce_mode="",
        conflict_rank_adjust_mode="",
        conflict_additive_soft_boosts_allowed=False,
        conflict_additive_soft_reduces_allowed=False,
        registry_atomicity_mode="",
        registry_concurrency_model="",
        registry_publish_requires_atomic_replace=False,
        registry_publish_requires_fsync=False,
        registry_rollback_to_last_known_good=False,
        rejection_reasons=(),
    )


def _default_shadow_projection(*, active_modules: tuple[str, ...]) -> ShadowProjection:
    module_active = "protocols" in active_modules
    return ShadowProjection(
        status="info" if module_active else "planned",
        run_state="not_run",
        verdict="not_run",
        truth_set_ref="",
        validation_set_ref="",
        divergent_comparison_count=0,
        blocking_comparison_count=0,
        total_comparison_count=0,
        build9x_diagnostics_count=0,
        open_hypotheses=0,
        replay_candidate_count=0,
        review_export_ready=False,
        import_artifact_id="none",
        import_lineage_version="n/a",
        blocking_reasons=(),
        manual_review_required=False,
    )


def _default_micro_live_projection(*, active_modules: tuple[str, ...]) -> MicroLiveProjection:
    module_active = "protocols" in active_modules
    return MicroLiveProjection(
        status="info" if module_active else "planned",
        run_state="not_run",
        verdict="not_run",
        shadow_run_id="",
        shadow_verdict="not_run",
        allowed_to_probe=False,
        requested_total_notional_usdt=0.0,
        approved_total_notional_usdt=0.0,
        approved_pair_notional_usdt=0.0,
        order_probe_limit=0,
        planned_pairs=(),
        planned_engines=(),
        import_artifact_id="none",
        import_lineage_version="n/a",
        observability_ready=False,
        halt_ready=False,
        onboarding_ready=False,
        blocking_reasons=(),
    )


def _default_live_light_projection(*, active_modules: tuple[str, ...]) -> LiveLightProjection:
    module_active = "protocols" in active_modules
    return LiveLightProjection(
        status="info" if module_active else "planned",
        run_state="not_run",
        verdict="not_run",
        micro_live_run_id="",
        micro_live_verdict="not_run",
        allowed_to_execute_small=False,
        requested_total_notional_usdt=0.0,
        approved_total_notional_usdt=0.0,
        approved_pair_notional_usdt=0.0,
        execution_order_limit=0,
        planned_pairs=(),
        planned_engines=(),
        import_artifact_id="none",
        import_lineage_version="n/a",
        observability_ready=False,
        halt_ready=False,
        execution_ready=False,
        broker_ready=False,
        exchange_ready=False,
        blocking_reasons=(),
    )


def _default_build14_projection(*, active_modules: tuple[str, ...]) -> Build14Projection:
    module_active = "complete_enablers" in active_modules
    return Build14Projection(
        status="info" if module_active else "planned",
        hard_state="shadow_enabled" if module_active else "coded",
        live_promotion_eligible=False,
        influence_mode="shadow_enabled" if module_active else "read_only",
        action="shadow_apply" if module_active else "observe",
        severity="nominal",
        summary=(
            "Build-14 enablers are SHADOW_ENABLED in Shadow; live promotion remains gated"
            if module_active
            else "Build-14 enablers are not materialized"
        ),
        market_toxicity_value=0.0,
        market_toxicity_status="nominal",
        execution_fragility_value=0.0,
        execution_fragility_status="nominal",
        confidence_penalty_weight=0.0,
        recommended_budget_factor=1.0,
        requires_manual_review=False,
        candidate_effect="shadow_enabled" if module_active else "observe_only",
        reason_codes=(),
        reader_projections=(),
    )


def _default_engine_judgment_projection() -> EngineJudgmentProjection:
    return EngineJudgmentProjection(
        status="planned",
        source_report_id="",
        source_shadow_run_id="",
        source_shadow_days_completed=0,
        source_shadow_required_days=30,
        cards=(),
    )


def _default_account_user_data_projection() -> AccountUserDataProjection:
    return AccountUserDataProjection(
        status="planned",
        authenticated=False,
        detail="No authenticated Binance user-data stream captured",
    )


def _default_execution_no_trade_bridge_projection(
    *,
    active_modules: tuple[str, ...],
) -> ExecutionNoTradeBridgeProjection:
    module_active = "protocols" in active_modules
    return ExecutionNoTradeBridgeProjection(
        status="info" if module_active else "planned",
        configured=False,
        selection_status="not_configured",
        detail=(
            "Compiled execution no-trade bridge is available but not configured"
            if module_active
            else "Compiled execution no-trade bridge is not materialized"
        ),
    )


_RUNTIME_HOOK_BRIDGE_LABELS: dict[HookId, str] = {
    HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION: "Engine A pre-entry",
    HookId.ENGINE_B_SWEEP_VALIDATION: "Engine B sweep",
    HookId.ENGINE_C_VOID_VALIDATION: "Engine C void",
    HookId.ENGINE_D_REENTRY_VALIDATION: "Engine D re-entry",
    HookId.RISK_MICRO_FRICTION_PRECHECK: "Risk micro-friction",
    HookId.SCORING_SOFT_PENALTY_LAYER: "Scoring soft penalty",
    HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT: "Portfolio relative rank",
    HookId.EXECUTION_NO_TRADE_FILTER: "Execution no-trade",
}


def _default_runtime_hook_bridge_projection(
    hook_id: HookId,
    *,
    active_modules: tuple[str, ...],
) -> RuntimeHookBridgeProjection:
    module_active = "protocols" in active_modules
    label = _RUNTIME_HOOK_BRIDGE_LABELS[hook_id]
    detail = (
        f"Compiled {label.lower()} bridge is available but not configured"
        if module_active
        else f"Compiled {label.lower()} bridge is not materialized"
    )
    return RuntimeHookBridgeProjection(
        hook_id=hook_id,
        label=label,
        status="info" if module_active else "planned",
        configured=False,
        selection_status="not_configured",
        detail=detail,
    )


def _runtime_hook_bridge_from_execution_no_trade_projection(
    projection: ExecutionNoTradeBridgeProjection,
) -> RuntimeHookBridgeProjection:
    return RuntimeHookBridgeProjection(
        hook_id=HookId.EXECUTION_NO_TRADE_FILTER,
        label=_RUNTIME_HOOK_BRIDGE_LABELS[HookId.EXECUTION_NO_TRADE_FILTER],
        status=projection.status,
        configured=projection.configured,
        selection_status=projection.selection_status,
        current_snapshot_id=projection.current_snapshot_id,
        previous_snapshot_id=projection.previous_snapshot_id,
        last_known_good_snapshot_id=projection.last_known_good_snapshot_id,
        binding_present=projection.binding_present,
        loaded=projection.loaded,
        compiled_plan_ref=projection.compiled_plan_ref,
        artifact_count=projection.artifact_count,
        failure_mode=projection.failure_mode,
        error_stage=projection.error_stage,
        error_type=projection.error_type,
        detail=projection.detail,
    )


def _execution_no_trade_bridge_from_runtime_hook_projection(
    projection: RuntimeHookBridgeProjection,
) -> ExecutionNoTradeBridgeProjection:
    return ExecutionNoTradeBridgeProjection(
        status=projection.status,
        configured=projection.configured,
        selection_status=projection.selection_status,
        current_snapshot_id=projection.current_snapshot_id,
        previous_snapshot_id=projection.previous_snapshot_id,
        last_known_good_snapshot_id=projection.last_known_good_snapshot_id,
        binding_present=projection.binding_present,
        loaded=projection.loaded,
        compiled_plan_ref=projection.compiled_plan_ref,
        artifact_count=projection.artifact_count,
        failure_mode=projection.failure_mode,
        error_stage=projection.error_stage,
        error_type=projection.error_type,
        detail=projection.detail,
    )


def _normalize_runtime_hook_bridge_projections(
    *,
    active_modules: tuple[str, ...],
    execution_no_trade_bridge: ExecutionNoTradeBridgeProjection,
    runtime_hook_bridge_projections: tuple[RuntimeHookBridgeProjection, ...] | None,
) -> tuple[RuntimeHookBridgeProjection, ...]:
    projections = {
        hook_id: _default_runtime_hook_bridge_projection(
            hook_id,
            active_modules=active_modules,
        )
        for hook_id in RUNTIME_OPEN_HOOK_IDS
    }
    projections[HookId.EXECUTION_NO_TRADE_FILTER] = (
        _runtime_hook_bridge_from_execution_no_trade_projection(execution_no_trade_bridge)
    )
    if runtime_hook_bridge_projections is not None:
        for projection in runtime_hook_bridge_projections:
            projections[projection.hook_id] = projection
    return tuple(projections[hook_id] for hook_id in RUNTIME_OPEN_HOOK_IDS)


def _build_build9_meta_projection(snapshot: MonitoringSnapshot) -> Build9MetaProjection:
    break_even_state = "drift_alert" if snapshot.meta.break_even_drift_alert else "stable"
    return Build9MetaProjection(
        dtr_coverage=snapshot.meta.dtr_coverage,
        dtr_status="healthy" if snapshot.meta.dtr_coverage >= 0.8 else "warning",
        cra_sterilization_rate=snapshot.meta.cra_sterilization_rate,
        cra_alert_count=snapshot.meta.cra_alert_count,
        cra_status=(
            "warning"
            if snapshot.meta.cra_sterilization_rate >= 0.2 or snapshot.meta.cra_alert_count > 0
            else "healthy"
        ),
        break_even_state=break_even_state,
        break_even_status="warning" if snapshot.meta.break_even_drift_alert else "healthy",
        break_even_drift_scopes=snapshot.meta.break_even_drift_scopes,
        edge_credible_count=snapshot.meta.edge_credible_count,
        edge_degraded_count=snapshot.meta.edge_degraded_count,
        edge_surveillance_count=snapshot.meta.edge_surveillance_count,
        edge_status="warning" if snapshot.meta.edge_degraded_count > 0 else "healthy",
    )


def _build_alert_projection(
    snapshot: MonitoringSnapshot,
    *,
    headline_status: str,
    operator_runtime: OperatorRuntimeProjection | None = None,
) -> AlertProjection:
    return AlertProjection(
        headline_status=headline_status,
        active_alert_count=snapshot.active_alert_count,
        alert_ids=tuple(alert.alert_id for alert in snapshot.alerts),
        queue_backlog=snapshot.infra.queue_backlog,
        backlog_high_water_mark=snapshot.infra.backlog_high_water_mark,
        drop_rate_pct=snapshot.infra.drop_rate_pct,
        stale_pair_count=snapshot.stale_pair_count,
        stale_pairs=snapshot.infra.stale_pairs,
        stale_spike_count=snapshot.infra.stale_spike_count,
        recovery_retry_count=snapshot.infra.recovery_retry_count,
        kill_switch_active=snapshot.infra.kill_switch_active,
        kill_switch_timestamp_ms=snapshot.infra.kill_switch_timestamp_ms,
        persisted_metric_names=snapshot.infra.persisted_metric_names,
        volatile_metric_names=snapshot.infra.volatile_metric_names,
        backlog_stale_status=(
            "warning" if snapshot.backlog_warning or snapshot.stale_warning else "healthy"
        ),
        dtr_loss_count=snapshot.infra.dtr_loss_count,
        log_loss_count=snapshot.infra.log_loss_count,
        break_even_drift_scope_count=len(snapshot.meta.break_even_drift_scopes),
        edge_degraded_count=snapshot.meta.edge_degraded_count,
        loss_drift_status=(
            "critical"
            if snapshot.loss_warning
            else "warning"
            if snapshot.meta.break_even_drift_alert or snapshot.meta.edge_degraded_count > 0
            else "healthy"
        ),
        operator_runtime=operator_runtime or OperatorRuntimeProjection(),
    )


def _elevate_headline_status_from_engine_judgment(
    headline_status: str,
    *,
    engine_judgment: EngineJudgmentProjection,
) -> str:
    if engine_judgment.status == "critical":
        return "critical"
    if engine_judgment.status == "warning" and headline_status == "healthy":
        return "warning"
    return headline_status


def _elevate_headline_status_from_build14(
    headline_status: str,
    *,
    build14: Build14Projection,
) -> str:
    if build14.severity == "critical" or build14.status == "critical":
        return "critical"
    if (
        build14.severity == "elevated" or build14.status == "warning"
    ) and headline_status == "healthy":
        return "warning"
    return headline_status


def _elevate_headline_status_from_account_user_data(
    headline_status: str,
    *,
    account_user_data: AccountUserDataProjection,
) -> str:
    if account_user_data.status == "critical":
        return "critical"
    if account_user_data.status == "warning" and headline_status == "healthy":
        return "warning"
    return headline_status


def _elevate_headline_status_from_replay_import(
    headline_status: str,
    *,
    replay_import: ReplayImportProjection,
) -> str:
    if replay_import.status == "critical":
        return "critical"
    if replay_import.status == "warning" and headline_status == "healthy":
        return "warning"
    return headline_status


def _elevate_headline_status_from_rollout(
    headline_status: str,
    *,
    shadow: ShadowProjection,
    micro_live: MicroLiveProjection,
    live_light: LiveProjection,
) -> str:
    rollout_statuses = (shadow.status, micro_live.status, live_light.status)
    if "critical" in rollout_statuses:
        return "critical"
    if "warning" in rollout_statuses and headline_status == "healthy":
        return "warning"
    return headline_status


def _elevate_headline_status_from_execution_no_trade_bridge(
    headline_status: str,
    *,
    execution_no_trade_bridge: ExecutionNoTradeBridgeProjection,
) -> str:
    if execution_no_trade_bridge.status == "critical":
        return "critical"
    if execution_no_trade_bridge.status == "warning" and headline_status == "healthy":
        return "warning"
    return headline_status


def _elevate_headline_status_from_runtime_hook_bridges(
    headline_status: str,
    *,
    runtime_hook_bridges: tuple[RuntimeHookBridgeProjection, ...],
) -> str:
    statuses = tuple(projection.status for projection in runtime_hook_bridges)
    if "critical" in statuses:
        return "critical"
    if "warning" in statuses and headline_status == "healthy":
        return "warning"
    return headline_status


def _elevate_headline_status_from_build9x(
    headline_status: str,
    *,
    build9x: Build9XProjection,
) -> str:
    if build9x.status == "critical":
        return "critical"
    if build9x.status == "warning" and headline_status == "healthy":
        return "warning"
    return headline_status


def _elevate_headline_status_from_build9_meta(
    headline_status: str,
    *,
    build9_meta: Build9MetaProjection,
) -> str:
    statuses = (
        build9_meta.dtr_status,
        build9_meta.cra_status,
        build9_meta.break_even_status,
        build9_meta.edge_status,
    )
    if "critical" in statuses:
        return "critical"
    if "warning" in statuses and headline_status == "healthy":
        return "warning"
    return headline_status


def _operator_safing_message(operator_runtime: OperatorRuntimeProjection) -> str:
    if not operator_runtime.latest_safing_action:
        return ""
    target = (
        f" -> {operator_runtime.latest_safing_target_runtime_mode}"
        if operator_runtime.latest_safing_target_runtime_mode
        else ""
    )
    reason = (
        f" reason={operator_runtime.latest_safing_reason}"
        if operator_runtime.latest_safing_reason
        else ""
    )
    return (
        "operator safing request: "
        f"{operator_runtime.latest_safing_action} "
        f"({operator_runtime.latest_safing_source_runtime_mode}{target})"
        f"{reason}"
    )


def _apply_operator_safing_to_micro_live_projection(
    projection: MicroLiveProjection,
    *,
    operator_runtime: OperatorRuntimeProjection | None,
) -> MicroLiveProjection:
    if operator_runtime is None:
        return projection
    if operator_runtime.latest_safing_source_runtime_mode != "micro_live":
        return projection
    if not operator_runtime.latest_safing_action:
        return projection
    reasons = list(projection.blocking_reasons)
    safing_message = _operator_safing_message(operator_runtime)
    if safing_message and safing_message not in reasons:
        reasons.append(safing_message)
    status = projection.status
    if operator_runtime.latest_safing_action == "set_halted":
        status = "critical"
    elif status in {"planned", "info", "healthy"}:
        status = "warning"
    run_state = (
        "operator_safing_requested"
        if projection.run_state in {"", "not_run"}
        else projection.run_state
    )
    return projection.model_copy(
        update={
            "status": status,
            "run_state": run_state,
            "operator_safing_action": operator_runtime.latest_safing_action,
            "operator_safing_target_runtime_mode": operator_runtime.latest_safing_target_runtime_mode,
            "operator_safing_reason": operator_runtime.latest_safing_reason,
            "blocking_reasons": tuple(reasons),
        }
    )


def _apply_operator_safing_to_live_light_projection(
    projection: LiveProjection,
    *,
    operator_runtime: OperatorRuntimeProjection | None,
) -> LiveProjection:
    if operator_runtime is None:
        return projection
    if operator_runtime.latest_safing_source_runtime_mode != "live":
        return projection
    if not operator_runtime.latest_safing_action:
        return projection
    reasons = list(projection.blocking_reasons)
    safing_message = _operator_safing_message(operator_runtime)
    if safing_message and safing_message not in reasons:
        reasons.append(safing_message)
    status = projection.status
    if operator_runtime.latest_safing_action == "set_halted":
        status = "critical"
    elif status in {"planned", "info", "healthy"}:
        status = "warning"
    run_state = (
        "operator_safing_requested"
        if projection.run_state in {"", "not_run"}
        else projection.run_state
    )
    return projection.model_copy(
        update={
            "status": status,
            "run_state": run_state,
            "operator_safing_action": operator_runtime.latest_safing_action,
            "operator_safing_target_runtime_mode": operator_runtime.latest_safing_target_runtime_mode,
            "operator_safing_reason": operator_runtime.latest_safing_reason,
            "blocking_reasons": tuple(reasons),
        }
    )


def build_technical_dashboard_payload(
    snapshot: MonitoringSnapshot,
    *,
    active_modules: tuple[str, ...] = (),
    active_engines: tuple[str, ...] = (),
    build9x_projection: Build9XProjection | None = None,
    engine_judgment_projection: EngineJudgmentProjection | None = None,
    shadow_projection: ShadowProjection | None = None,
    micro_live_projection: MicroLiveProjection | None = None,
    live_projection: LiveProjection | None = None,
    live_light_projection: LiveLightProjection | None = None,
    build14_projection: Build14Projection | None = None,
    account_user_data_projection: AccountUserDataProjection | None = None,
    execution_no_trade_bridge_projection: ExecutionNoTradeBridgeProjection | None = None,
    runtime_hook_bridge_projections: tuple[RuntimeHookBridgeProjection, ...] | None = None,
    replay_projection: ReplayImportProjection | None = None,
    operator_runtime: OperatorRuntimeProjection | None = None,
) -> TechnicalDashboardPayload:
    """Normalize runtime supervision truth into a typed Build-10 payload."""

    if live_projection is not None and live_light_projection is not None:
        raise ValueError(
            "Use either live_projection or legacy live_light_projection, not both"
        )
    resolved_live_projection = live_projection or live_light_projection

    resolved_snapshot = _resolve_snapshot(snapshot)
    headline_status = build_health_dashboard_payload(
        resolved_snapshot,
        operator_runtime=operator_runtime,
    ).headline_status
    build9x = build9x_projection or _default_build9x_projection(active_modules=active_modules)
    headline_status = _elevate_headline_status_from_build9x(
        headline_status,
        build9x=build9x,
    )
    engine_judgment = engine_judgment_projection or _default_engine_judgment_projection()
    headline_status = _elevate_headline_status_from_engine_judgment(
        headline_status,
        engine_judgment=engine_judgment,
    )
    shadow = shadow_projection or _default_shadow_projection(active_modules=active_modules)
    micro_live = _apply_operator_safing_to_micro_live_projection(
        micro_live_projection or _default_micro_live_projection(active_modules=active_modules),
        operator_runtime=operator_runtime,
    )
    live_light = _apply_operator_safing_to_live_light_projection(
        resolved_live_projection or _default_live_light_projection(active_modules=active_modules),
        operator_runtime=operator_runtime,
    )
    build14 = build14_projection or _default_build14_projection(active_modules=active_modules)
    headline_status = _elevate_headline_status_from_build14(
        headline_status,
        build14=build14,
    )
    account_user_data = account_user_data_projection or _default_account_user_data_projection()
    headline_status = _elevate_headline_status_from_account_user_data(
        headline_status,
        account_user_data=account_user_data,
    )
    execution_runtime_hook_projection = None
    if runtime_hook_bridge_projections is not None:
        execution_runtime_hook_projection = next(
            (
                projection
                for projection in runtime_hook_bridge_projections
                if projection.hook_id == HookId.EXECUTION_NO_TRADE_FILTER
            ),
            None,
        )
    execution_no_trade_bridge = execution_no_trade_bridge_projection
    if execution_no_trade_bridge is None and execution_runtime_hook_projection is not None:
        execution_no_trade_bridge = _execution_no_trade_bridge_from_runtime_hook_projection(
            execution_runtime_hook_projection
        )
    if execution_no_trade_bridge is None:
        execution_no_trade_bridge = _default_execution_no_trade_bridge_projection(
            active_modules=active_modules
        )
    runtime_hook_bridges = _normalize_runtime_hook_bridge_projections(
        active_modules=active_modules,
        execution_no_trade_bridge=execution_no_trade_bridge,
        runtime_hook_bridge_projections=runtime_hook_bridge_projections,
    )
    replay_import = replay_projection or _default_replay_projection(active_modules=active_modules)
    headline_status = _elevate_headline_status_from_execution_no_trade_bridge(
        headline_status,
        execution_no_trade_bridge=execution_no_trade_bridge,
    )
    headline_status = _elevate_headline_status_from_runtime_hook_bridges(
        headline_status,
        runtime_hook_bridges=runtime_hook_bridges,
    )
    headline_status = _elevate_headline_status_from_replay_import(
        headline_status,
        replay_import=replay_import,
    )
    headline_status = _elevate_headline_status_from_rollout(
        headline_status,
        shadow=shadow,
        micro_live=micro_live,
        live_light=live_light,
    )
    build9_meta = _build_build9_meta_projection(resolved_snapshot)
    headline_status = _elevate_headline_status_from_build9_meta(
        headline_status,
        build9_meta=build9_meta,
    )
    stale_engines = tuple(
        engine.engine_id
        for engine in resolved_snapshot.engines
        if engine.stale and (not active_engines or engine.engine_id in active_engines)
    )

    return TechnicalDashboardPayload(
        timestamp_ms=resolved_snapshot.timestamp_ms,
        correlation_id=resolved_snapshot.correlation_id,
        profile=resolved_snapshot.profile,
        runtime_mode=resolved_snapshot.runtime_mode,
        system=SystemProjection(
            headline_status=headline_status,
            active_modules=active_modules,
            active_engines=active_engines,
            stale_engines=stale_engines,
            build9x_status=build9x.status,
            shadow_status=shadow.status,
            micro_live_status=micro_live.status,
            live_light_status=live_light.status,
            build14_status=build14.status,
            replay_import_status=replay_import.status,
            governed_extensions_detail=(
                "Build-9X, Shadow, Micro-live, Live (historical label: Live-Light), replay/import, and Build-14 enablers remain governed. "
                "Complete stays closed and Build-14 does not bypass engines, risk, or portfolio."
            ),
        ),
        portfolio=resolved_snapshot.portfolio,
        engines=resolved_snapshot.engines,
        pairs=resolved_snapshot.pairs,
        infra=resolved_snapshot.infra,
        build9_meta=build9_meta,
        build9x=build9x,
        engine_judgment=engine_judgment,
        shadow=shadow,
        micro_live=micro_live,
        live_light=live_light,
        build14=build14,
        account_user_data=account_user_data,
        execution_no_trade_bridge=execution_no_trade_bridge,
        runtime_hook_bridges=runtime_hook_bridges,
        replay_import=replay_import,
        alerts=_build_alert_projection(
            resolved_snapshot,
            headline_status=headline_status,
            operator_runtime=operator_runtime,
        ),
    )


__all__ = [
    "build_technical_dashboard_payload",
]
