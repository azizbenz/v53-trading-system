"""Phase 2.5 adapter - system flow chain and operability score."""

from __future__ import annotations

from pydantic import BaseModel, Field

from cockpit.state_build1_core_health import Build1CoreHealthSnapshot
from cockpit.state_data_quality import DataQualitySnapshot
from cockpit.state_economic_sterilization import EconomicSterilizationSnapshot
from cockpit.state_engine_why import EngineWhySnapshot
from cockpit.state_feature_bridge import FeatureBridgeSnapshot
from cockpit.state_freshness import OperationalSourceSnapshot, SourceFreshnessSnapshot
from cockpit.state_kill_proof import KillProofSnapshot
from cockpit.state_queue_trace import QueueConsumptionTraceSnapshot
from cockpit.state_refusal_journal import RefusalJournalSnapshot
from cockpit.state_service_liveness import ServiceLivenessSnapshot
from cockpit.state_warmup_explainer import WarmupExplainerSnapshot


class SystemFlowStage(BaseModel, frozen=True):
    stage_name: str = Field(..., min_length=1)
    status: str = "unknown"
    detail: str = ""
    reason_codes: tuple[str, ...] = ()


class SystemOperabilityScore(BaseModel, frozen=True):
    build1_manifest_status: str = "NOT_PROVEN"
    build1_dag_status: str = "NOT_PROVEN"
    build1_guardrail_status: str = "NOT_PROVEN"
    build1_smoke_status: str = "NOT_PROVEN"
    build1_core_health_status: str = "NOT_PROVEN"
    warmup: str = "UNKNOWN"
    service: str = "OFFLINE"
    queue: str = "UNKNOWN"
    engines: str = "0/4 ACTIVE"
    economics: str = "SAMPLE_TOO_SMALL"
    scoring_cost_completeness_status: str = "UNKNOWN"
    book_depth_status: str = "BOOK_DEPTH_NOT_PROVEN"
    impact_depth_readiness_status: str = "BOOK_DEPTH_NOT_PROVEN"
    fill_realism_status: str = "FILL_REALISM_NOT_PROVEN"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
    shadow_extension_status: str = "MICRO_LIVE_BLOCKED_BY_DEPTH"
    minimum_shadow_days_required: int | None = None
    risk_input_completeness_status: str = "UNKNOWN"
    small_capital_viability_status: str = "BLOCKED_BY_BACKTEST"
    capital_profile_artifact_status: str = "CAPITAL_BUCKET_NOT_PROVEN"
    sizing_doctrine_status: str = "FIXED_FRACTION_VOL_TARGET_CAPS"
    portfolio_multi_asset_status: str = "BASELINE_CAPS_ONLY"
    executed_return_status: str = "EXECUTED_NET_RETURN_NOT_PROVEN"
    true_drawdown_status: str = "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    lineage: str = "MISSING"
    refusal_journal: str = "MISSING"
    kill_switch: str = "NOT_PROVEN"
    overall_verdict: str = "NOT_OPERABLE"


class SystemFlowSnapshot(OperationalSourceSnapshot):
    stages: tuple[SystemFlowStage, ...] = ()
    operability_score: SystemOperabilityScore = SystemOperabilityScore()


def read_system_flow(
    *,
    build1_core_health: Build1CoreHealthSnapshot | None = None,
    freshness: SourceFreshnessSnapshot,
    warmup: WarmupExplainerSnapshot,
    service_liveness: ServiceLivenessSnapshot,
    queue_trace: QueueConsumptionTraceSnapshot,
    engine_why: EngineWhySnapshot,
    economics: EconomicSterilizationSnapshot,
    feature_bridge: FeatureBridgeSnapshot,
    refusal_journal: RefusalJournalSnapshot,
    kill_proof: KillProofSnapshot,
    data_quality: DataQualitySnapshot,
) -> SystemFlowSnapshot:
    """Build a compact chain-of-proof for operator observability."""

    replay_source = next(
        (entry for entry in freshness.sources if entry.source_name == "replay_metrics"),
        freshness,
    )
    build1_snapshot = build1_core_health or Build1CoreHealthSnapshot()
    active_count = engine_why.active_count
    live_data_stale = data_quality.source_status == "stale" or any(
        row.status == "stale" for row in data_quality.pairs
    )
    market_data_passed = any(
        check.check_id == "market_data_capture" and check.status == "passed"
        for check in warmup.checks
    )
    replay_ok = replay_source.source_status in {"ok", "stale"}
    lineage_locked = feature_bridge.lineage_lock_status in {"locked", "valid", "present"}
    resolved_scoring_cost_status = (
        (
            "COST_MODEL_NOT_PROVEN"
            if economics.status == "partial"
            and economics.cost_model_completeness_status == "UNKNOWN"
            else economics.cost_model_completeness_status
        )
        if economics.scoring_cost_completeness_status == "UNKNOWN"
        else economics.scoring_cost_completeness_status
    )
    scoring_cost_complete = resolved_scoring_cost_status in {
        "COMPLETE",
        "COST_MODEL_COMPLETE",
    }
    depth_ready = economics.book_depth_source_status == "BOOK_DEPTH20_AVAILABLE"
    fill_realism_ready = economics.fill_realism_status in {
        "FILL_REALISM_PROVEN",
        "FILL_REALISM_SHADOW_MEASURED",
        "MEASURED",
        "PROVEN",
    }
    cost_parity_ready = economics.cost_parity_status in {
        "REPLAY_LIVE_COST_PARITY_PROVEN",
        "REPLAY_SHADOW_COST_PARITY_PROVEN",
    }
    capital_profiles_ready = (
        economics.capital_profile_artifact_status == "CAPITAL_BUCKET_READY"
    )
    small_capital_ready = economics.small_capital_viability_status in {"MEASURED", "PASS"}
    executed_return_ready = (
        economics.executed_only_net_return_status
        in {"EXECUTED_NET_RETURN_PROVEN", "EXECUTED_RETURN_PROVEN"}
    )
    true_drawdown_ready = (
        economics.true_drawdown_status
        in {"TRUE_NET_EQUITY_DRAWDOWN_PROVEN", "MEASURED", "PROVEN"}
    )
    portfolio_multi_asset_ready = economics.portfolio_multi_asset_status not in {
        "BASELINE_CAPS_ONLY",
        "NOT_IMPLEMENTED",
        "FUTURE_RESERVED",
        "UNKNOWN",
    }
    risk_inputs_ready = economics.risk_input_completeness_status in {
        "MEASURED",
        "GOVERNED_SOURCE",
        "NEUTRAL_BY_DESIGN",
        "COMPLETE",
    }
    scoring_readiness_partial = not (
        scoring_cost_complete
        and depth_ready
        and fill_realism_ready
        and cost_parity_ready
        and not economics.shadow_extension_required
        and capital_profiles_ready
        and small_capital_ready
        and executed_return_ready
        and true_drawdown_ready
        and portfolio_multi_asset_ready
        and risk_inputs_ready
    )
    if feature_bridge.source_status != "ok":
        feature_status = "red"
    elif not lineage_locked or not feature_bridge.runtime_consumption_proven:
        feature_status = "yellow"
    else:
        feature_status = "green"
    engine_status = "green" if active_count > 0 and any(row.records > 0 for row in engine_why.engines) else "red"
    if active_count > 0 and any(row.status == "dormant" for row in engine_why.engines if row.engine_id in {"engine_c", "engine_d"}):
        engine_status = "yellow"
    if queue_trace.consumption_status == "consumed_by_service":
        queue_stage_status = "green"
    elif queue_trace.command_queue_snapshot_present:
        queue_stage_status = "yellow"
    else:
        queue_stage_status = "red"
    if service_liveness.control_ready:
        service_stage_status = "green"
    elif service_liveness.shadow_service_running:
        service_stage_status = "yellow"
    else:
        service_stage_status = "red"
    cockpit_actions_status = (
        "green"
        if kill_proof.kill_switch_status.startswith("PROVEN")
        or queue_trace.consumption_status == "consumed_by_service"
        else ("yellow" if queue_trace.command_queue_snapshot_present else "red")
    )
    stages_list: list[SystemFlowStage] = []
    if build1_core_health is not None:
        stages_list.append(
            SystemFlowStage(
                stage_name="Build-1 Core",
                status=(
                    "green"
                    if build1_snapshot.build1_core_health_status == "PASS"
                    else "red"
                ),
                detail=(
                    f"manifest={build1_snapshot.build1_manifest_status} / "
                    f"dag={build1_snapshot.build1_dag_status} / "
                    f"guardrails={build1_snapshot.build1_guardrail_status} / "
                    f"smoke={build1_snapshot.build1_smoke_status}"
                ),
                reason_codes=build1_snapshot.reason_codes
                or (build1_snapshot.build1_core_health_status,),
            )
        )
    stages_list.extend(
        (
            SystemFlowStage(
                stage_name="Market Data Capture",
                status=(
                    "green"
                    if warmup.readiness_status == "passed" and market_data_passed
                    else ("yellow" if market_data_passed else "red")
                ),
                detail=f"{warmup.final_state} / eligible={warmup.eligible_to_trade}",
                reason_codes=(
                    ("market_data_capture_passed",)
                    if market_data_passed
                    else ("market_data_capture_not_proven",)
                ),
            ),
            SystemFlowStage(
                stage_name="Replay Metrics",
                status="green" if replay_ok else "red",
                detail="Latest replay metrics export freshness",
                reason_codes=replay_source.reason_codes,
            ),
            SystemFlowStage(
                stage_name="Feature Bridge",
                status=feature_status,
                detail=(
                    feature_bridge.feature_to_engine_path
                    or f"artifact={feature_bridge.artifact_presence_status} / runtime={feature_bridge.runtime_consumption_status}"
                ),
                reason_codes=feature_bridge.lineage_lock_reasons
                + ((feature_bridge.runtime_consumption_status,) if not feature_bridge.runtime_consumption_proven else ()),
            ),
            SystemFlowStage(
                stage_name="Engines",
                status=engine_status,
                detail=f"{active_count}/4 active",
                reason_codes=tuple(
                    row.engine_id for row in engine_why.engines if row.status in {"dormant", "suspended"}
                ),
            ),
            SystemFlowStage(
                stage_name="Scoring",
                status=(
                    "red"
                    if economics.status == "critical"
                    else (
                        "yellow"
                        if economics.status in {
                            "watch",
                            "partial",
                            "insufficient_sample",
                            "placeholder",
                            "stale",
                        }
                        or scoring_readiness_partial
                        else ("red" if economics.ce_net <= 0.0 else "green")
                    )
                ),
                detail=(
                    f"expected_ce_net={economics.ce_net:.4f} / "
                    f"executed_return={economics.executed_only_net_return_status} / "
                    f"sterilization={economics.economic_sterilization_ratio:.2f} / "
                    f"cost={resolved_scoring_cost_status} / "
                    f"depth={economics.book_depth_source_status} / "
                    f"fill={economics.fill_realism_status} / "
                    f"parity={economics.cost_parity_status} / "
                    f"shadow_days={economics.minimum_shadow_days_required if economics.minimum_shadow_days_required is not None else 'n/a'} / "
                    f"small_capital={economics.small_capital_viability_status} / "
                    f"capital_profiles={economics.capital_profile_artifact_status} / "
                    f"drawdown={economics.true_drawdown_status} / "
                    f"portfolio={economics.portfolio_multi_asset_status}"
                ),
                reason_codes=economics.reason_codes,
            ),
            SystemFlowStage(
                stage_name="Queue",
                status=queue_stage_status,
                detail=queue_trace.consumption_status,
                reason_codes=queue_trace.reason_codes,
            ),
            SystemFlowStage(
                stage_name="VPS Service",
                status=service_stage_status,
                detail=service_liveness.service_status,
                reason_codes=service_liveness.reason_codes,
            ),
            SystemFlowStage(
                stage_name="Cockpit Actions",
                status=cockpit_actions_status,
                detail=kill_proof.kill_switch_status,
                reason_codes=kill_proof.reason_codes,
            ),
        )
    )
    economics_label = (
        "SAMPLE_TOO_SMALL"
        if economics.status == "insufficient_sample"
        else (
                    "REPLAY_ECONOMICS_NOT_MEASURED"
                    if economics.status in {"placeholder", "stale"}
                    else (
                        economics.book_depth_source_status
                        if economics.book_depth_source_status in {
                            "BOOK_DEPTH_MISSING",
                            "BOOK_DEPTH_STALE",
                            "BOOK_DEPTH_NOT_PROVEN",
                        }
                        else (
                            economics.impact_depth_readiness_status
                            if economics.impact_depth_readiness_status in {
                                "LIMITED_DEPTH_PARTIAL",
                                "TOP_OF_BOOK_PROXY_ONLY",
                            }
                            else (
                                "SHADOW_EXTENDED_REQUIRED"
                                if economics.shadow_extension_required
                                else (
                                    economics.capital_profile_artifact_status
                                    if not capital_profiles_ready
                                    else (
                                    "FILL_REALISM_NOT_PROVEN"
                                    if not fill_realism_ready
                                    else (
                                        "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
                                        if not cost_parity_ready
                                        else (
                        "COST_MODEL_PARTIAL"
                        if economics.status == "partial"
                        else (
                            "COST_MODEL_PARTIAL"
                            if not scoring_cost_complete
                    else (
                        "SMALL_CAPITAL_NOT_PROVEN"
                        if not small_capital_ready
                        else (
                            "EXECUTED_RETURN_NOT_PROVEN"
                            if not executed_return_ready
                            else (
                                "TRUE_DRAWDOWN_NOT_PROVEN"
                                if not true_drawdown_ready
                                else (
                                    "PORTFOLIO_BASELINE_CAPS_ONLY"
                                    if not portfolio_multi_asset_ready
                                    else (
                                        "RISK_INPUTS_UNKNOWN"
                                        if not risk_inputs_ready
                                        else (
                                            "CE_NET_POSITIVE"
                                            if economics.status == "ok" and economics.ce_net > 0.0
                                            else "CE_NET_NEGATIVE"
                                        )
                                    )
                                )
                            )
                        )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
            )
        )
    )
    lineage_label = "LOCKED" if lineage_locked else "MISSING"
    refusal_label = "PERSISTED" if refusal_journal.source_status == "ok" else "MISSING"
    kill_label = "PROVEN" if kill_proof.kill_switch_status.startswith("PROVEN") else "NOT_PROVEN"
    if (
        build1_core_health is not None
        and build1_snapshot.build1_core_health_status != "PASS"
    ):
        overall = "NOT_OPERABLE"
    elif warmup.readiness_status != "passed" or not service_liveness.control_ready:
        overall = "NOT_OPERABLE"
    elif queue_trace.consumption_status != "consumed_by_service":
        overall = "SHADOW_THIN"
    elif (
        lineage_label == "MISSING"
        or refusal_label == "MISSING"
        or kill_label == "NOT_PROVEN"
        or live_data_stale
    ):
        overall = "SHADOW_THIN"
    elif economics_label != "CE_NET_POSITIVE":
        overall = "SHADOW_THIN"
    elif active_count >= 2:
        overall = "SHADOW_READY"
    else:
        overall = "SHADOW_THIN"
    queue_label = {
        "consumed_by_service": "CONSUMED",
        "queue_only": "QUEUE_ONLY",
        "not_configured": "NOT_CONFIGURED",
        "unknown": "UNKNOWN",
    }.get(queue_trace.consumption_status, "UNKNOWN")
    operability_score = SystemOperabilityScore(
        build1_manifest_status=build1_snapshot.build1_manifest_status,
        build1_dag_status=build1_snapshot.build1_dag_status,
        build1_guardrail_status=build1_snapshot.build1_guardrail_status,
        build1_smoke_status=build1_snapshot.build1_smoke_status,
        build1_core_health_status=build1_snapshot.build1_core_health_status,
        warmup="PASSED" if warmup.readiness_status == "passed" else "BLOCKED",
        service="ONLINE" if service_liveness.control_ready else "OFFLINE",
        queue=queue_label,
        engines=f"{active_count}/4 ACTIVE",
        economics=economics_label,
        scoring_cost_completeness_status=resolved_scoring_cost_status,
        book_depth_status=economics.book_depth_source_status,
        impact_depth_readiness_status=economics.impact_depth_readiness_status,
        fill_realism_status=economics.fill_realism_status,
        cost_parity_status=economics.cost_parity_status,
        shadow_extension_status=economics.shadow_extension_status,
        minimum_shadow_days_required=economics.minimum_shadow_days_required,
        risk_input_completeness_status=economics.risk_input_completeness_status,
        small_capital_viability_status=economics.small_capital_viability_status,
        capital_profile_artifact_status=economics.capital_profile_artifact_status,
        sizing_doctrine_status=economics.sizing_doctrine_status,
        portfolio_multi_asset_status=(
            f"{economics.portfolio_multi_asset_status} / {economics.covariance_model_status}"
        ),
        executed_return_status=economics.executed_only_net_return_status,
        true_drawdown_status=economics.true_drawdown_status,
        lineage=lineage_label,
        refusal_journal=refusal_label,
        kill_switch=kill_label,
        overall_verdict=overall,
    )
    return SystemFlowSnapshot(
        source_status=service_liveness.source_status,
        source_file=service_liveness.source_file,
        last_modified_at=service_liveness.last_modified_at,
        age_seconds=service_liveness.age_seconds,
        reason_codes=service_liveness.reason_codes,
        stages=tuple(stages_list),
        operability_score=operability_score,
    )


__all__ = [
    "SystemFlowSnapshot",
    "SystemFlowStage",
    "SystemOperabilityScore",
    "read_system_flow",
]
