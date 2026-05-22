"""Typed readers and compact summaries for cockpit runtime surfaces."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
import time

from cockpit.queue_support import build_dashboard_command_queue_snapshot
from cockpit.strategy_ladder_component_coverage_support import (
    load_component_coverage_dashboard_fields,
)
from cockpit.strategy_ladder_ml_handoff_support import (
    StrategyLadderMlHandoffDashboardSummary,
    read_strategy_ladder_ml_handoff_dashboard_summary,
)
from pydantic import BaseModel, Field

from cockpit.action_support import (
    CockpitBacktestJobRecord,
    CockpitBacktestJobStatus,
    load_backtest_job_records,
)
from cockpit.backtest_state_support import (
    action_name_for_phase,
    phase_id_for_action,
    phase_label_for_action,
)
from cockpit.form_state_support import read_lab_ml_handoff_form_state
from cockpit.strategy_ladder_workflow_support import (
    PHASE_A2,
    PHASE_B1,
    PHASE_B2,
    read_workflow_manifest,
    workflow_phase_root,
)
from interface_contracts import (
    DashboardCommandQueueSnapshot,
    build_strategy_ladder_proxy_fidelity_surface,
    build_governed_audit_evidence_projection,
    load_governed_audit_evidence_index,
)
from interface_contracts.shadow_vps_service_contracts import ShadowVpsServiceState
from monitoring import query_shadow_vps_service_events
from monitoring.artifact_visibility import (
    build_artifact_comparison_projections,
    build_artifact_runtime_visibility_projections,
    build_artifact_threshold_consumer_projections,
    build_artifact_verdict_bundle_projection,
)
from monitoring.contracts import (
    ArtifactComparisonProjection,
    ArtifactRuntimeVisibilityProjection,
    ArtifactThresholdConsumerProjection,
    ArtifactVerdictBundleProjection,
    ShadowVpsServiceLogQuery,
    ShadowVpsServiceLogQueryResult,
    ShadowVpsServiceMonitoringPayload,
)
from monitoring.local_observability_stack import LocalObservabilityStackSummary


class CockpitAlert(BaseModel, frozen=True):
    """Small typed alert surface for cockpit-native status cards."""

    alert_id: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class ObservabilityPageSummary(BaseModel, frozen=True):
    """Compact local observability stack status surfaced to the cockpit."""

    source_status: str = Field(..., min_length=1)
    output_dir: str = ""
    grafana_url: str = ""
    prometheus_url: str = ""
    bridge_url: str = ""
    bridge_status: str = "unknown"
    prometheus_status: str = "unknown"
    grafana_status: str = "unknown"
    bootstrap_summary_path: str = ""
    dashboard_summary_path: str = ""
    prom_text_path: str = ""
    shadow_dashboard_status_code: int = 0
    shadow_dashboard_uid: str = ""
    lab_dashboard_status_code: int = 0
    lab_dashboard_uid: str = ""
    build17_dashboard_status_code: int = 0
    build17_dashboard_uid: str = ""
    build17_embedded_in_shadow: bool = False


class BacktestJobsSummary(BaseModel, frozen=True):
    """Compact audited job progress counters surfaced to the backtest page."""

    requested_count: int = 0
    running_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    latest_job_id: str = ""
    latest_status: str = "none"
    latest_activity_iso: str = ""


class StrategyLadderBacktestSummary(BaseModel, frozen=True):
    """Latest Strategy Ladder summary surfaced on the cockpit backtest page."""

    source_status: str = "missing"
    job_id: str = ""
    run_id: str = ""
    phase_id: str = ""
    phase_label: str = ""
    workflow_run_id: str = ""
    phase_run_id: str = ""
    parent_workflow_ref: str = ""
    current_phase_status: str = "PHASE_NOT_STARTED"
    current_phase_error_code: str = ""
    current_phase_stderr_ref: str = ""
    preview_id: str = ""
    request_hash: str = ""
    summary_freshness_status: str = "SUMMARY_FRESHNESS_NOT_PROVEN"
    summary_matches_current_request: bool = False
    current_job_id: str = ""
    current_job_status: str = "JOB_NOT_PROVEN"
    current_job_phase_id: str = ""
    current_job_phase_run_id: str = ""
    current_job_output_root: str = ""
    current_job_stage_summary_path: str = ""
    current_job_error_summary: str = ""
    current_job_blocker_codes: tuple[str, ...] = ()
    last_successful_b2_job_id: str = ""
    last_successful_b2_status: str = "JOB_NOT_PROVEN"
    last_successful_b2_run_id: str = ""
    last_successful_b2_phase_run_id: str = ""
    last_successful_b2_final_status: str = "not_present"
    last_successful_b2_summary_path: str = ""
    displayed_summary_job_id: str = ""
    displayed_summary_path: str = ""
    displayed_summary_source: str = "NONE"
    stale_summary_warning: bool = False
    summary_matches_current_job: bool = False
    final_status: str = "not_present"
    data_factory_status: str = "DATA_FACTORY_NOT_PROVEN"
    raw_source_status: str = "RAW_SOURCE_NOT_PROVEN"
    raw_source_provenance_status: str = "RAW_SOURCE_PROVENANCE_NOT_PROVEN"
    raw_source_typing_status: str = "RAW_SOURCE_TYPE_NOT_PROVEN"
    pair_universe_status: str = "PAIR_UNIVERSE_NOT_PROVEN"
    available_pair_count: int = 0
    requested_pair_count: int = 0
    missing_requested_pairs: tuple[str, ...] = ()
    silver_index_status: str = "SILVER_INDEX_NOT_READY"
    gold_feature_store_status: str = "GOLD_FEATURE_STORE_NOT_READY"
    compression_status: str = "COMPRESSION_NOT_PROVEN"
    trade_schema_status: str = "TRADE_SCHEMA_NOT_PROVEN"
    kline_schema_status: str = "KLINE_SCHEMA_NOT_PROVEN"
    historical_metadata_status: str = "BYBIT_HISTORICAL_METADATA_NOT_PROVEN"
    metadata_source_mode: str = "LOCAL_METADATA_CACHE"
    metadata_cache_path: str = ""
    metadata_pairs_covered: tuple[str, ...] = ()
    missing_metadata_pairs: tuple[str, ...] = ()
    metadata_temporal_status: str = "METADATA_TEMPORAL_NOT_PROVEN"
    metadata_fetched_at_utc: str = ""
    metadata_temporal_drift_days: float | None = None
    fee_provenance_status: str = "NOT_PROVEN"
    capital_bucket_metadata_status: str = "CAPITAL_BUCKET_NOT_PROVEN"
    metadata_preview_rows: tuple[dict[str, object], ...] = ()
    orderbook_reconstruction_status: str = "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN"
    first_controlled_run_status: str = "FIRST_RUN_BLOCKED"
    ml_mode_status: str = "ML_TRAINING_DISABLED_FOR_BASELINE"
    feature_store_status: str = "FEATURE_STORE_NOT_PROVEN"
    candidate_export_status: str = "CANDIDATE_EXPORT_NOT_PROVEN"
    raw_window_extraction_status: str = "RAW_WINDOW_NOT_PROVEN"
    detailed_replay_status: str = "DETAILED_REPLAY_NOT_PROVEN"
    capital_profile_generation_status: str = "CAPITAL_PROFILE_NOT_PROVEN"
    promotion_artifact_status: str = "PROMOTION_ARTIFACTS_NOT_PROVEN"
    sample_size_survival_status: str = "SAMPLE_SIZE_NOT_PROVEN"
    statistical_validation_status: str = "not_present"
    feature_row_count: int = 0
    candidate_sample_cap: int = 0
    effective_engine_native_sample_size: int = 10
    engine_count: int = 4
    candidate_cap_formula: str = ""
    small_scope_enabled: bool = True
    full_scan_enabled: bool = False
    no_full_scan_enabled: bool = True
    candidate_discovery_limited: bool = True
    candidate_discovery_limit_reason: str = ""
    candidate_discovery_mode: str = "SAMPLE_CAPPED_DEBUG"
    candidate_discovery_cap_status: str = "CANDIDATE_DISCOVERY_LIMIT_NOT_PROVEN"
    preselection_status: str = "ENGINE_NATIVE_PRESELECTION_NOT_PROVEN"
    replay_input_mode_status: str = "PRESELECTED_ONLY"
    preselected_only: bool = True
    diagnostic_full_replay: bool = False
    b1_5_policy_mode: str = "conservative_hard_only"
    discovery_pre_candidate_count: int = 0
    engine_native_preselected_count: int = 0
    preselection_hard_rejected_count: int = 0
    preselection_soft_flagged_count: int = 0
    preselection_passed_count: int = 0
    b2_replay_candidate_count: int = 0
    trade_eligible_candidate_count: int = 0
    preselection_rejection_count: int = 0
    replay_savings_estimate_count: int = 0
    preselection_top_rejection_reasons: tuple[dict[str, object], ...] = ()
    preselection_top_hard_rejection_reasons: tuple[dict[str, object], ...] = ()
    preselection_top_soft_advisory_reasons: tuple[dict[str, object], ...] = ()
    preselection_rejection_rows: tuple[dict[str, object], ...] = ()
    sample_size_survival_count: int = 0
    statistical_validation_observation_count: int = 0
    statistical_validation_trial_count: int = 0
    statistical_validation_stationary_block_length: int = 0
    unique_candidate_count: int = 0
    base_event_count: int = 0
    per_engine_candidate_count: int | None = None
    engine_native_candidate_count: int = 0
    replay_record_count: int = 0
    evaluation_record_count: int = 0
    promotion_record_count: int = 0
    capital_bucket_record_count: int = 0
    replay_expansion_factor: float | None = None
    statistical_validation_benchmark_sharpe: float | None = None
    statistical_validation_acceptance_floor: float | None = None
    statistical_validation_sample_sharpe: float | None = None
    statistical_validation_psr: float | None = None
    statistical_validation_dsr: float | None = None
    statistical_validation_effective_sample_size: float | None = None
    statistical_validation_min_trl_required: float | None = None
    replay_expansion_axis: str = ""
    statistical_validation_min_trl_satisfied: bool = False
    statistical_validation_psr_passes_floor: bool = False
    statistical_validation_dsr_passes_floor: bool = False
    candidate_source_status: str = "CANDIDATE_SOURCE_NOT_PROVEN"
    count_semantics_validator_codes: tuple[str, ...] = ()
    statistical_validation_blocker_codes: tuple[str, ...] = ()
    matrix_count_inflation_status: str = "COUNT_SEMANTICS_NOT_PROVEN"
    raw_windows_total: int = 0
    trade_windows_found: int = 0
    trade_windows_missing: int = 0
    book_windows_found: int = 0
    book_windows_missing: int = 0
    ohlcv_windows_found: int = 0
    ohlcv_windows_missing: int = 0
    depth20_found: int = 0
    depth20_missing: int = 0
    candidate_truth_status: str = "CANDIDATE_TRUTH_NOT_PROVEN"
    expected_edge_truth_status: str = "EXPECTED_EDGE_TRUTH_NOT_PROVEN"
    expected_edge_proxy_count: int = 0
    expected_edge_governed_count: int = 0
    expected_edge_training_artifact_ref: str = ""
    expected_edge_label_source: str = "EXPECTED_EDGE_LABEL_SOURCE_NOT_PROVEN"
    expected_edge_label_fidelity: str = "EXPECTED_EDGE_PROXY_DISCOVERY_ONLY"
    expected_edge_anti_leakage_status: str = "EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN"
    expected_edge_walkforward_status: str = "EXPECTED_EDGE_WALKFORWARD_NOT_DECLARED"
    expected_edge_horizon: int | None = None
    expected_edge_purge_window: int | None = None
    expected_edge_embargo_window: int | None = None
    expected_edge_blocker_codes: tuple[str, ...] = ()
    engine_native_status: str = "ENGINE_NATIVE_NOT_REQUESTED"
    candidate_engine_native_count: int = 0
    candidate_proxy_count: int = 0
    engine_native_records_built: int = 0
    execution_label_source: str = "REPLAY_PROXY_EXECUTION"
    fee_model_source: str = "REPLAY_PROXY"
    spread_model_source: str = "REPLAY_PROXY"
    slippage_model_source: str = "REPLAY_PROXY"
    partial_fill_model_source: str = "REPLAY_PROXY"
    adverse_selection_source: str = "REPLAY_PROXY"
    order_type_selection_source: str = "REPLAY_PROXY"
    venue_constraints_source: str = "REPLAY_PROXY"
    execution_fidelity_gap_codes: tuple[str, ...] = ()
    feature_store_pipeline_status: str = "FEATURE_STORE_NOT_PROVEN"
    feature_row_sample_status: str = "FEATURE_ROWS_NOT_PROVEN"
    expected_edge_governance_status: str = "EXPECTED_EDGE_NOT_PROVEN"
    execution_fidelity_status: str = "EXECUTION_FIDELITY_NOT_PROVEN"
    threshold_calibration_status: str = "THRESHOLDS_NOT_DECLARED"
    threshold_default_count: int = 0
    threshold_calibrated_count: int = 0
    threshold_calibration_not_proven_count: int = 0
    proxy_fidelity_blocker_codes: tuple[str, ...] = ()
    protocol_readiness_status: str = "REPLAY_PROTOCOL_PROOF_NOT_PROVEN"
    protocol_shadow_runtime_compatibility_status: str = (
        "SHADOW_IMPORT_REQUIRES_REVIEW"
    )
    protocol_blocker_codes: tuple[str, ...] = ()
    protocol_micro_live_gate_message: str = ""
    protocol_live_gate_message: str = ""
    governed_audit_evidence_index_path: str = ""
    governed_evidence_status: str = "EVIDENCE_CLASS_NOT_PROVEN"
    audited_evidence_count: int = 0
    scratch_only_evidence_count: int = 0
    promotion_grade_evidence_count: int = 0
    run_manifest_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    capital_profiles_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    engine_promotion_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    pair_promotion_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    strategy_promotion_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    sample_size_survival_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    trade_detail_ledger_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    refusal_ledger_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    loss_analysis_ledger_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    evidence_audit_blocker_codes: tuple[str, ...] = ()
    artifact_inventory_path: str = ""
    stage_summary_path: str = ""
    command_preview: str = ""
    blocker_codes: tuple[str, ...] = ()
    # Patch 6 — operator-selected output_root and the typed proof matrix path.
    output_root: str = ""
    backtest_proof_matrix_path: str = ""
    overall_backtest_proof_status: str = "BACKTEST_PROOF_NOT_PROVEN"
    run_class_component_coverage_path: str = ""
    run_class: str = "RUN_CLASS_NOT_PROVEN"
    run_class_id: str = "RUN_CLASS_NOT_PROVEN"
    component_status_counts: dict[str, int] = Field(default_factory=dict)
    component_coverage_rows: tuple[dict[str, object], ...] = ()
    # Patch 6 batch 2 — surface two-stage / orderbook / threshold / cancel
    # state for the dashboard panels.
    feature_threshold_manifest_path: str = ""
    storage_budget_report_path: str = ""
    storage_budget_status: str = "STORAGE_BUDGET_NOT_PROVEN"
    silver_storage_mode_requested: str = "jsonl_debug"
    silver_storage_mode_effective: str = "jsonl_debug"
    silver_storage_status: str = "SILVER_STORAGE_NOT_PROVEN"
    silver_storage_format: str = "jsonl"
    date_pruning_status: str = "DATE_PRUNING_NOT_PROVEN"
    silver_index_date_range_status: str = "SILVER_INDEX_DATE_RANGE_NOT_PROVEN"
    raw_scan_budget_status: str = "DRY_RUN_SCOPE_NOT_PROVEN"
    files_seen: int = 0
    files_skipped_by_date_filter: int = 0
    orderbook_snapshot_status: str = "ORDERBOOK_SNAPSHOT_NOT_PROVEN"
    orderbook_delta_status: str = "ORDERBOOK_DELTA_NOT_PROVEN"
    orderbook_reconstruction_status: str = "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN"
    depth20_proof_status: str = "BOOK_DEPTH_NOT_PROVEN"
    snapshot_entry_count: int = 0
    delta_entry_count: int = 0
    snapshot_paths: tuple[str, ...] = ()
    delta_paths: tuple[str, ...] = ()
    sequence_gap_status: str = "BOOK_SEQUENCE_NOT_PROVEN"
    sequence_gap_report_path: str = ""
    gap_count: int = 0
    gap_files: tuple[str, ...] = ()
    gap_dates: tuple[str, ...] = ()
    first_gap_expected_seq: int | None = None
    first_gap_actual_seq: int | None = None
    first_gap_previous_seq: int | None = None
    first_gap_event_timestamp_ms: int | None = None
    gap_recovery_status: str = "ORDERBOOK_SEQUENCE_NOT_PROVEN"
    pair_inference_status: str = "PAIR_NOT_DETECTED"
    ignored_source_pairs: tuple[str, ...] = ()
    active_pairs_after_pruning: tuple[str, ...] = ()
    phase1_feature_discovery_status: str = "PHASE1_FEATURE_DISCOVERY_NOT_PROVEN"
    phase1_candidate_export_status: str = "PHASE1_CANDIDATE_EXPORT_NOT_PROVEN"
    phase2_raw_window_extraction_status: str = "PHASE2_RAW_WINDOW_EXTRACTION_NOT_PROVEN"
    phase2_detailed_replay_status: str = "PHASE2_DETAILED_REPLAY_NOT_PROVEN"
    feature_groups_available: tuple[str, ...] = ()
    feature_groups_declared: tuple[str, ...] = ()
    feature_groups_generated: tuple[str, ...] = ()
    feature_groups_ready: tuple[str, ...] = ()
    # Patch 2026-05-15 (timeframe propagation audit) — cockpit visibility for
    # the silver/gold timeframe diff. All four fields default to empty so
    # legacy manifests without the keys keep rendering cleanly.
    silver_timeframes_detected: tuple[str, ...] = ()
    gold_timeframes_generated: tuple[str, ...] = ()
    timeframes_pruned: tuple[str, ...] = ()
    pruning_reason_by_timeframe: dict[str, str] = Field(default_factory=dict)
    timeframe_feature_row_count: dict[str, int] = Field(default_factory=dict)
    threshold_count: int = 0
    run_state_banner_status: str = ""
    run_state_banner_message: str = ""
    run_state_banner_details: tuple[str, ...] = ()
    files_processed: int = 0
    rows_processed: int = 0
    replay_performance_profile_status: str = "REPLAY_PERFORMANCE_PROFILE_NOT_PROVEN"
    replay_performance_profile_path: str = ""
    replay_perf_total_wall_time_s: float | None = None
    replay_perf_total_cpu_time_s: float | None = None
    replay_perf_total_io_wait_estimate_s: float | None = None
    replay_perf_rows_processed: int = 0
    replay_perf_files_scanned: int = 0
    replay_perf_rows_per_s: float | None = None
    replay_perf_records_per_s: float | None = None
    replay_perf_indexed_lookup_status: str = "INDEX_LOOKUP_NOT_PROVEN"
    replay_perf_indexed_lookup_hit_rate: float | None = None
    replay_perf_index_lookup_miss_count: int = 0
    replay_perf_fallback_scan_count: int = 0
    replay_perf_window_cache_status: str = "WINDOW_CACHE_NOT_PROVEN"
    replay_perf_window_cache_hit_count: int = 0
    replay_perf_window_cache_miss_count: int = 0
    replay_perf_window_cache_reuse_ratio: float | None = None
    replay_perf_parquet_fast_path_status: str = "PARQUET_REPLAY_NOT_PROVEN"
    replay_perf_research_fast_debug_mode_status: str = (
        "RESEARCH_FAST_DEBUG_MODE_NOT_REQUESTED"
    )
    replay_perf_replay_workers_used: int = 0
    replay_perf_replay_parallelism_ratio: float | None = None
    replay_perf_replay_cpu_utilization: float | None = None
    replay_perf_replay_queue_wait_time_s: float = 0.0
    replay_perf_bottleneck_summary: tuple[str, ...] = ()
    replay_perf_raw_window_wall_time_s: float | None = None
    replay_perf_replay_wall_time_s: float | None = None
    replay_perf_label_store_wall_time_s: float | None = None
    replay_perf_matrix_wall_time_s: float | None = None
    replay_perf_report_wall_time_s: float | None = None
    raw_size_bytes: int = 0
    silver_size_bytes: int = 0
    gold_size_bytes: int = 0
    silver_bloat_ratio: float | None = None
    candidate_count: int = 0
    raw_window_count: int = 0
    detailed_replay_count: int = 0
    capital_profile_count: int = 0
    engine_promotion_count: int = 0
    pair_promotion_count: int = 0
    strategy_promotion_count: int = 0
    executed_count: int = 0
    reduced_count: int = 0
    no_fill_count: int = 0
    trade_count: int = 0
    refusal_count: int = 0
    loss_count: int = 0
    winning_count: int = 0
    losing_count: int = 0
    gross_pnl_bps: float | None = None
    net_pnl_bps: float | None = None
    max_drawdown_bps: float | None = None
    avg_gain_bps: float | None = None
    avg_loss_bps: float | None = None
    replay_fee_source_status: str = "FEE_SOURCE_NOT_PROVEN"
    replay_impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    replay_fill_realism_status: str = "FILL_REALISM_NOT_PROVEN"
    replay_cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
    replay_executed_only_net_return_status: str = "EXECUTED_NET_RETURN_NOT_PROVEN"
    replay_true_net_equity_drawdown_status: str = (
        "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    )
    historical_replay_venue: str = "BYBIT"
    execution_target_venue: str = "BINANCE"
    backtest_class: str = "BYBIT_PROXY_BACKTEST"
    venue_transfer_status: str = "BINANCE_SHADOW_REQUIRED"
    live_trading_eligibility_status: str = "BLOCKED"
    proof_ready_metrics: tuple[dict[str, object], ...] = ()
    proof_gap_metrics: tuple[dict[str, object], ...] = ()
    candidate_rows: tuple[dict[str, object], ...] = ()
    selected_candidate_id: str = ""
    selected_candidate_detail: dict[str, object] = Field(default_factory=dict)
    selected_candidate_replay: dict[str, object] = Field(default_factory=dict)
    selected_candidate_window: dict[str, object] = Field(default_factory=dict)
    trade_ledger_rows: tuple[dict[str, object], ...] = ()
    refusal_ledger_rows: tuple[dict[str, object], ...] = ()
    loss_ledger_rows: tuple[dict[str, object], ...] = ()
    engine_matrix_rows: tuple[dict[str, object], ...] = ()
    pair_matrix_rows: tuple[dict[str, object], ...] = ()
    timeframe_matrix_rows: tuple[dict[str, object], ...] = ()
    no_trade_audit_status: str = "NO_TRADE_AUDIT_NOT_PROVEN"
    no_trade_refusal_rows_total: int = 0
    no_trade_selected_count_total: int = 0
    no_trade_hard_blocked_count_total: int = 0
    no_trade_executed_count_total: int = 0
    no_trade_sample_size_status: str = "SAMPLE_SIZE_NOT_PROVEN"
    no_trade_common_reason_codes: tuple[str, ...] = ()
    no_trade_engine_rows: tuple[dict[str, object], ...] = ()
    no_trade_reason_rows: tuple[dict[str, object], ...] = ()
    no_trade_capital_bucket_rows: tuple[dict[str, object], ...] = ()
    engine_no_trade_diagnosis_status: str = "ENGINE_NO_TRADE_DIAGNOSIS_NOT_PROVEN"
    engine_no_trade_diagnosis_path: str = ""
    engine_no_trade_first_gate_status: str = "FIRST_GATE_NOT_PROVEN"
    engine_no_trade_common_blockers: tuple[str, ...] = ()
    engine_no_trade_engine_rows: tuple[dict[str, object], ...] = ()
    engine_no_trade_next_actions: tuple[dict[str, object], ...] = ()
    gate_waterfall_analysis_status: str = "GATE_WATERFALL_NOT_PROVEN"
    gate_waterfall_analysis_path: str = ""
    gate_waterfall_best_scenario: str = ""
    gate_waterfall_canonical_selected_count: int = 0
    gate_waterfall_canonical_executed_count: int = 0
    gate_waterfall_counterfactual_survival_count: int = 0
    gate_waterfall_canonical_vs_counterfactual_delta: int = 0
    gate_waterfall_dominant_blocking_gates: tuple[dict[str, object], ...] = ()
    gate_waterfall_funnel_rows: tuple[dict[str, object], ...] = ()
    gate_counterfactual_scenarios: tuple[dict[str, object], ...] = ()
    gate_counterfactual_engine_rows: tuple[dict[str, object], ...] = ()
    gate_counterfactual_timeframe_rows: tuple[dict[str, object], ...] = ()
    expected_edge_readiness_status: str = "EXPECTED_EDGE_READINESS_NOT_PROVEN"
    expected_edge_readiness_verdict: str = ""
    expected_edge_readiness_path: str = ""
    expected_edge_readiness_key_findings: tuple[str, ...] = ()
    cancellable_running_jobs: tuple[str, ...] = ()


class ArtifactFamilyVisibilitySummary(BaseModel, frozen=True):
    """Compact lab-facing artifact identity summary per runtime family/slot."""

    family_id: str = Field(..., min_length=1)
    slot: str = Field(..., min_length=1)
    artifact_id: str = "none"
    artifact_kind: str = ""
    feature_set_version: str = ""
    lineage_version: str = ""
    review_state: str = ""
    validation_status: str = ""
    influence_detail: str = ""


class ArtifactFamilyComparisonSummary(BaseModel, frozen=True):
    """Compact lab-facing comparison metric summary per artifact family."""

    family_id: str = Field(..., min_length=1)
    comparison_status: str = "not_available"
    champion_artifact_id: str = "none"
    challenger_artifact_id: str = "none"
    event_count: int = 0
    expected_gain_delta_mean: float = 0.0
    expected_ce_delta_mean: float = 0.0
    halal_eligible_event_count: int = 0
    halal_excluded_event_count: int = 0


class CockpitRuntimeSurfaces(BaseModel, frozen=True):
    """Resolved read-side surfaces consumed by the cockpit pages."""

    monitoring_payload: ShadowVpsServiceMonitoringPayload | None = None
    service_state: ShadowVpsServiceState | None = None
    queue_snapshot: DashboardCommandQueueSnapshot | None = None
    recent_logs: ShadowVpsServiceLogQueryResult | None = None
    artifact_runtime_visibility: tuple[ArtifactRuntimeVisibilityProjection, ...] = ()
    artifact_threshold_consumers: tuple[ArtifactThresholdConsumerProjection, ...] = ()
    artifact_comparisons: tuple[ArtifactComparisonProjection, ...] = ()
    artifact_verdict_bundle: ArtifactVerdictBundleProjection | None = None
    observability: ObservabilityPageSummary = ObservabilityPageSummary(
        source_status="missing"
    )
    backtest_jobs: tuple[CockpitBacktestJobRecord, ...] = ()
    backtest_summary: BacktestJobsSummary = BacktestJobsSummary()
    strategy_ladder_summary: StrategyLadderBacktestSummary = StrategyLadderBacktestSummary()
    strategy_ladder_ml_handoff: StrategyLadderMlHandoffDashboardSummary = (
        StrategyLadderMlHandoffDashboardSummary()
    )
    artifact_family_visibility: tuple[ArtifactFamilyVisibilitySummary, ...] = ()
    artifact_family_comparisons: tuple[ArtifactFamilyComparisonSummary, ...] = ()
    alerts: tuple[CockpitAlert, ...] = ()


def read_runtime_surfaces(
    *,
    service_dir: Path,
    queue_root: Path | None,
    observability_output_dir: Path | None,
    backtest_jobs_root: Path | None,
    selected_candidate_id: str = "",
    log_query: ShadowVpsServiceLogQuery | None = None,
) -> CockpitRuntimeSurfaces:
    """Load compact cockpit surfaces from the existing monitoring and queue rails."""

    monitoring_payload = _load_model(
        service_dir / "shadow_vps_service_monitoring_backend_payload.json",
        ShadowVpsServiceMonitoringPayload,
    )
    service_state = _load_model(
        service_dir / "shadow_vps_service.state.json",
        ShadowVpsServiceState,
    )
    queue_snapshot = (
        build_dashboard_command_queue_snapshot(queue_root)
        if queue_root is not None
        else None
    )
    effective_query = log_query or ShadowVpsServiceLogQuery(max_events=30)
    recent_logs = read_logs_summary(
        service_dir=service_dir,
        query=effective_query,
    )
    (
        artifact_runtime_visibility,
        artifact_threshold_consumers,
        artifact_comparisons,
        artifact_verdict_bundle,
    ) = _read_artifact_surfaces(
        service_state=service_state,
        monitoring_payload=monitoring_payload,
    )
    observability = read_observability_summary(observability_output_dir)
    backtest_jobs = (
        load_backtest_job_records(backtest_jobs_root)
        if backtest_jobs_root is not None
        else ()
    )
    backtest_summary = _summarize_backtest_jobs(backtest_jobs)
    strategy_ladder_summary = _read_strategy_ladder_summary(
        backtest_jobs,
        selected_candidate_id=selected_candidate_id,
    )
    strategy_ladder_ml_handoff = read_strategy_ladder_ml_handoff_dashboard_summary(
        backtest_jobs,
        form_state=read_lab_ml_handoff_form_state(backtest_jobs_root),
    )
    # Patch 6 batch 2 — surface job_ids that the dashboard Cancel button can act on.
    _running_states = {
        "JOB_RUNNING",
        "JOB_CREATED",
        "running",
        "JOB_CANCELLING",
    }
    cancellable_jobs = tuple(
        job.job_id
        for job in backtest_jobs
        if job.status.value in _running_states and job.pid > 0
    )
    if cancellable_jobs:
        strategy_ladder_summary = strategy_ladder_summary.model_copy(
            update={"cancellable_running_jobs": cancellable_jobs}
        )
    artifact_family_visibility = _summarize_artifact_family_visibility(
        artifact_runtime_visibility
    )
    artifact_family_comparisons = _summarize_artifact_family_comparisons(
        comparisons=artifact_comparisons,
        visibility=artifact_runtime_visibility,
    )
    alerts = build_cockpit_alerts(
        monitoring_payload=monitoring_payload,
        recent_logs=recent_logs,
        observability=observability,
    )
    return CockpitRuntimeSurfaces(
        monitoring_payload=monitoring_payload,
        service_state=service_state,
        queue_snapshot=queue_snapshot,
        recent_logs=recent_logs,
        artifact_runtime_visibility=artifact_runtime_visibility,
        artifact_threshold_consumers=artifact_threshold_consumers,
        artifact_comparisons=artifact_comparisons,
        artifact_verdict_bundle=artifact_verdict_bundle,
        observability=observability,
        backtest_jobs=backtest_jobs,
        backtest_summary=backtest_summary,
        strategy_ladder_summary=strategy_ladder_summary,
        strategy_ladder_ml_handoff=strategy_ladder_ml_handoff,
        artifact_family_visibility=artifact_family_visibility,
        artifact_family_comparisons=artifact_family_comparisons,
        alerts=alerts,
    )


def read_logs_summary(
    *,
    service_dir: Path,
    query: ShadowVpsServiceLogQuery,
) -> ShadowVpsServiceLogQueryResult | None:
    """Run a bounded cockpit log query against the durable Shadow event log."""

    events_path = service_dir / "shadow_vps_service.events.jsonl"
    if not events_path.is_file():
        return None
    return query_shadow_vps_service_events(
        events_path,
        query=query,
        timestamp_ms=_timestamp_ms(),
    )


def read_observability_summary(
    observability_output_dir: Path | None,
) -> ObservabilityPageSummary:
    """Read the local observability stack summary and bootstrap outputs when present."""

    if observability_output_dir is None:
        return ObservabilityPageSummary(source_status="missing")
    summary_path = observability_output_dir / "local_observability_stack.summary.json"
    summary = _load_model(summary_path, LocalObservabilityStackSummary)
    if summary is None:
        return ObservabilityPageSummary(
            source_status="missing",
            output_dir=str(observability_output_dir.resolve()),
        )
    bootstrap_payload = _load_json(
        Path(summary.bootstrap_summary_path),
        default={},
    )
    shadow_vps = bootstrap_payload.get("shadow_vps", {})
    lab = bootstrap_payload.get("lab", {})
    build17 = bootstrap_payload.get("build17", {})
    build17_status_code = _int_value(build17.get("dashboard_status_code"))
    build17_uid = str(build17.get("dashboard_uid", ""))
    build17_embedded = bool(build17.get("embedded_in_shadow", False))
    if build17_status_code <= 0 and _int_value(shadow_vps.get("dashboard_status_code")) > 0:
        build17_status_code = _int_value(shadow_vps.get("dashboard_status_code"))
        build17_uid = str(shadow_vps.get("dashboard_uid", ""))
        build17_embedded = True
    return ObservabilityPageSummary(
        source_status="ok",
        output_dir=summary.output_dir,
        grafana_url=summary.grafana_url,
        prometheus_url=summary.prometheus_url,
        bridge_url=summary.bridge_url,
        bridge_status=summary.bridge_status,
        prometheus_status=summary.prometheus_status,
        grafana_status=summary.grafana_status,
        bootstrap_summary_path=summary.bootstrap_summary_path,
        dashboard_summary_path=summary.dashboard_summary_path,
        prom_text_path=summary.prom_text_path,
        shadow_dashboard_status_code=_int_value(
            shadow_vps.get("dashboard_status_code")
        ),
        shadow_dashboard_uid=str(shadow_vps.get("dashboard_uid", "")),
        lab_dashboard_status_code=_int_value(lab.get("dashboard_status_code")),
        lab_dashboard_uid=str(lab.get("dashboard_uid", "")),
        build17_dashboard_status_code=build17_status_code,
        build17_dashboard_uid=build17_uid,
        build17_embedded_in_shadow=build17_embedded,
    )


def build_cockpit_alerts(
    *,
    monitoring_payload: ShadowVpsServiceMonitoringPayload | None,
    recent_logs: ShadowVpsServiceLogQueryResult | None,
    observability: ObservabilityPageSummary,
) -> tuple[CockpitAlert, ...]:
    """Derive bounded cockpit-native host and observability alerts."""

    alerts: list[CockpitAlert] = []
    if monitoring_payload is not None:
        alerts.extend(
            _build_host_alerts(monitoring_payload)
            + _build_vps_payload_alerts(
                monitoring_payload,
                observability=observability,
            )
        )
    if recent_logs is not None and recent_logs.parse_error_count > 0:
        alerts.append(
            CockpitAlert(
                alert_id="cockpit:log_parse_errors_present",
                severity="warning",
                category="infra",
                message=(
                    "Shadow VPS durable log contains parse errors "
                    f"({recent_logs.parse_error_count})."
                ),
            )
        )
    if observability.source_status != "ok":
        alerts.append(
            CockpitAlert(
                alert_id="cockpit:observability_missing_metrics",
                severity="warning",
                category="infra",
                message="Local observability stack summary is missing.",
            )
        )
    else:
        if observability.bridge_status not in {"started", "already_listening"}:
            alerts.append(
                CockpitAlert(
                    alert_id="cockpit:prometheus_bridge_unhealthy",
                    severity="warning",
                    category="infra",
                    message=f"Prometheus bridge status is {observability.bridge_status}.",
                )
            )
        if observability.grafana_status not in {"started", "already_listening"}:
            alerts.append(
                CockpitAlert(
                    alert_id="cockpit:grafana_dashboard_unavailable",
                    severity="warning",
                    category="infra",
                    message=f"Grafana status is {observability.grafana_status}.",
                )
            )
    return tuple(alerts)


def _read_artifact_surfaces(
    *,
    service_state: ShadowVpsServiceState | None,
    monitoring_payload: ShadowVpsServiceMonitoringPayload | None,
) -> tuple[
    tuple[ArtifactRuntimeVisibilityProjection, ...],
    tuple[ArtifactThresholdConsumerProjection, ...],
    tuple[ArtifactComparisonProjection, ...],
    ArtifactVerdictBundleProjection | None,
]:
    if service_state is None:
        return (), (), (), None
    runtime_visibility = build_artifact_runtime_visibility_projections(
        active_ml_artifact=service_state.active_ml_artifact,
        active_regime_detector_artifact=service_state.active_regime_detector_artifact,
        shadow_ml_challenger_artifact=service_state.shadow_ml_challenger_artifact,
        shadow_regime_detector_challenger_artifact=(
            service_state.shadow_regime_detector_challenger_artifact
        ),
    )
    threshold_consumers = build_artifact_threshold_consumer_projections(
        execution_runtime_projection_path=(
            monitoring_payload.execution_runtime_projection_ref
            if monitoring_payload is not None
            else service_state.last_execution_runtime_projection_ref
        )
    )
    comparisons = build_artifact_comparison_projections(
        active_ml_artifact=service_state.active_ml_artifact,
        active_regime_detector_artifact=service_state.active_regime_detector_artifact,
        shadow_ml_challenger_artifact=service_state.shadow_ml_challenger_artifact,
        shadow_regime_detector_challenger_artifact=(
            service_state.shadow_regime_detector_challenger_artifact
        ),
        ml_comparison_ref=service_state.last_shadow_ml_artifact_comparison_ref,
        regime_detector_comparison_ref=(
            service_state.last_shadow_regime_detector_artifact_comparison_ref
        ),
    )
    verdict = build_artifact_verdict_bundle_projection(
        verdict_bundle_ref=service_state.last_shadow_challenger_verdict_bundle_ref,
        verdict_bundle_status=service_state.last_shadow_challenger_verdict_bundle_status,
    )
    return runtime_visibility, threshold_consumers, comparisons, verdict


def _build_host_alerts(
    monitoring_payload: ShadowVpsServiceMonitoringPayload,
) -> list[CockpitAlert]:
    alerts: list[CockpitAlert] = []
    for suffix, severity, category, message in (
        _resource_alert(
            "cpu",
            value=monitoring_payload.process.cpu_pct,
            warning=85.0,
            critical=95.0,
            format_unit="%",
        ),
        _resource_alert(
            "ram",
            value=monitoring_payload.process.ram_pct,
            warning=80.0,
            critical=90.0,
            format_unit="%",
        ),
        _resource_alert(
            "disk",
            value=monitoring_payload.disk.used_pct,
            warning=80.0,
            critical=90.0,
            format_unit="%",
        ),
    ):
        if not suffix:
            continue
        alerts.append(
            CockpitAlert(
                alert_id=f"cockpit:host_{suffix}_high",
                severity=severity,
                category=category,
                message=message,
            )
        )
    return alerts


def _build_vps_payload_alerts(
    monitoring_payload: ShadowVpsServiceMonitoringPayload,
    *,
    observability: ObservabilityPageSummary,
) -> list[CockpitAlert]:
    alerts: list[CockpitAlert] = []
    if monitoring_payload.parse_error_count > 0:
        alerts.append(
            CockpitAlert(
                alert_id="cockpit:observability_stale_metrics",
                severity="warning",
                category="infra",
                message=(
                    "Shadow VPS monitoring payload reports log parse errors "
                    f"({monitoring_payload.parse_error_count})."
                ),
            )
        )
    if (
        observability.source_status != "ok"
        and (
            not monitoring_payload.scrape_manifest_ref
            or not monitoring_payload.prometheus_file_sd_ref
        )
    ):
        alerts.append(
            CockpitAlert(
                alert_id="cockpit:observability_missing_refs",
                severity="warning",
                category="infra",
                message="Prometheus scrape manifest or file_sd ref is missing.",
            )
        )
    return alerts


def _summarize_backtest_jobs(
    jobs: tuple[CockpitBacktestJobRecord, ...],
) -> BacktestJobsSummary:
    requested_count = sum(
        1 for job in jobs if job.status.value in {"requested", "JOB_CREATED"}
    )
    running_count = sum(
        1 for job in jobs if job.status.value in {"running", "JOB_RUNNING"}
    )
    completed_count = sum(
        1
        for job in jobs
        if job.status.value
        in {"completed", "JOB_COMPLETED", "JOB_COMPLETED_WITH_BLOCKERS"}
    )
    failed_count = sum(
        1
        for job in jobs
        if job.status.value in {"failed", "JOB_FAILED", "JOB_BLOCKED"}
    )
    latest = max(
        jobs,
        key=lambda job: _parse_iso(job.latest_activity_iso) or datetime.min.replace(tzinfo=UTC),
        default=None,
    )
    if latest is None:
        return BacktestJobsSummary()
    return BacktestJobsSummary(
        requested_count=requested_count,
        running_count=running_count,
        completed_count=completed_count,
        failed_count=failed_count,
        latest_job_id=latest.job_id,
        latest_status=latest.status.value,
        latest_activity_iso=latest.latest_activity_iso,
    )


def _read_strategy_ladder_summary(
    jobs: tuple[CockpitBacktestJobRecord, ...],
    *,
    selected_candidate_id: str = "",
) -> StrategyLadderBacktestSummary:
    grouped_jobs: dict[str, list[CockpitBacktestJobRecord]] = {}
    ordered_keys: list[str] = []
    for job in jobs:
        key = job.workflow_run_id or (str(Path(job.output_root).resolve()) if job.output_root else "")
        if not key:
            continue
        if key not in grouped_jobs:
            grouped_jobs[key] = []
            ordered_keys.append(key)
        grouped_jobs[key].append(job)

    for group_key in ordered_keys:
        scoped_jobs = tuple(grouped_jobs[group_key])
        latest_job = max(
            scoped_jobs,
            key=lambda record: _parse_iso(record.latest_activity_iso)
            or datetime.min.replace(tzinfo=UTC),
        )
        workflow_root = (
            Path(latest_job.parent_workflow_ref).parent
            if latest_job.parent_workflow_ref
            else None
        )
        workflow_manifest = (
            read_workflow_manifest(workflow_root)
            if workflow_root is not None
            else None
        )
        current_phase_id = (
            workflow_manifest.current_phase_id
            if workflow_manifest is not None
            else ""
        )
        current_phase_record = (
            workflow_manifest.phases.get(current_phase_id)
            if workflow_manifest is not None and current_phase_id
            else None
        )
        output_root = (
            Path(current_phase_record.phase_output_root)
            if current_phase_record is not None and current_phase_record.phase_output_root
            else Path(latest_job.output_root)
        )
        if not output_root.is_dir():
            if workflow_manifest is not None and workflow_root is not None:
                candidate_root = workflow_phase_root(
                    workflow_root,
                    current_phase_id or PHASE_B2,
                )
                if candidate_root.is_dir():
                    output_root = candidate_root
                else:
                    continue
            else:
                continue
        summary = StrategyLadderBacktestSummary().model_dump()
        summary["output_root"] = str(output_root.resolve())
        summary["current_job_id"] = latest_job.job_id
        summary["current_job_status"] = latest_job.status.value
        summary["current_job_phase_id"] = _job_phase_id(latest_job)
        summary["current_job_phase_run_id"] = latest_job.phase_run_id
        summary["current_job_output_root"] = str(Path(latest_job.output_root).resolve()) if latest_job.output_root else ""
        summary["current_job_stage_summary_path"] = latest_job.stage_summary_path
        summary["current_job_error_summary"] = latest_job.error_summary
        summary["current_job_blocker_codes"] = tuple(latest_job.blockers)
        last_successful_b2_job, last_successful_b2_payload, last_successful_b2_run_dir = (
            _find_last_successful_b2_summary(scoped_jobs)
        )
        current_job_payload: dict[str, object] = {}
        current_job_run_dir: Path | None = None
        if (
            _job_phase_id(latest_job) == PHASE_B2
            and latest_job.status.value in _SUCCESSFUL_JOB_STATUSES
        ):
            current_job_payload, current_job_run_dir = (
                _load_strategy_ladder_summary_payload_for_job(latest_job)
            )
        if last_successful_b2_job is not None:
            summary["last_successful_b2_job_id"] = last_successful_b2_job.job_id
            summary["last_successful_b2_status"] = last_successful_b2_job.status.value
            summary["last_successful_b2_phase_run_id"] = last_successful_b2_job.phase_run_id
            if last_successful_b2_job.stage_summary_path:
                summary["last_successful_b2_summary_path"] = (
                    last_successful_b2_job.stage_summary_path
                )
            elif last_successful_b2_run_dir is not None:
                summary["last_successful_b2_summary_path"] = str(
                    (
                        last_successful_b2_run_dir
                        / "reports"
                        / "strategy_ladder_summary.json"
                    ).resolve()
                )
            if isinstance(last_successful_b2_payload, dict):
                summary["last_successful_b2_run_id"] = str(
                    last_successful_b2_payload.get("run_id") or ""
                )
                summary["last_successful_b2_final_status"] = str(
                    last_successful_b2_payload.get("final_status") or "not_present"
                )
        if current_phase_record is not None:
            summary["source_status"] = "workflow_phase_only"
        if workflow_manifest is not None:
            summary["workflow_run_id"] = workflow_manifest.workflow_run_id
            summary["parent_workflow_ref"] = str(
                (workflow_root / "workflow_manifest.json").resolve()
            )
            if current_phase_id:
                summary["phase_id"] = current_phase_id
                summary["phase_label"] = phase_label_for_action(
                    action_name_for_phase(current_phase_id)
                )
            summary["candidate_discovery_mode"] = workflow_manifest.candidate_discovery_mode
            summary["effective_engine_native_sample_size"] = workflow_manifest.engine_native_sample_size
            summary["preselected_only"] = workflow_manifest.preselected_only
            summary["diagnostic_full_replay"] = (
                workflow_manifest.diagnostic_full_replay
            )
            summary["engine_count"] = workflow_manifest.engine_count
            summary["candidate_sample_cap"] = (
                workflow_manifest.engine_count * workflow_manifest.engine_native_sample_size
            )
            summary["candidate_cap_formula"] = (
                f"{workflow_manifest.engine_count} engines x "
                f"{workflow_manifest.engine_native_sample_size}"
            )
            summary["small_scope_enabled"] = workflow_manifest.small_scope_enabled
            summary["full_scan_enabled"] = workflow_manifest.full_scan_enabled
            summary["no_full_scan_enabled"] = workflow_manifest.no_full_scan_enabled
            summary["silver_storage_mode_requested"] = (
                workflow_manifest.silver_storage_mode_requested
            )
            summary["silver_storage_mode_effective"] = (
                workflow_manifest.silver_storage_mode_effective
            )
            if current_phase_record is not None:
                summary["phase_run_id"] = current_phase_record.phase_run_id
                summary["current_phase_status"] = current_phase_record.phase_status
                summary["current_phase_error_code"] = current_phase_record.error_code
                summary["current_phase_stderr_ref"] = current_phase_record.stderr_ref
                summary["current_job_blocker_codes"] = tuple(
                    dict.fromkeys(
                        (
                            *summary["current_job_blocker_codes"],
                            *current_phase_record.blocker_codes,
                        )
                    )
                )
                summary["blocker_codes"] = tuple(
                    dict.fromkeys(
                        (
                            *summary["blocker_codes"],
                            *current_phase_record.blocker_codes,
                        )
                    )
                )
        summary.update(load_component_coverage_dashboard_fields(output_root))
        found_any = current_phase_record is not None
        found_data_factory = False
        found_first_run = False
        found_ladder = False
        for job in scoped_jobs:
            if not summary["job_id"]:
                summary["job_id"] = job.job_id
            if job.workflow_run_id and not summary["workflow_run_id"]:
                summary["workflow_run_id"] = job.workflow_run_id
            if job.phase_run_id and not summary["phase_run_id"]:
                summary["phase_run_id"] = job.phase_run_id
            if job.parent_workflow_ref and not summary["parent_workflow_ref"]:
                summary["parent_workflow_ref"] = job.parent_workflow_ref
            if job.request_hash and not summary["request_hash"]:
                summary["request_hash"] = job.request_hash
            if job.preview_id and not summary["preview_id"]:
                summary["preview_id"] = job.preview_id
            if job.action_name and not summary["phase_id"]:
                summary["phase_id"] = phase_id_for_action(job.action_name)
                summary["phase_label"] = phase_label_for_action(job.action_name)
            proof_matrix_path = output_root / "backtest_proof_matrix.json"
            if proof_matrix_path.is_file():
                if not summary["backtest_proof_matrix_path"]:
                    summary["backtest_proof_matrix_path"] = str(
                        proof_matrix_path.resolve()
                    )
                proof_payload = _load_json(proof_matrix_path, default={})
                if isinstance(proof_payload, dict):
                    overall_proof = proof_payload.get(
                        "overall_backtest_proof_status"
                    )
                    if isinstance(overall_proof, str) and overall_proof:
                        summary["overall_backtest_proof_status"] = overall_proof
                    for surface_key in (
                        "orderbook_snapshot_status",
                        "orderbook_delta_status",
                        "orderbook_reconstruction_status",
                        "depth20_proof_status",
                        "sequence_gap_status",
                        "sequence_gap_report_path",
                        "gap_recovery_status",
                        "historical_metadata_status",
                        "metadata_source_mode",
                        "metadata_cache_path",
                        "metadata_temporal_status",
                        "metadata_fetched_at_utc",
                        "fee_provenance_status",
                        "capital_bucket_metadata_status",
                        "pair_inference_status",
                        "phase1_feature_discovery_status",
                        "phase1_candidate_export_status",
                        "phase2_raw_window_extraction_status",
                        "phase2_detailed_replay_status",
                        "storage_budget_status",
                        "silver_storage_status",
                        "replay_fee_source_status",
                        "replay_impact_source_status",
                        "replay_fill_realism_status",
                        "replay_cost_parity_status",
                        "replay_executed_only_net_return_status",
                        "replay_true_net_equity_drawdown_status",
                        "promotion_artifact_status",
                        "candidate_truth_status",
                        "expected_edge_truth_status",
                        "engine_native_status",
                        "execution_label_source",
                        "fee_model_source",
                        "spread_model_source",
                        "slippage_model_source",
                        "partial_fill_model_source",
                        "adverse_selection_source",
                        "order_type_selection_source",
                        "venue_constraints_source",
                        "historical_replay_venue",
                        "execution_target_venue",
                        "backtest_class",
                        "venue_transfer_status",
                        "live_trading_eligibility_status",
                        "date_pruning_status",
                        "silver_index_date_range_status",
                        "raw_scan_budget_status",
                    ):
                        value = proof_payload.get(surface_key)
                        if isinstance(value, str) and value:
                            summary[surface_key] = value
                    snapshot_count = proof_payload.get("snapshot_entry_count")
                    delta_count = proof_payload.get("delta_entry_count")
                    if isinstance(snapshot_count, int):
                        summary["snapshot_entry_count"] = snapshot_count
                    if isinstance(delta_count, int):
                        summary["delta_entry_count"] = delta_count
                    for numeric_key in (
                        "gap_count",
                        "first_gap_expected_seq",
                        "first_gap_actual_seq",
                        "first_gap_previous_seq",
                        "first_gap_event_timestamp_ms",
                        "candidate_count",
                        "raw_window_count",
                        "detailed_replay_count",
                        "executed_count",
                        "reduced_count",
                        "no_fill_count",
                    ):
                        value = proof_payload.get(numeric_key)
                        if isinstance(value, int):
                            summary[numeric_key] = value
                    bloat_ratio = proof_payload.get("silver_bloat_ratio")
                    if isinstance(bloat_ratio, (int, float)):
                        summary["silver_bloat_ratio"] = float(bloat_ratio)
                    snap_paths = proof_payload.get("snapshot_paths")
                    if isinstance(snap_paths, list):
                        summary["snapshot_paths"] = tuple(
                            str(item) for item in snap_paths[:10]
                        )
                    del_paths = proof_payload.get("delta_paths")
                    if isinstance(del_paths, list):
                        summary["delta_paths"] = tuple(
                            str(item) for item in del_paths[:10]
                        )
                    for list_key in ("gap_files", "gap_dates", "ignored_source_pairs", "active_pairs_after_pruning"):
                        value = proof_payload.get(list_key)
                        if isinstance(value, list):
                            summary[list_key] = tuple(str(item) for item in value[:10])
                    for list_key in ("metadata_pairs_covered", "missing_metadata_pairs"):
                        value = proof_payload.get(list_key)
                        if isinstance(value, list):
                            summary[list_key] = tuple(str(item) for item in value[:20])
                    execution_gap_codes = proof_payload.get("execution_fidelity_gap_codes")
                    if isinstance(execution_gap_codes, list):
                        summary["execution_fidelity_gap_codes"] = tuple(
                            str(item) for item in execution_gap_codes[:20]
                        )
                    ready_metrics = proof_payload.get("ready_metrics")
                    if isinstance(ready_metrics, list):
                        summary["proof_ready_metrics"] = tuple(
                            dict(item) for item in ready_metrics[:20] if isinstance(item, dict)
                        )
                    gap_metrics = proof_payload.get("metric_gaps")
                    if isinstance(gap_metrics, list):
                        summary["proof_gap_metrics"] = tuple(
                            dict(item) for item in gap_metrics[:20] if isinstance(item, dict)
                        )
                    ftm_path = proof_payload.get("feature_threshold_manifest_path")
                    if isinstance(ftm_path, str) and ftm_path:
                        summary["feature_threshold_manifest_path"] = ftm_path
                    sb_path = proof_payload.get("storage_budget_report_path")
                    if isinstance(sb_path, str) and sb_path:
                        summary["storage_budget_report_path"] = sb_path
            ftm_path_local = output_root / "feature_threshold_manifest.json"
            if ftm_path_local.is_file():
                ftm_payload = _load_json(ftm_path_local, default={})
                if isinstance(ftm_payload, dict):
                    groups = ftm_payload.get("feature_groups_available")
                    if isinstance(groups, list):
                        summary["feature_groups_available"] = tuple(
                            str(g.get("feature_group") or g)
                            if isinstance(g, dict)
                            else str(g)
                            for g in groups
                        )
                    thresholds = ftm_payload.get("thresholds_used")
                    if isinstance(thresholds, list):
                        summary["threshold_count"] = len(thresholds)
            gold_manifest_path = output_root / "gold_feature_manifest.json"
            if gold_manifest_path.is_file():
                gold_payload = _load_json(gold_manifest_path, default={})
                if isinstance(gold_payload, dict):
                    for field_name in (
                        "feature_groups_declared",
                        "feature_groups_generated",
                        "feature_groups_ready",
                    ):
                        groups = gold_payload.get(field_name)
                        if isinstance(groups, list):
                            summary[field_name] = tuple(str(item) for item in groups)
                    if not summary["feature_groups_available"]:
                        ready_groups = gold_payload.get("feature_groups_ready")
                        if isinstance(ready_groups, list):
                            summary["feature_groups_available"] = tuple(
                                str(item) for item in ready_groups
                            )
                    # Patch 2026-05-15 (timeframe propagation audit) — pull the
                    # silver→gold timeframe diff fields so the cockpit panel
                    # can show prunes explicitly. Legacy manifests without
                    # the keys stay safe because the loop only assigns when
                    # the field exists and matches the expected container
                    # type.
                    for tuple_field in (
                        "silver_timeframes_detected",
                        "gold_timeframes_generated",
                        "timeframes_pruned",
                    ):
                        values = gold_payload.get(tuple_field)
                        if isinstance(values, list):
                            summary[tuple_field] = tuple(str(item) for item in values)
                    pruning_reasons = gold_payload.get("pruning_reason_by_timeframe")
                    if isinstance(pruning_reasons, dict):
                        summary["pruning_reason_by_timeframe"] = {
                            str(key): str(value)
                            for key, value in pruning_reasons.items()
                        }
                    timeframe_rows = gold_payload.get("timeframe_feature_row_count")
                    if isinstance(timeframe_rows, dict):
                        summary["timeframe_feature_row_count"] = {
                            str(key): int(value)
                            for key, value in timeframe_rows.items()
                            if isinstance(value, (int, float))
                        }
            quality_path = output_root / "data_quality_report.json"
            if quality_path.is_file():
                quality_payload = _load_json(quality_path, default={})
                if isinstance(quality_payload, dict):
                    files_processed = quality_payload.get("files_processed")
                    rows_processed = quality_payload.get("rows_processed")
                    files_seen = quality_payload.get("files_seen")
                    files_skipped_date = quality_payload.get(
                        "files_skipped_by_date_filter"
                    )
                    if isinstance(files_processed, int):
                        summary["files_processed"] = files_processed
                    if isinstance(rows_processed, int):
                        summary["rows_processed"] = rows_processed
                    if isinstance(files_seen, int):
                        summary["files_seen"] = files_seen
                    if isinstance(files_skipped_date, int):
                        summary["files_skipped_by_date_filter"] = files_skipped_date
                    range_status = quality_payload.get("silver_index_date_range_status")
                    if isinstance(range_status, str) and range_status:
                        summary["silver_index_date_range_status"] = range_status
                    scan_status = quality_payload.get("raw_scan_budget_status")
                    if isinstance(scan_status, str) and scan_status:
                        summary["raw_scan_budget_status"] = scan_status
                    fmt = quality_payload.get("silver_storage_format")
                    if isinstance(fmt, str) and fmt:
                        summary["silver_storage_format"] = fmt
                    requested_mode = quality_payload.get("silver_storage_mode_requested")
                    if isinstance(requested_mode, str) and requested_mode:
                        summary["silver_storage_mode_requested"] = requested_mode
                    effective_mode = quality_payload.get("silver_storage_mode_effective")
                    if isinstance(effective_mode, str) and effective_mode:
                        summary["silver_storage_mode_effective"] = effective_mode
                    for field_name in (
                        "historical_metadata_status",
                        "metadata_source_mode",
                        "metadata_cache_path",
                        "metadata_temporal_status",
                        "metadata_fetched_at_utc",
                        "fee_provenance_status",
                        "capital_bucket_metadata_status",
                    ):
                        value = quality_payload.get(field_name)
                        if isinstance(value, str) and value:
                            summary[field_name] = value
                    for field_name in (
                        "metadata_pairs_covered",
                        "missing_metadata_pairs",
                    ):
                        value = quality_payload.get(field_name)
                        if isinstance(value, list):
                            summary[field_name] = tuple(str(item) for item in value[:20])
                    preview_rows = quality_payload.get("metadata_preview_rows")
                    if isinstance(preview_rows, list):
                        summary["metadata_preview_rows"] = tuple(
                            dict(item) for item in preview_rows[:5] if isinstance(item, dict)
                        )
            compression_path = output_root / "compression_report.json"
            if compression_path.is_file():
                compression_payload = _load_json(compression_path, default={})
                if isinstance(compression_payload, dict):
                    for numeric_key in (
                        "raw_size_bytes",
                        "silver_size_bytes",
                        "gold_size_bytes",
                    ):
                        value = compression_payload.get(numeric_key)
                        if isinstance(value, int):
                            summary[numeric_key] = value
                    bloat_ratio = compression_payload.get("silver_bloat_ratio")
                    if isinstance(bloat_ratio, (int, float)):
                        summary["silver_bloat_ratio"] = float(bloat_ratio)
                    storage_status = compression_payload.get("silver_storage_status")
                    if isinstance(storage_status, str) and storage_status:
                        summary["silver_storage_status"] = storage_status
                    recommendation = compression_payload.get("recommendation")
                    if isinstance(recommendation, str) and recommendation:
                        summary["run_state_banner_details"] = tuple(
                            dict.fromkeys(
                                (*summary["run_state_banner_details"], recommendation)
                            )
                        )
            if not found_data_factory:
                manifest_payload = _load_json(
                    output_root / "data_factory_manifest.json", default={}
                )
                data_quality_payload = _load_json(
                    output_root / "data_quality_report.json", default={}
                )
                raw_source_payload = _load_json(
                    output_root / "raw_source_report.json", default={}
                )
                pair_payload = _load_json(
                    output_root / "pair_universe_report.json", default={}
                )
                if isinstance(manifest_payload, dict) and manifest_payload:
                    found_any = True
                    found_data_factory = True
                    summary["source_status"] = "ok"
                    summary["data_factory_status"] = str(
                        manifest_payload.get(
                            "data_factory_status", "DATA_FACTORY_NOT_PROVEN"
                        )
                    )
                    summary["raw_source_status"] = str(
                        manifest_payload.get(
                            "raw_source_status", "RAW_SOURCE_NOT_PROVEN"
                        )
                    )
                    summary["raw_source_provenance_status"] = str(
                        manifest_payload.get(
                            "raw_source_provenance_status",
                            "RAW_SOURCE_PROVENANCE_NOT_PROVEN",
                        )
                    )
                    summary["raw_source_typing_status"] = str(
                        raw_source_payload.get(
                            "raw_source_typing_status",
                            manifest_payload.get(
                                "raw_source_typing_status",
                                "RAW_SOURCE_TYPE_NOT_PROVEN",
                            ),
                        )
                    )
                    summary["pair_universe_status"] = str(
                        manifest_payload.get(
                            "pair_universe_status", "PAIR_UNIVERSE_NOT_PROVEN"
                        )
                    )
                    summary["silver_index_status"] = str(
                        manifest_payload.get(
                            "silver_index_status", "SILVER_INDEX_NOT_READY"
                        )
                    )
                    summary["gold_feature_store_status"] = str(
                        manifest_payload.get(
                            "gold_feature_store_status", "GOLD_FEATURE_STORE_NOT_READY"
                        )
                    )
                    summary["compression_status"] = str(
                        manifest_payload.get(
                            "compression_status", "COMPRESSION_NOT_PROVEN"
                        )
                    )
                    files_processed = manifest_payload.get("files_processed")
                    rows_processed = manifest_payload.get("rows_processed")
                    bytes_read = manifest_payload.get("bytes_read")
                    bytes_written = manifest_payload.get("bytes_written")
                    if isinstance(files_processed, int):
                        summary["files_processed"] = files_processed
                    if isinstance(rows_processed, int):
                        summary["rows_processed"] = rows_processed
                    if isinstance(bytes_read, int):
                        summary["raw_size_bytes"] = bytes_read
                    if isinstance(bytes_written, int) and summary["silver_size_bytes"] == 0:
                        summary["silver_size_bytes"] = bytes_written
                    summary["trade_schema_status"] = str(
                        manifest_payload.get(
                            "trade_schema_status", "TRADE_SCHEMA_NOT_PROVEN"
                        )
                    )
                    summary["kline_schema_status"] = str(
                        manifest_payload.get(
                            "kline_schema_status", "KLINE_SCHEMA_NOT_PROVEN"
                        )
                    )
                    summary["historical_metadata_status"] = str(
                        manifest_payload.get(
                            "historical_metadata_status",
                            "BYBIT_HISTORICAL_METADATA_NOT_PROVEN",
                        )
                    )
                    summary["metadata_source_mode"] = str(
                        manifest_payload.get(
                            "metadata_source_mode", "LOCAL_METADATA_CACHE"
                        )
                    )
                    summary["fee_provenance_status"] = str(
                        manifest_payload.get(
                            "fee_provenance_status", "NOT_PROVEN"
                        )
                    )
                    summary["metadata_temporal_status"] = str(
                        manifest_payload.get(
                            "metadata_temporal_status",
                            "METADATA_TEMPORAL_NOT_PROVEN",
                        )
                    )
                    metadata_fetched_at_utc = str(
                        data_quality_payload.get(
                            "metadata_fetched_at_utc",
                            manifest_payload.get(
                                "metadata_fetched_at_utc",
                                summary["metadata_fetched_at_utc"],
                            ),
                        )
                    )
                    if metadata_fetched_at_utc:
                        summary["metadata_fetched_at_utc"] = metadata_fetched_at_utc
                    drift_value = manifest_payload.get("metadata_temporal_drift_days")
                    if not isinstance(drift_value, (int, float)):
                        drift_value = data_quality_payload.get("metadata_temporal_drift_days")
                    if isinstance(drift_value, (int, float)):
                        summary["metadata_temporal_drift_days"] = float(drift_value)
                    else:
                        summary["metadata_temporal_drift_days"] = (
                            _calculate_metadata_temporal_drift_days(
                                fetched_at_utc=summary["metadata_fetched_at_utc"],
                                replay_end=str(manifest_payload.get("end") or ""),
                            )
                        )
                    if not summary["backtest_proof_matrix_path"]:
                        summary["orderbook_reconstruction_status"] = str(
                            manifest_payload.get(
                                "orderbook_schema_status",
                                "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN",
                            )
                        )
                    summary["command_preview"] = (
                        job.command_preview or summary["command_preview"]
                    )
                    summary["artifact_inventory_path"] = (
                        job.artifact_inventory_path
                        or summary["artifact_inventory_path"]
                    )
                    summary["stage_summary_path"] = (
                        job.stage_summary_path or summary["stage_summary_path"]
                    )
                    summary["blocker_codes"] = tuple(
                        dict.fromkeys(
                            (
                                *summary["blocker_codes"],
                                *(
                                    str(item)
                                    for item in manifest_payload.get("blocker_codes")
                                    or ()
                                ),
                            )
                        )
                    )
                    if isinstance(pair_payload, dict):
                        requested_pairs = tuple(
                            str(item)
                            for item in pair_payload.get("requested_pairs") or ()
                        )
                        available_pairs = tuple(
                            str(item)
                            for item in pair_payload.get("available_pairs") or ()
                        )
                        missing_pairs = tuple(
                            str(item) for item in pair_payload.get("missing_pairs") or ()
                        )
                        summary["requested_pair_count"] = len(requested_pairs)
                        summary["available_pair_count"] = len(available_pairs)
                        summary["missing_requested_pairs"] = missing_pairs
            if not found_first_run:
                first_manifest = _load_json(
                    output_root / "first_run_manifest.json", default={}
                )
                first_summary = _load_json(
                    output_root / "first_run_stage_summary.json", default={}
                )
                if isinstance(first_manifest, dict) and first_manifest:
                    found_any = True
                    found_first_run = True
                    summary["source_status"] = "ok"
                    summary["run_id"] = str(
                        first_manifest.get("run_id", summary["run_id"])
                    )
                    summary["first_controlled_run_status"] = str(
                        first_manifest.get("first_run_status", "FIRST_RUN_BLOCKED")
                    )
                    summary["ml_mode_status"] = str(
                        first_manifest.get("ml_mode_status", "ML_MODE_OFF")
                    )
                    summary["command_preview"] = (
                        job.command_preview or summary["command_preview"]
                    )
                    summary["artifact_inventory_path"] = str(
                        (output_root / "first_run_artifact_inventory.json").resolve()
                    )
                    summary["stage_summary_path"] = str(
                        (output_root / "first_run_stage_summary.json").resolve()
                    )
                    summary["blocker_codes"] = tuple(
                        dict.fromkeys(
                            (
                                *summary["blocker_codes"],
                                *(
                                    str(item)
                                    for item in first_manifest.get("blocker_codes")
                                    or ()
                                ),
                                *(
                                    str(item)
                                    for item in first_summary.get("blockers") or ()
                                ),
                            )
                        )
                    )
            if not found_ladder:
                payload, run_dir = _load_strategy_ladder_summary_payload(
                    output_root,
                    jobs=scoped_jobs,
                    run_id=summary["run_id"],
                )
                if isinstance(current_job_payload, dict) and current_job_payload:
                    payload = current_job_payload
                    run_dir = current_job_run_dir
                if not isinstance(payload, dict) or not payload:
                    continue
                found_any = True
                found_ladder = True
                summary["source_status"] = "ok"
                summary["run_id"] = str(payload.get("run_id", ""))
                for numeric_key in (
                    "candidate_sample_cap",
                    "effective_engine_native_sample_size",
                    "engine_count",
                ):
                    value = payload.get(numeric_key)
                    if isinstance(value, int):
                        summary[numeric_key] = value
                for string_key in (
                    "workflow_run_id",
                    "phase_run_id",
                    "parent_workflow_ref",
                    "candidate_cap_formula",
                    "candidate_discovery_limit_reason",
                    "candidate_discovery_mode",
                    "candidate_discovery_cap_status",
                    "silver_storage_mode_requested",
                    "silver_storage_mode_effective",
                    "replay_expansion_axis",
                    "candidate_source_status",
                    "matrix_count_inflation_status",
                ):
                    value = payload.get(string_key)
                    if isinstance(value, str) and value:
                        summary[string_key] = value
                for bool_key in (
                    "small_scope_enabled",
                    "full_scan_enabled",
                    "no_full_scan_enabled",
                    "candidate_discovery_limited",
                ):
                    value = payload.get(bool_key)
                    if isinstance(value, bool):
                        summary[bool_key] = value
                summary["final_status"] = str(
                    payload.get("final_status", "not_present")
                )
                summary["data_factory_status"] = str(
                    payload.get("data_factory_status", summary["data_factory_status"])
                )
                summary["raw_source_status"] = str(
                    payload.get("raw_source_status", summary["raw_source_status"])
                )
                summary["raw_source_provenance_status"] = str(
                    payload.get(
                        "raw_source_provenance_status",
                        summary["raw_source_provenance_status"],
                    )
                )
                summary["raw_source_typing_status"] = str(
                    payload.get(
                        "raw_source_typing_status",
                        summary["raw_source_typing_status"],
                    )
                )
                summary["pair_universe_status"] = str(
                    payload.get(
                        "pair_universe_status", summary["pair_universe_status"]
                    )
                )
                summary["silver_index_status"] = str(
                    payload.get("silver_index_status", summary["silver_index_status"])
                )
                summary["gold_feature_store_status"] = str(
                    payload.get(
                        "gold_feature_store_status",
                        summary["gold_feature_store_status"],
                    )
                )
                if not summary["backtest_proof_matrix_path"]:
                    summary["orderbook_reconstruction_status"] = str(
                        payload.get(
                            "orderbook_reconstruction_status",
                            summary["orderbook_reconstruction_status"],
                        )
                    )
                summary["ml_mode_status"] = str(
                    payload.get("ml_mode_status", summary["ml_mode_status"])
                )
                drift_value = payload.get("metadata_temporal_drift_days")
                if isinstance(drift_value, (int, float)):
                    summary["metadata_temporal_drift_days"] = float(drift_value)
                summary["feature_store_status"] = str(
                    payload.get("feature_store_status", "FEATURE_STORE_NOT_PROVEN")
                )
                summary["candidate_export_status"] = str(
                    payload.get(
                        "candidate_export_status", "CANDIDATE_EXPORT_NOT_PROVEN"
                    )
                )
                summary["raw_window_extraction_status"] = str(
                    payload.get(
                        "raw_window_extraction_status", "RAW_WINDOW_NOT_PROVEN"
                    )
                )
                summary["detailed_replay_status"] = str(
                    payload.get(
                        "detailed_replay_status", "DETAILED_REPLAY_NOT_PROVEN"
                    )
                )
                summary["capital_profile_generation_status"] = str(
                    payload.get(
                        "capital_profile_generation_status",
                        "CAPITAL_PROFILE_NOT_PROVEN",
                    )
                )
                summary["promotion_artifact_status"] = str(
                    payload.get(
                        "promotion_artifact_status",
                        "PROMOTION_ARTIFACTS_NOT_PROVEN",
                    )
                )
                summary["sample_size_survival_status"] = str(
                    payload.get(
                        "sample_size_survival_status", "SAMPLE_SIZE_NOT_PROVEN"
                    )
                )
                summary["statistical_validation_status"] = str(
                    payload.get(
                        "statistical_validation_status",
                        summary["statistical_validation_status"],
                    )
                )
                for numeric_key in (
                    "candidate_count",
                    "feature_row_count",
                    "raw_window_count",
                    "detailed_replay_count",
                    "raw_windows_total",
                    "trade_windows_found",
                    "trade_windows_missing",
                    "book_windows_found",
                    "book_windows_missing",
                    "ohlcv_windows_found",
                    "ohlcv_windows_missing",
                    "depth20_found",
                    "depth20_missing",
                    "sample_size_survival_count",
                    "statistical_validation_observation_count",
                    "statistical_validation_trial_count",
                    "statistical_validation_stationary_block_length",
                    "unique_candidate_count",
                    "base_event_count",
                    "engine_native_candidate_count",
                    "replay_record_count",
                    "evaluation_record_count",
                    "promotion_record_count",
                    "capital_bucket_record_count",
                    "capital_profile_count",
                    "engine_promotion_count",
                    "pair_promotion_count",
                    "strategy_promotion_count",
                    "expected_edge_proxy_count",
                    "expected_edge_governed_count",
                    "expected_edge_horizon",
                    "expected_edge_purge_window",
                    "expected_edge_embargo_window",
                    "candidate_engine_native_count",
                    "candidate_proxy_count",
                    "engine_native_records_built",
                    "executed_count",
                    "reduced_count",
                    "no_fill_count",
                ):
                    value = payload.get(numeric_key)
                    if isinstance(value, int):
                        summary[numeric_key] = value
                per_engine_candidate_count = payload.get("per_engine_candidate_count")
                if isinstance(per_engine_candidate_count, int):
                    summary["per_engine_candidate_count"] = per_engine_candidate_count
                replay_expansion_factor = payload.get("replay_expansion_factor")
                if isinstance(replay_expansion_factor, (int, float)):
                    summary["replay_expansion_factor"] = float(replay_expansion_factor)
                for float_key in (
                    "statistical_validation_benchmark_sharpe",
                    "statistical_validation_acceptance_floor",
                    "statistical_validation_sample_sharpe",
                    "statistical_validation_psr",
                    "statistical_validation_dsr",
                    "statistical_validation_effective_sample_size",
                    "statistical_validation_min_trl_required",
                ):
                    value = payload.get(float_key)
                    if isinstance(value, (int, float)):
                        summary[float_key] = float(value)
                for bool_key in (
                    "statistical_validation_min_trl_satisfied",
                    "statistical_validation_psr_passes_floor",
                    "statistical_validation_dsr_passes_floor",
                ):
                    value = payload.get(bool_key)
                    if isinstance(value, bool):
                        summary[bool_key] = value
                for key, default in (
                    ("candidate_truth_status", "CANDIDATE_TRUTH_NOT_PROVEN"),
                    ("expected_edge_truth_status", "EXPECTED_EDGE_TRUTH_NOT_PROVEN"),
                    ("engine_native_status", "ENGINE_NATIVE_NOT_REQUESTED"),
                ):
                    summary[key] = str(payload.get(key, summary.get(key, default)))
                for key, default in (
                    ("expected_edge_training_artifact_ref", ""),
                    ("expected_edge_label_source", "EXPECTED_EDGE_LABEL_SOURCE_NOT_PROVEN"),
                    ("expected_edge_label_fidelity", "EXPECTED_EDGE_PROXY_DISCOVERY_ONLY"),
                    ("expected_edge_anti_leakage_status", "EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN"),
                    ("expected_edge_walkforward_status", "EXPECTED_EDGE_WALKFORWARD_NOT_DECLARED"),
                ):
                    summary[key] = str(payload.get(key, summary.get(key, default)))
                for key, default in (
                    ("execution_label_source", "REPLAY_PROXY_EXECUTION"),
                    ("fee_model_source", "REPLAY_PROXY"),
                    ("spread_model_source", "REPLAY_PROXY"),
                    ("slippage_model_source", "REPLAY_PROXY"),
                    ("partial_fill_model_source", "REPLAY_PROXY"),
                    ("adverse_selection_source", "REPLAY_PROXY"),
                    ("order_type_selection_source", "REPLAY_PROXY"),
                    ("venue_constraints_source", "REPLAY_PROXY"),
                ):
                    summary[key] = str(payload.get(key, summary.get(key, default)))
                execution_gap_codes = payload.get("execution_fidelity_gap_codes")
                if isinstance(execution_gap_codes, list):
                    summary["execution_fidelity_gap_codes"] = tuple(
                        str(item) for item in execution_gap_codes[:20]
                    )
                expected_edge_blocker_codes = payload.get("expected_edge_blocker_codes")
                if isinstance(expected_edge_blocker_codes, list):
                    summary["expected_edge_blocker_codes"] = tuple(
                        str(item) for item in expected_edge_blocker_codes[:20]
                    )
                count_semantics_validator_codes = payload.get(
                    "count_semantics_validator_codes"
                )
                if isinstance(count_semantics_validator_codes, list):
                    summary["count_semantics_validator_codes"] = tuple(
                        str(item) for item in count_semantics_validator_codes[:20]
                    )
                statistical_validation_blocker_codes = payload.get(
                    "statistical_validation_blocker_codes"
                )
                if isinstance(statistical_validation_blocker_codes, list):
                    summary["statistical_validation_blocker_codes"] = tuple(
                        str(item) for item in statistical_validation_blocker_codes[:20]
                    )
                evidence_projection = (
                    _load_governed_audit_evidence_projection(run_dir)
                    if run_dir is not None
                    else {}
                )
                for numeric_key in (
                    "audited_evidence_count",
                    "scratch_only_evidence_count",
                    "promotion_grade_evidence_count",
                ):
                    value = payload.get(numeric_key, evidence_projection.get(numeric_key))
                    if isinstance(value, int):
                        summary[numeric_key] = value
                for string_key in (
                    "governed_audit_evidence_index_path",
                    "governed_evidence_status",
                    "run_manifest_evidence_class",
                    "capital_profiles_evidence_class",
                    "engine_promotion_evidence_class",
                    "pair_promotion_evidence_class",
                    "strategy_promotion_evidence_class",
                    "sample_size_survival_evidence_class",
                    "trade_detail_ledger_evidence_class",
                    "refusal_ledger_evidence_class",
                    "loss_analysis_ledger_evidence_class",
                ):
                    value = payload.get(string_key, evidence_projection.get(string_key))
                    if isinstance(value, str) and value:
                        summary[string_key] = value
                evidence_audit_blocker_codes = payload.get(
                    "evidence_audit_blocker_codes",
                    evidence_projection.get("evidence_audit_blocker_codes"),
                )
                if isinstance(evidence_audit_blocker_codes, list):
                    summary["evidence_audit_blocker_codes"] = tuple(
                        str(item) for item in evidence_audit_blocker_codes[:20]
                    )
                elif isinstance(evidence_audit_blocker_codes, tuple):
                    summary["evidence_audit_blocker_codes"] = tuple(
                        str(item) for item in evidence_audit_blocker_codes[:20]
                    )
                summary["command_preview"] = job.command_preview
                if not summary["artifact_inventory_path"]:
                    summary["artifact_inventory_path"] = job.artifact_inventory_path
                if not summary["stage_summary_path"]:
                    summary["stage_summary_path"] = job.stage_summary_path
                summary["displayed_summary_path"] = _summary_path_for_run_dir(run_dir)
                summary["blocker_codes"] = tuple(
                    dict.fromkeys(
                        (
                            *summary["blocker_codes"],
                            *(
                                str(item)
                                for item in payload.get("promotion_blockers") or ()
                            ),
                            *summary["evidence_audit_blocker_codes"],
                        )
                    )
                )
                displayed_summary_job = _match_strategy_ladder_run_dir_to_job(
                    run_dir,
                    current_job=latest_job,
                    last_successful_b2_job=last_successful_b2_job,
                    jobs=scoped_jobs,
                )
                current_job_summary_path = _job_explicit_strategy_ladder_summary_path(
                    latest_job
                )
                last_successful_b2_summary_path = _job_explicit_strategy_ladder_summary_path(
                    last_successful_b2_job
                )
                displayed_summary_path = str(summary["displayed_summary_path"] or "")
                if (
                    displayed_summary_job is latest_job
                    and _summary_path_matches(
                        displayed_summary_path,
                        current_job_summary_path,
                    )
                ):
                    summary["displayed_summary_source"] = (
                        "CURRENT_B2_SUMMARY"
                        if _job_phase_id(latest_job) == PHASE_B2
                        else "CURRENT_JOB_SUMMARY"
                    )
                    summary["summary_matches_current_job"] = True
                    summary["stale_summary_warning"] = False
                    summary["displayed_summary_job_id"] = latest_job.job_id
                elif (
                    last_successful_b2_job is not None
                    and displayed_summary_job is last_successful_b2_job
                    and _summary_path_matches(
                        displayed_summary_path,
                        last_successful_b2_summary_path,
                    )
                ):
                    summary["displayed_summary_source"] = "LAST_SUCCESSFUL_B2_SUMMARY"
                    summary["summary_matches_current_job"] = False
                    summary["stale_summary_warning"] = bool(
                        latest_job.job_id and displayed_summary_job is not latest_job
                    )
                    summary["displayed_summary_job_id"] = last_successful_b2_job.job_id
                else:
                    summary["displayed_summary_source"] = "WORKFLOW_CANONICAL_SUMMARY"
                    summary["summary_matches_current_job"] = False
                    summary["stale_summary_warning"] = bool(
                        latest_job.job_id and displayed_summary_job is not latest_job
                    )
                    summary["displayed_summary_job_id"] = ""
            if found_data_factory and found_first_run and found_ladder:
                break
        if found_any:
            if not found_ladder:
                summary["displayed_summary_source"] = "WORKFLOW_PHASE_ONLY"
                summary["summary_matches_current_job"] = True
                summary["stale_summary_warning"] = False
                summary["displayed_summary_job_id"] = latest_job.job_id
            typed_summary = StrategyLadderBacktestSummary.model_validate(summary)
            enriched_summary = _enrich_strategy_ladder_summary_from_artifacts(
                typed_summary,
                output_root=output_root,
                jobs=scoped_jobs,
                selected_candidate_id=selected_candidate_id,
            )
            surfaced_summary = _apply_strategy_ladder_proxy_fidelity_surface(
                enriched_summary,
                output_root=output_root,
            )
            return _apply_replay_governance_projection(surfaced_summary)
    return StrategyLadderBacktestSummary()


def _apply_replay_governance_projection(
    summary: StrategyLadderBacktestSummary,
) -> StrategyLadderBacktestSummary:
    from monitoring.replay_governance_projection import project_replay_governance

    projection = project_replay_governance(
        overall_backtest_proof_status=summary.overall_backtest_proof_status,
        promotion_artifact_status=summary.promotion_artifact_status,
        expected_edge_truth_status=summary.expected_edge_truth_status,
        execution_label_source=summary.execution_label_source,
        execution_fidelity_gap_codes=summary.execution_fidelity_gap_codes,
    )
    return summary.model_copy(
        update={
            "protocol_readiness_status": projection.readiness_status,
            "protocol_shadow_runtime_compatibility_status": (
                projection.shadow_runtime_compatibility_status
            ),
            "protocol_blocker_codes": projection.blocking_reasons,
            "protocol_micro_live_gate_message": projection.micro_live_gate.message,
            "protocol_live_gate_message": projection.live_gate.message,
        }
    )


def _load_threshold_rows(output_root: Path) -> tuple[dict[str, object], ...]:
    payload = _load_json(output_root / "feature_threshold_manifest.json", default={})
    rows = payload.get("thresholds_used") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return ()
    return tuple(dict(item) for item in rows if isinstance(item, dict))


def _apply_strategy_ladder_proxy_fidelity_surface(
    summary: StrategyLadderBacktestSummary,
    *,
    output_root: Path,
) -> StrategyLadderBacktestSummary:
    threshold_rows = _load_threshold_rows(output_root)
    surface = build_strategy_ladder_proxy_fidelity_surface(
        feature_store_status=summary.feature_store_status,
        feature_row_count=summary.feature_row_count,
        expected_edge_truth_status=summary.expected_edge_truth_status,
        expected_edge_governed_count=summary.expected_edge_governed_count,
        execution_fidelity_gap_codes=summary.execution_fidelity_gap_codes,
        threshold_rows=threshold_rows,
        historical_replay_venue=summary.historical_replay_venue,
        execution_target_venue=summary.execution_target_venue,
        backtest_class=summary.backtest_class,
        venue_transfer_status=summary.venue_transfer_status,
        promotion_artifact_status=summary.promotion_artifact_status,
        overall_backtest_proof_status=summary.overall_backtest_proof_status,
    )
    return summary.model_copy(
        update={
            "feature_store_pipeline_status": surface.feature_store_pipeline_status,
            "feature_row_sample_status": surface.feature_row_sample_status,
            "expected_edge_governance_status": surface.expected_edge_governance_status,
            "execution_fidelity_status": surface.execution_fidelity_status,
            "threshold_calibration_status": surface.threshold_calibration_status,
            "threshold_default_count": surface.threshold_counts.default_count,
            "threshold_calibrated_count": surface.threshold_counts.calibrated_count,
            "threshold_calibration_not_proven_count": (
                surface.threshold_counts.calibration_not_proven_count
            ),
            "proxy_fidelity_blocker_codes": surface.blocker_codes,
            "venue_transfer_status": surface.venue_transfer_status,
            "promotion_artifact_status": surface.promotion_artifact_status,
            "overall_backtest_proof_status": surface.overall_backtest_proof_status,
        }
    )


def _enrich_strategy_ladder_summary_from_artifacts(
    summary: StrategyLadderBacktestSummary,
    *,
    output_root: Path,
    jobs: tuple[CockpitBacktestJobRecord, ...],
    selected_candidate_id: str,
) -> StrategyLadderBacktestSummary:
    run_dir = _resolve_strategy_ladder_run_dir(
        output_root,
        jobs=jobs,
        run_id=summary.run_id,
    )
    updates: dict[str, object] = {}
    if run_dir is not None:
        b1_candidate_events_path = (
            run_dir.parents[2]
            / "phase_b1_candidate_discovery"
            / "backtest_strategy_ladder"
            / run_dir.name
            / "fast_candidates"
            / "candidate_events.jsonl"
        )
        b1_candidate_summary_path = b1_candidate_events_path.with_name("candidate_summary.json")
        run_manifest_payload = _load_json(run_dir / "run_manifest.json", default={})
        if isinstance(run_manifest_payload, dict):
            for numeric_key in (
                "feature_row_count",
                "sample_size_survival_count",
                "unique_candidate_count",
                "base_event_count",
                "engine_native_candidate_count",
                "discovery_pre_candidate_count",
                "engine_native_preselected_count",
                "preselection_hard_rejected_count",
                "preselection_soft_flagged_count",
                "preselection_passed_count",
                "b2_replay_candidate_count",
                "trade_eligible_candidate_count",
                "preselection_rejection_count",
                "replay_savings_estimate_count",
                "replay_record_count",
                "evaluation_record_count",
                "promotion_record_count",
                "capital_bucket_record_count",
                "capital_profile_count",
                "engine_promotion_count",
                "pair_promotion_count",
                "strategy_promotion_count",
                "expected_edge_proxy_count",
                "expected_edge_governed_count",
                "candidate_engine_native_count",
                "candidate_proxy_count",
                "engine_native_records_built",
            ):
                value = run_manifest_payload.get(numeric_key)
                if isinstance(value, int):
                    updates[numeric_key] = value
            per_engine_candidate_count = run_manifest_payload.get("per_engine_candidate_count")
            if isinstance(per_engine_candidate_count, int):
                updates["per_engine_candidate_count"] = per_engine_candidate_count
            replay_expansion_factor = run_manifest_payload.get("replay_expansion_factor")
            if isinstance(replay_expansion_factor, (int, float)):
                updates["replay_expansion_factor"] = float(replay_expansion_factor)
            for string_key in (
                "candidate_source_status",
                "replay_expansion_axis",
                "matrix_count_inflation_status",
                "preselection_status",
                "replay_input_mode_status",
                "b1_5_policy_mode",
            ):
                value = run_manifest_payload.get(string_key)
                if isinstance(value, str) and value:
                    updates[string_key] = value
            for bool_key in ("preselected_only", "diagnostic_full_replay"):
                value = run_manifest_payload.get(bool_key)
                if isinstance(value, bool):
                    updates[bool_key] = value
            validator_codes = run_manifest_payload.get("count_semantics_validator_codes")
            if isinstance(validator_codes, list):
                updates["count_semantics_validator_codes"] = tuple(
                    str(item) for item in validator_codes[:20]
                )
        preselection_summary_payload = _load_json(
            run_dir / "reports" / "preselection_summary.json",
            default={},
        )
        if isinstance(preselection_summary_payload, dict) and preselection_summary_payload:
            for numeric_key in (
                "discovery_pre_candidate_count",
                "engine_native_preselected_count",
                "preselection_hard_rejected_count",
                "preselection_soft_flagged_count",
                "preselection_passed_count",
                "b2_replay_candidate_count",
                "preselection_rejection_count",
                "replay_savings_estimate_count",
            ):
                value = preselection_summary_payload.get(numeric_key)
                if isinstance(value, int):
                    updates[numeric_key] = value
            for string_key in ("status", "replay_input_mode_status", "b1_5_policy_mode"):
                value = preselection_summary_payload.get(string_key)
                if isinstance(value, str) and value:
                    updates[
                        "preselection_status"
                        if string_key == "status"
                        else "replay_input_mode_status"
                        if string_key == "replay_input_mode_status"
                        else "b1_5_policy_mode"
                    ] = value
            for bool_key in ("preselected_only", "diagnostic_full_replay"):
                value = preselection_summary_payload.get(bool_key)
                if isinstance(value, bool):
                    updates[bool_key] = value
            rejection_reasons = preselection_summary_payload.get("top_rejection_reasons")
            if isinstance(rejection_reasons, list):
                updates["preselection_top_rejection_reasons"] = tuple(
                    dict(item) for item in rejection_reasons[:12] if isinstance(item, dict)
                )
            hard_rejection_reasons = preselection_summary_payload.get(
                "top_hard_rejection_reasons"
            )
            if isinstance(hard_rejection_reasons, list):
                updates["preselection_top_hard_rejection_reasons"] = tuple(
                    dict(item)
                    for item in hard_rejection_reasons[:12]
                    if isinstance(item, dict)
                )
            soft_advisory_reasons = preselection_summary_payload.get(
                "top_soft_advisory_reasons"
            )
            if isinstance(soft_advisory_reasons, list):
                updates["preselection_top_soft_advisory_reasons"] = tuple(
                    dict(item)
                    for item in soft_advisory_reasons[:12]
                    if isinstance(item, dict)
                )
        preselection_rejection_rows = _load_jsonl_rows(
            run_dir / "preselection_rejection_ledger.jsonl",
            limit=25,
        )
        if preselection_rejection_rows:
            updates["preselection_rejection_rows"] = tuple(
                dict(item) for item in preselection_rejection_rows
            )
        candidate_summary_payload = _load_json(
            run_dir / "fast_candidates" / "candidate_summary.json",
            default={},
        )
        source_candidate_summary_payload = candidate_summary_payload
        if b1_candidate_summary_path.is_file():
            b1_candidate_summary_payload = _load_json(
                b1_candidate_summary_path,
                default={},
            )
            if isinstance(b1_candidate_summary_payload, dict) and b1_candidate_summary_payload:
                source_candidate_summary_payload = b1_candidate_summary_payload
        if isinstance(source_candidate_summary_payload, dict):
            for numeric_key in (
                "candidate_count",
                "unique_candidate_count",
                "base_event_count",
                "engine_native_candidate_count",
                "discovery_pre_candidate_count",
                "engine_native_preselected_count",
                "preselection_hard_rejected_count",
                "preselection_soft_flagged_count",
                "preselection_passed_count",
                "b2_replay_candidate_count",
                "trade_eligible_candidate_count",
                "preselection_rejection_count",
                "replay_savings_estimate_count",
                "candidate_sample_cap",
                "effective_engine_native_sample_size",
                "engine_count",
            ):
                value = source_candidate_summary_payload.get(numeric_key)
                if isinstance(value, int):
                    updates[numeric_key] = value
            per_engine_candidate_count = source_candidate_summary_payload.get(
                "per_engine_candidate_count"
            )
            if isinstance(per_engine_candidate_count, int):
                updates["per_engine_candidate_count"] = per_engine_candidate_count
            for string_key in (
                "candidate_source_status",
                "candidate_cap_formula",
                "candidate_discovery_status",
                "candidate_discovery_limit_reason",
                "candidate_discovery_mode",
                "candidate_discovery_cap_status",
                "preselection_status",
                "replay_input_mode_status",
                "b1_5_policy_mode",
            ):
                value = source_candidate_summary_payload.get(string_key)
                if isinstance(value, str) and value:
                    updates[string_key] = value
            for bool_key in (
                "small_scope_enabled",
                "full_scan_enabled",
                "no_full_scan_enabled",
                "candidate_discovery_limited",
                "preselected_only",
                "diagnostic_full_replay",
            ):
                value = source_candidate_summary_payload.get(bool_key)
                if isinstance(value, bool):
                    updates[bool_key] = value
        live_candidate_count = _count_jsonl_lines(
            run_dir / "fast_candidates" / "candidate_events.jsonl"
        )
        if summary.candidate_count == 0 and live_candidate_count > 0:
            updates["candidate_count"] = live_candidate_count
            if summary.candidate_export_status == "CANDIDATE_EXPORT_NOT_PROVEN":
                updates["candidate_export_status"] = "CANDIDATE_EXPORT_READY"
        live_raw_window_count = _count_named_artifacts(
            run_dir / "raw_windows",
            "window_manifest.json",
        )
        if summary.raw_window_count == 0 and live_raw_window_count > 0:
            candidate_baseline = int(
                updates.get("candidate_count", summary.candidate_count)
            )
            updates["raw_window_count"] = live_raw_window_count
            if summary.raw_window_extraction_status == "RAW_WINDOW_NOT_PROVEN":
                updates["raw_window_extraction_status"] = (
                    "RAW_WINDOW_READY"
                    if candidate_baseline > 0 and live_raw_window_count >= candidate_baseline
                    else "RAW_WINDOW_PARTIAL"
                )
        live_detailed_replay_count = _count_named_artifacts(
            run_dir / "detailed_replay",
            "*.json",
        )
        if summary.detailed_replay_count == 0 and live_detailed_replay_count > 0:
            candidate_baseline = int(
                updates.get("candidate_count", summary.candidate_count)
            )
            updates["detailed_replay_count"] = live_detailed_replay_count
            if summary.detailed_replay_status == "DETAILED_REPLAY_NOT_PROVEN":
                resolved_raw_window_status = str(
                    updates.get(
                        "raw_window_extraction_status",
                        summary.raw_window_extraction_status,
                    )
                )
                updates["detailed_replay_status"] = (
                    "DETAILED_REPLAY_PARTIAL"
                    if resolved_raw_window_status != "RAW_WINDOW_READY"
                    else (
                        "DETAILED_REPLAY_READY"
                        if candidate_baseline > 0
                        and live_detailed_replay_count >= candidate_baseline
                        else "DETAILED_REPLAY_PARTIAL"
                    )
                )
        engine_rows = _load_json_array_rows(run_dir / "reports" / "engine_matrix.json")
        pair_rows = _load_json_array_rows(run_dir / "reports" / "pair_matrix.json")
        timeframe_rows = _load_json_array_rows(
            run_dir / "reports" / "timeframe_matrix.json"
        )
        if engine_rows:
            updates["engine_matrix_rows"] = tuple(engine_rows[:8])
        if pair_rows:
            updates["pair_matrix_rows"] = tuple(pair_rows[:8])
        if timeframe_rows:
            updates["timeframe_matrix_rows"] = tuple(timeframe_rows[:8])

        candidate_events_path = run_dir / "fast_candidates" / "candidate_events.jsonl"
        all_candidate_rows = _load_all_jsonl_rows(candidate_events_path)
        count_semantics_rows = all_candidate_rows
        if b1_candidate_events_path.is_file():
            b1_candidate_rows = _load_all_jsonl_rows(b1_candidate_events_path)
            if b1_candidate_rows:
                count_semantics_rows = b1_candidate_rows
        source_candidate_semantics = _derive_candidate_count_semantics(count_semantics_rows)
        materialized_candidate_semantics = (
            _derive_candidate_count_semantics(all_candidate_rows)
            or source_candidate_semantics
        )
        for field_name in (
            "candidate_count",
            "unique_candidate_count",
            "base_event_count",
            "per_engine_candidate_count",
        ):
            if field_name in source_candidate_semantics:
                updates[field_name] = source_candidate_semantics[field_name]
        for field_name in (
            "engine_native_candidate_count",
            "candidate_engine_native_count",
            "candidate_proxy_count",
            "candidate_source_status",
        ):
            if field_name in materialized_candidate_semantics:
                updates[field_name] = materialized_candidate_semantics[field_name]
        candidate_rows = _load_jsonl_rows(candidate_events_path, limit=25)
        selected_id = selected_candidate_id.strip()
        if not selected_id and candidate_rows:
            selected_id = str(candidate_rows[0].get("candidate_id") or "")
        replay_cache: dict[str, dict[str, object]] = {}
        explorer_rows: list[dict[str, object]] = []
        for row in candidate_rows:
            candidate_id = str(row.get("candidate_id") or "")
            replay_payload = _load_candidate_replay_payload(
                run_dir, candidate_id, cache=replay_cache
            )
            explorer_rows.append(_build_candidate_explorer_row(row, replay_payload))
        if explorer_rows:
            updates["candidate_rows"] = tuple(explorer_rows)
        if selected_id:
            selected_row = None
            for row in candidate_rows:
                if str(row.get("candidate_id") or "") == selected_id:
                    selected_row = row
                    break
            if selected_row is None:
                selected_row = _load_candidate_row_by_id(candidate_events_path, selected_id)
            if selected_row is not None:
                replay_payload = _load_candidate_replay_payload(
                    run_dir, selected_id, cache=replay_cache
                )
                window_payload = _load_candidate_window_payload(run_dir, selected_id)
                updates["selected_candidate_id"] = selected_id
                updates["selected_candidate_detail"] = _build_candidate_detail_payload(
                    selected_row,
                    replay_payload,
                )
                updates["selected_candidate_replay"] = _build_candidate_replay_payload(
                    replay_payload
                )
                updates["selected_candidate_window"] = (
                    dict(window_payload) if window_payload else {}
                )

        all_trade_rows = _load_all_jsonl_rows(run_dir / "trade_detail_ledger.jsonl")
        all_refusal_rows = _load_all_jsonl_rows(run_dir / "refusal_ledger.jsonl")
        all_loss_rows = _load_all_jsonl_rows(run_dir / "loss_analysis_ledger.jsonl")
        trade_rows = all_trade_rows[:25]
        refusal_rows = all_refusal_rows[:25]
        loss_rows = all_loss_rows[:25]
        if trade_rows:
            updates["trade_ledger_rows"] = tuple(trade_rows)
        if refusal_rows:
            updates["refusal_ledger_rows"] = tuple(refusal_rows)
        if loss_rows:
            updates["loss_ledger_rows"] = tuple(loss_rows)
        updates.update(
            _derive_trade_summary(
                summary=summary,
                trade_rows=all_trade_rows,
                refusal_rows=all_refusal_rows,
                loss_rows=all_loss_rows,
                pair_rows=pair_rows,
            )
        )
        updates.update(
            _derive_no_trade_refusal_audit(
                summary=summary,
                refusal_rows=all_refusal_rows,
                engine_rows=engine_rows,
                pair_rows=pair_rows,
            )
        )
        updates.update(_load_engine_no_trade_diagnosis_updates(run_dir))
        updates.update(_load_gate_waterfall_updates(run_dir))
        unique_candidate_count = int(
            updates.get(
                "unique_candidate_count",
                updates.get("candidate_count", summary.candidate_count),
            )
        )
        replay_record_count = int(
            updates.get(
                "replay_record_count",
                updates.get(
                    "detailed_replay_count",
                    summary.replay_record_count or summary.detailed_replay_count,
                ),
            )
        )
        updates.setdefault("replay_record_count", replay_record_count)
        updates.setdefault("evaluation_record_count", replay_record_count)
        updates.setdefault("promotion_record_count", replay_record_count)
        updates.setdefault("capital_bucket_record_count", replay_record_count)
        if unique_candidate_count > 0 and replay_record_count > 0:
            updates.setdefault(
                "replay_expansion_factor",
                round(replay_record_count / unique_candidate_count, 6),
            )
            if replay_record_count > unique_candidate_count:
                updates.setdefault(
                    "replay_expansion_axis",
                    "capital_bucket"
                    if int(
                        updates.get(
                            "capital_profile_count",
                            getattr(summary, "capital_profile_count", 0),
                        )
                        or 0
                    )
                    > 1
                    else "evaluation_context",
                )
        matrix_status, validator_codes = _derive_count_semantics_validators(
            unique_candidate_count=unique_candidate_count,
            replay_record_count=replay_record_count,
            replay_expansion_axis=str(updates.get("replay_expansion_axis") or ""),
            candidate_source_status=str(
                updates.get("candidate_source_status", summary.candidate_source_status)
            ),
            engine_native_status=str(
                updates.get("engine_native_status", summary.engine_native_status)
            ),
            engine_native_candidate_count=int(
                updates.get(
                    "engine_native_candidate_count",
                    updates.get(
                        "candidate_engine_native_count",
                        summary.engine_native_candidate_count,
                    ),
                )
                or 0
            ),
            candidate_rows=count_semantics_rows,
            pair_rows=pair_rows,
            engine_rows=engine_rows,
        )
        updates["matrix_count_inflation_status"] = matrix_status
        updates["count_semantics_validator_codes"] = validator_codes
        if (
            int(updates.get("candidate_proxy_count", summary.candidate_proxy_count) or 0) > 0
            and str(updates.get("candidate_truth_status", summary.candidate_truth_status))
            in {
                "CANDIDATE_TRUTH_NOT_PROVEN",
                "CANDIDATE_ENGINE_NATIVE_NOT_PROVEN",
            }
        ):
            updates["candidate_truth_status"] = "CANDIDATE_TRUTH_PROXY_PRESENT"
        updates.update(_load_replay_performance_profile_updates(run_dir))
    gold_manifest_payload = _load_json(output_root / "gold_feature_manifest.json", default={})
    if isinstance(gold_manifest_payload, dict):
        feature_row_count = gold_manifest_payload.get("feature_row_count")
        if isinstance(feature_row_count, int) and feature_row_count >= 0:
            updates.setdefault("feature_row_count", feature_row_count)

    cancelled_job = next(
        (
            job
            for job in jobs
            if job.status.value in {"JOB_CANCELLED", "cancelled", "JOB_CANCELLING"}
        ),
        None,
    )
    candidate_count = int(updates.get("candidate_count", summary.candidate_count))
    raw_window_count = int(updates.get("raw_window_count", summary.raw_window_count))
    detailed_replay_count = int(
        updates.get("detailed_replay_count", summary.detailed_replay_count)
    )
    effective_sample_size = int(
        updates.get(
            "effective_engine_native_sample_size",
            summary.effective_engine_native_sample_size,
        )
    )
    engine_count = int(updates.get("engine_count", summary.engine_count or 4))
    sample_cap = int(updates.get("candidate_sample_cap", summary.candidate_sample_cap))
    if sample_cap <= 0 and effective_sample_size > 0 and engine_count > 0:
        sample_cap = effective_sample_size * engine_count
        updates["candidate_sample_cap"] = sample_cap
        updates["candidate_cap_formula"] = f"{engine_count} engines x {effective_sample_size}"
    if sample_cap > 0 and candidate_count >= sample_cap:
        updates["candidate_discovery_cap_status"] = "CANDIDATE_DISCOVERY_SAMPLE_CAPPED"
        updates["candidate_discovery_limited"] = True
        updates["candidate_discovery_limit_reason"] = "ENGINE_NATIVE_SAMPLE_CAP_ACTIVE"
    elif candidate_count > 0 and summary.full_scan_enabled:
        updates["candidate_discovery_cap_status"] = "CANDIDATE_DISCOVERY_EXHAUSTED"
        updates["candidate_discovery_limited"] = False
        updates["candidate_discovery_limit_reason"] = "DISCOVERY_EXHAUSTED_BEFORE_CAP"
    elif summary.full_scan_enabled:
        updates["candidate_discovery_cap_status"] = "CANDIDATE_DISCOVERY_FULL_SCAN_ENABLED"
    if cancelled_job is not None and (
        candidate_count > 0 or raw_window_count > 0 or detailed_replay_count > 0
    ):
        updates["run_state_banner_status"] = "CANCELLED_AFTER_PARTIAL_ARTIFACT_PRODUCTION"
        updates["run_state_banner_message"] = "Cancelled after partial artifact production."
        updates["run_state_banner_details"] = tuple(
            detail
            for detail in (
                f"candidate_count={candidate_count}" if candidate_count > 0 else "",
                f"raw_window_count={raw_window_count}" if raw_window_count > 0 else "",
                (
                    f"detailed_replay_count={detailed_replay_count}"
                    if detailed_replay_count > 0
                    else ""
                ),
            )
            if detail
        )
    elif (
        not summary.run_state_banner_status
        and summary.promotion_artifact_status == "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY"
    ):
        updates["run_state_banner_status"] = "PROMOTION_BLOCKED_BY_EXECUTION_FIDELITY"
        updates["run_state_banner_message"] = (
            "Promotion artifacts are blocked by execution fidelity gaps."
        )
        updates["run_state_banner_details"] = (
            summary.protocol_blocker_codes or summary.execution_fidelity_gap_codes
        )
    return summary.model_copy(update=updates)


def _load_replay_performance_profile_updates(run_dir: Path) -> dict[str, object]:
    profile_path = run_dir / "replay_performance_profile.json"
    profile_payload = _load_json(profile_path, default={})
    if not isinstance(profile_payload, dict) or not profile_payload:
        return {}

    updates: dict[str, object] = {
        "replay_performance_profile_status": str(
            profile_payload.get("status") or "REPLAY_PERFORMANCE_PROFILE_NOT_PROVEN"
        ),
        "replay_performance_profile_path": str(profile_path.resolve()),
    }

    def _optional_float(value: object) -> float | None:
        if isinstance(value, (int, float)):
            return round(float(value), 6)
        return None

    def _optional_non_negative_int(value: object) -> int | None:
        if isinstance(value, int) and value >= 0:
            return value
        return None

    for source_key, target_key in (
        ("total_wall_time_s", "replay_perf_total_wall_time_s"),
        ("total_cpu_time_s", "replay_perf_total_cpu_time_s"),
        ("total_io_wait_estimate_s", "replay_perf_total_io_wait_estimate_s"),
        ("replay_parallelism_ratio", "replay_perf_replay_parallelism_ratio"),
        ("replay_cpu_utilization", "replay_perf_replay_cpu_utilization"),
        ("replay_queue_wait_time_s", "replay_perf_replay_queue_wait_time_s"),
    ):
        value = _optional_float(profile_payload.get(source_key))
        if value is not None:
            updates[target_key] = value

    for source_key, target_key in (
        ("rows_processed", "replay_perf_rows_processed"),
        ("files_scanned", "replay_perf_files_scanned"),
        ("replay_workers_used", "replay_perf_replay_workers_used"),
        ("candidate_count", "candidate_count"),
        ("replay_record_count", "replay_record_count"),
    ):
        value = _optional_non_negative_int(profile_payload.get(source_key))
        if value is not None:
            updates[target_key] = value

    total_wall_time_s = _optional_float(profile_payload.get("total_wall_time_s"))
    profile_rows_processed = int(updates.get("replay_perf_rows_processed") or 0)
    profile_replay_record_count = _optional_non_negative_int(
        profile_payload.get("replay_record_count")
    ) or 0
    if total_wall_time_s is not None and total_wall_time_s > 0.0:
        updates["replay_perf_rows_per_s"] = round(
            profile_rows_processed / total_wall_time_s,
            6,
        )
        updates["replay_perf_records_per_s"] = round(
            profile_replay_record_count / total_wall_time_s,
            6,
        )

    indexed_lookup_metrics = profile_payload.get("indexed_lookup_metrics")
    if isinstance(indexed_lookup_metrics, dict):
        status = indexed_lookup_metrics.get("status")
        if isinstance(status, str) and status:
            updates["replay_perf_indexed_lookup_status"] = status
        hit_rate = _optional_float(indexed_lookup_metrics.get("indexed_lookup_hit_rate"))
        if hit_rate is not None:
            updates["replay_perf_indexed_lookup_hit_rate"] = hit_rate
        miss_count = _optional_non_negative_int(
            indexed_lookup_metrics.get("index_lookup_miss_count")
        )
        if miss_count is not None:
            updates["replay_perf_index_lookup_miss_count"] = miss_count
        fallback_scan_count = _optional_non_negative_int(
            indexed_lookup_metrics.get("fallback_scan_count")
        )
        if fallback_scan_count is not None:
            updates["replay_perf_fallback_scan_count"] = fallback_scan_count

    window_cache_metrics = profile_payload.get("window_cache_metrics")
    if isinstance(window_cache_metrics, dict):
        status = window_cache_metrics.get("status")
        if isinstance(status, str) and status:
            updates["replay_perf_window_cache_status"] = status
        hit_count = _optional_non_negative_int(window_cache_metrics.get("cache_hit_count"))
        if hit_count is not None:
            updates["replay_perf_window_cache_hit_count"] = hit_count
        miss_count = _optional_non_negative_int(window_cache_metrics.get("cache_miss_count"))
        if miss_count is not None:
            updates["replay_perf_window_cache_miss_count"] = miss_count
        reuse_ratio = _optional_float(window_cache_metrics.get("cache_reuse_ratio"))
        if reuse_ratio is not None:
            updates["replay_perf_window_cache_reuse_ratio"] = reuse_ratio

    parquet_fast_path_status = profile_payload.get("parquet_fast_path_status")
    if isinstance(parquet_fast_path_status, str) and parquet_fast_path_status:
        updates["replay_perf_parquet_fast_path_status"] = parquet_fast_path_status
    research_fast_debug_mode_status = profile_payload.get(
        "research_fast_debug_mode_status"
    )
    if (
        isinstance(research_fast_debug_mode_status, str)
        and research_fast_debug_mode_status
    ):
        updates["replay_perf_research_fast_debug_mode_status"] = (
            research_fast_debug_mode_status
        )
    bottleneck_summary = profile_payload.get("bottleneck_summary")
    if isinstance(bottleneck_summary, list):
        updates["replay_perf_bottleneck_summary"] = tuple(
            str(item) for item in bottleneck_summary[:5]
        )

    phase_lookup: dict[str, dict[str, object]] = {}
    phases = profile_payload.get("phases")
    if isinstance(phases, list):
        for item in phases:
            if not isinstance(item, dict):
                continue
            phase_name = str(item.get("phase_name") or "")
            if phase_name:
                phase_lookup[phase_name] = item

    for phase_name, target_key in (
        ("raw_window_extraction", "replay_perf_raw_window_wall_time_s"),
        ("replay_orchestration", "replay_perf_replay_wall_time_s"),
        ("label_store_generation", "replay_perf_label_store_wall_time_s"),
        ("matrix_generation", "replay_perf_matrix_wall_time_s"),
        ("dashboard_report_generation", "replay_perf_report_wall_time_s"),
    ):
        phase_payload = phase_lookup.get(phase_name)
        if phase_payload is None:
            continue
        wall_time_s = _optional_float(phase_payload.get("wall_time_s"))
        if wall_time_s is not None:
            updates[target_key] = wall_time_s

    return updates


def _resolve_strategy_ladder_run_dir(
    output_root: Path,
    *,
    jobs: tuple[CockpitBacktestJobRecord, ...],
    run_id: str,
) -> Path | None:
    for candidate in _strategy_ladder_run_dir_candidates(
        output_root,
        jobs=jobs,
        run_id=run_id,
    ):
        if candidate.is_dir():
            return candidate.resolve()
    return None


_SUCCESSFUL_JOB_STATUSES = {
    CockpitBacktestJobStatus.COMPLETED.value,
    CockpitBacktestJobStatus.JOB_COMPLETED.value,
    CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS.value,
}


def _job_phase_id(job: CockpitBacktestJobRecord) -> str:
    if job.phase_id:
        return job.phase_id
    if job.action_name:
        return phase_id_for_action(job.action_name)
    return ""


def _job_explicit_strategy_ladder_run_dirs(
    job: CockpitBacktestJobRecord,
) -> tuple[Path, ...]:
    candidates: list[Path] = []
    for raw_path in (
        job.stage_summary_path,
        job.artifact_inventory_path,
        *job.output_refs,
    ):
        if not raw_path:
            continue
        extracted = _extract_strategy_ladder_run_dir(Path(raw_path))
        if extracted is not None:
            candidates.append(extracted.resolve())
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return tuple(unique)


def _job_explicit_strategy_ladder_summary_path(
    job: CockpitBacktestJobRecord | None,
) -> str:
    if job is None:
        return ""
    if job.stage_summary_path:
        return str(Path(job.stage_summary_path).resolve())
    payload, run_dir = _load_strategy_ladder_summary_payload_for_job(job)
    if isinstance(payload, dict) and payload and run_dir is not None:
        return str((run_dir / "reports" / "strategy_ladder_summary.json").resolve())
    return ""


def _load_strategy_ladder_summary_payload_for_job(
    job: CockpitBacktestJobRecord,
) -> tuple[dict[str, object], Path | None]:
    for run_dir in _job_explicit_strategy_ladder_run_dirs(job):
        payload = _load_json(
            run_dir / "reports" / "strategy_ladder_summary.json",
            default={},
        )
        if isinstance(payload, dict) and payload:
            return payload, run_dir
    if not job.output_root:
        return {}, None
    output_root = Path(job.output_root)
    run_id = job.workflow_run_id or job.phase_run_id or ""
    return _load_strategy_ladder_summary_payload(
        output_root,
        jobs=(job,),
        run_id=run_id,
    )


def _find_last_successful_b2_summary(
    jobs: tuple[CockpitBacktestJobRecord, ...],
) -> tuple[CockpitBacktestJobRecord | None, dict[str, object], Path | None]:
    ordered_jobs = sorted(
        jobs,
        key=lambda record: _parse_iso(record.latest_activity_iso)
        or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )
    for job in ordered_jobs:
        if _job_phase_id(job) != PHASE_B2:
            continue
        if job.status.value not in _SUCCESSFUL_JOB_STATUSES:
            continue
        payload, run_dir = _load_strategy_ladder_summary_payload_for_job(job)
        if isinstance(payload, dict) and payload:
            return job, payload, run_dir
    return None, {}, None


def _summary_path_for_run_dir(run_dir: Path | None) -> str:
    if run_dir is None:
        return ""
    return str((run_dir / "reports" / "strategy_ladder_summary.json").resolve())


def _resolved_path_str(raw_path: str) -> str:
    if not raw_path:
        return ""
    try:
        return str(Path(raw_path).resolve())
    except OSError:
        return ""


def _summary_path_matches(left: str, right: str) -> bool:
    return bool(left) and bool(right) and _resolved_path_str(left) == _resolved_path_str(right)


def _job_explicitly_references_run_dir(
    job: CockpitBacktestJobRecord,
    run_dir: Path | None,
) -> bool:
    if run_dir is None:
        return False
    target = str(run_dir.resolve())
    return any(str(candidate) == target for candidate in _job_explicit_strategy_ladder_run_dirs(job))


def _match_strategy_ladder_run_dir_to_job(
    run_dir: Path | None,
    *,
    current_job: CockpitBacktestJobRecord,
    last_successful_b2_job: CockpitBacktestJobRecord | None,
    jobs: tuple[CockpitBacktestJobRecord, ...],
) -> CockpitBacktestJobRecord | None:
    if run_dir is None:
        return None
    if _job_explicitly_references_run_dir(current_job, run_dir):
        return current_job
    if (
        last_successful_b2_job is not None
        and _job_explicitly_references_run_dir(last_successful_b2_job, run_dir)
    ):
        return last_successful_b2_job
    for job in jobs:
        if _job_explicitly_references_run_dir(job, run_dir):
            return job
    return None


def _count_named_artifacts(root: Path, pattern: str) -> int:
    if not root.is_dir():
        return 0
    return sum(1 for path in root.rglob(pattern) if path.is_file())


def _count_jsonl_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
    except OSError:
        return 0


def _load_all_jsonl_rows(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    rows: list[dict[str, object]] = []
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict) and not bool(payload.get("artifact_header")):
                    rows.append(payload)
    except OSError:
        return []
    return rows


def _derive_candidate_count_semantics(
    candidate_rows: list[dict[str, object]],
) -> dict[str, object]:
    if not candidate_rows:
        return {}
    unique_keys = {
        (
            str(row.get("candidate_id") or ""),
            _candidate_timestamp_ms(row),
            str(row.get("pair") or ""),
            str(row.get("timeframe") or ""),
            str(row.get("engine_id") or ""),
            str(row.get("strategy_id") or ""),
        )
        for row in candidate_rows
    }
    base_keys = {
        (
            _candidate_timestamp_ms(row),
            str(row.get("pair") or ""),
            str(row.get("timeframe") or ""),
        )
        for row in candidate_rows
    }
    counts_by_engine: dict[str, int] = {}
    sources: set[str] = set()
    engine_native_candidate_count = 0
    candidate_proxy_count = 0
    for row in candidate_rows:
        engine_id = str(row.get("engine_id") or "")
        if engine_id:
            counts_by_engine[engine_id] = counts_by_engine.get(engine_id, 0) + 1
        source = str(row.get("candidate_source") or "").strip()
        if source:
            sources.add(source)
        if source == "ENGINE_NATIVE":
            engine_native_candidate_count += 1
        elif source == "COMPAT_FEATURE_DISCOVERY":
            candidate_proxy_count += 1
    per_engine_candidate_count: int | None = None
    if counts_by_engine:
        unique_counts = set(counts_by_engine.values())
        if len(unique_counts) == 1:
            per_engine_candidate_count = next(iter(unique_counts))
    if not sources:
        candidate_source_status = "CANDIDATE_SOURCE_NOT_PROVEN"
    elif sources == {"ENGINE_NATIVE"}:
        candidate_source_status = "CANDIDATE_SOURCE_ENGINE_NATIVE"
    elif sources == {"COMPAT_FEATURE_DISCOVERY"}:
        candidate_source_status = "CANDIDATE_SOURCE_COMPAT_PROXY_DISCOVERY"
    elif "ENGINE_NATIVE" in sources and "COMPAT_FEATURE_DISCOVERY" in sources:
        candidate_source_status = "CANDIDATE_SOURCE_MIXED_ENGINE_AND_PROXY"
    else:
        candidate_source_status = "CANDIDATE_SOURCE_FALLBACK_SYNTHETIC"
    return {
        "candidate_count": len(unique_keys),
        "unique_candidate_count": len(unique_keys),
        "base_event_count": len(base_keys),
        "per_engine_candidate_count": per_engine_candidate_count,
        "engine_native_candidate_count": engine_native_candidate_count,
        "candidate_engine_native_count": engine_native_candidate_count,
        "candidate_proxy_count": candidate_proxy_count,
        "candidate_source_status": candidate_source_status,
    }


def _derive_count_semantics_validators(
    *,
    unique_candidate_count: int,
    replay_record_count: int,
    replay_expansion_axis: str,
    candidate_source_status: str,
    engine_native_status: str,
    engine_native_candidate_count: int,
    candidate_rows: list[dict[str, object]],
    pair_rows: list[dict[str, object]],
    engine_rows: list[dict[str, object]],
) -> tuple[str, tuple[str, ...]]:
    validator_codes: list[str] = []
    pair_candidate_count = max(
        (int(row.get("candidate_count") or 0) for row in pair_rows),
        default=0,
    )
    if unique_candidate_count > 0 and pair_candidate_count > unique_candidate_count:
        validator_codes.append("MATRIX_COUNT_INFLATION")
    engine_candidate_sum = sum(int(row.get("candidate_count") or 0) for row in engine_rows)
    engine_evaluation_declared = any(
        int(row.get("engine_evaluation_count") or 0) > 0
        or int(row.get("evaluation_record_count") or 0) > 0
        or str(row.get("replay_expansion_axis") or "").strip()
        for row in engine_rows
    )
    if (
        unique_candidate_count > 0
        and engine_candidate_sum > unique_candidate_count
        and not engine_evaluation_declared
    ):
        validator_codes.append("MATRIX_COUNT_INFLATION")
    if (
        unique_candidate_count > 0
        and replay_record_count > unique_candidate_count
        and not replay_expansion_axis
    ):
        validator_codes.append("REPLAY_EXPANSION_UNDECLARED")
    if (
        unique_candidate_count > 0
        and engine_native_status == "ENGINE_NATIVE_FAILED_NO_RUNNER_INVOCATIONS"
        and candidate_source_status
        not in {
            "CANDIDATE_SOURCE_COMPAT_PROXY_DISCOVERY",
            "CANDIDATE_SOURCE_FALLBACK_SYNTHETIC",
            "CANDIDATE_SOURCE_MIXED_ENGINE_AND_PROXY",
        }
    ):
        validator_codes.append("SUMMARY_INCONSISTENT")
    if (
        engine_native_candidate_count == 0
        and any(str(row.get("engine_id") or "") for row in candidate_rows)
        and candidate_source_status == "CANDIDATE_SOURCE_NOT_PROVEN"
    ):
        validator_codes.append("SUMMARY_INCONSISTENT")
    deduped = tuple(dict.fromkeys(validator_codes))
    status = (
        "MATRIX_COUNT_INFLATION"
        if "MATRIX_COUNT_INFLATION" in deduped
        else "COUNT_SEMANTICS_CONSISTENT"
    )
    return status, deduped


def _load_strategy_ladder_summary_payload(
    output_root: Path,
    *,
    jobs: tuple[CockpitBacktestJobRecord, ...],
    run_id: str,
) -> tuple[dict[str, object], Path | None]:
    for run_dir in _strategy_ladder_run_dir_candidates(
        output_root,
        jobs=jobs,
        run_id=run_id,
    ):
        payload = _load_json(run_dir / "reports" / "strategy_ladder_summary.json", default={})
        if isinstance(payload, dict) and payload:
            return payload, run_dir
    return {}, None


def _load_governed_audit_evidence_projection(
    run_dir: Path,
) -> dict[str, object]:
    index_path = run_dir / "reports" / "governed_audit_evidence_index.json"
    index = load_governed_audit_evidence_index(index_path)
    if index is None:
        return {}
    return build_governed_audit_evidence_projection(
        index=index,
        index_path=index_path,
    )


def _strategy_ladder_run_dir_candidates(
    output_root: Path,
    *,
    jobs: tuple[CockpitBacktestJobRecord, ...],
    run_id: str,
) -> tuple[Path, ...]:
    candidates: list[Path] = []
    ladder_root = output_root / "backtest_strategy_ladder"
    if run_id:
        candidates.append(ladder_root / run_id)
    for job in jobs:
        if job.job_id:
            candidates.append(ladder_root / job.job_id)
        for ref in job.output_refs:
            extracted = _extract_strategy_ladder_run_dir(Path(ref))
            if extracted is not None:
                candidates.append(extracted)
    if ladder_root.is_dir():
        try:
            direct_children = sorted(
                child for child in ladder_root.iterdir() if child.is_dir()
            )
        except OSError:
            direct_children = []
        if len(direct_children) == 1:
            candidates.append(direct_children[0])
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return tuple(unique)


def _extract_strategy_ladder_run_dir(path: Path) -> Path | None:
    parts = list(path.parts)
    for index, part in enumerate(parts):
        if part != "backtest_strategy_ladder":
            continue
        next_index = index + 1
        if next_index >= len(parts):
            return None
        return Path(*parts[: next_index + 1])
    return None


def _load_json_array_rows(path: Path, *, limit: int = 25) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return []
    if not isinstance(payload, list):
        return []
    rows: list[dict[str, object]] = []
    for item in payload[:limit]:
        if isinstance(item, dict):
            rows.append(dict(item))
    return rows


def _load_jsonl_rows(path: Path, *, limit: int = 25) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    rows: list[dict[str, object]] = []
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                if len(rows) >= limit:
                    break
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    rows.append(payload)
    except OSError:
        return []
    return rows


def _load_candidate_row_by_id(
    candidate_events_path: Path,
    candidate_id: str,
) -> dict[str, object] | None:
    if not candidate_events_path.is_file():
        return None
    try:
        with candidate_events_path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if (
                    isinstance(payload, dict)
                    and str(payload.get("candidate_id") or "") == candidate_id
                ):
                    return payload
    except OSError:
        return None
    return None


def _load_candidate_replay_payload(
    run_dir: Path,
    candidate_id: str,
    *,
    cache: dict[str, dict[str, object]],
) -> dict[str, object]:
    if candidate_id in cache:
        return cache[candidate_id]
    path = run_dir / "detailed_replay" / f"{candidate_id}.json"
    payload = _load_json(path, default={}) if path.is_file() else {}
    cache[candidate_id] = payload if isinstance(payload, dict) else {}
    return cache[candidate_id]


def _load_candidate_window_payload(
    run_dir: Path,
    candidate_id: str,
) -> dict[str, object]:
    indexed = run_dir / "candidate_replay_windows" / f"{candidate_id}.json"
    payload = _load_json(indexed, default={})
    if isinstance(payload, dict) and payload:
        return payload
    return {}


def _select_primary_bucket_result(
    replay_payload: dict[str, object],
) -> dict[str, object]:
    bucket_results = replay_payload.get("bucket_results")
    rows: list[dict[str, object]] = []
    if isinstance(bucket_results, list):
        rows = [dict(item) for item in bucket_results if isinstance(item, dict)]
    if not rows:
        bucket_summary = replay_payload.get("bucket_result_summary")
        if isinstance(bucket_summary, list):
            rows = [dict(item) for item in bucket_summary if isinstance(item, dict)]
    rows.sort(key=lambda item: int(item.get("capital_bucket") or 0))
    return rows[0] if rows else {}


def _candidate_timestamp_ms(candidate_payload: dict[str, object]) -> int:
    value = candidate_payload.get("timestamp_ms")
    if isinstance(value, int):
        return value
    ns_value = candidate_payload.get("timestamp_ns")
    if isinstance(ns_value, int):
        return int(ns_value / 1_000_000)
    return 0


def _build_candidate_explorer_row(
    candidate_payload: dict[str, object],
    replay_payload: dict[str, object],
) -> dict[str, object]:
    compatibility = candidate_payload.get("compatibility_payload")
    compat = compatibility if isinstance(compatibility, dict) else {}
    primary = _select_primary_bucket_result(replay_payload)
    replay_status = str(
        replay_payload.get("detailed_replay_status") or "DETAILED_REPLAY_NOT_PROVEN"
    )
    execution_state = str(primary.get("execution_state") or "NOT_PROVEN")
    net_return = primary.get("executed_only_net_return")
    return {
        "candidate_id": str(candidate_payload.get("candidate_id") or ""),
        "timestamp_ms": _candidate_timestamp_ms(candidate_payload),
        "pair": str(candidate_payload.get("pair") or ""),
        "engine_id": str(candidate_payload.get("engine_id") or ""),
        "strategy_id": str(candidate_payload.get("strategy_id") or ""),
        "timeframe": str(candidate_payload.get("timeframe") or ""),
        "side": str(compat.get("side") or ""),
        "signal_strength": candidate_payload.get("preliminary_score"),
        "expected_ce": primary.get("expected_ce_net", compat.get("expected_edge_bps")),
        "expected_cost": (
            (float(compat.get("spread_bps") or 0.0) + float(compat.get("slippage_bps") or 0.0))
            if compat
            else None
        ),
        "score_raw": compat.get("raw_score"),
        "score_penalized": compat.get("penalized_score"),
        "score_final": compat.get("final_score"),
        "candidate_status": str(candidate_payload.get("candidate_source") or ""),
        "replay_status": replay_status,
        "accepted_or_refused": (
            "ACCEPTED" if execution_state in {"executed", "reduced"} else "REFUSED"
        ),
        "refusal_reason": ", ".join(
            str(item) for item in (primary.get("reason_codes") or [])[:3]
        ),
        "outcome_status": execution_state,
        "net_result": (
            round(float(net_return) * 10_000.0, 6)
            if isinstance(net_return, (int, float))
            else None
        ),
    }


def _build_candidate_detail_payload(
    candidate_payload: dict[str, object],
    replay_payload: dict[str, object],
) -> dict[str, object]:
    compatibility = candidate_payload.get("compatibility_payload")
    compat = compatibility if isinstance(compatibility, dict) else {}
    reason_codes = tuple(
        str(item) for item in (candidate_payload.get("preliminary_reason_codes") or ())
    )
    score_decomposition = {
        key: compat.get(key)
        for key in ("raw_score", "penalized_score", "final_score", "expected_edge_bps")
        if compat.get(key) is not None
    }
    warning_codes = tuple(
        code
        for code in reason_codes
        if "MISSING" in code or "FAILED" in code or "NOT_PROVEN" in code
    )
    micro_not_applied = any("microstructure.not_applied" in code for code in reason_codes)
    return {
        "candidate_id": str(candidate_payload.get("candidate_id") or ""),
        "timestamp_ms": _candidate_timestamp_ms(candidate_payload),
        "pair": str(candidate_payload.get("pair") or ""),
        "engine_id": str(candidate_payload.get("engine_id") or ""),
        "strategy_id": str(candidate_payload.get("strategy_id") or ""),
        "timeframe": str(candidate_payload.get("timeframe") or ""),
        "candidate_source": str(candidate_payload.get("candidate_source") or ""),
        "feature_refs": tuple(str(item) for item in (candidate_payload.get("feature_refs") or ())),
        "reason_codes": reason_codes,
        "feature_values": dict(compat.get("feature_values") or {}),
        "scoring_trace_status": "READY" if score_decomposition else "NOT_PROVEN",
        "score_decomposition": score_decomposition,
        "warning_codes": (
            warning_codes
            if score_decomposition
            else (*warning_codes, "SCORING_DECOMPOSITION_MISSING")
        ),
        "microstructure_consumption_status": (
            "NOT_CONSUMED" if micro_not_applied else "PARTIAL"
        ),
        "microstructure_not_consumed_reason": (
            "engine_c.microstructure.not_applied" if micro_not_applied else ""
        ),
        "score_raw": compat.get("raw_score"),
        "score_penalized": compat.get("penalized_score"),
        "score_final": compat.get("final_score"),
        "spread_bps": compat.get("spread_bps"),
        "slippage_bps": compat.get("slippage_bps"),
        "expected_edge_bps": compat.get("expected_edge_bps"),
        "gross_return_bps": compat.get("gross_return_bps"),
        "replay_status": str(
            replay_payload.get("detailed_replay_status") or "DETAILED_REPLAY_NOT_PROVEN"
        ),
    }


def _build_candidate_replay_payload(
    replay_payload: dict[str, object],
) -> dict[str, object]:
    primary = _select_primary_bucket_result(replay_payload)
    if not primary:
        return {}
    net_return = primary.get("executed_only_net_return")
    return {
        "detailed_replay_status": str(
            replay_payload.get("detailed_replay_status") or "DETAILED_REPLAY_NOT_PROVEN"
        ),
        "capital_bucket": primary.get("capital_bucket"),
        "execution_state": str(primary.get("execution_state") or ""),
        "no_fill_flag": bool(primary.get("no_fill_flag", False)),
        "partial_fill_flag": bool(primary.get("partial_fill_flag", False)),
        "expected_ce_net": primary.get("expected_ce_net"),
        "net_return_bps": (
            round(float(net_return) * 10_000.0, 6)
            if isinstance(net_return, (int, float))
            else None
        ),
        "fee_source_status": str(primary.get("fee_source_status") or ""),
        "impact_source_status": str(primary.get("impact_source_status") or ""),
        "fill_realism_status": str(primary.get("fill_realism_status") or ""),
        "cost_parity_status": str(primary.get("cost_parity_status") or ""),
        "executed_only_net_return_status": str(
            primary.get("executed_only_net_return_status") or ""
        ),
        "reason_codes": tuple(str(item) for item in (primary.get("reason_codes") or ())),
        "book_depth_source_status": str(primary.get("book_depth_source_status") or ""),
    }


def _derive_trade_summary(
    *,
    summary: StrategyLadderBacktestSummary,
    trade_rows: list[dict[str, object]],
    refusal_rows: list[dict[str, object]],
    loss_rows: list[dict[str, object]],
    pair_rows: list[dict[str, object]],
) -> dict[str, object]:
    updates: dict[str, object] = {}
    trade_count = len(trade_rows) or int(summary.executed_count + summary.reduced_count)
    refusal_count = len(refusal_rows) or int(summary.no_fill_count)
    loss_count = len(loss_rows)
    winning_count = 0
    losing_count = 0
    gross_values: list[float] = []
    net_values: list[float] = []
    for row in trade_rows:
        net_value = row.get("net_return_bps")
        if isinstance(net_value, (int, float)):
            net_float = float(net_value)
            net_values.append(net_float)
            if net_float > 0:
                winning_count += 1
            else:
                losing_count += 1
        gross_value = row.get("gross_return_bps")
        if isinstance(gross_value, (int, float)):
            gross_values.append(float(gross_value))
    if not loss_count:
        loss_count = losing_count
    updates["trade_count"] = trade_count
    updates["refusal_count"] = refusal_count
    updates["loss_count"] = loss_count
    updates["winning_count"] = winning_count
    updates["losing_count"] = losing_count
    updates["gross_pnl_bps"] = round(sum(gross_values), 6) if gross_values else None
    updates["net_pnl_bps"] = round(sum(net_values), 6) if net_values else None
    positive = [value for value in net_values if value > 0]
    negative = [value for value in net_values if value <= 0]
    updates["avg_gain_bps"] = (
        round(sum(positive) / len(positive), 6) if positive else None
    )
    updates["avg_loss_bps"] = (
        round(sum(negative) / len(negative), 6) if negative else None
    )
    updates["max_drawdown_bps"] = _compute_drawdown_bps(net_values)
    if pair_rows:
        row = pair_rows[0]
        for field_name in (
            "executed_count",
            "reduced_count",
            "no_fill_count",
            "fee_source_status",
            "impact_source_status",
            "fill_realism_status",
            "cost_parity_status",
            "executed_only_net_return_status",
            "true_net_equity_drawdown_status",
        ):
            value = row.get(field_name)
            if field_name.endswith("_status") and isinstance(value, str):
                alias = {
                    "fee_source_status": "replay_fee_source_status",
                    "impact_source_status": "replay_impact_source_status",
                    "fill_realism_status": "replay_fill_realism_status",
                    "cost_parity_status": "replay_cost_parity_status",
                    "executed_only_net_return_status": "replay_executed_only_net_return_status",
                    "true_net_equity_drawdown_status": "replay_true_net_equity_drawdown_status",
                }.get(field_name)
                if alias:
                    updates[alias] = value
            elif isinstance(value, int):
                updates[field_name] = value
    return updates


def _derive_no_trade_refusal_audit(
    *,
    summary: StrategyLadderBacktestSummary,
    refusal_rows: list[dict[str, object]],
    engine_rows: list[dict[str, object]],
    pair_rows: list[dict[str, object]],
) -> dict[str, object]:
    if not refusal_rows:
        return {}
    updates: dict[str, object] = {}
    total_refusals = len(refusal_rows)
    reason_counter: Counter[str] = Counter()
    engine_counter: Counter[str] = Counter()
    per_engine_reason_counter: dict[str, Counter[str]] = defaultdict(Counter)
    bucket_counter: Counter[int] = Counter()
    bucket_hard_blocked_counter: Counter[int] = Counter()
    common_reason_codes: set[str] | None = None
    for row in refusal_rows:
        engine_id = str(row.get("engine_id") or "unknown")
        engine_counter[engine_id] += 1
        reason_codes = tuple(
            str(code)
            for code in (row.get("reason_codes") or ())
            if isinstance(code, str) and code
        )
        reason_set = set(reason_codes)
        if common_reason_codes is None:
            common_reason_codes = set(reason_set)
        else:
            common_reason_codes &= reason_set
        for code in reason_set:
            reason_counter[code] += 1
            per_engine_reason_counter[engine_id][code] += 1
        capital_bucket = row.get("capital_bucket")
        if isinstance(capital_bucket, int):
            bucket_counter[capital_bucket] += 1
            if str(row.get("execution_state") or "") == "hard_blocked":
                bucket_hard_blocked_counter[capital_bucket] += 1
    resolved_common_codes = common_reason_codes or set()
    engine_matrix_index = {
        str(row.get("engine_id") or ""): row for row in engine_rows if isinstance(row, dict)
    }
    selected_count_total = sum(
        int(row.get("selected_count") or 0)
        for row in pair_rows
        if isinstance(row, dict)
    )
    hard_blocked_total = sum(
        int(row.get("hard_blocked_count") or 0)
        for row in pair_rows
        if isinstance(row, dict)
    )
    if hard_blocked_total <= 0:
        hard_blocked_total = sum(
            1
            for row in refusal_rows
            if str(row.get("execution_state") or "") == "hard_blocked"
        )
    engine_audit_rows: list[dict[str, object]] = []
    for engine_id in sorted(engine_counter):
        matrix_row = engine_matrix_index.get(engine_id, {})
        specific_reason_counts = [
            (code, count)
            for code, count in per_engine_reason_counter[engine_id].items()
            if code not in resolved_common_codes
        ]
        non_build14_specific_reason_counts = [
            (code, count)
            for code, count in specific_reason_counts
            if not code.startswith("BUILD14_APPLIED:")
            and not code.startswith("BUILD14_READER:")
            and code != "BUILD14_SHADOW_ENABLED_ACTIVE"
        ]
        if non_build14_specific_reason_counts:
            specific_reason_counts = non_build14_specific_reason_counts
        specific_reason_counts.sort(key=lambda item: (-item[1], item[0]))
        if not specific_reason_counts:
            specific_reason_counts = sorted(
                per_engine_reason_counter[engine_id].items(),
                key=lambda item: (-item[1], item[0]),
            )
        engine_audit_rows.append(
            {
                "engine_id": engine_id,
                "refusal_count": engine_counter[engine_id],
                "record_count": int(matrix_row.get("record_count") or engine_counter[engine_id]),
                "selected_count": int(matrix_row.get("selected_count") or 0),
                "hard_blocked_count": int(
                    matrix_row.get("hard_blocked_count") or engine_counter[engine_id]
                ),
                "top_reason_codes": tuple(
                    code for code, _ in specific_reason_counts[:4]
                ),
            }
        )
    sorted_reason_counts = sorted(
        reason_counter.items(),
        key=lambda item: (-item[1], item[0]),
    )
    reason_audit_rows = tuple(
        {
            "reason_code": code,
            "count": count,
            "share_of_refusals": round(count / total_refusals, 6),
        }
        for code, count in sorted_reason_counts[:20]
    )
    capital_bucket_rows = tuple(
        {
            "capital_bucket": bucket,
            "record_count": bucket_counter[bucket],
            "refusal_count": bucket_counter[bucket],
            "selected_count": 0,
            "hard_blocked_count": bucket_hard_blocked_counter[bucket],
        }
        for bucket in sorted(bucket_counter)
    )
    common_codes = tuple(
        code
        for code, _ in sorted(
            (
                (code, reason_counter[code])
                for code in resolved_common_codes
            ),
            key=lambda item: (-item[1], item[0]),
        )
    )
    updates["no_trade_audit_status"] = (
        "NO_TRADE_COLLAPSED_AFTER_HARD_FILTERS"
        if selected_count_total == 0 and hard_blocked_total >= total_refusals
        else "NO_TRADE_REFUSAL_AUDIT_READY"
    )
    updates["no_trade_refusal_rows_total"] = total_refusals
    updates["no_trade_selected_count_total"] = selected_count_total
    updates["no_trade_hard_blocked_count_total"] = hard_blocked_total
    updates["no_trade_executed_count_total"] = int(summary.executed_count or 0)
    updates["no_trade_sample_size_status"] = summary.sample_size_survival_status
    updates["no_trade_common_reason_codes"] = common_codes
    updates["no_trade_engine_rows"] = tuple(engine_audit_rows)
    updates["no_trade_reason_rows"] = reason_audit_rows
    updates["no_trade_capital_bucket_rows"] = capital_bucket_rows
    return updates


def _load_engine_no_trade_diagnosis_updates(run_dir: Path) -> dict[str, object]:
    payload = _load_json(
        run_dir / "reports" / "engine_no_trade_diagnosis.json",
        default={},
    )
    if not isinstance(payload, dict) or not payload:
        return {}
    common_blockers = tuple(
        str(row.get("reason_code") or "")
        for row in (payload.get("common_blockers") or ())
        if isinstance(row, dict) and str(row.get("reason_code") or "")
    )
    engine_rows = tuple(
        {
            "engine_id": str(row.get("engine_id") or ""),
            "candidate_count": int(row.get("candidate_count") or 0),
            "replay_record_count": int(row.get("replay_record_count") or 0),
            "selected_count": int(row.get("selected_count") or 0),
            "hard_blocked_count": int(row.get("hard_blocked_count") or 0),
            "first_blocking_layer": str(row.get("first_blocking_layer") or ""),
            "suspected_wiring_gaps": tuple(
                str(item) for item in (row.get("suspected_wiring_gaps") or ()) if str(item)
            ),
            "recommended_next_action": str(row.get("recommended_next_action") or ""),
        }
        for row in (payload.get("engines") or ())
        if isinstance(row, dict)
    )
    next_actions = tuple(
        dict(row)
        for row in (payload.get("next_action_ranking") or ())
        if isinstance(row, dict)
    )
    first_gate = dict(payload.get("first_gate_analysis") or {})
    return {
        "engine_no_trade_diagnosis_status": (
            "ENGINE_NO_TRADE_DIAGNOSIS_READY"
            if str(payload.get("source_status") or "") == "ok"
            else "ENGINE_NO_TRADE_DIAGNOSIS_NOT_PROVEN"
        ),
        "engine_no_trade_diagnosis_path": str(
            (run_dir / "reports" / "engine_no_trade_diagnosis.json").resolve()
        ),
        "engine_no_trade_first_gate_status": str(
            first_gate.get("gate_status") or "FIRST_GATE_NOT_PROVEN"
        ),
        "engine_no_trade_common_blockers": common_blockers,
        "engine_no_trade_engine_rows": engine_rows,
        "engine_no_trade_next_actions": next_actions,
    }


def _load_gate_waterfall_updates(run_dir: Path) -> dict[str, object]:
    waterfall_path = run_dir / "reports" / "gate_waterfall_analysis.json"
    waterfall_payload = _load_json(waterfall_path, default={})
    engine_path = run_dir / "reports" / "gate_counterfactual_by_engine.json"
    engine_payload = _load_json(engine_path, default={})
    timeframe_path = run_dir / "reports" / "gate_counterfactual_by_timeframe.json"
    timeframe_payload = _load_json(timeframe_path, default={})
    readiness_path = run_dir / "reports" / "expected_edge_readiness_audit.json"
    readiness_payload = _load_json(readiness_path, default={})
    if not isinstance(waterfall_payload, dict) or not waterfall_payload:
        waterfall_payload = {}
    if not isinstance(engine_payload, dict) or not engine_payload:
        engine_payload = {}
    if not isinstance(timeframe_payload, dict) or not timeframe_payload:
        timeframe_payload = {}
    if not isinstance(readiness_payload, dict) or not readiness_payload:
        readiness_payload = {}
    if not waterfall_payload and not readiness_payload:
        return {}
    best_scenario = dict(waterfall_payload.get("best_counterfactual_scenario") or {})
    dominant_gates = tuple(
        dict(row)
        for row in (waterfall_payload.get("dominant_blocking_gates") or ())
        if isinstance(row, dict)
    )
    funnel_rows = tuple(
        dict(row)
        for row in (waterfall_payload.get("funnel_metrics") or ())
        if isinstance(row, dict)
    )
    scenario_rows = tuple(
        dict(row)
        for row in (waterfall_payload.get("scenario_summaries") or ())
        if isinstance(row, dict)
    )
    engine_rows = tuple(
        dict(row)
        for row in (engine_payload.get("rows") or ())
        if isinstance(row, dict)
    )
    timeframe_rows = tuple(
        dict(row)
        for row in (timeframe_payload.get("rows") or ())
        if isinstance(row, dict)
    )
    key_findings = tuple(
        str(item)
        for item in (readiness_payload.get("key_findings") or ())
        if str(item)
    )
    return {
        "gate_waterfall_analysis_status": (
            str(waterfall_payload.get("status") or "GATE_WATERFALL_NOT_PROVEN")
            if waterfall_payload
            else "GATE_WATERFALL_NOT_PROVEN"
        ),
        "gate_waterfall_analysis_path": str(waterfall_path.resolve())
        if waterfall_payload
        else "",
        "gate_waterfall_best_scenario": str(best_scenario.get("scenario_id") or ""),
        "gate_waterfall_canonical_selected_count": int(
            waterfall_payload.get("canonical_selected_count") or 0
        ),
        "gate_waterfall_canonical_executed_count": int(
            waterfall_payload.get("canonical_executed_count") or 0
        ),
        "gate_waterfall_counterfactual_survival_count": int(
            best_scenario.get("counterfactual_survival_count") or 0
        ),
        "gate_waterfall_canonical_vs_counterfactual_delta": int(
            best_scenario.get("delta_vs_canonical_selected") or 0
        ),
        "gate_waterfall_dominant_blocking_gates": dominant_gates,
        "gate_waterfall_funnel_rows": funnel_rows,
        "gate_counterfactual_scenarios": scenario_rows,
        "gate_counterfactual_engine_rows": engine_rows,
        "gate_counterfactual_timeframe_rows": timeframe_rows,
        "expected_edge_readiness_status": (
            str(readiness_payload.get("status") or "EXPECTED_EDGE_READINESS_NOT_PROVEN")
            if readiness_payload
            else "EXPECTED_EDGE_READINESS_NOT_PROVEN"
        ),
        "expected_edge_readiness_verdict": str(
            readiness_payload.get("verdict") or ""
        ),
        "expected_edge_readiness_path": str(readiness_path.resolve())
        if readiness_payload
        else "",
        "expected_edge_readiness_key_findings": key_findings,
    }


def _compute_drawdown_bps(net_values: list[float]) -> float | None:
    if not net_values:
        return None
    running = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in net_values:
        running += value
        peak = max(peak, running)
        max_drawdown = max(max_drawdown, peak - running)
    return round(max_drawdown, 6)


def _summarize_artifact_family_visibility(
    visibility: tuple[ArtifactRuntimeVisibilityProjection, ...],
) -> tuple[ArtifactFamilyVisibilitySummary, ...]:
    rows: list[ArtifactFamilyVisibilitySummary] = []
    for item in visibility:
        rows.append(
            ArtifactFamilyVisibilitySummary(
                family_id=_visibility_family_id(item),
                slot=item.slot,
                artifact_id=item.artifact_id,
                artifact_kind=item.artifact_kind,
                feature_set_version=item.feature_set_version,
                lineage_version=item.lineage_version,
                review_state=item.review_state,
                validation_status=item.validation_status,
                influence_detail=item.influence_detail,
            )
        )
    return tuple(rows)


def _summarize_artifact_family_comparisons(
    *,
    comparisons: tuple[ArtifactComparisonProjection, ...],
    visibility: tuple[ArtifactRuntimeVisibilityProjection, ...],
) -> tuple[ArtifactFamilyComparisonSummary, ...]:
    family_by_artifact_id = {
        item.artifact_id: _base_family(item.artifact_kind)
        for item in visibility
        if item.artifact_id and item.artifact_id != "none"
    }
    rows: list[ArtifactFamilyComparisonSummary] = []
    for item in comparisons:
        family_id = family_by_artifact_id.get(
            item.champion_artifact_id,
            family_by_artifact_id.get(item.challenger_artifact_id, "unknown"),
        )
        rows.append(
            ArtifactFamilyComparisonSummary(
                family_id=family_id,
                comparison_status=item.comparison_status,
                champion_artifact_id=item.champion_artifact_id,
                challenger_artifact_id=item.challenger_artifact_id,
                event_count=item.event_count,
                expected_gain_delta_mean=item.expected_gain_delta_mean,
                expected_ce_delta_mean=item.expected_ce_delta_mean,
                halal_eligible_event_count=item.halal_eligible_event_count,
                halal_excluded_event_count=item.halal_excluded_event_count,
            )
        )
    return tuple(rows)


def _visibility_family_id(item: ArtifactRuntimeVisibilityProjection) -> str:
    family = _base_family(item.artifact_kind)
    if item.slot == "shadow_challenger":
        return f"shadow_{family}"
    return f"active_{family}"


def _base_family(artifact_kind: str) -> str:
    if artifact_kind == "ml_model_artifact":
        return "ml"
    if artifact_kind == "regime_detector_artifact":
        return "regime_detector"
    return "unknown"


def _resource_alert(
    suffix: str,
    *,
    value: float,
    warning: float,
    critical: float,
    format_unit: str,
) -> tuple[str, str, str, str]:
    if value >= critical:
        return (
            suffix,
            "critical",
            "infra",
            f"Host {suffix.upper()} usage is {value:.1f}{format_unit}.",
        )
    if value >= warning:
        return (
            suffix,
            "warning",
            "infra",
            f"Host {suffix.upper()} usage is {value:.1f}{format_unit}.",
        )
    return ("", "", "", "")


def _load_model(path: Path, model_type: type[BaseModel]) -> BaseModel | None:
    if not path.is_file():
        return None
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return None


def _load_json(path: Path, *, default: dict[str, object]) -> dict[str, object]:
    if not path.is_file():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return default
    return payload if isinstance(payload, dict) else default


def _int_value(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _parse_iso(raw_value: str) -> datetime | None:
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


def _calculate_metadata_temporal_drift_days(
    *,
    fetched_at_utc: str,
    replay_end: str,
) -> float | None:
    fetched_at = _parse_iso(fetched_at_utc)
    replay_end_dt = _parse_iso(f"{replay_end}T23:59:59+00:00") if replay_end else None
    if fetched_at is None or replay_end_dt is None:
        return None
    return round(abs((fetched_at - replay_end_dt).total_seconds()) / 86_400.0, 3)


def _timestamp_ms() -> int:
    return int(time.time() * 1000)


__all__ = [
    "CockpitAlert",
    "CockpitRuntimeSurfaces",
    "ObservabilityPageSummary",
    "build_cockpit_alerts",
    "read_logs_summary",
    "read_observability_summary",
    "read_runtime_surfaces",
]
