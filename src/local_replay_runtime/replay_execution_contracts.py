"""Typed execution-realism contracts for governed LOCAL_REPLAY."""

from __future__ import annotations

from execution_backbone.fee_aware_edge_gate import FeeAwareEdgeGateConfig
from execution_backbone.slippage_model import ExecutionSlippageModel
from execution_backbone.spread_guard import ExecutionSpreadGuardModel
from pydantic import BaseModel, Field, model_validator
from portfolio_minimal.opportunity_selector.eligibility_filter import PortfolioSnapshot
from regime_classifier.regime_lite import RegimeLiteThresholds
from risk_backbone.risk_runtime_models import RiskLimits
from scoring_backbone.hard_block_gate.blocker_evaluator import BlockerCondition
from scoring_backbone.ranking_router.ranking_score_builder import RankingWeights

from local_replay_runtime.enums import ReplayExecutionProviderKind
from local_replay_runtime.historical_data_gateway import HistoricalReplayDataset
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord

_SHADOW_PROVIDER_NAME = "shadow_execution_simulator_prudent_replay"
_SHADOW_PROVIDER_VERSION = "shadow_execution_simulator.v1"


class ParityTolerancePolicy(BaseModel, frozen=True):
    """Explicit parity policy for governed replay/shadow comparisons."""

    parity_scope: str = "logical_decision_with_prudent_score_cost_tolerance"
    decision_parity_kind: str = "logical_decision_state"
    score_parity_kind: str = "bounded_float64_score_tolerance"
    cost_parity_kind: str = "prudent_expected_cost_tolerance"
    float_precision: str = "binary64"
    minimum_compared_records: int = Field(default=1, ge=1)
    decision_match_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    score_match_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    score_tolerance: float = Field(default=0.03, ge=0.0)
    cost_tolerance: float = Field(default=0.0005, ge=0.0)


class ShadowExecutionSimulatorConfig(BaseModel, frozen=True):
    """Prudent execution assumptions for the default replay execution provider."""

    slippage_multiplier: float = Field(default=1.15, ge=1.0)
    latency_penalty_multiplier: float = Field(default=1.0, ge=1.0)
    phantom_fill_threshold: float = Field(default=0.15, ge=0.0, le=1.0)
    reduced_fill_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    economic_absurdity_buffer_bps: float = Field(default=0.50, ge=0.0)
    parity_policy: ParityTolerancePolicy = Field(default_factory=ParityTolerancePolicy)
    spread_guard_model: ExecutionSpreadGuardModel | None = None
    slippage_model: ExecutionSlippageModel | None = None
    fee_aware_edge_gate_config: FeeAwareEdgeGateConfig | None = None
    # Restored 2026-05-27 — backbone parity surface config fields (Codex
    # delivery, accidentally removed by an over-eager checkout earlier in
    # the same session). All defaults intentionally `None` so existing
    # test fixtures keep their pre-Codex shadow-simulator behaviour; B2
    # operators wire real values via opt-in calibration or per-run config.
    # Patch BACKBONE-PARITY-P1-S5 (2026-05-27) — Surface #5 branched to
    # canonical backbone : `risk_filter`. Default `RiskLimits` use 1e6
    # neutral caps (`gross/position/loss/beta/cluster`) so the canonical
    # `RiskRuntime.evaluate_candidate` is invoked without spuriously
    # rejecting backtest rows for size cap violations. The drawdown
    # thresholds keep RiskLimits' documented defaults (warning=0.02,
    # observe=0.04) which only impact `RiskExplainability` payload,
    # not the trade decision. The canonical_payload is report-only —
    # the simulator does NOT propagate `evaluation.action` to the
    # trading decision, only to `backbone_surface_report.risk_filter`.
    # Side-effect on `portfolio_state` surface : with both S4
    # (portfolio_snapshot) and S5 (risk_limits) non-None, the fallback
    # reason chain shifts to `PORTFOLIO_CLUSTER_CAPACITY_MISSING` (the
    # default `remaining_cluster_capacity` stays empty until upstream
    # runtime injects per-pair mappings).
    risk_limits: RiskLimits | None = Field(
        default_factory=lambda: RiskLimits(
            gross_cap=1_000_000.0,
            position_cap=1_000_000.0,
            loss_cap=1_000_000.0,
            beta_cap=1_000_000.0,
            cluster_cap=1_000_000.0,
        )
    )
    # Patch BACKBONE-PARITY-P1-S4 (2026-05-27) — Surface #4 branched to
    # canonical backbone : `portfolio_state`. Default snapshot wraps
    # `PortfolioSnapshot` with unbounded capacities (`inf`) so the canonical
    # `apply_caps` evaluator can be invoked without spurious gross/loss/beta
    # cap reductions in the surface report. `remaining_cluster_capacity`
    # stays empty by default — when the upstream runtime does not inject
    # per-pair cluster mappings the surface still falls back with reason
    # `PORTFOLIO_CLUSTER_CAPACITY_MISSING` (once S5 risk_limits is also
    # wired) instead of `PORTFOLIO_SNAPSHOT_NOT_CONFIGURED_FOR_BACKTEST`.
    # `apply_caps` is safe under `inf` capacities (lines 71/83 of
    # `portfolio_minimal/allocation_router/portfolio_cap_applier.py` short
    # circuit on `< float("inf")`). The canonical_payload is report-only —
    # the simulator does NOT propagate `capped.final_size` to the trading
    # decision, only to `backbone_surface_report.portfolio_state`.
    portfolio_snapshot: PortfolioSnapshot | None = Field(
        default_factory=lambda: PortfolioSnapshot(
            remaining_gross_capacity=float("inf"),
            remaining_loss_capacity=float("inf"),
            remaining_beta_capacity=float("inf"),
        )
    )
    # Patch BACKBONE-PARITY-P1-S3 (2026-05-27) — Surface #3 branched to
    # canonical backbone : `regime_classification`. Default thresholds
    # come from `RegimeLiteThresholds.from_documented_defaults()` (THR-RG01..04
    # documented doctrine seam ; vol_extreme=0.08, drop_extreme=0.05,
    # drawdown_extreme=0.02, dispersion_extreme=0.05, hysteresis=2h,
    # cooldown=24h). The canonical classifier is report-only at runtime
    # (`entries_blocked` is NOT consumed by the simulator to gate trades —
    # it only appears in `backbone_surface_report.regime_classification`).
    # When the 4 required feature metrics (`btc_realized_vol_24h`,
    # `btc_drop_1h`, `intraday_drawdown`, `engine_return_dispersion`) are
    # present in `row.feature_values` the surface status flips from
    # `NO_SURFACE_RESULT_AVAILABLE` / `LOCAL_REPLAY_FALLBACK_USED` to
    # `CANONICAL_BACKBONE_USED`. When metrics are missing the surface
    # falls back with `REGIME_CLASSIFIER_INPUTS_MISSING` instead of
    # `REGIME_LITE_THRESHOLDS_NOT_CONFIGURED` (still local-replay payload
    # when `row.regime` is set, NO_SURFACE_RESULT otherwise).
    regime_lite_thresholds: RegimeLiteThresholds | None = Field(
        default_factory=RegimeLiteThresholds.from_documented_defaults
    )
    # Patch BACKBONE-PARITY-P1-S2 (2026-05-27) — Surface #2 branched to
    # canonical backbone : `scoring_ranking`. Default `RankingWeights()`
    # uses operational weights (w_score=1.0, w_ce=0.5, w_cost=0.3,
    # w_corr=0.2, w_risk=0.2). The ranker computes a composite score from
    # these weights ; with these defaults the ranking is functional and
    # non-blocking — it cannot refuse a trade by itself, it can only
    # re-order candidates. Switch from `LOCAL_REPLAY_FALLBACK_USED` to
    # `CANONICAL_BACKBONE_USED`.
    scoring_ranking_weights: RankingWeights | None = Field(
        default_factory=RankingWeights
    )
    # Patch BACKBONE-PARITY-P1-S1 (2026-05-27) — Surface #1 branched to
    # canonical backbone : `hard_block_gate`. Default `BlockerCondition()`
    # has all `is_X = False`, so the canonical evaluator returns
    # `is_blocked = False` (no new hard block added). Trading behaviour is
    # unchanged ; only the `backbone_surface_report.hard_block_gate.status`
    # flips from `LOCAL_REPLAY_FALLBACK_USED` to `CANONICAL_BACKBONE_USED`.
    hard_block_conditions: BlockerCondition | None = Field(
        default_factory=BlockerCondition
    )
    ml_mode: str = "ML_MODE_OFF"
    expected_edge_model_status: str = "EXPECTED_EDGE_ARTIFACT_NOT_DECLARED"
    expected_edge_model_artifact_hash: str | None = None
    expected_edge_model_feature_hash: str | None = None
    expected_edge_training_artifact_ref: str | None = None
    # Protocols / Build-14 surface metadata (Codex backbone-parity tranche)
    protocol_contract_refs: tuple[str, ...] = ()
    refusal_contract_status: str = "REFUSAL_CONTRACT_NOT_DECLARED"
    live_transport_enabled: bool = False
    build14_feature_groups: tuple[str, ...] = ()
    build14_context_status: str = "BUILD14_CONTEXT_NOT_DECLARED"
    build14_upstream_filter_status: str = "BUILD14_UPSTREAM_FILTER_NOT_DECLARED"
    execution_runtime_projection_ref: str | None = None


class ReplayParityDiagnosticsSummary(BaseModel, frozen=True):
    """Typed parity diagnostics payload exported by governed LOCAL_REPLAY."""

    parity_status: str = Field(..., min_length=1)
    dataset_id: str = "unknown_dataset"
    decision_match_rate: float = Field(..., ge=0.0, le=1.0)
    score_match_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    baseline_status: str = "unknown"
    score_alignment: str = "unknown"
    cost_alignment: str = "unknown"
    mean_cost_gap: float = Field(default=0.0, ge=0.0)
    compared_records: int = Field(default=0, ge=0)
    missing_baseline_records: int = Field(default=0, ge=0)
    divergence_count: int = Field(default=0, ge=0)
    shared_core_match: bool = False
    book_depth_available: bool | None = None
    book_depth_levels: int | None = Field(default=None, ge=0)
    book_depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    book_depth_snapshot_count: int | None = Field(default=None, ge=0)
    book_depth_event_count: int | None = Field(default=None, ge=0)
    book_depth_missing_count: int | None = Field(default=None, ge=0)
    book_depth_staleness_status: str = "BOOK_DEPTH_NOT_PROVEN"
    impact_depth_level_used: int | None = Field(default=None, ge=0)
    impact_depth_readiness_status: str = "BOOK_DEPTH_NOT_PROVEN"
    shadow_extension_required: bool = True
    shadow_extension_reason: str | None = "NO_PROMOTION_GRADE_REPLAY_IMPACT_PROOF"
    minimum_shadow_days_required: int | None = Field(default=None, ge=0)
    shadow_extension_status: str = "MICRO_LIVE_BLOCKED_BY_DEPTH"
    impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    fill_ratio_source: str = "UNKNOWN"
    fill_realism_status: str = "FILL_REALISM_NOT_PROVEN"
    fill_source_status: str = "FILL_SOURCE_NOT_PROVEN"
    fill_model_name: str | None = None
    fill_model_version: str | None = None
    fill_ratio_expected: float | None = Field(default=None, ge=0.0, le=1.0)
    fill_ratio_observed: float | None = Field(default=None, ge=0.0, le=1.0)
    partial_fill_rate_expected: float | None = Field(default=None, ge=0.0, le=1.0)
    partial_fill_rate_observed: float | None = Field(default=None, ge=0.0, le=1.0)
    no_fill_rate_expected: float | None = Field(default=None, ge=0.0, le=1.0)
    no_fill_rate_observed: float | None = Field(default=None, ge=0.0, le=1.0)
    fill_latency_ms_expected: float | None = Field(default=None, ge=0.0)
    fill_latency_ms_observed: float | None = Field(default=None, ge=0.0)
    synthetic_fill_flag: bool = False
    measured_fill_flag: bool = False
    fill_provenance_ref: str | None = None
    fill_input_hash: str | None = None
    fill_policy_version: str | None = None
    realized_slippage_status: str = "NOT_PROVEN"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
    replay_cost_components: tuple[str, ...] = ()
    shadow_cost_components: tuple[str, ...] = ()
    live_cost_components: tuple[str, ...] = ()
    replay_fee_bps: float | None = Field(default=None, ge=0.0)
    shadow_fee_bps: float | None = Field(default=None, ge=0.0)
    live_fee_bps: float | None = Field(default=None, ge=0.0)
    replay_impact_bps: float | None = Field(default=None, ge=0.0)
    shadow_impact_bps: float | None = Field(default=None, ge=0.0)
    live_impact_bps: float | None = Field(default=None, ge=0.0)
    replay_slippage_bps: float | None = Field(default=None, ge=0.0)
    shadow_slippage_bps: float | None = Field(default=None, ge=0.0)
    live_slippage_bps: float | None = Field(default=None, ge=0.0)
    replay_fill_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    shadow_fill_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    live_fill_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    cost_drift_bps: float | None = None
    cost_drift_status: str = "NOT_PROVEN"
    parity_sample_count: int = Field(default=0, ge=0)
    parity_window_start: str | None = None
    parity_window_end: str | None = None
    parity_input_hash: str | None = None
    parity_policy_version: str | None = None
    parity_policy: dict[str, object] = Field(default_factory=dict)
    canonical_execution_backbone_status: str = "REPLAY_PROXY_ONLY"
    execution_label_source: str = "REPLAY_PROXY_EXECUTION"
    fee_model_source: str = "REPLAY_PROXY"
    spread_model_source: str = "REPLAY_PROXY"
    slippage_model_source: str = "REPLAY_PROXY"
    partial_fill_model_source: str = "REPLAY_PROXY"
    adverse_selection_source: str = "REPLAY_PROXY"
    order_type_selection_source: str = "REPLAY_PROXY"
    venue_constraints_source: str = "REPLAY_PROXY"
    execution_fidelity_gap_codes: tuple[str, ...] = ()
    spread_guard_model_loaded: bool = False
    slippage_model_loaded: bool = False
    execution_runtime_projection_ref: str | None = None
    canonical_expected_cost_components: tuple[str, ...] = ()
    # Restored 2026-05-27 — backbone parity surface report payload (Codex
    # delivery, accidentally removed earlier this session by an over-eager
    # checkout). Populated by `build_backbone_parity_surface_report` in
    # `shadow_execution_simulator.py:2493`.
    backbone_surface_report: dict[str, object] = Field(default_factory=dict)


class ReplayExecutionProviderRef(BaseModel, frozen=True):
    """Implementation metadata for the current replay execution provider."""

    provider_kind: ReplayExecutionProviderKind = ReplayExecutionProviderKind.SHADOW_SIMULATOR
    provider_name: str = Field(default=_SHADOW_PROVIDER_NAME, min_length=1)
    provider_version: str = Field(default=_SHADOW_PROVIDER_VERSION, min_length=1)


class ReplayExecutionEvaluationRequest(BaseModel, frozen=True):
    """Typed input for execution-realism evaluation inside LOCAL_REPLAY."""

    dataset: HistoricalReplayDataset
    execution_label: str = Field(default="shadow_fidelity_mode", min_length=1)
    execution_runtime_projection_path: str | None = None
    provider: ReplayExecutionProviderRef = Field(default_factory=ReplayExecutionProviderRef)
    simulator_config: ShadowExecutionSimulatorConfig = Field(
        default_factory=ShadowExecutionSimulatorConfig
    )


class ReplayExecutionEvaluationResult(BaseModel, frozen=True):
    """Typed output of the replay execution-realism seam."""

    request: ReplayExecutionEvaluationRequest
    dtr_records: tuple[DTRRecord, ...]
    parity_diagnostics: ReplayParityDiagnosticsSummary

    @model_validator(mode="after")
    def validate_record_count(self) -> "ReplayExecutionEvaluationResult":
        if len(self.dtr_records) != self.request.dataset.record_count:
            raise ValueError(
                "ReplayExecutionEvaluationResult dtr_records must match dataset record_count"
            )
        return self

    @property
    def parity_diagnostics_payload(self) -> dict[str, object]:
        return self.parity_diagnostics.model_dump(mode="json")


__all__ = [
    "ParityTolerancePolicy",
    "ReplayExecutionEvaluationRequest",
    "ReplayExecutionEvaluationResult",
    "ReplayExecutionProviderRef",
    "ReplayParityDiagnosticsSummary",
    "ShadowExecutionSimulatorConfig",
]
