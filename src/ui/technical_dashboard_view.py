"""Technical Build-10 supervision view over the normalized backend payload."""

from __future__ import annotations

from monitoring.contracts import TechnicalDashboardPayload
from ui.contracts import DashboardCard, DashboardSection, LightDashboardView
from ui.operator_actions import build_light_allowed_actions


def _join(values: tuple[str, ...], *, empty: str) -> str:
    return ", ".join(values) if values else empty


def _replay_signature_card_status(payload: TechnicalDashboardPayload) -> str:
    replay = payload.replay_import
    if replay.signature_check_status == "trust_eligible":
        return "healthy"
    if replay.signature_check_status == "not_provided":
        return "planned" if replay.artifact_id == "none" else "info"
    return "warning"


def _replay_compatibility_card_status(payload: TechnicalDashboardPayload) -> str:
    replay = payload.replay_import
    if replay.compatibility_status == "supported":
        return "healthy"
    if replay.compatibility_status == "not_evaluated":
        return "planned" if replay.artifact_id == "none" else "info"
    return "warning"


def _replay_compatibility_card_detail(payload: TechnicalDashboardPayload) -> str:
    replay = payload.replay_import
    if replay.compatibility_status == "not_evaluated" and replay.artifact_id == "none":
        return "No replay import candidate materialized"
    return _join(replay.compatibility_reasons, empty="No compatibility policy issue")


def _replay_signature_card_detail(payload: TechnicalDashboardPayload) -> str:
    replay = payload.replay_import
    if replay.signature_check_status == "not_provided" and replay.artifact_id == "none":
        return "No replay import candidate materialized"
    key_id = replay.signature_key_id or "none"
    trust = replay.trusted_key_status or "n/a"
    reasons = _join(replay.signature_check_reasons, empty="No signature policy issue")
    return f"key={key_id} / trust={trust} / {reasons}"


def _replay_conflict_card_status(payload: TechnicalDashboardPayload) -> str:
    replay = payload.replay_import
    if replay.conflict_resolution_mode == "" and replay.artifact_id == "none":
        return "planned"
    if replay.conflict_hard_veto_action == "no_trade":
        return "healthy"
    return "warning"


def _replay_conflict_card_detail(payload: TechnicalDashboardPayload) -> str:
    replay = payload.replay_import
    if replay.conflict_resolution_mode == "" and replay.artifact_id == "none":
        return "No replay import candidate materialized"
    return (
        f"veto={replay.conflict_hard_veto_action or 'n/a'} / "
        f"score={replay.conflict_score_aggregation_mode or 'n/a'} / "
        f"size={replay.conflict_size_reduce_mode or 'n/a'} / "
        f"rank={replay.conflict_rank_adjust_mode or 'n/a'} / "
        f"boosts={'yes' if replay.conflict_additive_soft_boosts_allowed else 'no'} / "
        f"reduces={'yes' if replay.conflict_additive_soft_reduces_allowed else 'no'}"
    )


def _replay_registry_card_status(payload: TechnicalDashboardPayload) -> str:
    replay = payload.replay_import
    if replay.registry_atomicity_mode == "" and replay.artifact_id == "none":
        return "planned"
    if (
        replay.registry_publish_requires_atomic_replace
        and replay.registry_publish_requires_fsync
        and replay.registry_rollback_to_last_known_good
    ):
        return "healthy"
    return "warning"


def _replay_registry_card_detail(payload: TechnicalDashboardPayload) -> str:
    replay = payload.replay_import
    if replay.registry_atomicity_mode == "" and replay.artifact_id == "none":
        return "No replay import candidate materialized"
    return (
        f"atomic={replay.registry_atomicity_mode or 'n/a'} / "
        f"concurrency={replay.registry_concurrency_model or 'n/a'} / "
        f"atomic_replace={'yes' if replay.registry_publish_requires_atomic_replace else 'no'} / "
        f"fsync={'yes' if replay.registry_publish_requires_fsync else 'no'} / "
        f"lkg={'yes' if replay.registry_rollback_to_last_known_good else 'no'}"
    )


def _engine_card(payload: TechnicalDashboardPayload) -> DashboardCard:
    if not payload.system.active_engines:
        return DashboardCard(
            key="engines_ab",
            label="Engines A/B",
            value="0",
            status="planned",
            detail="No active engines declared",
        )

    detail = f"Active: {_join(payload.system.active_engines, empty='none')}"
    if payload.system.stale_engines:
        detail = f"{detail} / stale: {_join(payload.system.stale_engines, empty='none')}"
        status = "warning"
    else:
        status = "healthy"

    return DashboardCard(
        key="engines_ab",
        label="Engines A/B",
        value=str(len(payload.system.active_engines)),
        status=status,
        detail=detail,
    )


def _operator_safing_value(payload: TechnicalDashboardPayload) -> str:
    action = payload.alerts.operator_runtime.latest_safing_action
    target = payload.alerts.operator_runtime.latest_safing_target_runtime_mode
    if not action:
        return "none"
    return f"{action} -> {target}" if target else action


def _operator_supervision_status(payload: TechnicalDashboardPayload) -> str:
    if payload.system.headline_status == "critical":
        return "critical"
    if payload.system.headline_status == "warning":
        return "warning"
    return "healthy"


def _build14_reader_status(value: str) -> str:
    if value == "critical":
        return "critical"
    if value == "elevated":
        return "warning"
    return "info"


def _build14_readers_summary(payload: TechnicalDashboardPayload) -> str:
    if not payload.build14.reader_projections:
        return "No Build-14 reader projection materialized"
    parts = []
    for reader in payload.build14.reader_projections:
        parts.append(f"{reader.reader_name}={reader.status} ({reader.observed_value:.2f})")
    return " / ".join(parts)


def _build14_reader_cards(payload: TechnicalDashboardPayload) -> tuple[DashboardCard, ...]:
    if not payload.build14.reader_projections:
        return ()
    cards: list[DashboardCard] = []
    for reader in payload.build14.reader_projections:
        cards.append(
            DashboardCard(
                key=f"build14_reader_{reader.reader_name}",
                label=reader.reader_name,
                value=f"{reader.status} ({reader.observed_value:.2f})",
                status=_build14_reader_status(reader.status),
                detail=(
                    f"family={reader.signal_family} / {reader.detail}"
                    + (
                        f" / log={reader.structured_log_key}"
                        if reader.structured_log_key
                        else ""
                    )
                ),
            )
        )
    return tuple(cards)


def _engine_physics_detail(engine) -> str:
    parts: list[str] = []
    physics = engine.physics
    if physics.physics_pressure_state and physics.physics_pressure_state != "nominal":
        parts.append(f"state={physics.physics_pressure_state}")
    if physics.delta_confirmation is not None:
        parts.append(f"delta={physics.delta_confirmation:.2f}")
    if physics.execution_fragility is not None:
        parts.append(f"fragility={physics.execution_fragility:.2f}")
    if physics.market_toxicity is not None:
        parts.append(f"toxicity={physics.market_toxicity:.2f}")
    if physics.spread_regime_penalty is not None:
        parts.append(f"spread_penalty={physics.spread_regime_penalty:.2f}")
    if physics.competition_support is not None:
        parts.append(f"competition={physics.competition_support:.2f}")
    if physics.sweep_score is not None:
        parts.append(f"sweep={physics.sweep_score:.2f}")
    if physics.absorption_score is not None:
        parts.append(f"absorption={physics.absorption_score:.2f}")
    if physics.poc_reversion_score is not None:
        parts.append(f"poc={physics.poc_reversion_score:.2f}")
    if physics.false_breakout_score is not None:
        parts.append(f"false_breakout={physics.false_breakout_score:.2f}")
    if physics.fragility_score is not None:
        parts.append(f"fragility_score={physics.fragility_score:.2f}")
    if physics.toxicity_score is not None:
        parts.append(f"toxicity_score={physics.toxicity_score:.2f}")
    if physics.execution_survivability_score is not None:
        parts.append(f"survivability={physics.execution_survivability_score:.2f}")
    if physics.micro_friction_score is not None:
        parts.append(f"micro_friction={physics.micro_friction_score:.2f}")
    return ", ".join(parts)


def _operator_controls_section(payload: TechnicalDashboardPayload) -> DashboardSection:
    allowed_actions = build_light_allowed_actions(payload.runtime_mode)
    safing_actions = tuple(
        action.value
        for action in allowed_actions
        if action.value in {"set_halted", "downgrade_to_micro_live", "downgrade_to_shadow"}
    )
    latest_safing_action = payload.alerts.operator_runtime.latest_safing_action
    kill_path_active = payload.alerts.kill_switch_active or latest_safing_action == "set_halted"
    supervision_status = _operator_supervision_status(payload)

    return DashboardSection(
        title="Operator Controls",
        cards=(
            DashboardCard(
                key="operator_manual_scope",
                label="Manual Scope",
                value=f"{len(allowed_actions)} actions",
                status="info",
                detail=_join(tuple(action.value for action in allowed_actions), empty="No action exposed"),
            ),
            DashboardCard(
                key="operator_safing_controls",
                label="Safing Controls",
                value=str(len(safing_actions)),
                status=supervision_status if safing_actions else "planned",
                detail=(
                    f"{_join(safing_actions, empty='No safing action exposed')} / "
                    f"supervision={payload.system.headline_status}"
                ),
            ),
            DashboardCard(
                key="operator_latest_safing",
                label="Latest Safing",
                value=_operator_safing_value(payload),
                status=(
                    "critical"
                    if latest_safing_action == "set_halted"
                    else "warning"
                    if latest_safing_action
                    else "info"
                ),
                detail=(
                    payload.alerts.operator_runtime.latest_safing_reason
                    or "No manual safing request recorded"
                ),
            ),
            DashboardCard(
                key="operator_kill_path",
                label="Kill Path",
                value="active" if kill_path_active else "armed",
                status="critical" if kill_path_active else supervision_status,
                detail=(
                    "SET_HALTED is available via the local operator UI"
                    if not payload.alerts.kill_switch_active
                    else "Infra kill switch is active; trading must remain halted"
                ),
            ),
        ),
    )


def _pair_cards(payload: TechnicalDashboardPayload) -> tuple[DashboardCard, ...]:
    if not payload.pairs:
        return (
            DashboardCard(
                key="pairs_empty",
                label="Pairs",
                value="0",
                status="planned",
                detail="No pair monitoring metrics declared",
            ),
        )

    cards: list[DashboardCard] = []
    for pair in payload.pairs:
        status = (
            "warning"
            if pair.health.value in {"stale", "offline", "suspended"}
            else "healthy"
        )
        detail = (
            f"cost={pair.average_cost_bps:.1f} / p90={pair.cost_p90_bps:.1f} / "
            f"ce={pair.ce_expected:.4f} / freq={pair.useful_frequency:.2f} / "
            f"backlog={pair.backlog_depth}"
        )
        if pair.suspension_reason:
            detail = f"{detail} / reason={pair.suspension_reason}"
        cards.append(
            DashboardCard(
                key=f"pair_{pair.pair.lower()}",
                label=pair.pair,
                value=f"{pair.health.value} / fresh={pair.freshness_ms}ms",
                status=status,
                detail=detail,
            )
        )
    return tuple(cards)


def _engine_cards(payload: TechnicalDashboardPayload) -> tuple[DashboardCard, ...]:
    if not payload.engines:
        return (
            DashboardCard(
                key="engines_empty",
                label="Engines",
                value="0",
                status="planned",
                detail="No engine monitoring metrics declared",
            ),
        )

    cards: list[DashboardCard] = []
    for engine in payload.engines:
        status = (
            "warning"
            if engine.stale or engine.suspension_reason
            else "healthy"
        )
        detail = (
            f"cost={engine.expected_cost_bps:.1f} / ce={engine.ce_expected:.4f} / "
            f"freq={engine.useful_frequency:.2f} / sharpe={engine.sharpe_per_trade:.2f} / "
            f"dd={engine.drawdown_pct:.1f}%"
        )
        detail = (
            f"{detail} / penalized={engine.scoring_penalized_score:.2f} / "
            f"size_mult={engine.scoring_final_size_multiplier:.2f}"
        )
        if engine.scoring_ranking_score is not None:
            detail = f"{detail} / ranking={engine.scoring_ranking_score:.2f}"
        if engine.scoring_summary:
            detail = f"{detail} / scoring={engine.scoring_summary}"
        if engine.risk_summary:
            detail = f"{detail} / risk={engine.risk_summary}"
        if engine.scoring_reason_codes:
            detail = f"{detail} / score_codes={','.join(engine.scoring_reason_codes)}"
        if engine.risk_reason_codes:
            detail = f"{detail} / risk_codes={','.join(engine.risk_reason_codes)}"
        if engine.selection_outcome_code:
            detail = f"{detail} / selection={engine.selection_outcome_code}"
        if engine.portfolio_verdict_code:
            detail = f"{detail} / portfolio={engine.portfolio_verdict_code}"
        if engine.phantom_trade:
            phantom_detail = engine.phantom_reason_code or "phantom"
            detail = f"{detail} / phantom={phantom_detail}"
        if engine.hard_blocked:
            detail = f"{detail} / hard_blocked=yes"
        if engine.risk_decision_severity:
            detail = f"{detail} / risk_severity={engine.risk_decision_severity}"
        if engine.drawdown_state_code:
            detail = f"{detail} / drawdown={engine.drawdown_state_code}"
        if engine.blocked_guard_count > 0:
            detail = f"{detail} / blocked_guards={engine.blocked_guard_count}"
        physics_detail = _engine_physics_detail(engine)
        if physics_detail:
            detail = f"{detail} / physics={physics_detail}"
        if engine.suspension_reason:
            detail = f"{detail} / reason={engine.suspension_reason}"
        cards.append(
            DashboardCard(
                key=f"engine_{engine.engine_id.lower()}",
                label=engine.engine_id,
                value=(
                    f"signals={engine.emitted_signals} / "
                    f"edge={engine.net_edge_bps:.1f}"
                ),
                status=status,
                detail=detail,
            )
        )
    return tuple(cards)


def _engine_judgment_cards(payload: TechnicalDashboardPayload) -> tuple[DashboardCard, ...]:
    judgment = payload.engine_judgment
    if not judgment.cards:
        return (
            DashboardCard(
                key="engine_judgment_empty",
                label="Engine Judgment",
                value="not available",
                status=judgment.status,
                detail="No Shadow report-derived engine judgment has been projected yet.",
            ),
        )

    promotable_count = sum(1 for card in judgment.cards if card.judgment_verdict == "promotable")
    shadow_only_count = sum(1 for card in judgment.cards if card.judgment_verdict == "shadow-only")
    rewrite_required_count = sum(
        1 for card in judgment.cards if card.judgment_verdict == "rewrite-required"
    )
    dormant_count = sum(1 for card in judgment.cards if card.judgment_verdict == "dormant")

    cards: list[DashboardCard] = [
        DashboardCard(
            key="engine_judgment_summary",
            label="Verdict Summary",
            value=(
                f"promotable={promotable_count} / shadow-only={shadow_only_count} / "
                f"rewrite={rewrite_required_count} / dormant={dormant_count}"
            ),
            status=judgment.status,
            detail=f"engines={len(judgment.cards)} / supervised verdict surface",
        ),
        DashboardCard(
            key="engine_judgment_source",
            label="Shadow Source",
            value=(
                f"{judgment.source_shadow_days_completed}/"
                f"{judgment.source_shadow_required_days} day(s)"
            ),
            status=judgment.status,
            detail=(
                f"report={judgment.source_report_id or 'n/a'} / "
                f"run={judgment.source_shadow_run_id or 'n/a'}"
            ),
        ),
    ]
    if judgment.portfolio_judgment_verdict:
        detail = (
            f"physics={judgment.portfolio_physics_pressure or 'n/a'} / "
            f"redundancy={judgment.portfolio_redundancy_pressure or 'n/a'} / "
            f"cluster={judgment.portfolio_cluster_pressure or 'n/a'} / "
            f"beta={judgment.portfolio_beta_pressure or 'n/a'} / "
            f"gross={judgment.portfolio_gross_capacity_pressure or 'n/a'} / "
            f"loss={judgment.portfolio_loss_capacity_pressure or 'n/a'} / "
            f"portfolio_rejected={judgment.portfolio_rejected_engine_count} / "
            f"ranking_rejected={judgment.ranking_rejected_engine_count} / "
            f"elevated_physics={judgment.elevated_physics_engine_count} / "
            f"critical_physics={judgment.critical_physics_engine_count} / "
            f"phantom={judgment.phantom_trade_count}"
        )
        if judgment.portfolio_rationale:
            detail = f"{detail} / rationale={judgment.portfolio_rationale}"
        cards.append(
            DashboardCard(
                key="engine_judgment_portfolio",
                label="Portfolio Verdict",
                value=judgment.portfolio_judgment_verdict,
                status=(
                    "healthy"
                    if judgment.portfolio_judgment_verdict == "promotable"
                    else "warning"
                    if judgment.portfolio_judgment_verdict == "shadow-only"
                    else "critical"
                    if judgment.portfolio_judgment_verdict == "rewrite-required"
                    else "planned"
                ),
                detail=detail,
            )
        )
    for card in judgment.cards:
        detail = (
            f"shadow_component={card.component_verdict} / useful_freq={card.useful_frequency:.2f} / "
            f"ce={card.ce_expected:.4f} / cost_bps={card.estimated_cost_bps:.2f} / "
            f"edge_net={card.edge_net:.4f} / economic_pass={card.economic_pass_rate:.2f} / "
            f"redundancy={card.redundancy_score:.2f} / "
            f"portfolio_contribution={card.portfolio_contribution:.4f} / "
            f"conflict={card.conflict_rate:.2f} / marginal_edge={card.marginal_edge:.4f} / "
            f"obs={card.observations}"
        )
        if card.rationale:
            detail = f"{detail} / rationale={card.rationale}"
        if card.evidence_summary:
            detail = f"{detail} / evidence={card.evidence_summary}"
        cards.append(
            DashboardCard(
                key=f"engine_judgment_{card.engine_id.lower()}",
                label=card.engine_id,
                value=card.judgment_verdict,
                status=card.status,
                detail=detail,
            )
        )
    return tuple(cards)


def _risk_cards(payload: TechnicalDashboardPayload) -> tuple[DashboardCard, ...]:
    return (
        DashboardCard(
            key="risk_exposure",
            label="Exposure",
            value=(
                f"gross={payload.portfolio.gross_capacity_used_pct:.1f}% / "
                f"loss={payload.portfolio.loss_capacity_used_pct:.1f}%"
            ),
            status=(
                "warning"
                if payload.portfolio.loss_capacity_used_pct >= 25.0
                else "healthy"
            ),
            detail=f"capital={payload.portfolio.capital_deployed_usdt:.2f}",
        ),
        DashboardCard(
            key="risk_beta_cluster",
            label="Beta / Cluster",
            value=(
                f"beta={payload.portfolio.beta_utilization:.2f} / "
                f"cluster={payload.portfolio.dominant_cluster or 'n/a'}"
            ),
            status="warning" if payload.portfolio.beta_utilization >= 0.8 else "healthy",
            detail=f"pnl={payload.portfolio.pnl_net_usdt:.2f}",
        ),
        DashboardCard(
            key="risk_breaches",
            label="Breaches",
            value=str(len(payload.portfolio.breaches)),
            status="warning" if payload.portfolio.breaches else "healthy",
            detail=_join(payload.portfolio.breaches, empty="No active breach"),
        ),
    )


def _execution_cards(payload: TechnicalDashboardPayload) -> tuple[DashboardCard, ...]:
    return (
        DashboardCard(
            key="execution_costs",
            label="Costs",
            value=(
                f"exp={payload.infra.expected_cost_bps:.1f} / "
                f"real={payload.infra.realized_cost_bps:.1f} / "
                f"elw={payload.infra.elw_bps:.1f}"
            ),
            status=(
                "warning"
                if payload.infra.realized_cost_bps > payload.infra.expected_cost_bps
                else "healthy"
            ),
        ),
        DashboardCard(
            key="execution_fills",
            label="Fills",
            value=(
                f"partial={payload.infra.partial_fill_count} / "
                f"latency_p95={payload.infra.fill_latency_ms_p95}ms"
            ),
            status="warning" if payload.infra.partial_fill_count > 0 else "healthy",
        ),
        DashboardCard(
            key="execution_reconciliation",
            label="Reconciliation",
            value=str(payload.infra.reconciliation_alert_count),
            status=(
                "warning"
                if payload.infra.reconciliation_alert_count > 0
                else "healthy"
            ),
            detail="execution alert count",
        ),
        DashboardCard(
            key="execution_no_trade_bridge",
            label="No-trade bridge",
            value=(
                f"sel={payload.execution_no_trade_bridge.selection_status} / "
                f"loaded={'yes' if payload.execution_no_trade_bridge.loaded else 'no'}"
            ),
            status=payload.execution_no_trade_bridge.status,
            detail=(
                f"cfg={'yes' if payload.execution_no_trade_bridge.configured else 'no'} / "
                f"binding={'yes' if payload.execution_no_trade_bridge.binding_present else 'no'} / "
                f"snapshot={payload.execution_no_trade_bridge.current_snapshot_id or 'none'} / "
                f"lkg={payload.execution_no_trade_bridge.last_known_good_snapshot_id or 'none'}"
                + (
                    f" / ref={payload.execution_no_trade_bridge.compiled_plan_ref}"
                    if payload.execution_no_trade_bridge.compiled_plan_ref
                    else ""
                )
                + (
                    f" / err={payload.execution_no_trade_bridge.error_type}"
                    if payload.execution_no_trade_bridge.error_type
                    else ""
                )
            ),
        ),
    )


def _infra_cards(payload: TechnicalDashboardPayload) -> tuple[DashboardCard, ...]:
    return (
        DashboardCard(
            key="infra_queue",
            label="Queue",
            value=(
                f"backlog={payload.infra.queue_backlog} / "
                f"hwm={payload.infra.backlog_high_water_mark} / "
                f"drop={payload.infra.drop_rate_pct:.1f}%"
            ),
            status=(
                "warning"
                if payload.infra.queue_backlog > 0 or payload.infra.drop_rate_pct > 0.0
                else "healthy"
            ),
        ),
        DashboardCard(
            key="infra_recovery",
            label="Recovery",
            value=(
                f"reconnect={payload.infra.reconnect_count} / "
                f"retry={payload.infra.recovery_retry_count} / "
                f"stale_spikes={payload.infra.stale_spike_count}"
            ),
            status=(
                "warning"
                if payload.infra.reconnect_count > 0
                or payload.infra.recovery_retry_count > 0
                or payload.infra.stale_spike_count > 0
                else "healthy"
            ),
            detail=_join(payload.infra.stale_pairs, empty="No stale pair"),
        ),
        DashboardCard(
            key="infra_losses",
            label="Losses / Kill",
            value=(
                f"dtr={payload.infra.dtr_loss_count} / "
                f"log={payload.infra.log_loss_count} / "
                f"kill={'on' if payload.infra.kill_switch_active else 'off'}"
            ),
            status="critical" if payload.infra.kill_switch_active else "warning" if (
                payload.infra.dtr_loss_count > 0 or payload.infra.log_loss_count > 0
            ) else "healthy",
        ),
    )


def _account_user_data_section(payload: TechnicalDashboardPayload) -> DashboardSection:
    account = payload.account_user_data
    if account.authenticated:
        auth_value = "authenticated"
    elif account.summary_ref:
        auth_value = "not_authenticated"
    else:
        auth_value = "not_configured"

    event_types = _join(account.event_types, empty="No account event observed")
    pair_scope = _join(account.pair_scope, empty="No market pair scope recorded")
    endpoint = account.endpoint or "No authenticated endpoint recorded"
    return DashboardSection(
        title="Account / User Data",
        cards=(
            DashboardCard(
                key="account_user_data_auth",
                label="Authentication",
                value=auth_value,
                status=account.status,
                detail=(
                    f"session={account.session_date or 'n/a'} / "
                    f"mode={account.acquisition_mode or 'n/a'} / "
                    f"endpoint={endpoint}"
                ),
            ),
            DashboardCard(
                key="account_user_data_subscription",
                label="Subscription",
                value=(
                    f"id={account.subscription_id if account.subscription_id is not None else 'none'} / "
                    f"events={account.event_count}"
                ),
                status="healthy" if account.authenticated else account.status,
                detail=event_types,
            ),
            DashboardCard(
                key="account_user_data_scope",
                label="Scope",
                value=f"pairs={len(account.pair_scope)} / event_types={len(account.event_types)}",
                status="info" if account.pair_scope else account.status,
                detail=pair_scope,
            ),
            DashboardCard(
                key="account_user_data_artifacts",
                label="Artifacts",
                value="available" if account.summary_ref else "missing",
                status=("healthy" if account.summary_ref else account.status),
                detail=account.detail,
            ),
        ),
    )


def build_technical_dashboard_view(payload: TechnicalDashboardPayload) -> LightDashboardView:
    """Project normalized monitoring truth into the locked Build-10 UI surface."""

    sections = (
        DashboardSection(
            title="System",
            cards=(
                DashboardCard(
                    key="headline_status",
                    label="Headline",
                    value=payload.system.headline_status,
                    status=payload.system.headline_status,
                    detail=f"{payload.alerts.active_alert_count} active alert(s)",
                ),
                DashboardCard(
                    key="runtime_mode",
                    label="Runtime",
                    value=payload.runtime_mode.value,
                    status="info",
                    detail=f"profile={payload.profile.value}",
                ),
                DashboardCard(
                    key="active_modules",
                    label="Active Modules",
                    value=str(len(payload.system.active_modules)),
                    status="healthy" if payload.system.active_modules else "planned",
                    detail=_join(payload.system.active_modules, empty="No active modules declared"),
                ),
                _engine_card(payload),
                DashboardCard(
                    key="governed_extensions",
                    label="Governed Extensions",
                    value=(
                        f"9X={payload.system.build9x_status} / "
                        f"shadow={payload.system.shadow_status} / "
                        f"micro={payload.system.micro_live_status} / "
                        f"live={payload.system.live_light_status} / "
                        f"b14={payload.system.build14_status} / "
                        f"replay={payload.system.replay_import_status}"
                    ),
                    status=(
                        "critical"
                        if "critical" in {
                            payload.system.build9x_status,
                            payload.system.shadow_status,
                            payload.system.micro_live_status,
                            payload.system.live_light_status,
                            payload.system.build14_status,
                            payload.system.replay_import_status,
                        }
                        else "warning"
                        if "warning" in {
                            payload.system.build9x_status,
                            payload.system.shadow_status,
                            payload.system.micro_live_status,
                            payload.system.live_light_status,
                            payload.system.build14_status,
                            payload.system.replay_import_status,
                        }
                        else "info"
                    ),
                    detail=payload.system.governed_extensions_detail,
                ),
            ),
        ),
        DashboardSection(
            title="Portfolio",
            cards=(
                DashboardCard(
                    key="capital_deployed",
                    label="Capital Deployed",
                    value=f"{payload.portfolio.capital_deployed_usdt:.2f}",
                    status="info",
                    detail=f"opportunities={payload.portfolio.allocated_opportunities}",
                ),
                DashboardCard(
                    key="capacity_usage",
                    label="Capacity Usage",
                    value=(
                        f"gross={payload.portfolio.gross_capacity_used_pct:.1f}% / "
                        f"loss={payload.portfolio.loss_capacity_used_pct:.1f}%"
                    ),
                    status=(
                        "warning"
                        if payload.portfolio.loss_capacity_used_pct >= 25.0
                        else "healthy"
                    ),
                    detail=f"beta={payload.portfolio.beta_utilization:.2f}",
                ),
                DashboardCard(
                    key="ce_net",
                    label="CE Net",
                    value=f"{payload.portfolio.ce_net:.6f}",
                    status="healthy" if payload.portfolio.ce_net >= 0 else "warning",
                ),
            ),
        ),
        DashboardSection(
            title="Pairs",
            cards=_pair_cards(payload),
        ),
        DashboardSection(
            title="Engines",
            cards=_engine_cards(payload),
        ),
        DashboardSection(
            title="Engine Judgement",
            cards=_engine_judgment_cards(payload),
        ),
        DashboardSection(
            title="Risk",
            cards=_risk_cards(payload),
        ),
        DashboardSection(
            title="Execution",
            cards=_execution_cards(payload),
        ),
        DashboardSection(
            title="Data & Infra",
            cards=_infra_cards(payload),
        ),
        _account_user_data_section(payload),
        DashboardSection(
            title="Build-9 Meta",
            cards=(
                DashboardCard(
                    key="dtr_summary",
                    label="DTR Summary",
                    value=f"coverage={payload.build9_meta.dtr_coverage:.2%}",
                    status=payload.build9_meta.dtr_status,
                    detail=f"stale_pairs={payload.alerts.stale_pair_count}",
                ),
                DashboardCard(
                    key="cra_summary",
                    label="CRA Summary",
                    value=f"sterilization={payload.build9_meta.cra_sterilization_rate:.2%}",
                    status=payload.build9_meta.cra_status,
                    detail=f"alerts={payload.build9_meta.cra_alert_count}",
                ),
                DashboardCard(
                    key="break_even_summary",
                    label="Break-even",
                    value=payload.build9_meta.break_even_state,
                    status=payload.build9_meta.break_even_status,
                    detail=_join(
                        payload.build9_meta.break_even_drift_scopes,
                        empty="No drift scope",
                    ),
                ),
                DashboardCard(
                    key="edge_summary",
                    label="Edge Summary",
                    value=(
                        f"credible={payload.build9_meta.edge_credible_count} / "
                        f"degraded={payload.build9_meta.edge_degraded_count} / "
                        f"surveillance={payload.build9_meta.edge_surveillance_count}"
                    ),
                    status=payload.build9_meta.edge_status,
                ),
            ),
        ),
        DashboardSection(
            title="Build-9X",
            cards=(
                DashboardCard(
                    key="diagnostics_recent",
                    label="Diagnostics",
                    value=str(payload.build9x.diagnostics_count),
                    status=payload.build9x.status,
                    detail=payload.build9x.diagnostics_summary,
                ),
                DashboardCard(
                    key="hypotheses_open",
                    label="Open Hypotheses",
                    value=str(payload.build9x.open_hypotheses),
                    status=(
                        "warning"
                        if payload.build9x.open_hypotheses > 0
                        else "info"
                        if payload.build9x.status != "planned"
                        else "planned"
                    ),
                    detail=f"total={payload.build9x.total_hypotheses}",
                ),
                DashboardCard(
                    key="near_miss_candidates",
                    label="Near Miss / Candidates",
                    value=(
                        f"near_miss={payload.build9x.near_miss_count} / "
                        f"replay={payload.build9x.replay_candidate_count}"
                    ),
                    status=(
                        "warning"
                        if payload.build9x.near_miss_count > 0
                        or payload.build9x.replay_candidate_count > 0
                        else "info"
                        if payload.build9x.status != "planned"
                        else "planned"
                    ),
                ),
                DashboardCard(
                    key="enrichment_mapping",
                    label="Enrichment Mapping",
                    value=(
                        f"mapped={payload.build9x.enrichment_hypothesis_count} / "
                        f"replay={payload.build9x.expected_replay_evidence_count} / "
                        f"shadow={payload.build9x.expected_shadow_evidence_count}"
                    ),
                    status=(
                        "warning"
                        if payload.build9x.enrichment_hypothesis_count > 0
                        else "info"
                        if payload.build9x.status != "planned"
                        else "planned"
                    ),
                    detail=(
                        f"{payload.build9x.enrichment_summary} / "
                        f"family={payload.build9x.latest_enrichment_signal_family or 'n/a'}"
                    ),
                ),
                DashboardCard(
                    key="memory_review",
                    label="Memory / Review",
                    value=(
                        f"records={payload.build9x.memory_record_count} / "
                        f"export={'ready' if payload.build9x.review_export_ready else 'none'}"
                    ),
                    status=(
                        "healthy"
                        if payload.build9x.review_export_ready
                        else "info"
                        if payload.build9x.memory_record_count > 0
                        else "planned"
                    ),
                    detail=payload.build9x.latest_memory_summary,
                ),
                DashboardCard(
                    key="capacity_backpressure",
                    label="Capacity / Backpressure",
                    value=(
                        f"queue={payload.build9x.learning_queue_depth} / "
                        f"mode={payload.build9x.learning_capture_mode}"
                    ),
                    status=(
                        "critical"
                        if payload.build9x.review_blocked_due_to_incomplete_data
                        else "warning"
                        if payload.build9x.learning_backlog_state != "normal"
                        or payload.build9x.learning_backpressure_active
                        else "healthy"
                        if payload.build9x.status != "planned"
                        else "planned"
                    ),
                    detail=(
                        f"backlog={payload.build9x.learning_backlog_state} / "
                        f"oldest={payload.build9x.learning_queue_oldest_age_ms}ms / "
                        f"unprocessed={payload.build9x.learning_unprocessed_items_count}"
                    ),
                ),
                DashboardCard(
                    key="worker_budget",
                    label="Worker Budget",
                    value=(
                        f"cpu={payload.build9x.learning_worker_cpu_pct:.1f}% / "
                        f"rss={payload.build9x.learning_worker_rss_mb:.1f}MB"
                    ),
                    status=(
                        "critical"
                        if payload.build9x.learning_log_loss_total > 0
                        else "warning"
                        if payload.build9x.learning_export_failures_total > 0
                        or payload.build9x.learning_write_latency_ms > 0.0
                        else "healthy"
                        if payload.build9x.status != "planned"
                        else "planned"
                    ),
                    detail=(
                        f"write={payload.build9x.learning_write_latency_ms:.1f}ms / "
                        f"export_fail={payload.build9x.learning_export_failures_total} / "
                        f"log_loss={payload.build9x.learning_log_loss_total}"
                    ),
                ),
            ),
        ),
        DashboardSection(
            title="Build-11 Shadow",
            cards=(
                DashboardCard(
                    key="shadow_run_state",
                    label="Run State",
                    value=payload.shadow.run_state,
                    status=payload.shadow.status,
                    detail=(
                        f"truth={payload.shadow.truth_set_ref or 'n/a'} / "
                        f"validation={payload.shadow.validation_set_ref or 'n/a'}"
                    ),
                ),
                DashboardCard(
                    key="shadow_verdict",
                    label="Gating Verdict",
                    value=payload.shadow.verdict,
                    status=payload.shadow.status,
                    detail=(
                        "manual review required"
                        if payload.shadow.manual_review_required
                        else "manual review not required"
                    ),
                ),
                DashboardCard(
                    key="shadow_divergences",
                    label="Divergences",
                    value=(
                        f"blocking={payload.shadow.blocking_comparison_count} / "
                        f"divergent={payload.shadow.divergent_comparison_count} / "
                        f"total={payload.shadow.total_comparison_count}"
                    ),
                    status=(
                        "critical"
                        if payload.shadow.blocking_comparison_count > 0
                        else "warning"
                        if payload.shadow.divergent_comparison_count > 0
                        else payload.shadow.status
                    ),
                ),
                DashboardCard(
                    key="shadow_candidate_state",
                    label="Candidate State",
                    value=(
                        f"diagnostics={payload.shadow.build9x_diagnostics_count} / "
                        f"hypotheses={payload.shadow.open_hypotheses} / "
                        f"replay={payload.shadow.replay_candidate_count}"
                    ),
                    status=(
                        "warning"
                        if payload.shadow.manual_review_required
                        else "info"
                        if payload.shadow.status != "planned"
                        else "planned"
                    ),
                    detail=(
                        "review export ready"
                        if payload.shadow.review_export_ready
                        else "review export missing"
                    ),
                ),
                DashboardCard(
                    key="shadow_import_lineage",
                    label="Import Lineage",
                    value=payload.shadow.import_lineage_version,
                    status=(
                        "healthy"
                        if payload.shadow.import_lineage_version not in {"", "n/a"}
                        else "critical"
                        if payload.shadow.status != "planned"
                        else "planned"
                    ),
                    detail=payload.shadow.import_artifact_id or "No import artifact id",
                ),
                DashboardCard(
                    key="shadow_blocking_reasons",
                    label="Blocking Reasons",
                    value=str(len(payload.shadow.blocking_reasons)),
                    status=(
                        "critical"
                        if payload.shadow.blocking_reasons
                        else "healthy"
                        if payload.shadow.status == "healthy"
                        else payload.shadow.status
                    ),
                    detail=_join(payload.shadow.blocking_reasons, empty="No blocking reason"),
                ),
            ),
        ),
        DashboardSection(
            title="Build-12 Micro-live",
            cards=(
                DashboardCard(
                    key="micro_live_run_state",
                    label="Run State",
                    value=payload.micro_live.run_state,
                    status=payload.micro_live.status,
                    detail=f"shadow_run={payload.micro_live.shadow_run_id or 'n/a'}",
                ),
                DashboardCard(
                    key="micro_live_verdict",
                    label="Probe Verdict",
                    value=payload.micro_live.verdict,
                    status=payload.micro_live.status,
                    detail=f"shadow_verdict={payload.micro_live.shadow_verdict}",
                ),
                DashboardCard(
                    key="micro_live_budget",
                    label="Budget",
                    value=(
                        f"approved={payload.micro_live.approved_total_notional_usdt:.2f} / "
                        f"pair={payload.micro_live.approved_pair_notional_usdt:.2f}"
                    ),
                    status=payload.micro_live.status,
                    detail=f"requested={payload.micro_live.requested_total_notional_usdt:.2f}",
                ),
                DashboardCard(
                    key="micro_live_surface",
                    label="Probe Surface",
                    value=(
                        f"pairs={len(payload.micro_live.planned_pairs)} / "
                        f"engines={len(payload.micro_live.planned_engines)} / "
                        f"orders={payload.micro_live.order_probe_limit}"
                    ),
                    status=(
                        "info"
                        if payload.micro_live.planned_pairs or payload.micro_live.planned_engines
                        else payload.micro_live.status
                    ),
                    detail=_join(payload.micro_live.planned_pairs, empty="No probe surface planned"),
                ),
                DashboardCard(
                    key="micro_live_guardrails",
                    label="Guardrails",
                    value=(
                        f"obs={'ready' if payload.micro_live.observability_ready else 'missing'} / "
                        f"halt={'ready' if payload.micro_live.halt_ready else 'missing'} / "
                        f"onboarding={'ready' if payload.micro_live.onboarding_ready else 'missing'}"
                    ),
                    status=(
                        "healthy"
                        if payload.micro_live.observability_ready
                        and payload.micro_live.halt_ready
                        and payload.micro_live.onboarding_ready
                        else "critical"
                        if payload.micro_live.status != "planned"
                        else "planned"
                    ),
                    detail=payload.micro_live.import_lineage_version,
                ),
                DashboardCard(
                    key="micro_live_safing_request",
                    label="Safing Request",
                    value=(
                        f"{payload.micro_live.operator_safing_action}"
                        + (
                            f" -> {payload.micro_live.operator_safing_target_runtime_mode}"
                            if payload.micro_live.operator_safing_target_runtime_mode
                            else ""
                        )
                        if payload.micro_live.operator_safing_action
                        else "none"
                    ),
                    status=(
                        "critical"
                        if payload.micro_live.operator_safing_action == "set_halted"
                        else "warning"
                        if payload.micro_live.operator_safing_action
                        else "info"
                    ),
                    detail=(
                        payload.micro_live.operator_safing_reason
                        or "No manual safing request projected"
                    ),
                ),
                DashboardCard(
                    key="micro_live_blocking_reasons",
                    label="Blocking Reasons",
                    value=str(len(payload.micro_live.blocking_reasons)),
                    status=(
                        "critical"
                        if payload.micro_live.blocking_reasons
                        else "healthy"
                        if payload.micro_live.status == "healthy"
                        else payload.micro_live.status
                    ),
                    detail=_join(payload.micro_live.blocking_reasons, empty="No blocking reason"),
                ),
            ),
        ),
        DashboardSection(
            title="Build-13 Live",
            cards=(
                DashboardCard(
                    key="live_light_run_state",
                    label="Run State",
                    value=payload.live_light.run_state,
                    status=payload.live_light.status,
                    detail=f"micro_live_run={payload.live_light.micro_live_run_id or 'n/a'}",
                ),
                DashboardCard(
                    key="live_light_verdict",
                    label="Execution Verdict",
                    value=payload.live_light.verdict,
                    status=payload.live_light.status,
                    detail=f"micro_live_verdict={payload.live_light.micro_live_verdict}",
                ),
                DashboardCard(
                    key="live_light_budget",
                    label="Budget",
                    value=(
                        f"approved={payload.live_light.approved_total_notional_usdt:.2f} / "
                        f"pair={payload.live_light.approved_pair_notional_usdt:.2f}"
                    ),
                    status=payload.live_light.status,
                    detail=(
                        f"requested={payload.live_light.requested_total_notional_usdt:.2f} / "
                        f"build14={payload.live_light.build14_action}@{payload.live_light.build14_recommended_budget_factor:.2f}"
                    ),
                ),
                DashboardCard(
                    key="live_light_surface",
                    label="Execution Surface",
                    value=(
                        f"pairs={len(payload.live_light.planned_pairs)} / "
                        f"engines={len(payload.live_light.planned_engines)} / "
                        f"orders={payload.live_light.execution_order_limit}"
                    ),
                    status=(
                        "info"
                        if payload.live_light.planned_pairs or payload.live_light.planned_engines
                        else payload.live_light.status
                    ),
                    detail=_join(payload.live_light.planned_pairs, empty="No execution surface planned"),
                ),
                DashboardCard(
                    key="live_light_readiness",
                    label="Readiness",
                    value=(
                        f"obs={'ready' if payload.live_light.observability_ready else 'missing'} / "
                        f"halt={'ready' if payload.live_light.halt_ready else 'missing'} / "
                        f"exec={'ready' if payload.live_light.execution_ready else 'missing'} / "
                        f"broker={'ready' if payload.live_light.broker_ready else 'missing'} / "
                        f"exchange={'ready' if payload.live_light.exchange_ready else 'missing'}"
                    ),
                    status=(
                        "healthy"
                        if payload.live_light.observability_ready
                        and payload.live_light.halt_ready
                        and payload.live_light.execution_ready
                        and payload.live_light.broker_ready
                        and payload.live_light.exchange_ready
                        else "critical"
                        if payload.live_light.status != "planned"
                        else "planned"
                    ),
                    detail=payload.live_light.build14_summary or payload.live_light.import_lineage_version,
                ),
                DashboardCard(
                    key="live_light_safing_request",
                    label="Safing Request",
                    value=(
                        f"{payload.live_light.operator_safing_action}"
                        + (
                            f" -> {payload.live_light.operator_safing_target_runtime_mode}"
                            if payload.live_light.operator_safing_target_runtime_mode
                            else ""
                        )
                        if payload.live_light.operator_safing_action
                        else "none"
                    ),
                    status=(
                        "critical"
                        if payload.live_light.operator_safing_action == "set_halted"
                        else "warning"
                        if payload.live_light.operator_safing_action
                        else "info"
                    ),
                    detail=(
                        payload.live_light.operator_safing_reason
                        or "No manual safing request projected"
                    ),
                ),
                DashboardCard(
                    key="live_light_blocking_reasons",
                    label="Blocking Reasons",
                    value=str(len(payload.live_light.blocking_reasons)),
                    status=(
                        "critical"
                        if payload.live_light.blocking_reasons
                        else "healthy"
                        if payload.live_light.status == "healthy"
                        else payload.live_light.status
                    ),
                    detail=_join(payload.live_light.blocking_reasons, empty="No blocking reason"),
                ),
            ),
        ),
        DashboardSection(
            title="Build-14 Enablers",
            cards=(
                DashboardCard(
                    key="build14_mode",
                    label="Mode",
                    value=f"{payload.build14.influence_mode} / {payload.build14.action}",
                    status=payload.build14.status,
                    detail=f"severity={payload.build14.severity}",
                ),
                DashboardCard(
                    key="build14_readers",
                    label="Readers",
                    value=(
                        f"count={len(payload.build14.reader_projections)} / "
                        f"toxicity={payload.build14.market_toxicity_status} ({payload.build14.market_toxicity_value:.2f}) / "
                        f"fragility={payload.build14.execution_fragility_status} ({payload.build14.execution_fragility_value:.2f})"
                    ),
                    status=(
                        "critical"
                        if payload.build14.severity == "critical"
                        else "warning"
                        if payload.build14.severity == "elevated"
                        else payload.build14.status
                    ),
                    detail=(
                        f"{payload.build14.summary} / {_build14_readers_summary(payload)}"
                        if payload.build14.reader_projections
                        else payload.build14.summary
                    ),
                ),
                DashboardCard(
                    key="build14_candidate_effect",
                    label="Candidate Effect",
                    value=payload.build14.candidate_effect,
                    status=payload.build14.status,
                    detail=(
                        f"penalty={payload.build14.confidence_penalty_weight:.2f} / "
                        f"budget_factor={payload.build14.recommended_budget_factor:.2f}"
                    ),
                ),
                DashboardCard(
                    key="build14_guardrails",
                    label="Guardrails",
                    value=(
                        "review_only"
                        if payload.build14.requires_manual_review
                        else "bounded_modulation"
                        if payload.build14.influence_mode == "limited_influence"
                        else "shadow_enabled"
                        if payload.build14.influence_mode == "shadow_enabled"
                        else "read_only"
                    ),
                    status=(
                        "warning"
                        if payload.build14.requires_manual_review
                        else "healthy"
                        if payload.build14.status in {"healthy", "info"}
                        else payload.build14.status
                    ),
                    detail=_join(payload.build14.reason_codes, empty="No Build-14 reason code"),
                ),
            )
            + _build14_reader_cards(payload),
        ),
        _operator_controls_section(payload),
        DashboardSection(
            title="Replay & Import",
            cards=(
                DashboardCard(
                    key="artifact_manifest",
                    label="Artifact Manifest",
                    value=payload.replay_import.artifact_id,
                    status=payload.replay_import.status,
                    detail=payload.replay_import.artifact_kind,
                ),
                DashboardCard(
                    key="lineage_version",
                    label="Lineage",
                    value=payload.replay_import.lineage_version,
                    status="info" if payload.replay_import.artifact_id != "none" else "planned",
                    detail=payload.replay_import.lifecycle_state,
                ),
                DashboardCard(
                    key="validation_status",
                    label="Validation",
                    value=payload.replay_import.validation_status,
                    status=(
                        "healthy"
                        if payload.replay_import.validation_status == "accepted"
                        else "warning"
                        if payload.replay_import.validation_status != "not_run"
                        else "planned"
                    ),
                    detail=payload.replay_import.review_state,
                ),
                DashboardCard(
                    key="validation_reasons",
                    label="Validation Reasons",
                    value=str(len(payload.replay_import.rejection_reasons)),
                    status=(
                        "warning"
                        if payload.replay_import.rejection_reasons
                        else "healthy"
                        if payload.replay_import.validation_status == "accepted"
                        else "planned"
                    ),
                    detail=_join(
                        payload.replay_import.rejection_reasons,
                        empty="No validation rejection",
                    ),
                ),
                DashboardCard(
                    key="compatibility_policy",
                    label="Compatibility Policy",
                    value=payload.replay_import.compatibility_status,
                    status=_replay_compatibility_card_status(payload),
                    detail=_replay_compatibility_card_detail(payload),
                ),
                DashboardCard(
                    key="signature_policy",
                    label="Signature Policy",
                    value=payload.replay_import.signature_check_status,
                    status=_replay_signature_card_status(payload),
                    detail=_replay_signature_card_detail(payload),
                ),
                DashboardCard(
                    key="conflict_policy",
                    label="Conflict Policy",
                    value=payload.replay_import.conflict_resolution_mode or "not_configured",
                    status=_replay_conflict_card_status(payload),
                    detail=_replay_conflict_card_detail(payload),
                ),
                DashboardCard(
                    key="registry_policy",
                    label="Registry Policy",
                    value=payload.replay_import.registry_atomicity_mode or "not_configured",
                    status=_replay_registry_card_status(payload),
                    detail=_replay_registry_card_detail(payload),
                ),
            ),
        ),
        DashboardSection(
            title="Alerts",
            cards=(
                DashboardCard(
                    key="active_alerts",
                    label="Active Alerts",
                    value=str(payload.alerts.active_alert_count),
                    status=payload.alerts.headline_status,
                    detail=_join(payload.alerts.alert_ids, empty="No active alert"),
                ),
                DashboardCard(
                    key="backlog_stale",
                    label="Backlog / Stale",
                    value=(
                        f"backlog={payload.alerts.queue_backlog} / "
                        f"stale={payload.alerts.stale_pair_count}"
                    ),
                    status=payload.alerts.backlog_stale_status,
                    detail=_join(payload.alerts.stale_pairs, empty="No stale pair"),
                ),
                DashboardCard(
                    key="infra_guardrails",
                    label="Infra Guardrails",
                    value=(
                        f"hwm={payload.alerts.backlog_high_water_mark} / "
                        f"drop={payload.alerts.drop_rate_pct:.1f}% / "
                        f"spikes={payload.alerts.stale_spike_count}"
                    ),
                    status=(
                        "critical"
                        if payload.alerts.kill_switch_active
                        else "warning"
                        if (
                            payload.alerts.backlog_high_water_mark > payload.alerts.queue_backlog
                            or payload.alerts.drop_rate_pct > 5.0
                            or payload.alerts.recovery_retry_count > 0
                            or payload.alerts.stale_spike_count > 0
                        )
                        else "healthy"
                    ),
                    detail=(
                        f"retry={payload.alerts.recovery_retry_count} / "
                        f"kill={'active' if payload.alerts.kill_switch_active else 'inactive'}"
                    ),
                ),
                DashboardCard(
                    key="loss_drift",
                    label="Loss / Drift",
                    value=(
                        f"dtr={payload.alerts.dtr_loss_count} / "
                        f"log={payload.alerts.log_loss_count} / "
                        f"drift={payload.alerts.break_even_drift_scope_count}"
                    ),
                    status=payload.alerts.loss_drift_status,
                ),
                DashboardCard(
                    key="observability_surface",
                    label="Observability",
                    value=(
                        f"persisted={len(payload.alerts.persisted_metric_names)} / "
                        f"volatile={len(payload.alerts.volatile_metric_names)}"
                    ),
                    status=(
                        "warning"
                        if payload.alerts.volatile_metric_names
                        and (
                            payload.alerts.backlog_high_water_mark > 0
                            or payload.alerts.drop_rate_pct > 0.0
                            or payload.alerts.stale_spike_count > 0
                            or payload.alerts.recovery_retry_count > 0
                            or payload.alerts.kill_switch_active
                        )
                        else "info"
                    ),
                    detail=(
                        "volatile: "
                        + _join(payload.alerts.volatile_metric_names, empty="none")
                    ),
                ),
                DashboardCard(
                    key="operator_events",
                    label="Operator Events",
                    value=str(payload.alerts.operator_runtime.event_count),
                    status=(
                        "warning"
                        if payload.alerts.operator_runtime.event_count > 1
                        else "info"
                    ),
                    detail=(
                        payload.alerts.operator_runtime.latest_event_message
                        or "No operator event projected"
                    ),
                ),
                DashboardCard(
                    key="operator_notifications",
                    label="Operator Notifications",
                    value=(
                        f"pending={payload.alerts.operator_runtime.pending_notification_count} / "
                        f"ack={payload.alerts.operator_runtime.acknowledged_notification_count}"
                    ),
                    status=(
                        "critical"
                        if payload.alerts.operator_runtime.pending_notification_count > 0
                        and payload.alerts.headline_status == "critical"
                        else "warning"
                        if payload.alerts.operator_runtime.pending_notification_count > 0
                        else "healthy"
                        if payload.alerts.operator_runtime.acknowledged_notification_count > 0
                        else "info"
                    ),
                    detail=_join(
                        payload.alerts.operator_runtime.pending_notification_alert_ids,
                        empty=(
                            f"latest ack: {payload.alerts.operator_runtime.latest_acknowledged_alert_id}"
                            if payload.alerts.operator_runtime.latest_acknowledged_alert_id
                            else "No notification projected"
                        ),
                    ),
                ),
            ),
        ),
    )

    return LightDashboardView(
        timestamp_ms=payload.timestamp_ms,
        correlation_id=payload.correlation_id,
        profile=payload.profile,
        runtime_mode=payload.runtime_mode,
        sections=sections,
        future_panels=payload.future_panels,
    )


__all__ = [
    "build_technical_dashboard_view",
]
