"""Tests for the normalized Build-10 technical supervision view."""

from __future__ import annotations

from interface_contracts import HookId, PairHealthLevel, ProfileId, RuntimeMode
from meta import (
    build_break_even_report,
    build_cra_report,
    build_dtr_summary,
    build_edge_report,
)
from meta_minimal.break_even_dashboard.motor_pair_break_even_view import BreakEvenView
from meta_minimal.cra_monitor.cra_alert_builder import CRAAlert, CRAAlertLevel
from meta_minimal.cra_monitor.sterilization_classifier import (
    SterilizationClass,
    SterilizationResult,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import (
    EdgeClassification,
    EdgeStatus,
)
from monitoring import (
    AccountUserDataProjection,
    Build14ReaderProjection,
    Build14Projection,
    Build9XProjection,
    EngineJudgmentCard,
    EngineJudgmentProjection,
    ExecutionNoTradeBridgeProjection,
    ExecutionRuntimeProjectionBridgeProjection,
    LiveLightProjection,
    MicroLiveProjection,
    OperatorRuntimeProjection,
    RegimeLiteSafingProjection,
    ReplayImportProjection,
    RuntimeHookBridgeProjection,
    ShadowProjection,
    build_technical_dashboard_payload,
    collect_engine_metrics,
    collect_infra_metrics,
    collect_meta_metrics,
    collect_monitoring_snapshot,
    collect_pair_metrics,
    collect_portfolio_metrics,
)
from ui import build_technical_dashboard_view


def _snapshot(**overrides):
    dtr_summary = build_dtr_summary(
        (
            build_dtr(
                dtr_id="dtr-1",
                pair="BTCUSDT",
                engine_id="engine_a",
                decision_state=DecisionState.SELECTED,
                timestamp=1000.0,
            ),
        ),
        total_opportunities=2,
    )
    cra_report = build_cra_report(
        (
            SterilizationResult(
                pair="BTCUSDT",
                engine_id="engine_a",
                classification=SterilizationClass.PHANTOM_PROBABLE,
                multiplier=0.5,
                phantom_risk_score=0.8,
            ),
        ),
        alerts=(
            CRAAlert(
                scope="engine_a",
                sterilization_rate=1.0,
                total_trades=1,
                sterilized_count=1,
                alert_level=CRAAlertLevel.WARNING,
                dominant_cause="spread_drift",
            ),
        ),
    )
    break_even_report = build_break_even_report(
        (
            BreakEvenView(
                scope="engine_b",
                sample_size=10,
                mean_realized_cost=0.0015,
                mean_expected_cost=0.0010,
                mean_cost_drift=0.0005,
                profitable_rate=0.4,
            ),
        )
    )
    edge_report = build_edge_report(
        (
            EdgeClassification(
                scope="engine_a",
                status=EdgeStatus.CREDIBLE,
                mean_net_return=0.002,
                standard_error=0.0003,
                sample_size=20,
                sharpe_per_trade=0.3,
                mean_cost_p90=0.001,
                ce_observed=0.0005,
                cluster_utilization=0.2,
            ),
            EdgeClassification(
                scope="engine_b",
                status=EdgeStatus.DEGRADED,
                mean_net_return=-0.001,
                standard_error=0.0004,
                sample_size=20,
                sharpe_per_trade=-0.1,
                mean_cost_p90=0.002,
                ce_observed=0.0,
                cluster_utilization=0.4,
            ),
        )
    )
    defaults = dict(
        correlation_id="corr-tech",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=2,
            gross_capacity_used_pct=35.0,
            loss_capacity_used_pct=8.0,
            beta_utilization=0.3,
            capital_deployed_usdt=1200.0,
            ce_net=0.0012,
        ),
        infra=collect_infra_metrics(queue_backlog=75, stale_pairs=("BTCUSDT",)),
        meta=collect_meta_metrics(
            dtr_summary,
            cra_report,
            break_even_report,
            edge_report,
            future_learning_diagnostics=2,
            future_learning_hypotheses=1,
        ),
        engines=(
            collect_engine_metrics(
                engine_id="engine_a",
                emitted_signals=2,
                net_edge_bps=12.0,
                expected_cost_bps=4.0,
                ce_expected=0.0007,
                scoring_penalized_score=1.2,
                scoring_ranking_score=0.8,
                scoring_final_size_multiplier=1.0,
                scoring_summary="features=momentum,flow / score_penalties=spread / size_penalties=none / selection=selected",
                risk_summary="risk=accept / no blocker triggered",
                scoring_reason_codes=("PEN_SPREAD", "SELECTION_SELECTED"),
                selection_outcome_code="selected",
                portfolio_verdict_code="compatible",
                risk_decision_severity="nominal",
                drawdown_state_code="accepted",
                physics_pressure_state="nominal",
                delta_confirmation=0.9,
                market_toxicity=0.2,
                spread_regime_penalty=0.1,
                competition_support=0.8,
                fragility_score=0.08,
                toxicity_score=0.14,
                execution_survivability_score=0.94,
                micro_friction_score=0.09,
            ),
            collect_engine_metrics(
                engine_id="engine_b",
                emitted_signals=1,
                net_edge_bps=4.0,
                expected_cost_bps=3.0,
                ce_expected=0.0002,
                scoring_penalized_score=0.3,
                scoring_ranking_score=0.1,
                scoring_final_size_multiplier=0.1,
                scoring_summary="features=flow / score_penalties=stale / size_penalties=size_stale / selection=rejected_ranking",
                risk_summary="risk=reduce_exposure / dominant=RISK_DRAWDOWN_REDUCE / category=drawdown_state / total=1",
                scoring_reason_codes=("PEN_STALE", "SIZE_SIZE_STALE", "SELECTION_REJECTED_RANKING"),
                risk_reason_codes=("RISK_DRAWDOWN_REDUCE",),
                selection_outcome_code="rejected_ranking",
                phantom_trade=True,
                phantom_reason_code="PHANTOM_RISK",
                risk_decision_severity="warning",
                drawdown_state_code="reduce_exposure",
                blocked_guard_count=1,
                stale=True,
                sweep_score=0.9,
                absorption_score=0.8,
                poc_reversion_score=0.7,
                false_breakout_score=0.4,
                execution_fragility=0.6,
                market_toxicity=0.7,
                spread_regime_penalty=0.5,
                physics_pressure_state="elevated",
                fragility_score=0.52,
                toxicity_score=0.63,
                execution_survivability_score=0.41,
                micro_friction_score=0.47,
            ),
        ),
        pairs=(
            collect_pair_metrics(
                pair="BTCUSDT",
                health=PairHealthLevel.STALE,
                freshness_ms=9000,
                backlog_depth=75,
            ),
        ),
    )
    defaults.update(overrides)
    return collect_monitoring_snapshot(**defaults)


def _build9x_projection() -> Build9XProjection:
    return Build9XProjection(
        status="warning",
        diagnostics_count=2,
        diagnostics_summary="Two governed issues detected",
        open_hypotheses=1,
        total_hypotheses=1,
        near_miss_count=1,
        replay_candidate_count=1,
        memory_record_count=1,
        latest_memory_summary="Stored governed review state",
        enrichment_hypothesis_count=1,
        latest_enrichment_target="meta_minimal.cra_monitor",
        latest_enrichment_signal_family="economics",
        expected_replay_evidence_count=2,
        expected_shadow_evidence_count=1,
        enrichment_summary="sterilization -> meta_minimal.cra_monitor",
        review_export_ready=True,
        review_export_ref="exports/review.md",
        learning_queue_depth=1200,
        learning_queue_oldest_age_ms=350,
        learning_worker_cpu_pct=8.5,
        learning_worker_rss_mb=180.0,
        learning_write_latency_ms=12.0,
        learning_export_failures_total=0,
        learning_log_loss_total=0,
        learning_unprocessed_items_count=0,
        learning_backlog_state="alert",
        learning_capture_mode="full_capture",
        learning_observability_reduced=False,
        learning_backpressure_active=False,
        review_blocked_due_to_incomplete_data=False,
        promotion_blocked_due_to_incomplete_data=False,
        learning_capacity_summary="queue=1200 / backlog=alert / mode=full_capture",
    )


def _accepted_replay_projection() -> ReplayImportProjection:
    return ReplayImportProjection(
        status="healthy",
        artifact_id="artifact-1",
        artifact_kind="review_packet",
        lineage_version="a.v2.1",
        lifecycle_state="exported",
        validation_status="accepted",
        review_state="pending",
        compatibility_status="supported",
        signature_check_status="trust_eligible",
        signature_key_id="lab_ed25519_2026_q2_k1",
        trusted_key_status="active",
        conflict_resolution_mode="no_trade_then_strictest",
        conflict_hard_veto_action="no_trade",
        conflict_score_aggregation_mode="bounded_sum_with_global_cap",
        conflict_size_reduce_mode="min_factor_wins",
        conflict_rank_adjust_mode="bounded_sum",
        conflict_additive_soft_boosts_allowed=True,
        conflict_additive_soft_reduces_allowed=True,
        registry_atomicity_mode="atomic_snapshot_swap",
        registry_concurrency_model="single_writer_multi_reader",
        registry_publish_requires_atomic_replace=True,
        registry_publish_requires_fsync=True,
        registry_rollback_to_last_known_good=True,
        rejection_reasons=(),
    )


def test_technical_dashboard_view_exposes_system_meta_build9x_and_replay_sections():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=(
            "interface_contracts",
            "manifest_registry",
            "meta",
            "meta_learning",
            "local_replay_runtime",
            "backtest_artifact_import",
            "monitoring",
            "ui",
        ),
        active_engines=("engine_a", "engine_b"),
        build9x_projection=_build9x_projection(),
        replay_projection=_accepted_replay_projection(),
    )

    view = build_technical_dashboard_view(payload)

    titles = {section.title for section in view.sections}
    assert titles == {
        "Build-10",
        "System",
        "Portfolio",
        "Pairs",
        "Engines",
        "Engine Judgement",
        "Risk",
        "Execution",
        "Data & Infra",
        "Account / User Data",
        "Build-9 Meta",
        "Build-9X",
        "Build-11 Shadow",
        "Build-12 Micro-live",
        "Build-13 Live",
        "Build-14 Enablers",
        "Artifact Hooks",
        "Operator Controls",
        "Replay & Import",
        "Alerts",
    }
    build10 = next(section for section in view.sections if section.title == "Build-10")
    assert next(card for card in build10.cards if card.key == "build10_state").value == "implemented"
    assert next(card for card in build10.cards if card.key == "build10_governed_rail").value == "light / shadow"
    governed = next(card for card in build10.cards if card.key == "build10_extensions")
    system = next(section for section in view.sections if section.title == "System")
    assert "9X=warning" in governed.value
    assert "micro=planned" in governed.value
    assert "live=planned" in governed.value
    assert "b14=planned" in governed.value
    build9x = next(section for section in view.sections if section.title == "Build-9X")
    assert next(card for card in build9x.cards if card.key == "diagnostics_recent").value == "2"
    assert next(card for card in build9x.cards if card.key == "hypotheses_open").value == "1"
    assert next(card for card in build9x.cards if card.key == "enrichment_mapping").value == (
        "mapped=1 / replay=2 / shadow=1"
    )
    assert next(card for card in build9x.cards if card.key == "enrichment_mapping").detail == (
        "sterilization -> meta_minimal.cra_monitor / family=economics"
    )
    assert next(card for card in build9x.cards if card.key == "capacity_backpressure").detail == (
        "backlog=alert / oldest=350ms / unprocessed=0"
    )
    assert next(card for card in build9x.cards if card.key == "worker_budget").value == "cpu=8.5% / rss=180.0MB"
    replay = next(section for section in view.sections if section.title == "Replay & Import")
    shadow = next(section for section in view.sections if section.title == "Build-11 Shadow")
    micro = next(section for section in view.sections if section.title == "Build-12 Micro-live")
    live = next(section for section in view.sections if section.title == "Build-13 Live")
    build14 = next(section for section in view.sections if section.title == "Build-14 Enablers")
    engine_judgment = next(section for section in view.sections if section.title == "Engine Judgement")
    pairs = next(section for section in view.sections if section.title == "Pairs")
    engines = next(section for section in view.sections if section.title == "Engines")
    risk = next(section for section in view.sections if section.title == "Risk")
    execution = next(section for section in view.sections if section.title == "Execution")
    infra = next(section for section in view.sections if section.title == "Data & Infra")
    account = next(section for section in view.sections if section.title == "Account / User Data")
    assert next(card for card in shadow.cards if card.key == "shadow_run_state").value == "not_run"
    assert next(card for card in micro.cards if card.key == "micro_live_run_state").value == "not_run"
    assert next(card for card in live.cards if card.key == "live_light_run_state").value == "not_run"
    assert next(card for card in replay.cards if card.key == "conflict_policy").value == "no_trade_then_strictest"

    assert "veto=no_trade" in next(
        card for card in replay.cards if card.key == "conflict_policy"
    ).detail
    assert next(card for card in replay.cards if card.key == "registry_policy").value == "atomic_snapshot_swap"
    assert "concurrency=single_writer_multi_reader" in next(
        card for card in replay.cards if card.key == "registry_policy"
    ).detail
    assert next(card for card in build14.cards if card.key == "build14_mode").value == "read_only / observe"
    assert next(card for card in build14.cards if card.key == "build14_readers").value.startswith("count=0 /")
    assert next(card for card in engine_judgment.cards if card.key == "engine_judgment_empty").status == "planned"
    assert next(card for card in pairs.cards if card.key == "pair_btcusdt").value == "stale / fresh=9000ms"
    assert next(card for card in engines.cards if card.key == "engine_engine_a").value == "signals=2 / edge=12.0"
    assert "scoring=features=momentum,flow" in next(
        card for card in engines.cards if card.key == "engine_engine_a"
    ).detail
    assert "penalized=1.20" in next(
        card for card in engines.cards if card.key == "engine_engine_a"
    ).detail
    assert "selection=selected" in next(
        card for card in engines.cards if card.key == "engine_engine_a"
    ).detail
    assert "score_codes=PEN_SPREAD,SELECTION_SELECTED" in next(
        card for card in engines.cards if card.key == "engine_engine_a"
    ).detail
    assert "physics=delta=0.90, toxicity=0.20, spread_penalty=0.10, competition=0.80" in next(
        card for card in engines.cards if card.key == "engine_engine_a"
    ).detail
    assert "fragility_score=0.08" in next(
        card for card in engines.cards if card.key == "engine_engine_a"
    ).detail
    assert "survivability=0.94" in next(
        card for card in engines.cards if card.key == "engine_engine_a"
    ).detail
    assert "phantom=PHANTOM_RISK" in next(
        card for card in engines.cards if card.key == "engine_engine_b"
    ).detail
    assert "blocked_guards=1" in next(
        card for card in engines.cards if card.key == "engine_engine_b"
    ).detail
    assert "drawdown=reduce_exposure" in next(
        card for card in engines.cards if card.key == "engine_engine_b"
    ).detail
    assert (
        "fragility=0.60, toxicity=0.70, spread_penalty=0.50, sweep=0.90, "
        "absorption=0.80, poc=0.70, false_breakout=0.40"
    ) in next(
        card for card in engines.cards if card.key == "engine_engine_b"
    ).detail
    assert "state=elevated" in next(
        card for card in engines.cards if card.key == "engine_engine_b"
    ).detail
    assert "micro_friction=0.47" in next(
        card for card in engines.cards if card.key == "engine_engine_b"
    ).detail
    assert next(card for card in risk.cards if card.key == "risk_exposure").value == "gross=35.0% / loss=8.0%"
    assert next(card for card in execution.cards if card.key == "execution_fills").value == "partial=0 / latency_p95=0ms"
    assert next(card for card in execution.cards if card.key == "execution_fills").detail == "signal_to_submit_p90=0ms"
    assert next(card for card in infra.cards if card.key == "infra_queue").value == "backlog=75 / hwm=75 / drop=0.0%"
    assert next(card for card in account.cards if card.key == "account_user_data_auth").value == "not_configured"
    assert next(card for card in account.cards if card.key == "account_user_data_artifacts").value == "missing"
    replay = next(section for section in view.sections if section.title == "Replay & Import")
    assert next(card for card in replay.cards if card.key == "artifact_manifest").value == "artifact-1"
    assert next(card for card in replay.cards if card.key == "validation_status").value == "accepted"
    assert next(card for card in replay.cards if card.key == "compatibility_policy").value == "supported"
    assert next(card for card in replay.cards if card.key == "compatibility_policy").status == "healthy"
    assert next(card for card in replay.cards if card.key == "signature_policy").value == "trust_eligible"
    assert next(card for card in replay.cards if card.key == "signature_policy").status == "healthy"


def test_technical_dashboard_view_reports_complete_live_governed_rail():
    payload = build_technical_dashboard_payload(
        _snapshot(
            profile=ProfileId.COMPLETE,
            runtime_mode=RuntimeMode.LIVE,
        ),
        active_modules=("monitoring", "ui", "protocols"),
        active_engines=("engine_a", "engine_b"),
    )

    view = build_technical_dashboard_view(payload)

    build10 = next(section for section in view.sections if section.title == "Build-10")
    assert next(card for card in build10.cards if card.key == "build10_governed_rail").value == (
        "complete / live"
    )
    system = next(section for section in view.sections if section.title == "System")
    assert any(
        card.key == "runtime_mode" and card.detail == "profile=complete"
        for card in system.cards
    )


def test_technical_dashboard_view_handles_empty_governed_state_cleanly():
    payload = build_technical_dashboard_payload(
        _snapshot(infra=collect_infra_metrics()),
        active_modules=("interface_contracts", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
    )

    view = build_technical_dashboard_view(payload)
    build9x = next(section for section in view.sections if section.title == "Build-9X")
    engine_judgment = next(section for section in view.sections if section.title == "Engine Judgement")
    shadow = next(section for section in view.sections if section.title == "Build-11 Shadow")
    micro = next(section for section in view.sections if section.title == "Build-12 Micro-live")
    live = next(section for section in view.sections if section.title == "Build-13 Live")
    build14 = next(section for section in view.sections if section.title == "Build-14 Enablers")
    account = next(section for section in view.sections if section.title == "Account / User Data")
    replay = next(section for section in view.sections if section.title == "Replay & Import")
    assert next(card for card in build9x.cards if card.key == "diagnostics_recent").value == "0"
    assert next(card for card in build9x.cards if card.key == "enrichment_mapping").status == "planned"
    assert next(card for card in build9x.cards if card.key == "memory_review").status == "planned"
    assert next(card for card in build9x.cards if card.key == "capacity_backpressure").status == "planned"
    assert next(card for card in build9x.cards if card.key == "worker_budget").status == "planned"
    assert next(card for card in engine_judgment.cards if card.key == "engine_judgment_empty").status == "planned"
    assert next(card for card in shadow.cards if card.key == "shadow_run_state").status == "planned"
    assert next(card for card in micro.cards if card.key == "micro_live_run_state").status == "planned"
    assert next(card for card in live.cards if card.key == "live_light_run_state").status == "planned"
    assert next(card for card in build14.cards if card.key == "build14_mode").status == "planned"
    assert next(card for card in account.cards if card.key == "account_user_data_auth").status == "planned"
    assert next(card for card in replay.cards if card.key == "artifact_manifest").value == "none"
    assert next(card for card in replay.cards if card.key == "validation_status").value == "not_run"
    assert next(card for card in replay.cards if card.key == "compatibility_policy").status == "planned"
    assert next(card for card in replay.cards if card.key == "signature_policy").status == "planned"


def test_technical_dashboard_view_escalates_headline_from_build9x():
    snapshot = _snapshot().model_copy(
        update={
            "alerts": (),
            "backlog_warning": False,
            "stale_warning": False,
            "loss_warning": False,
        }
    )
    snapshot = snapshot.model_copy(
        update={
            "meta": snapshot.meta.model_copy(
                update={
                    "break_even_drift_alert": False,
                    "edge_degraded_count": 0,
                }
            )
        }
    )

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("meta_learning", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        build9x_projection=Build9XProjection(
            status="warning",
            diagnostics_count=1,
            diagnostics_summary="One governed issue detected",
            open_hypotheses=1,
            total_hypotheses=1,
            near_miss_count=0,
            replay_candidate_count=0,
            memory_record_count=0,
            latest_memory_summary="No memory records",
        ),
    )

    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    operator = next(section for section in view.sections if section.title == "Operator Controls")

    assert next(card for card in system.cards if card.key == "headline_status").status == "warning"
    assert next(card for card in operator.cards if card.key == "operator_safing_controls").status == "warning"
    assert next(card for card in operator.cards if card.key == "operator_kill_path").status == "warning"


def test_technical_dashboard_view_escalates_headline_from_build9_meta():
    snapshot = _snapshot().model_copy(
        update={
            "alerts": (),
            "backlog_warning": False,
            "stale_warning": False,
            "loss_warning": False,
        }
    )
    snapshot = snapshot.model_copy(
        update={
            "meta": snapshot.meta.model_copy(
                update={
                    "dtr_coverage": 0.50,
                    "cra_sterilization_rate": 0.25,
                    "cra_alert_count": 1,
                    "break_even_drift_alert": False,
                    "break_even_drift_scopes": (),
                    "edge_degraded_count": 0,
                }
            )
        }
    )

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("meta", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
    )

    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    operator = next(section for section in view.sections if section.title == "Operator Controls")

    assert next(card for card in system.cards if card.key == "headline_status").status == "warning"
    assert next(card for card in operator.cards if card.key == "operator_safing_controls").status == "warning"
    assert next(card for card in operator.cards if card.key == "operator_kill_path").status == "warning"


def test_technical_dashboard_view_projects_authenticated_account_user_data_when_available():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        account_user_data_projection=AccountUserDataProjection(
            status="healthy",
            authenticated=True,
            session_date="2026-04-03",
            acquisition_mode="native_live_websocket_auto_export",
            endpoint="wss://ws-api.binance.com:443/ws-api/v3",
            summary_ref="build/live_user_data_capture_summary.json",
            events_ref="build/live_user_data_events.jsonl",
            subscription_id=0,
            event_count=0,
            event_types=(),
            pair_scope=("BTCUSDT", "ETHUSDT"),
            detail="Authenticated Binance user-data stream captured; no account event was emitted during the bounded capture window.",
        ),
    )

    view = build_technical_dashboard_view(payload)
    account = next(section for section in view.sections if section.title == "Account / User Data")

    assert next(card for card in account.cards if card.key == "account_user_data_auth").value == "authenticated"
    assert next(card for card in account.cards if card.key == "account_user_data_auth").status == "healthy"
    assert next(card for card in account.cards if card.key == "account_user_data_subscription").value == "id=0 / events=0"
    assert next(card for card in account.cards if card.key == "account_user_data_scope").detail == "BTCUSDT, ETHUSDT"
    assert next(card for card in account.cards if card.key == "account_user_data_artifacts").detail.startswith(
        "Authenticated Binance user-data stream captured"
    )


def test_technical_dashboard_view_escalates_headline_from_account_user_data():
    snapshot = _snapshot(runtime_mode=RuntimeMode.LIVE).model_copy(
        update={
            "alerts": (),
            "backlog_warning": False,
            "stale_warning": False,
            "loss_warning": False,
        }
    )
    snapshot = snapshot.model_copy(
        update={
            "meta": snapshot.meta.model_copy(
                update={
                    "break_even_drift_alert": False,
                    "edge_degraded_count": 0,
                }
            )
        }
    )

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        account_user_data_projection=AccountUserDataProjection(
            status="warning",
            authenticated=False,
            detail="User-data artifact exists but authentication was not confirmed.",
        ),
    )

    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    operator = next(section for section in view.sections if section.title == "Operator Controls")

    assert next(card for card in system.cards if card.key == "headline_status").status == "warning"
    assert next(card for card in operator.cards if card.key == "operator_safing_controls").status == "warning"
    assert next(card for card in operator.cards if card.key == "operator_kill_path").status == "warning"


def test_technical_dashboard_view_projects_engine_judgment_when_available():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b", "engine_c", "engine_d"),
        engine_judgment_projection=EngineJudgmentProjection(
            status="warning",
            source_report_id="shadow_report:light:1",
            source_shadow_run_id="shadow-run-1",
            source_shadow_days_completed=1,
            source_shadow_required_days=30,
            portfolio_judgment_verdict="shadow-only",
            portfolio_physics_pressure="elevated",
            portfolio_cluster_pressure="critical",
            portfolio_loss_capacity_pressure="elevated",
            portfolio_rejected_engine_count=1,
            ranking_rejected_engine_count=1,
            elevated_physics_engine_count=1,
            critical_physics_engine_count=1,
            phantom_trade_count=2,
            portfolio_rationale="portfolio concentration remained elevated in Shadow",
            cards=(
                EngineJudgmentCard(
                    engine_id="engine_a",
                    component_verdict="shadow_validated",
                    judgment_verdict="shadow-only",
                    status="warning",
                    useful_frequency=1.0,
                    ce_expected=0.0007,
                    estimated_cost_bps=10.0,
                    edge_net=0.005,
                    economic_pass_rate=1.0,
                    conflict_rate=0.0,
                    marginal_edge=0.004,
                    redundancy_score=0.0,
                    portfolio_contribution=0.004,
                    observations=1,
                    rationale="Shadow gate incomplete: 1/30 day(s), report_complete=False",
                    evidence_summary="runtime_status=accepted / pair=BTCUSDT / conviction=high",
                ),
                EngineJudgmentCard(
                    engine_id="engine_c",
                    component_verdict="dormant",
                    judgment_verdict="dormant",
                    status="planned",
                    useful_frequency=0.0,
                    ce_expected=0.0,
                    estimated_cost_bps=0.0,
                    edge_net=0.0,
                    economic_pass_rate=0.0,
                    conflict_rate=0.0,
                    marginal_edge=0.0,
                    redundancy_score=0.0,
                    portfolio_contribution=0.0,
                    observations=0,
                    rationale="component marked dormant by the Shadow component verdicts",
                    evidence_summary="Engine C remains dormant in this surface",
                ),
            ),
        ),
    )

    view = build_technical_dashboard_view(payload)
    engine_judgment = next(section for section in view.sections if section.title == "Engine Judgement")

    assert next(card for card in engine_judgment.cards if card.key == "engine_judgment_summary").value == (
        "promotable=0 / shadow-only=1 / rewrite=0 / dormant=1"
    )
    assert next(card for card in engine_judgment.cards if card.key == "engine_judgment_source").value == "1/30 day(s)"
    assert next(card for card in engine_judgment.cards if card.key == "engine_judgment_portfolio").value == "shadow-only"
    assert "physics=elevated" in next(
        card for card in engine_judgment.cards if card.key == "engine_judgment_portfolio"
    ).detail
    assert "cluster=critical" in next(
        card for card in engine_judgment.cards if card.key == "engine_judgment_portfolio"
    ).detail
    assert "rationale=portfolio concentration remained elevated in Shadow" in next(
        card for card in engine_judgment.cards if card.key == "engine_judgment_portfolio"
    ).detail
    assert next(card for card in engine_judgment.cards if card.key == "engine_judgment_engine_a").value == "shadow-only"
    assert next(card for card in engine_judgment.cards if card.key == "engine_judgment_engine_a").status == "warning"
    assert "shadow_component=shadow_validated" in next(
        card for card in engine_judgment.cards if card.key == "engine_judgment_engine_a"
    ).detail
    assert "ce=0.0007" in next(
        card for card in engine_judgment.cards if card.key == "engine_judgment_engine_a"
    ).detail
    assert "portfolio_contribution=0.0040" in next(
        card for card in engine_judgment.cards if card.key == "engine_judgment_engine_a"
    ).detail
    assert "rationale=Shadow gate incomplete: 1/30 day(s), report_complete=False" in next(
        card for card in engine_judgment.cards if card.key == "engine_judgment_engine_a"
    ).detail
    assert next(card for card in engine_judgment.cards if card.key == "engine_judgment_engine_c").value == "dormant"


def test_technical_dashboard_view_escalates_headline_from_engine_judgment():
    snapshot = _snapshot().model_copy(
        update={
            "alerts": (),
            "backlog_warning": False,
            "stale_warning": False,
            "loss_warning": False,
        }
    )
    snapshot = snapshot.model_copy(
        update={
            "meta": snapshot.meta.model_copy(
                update={
                    "break_even_drift_alert": False,
                    "edge_degraded_count": 0,
                }
            )
        }
    )

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        engine_judgment_projection=EngineJudgmentProjection(
            status="critical",
            portfolio_judgment_verdict="rewrite-required",
        ),
    )

    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    alerts = next(section for section in view.sections if section.title == "Alerts")

    assert next(card for card in system.cards if card.key == "headline_status").status == "critical"
    assert next(card for card in system.cards if card.key == "headline_status").value == "critical"
    assert next(card for card in alerts.cards if card.key == "active_alerts").status == "critical"


def test_technical_dashboard_view_projects_shadow_enabled_build14_when_module_active():
    payload = build_technical_dashboard_payload(
        _snapshot(infra=collect_infra_metrics()),
        active_modules=("monitoring", "ui", "complete_enablers"),
        active_engines=("engine_a", "engine_b"),
    )

    view = build_technical_dashboard_view(payload)
    build14 = next(section for section in view.sections if section.title == "Build-14 Enablers")

    assert next(card for card in build14.cards if card.key == "build14_mode").value == (
        "shadow_enabled / shadow_apply"
    )
    assert next(card for card in build14.cards if card.key == "build14_candidate_effect").value == (
        "shadow_enabled"
    )
    assert next(card for card in build14.cards if card.key == "build14_guardrails").value == (
        "shadow_enabled"
    )


def test_technical_dashboard_view_projects_alerts_and_engine_staleness_without_prefilled_alerts():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=("interface_contracts", "meta_learning", "local_replay_runtime", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        operator_runtime=OperatorRuntimeProjection(
            event_count=2,
            latest_event_type="screen_opened",
            latest_event_message="screen opened: overview",
            pending_notification_count=1,
            pending_notification_alert_ids=("corr-tech:loss",),
            acknowledged_notification_count=0,
        ),
    )

    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    alerts = next(section for section in view.sections if section.title == "Alerts")
    engines = next(card for card in system.cards if card.key == "engines_ab")
    active_alerts = next(card for card in alerts.cards if card.key == "active_alerts")

    assert engines.status == "warning"
    assert "stale: engine_b" in engines.detail
    assert int(active_alerts.value) >= 3
    assert active_alerts.status in {"warning", "critical"}
    assert any(card.key == "operator_events" and card.value == "2" for card in alerts.cards)
    assert any(card.key == "operator_notifications" and card.value == "pending=1 / ack=0" for card in alerts.cards)


def test_technical_dashboard_view_surfaces_rejected_import_and_future_panels():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=("meta_learning", "local_replay_runtime", "backtest_artifact_import", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        build9x_projection=_build9x_projection(),
        replay_projection=ReplayImportProjection(
            status="warning",
            artifact_id="artifact-1",
            artifact_kind="review_packet",
            lineage_version="a.v2.1",
            lifecycle_state="exported",
            validation_status="needs_revision",
            review_state="needs_revision",
            compatibility_status="rejected",
            compatibility_reasons=("ARTIFACT_SCHEMA_MINOR_UNSUPPORTED", "FEATURE_SET_UNKNOWN"),
            signature_check_status="key_id_unknown",
            signature_key_id="lab_unknown",
            signature_check_reasons=("KEY_ID_UNKNOWN",),
            conflict_resolution_mode="no_trade_then_strictest",
            conflict_hard_veto_action="no_trade",
            conflict_score_aggregation_mode="bounded_sum_with_global_cap",
            conflict_size_reduce_mode="min_factor_wins",
            conflict_rank_adjust_mode="bounded_sum",
            conflict_additive_soft_boosts_allowed=True,
            conflict_additive_soft_reduces_allowed=True,
            registry_atomicity_mode="atomic_snapshot_swap",
            registry_concurrency_model="single_writer_multi_reader",
            registry_publish_requires_atomic_replace=True,
            registry_publish_requires_fsync=True,
            registry_rollback_to_last_known_good=True,
            rejection_reasons=("import target must start at SHADOW",),
        ),
    )

    view = build_technical_dashboard_view(payload)
    replay = next(section for section in view.sections if section.title == "Replay & Import")
    validation = next(card for card in replay.cards if card.key == "validation_status")
    reasons = next(card for card in replay.cards if card.key == "validation_reasons")
    compatibility = next(card for card in replay.cards if card.key == "compatibility_policy")
    signature = next(card for card in replay.cards if card.key == "signature_policy")
    conflict = next(card for card in replay.cards if card.key == "conflict_policy")
    registry = next(card for card in replay.cards if card.key == "registry_policy")
    assert validation.status == "warning"
    assert validation.value == "needs_revision"
    assert reasons.detail == "import target must start at SHADOW"
    assert compatibility.status == "warning"
    assert compatibility.value == "rejected"
    assert "ARTIFACT_SCHEMA_MINOR_UNSUPPORTED" in compatibility.detail
    assert signature.status == "warning"
    assert signature.value == "key_id_unknown"
    assert "key=lab_unknown" in signature.detail
    assert conflict.status == "healthy"
    assert conflict.value == "no_trade_then_strictest"
    assert "score=bounded_sum_with_global_cap" in conflict.detail
    assert registry.status == "healthy"
    assert registry.value == "atomic_snapshot_swap"
    assert "atomic_replace=yes" in registry.detail
    assert set(view.future_panels) == {
        "technical_supervision",
        "build9x_diagnostics",
        "shadow_supervision",
        "micro_live_supervision",
        "live_light_supervision",
        "build14_supervision",
        "artifact_import",
        "observability_export",
    }


def test_technical_dashboard_view_marks_missing_modules_and_engines_as_planned():
    payload = build_technical_dashboard_payload(_snapshot(infra=collect_infra_metrics()))
    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    modules = next(card for card in system.cards if card.key == "active_modules")
    engines = next(card for card in system.cards if card.key == "engines_ab")

    assert modules.status == "planned"
    assert modules.detail == "No active modules declared"
    assert engines.status == "planned"
    assert engines.detail == "No active engines declared"


def test_technical_dashboard_view_projects_execution_no_trade_bridge_card():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
    ).model_copy(
        update={
            "execution_no_trade_bridge": build_technical_dashboard_payload(
                _snapshot(),
                active_modules=("protocols", "monitoring", "ui"),
                active_engines=("engine_a", "engine_b"),
            ).execution_no_trade_bridge.model_copy(
                update={
                    "status": "warning",
                    "configured": True,
                    "selection_status": "binding_only",
                    "current_snapshot_id": "snap-2",
                    "last_known_good_snapshot_id": "snap-1",
                    "binding_present": True,
                    "loaded": False,
                    "compiled_plan_ref": "compiled/snap-2/execution_no_trade.json",
                    "failure_mode": "fail_open_baseline_skip_artifact",
                    "error_stage": "plan_selection",
                    "error_type": "ValueError",
                }
            )
        }
    )

    view = build_technical_dashboard_view(payload)
    execution = next(section for section in view.sections if section.title == "Execution")
    bridge = next(card for card in execution.cards if card.key == "execution_no_trade_bridge")

    assert bridge.status == "warning"
    assert bridge.value == "sel=binding_only / loaded=no"
    assert "cfg=yes" in bridge.detail
    assert "snapshot=snap-2" in bridge.detail
    assert "lkg=snap-1" in bridge.detail
    assert "err=ValueError" in bridge.detail
    assert "mode=fail_open_baseline_skip_artifact" in bridge.detail
    assert "stage=plan_selection" in bridge.detail


def test_technical_dashboard_view_projects_execution_runtime_projection_bridge_card():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        execution_runtime_projection_bridge_projection=ExecutionRuntimeProjectionBridgeProjection(
            status="warning",
            configured=True,
            projection_found=True,
            projection_loaded=True,
            projection_status="partial",
            projection_path="build/local_lab_execution_runtime_projection.json",
            consumer_count=3,
            ready_consumer_count=1,
            partial_consumer_count=2,
            blocked_consumer_count=0,
            rate_limit_model_loaded=True,
            spread_guard_model_loaded=False,
            slippage_model_loaded=False,
        ),
    )

    view = build_technical_dashboard_view(payload)
    execution = next(section for section in view.sections if section.title == "Execution")
    bridge = next(
        card for card in execution.cards if card.key == "execution_runtime_projection_bridge"
    )

    assert bridge.status == "warning"
    assert bridge.value == "proj=partial / loaded=yes / consumers=3"
    assert "cfg=yes" in bridge.detail
    assert "ready=1" in bridge.detail
    assert "spread_guard=no" in bridge.detail
    assert "slippage=no" in bridge.detail
    assert "path=build/local_lab_execution_runtime_projection.json" in bridge.detail


def test_technical_dashboard_view_projects_runtime_hook_bridge_section():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        runtime_hook_bridge_projections=(
            RuntimeHookBridgeProjection(
                hook_id=HookId.ENGINE_B_SWEEP_VALIDATION,
                label="Engine B sweep",
                status="warning",
                configured=True,
                selection_status="binding_only",
                binding_present=True,
                artifact_count=2,
                action_kinds=("soft_reduce",),
                detail="Compiled Engine B bridge binding published but plan not loaded",
            ),
            RuntimeHookBridgeProjection(
                hook_id=HookId.RISK_MICRO_FRICTION_PRECHECK,
                label="Risk micro-friction",
                status="healthy",
                configured=True,
                selection_status="loaded",
                loaded=True,
                artifact_count=1,
                action_kinds=("no_trade",),
                detail="Compiled risk micro-friction bridge loaded from current snapshot",
            ),
        ),
    )

    view = build_technical_dashboard_view(payload)
    hook_section = next(section for section in view.sections if section.title == "Artifact Hooks")
    summary = next(card for card in hook_section.cards if card.key == "runtime_hook_bridges_summary")
    engine_b = next(
        card for card in hook_section.cards if card.key == "runtime_hook_bridge_engine_b_sweep_validation"
    )

    assert summary.value == "open=8 / configured=2 / loaded=1"
    assert summary.status == "warning"
    assert "runtime_projection=planned" in summary.detail
    assert engine_b.value == "sel=binding_only / loaded=no"
    assert "actions=soft_reduce" in engine_b.detail
    assert "artifacts=2" in engine_b.detail


def test_technical_dashboard_view_escalates_headline_from_execution_no_trade_bridge():
    snapshot = _snapshot().model_copy(
        update={
            "alerts": (),
            "backlog_warning": False,
            "stale_warning": False,
            "loss_warning": False,
        }
    )
    snapshot = snapshot.model_copy(
        update={
            "meta": snapshot.meta.model_copy(
                update={
                    "break_even_drift_alert": False,
                    "edge_degraded_count": 0,
                }
            )
        }
    )

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        execution_no_trade_bridge_projection=ExecutionNoTradeBridgeProjection(
            status="warning",
            configured=True,
            selection_status="binding_only",
        ),
    )

    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    operator = next(section for section in view.sections if section.title == "Operator Controls")

    assert next(card for card in system.cards if card.key == "headline_status").status == "warning"
    assert next(card for card in operator.cards if card.key == "operator_safing_controls").status == "warning"
    assert next(card for card in operator.cards if card.key == "operator_kill_path").status == "warning"


def test_technical_dashboard_view_projects_shadow_summary_when_available():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        shadow_projection=ShadowProjection(
            status="warning",
            run_state="completed",
            verdict="needs_review",
            truth_set_ref="shadow_truth:t1",
            validation_set_ref="shadow_validation:v1",
            divergent_comparison_count=2,
            blocking_comparison_count=0,
            total_comparison_count=7,
            build9x_diagnostics_count=2,
            open_hypotheses=1,
            replay_candidate_count=1,
            review_export_ready=False,
            import_artifact_id="artifact-shadow-1",
            import_lineage_version="a.v1.0.r1",
            execution_telemetry_ref="E:/shadow/shadow_vps_service_execution_telemetry.json",
            execution_telemetry_status="written",
            telegram_alert_delivery_status="failed",
            telegram_alert_delivery_event_type="shadow_day_failed",
            telegram_alert_delivery_error="http_500",
            execution_runtime_bootstrap_ref="E:/shadow/execution_runtime_bootstrap.summary.json",
            execution_runtime_bootstrap_status="ready",
            execution_runtime_bootstrap_source="live_websocket_config",
            execution_runtime_gatekeeper_audit_ref="E:/shadow/artifacts/gatekeeper/audit.jsonl",
            execution_runtime_gatekeeper_audit_source="cli",
            execution_runtime_bootstrap_user_data_stream_enabled=False,
            execution_runtime_bootstrap_reconciliation_boot_executed=True,
            execution_runtime_bootstrap_reconciliation_boot_trading_blocked=False,
            execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped=False,
            execution_runtime_bootstrap_reconciliation_boot_detail="boot reconciliation aligned local and remote state",
            execution_runtime_bootstrap_reconciliation_boot_recovery_action="none",
            execution_runtime_bootstrap_reconciliation_boot_divergence_count=0,
            execution_runtime_projection_ref="E:/shadow/local_lab_execution_runtime_projection.json",
            execution_runtime_projection_source="cli",
            regime_lite_assessment_ref="E:/shadow/regime_lite_assessment.json",
            regime_lite_assessment_source="live_websocket_config",
            regime_lite_safing_recommendation_ref="E:/shadow/regime_lite_safing_recommendation.json",
            regime_lite_safing_recommendation_source="cli",
            info_stress_assessment_ref="E:/shadow/info_stress_assessment.json",
            info_stress_assessment_source="cli",
            info_stress_governance_status="assessment_only",
            info_stress_level="extreme",
            info_stress_alert_count=3,
            info_stress_entries_blocked=True,
            info_stress_entries_blocked_until_ts=1700086400,
            info_stress_reason_codes=("INFO_STRESS_SPREAD_EXPLOSION",),
            info_stress_detail="info_stress reached EXTREME in shadow",
            execution_runtime_projection_status="ready",
            execution_runtime_projection_ready=True,
            execution_runtime_projection_consumer_count=3,
            execution_runtime_projection_ready_consumer_count=3,
            execution_runtime_projection_partial_consumer_count=0,
            execution_runtime_projection_blocked_consumer_count=0,
            execution_runtime_projection_bridge_status="healthy",
            execution_runtime_projection_bridge_loaded=True,
            execution_runtime_projection_rate_limit_model_loaded=True,
            execution_runtime_projection_spread_guard_model_loaded=True,
            execution_runtime_projection_slippage_model_loaded=True,
            regime_lite_safing=RegimeLiteSafingProjection(
                status="critical",
                severity="halt_recommended",
                should_block_new_entries=True,
                should_exit_all=True,
                recommended_operator_action="set_halted",
                operator_safing_request_action="set_halted",
                operator_safing_request_source_runtime_mode="shadow",
                detail="regime_lite reached EXTREME in shadow; recommend set_halted",
                reason_codes=("RISK_REGIME_EXTREME_EXIT_ALL",),
            ),
            blocking_reasons=("Build-9X review export must be ready before accepting Shadow",),
            manual_review_required=True,
        ),
    )

    view = build_technical_dashboard_view(payload)
    build10 = next(section for section in view.sections if section.title == "Build-10")
    system = next(section for section in view.sections if section.title == "System")
    shadow = next(section for section in view.sections if section.title == "Build-11 Shadow")

    governed = next(card for card in build10.cards if card.key == "build10_extensions")
    assert "shadow=warning" in governed.value
    assert next(card for card in shadow.cards if card.key == "shadow_verdict").value == "needs_review"
    assert next(card for card in shadow.cards if card.key == "shadow_divergences").status == "warning"
    assert next(
        card for card in shadow.cards if card.key == "shadow_execution_telemetry"
    ).value == "written"
    assert next(
        card for card in shadow.cards if card.key == "shadow_execution_telemetry"
    ).status == "healthy"
    assert "shadow_vps_service_execution_telemetry.json" in next(
        card for card in shadow.cards if card.key == "shadow_execution_telemetry"
    ).detail
    assert next(
        card for card in shadow.cards if card.key == "shadow_telegram_alerts"
    ).value == "failed"
    assert next(
        card for card in shadow.cards if card.key == "shadow_telegram_alerts"
    ).status == "critical"
    assert "event=shadow_day_failed" in next(
        card for card in shadow.cards if card.key == "shadow_telegram_alerts"
    ).detail
    assert "error=http_500" in next(
        card for card in shadow.cards if card.key == "shadow_telegram_alerts"
    ).detail
    assert next(
        card for card in shadow.cards if card.key == "shadow_execution_bootstrap"
    ).value == "ready@live_websocket_config"
    assert next(
        card for card in shadow.cards if card.key == "shadow_execution_bootstrap"
    ).status == "healthy"
    assert "gatekeeper_source=cli" in next(
        card for card in shadow.cards if card.key == "shadow_execution_bootstrap"
    ).detail
    assert "divergences=0" in next(
        card for card in shadow.cards if card.key == "shadow_execution_bootstrap"
    ).detail
    assert "execution_runtime_bootstrap.summary.json" in next(
        card for card in shadow.cards if card.key == "shadow_execution_bootstrap"
    ).detail
    assert next(
        card for card in shadow.cards if card.key == "shadow_execution_projection"
    ).value == "ready@cli"
    assert next(
        card for card in shadow.cards if card.key == "shadow_execution_projection"
    ).status == "healthy"
    assert "spread_guard=yes" in next(
        card for card in shadow.cards if card.key == "shadow_execution_projection"
    ).detail
    assert "local_lab_execution_runtime_projection.json" in next(
        card for card in shadow.cards if card.key == "shadow_execution_projection"
    ).detail
    assert next(
        card for card in shadow.cards if card.key == "shadow_regime_lite_safing"
    ).value == "halt_recommended"
    assert next(
        card for card in shadow.cards if card.key == "shadow_regime_lite_safing"
    ).status == "critical"
    assert "block_entries=yes" in next(
        card for card in shadow.cards if card.key == "shadow_regime_lite_safing"
    ).detail
    assert "assessment_source=live_websocket_config" in next(
        card for card in shadow.cards if card.key == "shadow_regime_lite_safing"
    ).detail
    assert "safing_source=cli" in next(
        card for card in shadow.cards if card.key == "shadow_regime_lite_safing"
    ).detail
    assert "regime_lite_assessment.json" in next(
        card for card in shadow.cards if card.key == "shadow_regime_lite_safing"
    ).detail
    assert "regime_lite_safing_recommendation.json" in next(
        card for card in shadow.cards if card.key == "shadow_regime_lite_safing"
    ).detail
    assert "exit_all=yes" in next(
        card for card in shadow.cards if card.key == "shadow_regime_lite_safing"
    ).detail
    assert "RISK_REGIME_EXTREME_EXIT_ALL" in next(
        card for card in shadow.cards if card.key == "shadow_regime_lite_safing"
    ).detail
    assert next(
        card for card in shadow.cards if card.key == "shadow_info_stress"
    ).value == "assessment_only@extreme"
    assert next(
        card for card in shadow.cards if card.key == "shadow_info_stress"
    ).status == "warning"
    assert "assessment_source=cli" in next(
        card for card in shadow.cards if card.key == "shadow_info_stress"
    ).detail
    assert "info_stress_assessment.json" in next(
        card for card in shadow.cards if card.key == "shadow_info_stress"
    ).detail
    assert "INFO_STRESS_SPREAD_EXPLOSION" in next(
        card for card in shadow.cards if card.key == "shadow_info_stress"
    ).detail
    assert next(card for card in shadow.cards if card.key == "shadow_blocking_reasons").detail == (
        "Build-9X review export must be ready before accepting Shadow"
    )


def test_technical_dashboard_view_projects_micro_live_summary_when_available():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        micro_live_projection=MicroLiveProjection(
            status="healthy",
            run_state="ready_to_probe",
            verdict="allowed_to_probe",
            shadow_run_id="shadow-run-1",
            shadow_verdict="accepted",
            allowed_to_probe=True,
            requested_total_notional_usdt=20.0,
            approved_total_notional_usdt=20.0,
            approved_pair_notional_usdt=10.0,
            order_probe_limit=2,
            planned_pairs=("BTCUSDT", "ETHUSDT"),
            planned_engines=("engine_a", "engine_b"),
            import_artifact_id="artifact-micro-1",
            import_lineage_version="a.v1.0.r1",
            observability_ready=True,
            halt_ready=True,
            onboarding_ready=True,
            operator_safing_action="downgrade_to_shadow",
            operator_safing_target_runtime_mode="shadow",
            operator_safing_reason="manual requalification requested",
            blocking_reasons=(),
        ),
    )

    view = build_technical_dashboard_view(payload)
    build10 = next(section for section in view.sections if section.title == "Build-10")
    system = next(section for section in view.sections if section.title == "System")
    micro = next(section for section in view.sections if section.title == "Build-12 Micro-live")

    governed = next(card for card in build10.cards if card.key == "build10_extensions")
    assert "micro=healthy" in governed.value
    assert next(card for card in micro.cards if card.key == "micro_live_verdict").value == "allowed_to_probe"
    assert next(card for card in micro.cards if card.key == "micro_live_guardrails").status == "healthy"
    assert next(card for card in micro.cards if card.key == "micro_live_safing_request").value == (
        "downgrade_to_shadow -> shadow"
    )
    assert next(card for card in micro.cards if card.key == "micro_live_safing_request").detail == (
        "manual requalification requested"
    )


def test_technical_dashboard_view_projects_live_light_summary_when_available():
    payload = build_technical_dashboard_payload(
        _snapshot(runtime_mode=RuntimeMode.LIVE),
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        live_light_projection=LiveLightProjection(
            status="healthy",
            run_state="ready_to_execute_small",
            verdict="allowed_to_execute_small",
            micro_live_run_id="micro-run-1",
            micro_live_verdict="allowed_to_probe",
            allowed_to_execute_small=True,
            requested_total_notional_usdt=80.0,
            approved_total_notional_usdt=80.0,
            approved_pair_notional_usdt=40.0,
            execution_order_limit=3,
            planned_pairs=("BTCUSDT", "ETHUSDT"),
            planned_engines=("engine_a", "engine_b"),
            import_artifact_id="artifact-live-1",
            import_lineage_version="a.v1.0.r1",
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            operator_safing_action="downgrade_to_micro_live",
            operator_safing_target_runtime_mode="micro_live",
            operator_safing_reason="execution drift requires step-down",
            blocking_reasons=(),
        ),
    )

    view = build_technical_dashboard_view(payload)
    build10 = next(section for section in view.sections if section.title == "Build-10")
    system = next(section for section in view.sections if section.title == "System")
    live = next(section for section in view.sections if section.title == "Build-13 Live")

    governed = next(card for card in build10.cards if card.key == "build10_extensions")
    assert "live=healthy" in governed.value
    assert next(card for card in live.cards if card.key == "live_light_verdict").value == "allowed_to_execute_small"
    assert next(card for card in live.cards if card.key == "live_light_readiness").status == "healthy"
    assert next(card for card in live.cards if card.key == "live_light_safing_request").value == (
        "downgrade_to_micro_live -> micro_live"
    )
    assert next(card for card in live.cards if card.key == "live_light_safing_request").detail == (
        "execution drift requires step-down"
    )


def test_technical_dashboard_view_exposes_operator_controls_for_current_runtime():
    payload = build_technical_dashboard_payload(
        _snapshot(runtime_mode=RuntimeMode.LIVE, infra=collect_infra_metrics(kill_switch_active=True)),
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        operator_runtime=OperatorRuntimeProjection(
            event_count=3,
            latest_event_type="operator_action_accepted",
            latest_event_message="manual safing accepted",
            latest_safing_action="downgrade_to_micro_live",
            latest_safing_source_runtime_mode="live",
            latest_safing_target_runtime_mode="micro_live",
            latest_safing_reason="execution drift requires step-down",
            pending_notification_count=0,
            acknowledged_notification_count=1,
            latest_acknowledged_alert_id="corr-tech:loss",
        ),
    )

    view = build_technical_dashboard_view(payload)
    operator = next(section for section in view.sections if section.title == "Operator Controls")

    assert next(card for card in operator.cards if card.key == "operator_manual_scope").detail == (
        "view_critical_screens, suspend_pair, request_pair_resume, suspend_engine, "
        "set_halted, downgrade_to_micro_live, downgrade_to_shadow, view_alert_history, "
        "acknowledge_critical_alert"
    )
    assert next(card for card in operator.cards if card.key == "operator_safing_controls").detail == (
        "set_halted, downgrade_to_micro_live, downgrade_to_shadow / supervision=critical"
    )
    assert next(card for card in operator.cards if card.key == "operator_latest_safing").value == (
        "downgrade_to_micro_live -> micro_live"
    )
    assert next(card for card in operator.cards if card.key == "operator_latest_safing").detail == (
        "execution drift requires step-down"
    )
    assert next(card for card in operator.cards if card.key == "operator_kill_path").value == "active"
    assert next(card for card in operator.cards if card.key == "operator_kill_path").status == "critical"


def test_technical_dashboard_view_prefers_operator_last_error_in_alerts_section():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a",),
        operator_runtime=OperatorRuntimeProjection(
            event_count=1,
            latest_event_type="screen_opened",
            latest_event_message="screen opened: overview",
            last_error="state_file_corrupted:JSONDecodeError:bad payload",
        ),
    )

    view = build_technical_dashboard_view(payload)
    alerts = next(section for section in view.sections if section.title == "Alerts")

    assert next(card for card in alerts.cards if card.key == "operator_events").detail == (
        "state_file_corrupted:JSONDecodeError:bad payload"
    )


def test_technical_dashboard_view_escalates_operator_controls_from_supervision_status():
    snapshot = _snapshot().model_copy(
        update={
            "alerts": (),
            "backlog_warning": False,
            "stale_warning": False,
            "loss_warning": False,
        }
    )
    snapshot = snapshot.model_copy(
        update={
            "meta": snapshot.meta.model_copy(
                update={
                    "break_even_drift_alert": False,
                    "edge_degraded_count": 0,
                }
            )
        }
    )

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        engine_judgment_projection=EngineJudgmentProjection(
            status="warning",
            portfolio_judgment_verdict="shadow-only",
        ),
    )

    view = build_technical_dashboard_view(payload)
    operator = next(section for section in view.sections if section.title == "Operator Controls")

    assert next(card for card in operator.cards if card.key == "operator_safing_controls").status == "warning"
    assert next(card for card in operator.cards if card.key == "operator_safing_controls").detail.endswith(
        "/ supervision=warning"
    )
    assert next(card for card in operator.cards if card.key == "operator_kill_path").value == "armed"
    assert next(card for card in operator.cards if card.key == "operator_kill_path").status == "warning"


def test_technical_dashboard_view_escalates_headline_from_build14():
    snapshot = _snapshot().model_copy(
        update={
            "alerts": (),
            "backlog_warning": False,
            "stale_warning": False,
            "loss_warning": False,
        }
    )
    snapshot = snapshot.model_copy(
        update={
            "meta": snapshot.meta.model_copy(
                update={
                    "break_even_drift_alert": False,
                    "edge_degraded_count": 0,
                }
            )
        }
    )

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        build14_projection=Build14Projection(
            status="warning",
            influence_mode="limited_influence",
            action="downgrade_confidence",
            severity="elevated",
            summary="Build-14 limited influence requires warning-level supervision",
            candidate_effect="confidence_downgrade",
            confidence_penalty_weight=0.10,
            recommended_budget_factor=0.85,
        ),
    )

    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    operator = next(section for section in view.sections if section.title == "Operator Controls")

    assert next(card for card in system.cards if card.key == "headline_status").status == "warning"
    assert next(card for card in operator.cards if card.key == "operator_safing_controls").status == "warning"
    assert next(card for card in operator.cards if card.key == "operator_kill_path").status == "warning"


def test_technical_dashboard_view_escalates_headline_from_replay_import():
    snapshot = _snapshot().model_copy(
        update={
            "alerts": (),
            "backlog_warning": False,
            "stale_warning": False,
            "loss_warning": False,
        }
    )
    snapshot = snapshot.model_copy(
        update={
            "meta": snapshot.meta.model_copy(
                update={
                    "break_even_drift_alert": False,
                    "edge_degraded_count": 0,
                }
            )
        }
    )

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        replay_projection=ReplayImportProjection(
            status="warning",
            artifact_id="artifact-1",
            artifact_kind="review_packet",
            lineage_version="a.v1.0.r1",
            validation_status="needs_revision",
            review_state="needs_revision",
        ),
    )

    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    operator = next(section for section in view.sections if section.title == "Operator Controls")

    assert next(card for card in system.cards if card.key == "headline_status").status == "warning"
    assert next(card for card in operator.cards if card.key == "operator_safing_controls").status == "warning"
    assert next(card for card in operator.cards if card.key == "operator_kill_path").status == "warning"


def test_technical_dashboard_view_escalates_headline_from_shadow_projection():
    snapshot = _snapshot().model_copy(
        update={
            "alerts": (),
            "backlog_warning": False,
            "stale_warning": False,
            "loss_warning": False,
        }
    )
    snapshot = snapshot.model_copy(
        update={
            "meta": snapshot.meta.model_copy(
                update={
                    "break_even_drift_alert": False,
                    "edge_degraded_count": 0,
                }
            )
        }
    )

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        shadow_projection=ShadowProjection(
            status="warning",
            run_state="completed",
            verdict="needs_review",
        ),
    )

    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    operator = next(section for section in view.sections if section.title == "Operator Controls")

    assert next(card for card in system.cards if card.key == "headline_status").status == "warning"
    assert next(card for card in operator.cards if card.key == "operator_safing_controls").status == "warning"
    assert next(card for card in operator.cards if card.key == "operator_kill_path").status == "warning"


def test_technical_dashboard_view_projects_build14_limited_influence_when_available():
    payload = build_technical_dashboard_payload(
        _snapshot(runtime_mode=RuntimeMode.LIVE),
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        build14_projection=Build14Projection(
            status="warning",
            influence_mode="limited_influence",
            action="downgrade_confidence",
            severity="elevated",
            summary="Build-14 limited influence reduces live-light confidence and budget",
            market_toxicity_value=0.46,
            market_toxicity_status="elevated",
            execution_fragility_value=0.35,
            execution_fragility_status="nominal",
            confidence_penalty_weight=0.10,
            recommended_budget_factor=0.85,
            requires_manual_review=False,
            candidate_effect="confidence_downgrade",
            reason_codes=("market_toxicity_snapshot_elevated",),
            reader_projections=(
                Build14ReaderProjection(
                    reader_name="market_toxicity_snapshot",
                    signal_family="microstructure",
                    observed_value=0.46,
                    status="elevated",
                    detail="toxicity drift detected",
                    structured_log_key="build14.market_toxicity_snapshot",
                ),
                Build14ReaderProjection(
                    reader_name="competition_monitor",
                    signal_family="risk",
                    observed_value=0.18,
                    status="nominal",
                    detail="competition remains within tolerance",
                    structured_log_key="build14.competition_monitor",
                ),
            ),
        ),
        live_light_projection=LiveLightProjection(
            status="warning",
            run_state="ready_to_execute_small",
            verdict="allowed_to_execute_small",
            micro_live_run_id="micro-run-1",
            micro_live_verdict="allowed_to_probe",
            allowed_to_execute_small=True,
            requested_total_notional_usdt=80.0,
            approved_total_notional_usdt=68.0,
            approved_pair_notional_usdt=34.0,
            execution_order_limit=3,
            planned_pairs=("BTCUSDT", "ETHUSDT"),
            planned_engines=("engine_a", "engine_b"),
            import_artifact_id="artifact-live-1",
            import_lineage_version="a.v1.0.r1",
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            blocking_reasons=(),
            build14_influence_mode="limited_influence",
            build14_action="downgrade_confidence",
            build14_severity="elevated",
            build14_summary="Build-14 limited influence reduces live-light confidence and budget",
            build14_reason_codes=("market_toxicity_snapshot_elevated",),
            build14_confidence_penalty_weight=0.10,
            build14_recommended_budget_factor=0.85,
        ),
    )

    view = build_technical_dashboard_view(payload)
    build10 = next(section for section in view.sections if section.title == "Build-10")
    system = next(section for section in view.sections if section.title == "System")
    live = next(section for section in view.sections if section.title == "Build-13 Live")
    build14 = next(section for section in view.sections if section.title == "Build-14 Enablers")

    governed = next(card for card in build10.cards if card.key == "build10_extensions")
    assert "b14=warning" in governed.value
    assert next(card for card in live.cards if card.key == "live_light_budget").detail.endswith(
        "build14=downgrade_confidence@0.85"
    )
    assert next(card for card in build14.cards if card.key == "build14_candidate_effect").value == "confidence_downgrade"
    assert next(card for card in build14.cards if card.key == "build14_guardrails").detail == "market_toxicity_snapshot_elevated"
    assert next(card for card in build14.cards if card.key == "build14_readers").value.startswith("count=2 /")
    assert next(card for card in build14.cards if card.key == "build14_reader_market_toxicity_snapshot").value == (
        "elevated (0.46)"
    )
    assert "family=microstructure" in next(
        card for card in build14.cards if card.key == "build14_reader_market_toxicity_snapshot"
    ).detail
