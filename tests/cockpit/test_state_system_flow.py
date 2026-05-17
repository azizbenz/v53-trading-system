from __future__ import annotations

from cockpit.state_data_quality import DataQualitySnapshot
from cockpit.state_build1_core_health import Build1CoreHealthSnapshot
from cockpit.state_economic_sterilization import EconomicSterilizationSnapshot
from cockpit.state_engine_why import EngineWhyRow, EngineWhySnapshot
from cockpit.state_feature_bridge import FeatureBridgeSnapshot
from cockpit.state_freshness import SourceFreshnessEntry, SourceFreshnessSnapshot
from cockpit.state_kill_proof import KillProofSnapshot
from cockpit.state_queue_trace import QueueConsumptionTraceSnapshot
from cockpit.state_refusal_journal import RefusalJournalSnapshot
from cockpit.state_service_liveness import ServiceLivenessSnapshot
from cockpit.state_system_flow import read_system_flow
from cockpit.state_warmup_explainer import WarmupExplainerCheck, WarmupExplainerSnapshot


def test_system_flow_flags_lineage_missing_and_shadow_ready_only_when_operable() -> None:
    snapshot = read_system_flow(
        freshness=SourceFreshnessSnapshot(
            source_status="ok",
            sources=(
                SourceFreshnessEntry(
                    source_name="replay_metrics",
                    status="ok",
                    source_status="ok",
                    exists=True,
                ),
            ),
        ),
        warmup=WarmupExplainerSnapshot(
            source_status="ok",
            final_state="ready",
            eligible_to_trade=True,
            readiness_status="passed",
            required_checks_passed=True,
            checks=(
                WarmupExplainerCheck(check_id="bootstrap_reconciliation", status="passed"),
                WarmupExplainerCheck(check_id="remote_account_state", status="passed"),
                WarmupExplainerCheck(check_id="time_sync", status="passed"),
                WarmupExplainerCheck(check_id="market_data_capture", status="passed"),
                WarmupExplainerCheck(check_id="binance_credentials", status="passed"),
            ),
        ),
        service_liveness=ServiceLivenessSnapshot(
            source_status="ok",
            shadow_service_running=True,
            control_ready=True,
            service_status="running",
        ),
        queue_trace=QueueConsumptionTraceSnapshot(
            source_status="ok",
            command_queue_snapshot_present=True,
            consumption_status="consumed_by_service",
        ),
        engine_why=EngineWhySnapshot(
            source_status="ok",
            active_count=2,
            engines=(
                EngineWhyRow(engine_id="engine_a", status="active", records=10),
                EngineWhyRow(engine_id="engine_b", status="active", records=10),
                EngineWhyRow(engine_id="engine_c", status="dormant", records=0),
                EngineWhyRow(engine_id="engine_d", status="dormant", records=0),
            ),
        ),
        economics=EconomicSterilizationSnapshot(
            source_status="ok",
            economic_sterilization_ratio=0.20,
            status="ok",
        ),
        feature_bridge=FeatureBridgeSnapshot(
            source_status="ok",
            lineage_lock_status="missing",
            lineage_lock_reasons=("feature lineage lock is required",),
        ),
        refusal_journal=RefusalJournalSnapshot(source_status="missing"),
        kill_proof=KillProofSnapshot(source_status="ok", kill_switch_status="NOT_PROVEN"),
        data_quality=DataQualitySnapshot(source_status="ok", pairs=()),
    )
    feature_stage = next(stage for stage in snapshot.stages if stage.stage_name == "Feature Bridge")
    assert feature_stage.status == "yellow"
    assert snapshot.operability_score.overall_verdict == "SHADOW_THIN"


def test_system_flow_marks_service_offline_as_not_operable() -> None:
    snapshot = read_system_flow(
        freshness=SourceFreshnessSnapshot(source_status="ok", sources=()),
        warmup=WarmupExplainerSnapshot(
            source_status="ok",
            final_state="blocked",
            eligible_to_trade=False,
            readiness_status="blocked",
            checks=(),
        ),
        service_liveness=ServiceLivenessSnapshot(
            source_status="stale",
            shadow_service_running=False,
            control_ready=False,
            archive_reader_only=True,
            service_status="offline",
        ),
        queue_trace=QueueConsumptionTraceSnapshot(source_status="ok", consumption_status="not_configured"),
        engine_why=EngineWhySnapshot(source_status="ok", active_count=0, engines=()),
        economics=EconomicSterilizationSnapshot(source_status="ok", status="insufficient_sample"),
        feature_bridge=FeatureBridgeSnapshot(source_status="missing"),
        refusal_journal=RefusalJournalSnapshot(source_status="missing"),
        kill_proof=KillProofSnapshot(source_status="not_yet_persisted"),
        data_quality=DataQualitySnapshot(source_status="ok", pairs=()),
    )
    service_stage = next(stage for stage in snapshot.stages if stage.stage_name == "VPS Service")
    assert service_stage.status == "red"
    assert snapshot.operability_score.overall_verdict == "NOT_OPERABLE"


def test_system_flow_keeps_placeholder_replay_economics_out_of_green() -> None:
    snapshot = read_system_flow(
        freshness=SourceFreshnessSnapshot(
            source_status="ok",
            sources=(
                SourceFreshnessEntry(
                    source_name="replay_metrics",
                    status="ok",
                    source_status="ok",
                    exists=True,
                ),
            ),
        ),
        warmup=WarmupExplainerSnapshot(
            source_status="ok",
            final_state="ready",
            eligible_to_trade=True,
            readiness_status="passed",
            required_checks_passed=True,
            checks=(WarmupExplainerCheck(check_id="market_data_capture", status="passed"),),
        ),
        service_liveness=ServiceLivenessSnapshot(
            source_status="ok",
            shadow_service_running=True,
            control_ready=True,
            service_status="running",
        ),
        queue_trace=QueueConsumptionTraceSnapshot(
            source_status="ok",
            command_queue_snapshot_present=True,
            consumption_status="consumed_by_service",
        ),
        engine_why=EngineWhySnapshot(
            source_status="ok",
            active_count=2,
            engines=(
                EngineWhyRow(engine_id="engine_a", status="active", records=10),
                EngineWhyRow(engine_id="engine_b", status="active", records=10),
            ),
        ),
        economics=EconomicSterilizationSnapshot(
            source_status="ok",
            ce_net=0.001,
            economic_sterilization_ratio=0.10,
            status="placeholder",
            capital_profile_artifact_status="CAPITAL_BUCKET_READY",
        ),
        feature_bridge=FeatureBridgeSnapshot(
            source_status="ok",
            lineage_lock_status="locked",
            lineage_lock_reasons=(),
        ),
        refusal_journal=RefusalJournalSnapshot(source_status="ok"),
        kill_proof=KillProofSnapshot(source_status="ok", kill_switch_status="PROVEN_NOT_ARMED"),
        data_quality=DataQualitySnapshot(source_status="ok", pairs=()),
    )

    scoring_stage = next(stage for stage in snapshot.stages if stage.stage_name == "Scoring")
    assert scoring_stage.status == "yellow"
    assert snapshot.operability_score.economics == "REPLAY_ECONOMICS_NOT_MEASURED"
    assert snapshot.operability_score.overall_verdict == "SHADOW_THIN"


def test_system_flow_keeps_partial_cost_model_out_of_green() -> None:
    snapshot = read_system_flow(
        freshness=SourceFreshnessSnapshot(
            source_status="ok",
            sources=(
                SourceFreshnessEntry(
                    source_name="replay_metrics",
                    status="ok",
                    source_status="ok",
                    exists=True,
                ),
            ),
        ),
        warmup=WarmupExplainerSnapshot(
            source_status="ok",
            final_state="ready",
            eligible_to_trade=True,
            readiness_status="passed",
            required_checks_passed=True,
            checks=(WarmupExplainerCheck(check_id="market_data_capture", status="passed"),),
        ),
        service_liveness=ServiceLivenessSnapshot(
            source_status="ok",
            shadow_service_running=True,
            control_ready=True,
            service_status="running",
        ),
        queue_trace=QueueConsumptionTraceSnapshot(
            source_status="ok",
            command_queue_snapshot_present=True,
            consumption_status="consumed_by_service",
        ),
        engine_why=EngineWhySnapshot(
            source_status="ok",
            active_count=2,
            engines=(
                EngineWhyRow(engine_id="engine_a", status="active", records=10),
                EngineWhyRow(engine_id="engine_b", status="active", records=10),
            ),
        ),
        economics=EconomicSterilizationSnapshot(
            source_status="ok",
            ce_net=0.001,
            economic_sterilization_ratio=0.10,
            status="partial",
            reason_codes=("REPLAY_COST_MODEL_PARTIAL",),
            capital_profile_artifact_status="CAPITAL_BUCKET_READY",
            book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
            impact_depth_readiness_status="DEPTH20_AVAILABLE",
            shadow_extension_required=False,
            shadow_extension_status="SHADOW_STANDARD_30D",
            fill_realism_status="FILL_REALISM_PROVEN",
            cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
        ),
        feature_bridge=FeatureBridgeSnapshot(
            source_status="ok",
            lineage_lock_status="locked",
            lineage_lock_reasons=(),
        ),
        refusal_journal=RefusalJournalSnapshot(source_status="ok"),
        kill_proof=KillProofSnapshot(source_status="ok", kill_switch_status="PROVEN_NOT_ARMED"),
        data_quality=DataQualitySnapshot(source_status="ok", pairs=()),
    )

    scoring_stage = next(stage for stage in snapshot.stages if stage.stage_name == "Scoring")
    assert scoring_stage.status == "yellow"
    assert snapshot.operability_score.economics == "COST_MODEL_PARTIAL"
    assert snapshot.operability_score.scoring_cost_completeness_status == "COST_MODEL_NOT_PROVEN"
    assert snapshot.operability_score.overall_verdict == "SHADOW_THIN"


def test_system_flow_keeps_artifact_only_feature_bridge_out_of_green() -> None:
    snapshot = read_system_flow(
        freshness=SourceFreshnessSnapshot(source_status="ok", sources=()),
        warmup=WarmupExplainerSnapshot(
            source_status="ok",
            final_state="ready",
            eligible_to_trade=True,
            readiness_status="passed",
            required_checks_passed=True,
            checks=(WarmupExplainerCheck(check_id="market_data_capture", status="passed"),),
        ),
        service_liveness=ServiceLivenessSnapshot(
            source_status="ok",
            shadow_service_running=True,
            control_ready=True,
            service_status="running",
        ),
        queue_trace=QueueConsumptionTraceSnapshot(
            source_status="ok",
            command_queue_snapshot_present=True,
            consumption_status="consumed_by_service",
        ),
        engine_why=EngineWhySnapshot(
            source_status="ok",
            active_count=2,
            engines=(
                EngineWhyRow(engine_id="engine_c", status="active", records=10),
                EngineWhyRow(engine_id="engine_d", status="active", records=10),
            ),
        ),
        economics=EconomicSterilizationSnapshot(
            source_status="ok",
            status="ok",
            ce_net=0.01,
            economic_sterilization_ratio=0.10,
        ),
        feature_bridge=FeatureBridgeSnapshot(
            source_status="ok",
            artifact_presence_status="ARTIFACT_PRESENT_ONLY",
            runtime_consumption_status="NOT_PROVEN",
            runtime_active=False,
            lineage_lock_status="locked",
            lineage_lock_reasons=(),
        ),
        refusal_journal=RefusalJournalSnapshot(source_status="ok"),
        kill_proof=KillProofSnapshot(source_status="ok", kill_switch_status="PROVEN_NOT_ARMED"),
        data_quality=DataQualitySnapshot(source_status="ok", pairs=()),
    )

    feature_stage = next(stage for stage in snapshot.stages if stage.stage_name == "Feature Bridge")
    assert feature_stage.status == "yellow"
    assert "NOT_PROVEN" in feature_stage.reason_codes


def test_system_flow_keeps_small_capital_not_proven_out_of_green() -> None:
    snapshot = read_system_flow(
        freshness=SourceFreshnessSnapshot(source_status="ok", sources=()),
        warmup=WarmupExplainerSnapshot(
            source_status="ok",
            final_state="ready",
            eligible_to_trade=True,
            readiness_status="passed",
            required_checks_passed=True,
            checks=(WarmupExplainerCheck(check_id="market_data_capture", status="passed"),),
        ),
        service_liveness=ServiceLivenessSnapshot(
            source_status="ok",
            shadow_service_running=True,
            control_ready=True,
            service_status="running",
        ),
        queue_trace=QueueConsumptionTraceSnapshot(
            source_status="ok",
            command_queue_snapshot_present=True,
            consumption_status="consumed_by_service",
        ),
        engine_why=EngineWhySnapshot(
            source_status="ok",
            active_count=2,
            engines=(
                EngineWhyRow(engine_id="engine_a", status="active", records=10),
                EngineWhyRow(engine_id="engine_b", status="active", records=10),
            ),
        ),
        economics=EconomicSterilizationSnapshot(
            source_status="ok",
            ce_net=0.01,
            economic_sterilization_ratio=0.10,
            status="ok",
            cost_model_completeness_status="COST_MODEL_COMPLETE",
            scoring_cost_completeness_status="COST_MODEL_COMPLETE",
            book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
            impact_depth_readiness_status="DEPTH20_AVAILABLE",
            shadow_extension_required=False,
            shadow_extension_status="SHADOW_STANDARD_30D",
            fill_realism_status="FILL_REALISM_PROVEN",
            cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
            risk_input_completeness_status="MEASURED",
            small_capital_viability_status="NOT_PROVEN",
            min_notional_viability_status="MEASURED",
            capital_fragmentation_status="MEASURED",
            capital_profile_artifact_status="CAPITAL_BUCKET_READY",
            sizing_doctrine_status="FIXED_FRACTION_VOL_TARGET_CAPS",
            portfolio_multi_asset_status="FULLY_PROVEN",
            covariance_model_status="EXPLICIT",
            executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
            true_drawdown_status="TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
        ),
        feature_bridge=FeatureBridgeSnapshot(
            source_status="ok",
            lineage_lock_status="locked",
            lineage_lock_reasons=(),
            runtime_consumption_proven=True,
        ),
        refusal_journal=RefusalJournalSnapshot(source_status="ok"),
        kill_proof=KillProofSnapshot(source_status="ok", kill_switch_status="PROVEN_NOT_ARMED"),
        data_quality=DataQualitySnapshot(source_status="ok", pairs=()),
    )

    scoring_stage = next(stage for stage in snapshot.stages if stage.stage_name == "Scoring")
    assert scoring_stage.status == "yellow"
    assert snapshot.operability_score.economics == "SMALL_CAPITAL_NOT_PROVEN"
    assert snapshot.operability_score.small_capital_viability_status == "NOT_PROVEN"
    assert snapshot.operability_score.overall_verdict == "SHADOW_THIN"


def test_system_flow_keeps_missing_true_drawdown_out_of_green() -> None:
    snapshot = read_system_flow(
        freshness=SourceFreshnessSnapshot(source_status="ok", sources=()),
        warmup=WarmupExplainerSnapshot(
            source_status="ok",
            final_state="ready",
            eligible_to_trade=True,
            readiness_status="passed",
            required_checks_passed=True,
            checks=(WarmupExplainerCheck(check_id="market_data_capture", status="passed"),),
        ),
        service_liveness=ServiceLivenessSnapshot(
            source_status="ok",
            shadow_service_running=True,
            control_ready=True,
            service_status="running",
        ),
        queue_trace=QueueConsumptionTraceSnapshot(
            source_status="ok",
            command_queue_snapshot_present=True,
            consumption_status="consumed_by_service",
        ),
        engine_why=EngineWhySnapshot(
            source_status="ok",
            active_count=2,
            engines=(
                EngineWhyRow(engine_id="engine_a", status="active", records=10),
                EngineWhyRow(engine_id="engine_b", status="active", records=10),
            ),
        ),
        economics=EconomicSterilizationSnapshot(
            source_status="ok",
            ce_net=0.01,
            economic_sterilization_ratio=0.10,
            status="ok",
            cost_model_completeness_status="COST_MODEL_COMPLETE",
            scoring_cost_completeness_status="COST_MODEL_COMPLETE",
            book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
            impact_depth_readiness_status="DEPTH20_AVAILABLE",
            shadow_extension_required=False,
            shadow_extension_status="SHADOW_STANDARD_30D",
            fill_realism_status="FILL_REALISM_PROVEN",
            cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
            risk_input_completeness_status="MEASURED",
            small_capital_viability_status="MEASURED",
            min_notional_viability_status="MEASURED",
            capital_fragmentation_status="MEASURED",
            capital_profile_artifact_status="CAPITAL_BUCKET_READY",
            sizing_doctrine_status="FIXED_FRACTION_VOL_TARGET_CAPS",
            portfolio_multi_asset_status="FULLY_PROVEN",
            covariance_model_status="EXPLICIT",
            executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
            true_drawdown_status="TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN",
        ),
        feature_bridge=FeatureBridgeSnapshot(
            source_status="ok",
            lineage_lock_status="locked",
            lineage_lock_reasons=(),
            runtime_consumption_proven=True,
        ),
        refusal_journal=RefusalJournalSnapshot(source_status="ok"),
        kill_proof=KillProofSnapshot(source_status="ok", kill_switch_status="PROVEN_NOT_ARMED"),
        data_quality=DataQualitySnapshot(source_status="ok", pairs=()),
    )

    scoring_stage = next(stage for stage in snapshot.stages if stage.stage_name == "Scoring")
    assert scoring_stage.status == "yellow"
    assert snapshot.operability_score.economics == "TRUE_DRAWDOWN_NOT_PROVEN"
    assert (
        snapshot.operability_score.true_drawdown_status
        == "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    )
    assert snapshot.operability_score.overall_verdict == "SHADOW_THIN"


def test_system_flow_keeps_baseline_portfolio_caps_out_of_full_risk_green() -> None:
    snapshot = read_system_flow(
        freshness=SourceFreshnessSnapshot(source_status="ok", sources=()),
        warmup=WarmupExplainerSnapshot(
            source_status="ok",
            final_state="ready",
            eligible_to_trade=True,
            readiness_status="passed",
            required_checks_passed=True,
            checks=(WarmupExplainerCheck(check_id="market_data_capture", status="passed"),),
        ),
        service_liveness=ServiceLivenessSnapshot(
            source_status="ok",
            shadow_service_running=True,
            control_ready=True,
            service_status="running",
        ),
        queue_trace=QueueConsumptionTraceSnapshot(
            source_status="ok",
            command_queue_snapshot_present=True,
            consumption_status="consumed_by_service",
        ),
        engine_why=EngineWhySnapshot(
            source_status="ok",
            active_count=2,
            engines=(
                EngineWhyRow(engine_id="engine_a", status="active", records=10),
                EngineWhyRow(engine_id="engine_b", status="active", records=10),
            ),
        ),
        economics=EconomicSterilizationSnapshot(
            source_status="ok",
            ce_net=0.01,
            economic_sterilization_ratio=0.10,
            status="ok",
            cost_model_completeness_status="COST_MODEL_COMPLETE",
            scoring_cost_completeness_status="COST_MODEL_COMPLETE",
            book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
            impact_depth_readiness_status="DEPTH20_AVAILABLE",
            shadow_extension_required=False,
            shadow_extension_status="SHADOW_STANDARD_30D",
            fill_realism_status="FILL_REALISM_PROVEN",
            cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
            risk_input_completeness_status="MEASURED",
            small_capital_viability_status="MEASURED",
            min_notional_viability_status="MEASURED",
            capital_fragmentation_status="MEASURED",
            capital_profile_artifact_status="CAPITAL_BUCKET_READY",
            sizing_doctrine_status="FIXED_FRACTION_VOL_TARGET_CAPS",
            portfolio_multi_asset_status="BASELINE_CAPS_ONLY",
            covariance_model_status="NOT_IMPLEMENTED",
            executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
            true_drawdown_status="TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
        ),
        feature_bridge=FeatureBridgeSnapshot(
            source_status="ok",
            lineage_lock_status="locked",
            lineage_lock_reasons=(),
            runtime_consumption_proven=True,
        ),
        refusal_journal=RefusalJournalSnapshot(source_status="ok"),
        kill_proof=KillProofSnapshot(source_status="ok", kill_switch_status="PROVEN_NOT_ARMED"),
        data_quality=DataQualitySnapshot(source_status="ok", pairs=()),
    )

    scoring_stage = next(stage for stage in snapshot.stages if stage.stage_name == "Scoring")
    assert scoring_stage.status == "yellow"
    assert snapshot.operability_score.economics == "PORTFOLIO_BASELINE_CAPS_ONLY"
    assert "BASELINE_CAPS_ONLY" in snapshot.operability_score.portfolio_multi_asset_status
    assert snapshot.operability_score.overall_verdict == "SHADOW_THIN"


def test_system_flow_projects_build1_core_health_and_blocks_when_red() -> None:
    snapshot = read_system_flow(
        build1_core_health=Build1CoreHealthSnapshot(
            source_status="ok",
            build1_manifest_status="PASS",
            build1_dag_status="PASS",
            build1_guardrail_status="FAIL",
            build1_smoke_status="FAIL",
            build1_core_health_status="BLOCKED",
            reason_codes=("engineering_guardrails:new_violations",),
        ),
        freshness=SourceFreshnessSnapshot(source_status="ok", sources=()),
        warmup=WarmupExplainerSnapshot(
            source_status="ok",
            final_state="ready",
            eligible_to_trade=True,
            readiness_status="passed",
            required_checks_passed=True,
            checks=(WarmupExplainerCheck(check_id="market_data_capture", status="passed"),),
        ),
        service_liveness=ServiceLivenessSnapshot(
            source_status="ok",
            shadow_service_running=True,
            control_ready=True,
            service_status="running",
        ),
        queue_trace=QueueConsumptionTraceSnapshot(
            source_status="ok",
            command_queue_snapshot_present=True,
            consumption_status="consumed_by_service",
        ),
        engine_why=EngineWhySnapshot(
            source_status="ok",
            active_count=2,
            engines=(
                EngineWhyRow(engine_id="engine_a", status="active", records=10),
                EngineWhyRow(engine_id="engine_b", status="active", records=10),
            ),
        ),
        economics=EconomicSterilizationSnapshot(
            source_status="ok",
            ce_net=0.01,
            economic_sterilization_ratio=0.10,
            status="ok",
            cost_model_completeness_status="COST_MODEL_COMPLETE",
            scoring_cost_completeness_status="COST_MODEL_COMPLETE",
            book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
            impact_depth_readiness_status="DEPTH20_AVAILABLE",
            shadow_extension_required=False,
            shadow_extension_status="SHADOW_STANDARD_30D",
            fill_realism_status="FILL_REALISM_PROVEN",
            cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
            risk_input_completeness_status="MEASURED",
            small_capital_viability_status="MEASURED",
            min_notional_viability_status="MEASURED",
            capital_fragmentation_status="MEASURED",
            capital_profile_artifact_status="CAPITAL_BUCKET_READY",
            sizing_doctrine_status="FIXED_FRACTION_VOL_TARGET_CAPS",
            portfolio_multi_asset_status="FULLY_PROVEN",
            covariance_model_status="EXPLICIT",
            executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
            true_drawdown_status="TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
        ),
        feature_bridge=FeatureBridgeSnapshot(
            source_status="ok",
            lineage_lock_status="locked",
            lineage_lock_reasons=(),
            runtime_consumption_proven=True,
        ),
        refusal_journal=RefusalJournalSnapshot(source_status="ok"),
        kill_proof=KillProofSnapshot(source_status="ok", kill_switch_status="PROVEN_NOT_ARMED"),
        data_quality=DataQualitySnapshot(source_status="ok", pairs=()),
    )

    build1_stage = next(stage for stage in snapshot.stages if stage.stage_name == "Build-1 Core")
    assert build1_stage.status == "red"
    assert snapshot.operability_score.build1_guardrail_status == "FAIL"
    assert snapshot.operability_score.build1_core_health_status == "BLOCKED"
    assert snapshot.operability_score.overall_verdict == "NOT_OPERABLE"


def test_system_flow_keeps_missing_executed_return_out_of_green() -> None:
    snapshot = read_system_flow(
        freshness=SourceFreshnessSnapshot(source_status="ok", sources=()),
        warmup=WarmupExplainerSnapshot(
            source_status="ok",
            final_state="ready",
            eligible_to_trade=True,
            readiness_status="passed",
            required_checks_passed=True,
            checks=(WarmupExplainerCheck(check_id="market_data_capture", status="passed"),),
        ),
        service_liveness=ServiceLivenessSnapshot(
            source_status="ok",
            shadow_service_running=True,
            control_ready=True,
            service_status="running",
        ),
        queue_trace=QueueConsumptionTraceSnapshot(
            source_status="ok",
            command_queue_snapshot_present=True,
            consumption_status="consumed_by_service",
        ),
        engine_why=EngineWhySnapshot(
            source_status="ok",
            active_count=2,
            engines=(
                EngineWhyRow(engine_id="engine_a", status="active", records=10),
                EngineWhyRow(engine_id="engine_b", status="active", records=10),
            ),
        ),
        economics=EconomicSterilizationSnapshot(
            source_status="ok",
            ce_net=0.01,
            economic_sterilization_ratio=0.10,
            status="ok",
            cost_model_completeness_status="COST_MODEL_COMPLETE",
            scoring_cost_completeness_status="COST_MODEL_COMPLETE",
            book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
            impact_depth_readiness_status="DEPTH20_AVAILABLE",
            shadow_extension_required=False,
            shadow_extension_status="SHADOW_STANDARD_30D",
            fill_realism_status="FILL_REALISM_PROVEN",
            cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
            risk_input_completeness_status="MEASURED",
            small_capital_viability_status="MEASURED",
            min_notional_viability_status="MEASURED",
            capital_fragmentation_status="MEASURED",
            capital_profile_artifact_status="CAPITAL_BUCKET_READY",
            sizing_doctrine_status="FIXED_FRACTION_VOL_TARGET_CAPS",
            portfolio_multi_asset_status="FULLY_PROVEN",
            covariance_model_status="EXPLICIT",
            executed_only_net_return_status="EXECUTED_NET_RETURN_NOT_PROVEN",
            true_drawdown_status="TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
        ),
        feature_bridge=FeatureBridgeSnapshot(
            source_status="ok",
            lineage_lock_status="locked",
            lineage_lock_reasons=(),
            runtime_consumption_proven=True,
        ),
        refusal_journal=RefusalJournalSnapshot(source_status="ok"),
        kill_proof=KillProofSnapshot(source_status="ok", kill_switch_status="PROVEN_NOT_ARMED"),
        data_quality=DataQualitySnapshot(source_status="ok", pairs=()),
    )

    scoring_stage = next(stage for stage in snapshot.stages if stage.stage_name == "Scoring")
    assert scoring_stage.status == "yellow"
    assert snapshot.operability_score.economics == "EXECUTED_RETURN_NOT_PROVEN"
    assert (
        snapshot.operability_score.executed_return_status
        == "EXECUTED_NET_RETURN_NOT_PROVEN"
    )
    assert snapshot.operability_score.overall_verdict == "SHADOW_THIN"


def test_system_flow_projects_limited_depth_and_parity_as_non_green() -> None:
    snapshot = read_system_flow(
        freshness=SourceFreshnessSnapshot(source_status="ok", sources=()),
        warmup=WarmupExplainerSnapshot(
            source_status="ok",
            final_state="ready",
            eligible_to_trade=True,
            readiness_status="passed",
            required_checks_passed=True,
            checks=(WarmupExplainerCheck(check_id="market_data_capture", status="passed"),),
        ),
        service_liveness=ServiceLivenessSnapshot(
            source_status="ok",
            shadow_service_running=True,
            control_ready=True,
            service_status="running",
        ),
        queue_trace=QueueConsumptionTraceSnapshot(
            source_status="ok",
            command_queue_snapshot_present=True,
            consumption_status="consumed_by_service",
        ),
        engine_why=EngineWhySnapshot(
            source_status="ok",
            active_count=2,
            engines=(
                EngineWhyRow(engine_id="engine_a", status="active", records=10),
                EngineWhyRow(engine_id="engine_b", status="active", records=10),
            ),
        ),
        economics=EconomicSterilizationSnapshot(
            source_status="ok",
            ce_net=0.01,
            economic_sterilization_ratio=0.10,
            status="ok",
            cost_model_completeness_status="COST_MODEL_PARTIAL_IMPACT_MISSING",
            scoring_cost_completeness_status="COST_MODEL_PARTIAL_IMPACT_MISSING",
            capital_profile_artifact_status="CAPITAL_BUCKET_READY",
            book_depth_source_status="BOOK_LIMITED_DEPTH_AVAILABLE",
            impact_depth_readiness_status="LIMITED_DEPTH_PARTIAL",
            shadow_extension_required=True,
            shadow_extension_reason="SHADOW_EXTENDED_REQUIRED",
            minimum_shadow_days_required=45,
            shadow_extension_status="SHADOW_EXTENDED_45D",
            fill_realism_status="FILL_REALISM_MODEL_ONLY",
            cost_parity_status="REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
        ),
        feature_bridge=FeatureBridgeSnapshot(
            source_status="ok",
            lineage_lock_status="locked",
            lineage_lock_reasons=(),
            runtime_consumption_proven=True,
        ),
        refusal_journal=RefusalJournalSnapshot(source_status="ok"),
        kill_proof=KillProofSnapshot(source_status="ok", kill_switch_status="PROVEN_NOT_ARMED"),
        data_quality=DataQualitySnapshot(source_status="ok", pairs=()),
    )

    scoring_stage = next(stage for stage in snapshot.stages if stage.stage_name == "Scoring")
    assert scoring_stage.status == "yellow"
    assert snapshot.operability_score.economics == "LIMITED_DEPTH_PARTIAL"
    assert snapshot.operability_score.book_depth_status == "BOOK_LIMITED_DEPTH_AVAILABLE"
    assert snapshot.operability_score.cost_parity_status == "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
    assert snapshot.operability_score.shadow_extension_status == "SHADOW_EXTENDED_45D"
    assert snapshot.operability_score.overall_verdict == "SHADOW_THIN"


def test_system_flow_projects_missing_capital_profiles_as_non_green() -> None:
    snapshot = read_system_flow(
        freshness=SourceFreshnessSnapshot(source_status="ok", sources=()),
        warmup=WarmupExplainerSnapshot(
            source_status="ok",
            final_state="ready",
            eligible_to_trade=True,
            readiness_status="passed",
            required_checks_passed=True,
            checks=(WarmupExplainerCheck(check_id="market_data_capture", status="passed"),),
        ),
        service_liveness=ServiceLivenessSnapshot(
            source_status="ok",
            shadow_service_running=True,
            control_ready=True,
            service_status="running",
        ),
        queue_trace=QueueConsumptionTraceSnapshot(
            source_status="ok",
            command_queue_snapshot_present=True,
            consumption_status="consumed_by_service",
        ),
        engine_why=EngineWhySnapshot(
            source_status="ok",
            active_count=2,
            engines=(
                EngineWhyRow(engine_id="engine_a", status="active", records=10),
                EngineWhyRow(engine_id="engine_b", status="active", records=10),
            ),
        ),
        economics=EconomicSterilizationSnapshot(
            source_status="ok",
            ce_net=0.01,
            economic_sterilization_ratio=0.10,
            status="ok",
            cost_model_completeness_status="COST_MODEL_COMPLETE",
            scoring_cost_completeness_status="COST_MODEL_COMPLETE",
            book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
            impact_depth_readiness_status="DEPTH20_AVAILABLE",
            shadow_extension_required=False,
            shadow_extension_status="SHADOW_STANDARD_30D",
            fill_realism_status="FILL_REALISM_PROVEN",
            cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
            small_capital_viability_status="MEASURED",
            capital_profile_artifact_status="CAPITAL_BUCKET_NOT_PROVEN",
            min_notional_viability_status="MEASURED",
            capital_fragmentation_status="MEASURED",
            executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
            true_drawdown_status="TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
            portfolio_multi_asset_status="FULLY_PROVEN",
        ),
        feature_bridge=FeatureBridgeSnapshot(
            source_status="ok",
            lineage_lock_status="locked",
            lineage_lock_reasons=(),
            runtime_consumption_proven=True,
        ),
        refusal_journal=RefusalJournalSnapshot(source_status="ok"),
        kill_proof=KillProofSnapshot(source_status="ok", kill_switch_status="PROVEN_NOT_ARMED"),
        data_quality=DataQualitySnapshot(source_status="ok", pairs=()),
    )

    scoring_stage = next(stage for stage in snapshot.stages if stage.stage_name == "Scoring")
    assert "capital_profiles=CAPITAL_BUCKET_NOT_PROVEN" in scoring_stage.detail
    assert snapshot.operability_score.capital_profile_artifact_status == "CAPITAL_BUCKET_NOT_PROVEN"
    assert snapshot.operability_score.overall_verdict == "SHADOW_THIN"
